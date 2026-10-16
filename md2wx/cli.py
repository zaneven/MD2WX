"""
MD2WX 命令行工具 (CLI Entrypoint)
支持多主题风格化渲染、自定义主题文件加载与一键发布
"""
import os
import re
import sys
import json
import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import Dict
from urllib.parse import unquote

from . import __version__
from .parser import (
    markdown_to_wechat_html,
    parse_frontmatter,
    strip_markdown,
    extract_quote_text,
    collect_external_image_urls,
    expand_obsidian_images,
)
from .themes import list_themes, get_theme, get_builtin_themes_dir, get_user_themes_dir, get_builtin_theme_cover
from .cover import (
    render_article_cover_png,
    render_article_dual_cover_png,
    stitch_cover_images,
    WECHAT_CROP_235_1,
    WECHAT_CROP_1_1,
)
from .envutil import load_env, is_placeholder
from .imagehost import (
    get_image_host_config,
    upload_image_file as upload_image_to_host,
    upload_image_bytes,
    download_image_bytes,
    CONFIG_HINT as IMAGE_HOST_HINT,
)
from .uploader import get_access_token, upload_image_to_wechat_cdn, upload_image_bytes_to_wechat_cdn
from .publisher import publish_draft_to_wechat
from .linter import lint_markdown, format_lint_report, has_errors
from .richrender import extract_rich_blocks, resolve_rich_blocks, substitute_rich_html, rehost_data_uri_images

# 各主题封面徽标预设 (与 Web Studio THEME_COVER_PRESETS 保持一致)
COVER_BADGE_PRESETS = {
    "tech-blue": "TECH BLOG",
    "acid-bold": "ACID BOLD",
    "dark-night": "NIGHT RUN",
    "elegant-purple": "AESTHETIC",
    "terminal-geek": "BASH / DEV",
    "vintage-news": "WEEKLY PRESS",
    "warm-memo": "HEALING NOTE",
    "warm-orange": "SUNSHINE",
    "wechat-green": "WECHAT OFFICIAL",
    "forest-green": "FOREST NOTE",
    "terracotta-clay": "CLAY CRAFT",
    "morandi-mist": "MORANDI",
    "pastel-cream": "PASTEL DAY",
}

# 微信公众平台字段长度上限
WECHAT_TITLE_MAX_LEN = 64
WECHAT_DIGEST_MAX_LEN = 120

def print_themes_list():
    """以精美清晰的终端格式打印所有已安装主题清单（遵循规范，不使用 Emoji）"""
    all_themes = list_themes()
    print("================================================================================")
    print("  MD2WX 视觉主题库 (Theme Gallery)")
    print("================================================================================")
    print(f"内置主题目录: {get_builtin_themes_dir()}")
    print(f"用户扩展目录: {get_user_themes_dir()}")
    print("--------------------------------------------------------------------------------")
    print(f"{'主题 ID (ID)':<18} | {'主题名称与视觉特征':<26} | {'主色调'}")
    print("--------------------------------------------------------------------------------")
    for tid, t in all_themes.items():
        name = t.get("name", tid)
        desc = t.get("description", "")
        accent = t.get("accent", "#000000")
        styles = t.get("styles", {})
        container_style = styles.get("container", "clean")
        h1_style = styles.get("h1", "underline")

        print(f"[*] {tid:<14} | {name:<24} | {accent}")
        print(f"    - 风格标签: [容器: {container_style}] [H1: {h1_style}]")
        print(f"    - 描述说明: {desc}")
        print()
    print("--------------------------------------------------------------------------------")
    print("使用方式:")
    print("  md2wx article.md -t vintage-news -c       # 使用指定内置主题")
    print("  md2wx article.md -t ./my-theme.json -c   # 使用自定义主题文件")
    print("================================================================================")

def load_env_credentials() -> Dict[str, str]:
    """从环境变量或常见 .env 路径加载微信凭证（统一走 envutil.load_env）"""
    env = load_env()
    app_id = env.get("WECHAT_APP_ID", "")
    app_secret = env.get("WECHAT_APP_SECRET", "")
    if is_placeholder(app_id):
        app_id = ""
    if is_placeholder(app_secret):
        app_secret = ""
    return {"app_id": app_id, "app_secret": app_secret}

def copy_html_to_clipboard(html: str) -> bool:
    """在 macOS 环境下将 HTML 作为富文本写入剪贴板 (可以直接 Cmd+V 粘贴到微信后台)"""
    if sys.platform != "darwin":
        return False
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(html)
            tmp_path = f.name
        script = f'set the clipboard to (read (POSIX file "{tmp_path}") as «class HTML»)'
        # 使用 argv 形式调用，避免 shell 拼接与注入风险
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

def main():
    parser = argparse.ArgumentParser(
        prog="md2wx",
        description="MD2WX: 将 Markdown 文档转换为微信公众号原生内联高质感 HTML，支持剪贴板富文本注入与草稿箱一键发布"
    )
    parser.add_argument("input", nargs="?", help="Markdown 文件路径（留空则从标准输入 stdin 读取）")
    parser.add_argument("-o", "--output", help="输出 HTML 文件路径")
    parser.add_argument("-c", "--clip", action="store_true", help="将生成的带样式富文本直接复制到剪贴板（微信后台直接 Cmd+V）")
    parser.add_argument("-t", "--theme", default="tech-blue", help="选择设计主题名称 (如 vintage-news, terminal-geek 等) 或指定外部 JSON 主题文件路径")
    parser.add_argument("--list-themes", action="store_true", help="列出所有可用的内置与用户自定义设计主题")
    parser.add_argument("--web", action="store_true", help="启动 MD2WX Web Studio 可视化排版工作台并在浏览器中打开")
    parser.add_argument("-p", "--publish", action="store_true", help="一键推送到微信公众号草稿箱")
    parser.add_argument("--dry-run", action="store_true", help="发布演练: 完成渲染与封面解析后打印将上报微信的草稿 payload 摘要，不请求任何微信接口 (需搭配 -p)")
    parser.add_argument("--cover", help="指定头条封面图片路径 (默认优先级: 此参数 > frontmatter cover: > 动态渲染主题双封面 > 正文首图)")
    parser.add_argument("--cover-square", help="指定次条/会话 1:1 方形封面图片路径 (与 --cover 搭配时将自动拼接为双比例合图)")
    parser.add_argument("--no-dual-cover", action="store_true", help="禁用双比例拼接封面，仅生成单张 2.35:1 头条封面")
    parser.add_argument("--author", help="指定文章作者 (默认读取 Frontmatter 或 '野生宝藏箱')")
    parser.add_argument("--title", help="指定文章标题 (默认读取 Frontmatter 或首个 H1)")
    parser.add_argument("--app-id", help="微信 AppID (默认从环境变量或 .env 读取)")
    parser.add_argument("--no-cover", action="store_true", help="不在正文顶部注入封面卡片")
    parser.add_argument("--upload-image", metavar="PATH", help="将本地图片上传到 .env 配置的在线图床并输出图片链接 (需配置 IMAGE_HOST_UPLOAD_URL)")
    parser.add_argument("--lint", action="store_true", help="对文章执行发稿规范自检 (标题 20 字 / 摘要 50 字 / 禁填 cover / 控制字符 / 外链图片)")
    parser.add_argument("--rehost-images", action="store_true", help="将正文外链图片自动转存到 .env 配置的在线图床并换链 (规避微信外链封禁)")

    args = parser.parse_args()

    # 处理 --web 选项
    if args.web:
        import socket
        import time
        import webbrowser
        web_dir = Path(__file__).resolve().parent.parent / "web"
        port = 3000
        print("================================================================================")
        print("  MD2WX Web Studio (可视化排版工作台)")
        print("================================================================================")
        print(f"前端工作目录: {web_dir}")
        print(f"正在启动本地 Web 预览服务 (http://localhost:{port}) ...")
        try:
            proc = subprocess.Popen(["npm", "run", "dev"], cwd=str(web_dir))
            # 轮询端口就绪后再打开浏览器，避免浏览器先于服务启动而加载失败
            deadline = time.time() + 20
            ready = False
            while time.time() < deadline:
                if proc.poll() is not None:
                    break
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                        ready = True
                        break
                except OSError:
                    time.sleep(0.3)
            if ready:
                webbrowser.open(f"http://localhost:{port}")
            else:
                print("[-] 服务启动超时或已退出，请检查 npm 环境与端口占用。", file=sys.stderr)
            proc.wait()
        except KeyboardInterrupt:
            print("\n[+] 服务已停止。")
            proc.terminate()
        except FileNotFoundError:
            print("[-] 未找到 npm 命令，请先安装 Node.js。", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[-] 启动 Web 服务失败: {e}", file=sys.stderr)
        sys.exit(0)

    # 处理 --list-themes 选项
    if args.list_themes:
        print_themes_list()
        sys.exit(0)

    # 处理 --upload-image 选项：上传本地图片到在线图床并输出链接
    if args.upload_image:
        host_cfg = get_image_host_config()
        if not host_cfg:
            print(f"[-] 错误: {IMAGE_HOST_HINT}", file=sys.stderr)
            print("    配置示例 (.env):", file=sys.stderr)
            print("      IMAGE_HOST_UPLOAD_URL=https://your-image-host/api/uploads", file=sys.stderr)
            print("      IMAGE_HOST_TOKEN=your_token  # 可选", file=sys.stderr)
            sys.exit(1)
        try:
            url = upload_image_to_host(args.upload_image, host_cfg)
            print(f"[+] 图片已上传到图床:", file=sys.stderr)
            sys.stdout.write(url + "\n")
        except Exception as e:
            print(f"[-] 图片上传失败: {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    # 1. 校验主题配置：交给 get_theme 统一解析（含文件路径加载与回退），
    #    并在确实发生回退时给出明确警告，避免预检逻辑与解析逻辑漂移
    theme_input = args.theme
    theme_cfg = get_theme(theme_input)
    candidate_json = Path(theme_input).expanduser()
    loaded_from_file = (
        candidate_json.is_file()
        and theme_cfg.get("_source_path") == str(candidate_json.resolve())
    )
    if theme_input != theme_cfg.get("id") and not loaded_from_file:
        print(f"[-] 警告: 未找到指定主题 '{theme_input}'，回退使用默认 '{theme_cfg.get('id')}' 主题。", file=sys.stderr)
        print(f"    提示: 使用 'md2wx --list-themes' 可查看所有已安装主题。\n", file=sys.stderr)

    # 2. 获取输入内容
    base_dir = Path.cwd()
    if args.input:
        input_path = Path(args.input).resolve()
        if not input_path.exists():
            print(f"[-] 错误: 文件不存在 -> {args.input}", file=sys.stderr)
            sys.exit(1)
        base_dir = input_path.parent
        with open(input_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
    else:
        if sys.stdin.isatty():
            parser.print_help()
            sys.exit(0)
        raw_content = sys.stdin.read()

    # 3. 解析 Frontmatter 与正文
    meta, body_md = parse_frontmatter(raw_content)

    # 3.1 Obsidian wiki 图片语法归一化 (![[x.png]] -> ![](x.png))：
    #     让后续 CDN 上传扫描、外链检测与渲染统一按标准图片语法处理
    body_md = expand_obsidian_images(body_md)

    # 3.5 发稿规范自检 (--lint 仅输出报告，存在阻断问题时以非零码退出)
    if args.lint:
        lint_issues = lint_markdown(raw_content)
        print(format_lint_report(lint_issues))
        sys.exit(1 if has_errors(lint_issues) else 0)

    # 3.6 富文本块预处理：Mermaid 图表与数学公式抽取为占位 token 并无头预渲染
    rich_blocks = []
    try:
        body_md, rich_blocks = extract_rich_blocks(body_md)
        if rich_blocks:
            print(f">>> 检测到 {len(rich_blocks)} 个 Mermaid 图表 / 数学公式，正在无头渲染...")
            resolve_rich_blocks(rich_blocks)
            rich_failed = sum(1 for b in rich_blocks if not b.get("rendered"))
            if rich_failed:
                print(
                    f"    [!] {rich_failed} 处富文本块未能截图渲染 (无头浏览器不可用)，已降级为文本形态，发布前请真机确认。",
                    file=sys.stderr,
                )
            else:
                print("    [+] 富文本块渲染完成。")
    except Exception as e:
        print(f"[-] 富文本块处理异常，相关位置将降级为文本形态: {e}", file=sys.stderr)
        rich_blocks = []

    # 确定元数据
    title = args.title or meta.get("title")
    if not title:
        # 从 H1 提取
        for line in body_md.split("\n"):
            if line.strip().startswith("# "):
                title = line.strip()[2:].strip()
                break
    title = title or "未命名文章"

    author = args.author or meta.get("author") or "野生宝藏箱"
    # 摘要优先级与 Web Studio extractCoverMeta 对齐: frontmatter digest > 正文首个引言块 > 正文纯文本摘要
    digest = meta.get("digest") or extract_quote_text(body_md, 120) or strip_markdown(body_md, 120)

    # 微信公众平台字段长度校验 (标题 64 字、摘要 120 字)，超长提前截断并警告
    if len(title) > WECHAT_TITLE_MAX_LEN:
        print(f"[-] 警告: 标题超过微信 {WECHAT_TITLE_MAX_LEN} 字上限，已自动截断。", file=sys.stderr)
        title = title[:WECHAT_TITLE_MAX_LEN]
    if digest and len(digest) > WECHAT_DIGEST_MAX_LEN:
        print(f"[-] 警告: 摘要超过微信 {WECHAT_DIGEST_MAX_LEN} 字上限，已自动截断。", file=sys.stderr)
        digest = digest[:WECHAT_DIGEST_MAX_LEN]

    # 4. 如果需要发布到公众号草稿箱，需要前置上传正文图片
    image_map = {}
    creds = load_env_credentials()
    app_id = args.app_id or creds["app_id"]
    app_secret = creds["app_secret"]

    # 4.0 外链图片检测与可选图床换链 (微信编辑器会封禁外站图床)
    external_images = collect_external_image_urls(body_md)
    if external_images and not args.publish:
        if args.rehost_images:
            host_cfg = get_image_host_config()
            if not host_cfg:
                print(f"[-] 错误: {IMAGE_HOST_HINT}", file=sys.stderr)
                sys.exit(1)
            print(f">>> 检测到 {len(external_images)} 处外链图片，正在转存图床...")
            for ext_url in external_images:
                try:
                    data, filename, mime = download_image_bytes(ext_url)
                    hosted_url = upload_image_bytes(data, filename, mime, host_cfg)
                    image_map[ext_url] = hosted_url
                    print(f"    -> 已换链: {hosted_url[:60]}...")
                except Exception as e:
                    print(f"    [-] 外链图片转存失败 ({ext_url}): {e}", file=sys.stderr)
        else:
            print(f"[!] 检测到 {len(external_images)} 处正文外链图片，微信编辑器可能封禁外站图床。", file=sys.stderr)
            print("    发布模式 (-p) 会自动转存微信官方 CDN；剪贴板模式可使用 --rehost-images 换链到图床。", file=sys.stderr)

    token = None
    if args.publish and args.dry_run:
        print(">>> [DRY RUN] 发布演练模式：跳过凭据获取、图片上传与草稿推送，仅完成渲染与 payload 预览。")
    if args.publish and not args.dry_run:
        # AppSecret 属敏感信息，仅从环境变量/.env 读取；缺失时交互式输入，避免进入 shell history
        if not app_secret and sys.stdin.isatty():
            import getpass
            app_secret = getpass.getpass("请输入 WECHAT_APP_SECRET (输入不回显): ")
        if not app_id or not app_secret:
            print("[-] 错误: 推送草稿箱需要配置 WECHAT_APP_ID 和 WECHAT_APP_SECRET！", file=sys.stderr)
            sys.exit(1)
        print(">>> 1. 获取微信 Access Token...")
        try:
            token = get_access_token(app_id, app_secret)
            print("    [+] Access Token 获取成功！(本地缓存命中则直接复用)")
        except Exception as e:
            print(f"[-] 获取 Token 失败: {e}", file=sys.stderr)
            sys.exit(1)

        # 扫描正文图片引用并上传至微信官方 CDN (支持 title 语法与 URL 编码路径，精确捕获 src)
        img_matches = list(re.finditer(r'!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)', body_md))
        if img_matches:
            print(f">>> 2. 检测到 {len(img_matches)} 处图片引用，正在上传至微信官方 CDN...")
            upload_failed = []
            for m in img_matches:
                img_src = unquote(m.group(2))

                # 已是微信 CDN 图，无需处理
                if "mmbiz.qpic.cn" in img_src:
                    continue
                if img_src in image_map:
                    continue

                # A. 外链 http(s) 图片：下载字节后转存微信 CDN，规避微信外链防盗链
                if img_src.startswith(("http://", "https://")):
                    try:
                        print(f"    正在下载外链图片并转存微信: {img_src} ...")
                        data, filename, mime = download_image_bytes(img_src)
                        cdn_url = upload_image_bytes_to_wechat_cdn(token, data, filename, mime)
                        image_map[img_src] = cdn_url
                        print(f"    -> 成功换链: {cdn_url[:60]}...")
                    except Exception as e:
                        upload_failed.append(img_src)
                        print(f"    [-] 外链图片转存失败 ({img_src}): {e}", file=sys.stderr)
                    continue

                # B. Base64 内嵌图片 (data:image/...;base64,...)：解码后转存微信 CDN
                if img_src.startswith("data:image/") and ";base64," in img_src:
                    try:
                        import base64
                        header, b64 = img_src.split(";base64,", 1)
                        mime = header.replace("data:", "") or "image/png"
                        data = base64.b64decode(b64)
                        ext = mime.split("/")[-1].split("+")[0] or "png"
                        filename = f"pasted.{ext}"
                        print(f"    正在转存内嵌 Base64 图片 ...")
                        cdn_url = upload_image_bytes_to_wechat_cdn(token, data, filename, mime)
                        image_map[img_src] = cdn_url
                        print(f"    -> 成功换链: {cdn_url[:60]}...")
                    except Exception as e:
                        upload_failed.append(img_src)
                        print(f"    [-] Base64 图片转存失败: {e}", file=sys.stderr)
                    continue

                # C. 本地相对路径图片
                local_img_path = (base_dir / img_src).resolve()
                if not local_img_path.exists():
                    upload_failed.append(img_src)
                    print(f"    [-] 本地图片不存在，发布后将保持原样: {img_src}", file=sys.stderr)
                    continue
                try:
                    print(f"    正在上传图片: {img_src} ...")
                    cdn_url = upload_image_to_wechat_cdn(token, str(local_img_path))
                    image_map[img_src] = cdn_url
                    print(f"    -> 成功换链: {cdn_url[:60]}...")
                except Exception as e:
                    upload_failed.append(img_src)
                    print(f"    [-] 图片上传失败 ({img_src}): {e}", file=sys.stderr)
            if upload_failed:
                print(f"    [!] 共 {len(upload_failed)} 处图片未能换链，对应位置在草稿中将无法显示。", file=sys.stderr)

    # 5. 执行 Markdown -> 微信专用 HTML 转换 (提取封面元数据并按需在正文顶部注入封面卡片)
    cover_meta = {
        "title": title,
        "digest": digest,
        "author": author,
        "badge": COVER_BADGE_PRESETS.get(theme_input, "TECH BLOG"),
        "vol": f"2026 · V{__version__}"
    }
    html_output = markdown_to_wechat_html(
        body_md,
        theme_name=theme_input,
        image_map=image_map,
        insert_cover=not args.no_cover,
        cover_meta=cover_meta,
        rich_blocks=rich_blocks
    )

    # 5.5 行内公式 token 后置替换 (块级 token 已在解析主循环直接落块)
    if rich_blocks:
        html_output = substitute_rich_html(html_output, rich_blocks)

    # 6. 输出处理
    # 选项 A: 写入输出文件
    if args.output:
        out_path = Path(args.output).resolve()
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_output)
        print(f"[+] 微信 HTML 已保存至: {out_path}")

    # 选项 B: 复制到系统剪贴板
    if args.clip:
        copied = copy_html_to_clipboard(html_output)
        if copied:
            print("[+] 已将微信带样式富文本成功复制到剪贴板！可以直接在微信公众平台编辑器中按 Cmd+V 粘贴。")
        else:
            print("[-] 剪贴板注入富文本未生效，请通过 -o 参数保存为 HTML 文件在浏览器中打开复制。", file=sys.stderr)

    # 选项 C: 默认如果没有指定输出文件和剪贴板，且未发布，则打印到 stdout
    if not args.output and not args.clip and not args.publish:
        sys.stdout.write(html_output)

    # 选项 D: 一键发布到微信公众号草稿箱
    if args.publish:
        print(">>> 3. 准备提交草稿至微信公众号...")

        # 发布前规范自检 (仅提示，不阻断发布)
        pre_issues = lint_markdown(raw_content)
        if pre_issues:
            print("    [lint] 发布前规范自检发现以下问题 (不阻断):")
            for line in format_lint_report(pre_issues).split("\n"):
                print(f"      {line}")

        # 富文本渲染产物 (base64 内联图) 统一转存微信官方 CDN，草稿箱正文不支持 data URI
        if rich_blocks and not args.dry_run:
            html_output, rich_ok, rich_fail = rehost_data_uri_images(token, html_output)
            if rich_ok or rich_fail:
                print(f"    富文本图片已转存微信 CDN: 成功 {rich_ok} 处 / 失败 {rich_fail} 处")
                if rich_fail:
                    print("    [!] 部分富文本图片转存失败，对应位置在草稿中将无法显示。", file=sys.stderr)

        # 确定封面图与裁剪坐标，优先级: 用户指定双封面 > frontmatter双封面 > 命令行--cover > frontmatter cover > 动态双比例封面 > 动态单版封面 > 主题静态封面 > 首图
        cover_path = None
        pic_crop_235_1 = None
        pic_crop_1_1 = None

        if args.cover and args.cover_square:
            print(f"    检测到用户自定义双封面: 头条({args.cover}) + 次条/方图({args.cover_square})")
            stitched = stitch_cover_images(args.cover, args.cover_square)
            if stitched:
                cover_path = stitched
                pic_crop_235_1 = WECHAT_CROP_235_1
                pic_crop_1_1 = WECHAT_CROP_1_1
                print("    已完成双封面拼图合成 (3350x1000)")
            else:
                cover_path = str(Path(args.cover).resolve())
        elif args.cover:
            cover_path = str(Path(args.cover).resolve())
        elif meta.get("cover") and meta.get("cover_square"):
            b_file = str((base_dir / meta["cover"]).resolve())
            s_file = str((base_dir / meta["cover_square"]).resolve())
            stitched = stitch_cover_images(b_file, s_file)
            if stitched:
                cover_path = stitched
                pic_crop_235_1 = WECHAT_CROP_235_1
                pic_crop_1_1 = WECHAT_CROP_1_1
                print("    已自文章 Frontmatter 完成双封面拼图合成 (3350x1000)")
            else:
                cover_path = b_file
        elif meta.get("cover"):
            cover_path = str((base_dir / meta["cover"]).resolve())
        else:
            theme_id = theme_cfg.get("id")
            if not args.no_dual_cover:
                # 默认优先动态渲染文章专属主题双封面 (3350x1000，左侧 2350x1000 头条 + 右侧 1000x1000 方图)
                dual_res = render_article_dual_cover_png(
                    theme_id, title=title, digest=digest, author=author, tags=meta.get("tags")
                )
                if dual_res:
                    cover_path, pic_crop_235_1, pic_crop_1_1 = dual_res
                    print(f"    已动态生成 '{theme_cfg.get('name')}' 主题专属双比例拼接封面 (3350x1000):")
                    print(f"      - 2.35:1 头条裁剪坐标: {pic_crop_235_1}")
                    print(f"      - 1:1 次条/方图裁剪坐标: {pic_crop_1_1}")

            if not cover_path:
                cover_path = render_article_cover_png(
                    theme_id, title=title, digest=digest, author=author, tags=meta.get("tags")
                )
                if cover_path:
                    print(f"    已动态生成 '{theme_cfg.get('name')}' 主题专属单版封面 (2350x1000)。")
                else:
                    # 无头浏览器不可用时降级为内置静态主题封面
                    theme_cover = get_builtin_theme_cover(theme_id)
                    if theme_cover:
                        cover_path = str(theme_cover)
                        print(f"    未检测到无头浏览器，使用 '{theme_cfg.get('name')}' 主题静态默认封面。")
            if not cover_path and image_map:
                # 取第一张本地图片作为默认封面候选
                first_local = list(image_map.keys())[0]
                cover_path = str((base_dir / first_local).resolve())

        if not cover_path or not Path(cover_path).exists():
            print("[-] 错误: 微信图文消息必须设置封面图！请使用 --cover 参数指定封面图片路径。", file=sys.stderr)
            sys.exit(1)

        print(f"    使用封面图片: {cover_path}")
        source_url = meta.get("content_source_url") or meta.get("source_url") or "https://md2wx.zaneven.com"

        # 发布演练：完整走完渲染与封面解析，仅打印将上报的 payload 摘要，不发起任何微信请求
        if args.dry_run:
            article_preview = {
                "title": title,
                "author": author,
                "digest": digest,
                "content_source_url": source_url,
                "thumb_media_id": f"<待上传: {cover_path}>",
                "need_open_comment": 1,
                "only_fans_can_comment": 0,
            }
            if pic_crop_235_1:
                article_preview["pic_crop_235_1"] = pic_crop_235_1
            if pic_crop_1_1:
                article_preview["pic_crop_1_1"] = pic_crop_1_1
            print(">>> [DRY RUN] 将上报微信 draft/add 的 payload 摘要:")
            print(json.dumps({"articles": [article_preview]}, ensure_ascii=False, indent=2))
            print(f"    content: 微信内联 HTML 共 {len(html_output)} 字符 (可用 -o/--clip 配合查验全文)")
            print("[DRY RUN] 已停止：未上传素材、未推送草稿。去除 --dry-run 参数后将执行真实发布。")
            return

        try:
            res = publish_draft_to_wechat(
                token=token,
                title=title,
                content_html=html_output,
                author=author,
                digest=digest,
                cover_image_path=cover_path,
                pic_crop_235_1=pic_crop_235_1,
                pic_crop_1_1=pic_crop_1_1,
                content_source_url=source_url,
                token_refresher=lambda: get_access_token(app_id, app_secret, force_refresh=True),
            )
            print("[+] 恭喜！文章已成功推送到微信公众号草稿箱！")
            print(f"    草稿标题: {res['title']}")
            print(f"    草稿 ID:   {res['media_id']}")
            if res.get("pic_crop_235_1"):
                print(f"    双图裁剪坐标已同步生效 (头条: {res['pic_crop_235_1']}, 方图: {res['pic_crop_1_1']})")
            if res.get("preview_url"):
                print(f"    临时预览: {res['preview_url']}")
        except Exception as e:
            print(f"[-] 提交草稿箱失败: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()

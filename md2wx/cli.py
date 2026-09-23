"""
MD2WX 命令行工具 (CLI Entrypoint)
支持多主题风格化渲染、自定义主题文件加载与一键发布
"""
import os
import re
import sys
import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import Dict
from urllib.parse import unquote

from . import __version__
from .parser import markdown_to_wechat_html, parse_frontmatter, strip_markdown, extract_quote_text
from .themes import list_themes, get_theme, get_builtin_themes_dir, get_user_themes_dir, get_builtin_theme_cover
from .cover import render_article_cover_png
from .envutil import load_env, is_placeholder
from .imagehost import (
    get_image_host_config,
    upload_image_file as upload_image_to_host,
    download_image_bytes,
    CONFIG_HINT as IMAGE_HOST_HINT,
)
from .uploader import get_access_token, upload_image_to_wechat_cdn, upload_image_bytes_to_wechat_cdn
from .publisher import publish_draft_to_wechat

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
    parser.add_argument("--cover", help="指定封面图片路径 (默认优先级: 此参数 > frontmatter cover: > 动态渲染主题封面 > 正文首图)")
    parser.add_argument("--author", help="指定文章作者 (默认读取 Frontmatter 或 '野生宝藏箱')")
    parser.add_argument("--title", help="指定文章标题 (默认读取 Frontmatter 或首个 H1)")
    parser.add_argument("--app-id", help="微信 AppID (默认从环境变量或 .env 读取)")
    parser.add_argument("--no-cover", action="store_true", help="不在正文顶部注入封面卡片")
    parser.add_argument("--upload-image", metavar="PATH", help="将本地图片上传到 .env 配置的在线图床并输出图片链接 (需配置 IMAGE_HOST_UPLOAD_URL)")

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

    token = None
    if args.publish:
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
            print("    [+] Access Token 获取成功！")
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
        cover_meta=cover_meta
    )

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
        # 确定封面图，优先级: --cover 参数 > frontmatter cover: > 主题默认封面 > 正文首图
        cover_path = None
        if args.cover:
            cover_path = str(Path(args.cover).resolve())
        elif meta.get("cover"):
            cover_path = str((base_dir / meta["cover"]).resolve())
        else:
            theme_id = theme_cfg.get("id")
            # 优先动态渲染文章专属主题封面 (与 Web Studio Cover Studio 同款视觉，
            # 标题/摘要/作者/标签自动排版进主题设计稿，输出 2350x1000 头条尺寸)
            cover_path = render_article_cover_png(
                theme_id, title=title, digest=digest, author=author, tags=meta.get("tags")
            )
            if cover_path:
                print(f"    已动态生成 '{theme_cfg.get('name')}' 主题专属封面 (文章标题/摘要自动渲染)。")
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
        try:
            source_url = meta.get("content_source_url") or meta.get("source_url") or "https://md2wx.zaneven.com"
            res = publish_draft_to_wechat(
                token=token,
                title=title,
                content_html=html_output,
                author=author,
                digest=digest,
                cover_image_path=cover_path,
                content_source_url=source_url
            )
            print("[+] 恭喜！文章已成功推送到微信公众号草稿箱！")
            print(f"    草稿标题: {res['title']}")
            print(f"    草稿 ID:   {res['media_id']}")
            if res.get("preview_url"):
                print(f"    临时预览: {res['preview_url']}")
        except Exception as e:
            print(f"[-] 提交草稿箱失败: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()

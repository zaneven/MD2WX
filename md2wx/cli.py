"""
MD2WX 命令行工具 (CLI Entrypoint)
支持多主题风格化渲染、自定义主题文件加载与一键发布
"""
import os
import sys
import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict

from .parser import markdown_to_wechat_html, parse_frontmatter, strip_markdown
from .themes import list_themes, get_theme, load_theme_file, get_builtin_themes_dir, get_user_themes_dir
from .uploader import get_access_token, upload_image_to_wechat_cdn
from .publisher import publish_draft_to_wechat

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
    """从环境变量或已知路径加载微信凭证"""
    creds = {
        "app_id": os.environ.get("WECHAT_APP_ID", ""),
        "app_secret": os.environ.get("WECHAT_APP_SECRET", "")
    }
    # 尝试读取常见 .env 路径
    candidate_envs = [
        Path.cwd() / ".env",
        Path.home() / "Develop" / "wx-serv" / ".env",
        Path.home() / "Develop" / "MD2WX" / ".env",
    ]
    for env_file in candidate_envs:
        if creds["app_id"] and creds["app_secret"]:
            break
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("WECHAT_APP_ID=") and not creds["app_id"]:
                        creds["app_id"] = line.split("=", 1)[1].strip().strip("'\"")
                    elif line.startswith("WECHAT_APP_SECRET=") and not creds["app_secret"]:
                        creds["app_secret"] = line.split("=", 1)[1].strip().strip("'\"")
    return creds

def copy_html_to_clipboard(html: str) -> bool:
    """在 macOS 环境下将 HTML 作为富文本写入剪贴板 (可以直接 Cmd+V 粘贴到微信后台)"""
    if sys.platform != "darwin":
        return False
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(html)
            tmp_path = f.name
        cmd = f'osascript -e \'set the clipboard to (read (POSIX file "{tmp_path}") as «class HTML»)\''
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return res.returncode == 0
    except Exception:
        return False

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
    parser.add_argument("--cover", help="指定封面图片路径 (发布草稿时必填，或自动提取正文首图)")
    parser.add_argument("--author", help="指定文章作者 (默认读取 Frontmatter 或 '野生宝藏箱')")
    parser.add_argument("--title", help="指定文章标题 (默认读取 Frontmatter 或首个 H1)")
    parser.add_argument("--app-id", help="微信 AppID (默认从环境变量或 .env 读取)")
    parser.add_argument("--app-secret", help="微信 AppSecret (默认从环境变量或 .env 读取)")

    args = parser.parse_args()

    # 处理 --web 选项
    if args.web:
        import webbrowser
        web_dir = Path(__file__).resolve().parent.parent / "web"
        dist_dir = web_dir / "dist"
        print("================================================================================")
        print("  MD2WX Web Studio (可视化排版工作台)")
        print("================================================================================")
        print(f"前端工作目录: {web_dir}")
        print("正在启动本地 Web 预览服务 (http://localhost:3000) ...")
        try:
            webbrowser.open("http://localhost:3000")
            cmd = ["npm", "run", "dev"]
            subprocess.run(cmd, cwd=str(web_dir))
        except KeyboardInterrupt:
            print("\n[+] 服务已停止。")
        except Exception as e:
            print(f"[-] 启动 Web 服务失败: {e}", file=sys.stderr)
        sys.exit(0)

    # 处理 --list-themes 选项
    if args.list_themes:
        print_themes_list()
        sys.exit(0)

    # 1. 校验并获取主题配置
    theme_input = args.theme
    candidate_json = Path(theme_input).expanduser()
    registered_themes = list_themes()
    if not candidate_json.is_file() and theme_input not in registered_themes:
        print(f"[-] 警告: 未找到指定主题 '{theme_input}'，回退使用默认 'tech-blue' 主题。", file=sys.stderr)
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
    digest = meta.get("digest") or strip_markdown(body_md, 120)

    # 4. 如果需要发布到公众号草稿箱，需要前置上传正文图片
    image_map = {}
    creds = load_env_credentials()
    app_id = args.app_id or creds["app_id"]
    app_secret = args.app_secret or creds["app_secret"]

    token = None
    if args.publish:
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

        # 扫描本地图片并上传
        import re
        img_matches = list(re.finditer(r'!\[(.*?)\]\((.*?)\)', body_md))
        if img_matches:
            print(f">>> 2. 检测到 {len(img_matches)} 处图片引用，正在上传至微信官方 CDN...")
            for m in img_matches:
                alt = m.group(1)
                img_src = m.group(2)
                if img_src.startswith("http://") or img_src.startswith("https://"):
                    # 外部网络图如果包含微信 CDN 则跳过
                    if "mmbiz.qpic.cn" in img_src:
                        continue
                # 本地相对路径查找
                local_img_path = (base_dir / img_src).resolve()
                if local_img_path.exists() and img_src not in image_map:
                    try:
                        print(f"    正在上传图片: {img_src} ...")
                        cdn_url = upload_image_to_wechat_cdn(token, str(local_img_path))
                        image_map[img_src] = cdn_url
                        print(f"    -> 成功换链: {cdn_url[:60]}...")
                    except Exception as e:
                        print(f"    [-] 图片上传失败 ({img_src}): {e}", file=sys.stderr)

    # 5. 执行 Markdown -> 微信专用 HTML 转换
    html_output = markdown_to_wechat_html(body_md, theme_name=theme_input, image_map=image_map)

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
        # 确定封面图
        cover_path = None
        if args.cover:
            cover_path = str(Path(args.cover).resolve())
        elif meta.get("cover"):
            cover_path = str((base_dir / meta["cover"]).resolve())
        elif image_map:
            # 取第一张本地图片作为默认封面候选
            first_local = list(image_map.keys())[0]
            cover_path = str((base_dir / first_local).resolve())

        if not cover_path or not Path(cover_path).exists():
            print("[-] 错误: 微信图文消息必须设置封面图！请使用 --cover 参数指定封面图片路径。", file=sys.stderr)
            sys.exit(1)

        print(f"    使用封面图片: {cover_path}")
        try:
            res = publish_draft_to_wechat(
                token=token,
                title=title,
                content_html=html_output,
                author=author,
                digest=digest,
                cover_image_path=cover_path
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

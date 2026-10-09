"""
MD2WX 富文本块渲染引擎 (Mermaid 图表 / 数学公式 -> 微信兼容内联图片)

微信公众号不支持 SVG 与外部脚本，Mermaid 与 KaTeX 的产物无法直接存活。
本模块复用 cover.py 的无头浏览器基建，采用两段式渲染：
  第一遍  --dump-dom  加载 CDN 上的 mermaid.js / katex 渲染内容并回写测量尺寸
  第二遍  --screenshot 按精确尺寸 2x 高清采样截图，输出内联 data URI PNG
零第三方依赖：渲染库从 CDN 动态加载；无网络或无浏览器时安全降级为
代码块 / 行内样式文本，绝不阻断主排版流程。
"""
import os
import re
import json
import time
import base64
import shutil
import hashlib
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .cover import find_headless_browser

# 渲染库 CDN 地址 (锁定版本，保证渲染结果稳定)
MERMAID_JS_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"
KATEX_JS_CDN = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"
KATEX_CSS_CDN = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css"

RICH_CACHE_DIR = Path.home() / ".config" / "md2wx" / "rich"

_RICH_TOKEN_RE = re.compile(r"@@MD(?:MERMAID|MATH)_\d+@@")
# 数学公式预处理 (pandoc 规则变体)：$ 后非空白开头、$ 前非空白结尾、闭合 $ 后不能紧跟数字
# (避免 "$100 and $200" 这类价格文本被误判为行内公式)
_MATH_BLOCK_ONELINE_RE = re.compile(r"\$\$(?!\s)(.+?)(?<!\s)\$\$", re.DOTALL)
_MATH_BLOCK_OPEN_RE = re.compile(r"^\$\$\s*$")
_MATH_BLOCK_CLOSE_RE = re.compile(r"^\$\$\s*$")
_MATH_INLINE_RE = re.compile(r"\$(?!\s)((?:[^$\n\\]|\\.)+?)(?<!\s)\$(?!\d)")


def extract_rich_blocks(md_text: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    预处理 Markdown，将 Mermaid 围栏与数学公式抽取为占位 token：
      ```mermaid 围栏   -> @@MDMERMAID_n@@ (整段替换为独立占位行)
      $$...$$ 公式块     -> @@MDMERMAID... 见下 @@MDMATH_n@@ (display 模式)
      $...$ 行内公式     -> @@MDMATH_n@@ (inline 模式)
    返回 (替换后的 Markdown, 富文本块列表)；每个块含 token/kind/content 字段。
    非 mermaid 代码围栏内容原样保留，绝不误伤其中的 $ 与示例代码。
    """
    lines = md_text.split("\n")
    out_lines: List[str] = []
    blocks: List[Dict[str, str]] = []

    in_fence = False
    fence_marker = ""
    math_block_open = False
    math_block_lines: List[str] = []

    def _next_token(kind: str, content: str, display: bool = False) -> str:
        blocks.append({
            "token": f"@@MD{kind}_{len(blocks)}@@",
            "kind": kind.lower(),
            "content": content,
            "display": display,
        })
        return blocks[-1]["token"]

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        # 围栏状态机 (mermaid 围栏整段抽取，其余围栏透传保护)
        if not in_fence and stripped.startswith("```"):
            lang = stripped[3:].strip().lower()
            if lang == "mermaid":
                code_lines: List[str] = []
                idx += 1
                while idx < len(lines) and not lines[idx].strip().startswith("```"):
                    code_lines.append(lines[idx])
                    idx += 1
                idx += 1  # 跳过闭合围栏
                out_lines.append(_next_token("MERMAID", "\n".join(code_lines).strip(), display=True))
                continue
            in_fence = True
            fence_marker = stripped[:3]
            out_lines.append(line)
            idx += 1
            continue
        if in_fence:
            out_lines.append(line)
            if stripped.startswith(fence_marker):
                in_fence = False
            idx += 1
            continue

        # 多行 $$ 公式块
        if not math_block_open and _MATH_BLOCK_OPEN_RE.match(stripped):
            math_block_open = True
            math_block_lines = []
            idx += 1
            continue
        if math_block_open:
            if _MATH_BLOCK_CLOSE_RE.match(stripped):
                out_lines.append(_next_token("MATH", "\n".join(math_block_lines).strip(), display=True))
                math_block_open = False
            else:
                math_block_lines.append(line)
            idx += 1
            continue

        # 单行 $$...$$ 公式块
        oneline_math = _MATH_BLOCK_ONELINE_RE.search(stripped)
        if oneline_math and stripped.strip("$ ").replace(" ", "") == oneline_math.group(1).replace(" ", ""):
            out_lines.append(_next_token("MATH", oneline_math.group(1).strip(), display=True))
            idx += 1
            continue

        # 行内 $...$ 公式
        if "$" in line:
            def _inline_math_sub(m: "re.Match") -> str:
                return _next_token("MATH", m.group(1))

            line = _MATH_INLINE_RE.sub(_inline_math_sub, line)

        out_lines.append(line)
        idx += 1

    # 未闭合的公式块按原样还原，避免吞掉正文
    if math_block_open:
        out_lines.insert(len(out_lines), "$$")
        out_lines.extend(math_block_lines)

    return "\n".join(out_lines), blocks


def _build_rich_page_html(kind: str, content: str) -> str:
    """
    构建自包含渲染页 HTML：加载 CDN 渲染库，渲染完成后把内容尺寸回写到
    #md2wx-size 节点 (第一遍 --dump-dom 读取尺寸，第二遍按尺寸截图)
    """
    if kind == "mermaid":
        head = f'<script src="{MERMAID_JS_CDN}"></script>'
        render_js = f"""
    mermaid.initialize({{ startOnLoad: false, theme: 'neutral', flowchart: {{ useMaxWidth: false }}, sequence: {{ useMaxWidth: false }}, gantt: {{ useMaxWidth: false }} }});
    const {{ svg }} = await mermaid.render('md2wx-svg', {json.dumps(content)});
    stage.innerHTML = svg;
    const el = stage.firstElementChild;
    const r = el.getBoundingClientRect();
    el.setAttribute('width', Math.ceil(r.width));
    el.setAttribute('height', Math.ceil(r.height));
    el.style.maxWidth = 'none';
    done(Math.ceil(r.width), Math.ceil(r.height));"""
    else:
        head = f'<link rel="stylesheet" href="{KATEX_CSS_CDN}"><script src="{KATEX_JS_CDN}"></script>'
        render_js = f"""
    const inner = document.createElement('span');
    inner.style.display = 'inline-block';
    stage.appendChild(inner);
    katex.render({json.dumps(content)}, inner, {{ displayMode: true, throwOnError: false }});
    const r = inner.getBoundingClientRect();
    stage.style.width = Math.ceil(r.width) + 'px';
    stage.style.height = Math.ceil(r.height) + 'px';
    done(Math.ceil(r.width), Math.ceil(r.height));"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{head}
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ background: #ffffff; }}
#stage {{ background: #ffffff; padding: 0; font-size: 16px; }}
.katex-display {{ margin: 0; }}
#md2wx-size {{ visibility: hidden; }}
</style>
</head>
<body>
<div id="stage"></div>
<div id="md2wx-size">PENDING</div>
<script>
(async () => {{
  const stage = document.getElementById('stage');
  const done = (w, h) => {{ document.getElementById('md2wx-size').textContent = w + 'x' + h; }};
  try {{{render_js}
  }} catch (e) {{
    document.getElementById('md2wx-size').textContent = 'ERR:' + (e && e.message ? e.message : e);
  }}
}})();
</script>
</body>
</html>"""


def _run_browser(args: List[str], timeout: int = 60) -> Optional[str]:
    """
    执行无头浏览器命令并捕获 stdout (写入临时文件后读取)。
    注意一：不能用管道 capture —— Chrome 的 helper 子进程会继承管道 fd，
    导致 communicate() 永远等不到 EOF (cover.py 的 DEVNULL+轮询同理规避)。
    注意二：不能加 --user-data-dir —— 部分平台 Chrome 上 dump-dom 与
    独立 profile 组合会永久挂起 (实测 macOS)；无 profile 时即使 Chrome
    正在运行也能正常无头渲染。超时或失败返回 None
    """
    browser = find_headless_browser()
    if not browser:
        return None
    out_file = tempfile.NamedTemporaryFile("w+", suffix=".dom", delete=False)
    out_file.close()
    try:
        cmd = [
            browser,
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            *args,
        ]
        with open(out_file.name, "wb") as stdout_fh:
            proc = subprocess.Popen(cmd, stdout=stdout_fh, stderr=subprocess.DEVNULL)
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass
                return None
        with open(out_file.name, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return None
    finally:
        try:
            os.remove(out_file.name)
        except OSError:
            pass


def _measure_rich_content(kind: str, content: str) -> Optional[Tuple[int, int, str]]:
    """
    第一遍渲染：dump-dom 读取渲染完成后的内容尺寸
    返回 (width, height, html_path)；html_path 交由调用方在第二遍截图后清理。
    渲染失败或库加载失败返回 None (此时页面文件已自行清理)
    """
    html_path = ""
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(_build_rich_page_html(kind, content))
            html_path = f.name
        dom = _run_browser(["--virtual-time-budget=10000", "--dump-dom", f"file://{html_path}"])
    except Exception:
        if html_path:
            try:
                os.remove(html_path)
            except OSError:
                pass
        return None

    if not dom:
        try:
            os.remove(html_path)
        except OSError:
            pass
        return None
    m = re.search(r'id="md2wx-size"[^>]*>([^<]*)<', dom)
    if not m:
        try:
            os.remove(html_path)
        except OSError:
            pass
        return None
    value = m.group(1).strip()
    if value.startswith("ERR") or "x" not in value:
        try:
            os.remove(html_path)
        except OSError:
            pass
        return None
    try:
        w, h = (int(p) for p in value.split("x", 1))
    except ValueError:
        try:
            os.remove(html_path)
        except OSError:
            pass
        return None
    if w <= 0 or h <= 0 or w > 6000 or h > 6000:
        try:
            os.remove(html_path)
        except OSError:
            pass
        return None
    return w, h, html_path


def _render_rich_png(kind: str, content: str, measured: Optional[Tuple[int, int, str]] = None) -> Optional[bytes]:
    """
    第二遍精确截图：按测量尺寸 2x 高清采样输出 PNG
    measured 缺省时内部自行测量；任一环节失败 (无浏览器 / 无网络 / 语法错误) 返回 None
    """
    if measured is None:
        measured = _measure_rich_content(kind, content)
    if not measured:
        return None
    w, h, html_path = measured

    # 复用第一遍的页面文件做第二遍截图，尺寸加上 6px 余量防止边缘裁切 (inline-block 基线下溢)
    out_path = Path(tempfile.mktemp(prefix="md2wx-rich-", suffix=".png"))
    try:
        browser = find_headless_browser()
        if not browser:
            return None
        cmd = [
            browser,
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            "--virtual-time-budget=10000",
            f"--window-size={w + 6},{h + 6}",
            "--force-device-scale-factor=2",
            f"--screenshot={out_path}",
            f"file://{html_path}",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 40
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            if out_path.exists() and out_path.stat().st_size > 0:
                break
            time.sleep(0.2)
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        if not out_path.exists() or out_path.stat().st_size <= 0:
            return None
        return out_path.read_bytes()
    except Exception:
        return None
    finally:
        try:
            os.remove(html_path)
        except OSError:
            pass
        try:
            out_path.unlink(missing_ok=True)
        except OSError:
            pass


def _render_cached_pair(kind: str, content: str) -> Tuple[Optional[bytes], int]:
    """
    按内容指纹缓存渲染结果 (PNG + 逻辑宽度元数据)，重复渲染同一图表/公式零开销
    返回 (PNG 字节或 None, 逻辑宽度)
    """
    fingerprint = hashlib.md5(f"{kind}:{content}".encode("utf-8")).hexdigest()[:16]
    cache_png = RICH_CACHE_DIR / f"rich-{kind}-{fingerprint}.png"
    cache_meta = RICH_CACHE_DIR / f"rich-{kind}-{fingerprint}.json"
    if cache_png.exists() and cache_png.stat().st_size > 0:
        try:
            width = 0
            if cache_meta.exists():
                width = int(json.loads(cache_meta.read_text(encoding="utf-8")).get("width", 0))
            return cache_png.read_bytes(), width
        except Exception:
            pass

    measured = _measure_rich_content(kind, content)
    width = 0
    png = None
    if measured:
        width = measured[0] + 6
        png = _render_rich_png(kind, content, measured)

    if png:
        try:
            RICH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_png.write_bytes(png)
            cache_meta.write_text(json.dumps({"width": width}), encoding="utf-8")
        except OSError:
            pass
    return png, width


def _fallback_html(block: Dict[str, str]) -> str:
    """无浏览器 / 无网络时的安全降级：Mermaid 回退代码块，公式回退行内样式文本"""
    from .parser import render_code

    if block["kind"] == "mermaid":
        return render_code(block["content"], "mermaid", {"code_bg": "#18181b", "code_text": "#e4e4e7", "accent": "#2563eb", "border_color": "#e4e4e7", "sub_color": "#71717a", "code_style": "mac_dark"})
    escaped = (
        block["content"]
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return (
        f'<code style="background: rgba(0,0,0,0.06); padding: 2px 6px; border-radius: 4px; '
        f'font-size: 13.5px; color: #2563eb; font-family: monospace;">{escaped}</code>'
    )


def resolve_rich_blocks(blocks: List[Dict[str, str]]) -> None:
    """
    就地解析所有富文本块，为每个块生成 block['html']：
    优先无头浏览器渲染为内联 data URI 图片 (记录逻辑宽度用于精确回显)，
    失败时降级为文本形态
    """
    for block in blocks:
        block["width"] = 0
        png = None
        try:
            png, block["width"] = _render_cached_pair(block["kind"], block["content"])
        except Exception:
            png = None
        if png:
            b64 = base64.b64encode(png).decode("ascii")
            block["data_uri"] = f"data:image/png;base64,{b64}"
        block["html"] = _build_block_html(block)


def _build_block_html(block: Dict[str, str]) -> str:
    data_uri = block.get("data_uri")
    if not data_uri:
        return _fallback_html(block)

    # 2x 高清采样图按逻辑像素宽度回显，保证与正文字号协调且在移动端清晰
    width_style = f"width: {block.get('width') or 0}px;" if block.get("width") else ""
    if not block.get("display", False):
        # 行内公式：随文字基线排布
        return (
            f'<img src="{data_uri}" alt="formula" '
            f'style="max-width: 100%; height: auto; vertical-align: middle; display: inline-block; {width_style}" />'
        )
    if block["kind"] == "mermaid":
        return (
            f'<div style="margin: 22px 0; text-align: center;">'
            f'<img src="{data_uri}" alt="mermaid diagram" '
            f'style="max-width: 100%; height: auto; display: inline-block; {width_style}" /></div>'
        )
    # 块级公式：独立居中展示
    return (
        f'<div style="margin: 18px 0; text-align: center;">'
        f'<img src="{data_uri}" alt="formula" '
        f'style="max-width: 100%; height: auto; display: inline-block; {width_style}" /></div>'
    )


def substitute_rich_html(html: str, blocks: List[Dict[str, str]]) -> str:
    """把 HTML 中的富文本占位 token 替换为渲染产物 (图片或降级文本)"""
    for block in blocks:
        html = html.replace(block["token"], block.get("html", ""))
    return html


# data URI 内联图片 (富文本渲染产物)，发布前统一转存微信 CDN
_DATA_URI_IMG_RE = re.compile(
    r'<img src="data:image/(png|jpeg|jpg|gif|webp);base64,([A-Za-z0-9+/=\s]+)"'
)


def rehost_data_uri_images(token: str, html: str) -> Tuple[str, int, int]:
    """
    扫描 HTML 中的 base64 内联图片并上传微信 CDN 换链 (草稿箱正文不支持 data URI)
    返回 (换链后的 HTML, 成功数, 失败数)
    """
    from .uploader import upload_image_bytes_to_wechat_cdn

    success = failed = 0

    def _swap(m: "re.Match") -> str:
        nonlocal success, failed
        mime = m.group(1)
        if mime == "jpg":
            mime = "jpeg"
        try:
            data = base64.b64decode(m.group(2))
            cdn_url = upload_image_bytes_to_wechat_cdn(token, data, f"rich.{mime}", f"image/{mime}")
            success += 1
            return f'<img src="{cdn_url}"'
        except Exception:
            failed += 1
            return m.group(0)

    return _DATA_URI_IMG_RE.sub(_swap, html), success, failed

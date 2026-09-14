"""
MD2WX Markdown -> 微信公众号专用内联 HTML 转换引擎
支持多主题视觉组件化渲染策略 (对标 WePost 卡片级排版质感)
"""
import re
from typing import Dict, Tuple, Optional, List, Any
from .themes import get_theme

def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """解析并剥离 Markdown 顶部的 YAML Frontmatter"""
    meta: Dict[str, Any] = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1].strip()
            body = parts[2].strip()
            for line in fm_text.split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if v.startswith("[") and v.endswith("]"):
                        tags = [t.strip().strip("'\"") for t in v[1:-1].split(",") if t.strip()]
                        meta[k] = tags
                    else:
                        meta[k] = v
    return meta, body

def strip_markdown(md_text: str, max_len: int = 120) -> str:
    """剥离 Markdown 符号生成纯文本摘要 (Digest)"""
    text = re.sub(r'!\[.*?\]\(.*?\)', '', md_text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'[`#*_\->|]', '', text)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    plain = " ".join(lines)
    return plain[:max_len].strip()

def format_inline(text: str, accent: str, code_font_size: str = "13.5px") -> str:
    """
    统一解析行内 Markdown 语法：
    1. 保护并严格对行内代码进行 HTML 实体转义 (& -> &amp;, < -> &lt;, > -> &gt;)，彻底杜绝 <style> 等标签被微信拦截截断；
    2. 保护超链接；
    3. 解析加粗 **...** 和斜体 *...*；
    4. 还原保护的 tokens。
    """
    tokens: Dict[str, str] = {}
    token_idx = 0

    # 1. 保护并转义行内代码 `...`
    def save_code(m: re.Match) -> str:
        nonlocal token_idx
        k = f"\x00MDCODE{token_idx}\x00"
        token_idx += 1
        raw = m.group(1)
        esc = (
            raw.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        tokens[k] = (
            f'<code style="background: rgba(0,0,0,0.06); padding: 2px 6px; border-radius: 4px; '
            f'font-size: {code_font_size}; color: {accent}; font-family: monospace;">{esc}</code>'
        )
        return k

    text = re.sub(r"`([^`]+?)`", save_code, text)

    # 2. 保护超链接 [...](...)
    def save_link(m: re.Match) -> str:
        nonlocal token_idx
        k = f"\x00MDLINK{token_idx}\x00"
        token_idx += 1
        label = m.group(1).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        url = m.group(2)
        tokens[k] = f'<a href="{url}" style="color: {accent}; text-decoration: none; border-bottom: 1px dashed {accent};">{label}</a>'
        return k

    text = re.sub(r"\[(.*?)\]\((.*?)\)", save_link, text)

    # 3. 粗体与斜体
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", text)

    # 4. 还原保护的 tokens
    for k, v in tokens.items():
        text = text.replace(k, v)

    return text


# ==============================================================================
# 视觉组件渲染策略 (Component Renderers)
# ==============================================================================

def render_h1(title_text: str, theme: dict) -> str:
    """渲染一级主标题"""
    style = theme.get("h1_style", theme.get("styles", {}).get("h1", "underline"))
    accent = theme["accent"]
    accent_bg = theme["accent_bg"]
    border_color = theme["border_color"]
    code_bg = theme["code_bg"]
    sub_color = theme["sub_color"]
    page_bg = theme.get("page_bg", "#ffffff")
    is_dark = page_bg in ["#0b0f19", "#0f172a", "#18181b", "#09090b"]
    title_color = "#f8fafc" if is_dark else "#18181b"

    if style == "double_line":
        # 复古报刊风格：上下双细线居中
        return (
            f'<div style="margin: 38px 0 26px 0; text-align: center;">'
            f'<div style="border-top: 1px solid {border_color}; border-bottom: 1px solid {border_color}; padding: 12px 14px; display: inline-block; min-width: 60%;">'
            f'<h1 style="font-size: 22px; font-weight: 700; color: {accent}; margin: 0; line-height: 1.4; letter-spacing: 1px;">{title_text}</h1>'
            f'</div></div>'
        )
    elif style == "capsule":
        # 温暖便签/胶囊徽章风格
        return (
            f'<div style="margin: 36px 0 24px 0; text-align: center;">'
            f'<span style="display: inline-block; background: {accent}; color: #ffffff; padding: 9px 26px; border-radius: 30px; font-size: 20px; font-weight: 700; letter-spacing: 0.8px; box-shadow: 0 4px 14px rgba(0,0,0,0.12);">'
            f'{title_text}'
            f'</span></div>'
        )
    elif style == "terminal":
        # 极客终端命令行风格
        return (
            f'<div style="margin: 36px 0 24px 0; padding: 14px 18px; background: {code_bg}; border: 1px solid {border_color}; border-radius: 6px;">'
            f'<div style="color: {sub_color}; font-size: 12px; margin-bottom: 6px; font-family: monospace;">$ cat article.md</div>'
            f'<h1 style="font-size: 20px; font-weight: 700; color: {accent}; margin: 0; line-height: 1.4; font-family: monospace;">&gt; {title_text}</h1>'
            f'</div>'
        )
    elif style == "brutalist":
        # 先锋野兽派硬框与硬阴影
        return (
            f'<div style="margin: 36px 0 24px 0; text-align: center;">'
            f'<div style="display: inline-block; background: {accent_bg}; border: 2.5px solid #000000; box-shadow: 4px 4px 0 #000000; padding: 10px 22px;">'
            f'<h1 style="font-size: 21px; font-weight: 800; color: #000000; margin: 0; letter-spacing: 1px;">{title_text}</h1>'
            f'</div></div>'
        )
    else:
        # 默认：现代居中下划粗线 (underline)
        return (
            f'<h1 style="font-size: 23px; font-weight: 800; color: {title_color}; line-height: 1.4; margin: 36px 0 22px 0; text-align: center; letter-spacing: 0.5px;">'
            f'<span style="border-bottom: 3px solid {accent}; padding-bottom: 6px;">{title_text}</span>'
            f'</h1>'
        )

def render_h2(h2_text: str, theme: dict) -> str:
    """渲染二级分区标题"""
    style = theme.get("h2_style", theme.get("styles", {}).get("h2", "left_bar"))
    accent = theme["accent"]
    accent_bg = theme["accent_bg"]
    border_color = theme["border_color"]
    text_color = theme["text_color"]
    page_bg = theme.get("page_bg", "#ffffff")
    is_dark = page_bg in ["#0b0f19", "#0f172a", "#18181b", "#09090b"]
    heading_color = "#f8fafc" if is_dark else "#18181b"

    if style == "pill_badge":
        # 胶囊药丸徽章
        return (
            f'<div style="margin: 34px 0 16px 0;">'
            f'<span style="display: inline-block; background: {accent}; color: #ffffff; font-size: 16px; font-weight: 700; padding: 5px 15px; border-radius: 20px; letter-spacing: 0.5px;">'
            f'{h2_text}'
            f'</span></div>'
        )
    elif style == "bubble_bg":
        # 柔和底色块
        return (
            f'<div style="margin: 34px 0 16px 0;">'
            f'<span style="display: inline-block; background: {accent_bg}; color: {accent}; font-size: 17px; font-weight: 700; padding: 6px 14px; border-radius: 6px; border-left: 3px solid {accent};">'
            f'{h2_text}'
            f'</span></div>'
        )
    elif style == "serif_badge":
        # 古典报刊章节符号
        return (
            f'<h2 style="font-size: 18.5px; font-weight: 700; color: {accent}; margin: 34px 0 16px 0; padding-bottom: 6px; border-bottom: 1px solid {border_color}; line-height: 1.4; letter-spacing: 0.5px;">'
            f'<span style="color: {accent}; margin-right: 6px; font-family: Georgia, serif;">§</span>{h2_text}'
            f'</h2>'
        )
    elif style == "terminal_prompt":
        # 极客终端命令风格
        return (
            f'<div style="margin: 32px 0 16px 0; font-family: monospace;">'
            f'<span style="color: {accent}; font-weight: 700; font-size: 18px; margin-right: 8px;">//</span>'
            f'<h2 style="display: inline; font-size: 17.5px; font-weight: 700; color: {text_color}; margin: 0; font-family: monospace;">{h2_text}</h2>'
            f'</div>'
        )
    elif style == "brutalist_box":
        # 新野兽粗黑边框与硬投影
        return (
            f'<div style="margin: 34px 0 16px 0; display: inline-block; background: {accent_bg}; border: 2px solid #000000; box-shadow: 3px 3px 0 #000000; padding: 5px 14px;">'
            f'<h2 style="font-size: 17px; font-weight: 800; color: #000000; margin: 0;">{h2_text}</h2>'
            f'</div>'
        )
    elif style == "bottom_line":
        # 全宽底线
        return (
            f'<h2 style="font-size: 18.5px; font-weight: 700; color: {heading_color}; margin: 34px 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid {accent}; line-height: 1.4;">'
            f'{h2_text}'
            f'</h2>'
        )
    else:
        # 默认：左侧 4px 竖线条
        return (
            f'<h2 style="font-size: 19px; font-weight: 700; color: {heading_color}; margin: 34px 0 16px 0; padding-left: 12px; border-left: 4px solid {accent}; line-height: 1.4;">'
            f'{h2_text}'
            f'</h2>'
        )

def render_h3(h3_text: str, theme: dict) -> str:
    """渲染三级小标题"""
    style = theme.get("h3_style", theme.get("styles", {}).get("h3", "diamond"))
    accent = theme["accent"]
    accent_bg = theme["accent_bg"]
    sub_color = theme["sub_color"]
    page_bg = theme.get("page_bg", "#ffffff")
    is_dark = page_bg in ["#0b0f19", "#0f172a", "#18181b", "#09090b"]
    heading_color = "#f8fafc" if is_dark else "#18181b"

    if style == "circle_badge":
        # 实心小圆角方块
        return (
            f'<h3 style="font-size: 16.5px; font-weight: 600; color: {accent}; margin: 24px 0 12px 0; line-height: 1.4;">'
            f'<span style="display: inline-block; width: 8px; height: 8px; background: {accent}; border-radius: 2px; margin-right: 8px; vertical-align: middle;"></span>{h3_text}'
            f'</h3>'
        )
    elif style == "highlight_bg":
        # 荧光笔底纹
        return (
            f'<h3 style="font-size: 16.5px; font-weight: 600; color: {heading_color}; margin: 24px 0 12px 0; line-height: 1.4;">'
            f'<span style="background: linear-gradient(to top, {accent_bg} 45%, transparent 45%); padding: 1px 4px;">{h3_text}</span>'
            f'</h3>'
        )
    elif style == "slash":
        # 极客双斜线
        return (
            f'<h3 style="font-size: 16px; font-weight: 600; color: {accent}; margin: 24px 0 12px 0; line-height: 1.4; font-family: monospace;">'
            f'<span style="color: {sub_color}; margin-right: 6px;">##</span>{h3_text}'
            f'</h3>'
        )
    else:
        # 默认：菱形星号 ✦
        return (
            f'<h3 style="font-size: 16.5px; font-weight: 600; color: {accent}; margin: 24px 0 12px 0; line-height: 1.4;">'
            f'<span style="margin-right: 6px;">✦</span>{h3_text}'
            f'</h3>'
        )

def render_quote(inner_content: str, theme: dict) -> str:
    """渲染多行聚合引言块"""
    style = theme.get("quote_style", theme.get("styles", {}).get("quote", "left_stripe"))
    accent = theme["accent"]
    quote_bg = theme["quote_bg"]
    border_color = theme["border_color"]
    text_color = theme["text_color"]
    sub_color = theme["sub_color"]

    if style == "elegant_quote":
        # 复古报刊风格：典雅大引号与上下双细线
        return (
            f'<blockquote style="margin: 24px 0; padding: 16px 20px; background: {quote_bg}; border-top: 1px solid {border_color}; border-bottom: 1px solid {border_color}; color: {text_color}; font-size: 14.5px; position: relative;">\n'
            f'<div style="font-size: 28px; color: {accent}; line-height: 1; margin-bottom: 4px; font-family: Georgia, serif;">“</div>\n'
            f'{inner_content}\n'
            f'<div style="font-size: 28px; color: {accent}; line-height: 1; text-align: right; margin-top: 4px; font-family: Georgia, serif;">”</div>\n'
            f'</blockquote>'
        )
    elif style == "bubble_card":
        # 优雅气泡卡片
        return (
            f'<blockquote style="margin: 22px 0; padding: 16px 18px; background: {quote_bg}; border: 1px solid {border_color}; border-radius: 10px; color: {text_color}; font-size: 14.5px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">\n'
            f'{inner_content}\n'
            f'</blockquote>'
        )
    elif style == "paper_memo":
        # 温暖便签贴纸风格
        return (
            f'<div style="margin: 24px 0; background: {quote_bg}; border: 1px solid {border_color}; border-left: 4px solid {accent}; border-radius: 4px; padding: 14px 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); color: {text_color}; font-size: 14.5px;">\n'
            f'<div style="font-size: 11px; font-weight: 700; color: {accent}; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">NOTE // 便签</div>\n'
            f'{inner_content}\n'
            f'</div>'
        )
    elif style == "terminal_box":
        # 极客终端回显
        return (
            f'<div style="margin: 22px 0; padding: 12px 16px; background: {quote_bg}; border-left: 3px solid {accent}; border: 1px solid {border_color}; border-radius: 4px; font-family: monospace; font-size: 13.5px; color: {text_color};">\n'
            f'<div style="color: {sub_color}; font-size: 11px; margin-bottom: 6px;">[OUTPUT / 回显]</div>\n'
            f'{inner_content}\n'
            f'</div>'
        )
    elif style == "brutalist":
        # 先锋野兽派粗黑实线框
        return (
            f'<blockquote style="margin: 24px 0; padding: 14px 16px; background: {quote_bg}; border: 2px solid #000000; box-shadow: 3px 3px 0 #000000; color: #000000; font-size: 14.5px; font-weight: 500;">\n'
            f'{inner_content}\n'
            f'</blockquote>'
        )
    else:
        # 默认：经典左侧竖条 (left_stripe)
        return (
            f'<blockquote style="margin: 22px 0; padding: 14px 18px; background: {quote_bg}; border-left: 4px solid {accent}; color: {text_color}; font-size: 14.5px; border-radius: 0 8px 8px 0; line-height: 1.75;">\n'
            f'{inner_content}\n'
            f'</blockquote>'
        )

def render_code(raw_code: str, code_lang: str, theme: dict) -> str:
    """渲染多行代码块"""
    style = theme.get("code_style", theme.get("styles", {}).get("code", "mac_dark"))
    code_bg = theme["code_bg"]
    code_text = theme.get("code_text", "#e4e4e7")
    accent = theme["accent"]
    border_color = theme["border_color"]
    sub_color = theme["sub_color"]

    if style == "terminal":
        # 纯黑终端状态栏风格
        top_bar = (
            f'<div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 12px; background: #020617; border-bottom: 1px solid {border_color}; font-family: monospace; font-size: 11.5px; color: {sub_color};">'
            f'<span>term: {code_lang or "bash"}</span>'
            f'<span style="color: {accent};">● RUNNING</span>'
            f'</div>'
        )
        return (
            f'<div style="margin: 22px 0; border-radius: 6px; overflow: hidden; border: 1px solid {border_color}; box-shadow: 0 4px 14px rgba(0,0,0,0.15);">'
            f'{top_bar}'
            f'<pre style="margin: 0; padding: 14px 16px; background: {code_bg}; color: {code_text}; font-size: 13.5px; line-height: 1.6; overflow-x: auto; font-family: Consolas, Monaco, monospace;"><code>{raw_code}</code></pre>'
            f'</div>'
        )
    elif style == "clean_flat":
        # 极简扁平圆角无指示灯
        return (
            f'<div style="margin: 22px 0; border-radius: 8px; overflow: hidden; border: 1px solid {border_color};">'
            f'<pre style="margin: 0; padding: 14px 16px; background: {code_bg}; color: {code_text}; font-size: 13.5px; line-height: 1.6; overflow-x: auto; font-family: Consolas, Monaco, monospace;"><code>{raw_code}</code></pre>'
            f'</div>'
        )
    else:
        # 默认：Mac 红黄绿三色小圆点
        mac_dots = (
            '<div style="display: flex; align-items: center; padding: 8px 12px; background: #27272a; border-top-left-radius: 8px; border-top-right-radius: 8px; border-bottom: 1px solid #3f3f46;">'
            '<span style="width: 10px; height: 10px; border-radius: 50%; background: #ef4444; display: inline-block; margin-right: 6px;"></span>'
            '<span style="width: 10px; height: 10px; border-radius: 50%; background: #f59e0b; display: inline-block; margin-right: 6px;"></span>'
            '<span style="width: 10px; height: 10px; border-radius: 50%; background: #10b981; display: inline-block; margin-right: 10px;"></span>'
            f'<span style="color: #a1a1aa; font-size: 12px; font-family: monospace;">{code_lang or "code"}</span>'
            '</div>'
        )
        return (
            f'<div style="margin: 22px 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.08);">'
            f'{mac_dots}'
            f'<pre style="margin: 0; padding: 14px 16px; background: {code_bg}; color: {code_text}; font-size: 13.5px; line-height: 1.6; overflow-x: auto; font-family: Consolas, Monaco, monospace;"><code>{raw_code}</code></pre>'
            f'</div>'
        )

def render_table(header: List[str], rows: List[List[str]], theme: dict) -> str:
    """渲染表格"""
    style = theme.get("table_style", theme.get("styles", {}).get("table", "zebra"))
    accent = theme["accent"]
    accent_bg = theme["accent_bg"]
    border_color = theme["border_color"]
    text_color = theme["text_color"]
    page_bg = theme.get("page_bg", "#ffffff")
    is_dark = page_bg in ["#0b0f19", "#0f172a", "#18181b", "#09090b"]
    td_bg_alt = "#1e293b" if is_dark else "#fafafa"
    td_bg = "#0f172a" if is_dark else "#ffffff"

    if style == "three_line":
        # 经典学术三线表 (古典报刊首选：顶线加粗、底线加粗、表头细线、无坚固竖线)
        table_html = (
            f'<div style="overflow-x: auto; margin: 24px 0;">'
            f'<table style="width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; '
            f'border-top: 2px solid {accent}; border-bottom: 2px solid {accent}; background: transparent;">'
        )
        if header:
            table_html += f'<thead><tr>'
            for h in header:
                table_html += f'<th style="padding: 10px 14px; font-weight: 700; color: {accent}; border-bottom: 1px solid {border_color};">{h}</th>'
            table_html += '</tr></thead>'
        table_html += '<tbody>'
        for row in rows:
            table_html += f'<tr style="border-bottom: 1px dashed {border_color};">'
            for c in row:
                c_fmt = format_inline(c, accent, "12.5px")
                table_html += f'<td style="padding: 10px 14px; color: {text_color}; line-height: 1.5;">{c_fmt}</td>'
            table_html += '</tr>'
        table_html += '</tbody></table></div>'
        return table_html
    elif style == "grid":
        # 极客/先锋全网格卡片表
        table_html = (
            f'<div style="overflow-x: auto; margin: 24px 0;">'
            f'<table style="width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; '
            f'border: 2px solid {border_color}; background: {td_bg};">'
        )
        if header:
            table_html += f'<thead><tr style="background: {accent_bg};">'
            for h in header:
                table_html += f'<th style="padding: 10px 14px; font-weight: 700; color: {accent}; border: 1px solid {border_color};">{h}</th>'
            table_html += '</tr></thead>'
        table_html += '<tbody>'
        for row in rows:
            table_html += f'<tr>'
            for c in row:
                c_fmt = format_inline(c, accent, "12.5px")
                table_html += f'<td style="padding: 10px 14px; color: {text_color}; line-height: 1.5; border: 1px solid {border_color};">{c_fmt}</td>'
            table_html += '</tr>'
        table_html += '</tbody></table></div>'
        return table_html
    else:
        # 默认：现代斑马纹 (zebra)
        table_html = (
            f'<div style="overflow-x: auto; margin: 24px 0;">'
            f'<table style="width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; '
            f'background: {td_bg}; border-radius: 8px; overflow: hidden; border: 1px solid {border_color};">'
        )
        if header:
            table_html += f'<thead><tr style="background: {accent_bg};">'
            for h in header:
                table_html += f'<th style="padding: 11px 14px; font-weight: 600; color: {accent}; border-bottom: 2px solid {border_color};">{h}</th>'
            table_html += '</tr></thead>'
        table_html += '<tbody>'
        for r_idx, row in enumerate(rows):
            bg = td_bg_alt if r_idx % 2 == 1 else td_bg
            table_html += f'<tr style="background: {bg}; border-bottom: 1px solid {border_color};">'
            for c in row:
                c_fmt = format_inline(c, accent, "12.5px")
                table_html += f'<td style="padding: 10px 14px; color: {text_color}; line-height: 1.5;">{c_fmt}</td>'
            table_html += '</tr>'
        table_html += '</tbody></table></div>'
        return table_html

def render_list_item(item_text: str, theme: dict) -> str:
    """渲染列表项"""
    style = theme.get("list_style", theme.get("styles", {}).get("list", "bullet"))
    accent = theme["accent"]
    text_color = theme["text_color"]

    if style == "diamond":
        bullet_symbol = "◆"
    elif style == "square":
        bullet_symbol = "■"
    elif style == "arrow":
        bullet_symbol = "▸"
    else:
        bullet_symbol = "•"

    return (
        f'<section style="display: flex; align-items: flex-start; margin-bottom: 8px; line-height: 1.75; font-size: 15.5px; color: {text_color};">'
        f'<span style="color: {accent}; margin-right: 8px; font-size: 15px; line-height: 1.75;">{bullet_symbol}</span>'
        f'<span style="flex: 1;">{item_text}</span>'
        f'</section>'
    )

def render_hr(theme: dict) -> str:
    """渲染分割线"""
    style = theme.get("hr_style", theme.get("styles", {}).get("hr", "line"))
    accent = theme["accent"]
    border_color = theme["border_color"]
    sub_color = theme["sub_color"]

    if style == "gradient":
        # 渐变双向淡出虚化线
        return f'<div style="height: 1px; background: linear-gradient(to right, transparent, {accent}, transparent); margin: 34px auto; width: 85%;"></div>'
    elif style == "asterisk":
        # 文艺星号组居中
        return f'<div style="text-align: center; color: {accent}; font-size: 14px; letter-spacing: 8px; margin: 32px 0;">✻  ✻  ✻</div>'
    elif style == "terminal_dash":
        # 极客虚线
        return f'<div style="text-align: center; color: {sub_color}; font-family: monospace; font-size: 12px; letter-spacing: 2px; margin: 32px 0;">----------------------------------------</div>'
    else:
        # 默认：细实线
        return f'<hr style="border: 0; height: 1px; background: {border_color}; margin: 32px auto; width: 85%;" />'

def render_container(body_html: str, theme: dict) -> str:
    """根据主题渲染外层主排版容器"""
    style = theme.get("container_style", theme.get("styles", {}).get("container", "clean"))
    page_bg = theme.get("page_bg", "#ffffff")
    text_color = theme["text_color"]
    border_color = theme["border_color"]
    font_family = theme.get("typography", {}).get(
        "font_family",
        "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    )

    base_style = (
        f"max-width: 677px; margin: 0 auto; box-sizing: border-box; "
        f"font-family: {font_family}; background: {page_bg}; color: {text_color}; "
    )

    if style == "paper":
        # 复古报刊：米黄质感底色，带微边框
        container_style = (
            f"{base_style} padding: 24px 16px; border: 1px solid {border_color}; "
            f"border-radius: 4px; box-shadow: 0 2px 12px rgba(0,0,0,0.03);"
        )
    elif style == "dark":
        # 极客深邃纯黑
        container_style = (
            f"{base_style} padding: 20px 14px; border: 1px solid {border_color}; "
            f"border-radius: 8px;"
        )
    elif style == "card":
        # 独立悬浮圆角卡片
        container_style = (
            f"{base_style} padding: 24px 16px; border-radius: 12px; "
            f"box-shadow: 0 4px 20px rgba(0,0,0,0.05);"
        )
    elif style == "memo":
        # 温暖便签
        container_style = (
            f"{base_style} padding: 22px 14px; border-radius: 10px; "
            f"border: 1px dashed {border_color};"
        )
    elif style == "brutalist":
        # 先锋野兽派：粗黑边框 + 黑色硬投影
        container_style = (
            f"{base_style} padding: 20px 14px; border: 2.5px solid #000000; "
            f"box-shadow: 5px 5px 0 #000000;"
        )
    else:
        # 默认：极简无框
        container_style = f"{base_style} padding: 14px 8px;"

    return f'<div style="{container_style}">\n{body_html}\n</div>'

# ==============================================================================
# Markdown 解析主循环 (Parser Pipeline)
# ==============================================================================

def markdown_to_wechat_html(
    md_text: str,
    theme_name: str = "tech-blue",
    image_map: Optional[Dict[str, str]] = None
) -> str:
    """
    将 Markdown 文本转换为微信公众号完美适配的纯 Inline CSS HTML
    支持指定主题名称或自定义 JSON 主题文件路径
    """
    theme = get_theme(theme_name)
    accent = theme["accent"]
    text_color = theme["text_color"]
    sub_color = theme["sub_color"]

    typography = theme.get("typography", {})
    font_size_base = typography.get("font_size_base", "15.5px")
    line_height_base = typography.get("line_height_base", "1.8")
    letter_spacing = typography.get("letter_spacing", "0.4px")
    paragraph_indent = typography.get("paragraph_indent", False)
    indent_css = "text-indent: 2em; " if paragraph_indent else ""

    # 1. 替换已上传到微信 CDN 的图片链接
    if image_map:
        for local_ref, cdn_url in image_map.items():
            md_text = md_text.replace(local_ref, cdn_url)

    lines = md_text.split("\n")
    html_parts = []

    in_code_block = False
    code_lang = ""
    code_lines = []

    in_table = False
    table_lines = []

    def flush_table() -> str:
        nonlocal in_table, table_lines
        if not table_lines:
            return ""
        header = []
        rows = []
        for i, line in enumerate(table_lines):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if i == 0:
                header = cells
            elif i == 1 and all(set(c).issubset({'-', ':', ' '}) for c in cells):
                continue
            else:
                rows.append(cells)

        rendered = render_table(header, rows, theme)
        table_lines = []
        in_table = False
        return rendered

    def flush_code() -> str:
        nonlocal in_code_block, code_lang, code_lines
        raw_code = "\n".join(code_lines)
        raw_code = raw_code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rendered = render_code(raw_code, code_lang, theme)
        code_lines = []
        in_code_block = False
        return rendered

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        # 1. 代码块
        if stripped.startswith("```"):
            if in_code_block:
                html_parts.append(flush_code())
            else:
                if in_table:
                    html_parts.append(flush_table())
                in_code_block = True
                code_lang = stripped[3:].strip()
                code_lines = []
            idx += 1
            continue

        if in_code_block:
            code_lines.append(line)
            idx += 1
            continue

        # 2. 表格
        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
            table_lines.append(stripped)
            idx += 1
            continue
        elif in_table:
            html_parts.append(flush_table())

        # 3. 空行
        if not stripped:
            idx += 1
            continue

        # 4. 分割线
        if stripped in ["---", "***", "___"]:
            html_parts.append(render_hr(theme))
            idx += 1
            continue

        # 5. 一级标题
        if stripped.startswith("# "):
            title_text = stripped[2:].strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_parts.append(render_h1(title_text, theme))
            idx += 1
            continue

        # 6. 二级标题
        if stripped.startswith("## "):
            h2_text = stripped[3:].strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_parts.append(render_h2(h2_text, theme))
            idx += 1
            continue

        # 7. 三级标题
        if stripped.startswith("### "):
            h3_text = stripped[4:].strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_parts.append(render_h3(h3_text, theme))
            idx += 1
            continue

        # 8. 引用块聚合处理（聚合连续的 > 行，合成单个连贯的 blockquote 容器）
        if stripped.startswith(">"):
            quote_lines = []
            while idx < len(lines) and lines[idx].strip().startswith(">"):
                q_line = lines[idx].strip()
                if q_line.startswith("> "):
                    q_line = q_line[2:].strip()
                elif q_line.startswith(">"):
                    q_line = q_line[1:].strip()
                quote_lines.append(q_line)
                idx += 1

            formatted_items = []
            for q_line in quote_lines:
                if not q_line:
                    formatted_items.append('<div style="height: 6px;"></div>')
                    continue
                q_fmt = format_inline(q_line, accent, "13px")
                formatted_items.append(f'<div style="margin: 4px 0; line-height: 1.75;">{q_fmt}</div>')

            inner_content = "\n".join(formatted_items)
            html_parts.append(render_quote(inner_content, theme))
            continue

        # 9. 列表项
        if stripped.startswith("- ") or stripped.startswith("* "):
            item_text = stripped[2:].strip()
            item_fmt = format_inline(item_text, accent, "13.5px")
            html_parts.append(render_list_item(item_fmt, theme))
            idx += 1
            continue

        # 10. 图片格式 ![alt](url)
        img_match = re.match(r'^!\[(.*?)\]\((.*?)\)$', stripped)
        if img_match:
            alt, src = img_match.group(1), img_match.group(2)
            caption = f'<div style="text-align: center; color: {sub_color}; font-size: 13px; margin-top: 6px; font-style: italic;">{alt}</div>' if alt else ""
            html_parts.append(
                f'<div style="margin: 24px 0; text-align: center;">'
                f'<img src="{src}" alt="{alt}" style="max-width: 96%; height: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); display: inline-block;" />'
                f'{caption}'
                f'</div>'
            )
            idx += 1
            continue

        # 11. 显式图注 (*▲ 图：...*)
        caption_match = re.match(r'^\*▲ 图：(.+?)\*$', stripped)
        if caption_match:
            cap_text = caption_match.group(1)
            html_parts.append(
                f'<div style="text-align: center; color: {sub_color}; font-size: 13px; margin: -16px 0 20px 0; font-style: italic;">'
                f'▲ 图：{cap_text}'
                f'</div>'
            )
            idx += 1
            continue

        # 12. 正文段落
        p_text = format_inline(stripped, accent, "13.5px")

        html_parts.append(
            f'<p style="font-size: {font_size_base}; line-height: {line_height_base}; color: {text_color}; '
            f'margin: 18px 0; letter-spacing: {letter_spacing}; {indent_css}text-align: justify;">'
            f'{p_text}'
            f'</p>'
        )
        idx += 1

    if in_table:
        html_parts.append(flush_table())
    if in_code_block:
        html_parts.append(flush_code())

    final_body = "\n".join(html_parts)
    return render_container(final_body, theme)

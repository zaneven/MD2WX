"""
MD2WX 文章专属主题封面动态渲染引擎 (Theme-Matched Article Cover Generator)
与 Web Studio Cover Studio 保持同一套视觉预设：
1. 依据文章标题/摘要/作者 + 主题预设，构建自包含封面 HTML (移植 web/src/styles/cover.css 横版 Banner 版式)
2. 调用系统已安装的 Chrome/Edge/Chromium 无头截图输出 2350x1000 PNG (微信头条 2.35:1 推荐尺寸)
3. 未检测到无头浏览器时安全降级，由调用方回退到内置静态主题封面
遵循零依赖哲学：仅使用 Python 标准库 (subprocess 调用系统浏览器，不引入任何第三方包)
"""
import os
import sys
import time
import html
import json
import shutil
import hashlib
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Optional

# 与 Web Studio THEME_COVER_PRESETS (web/src/core/cover.js) 保持一致
THEME_COVER_PRESETS: Dict[str, Dict[str, str]] = {
    "tech-blue": {
        "name": "现代科技蓝",
        "defaultTag": "深度架构 · 极客手记",
        "badgeText": "TECH BLOG",
        "volText": "2026 · VOL.02",
    },
    "acid-bold": {
        "name": "先锋野兽派",
        "defaultTag": "态度发声 · 拒绝平庸",
        "badgeText": "ACID BOLD",
        "volText": "VOL.02 // POP",
    },
    "dark-night": {
        "name": "暗黑极客风",
        "defaultTag": "赛博夜读 · 极客沉思",
        "badgeText": "NIGHT RUN",
        "volText": "0x02 // CYBER",
    },
    "elegant-purple": {
        "name": "先锋优雅紫",
        "defaultTag": "设计美学 · 独立思考",
        "badgeText": "AESTHETIC",
        "volText": "2026 · ISSUE 02",
    },
    "terminal-geek": {
        "name": "极客终端",
        "defaultTag": "SHELL · 架构复盘",
        "badgeText": "BASH / DEV",
        "volText": "TERM // 2026",
    },
    "vintage-news": {
        "name": "复古报刊",
        "defaultTag": "人文书卷 · 思想论丛",
        "badgeText": "WEEKLY PRESS",
        "volText": "第 02 期 · 专刊",
    },
    "warm-memo": {
        "name": "温暖便签",
        "defaultTag": "生活手记 · 日常微光",
        "badgeText": "HEALING NOTE",
        "volText": "2026 · MEMO #02",
    },
    "warm-orange": {
        "name": "温暖活力橙",
        "defaultTag": "元气日常 · 读书感悟",
        "badgeText": "SUNSHINE",
        "volText": "2026 · VOL.02",
    },
    "wechat-green": {
        "name": "微信生态绿",
        "defaultTag": "官方资讯 · 行业前沿",
        "badgeText": "WECHAT OFFICIAL",
        "volText": "2026 · ISSUE 02",
    },
}

COVER_WIDTH = 1175
COVER_HEIGHT = 500
SQUARE_COVER_WIDTH = 500
SQUARE_COVER_HEIGHT = 500
DUAL_COVER_WIDTH = 1675  # 1175 + 500
DUAL_COVER_HEIGHT = 500

# 微信公众号草稿箱推荐双封面裁剪坐标 (针对 3350x1000 左右并排合成图)
# 2.35:1 头条横版大图: X 在 [0, 2350], Y 在 [0, 1000] -> X2 = 2350/3350 ≈ 0.701493
WECHAT_CROP_235_1 = "0_0_0.701493_1"
# 1:1 次条/会话分享方图: X 在 [2350, 3350], Y 在 [0, 1000] -> X1 = 2350/3350 ≈ 0.701493
WECHAT_CROP_1_1 = "0.701493_0_1_1"

# 横版 Banner 与 Square 方图版式样式 (忠实对齐 web/src/styles/cover.css)
_COVER_CSS = """
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #ffffff; }
.cover-canvas {
  box-sizing: border-box; position: relative; overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  -webkit-font-smoothing: antialiased; display: flex; flex-direction: column;
}
.cover-canvas.ratio-banner { width: 1175px; height: 500px; }
.cover-canvas.ratio-square { width: 500px; height: 500px; }
.cover-inner {
  width: 100%; height: 100%; padding: 44px 52px;
  display: flex; flex-direction: column; justify-content: space-between;
  position: relative; z-index: 2; box-sizing: border-box;
}
.ratio-square .cover-inner { padding: 34px 36px; }

/* Banner 比例内部网格布局 */
.banner-top-bar { display: flex; align-items: center; justify-content: space-between; }
.banner-top-bar .top-left { display: flex; align-items: center; gap: 14px; max-width: 415px; overflow: hidden; }
.cover-badge {
  font-size: 19px; font-weight: 900; letter-spacing: 1.2px; padding: 6px 16px;
  border-radius: 999px; text-transform: uppercase; display: inline-flex;
  align-items: center; line-height: 1; flex-shrink: 0;
}
.cover-tag-banner { font-size: 19px; font-weight: 800; letter-spacing: 0.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cover-vol { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 20px; font-weight: 800; letter-spacing: 1.5px; }
.banner-body { display: flex; align-items: center; justify-content: space-between; gap: 40px; margin: auto 0; min-width: 0; }
.banner-left-col { width: 410px; max-width: 410px; flex-shrink: 0; display: flex; flex-direction: column; gap: 18px; min-width: 0; }
.headline-indicator { width: 64px; height: 8px; border-radius: 4px; }
.banner-main-title { font-size: 46px; font-weight: 900; line-height: 1.18; letter-spacing: -0.6px; margin: 0; word-break: break-word; }
.banner-left-meta { display: flex; align-items: center; gap: 14px; margin-top: 4px; }
.banner-author-pill { font-size: 19px; font-weight: 800; padding: 6px 16px; border-radius: 999px; background: rgba(255, 255, 255, 0.16); line-height: 1.2; }
.banner-right-card {
  flex: 1; max-width: 580px; border-radius: 24px; padding: 34px 38px;
  display: flex; flex-direction: column; justify-content: space-between;
  min-height: 250px; min-width: 0; box-shadow: 0 20px 48px rgba(0, 0, 0, 0.3);
}
.card-quote-icon { opacity: 0.6; line-height: 1; margin-bottom: 6px; }
.banner-digest { font-size: 28px; line-height: 1.48; font-weight: 700; margin: 0; opacity: 0.95; word-break: break-word; }
.card-signature { font-size: 22px; font-weight: 800; text-align: right; margin-top: 16px; letter-spacing: 0.5px; opacity: 0.9; }

/* Square (1:1) 比例内部布局 */
.square-top-bar { display: flex; align-items: center; justify-content: space-between; }
.square-content-box { margin: auto 0; display: flex; flex-direction: column; gap: 16px; }
.cover-category-chip { align-self: flex-start; font-size: 16px; font-weight: 800; padding: 6px 16px; border-radius: 999px; letter-spacing: 0.5px; }
.square-main-title { font-size: 40px; font-weight: 900; line-height: 1.18; letter-spacing: -0.6px; margin: 0; word-break: break-word; }
.square-digest { font-size: 20px; line-height: 1.5; margin: 0; opacity: 0.92; word-break: break-word; font-weight: 600; }
.square-bottom-bar { display: flex; align-items: center; justify-content: space-between; padding-top: 14px; border-top: 1px solid rgba(255, 255, 255, 0.12); }
.author-wrap { display: flex; align-items: center; gap: 10px; font-size: 19px; font-weight: 800; }
.author-dot { width: 10px; height: 10px; border-radius: 50%; }

/* Dual (双图合拼画布: 1675x500 逻辑尺寸, 2x 采样即 3350x1000) */
.cover-canvas-dual { display: flex; flex-direction: row; width: 1675px; height: 500px; overflow: hidden; background: #000000; }
.cover-canvas-dual .cover-canvas.ratio-banner { width: 1175px; height: 500px; flex-shrink: 0; }
.cover-canvas-dual .cover-canvas.ratio-square { width: 500px; height: 500px; flex-shrink: 0; }

.term-window-controls { display: flex; align-items: center; gap: 8px; padding: 12px 24px; background: #090e1a; border-bottom: 1px solid #1e293b; }
.term-window-controls .dot { width: 12px; height: 12px; border-radius: 50%; }
.term-window-controls .dot.red { background: #ef4444; }
.term-window-controls .dot.yellow { background: #f59e0b; }
.term-window-controls .dot.green { background: #10b981; }
.term-prompt-title { margin-left: 12px; font-size: 13px; color: #64748b; }
.wechat-verify-badge {
  display: inline-flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 700;
  color: #07c160; background: rgba(7, 193, 96, 0.12); padding: 2px 6px; border-radius: 4px; margin-left: 6px;
}

/* --- 1. 现代科技蓝 (tech-blue) --- */
.cover-theme-tech-blue { background: radial-gradient(circle at 80% 20%, #1e3a8a 0%, #0a0f1d 70%); color: #ffffff; border: 1px solid rgba(56, 189, 248, 0.25); }
.cover-theme-tech-blue .headline-indicator { background: linear-gradient(90deg, #38bdf8, #2563eb); }
.cover-theme-tech-blue .cover-badge { background: #2563eb; color: #ffffff; box-shadow: 0 0 16px rgba(37, 99, 235, 0.4); }
.cover-theme-tech-blue .banner-right-card { background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(56, 189, 248, 0.25); box-shadow: 0 16px 36px rgba(0, 0, 0, 0.4); }
.cover-theme-tech-blue .card-quote-icon { color: #38bdf8; }
.cover-theme-tech-blue .card-signature { color: #38bdf8; font-weight: 800; }
.cover-theme-tech-blue .cover-category-chip { background: rgba(37, 99, 235, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); }
.cover-theme-tech-blue .author-dot { background: #38bdf8; box-shadow: 0 0 8px #38bdf8; }

/* --- 2. 先锋野兽派 (acid-bold) --- */
.cover-theme-acid-bold { background: #fee500; color: #000000; border: 12px solid #000000; }
.cover-theme-acid-bold .cover-inner { border: 4px solid #000000; }
.cover-theme-acid-bold .headline-indicator { background: #000000; height: 10px; }
.cover-theme-acid-bold .cover-badge { background: #000000; color: #fee500; border: 3px solid #000000; box-shadow: 4px 4px 0 #000000; }
.cover-theme-acid-bold .banner-right-card { background: #ffffff; border: 5px solid #000000; box-shadow: 10px 10px 0 #000000; color: #000000; }
.cover-theme-acid-bold .card-quote-icon { color: #000000; }
.cover-theme-acid-bold .card-signature { color: #000000; font-weight: 900; }
.cover-theme-acid-bold .square-bottom-bar { border-top: 4px solid #000000; }
.cover-theme-acid-bold .cover-category-chip { background: #000000; color: #fee500; }
.cover-theme-acid-bold .author-dot { background: #000000; }

/* --- 3. 暗黑极客风 (dark-night) --- */
.cover-theme-dark-night { background: #0b0f19; color: #f1f5f9; border: 1px solid #1e293b; }
.cover-theme-dark-night .headline-indicator { background: #38bdf8; box-shadow: 0 0 12px #38bdf8; }
.cover-theme-dark-night .cover-badge { background: #1e293b; color: #38bdf8; border: 1px solid #38bdf8; }
.cover-theme-dark-night .banner-right-card { background: rgba(15, 23, 42, 0.75); border: 1px solid #334155; }
.cover-theme-dark-night .card-quote-icon { color: #38bdf8; }
.cover-theme-dark-night .card-signature { color: #38bdf8; font-weight: 800; }
.cover-theme-dark-night .cover-category-chip { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
.cover-theme-dark-night .author-dot { background: #38bdf8; box-shadow: 0 0 8px #38bdf8; }

/* --- 4. 先锋优雅紫 (elegant-purple) --- */
.cover-theme-elegant-purple { background: linear-gradient(135deg, #2e1065 0%, #0f172a 100%); color: #f5f3ff; border: 1px solid rgba(192, 132, 252, 0.3); }
.cover-theme-elegant-purple .headline-indicator { background: linear-gradient(90deg, #c084fc, #7c3aed); }
.cover-theme-elegant-purple .cover-badge { background: #7c3aed; color: #ffffff; box-shadow: 0 4px 18px rgba(124, 58, 237, 0.4); }
.cover-theme-elegant-purple .banner-right-card { background: rgba(30, 27, 75, 0.65); border: 1px solid rgba(192, 132, 252, 0.25); }
.cover-theme-elegant-purple .card-quote-icon { color: #c084fc; }
.cover-theme-elegant-purple .card-signature { color: #c084fc; font-weight: 800; }
.cover-theme-elegant-purple .cover-category-chip { background: rgba(192, 132, 252, 0.2); color: #e9d5ff; border: 1px solid rgba(192, 132, 252, 0.35); }
.cover-theme-elegant-purple .author-dot { background: #c084fc; box-shadow: 0 0 8px #c084fc; }

/* --- 5. 极客终端 (terminal-geek) --- */
.cover-theme-terminal-geek { background: #020617; color: #34d399; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; border: 2px solid #065f46; }
.cover-theme-terminal-geek .headline-indicator { background: #10b981; box-shadow: 0 0 10px #10b981; }
.cover-theme-terminal-geek .banner-main-title { color: #10b981; text-shadow: 0 0 16px rgba(16, 185, 129, 0.4); }
.cover-theme-terminal-geek .banner-digest { color: #a7f3d0; }
.cover-theme-terminal-geek .square-main-title { color: #10b981; text-shadow: 0 0 16px rgba(16, 185, 129, 0.4); }
.cover-theme-terminal-geek .square-digest { color: #a7f3d0; }
.cover-theme-terminal-geek .square-bottom-bar { border-top: 1px solid #065f46; }
.cover-theme-terminal-geek .cover-badge { background: #064e3b; color: #34d399; border: 1px solid #10b981; }
.cover-theme-terminal-geek .banner-right-card { background: #090f1d; border: 1.5px solid #065f46; }
.cover-theme-terminal-geek .card-quote-icon { color: #10b981; }
.cover-theme-terminal-geek .card-signature { color: #34d399; font-weight: 700; font-family: ui-monospace, Menlo, monospace; }
.cover-theme-terminal-geek .cover-category-chip { background: #064e3b; color: #34d399; border: 1px solid #10b981; }
.cover-theme-terminal-geek .author-dot { background: #10b981; box-shadow: 0 0 8px #10b981; }

/* --- 6. 复古报刊 (vintage-news) --- */
.cover-theme-vintage-news { background: #fdfbf7; color: #292524; font-family: -apple-system-font, "Songti SC", "Noto Serif SC", "Source Han Serif SC", SimSun, Georgia, serif; border: 8px double #44403c; }
.cover-theme-vintage-news .headline-indicator { background: #854d0e; height: 6px; }
.cover-theme-vintage-news .cover-badge { background: #292524; color: #fef3c7; border-radius: 2px; }
.cover-theme-vintage-news .banner-right-card { background: #f5f0e6; border: 2px solid #a8a29e; border-radius: 8px; color: #1c1917; }
.cover-theme-vintage-news .card-quote-icon { color: #854d0e; }
.cover-theme-vintage-news .card-signature { color: #854d0e; font-family: -apple-system-font, "Songti SC", "Noto Serif SC", SimSun, Georgia, serif; font-weight: 800; }
.cover-theme-vintage-news .square-bottom-bar { border-top: 2px solid #a8a29e; }
.cover-theme-vintage-news .cover-category-chip { background: #fef3c7; color: #854d0e; border: 1px solid #d6d3d1; }
.cover-theme-vintage-news .author-dot { background: #854d0e; }

/* --- 7. 温暖便签 (warm-memo) --- */
.cover-theme-warm-memo { background: #fefcf8; color: #292524; border: 1px solid #fed7aa; }
.cover-theme-warm-memo .headline-indicator { background: #ea580c; border-radius: 999px; height: 8px; }
.cover-theme-warm-memo .cover-badge { background: #ea580c; color: #ffffff; border-radius: 999px; }
.cover-theme-warm-memo .banner-right-card { background: #fff7ed; border: 2px solid #fdba74; border-radius: 24px; box-shadow: 0 10px 25px rgba(234, 88, 12, 0.1); }
.cover-theme-warm-memo .card-quote-icon { color: #ea580c; }
.cover-theme-warm-memo .card-signature { color: #ea580c; font-weight: 800; }
.cover-theme-warm-memo .cover-category-chip { background: #ffedd5; color: #ea580c; }
.cover-theme-warm-memo .author-dot { background: #ea580c; }

/* --- 8. 温暖活力橙 (warm-orange) --- */
.cover-theme-warm-orange { background: linear-gradient(135deg, #ea580c 0%, #7c2d12 100%); color: #ffffff; border: 1px solid rgba(253, 186, 116, 0.3); }
.cover-theme-warm-orange .headline-indicator { background: #fed7aa; height: 8px; }
.cover-theme-warm-orange .cover-badge { background: #ffffff; color: #ea580c; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2); }
.cover-theme-warm-orange .banner-right-card { background: rgba(255, 255, 255, 0.14); border: 1px solid rgba(255, 255, 255, 0.25); }
.cover-theme-warm-orange .card-quote-icon { color: #fed7aa; }
.cover-theme-warm-orange .card-signature { color: #fed7aa; font-weight: 800; }
.cover-theme-warm-orange .cover-category-chip { background: rgba(255, 255, 255, 0.2); color: #ffffff; }
.cover-theme-warm-orange .author-dot { background: #fed7aa; }

/* --- 9. 微信生态绿 (wechat-green) --- */
.cover-theme-wechat-green { background: linear-gradient(135deg, #064e3b 0%, #022c22 100%); color: #ffffff; border: 1px solid rgba(74, 222, 128, 0.2); }
.cover-theme-wechat-green .headline-indicator { background: #07c160; box-shadow: 0 0 10px rgba(7, 193, 96, 0.6); height: 8px; }
.cover-theme-wechat-green .cover-badge { background: #07c160; color: #ffffff; }
.cover-theme-wechat-green .banner-right-card { background: rgba(6, 78, 59, 0.5); border: 1px solid rgba(74, 222, 128, 0.25); }
.cover-theme-wechat-green .card-quote-icon { color: #4ade80; }
.cover-theme-wechat-green .cover-category-chip { background: rgba(7, 193, 96, 0.25); color: #86efac; }
.cover-theme-wechat-green .author-dot { background: #07c160; box-shadow: 0 0 8px #07c160; }
"""

_QUOTE_ICON_SVG = (
    '<svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M4.583 17.321C3.553 16.227 3 15 3 13.011c0-3.5 2.457-6.637 6.03-8.188l.893 1.378c-3.335 1.804-3.987 4.145-4.247 5.621.537-.278 1.24-.375 1.929-.311 1.804.167 3.226 1.648 3.226 3.489a3.5 3.5 0 0 1-3.5 3.5c-1.073 0-2.099-.49-2.748-1.179zm10 0C13.553 16.227 13 15 13 13.011c0-3.5 2.457-6.637 6.03-8.188l.893 1.378c-3.335 1.804-3.987 4.145-4.247 5.621.537-.278 1.24-.375 1.929-.311 1.804.167 3.226 1.648 3.226 3.489a3.5 3.5 0 0 1-3.5 3.5c-1.073 0-2.099-.49-2.748-1.179z"/>'
    "</svg>"
)

_VERIFY_BADGE_SVG = (
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#07c160" stroke-width="2.5" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>'
)


def build_cover_meta(theme_id: str, title: str = "", digest: str = "",
                     author: str = "", tags=None) -> Dict[str, str]:
    """
    汇聚文章元数据与主题预设，生成封面渲染所需的完整 meta
    与 Web Studio extractCoverMeta 保持一致的截断上限 (标题 36 / 摘要 60 / 作者 16 / 标签 24)
    """
    preset = THEME_COVER_PRESETS.get(theme_id, THEME_COVER_PRESETS["tech-blue"])
    tag = " · ".join(tags) if isinstance(tags, list) and tags else preset["defaultTag"]
    return {
        "title": (title or "在喧嚣时代重塑深度思考").strip()[:36],
        "digest": (digest or "真正的专注，是在充满干扰的世界中守住内心的秩序").strip()[:60],
        "author": (author or "野生宝藏箱").strip()[:16],
        "tag": tag.strip()[:24],
        "badge": preset["badgeText"],
        "vol": preset["volText"],
    }


def _build_banner_inner_html(theme_id: str, meta: Dict[str, str]) -> str:
    """构建 2.35:1 Banner 内部画布节点"""
    esc = lambda k: html.escape(str(meta.get(k, "")), quote=True)  # noqa: E731
    term_controls = ""
    if theme_id == "terminal-geek":
        term_controls = (
            '<div class="term-window-controls">'
            '<span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span>'
            f'<span class="term-prompt-title">bash - md2wx-article.sh (80x24)</span>'
            "</div>"
        )
    wechat_badge = ""
    if theme_id == "wechat-green":
        wechat_badge = f'<span class="wechat-verify-badge">{_VERIFY_BADGE_SVG}<span>官方认证排版</span></span>'

    return f"""<div class="cover-canvas cover-theme-{html.escape(theme_id)} ratio-banner">
  {term_controls}
  <div class="cover-inner">
    <div class="banner-top-bar">
      <div class="top-left">
        <span class="cover-badge">{esc("badge")}</span>
        <span class="cover-tag-banner">{esc("tag")}</span>
      </div>
      <div class="top-right">
        <span class="cover-vol">{esc("vol")}</span>
      </div>
    </div>
    <div class="banner-body">
      <div class="banner-left-col">
        <div class="headline-indicator"></div>
        <h1 class="banner-main-title">{esc("title")}</h1>
        <div class="banner-left-meta">
          <span class="banner-author-pill">{esc("author")}</span>
          {wechat_badge}
        </div>
      </div>
      <div class="banner-right-card">
        <div class="card-quote-icon">{_QUOTE_ICON_SVG}</div>
        <p class="banner-digest">{esc("digest")}</p>
        <div class="card-signature">&mdash; {esc("author")}</div>
      </div>
    </div>
  </div>
</div>"""


def _build_square_inner_html(theme_id: str, meta: Dict[str, str]) -> str:
    """构建 1:1 Square 方图内部画布节点"""
    esc = lambda k: html.escape(str(meta.get(k, "")), quote=True)  # noqa: E731
    term_controls = ""
    if theme_id == "terminal-geek":
        term_controls = (
            '<div class="term-window-controls">'
            '<span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span>'
            f'<span class="term-prompt-title">bash - md2wx-article.sh (80x24)</span>'
            "</div>"
        )
    wechat_badge = ""
    if theme_id == "wechat-green":
        wechat_badge = f'<span class="wechat-verify-badge">{_VERIFY_BADGE_SVG}<span>官方认证排版</span></span>'

    return f"""<div class="cover-canvas cover-theme-{html.escape(theme_id)} ratio-square">
  {term_controls}
  <div class="cover-inner">
    <div class="square-top-bar">
      <span class="cover-badge">{esc("badge")}</span>
      <span class="cover-vol">{esc("vol")}</span>
    </div>
    <div class="square-content-box">
      <div class="cover-category-chip">{esc("tag")}</div>
      <h1 class="square-main-title">{esc("title")}</h1>
      <p class="square-digest">{esc("digest")}</p>
    </div>
    <div class="square-bottom-bar">
      <div class="author-wrap">
        <div class="author-dot"></div>
        <span class="author-name">{esc("author")}</span>
        {wechat_badge}
      </div>
    </div>
  </div>
</div>"""


def build_cover_html(theme_id: str, meta: Dict[str, str], ratio: str = "banner") -> str:
    """
    构建自包含封面 HTML
    ratio="banner": 横版 2.35:1 Banner 版式 (1175x500)
    ratio="square": 方图 1:1 次条/方图版式 (500x500)
    ratio="dual":   双图左右合拼画板 (1675x500)
    """
    if ratio == "dual":
        return build_dual_cover_html(theme_id, meta)
    inner = _build_square_inner_html(theme_id, meta) if ratio == "square" else _build_banner_inner_html(theme_id, meta)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>{_COVER_CSS}</style>
</head>
<body>
{inner}
</body>
</html>"""


def build_dual_cover_html(theme_id: str, meta: Dict[str, str]) -> str:
    """
    构建双图并排合拼画板 HTML (1675x500 逻辑尺寸，左侧 2.35:1 头条 + 右侧 1:1 方图)
    2x 设备像素比采样输出即为标准的 3350x1000 高清合图
    """
    banner_html = _build_banner_inner_html(theme_id, meta)
    square_html = _build_square_inner_html(theme_id, meta)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>{_COVER_CSS}</style>
</head>
<body>
<div class="cover-canvas-dual">
  {banner_html}
  {square_html}
</div>
</body>
</html>"""


def find_headless_browser() -> Optional[str]:
    """
    探测系统可用的 Chrome 内核无头浏览器
    优先级: MD2WX_BROWSER 环境变量 > macOS /Applications 常见浏览器 > Linux/Win PATH 查找
    """
    candidates = []
    env_browser = os.environ.get("MD2WX_BROWSER")
    if env_browser:
        candidates.append(env_browser)

    if sys.platform == "darwin":
        for app in ("Google Chrome", "Microsoft Edge", "Chromium", "Brave Browser",
                    "Google Chrome Dev", "Google Chrome Canary", "Arc"):
            candidates.append(f"/Applications/{app}.app/Contents/MacOS/{app}")
    else:
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                     "microsoft-edge", "msedge", "chrome"):
            found = shutil.which(name)
            if found:
                candidates.append(found)

    for c in candidates:
        # 兼容传入裸命令名 (PATH 查找) 与绝对路径两种形式
        resolved = shutil.which(c) or c
        if os.path.isfile(resolved) and os.access(resolved, os.X_OK):
            return resolved
    return None


def _render_html_to_png(html_content: str, width: int, height: int,
                        out_path: Path, scale: int = 2) -> bool:
    """
    借助无头浏览器将 HTML 内容渲染并导出为 PNG 截图
    采用独立临时 user-data-dir 与稳定轮询退出机制，严防卡死与配置文件锁冲突
    """
    browser = find_headless_browser()
    if not browser:
        return False

    out_path.parent.mkdir(parents=True, exist_ok=True)
    html_path = ""
    profile_dir = ""
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(html_content)
            html_path = f.name

        profile_dir = tempfile.mkdtemp(prefix="md2wx-chrome-profile-")
        cmd = [
            browser,
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            "--virtual-time-budget=1500",
            f"--user-data-dir={profile_dir}",
            f"--window-size={width},{height}",
            f"--force-device-scale-factor={scale}",
            f"--screenshot={out_path}",
            f"file://{html_path}",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.time() + 30
            last_size = -1
            while time.time() < deadline:
                if proc.poll() is not None:
                    break
                if out_path.exists():
                    size = out_path.stat().st_size
                    if size > 0 and size == last_size:
                        break
                    last_size = size
                time.sleep(0.25)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()

        return out_path.exists() and out_path.stat().st_size > 0
    except Exception:
        return False
    finally:
        for p in (html_path, profile_dir):
            if p:
                try:
                    os.remove(p) if p.endswith(".html") else shutil.rmtree(p, ignore_errors=True)
                except Exception:
                    pass


def render_article_cover_png(theme_id: str, title: str = "", digest: str = "",
                             author: str = "", tags=None, ratio: str = "banner") -> Optional[str]:
    """
    渲染文章专属单版主题封面 (默认输出 2350x1000 PNG，2x 采样自 1175x500 逻辑画布)
    相同内容 (主题/比例/标题/摘要/作者/标签一致) 命中本地缓存直接复用
    返回 PNG 绝对路径；无可用无头浏览器或截图失败时返回 None
    """
    meta = build_cover_meta(theme_id, title=title, digest=digest, author=author, tags=tags)

    fingerprint = hashlib.md5(
        json.dumps({"theme": theme_id, "ratio": ratio, **meta}, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    cache_dir = Path.home() / ".config" / "md2wx" / "covers"
    out_path = cache_dir / f"cover-{theme_id}-{ratio}-{fingerprint}.png"
    if out_path.exists() and out_path.stat().st_size > 0:
        return str(out_path)

    w = SQUARE_COVER_WIDTH if ratio == "square" else COVER_WIDTH
    h = SQUARE_COVER_HEIGHT if ratio == "square" else COVER_HEIGHT
    html_content = build_cover_html(theme_id, meta, ratio=ratio)

    if _render_html_to_png(html_content, w, h, out_path, scale=2):
        return str(out_path)
    return None


def render_article_dual_cover_png(theme_id: str, title: str = "", digest: str = "",
                                  author: str = "", tags=None) -> Optional[tuple]:
    """
    渲染微信草稿箱推荐双封面合拼图 (3350x1000 PNG，左侧 2350x1000 头条 + 右侧 1000x1000 方图)
    相同内容命中本地缓存直接复用，不重复渲染
    返回三元组: (PNG绝对路径, pic_crop_235_1裁剪坐标, pic_crop_1_1裁剪坐标)
    无可用浏览器或渲染失败时返回 None
    """
    meta = build_cover_meta(theme_id, title=title, digest=digest, author=author, tags=tags)

    fingerprint = hashlib.md5(
        json.dumps({"theme": theme_id, "mode": "dual", **meta}, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    cache_dir = Path.home() / ".config" / "md2wx" / "covers"
    out_path = cache_dir / f"cover-dual-{theme_id}-{fingerprint}.png"

    if out_path.exists() and out_path.stat().st_size > 0:
        return str(out_path), WECHAT_CROP_235_1, WECHAT_CROP_1_1

    html_content = build_dual_cover_html(theme_id, meta)
    if _render_html_to_png(html_content, DUAL_COVER_WIDTH, DUAL_COVER_HEIGHT, out_path, scale=2):
        return str(out_path), WECHAT_CROP_235_1, WECHAT_CROP_1_1
    return None


def stitch_cover_images(banner_path: str, square_path: str) -> Optional[str]:
    """
    将用户指定的两张本地封面图 (头条横版 + 次条方图) 左右拼接为微信合拼封面图 (3350x1000)
    优先使用 PIL 高保真重采样；若无 PIL 则借助 Chrome 无头浏览器原生排版截图，保证零外部硬依赖
    返回拼接后的 PNG 绝对路径；失败时返回 None
    """
    b_path = Path(banner_path).resolve()
    s_path = Path(square_path).resolve()
    if not b_path.exists() or not s_path.exists():
        return None

    cache_dir = Path.home() / ".config" / "md2wx" / "covers"
    cache_dir.mkdir(parents=True, exist_ok=True)
    mtime_sig = f"{b_path}:{b_path.stat().st_mtime}:{s_path}:{s_path.stat().st_mtime}"
    sig = hashlib.md5(mtime_sig.encode("utf-8")).hexdigest()[:16]
    out_path = cache_dir / f"stitched-{sig}.png"
    if out_path.exists() and out_path.stat().st_size > 0:
        return str(out_path)

    # 1. 尝试使用 PIL 快速合成
    try:
        from PIL import Image, ImageOps
        with Image.open(b_path) as im_b, Image.open(s_path) as im_s:
            im_b_rgb = im_b.convert("RGB")
            im_s_rgb = im_s.convert("RGB")
            resample_filter = getattr(Image, "Resampling", Image).LANCZOS
            fit_b = ImageOps.fit(im_b_rgb, (2350, 1000), method=resample_filter)
            fit_s = ImageOps.fit(im_s_rgb, (1000, 1000), method=resample_filter)
            canvas = Image.new("RGB", (3350, 1000), (0, 0, 0))
            canvas.paste(fit_b, (0, 0))
            canvas.paste(fit_s, (2350, 0))
            canvas.save(out_path, format="PNG")
            return str(out_path)
    except Exception:
        pass

    # 2. 无 PIL 时的无头浏览器纯原生拼接兜底
    stitch_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ background: #000000; overflow: hidden; }}
.stitch-box {{ display: flex; flex-direction: row; width: 1675px; height: 500px; }}
.stitch-banner {{ width: 1175px; height: 500px; object-fit: cover; display: block; }}
.stitch-square {{ width: 500px; height: 500px; object-fit: cover; display: block; }}
</style>
</head>
<body>
<div class="stitch-box">
  <img class="stitch-banner" src="{b_path.as_uri()}">
  <img class="stitch-square" src="{s_path.as_uri()}">
</div>
</body>
</html>"""
    if _render_html_to_png(stitch_html, DUAL_COVER_WIDTH, DUAL_COVER_HEIGHT, out_path, scale=2):
        return str(out_path)
    return None


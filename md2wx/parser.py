"""
MD2WX Markdown -> 微信公众号专用内联 HTML 转换引擎
支持多主题视觉组件化渲染策略 (对标 WePost 卡片级排版质感)
"""
import re
from typing import Dict, Tuple, Optional, List, Any
from urllib.parse import unquote, urlparse
from .themes import get_theme
from .highlighter import highlight_code

def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """解析并剥离 Markdown 顶部的 YAML Frontmatter"""
    meta: Dict[str, Any] = {}
    # 统一换行符，避免 CRLF 编辑的文档解析异常
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    body = normalized
    # 仅当首行严格为 '---' 时才视为 Frontmatter，避免正文以 --- 分隔线开头被误判
    if normalized.startswith("---\n") or normalized == "---":
        closing = re.search(r"^---\s*$", normalized[4:], re.MULTILINE)
        if closing:
            fm_text = normalized[4:4 + closing.start()].strip()
            candidate_meta: Dict[str, Any] = {}
            for line in fm_text.split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if v.startswith("[") and v.endswith("]"):
                        tags = [t.strip().strip("'\"") for t in v[1:-1].split(",") if t.strip()]
                        candidate_meta[k] = tags
                    else:
                        candidate_meta[k] = v
            # 只有解析出至少一条元数据才认定为 Frontmatter，否则按普通正文处理
            if candidate_meta:
                meta = candidate_meta
                body = normalized[4 + closing.end():].lstrip("\n")
    return meta, body

def extract_quote_text(md_text: str, max_len: int = 120) -> str:
    """提取正文第一个引言块 (>) 内容作为摘要候选，剥离行内 Markdown 修饰符，无引言时返回空串"""
    m = re.search(r"^>\s*(.+)$", md_text, re.MULTILINE)
    if not m:
        return ""
    return re.sub(r"[`*_]", "", m.group(1)).strip()[:max_len]

def strip_markdown(md_text: str, max_len: int = 120) -> str:
    """剥离 Markdown 符号生成纯文本摘要 (Digest)"""
    text = re.sub(r'!\[.*?\]\(.*?\)', '', md_text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'[`#*_\->|]', '', text)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    plain = " ".join(lines)
    return plain[:max_len].strip()

# ------------------------------------------------------------------------------
# Obsidian wiki 图片语法归一化
# Obsidian 本地插图使用 ![[文件名]] 嵌入语法 (裸链接形态 [[文件名]])，而 MD2WX 图片管道
# 仅识别标准 Markdown ![alt](path)。这里先做一次纯字符串归一化，把 wiki 图片转换为标准
# 语法，从而无缝复用既有 inline/块级图片、image_map 换链、外链检测与 lint 全链路。
# ------------------------------------------------------------------------------
_OBSIDIAN_IMG_EXTS = frozenset({
    "png", "jpg", "jpeg", "gif", "webp", "bmp", "svg",
    "avif", "tiff", "tif", "ico", "heic",
})
_OBSIDIAN_WIKI_RE = re.compile(r"(!?)\[\[([^\[\]]+?)\]\]")
_INLINE_CODE_RE = re.compile(r"(`+)((?:(?!\1)[\s\S])+?)\1")
_WIKI_SIZE_RE = re.compile(r"^\d+(?:\s*x\s*\d+)?$", re.IGNORECASE)

def _wiki_target_is_image(target: str) -> bool:
    """目标是否带图片扩展名 (png/jpg/...)，用于甄别裸链接 [[x]] 是否为图片"""
    ext = target.rpartition(".")[2].lower()
    return bool(ext) and ext in _OBSIDIAN_IMG_EXTS

def _wiki_to_md_image(match: "re.Match") -> str:
    """单条 wiki 语法 -> 标准 Markdown 图片；非图片 (如笔记链接) 原样返回"""
    forced = match.group(1) == "!"          # ![[...]] 一律视为图片嵌入
    target, _, alias = match.group(2).partition("|")
    target = target.strip()
    alias = alias.strip()
    if not target:
        return match.group(0)
    if not forced and not _wiki_target_is_image(target):
        return match.group(0)               # 裸 [[某篇笔记]] 等非图片链接保持原样
    # Obsidian 的 |100 / |100x200 是尺寸而非别名，标准 Markdown 无宽度语义，丢弃
    alt = "" if _WIKI_SIZE_RE.match(alias) else alias
    src = target.replace(" ", "%20")        # 现有图片正则组不支持空格，转义后下游 unquote 还原
    return f"![{alt}]({src})"

def expand_obsidian_images(md_text: str) -> str:
    """
    将 Obsidian wiki 图片语法归一化为标准 Markdown 图片语法 (幂等)：
      ![[arch.png]]        -> ![](arch.png)
      ![[arch.png|说明]]    -> ![说明](arch.png)
      ![[arch.png|100]]     -> ![](arch.png)          (数字别名按尺寸丢弃)
      ![[my image.png]]     -> ![](my%20image.png)     (空格转义，下游 unquote 还原)
      [[arch.png]]          -> ![](arch.png)           (裸链接仅图片扩展名才转)
    跳过围栏代码块与行内代码，避免误伤示例文本中的字面量。
    """
    def _convert(part: str) -> str:
        """转换普通文本段，行内代码片段原样保留 (与 format_inline 的 save_code 同款切分)"""
        out: List[str] = []
        pos = 0
        for m in _INLINE_CODE_RE.finditer(part):
            out.append(_OBSIDIAN_WIKI_RE.sub(_wiki_to_md_image, part[pos:m.start()]))
            out.append(m.group(0))
            pos = m.end()
        out.append(_OBSIDIAN_WIKI_RE.sub(_wiki_to_md_image, part[pos:]))
        return "".join(out)

    segments = re.split(r"(```.*?```|~~~.*?~~~)", md_text, flags=re.DOTALL)
    return "".join(
        seg if seg.startswith("```") or seg.startswith("~~~") else _convert(seg)
        for seg in segments
    )

# 微信官方图片 CDN 域名 (外链图片检测白名单，这些域名之外的图片会被微信编辑器封禁)
WECHAT_CDN_HOSTS = ("mmbiz.qpic.cn", "mmbiz.wpimg.cn")

def collect_external_image_urls(md_text: str) -> List[str]:
    """
    收集正文 Markdown 中的外链图片 URL (http/https 且非微信官方 CDN)。
    微信编辑器会封禁外站图床的图片，调用方应提示用户转存或自动换链。
    跳过代码围栏段避免误报示例代码中的链接；按出现顺序去重。
    """
    md_text = expand_obsidian_images(md_text)
    urls: List[str] = []
    seen = set()
    segments = re.split(r"(```.*?```|~~~.*?~~~)", md_text, flags=re.DOTALL)
    for seg in segments:
        if seg.startswith("```") or seg.startswith("~~~"):
            continue
        for m in re.finditer(r'!\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)', seg):
            src = unquote(m.group(1))
            if not src.lower().startswith(("http://", "https://")):
                continue
            host = urlparse(src).netloc.lower()
            if any(h in host for h in WECHAT_CDN_HOSTS):
                continue
            if src not in seen:
                seen.add(src)
                urls.append(src)
    return urls

def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """6/3 位十六进制颜色转 rgba() 字符串；非法输入原样返回"""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return hex_color
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return hex_color
    return f"rgba({r}, {g}, {b}, {alpha})"

def _entity_safe_escape(seg: str) -> str:
    """
    转义普通文本中的 HTML 敏感字符，但放过已是 HTML 实体的 &name; / &#123; / &#xAB;，
    避免用户手写的实体被二次转义后按字面显示
    """
    seg = re.sub(r"&(?!(?:[a-zA-Z][a-zA-Z0-9]*|#[0-9]+|#x[0-9a-fA-F]+);)", "&amp;", seg)
    return seg.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

# 允许放行的微信安全行内 HTML 标签（仅无属性形态；其余标签一律转义显示）
_HTML_WHITELIST_RE = re.compile(r"&lt;(/?)\s*(br|b|strong|em|u|s|sub|sup|mark)\s*(/?)\s*&gt;", re.IGNORECASE)

def _unescape_whitelist_html(text: str) -> str:
    return _HTML_WHITELIST_RE.sub(lambda m: f"<{m.group(1)}{m.group(2).lower()}{m.group(3)}>", text)

def preprocess_lines(lines: List[str]) -> Tuple[List[str], Dict[str, Dict[str, str]], Dict[str, str]]:
    """
    Stage A 预扫描：收集参考式链接定义 [ref]: url 与脚注定义 [^id]: text，
    定义行从正文行流中移除（不渲染）。围栏代码块内的同名行不视为定义。
    ref label 大小写不敏感；重复定义首个生效 (CommonMark 规则)。
    脚注定义 V1 仅支持单行正文（多行延续按普通段落处理）。
    """
    ref_defs: Dict[str, Dict[str, str]] = {}
    footnote_defs: Dict[str, str] = {}
    keep: List[str] = []
    fence_ch = ""
    fence_len = 0
    for line in lines:
        stripped = line.strip()
        fence_m = re.match(r"^(`{3,}|~{3,})", stripped)
        if fence_m:
            if not fence_ch:
                fence_ch, fence_len = fence_m.group(1)[0], len(fence_m.group(1))
            elif fence_m.group(1)[0] == fence_ch and len(fence_m.group(1)) >= fence_len:
                fence_ch = ""
            keep.append(line)
            continue
        if not fence_ch:
            fn_m = _FOOTNOTE_DEF_RE.match(line)
            if fn_m:
                fid = fn_m.group(1).strip().lower()
                if fid and fid not in footnote_defs:
                    footnote_defs[fid] = fn_m.group(2).strip()
                continue
            ref_m = _REF_DEF_RE.match(line)
            if ref_m:
                label = ref_m.group(1).strip().lower()
                if label and label not in ref_defs:
                    ref_defs[label] = {"url": ref_m.group(2), "title": ref_m.group(3) or ""}
                continue
        keep.append(line)
    return keep, ref_defs, footnote_defs

_REF_DEF_RE = re.compile(r"^ {0,3}\[([^^\]]+)\]:\s*<?([^\s>]+)>?(?:\s+[\"\'(](.+?)[\"\')])?\s*$")
_FOOTNOTE_DEF_RE = re.compile(r"^ {0,3}\[\^([^\]]+)\]:\s?(.*)$")

def format_inline(
    text: str,
    accent: str,
    code_font_size: str = "13.5px",
    footnotes: Optional[List[Dict[str, str]]] = None,
    url_footnotes: bool = True,
    ref_defs: Optional[Dict[str, Dict[str, str]]] = None,
    footnote_defs: Optional[Dict[str, str]] = None,
    accent_bg: Optional[str] = None,
) -> str:
    """
    统一解析行内 Markdown 语法 (CommonMark + GFM + 常用扩展)：
    1. 保护行内代码（含双反引号）与反斜杠转义字符；
    2. 行内/参考式图片、尖括号自动链接、超链接、参考式链接、脚注引用、裸 URL；
    3. 实体安全转义 + 微信安全 HTML 白名单放行；
    4. 加粗（**/__）、斜体（*/_）、删除线、==高亮==；
    5. 彻底递归还原所有 Tokens，杜绝控制字符 \x00 导致的截断。

    footnotes: 文末脚注收集器 (None = URL 渲染为锚点而非脚注)；
    url_footnotes: False 时 URL 一律渲染锚点 (link_to_footnote=False 场景)；
    ref_defs: 参考式链接定义表 (预扫描产出，label 小写为键)；
    footnote_defs: [^id] 脚注定义表 (预扫描产出)；
    accent_bg: ==高亮== 背景色 (缺省时由 accent 派生半透明色)。
    """
    tokens: Dict[str, str] = {}
    token_idx = 0

    # 脚注编号统一分配 (URL 脚注与 [^id] 文本脚注共用一个有序列表)
    footnote_num = footnotes if footnotes is not None else []

    def save_token(prefix: str, value: str) -> str:
        nonlocal token_idx
        k = f"@@{prefix}_{token_idx}@@"
        token_idx += 1
        tokens[k] = value
        return k

    def esc_basic(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    def footnote_sup(f_num: int, label_html: str = "") -> str:
        label_part = f'<span style="color: {accent}; font-weight: 500;">{label_html}</span>' if label_html else ""
        return (
            f'{label_part}<sup style="font-size: 11px; color: {accent}; margin-left: 2px; '
            f'font-weight: bold; vertical-align: super;">[{f_num}]</sup>'
        )

    def register_url_footnote(url: str, label: str) -> int:
        match_idx = -1
        for idx, item in enumerate(footnote_num):
            if item.get("url") == url:
                match_idx = idx
                break
        if match_idx == -1:
            footnote_num.append({"label": label, "url": url, "kind": "url"})
            return len(footnote_num)
        return match_idx + 1

    # 1. 保护并转义行内代码 `...` 与 ``...``（双反引号可内含单反引号，内容首尾各剥离一个空格）
    def save_code(m: "re.Match") -> str:
        raw = m.group(2)
        if len(raw) >= 2 and raw.startswith(" ") and raw.endswith(" "):
            raw = raw[1:-1]
        return save_token(
            "MDCODE",
            f'<code style="background: rgba(0,0,0,0.06); padding: 2px 6px; border-radius: 4px; '
            f'font-size: {code_font_size}; color: {accent}; font-family: monospace;">{esc_basic(raw)}</code>',
        )

    text = re.sub(r"(`+)((?:(?!\1)[\s\S])+?)\1", save_code, text)

    # 1.5 反斜杠转义：\x 的下一字符按字面输出，且不参与后续任何格式化
    def save_escape(m: "re.Match") -> str:
        return save_token("MDESC", esc_basic(m.group(1)))

    text = re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~])", save_escape, text)

    # 2. 图片：参考式 ![alt][ref] 与行内 ![alt](src "title")
    #    必须先于链接解析，否则 [alt](src) 部分会先被链接正则吞掉
    def _inline_img_html(alt: str, src: str) -> str:
        return (
            f'<img src="{src.replace(chr(34), "&quot;")}" alt="{esc_basic(alt)}" '
            f'style="max-width: 96%; height: auto; border-radius: 8px; display: inline-block;" />'
        )

    def save_ref_image(m: "re.Match") -> str:
        if not ref_defs:
            return m.group(0)
        d = ref_defs.get(m.group(2).strip().lower()) or ref_defs.get(m.group(1).strip().lower())
        if not d:
            return m.group(0)
        return save_token("MDIMG", _inline_img_html(m.group(1), d["url"]))

    text = re.sub(r"!\[([^\]]*)\]\[([^\]]*)\]", save_ref_image, text)

    def save_image(m: "re.Match") -> str:
        return save_token("MDIMG", _inline_img_html(m.group(1), m.group(2)))

    text = re.sub(r"!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)", save_image, text)

    # 2.2 尖括号自动链接：<https://...> 剥尖括号交给裸 URL 步骤；<mail@...> 转脚注/锚点
    text = re.sub(r"<(https?://[^\s<>]+)>", r"\1", text)

    def save_mail(m: "re.Match") -> str:
        addr = m.group(1)
        url = f"mailto:{addr}"
        if footnotes is not None and url_footnotes:
            f_num = register_url_footnote(url, addr)
            return save_token("MDMAIL", footnote_sup(f_num, addr))
        return save_token("MDMAIL", f'<a href="{url}" style="color: {accent}; text-decoration: none; border-bottom: 1px dashed {accent};">{addr}</a>')

    text = re.sub(r"<([\w.+-]+@[\w-]+\.[\w.-]+)>", save_mail, text)

    # 3. 保护超链接 [...](...)
    def save_link(m: "re.Match") -> str:
        raw_label = m.group(1)
        esc_label = esc_basic(raw_label)

        # 立即展开 label 中嵌套的已有 code token
        for tk, tv in tokens.items():
            if tk in esc_label:
                esc_label = esc_label.replace(tk, tv)

        url = m.group(2).replace('"', "&quot;")

        # 处理本地 file:/// 协议，重定向至 GitHub 仓库对应源码或安全 URL，防止微信安全拦截
        if url.startswith("file:///"):
            if "MD2WX" in url:
                sub_path = url.split("MD2WX/")[-1]
                url = f"https://github.com/zaneven/MD2WX/blob/main/{sub_path}"
            else:
                url = "https://github.com/zaneven/MD2WX"

        if footnotes is not None and url_footnotes and not url.startswith("#"):
            f_num = register_url_footnote(url, esc_label)
            return save_token("MDLINK", footnote_sup(f_num, esc_label))
        return save_token("MDLINK", f'<a href="{url}" style="color: {accent}; text-decoration: none; border-bottom: 1px dashed {accent};">{esc_label}</a>')

    text = re.sub(r"\[(.*?)\]\((.*?)\)", save_link, text)

    # 3.2 参考式链接 [text][ref] / 折叠式 [ref]（定义由预扫描收集，未解析时保持字面）
    def save_ref_link(m: "re.Match") -> str:
        if not ref_defs:
            return m.group(0)
        label = m.group(1)
        ref = (m.group(2) if m.lastindex and m.lastindex >= 2 and m.group(2) else label).strip().lower()
        d = ref_defs.get(ref)
        if not d:
            return m.group(0)
        return save_link(re.match(r"\[(.*?)\]\((.*)\)", f"[{label}]({d['url']})"))

    text = re.sub(r"\[([^\]]+)\]\[([^\]]*)\]", save_ref_link, text)
    text = re.sub(r"\[([^\]\[\s]+)\](?![\(\[])", save_ref_link, text)

    # 3.3 脚注引用 [^id]：编号按首次引用顺序并入文末脚注区 (定义由预扫描收集)
    def save_footnote_ref(m: "re.Match") -> str:
        if not footnote_defs:
            return m.group(0)
        fid = m.group(1).strip().lower()
        if fid not in footnote_defs:
            return m.group(0)
        key = f"@@FN:{fid}@@"
        match_idx = -1
        for idx_, item in enumerate(footnote_num):
            if item.get("url") == key:
                match_idx = idx_
                break
        if match_idx == -1:
            footnote_num.append({"label": fid, "url": key, "kind": "text", "text": footnote_defs[fid]})
            f_num = len(footnote_num)
        else:
            f_num = match_idx + 1
        return save_token("MDFN", footnote_sup(f_num))

    text = re.sub(r"\[\^([^\]]+)\]", save_footnote_ref, text)

    # 3.5 自动链接：裸 http(s) URL 与 Markdown 链接同等待遇，自动转文末脚注
    #     (微信不支持外链跳转，遗漏的裸 URL 在正文点击同样会被阻断)
    _AUTOLINK_URL_RE = re.compile(r"https?://[^\s<>()\[\]\"']+[^\s<>()\[\]\"'.,;:!?]")

    def save_autolink(m: "re.Match") -> str:
        url = m.group(0)
        if footnotes is not None and url_footnotes:
            label = url if len(url) <= 60 else url[:57] + "..."
            f_num = register_url_footnote(url, label)
            return save_token("MDURL", footnote_sup(f_num, label))
        show_label = url if len(url) <= 60 else url[:57] + "..."
        return save_token("MDURL", f'<a href="{url}" style="color: {accent}; text-decoration: none; border-bottom: 1px dashed {accent};">{show_label}</a>')

    text = _AUTOLINK_URL_RE.sub(save_autolink, text)

    # 4. 对未受 token 保护的普通文本统一转义 HTML (实体安全，防双重转义)，
    #    并放行微信安全白名单行内标签，其余 <tag> 显示为字面文本
    text = "".join(
        seg if seg.startswith("@@MD")
        else _unescape_whitelist_html(_entity_safe_escape(seg))
        for seg in re.split(r"(@@MD[A-Z]+_\d+@@)", text)
    )

    # 5. 粗体与斜体 (** 与 __ / * 与 _，下划线形态词边界感知：词内 _ 不触发)
    text = re.sub(r"\*\*(?![\*\s])((?:[^*]|\*(?!\*))+?)(?<![\*\s])\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w\\])__(?!\s)((?:[^_]|_(?!_))+?)(?<!\s)__(?!\w)", r"<strong>\1</strong>", text)
    text = re.sub(r"(^|[^*])\*(?![\*\s])([^*\n]+?)(?<![\*\s])\*(?!\*)", r"\1<em>\2</em>", text)
    text = re.sub(r"(?<![`\w])_(?!\s)([^_\n]+?)(?<!\s)_(?!\w)", r"<em>\1</em>", text)

    # 5.5 GFM 删除线 ~text~ / ~~text~~ (del 标签在微信白名单内，内联样式保证不褪色)
    text = re.sub(
        r"(~{1,2})(?![\s~])((?:[^~]|~(?!~))+?)(?<![\s~])\1",
        rf'<del style="color: {accent}; opacity: 0.72;">\2</del>',
        text,
    )

    # 5.6 扩展高亮 ==text== (主题色荧光笔效果)
    mark_bg = accent_bg if accent_bg else _hex_to_rgba(accent, 0.15)
    text = re.sub(
        r"==(?!\s)([\s\S]+?)(?<!\s)==",
        rf'<mark style="background: {mark_bg}; padding: 1px 3px; border-radius: 3px;">\1</mark>',
        text,
    )

    # 6. 彻底还原保护的 tokens (支持多层嵌套展开)
    max_loops = 5
    while any(k in text for k in tokens) and max_loops > 0:
        for k, v in list(tokens.items()):
            if k in text:
                text = text.replace(k, v)
        max_loops -= 1

    # 7. 防御性消除任何残留的控制字符
    text = text.replace("\x00", "")

    return text

_CJK_CHAR_RE = re.compile(r"[一-鿿　-〿＀-￯]")

def _is_cjk_char(ch: str) -> bool:
    return bool(ch) and bool(_CJK_CHAR_RE.match(ch))

# 列表项标记：- * + 无序，N. / N) 有序
_LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]|\d{1,9}[.)])(\s+(.*))?$")

def join_paragraph_lines(buf: List[str], force_breaks: bool = False) -> str:
    """
    段落行合并 (CommonMark 软换行语义)：
    - 行尾 2+ 空格或单个反斜杠 = 硬换行，插入 @@MDBR_0@@ 占位 (行内解析后还原为 <br />)；
    - 普通软换行：相邻字符任一侧为 CJK/全角字符时直接拼接，否则以空格拼接。
    force_breaks=True 关掉软换行语义，行与行之间一律硬换行：引用块内作者手写的分行
    (开头的作者/标签/摘要等信息) 必须逐行保留，否则推送微信后会塌成一段。
    """
    parts: List[Tuple[bool, str]] = []
    for raw in buf:
        hard = False
        ln = raw
        if ln.endswith("  "):
            hard = True
            ln = ln.rstrip()
        elif ln.endswith("\\") and not ln.endswith("\\\\"):
            hard = True
            ln = ln[:-1].rstrip()
        else:
            ln = ln.rstrip()
        parts.append((hard, ln))
    result = ""
    for i, (hard, ln) in enumerate(parts):
        if i == 0:
            result = ln
            continue
        prev_ln = parts[i - 1][1]
        if parts[i - 1][0] or force_breaks:
            result += "@@MDBR_0@@" + ln
            continue
        prev_ch = prev_ln[-1:] if prev_ln else ""
        next_ch = ln[:1]
        if prev_ch and next_ch and (_is_cjk_char(prev_ch) or _is_cjk_char(next_ch)):
            result += ln
        else:
            result += " " + ln
    return result

def render_ordered_list_item(item_text: str, number: int, theme: dict) -> str:
    """渲染有序列表项 (保留源文档编号，与无序列表同一 flex 视觉骨架)"""
    accent = theme["accent"]
    text_color = theme["text_color"]
    return (
        f'<section style="display: flex; align-items: flex-start; margin-bottom: 8px; line-height: 1.75; font-size: 15.5px; color: {text_color};">'
        f'<span style="color: {accent}; margin-right: 8px; font-size: 15px; line-height: 1.75; font-weight: 700; min-width: 20px;">{number}.</span>'
        f'<span style="flex: 1;">{item_text}</span>'
        f'</section>'
    )

def render_h4(h4_text: str, theme: dict) -> str:
    """渲染四级小标题 (默认：左侧短竖条 + 缩小字号；主题可用 styles.h4 覆盖)"""
    accent = theme["accent"]
    page_bg = theme.get("page_bg", "#ffffff")
    is_dark = page_bg in ["#0b0f19", "#0f172a", "#18181b", "#09090b"]
    heading_color = "#f8fafc" if is_dark else "#18181b"
    return (
        f'<section style="margin: 20px 0 10px 0; line-height: 1.4; display: flex; align-items: center;">'
        f'<span style="display: inline-block; width: 3px; height: 14px; background: {accent}; border-radius: 2px; margin-right: 8px; flex-shrink: 0;"></span>'
        f'<span style="font-size: 15.5px; font-weight: 700; color: {accent};">{h4_text}</span>'
        f'</section>'
    )

def render_h5(h5_text: str, theme: dict) -> str:
    """渲染五级小标题 (默认：accent 短划前缀)"""
    accent = theme["accent"]
    page_bg = theme.get("page_bg", "#ffffff")
    is_dark = page_bg in ["#0b0f19", "#0f172a", "#18181b", "#09090b"]
    heading_color = "#f8fafc" if is_dark else "#18181b"
    return (
        f'<section style="margin: 18px 0 8px 0; line-height: 1.4;">'
        f'<span style="color: {accent}; margin-right: 6px; font-weight: 700;">—</span>'
        f'<span style="font-size: 15px; font-weight: 600; color: {heading_color};">{h5_text}</span>'
        f'</section>'
    )

def render_h6(h6_text: str, theme: dict) -> str:
    """渲染六级小标题 (默认：弱化的副色小字)"""
    sub_color = theme["sub_color"]
    return (
        f'<section style="margin: 16px 0 8px 0; line-height: 1.4;">'
        f'<span style="font-size: 14px; font-weight: 600; color: {sub_color}; letter-spacing: 0.5px;">{h6_text}</span>'
        f'</section>'
    )

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
            f'<section style="margin: 38px 0 26px 0; text-align: center;">'
            f'<section style="border-top: 1px solid {border_color}; border-bottom: 1px solid {border_color}; padding: 12px 14px; display: inline-block; min-width: 60%;">'
            f'<span style="font-size: 22px; font-weight: 700; color: {accent}; margin: 0; line-height: 1.4; letter-spacing: 1px; display: block;">{title_text}</span>'
            f'</section></section>'
        )
    elif style == "capsule":
        # 温暖便签/胶囊徽章风格
        return (
            f'<section style="margin: 36px 0 24px 0; text-align: center;">'
            f'<span style="display: inline-block; background: {accent}; color: #ffffff; padding: 9px 26px; border-radius: 30px; font-size: 20px; font-weight: 700; letter-spacing: 0.8px; box-shadow: 0 4px 14px rgba(0,0,0,0.12);">'
            f'{title_text}'
            f'</span></section>'
        )
    elif style == "terminal":
        # 极客终端命令行风格
        return (
            f'<section style="margin: 36px 0 24px 0; padding: 14px 18px; background: {code_bg}; border: 1px solid {border_color}; border-radius: 6px;">'
            f'<div style="color: {sub_color}; font-size: 12px; margin-bottom: 6px; font-family: monospace;">$ cat article.md</div>'
            f'<span style="font-size: 20px; font-weight: 700; color: {accent}; margin: 0; line-height: 1.4; font-family: monospace; display: block;">&gt; {title_text}</span>'
            f'</section>'
        )
    elif style == "brutalist":
        # 先锋野兽派硬框与硬阴影
        return (
            f'<section style="margin: 36px 0 24px 0; text-align: center;">'
            f'<section style="display: inline-block; background: {accent_bg}; border: 2.5px solid #000000; box-shadow: 4px 4px 0 #000000; padding: 10px 22px;">'
            f'<span style="font-size: 21px; font-weight: 800; color: #000000; margin: 0; letter-spacing: 1px; display: block;">{title_text}</span>'
            f'</section></section>'
        )
    else:
        # 默认：现代居中下划粗线 (underline)
        return (
            f'<section style="text-align: center; margin: 36px 0 22px 0;">'
            f'<span style="font-size: 23px; font-weight: 800; color: {title_color}; line-height: 1.4; letter-spacing: 0.5px; border-bottom: 3px solid {accent}; padding-bottom: 6px; display: inline-block;">'
            f'{title_text}'
            f'</span></section>'
        )

def render_h2(h2_text: str, theme: dict) -> str:
    """渲染二级分区标题 (使用微信免疫剥离的 section 容器)"""
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
            f'<section style="margin: 34px 0 16px 0;">'
            f'<span style="display: inline-block; background: {accent}; color: #ffffff; font-size: 16px; font-weight: 700; padding: 5px 15px; border-radius: 20px; letter-spacing: 0.5px;">'
            f'{h2_text}'
            f'</span></section>'
        )
    elif style == "bubble_bg":
        # 柔和底色块
        return (
            f'<section style="margin: 34px 0 16px 0;">'
            f'<span style="display: inline-block; background: {accent_bg}; color: {accent}; font-size: 17px; font-weight: 700; padding: 6px 14px; border-radius: 6px; border-left: 3px solid {accent};">'
            f'{h2_text}'
            f'</span></section>'
        )
    elif style == "serif_badge":
        # 古典报刊章节符号
        return (
            f'<section style="margin: 34px 0 16px 0; padding-bottom: 6px; border-bottom: 1px solid {border_color};">'
            f'<span style="color: {accent}; margin-right: 6px; font-family: Georgia, serif; font-size: 18.5px; font-weight: 700;">§</span>'
            f'<span style="font-size: 18.5px; font-weight: 700; color: {accent}; line-height: 1.4; letter-spacing: 0.5px;">{h2_text}</span>'
            f'</section>'
        )
    elif style == "terminal_prompt":
        # 极客终端命令风格
        return (
            f'<section style="margin: 32px 0 16px 0; font-family: monospace;">'
            f'<span style="color: {accent}; font-weight: 700; font-size: 18px; margin-right: 8px;">//</span>'
            f'<span style="display: inline; font-size: 17.5px; font-weight: 700; color: {text_color}; margin: 0; font-family: monospace;">{h2_text}</span>'
            f'</section>'
        )
    elif style == "brutalist_box":
        # 新野兽粗黑边框与硬投影
        return (
            f'<section style="margin: 34px 0 16px 0; text-align: left;">'
            f'<section style="display: inline-block; background: {accent_bg}; border: 2px solid #000000; box-shadow: 3px 3px 0 #000000; padding: 5px 14px;">'
            f'<span style="font-size: 17px; font-weight: 800; color: #000000; margin: 0; line-height: 1.4; display: block;">{h2_text}</span>'
            f'</section></section>'
        )
    elif style == "bottom_line":
        # 全宽底线
        return (
            f'<section style="margin: 34px 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid {accent};">'
            f'<span style="font-size: 18.5px; font-weight: 700; color: {heading_color}; line-height: 1.4; display: block;">{h2_text}</span>'
            f'</section>'
        )
    else:
        # 默认：左侧 4px 竖线条
        return (
            f'<section style="margin: 34px 0 16px 0; padding-left: 12px; border-left: 4px solid {accent};">'
            f'<span style="font-size: 19px; font-weight: 700; color: {heading_color}; line-height: 1.4; display: block;">{h2_text}</span>'
            f'</section>'
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
            f'<section style="margin: 24px 0 12px 0;">'
            f'<span style="display: inline-block; width: 8px; height: 8px; background: {accent}; border-radius: 2px; margin-right: 8px; vertical-align: middle;"></span>'
            f'<span style="font-size: 16.5px; font-weight: 600; color: {accent}; line-height: 1.4;">{h3_text}</span>'
            f'</section>'
        )
    elif style == "highlight_bg":
        # 荧光笔底纹
        return (
            f'<section style="margin: 24px 0 12px 0;">'
            f'<span style="background: linear-gradient(to top, {accent_bg} 45%, transparent 45%); padding: 1px 4px; font-size: 16.5px; font-weight: 600; color: {heading_color}; line-height: 1.4;">{h3_text}</span>'
            f'</section>'
        )
    elif style == "slash":
        # 极客双斜线
        return (
            f'<section style="margin: 24px 0 12px 0; font-family: monospace;">'
            f'<span style="color: {sub_color}; margin-right: 6px;">##</span>'
            f'<span style="font-size: 16px; font-weight: 600; color: {accent}; line-height: 1.4;">{h3_text}</span>'
            f'</section>'
        )
    else:
        # 默认：矢量四角星形（纯 SVG，无 Emoji）
        return (
            f'<section style="margin: 24px 0 12px 0; line-height: 1.4; display: flex; align-items: center;">'
            f'<svg width="14" height="14" viewBox="0 0 24 24" fill="{accent}" style="margin-right: 6px; flex-shrink: 0;"><polygon points="12 2 15 9 22 12 15 15 12 22 9 15 2 12 9 9"/></svg>'
            f'<span style="font-size: 16.5px; font-weight: 600; color: {accent};">{h3_text}</span>'
            f'</section>'
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

def _wechat_safe_line_structure(html_str: str) -> str:
    """
    将代码块 HTML 的换行结构改为微信自包含式：
    - 换行符 -> <br> (br 在微信标签白名单中永远保留，不依赖 pre 语义与 white-space CSS)
    - 空格   -> &nbsp; (缩进与 ASCII 树形对齐在任意净化策略下都不丢失)
    仅处理文本节点，标签与内联样式属性原样保留
    """
    parts = re.split(r"(<[^>]+>)", html_str)
    out = []
    for part in parts:
        if part.startswith("<"):
            out.append(part)
        else:
            out.append(part.replace("\n", "<br>").replace(" ", "&nbsp;"))
    return "".join(out)

def render_code(raw_code: str, code_lang: str, theme: dict) -> str:
    """渲染多行代码块并应用纯内联语法着色"""
    style = theme.get("code_style", theme.get("styles", {}).get("code", "mac_dark"))
    code_bg = theme["code_bg"]
    code_text = theme.get("code_text", "#e4e4e7")
    accent = theme["accent"]
    border_color = theme["border_color"]
    sub_color = theme["sub_color"]

    # 纯内联语法着色（微信后台不褪色），并把换行/空格转为微信白名单安全的自包含结构
    highlighted = _wechat_safe_line_structure(highlight_code(raw_code, code_lang))

    # 微信会剥离 pre 自身的 overflow-x，但放行 div/section 容器上的横向滚动
    # (与 render_table 的滚动容器同款策略)，由外层包裹层承载横向滑动
    code_scroll_open = f'<div style="overflow-x: auto; -webkit-overflow-scrolling: touch; background: {code_bg}; padding: 14px 16px;">'
    code_scroll_close = '</div>'

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
            f'{code_scroll_open}'
            f'<pre style="margin: 0; background: {code_bg}; color: {code_text}; font-size: 13.5px; line-height: 1.6; font-family: \'SF Mono\', SFMono-Regular, Menlo, Consolas, \'Liberation Mono\', \'Courier New\', monospace;"><code>{highlighted}</code></pre>'
            f'{code_scroll_close}'
            f'</div>'
        )
    elif style == "clean_flat":
        # 极简扁平圆角无指示灯
        return (
            f'<div style="margin: 22px 0; border-radius: 8px; overflow: hidden; border: 1px solid {border_color};">'
            f'{code_scroll_open}'
            f'<pre style="margin: 0; background: {code_bg}; color: {code_text}; font-size: 13.5px; line-height: 1.6; font-family: \'SF Mono\', SFMono-Regular, Menlo, Consolas, \'Liberation Mono\', \'Courier New\', monospace;"><code>{highlighted}</code></pre>'
            f'{code_scroll_close}'
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
            f'{code_scroll_open}'
            f'<pre style="margin: 0; background: {code_bg}; color: {code_text}; font-size: 13.5px; line-height: 1.6; font-family: \'SF Mono\', SFMono-Regular, Menlo, Consolas, \'Liberation Mono\', \'Courier New\', monospace;"><code>{highlighted}</code></pre>'
            f'{code_scroll_close}'
            f'</div>'
        )

def render_table(header: List[str], rows: List[List[str]], theme: dict, aligns: Optional[List[str]] = None) -> str:
    """渲染表格 (aligns: 分隔行冒号解析出的逐列对齐 left/center/right，缺省 left)"""
    aligns = aligns or []

    def col_align(col_idx: int) -> str:
        return aligns[col_idx] if col_idx < len(aligns) else "left"
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
            for h_idx, h in enumerate(header):
                table_html += f'<th style="padding: 10px 14px; font-weight: 700; color: {accent}; border-bottom: 1px solid {border_color}; text-align: {col_align(h_idx)};">{h}</th>'
            table_html += '</tr></thead>'
        table_html += '<tbody>'
        for row in rows:
            table_html += f'<tr style="border-bottom: 1px dashed {border_color};">'
            for c_idx, c in enumerate(row):
                c_fmt = format_inline(c, accent, "12.5px")
                table_html += f'<td style="padding: 10px 14px; color: {text_color}; line-height: 1.5; text-align: {col_align(c_idx)};">{c_fmt}</td>'
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
            for h_idx, h in enumerate(header):
                table_html += f'<th style="padding: 10px 14px; font-weight: 700; color: {accent}; border: 1px solid {border_color}; text-align: {col_align(h_idx)};">{h}</th>'
            table_html += '</tr></thead>'
        table_html += '<tbody>'
        for row in rows:
            table_html += f'<tr>'
            for c_idx, c in enumerate(row):
                c_fmt = format_inline(c, accent, "12.5px")
                table_html += f'<td style="padding: 10px 14px; color: {text_color}; line-height: 1.5; border: 1px solid {border_color}; text-align: {col_align(c_idx)};">{c_fmt}</td>'
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
            for h_idx, h in enumerate(header):
                table_html += f'<th style="padding: 11px 14px; font-weight: 600; color: {accent}; border-bottom: 2px solid {border_color}; text-align: {col_align(h_idx)};">{h}</th>'
            table_html += '</tr></thead>'
        table_html += '<tbody>'
        for r_idx, row in enumerate(rows):
            bg = td_bg_alt if r_idx % 2 == 1 else td_bg
            table_html += f'<tr style="background: {bg}; border-bottom: 1px solid {border_color};">'
            for c_idx, c in enumerate(row):
                c_fmt = format_inline(c, accent, "12.5px")
                table_html += f'<td style="padding: 10px 14px; color: {text_color}; line-height: 1.5; text-align: {col_align(c_idx)};">{c_fmt}</td>'
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

def render_task_item(item_text: str, checked: bool, theme: dict) -> str:
    """渲染 GFM 任务列表项 (纯 SVG 矢量勾选框，无 Emoji，微信兼容内联样式)"""
    accent = theme["accent"]
    text_color = theme["text_color"]

    if checked:
        checkbox = (
            f'<svg width="15" height="15" viewBox="0 0 24 24" style="vertical-align: -2px; flex-shrink: 0;">'
            f'<rect x="2" y="2" width="20" height="20" rx="5" fill="{accent}"/>'
            f'<path d="M7 12.5l3.2 3.2L17 9" fill="none" stroke="#ffffff" stroke-width="2.5" '
            f'stroke-linecap="round" stroke-linejoin="round"/></svg>'
        )
    else:
        checkbox = (
            f'<svg width="15" height="15" viewBox="0 0 24 24" style="vertical-align: -2px; flex-shrink: 0;">'
            f'<rect x="2.5" y="2.5" width="19" height="19" rx="5" fill="none" stroke="{accent}" stroke-width="2"/></svg>'
        )

    return (
        f'<section style="display: flex; align-items: flex-start; margin-bottom: 8px; line-height: 1.75; font-size: 15.5px; color: {text_color};">'
        f'<span style="margin-right: 7px; line-height: 1.75;">{checkbox}</span>'
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
        # 文艺星号组居中 (与 Web 端 parser.js 对齐，采用纯 SVG 三圆点矢量呈现)
        return f'<div style="text-align: center; margin: 32px 0; line-height: 1;"><svg width="60" height="12" viewBox="0 0 60 12" fill="{accent}" style="display: inline-block;"><circle cx="10" cy="6" r="3"/><circle cx="30" cy="6" r="3"/><circle cx="50" cy="6" r="3"/></svg></div>'
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

    return f'<section style="{container_style}">\n{body_html}\n</section>'

def render_wechat_article_header_cover(theme_id: str = "acid-bold", meta: dict = None) -> str:
    """生成可直接内嵌在微信公众号可复制正文顶部的富文本封面 HTML (自包含纯内联样式)"""
    if not meta:
        meta = {}
    safe_title = (meta.get("title") or "在喧嚣时代重塑深度思考").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    safe_digest = (meta.get("digest") or "真正的专注，是在充满干扰的世界中守住内心的秩序").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    safe_author = (meta.get("author") or "野生宝藏箱").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_tag = (meta.get("tag") or "深度架构 · 极客手记").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_badge = (meta.get("badge") or ("ACID BOLD" if theme_id == "acid-bold" else "TECH BLOG")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_vol = (meta.get("vol") or "2026 · V1.0.2 RELEASE").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    if theme_id == "acid-bold":
        return (
            f'<section style="margin: 0 0 28px 0; background: #fee500; border: 3.5px solid #000000; box-shadow: 6px 6px 0 #000000; padding: 26px 20px; box-sizing: border-box; text-align: left;">\n'
            f'  <section style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">\n'
            f'    <span style="background: #000000; color: #fee500; font-size: 13px; font-weight: 900; padding: 4px 12px; border-radius: 3px; letter-spacing: 1px;">{safe_badge}</span>\n'
            f'    <span style="font-size: 14px; font-weight: 900; color: #000000; font-family: monospace;">{safe_vol}</span>\n'
            f'  </section>\n'
            f'  <section style="width: 50px; height: 7px; background: #000000; margin-bottom: 14px;"></section>\n'
            f'  <section style="margin: 0 0 12px 0;"><span style="font-size: 25px; font-weight: 900; line-height: 1.28; color: #000000; letter-spacing: -0.3px; display: block;">{safe_title}</span></section>\n'
            f'  <p style="font-size: 16px; line-height: 1.6; color: #171717; margin: 0 0 18px 0; font-weight: 600;">{safe_digest}</p>\n'
            f'  <section style="border-top: 2.5px solid #000000; padding-top: 12px; display: flex; align-items: center; justify-content: space-between;">\n'
            f'    <span style="font-size: 14px; font-weight: 900; color: #000000;">{safe_author} // 先锋态度</span>\n'
            f'  </section>\n'
            f'</section>'
        )
    elif theme_id == "terminal-geek":
        return (
            f'<section style="margin: 0 0 28px 0; background: #020617; border: 1.5px solid #065f46; border-radius: 10px; overflow: hidden; box-sizing: border-box; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; text-align: left;">\n'
            f'  <section style="background: #090e1a; padding: 10px 14px; border-bottom: 1px solid #1e293b; display: flex; align-items: center;">\n'
            f'    <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #ef4444; margin-right: 6px;"></span>\n'
            f'    <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #f59e0b; margin-right: 6px;"></span>\n'
            f'    <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #10b981; margin-right: 12px;"></span>\n'
            f'    <span style="font-size: 12px; color: #64748b;">bash - post.sh ({safe_vol})</span>\n'
            f'  </section>\n'
            f'  <section style="padding: 24px 20px;">\n'
            f'    <div style="font-size: 13px; color: #10b981; font-weight: 800; margin-bottom: 10px;">&gt; ./render --theme=terminal</div>\n'
            f'    <section style="margin: 0 0 12px 0;"><span style="font-size: 24px; font-weight: 900; line-height: 1.32; color: #34d399; letter-spacing: 0.3px; display: block;">{safe_title}</span></section>\n'
            f'    <p style="font-size: 15.5px; line-height: 1.6; color: #a7f3d0; margin: 0 0 16px 0;">{safe_digest}</p>\n'
            f'    <section style="border-top: 1px solid #1e293b; padding-top: 12px; display: flex; align-items: center; justify-content: space-between;">\n'
            f'      <span style="font-size: 13px; color: #10b981; font-weight: 700;">// {safe_author}</span>\n'
            f'    </section>\n'
            f'  </section>\n'
            f'</section>'
        )
    else:
        # 默认科技蓝大卡片
        return (
            f'<section style="margin: 0 0 28px 0; border-radius: 12px; padding: 26px 20px; background: linear-gradient(135deg, #090d16 0%, #0f172a 50%, #1e293b 100%); border: 1px solid rgba(56, 189, 248, 0.2); box-shadow: 0 8px 24px rgba(0,0,0,0.15); box-sizing: border-box; text-align: left;">\n'
            f'  <section style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">\n'
            f'    <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-size: 13px; font-weight: 800; padding: 4px 12px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.3);">{safe_badge}</span>\n'
            f'    <span style="font-size: 13px; color: #94a3b8; font-family: monospace;">{safe_vol}</span>\n'
            f'  </section>\n'
            f'  <section style="width: 44px; height: 5px; background: #38bdf8; border-radius: 2px; margin-bottom: 14px;"></section>\n'
            f'  <section style="margin: 0 0 12px 0;"><span style="font-size: 25px; font-weight: 900; line-height: 1.3; color: #ffffff; display: block;">{safe_title}</span></section>\n'
            f'  <p style="font-size: 16px; line-height: 1.6; color: #cbd5e1; margin: 0 0 18px 0; font-weight: 500;">{safe_digest}</p>\n'
            f'  <section style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 12px; display: flex; align-items: center; justify-content: space-between;">\n'
            f'    <span style="font-size: 14px; font-weight: 800; color: #38bdf8;">{safe_author}</span>\n'
            f'  </section>\n'
            f'</section>'
        )

# ==============================================================================
# Markdown 解析主循环 (Parser Pipeline)
# ==============================================================================

def markdown_to_wechat_html(
    md_text: str,
    theme_name: str = "acid-bold",
    image_map: Optional[Dict[str, str]] = None,
    link_to_footnote: bool = True,
    insert_cover: bool = True,
    cover_meta: Optional[dict] = None,
    rich_blocks: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    将 Markdown 文本转换为微信公众号完美适配的纯 Inline CSS HTML
    支持指定主题名称或自定义 JSON 主题文件路径
    rich_blocks: 富文本块列表 (Mermaid/公式，由 richrender 预渲染)，
    块级 token 独占一行时直接落块，避免 <div> 嵌入 <p> 被微信净化破坏
    """
    # 0. Obsidian wiki 图片语法归一化 (幂等)：![[x.png]] -> ![](x.png)，
    #    使其复用后续 inline/块级图片与 image_map 换链管道
    md_text = expand_obsidian_images(md_text)

    # 块级富文本 token -> 渲染产物映射 (仅 display 块；行内公式仍走后置替换)
    rich_block_map: Dict[str, str] = {
        b["token"]: b.get("html", "")
        for b in (rich_blocks or [])
        if b.get("display", False)
    }
    theme = get_theme(theme_name)
    accent = theme["accent"]
    text_color = theme["text_color"]
    sub_color = theme["sub_color"]
    border_color = theme.get("border_color", "rgba(0,0,0,0.08)")

    typography = theme.get("typography", {})
    font_size_base = typography.get("font_size_base", "15.5px")
    line_height_base = typography.get("line_height_base", "1.8")
    letter_spacing = typography.get("letter_spacing", "0.4px")
    paragraph_indent = typography.get("paragraph_indent", False)
    indent_css = "text-indent: 2em; " if paragraph_indent else ""

    # 文末脚注收集器 (URL 脚注与 [^id] 文本脚注共用；URL 脚注开关由 url_footnotes 控制)
    footnotes: List[Dict[str, str]] = []

    # 1. 替换已上传到微信 CDN 的图片链接：
    #    仅精确替换 Markdown 图片语法中的 src，且跳过代码围栏段，
    #    避免裸 str.replace 污染代码块或误伤路径相似的普通文本。
    if image_map:
        from urllib.parse import unquote

        def _swap_image_token(m: "re.Match") -> str:
            raw_src = m.group(2)
            cdn_url = image_map.get(raw_src) or image_map.get(unquote(raw_src))
            return f'{m.group(1)}({cdn_url})' if cdn_url else m.group(0)

        img_token_re = re.compile(r'(!\[[^\]]*\])\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)')
        segments = re.split(r'(```.*?```|~~~.*?~~~)', md_text, flags=re.DOTALL)
        md_text = ''.join(
            seg if seg.startswith('```') or seg.startswith('~~~')
            else img_token_re.sub(_swap_image_token, seg)
            for seg in segments
        )

    lines, ref_defs, footnote_defs = preprocess_lines(md_text.split("\n"))
    html_parts = []

    # 微信公众号文章顶部自动嵌入当前主题专属封面卡片 (默认开启)
    if insert_cover and cover_meta:
        header_cover = render_wechat_article_header_cover(theme_name, cover_meta)
        if header_cover:
            html_parts.append(header_cover)

    # 块级渲染主循环 (嵌套引用会对内层行递归调用 render_block_lines)

    def render_block_lines(block_lines: List[str], force_breaks: bool = False) -> List[str]:
        # force_breaks: 引用块内层渲染，段内每行独立成行 (见 join_paragraph_lines)
        # 每层递归独立的块状态
        in_code_block = False
        code_lang = ""
        code_lines = []
        code_fence_ch = ""
        code_fence_len = 0
        in_table = False
        table_lines = []
        para_buf: List[str] = []

        def flush_table() -> str:
            nonlocal in_table, table_lines
            if not table_lines:
                return ""
            header = []
            rows = []
            aligns: List[str] = []
            for i, line in enumerate(table_lines):
                cells = [c.strip() for c in line.strip().strip("|").replace("\\|", "\x00P\x00").split("|")]
                cells = [c.replace("\x00P\x00", "|") for c in cells]
                if i == 0:
                    header = cells
                elif i == 1 and all(re.match(r"^[-: ]*$", c) and "-" in c for c in cells):
                    # GFM 对齐标记：:--- 左(默认)、---: 右、:---: 居中
                    aligns = [
                        "left" if not c.strip().endswith(":")
                        else ("center" if c.strip().startswith(":") else "right")
                        for c in cells
                    ]
                    continue
                else:
                    rows.append(cells)
            rendered = render_table(header, rows, theme, aligns)
            table_lines = []
            in_table = False
            return rendered

        def flush_code() -> str:
            nonlocal in_code_block, code_lang, code_lines, code_fence_ch, code_fence_len
            raw_code = "\n".join(code_lines)
            rendered = render_code(raw_code, code_lang, theme)
            code_lines = []
            in_code_block = False
            code_fence_ch = ""
            code_fence_len = 0
            return rendered

        def inline_fmt(text: str, size: str = "13.5px") -> str:
            return format_inline(
                text, accent, size,
                footnotes=footnotes, url_footnotes=link_to_footnote,
                ref_defs=ref_defs, footnote_defs=footnote_defs,
                accent_bg=theme.get("accent_bg"),
            ).replace("@@MDBR_0@@", "<br />")

        def flush_para() -> str:
            nonlocal para_buf
            if not para_buf:
                return ""
            joined = join_paragraph_lines(para_buf, force_breaks)
            para_buf = []
            p_text = inline_fmt(joined)
            return (
                f'<p style="font-size: {font_size_base}; line-height: {line_height_base}; color: {text_color}; '
                f'margin: 18px 0; letter-spacing: {letter_spacing}; {indent_css}text-align: justify;">'
                f'{p_text}'
                f'</p>'
            )

        def parse_list(i: int, min_indent: int) -> Tuple[List[Dict[str, Any]], int]:
            """解析列表块 (含多层嵌套)；空行结束列表，缩进 2+ 空格的 marker 归入子列表"""
            items: List[Dict[str, Any]] = []
            first_indent = None
            while i < len(block_lines):
                ln = block_lines[i]
                if not ln.strip():
                    break
                lm = _LIST_ITEM_RE.match(ln.expandtabs(4))
                if not lm:
                    break
                ind = len(lm.group(1))
                if ind < min_indent:
                    break
                if first_indent is None:
                    first_indent = ind
                if ind < first_indent:
                    break
                if ind >= first_indent + 2:
                    if not items:
                        break
                    sub_items, i = parse_list(i, ind)
                    items[-1]["children"].extend(sub_items)
                    continue
                marker = lm.group(2)
                content = (lm.group(3) or "").strip()
                ordered = bool(re.match(r"\d", marker))
                number = int(re.match(r"(\d+)", marker).group(1)) if ordered else 0
                task = None
                tm = re.match(r"^\[( |x|X)\]\s+(.*)$", content)
                if tm:
                    task = tm.group(1).lower() == "x"
                    content = tm.group(2)
                item: Dict[str, Any] = {
                    "ordered": ordered, "number": number, "task": task,
                    "lines": [content] if content else [], "children": [],
                }
                items.append(item)
                i += 1
                # 同项延续行：缩进 >= 内容列的非 marker 行并入当前项
                content_col = first_indent + len(marker) + 1
                while i < len(block_lines):
                    nxt = block_lines[i]
                    if not nxt.strip():
                        break
                    nxt_exp = nxt.expandtabs(4)
                    nlm = _LIST_ITEM_RE.match(nxt_exp)
                    if nlm:
                        break
                    n_ind = len(nxt_exp) - len(nxt_exp.lstrip(" "))
                    if n_ind >= content_col:
                        item["lines"].append(nxt_exp.strip())
                        i += 1
                    else:
                        break
            return items, i

        def render_list_html(items: List[Dict[str, Any]]) -> str:
            out = []
            for it in items:
                content_html = ""
                if it["lines"]:
                    content_html = inline_fmt(join_paragraph_lines(it["lines"]))
                if it["children"]:
                    content_html += f'<div style="padding-left: 16px; margin-top: 2px;">{render_list_html(it["children"])}</div>'
                if it["task"] is not None:
                    out.append(render_task_item(content_html, it["task"], theme))
                elif it["ordered"]:
                    out.append(render_ordered_list_item(content_html, it["number"], theme))
                else:
                    out.append(render_list_item(content_html, theme))
            return "".join(out)

        parts: List[str] = []
        idx = 0
        n = len(block_lines)
        while idx < n:
            raw_line = block_lines[idx]
            stripped = raw_line.strip()

            # 1. 围栏代码块 (``` 与 ~~~ 等价，3+ 字符；闭栏需同字符且长度不小于开栏)
            fence_m = re.match(r"^(`{3,}|~{3,})(.*)$", stripped)
            if fence_m:
                f_ch = fence_m.group(1)[0]
                if in_code_block:
                    if f_ch == code_fence_ch and len(fence_m.group(1)) >= code_fence_len:
                        parts.append(flush_code())
                    else:
                        code_lines.append(raw_line)
                else:
                    if in_table:
                        parts.append(flush_table())
                    fp = flush_para()
                    if fp:
                        parts.append(fp)
                    in_code_block = True
                    code_fence_ch = f_ch
                    code_fence_len = len(fence_m.group(1))
                    code_lang = fence_m.group(2).strip()
                    code_lines = []
                idx += 1
                continue

            if in_code_block:
                code_lines.append(raw_line)
                idx += 1
                continue

            # 2. 表格
            if stripped.startswith("|") and stripped.endswith("|"):
                in_table = True
                table_lines.append(stripped)
                idx += 1
                continue
            elif in_table:
                parts.append(flush_table())

            # 3. 空行：结束当前段落
            if not stripped:
                fp = flush_para()
                if fp:
                    parts.append(fp)
                idx += 1
                continue

            # 3.5 块级富文本占位 token (Mermaid/块级公式，已由 richrender 预渲染为图片)
            if stripped in rich_block_map:
                fp = flush_para()
                if fp:
                    parts.append(fp)
                parts.append(rich_block_map[stripped])
                idx += 1
                continue

            # 3.2 缩进代码块：4+ 空格缩进且无未决段落 (列表项内部由列表解析器自行消费)
            if not para_buf and (raw_line.startswith("    ") or raw_line.startswith("\t")):
                fp = flush_para()
                if fp:
                    parts.append(fp)
                code_lines = []
                while idx < n and (block_lines[idx].startswith("    ") or block_lines[idx].startswith("\t") or not block_lines[idx].strip()):
                    exp = block_lines[idx].expandtabs(4)
                    code_lines.append(exp[4:] if exp.startswith("    ") else exp)
                    idx += 1
                while code_lines and not code_lines[-1].strip():
                    code_lines.pop()
                if code_lines:
                    parts.append(render_code("\n".join(code_lines), "code", theme))
                continue

            # 3.4 Setext 标题：段落缓冲非空时的 === / --- 下划线 (先于分割线判定)
            setext_m = re.match(r"^ {0,3}(=+|-+)\s*$", raw_line)
            if setext_m and para_buf:
                joined = join_paragraph_lines(para_buf)
                para_buf = []
                level = 1 if setext_m.group(1)[0] == "=" else 2
                parts.append(render_h1(inline_fmt(joined), theme) if level == 1 else render_h2(inline_fmt(joined), theme))
                idx += 1
                continue

            # 3.6 分割线 (3+ 个 -/*/ _，允许空格分隔，如 - - - / ****)
            if re.match(r"^ {0,3}([-*_])(?:[ \t]*\1){2,}\s*$", raw_line):
                fp = flush_para()
                if fp:
                    parts.append(fp)
                parts.append(render_hr(theme))
                idx += 1
                continue

            # 4. ATX 标题 # ~ ###### (去除尾部 # 修饰；文本运行行内格式化)
            atx_m = re.match(r"^(#{1,6})(?:\s+(.*?))?\s*#*\s*$", stripped)
            if atx_m:
                fp = flush_para()
                if fp:
                    parts.append(fp)
                level = len(atx_m.group(1))
                h_text = inline_fmt((atx_m.group(2) or "").strip())
                if level == 1:
                    parts.append(render_h1(h_text, theme))
                elif level == 2:
                    parts.append(render_h2(h_text, theme))
                elif level == 3:
                    parts.append(render_h3(h_text, theme))
                elif level == 4:
                    parts.append(render_h4(h_text, theme))
                elif level == 5:
                    parts.append(render_h5(h_text, theme))
                else:
                    parts.append(render_h6(h_text, theme))
                idx += 1
                continue

            # 5. 引用块 (剥一层 > 后递归渲染内层，支持 >> 多级嵌套；引用内空行为间隔)
            if stripped.startswith(">"):
                fp = flush_para()
                if fp:
                    parts.append(fp)
                if in_table:
                    parts.append(flush_table())
                inner_lines = []
                while idx < n and block_lines[idx].strip().startswith(">"):
                    q_line = block_lines[idx].strip()
                    inner_lines.append(q_line[2:].strip() if q_line.startswith("> ") else q_line[1:].strip())
                    idx += 1
                seg_parts: List[str] = []
                run: List[str] = []

                def flush_quote_run() -> None:
                    if run:
                        seg_parts.extend(render_block_lines(list(run), force_breaks=True))
                        run.clear()

                for q in inner_lines:
                    if q.strip():
                        run.append(q)
                    else:
                        flush_quote_run()
                        seg_parts.append('<div style="height: 6px;"></div>')
                flush_quote_run()
                parts.append(render_quote("\n".join(seg_parts), theme))
                continue

            # 6. 列表 (有序/无序/任务，含多层嵌套)
            list_m = _LIST_ITEM_RE.match(raw_line.expandtabs(4))
            if list_m and len(list_m.group(1)) < 4:
                fp = flush_para()
                if fp:
                    parts.append(fp)
                if in_table:
                    parts.append(flush_table())
                items, end_idx = parse_list(idx, len(list_m.group(1)))
                parts.append(render_list_html(items))
                idx = end_idx
                continue

            # 7. 独立行图片 (命中才冲刷段落缓冲，普通段落行继续走缓冲合并)
            img_match = re.match(r'^!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)$', stripped)
            if img_match:
                fp = flush_para()
                if fp:
                    parts.append(fp)
                alt = img_match.group(1).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                src = img_match.group(2).replace('"', "&quot;")
                caption = f'<div style="text-align: center; color: {sub_color}; font-size: 13px; margin-top: 6px; font-style: italic;">{alt}</div>' if alt else ""
                parts.append(
                    f'<div style="margin: 24px 0; text-align: center;">'
                    f'<img src="{src}" alt="{alt}" style="max-width: 96%; height: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); display: inline-block;" />'
                    f'{caption}'
                    f'</div>'
                )
                idx += 1
                continue

            # 8. 显式图注 (*▲ 图：...*)
            caption_match = re.match(r'^\*▲ 图：(.+?)\*$', stripped)
            if caption_match:
                fp = flush_para()
                if fp:
                    parts.append(fp)
                cap_text = caption_match.group(1)
                parts.append(
                    f'<div style="text-align: center; color: {sub_color}; font-size: 13px; margin: -16px 0 20px 0; font-style: italic;">'
                    f'▲ 图：{cap_text}'
                    f'</div>'
                )
                idx += 1
                continue

            # 9. 段落缓冲 (连续非空行合并为同一段；保留行尾空格供硬换行判定)
            para_buf.append(raw_line.rstrip("\r\n").lstrip())
            idx += 1

        fp = flush_para()
        if fp:
            parts.append(fp)
        if in_table:
            parts.append(flush_table())
        if in_code_block:
            parts.append(flush_code())
        return parts

    html_parts.extend(render_block_lines(lines))


        # 13. 注入文末参考链接与学术资料引用卡片
    if footnotes:
        list_items = []
        for f_idx, fn in enumerate(footnotes):
            num_html = f'<span style="color: {accent}; font-weight: 700; margin-right: 6px;">[{f_idx + 1}]</span>'
            if fn.get("kind") == "text":
                # [^id] 脚注：渲染定义正文 (定义内的链接渲染为锚点，不再产生新脚注)
                body_html = format_inline(fn.get("text", ""), accent, "12px", accent_bg=theme.get("accent_bg"))
                list_items.append(
                    f'<li style="margin: 5px 0; word-break: break-all; list-style-type: none;">'
                    f'{num_html}'
                    f'<span style="color: {text_color}; font-weight: 500;">{body_html}</span>'
                    f'</li>'
                )
            else:
                clean_label = fn["label"]
                list_items.append(
                    f'<li style="margin: 5px 0; word-break: break-all; list-style-type: none;">'
                    f'{num_html}'
                    f'<span style="color: {text_color}; font-weight: 500;">{clean_label}</span>: '
                    f'<span style="color: {sub_color}; font-family: monospace; font-size: 11.5px;">{fn["url"]}</span>'
                    f'</li>'
                )
        items_html = "\n".join(list_items)
        html_parts.append(
            f'<section style="margin-top: 36px; padding: 16px 18px; border-radius: 8px; background: rgba(0,0,0,0.02); border-left: 3px solid {accent}; border-top: 1px solid {border_color};">\n'
            f'<div style="font-size: 13.5px; font-weight: 700; color: {accent}; margin-bottom: 10px; display: flex; align-items: center;">\n'
            f'<span>参考链接与资料引用</span>\n'
            f'</div>\n'
            f'<ul style="margin: 0; padding-left: 0; font-size: 12px; color: {sub_color}; line-height: 1.8;">\n'
            f'{items_html}\n'
            f'</ul>\n'
            f'</section>'
        )

    final_body = "\n".join(html_parts)
    return render_container(final_body, theme)

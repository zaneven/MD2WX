"""
MD2WX 发稿规范校验器 (md2wx --lint)

沉淀本仓库开发日志/公众号文章的成文规范，发布前一键自检：
  1. 主标题 (frontmatter title 或首个 H1) 严禁超过 20 字，且不应以句读标点收尾
  2. 摘要 (frontmatter digest) 严格控制在 50 字以内，缺失时提示补写
  3. frontmatter 严禁填写 cover 字段 (统一由主题封面工坊/双比例引擎生成)
  4. 正文不得包含 \\x00 等控制字符 (会导致微信草稿静默截断)
  5. 检测正文外链图片 (微信编辑器会封禁外站图床)
  6. 标题层级跳跃 (H1 直接跳 H3 及更深)
  7. 围栏代码块缺少语言标注 (影响语法高亮质量)
  8. 图片缺少 alt 描述文本
  9. 同一图片 URL 被重复引用 (发布时将重复上传/换链，建议复用同一引用)
 10. 未闭合的块级 HTML 标签 (会让微信后台后续排版整体错乱)
 11. Emoji (项目规范要求界面与正文统一使用纯文本或矢量图标)
 12. 链接协议/格式异常 (缺少协议、含空白、非 http/https 协议)
 13. 中文正文全半角标点混用 (半角 , ; : ! ? ( ) 需改为全角)

规则编号 (code) 与 Web 端 web/src/core/lint.js 严格一一对应，
tests/test_lint_consistency.py 会在 Node 环境下逐条比对双端问题清单。
"""
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

from .parser import parse_frontmatter, collect_external_image_urls, expand_obsidian_images

DEVLOG_TITLE_MAX_LEN = 20
DEVLOG_DIGEST_MAX_LEN = 50

# 微信草稿箱 API 严禁的控制字符 (Null Byte 等会导致正文静默截断)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

_ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+\S")
_FENCE_OPEN_RE = re.compile(r"^(```+|~~~+)\s*([^`]*)$")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")

# Emoji 区段 (含 Emoji 主体、杂项符号、丁巴特与 Keycap，不含裸变体选择符 FE0F)
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u20E3]"
)
_HAN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")

# 中文正文中常见的半角标点 -> 全角建议
_HALF_TO_FULL = {
    ",": "，",
    ";": "；",
    ":": "：",
    "!": "！",
    "?": "？",
    "(": "（",
    ")": "）",
}
_TITLE_TRAILING_PUNCT = "。．.，,；;：:"
_DIGEST_TRAILING_PUNCT = "，,；;：:"

# 高风险块级标签：未闭合会让微信后台后续内容整体错乱
_BLOCK_TAGS = ("div", "section", "table", "pre", "style", "script", "iframe", "video", "svg")
_BLOCK_TAG_RE = re.compile(r"<(/?)\s*(" + "|".join(_BLOCK_TAGS) + r")\b[^>]*?(/?)>", re.IGNORECASE)

# 行内遮罩正则：仅用于统计与定位，遮罩后长度不变，保证列/行号可回溯
_RE_INLINE_CODE = re.compile(r"(`+)(?:(?!\1)[\s\S])+?\1")
_RE_LINK_TARGET = re.compile(r"\]\(\s*<?[^)\n]*>?(?:\s+\"[^\"]*\")?\s*\)")
_RE_BARE_URL = re.compile(r"https?://[^\s<>()\[\]]+")
_RE_HTML_TAG = re.compile(r"</?[A-Za-z][^>\n]*>")
_RE_ENTITY = re.compile(r"&(?:[a-zA-Z][a-zA-Z0-9]*|#[0-9]+|#x[0-9a-fA-F]+);")
_RE_MD_LINK = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]*)>?(?:\s+\"[^\"]*\")?\s*\)")


def _blank(match: "re.Match") -> str:
    """把匹配片段替换为等长空白 (保留换行)，用于在不改变坐标的前提下跳过非正文内容"""
    return re.sub(r"[^\n]", " ", match.group(0))


def _mask_inline_code(line: str) -> str:
    return _RE_INLINE_CODE.sub(_blank, line)


def _mask_prose(line: str) -> str:
    """遮罩行内代码、链接目标、裸 URL、HTML 标签与实体，只留下可读正文"""
    line = _RE_INLINE_CODE.sub(_blank, line)
    line = _RE_LINK_TARGET.sub(_blank, line)
    line = _RE_BARE_URL.sub(_blank, line)
    line = _RE_HTML_TAG.sub(_blank, line)
    return _RE_ENTITY.sub(_blank, line)


def _strip_fenced(body: str) -> str:
    """把围栏代码块整段替换为空行，保持行号不变"""
    out: List[str] = []
    fence_marker = ""
    for line in body.split("\n"):
        if fence_marker:
            stripped = line.strip()
            if stripped.startswith(fence_marker) and set(stripped) <= {fence_marker[0]}:
                fence_marker = ""
            out.append("")
            continue
        fence_m = _FENCE_OPEN_RE.match(line)
        if fence_m:
            fence_marker = fence_m.group(1)
            out.append("")
            continue
        out.append(line)
    return "\n".join(out)


def _mask_body(body: str) -> Tuple[str, str]:
    """
    返回 (prose_masked, code_masked)：
      prose_masked: 围栏 + 行内代码 + 链接目标/裸 URL/HTML 标签/实体全部遮罩，用于标点与 Emoji 检测
      code_masked:  仅遮罩围栏与行内代码，保留链接与 HTML 标签，用于链接格式与标签闭合检测
    """
    prose_lines: List[str] = []
    code_lines: List[str] = []
    for line in _strip_fenced(body).split("\n"):
        prose_lines.append(_mask_prose(line))
        code_lines.append(_mask_inline_code(line))
    return "\n".join(prose_lines), "\n".join(code_lines)


def _field_line(raw_lines: List[str], key: str) -> int:
    """定位 frontmatter 字段所在行 (1-based)；未找到返回 1"""
    for idx, line in enumerate(raw_lines):
        if idx == 0 and line.strip() == "---":
            continue
        if line.strip() == "---":
            break
        if re.match(r"^\s*" + re.escape(key) + r"\s*:", line):
            return idx + 1
    return 1


def _first_half_width_punct(text: str) -> str:
    for ch in text:
        if ch in _HALF_TO_FULL:
            return ch
    return ""


def _scan_body_structure(body: str) -> Dict[str, object]:
    """
    扫描正文结构，返回 lint 规则所需的原始清单 (行号均为正文内 1-based)：
      headings: [(level, line, text)]
      fences_without_lang: [(line, lang_info)]
      image_urls: [(url, line)]，含重复
      images_missing_alt: [(line, url)]
    """
    headings: List[tuple] = []
    fences_without_lang: List[tuple] = []
    image_urls: List[tuple] = []
    images_missing_alt: List[tuple] = []

    fence_marker = ""  # 当前所处代码围栏的开栏标记 (```` / ~~~~)，空串表示不在代码块内
    for idx, line in enumerate(body.split("\n"), start=1):
        if fence_marker:
            # 闭栏需与开栏同字符且长度不小于开栏
            stripped = line.strip()
            if stripped.startswith(fence_marker) and set(stripped) <= {fence_marker[0]}:
                fence_marker = ""
            continue

        fence_m = _FENCE_OPEN_RE.match(line)
        if fence_m:
            marker, info = fence_m.group(1), fence_m.group(2).strip()
            if not info:
                fences_without_lang.append((idx, info))
            fence_marker = marker
            continue

        heading_m = _ATX_HEADING_RE.match(line)
        if heading_m:
            headings.append((len(heading_m.group(1)), idx, line.lstrip("#").strip()))

        for img_m in _IMAGE_RE.finditer(line):
            image_urls.append((img_m.group(2), idx))
            if not img_m.group(1).strip():
                images_missing_alt.append((idx, img_m.group(2)))

    return {
        "headings": headings,
        "fences_without_lang": fences_without_lang,
        "image_urls": image_urls,
        "images_missing_alt": images_missing_alt,
    }


def _punctuation_hits(masked_body: str) -> List[Tuple[int, List[str]]]:
    """
    逐行检测中文正文里的半角标点：
      - 半角标点紧邻汉字 (前后任一侧) -> 全半角混用
      - 英文单词后的半角逗号/分号接中文 -> 全半角混用
    返回 [(line, [标点...])]，标点按首次出现顺序去重。
    """
    hits: List[Tuple[int, List[str]]] = []
    for line_idx, line in enumerate(masked_body.split("\n"), start=1):
        found: List[str] = []
        length = len(line)
        for col, ch in enumerate(line):
            if ch not in _HALF_TO_FULL:
                continue
            before = line[col - 1] if col > 0 else ""
            after = line[col + 1] if col + 1 < length else ""
            adjacent_han = bool(
                (before and _HAN_RE.match(before)) or (after and _HAN_RE.match(after))
            )
            if adjacent_han:
                if ch not in found:
                    found.append(ch)
                continue
            if ch in ",;":
                prev_ascii_word = bool(before) and (before.isalnum() and ord(before) < 0x2E80)
                next_is_space = bool(after) and after.isspace()
                if prev_ascii_word and next_is_space:
                    probe = col + 1
                    while probe < length and line[probe].isspace():
                        probe += 1
                    if probe < length and _HAN_RE.match(line[probe]):
                        if ch not in found:
                            found.append(ch)
        if found:
            hits.append((line_idx, found))
    return hits


def _link_format_issues(masked_body: str) -> List[Tuple[int, str, str]]:
    """
    校验 Markdown 链接协议与格式 (不做网络请求，Web 端可直接复用)：
      - 空目标
      - 目标含空白字符
      - 以 // 开头 (缺少协议)
      - 协议不是 http / https / mailto
      - www. 开头 (缺少协议)
    返回 [(line, url, reason)]
    """
    issues: List[Tuple[int, str, str]] = []
    for line_idx, line in enumerate(masked_body.split("\n"), start=1):
        for match in _RE_MD_LINK.finditer(line):
            target = match.group(1).strip()
            reason = ""
            if not target:
                reason = "链接目标为空"
            elif re.search(r"\s", target):
                reason = "链接目标包含空白字符"
            elif target.startswith("//"):
                reason = "缺少 http/https 协议"
            elif re.match(r"^[A-Za-z][A-Za-z0-9+.\-]*:", target):
                scheme = target.split(":", 1)[0].lower()
                if scheme not in ("http", "https", "mailto"):
                    reason = f"不支持的协议「{scheme}」"
            elif re.match(r"^www\.", target, re.IGNORECASE):
                reason = "缺少 http/https 协议"
            if reason:
                issues.append((line_idx, target, reason))
    return issues


def lint_markdown(raw_md: str) -> List[Dict[str, object]]:
    """
    按 MD2WX 发稿规范检查 Markdown，返回问题列表。
    每项 {level: "error"|"warn", code, message, line}；error 不为空时 CLI 以非零码退出。
    规则顺序与 Web 端 web/src/core/lint.js 严格一致，便于双端逐条比对。
    """
    issues: List[Dict[str, object]] = []

    def _add(level: str, code: str, message: str, line: int = 1) -> None:
        issues.append({"level": level, "code": code, "message": message, "line": int(line)})

    meta, body = parse_frontmatter(raw_md)
    normalized = raw_md.replace("\r\n", "\n").replace("\r", "\n")
    raw_lines = normalized.split("\n")
    # Frontmatter 被剥离后 body 行号相对偏移，用于把问题定位回编辑器原始行
    body_line_offset = len(raw_lines) - len(body.split("\n"))

    def _raw_line(body_line: int) -> int:
        return max(1, body_line + body_line_offset)

    # Obsidian wiki 图片语法归一化：让图片 alt/重复引用/外链检查覆盖 ![[x.png]] 写法
    body = expand_obsidian_images(body)
    body_lines = body.split("\n")
    prose_masked, code_masked = _mask_body(body)

    # 1. 主标题：frontmatter title 优先，其次首个 H1
    title = meta.get("title") or ""
    if not isinstance(title, str):
        title = str(title)
    title_line = _field_line(raw_lines, "title")
    if not title:
        for idx, line in enumerate(body_lines, start=1):
            if line.strip().startswith("# "):
                title = line.strip()[2:].strip()
                title_line = _raw_line(idx)
                break
    if not title:
        _add("warn", "title-missing", "未找到主标题 (frontmatter title 或首个 H1)，将回退为「未命名文章」。")
    else:
        if len(title) > DEVLOG_TITLE_MAX_LEN:
            _add(
                "error",
                "title-too-long",
                f"主标题 {len(title)} 字，超过规范上限 {DEVLOG_TITLE_MAX_LEN} 字：「{title}」",
                title_line,
            )
        trailing = title.rstrip()[-1:] if title.rstrip() else ""
        if trailing in _TITLE_TRAILING_PUNCT:
            _add(
                "warn",
                "title-punctuation",
                f"主标题结尾不要使用标点「{trailing}」，微信会话列表按纯文本展示更清爽。",
                title_line,
            )
        else:
            half = _first_half_width_punct(title)
            if half:
                _add(
                    "warn",
                    "title-punctuation",
                    f"主标题混用半角标点「{half}」，建议改为全角「{_HALF_TO_FULL[half]}」。",
                    title_line,
                )

    # 2. 摘要 digest
    digest = meta.get("digest") or ""
    if not isinstance(digest, str):
        digest = str(digest)
    digest_line = _field_line(raw_lines, "digest")
    if not digest:
        _add("warn", "digest-missing", "frontmatter 缺少 digest 摘要，发布时将回退为正文首段/引言。")
    else:
        if len(digest) > DEVLOG_DIGEST_MAX_LEN:
            _add(
                "error",
                "digest-too-long",
                f"digest 摘要 {len(digest)} 字，超过规范上限 {DEVLOG_DIGEST_MAX_LEN} 字：「{digest}」",
                digest_line,
            )
        trailing = digest.rstrip()[-1:] if digest.rstrip() else ""
        if trailing in _DIGEST_TRAILING_PUNCT:
            _add(
                "warn",
                "digest-punctuation",
                f"digest 结尾不要使用标点「{trailing}」，微信摘要会自动截断展示。",
                digest_line,
            )
        else:
            half = _first_half_width_punct(digest)
            if half:
                _add(
                    "warn",
                    "digest-punctuation",
                    f"digest 混用半角标点「{half}」，建议改为全角「{_HALF_TO_FULL[half]}」。",
                    digest_line,
                )

    # 3. cover 字段禁填 (统一由主题封面工坊/双比例封面引擎自动生成)
    if "cover" in meta:
        _add(
            "error",
            "cover-forbidden",
            "frontmatter 填写了 cover 字段，规范要求留空由主题封面引擎自动生成。",
            _field_line(raw_lines, "cover"),
        )

    # 4. 控制字符 (微信草稿箱会静默截断正文)
    control_match = _CONTROL_CHARS_RE.search(body)
    if control_match:
        control_line = body.count("\n", 0, control_match.start()) + 1
        _add(
            "error",
            "control-chars",
            f"正文包含控制字符 U+{ord(control_match.group(0)):04X}，微信草稿箱 API 会导致正文静默截断。",
            _raw_line(control_line),
        )

    # 5. Emoji 检测 (项目规范：界面与正文统一使用纯文本或矢量图标)
    for line_idx, line in enumerate(prose_masked.split("\n"), start=1):
        found = _EMOJI_RE.findall(line)
        if not found:
            continue
        sample = found[0]
        if len(found) > 1:
            message = f"检测到 {len(found)} 处 Emoji（如「{sample}」），项目规范要求正文使用纯文本或矢量图标。"
        else:
            message = f"检测到 Emoji「{sample}」，项目规范要求正文使用纯文本或矢量图标。"
        _add("warn", "emoji-banned", message, _raw_line(line_idx))

    # 6. 未闭合块级 HTML 标签 (会导致微信后台后续排版整体错乱)
    open_counts: Dict[str, int] = {}
    close_counts: Dict[str, int] = {}
    first_lines: Dict[str, int] = {}
    for line_idx, line in enumerate(code_masked.split("\n"), start=1):
        for match in _BLOCK_TAG_RE.finditer(line):
            closing, tag, self_closing = match.group(1), match.group(2).lower(), match.group(3)
            if self_closing:
                continue
            if closing:
                close_counts[tag] = close_counts.get(tag, 0) + 1
            else:
                open_counts[tag] = open_counts.get(tag, 0) + 1
                first_lines.setdefault(tag, line_idx)
    for tag, open_count in open_counts.items():
        if open_count > close_counts.get(tag, 0):
            _add(
                "error",
                "html-unclosed",
                f"检测到未闭合的 <{tag}> 标签，粘贴到微信后台会导致后续排版错乱，请补齐闭合标签。",
                _raw_line(first_lines[tag]),
            )

    # 7. 外链图片 (微信编辑器封禁外站图床，需转存微信 CDN 或图床)
    external_images = collect_external_image_urls(body)
    if external_images:
        preview = "、".join(external_images[:3])
        more = f" 等 {len(external_images)} 处" if len(external_images) > 3 else ""
        first_external = external_images[0]
        external_line = 1
        for idx, line in enumerate(body_lines, start=1):
            if first_external in line:
                external_line = idx
                break
        _add(
            "warn",
            "external-images",
            f"检测到外链图片{more}：{preview}。发布模式 (-p) 会自动转存微信 CDN，剪贴板模式可使用 --rehost-images 换链。",
            _raw_line(external_line),
        )

    # 8-11. 正文结构类规范 (标题层级 / 代码块语言 / 图片 alt / 重复图片)
    structure = _scan_body_structure(body)

    # 8. 标题层级跳跃：H1 直接跳 H3 及更深
    prev_level = 0
    for level, line_no, text in structure["headings"]:
        if prev_level and level > prev_level + 1:
            _add(
                "warn",
                "heading-skip",
                f"标题层级跳跃：H{prev_level} 后直接出现 H{level}「{text[:24]}…」，建议逐级递进。",
                _raw_line(line_no),
            )
            break  # 只提示首个跳跃点，避免刷屏
        prev_level = level

    # 9. 围栏代码块缺少语言标注 (影响语法高亮与移动端阅读体验)
    fences_without_lang = structure["fences_without_lang"]
    if fences_without_lang:
        _add(
            "warn",
            "code-lang-missing",
            f"{len(fences_without_lang)} 处围栏代码块未标注语言。纯文本块可忽略；语法代码建议补语言标注以启用高亮。",
            _raw_line(fences_without_lang[0][0]),
        )

    # 10. 图片缺少 alt 描述文本
    images_missing_alt = structure["images_missing_alt"]
    if images_missing_alt:
        _add(
            "warn",
            "image-alt-missing",
            f"{len(images_missing_alt)} 处图片缺少 alt 描述文本，建议补充说明 (微信图片折叠时无法展示语义)。",
            _raw_line(images_missing_alt[0][0]),
        )

    # 11. 同一图片 URL 被重复引用 (发布时会重复上传/换链)
    seen_urls = set()
    for url, line_no in structure["image_urls"]:
        if url in seen_urls:
            _add(
                "warn",
                "duplicate-image",
                f"同一图片被重复引用：{url[:60]}。建议复用同一处引用或拆分为不同说明图。",
                _raw_line(line_no),
            )
            break
        seen_urls.add(url)

    # 12. 链接协议 / 格式异常 (不发起网络请求，双端规则一致)
    for line_idx, target, reason in _link_format_issues(code_masked):
        _add(
            "warn",
            "link-format-invalid",
            f"链接格式异常「{target}」：{reason}，微信无法识别。",
            _raw_line(line_idx),
        )

    # 13. 中文正文全半角标点混用 (逐行提示，便于编辑器点击定位)
    for line_idx, puncts in _punctuation_hits(prose_masked):
        half = "、".join(f"「{ch}」" for ch in puncts)
        full = "、".join(f"「{_HALF_TO_FULL[ch]}」" for ch in puncts)
        _add(
            "warn",
            "punctuation-mixed",
            f"中文正文混用半角标点{half}，建议改为全角{full}。",
            _raw_line(line_idx),
        )

    return issues


# ------------------------------------------------------------------------------
# CLI 专属：外链可达性探测 (Web 端受跨域限制，仅做协议/格式校验)
# ------------------------------------------------------------------------------
_EXTERNAL_LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*<?(https?://[^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)", re.IGNORECASE)
_AUTOLINK_RE = re.compile(r"<(https?://[^>\s]+)>", re.IGNORECASE)


def collect_external_links(md_text: str) -> List[Tuple[str, int]]:
    """收集正文中的 HTTP 外链 [(url, line)]，跳过代码围栏、图片与重复项"""
    masked = _mask_inline_code(_strip_fenced(md_text))
    links: List[Tuple[str, int]] = []
    seen = set()
    for line_idx, line in enumerate(masked.split("\n"), start=1):
        # 图片链接不在可达性探测范围内 (外链图片由 external-images 规则覆盖)
        candidates = [
            m.group(1)
            for m in _RE_MD_LINK.finditer(line)
            if not m.group(0).startswith("!")
        ]
        candidates.extend(m.group(1) for m in _AUTOLINK_RE.finditer(line))
        for url in candidates:
            if url in seen:
                continue
            seen.add(url)
            links.append((url, line_idx))
    return links


def check_link_reachability(
    md_text: str,
    timeout: float = 3.0,
    max_links: int = 20,
) -> List[Dict[str, object]]:
    """
    并发探测正文外链可达性：超时或网络异常降级为 warn，不阻断发布。
    Returns issue dicts 与 lint_markdown 同构 (code: link-unreachable / link-timeout)。
    """
    import socket
    import urllib.error
    import urllib.request

    links = collect_external_links(md_text)[:max_links]
    if not links:
        return []

    headers = {"User-Agent": "Mozilla/5.0 (compatible; MD2WX-Lint/1.0)"}

    def _probe(item: Tuple[str, int]) -> Optional[Dict[str, object]]:
        url, line = item
        request = urllib.request.Request(url, headers=headers, method="HEAD")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - 仅探测用户正文链接
                status = getattr(response, "status", 200)
            if status and status >= 400 and status != 405:
                return {
                    "level": "warn",
                    "code": "link-unreachable",
                    "message": f"外链返回 HTTP {status}：{url}",
                    "line": line,
                }
            return None
        except socket.timeout:
            return {
                "level": "warn",
                "code": "link-timeout",
                "message": f"外链探测超时 ({timeout:g}s)：{url}",
                "line": line,
            }
        except urllib.error.HTTPError as exc:
            if exc.code == 405:  # 部分站点不支持 HEAD，视为可达
                return None
            return {
                "level": "warn",
                "code": "link-unreachable",
                "message": f"外链返回 HTTP {exc.code}：{url}",
                "line": line,
            }
        except Exception:
            return {
                "level": "warn",
                "code": "link-unreachable",
                "message": f"外链探测失败：{url}",
                "line": line,
            }

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_probe, links))
    return [item for item in results if item]


def has_errors(issues: List[Dict[str, object]]) -> bool:
    """是否存在阻断级问题 (error)"""
    return any(item["level"] == "error" for item in issues)


def summarize(issues: List[Dict[str, object]]) -> Dict[str, int]:
    """统计 error / warn 数量，供 --format json 与 Web 端面板共用口径"""
    errors = sum(1 for i in issues if i["level"] == "error")
    return {"errors": errors, "warnings": len(issues) - errors}


def format_lint_report(issues: List[Dict[str, object]]) -> str:
    """渲染终端友好的检查报告 (遵循规范，不使用 Emoji)"""
    if not issues:
        return "[lint] 全部通过：标题、摘要、封面字段、控制字符与外链图片均符合规范。"
    lines = []
    for item in issues:
        mark = "[!]" if item["level"] == "error" else "[*]"
        line = item.get("line")
        where = f"L{line} " if line else ""
        lines.append(f"{mark} {where}{item['message']}")
    counts = summarize(issues)
    lines.append(f"[lint] 共 {counts['errors']} 项阻断问题 / {counts['warnings']} 项建议。")
    return "\n".join(lines)

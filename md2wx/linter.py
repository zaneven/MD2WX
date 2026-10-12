"""
MD2WX 发稿规范校验器 (md2wx --lint)

沉淀本仓库开发日志/公众号文章的成文规范，发布前一键自检：
  1. 主标题 (frontmatter title 或首个 H1) 严禁超过 20 字
  2. 摘要 (frontmatter digest) 严格控制在 50 字以内，缺失时提示补写
  3. frontmatter 严禁填写 cover 字段 (统一由主题封面工坊/双比例引擎生成)
  4. 正文不得包含 \\x00 等控制字符 (会导致微信草稿静默截断)
  5. 检测正文外链图片 (微信编辑器会封禁外站图床)
  6. 标题层级跳跃 (H1 直接跳 H3 及更深)
  7. 围栏代码块缺少语言标注 (影响语法高亮质量)
  8. 图片缺少 alt 描述文本
  9. 同一图片 URL 被重复引用 (发布时将重复上传/换链，建议复用同一引用)
"""
import re
from typing import Dict, List

from .parser import parse_frontmatter, collect_external_image_urls

DEVLOG_TITLE_MAX_LEN = 20
DEVLOG_DIGEST_MAX_LEN = 50

# 微信草稿箱 API 严禁的控制字符 (Null Byte 等会导致正文静默截断)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

_ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+\S")
_FENCE_OPEN_RE = re.compile(r"^(```+|~~~+)\s*([^`]*)$")
_IMAGE_NO_ALT_RE = re.compile(r"!\[\s*\]\(")


def _scan_body_structure(body: str) -> Dict[str, object]:
    """
    扫描正文结构，返回 lint 规则所需的原始清单：
      headings: [(level, line)]，代码围栏内的 # 注释不计
      fences_without_lang: 缺语言标注的围栏数量
      image_urls: 全部图片引用 URL (含重复)
      images_missing_alt: 缺 alt 的图片数量
    """
    headings: List[tuple] = []
    fences_without_lang = 0
    image_urls: List[str] = []
    images_missing_alt = 0

    fence_marker = ""  # 当前所处代码围栏的开栏标记 (```` / ~~~~)，空串表示不在代码块内
    for line in body.split("\n"):
        if fence_marker:
            # 闭栏需与开栏同字符且长度不小于开栏
            if line.strip().startswith(fence_marker) and set(line.strip()) <= {fence_marker[0]}:
                fence_marker = ""
            continue

        fence_m = _FENCE_OPEN_RE.match(line)
        if fence_m:
            marker, info = fence_m.group(1), fence_m.group(2).strip()
            if not info:
                fences_without_lang += 1
            fence_marker = marker
            continue

        heading_m = _ATX_HEADING_RE.match(line)
        if heading_m:
            headings.append((len(heading_m.group(1)), line))

        for img_m in re.finditer(r"!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?", line):
            image_urls.append(img_m.group(2))
            if not img_m.group(1).strip():
                images_missing_alt += 1

    return {
        "headings": headings,
        "fences_without_lang": fences_without_lang,
        "image_urls": image_urls,
        "images_missing_alt": images_missing_alt,
    }


def lint_markdown(raw_md: str) -> List[Dict[str, str]]:
    """
    按 MD2WX 发稿规范检查 Markdown，返回问题列表。
    每项 {level: "error"|"warn", code, message}；error 不为空时 CLI 以非零码退出。
    """
    issues: List[Dict[str, str]] = []

    def _add(level: str, code: str, message: str) -> None:
        issues.append({"level": level, "code": code, "message": message})

    meta, body = parse_frontmatter(raw_md)

    # 1. 主标题：frontmatter title 优先，其次首个 H1
    title = meta.get("title") or ""
    if not title:
        for line in body.split("\n"):
            if line.strip().startswith("# "):
                title = line.strip()[2:].strip()
                break
    if not title:
        _add("warn", "title-missing", "未找到主标题 (frontmatter title 或首个 H1)，将回退为「未命名文章」。")
    elif len(title) > DEVLOG_TITLE_MAX_LEN:
        _add(
            "error",
            "title-too-long",
            f"主标题 {len(title)} 字，超过规范上限 {DEVLOG_TITLE_MAX_LEN} 字：「{title}」",
        )

    # 2. 摘要 digest
    digest = meta.get("digest") or ""
    if not digest:
        _add("warn", "digest-missing", "frontmatter 缺少 digest 摘要，发布时将回退为正文首段/引言。")
    elif len(digest) > DEVLOG_DIGEST_MAX_LEN:
        _add(
            "error",
            "digest-too-long",
            f"digest 摘要 {len(digest)} 字，超过规范上限 {DEVLOG_DIGEST_MAX_LEN} 字：「{digest}」",
        )

    # 3. cover 字段禁填 (统一由主题封面工坊/双比例封面引擎自动生成)
    if "cover" in meta:
        _add("error", "cover-forbidden", "frontmatter 填写了 cover 字段，规范要求留空由主题封面引擎自动生成。")

    # 4. 控制字符 (微信草稿箱会静默截断正文)
    control_match = _CONTROL_CHARS_RE.search(body)
    if control_match:
        _add(
            "error",
            "control-chars",
            f"正文包含控制字符 U+{ord(control_match.group(0)):04X}，微信草稿箱 API 会导致正文静默截断。",
        )

    # 5. 外链图片 (微信编辑器封禁外站图床，需转存微信 CDN 或图床)
    external_images = collect_external_image_urls(body)
    if external_images:
        preview = "、".join(external_images[:3])
        more = f" 等 {len(external_images)} 处" if len(external_images) > 3 else ""
        _add(
            "warn",
            "external-images",
            f"检测到外链图片{more}：{preview}。发布模式 (-p) 会自动转存微信 CDN，剪贴板模式可使用 --rehost-images 换链。",
        )

    # 6-9. 正文结构类规范 (标题层级 / 代码块语言 / 图片 alt / 重复图片)
    structure = _scan_body_structure(body)

    # 6. 标题层级跳跃：H1 直接跳 H3 及更深
    prev_level = 0
    for level, line in structure["headings"]:
        if prev_level and level > prev_level + 1:
            _add(
                "warn",
                "heading-skip",
                f"标题层级跳跃：H{prev_level} 后直接出现 H{level}「{line.lstrip('#').strip()[:24]}…」，建议逐级递进。",
            )
            break  # 只提示首个跳跃点，避免刷屏
        prev_level = level

    # 7. 围栏代码块缺少语言标注 (影响语法高亮与移动端阅读体验)
    if structure["fences_without_lang"]:
        _add(
            "warn",
            "code-lang-missing",
            f"{structure['fences_without_lang']} 处围栏代码块未标注语言。纯文本块可忽略；语法代码建议补语言标注以启用高亮。",
        )

    # 8. 图片缺少 alt 描述文本
    if structure["images_missing_alt"]:
        _add(
            "warn",
            "image-alt-missing",
            f"{structure['images_missing_alt']} 处图片缺少 alt 描述文本，建议补充说明 (微信图片折叠时无法展示语义)。",
        )

    # 9. 同一图片 URL 被重复引用 (发布时会重复上传/换链)
    seen_urls = set()
    for url in structure["image_urls"]:
        if url in seen_urls:
            _add("warn", "duplicate-image", f"同一图片被重复引用：{url[:60]}。建议复用同一处引用或拆分为不同说明图。")
            break
        seen_urls.add(url)

    return issues


def has_errors(issues: List[Dict[str, str]]) -> bool:
    """是否存在阻断级问题 (error)"""
    return any(item["level"] == "error" for item in issues)


def format_lint_report(issues: List[Dict[str, str]]) -> str:
    """渲染终端友好的检查报告 (遵循规范，不使用 Emoji)"""
    if not issues:
        return "[lint] 全部通过：标题、摘要、封面字段、控制字符与外链图片均符合规范。"
    lines = []
    for item in issues:
        mark = "[!]" if item["level"] == "error" else "[*]"
        lines.append(f"{mark} {item['message']}")
    errors = sum(1 for i in issues if i["level"] == "error")
    warns = len(issues) - errors
    lines.append(f"[lint] 共 {errors} 项阻断问题 / {warns} 项建议。")
    return "\n".join(lines)

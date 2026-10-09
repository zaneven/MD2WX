"""
MD2WX 发稿规范校验器 (md2wx --lint)

沉淀本仓库开发日志/公众号文章的成文规范，发布前一键自检：
  1. 主标题 (frontmatter title 或首个 H1) 严禁超过 20 字
  2. 摘要 (frontmatter digest) 严格控制在 50 字以内，缺失时提示补写
  3. frontmatter 严禁填写 cover 字段 (统一由主题封面工坊/双比例引擎生成)
  4. 正文不得包含 \\x00 等控制字符 (会导致微信草稿静默截断)
  5. 检测正文外链图片 (微信编辑器会封禁外站图床)
"""
import re
from typing import Dict, List

from .parser import parse_frontmatter, collect_external_image_urls

DEVLOG_TITLE_MAX_LEN = 20
DEVLOG_DIGEST_MAX_LEN = 50

# 微信草稿箱 API 严禁的控制字符 (Null Byte 等会导致正文静默截断)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


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

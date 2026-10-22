"""MD2WX 发稿规范校验器 (lint) 单元测试"""
from md2wx.linter import format_lint_report, has_errors, lint_markdown


def _codes(issues):
    return {i["code"] for i in issues}


def test_clean_article_passes():
    md = "---\ntitle: 短标题\ndigest: 五十字以内的合格摘要写这里就好。\n---\n\n# 短标题\n\n正文。\n"
    issues = lint_markdown(md)
    assert not has_errors(issues)
    assert "title-too-long" not in _codes(issues)
    assert "digest-too-long" not in _codes(issues)
    assert "cover-forbidden" not in _codes(issues)


def test_title_over_20_chars_is_error():
    md = "---\ntitle: 这是一个肯定超过了二十个字符的超长文章标题需要被拦截\n---\n\n正文\n"
    issues = lint_markdown(md)
    assert has_errors(issues)
    assert "title-too-long" in _codes(issues)


def test_title_from_h1_fallback():
    md = "# " + "超" * 21 + "\n\n正文\n"
    issues = lint_markdown(md)
    assert "title-too-long" in _codes(issues)


def test_missing_digest_is_warn_not_error():
    md = "---\ntitle: 短标题\n---\n\n正文\n"
    issues = lint_markdown(md)
    assert not has_errors(issues)
    assert "digest-missing" in _codes(issues)


def test_digest_over_50_chars_is_error():
    md = "---\ntitle: 短标题\ndigest: " + "长" * 51 + "\n---\n\n正文\n"
    issues = lint_markdown(md)
    assert has_errors(issues)
    assert "digest-too-long" in _codes(issues)


def test_cover_field_forbidden():
    md = "---\ntitle: 短标题\ndigest: 摘要\ncover: ./assets/cover.png\n---\n\n正文\n"
    issues = lint_markdown(md)
    assert has_errors(issues)
    assert "cover-forbidden" in _codes(issues)


def test_control_chars_detected():
    md = "---\ntitle: 短标题\n---\n\n正文\x00被截断\n"
    issues = lint_markdown(md)
    assert has_errors(issues)
    assert "control-chars" in _codes(issues)


def test_external_images_warn():
    md = "---\ntitle: 短标题\ndigest: 摘要\n---\n\n![外图](https://cdn.example.com/a.png)\n"
    issues = lint_markdown(md)
    assert not has_errors(issues)
    assert "external-images" in _codes(issues)


def test_wechat_cdn_images_not_flagged():
    md = (
        "---\ntitle: 短标题\ndigest: 摘要\n---\n\n"
        "![图](https://mmbiz.qpic.cn/mmbiz_png/abc/640)\n"
    )
    assert "external-images" not in _codes(lint_markdown(md))


def test_external_images_in_code_fence_ignored():
    md = (
        "---\ntitle: 短标题\ndigest: 摘要\n---\n\n"
        "```text\n![不是图片](https://cdn.example.com/a.png)\n```\n"
    )
    assert "external-images" not in _codes(lint_markdown(md))


def test_format_report_and_has_errors():
    issues = lint_markdown("---\ntitle: 短标题\ndigest: 摘要\ncover: x\n---\n\n正文\n")
    report = format_lint_report(issues)
    assert "cover" in report
    assert format_lint_report([]).count("全部通过") == 1


def test_heading_level_skip_warns():
    md = (
        "---\ntitle: 短标题\ndigest: 摘要\n---\n\n"
        "# 一级\n\n### 直接跳三级\n\n正文\n"
    )
    assert "heading-skip" in _codes(lint_markdown(md))


def test_heading_sequential_no_warn():
    md = (
        "---\ntitle: 短标题\ndigest: 摘要\n---\n\n"
        "# 一级\n\n## 二级\n\n### 三级\n\n#### 四级\n\n正文\n"
    )
    assert "heading-skip" not in _codes(lint_markdown(md))


def test_heading_inside_code_fence_ignored():
    md = (
        "---\ntitle: 短标题\ndigest: 摘要\n---\n\n"
        "# 一级\n\n```python\n### 这是注释不是标题\n```\n\n正文\n"
    )
    assert "heading-skip" not in _codes(lint_markdown(md))


def test_code_fence_without_lang_warns():
    md = (
        "---\ntitle: 短标题\ndigest: 摘要\n---\n\n"
        "```python\nprint(1)\n```\n\n```\nplain text\n```\n\n正文\n"
    )
    assert "code-lang-missing" in _codes(lint_markdown(md))


def test_image_without_alt_warns():
    md = (
        "---\ntitle: 短标题\ndigest: 摘要\n---\n\n"
        "![](https://cdn.example.com/a.png)\n\n"
        "![有描述](https://cdn.example.com/b.png)\n\n正文\n"
    )
    issues = lint_markdown(md)
    assert "image-alt-missing" in _codes(issues)


def test_duplicate_image_warns():
    md = (
        "---\ntitle: 短标题\ndigest: 摘要\n---\n\n"
        "![首图](https://cdn.example.com/hero.png)\n\n"
        "![复用](https://cdn.example.com/hero.png)\n\n正文\n"
    )
    assert "duplicate-image" in _codes(lint_markdown(md))


def test_obsidian_wiki_images_counted():
    """Obsidian ![[x.png]] 图片纳入 alt 缺失与重复引用检查"""
    md = (
        "---\ntitle: 短标题\ndigest: 摘要\n---\n\n"
        "![[a.png]]\n\n![[a.png]]\n\n正文\n"
    )
    codes = _codes(lint_markdown(md))
    assert "image-alt-missing" in codes   # 无别名 -> alt 缺失
    assert "duplicate-image" in codes     # 同图重复引用


def test_obsidian_wiki_image_with_alias_has_alt():
    """带别名的 wiki 图片视为已有 alt，不报缺失"""
    md = (
        "---\ntitle: 短标题\ndigest: 摘要\n---\n\n"
        "![[a.png|架构说明]]\n\n正文\n"
    )
    assert "image-alt-missing" not in _codes(lint_markdown(md))


# ---------------------------------------------------------------------------
# 波次一 (v1.9.0)：Lint 规则扩充
# ---------------------------------------------------------------------------
def _clean(body, title="短标题", digest="合格摘要内容", extra=""):
    return f"---\ntitle: {title}\ndigest: {digest}\n{extra}---\n\n{body}"


def test_punctuation_mixed_detected_with_full_width_suggestion():
    issues = lint_markdown(_clean("这是中文,混用半角标点;还有冒号:测试。\n"))
    item = next(i for i in issues if i["code"] == "punctuation-mixed")
    assert item["level"] == "warn"
    assert "「,」" in item["message"]
    assert "「，」" in item["message"]
    assert "全角" in item["message"]


def test_punctuation_in_code_fence_and_inline_code_ignored():
    md = _clean("`a,b:c` 与代码块不检测。\n\n```text\n中文,半角;标点\n```\n")
    assert "punctuation-mixed" not in _codes(lint_markdown(md))


def test_punctuation_in_link_target_ignored():
    md = _clean("跳转到 [章节](#一级,标题) 不应误报。\n")
    assert "punctuation-mixed" not in _codes(lint_markdown(md))


def test_punctuation_cjk_parenthesis_detected():
    md = _clean("中文正文里的括号(示例)被检出。\n")
    assert "punctuation-mixed" in _codes(lint_markdown(md))


def test_title_punctuation_trailing_period_warns():
    md = _clean("正文。\n", title="标题以句号结尾。")
    assert "title-punctuation" in _codes(lint_markdown(md))


def test_title_half_width_punctuation_warns():
    md = _clean("正文。\n", title="标题混用(半角)")
    assert "title-punctuation" in _codes(lint_markdown(md))


def test_digest_punctuation_warns():
    md = _clean("正文。\n", digest="摘要混用半角逗号,触发规则")
    assert "digest-punctuation" in _codes(lint_markdown(md))


def test_emoji_detected_and_code_fence_ignored():
    issues = lint_markdown(_clean("正文里有一个表情 😀。\n"))
    assert "emoji-banned" in _codes(issues)
    md = _clean("```text\n😀\n```\n")
    assert "emoji-banned" not in _codes(lint_markdown(md))


def test_unclosed_html_tag_is_error():
    issues = lint_markdown(_clean("<div>未闭合容器\n"))
    item = next(i for i in issues if i["code"] == "html-unclosed")
    assert item["level"] == "error"
    assert has_errors(issues)


def test_closed_html_tag_and_code_fence_ok():
    assert "html-unclosed" not in _codes(lint_markdown(_clean("<div>闭合</div>\n")))
    assert "html-unclosed" not in _codes(lint_markdown(_clean("```html\n<div>\n```\n")))


def test_link_format_invalid_protocol_and_missing_scheme():
    md = _clean("[坏协议](htp://example.com) 与 [缺协议](www.example.com) 以及 [空]()\n")
    issues = [i for i in lint_markdown(md) if i["code"] == "link-format-invalid"]
    assert len(issues) == 3


def test_link_format_valid_links_not_flagged():
    md = _clean("[官网](https://example.com) [邮件](mailto:a@b.com) [锚点](#小节)\n")
    assert "link-format-invalid" not in _codes(lint_markdown(md))


def test_issue_carries_line_number():
    md = "---\ntitle: 短标题\ndigest: 摘要\n---\n\n正文。\n\n表情 😀\n"
    item = next(i for i in lint_markdown(md) if i["code"] == "emoji-banned")
    assert item["line"] == 8


def test_summarize_counts():
    from md2wx.linter import summarize

    issues = lint_markdown(_clean("正文,混用。\n", title="超" * 21))
    counts = summarize(issues)
    assert counts["errors"] == 1
    assert counts["warnings"] >= 1

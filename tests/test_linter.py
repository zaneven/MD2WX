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

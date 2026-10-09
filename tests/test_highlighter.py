"""MD2WX 语法高亮引擎单元测试"""
from md2wx.highlighter import highlight_code


def test_plain_text_not_tokenized():
    """text/plain/空语言不做词法拆分，避免 ASCII 树被染色"""
    code = "├── a.txt\n└── b/ c - d.txt"
    out = highlight_code(code, "text")
    assert "<span" not in out
    assert out == highlight_code(code, "") == highlight_code(code, "plain")


def test_python_keywords_strings_comments():
    code = 'def foo():\n    # 注释\n    s = "bar"\n    return s'
    out = highlight_code(code, "python")
    assert 'color: #f472b6' in out          # keyword
    assert 'font-style: italic' in out      # comment
    assert 'color: #34d399' in out          # string


def test_html_entities_escaped():
    """& < > " 均需转义，防止破坏 HTML 结构"""
    code = 'x = "a & <b> \\"c\\""'
    out = highlight_code(code, "python")
    assert "&amp;" in out
    assert "&lt;" in out
    assert "&quot;" in out
    assert "<b>" not in out.replace("&lt;", "")


def test_url_protocol_not_commented():
    """https:// 协议双斜杠不应被染成注释色"""
    code = "const url = 'https://example.com/a';"
    out = highlight_code(code, "javascript")
    # 字符串整体为 string 色，https 不得落入 comment span
    comment_part = out.split('font-style: italic')
    assert len(comment_part) == 1  # 无注释片段


def test_function_and_operator_colors():
    code = "foo(1 + 2)"
    out = highlight_code(code, "javascript")
    assert 'color: #a78bfa' in out  # function
    assert 'color: #94a3b8' in out  # operator
    assert 'color: #fbbf24' in out  # number


def test_sql_case_insensitive_keywords():
    out = highlight_code("select id from users", "sql")
    assert 'color: #f472b6' in out


def test_unknown_lang_fallback_keywords():
    out = highlight_code("function go() { return 1; }", "rust")
    assert "function" in out and "span" in out

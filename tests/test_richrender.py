"""MD2WX 富文本块渲染引擎 (richrender) 单元测试 (不依赖无头浏览器)"""
import base64
from unittest.mock import patch

from md2wx.richrender import (
    extract_rich_blocks,
    rehost_data_uri_images,
    resolve_rich_blocks,
    substitute_rich_html,
)


def test_extract_mermaid_fence():
    md = "# T\n\n```mermaid\ngraph TD; A-->B;\n```\n\n正文\n"
    md2, blocks = extract_rich_blocks(md)
    assert len(blocks) == 1
    assert blocks[0]["kind"] == "mermaid"
    assert blocks[0]["display"] is True
    assert blocks[0]["content"] == "graph TD; A-->B;"
    assert blocks[0]["token"] in md2
    assert "mermaid" not in md2  # 围栏整体被替换


def test_extract_math_block_multiline():
    md = "前文\n\n$$\nx = a + b\ny = c\n$$\n\n后文\n"
    md2, blocks = extract_rich_blocks(md)
    assert len(blocks) == 1
    assert blocks[0]["kind"] == "math"
    assert blocks[0]["display"] is True
    assert "x = a + b" in blocks[0]["content"]


def test_extract_inline_math_and_price_safety():
    md = "质能方程 $E=mc^2$ 很有名，但价格 $100 and $200 不该被误判。"
    md2, blocks = extract_rich_blocks(md)
    assert len(blocks) == 1
    assert blocks[0]["content"] == "E=mc^2"
    assert blocks[0]["display"] is False
    # 价格文本原样保留
    assert "$100 and $200" in md2


def test_math_inside_code_fence_untouched():
    md = "```\n Cost: $a + $b\n```\n\n$ x $\n"
    md2, blocks = extract_rich_blocks(md)
    assert "$a + $b" in md2  # 围栏内容不被抽取
    # 行内公式要求 $ 后非空白，"$ x $" 不构成公式
    assert blocks == []


def test_unclosed_math_block_restored():
    md = "正文\n\n$$\n未闭合公式\n"
    md2, blocks = extract_rich_blocks(md)
    assert blocks == []
    assert "$$" in md2 and "未闭合公式" in md2


def test_substitute_rich_html():
    blocks = [{"token": "@@MDMATH_0@@", "kind": "math", "content": "x", "display": False, "html": "<b>X</b>"}]
    assert substitute_rich_html("a @@MDMATH_0@@ b", blocks) == "a <b>X</b> b"


def test_resolve_fallback_without_browser():
    """无无头浏览器时安全降级为代码块文本形态，绝不抛异常"""
    blocks = [{"token": "@@MDMERMAID_0@@", "kind": "mermaid", "content": "graph TD; A-->B;", "display": True}]
    with patch("md2wx.richrender.find_headless_browser", return_value=None):
        resolve_rich_blocks(blocks)
    assert "data_uri" not in blocks[0]
    assert "<pre" in blocks[0]["html"]
    assert "--&gt;" in blocks[0]["html"]  # 降级为代码块且已转义


def test_rehost_data_uri_images():
    def fake_upload(token, data, filename, mime):
        assert data == base64.b64decode("aGVsbG8=")
        return "http://mmbiz.qpic.cn/new"

    html = '<p>x</p><img src="data:image/png;base64,aGVsbG8=" alt="f" />'
    with patch("md2wx.uploader.upload_image_bytes_to_wechat_cdn", side_effect=fake_upload):
        out, ok, fail = rehost_data_uri_images("TOKEN", html)
    assert ok == 1 and fail == 0
    assert 'src="http://mmbiz.qpic.cn/new"' in out

    with patch(
        "md2wx.uploader.upload_image_bytes_to_wechat_cdn",
        side_effect=RuntimeError("boom"),
    ):
        out, ok, fail = rehost_data_uri_images("TOKEN", html)
    assert ok == 0 and fail == 1
    assert "data:image/png;base64,aGVsbG8=" in out  # 失败保留原样

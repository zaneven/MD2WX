"""
MD2WX 动态主题封面渲染引擎单元测试
"""
import os
import unittest
from unittest import mock

from md2wx.cover import (
    build_cover_meta,
    build_cover_html,
    find_headless_browser,
    render_article_cover_png,
    THEME_COVER_PRESETS,
)


class TestDynamicCover(unittest.TestCase):

    def test_build_cover_meta_defaults_and_slicing(self):
        """测试封面元数据汇聚：主题预设填充、超长截断与自定义标签拼接"""
        meta = build_cover_meta("acid-bold")
        # 未提供字段时使用主题预设与兜底文案
        self.assertEqual(meta["badge"], "ACID BOLD")
        self.assertEqual(meta["vol"], "VOL.02 // POP")
        self.assertEqual(meta["tag"], "态度发声 · 拒绝平庸")
        self.assertTrue(meta["title"])

        # 超长字段按 Web Studio 同款上限截断
        long_meta = build_cover_meta(
            "tech-blue", title="长" * 50, digest="摘" * 80, author="作" * 30,
            tags=["架构", "微信", "排版"],
        )
        self.assertEqual(len(long_meta["title"]), 36)
        self.assertEqual(len(long_meta["digest"]), 60)
        self.assertEqual(len(long_meta["author"]), 16)
        self.assertEqual(long_meta["tag"], "架构 · 微信 · 排版")

    def test_build_cover_html_theme_visuals(self):
        """测试封面 HTML 包含主题视觉锚点与文章元数据，且全部转义安全"""
        html = build_cover_html("acid-bold", build_cover_meta(
            "acid-bold", title="标题<script>", digest="摘要", author="作者"
        ))
        self.assertIn("cover-theme-acid-bold", html)
        self.assertIn("ratio-banner", html)
        self.assertIn("ACID BOLD", html)
        self.assertIn("标题&lt;script&gt;", html)  # XSS/实体转义
        self.assertNotIn("<script>", html)
        # 极客终端主题包含窗口控制条元素，其余主题不包含 (CSS 规则全主题共享)
        term_html = build_cover_html("terminal-geek", build_cover_meta("terminal-geek"))
        self.assertIn('<div class="term-window-controls">', term_html)
        self.assertNotIn('<div class="term-window-controls">', html)
        # 微信生态绿包含官方认证徽标
        green_html = build_cover_html("wechat-green", build_cover_meta("wechat-green"))
        self.assertIn("wechat-verify-badge", green_html)
        # 未知主题回退 tech-blue 预设
        fallback_meta = build_cover_meta("not-exist-theme")
        self.assertEqual(fallback_meta["badge"], THEME_COVER_PRESETS["tech-blue"]["badgeText"])

    def test_render_graceful_fallback_without_browser(self):
        """测试无可用无头浏览器时安全返回 None (调用方回退静态封面)"""
        with mock.patch.dict(os.environ, {"MD2WX_BROWSER": "/definitely/not/a/browser"}), \
             mock.patch("md2wx.cover.find_headless_browser", return_value=None):
            self.assertIsNone(render_article_cover_png("acid-bold", title="T", digest="D"))

    def test_render_returns_png_when_browser_available(self):
        """测试本机存在 Chrome 内核浏览器时真实渲染出 2x 采样 PNG (有浏览器则跳过断言)"""
        if not find_headless_browser():
            self.skipTest("本机未安装 Chrome/Edge/Chromium，跳过真实渲染测试")
        out = render_article_cover_png(
            "tech-blue", title="端到端测试封面", digest="动态渲染摘要", author="测试作者"
        )
        self.assertIsNotNone(out)
        self.assertTrue(os.path.exists(out))
        # PNG 魔数校验
        with open(out, "rb") as f:
            self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")
        # 2x 采样自 1175x500
        self.assertGreater(os.path.getsize(out), 10000)


if __name__ == "__main__":
    unittest.main()

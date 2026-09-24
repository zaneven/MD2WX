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

    def test_dual_cover_html_and_coordinates(self):
        """测试双封面画板结构与裁剪坐标比例数学精度"""
        from md2wx.cover import build_dual_cover_html, WECHAT_CROP_235_1, WECHAT_CROP_1_1

        meta = build_cover_meta("tech-blue", title="测试双封面", digest="测试双封面摘要")
        dual_html = build_dual_cover_html("tech-blue", meta)
        self.assertIn("cover-canvas-dual", dual_html)
        self.assertIn("ratio-banner", dual_html)
        self.assertIn("ratio-square", dual_html)
        self.assertIn("测试双封面", dual_html)

        # 校验坐标格式 X1_Y1_X2_Y2
        c235 = [float(x) for x in WECHAT_CROP_235_1.split("_")]
        c11 = [float(x) for x in WECHAT_CROP_1_1.split("_")]
        self.assertEqual(len(c235), 4)
        self.assertEqual(len(c11), 4)

        # 归一化区间在 0 到 1 之间
        for val in c235 + c11:
            self.assertTrue(0.0 <= val <= 1.0)

        # 比例精度验证 (基于总宽 3350, 总高 1000)
        w_banner = (c235[2] - c235[0]) * 3350
        h_banner = (c235[3] - c235[1]) * 1000
        ratio_banner = w_banner / h_banner
        self.assertAlmostEqual(ratio_banner, 2.35, places=3)

        w_square = (c11[2] - c11[0]) * 3350
        h_square = (c11[3] - c11[1]) * 1000
        ratio_square = w_square / h_square
        self.assertAlmostEqual(ratio_square, 1.0, places=3)

    def test_render_dual_cover_png(self):
        """测试双比例合拼封面真实渲染 (3350x1000 像素)"""
        from md2wx.cover import render_article_dual_cover_png, WECHAT_CROP_235_1, WECHAT_CROP_1_1
        if not find_headless_browser():
            self.skipTest("本机未安装 Chrome/Edge/Chromium，跳过真实渲染测试")

        res = render_article_dual_cover_png("tech-blue", title="双比例封面单测", digest="双比例封面摘要")
        self.assertIsNotNone(res)
        out_path, crop_235, crop_11 = res
        self.assertTrue(os.path.exists(out_path))
        self.assertEqual(crop_235, WECHAT_CROP_235_1)
        self.assertEqual(crop_11, WECHAT_CROP_1_1)
        with open(out_path, "rb") as f:
            self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")

    def test_stitch_cover_images(self):
        """测试用户指定双图时的拼图合成"""
        import tempfile
        from PIL import Image
        from md2wx.cover import stitch_cover_images

        with tempfile.NamedTemporaryFile(suffix=".png") as f1, tempfile.NamedTemporaryFile(suffix=".png") as f2:
            im1 = Image.new("RGB", (900, 383), (255, 0, 0))
            im1.save(f1.name)
            im2 = Image.new("RGB", (500, 500), (0, 255, 0))
            im2.save(f2.name)

            out = stitch_cover_images(f1.name, f2.name)
            self.assertIsNotNone(out)
            self.assertTrue(os.path.exists(out))
            with Image.open(out) as im_out:
                self.assertEqual(im_out.size, (3350, 1000))


if __name__ == "__main__":
    unittest.main()

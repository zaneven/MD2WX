"""
MD2WX 转换引擎与主题系统单元测试集
"""
import unittest
import tempfile
import json
from pathlib import Path

from md2wx.parser import parse_frontmatter, markdown_to_wechat_html, strip_markdown
from md2wx.themes import list_themes, get_theme, load_theme_file

class TestMD2WXParserAndThemes(unittest.TestCase):

    def test_frontmatter_parsing(self):
        content = """---
title: 测试文章
author: 极客小哥
tags: [python, wechat]
---

# 正文标题

这里是正文段落。
"""
        meta, body = parse_frontmatter(content)
        self.assertEqual(meta.get("title"), "测试文章")
        self.assertEqual(meta.get("author"), "极客小哥")
        self.assertEqual(meta.get("tags"), ["python", "wechat"])
        self.assertIn("# 正文标题", body)

    def test_continuous_blockquote_aggregation(self):
        """测试多行连续引文是否被合并在同一个 blockquote 容器内，绝不断开"""
        md = """> **作者**：野生宝藏箱
> **核心标签**：AI 自动化 · WePost
> **一句话简介**：从热点抓取到静默同步。
"""
        html = markdown_to_wechat_html(md)
        self.assertEqual(html.count("<blockquote"), 1)
        self.assertEqual(html.count("</blockquote>"), 1)
        self.assertIn("<strong>作者</strong>：野生宝藏箱", html)
        self.assertIn("<strong>核心标签</strong>", html)

    def test_mac_code_block_rendering(self):
        """测试默认科技主题下代码块是否生成 Mac 红黄绿圆点指示灯，以及换行/缩进的自包含结构"""
        md = """```python
def hello():
    return "wechat"
```"""
        html = markdown_to_wechat_html(md, theme_name="tech-blue")
        self.assertIn("#ef4444", html)
        self.assertIn("#f59e0b", html)
        self.assertIn("#10b981", html)
        self.assertIn("hello", html)
        self.assertIn("wechat", html)
        # 微信白名单安全换行结构: 换行 -> <br>，缩进空格 -> &nbsp;，pre 内不再依赖裸换行
        self.assertIn("<br>", html)
        self.assertNotIn("\n", html.split("<code>")[1].split("</code>")[0])

    def test_table_rendering(self):
        """测试 Markdown 表格解析与斑马纹样式"""
        md = """| 项目 | 说明 |
| :--- | :--- |
| WePost | 卡片生成器 |
| MD2WX | 微信排版工具 |
"""
        html = markdown_to_wechat_html(md, theme_name="tech-blue")
        self.assertIn("<table", html)
        self.assertIn("<th", html)
        self.assertIn("<td", html)
        self.assertIn("WePost", html)

    def test_image_caption_and_mapping(self):
        """测试图片图注与微信 CDN 换链映射"""
        md = """![架构图](assets/arch.png)
*▲ 图：全自动流水线架构全貌*
"""
        image_map = {"assets/arch.png": "http://mmbiz.qpic.cn/sz_mmbiz_png/mock_hash/0?wx_fmt=png"}
        html = markdown_to_wechat_html(md, image_map=image_map)
        self.assertIn("http://mmbiz.qpic.cn/sz_mmbiz_png/mock_hash/0?wx_fmt=png", html)
        self.assertNotIn("assets/arch.png", html)
        self.assertIn("▲ 图：全自动流水线架构全貌", html)

    def test_strip_markdown_digest(self):
        """测试纯文本摘要提取"""
        md = "# 标题\n\n这是**加粗文字**与`代码`。[链接](http://example.com)"
        digest = strip_markdown(md, 50)
        self.assertNotIn("#", digest)
        self.assertNotIn("*", digest)
        self.assertNotIn("`", digest)
        self.assertIn("这是加粗文字与代码", digest)

    # ==========================================================================
    # 多主题与多风格化测试
    # ==========================================================================

    def test_all_builtin_themes_loadable_and_renderable(self):
        """测试所有内置主题均可被加载并无异常完成完整文档渲染"""
        themes = list_themes()
        self.assertGreaterEqual(len(themes), 7)
        self.assertIn("tech-blue", themes)
        self.assertIn("vintage-news", themes)
        self.assertIn("terminal-geek", themes)
        self.assertIn("warm-memo", themes)
        self.assertIn("acid-bold", themes)
        self.assertIn("wechat-green", themes)
        self.assertIn("elegant-purple", themes)

        sample_md = """# 主标题
## 分区标题
### 小标题
> 引言内容
- 列表 1
- 列表 2

```bash
echo hello
```

| A | B |
|---|---|
| 1 | 2 |
"""
        for theme_id in themes.keys():
            html = markdown_to_wechat_html(sample_md, theme_name=theme_id)
            self.assertTrue(len(html) > 100)
            self.assertIn("主标题", html)
            self.assertIn("分区标题", html)
            self.assertIn("引言内容", html)

    def test_vintage_news_theme_features(self):
        """测试复古报刊风格的特色渲染：双细线H1、学术三线表、大引号名言"""
        md = """# 独立思考的艺术
## 第一章 深度沉思
> 真正的自由来自内心的秩序。

| 学派 | 核心命题 |
| :--- | :--- |
| 斯多葛 | 控制你能控制的 |
"""
        html = markdown_to_wechat_html(md, theme_name="vintage-news")
        # 1. 衬线体
        self.assertIn("Songti SC", html)
        # 2. 纸质底色
        self.assertIn("#fdfbf7", html)
        # 3. 引用大引号
        self.assertIn("“", html)
        self.assertIn("”", html)
        # 4. 学术三线表 (顶线粗)
        self.assertIn("border-top: 2px solid #854d0e", html)
        self.assertIn("border-bottom: 2px solid #854d0e", html)

    def test_terminal_geek_theme_features(self):
        """测试极客终端风格的特色渲染：全黑底、命令行提示符与终端状态栏"""
        md = """# KUBERNETES DEPLOYMENT
## CLUSTER SETUP
> Pod deployment completed.

```yaml
apiVersion: v1
kind: Pod
```
"""
        html = markdown_to_wechat_html(md, theme_name="terminal-geek")
        # 1. 深邃黑底
        self.assertIn("#0b0f19", html)
        # 2. 终端提示符
        self.assertIn("$ cat article.md", html)
        self.assertIn("//", html)
        # 3. 终端状态栏
        self.assertIn("● RUNNING", html)
        # 4. 青绿发光色
        self.assertIn("#10b981", html)

    def test_warm_memo_theme_features(self):
        """测试温暖便签风格：胶囊色块与日系NOTE便签引用"""
        md = """# 晨间随想
## 今日治愈瞬间
> 在阳台看日出，咖啡很香。
"""
        html = markdown_to_wechat_html(md, theme_name="warm-memo")
        # 1. 胶囊圆角
        self.assertIn("border-radius: 30px", html)
        # 2. 便签NOTE标识
        self.assertIn("NOTE // 便签", html)
        # 3. 暖杏色底
        self.assertIn("#fefcf8", html)

    def test_acid_bold_theme_features(self):
        """测试先锋野兽派风格：粗黑框与纯黑硬投影"""
        md = """# ATTITUDE YOUTH
## NO COMPROMISE
> 保持真实，打破规则。
"""
        html = markdown_to_wechat_html(md, theme_name="acid-bold")
        # 粗黑边框与纯黑硬投影
        self.assertIn("2.5px solid #000000", html)
        self.assertIn("4px 4px 0 #000000", html)

    def test_extract_quote_text_digest(self):
        """测试正文首个引言块提取摘要：剥离修饰符、超长截断、无引言返回空串"""
        from md2wx.parser import extract_quote_text
        md = """# 标题

正文段落。

> **真正的专注**，是在充满干扰的世界中守住内心的秩序。

后续正文。
"""
        self.assertEqual(extract_quote_text(md), "真正的专注，是在充满干扰的世界中守住内心的秩序。")
        self.assertEqual(extract_quote_text("没有引言的内容"), "")
        self.assertEqual(extract_quote_text("> " + "长" * 200, max_len=10), "长" * 10)

    def test_builtin_theme_covers_packaged(self):
        """测试所有内置主题均有随包分发的默认封面图，自定义主题则安全返回 None"""
        from md2wx.themes import get_builtin_theme_cover
        for theme_id in ["tech-blue", "terminal-geek", "acid-bold", "vintage-news",
                         "warm-memo", "warm-orange", "dark-night", "elegant-purple", "wechat-green"]:
            cover = get_builtin_theme_cover(theme_id)
            self.assertIsNotNone(cover, f"主题 {theme_id} 缺少内置默认封面")
            self.assertTrue(cover.exists())
            self.assertEqual(cover.suffix, ".png")
        # 自定义/未知主题与空标识无内置封面
        self.assertIsNone(get_builtin_theme_cover("my-custom-theme"))
        self.assertIsNone(get_builtin_theme_cover(""))

    def test_plain_text_code_block_not_tokenized(self):
        """测试 text/plain/无语言代码块不做词法高亮拆分，保持 ASCII 目录树纯文本完整性"""
        tree_md = """```text
public/
├── 数据大屏/
│   └── 看板.html
└── 报告/
```"""
        html = markdown_to_wechat_html(tree_md, theme_name="acid-bold")
        # 目录树字符完整保留，缩进空格转为 &nbsp;，未被包裹彩色 span
        self.assertIn("├──&nbsp;数据大屏/", html)
        self.assertIn("└──&nbsp;报告/", html)
        self.assertIn("<br>", html)
        self.assertNotIn('<span style="color: #94a3b8;">/</span>', html)
        # 编程语言仍正常高亮
        code_html = markdown_to_wechat_html("```python\ndef hi(): pass\n```", theme_name="acid-bold")
        self.assertIn("<span", code_html)

    def test_custom_theme_file_loading_and_fallback(self):
        """测试从外部临时 JSON 文件直接加载并应用主题，以及部分字段缺失时的自动深度兜底"""
        custom_theme_data = {
            "name": "我的专属樱花粉",
            "colors": {
                "accent": "#ec4899",
                "accent_bg": "#fdf2f8",
            }
            # 故意缺少 typography、styles、border_color 等
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(custom_theme_data, f)
            temp_path = f.name

        try:
            theme = get_theme(temp_path)
            self.assertEqual(theme["accent"], "#ec4899")
            self.assertEqual(theme["colors"]["accent_bg"], "#fdf2f8")
            # 验证缺失字段被自动安全兜底
            self.assertIn("border_color", theme)
            self.assertIn("typography", theme)
            self.assertIn("styles", theme)
            self.assertEqual(theme["styles"]["h1"], "underline")

            # 验证可以用该临时文件路径直接渲染 Markdown
            md = "# 樱花盛开\n\n正文段落。"
            html = markdown_to_wechat_html(md, theme_name=temp_path)
            self.assertIn("#ec4899", html)
            self.assertIn("樱花盛开", html)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_html_tag_escaping_in_inline_code(self):
        """测试代码中的 <style> 等 HTML 标签必须被安全转义为 &lt;style&gt;，防止微信截断文章"""
        md = "- 对 `<style>` 标签与 `<script>` 的防御，还有 `<blockquote>` 和 `a < b`"
        html = markdown_to_wechat_html(md)
        self.assertIn("&lt;style&gt;", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&lt;blockquote&gt;", html)
        self.assertIn("a &lt; b", html)
        # 确保没有裸露的 <style>
        self.assertNotIn("<style>", html)
        self.assertNotIn("<script>", html)

    def test_bold_inline_with_quotes_and_asterisks(self):
        """测试加粗遇到单引号、双引号以及容错避免跨段误吞"""
        md = "测试 **'单引号'** 与 **“中文双引号”**，还有多余星号容错：**加粗1**。**** 中间普通文本 **加粗2**"
        html = markdown_to_wechat_html(md)
        self.assertIn("<strong>'单引号'</strong>", html)
        self.assertIn("<strong>“中文双引号”</strong>", html)
        self.assertIn("<strong>加粗1</strong>", html)
        self.assertIn("<strong>加粗2</strong>", html)
        self.assertNotIn("<strong> 中间普通文本", html)

if __name__ == "__main__":
    unittest.main()


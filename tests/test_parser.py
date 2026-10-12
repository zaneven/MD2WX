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
        # 横向滚动由 div 包裹层承载 (微信剥离 pre 自身的 overflow-x)
        self.assertIn('overflow-x: auto; -webkit-overflow-scrolling: touch;', html)

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
                         "warm-memo", "warm-orange", "dark-night", "elegant-purple", "wechat-green",
                         "forest-green", "terracotta-clay", "morandi-mist", "pastel-cream"]:
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


class TestMarkdownFullSyntax(unittest.TestCase):
    """CommonMark + GFM + 扩展语法完整支持测试 (v1.5.0)"""

    def _render(self, md: str) -> str:
        return markdown_to_wechat_html(md, "tech-blue", insert_cover=False)

    def test_paragraph_merging_cjk_and_ascii(self):
        html = self._render("第一行文字\n第二行文字")
        self.assertIn("<p", html)
        self.assertIn("第一行文字第二行文字", html)
        html2 = self._render("english words\nnext line")
        self.assertIn("english words next line", html2)

    def test_hard_break_two_spaces_and_backslash(self):
        html = self._render("行尾两空格  \n下一行。")
        self.assertIn("<br />", html)
        html2 = self._render("行尾反斜杠\\\n下一行。")
        self.assertIn("<br />", html2)

    def test_setext_headings(self):
        html = self._render("标题一\n===\n\n标题二\n---")
        self.assertIn("标题一", html)
        self.assertIn("标题二", html)
        # --- 独立出现仍为分割线
        html2 = self._render("---")
        self.assertIn("<hr", html2)

    def test_hr_variants(self):
        for marker in ["----", "* * *", "- - -", "____"]:
            self.assertIn("<hr", self._render(marker), marker)

    def test_tilde_fences(self):
        html = self._render("~~~python\nprint(1)\n~~~")
        self.assertIn("print", html)
        html2 = self._render("````\ncode with ``` inside\n````")
        self.assertIn("code&nbsp;with", html2)

    def test_single_tilde_strikethrough(self):
        """GFM 单波浪删除线 ~text~ 与双波浪 ~~text~~ 均转为 del"""
        html = self._render("~单波浪删除~ 与 ~~双波浪删除~~")
        self.assertIn("<del", html)
        self.assertEqual(html.count("<del"), 2)
        # 空白相邻不成删除线
        html2 = self._render("a ~ b ~ c")
        self.assertNotIn("<del", html2)

    def test_heading_levels_and_inline_format(self):
        html = self._render("# 一级\n## 二级\n### 三级\n#### 四级\n##### 五级\n###### 六级")
        self.assertIn("一级", html)
        self.assertIn("六级", html)
        html2 = self._render("## 标题含 **加粗** 与 [链接](https://x.io/a)")
        self.assertIn("<strong>加粗</strong>", html2)

    def test_ordered_lists_preserve_number(self):
        html = self._render("1. 第一\n2. 第二\n5. 第五")
        self.assertIn(">1.</span>", html.replace(" ", ""))
        self.assertIn(">5.</span>", html.replace(" ", ""))

    def test_plus_marker_list(self):
        html = self._render("+ 加号项")
        self.assertIn("加号项", html)
        self.assertIn("•", html)

    def test_nested_lists_indentation(self):
        md = "- 顶级\n  - 子级\n    - 三级"
        html = self._render(md)
        self.assertEqual(html.count("padding-left: 16px"), 2)

    def test_ordered_nested_and_mixed(self):
        md = "1. 父项\n   1. 子有序\n   - 子无序"
        html = self._render(md)
        self.assertIn("父项", html)
        self.assertIn("子有序", html)
        self.assertIn("子无序", html)

    def test_task_in_ordered_list(self):
        md = "1. [x] 已完成步骤"
        html = self._render(md)
        self.assertIn("<svg", html)
        self.assertIn("已完成步骤", html)

    def test_indented_code_block(self):
        md = "段落前空行\n\n    code line one\n    code line two"
        html = self._render(md)
        self.assertIn("code&nbsp;line&nbsp;one", html)

    def test_nested_blockquotes(self):
        html = self._render("> 外层\n>> 内层")
        self.assertGreaterEqual(html.count("<blockquote"), 2)
        self.assertIn("内层", html)

    def test_table_alignment_and_escaped_pipe(self):
        md = "| A | B | C |\n| :--- | :---: | ---: |\n| 左 | 中 | 右 |"
        html = self._render(md)
        self.assertIn("text-align: center;", html)
        self.assertIn("text-align: right;", html)
        html2 = self._render("| 语法 |\n| --- |\n| a \\| b |")
        self.assertIn("<td", html2)

    def test_reference_links_and_images(self):
        md = "见 [手册][m] 与 [m] 折叠；图 ![图标][i]。\n\n[m]: https://ref.io/manual\n[i]: https://ref.io/logo.png"
        html = self._render(md)
        self.assertIn("[1]", html)
        self.assertIn('<img src="https://ref.io/logo.png"', html)
        self.assertNotIn("[m]:", html)
        self.assertNotIn("[i]:", html)

    def test_footnote_syntax(self):
        md = "引用[^1]与[^note]。\n\n[^1]: 第一条说明\n[^note]: 第二条说明"
        html = self._render(md)
        self.assertIn("[1]", html)
        self.assertIn("[2]", html)
        self.assertIn("第一条说明", html)
        self.assertNotIn("[^1]:", html)

    def test_backslash_escapes(self):
        html = self._render("\\*不是斜体\\* 与 1\\. 不是列表")
        self.assertNotIn("<em>", html)
        self.assertIn("不是斜体", html)

    def test_entity_passthrough(self):
        html = self._render("版权 &copy; 与 &amp; 和 &#123;")
        self.assertIn("&copy;", html)
        self.assertNotIn("&amp;copy;", html)
        self.assertNotIn("&amp;amp;", html)

    def test_html_whitelist(self):
        html = self._render("<b>粗</b> <u>下划</u> <mark>标</mark> <script>evil</script> <kbd>键</kbd>")
        self.assertIn("<b>粗</b>", html)
        self.assertIn("<u>下划</u>", html)
        self.assertIn("<mark>标</mark>", html)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<kbd>", html)

    def test_mark_highlight(self):
        html = self._render("重点==高亮内容==结束")
        self.assertIn("<mark", html)
        self.assertIn("高亮内容", html)

    def test_double_backtick_code(self):
        html = self._render("``内含 ` 井号`` 结束")
        self.assertIn("<code", html)
        self.assertIn("内含", html)

    def test_inline_image(self):
        html = self._render("段落中 ![小图](https://cdn.example.com/x.png) 内嵌")
        self.assertIn("<img", html)
        self.assertIn("内嵌", html)

    def test_angle_autolink(self):
        html = self._render("访问 <https://auto.io/x> 与 <mail@test.io>")
        self.assertIn("auto.io/x", html)
        self.assertIn("mail@test.io", html)
        self.assertNotIn("&lt;https", html)

    def test_intraword_underscore_not_emphasized(self):
        html = self._render("变量 foo_bar_baz 保持原样")
        self.assertNotIn("<em>", html)

    def test_link_to_footnote_false_still_footnote_refs(self):
        md = "脚注[^1]引用。\n\n[^1]: 说明文字"
        html = markdown_to_wechat_html(md, "tech-blue", insert_cover=False, link_to_footnote=False)
        self.assertIn("说明文字", html)
        self.assertNotIn("[^1]:", html)

    def test_rich_token_not_joined_into_paragraph(self):
        md = "段落文字\n@@MDMERMAID_0@@\n继续段落"
        html = markdown_to_wechat_html(md, "tech-blue", insert_cover=False, rich_blocks=[{"token": "@@MDMERMAID_0@@", "display": True, "html": "<div>RICH</div>"}])
        self.assertIn("<div>RICH</div>", html)
        self.assertIn("段落文字", html)
        self.assertIn("继续段落", html)
        self.assertNotIn("段落文字继续段落", html)


if __name__ == "__main__":
    unittest.main()


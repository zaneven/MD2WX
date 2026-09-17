<div align="center">

<img src="assets/logo.svg" alt="MD2WX Logo" width="112" height="112" style="margin-bottom: 8px;" />

# MD2WX (Markdown to WeChat)

**专为微信公众号深度定制的 Markdown 高质感排版转换器与草稿箱发布工具**

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Online Studio](https://img.shields.io/badge/Online_Studio-md2wx.zaneven.com-0284c7?style=flat-square&logo=googlechrome&logoColor=white)](https://md2wx.zaneven.com/)
[![License MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Tests Passing](https://img.shields.io/badge/Tests-Passing-brightgreen?style=flat-square)](tests/)

</div>

---

## 解决的痛点

微信公众平台的富文本编辑器由于安全与排版限制，存在诸多严苛规则：
- **过滤所有 `<style>` 标签与外部 CSS**：任何常规 Markdown 转换器输出的类名样式全部失效；
- **等宽字符画在手机端严重错乱**：ASCII 架构图在手机窄屏浏览时经常被强制折行、中英全半角错位；
- **连续引言被强行割裂**：标准 Markdown 的连续 `> ` 引文行常被分割为多个独立的小框，断断续续；
- **外部图片防盗链破图**：未经微信 CDN 换链的图片，在图文内经常变红叉；
- **千篇一律的排版风格**：传统工具通常只换 accent 强调色，缺乏如杂志、报刊、便签、极客终端等鲜明的视觉风格骨架。

**MD2WX** 是一个**零冗余外部依赖**的专用命令行工具与 Python 库，能够把标准 Markdown 一键转换为**纯 Inline CSS 内联样式的微信精美排版**，并拥有**文件驱动的多视觉风格化主题引擎**（对标 WePost 卡片级风格差异），支持剪贴板富文本注入与草稿箱一键发布。

---

## 核心特性

- **极致纯净的纯 Inline Style 注入**：绕过微信编辑器对 `<style>` 的封杀，每一个标签均物理内嵌高质感 CSS 属性；
- **组件化风格排版引擎 (Component Styles)**：支持按主题选择不同的容器模式、H1/H2 标题形态、大引号名言、学术三线表、日系便签、终端命令行等，呈现截然不同的版面骨架；
- **标准主题文件解耦 (Theme Files)**：所有主题均抽象为独立的 `.json` 文件，支持内置自动发现、用户目录扩展与指定外部 JSON 运行；
- **连续多行引文聚合器**：智能聚合连续的 `> ` 引文行，合成连贯带主题色边条的「文章导读/元信息卡片」，彻底消除割裂感；
- **Mac 终端三色指示灯代码框**：红黄绿小圆点装饰、右上角语言标签、深色背景与等宽字体；
- **微信官方 CDN 自动搬运换链**：调用官方 `media/uploadimg` 接口把本地相对路径图片自动上传并替换为永久官方 CDN 地址；
- **macOS 原生剪贴板富文本注入（`--clip`）**：直接以 `«class HTML»` 富文本写入系统剪贴板，在公众号后台按 **Cmd+V** 即可直接贴入排版；
- **微信公众平台草稿箱一键推送（`--publish`）**：支持自动绑定封面、生成带样式草稿，并返回微信官方临时预览链接。

---

## 快速安装

克隆仓库后在本地以可编辑模式安装：

```bash
git clone https://github.com/zaneven/MD2WX.git
cd MD2WX
pip install -e .
```

安装完成后，即可在任何终端使用 `md2wx` 命令行工具或启动 Web 工作台。

---

## Web 可视化排版工作台 (MD2WX Studio)

除了命令行外，MD2WX 还提供了**纯前端驱动的可视化排版工作台**。在网页端直接粘贴 Markdown 文本，即可享受即时渲染、主题切换、微信外链自动转文末脚注、内联代码彩色语法高亮、双栏联动同步滚动与移动端真机仿真。

🌐 **在线免安装体验**：**[https://md2wx.zaneven.com](https://md2wx.zaneven.com)**

<div align="center">
  <img src="assets/web_studio_preview.png" alt="MD2WX Web Studio" width="100%" style="border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.25);" />
</div>

### 启动工作台

只需一行命令即可在本地启动并自动打开浏览器：

```bash
md2wx --web
```

或直接进入 `web/` 目录运行：

```bash
cd web
npm install
npm run dev
```

### Web 端核心亮点
- **纯前端零延迟响应**：内置纯 JavaScript 解析引擎，本地打字毫秒级无感知实时重绘；
- **iPhone 仿真实机视窗**：真实还原微信公众号在移动端的行距、边距与排版质感，并支持一键切换「全宽桌面视图」；
- **9 套独立视觉骨架主题**：报刊、便签、终端、野兽派、优雅紫等主题即点即换；
- **一键写入微信富文本**：基于原生 Clipboard API 写入 `text/html`，直接在微信公众号后台按 **Cmd + V** 即可保留全部样式；
- **全站纯矢量设计**：严格遵循专业美学标准，杜绝使用 Emoji，全站统一采用精美 SVG 矢量图标。

---

## 命令行用法 (CLI)

### 1. 一键转换富文本并复制到剪贴板（推荐工作流）

无需导出文件，转换后直接按 `Cmd+V` 粘贴进微信公众平台后台：

```bash
md2wx article.md --clip
```

### 2. 查看所有可用主题 (`--list-themes`)

查看内置主题、用户自定义主题及其视觉标签：

```bash
md2wx --list-themes
```

### 3. 选择特定主题排版

不仅是换颜色，更是整体视觉骨架的切换：

```bash
# 使用复古报刊风格（古典双细线 + 学术三线表 + 大引号名言）
md2wx article.md -t vintage-news -c

# 使用极客终端风格（深黑底色 + 等宽字体 + 终端命令标题）
md2wx article.md -t terminal-geek -c

# 使用温暖便签风格（日系奶油色系 + 胶囊色块 + 便签贴纸）
md2wx article.md -t warm-memo -c

# 使用先锋野兽派风格（粗黑实线边框 + 黑色硬投影）
md2wx article.md -t acid-bold -c
```

### 4. 导出为自包含的 HTML 文件

在浏览器中打开预览并排版：

```bash
md2wx article.md -t vintage-news -o article.html
```

### 5. 一键直推微信公众号草稿箱

配置好微信凭据后，全自动完成图片上传 + 封面绑定 + 提交草稿：

```bash
md2wx article.md --publish --cover assets/cover.png
```

如果未显式指定 `--cover`，工具会自动从 Frontmatter 的 `cover` 字段或正文第一张本地图片推断封面。

### 6. 管道与标准输入流支持

极客友好，与其他命令行工具无缝衔接：

```bash
cat article.md | md2wx -t wechat-green --clip
```

---

## 官方预置视觉主题

MD2WX 官方内置了 9 套风格截然不同的设计主题（均位于 `md2wx/themes/*.json`）：

| 主题代号 | 视觉风格 | 核心视觉组件组合 (Styles) | 推荐场景 |
| :--- | :--- | :--- | :--- |
| `tech-blue` *(默认)* | **现代科技蓝** | 极简容器 + 下划粗线 H1 + 左侧竖条 H2 + Mac 圆点代码框 + 斑马纹表格 | 架构复盘、技术干货、开发者手记 |
| `vintage-news` | **复古报刊** | 米黄纸质底色 + 衬线字体 + 双细线 H1 + 学术三线表 + 典雅大引号名言 | 人文深度长文、书摘精读、文化评论 |
| `terminal-geek` | **极客终端** | 纯黑底色 + 等宽字 + 命令行 H1 + 终端运行状态条代码框 + 回显引用 | Linux/运维笔记、开源发布、黑客范 |
| `warm-memo` | **温暖便签** | 暖杏底色 + 胶囊色块 H1/H2 + 日系 NOTE 便签贴纸 + 荧光笔涂鸦 H3 | 生活感悟、治愈随笔、读书手作 |
| `acid-bold` | **先锋野兽派** | 纯黑粗实线框 + 黑色硬投影 + 粗黑方块列表 + 醒目大色块 | 青年态度、潮流观点、先锋专栏 |
| `elegant-purple` | **先锋优雅紫** | 微阴影悬浮卡片 + 柔和色块 H2 + 气泡卡片引用 + 渐变分割线 | 设计美学、独立思考、产品体验 |
| `dark-night` | **暗黑极客风** | 沉浸深蓝灰底 + 冷冽荧光蓝 + 网格暗色表 + Mac 圆点深黑代码框 | 深夜阅读、极客笔记、沉浸长文 |
| `warm-orange` | **温暖活力橙** | 温暖橙色调 + 下划粗线 H1 + 左条 H2 + 斑马纹表格 | 生活感悟、读书故事、个人随笔 |
| `wechat-green` | **微信生态绿** | 官方微信绿 + 严谨规范排版 + 柔和灰底引用 | 官方发布、行业资讯速递、社群早报 |

---

### 主题预览效果图 (Theme Gallery)

> 点击图片可查看 2x 超清渲染细节，点击链接可直接浏览对应的排版 HTML。

<table>
  <tr>
    <td width="50%" align="center" valign="top">
      <h4>✦ 现代科技蓝 (tech-blue · 默认)</h4>
      <p><i>硅谷现代排版 · 下划粗线 · 左侧竖条 · 斑马纹表格</i></p>
      <a href="assets/previews/tech-blue.png"><img src="assets/previews/tech-blue.png" alt="tech-blue" width="100%" /></a>
      <p><a href="previews/tech-blue.html">预览 HTML</a></p>
    </td>
    <td width="50%" align="center" valign="top">
      <h4>✦ 复古报刊 (vintage-news)</h4>
      <p><i>米黄纸质底色 · 粗衬线体 · 双细线居中 · 学术三线表</i></p>
      <a href="assets/previews/vintage-news.png"><img src="assets/previews/vintage-news.png" alt="vintage-news" width="100%" /></a>
      <p><a href="previews/vintage-news.html">预览 HTML</a></p>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center" valign="top">
      <h4>✦ 极客终端 (terminal-geek)</h4>
      <p><i>深黑底色 · 等宽字体 · 命令行标题 · 运行状态栏代码框</i></p>
      <a href="assets/previews/terminal-geek.png"><img src="assets/previews/terminal-geek.png" alt="terminal-geek" width="100%" /></a>
      <p><a href="previews/terminal-geek.html">预览 HTML</a></p>
    </td>
    <td width="50%" align="center" valign="top">
      <h4>✦ 温暖便签 (warm-memo)</h4>
      <p><i>日系奶油杏黄 · 胶囊色块 · 便签贴纸 · 治愈手作随笔</i></p>
      <a href="assets/previews/warm-memo.png"><img src="assets/previews/warm-memo.png" alt="warm-memo" width="100%" /></a>
      <p><a href="previews/warm-memo.html">预览 HTML</a></p>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center" valign="top">
      <h4>✦ 先锋野兽派 (acid-bold)</h4>
      <p><i>高反差黑框硬投影 · 粗线条色块 · 波普视觉冲击</i></p>
      <a href="assets/previews/acid-bold.png"><img src="assets/previews/acid-bold.png" alt="acid-bold" width="100%" /></a>
      <p><a href="previews/acid-bold.html">预览 HTML</a></p>
    </td>
    <td width="50%" align="center" valign="top">
      <h4>✦ 先锋优雅紫 (elegant-purple)</h4>
      <p><i>现代雅致紫调 · 微阴影悬浮卡片 · 气泡卡片引言</i></p>
      <a href="assets/previews/elegant-purple.png"><img src="assets/previews/elegant-purple.png" alt="elegant-purple" width="100%" /></a>
      <p><a href="previews/elegant-purple.html">预览 HTML</a></p>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center" valign="top">
      <h4>✦ 暗黑极客风 (dark-night)</h4>
      <p><i>沉浸暗黑质感 · 深蓝灰底色 · 冷冽荧光蓝强调色</i></p>
      <a href="assets/previews/dark-night.png"><img src="assets/previews/dark-night.png" alt="dark-night" width="100%" /></a>
      <p><a href="previews/dark-night.html">预览 HTML</a></p>
    </td>
    <td width="50%" align="center" valign="top">
      <h4>✦ 温暖活力橙 (warm-orange)</h4>
      <p><i>温暖活力橙色调 · 清爽阅读骨架 · 随笔与故事首选</i></p>
      <a href="assets/previews/warm-orange.png"><img src="assets/previews/warm-orange.png" alt="warm-orange" width="100%" /></a>
      <p><a href="previews/warm-orange.html">预览 HTML</a></p>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center" valign="top">
      <h4>✦ 微信生态绿 (wechat-green)</h4>
      <p><i>经典微信绿调 · 官方严谨规范排版 · 行业资讯与早报</i></p>
      <a href="assets/previews/wechat-green.png"><img src="assets/previews/wechat-green.png" alt="wechat-green" width="100%" /></a>
      <p><a href="previews/wechat-green.html">预览 HTML</a></p>
    </td>
    <td width="50%" align="center" valign="top">
      <h4>✦ 扩展你的专属主题</h4>
      <p><i>支持自由扩展任意自定义 JSON 主题文件，轻松定制专属视觉规范</i></p>
      <br>
      <pre><code>md2wx article.md -t ./my-theme.json -c</code></pre>
      <p>所有主题解耦为标准 JSON 文件，开箱即用，深度容错兜底。</p>
    </td>
  </tr>
</table>

---

## 如何扩展自定义主题？(Theme Extension)

MD2WX 采用标准 JSON 格式定义主题，扩展自定义主题非常简单，支持三种方式：

### 扩展途径
1. **直接指定文件路径**：`md2wx article.md -t /path/to/my-theme.json -c`
2. **放入用户配置目录**：放置在 `~/.config/md2wx/themes/` 下（如 `~/.config/md2wx/themes/sakura-pink.json`），`md2wx` 会自动识别，通过 `-t sakura-pink` 即可全局调用；
3. **贡献到内置主题库**：直接向 `md2wx/themes/` 目录贡献 `.json` 提交 PR。

### 主题 JSON 规范模版

新建 `my-theme.json`：

```json
{
  "id": "my-theme",
  "name": "我的专属主题",
  "description": "主题的简要说明描述",
  "colors": {
    "accent": "#2563eb",
    "accent_bg": "#eff6ff",
    "text_color": "#27272a",
    "sub_color": "#71717a",
    "border_color": "#e4e4e7",
    "code_bg": "#18181b",
    "code_text": "#e4e4e7",
    "quote_bg": "#f4f4f5",
    "page_bg": "#ffffff"
  },
  "typography": {
    "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    "font_size_base": "15.5px",
    "line_height_base": "1.8",
    "letter_spacing": "0.4px",
    "paragraph_indent": false
  },
  "styles": {
    "container": "clean",
    "h1": "underline",
    "h2": "left_bar",
    "h3": "diamond",
    "quote": "left_stripe",
    "code": "mac_dark",
    "table": "zebra",
    "list": "bullet",
    "hr": "line"
  }
}
```

> **字段兜底说明**：如果您只希望微调颜色，您只需在 JSON 里定义 `colors` 中的几个键，其他未填写的 `styles` 与 `typography` 将自动继承默认基准配置，安全无痛！

### 可选组件风格模式清单

| 组件 (`styles`) | 可选值 | 说明 |
| :--- | :--- | :--- |
| `container` | `clean`, `paper`, `dark`, `card`, `memo`, `brutalist` | 容器外框与底色模式 |
| `h1` | `underline`, `double_line`, `capsule`, `terminal`, `brutalist` | 一级大标题渲染模式 |
| `h2` | `left_bar`, `pill_badge`, `bubble_bg`, `serif_badge`, `terminal_prompt`, `brutalist_box`, `bottom_line` | 二级分区标题模式 |
| `h3` | `diamond`, `circle_badge`, `highlight_bg`, `slash` | 三级小标题与装饰前缀 |
| `quote` | `left_stripe`, `elegant_quote`, `bubble_card`, `paper_memo`, `terminal_box`, `brutalist` | 引言容器与装饰模式 |
| `code` | `mac_dark`, `terminal`, `clean_flat` | 代码块顶栏与样式 |
| `table` | `zebra`, `three_line`, `grid` | 表格斑马纹 / 学术三线表 / 全框线 |
| `list` | `bullet` (`•`), `diamond` (`◆`), `square` (`■`), `arrow` (`▸`) | 列表项符号模式 |
| `hr` | `line`, `gradient`, `asterisk`, `terminal_dash` | 分割线模式 |

---

## 配置微信凭据（用于 `--publish`）

复制配置模版：

```bash
cp .env.example .env
```

编辑 `.env` 填入微信公众平台（mp.weixin.qq.com）的开发者凭据：

```bash
WECHAT_APP_ID=wx98c10ae878xxxxxx
WECHAT_APP_SECRET=20827782e3e1f62xxxxxx
```

> **凭据自动探测**：MD2WX 会按顺序自动探测当前目录的 `.env`、`~/Develop/wx-serv/.env` 或全局环境变量，您无需重复配置。

---

## Python API 调用

MD2WX 同时支持作为一个独立的 Python 库嵌入到您自己的自动化脚本中：

```python
from md2wx import markdown_to_wechat_html, parse_frontmatter, list_themes, get_theme

# 1. 查看所有已注册主题
themes = list_themes()
print("当前可用主题:", list(themes.keys()))

markdown_text = """
# 思考的秩序

> **作者**：野生宝藏箱  
> **核心标签**：AI 自动化 · 架构

这是正文内容。
"""

# 2. 剥离 Frontmatter (若有)
meta, body = parse_frontmatter(markdown_text)

# 3. 指定主题渲染为微信内联 HTML (支持主题 ID 或外部 JSON 路径)
wechat_html = markdown_to_wechat_html(body, theme_name="vintage-news")
print(wechat_html)
```

---

## 自动化测试

项目自包含全套单元测试，开箱即测：

```bash
python3 -m unittest discover -s tests -v
```

---

## 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

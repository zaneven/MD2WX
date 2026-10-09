---
title: 打造专属风格：JSON 视觉骨架主题定制
author: 野生宝藏箱
digest: 深入 MD2WX 主题配置文件结构，学习通过纯 JSON 自定义色彩、排版字体与 9 大核心组件骨架。
date: 2026-10-08
tags:
  - MD2WX
  - 主题定制
  - 视觉设计
  - JSON
  - 排版规范
---

# 打造专属风格：JSON 视觉骨架主题定制

> **作者**：野生宝藏箱  
> **面向对象**：注重品牌统一调性的团队、公众号主理人、排版细节控  
> **核心概念**：JSON 驱动的视觉骨架、组件样式组合、全局主题扩展  

---

## 01. 拒绝千篇一律的「换皮」排版

绝大多数排版工具所谓的主题定制，本质上只是**换一个强调色（Accent Color）**：把标题的下划线从蓝色改成绿色，把引用框的左边条从灰色改成紫色。

然而真正的视觉设计风格，是由色彩、字体间距以及**组件骨架模式**共同决定的：
- 一篇复古人文长文，需要的是米黄纸质底色、学术三线表和典雅的大引号名言；
- 一篇黑客范的技术日志，需要的是纯黑底色、等宽字体、带有终端光标的命令行标题；
- 一份轻快的生活随笔，需要的是奶油色调、日系便签贴纸和圆润的胶囊小标。

MD2WX 采用了**纯 JSON 文件驱动的主题解耦架构**。所有视觉规范均抽象为标准的 `.json` 配置文件。你不需要修改任何 Python 源码或前端代码，只需写一个几行配置的 JSON 文件，就能完全定义出一套具有专属辨识度的全新版面骨架。

---

## 02. 主题 JSON 文件结构拆解

一个标准的 MD2WX 主题文件主要由三大块构成：`colors`（调色盘）、`typography`（排印规范）和 `styles`（组件模式映射）。

新建一个 `my-brand.json` 文件：

```json
{
  "id": "my-brand",
  "name": "我的专属品牌风",
  "description": "专为技术周刊定制的深邃靛蓝排版",
  "colors": {
    "accent": "#4f46e5",
    "accent_bg": "#eef2ff",
    "text_color": "#1e293b",
    "sub_color": "#64748b",
    "border_color": "#e2e8f0",
    "code_bg": "#0f172a",
    "code_text": "#e2e8f0",
    "quote_bg": "#f8fafc",
    "page_bg": "#ffffff"
  },
  "typography": {
    "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    "font_size_base": "16px",
    "line_height_base": "1.85",
    "letter_spacing": "0.4px",
    "paragraph_indent": false
  },
  "styles": {
    "container": "card",
    "h1": "capsule",
    "h2": "left_bar",
    "h3": "circle_badge",
    "quote": "elegant_quote",
    "code": "mac_dark",
    "table": "zebra",
    "list": "bullet",
    "hr": "gradient"
  }
}
```

### 1. 调色盘 (`colors`)
定义整套排版的色彩基调：
- `accent`：主强调色，用于重点标题底色、强引用标记、主链接等；
- `accent_bg`：强调色对应的浅色背景，通常用于次级高亮标记；
- `text_color`：正文字体颜色，建议选用深灰（如 `#1e293b`），比纯黑 `#000000` 更柔和耐看；
- `code_bg` 与 `code_text`：代码块容器的底色与前景色；
- `page_bg`：整篇文章的外层画布底色（支持白底、米黄纸质底或暗黑底色）。

### 2. 排印规范 (`typography`)
针对移动端阅读节奏的微调：
- `font_size_base`：正文基准字号。官方调校推荐为 `16px` 或 `15.5px`，在现代大屏手机上阅读最为舒适；
- `line_height_base`：正文黄金行高，推荐设定在 `1.8` 至 `1.85` 之间，留白呼吸感适中；
- `letter_spacing`：字间距，默认 `0.4px` 能够有效缓解中英混排时的视觉压迫；
- `paragraph_indent`：段落首行是否缩进（`true` 或 `false`，互联网长文通常保持不缩进并配合段间距）。

---

## 03. 核心组件模式清单 (`styles`)

`styles` 字段是 MD2WX 区别于其他工具的核心所在。每个组件都内置了多套经过真机调校的结构预设，你可以像搭积木一样自由组合：

| 组件 (`styles`) | 可选值 | 视觉效果说明 |
| :--- | :--- | :--- |
| **`container`** | `clean`, `paper`, `dark`, `card`, `memo`, `brutalist` | 画布容器模式（纸质底、卡片悬浮、便签或野兽派硬框） |
| **`h1`** | `underline`, `double_line`, `capsule`, `terminal`, `brutalist` | 一级标题形态（下划粗线、复古双细线、胶囊色块、终端符等） |
| **`h2`** | `left_bar`, `pill_badge`, `bubble_bg`, `serif_badge`, `terminal_prompt`, `brutalist_box` | 二级分区标题模式（左侧坚条、气泡徽标、纯黑硬框等） |
| **`h3`** | `diamond`, `circle_badge`, `highlight_bg`, `slash` | 三级小标题装饰（菱形标记、圆形徽章、荧光笔涂鸦） |
| **`quote`** | `left_stripe`, `elegant_quote`, `bubble_card`, `paper_memo`, `terminal_box` | 引用块模式（经典左边条、学术大引号名言、日系便签贴纸） |
| **`code`** | `mac_dark`, `terminal`, `clean_flat` | 代码块容器（Mac 三色圆点顶栏、极客命令行顶栏、极简浅色框） |
| **`table`** | `zebra`, `three_line`, `grid` | 表格模式（斑马纹交替底色、学术三线表、全网格框） |
| **`list`** | `bullet` (`•`), `diamond` (`◆`), `square` (`■`), `arrow` (`▸`) | 无序列表符号的形状模式 |
| **`hr`** | `line`, `gradient`, `asterisk`, `terminal_dash` | 分割线模式（实线、双色渐变线、古典星号居中、终端虚线） |

---

## 04. 扩展与应用自定义主题

编写好你的专属主题 JSON 文件后，有以下三种使用方式：

### 方式一：临时直接调用本地文件
如果只想在单篇文章中测试效果，可以直接把 JSON 文件路径传给 `-t` 参数：

```bash
md2wx article.md -t ./my-brand.json --clip
```

### 方式二：注册为全局用户主题（推荐）
如果你希望在任何目录下都能通过名字调用该主题，只需将 JSON 文件放入系统的 MD2WX 配置目录：

```bash
mkdir -p ~/.config/md2wx/themes/
cp my-brand.json ~/.config/md2wx/themes/my-brand.json
```

此时再次运行 `md2wx --list-themes`，你会发现 `my-brand` 已经被自动注册为系统可用主题。在任意工程目录下均可直接调用：

```bash
md2wx article.md -t my-brand -c
```

### 方式三：向官方仓库提交 PR
如果你的主题设计具备独创性与普适美感，欢迎将文件放入 `md2wx/themes/` 目录，向开源仓库发起 Pull Request，让所有用户共同使用。

---

## 05. 容错与缺省继承机制

为了降低定制门槛，MD2WX 内置了完善的**属性继承机制**。

你完全不需要把上面完整的配置字段全部写满。如果你只想快速调整主题的几个主色调，可以只写你关心的一两个字段：

```json
{
  "id": "my-quick-theme",
  "name": "极简微调主题",
  "colors": {
    "accent": "#e11d48",
    "accent_bg": "#ffe4e6"
  }
}
```

所有未在 JSON 中显式声明的 `styles` 与 `typography`，解析器都会自动继承自基准默认主题（`tech-blue`），确保渲染过程永远安全无报错。

---

## 06. 下一步

在掌握了版面样式的终极定制之后，整个写作流程中唯一剩下的外部不稳定因素就是**图片**。

外部自建图床为什么在微信里老是红叉破图？怎样用 Cloudflare R2 搭建一套永久免费且不限流量的私有图床？下一篇我们将彻底理清：[图床排坑指南：微信换链与自建 R2](2026-10-08-md2wx-tutorial-06-imagehost-r2.md)。

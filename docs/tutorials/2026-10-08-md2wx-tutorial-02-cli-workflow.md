---
title: 本地写作流：CLI 安装与剪贴板极速排版
author: 野生宝藏箱
digest: 详解 MD2WX 命令行工具的安装与极速排版，利用系统原生剪贴板注入实现一行命令秒级排版。
date: 2026-10-08
tags:
  - MD2WX
  - CLI
  - 命令行
  - 效率工具
  - 自动化
---

# 本地写作流：CLI 安装与剪贴板极速排版

> **作者**：野生宝藏箱  
> **面向对象**：终端极客、Obsidian / VS Code 重度用户、追求无缝效率的创作者  
> **核心工具**：MD2WX Python 命令行引擎（CLI）  

---

## 01. 告别浏览器来回切换

在上一篇教程中，我们介绍了纯前端的 MD2WX Web Studio。对于偶尔发文的用户来说，在线粘贴非常直观。但如果你习惯于在本地编辑器（例如 Obsidian、VS Code 或 Typora）中撰写几十页的技术长文，每次都要打开浏览器、全选复制、切换网页粘贴、再点复制富文本，操作路径依然显得繁琐。

更自然的方式是：**写完文章后，在终端敲一行命令，或者在编辑器里按一个快捷键，格式化后的微信富文本就已经静静躺在你的系统剪贴板里了。**

你只需要切到微信公众号后台，按下 `Cmd + V`，排版就已全部完成。这就是 MD2WX CLI 引擎的核心使命。

---

## 02. 环境要求与快速安装

MD2WX 遵循**零外部重型依赖**的设计哲学。其 CLI 核心解析器与富文本注入器完全使用 Python 3.8+ 标准库手写（基于 `re`、`json`、`subprocess` 等原生模块），因此你不需要下载庞大的第三方依赖包。

### 1. 确认 Python 环境
在终端中执行以下命令，确保 Python 版本在 3.8 或以上：

```bash
python3 --version
```

### 2. 克隆仓库并安装
推荐使用 Git 克隆仓库，并通过 `pip` 以可编辑开发模式进行安装：

```bash
# 克隆代码仓库
git clone https://github.com/zaneven/MD2WX.git
cd MD2WX

# 本地安装命令行工具
pip install -e .
```

安装完成后，在终端运行命令验证是否安装成功：

```bash
md2wx --help
```

如果看到命令参数说明列表，说明环境已经就绪。

---

## 03. 最简工作流：一键写入剪贴板

MD2WX CLI 最常用、最丝滑的参数是 `--clip`（简写为 `-c`）：

```bash
md2wx my_article.md --clip
```

执行后，终端会打印出解析与内联样式处理进度，并显示：
```text
✓ 微信富文本排版已成功复制到系统剪贴板！可以直接在微信公众号后台粘贴。
```

此时，你直接进入微信公众号编辑后台，按下 `Cmd + V`（Windows 用户按 `Ctrl + V`），就会发现整篇文章已经带着高质感的内联样式完美贴入，包括 Mac 终端圆点代码框、精调字号与自动追加的文末外链脚注。

### 底层机理解析：原生剪贴板注入
很多命令行工具复制出来的只是纯文本，或者裸 HTML 源码，粘贴到微信后台只会是一堆乱码字符。

MD2WX 在 macOS 下通过底层的 `osascript` 与十六进制数据流，将内容以 `«class HTML»` 的原生富文本 MIME 类型写入系统剪贴板剪贴板服务（Pasteboard）。这样微信编辑器会将其识别为合法的富文本 DOM 节点进行解析，从而完整保留每个标签的内联 CSS 样式。

---

## 04. 常用命令行操作

除了基础的复制之外，MD2WX CLI 还支持灵活的定制选项：

### 1. 查看可用主题清单
执行以下命令，列出当前系统内置的所有视觉主题及其设计说明：

```bash
md2wx --list-themes
```

### 2. 指定主题进行排版
通过 `-t` 或 `--theme` 参数指定主题代号：

```bash
# 使用古典学术的复古报刊风格
md2wx my_article.md -t vintage-news -c

# 使用黑客范的极客终端风格
md2wx my_article.md -t terminal-geek -c

# 使用先锋视觉的野兽派风格
md2wx my_article.md -t acid-bold -c
```

### 3. 导出为自包含 HTML 文件
如果需要先在本地浏览器中审查，或者需要将 HTML 存档，可以使用 `-o` 参数导出文件：

```bash
md2wx my_article.md -t vintage-news -o preview.html
```

双击生成的 `preview.html` 即可在本地浏览器中全屏查看。

### 4. 配合 Unix 管道（Pipeline）
MD2WX 支持从标准输入流（stdin）接收 Markdown 内容，非常适合与其他命令行工具串联：

```bash
# 将文章内容过滤后送入排版
cat my_article.md | md2wx -t wechat-green --clip

# 结合 curl 抓取远程 Markdown 并直接排版复制
curl -s https://raw.githubusercontent.com/user/repo/main/README.md | md2wx -c
```

---

## 05. 进阶玩法：联动本地编辑器与启动项

为了将效率推向极致，你可以将这行命令集成到本地工作流中：

### 方案 A：在 VS Code 中配置一键任务
在工作区的 `.vscode/tasks.json` 中添加以下配置：

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "MD2WX: 一键排版到微信剪贴板",
      "type": "shell",
      "command": "md2wx '${file}' --clip",
      "problemMatcher": [],
      "group": {
        "kind": "build",
        "isDefault": true
      }
    }
  ]
}
```
保存后，在任何打开的 Markdown 文件中按下快捷键 `Cmd + Shift + B`，即可瞬间完成排版复制。

### 方案 B：在 Raycast / Alfred 中绑定快捷脚本
在 Raycast 的 Script Commands 中编写一个简单的 shell 脚本：
```bash
#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Format to WeChat
# @raycast.mode silent

pbpaste | md2wx --clip
```
这样你只需在任何编辑器里选中文字 `Cmd + C`，呼出 Raycast 回车，剪贴板中的内容就被就地升华为带有内联样式的微信富文本。

---

## 06. 下一步

搞定了文章正文的极速排版之后，很多作者经常遇到的下一个拦路虎就是**公众号封面**。微信头条的 2.35:1 长图在朋友圈或聊天框里经常被裁成正方形，导致文字被无情切断。

下一篇教程我们将深入探讨：[封面不求人：双比例拼接与安全区](2026-10-08-md2wx-tutorial-03-cover-studio.md)。

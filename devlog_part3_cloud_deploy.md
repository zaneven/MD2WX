---
title: MD2WX Studio 全球上线：GitHub Pages 自动化部署、自定义域名与微信排版黑科技实战
author: 野生宝藏箱
digest: 从本地 Web 工作台到全球公网访问！完整复盘 MD2WX Studio 如何利用 GitHub Actions + Cloudflare 绑定独立域名 md2wx.zaneven.com，并攻克微信外链自动转脚注、纯内联代码语法高亮、双栏联动同步滚动与全局快捷键的高阶进化全过程。
cover: assets/cover-acid-bold.png
---

# MD2WX Studio 全球上线：GitHub Pages 自动化部署、自定义域名与微信排版黑科技实战

> **作者**：野生宝藏箱  
> **模式**：纯纯的 Vibe Coding（灵感直觉 -> 与 AI 对话 -> 秒级落地）  
> **排版主题**：tech-blue 现代科技蓝 / acid-bold 先锋野兽派  
> **一句话简介**：从本地玩具跃迁为全球生产力工具，微信公众号排版工作台正式上线！

昨天，我们成功将 **MD2WX** 从一个纯 Python 命令行工具，进化为了拥有 iPhone 仿真实机视口、9 大视觉骨架主题的 Web 工作台。

但很多朋友在体验后立刻提出了更迫切的诉求：

> *“虽然本地跑 `npm run dev` 很爽，但我有时候在 iPad 上码字、或者在别人电脑上临时要发文，能不能直接打开网页就能用？”*  
> *“能不能有个专属的独立域名，不用每次都去克隆代码？”*  
> *“公众号正文不能点外链，能不能自动把链接转成文末的文献引用列表？”*  
> *“代码块在微信后台贴进去全是单色白字，能不能让微信也能支持内联代码语法高亮？”*

**用户的呼声就是最明确的冲锋号角。**

今天，我再次敲开终端与 AI 结对编程，一口气完成了 **全球生产环境上线** 与 **多项微信排版核心黑科技攻坚**。

不仅拿下了独立域名 **[https://md2wx.zaneven.com](https://md2wx.zaneven.com)**，更把整个排版体验推向了全新高度。

以下是今天的全链路实战复盘与技术深度记录。

---

## 01. 云端上线：GitHub Actions + Pages 自动化部署

要让一个纯前端应用零成本、高可用地发布到公网，最优雅的方案莫过于 **GitHub Pages + GitHub Actions**。

但真正落地的过程中，我们跨过了两个最容易踩坑的暗礁：

### ✦ 避坑 1：子路径静态资源 404 白屏灾难
GitHub Pages 默认的仓库访问路径形如 `https://<user>.github.io/<repo>/`。
Vite 默认的资源引用路径是绝对根路径 `/assets/index.js`，一旦部署到带仓库名的二级子路径下，浏览器会直接在域名根目录下请求资源，导致 **404 白屏**。

我们果断在 `web/vite.config.js` 中将资源基准路径重构为自适应相对路径：

```javascript
// web/vite.config.js
import { defineConfig } from 'vite';

export default defineConfig({
  base: './', // 无论是一级域名、二级子路径还是独立域名，静态资源自适应相对定位
  server: { port: 3000, host: true },
  build: { outDir: 'dist', assetsDir: 'assets' }
});
```
同时将 `index.html` 中的 Favicon、Apple Touch Icon 链接全部调整为相对路径 `./favicon.svg`，彻底杜绝了资源加载破损。

### ✦ 避坑 2：GitHub Actions 官方 Pages 流水线与 Node 22 升级
传统的 `gh-pages` 分支推送方案容易让仓库的 git 树变得杂乱。我们采用了 GitHub 官方推荐的 `actions/deploy-pages` 现代流水线，并将构建环境平滑升级到最新的 **Node.js 22**：

```yaml
# .github/workflows/deploy.yml
name: Deploy Web to GitHub Pages

on:
  push:
    branches: [main]
    paths: ['web/**', '.github/workflows/deploy.yml']
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: 'pages'
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: 'npm'
          cache-dependency-path: 'web/package-lock.json'
      - working-directory: web
        run: npm ci && npm run build
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: 'web/dist'
      - id: deployment
        uses: actions/deploy-pages@v4
```

每次只需 `git push origin main`，25 秒之内云端自动完成依赖安装、Vite 编译打包与零停机原子化发布！

---

## 02. 域名解析与免费 SSL：绑定 md2wx.zaneven.com

有了 GitHub Pages，下一步就是绑定属于我自己的专属品牌域名：**`md2wx.zaneven.com`**。

由于我的域名托管在 Cloudflare，我们直接利用本机的 Wrangler 凭证与 Cloudflare API 完成了精准配置：

### ✦ Cloudflare DNS 配置要点
为 `zaneven.com` 区域添加一条 CNAME 记录：
- **Type**：`CNAME`
- **Name**：`md2wx`
- **Target**：`zaneven.github.io`
- **Proxy Status**：`DNS only`（关闭小黄云代理）

> **为什么关闭 Cloudflare 代理（DNS only）？**  
> GitHub Pages 需要为自定义域名向 Let's Encrypt 申请官方 SSL 证书。如果开启 Cloudflare 代理，可能会干扰 GitHub 的 ACME 挑战验证。先使用 `DNS only` 直连，GitHub 在 30 秒内就能签发出官方证书！

### ✦ 持久化 CNAME 文件防丢失
为避免每一次打包部署导致自定义域名被冲掉，我们在 `web/public/CNAME` 中写入了 `md2wx.zaneven.com`。
Vite 在打包时会自动将其无损复制到 `dist/CNAME`。

通过 GitHub API 绑定后，证书直接秒变 `approved`，随后开启全站 **Enforce HTTPS** 强制加密跳转！

整个公网站点自此正式立于云端：👉 **[https://md2wx.zaneven.com/](https://md2wx.zaneven.com/)**

---

## 03. 微信排版黑科技：破解公众号两大硬核痛点

站点上线只是基础，真正决定排版工具上限的，是**对微信公众号特殊机制的理解深度**。

今天我们攻克了两个在排版圈困扰无数创作者的核心痛点：

### ✦ 痛点一：微信无法点击外链？自动转文末学术文献脚注！
微信公众平台对外部链接有极其严苛的限制（除了已绑定的公众号文章外，普通外部 URL 根本无法直接点击跳转）。

以往很多创作者只能手动在括号里写出长长的 URL，版面极其破碎丑陋。

我们在前端解析管道中内置了 **微信智能文献脚注引擎**：

1. **正文角标化**：自动提取正文中的 `[链接文本](url)`，替换为高质感的主题色角标 `链接文本[1]`、`链接文本[2]`；
2. **文末文献列表自动聚合**：自动去重搜集文中所有引用的文献链接，并在文章末尾自动注入带有主题色左边条的「参考链接与资料引用」文献列表卡片：

```html
<!-- 编译输出片段 -->
<section style="margin-top: 36px; padding: 16px 18px; border-radius: 8px; background: rgba(0,0,0,0.02); border-left: 3px solid #2563eb;">
  <div style="font-size: 13.5px; font-weight: 700; color: #2563eb; margin-bottom: 10px;">参考链接与资料引用</div>
  <ul style="margin: 0; padding-left: 0; font-size: 12px; line-height: 1.8;">
    <li>[1] DeepSeek 官方文档: https://api-docs.deepseek.com</li>
  </ul>
</section>
```

在顶部「排版微调」中提供了全局开关，作者可根据图文类型自由开启或关闭。

---

### ✦ 痛点二：公众号后台代码无色彩？自研纯内联语法着色引擎！
传统 Markdown 工具渲染代码高亮通常依赖外部 CSS（如 Prism.js 或 Highlight.js 生成 `<span class="token keyword">`）。

**但微信公众号后台富文本编辑器会无情过滤掉所有的 class 属性！** 这导致复制到微信后台后，原本五彩斑斓的代码全部褪色为单调的白色或黑色。

为了彻底解决这一痛点，我们手写了一个专门针对微信公众平台的纯内联轻量语法着色引擎 [`highlighter.js`](file:///Users/a1/Develop/MD2WX/web/src/core/highlighter.js)：

- **直接注入内联样式**：不产生任何 class，将 Python、JS/TS、CSS、HTML、Bash、SQL 等语言的关键字、字符串、数字、注释直接转化为带 `style="color: #f472b6;"` 的 `<span>` 标签；
- **完美兼容三大视觉代码框**：无论是在 Mac 三色指示灯框、极客命令行终端，还是极简扁平框中，代码色彩在复制到公众号后台后依然 **原汁原味，鲜明饱满**！

---

## 04. 心流级交互：双栏同步滚动、全局快捷键与图片拖拽

有了强大的排版输出，我们把目光聚焦到了创作者在键盘上的每一个击键与视线流转：

| 功能特性 | 交互细节 | 带来的生产力提升 |
| :--- | :--- | :--- |
| **双栏联动同步滚动** | 基于比例换算联动右侧 iPhone/桌面预览，内置互斥锁防抖 | 对照长文排版细节无需左右频繁切换鼠标滚动，视线始终聚焦 |
| **Cmd / Ctrl + S** | 拦截浏览器“保存网页”默认行为，触发本地草稿毫秒级持久化 | 杜绝意外刷新或误触导致的内容丢失，满满的安全感 |
| **Cmd / Ctrl + Enter** | 键盘流终极武器，无需鼠标点击，一键编译并复制富文本到剪贴板 | 排版完成双手无需脱离键盘，直接切到微信后台 Cmd+V 粘贴 |
| **本地截图粘贴 / 拖拽** | 剪贴板截图直接按 Cmd+V 自动转 Base64 Markdown 嵌入；本地图片拖入显示蓝色虚线边框 | 免除手动找图床上传、拷贝链接的繁琐步骤 |
| **排版微调面板** | 顶部弹窗支持正文字号 (14/15.5/16.5/17.5px)、行距 (1.6/1.8/1.95/2.1) 自由切换 | 满足不同作者对于手机端阅读密度的极致挑剔 |

---

## 05. 视觉重构：主题选择器的优雅迁徙

在今天开发的最后，我们针对界面布局做了一次像素级的重构微调：

- **移除顶栏干扰**：把原本悬浮在顶部 Header 中央的主题选择器移除，让顶部导航条彻底回归极简开阔；
- **对齐视口操作**：将主题选择器移动到右侧预览区工具栏（`preview-toolbar`）的最右侧，与左侧的「iPhone 仿真实机 / 全宽桌面视图」切换 Tab 并肩而立；
- **精雕尺寸与浮层定位**：触发按钮微调为 28px 高度，下拉菜单改为右对齐贴边展开，层级高过预览画布，整体界面美感一气呵成。

当然，全站依然坚定践行 **100% 纯 SVG 矢量图标规范**，绝不使用任何操作系统 Emoji，呈现最克制、纯粹的开发者工具美学。

---

## 06. 总结与在线体验

从一个想法到纯 Python 命令行，再到如今部署在全球边缘网络、拥有独立域名与完整排版黑科技的 **MD2WX Studio**，这场 Vibe Coding 的旅程展现了人机结对编程令人惊叹的加速度。

如果你也是一名经常在微信公众号码字、追求高质感版面、又不想忍受沉重依赖和繁琐操作的创作者，欢迎立刻打开浏览器体验：

👉 **在线排版工作台**：**[https://md2wx.zaneven.com](https://md2wx.zaneven.com)**  
👉 **开源 GitHub 仓库**：**[https://github.com/zaneven/MD2WX](https://github.com/zaneven/MD2WX)**

不用登录，没有套路，随开随用，数据完全留在你的本地浏览器。

*保持专注，重塑秩序。我们下一个版本见！*

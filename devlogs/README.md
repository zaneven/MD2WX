# MD2WX 开发日志与演进全记录 (DevLogs)

欢迎查阅 **MD2WX**（Markdown to WeChat Formatter）的完整研发记录。本项目采用 **Vibe Coding** 模式（直觉驱动 -> AI 结对 -> 秒级落地），从最初的一个轻量 Python CLI 脚本，逐步演进为集**双端渲染引擎**、**仿真实机视口 Web Studio**、**自动化云端部署**与**专属封面图工坊 Cover Studio**于一体的生产级内容创作者武器库。

---

## 目录索引与演进脉络

```
devlogs/
├── README.md                          # 本索引导航文件
├── devlog_part1_cli_engine.md         # Part 1: 核心 CLI 引擎诞生与纯标准库 AST 解析器
├── devlog_part2_studio.md             # Part 2: 纯前端 Web Studio 上线与真机仿真视口
├── devlog_part3_cloud_deploy.md        # Part 3: GitHub Pages 自动化部署与微信排版黑科技
└── devlog_part4_cover_studio.md       # Part 4: 9大主题专属封面、1:1安全区与真机大字排版
```

---

## 各期开发日志要点总结

### [Part 1: 核心 CLI 引擎诞生与纯标准库 AST 解析器](devlog_part1_cli_engine.md)
- **版本关联**：`v1.0.0`
- **主要内容**：
  - 攻克微信公众号排版复制变形、样式丢失的痛点。
  - 坚持**零外部重型依赖**哲学：使用纯 Python 标准库手写 AST + 正则 Markdown 解析器与内联样式转换器。
  - 初步设计 9 大独立视觉骨架主题（科技蓝、极客黑、先锋酸性、学术优雅、报刊经典等）。
  - 实现 macOS 原生剪贴板富文本直接注入与微信官方草稿箱 API 一键直推。

### [Part 2: 纯前端 Web Studio 上线与真机仿真视口](devlog_part2_studio.md)
- **版本关联**：`v1.0.1`
- **主要内容**：
  - 突破纯命令行交互壁垒，打造无需本地 Python 环境的开箱即用 Web 工作台。
  - 引入 **iPhone 16 Pro 仿真实机视口**（灵动岛、真机比例、安全边距），还原微信真实阅读体验。
  - 确立**纯矢量 SVG、严禁使用 Emoji** 的 UI 设计规范。
  - 重塑品牌视觉识别体系：打造酸性先锋矢量 Master Logo 与高精度 Favicon。

### [Part 3: GitHub Pages 自动化部署与微信排版黑科技](devlog_part3_cloud_deploy.md)
- **版本关联**：`v1.0.1+`
- **主要内容**：
  - 基于 GitHub Actions 实现 Web 工作台自动化构建与 GitHub Pages 部署，绑定独立域名 `md2wx.zaneven.com`。
  - 攻克微信公众号富文本排版核心壁垒：
    - **外链自动转脚注**：解决微信不支持外部超链接跳转的限制。
    - **纯内联代码语法高亮**：避开外部 CSS class 被微信过滤的问题，实现纯内联 token 级高亮。
    - **双栏联动同步滚动**：实现编辑器与移动端预览视口的平滑精准同步。
    - **全局快捷键系统**：复制、清空、换主题等高频操作秒级触发。

### [Part 4: 9大主题专属封面、1:1安全区与真机大字排版](devlog_part4_cover_studio.md)
- **版本关联**：`v1.0.2`
- **主要内容**：
  - 终结“排版两分钟，找封面两小时”的内耗：推出 **Cover Studio 封面工坊**。
  - 为 9 大视觉主题定制同源设计语言的默认封面模板。
  - 攻克微信公众号**单图文转发 1:1 裁切“断头”痛点**，首创 2.35:1 全图与 1:1 核心安全区实时预览视框。
  - 优化移动端字号与层级：推出“真机大字版”正文排版（16px 正文字号、1.85 行高、精调行距）。
  - 支持封面图免下载、一键复制并直粘微信后台。

---

## 变更记录与版本发布
自 `v1.0.2` 起，后续常规版本更新及特性总结将统一在项目的 **[GitHub Releases](https://github.com/zaneven/MD2WX/releases)** 中发布和维护。历史各篇长文 DevLog 保留在本目录，作为产品技术演进与设计哲学的深度记录。

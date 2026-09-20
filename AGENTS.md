# MD2WX 项目智能体协作与开发规范 (AGENTS.md)

欢迎使用并维护 **MD2WX**！本文档专为 AI 智能体（如 Antigravity / Gemini / Claude Code）及核心开发者编写，旨在阐明项目设计哲学、双端架构拓扑、关键技术限制以及协作红线。

---

## 1. 项目定位与核心哲学

**MD2WX** 是专为微信公众号打造的高质感 Markdown 排版转换器与草稿箱自动化发布工具。其诞生源于创作者长期面临的痛点：**写文十分钟，排版两小时**，外部编辑器排版复制进微信后台常常出现样式丢失、外链失效、移动端排版变形等问题。

### 核心设计哲学
1. **零外部重型依赖（Zero Heavy Dependencies）**：
   - CLI 核心引擎使用纯 Python 3.8+ 标准库（`re`, `json`, `urllib` 等），不依赖庞大笨重的第三方三方库。
   - Web 工作台坚持纯原生轻量设计（Vite + 原生 JavaScript + Vanilla CSS），不引入 React/Vue 等框架或 TailwindCSS。
2. **极客美学与视觉骨架（Aesthetic & Themes）**：
   - 内置 9 大经过真机像素级调校的独立视觉骨架主题（科技蓝、极客黑、先锋酸性、学术优雅、报刊经典等）。
   - 彻底摆脱粗糙简陋的排版风格，兼顾移动端真机阅读的排版节奏与字号层级（16px 正文、1.85 行高）。
3. **闭环生产力（End-to-End Workflow）**：
   - 支持本地富文本剪贴板原生注入、一键直推微信官方草稿箱，以及主题专属封面工坊（Cover Studio）。

---

## 2. 目录架构与模块职责

```
MD2WX/
├── AGENTS.md                   # 本文件：智能体协作与开发规范指南
├── README.md                   # 官方中英文开源说明与特性画廊
├── pyproject.toml              # Python CLI 打包配置 (setuptools)
├── sample_article.md           # 标准 Markdown 排版评测样例文章
├── render_cover.html           # 9大主题封面无头/本地渲染与导出画板
│
├── devlogs/                    # 完整研发演进日志合集 (Part 1 - Part 4)
│   ├── README.md               # 开发日志导航索引
│   ├── devlog_part1_cli_engine.md
│   ├── devlog_part2_studio.md
│   ├── devlog_part3_cloud_deploy.md
│   └── devlog_part4_cover_studio.md
│
├── md2wx/                      # Python CLI 核心包
│   ├── __init__.py
│   ├── cli.py                  # 命令行参数解析、交互与系统剪贴板注入 (pbcopy/osascript)
│   ├── parser.py               # 核心解析引擎：AST构建、Token化、内联样式注入、外链转脚注
│   ├── highlighter.py          # 纯内联语法高亮器（词法分词 + 微信兼容内联 span）
│   ├── publisher.py            # 微信公众号后台交互（access_token、素材上传、草稿箱推送）
│   └── themes/                 # 9大主题 JSON 配置文件夹
│       ├── tech-blue.json      # 现代科技蓝（默认）
│       ├── terminal-geek.json  # 极客终端黑
│       ├── acid-bold.json      # 先锋野兽派
│       └── ...
│
├── web/                        # 纯前端 Web Studio 工作台
│   ├── package.json            # Vite 轻量构建配置
│   ├── vite.config.js          # 构建入口与资源配置
│   ├── index.html              # Studio 页面结构与 iPhone 16 Pro 仿真视口容器
│   └── src/
│       ├── app.js              # Web 应用主逻辑：双栏联动滚动、实时解析、快捷键响应
│       ├── core/
│       │   ├── parser.js       # 浏览器端轻量 Markdown 解析与样式内联引擎
│       │   ├── highlighter.js  # 纯内联 JS 语法高亮
│       │   └── clipboard.js    # 现代浏览器 Clipboard API 富文本注入
│       ├── themes/             # Web 端主题配置定义
│       └── styles/             # Vanilla CSS 设计系统与仿真视口样式
│
├── tests/                      # Python 自动化测试套件
│   ├── test_parser.py          # 解析器、内联转换、主题注入与边界单测
│   └── test_publisher.py       # 草稿箱发布逻辑与 Mock 测试
│
└── .github/workflows/          # GitHub Actions 自动化工作流
    ├── deploy.yml              # Web Studio 部署至 GitHub Pages (md2wx.zaneven.com)
    └── release.yml             # 基于 Tag (v*) 触发的自动化测试与 Release 发布
```

---

## 3. 微信公众号富文本排版核心技术限制与规范

在微信排版引擎中，任何输出给微信编辑器的 HTML 必须满足极其苛刻的限制条件，违反任何一条均会导致样式失效或后台报错：

1. **必须完全内联化（Inline Styles Only）**：
   - 微信公众号编辑器在粘贴或导入时，会**无情剥离所有外部 `<style>` 样式表和 class 选择器**。
   - 所有字体、字阶、行高、背景色、阴影、圆角必须通过行内属性 `style="..."` 精确内联至每个标签。
2. **严禁依赖外部 CSS 类名与第三方高亮库（如 Prism/Highlight.js 生成 class）**：
   - 代码高亮必须由 `highlighter.py` / `web/src/core/highlighter.js` 将每个语法 token 直接转换为自带 `style="color: ...; font-weight: ..."` 的 `<span>`。
3. **微信不支持外部超链接跳转（外链必须自动转脚注）**：
   - 微信后台仅对认证服务号的部分特定场景开放外链。在普通正文中的普通外部链接，微信会清除 `href` 或阻断点击。
   - **强制要求**：解析器遇到 `[链接文本](https://example.com)` 时，必须渲染为 `链接文本 [1]`，并在文章末尾自动追加 `### 参考链接 / 脚注` 列表。
4. **空字节与防静默截断防护**：
   - 微信草稿箱 API 对内容严禁含有 `\x00`（Null Byte）等非打印控制字符，否则会导致后续文章正文被静默截断。解析前必须做控制字符 Sanitization 清理。
5. **单图文封面 1:1 裁切安全区**：
   - 微信头条封面比例为 2.35:1（900x383 或 2350x1000），但在微信对话框分享、朋友圈二次转发时会被自动裁剪为正方形 1:1。
   - 设计或渲染封面图时，核心文字与视觉主体必须置于中部的 1:1 安全区内。

---

## 4. 开发红线与行为准则

作为协助开发该项目的智能体，必须始终严格遵守以下准则：

1. **界面图标规范：绝对不要使用 Emoji**：
   - 在前端界面（Web Studio、工具栏、弹窗等）开发时，**严禁使用 Emoji**，一律使用现代、精致的纯矢量 SVG 图标（Lucide/Feather 风格），保持极客科技质感。
2. **保持零依赖轻量化设计**：
   - Python 端除开发测试工具（pytest）外，核心功能严禁引入外部重型依赖。
   - Web 端严禁擅自安装 React、Vue、TailwindCSS 等重型库，使用原生 JS 与 Vanilla CSS 即可获得极致响应性能。
3. **Admin 模块同步生产约束**：
   - 若改动涉及 admin 相关的核心代码或配置，完成修改后必须确认并执行推送/部署到生产环境。
4. **版本发布规范（GitHub Release）**：
   - 以后凡是有新版本更新（Bug 修复、新增主题、重大特性等），必须按照语义化版本打 Tag，并将**技术亮点、更新要点精简总结并发布到 GitHub Releases**中。
5. **测试保障**：
   - 每次修改核心解析器或高亮逻辑后，必须执行 `python3 -m pytest`，并保证 100% 测试通过率；修改 Web 端代码后必须执行 `npm run build` 确保无编译错误。

---

## 5. 常用开发、测试与发布命令速查

### Python CLI 引擎
```bash
# 运行单元测试
python3 -m pytest

# 本地以开发模式安装 CLI
pip install -e .

# 使用指定主题预览渲染输出 HTML
md2wx sample_article.md -t tech-blue -o output.html

# 渲染并直接写入系统剪贴板（macOS 原生富文本）
md2wx sample_article.md -t acid-bold -c

# 推送到微信公众号草稿箱（需配置 .env 中的 APPID 与 APPSECRET）
md2wx sample_article.md -t tech-blue -p
```

### Web Studio 工作台
```bash
cd web

# 启动本地开发热更新服务
npm run dev

# 校验生产环境构建
npm run build

# 本地预览构建产物
npm run preview
```

### 版本发布流程 (Release SOP)
1. **更新版本号**：在 `pyproject.toml` 和 `web/package.json` 中同步更新版本号（例如 `1.0.3`）。
2. **运行全量测试与构建**：
   ```bash
   python3 -m pytest && cd web && npm run build && cd ..
   ```
3. **提交代码并打 Tag**：
   ```bash
   git add .
   git commit -m "chore(release): bump version to v1.0.3"
   git tag -a v1.0.3 -m "Release v1.0.3"
   git push origin main --tags
   ```
4. **发布 GitHub Release**：
   使用 GitHub CLI 创建 Release 并附带更新要点：
   ```bash
   gh release create v1.0.3 \
     --title "v1.0.3: [特性标题]" \
     --notes-file release_notes.md
   ```
   *（或由 `.github/workflows/release.yml` 监听 Tag 推送后自动运行）*

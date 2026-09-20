import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

// 引入 cover.js
import { renderCoverHtml, THEME_COVER_PRESETS } from '../web/src/core/cover.js';

const coverCssPath = path.resolve(rootDir, 'web/src/styles/cover.css');
const cssContent = fs.readFileSync(coverCssPath, 'utf8');

const outputDirLocal = path.resolve(rootDir, 'assets/covers');
const outputDirObsidian = '/Users/a1/Library/Mobile Documents/iCloud~md~obsidian/Documents/Z/00_Inbox/techBlog/assets/covers';

fs.mkdirSync(outputDirLocal, { recursive: true });
fs.mkdirSync(outputDirObsidian, { recursive: true });

// 为 9 大主题定制具有代表性的高质量标题与金句展示
const THEME_CASES = [
  {
    id: 'acid-bold',
    title: '在喧嚣的时代，重塑深度思考的秩序',
    digest: '真正的专注，不是在安静的环境里做简单的事，而是在充满干扰的世界中守住内心的秩序。',
    tag: '先锋态度 · 拒绝平庸',
    badge: 'ACID BOLD',
    vol: 'VOL.02 // POP'
  },
  {
    id: 'tech-blue',
    title: '高可用分布式系统架构演进实战',
    digest: '从单体到分布式，不仅是组件的拆分，更是服务治理、容灾边界与一致性模型的全面进化。',
    tag: '深度架构 · 极客手记',
    badge: 'TECH BLOG',
    vol: '2026 · ARCH #02'
  },
  {
    id: 'dark-night',
    title: '深入理解零知识证明与现代密码学',
    digest: '在不泄露任何秘密的前提下证明真相，数学的美感正是数字时代对抗虚妄的最强铠甲。',
    tag: '赛博夜读 · 极客沉思',
    badge: 'NIGHT RUN',
    vol: '0x02 // CYBER'
  },
  {
    id: 'elegant-purple',
    title: '留白与张力：现代视觉排印美学探索',
    digest: '克制即力量，优秀的信息设计永远在繁复中提炼纯粹，让每一次目光驻留都成为享受。',
    tag: '设计美学 · 独立思考',
    badge: 'AESTHETIC',
    vol: '2026 · ISSUE 02'
  },
  {
    id: 'terminal-geek',
    title: 'Linux 内核调度器深度原理剖析',
    digest: '探寻 CFS 完全公平调度器的核心逻辑，从红黑树到虚拟运行时间，感知底层操作系统的律动。',
    tag: 'SHELL · 架构复盘',
    badge: 'BASH / DEV',
    vol: 'TERM // 2026'
  },
  {
    id: 'vintage-news',
    title: '数字时代的深度阅读与古典书卷',
    digest: '在信息碎片如潮水般涌来的岁月，翻开一本泛黄的书卷，重拾沉潜于文字深处的宁静。',
    tag: '人文书卷 · 思想论丛',
    badge: 'WEEKLY PRESS',
    vol: '第 02 期 · 专刊'
  },
  {
    id: 'warm-memo',
    title: '把普通日子过得热气腾腾的生活手记',
    digest: '记录清晨的第一缕微光、窗台绿植的舒展、与每一份不期而遇的温暖微小日常。',
    tag: '生活手记 · 日常微光',
    badge: 'HEALING NOTE',
    vol: '2026 · MEMO #02'
  },
  {
    id: 'warm-orange',
    title: '元气满满的习惯重塑与认知迭代指南',
    digest: '告别精神内耗，用微小的正向反馈启动飞轮效应，每天都是重塑自我的全新起点。',
    tag: '元气日常 · 读书感悟',
    badge: 'SUNSHINE',
    vol: '2026 · VOL.02'
  },
  {
    id: 'wechat-green',
    title: '微信公众平台技术生态与创作者指引',
    digest: '规范排版标准，拥抱高质量原生渲染，让优质内容以最体面的形态触达千家万户。',
    tag: '官方资讯 · 行业前沿',
    badge: 'WECHAT OFFICIAL',
    vol: '2026 · ISSUE 02'
  }
];

const chromeBin = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

for (const item of THEME_CASES) {
  const meta = {
    title: item.title,
    digest: item.digest,
    author: '野生宝藏箱',
    tag: item.tag,
    badge: item.badge,
    vol: item.vol,
    website: 'MD2WX.ZANEVEN.COM'
  };

  const coverHtml = renderCoverHtml(item.id, 'banner', meta, false);

  const fullHtml = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body {
      width: 1175px;
      height: 500px;
      overflow: hidden;
      background: transparent;
      -webkit-font-smoothing: antialiased;
    }
    ${cssContent}
  </style>
</head>
<body>
  ${coverHtml}
</body>
</html>`;

  const tempHtmlPath = path.resolve(rootDir, `assets/covers/temp_${item.id}.html`);
  const targetPngLocal = path.resolve(outputDirLocal, `cover-${item.id}.png`);
  const targetPngObsidian = path.resolve(outputDirObsidian, `cover-${item.id}.png`);

  fs.writeFileSync(tempHtmlPath, fullHtml, 'utf8');

  try {
    const cmd = `"${chromeBin}" --headless --disable-gpu --screenshot="${targetPngLocal}" --window-size=1175,500 "file://${tempHtmlPath}"`;
    execSync(cmd, { stdio: 'pipe' });
    fs.copyFileSync(targetPngLocal, targetPngObsidian);
    console.log(`Generated cover for [${item.id}] -> ${targetPngLocal}`);
  } catch (err) {
    console.error(`Failed to generate cover for [${item.id}]:`, err);
  } finally {
    if (fs.existsSync(tempHtmlPath)) {
      fs.unlinkSync(tempHtmlPath);
    }
  }
}

console.log('All 9 theme covers rendered successfully!');

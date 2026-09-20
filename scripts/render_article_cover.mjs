import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

import { renderCoverHtml } from '../web/src/core/cover.js';

const coverCssPath = path.resolve(rootDir, 'web/src/styles/cover.css');
const cssContent = fs.readFileSync(coverCssPath, 'utf8');

// 本文专属封面元数据
const meta = {
  title: '告别封面荒！\nMD2WX v1.0.2',
  digest: '彻底终结“文章排版两分钟，找封面两小时”的创作者内耗！9 大主题专属封面、微信 1:1 裁切安全区与真机大字排版实战。',
  author: '野生宝藏箱',
  tag: '先锋态度 · 封面工坊',
  badge: 'ACID BOLD',
  vol: '2026 · V1.0.2 RELEASE',
  website: 'MD2WX.ZANEVEN.COM'
};

const coverHtml = renderCoverHtml('acid-bold', 'banner', meta, false);

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

const tempHtmlPath = path.resolve(rootDir, 'assets/covers/temp_article_cover.html');
const targetPngLocal = path.resolve(rootDir, 'assets/covers/cover-v1.0.2-article.png');
const targetPngObsidian = '/Users/a1/Library/Mobile Documents/iCloud~md~obsidian/Documents/Z/00_Inbox/techBlog/assets/covers/cover-v1.0.2-article.png';

fs.writeFileSync(tempHtmlPath, fullHtml, 'utf8');

const chromeBin = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const cmd = `"${chromeBin}" --headless --disable-gpu --screenshot="${targetPngLocal}" --window-size=1175,500 "file://${tempHtmlPath}"`;
execSync(cmd, { stdio: 'inherit' });
fs.copyFileSync(targetPngLocal, targetPngObsidian);
fs.unlinkSync(tempHtmlPath);

console.log(`Successfully generated article cover -> ${targetPngLocal}`);

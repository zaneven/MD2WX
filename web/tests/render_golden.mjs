/**
 * Golden 渲染 harness：用 Web 端 parser.js 对固定输入按全部内置主题渲染，
 * 输出 JSON 供 tests/test_consistency.py 与 Python 端 parser.py 逐主题比对。
 * 用法: node --import ./tests/register-loader.mjs ./tests/render_golden.mjs <input.md>
 */
import { readFileSync } from 'node:fs';
import { markdownToWechatHtml, parseFrontmatter } from '../src/core/parser.js';
import { BUILTIN_THEMES } from '../src/core/themes.js';

const inputPath = process.argv[2];
if (!inputPath) {
  console.error('usage: node --import ./tests/register-loader.mjs ./tests/render_golden.mjs <input.md>');
  process.exit(2);
}

const raw = readFileSync(inputPath, 'utf8');
const { body } = parseFrontmatter(raw);

const renders = {};
for (const themeId of Object.keys(BUILTIN_THEMES)) {
  renders[themeId] = markdownToWechatHtml(body, themeId, null, { insertCover: false });
}

process.stdout.write(JSON.stringify({
  themes: Object.keys(BUILTIN_THEMES),
  themeIds: Object.values(BUILTIN_THEMES).map((t) => t.id),
  renders,
}));

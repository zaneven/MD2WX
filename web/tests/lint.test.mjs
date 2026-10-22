/** 发稿体检 lint.js 核心规则测试 (与 CLI 端 linter.py 镜像) */
import test from 'node:test';
import assert from 'node:assert/strict';

import {
  lintMarkdown,
  hasErrors,
  summarizeLint,
  autoFixPunctuation,
  computeReadingStats,
} from '../src/core/lint.js';

function clean(body, { title = '短标题', digest = '合格摘要内容', extra = '' } = {}) {
  return `---\ntitle: ${title}\ndigest: ${digest}\n${extra}---\n\n${body}`;
}

const codes = (issues) => issues.map((item) => item.code);

test('干净文章无问题', () => {
  const issues = lintMarkdown(clean('正文内容，标点规范。\n'));
  assert.deepEqual(issues, []);
  assert.equal(hasErrors(issues), false);
});

test('标题超长与结尾标点', () => {
  const issues = lintMarkdown(clean('正文。\n', { title: '标题以句号结尾。' }));
  assert.ok(codes(issues).includes('title-punctuation'));
  assert.equal(hasErrors(issues), false);

  const long = lintMarkdown(clean('正文。\n', { title: '超'.repeat(21) }));
  assert.ok(codes(long).includes('title-too-long'));
  assert.equal(hasErrors(long), true);
});

test('摘要半角标点', () => {
  const issues = lintMarkdown(clean('正文。\n', { digest: '摘要混用半角逗号,触发规则' }));
  assert.ok(codes(issues).includes('digest-punctuation'));
});

test('中文全半角标点混用与跳过代码/链接', () => {
  const issues = lintMarkdown(clean('中文,混用半角;标点:测试。\n'));
  const item = issues.find((i) => i.code === 'punctuation-mixed');
  assert.ok(item);
  assert.match(item.message, /全角/);
  assert.ok(item.line >= 6);

  const ignored = lintMarkdown(
    clean('`a,b:c` 与 [章节](#一级,标题) 跳过。\n\n```text\n中文,半角;\n```\n'),
  );
  assert.ok(!codes(ignored).includes('punctuation-mixed'));
});

test('中文括号混用会被检出', () => {
  assert.ok(codes(lintMarkdown(clean('中文括号(示例)触发。\n'))).includes('punctuation-mixed'));
});

test('Emoji 检出且跳过代码围栏', () => {
  assert.ok(codes(lintMarkdown(clean('正文表情 😀。\n'))).includes('emoji-banned'));
  assert.ok(!codes(lintMarkdown(clean('```text\n😀\n```\n'))).includes('emoji-banned'));
});

test('未闭合块级标签是 error，闭合或代码围栏内不报', () => {
  const bad = lintMarkdown(clean('<div>未闭合容器\n'));
  assert.ok(codes(bad).includes('html-unclosed'));
  assert.equal(hasErrors(bad), true);
  assert.ok(!codes(lintMarkdown(clean('<div>闭合</div>\n'))).includes('html-unclosed'));
  assert.ok(!codes(lintMarkdown(clean('```html\n<div>\n```\n'))).includes('html-unclosed'));
});

test('链接协议与格式校验', () => {
  const issues = lintMarkdown(
    clean('[坏协议](htp://example.com) [缺协议](www.example.com) [空]()\n'),
  );
  assert.equal(issues.filter((i) => i.code === 'link-format-invalid').length, 3);

  const ok = lintMarkdown(clean('[官网](https://example.com) [锚点](#小节) [邮件](mailto:a@b.com)\n'));
  assert.ok(!codes(ok).includes('link-format-invalid'));
});

test('控制字符为 error 且带行号', () => {
  const issues = lintMarkdown('---\ntitle: 短标题\ndigest: 摘要\n---\n\n正文\u0000截断\n');
  const item = issues.find((i) => i.code === 'control-chars');
  assert.equal(item.level, 'error');
  assert.equal(item.line, 6);
});

test('问题行号可定位到编辑器原始行', () => {
  const md = '---\ntitle: 短标题\ndigest: 摘要\n---\n\n正文。\n\n表情 😀\n';
  const item = lintMarkdown(md).find((i) => i.code === 'emoji-banned');
  assert.equal(item.line, 8);
});

test('summarizeLint 统计口径', () => {
  const issues = lintMarkdown(clean('正文,混用。\n', { title: '超'.repeat(21) }));
  const counts = summarizeLint(issues);
  assert.equal(counts.errors, 1);
  assert.ok(counts.warnings >= 1);
});

test('一键修复半角标点保留代码与链接', () => {
  const md = '中文,混用;标点:测试 `a,b` 与 [链接](#一级,标题)\n';
  const { text, fixed } = autoFixPunctuation(md);
  assert.ok(text.includes('中文，混用；标点：测试'));
  assert.ok(text.includes('`a,b`'));
  assert.ok(text.includes('#一级,标题'));
  assert.ok(fixed >= 3);

  const noop = autoFixPunctuation('中文，已经规范。\n');
  assert.equal(noop.fixed, 0);
});

test('阅读指标：字数 / 阅读时长 / 图片数量', () => {
  const stats = computeReadingStats(
    '---\ntitle: 短标题\ndigest: 摘要\n---\n\n# 标题\n\n中文正文 hello world\n\n![图](https://cdn.example.com/a.png)\n',
  );
  assert.ok(stats.chars > 0);
  assert.ok(stats.minutes >= 1);
  assert.equal(stats.images, 1);
});

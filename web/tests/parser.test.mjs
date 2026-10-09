/** parser.js 核心行为测试 */
import test from 'node:test';
import assert from 'node:assert/strict';

import {
  markdownToWechatHtml,
  parseFrontmatter,
  formatInline,
  collectExternalImageUrls,
} from '../src/core/parser.js';

test('parseFrontmatter 基本解析与剥离', () => {
  const { meta, body } = parseFrontmatter('---\ntitle: 标题\ntags: [a, b]\n---\n\n正文');
  assert.equal(meta.title, '标题');
  assert.deepEqual(meta.tags, ['a', 'b']);
  assert.equal(body.trim(), '正文');
});

test('formatInline 加粗斜体删除线', () => {
  const out = formatInline('**粗** 与 *斜* 与 ~~删~~', '#2563eb');
  assert.ok(out.includes('<strong>粗</strong>'));
  assert.ok(out.includes('<em>斜</em>'));
  assert.ok(out.includes('<del'));
});

test('formatInline 裸 URL 自动转脚注', () => {
  const footnotes = [];
  const out = formatInline('看 https://example.com/docs 很好', '#2563eb', '13.5px', footnotes);
  assert.ok(out.includes('[1]'));
  assert.equal(footnotes.length, 1);
  assert.equal(footnotes[0].url, 'https://example.com/docs');
});

test('formatInline 普通文本 HTML 转义', () => {
  const out = formatInline('<tag> & "q"', '#2563eb');
  assert.ok(out.includes('&lt;tag&gt;'));
  assert.ok(out.includes('&amp;'));
  assert.ok(out.includes('&quot;'));
});

test('markdownToWechatHtml 任务列表渲染 SVG 勾选框', () => {
  const html = markdownToWechatHtml('- [x] 完成\n- [ ] 待办', 'tech-blue', null, { insertCover: false });
  assert.ok(html.includes('<svg'));
  assert.ok(html.includes('rect'));
});

test('markdownToWechatHtml 外链自动转文末脚注', () => {
  const html = markdownToWechatHtml('见 [文档](https://example.com/x)', 'tech-blue', null, { insertCover: false });
  assert.ok(html.includes('参考链接与资料引用'));
  assert.ok(html.includes('[1]'));
});

test('markdownToWechatHtml 块级富文本 token 落块', () => {
  const html = markdownToWechatHtml('@@MDMERMAID_0@@\n\n正文', 'tech-blue', null, { insertCover: false });
  assert.ok(html.includes('data-md-rich-token="@@MDMERMAID_0@@"'));
});

test('collectExternalImageUrls 检测外链图并跳过微信 CDN 与代码围栏', () => {
  const md = [
    '![a](https://mmbiz.qpic.cn/mmbiz_png/x/640)',
    '![b](https://cdn.example.com/a.png)',
    '```text',
    '![c](https://cdn.example.com/evil.png)',
    '```',
  ].join('\n');
  const urls = collectExternalImageUrls(md);
  assert.deepEqual(urls, ['https://cdn.example.com/a.png']);
});

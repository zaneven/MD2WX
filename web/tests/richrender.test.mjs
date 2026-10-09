/** richrender.js 预处理 (prepareRichBlocks) 测试 —— 与 CLI 端同规则 */
import test from 'node:test';
import assert from 'node:assert/strict';

import { prepareRichBlocks, substituteRichHtml } from '../src/core/richrender.js';

test('抽取 mermaid 围栏为块级 token', () => {
  const { md, blocks } = prepareRichBlocks('# T\n\n```mermaid\ngraph TD; A-->B;\n```\n\n正文');
  assert.equal(blocks.length, 1);
  assert.equal(blocks[0].kind, 'mermaid');
  assert.equal(blocks[0].display, true);
  assert.equal(blocks[0].content, 'graph TD; A-->B;');
  assert.ok(blocks[0].token.startsWith('@@MDMERMAID_'));
  assert.ok(!md.includes('```mermaid'));
});

test('抽取多行公式块', () => {
  const { blocks } = prepareRichBlocks('$$\nx = 1\ny = 2\n$$');
  assert.equal(blocks.length, 1);
  assert.equal(blocks[0].kind, 'math');
  assert.equal(blocks[0].display, true);
  assert.ok(blocks[0].content.includes('x = 1'));
});

test('行内公式与价格安全', () => {
  const { md, blocks } = prepareRichBlocks('质能 $E=mc^2$ 有名，价格 $100 and $200 不误判。');
  assert.equal(blocks.length, 1);
  assert.equal(blocks[0].content, 'E=mc^2');
  assert.equal(blocks[0].display, false);
  assert.ok(md.includes('$100 and $200'));
});

test('代码围栏内不被抽取', () => {
  const { blocks } = prepareRichBlocks('```\nCost: $a + $b\n```');
  assert.deepEqual(blocks, []);
});

test('substituteRichHtml 替换占位与行内 token', () => {
  const html = '<div style="margin: 22px 0; text-align: center;" data-md-rich-token="@@MDMERMAID_0@@"></div><p>x @@MDMATH_0@@ y</p>';
  const out = substituteRichHtml(html, new Map([
    ['@@MDMERMAID_0@@', '<div>IMG1</div>'],
    ['@@MDMATH_0@@', '<img src="data:" />'],
  ]));
  assert.ok(out.includes('<div>IMG1</div>'));
  assert.ok(out.includes('<img src="data:" />'));
  assert.ok(!out.includes('@@MD'));
});

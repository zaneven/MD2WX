/** themes.js / highlighter.js 基础行为测试 */
import test from 'node:test';
import assert from 'node:assert/strict';

import { getTheme, isDarkTheme, BUILTIN_THEMES, DEFAULT_THEME_ID } from '../src/core/themes.js';
import { highlightCode } from '../src/core/highlighter.js';

test('内置主题数量与默认主题', () => {
  assert.equal(Object.keys(BUILTIN_THEMES).length, 13);
  assert.ok(BUILTIN_THEMES[DEFAULT_THEME_ID]);
});

test('getTheme 兜底合并与兼容包装', () => {
  const t = getTheme('tech-blue');
  assert.equal(t.accent, t.colors.accent);
  assert.equal(t.h2_style, t.styles.h2);
  assert.equal(t.id, 'tech-blue');
});

test('getTheme 未知主题回退默认', () => {
  assert.equal(getTheme('not-exist').id, DEFAULT_THEME_ID);
});

test('isDarkTheme 启发式', () => {
  assert.ok(isDarkTheme(getTheme('terminal-geek')));
  assert.ok(!isDarkTheme(getTheme('tech-blue')));
});

test('highlightCode 纯文本不拆分', () => {
  const out = highlightCode('a - b / c', 'text');
  assert.ok(!out.includes('<span'));
});

test('highlightCode 关键字与字符串着色', () => {
  const out = highlightCode('const s = "x";', 'js');
  assert.ok(out.includes('#f472b6'));
  assert.ok(out.includes('#34d399'));
});

test('highlightCode 转义特殊字符', () => {
  const out = highlightCode('const s = "<b>&</b>";', 'js');
  assert.ok(out.includes('&lt;b&gt;'));
  assert.ok(out.includes('&amp;'));
});

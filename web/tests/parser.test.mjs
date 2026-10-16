/** parser.js 核心行为测试 */
import test from 'node:test';
import assert from 'node:assert/strict';

import {
  markdownToWechatHtml,
  parseFrontmatter,
  formatInline,
  collectExternalImageUrls,
  expandObsidianImages,
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

test('formatInline 单波浪删除线', () => {
  const out = formatInline('~单波浪~ 与 a ~ b ~ c', '#2563eb');
  assert.ok(out.includes('<del'));
  assert.ok(out.includes('a ~ b ~ c'));
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

// ==================== Obsidian wiki 图片语法兼容 ====================

test('expandObsidianImages 各种语法归一化', () => {
  assert.equal(expandObsidianImages('![[arch.png]]'), '![](arch.png)');
  assert.equal(expandObsidianImages('![[d.png|说明]]'), '![说明](d.png)');
  assert.equal(expandObsidianImages('![[d.png|320]]'), '![](d.png)');
  assert.equal(expandObsidianImages('![[d.png|100x200]]'), '![](d.png)');
  assert.equal(expandObsidianImages('![[my image.png]]'), '![](my%20image.png)');
  assert.equal(expandObsidianImages('[[arch.png]]'), '![](arch.png)');
  assert.equal(expandObsidianImages('[[某篇笔记]] 与 [[Note Name]]'), '[[某篇笔记]] 与 [[Note Name]]');
});

test('expandObsidianImages 跳过围栏与行内代码', () => {
  assert.equal(expandObsidianImages('`![[x.png]]`'), '`![[x.png]]`');
  assert.equal(expandObsidianImages('```\n![[y.png]]\n```'), '```\n![[y.png]]\n```');
});

test('expandObsidianImages 幂等', () => {
  const src = '![[a.png]] [[b.png|c]] [[note]] ![alt](x.png)';
  const once = expandObsidianImages(src);
  assert.equal(expandObsidianImages(once), once);
  assert.ok(once.includes('![alt](x.png)'));
});

test('markdownToWechatHtml 渲染 Obsidian 图片为 img', () => {
  const html = markdownToWechatHtml(
    '段落前 ![[架构图.png]] 中段。\n\n![[photo.jpeg]]\n\n![[d.png|系统架构]]\n\n笔记 [[某篇笔记]]',
    'tech-blue', null, { insertCover: false },
  );
  assert.equal((html.match(/<img/g) || []).length, 3);
  assert.ok(html.includes('<img src="架构图.png"'));
  assert.ok(html.includes('alt="系统架构"'));
  assert.ok(html.includes('[[某篇笔记]]'));
});

// ==================== CommonMark + GFM + 扩展语法完整支持 (v1.5.0) ====================

const render = (md, opts = {}) => markdownToWechatHtml(md, 'tech-blue', null, { insertCover: false, ...opts });

test('段落合并：CJK 直接拼接，ASCII 补空格', () => {
  assert.ok(render('第一行文字\n第二行文字').includes('第一行文字第二行文字'));
  assert.ok(render('english words\nnext line').includes('english words next line'));
});

test('硬换行：行尾两空格与反斜杠', () => {
  assert.ok(render('行尾两空格  \n下一行。').includes('<br />'));
  assert.ok(render('行尾反斜杠\\\n下一行。').includes('<br />'));
});

test('Setext 标题与分割线歧义消解', () => {
  const html = render('标题一\n===\n\n标题二\n---');
  assert.ok(html.includes('标题一'));
  assert.ok(html.includes('标题二'));
  assert.ok(render('---').includes('<hr'));
});

test('分割线变体', () => {
  for (const marker of ['----', '* * *', '- - -', '____']) {
    assert.ok(render(marker).includes('<hr'), marker);
  }
});

test('波浪围栏与四反引号围栏', () => {
  assert.ok(render('~~~python\nprint(1)\n~~~').includes('print'));
  assert.ok(render('````\ncode with ``` inside\n````').includes('code&nbsp;with'));
});

test('h1-h6 路由与标题行内格式化', () => {
  const html = render('# 一\n## 二\n### 三\n#### 四\n##### 五\n###### 六');
  for (const t of ['一', '二', '三', '四', '五', '六']) assert.ok(html.includes(t));
  assert.ok(render('## 标题含 **加粗**').includes('<strong>加粗</strong>'));
});

test('有序列表保留源编号', () => {
  const html = render('1. 第一\n2. 第二\n5. 第五');
  assert.ok(html.replace(/ /g, '').includes('>1.</span>'));
  assert.ok(html.replace(/ /g, '').includes('>5.</span>'));
});

test('加号列表标记', () => {
  assert.ok(render('+ 加号项').includes('加号项'));
});

test('嵌套列表缩进层级', () => {
  const html = render('- 顶级\n  - 子级\n    - 三级');
  assert.equal((html.match(/padding-left: 16px/g) || []).length, 2);
});

test('有序嵌套与混合标记', () => {
  const html = render('1. 父项\n   1. 子有序\n   - 子无序');
  for (const t of ['父项', '子有序', '子无序']) assert.ok(html.includes(t));
});

test('有序列表内任务项', () => {
  const html = render('1. [x] 已完成步骤');
  assert.ok(html.includes('<svg'));
  assert.ok(html.includes('已完成步骤'));
});

test('缩进代码块', () => {
  assert.ok(render('段\n\n    code line one\n    two').includes('code&nbsp;line&nbsp;one'));
});

test('嵌套引用块', () => {
  const html = render('> 外层\n>> 内层');
  assert.ok(html.split('<blockquote').length - 1 >= 2);
  assert.ok(html.includes('内层'));
});

test('引用块内作者手写的分行逐行保留', () => {
  const html = render('> **作者**：野生宝藏箱\n> **核心标签**：AI 自动化 · WePost\n> **一句话简介**：从热点抓取到静默同步。');
  assert.ok(
    html.includes(
      '<strong>作者</strong>：野生宝藏箱<br /><strong>核心标签</strong>：AI 自动化 · WePost<br /><strong>一句话简介</strong>：从热点抓取到静默同步。'
    )
  );
  assert.ok(!html.includes('<br /><br />'));
});

test('引用块之外的段落仍走软换行拼接', () => {
  const html = render('这是一段被作者在源码里\n折成两行的中文正文。');
  assert.ok(html.includes('这是一段被作者在源码里折成两行的中文正文。'));
  assert.ok(!html.includes('<br />'));
});

test('表格对齐与转义管道', () => {
  const html = render('| A | B | C |\n| :--- | :---: | ---: |\n| 左 | 中 | 右 |');
  assert.ok(html.includes('text-align: center;'));
  assert.ok(html.includes('text-align: right;'));
  assert.ok(render('| 语法 |\n| --- |\n| a \\| b |').includes('<td'));
});

test('参考式链接与参考式图片', () => {
  const md = '见 [手册][m] 与 [m] 折叠；图 ![图标][i]。\n\n[m]: https://ref.io/manual\n[i]: https://ref.io/logo.png';
  const html = render(md);
  assert.ok(html.includes('[1]'));
  assert.ok(html.includes('<img src="https://ref.io/logo.png"'));
  assert.ok(!html.includes('[m]:'));
  assert.ok(!html.includes('[i]:'));
});

test('脚注语法 [^id]', () => {
  const md = '引用[^1]与[^note]。\n\n[^1]: 第一条说明\n[^note]: 第二条说明';
  const html = render(md);
  assert.ok(html.includes('[1]'));
  assert.ok(html.includes('[2]'));
  assert.ok(html.includes('第一条说明'));
  assert.ok(!html.includes('[^1]:'));
});

test('反斜杠转义', () => {
  const html = render('\\*不是斜体\\* 与 1\\. 不是列表');
  assert.ok(!html.includes('<em>'));
  assert.ok(html.includes('不是斜体'));
});

test('实体透传不双重转义', () => {
  const html = render('版权 &copy; 与 &amp; 和 &#123;');
  assert.ok(html.includes('&copy;'));
  assert.ok(!html.includes('&amp;copy;'));
  assert.ok(!html.includes('&amp;amp;'));
});

test('HTML 白名单放行与其余转义', () => {
  const html = render('<b>粗</b> <u>下划</u> <mark>标</mark> <script>evil</script> <kbd>键</kbd>');
  assert.ok(html.includes('<b>粗</b>'));
  assert.ok(html.includes('<u>下划</u>'));
  assert.ok(html.includes('<mark>标</mark>'));
  assert.ok(!html.includes('<script>'));
  assert.ok(!html.includes('<kbd>'));
});

test('==高亮== 扩展语法', () => {
  const html = render('重点==高亮内容==结束');
  assert.ok(html.includes('<mark'));
  assert.ok(html.includes('高亮内容'));
});

test('双反引号行内代码', () => {
  const html = render('``内含 ` 井号`` 结束');
  assert.ok(html.includes('<code'));
  assert.ok(html.includes('内含'));
});

test('段落中行内图片', () => {
  const html = render('段落中 ![小图](https://cdn.example.com/x.png) 内嵌');
  assert.ok(html.includes('<img'));
  assert.ok(html.includes('内嵌'));
});

test('尖括号自动链接', () => {
  const html = render('访问 <https://auto.io/x> 与 <mail@test.io>');
  assert.ok(html.includes('auto.io/x'));
  assert.ok(html.includes('mail@test.io'));
  assert.ok(!html.includes('&lt;https'));
});

test('词内下划线不触发斜体', () => {
  assert.ok(!render('变量 foo_bar_baz 保持原样').includes('<em>'));
});

test('linkToFootnote=false 时 [^id] 脚注仍可用', () => {
  const md = '脚注[^1]引用。\n\n[^1]: 说明文字';
  const html = render(md, { linkToFootnote: false });
  assert.ok(html.includes('说明文字'));
  assert.ok(!html.includes('[^1]:'));
});

/**
 * MD2WX Web Studio - 大纲导航 (TOC 抽屉)
 * 从正文 H1-H6 自动生成层级目录，点击定位编辑器对应行并同步滚动右侧预览
 */
import { parseFrontmatter } from '../core/parser.js';
import { gotoEditorLine, revealPreviewHeading, lineStartOffset } from './editor-nav.js';

const HEADING_RE = /^(#{1,6})\s+(.+?)\s*$/;
const FENCE_OPEN_RE = /^(```+|~~~+)/;

let drawerEl = null;
let listEl = null;
let countEl = null;
let lastSignature = null;
let initialized = false;

/**
 * 解析正文标题 (跳过围栏代码块)，返回 [{ level, text, line }]，行号为全文 1-based
 */
export function extractHeadings(rawMd) {
  const normalized = String(rawMd || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const { body } = parseFrontmatter(normalized);
  const offset = normalized.split('\n').length - body.split('\n').length;
  const headings = [];
  let fenceMarker = '';

  body.split('\n').forEach((line, i) => {
    if (fenceMarker) {
      const stripped = line.trim();
      if (stripped.startsWith(fenceMarker) && /^[`~]+$/.test(stripped)) fenceMarker = '';
      return;
    }
    const fence = line.match(FENCE_OPEN_RE);
    if (fence) {
      fenceMarker = fence[1];
      return;
    }
    const match = line.match(HEADING_RE);
    if (!match) return;
    headings.push({
      level: match[1].length,
      text: match[2].replace(/\s+#+\s*$/, '').trim(),
      line: i + 1 + offset,
    });
  });
  return headings;
}

function setDrawerOpen(open) {
  if (!drawerEl) return;
  drawerEl.classList.toggle('show', open);
  const btn = document.getElementById('tool-toc');
  if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
}

/** 展开大纲抽屉 (供外部调用) */
export function openTocDrawer() {
  setDrawerOpen(true);
}

/** 折叠大纲抽屉 */
export function closeTocDrawer() {
  setDrawerOpen(false);
}

/**
 * 每次渲染后刷新目录树；仅在标题指纹变化时重建 DOM
 */
export function updateToc(rawMd) {
  if (!listEl) return;
  const headings = extractHeadings(rawMd);
  const signature = headings.map((h) => `${h.level}|${h.line}|${h.text}`).join('§');
  if (signature === lastSignature) return;
  lastSignature = signature;

  if (countEl) countEl.textContent = `${headings.length} 个标题`;
  listEl.innerHTML = '';

  if (!headings.length) {
    const empty = document.createElement('div');
    empty.className = 'toc-empty';
    empty.textContent = '正文还没有标题，输入 # 开头即可生成大纲';
    listEl.appendChild(empty);
    return;
  }

  const minLevel = Math.min(...headings.map((h) => h.level));
  headings.forEach((heading) => {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'toc-item';
    item.style.paddingLeft = `${10 + (heading.level - minLevel) * 14}px`;
    item.title = `H${heading.level} · 第 ${heading.line} 行`;

    const badge = document.createElement('span');
    badge.className = 'toc-level';
    badge.textContent = `H${heading.level}`;

    const text = document.createElement('span');
    text.className = 'toc-text';
    text.textContent = heading.text;

    item.appendChild(badge);
    item.appendChild(text);
    item.addEventListener('click', () => {
      gotoEditorLine(heading.line);
      revealPreviewHeading(heading.text);
      listEl.querySelectorAll('.toc-item.active').forEach((el) => el.classList.remove('active'));
      item.classList.add('active');
    });
    listEl.appendChild(item);
  });
}

/** 绑定工具栏按钮、抽屉关闭与 Esc / 外部点击交互 */
export function initToc() {
  if (initialized) return;
  initialized = true;

  drawerEl = document.getElementById('toc-drawer');
  listEl = document.getElementById('toc-list');
  countEl = document.getElementById('toc-count');
  if (!drawerEl) return;

  document.getElementById('tool-toc')?.addEventListener('click', (e) => {
    e.stopPropagation();
    setDrawerOpen(!drawerEl.classList.contains('show'));
  });
  document.getElementById('btn-toc-close')?.addEventListener('click', () => closeTocDrawer());

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && drawerEl.classList.contains('show')) closeTocDrawer();
  });
  document.addEventListener('click', (e) => {
    if (!drawerEl.classList.contains('show')) return;
    if (e.target.closest('#toc-drawer') || e.target.closest('#tool-toc')) return;
    closeTocDrawer();
  });
}

/**
 * 定位并高亮某个标题所在行 (供外部联动)
 */
export function jumpToHeading(heading) {
  if (!heading) return;
  gotoEditorLine(heading.line);
  revealPreviewHeading(heading.text);
}

// 供单元测试或外部工具复用行偏移计算
export { lineStartOffset };

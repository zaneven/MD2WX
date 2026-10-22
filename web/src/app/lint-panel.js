/**
 * MD2WX Web Studio - 发稿体检面板
 * 预览区底部常驻 Lint 问题栏：规则与 CLI 端一致，error 级别阻断复制动作，
 * 点击问题项定位到编辑器对应行，标点类问题支持一键修复
 */
import { lintMarkdown, summarizeLint, autoFixPunctuation } from '../core/lint.js';
import { state } from './state.js';
import { showToast } from './ui.js';
import { gotoEditorLine } from './editor-nav.js';

let panelEl = null;
let listEl = null;
let summaryEl = null;
let errorChip = null;
let warnChip = null;
let fixBtn = null;
let lastSignature = null;

/** 折叠/展开体检面板 */
export function expandLintPanel() {
  if (!panelEl) return;
  panelEl.classList.add('expanded');
  const toggle = document.getElementById('lint-panel-toggle');
  if (toggle) toggle.setAttribute('aria-expanded', 'true');
}

export function collapseLintPanel() {
  if (!panelEl) return;
  panelEl.classList.remove('expanded');
  const toggle = document.getElementById('lint-panel-toggle');
  if (toggle) toggle.setAttribute('aria-expanded', 'false');
}

function toggleLintPanel() {
  if (!panelEl) return;
  if (panelEl.classList.contains('expanded')) collapseLintPanel();
  else expandLintPanel();
}

function issueRow(issue) {
  const row = document.createElement('button');
  row.type = 'button';
  row.className = `lint-issue ${issue.level}`;
  row.title = `点击定位到第 ${issue.line} 行`;

  const level = document.createElement('span');
  level.className = 'lint-issue-level';
  level.textContent = issue.level === 'error' ? '阻断' : '建议';

  const code = document.createElement('span');
  code.className = 'lint-issue-code';
  code.textContent = issue.code;

  const message = document.createElement('span');
  message.className = 'lint-issue-message';
  message.textContent = issue.message;

  const line = document.createElement('span');
  line.className = 'lint-issue-line';
  line.textContent = `L${issue.line}`;

  row.appendChild(level);
  row.appendChild(code);
  row.appendChild(message);
  row.appendChild(line);
  row.addEventListener('click', () => {
    gotoEditorLine(issue.line);
    row.classList.add('active');
  });
  return row;
}

/**
 * 渲染问题清单
 * @param {Array} issues lintMarkdown 输出
 * @param {boolean} force 强制重建 (标点修复后需要刷新)
 */
function renderIssues(issues, force = false) {
  if (!panelEl) return;
  const signature = issues.map((i) => `${i.level}|${i.code}|${i.line}|${i.message}`).join('§');
  if (!force && signature === lastSignature) return;
  lastSignature = signature;

  const { errors, warnings } = summarizeLint(issues);
  panelEl.classList.toggle('has-errors', errors > 0);
  panelEl.classList.toggle('is-clean', errors === 0 && warnings === 0);

  if (summaryEl) {
    if (errors > 0) summaryEl.textContent = `${errors} 项阻断 · ${warnings} 项建议`;
    else if (warnings > 0) summaryEl.textContent = `${warnings} 项优化建议`;
    else summaryEl.textContent = '发稿体检通过';
  }
  if (errorChip) {
    errorChip.textContent = `阻断 ${errors}`;
    errorChip.classList.toggle('is-hot', errors > 0);
  }
  if (warnChip) {
    warnChip.textContent = `建议 ${warnings}`;
    warnChip.classList.toggle('is-hot', warnings > 0);
  }
  if (fixBtn) {
    const hasPunct = issues.some((i) => i.code === 'punctuation-mixed');
    fixBtn.disabled = !hasPunct;
    fixBtn.classList.toggle('is-active', hasPunct);
  }

  if (!listEl) return;
  listEl.innerHTML = '';
  if (!issues.length) {
    const ok = document.createElement('div');
    ok.className = 'lint-clean-hint';
    ok.textContent = '标题、摘要、标点、Emoji、外链图片与 HTML 标签均符合发稿规范。';
    listEl.appendChild(ok);
    return;
  }

  // error 优先，其次按行号升序，便于先处理阻断问题
  const ordered = [...issues].sort((a, b) => {
    if (a.level !== b.level) return a.level === 'error' ? -1 : 1;
    return a.line - b.line;
  });
  ordered.forEach((issue) => listEl.appendChild(issueRow(issue)));
}

/**
 * 每次渲染后刷新体检结果 (纯本地同步计算，无网络请求)
 * @param {string} rawMd 完整 Markdown
 */
export function updateLintPanel(rawMd) {
  const issues = lintMarkdown(rawMd);
  state.lintIssues = issues;
  renderIssues(issues);
}

/** 一键修复中文半角标点并回写编辑器 */
function fixPunctuation() {
  const textarea = document.getElementById('markdown-input');
  if (!textarea) return;
  const { text, fixed } = autoFixPunctuation(textarea.value);
  if (!fixed) {
    showToast('没有检测到需要修复的中文半角标点', 'error');
    return;
  }
  textarea.value = text;
  textarea.dispatchEvent(new Event('input', { bubbles: true }));
  renderIssues(lintMarkdown(text), true);
  showToast(`已修复 ${fixed} 处中文半角标点`);
}

/** 初始化面板 DOM 事件 (在 app 启动时调用一次) */
export function initLintPanel() {
  panelEl = document.getElementById('lint-panel');
  listEl = document.getElementById('lint-issue-list');
  summaryEl = document.getElementById('lint-summary');
  errorChip = document.getElementById('lint-error-count');
  warnChip = document.getElementById('lint-warn-count');
  fixBtn = document.getElementById('btn-fix-punctuation');
  if (!panelEl) return;

  document.getElementById('lint-panel-toggle')?.addEventListener('click', toggleLintPanel);
  fixBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    fixPunctuation();
  });
  collapseLintPanel();
}

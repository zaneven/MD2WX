/**
 * MD2WX Web Studio - 编辑器定位导航
 * 供大纲抽屉与发稿体检面板共用：按行号跳转编辑器、按标题同步预览视口
 */

/** 计算第 line 行 (1-based) 在文本中的起始偏移 */
export function lineStartOffset(text, line) {
  const target = Math.max(1, line);
  let offset = 0;
  for (let i = 1; i < target; i += 1) {
    const next = text.indexOf('\n', offset);
    if (next < 0) return text.length;
    offset = next + 1;
  }
  return Math.min(offset, text.length);
}

/**
 * 把光标定位到指定行并滚动到可视区域
 * @param {number} line 1-based 行号
 */
export function gotoEditorLine(line) {
  const textarea = document.getElementById('markdown-input');
  if (!textarea) return;
  const target = Math.max(1, line);
  const start = lineStartOffset(textarea.value, target);
  const newline = textarea.value.indexOf('\n', start);
  const end = newline < 0 ? textarea.value.length : newline;

  textarea.focus();
  textarea.setSelectionRange(start, end);

  const lineHeight = parseFloat(getComputedStyle(textarea).lineHeight) || 22;
  const visibleLines = textarea.clientHeight / lineHeight;
  const desiredTop = Math.max(0, (target - Math.max(2, visibleLines / 3)) * lineHeight);
  textarea.scrollTop = desiredTop;
}

/** 归一化标题文本用于预览区匹配 (忽略空白与 Markdown 强调符) */
function normalizeHeading(text) {
  return String(text || '')
    .replace(/[*_`~]/g, '')
    .replace(/\s+/g, '')
    .trim();
}

/**
 * 右侧预览视口滚动到对应标题
 * 微信内联标题没有原生 id，这里按文本匹配叶子级文本块
 * @param {string} headingText 标题纯文本
 */
export function revealPreviewHeading(headingText) {
  const previewTarget = document.getElementById('preview-render-target');
  if (!previewTarget) return;
  const needle = normalizeHeading(headingText);
  if (!needle) return;

  const candidates = Array.from(previewTarget.querySelectorAll('*'));
  let fallback = null;
  for (const el of candidates) {
    // 只匹配叶子级文本块，避免命中包裹整个正文的容器
    if (el.children.length > 0) continue;
    const text = normalizeHeading(el.textContent);
    if (!text) continue;
    if (text === needle) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }
    if (!fallback && text.startsWith(needle.slice(0, 12))) fallback = el;
  }
  if (fallback) fallback.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

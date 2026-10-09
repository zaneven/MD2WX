/**
 * MD2WX Web Studio - 双栏联动滚动
 * 编辑器滚动按比例同步至仿真预览区 (带互斥锁防抖)
 */

import { state } from './state.js';

const textarea = document.getElementById('markdown-input');
const gutter = document.getElementById('editor-gutter');
const phoneScroll = document.getElementById('phone-content-scroll');
const previewCanvas = document.getElementById('preview-canvas');

/**
 * 双栏联动同步滚动 (带互斥锁防抖)
 */
export function handleSyncScroll() {
  syncGutterScroll();
  if (!state.enableSyncScroll) return;
  if (state.isSyncingScroll) return;

  state.isSyncingScroll = true;
  const targetScrollEl = state.currentViewMode === 'desktop' ? previewCanvas : phoneScroll;
  if (targetScrollEl) {
    const editorScrollable = textarea.scrollHeight - textarea.clientHeight;
    if (editorScrollable > 0) {
      const scrollRatio = textarea.scrollTop / editorScrollable;
      const targetScrollable = targetScrollEl.scrollHeight - targetScrollEl.clientHeight;
      targetScrollEl.scrollTop = scrollRatio * targetScrollable;
    }
  }
  requestAnimationFrame(() => {
    state.isSyncingScroll = false;
  });
}

function syncGutterScroll() {
  gutter.scrollTop = textarea.scrollTop;
}

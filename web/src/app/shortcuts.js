/**
 * MD2WX Web Studio - 全局快捷键
 * Cmd/Ctrl + S 保存草稿、Cmd/Ctrl + Enter 复制排版、编辑器内 B/I/K 快捷格式化
 */

import { insertFormatting } from './editor.js';
import { saveDraft } from './preview.js';
import { handleCopy } from './publish.js';
import { showToast } from './ui.js';

const textarea = document.getElementById('markdown-input');

/**
 * 绑定全局键盘快捷键
 */
export function bindShortcuts() {
  // 快捷键支持 (Cmd/Ctrl + S, Cmd/Ctrl + Enter, Cmd/Ctrl + B/I/K)
  document.addEventListener('keydown', (e) => {
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const modifier = isMac ? e.metaKey : e.ctrlKey;

    // Cmd/Ctrl + S: 快速保存草稿
    if (modifier && e.key.toLowerCase() === 's') {
      e.preventDefault();
      saveDraft(textarea.value);
      showToast('草稿已成功保存至本地浏览器');
      return;
    }

    // Cmd/Ctrl + Enter: 复制排版到微信
    if (modifier && e.key === 'Enter') {
      e.preventDefault();
      handleCopy();
      return;
    }

    // 编辑器内部快捷格式化
    if (document.activeElement === textarea && modifier) {
      if (e.key.toLowerCase() === 'b') {
        e.preventDefault();
        insertFormatting('**', '**', '粗体文字');
      } else if (e.key.toLowerCase() === 'i') {
        e.preventDefault();
        insertFormatting('*', '*', '斜体文字');
      } else if (e.key.toLowerCase() === 'k') {
        e.preventDefault();
        insertFormatting('[', '](https://example.com)', '链接说明');
      }
    }
  });
}

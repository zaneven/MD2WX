/**
 * MD2WX Web Studio - 通用 UI 基础设施
 * SVG 矢量图标初始化、浮动 Toast 通知与手机状态栏实时时钟
 */

import { ICONS, setIcon } from '../assets/icons.js';

const toastContainer = document.getElementById('toast-container');
const phoneClock = document.getElementById('phone-clock');

/**
 * 初始化所有 SVG 矢量图标
 */
export function initIcons() {
  setIcon('#logo-icon', 'logo');
  setIcon('#theme-chevron-icon', 'chevronDown');
  setIcon('#icon-sample', 'fileText');
  setIcon('#icon-drafts', 'folder');
  setIcon('#icon-draft-new', 'plus');
  setIcon('#icon-download', 'download');
  setIcon('#icon-copy-header', 'copy');
  setIcon('#icon-copy-floating', 'copy');
  setIcon('#icon-phone', 'smartphone');
  setIcon('#icon-desktop', 'monitor');
  setIcon('#icon-wifi', 'wifi');
  setIcon('#icon-battery', 'battery');
  setIcon('#icon-nav-back', 'arrowLeft');
  setIcon('#icon-nav-more', 'moreVertical');

  // Toolbar & Header Icons
  setIcon('#icon-settings', 'settings');
  setIcon('#icon-sliders-title', 'sliders');
  setIcon('#icon-bold', 'bold');
  setIcon('#icon-italic', 'italic');
  setIcon('#icon-h1', 'heading1');
  setIcon('#icon-h2', 'heading2');
  setIcon('#icon-h3', 'heading3');
  setIcon('#icon-strike', 'strikethrough');
  setIcon('#icon-highlight', 'highlight');
  setIcon('#icon-inline-code', 'inlineCode');
  setIcon('#icon-list-ordered', 'listOrdered');
  setIcon('#icon-list-task', 'listTodo');
  setIcon('#icon-math', 'sigma');
  setIcon('#icon-mermaid', 'workflow');
  setIcon('#icon-quote', 'quote');
  setIcon('#icon-code', 'code');
  setIcon('#icon-table', 'table');
  setIcon('#icon-list', 'list');
  setIcon('#icon-minus', 'minus');
  setIcon('#icon-link', 'link');
  setIcon('#icon-image', 'imagePlus');
  setIcon('#icon-trash', 'trash');

  // Cover Studio & Changelog Icons
  setIcon('#icon-cover-trigger', 'sparkles');
  setIcon('#icon-cover-window-logo', 'image');
  setIcon('#icon-cover-close', 'x');
  setIcon('#icon-ratio-banner', 'rectangle');
  setIcon('#icon-ratio-square', 'square');
  setIcon('#icon-ratio-dual', 'dual');
  setIcon('#icon-copy-coords', 'crop');
  setIcon('#icon-action-hint', 'info');
  setIcon('#icon-copy-cover', 'copy');
  setIcon('#icon-download-cover', 'download');
  setIcon('#icon-sync-article', 'refresh');
  setIcon('#icon-changelog-header', 'info');
  setIcon('#icon-changelog-close', 'x');
  setIcon('#icon-feat-theme', 'palette');
  setIcon('#icon-feat-ratio', 'smartphone');
  setIcon('#icon-feat-copy', 'copy');
}

/**
 * 显示浮动 Toast 通知
 */
export function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = 'toast';

  const iconSpan = document.createElement('span');
  iconSpan.className = 'toast-icon';
  iconSpan.innerHTML = type === 'success' ? ICONS.check : ICONS.copy;

  const msgSpan = document.createElement('span');
  msgSpan.className = 'toast-message';
  msgSpan.textContent = message;

  toast.appendChild(iconSpan);
  toast.appendChild(msgSpan);
  toastContainer.appendChild(toast);

  // Trigger enter animation
  requestAnimationFrame(() => {
    toast.classList.add('show');
  });

  // Auto dismiss
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => {
      if (toast.parentNode) {
        toastContainer.removeChild(toast);
      }
    }, 300);
  }, 2600);
}

/**
 * 更新手机顶部实时时钟
 */
export function updateClock() {
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  phoneClock.textContent = `${hours}:${minutes}`;
}

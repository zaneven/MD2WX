/**
 * MD2WX Web Studio - 排版微调设置面板
 * 字号/行距分段选择、封面插入与脚注/同步滚动开关、弹窗交互
 */

import { state } from './state.js';
import { showToast } from './ui.js';
import { renderPreview } from './preview.js';

/**
 * 初始化排版微调设置面板
 */
export function initSettings() {
  const settingsBtn = document.getElementById('btn-settings-trigger');
  const settingsDropdown = document.getElementById('settings-dropdown-menu');
  const toggleInsertCover = document.getElementById('toggle-insert-cover');
  const toggleFootnotes = document.getElementById('toggle-footnotes');
  const toggleSyncScroll = document.getElementById('toggle-sync-scroll');
  const themeDropdownMenu = document.getElementById('theme-dropdown-menu');

  if (!settingsBtn || !settingsDropdown) return;

  // 初始化 UI 勾选状态
  if (toggleInsertCover) toggleInsertCover.checked = state.insertCoverEnabled;
  if (toggleFootnotes) toggleFootnotes.checked = state.enableFootnotes;
  if (toggleSyncScroll) toggleSyncScroll.checked = state.enableSyncScroll;

  // 插入封面图开关 (在可复制的微信正文顶部显示封面图)
  if (toggleInsertCover) {
    toggleInsertCover.addEventListener('change', (e) => {
      state.insertCoverEnabled = e.target.checked;
      localStorage.setItem('md2wx_insert_cover', String(state.insertCoverEnabled));
      renderPreview();
      showToast(state.insertCoverEnabled ? '已开启：在微信正文顶部插入封面图' : '已关闭正文顶部封面图');
    });
  }

  // 正文字号切换
  document.querySelectorAll('#control-font-size .segment-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.val === state.currentFontSize);
    btn.addEventListener('click', () => {
      document.querySelectorAll('#control-font-size .segment-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.currentFontSize = btn.dataset.val;
      localStorage.setItem('md2wx_font_size', state.currentFontSize);
      renderPreview();
    });
  });

  // 行距切换
  document.querySelectorAll('#control-line-height .segment-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.val === state.currentLineHeight);
    btn.addEventListener('click', () => {
      document.querySelectorAll('#control-line-height .segment-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.currentLineHeight = btn.dataset.val;
      localStorage.setItem('md2wx_line_height', state.currentLineHeight);
      renderPreview();
    });
  });

  // 外链转文末脚注开关
  if (toggleFootnotes) {
    toggleFootnotes.addEventListener('change', (e) => {
      state.enableFootnotes = e.target.checked;
      localStorage.setItem('md2wx_enable_footnotes', String(state.enableFootnotes));
      renderPreview();
      showToast(state.enableFootnotes ? '已开启外链自动转文末脚注' : '已关闭外链转脚注');
    });
  }

  // 双栏同步滚动开关
  if (toggleSyncScroll) {
    toggleSyncScroll.addEventListener('change', (e) => {
      state.enableSyncScroll = e.target.checked;
      localStorage.setItem('md2wx_sync_scroll', String(state.enableSyncScroll));
      showToast(state.enableSyncScroll ? '已开启双栏联动同步滚动' : '已关闭双栏同步滚动');
    });
  }

  // 弹窗切换与点击外部自动收起
  settingsBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    settingsDropdown.classList.toggle('show');
    themeDropdownMenu.classList.remove('show');
  });

  document.addEventListener('click', (e) => {
    if (!settingsBtn.contains(e.target) && !settingsDropdown.contains(e.target)) {
      settingsDropdown.classList.remove('show');
    }
  });
}

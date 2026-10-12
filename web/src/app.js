/**
 * MD2WX Web Studio - 主应用入口
 * 严格遵循规范：无任何 Emoji，全站统一高质感 SVG 矢量图标
 * 仅负责导入各功能模块并做初始化接线，具体职责见 app/ 目录下各模块
 */

import { state } from './app/state.js';
import { initIcons, updateClock } from './app/ui.js';
import { renderPreview, setViewMode, bindViewModeTabs } from './app/preview.js';
import { bindEditorEvents, DEFAULT_SAMPLE_ARTICLE } from './app/editor.js';
import { initDrafts } from './app/drafts.js';
import { renderThemeDropdown, selectTheme, bindThemeControls } from './app/theme.js';
import { initSettings } from './app/settings.js';
import { bindShortcuts } from './app/shortcuts.js';
import { bindPublishActions } from './app/publish.js';
import { initCoverStudio } from './app/cover-studio.js';
import { initChangelogModal } from './app/changelog.js';
import { applyVersion } from './version.js';

/**
 * 应用启动入口
 */
function init() {
  initIcons();
  applyVersion();
  renderThemeDropdown();
  initSettings();
  initCoverStudio();
  initChangelogModal();
  updateClock();
  setInterval(updateClock, 30000);

  // 载入草稿箱活动草稿 (旧版单草稿键自动迁移)；无任何草稿时回退官方示例
  const textarea = document.getElementById('markdown-input');
  const restoredDraft = initDrafts();
  textarea.value = restoredDraft !== null && restoredDraft !== undefined && restoredDraft !== ''
    ? restoredDraft
    : DEFAULT_SAMPLE_ARTICLE;

  selectTheme(state.currentThemeId);
  setViewMode(state.currentViewMode);
  bindEditorEvents();
  bindThemeControls();
  bindViewModeTabs();
  bindPublishActions();
  bindShortcuts();
  renderPreview();

  // 自动化视图与截图辅助钩子 (URL View Hook，仅开发构建可用)
  if (!import.meta.env.DEV) return;
  const urlParams = new URLSearchParams(window.location.search);
  const autoView = urlParams.get('view');
  if (autoView === 'cover_studio') {
    setTimeout(() => {
      const btn = document.getElementById('btn-open-cover');
      if (btn) btn.click();
    }, 100);
  } else if (autoView === 'crop_guide') {
    setTimeout(() => {
      const btn = document.getElementById('btn-open-cover');
      if (btn) btn.click();
      setTimeout(() => {
        const safeCheck = document.getElementById('toggle-safe-area');
        if (safeCheck && !safeCheck.checked) safeCheck.click();
      }, 80);
    }, 100);
  } else if (autoView === 'changelog') {
    setTimeout(() => {
      const btn = document.getElementById('btn-version-badge');
      if (btn) btn.click();
    }, 100);
  } else if (autoView === 'settings_inline') {
    setTimeout(() => {
      const btn = document.getElementById('btn-settings-trigger');
      if (btn) btn.click();
    }, 100);
  }
}

document.addEventListener('DOMContentLoaded', init);

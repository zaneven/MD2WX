/**
 * MD2WX Web Studio - 主题模块
 * 主题下拉菜单渲染、主题切换激活、手机外壳配色适配与触发按钮绑定
 */

import { BUILTIN_THEMES, getTheme, isDarkTheme } from '../core/themes.js';
import { state } from './state.js';
import { renderPreview } from './preview.js';

const phoneScroll = document.getElementById('phone-content-scroll');
const themeTriggerBtn = document.getElementById('theme-trigger-btn');
const themeDropdownMenu = document.getElementById('theme-dropdown-menu');
const currentThemeNameEl = document.getElementById('current-theme-name');
const currentThemeDotEl = document.getElementById('current-theme-dot');
const statusThemeTag = document.getElementById('status-theme-tag');
const previewStyleInfo = document.getElementById('preview-style-info');

/**
 * 构建主题下拉菜单列表
 */
export function renderThemeDropdown() {
  themeDropdownMenu.innerHTML = '';
  const themes = Object.values(BUILTIN_THEMES);

  for (const t of themes) {
    const item = document.createElement('div');
    item.className = `theme-option-item ${t.id === state.currentThemeId ? 'active' : ''}`;
    item.dataset.themeId = t.id;

    const accent = t.colors?.accent || '#2563eb';

    item.innerHTML = `
      <div class="theme-info">
        <div class="theme-name">
          <span style="width: 8px; height: 8px; border-radius: 50%; background: ${accent}; display: inline-block;"></span>
          <span>${t.name}</span>
        </div>
        <div class="theme-desc">${t.description || ''}</div>
      </div>
      <span style="font-size: 11px; color: #8a8a8a; font-family: monospace;">${t.id}</span>
    `;

    item.addEventListener('click', () => {
      selectTheme(t.id);
      themeDropdownMenu.classList.remove('show');
    });

    themeDropdownMenu.appendChild(item);
  }
}

/**
 * 切换并激活主题
 */
export function selectTheme(themeId) {
  if (!BUILTIN_THEMES[themeId]) return;
  state.currentThemeId = themeId;
  localStorage.setItem('md2wx_theme', themeId);

  const theme = getTheme(themeId);
  currentThemeNameEl.textContent = theme.name.split('(')[0].trim();
  currentThemeDotEl.style.backgroundColor = theme.accent;
  currentThemeDotEl.style.color = theme.accent;

  statusThemeTag.textContent = `主题: ${theme.name.split('(')[0].trim()}`;

  // 风格摘要显示
  const styles = theme.styles || {};
  const containerMap = {
    clean: '极简白',
    paper: '牛皮纸微框',
    dark: '曜石纯黑',
    card: '悬浮卡片',
    memo: '日系便签',
    brutalist: '新野兽派硬框',
  };
  const h1Map = {
    underline: '下划粗线',
    double_line: '古典双线',
    capsule: '胶囊药丸',
    terminal: '终端命令行',
    brutalist: '黑框硬投影',
  };
  const tableMap = {
    zebra: '现代斑马纹',
    three_line: '学术三线表',
    grid: '全网格卡片',
  };

  if (previewStyleInfo) {
    previewStyleInfo.textContent = `容器: ${containerMap[styles.container] || styles.container} · 标题: ${h1Map[styles.h1] || styles.h1} · 表格: ${tableMap[styles.table] || styles.table}`;
  }

  // 适配移动端外壳配色
  adaptPhoneTheme(theme);

  // 高亮下拉项
  document.querySelectorAll('.theme-option-item').forEach((el) => {
    el.classList.toggle('active', el.dataset.themeId === themeId);
  });

  // 立即触发重新渲染
  renderPreview();
}

/**
 * 适配手机外壳各栏位背景（如暗黑模式/羊皮纸模式）
 */
function adaptPhoneTheme(theme) {
  const pageBg = theme.page_bg || '#ffffff';
  const isDark = isDarkTheme(theme);
  const wechatNavBar = document.getElementById('wechat-nav-bar');
  const phoneStatusBar = document.getElementById('phone-status-bar');

  if (isDark) {
    phoneScroll.style.backgroundColor = pageBg;
    wechatNavBar.style.backgroundColor = pageBg;
    wechatNavBar.style.color = '#f8fafc';
    wechatNavBar.style.borderBottomColor = 'rgba(255, 255, 255, 0.08)';
    phoneStatusBar.style.color = '#ffffff';
  } else {
    phoneScroll.style.backgroundColor = pageBg;
    wechatNavBar.style.backgroundColor = pageBg;
    wechatNavBar.style.color = '#18181b';
    wechatNavBar.style.borderBottomColor = 'rgba(0, 0, 0, 0.06)';
    phoneStatusBar.style.color = '#18181b';
  }
}

/**
 * 绑定主题下拉菜单触发与外部点击自动关闭
 */
export function bindThemeControls() {
  themeTriggerBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    themeDropdownMenu.classList.toggle('show');
    document.getElementById('settings-dropdown-menu').classList.remove('show');
  });

  document.addEventListener('click', (e) => {
    if (!themeTriggerBtn.contains(e.target) && !themeDropdownMenu.contains(e.target)) {
      themeDropdownMenu.classList.remove('show');
    }
  });
}

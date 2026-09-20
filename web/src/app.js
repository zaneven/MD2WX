/**
 * MD2WX Web Studio - 主应用交互逻辑
 * 严格遵循规范：无任何 Emoji，全站统一高质感 SVG 矢量图标
 */

import { ICONS, setIcon } from './assets/icons.js';
import { BUILTIN_THEMES, DEFAULT_THEME_ID, getTheme, isDarkTheme } from './core/themes.js';
import { markdownToWechatHtml, parseFrontmatter } from './core/parser.js';
import { copyWechatHtml, downloadHtmlFile } from './core/clipboard.js';
import { COVER_DIMENSIONS, extractCoverMeta, renderCoverHtml, THEME_COVER_PRESETS } from './core/cover.js';
import { domToPngBlob, copyImageToClipboard, downloadImageBlob } from './core/canvas_exporter.js';

// 官方排版示范长文
const DEFAULT_SAMPLE_ARTICLE = `---
title: 在喧嚣的时代，重塑深度思考的秩序
author: 野生宝藏箱
digest: 真正的专注，不是在安静的环境里做简单的事，而是在充满干扰的世界中守住内心的秩序。
---

# 在喧嚣的时代，重塑深度思考的秩序

> **作者**：野生宝藏箱  
> **核心标签**：AI 自动化 · 架构复盘 · 极客手记  
> **一句话简介**：从热点抓取到全自动排版，构建属于你的数字花园。

真正的专注，不是在安静的环境里做简单的事，而是在充满干扰的世界中守住内心的秩序。我们每天接收海量的信息碎片，却越来越少体验到思维深潜的愉悦。阅读长文、推演逻辑、写下真实感悟，是抵抗思维退化的终极武器。

## 01. 核心架构与设计哲学

所谓卓越，就是将平凡的事反复雕琢，直到它泛出理性的光芒。

### 核心设计组件对比

| 模块 | 职责与定位 | 实现技术 |
| :--- | :--- | :--- |
| **Parser 引擎** | 解析 Markdown 并注入内联 CSS | 纯 Python 标准库 (零依赖) |
| **Theme System** | JSON 文件驱动的视觉风格渲染 | Strategy Pattern + Deep Merge |
| **Uploader** | 微信永久 CDN 换链搬运 | WeChat Media API |

\`\`\`python
def deploy_article(markdown_path: str, theme: str = "vintage-news"):
    # 纯内联样式转换
    html = markdown_to_wechat_html(markdown_path, theme_name=theme)
    return html
\`\`\`

- 坚持纯 Python 标准库零沉重依赖；
- 组件化视觉模式支持报刊、便签、终端等丰富变体；
- 一键注入剪贴板，支持直接 Cmd+V 粘贴公众号后台。

---

*▲ 图：全自动极简发布流水线架构全貌*`;

// App State
let currentThemeId = localStorage.getItem('md2wx_theme') || DEFAULT_THEME_ID;
let currentViewMode = localStorage.getItem('md2wx_view_mode') || 'mobile';
let currentFontSize = localStorage.getItem('md2wx_font_size') || '15.5px';
let currentLineHeight = localStorage.getItem('md2wx_line_height') || '1.8';
let enableFootnotes = localStorage.getItem('md2wx_enable_footnotes') !== 'false';
let enableSyncScroll = localStorage.getItem('md2wx_sync_scroll') !== 'false';
let insertCoverEnabled = localStorage.getItem('md2wx_insert_cover') !== 'false'; // 排版微调：正文顶部插入封面图 (默认勾选)
let isSyncingScroll = false;
let debounceTimer = null;
let currentHtmlOutput = '';
let currentCoverMeta = null; // 全局当前文章封面定制元数据，与正文顶部封面图联动

// DOM Elements
const textarea = document.getElementById('markdown-input');
const gutter = document.getElementById('editor-gutter');
const previewTarget = document.getElementById('preview-render-target');
const phoneScroll = document.getElementById('phone-content-scroll');
const deviceFrame = document.getElementById('device-frame');
const previewCanvas = document.getElementById('preview-canvas');
const wechatNavTitle = document.getElementById('wechat-nav-title');
const phoneClock = document.getElementById('phone-clock');
const themeTriggerBtn = document.getElementById('theme-trigger-btn');
const themeDropdownMenu = document.getElementById('theme-dropdown-menu');
const currentThemeNameEl = document.getElementById('current-theme-name');
const currentThemeDotEl = document.getElementById('current-theme-dot');
const statusThemeTag = document.getElementById('status-theme-tag');
const statusWordCount = document.getElementById('status-word-count');
const statusReadTime = document.getElementById('status-read-time');
const previewStyleInfo = document.getElementById('preview-style-info');
const toastContainer = document.getElementById('toast-container');

/**
 * 初始化所有 SVG 矢量图标
 */
function initIcons() {
  setIcon('#logo-icon', 'logo');
  setIcon('#theme-chevron-icon', 'chevronDown');
  setIcon('#icon-sample', 'fileText');
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
 * 实时更新行号
 */
function updateGutter() {
  const lineCount = textarea.value.split('\n').length;
  const numbers = [];
  for (let i = 1; i <= lineCount; i++) {
    numbers.push(i);
  }
  gutter.innerHTML = numbers.join('<br>');
}

/**
 * 双栏联动同步滚动 (带互斥锁防抖)
 */
function handleSyncScroll() {
  syncGutterScroll();
  if (!enableSyncScroll) return;
  if (isSyncingScroll) return;

  isSyncingScroll = true;
  const targetScrollEl = currentViewMode === 'desktop' ? previewCanvas : phoneScroll;
  if (targetScrollEl) {
    const editorScrollable = textarea.scrollHeight - textarea.clientHeight;
    if (editorScrollable > 0) {
      const scrollRatio = textarea.scrollTop / editorScrollable;
      const targetScrollable = targetScrollEl.scrollHeight - targetScrollEl.clientHeight;
      targetScrollEl.scrollTop = scrollRatio * targetScrollable;
    }
  }
  requestAnimationFrame(() => {
    isSyncingScroll = false;
  });
}

function syncGutterScroll() {
  gutter.scrollTop = textarea.scrollTop;
}

/**
 * 计算字数与阅读时间
 */
function updateWordCount(text) {
  // 匹配汉字字符数与英文单词数
  const chineseChars = (text.match(/[\u4e00-\u9fa5]/g) || []).length;
  const englishWords = (text.replace(/[\u4e00-\u9fa5]/g, ' ').match(/\b\w+\b/g) || []).length;
  const totalCount = chineseChars + englishWords;

  statusWordCount.textContent = `${totalCount} 字`;
  const minutes = Math.max(1, Math.ceil(totalCount / 400));
  statusReadTime.textContent = `约 ${minutes} 分钟阅读`;
}

/**
 * 显示浮动 Toast 通知
 */
function showToast(message, type = 'success') {
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
 * 构建主题下拉菜单列表
 */
function renderThemeDropdown() {
  themeDropdownMenu.innerHTML = '';
  const themes = Object.values(BUILTIN_THEMES);

  for (const t of themes) {
    const item = document.createElement('div');
    item.className = `theme-option-item ${t.id === currentThemeId ? 'active' : ''}`;
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
      <span style="font-size: 11px; color: #64748b; font-family: monospace;">${t.id}</span>
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
function selectTheme(themeId) {
  if (!BUILTIN_THEMES[themeId]) return;
  currentThemeId = themeId;
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
 * 切换视口显示模式 (仿真实机 / 宽屏桌面)
 */
function setViewMode(mode) {
  currentViewMode = mode;
  localStorage.setItem('md2wx_view_mode', mode);

  const tabMobile = document.getElementById('tab-mode-mobile');
  const tabDesktop = document.getElementById('tab-mode-desktop');

  if (mode === 'desktop') {
    previewCanvas.classList.add('desktop-view');
    tabDesktop.classList.add('active');
    tabMobile.classList.remove('active');
  } else {
    previewCanvas.classList.remove('desktop-view');
    tabMobile.classList.add('active');
    tabDesktop.classList.remove('active');
  }
}

/**
 * 核心渲染执行函数
 */
function renderPreview() {
  const rawText = textarea.value;
  updateGutter();
  updateWordCount(rawText);

  // 解析 Frontmatter
  const { meta, body } = parseFrontmatter(rawText);

  // 动态更新文章标题栏
  let articleTitle = meta.title;
  if (!articleTitle) {
    const firstH1 = body.match(/^#\s+(.+)$/m);
    if (firstH1) {
      articleTitle = firstH1[1].trim();
    }
  }
  wechatNavTitle.textContent = articleTitle || '文章详情';

  // 转换为微信专用的纯 Inline CSS HTML (注入排版微调参数、文末脚注设置与顶部封面卡片)
  currentHtmlOutput = markdownToWechatHtml(body, currentThemeId, null, {
    fontSize: currentFontSize,
    lineHeight: currentLineHeight,
    linkToFootnote: enableFootnotes,
    insertCover: insertCoverEnabled,
    coverMeta: currentCoverMeta,
  });
  previewTarget.innerHTML = currentHtmlOutput;

  saveDraft(rawText);
}

/**
 * 自动保存本地草稿。
 * 粘贴的 base64 图片体积巨大，直接写入会超出 localStorage 5MB 配额并抛
 * QuotaExceededError 中断渲染：超限时降级为剔除图片数据后保存，并提示一次。
 */
let draftQuotaWarned = false;
function saveDraft(rawText) {
  try {
    localStorage.setItem('md2wx_draft', rawText);
    draftQuotaWarned = false;
  } catch (e) {
    try {
      localStorage.setItem(
        'md2wx_draft',
        rawText.replace(/!\[[^\]]*\]\(data:image\/[^)]+\)/g, '![粘贴图片]()')
      );
      if (!draftQuotaWarned) {
        draftQuotaWarned = true;
        showToast('草稿超过本地存储上限，已省略内嵌图片数据 (编辑器内容不受影响)', 'error');
      }
    } catch (e2) {
      // 存储完全不可用时静默跳过，不阻断渲染
    }
  }
}

/**
 * 防抖渲染调度
 */
function scheduleRender() {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(renderPreview, 30);
}

/**
 * 快捷插入 Markdown 语法
 */
function insertFormatting(prefix, suffix = '', defaultText = '') {
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const text = textarea.value;
  const selectedText = text.slice(start, end) || defaultText;

  const replacement = prefix + selectedText + suffix;
  textarea.value = text.slice(0, start) + replacement + text.slice(end);

  const newCursor = start + prefix.length + selectedText.length;
  textarea.setSelectionRange(newCursor, newCursor);
  textarea.focus();

  scheduleRender();
}

/**
 * 执行一键复制公众号排版
 */
async function handleCopy() {
  if (!currentHtmlOutput) {
    showToast('当前暂无可复制的内容', 'error');
    return;
  }

  const btnHeader = document.getElementById('btn-copy-header');
  const btnFloating = document.getElementById('btn-copy-floating');

  const result = await copyWechatHtml(currentHtmlOutput, textarea.value);
  if (result.success) {
    showToast('已复制为微信公众号富文本！请在微信后台按 Cmd+V 直接粘贴');

    // 复制成功临时高亮按钮状态
    [btnHeader, btnFloating].forEach((b) => {
      if (b) {
        b.classList.add('btn-success');
        const origHtml = b.innerHTML;
        b.innerHTML = `${ICONS.check}<span>已复制</span>`;
        setTimeout(() => {
          b.classList.remove('btn-success');
          b.innerHTML = origHtml;
        }, 1800);
      }
    });
  } else {
    showToast('复制失败: ' + (result.error || '权限受限'), 'error');
  }
}

/**
 * 更新手机顶部实时时钟
 */
function updateClock() {
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  phoneClock.textContent = `${hours}:${minutes}`;
}

/**
 * 绑定所有事件监听
 */
function bindEvents() {
  // 编辑器实时输入与双栏滚动联动
  textarea.addEventListener('input', scheduleRender);
  textarea.addEventListener('scroll', handleSyncScroll);

  // 主题下拉菜单触发与外部点击自动关闭
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

  // 视口模式切换
  document.getElementById('tab-mode-mobile').addEventListener('click', () => setViewMode('mobile'));
  document.getElementById('tab-mode-desktop').addEventListener('click', () => setViewMode('desktop'));

  // 顶部操作按钮
  document.getElementById('btn-copy-header').addEventListener('click', handleCopy);
  document.getElementById('btn-copy-floating').addEventListener('click', handleCopy);

  document.getElementById('btn-export-html').addEventListener('click', () => {
    downloadHtmlFile(currentHtmlOutput, 'md2wx-article.html');
    showToast('已导出自包含微信排版 HTML 文件');
  });

  document.getElementById('btn-load-sample').addEventListener('click', () => {
    textarea.value = DEFAULT_SAMPLE_ARTICLE;
    scheduleRender();
    showToast('已载入排版示范长文');
  });

  // 工具栏格式化快捷按钮
  document.getElementById('tool-bold').addEventListener('click', () => insertFormatting('**', '**', '粗体文字'));
  document.getElementById('tool-italic').addEventListener('click', () => insertFormatting('*', '*', '斜体文字'));
  document.getElementById('tool-h1').addEventListener('click', () => insertFormatting('# ', '\n', '一级主标题'));
  document.getElementById('tool-h2').addEventListener('click', () => insertFormatting('## ', '\n', '二级分区标题'));
  document.getElementById('tool-quote').addEventListener('click', () => insertFormatting('> ', '\n', '核心观点与导读引言'));
  document.getElementById('tool-code').addEventListener('click', () => insertFormatting('```python\n', '\n```', '# 编写代码逻辑\nprint("Hello MD2WX")'));
  document.getElementById('tool-table').addEventListener('click', () => {
    const sampleTable = `| 模块 | 职责与定位 | 实现技术 |\n| :--- | :--- | :--- |\n| 核心引擎 | Markdown 解析 | 纯 Python / JS |\n| 主题系统 | 视觉规范注入 | JSON 驱动 |\n`;
    insertFormatting('', '', sampleTable);
  });
  document.getElementById('tool-list').addEventListener('click', () => insertFormatting('- ', '\n', '核心列表项'));
  document.getElementById('tool-hr').addEventListener('click', () => insertFormatting('\n---\n', '', ''));
  document.getElementById('tool-link').addEventListener('click', () => insertFormatting('[', '](https://example.com)', '链接说明'));
  document.getElementById('tool-image').addEventListener('click', () => insertFormatting('![图片说明](', ')', 'https://example.com/image.png'));

  document.getElementById('tool-clear').addEventListener('click', () => {
    if (confirm('确定要清空当前的编辑器内容吗？')) {
      textarea.value = '';
      scheduleRender();
      showToast('编辑器已清空');
    }
  });

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

  // 支持 Tab 缩进输入
  textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      textarea.value = textarea.value.substring(0, start) + '  ' + textarea.value.substring(end);
      textarea.selectionStart = textarea.selectionEnd = start + 2;
      scheduleRender();
    }
  });

  // 本地图片粘贴支持 (支持剪贴板中的截图直接转 Base64 嵌入)
  textarea.addEventListener('paste', (e) => {
    const items = (e.clipboardData || window.clipboardData)?.items;
    if (!items) return;
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.indexOf('image') !== -1) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) {
          const reader = new FileReader();
          reader.onload = (event) => {
            const base64Url = event.target.result;
            insertFormatting('![粘贴图片](', ')', base64Url);
            showToast('已将剪贴板图片转换为 Markdown 嵌入');
          };
          reader.readAsDataURL(file);
        }
        return;
      }
    }
  });

  // 本地图片拖拽上传与防盗链感知
  const textareaWrapper = document.querySelector('.editor-textarea-wrapper');
  if (textareaWrapper) {
    textareaWrapper.addEventListener('dragover', (e) => {
      e.preventDefault();
      textareaWrapper.classList.add('drag-over');
    });
    textareaWrapper.addEventListener('dragleave', () => {
      textareaWrapper.classList.remove('drag-over');
    });
    textareaWrapper.addEventListener('drop', (e) => {
      e.preventDefault();
      textareaWrapper.classList.remove('drag-over');
      const files = e.dataTransfer?.files;
      if (files && files.length > 0) {
        const file = files[0];
        if (file.type.startsWith('image/')) {
          const reader = new FileReader();
          reader.onload = (event) => {
            const base64Url = event.target.result;
            insertFormatting(`![${file.name}](`, ')', base64Url);
            showToast(`已插入拖拽图片: ${file.name}`);
          };
          reader.readAsDataURL(file);
        }
      }
    });
  }
}

/**
 * 初始化排版微调设置面板
 */
function initSettings() {
  const settingsBtn = document.getElementById('btn-settings-trigger');
  const settingsDropdown = document.getElementById('settings-dropdown-menu');
  const toggleInsertCover = document.getElementById('toggle-insert-cover');
  const toggleFootnotes = document.getElementById('toggle-footnotes');
  const toggleSyncScroll = document.getElementById('toggle-sync-scroll');

  if (!settingsBtn || !settingsDropdown) return;

  // 初始化 UI 勾选状态
  if (toggleInsertCover) toggleInsertCover.checked = insertCoverEnabled;
  if (toggleFootnotes) toggleFootnotes.checked = enableFootnotes;
  if (toggleSyncScroll) toggleSyncScroll.checked = enableSyncScroll;

  // 插入封面图开关 (在可复制的微信正文顶部显示封面图)
  if (toggleInsertCover) {
    toggleInsertCover.addEventListener('change', (e) => {
      insertCoverEnabled = e.target.checked;
      localStorage.setItem('md2wx_insert_cover', String(insertCoverEnabled));
      renderPreview();
      showToast(insertCoverEnabled ? '已开启：在微信正文顶部插入封面图' : '已关闭正文顶部封面图');
    });
  }

  // 正文字号切换
  document.querySelectorAll('#control-font-size .segment-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.val === currentFontSize);
    btn.addEventListener('click', () => {
      document.querySelectorAll('#control-font-size .segment-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      currentFontSize = btn.dataset.val;
      localStorage.setItem('md2wx_font_size', currentFontSize);
      renderPreview();
    });
  });

  // 行距切换
  document.querySelectorAll('#control-line-height .segment-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.val === currentLineHeight);
    btn.addEventListener('click', () => {
      document.querySelectorAll('#control-line-height .segment-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      currentLineHeight = btn.dataset.val;
      localStorage.setItem('md2wx_line_height', currentLineHeight);
      renderPreview();
    });
  });

  // 外链转文末脚注开关
  if (toggleFootnotes) {
    toggleFootnotes.addEventListener('change', (e) => {
      enableFootnotes = e.target.checked;
      localStorage.setItem('md2wx_enable_footnotes', String(enableFootnotes));
      renderPreview();
      showToast(enableFootnotes ? '已开启外链自动转文末脚注' : '已关闭外链转脚注');
    });
  }

  // 双栏同步滚动开关
  if (toggleSyncScroll) {
    toggleSyncScroll.addEventListener('change', (e) => {
      enableSyncScroll = e.target.checked;
      localStorage.setItem('md2wx_sync_scroll', String(enableSyncScroll));
      showToast(enableSyncScroll ? '已开启双栏联动同步滚动' : '已关闭双栏同步滚动');
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

/**
 * 封面工作台交互逻辑 (Cover Studio Engine)
 */
function initCoverStudio() {
  const overlay = document.getElementById('cover-modal-overlay');
  const btnOpen = document.getElementById('btn-open-cover');
  const btnClose = document.getElementById('btn-close-cover-modal');
  const tabBanner = document.getElementById('tab-ratio-banner');
  const tabSquare = document.getElementById('tab-ratio-square');
  const toggleSafeArea = document.getElementById('toggle-safe-area');
  const selectThemeEl = document.getElementById('select-cover-theme');
  const btnSync = document.getElementById('btn-sync-from-article');
  const btnCopy = document.getElementById('btn-copy-cover-image');
  const btnDownload = document.getElementById('btn-download-cover-image');

  const inputTitle = document.getElementById('input-cover-title');
  const inputDigest = document.getElementById('input-cover-digest');
  const inputTag = document.getElementById('input-cover-tag');
  const inputBadge = document.getElementById('input-cover-badge');
  const inputVol = document.getElementById('input-cover-vol');
  const inputAuthor = document.getElementById('input-cover-author');

  const viewport = document.getElementById('cover-canvas-viewport');
  const scaler = document.getElementById('cover-scaler-container');
  const renderTarget = document.getElementById('cover-render-target');
  const dimHint = document.getElementById('cover-dimensions-hint');

  if (!overlay || !btnOpen) return;

  // 封面内部工作台状态
  let coverThemeId = currentThemeId;
  let coverRatio = 'banner'; // 'banner' (2.35:1) | 'square' (1:1)
  let showSafeGuide = false; // 微信 1:1 裁切与安全线默认关闭，避免遮挡预览
  let coverMeta = {};

  const shareTitleEl = document.getElementById('preview-share-title');
  const shareDigestEl = document.getElementById('preview-share-digest');
  const shareThumbEl = document.getElementById('preview-share-thumb-box');

  // 同步表单数据
  function syncFormInputs() {
    inputTitle.value = coverMeta.title || '';
    inputDigest.value = coverMeta.digest || '';
    inputTag.value = coverMeta.tag || '';
    inputBadge.value = coverMeta.badge || '';
    inputVol.value = coverMeta.vol || '';
    inputAuthor.value = coverMeta.author || '';
  }

  // 从编辑器正文重新智能提取
  function refreshMetaFromArticle() {
    coverMeta = extractCoverMeta(textarea.value, coverThemeId);
    syncFormInputs();
  }

  // 视口自适应等比缩放计算：显式锁定物理逻辑尺寸，坚决消除 flex 挤压裁切
  function updateScaler() {
    if (!viewport || !scaler) return;
    const rect = viewport.getBoundingClientRect();
    const padding = 36;
    const availW = Math.max(100, rect.width - padding * 2);
    const availH = Math.max(100, rect.height - padding * 2);
    const dim = COVER_DIMENSIONS[coverRatio] || COVER_DIMENSIONS.banner;

    // 关键：强制设置 scaler 的固定逻辑物理尺寸与防收缩
    scaler.style.width = `${dim.width}px`;
    scaler.style.height = `${dim.height}px`;
    scaler.style.flexShrink = '0';

    const scaleW = availW / dim.width;
    const scaleH = availH / dim.height;
    // 限制最大缩放倍数为 1，确保不会因为超大屏而失真，小屏等比顺滑缩小
    const finalScale = Math.min(scaleW, scaleH, 1);

    scaler.style.transform = `scale(${finalScale.toFixed(4)})`;
  }

  // 渲染封面画布并联动微信分享卡片
  function renderCover() {
    if (!renderTarget) return;
    currentCoverMeta = { ...coverMeta };
    renderTarget.innerHTML = renderCoverHtml(coverThemeId, coverRatio, coverMeta, showSafeGuide);

    const dim = COVER_DIMENSIONS[coverRatio] || COVER_DIMENSIONS.banner;
    const exportW = dim.width * 2;
    const exportH = dim.height * 2;
    if (dimHint) {
      dimHint.textContent = `导出分辨率: ${exportW} × ${exportH} 像素 (Retina 2x 高清)`;
    }

    // 联动微信转发聊天卡片预览
    if (shareTitleEl) shareTitleEl.textContent = coverMeta.title || '文章标题';
    if (shareDigestEl) shareDigestEl.textContent = coverMeta.digest || '真正的专注，是在充满干扰的世界中守住内心的秩序。';
    if (shareThumbEl) {
      const preset = THEME_COVER_PRESETS[coverThemeId] || THEME_COVER_PRESETS['tech-blue'];
      shareThumbEl.innerHTML = `
        <div style="width:100%;height:100%;background:#090d16;display:flex;flex-direction:column;align-items:center;justify-content:center;border-radius:4px;gap:2px;">
          <span style="font-size:9px;font-weight:900;color:#38bdf8;line-height:1;">${(preset.badgeText || 'COVER').slice(0, 6)}</span>
          <span style="font-size:8px;font-weight:700;color:#10b981;line-height:1;">1:1截取</span>
        </div>
      `;
    }

    updateScaler();
  }

  // 打开模态框
  function openCoverModal() {
    coverThemeId = currentThemeId;
    if (selectThemeEl) {
      selectThemeEl.value = coverThemeId;
    }
    refreshMetaFromArticle();
    overlay.classList.add('active');
    
    // 即时渲染并在弹窗展开动画期间多阶段精细校准缩放
    renderCover();
    requestAnimationFrame(updateScaler);
    setTimeout(updateScaler, 80);
    setTimeout(updateScaler, 260);
  }

  // 关闭模态框
  function closeCoverModal() {
    overlay.classList.remove('active');
  }

  // 事件监听绑定
  btnOpen.addEventListener('click', openCoverModal);
  btnClose.addEventListener('click', closeCoverModal);

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      closeCoverModal();
    }
  });

  // 比例切换
  tabBanner.addEventListener('click', () => {
    tabBanner.classList.add('active');
    tabSquare.classList.remove('active');
    coverRatio = 'banner';
    renderCover();
  });

  tabSquare.addEventListener('click', () => {
    tabSquare.classList.add('active');
    tabBanner.classList.remove('active');
    coverRatio = 'square';
    renderCover();
  });

  // 安全区标线切换
  toggleSafeArea.addEventListener('change', (e) => {
    showSafeGuide = e.target.checked;
    renderCover();
  });

  // 主题切换
  selectThemeEl.addEventListener('change', (e) => {
    coverThemeId = e.target.value;
    const preset = THEME_COVER_PRESETS[coverThemeId];
    if (preset) {
      coverMeta.badge = preset.badgeText;
      coverMeta.vol = preset.volText;
      syncFormInputs();
    }
    renderCover();
  });

  // 重新同步正文
  btnSync.addEventListener('click', () => {
    refreshMetaFromArticle();
    renderCover();
    showToast('已从当前文章提取最新标题与摘要', 'info');
  });

  // 表单输入监听 (输入即时联动封面与正文顶部嵌入卡片)
  inputTitle.addEventListener('input', (e) => {
    coverMeta.title = e.target.value;
    renderCover();
    scheduleRender();
  });
  inputDigest.addEventListener('input', (e) => {
    coverMeta.digest = e.target.value;
    renderCover();
    scheduleRender();
  });
  inputTag.addEventListener('input', (e) => {
    coverMeta.tag = e.target.value;
    renderCover();
    scheduleRender();
  });
  inputBadge.addEventListener('input', (e) => {
    coverMeta.badge = e.target.value;
    renderCover();
    scheduleRender();
  });
  inputVol.addEventListener('input', (e) => {
    coverMeta.vol = e.target.value;
    renderCover();
    scheduleRender();
  });
  inputAuthor.addEventListener('input', (e) => {
    coverMeta.author = e.target.value;
    renderCover();
    scheduleRender();
  });

  // 复制封面图片到剪贴板 (基于 Promise 瞬时手势保持与双引擎渲染)
  btnCopy.addEventListener('click', async () => {
    // 关键：从输入框强制提取最新值，确保绝对不会复制旧的/未保存的文字
    coverMeta.title = inputTitle.value.trim() || coverMeta.title || '';
    coverMeta.digest = inputDigest.value.trim() || coverMeta.digest || '';
    coverMeta.tag = inputTag.value.trim() || coverMeta.tag || '';
    coverMeta.badge = inputBadge.value.trim() || coverMeta.badge || '';
    coverMeta.vol = inputVol.value.trim() || coverMeta.vol || '';
    coverMeta.author = inputAuthor.value.trim() || coverMeta.author || '';

    // 重新渲染封面画布并同步文章顶部内联封面
    renderCover();
    renderPreview();

    const coverNode = renderTarget.firstElementChild;
    if (!coverNode) return;

    const originalHtml = btnCopy.innerHTML;
    try {
      btnCopy.disabled = true;
      btnCopy.innerHTML = '<span>正在处理图片...</span>';

      const dim = COVER_DIMENSIONS[coverRatio] || COVER_DIMENSIONS.banner;
      const blobPromise = domToPngBlob(coverNode, {
        width: dim.width,
        height: dim.height,
        scale: 2,
        themeId: coverThemeId,
        ratio: coverRatio,
        meta: { ...coverMeta }
      });

      await copyImageToClipboard(blobPromise);

      // 按钮即时成功反馈
      btnCopy.innerHTML = `<span style="color:#10b981;display:flex;align-items:center;gap:6px;">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
        <span>已复制到剪贴板！</span>
      </span>`;
      showToast('封面图片已成功复制到剪贴板！微信公众号后台可直接粘贴', 'success');

      setTimeout(() => {
        btnCopy.disabled = false;
        btnCopy.innerHTML = originalHtml;
      }, 2200);
    } catch (err) {
      console.error('复制封面失败:', err);
      btnCopy.disabled = false;
      btnCopy.innerHTML = originalHtml;
      showToast(`复制失败: ${err.message || '请尝试点击“下载高清 PNG”保存'}`, 'error');
    }
  });

  // 下载高清 PNG 文件
  btnDownload.addEventListener('click', async () => {
    // 强制提取最新值
    coverMeta.title = inputTitle.value.trim() || coverMeta.title || '';
    coverMeta.digest = inputDigest.value.trim() || coverMeta.digest || '';
    coverMeta.tag = inputTag.value.trim() || coverMeta.tag || '';
    coverMeta.badge = inputBadge.value.trim() || coverMeta.badge || '';
    coverMeta.vol = inputVol.value.trim() || coverMeta.vol || '';
    coverMeta.author = inputAuthor.value.trim() || coverMeta.author || '';

    renderCover();
    renderPreview();

    const coverNode = renderTarget.firstElementChild;
    if (!coverNode) return;

    const originalHtml = btnDownload.innerHTML;
    try {
      btnDownload.disabled = true;
      btnDownload.innerHTML = '<span>生成高清文件...</span>';

      const dim = COVER_DIMENSIONS[coverRatio] || COVER_DIMENSIONS.banner;
      const blob = await domToPngBlob(coverNode, {
        width: dim.width,
        height: dim.height,
        scale: 2,
        themeId: coverThemeId,
        ratio: coverRatio,
        meta: { ...coverMeta }
      });

      const filename = `md2wx-cover-${coverThemeId}-${coverRatio}.png`;
      downloadImageBlob(blob, filename);
      showToast(`已开始下载高清封面: ${filename}`, 'success');
    } catch (err) {
      console.error('下载封面失败:', err);
      showToast(`下载失败: ${err.message}`, 'error');
    } finally {
      btnDownload.disabled = false;
      btnDownload.innerHTML = originalHtml;
    }
  });

  // 视口尺寸变化监听（结合 ResizeObserver 与 window.resize）
  if (window.ResizeObserver && viewport) {
    const ro = new ResizeObserver(() => {
      if (overlay.classList.contains('active')) {
        updateScaler();
      }
    });
    ro.observe(viewport);
  }

  window.addEventListener('resize', () => {
    if (overlay.classList.contains('active')) {
      updateScaler();
    }
  });
}

/**
 * 版本速递对话框逻辑 (Changelog Modal)
 */
function initChangelogModal() {
  const badgeBtn = document.getElementById('btn-version-badge');
  const overlay = document.getElementById('changelog-modal-overlay');
  const closeBtn = document.getElementById('btn-close-changelog-modal');

  if (!badgeBtn || !overlay) return;

  function openModal() {
    overlay.classList.add('active');
  }

  function closeModal() {
    overlay.classList.remove('active');
  }

  badgeBtn.addEventListener('click', openModal);
  if (closeBtn) closeBtn.addEventListener('click', closeModal);

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeModal();
  });

  // 全局 Esc 快捷键关闭弹窗
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const coverOverlay = document.getElementById('cover-modal-overlay');
      if (coverOverlay && coverOverlay.classList.contains('active')) {
        coverOverlay.classList.remove('active');
      }
      if (overlay.classList.contains('active')) {
        closeModal();
      }
    }
  });
}

/**
 * 应用启动入口
 */
function init() {
  initIcons();
  renderThemeDropdown();
  initSettings();
  initCoverStudio();
  initChangelogModal();
  updateClock();
  setInterval(updateClock, 30000);

  // 载入草稿或默认示例
  const savedDraft = localStorage.getItem('md2wx_draft');
  textarea.value = savedDraft || DEFAULT_SAMPLE_ARTICLE;

  selectTheme(currentThemeId);
  setViewMode(currentViewMode);
  bindEvents();
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

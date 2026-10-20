/**
 * MD2WX Web Studio - 编辑器模块
 * 官方示例文章、Markdown 快捷插入、图床上传插入与编辑区/工具栏事件绑定
 */

import {
  isImageHostConfigured,
  uploadImageFile,
  validateImageFile,
  IMAGE_HOST_UNCONFIGURED_HINT,
} from '../core/imagehost.js';
import { showToast } from './ui.js';
import { handleSyncScroll } from './scroll-sync.js';
import { scheduleRender } from './preview.js';
import {
  getDrafts,
  loadDraft,
  createDraft,
  deleteDraft,
  getActiveDraftId,
  formatRelativeTime,
} from './drafts.js';
import { ICONS } from '../assets/icons.js';
import sampleArticle from '../../../sample_article.md?raw';

const textarea = document.getElementById('markdown-input');

// 官方排版示范：与 CLI 共用仓库根目录的 sample_article.md（单一数据源）
export const DEFAULT_SAMPLE_ARTICLE = sampleArticle.trim();

/**
 * 快捷插入 Markdown 语法
 */
export function insertFormatting(prefix, suffix = '', defaultText = '') {
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
 * 常驻草稿箱侧栏 (编辑器左侧)：草稿列表渲染、切换载入、新建与删除
 * 数据层见 drafts.js，此处仅负责 DOM 交互
 */
function bindDraftsSidebar(textarea) {
  const listEl = document.getElementById('drafts-list');
  const countEl = document.getElementById('drafts-count');
  const newBtn = document.getElementById('btn-draft-new');
  if (!listEl) return;

  // 列表指纹 (含活动草稿)：仅当标题/时间/活动态变化时才重建 DOM，
  // 避免编辑输入触发的高频自动保存反复重绘侧栏
  let lastSignature = null;

  function renderDraftList() {
    const drafts = getDrafts();
    const activeId = getActiveDraftId();
    const signature = [
      activeId,
      ...drafts.map((d) => `${d.id}|${d.title}|${formatRelativeTime(d.updatedAt)}`),
    ].join('§');
    if (signature === lastSignature) return;
    lastSignature = signature;

    if (countEl) countEl.textContent = `${drafts.length} 篇`;
    listEl.innerHTML = '';

    if (!drafts.length) {
      const empty = document.createElement('div');
      empty.className = 'drafts-empty';
      empty.textContent = '暂无草稿';
      listEl.appendChild(empty);
      return;
    }

    drafts.forEach((d) => {
      const item = document.createElement('div');
      item.className = 'draft-item' + (d.id === activeId ? ' active' : '');

      const main = document.createElement('div');
      main.className = 'draft-item-main';
      const title = document.createElement('div');
      title.className = 'draft-item-title';
      title.textContent = d.title || '未命名草稿';
      const time = document.createElement('div');
      time.className = 'draft-item-time';
      time.textContent = formatRelativeTime(d.updatedAt);
      main.appendChild(title);
      main.appendChild(time);

      const del = document.createElement('button');
      del.type = 'button';
      del.className = 'draft-item-delete';
      del.title = '删除此草稿';
      del.innerHTML = ICONS.trash;

      item.appendChild(main);
      item.appendChild(del);
      listEl.appendChild(item);

      main.addEventListener('click', () => {
        const content = loadDraft(d.id);
        if (content === null) return;
        textarea.value = content;
        scheduleRender();
        renderDraftList();
        showToast(`已载入草稿「${title.textContent}」`);
      });
      del.addEventListener('click', (e) => {
        e.stopPropagation();
        if (!confirm(`确定删除草稿「${d.title || '未命名草稿'}」吗？`)) return;
        const res = deleteDraft(d.id);
        if (res) {
          textarea.value = res.content;
          scheduleRender();
        }
        renderDraftList();
        showToast('草稿已删除');
      });
    });
  }

  newBtn?.addEventListener('click', () => {
    createDraft();
    textarea.value = '';
    scheduleRender();
    renderDraftList();
    showToast('已新建空白草稿');
  });

  // 自动保存 (每次输入) 会改变草稿标题与更新时间，节流刷新侧栏
  let refreshTimer = null;
  window.addEventListener('md2wx:drafts-changed', () => {
    if (refreshTimer) return;
    refreshTimer = setTimeout(() => {
      refreshTimer = null;
      renderDraftList();
    }, 500);
  });

  renderDraftList();
}

/**
 * 绑定编辑区与工具栏事件
 */
export function bindEditorEvents() {
  // 编辑器实时输入与双栏滚动联动
  textarea.addEventListener('input', scheduleRender);
  textarea.addEventListener('scroll', handleSyncScroll);

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
  document.getElementById('tool-h3').addEventListener('click', () => insertFormatting('### ', '\n', '三级小节标题'));
  document.getElementById('tool-strike').addEventListener('click', () => insertFormatting('~~', '~~', '删除线文字'));
  document.getElementById('tool-highlight').addEventListener('click', () => insertFormatting('==', '==', '重点高亮'));
  document.getElementById('tool-inline-code').addEventListener('click', () => insertFormatting('`', '`', '行内代码'));
  document.getElementById('tool-quote').addEventListener('click', () => insertFormatting('> ', '\n', '核心观点与导读引言'));
  document.getElementById('tool-code').addEventListener('click', () => insertFormatting('```python\n', '\n```', '# 编写代码逻辑\nprint("Hello MD2WX")'));
  document.getElementById('tool-table').addEventListener('click', () => {
    const sampleTable = `| 模块 | 职责与定位 | 实现技术 |\n| :--- | :--- | :--- |\n| 核心引擎 | Markdown 解析 | 纯 Python / JS |\n| 主题系统 | 视觉规范注入 | JSON 驱动 |\n`;
    insertFormatting('', '', sampleTable);
  });
  document.getElementById('tool-list').addEventListener('click', () => insertFormatting('- ', '\n', '核心列表项'));
  document.getElementById('tool-list-ordered').addEventListener('click', () => insertFormatting('1. ', '\n', '有序列表项'));
  document.getElementById('tool-list-task').addEventListener('click', () => insertFormatting('- [ ] ', '\n', '待办事项'));
  document.getElementById('tool-math').addEventListener('click', () => insertFormatting('$$\n', '\n$$', 'E = mc^2'));
  document.getElementById('tool-mermaid').addEventListener('click', () => insertFormatting('```mermaid\n', '\n```', 'graph LR\n  A[Markdown] --> B[微信公众号]'));
  document.getElementById('tool-hr').addEventListener('click', () => insertFormatting('\n---\n', '', ''));
  document.getElementById('tool-link').addEventListener('click', () => insertFormatting('[', '](https://example.com)', '链接说明'));

  // 图片插入菜单 (图床上传 / 粘贴链接)，参考 WePost 插入图片浮层交互
  const imageMenu = document.getElementById('image-menu');
  const imageUrlInput = document.getElementById('image-url-input');
  const imageHostHint = document.getElementById('image-host-hint');
  const imageUploadTrigger = document.getElementById('image-upload-trigger');
  const imageFileInput = document.getElementById('image-file-input');
  const imageHostConfigured = isImageHostConfigured();

  /**
   * 上传本地图片文件到图床并插入正文；未配置时提示不支持
   */
  async function handleImageUpload(file, altLabel = '图片') {
    if (!file) return;
    const precheck = validateImageFile(file);
    if (precheck) {
      showToast(precheck, 'error');
      return;
    }
    if (!imageHostConfigured) {
      showToast(IMAGE_HOST_UNCONFIGURED_HINT, 'error');
      return;
    }
    showToast('正在上传图片到图床…');
    try {
      const url = await uploadImageFile(file);
      insertFormatting(`![${altLabel}](`, ')', url);
      showToast('图片已上传并插入正文');
    } catch (e) {
      showToast(`图床上传失败: ${e.message || '未知错误'}`, 'error');
    }
  }

  if (imageHostHint) {
    imageHostHint.textContent = imageHostConfigured ? '' : '当前未配置图床，本地上传不可用';
  }
  if (imageUploadTrigger && !imageHostConfigured) {
    imageUploadTrigger.classList.add('is-disabled');
    imageUploadTrigger.title = IMAGE_HOST_UNCONFIGURED_HINT;
  }

  document.getElementById('tool-image').addEventListener('click', (e) => {
    e.stopPropagation();
    imageMenu?.classList.toggle('show');
  });
  document.addEventListener('click', (e) => {
    if (imageMenu && !e.target.closest('.image-tool-wrap')) {
      imageMenu.classList.remove('show');
    }
  });
  if (imageUrlInput) {
    imageUrlInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        document.getElementById('image-url-insert')?.click();
      }
    });
  }
  document.getElementById('image-url-insert')?.addEventListener('click', () => {
    const url = (imageUrlInput?.value || '').trim();
    if (!/^https?:\/\//i.test(url)) {
      showToast('请输入 http/https 开头的图片链接', 'error');
      return;
    }
    insertFormatting('![图片](', ')', url);
    if (imageUrlInput) imageUrlInput.value = '';
    imageMenu?.classList.remove('show');
  });
  imageUploadTrigger?.addEventListener('click', () => {
    if (!imageHostConfigured) {
      showToast(IMAGE_HOST_UNCONFIGURED_HINT, 'error');
      return;
    }
    imageFileInput?.click();
  });
  imageFileInput?.addEventListener('change', async () => {
    const file = imageFileInput.files && imageFileInput.files[0];
    imageFileInput.value = '';
    await handleImageUpload(file, file ? file.name.replace(/\.[^.]+$/, '') : '图片');
    imageMenu?.classList.remove('show');
  });

  document.getElementById('tool-clear').addEventListener('click', () => {
    if (confirm('确定要清空当前的编辑器内容吗？')) {
      textarea.value = '';
      scheduleRender();
      showToast('编辑器已清空');
    }
  });

  // 常驻草稿箱侧栏 (列表/切换/新建/删除)
  bindDraftsSidebar(textarea);

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

  // 本地图片粘贴支持 (剪贴板截图上传图床，未配置时提示不支持)
  textarea.addEventListener('paste', (e) => {
    const items = (e.clipboardData || window.clipboardData)?.items;
    if (!items) return;
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.indexOf('image') !== -1) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) handleImageUpload(file, '粘贴图片');
        return;
      }
    }
  });

  // 本地图片拖拽上传 (上传图床，未配置时提示不支持)
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
          handleImageUpload(file, file.name.replace(/\.[^.]+$/, '') || '图片');
        }
      }
    });
  }
}

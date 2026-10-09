/**
 * MD2WX Web Studio - 预览渲染管线
 * 行号槽、字数统计、核心渲染调度、草稿持久化与视口模式切换
 */

import { markdownToWechatHtml, parseFrontmatter } from '../core/parser.js';
import { prepareRichBlocks, hydrateRichBlocks } from '../core/richrender.js';
import { extractCoverMeta } from '../core/cover.js';
import { state } from './state.js';
import { showToast } from './ui.js';
import { updateExternalImageGuard } from './imageguard.js';

const textarea = document.getElementById('markdown-input');
const gutter = document.getElementById('editor-gutter');
const previewTarget = document.getElementById('preview-render-target');
const wechatNavTitle = document.getElementById('wechat-nav-title');
const previewCanvas = document.getElementById('preview-canvas');
const statusWordCount = document.getElementById('status-word-count');
const statusReadTime = document.getElementById('status-read-time');

/**
 * 实时更新行号
 */
export function updateGutter() {
  const lineCount = textarea.value.split('\n').length;
  const numbers = [];
  for (let i = 1; i <= lineCount; i++) {
    numbers.push(i);
  }
  gutter.innerHTML = numbers.join('<br>');
}

/**
 * 计算字数与阅读时间
 */
function updateWordCount(text) {
  // 匹配汉字字符数与英文单词数
  const chineseChars = (text.match(/[一-龥]/g) || []).length;
  const englishWords = (text.replace(/[一-龥]/g, ' ').match(/\b\w+\b/g) || []).length;
  const totalCount = chineseChars + englishWords;

  statusWordCount.textContent = `${totalCount} 字`;
  const minutes = Math.max(1, Math.ceil(totalCount / 400));
  statusReadTime.textContent = `约 ${minutes} 分钟阅读`;
}

/**
 * 自动保存本地草稿。
 * 粘贴的 base64 图片体积巨大，直接写入会超出 localStorage 5MB 配额并抛
 * QuotaExceededError 中断渲染：超限时降级为剔除图片数据后保存，并提示一次。
 */
let draftQuotaWarned = false;
export function saveDraft(rawText) {
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
 * 核心渲染执行函数
 */
export function renderPreview() {
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

  // 富文本块预处理：Mermaid/公式抽取为占位 token (与 CLI 端 richrender 同规则)
  const { md: richMd, blocks: richBlocks } = prepareRichBlocks(body);
  state.currentRichBlocks = richBlocks;

  // 转换为微信专用的纯 Inline CSS HTML (注入排版微调参数、文末脚注设置与顶部封面卡片)
  state.currentHtmlOutput = markdownToWechatHtml(richMd, state.currentThemeId, null, {
    fontSize: state.currentFontSize,
    lineHeight: state.currentLineHeight,
    linkToFootnote: state.enableFootnotes,
    insertCover: state.insertCoverEnabled,
    // 封面元数据必须从原始正文提取，避免富文本占位 token 泄漏进封面摘要
    coverMeta: state.currentCoverMeta || extractCoverMeta(body, state.currentThemeId),
  });
  previewTarget.innerHTML = state.currentHtmlOutput;

  // 富文本块异步水合 (CDN 加载 mermaid/KaTeX 就地渲染，不阻塞主渲染管线)
  hydrateRichBlocks(previewTarget, richBlocks).catch((err) => {
    console.warn('富文本块水合失败:', err);
  });

  // 外链图片防护横幅 (微信编辑器封禁外站图床)
  updateExternalImageGuard(document.getElementById('phone-content-scroll'), body);

  saveDraft(rawText);
}

/**
 * 防抖渲染调度
 */
export function scheduleRender() {
  if (state.debounceTimer) clearTimeout(state.debounceTimer);
  state.debounceTimer = setTimeout(renderPreview, 30);
}

/**
 * 切换视口显示模式 (仿真实机 / 宽屏桌面)
 */
export function setViewMode(mode) {
  state.currentViewMode = mode;
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
 * 绑定视口模式切换按钮
 */
export function bindViewModeTabs() {
  document.getElementById('tab-mode-mobile').addEventListener('click', () => setViewMode('mobile'));
  document.getElementById('tab-mode-desktop').addEventListener('click', () => setViewMode('desktop'));
}

/**
 * MD2WX Web Studio - 封面工作台交互逻辑 (Cover Studio Engine)
 * 双比例封面预览缩放、微信分享卡片联动与封面图复制/下载导出
 */

import {
  COVER_DIMENSIONS,
  extractCoverMeta,
  renderCoverHtml,
  THEME_COVER_PRESETS,
  WECHAT_CROP_COORDINATES,
} from '../core/cover.js';
import { domToPngBlob, copyImageToClipboard, downloadImageBlob } from '../core/canvas_exporter.js';
import { state } from './state.js';
import { showToast } from './ui.js';
import { renderPreview, scheduleRender } from './preview.js';

const textarea = document.getElementById('markdown-input');

/**
 * 初始化封面工作台
 */
export function initCoverStudio() {
  const overlay = document.getElementById('cover-modal-overlay');
  const btnOpen = document.getElementById('btn-open-cover');
  const btnClose = document.getElementById('btn-close-cover-modal');
  const tabBanner = document.getElementById('tab-ratio-banner');
  const tabSquare = document.getElementById('tab-ratio-square');
  const tabDual = document.getElementById('tab-ratio-dual');
  const toggleSafeArea = document.getElementById('toggle-safe-area');
  const selectThemeEl = document.getElementById('select-cover-theme');
  const btnSync = document.getElementById('btn-sync-from-article');
  const btnCopyCoords = document.getElementById('btn-copy-crop-coords');
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
  let coverThemeId = state.currentThemeId;
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
    state.currentCoverMeta = { ...coverMeta };
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
      const preset = THEME_COVER_PRESETS[coverThemeId] || THEME_COVER_PRESETS['acid-bold'];
      shareThumbEl.innerHTML = `
        <div style="width:100%;height:100%;background:#0a0a0a;display:flex;flex-direction:column;align-items:center;justify-content:center;border-radius:4px;gap:2px;">
          <span style="font-size:9px;font-weight:900;color:#34d399;line-height:1;">${(preset.badgeText || 'COVER').slice(0, 6)}</span>
          <span style="font-size:8px;font-weight:700;color:#10b981;line-height:1;">1:1截取</span>
        </div>
      `;
    }

    updateScaler();
  }

  // 打开模态框
  function openCoverModal() {
    coverThemeId = state.currentThemeId;
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
    if (tabDual) tabDual.classList.remove('active');
    coverRatio = 'banner';
    renderCover();
  });

  tabSquare.addEventListener('click', () => {
    tabSquare.classList.add('active');
    tabBanner.classList.remove('active');
    if (tabDual) tabDual.classList.remove('active');
    coverRatio = 'square';
    renderCover();
  });

  if (tabDual) {
    tabDual.addEventListener('click', () => {
      tabDual.classList.add('active');
      tabBanner.classList.remove('active');
      tabSquare.classList.remove('active');
      coverRatio = 'dual';
      renderCover();
    });
  }

  if (btnCopyCoords) {
    btnCopyCoords.addEventListener('click', async () => {
      const coordsSnippet = `pic_crop_235_1: "${WECHAT_CROP_COORDINATES.crop_235_1}"\npic_crop_1_1: "${WECHAT_CROP_COORDINATES.crop_1_1}"`;
      try {
        await navigator.clipboard.writeText(coordsSnippet);
        showToast('微信双封面裁剪坐标已复制到剪贴板！', 'success');
      } catch (err) {
        showToast(`复制失败: ${err.message}`, 'error');
      }
    });
  }

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

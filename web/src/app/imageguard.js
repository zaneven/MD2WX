/**
 * MD2WX Web Studio - 外链图片防护
 * 微信编辑器会封禁外站图床的图片 (防盗链)，预览区顶部实时检测并提示，
 * 支持一键转存到 .env 配置的在线图床并回写编辑器换链
 */

import { collectExternalImageUrls } from '../core/parser.js';
import { isImageHostConfigured, rehostExternalImageUrl, IMAGE_HOST_UNCONFIGURED_HINT } from '../core/imagehost.js';
import { showToast } from './ui.js';

let bannerEl = null;
let rehosting = false;

/**
 * 每次渲染后调用：检测正文外链图片并维护防护横幅
 * @param {HTMLElement} scrollArea 预览滚动容器 (#phone-content-scroll)
 * @param {string} markdownBody 剥离 Frontmatter 后的正文
 */
export function updateExternalImageGuard(scrollArea, markdownBody) {
  const urls = collectExternalImageUrls(markdownBody);

  if (!urls.length) {
    if (bannerEl) {
      bannerEl.remove();
      bannerEl = null;
    }
    return;
  }

  if (!bannerEl) {
    bannerEl = document.createElement('div');
    bannerEl.className = 'external-image-guard';
    scrollArea.insertBefore(bannerEl, scrollArea.firstChild);
  }

  const canRehost = isImageHostConfigured();
  bannerEl.innerHTML = `
    <div style="margin: 10px 12px 0; padding: 10px 12px; border: 1px solid #fdba74; background: #fff7ed; border-radius: 8px; font-size: 12px; line-height: 1.6; color: #9a3412;">
      <div style="font-weight: 700; margin-bottom: 4px;">检测到 ${urls.length} 处外链图片</div>
      <div style="margin-bottom: 8px; word-break: break-all;">${escapeHtml(urls[0])}${urls.length > 1 ? ` 等 ${urls.length} 处` : ''}。微信编辑器可能封禁外站图床，建议转存。</div>
      <button type="button" data-guard-rehost style="${canRehost ? '' : 'opacity: 0.5;'} background: #ea580c; color: #ffffff; border: 0; border-radius: 6px; padding: 5px 12px; font-size: 12px; font-weight: 700; cursor: pointer;">一键转存图床</button>
      ${canRehost ? '' : '<span style="margin-left: 8px; color: #9a3412;">未配置图床</span>'}
    </div>`;

  const btn = bannerEl.querySelector('[data-guard-rehost]');
  if (btn) {
    btn.addEventListener('click', () => rehostAll(urls));
  }
}

async function rehostAll(urls) {
  if (rehosting) return;
  if (!isImageHostConfigured()) {
    showToast(IMAGE_HOST_UNCONFIGURED_HINT, 'error');
    return;
  }
  rehosting = true;
  showToast(`正在转存 ${urls.length} 处外链图片...`);
  const urlMap = new Map();
  let failed = 0;
  for (const url of urls) {
    try {
      const hosted = await rehostExternalImageUrl(url);
      urlMap.set(url, hosted);
    } catch (err) {
      failed++;
      console.warn('外链图片转存失败:', err);
    }
  }
  rehosting = false;

  if (urlMap.size > 0) {
    // 回写编辑器正文换链并触发重渲染
    const textarea = document.getElementById('markdown-input');
    let md = textarea.value;
    for (const [oldUrl, newUrl] of urlMap.entries()) {
      md = md.split(oldUrl).join(newUrl);
    }
    textarea.value = md;
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    showToast(`已转存 ${urlMap.size} 处外链图片${failed ? `，${failed} 处失败` : ''}`);
  } else {
    showToast(`外链图片转存失败 (跨域或图床未就绪)${failed ? `: ${failed} 处` : ''}`, 'error');
  }
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

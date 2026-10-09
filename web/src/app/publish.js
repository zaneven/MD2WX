/**
 * MD2WX Web Studio - 发布动作
 * 一键复制公众号排版富文本与导出自包含 HTML 文件
 */

import { ICONS } from '../assets/icons.js';
import { copyWechatHtml, downloadHtmlFile } from '../core/clipboard.js';
import { rasterizeRichBlocks, substituteRichHtml } from '../core/richrender.js';
import { state } from './state.js';
import { showToast } from './ui.js';

const textarea = document.getElementById('markdown-input');
const previewTarget = document.getElementById('preview-render-target');

/**
 * 获取可复制的最终 HTML：先把 Mermaid/公式渲染产物光栅化为内联 PNG
 * (微信不支持 SVG 与外部脚本，必须位图化才能存活)
 */
async function getExportableHtml() {
  if (!state.currentRichBlocks || !state.currentRichBlocks.length) {
    return state.currentHtmlOutput;
  }
  try {
    const replacements = await rasterizeRichBlocks(previewTarget, state.currentRichBlocks);
    return substituteRichHtml(state.currentHtmlOutput, replacements);
  } catch (err) {
    console.warn('富文本块光栅化失败，相关位置将保留占位:', err);
    return state.currentHtmlOutput;
  }
}

/**
 * 执行一键复制公众号排版
 */
export async function handleCopy() {
  if (!state.currentHtmlOutput) {
    showToast('当前暂无可复制的内容', 'error');
    return;
  }

  const btnHeader = document.getElementById('btn-copy-header');
  const btnFloating = document.getElementById('btn-copy-floating');

  const exportableHtml = await getExportableHtml();
  const result = await copyWechatHtml(exportableHtml, textarea.value);
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
 * 绑定顶部复制与导出按钮
 */
export function bindPublishActions() {
  document.getElementById('btn-copy-header').addEventListener('click', handleCopy);
  document.getElementById('btn-copy-floating').addEventListener('click', handleCopy);

  document.getElementById('btn-export-html').addEventListener('click', async () => {
    const exportableHtml = await getExportableHtml();
    downloadHtmlFile(exportableHtml, 'md2wx-article.html');
    showToast('已导出自包含微信排版 HTML 文件');
  });
}

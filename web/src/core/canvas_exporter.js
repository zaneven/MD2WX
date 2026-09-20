/**
 * MD2WX 高保真封面导出与剪贴板工具 (Robust Cover Canvas Exporter)
 * 采用【双引擎架构】：
 * 引擎 1：原生 SVG Data URL ForeignObject 超高清离线采样
 * 引擎 2：纯原生 Canvas 2D 矢量直绘保底引擎（100% 免疫沙箱跨域与 Tainted Canvas 限制）
 * 剪贴板支持 Promise 手势保持，彻底解决 Safari/Chrome 异步过期问题
 */

import { COVER_DIMENSIONS } from './cover.js';
import coverCssText from '../styles/cover.css?inline';

/**
 * 纯原生 Canvas 2D 高保真备用绘制引擎
 * 当 SVG 遇到跨域/沙箱限制时自动启用，零依赖秒级出图
 */
export function renderCoverDirectCanvas(themeId, ratio, meta, scale = 2) {
  const isSquare = ratio === 'square';
  const dim = COVER_DIMENSIONS[ratio] || COVER_DIMENSIONS.banner;
  const width = Math.round(dim.width * scale);
  const height = Math.round(dim.height * scale);

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');

  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';

  const title = meta.title || '在喧嚣时代重塑深度思考';
  const digest = meta.digest || '真正的专注，是在充满干扰的世界中守住内心的秩序';
  const author = meta.author || '野生宝藏箱';
  const tag = meta.tag || '深度架构 · 极客手记';
  const badge = meta.badge || 'TECH BLOG';
  const vol = meta.vol || '2026 · VOL.02';
  const site = meta.website || 'MD2WX.ZANEVEN.COM';

  // 1. 背景绘制 (根据主题定制)
  ctx.save();
  if (themeId === 'acid-bold') {
    ctx.fillStyle = '#fee500';
    ctx.fillRect(0, 0, width, height);
    // 粗黑边框
    ctx.lineWidth = 20 * scale;
    ctx.strokeStyle = '#000000';
    ctx.strokeRect(0, 0, width, height);
  } else if (themeId === 'dark-night') {
    const grad = ctx.createRadialGradient(width * 0.75, height * 0.25, 40 * scale, width * 0.5, height * 0.5, width * 0.85);
    grad.addColorStop(0, '#1e1b4b');
    grad.addColorStop(0.65, '#030712');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = '#312e81';
    ctx.lineWidth = 1 * scale;
    ctx.strokeRect(0, 0, width, height);
  } else if (themeId === 'terminal-geek') {
    ctx.fillStyle = '#020617';
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = '#065f46';
    ctx.lineWidth = 4 * scale;
    ctx.strokeRect(0, 0, width, height);
  } else if (themeId === 'vintage-news') {
    ctx.fillStyle = '#fdfbf7';
    ctx.fillRect(0, 0, width, height);
    // 双细线边框
    ctx.strokeStyle = '#44403c';
    ctx.lineWidth = 6 * scale;
    ctx.strokeRect(16 * scale, 16 * scale, width - 32 * scale, height - 32 * scale);
    ctx.lineWidth = 2 * scale;
    ctx.strokeRect(24 * scale, 24 * scale, width - 48 * scale, height - 48 * scale);
  } else if (themeId === 'warm-memo') {
    ctx.fillStyle = '#fefcf8';
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = '#fed7aa';
    ctx.lineWidth = 2 * scale;
    ctx.strokeRect(0, 0, width, height);
  } else if (themeId === 'warm-orange') {
    const grad = ctx.createLinearGradient(0, 0, width, height);
    grad.addColorStop(0, '#ea580c');
    grad.addColorStop(1, '#7c2d12');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);
  } else if (themeId === 'wechat-green') {
    const grad = ctx.createLinearGradient(0, 0, width, height);
    grad.addColorStop(0, '#064e3b');
    grad.addColorStop(1, '#022c22');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);
  } else if (themeId === 'elegant-purple') {
    const grad = ctx.createLinearGradient(0, 0, width, height);
    grad.addColorStop(0, '#2e1065');
    grad.addColorStop(1, '#0f172a');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);
  } else {
    // 默认 tech-blue
    const grad = ctx.createRadialGradient(width * 0.8, height * 0.2, 50 * scale, width * 0.5, height * 0.5, width * 0.8);
    grad.addColorStop(0, '#1e3a8a');
    grad.addColorStop(0.7, '#0a0f1d');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);
  }
  ctx.restore();

  // 辅助圆角矩形方法
  function drawRoundRect(x, y, w, h, r, fillColor, strokeColor, strokeWidth = 1) {
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
    if (fillColor) {
      ctx.fillStyle = fillColor;
      ctx.fill();
    }
    if (strokeColor) {
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = strokeWidth;
      ctx.stroke();
    }
    ctx.restore();
  }

  // 文本折行渲染助手
  function drawWrapText(text, x, y, maxW, lineH, maxLines = 3) {
    const chars = text.split('');
    let line = '';
    let currentY = y;
    let linesDrawn = 0;

    for (let n = 0; n < chars.length; n++) {
      const testLine = line + chars[n];
      const metrics = ctx.measureText(testLine);
      if (metrics.width > maxW && n > 0) {
        if (linesDrawn === maxLines - 1 && n < chars.length) {
          ctx.fillText(line + '...', x, currentY);
          return;
        }
        ctx.fillText(line, x, currentY);
        line = chars[n];
        currentY += lineH;
        linesDrawn++;
        if (linesDrawn >= maxLines) return;
      } else {
        line = testLine;
      }
    }
    ctx.fillText(line, x, currentY);
  }

  // 确定色彩与文字
  const isAcid = themeId === 'acid-bold';
  const isTerm = themeId === 'terminal-geek';
  const isVintage = themeId === 'vintage-news';
  const isMemo = themeId === 'warm-memo';

  let primaryText = '#ffffff';
  let subText = 'rgba(255, 255, 255, 0.85)';
  let accentColor = '#38bdf8';

  if (isAcid) {
    primaryText = '#000000';
    subText = '#262626';
    accentColor = '#000000';
  } else if (isVintage || isMemo) {
    primaryText = '#1c1917';
    subText = '#57534e';
    accentColor = isMemo ? '#ea580c' : '#854d0e';
  } else if (isTerm) {
    primaryText = '#10b981';
    subText = '#a7f3d0';
    accentColor = '#10b981';
  }

  const padX = 52 * scale;
  const padY = 44 * scale;

  if (isSquare) {
    // 方形版式 (1:1) - 移动端优先大字版
    // 顶部栏
    ctx.font = `900 ${20 * scale}px -apple-system, sans-serif`;
    const badgeW = ctx.measureText(badge).width + 36 * scale;
    drawRoundRect(padX, padY, badgeW, 38 * scale, 19 * scale, isAcid ? '#000' : accentColor);
    ctx.fillStyle = isAcid ? '#fee500' : '#ffffff';
    ctx.fillText(badge, padX + 18 * scale, padY + 26 * scale);

    ctx.fillStyle = subText;
    ctx.font = `800 ${20 * scale}px ui-monospace, Menlo, monospace`;
    ctx.textAlign = 'right';
    ctx.fillText(vol, width - padX, padY + 26 * scale);
    ctx.textAlign = 'left';

    // 居中主内容
    const midY = height * 0.26;
    drawRoundRect(padX, midY, ctx.measureText(tag).width + 32 * scale, 36 * scale, 18 * scale, 'rgba(128,128,128,0.2)');
    ctx.fillStyle = accentColor;
    ctx.font = `800 ${18 * scale}px -apple-system, sans-serif`;
    ctx.fillText(tag, padX + 16 * scale, midY + 25 * scale);

    // 超大主标题 (52px)
    ctx.fillStyle = primaryText;
    ctx.font = `900 ${52 * scale}px -apple-system, sans-serif`;
    drawWrapText(title, padX, midY + 92 * scale, width - padX * 2, 62 * scale, 3);

    // 大字金句导读 (24px)
    ctx.fillStyle = subText;
    ctx.font = `600 ${24 * scale}px -apple-system, sans-serif`;
    drawWrapText(digest, padX, midY + 290 * scale, width - padX * 2, 38 * scale, 2);

    // 底部栏 (精简纯作者)
    ctx.strokeStyle = isAcid ? '#000000' : 'rgba(255, 255, 255, 0.15)';
    ctx.lineWidth = isAcid ? 4 * scale : 1 * scale;
    ctx.beginPath();
    ctx.moveTo(padX, height - padY - 20 * scale);
    ctx.lineTo(width - padX, height - padY - 20 * scale);
    ctx.stroke();

    ctx.fillStyle = primaryText;
    ctx.font = `800 ${22 * scale}px -apple-system, sans-serif`;
    ctx.fillText(author, padX, height - padY);
  } else {
    // 横版 Banner (2.35:1) - 移动端优先大字版
    // 顶部栏
    ctx.font = `900 ${20 * scale}px -apple-system, sans-serif`;
    const badgeW = ctx.measureText(badge).width + 36 * scale;
    drawRoundRect(padX, padY, badgeW, 38 * scale, 19 * scale, isAcid ? '#000000' : accentColor);
    ctx.fillStyle = isAcid ? '#fee500' : '#ffffff';
    ctx.fillText(badge, padX + 18 * scale, padY + 26 * scale);

    ctx.fillStyle = subText;
    ctx.font = `800 ${22 * scale}px -apple-system, sans-serif`;
    ctx.fillText(tag, padX + badgeW + 20 * scale, padY + 27 * scale);

    ctx.font = `800 ${20 * scale}px ui-monospace, Menlo, monospace`;
    ctx.textAlign = 'right';
    ctx.fillText(vol, width - padX, padY + 27 * scale);
    ctx.textAlign = 'left';

    // 左侧 1:1 核心视觉资产区：放大锁定在 410px 宽度内折行，绝对不超出 500px 微信截取线
    const leftW = 410 * scale;
    const bodyStartY = padY + 84 * scale;

    drawRoundRect(padX, bodyStartY, 64 * scale, 8 * scale, 4 * scale, accentColor);

    // 超大主标题 (46px，严格安全防越界)
    ctx.fillStyle = primaryText;
    ctx.font = `900 ${46 * scale}px -apple-system, sans-serif`;
    drawWrapText(title, padX, bodyStartY + 68 * scale, leftW, 56 * scale, 3);

    // 绘制大号作者落款胶囊 (19px)
    const authorPillW = ctx.measureText(author).width + 34 * scale;
    drawRoundRect(padX, bodyStartY + 270 * scale, authorPillW, 36 * scale, 18 * scale, 'rgba(128,128,128,0.22)');
    ctx.fillStyle = primaryText;
    ctx.font = `800 ${19 * scale}px -apple-system, sans-serif`;
    ctx.fillText(author, padX + 17 * scale, bodyStartY + 295 * scale);

    // 右侧大字金句引言卡片 (大字 28px，精简掉底部小网址和多余层级)
    const cardX = width - padX - 450 * scale;
    const cardY = bodyStartY + 6 * scale;
    const cardW = 450 * scale;
    const cardH = 280 * scale;

    drawRoundRect(
      cardX, cardY, cardW, cardH, 24 * scale,
      isAcid ? '#ffffff' : (isVintage || isMemo ? '#f5f0e6' : 'rgba(255, 255, 255, 0.12)'),
      isAcid ? '#000000' : 'rgba(255, 255, 255, 0.22)',
      isAcid ? 5 * scale : 1 * scale
    );

    // 卡片大字导读 (28px)
    ctx.fillStyle = isAcid || isVintage || isMemo ? '#1c1917' : '#ffffff';
    ctx.font = `700 ${28 * scale}px -apple-system, sans-serif`;
    drawWrapText(digest, cardX + 36 * scale, cardY + 70 * scale, cardW - 72 * scale, 42 * scale, 3);

    // 卡片右下角大号作者签名 (22px)
    ctx.fillStyle = isAcid ? '#000000' : (isVintage || isMemo ? '#854d0e' : accentColor);
    ctx.font = `800 ${22 * scale}px -apple-system, sans-serif`;
    ctx.textAlign = 'right';
    ctx.fillText(`— ${author}`, cardX + cardW - 36 * scale, cardY + cardH - 32 * scale);
    ctx.textAlign = 'left';
  }

  return new Promise((resolve) => {
    canvas.toBlob((blob) => {
      resolve(blob);
    }, 'image/png', 1.0);
  });
}

/**
 * 将指定 DOM 节点导出为高清 PNG Blob (高保真 DOM 光栅化引擎)
 * 100% 忠实还原页面上真实展示的 CSS 样式、渐变、阴影、矢量图与排版效果
 * @param {HTMLElement} element - 页面上真实渲染的 .cover-canvas DOM 节点
 * @param {Object} options
 * @returns {Promise<Blob>}
 */
export async function domToPngBlob(element, options = {}) {
  const { width = 1175, height = 500, scale = 2, themeId = 'tech-blue', ratio = 'banner', meta = {} } = options;

  if (!element) {
    return await renderCoverDirectCanvas(themeId, ratio, meta, scale);
  }

  // 1. 深克隆页面上正在显示的真实 DOM 节点
  const clone = element.cloneNode(true);

  // 2. 移除任何可能叠加在界面上的参考辅助线（例如安全区虚线、微信 1:1 截取框等）
  const guides = clone.querySelectorAll('.cover-safe-guide, .cover-wechat-crop-guide');
  guides.forEach((g) => g.remove());

  // 3. 强制重设几何物理尺寸与独立布局，剥离视口 transform 缩放影响
  clone.style.transform = 'none';
  clone.style.webkitTransform = 'none';
  clone.style.margin = '0';
  clone.style.position = 'relative';
  clone.style.top = '0';
  clone.style.left = '0';
  clone.style.width = `${width}px`;
  clone.style.height = `${height}px`;
  clone.style.boxSizing = 'border-box';

  // 4. 将克隆的 DOM 序列化为符合 XML 规范的合法 XHTML
  const serializer = new XMLSerializer();
  const xhtml = serializer.serializeToString(clone);

  // 5. 组装内联了全部 cover.css 设计样式的自包含独立 SVG 文档
  //    注意：必须剥离 backdrop-filter，SVG foreignObject 光栅化会错误渲染毛玻璃图层，
  //    其阴影会溢出遮挡底部栏文字，导致导出内容与预览不一致。
  const exportCssText = coverCssText.replace(/(-webkit-)?backdrop-filter\s*:[^;}]*/g, '');
  const svgString = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <defs>
    <style type="text/css">
      <![CDATA[
        *, *::before, *::after {
          box-sizing: border-box;
          -webkit-font-smoothing: antialiased;
        }
        ${exportCssText}
      ]]>
    </style>
  </defs>
  <foreignObject width="${width}" height="${height}" x="0" y="0">
    <div xmlns="http://www.w3.org/1999/xhtml" style="width:${width}px;height:${height}px;margin:0;padding:0;overflow:hidden;-webkit-font-smoothing:antialiased;">
      ${xhtml}
    </div>
  </foreignObject>
</svg>`;

  // 6. 必须使用 Data URL 而非 Blob URL：Chromium 下 Blob URL 的 SVG 图像绘制到 Canvas 会触发
  //    Tainted Canvas SecurityError，导致 toBlob 抛异常而静默降级到备用引擎（样式与预览不一致）。
  //    Data URL 加载的 SVG 保持画布 Origin-Clean，可完整保留 DOM 光栅化的高保真结果。
  const dataUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgString);
  const img = new Image();

  return new Promise((resolve) => {
    let timeoutId = setTimeout(() => {
      console.warn('SVG 光栅化超时，切换为原生 Canvas 2D 备用引擎');
      resolve(renderCoverDirectCanvas(themeId, ratio, meta, scale));
    }, 1800);

    img.onload = () => {
      clearTimeout(timeoutId);
      try {
        const canvas = document.createElement('canvas');
        canvas.width = Math.round(width * scale);
        canvas.height = Math.round(height * scale);
        const ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

        canvas.toBlob((blob) => {
          if (blob) {
            resolve(blob);
          } else {
            console.warn('toBlob 返回空，回退备用引擎');
            resolve(renderCoverDirectCanvas(themeId, ratio, meta, scale));
          }
        }, 'image/png', 1.0);
      } catch (err) {
        clearTimeout(timeoutId);
        console.warn('Canvas 绘制异常，切换为备用引擎:', err);
        resolve(renderCoverDirectCanvas(themeId, ratio, meta, scale));
      }
    };

    img.onerror = (err) => {
      clearTimeout(timeoutId);
      console.warn('Image 加载 SVG 失败，切换为备用引擎:', err);
      resolve(renderCoverDirectCanvas(themeId, ratio, meta, scale));
    };

    img.src = dataUrl;
  });
}

/**
 * 将 Blob 图片写入系统剪贴板（微信公众号后台可直接 Cmd+V / Ctrl+V 粘贴）
 * 遵循现代浏览器标准：优先使用直传 Blob，回退支持 Promise<Blob>
 * @param {Blob|Promise<Blob>} imageBlobOrPromise
 * @returns {Promise<boolean>}
 */
export async function copyImageToClipboard(imageBlobOrPromise) {
  if (!navigator.clipboard || !window.ClipboardItem) {
    throw new Error('当前浏览器不支持直接写入图片至剪贴板，请使用下载 PNG 按钮');
  }

  // 1. Safari 核心方案：在用户手势初始调用栈中，直接传入 Promise<Blob>，防止 await 导致手势令牌失效
  try {
    const isPromise = Boolean(imageBlobOrPromise && typeof imageBlobOrPromise.then === 'function');
    const blobPromise = isPromise ? imageBlobOrPromise : Promise.resolve(imageBlobOrPromise);
    const item = new ClipboardItem({ 'image/png': blobPromise });
    await navigator.clipboard.write([item]);
    return true;
  } catch (safariErr) {
    console.warn('Promise 剪贴板写入未通过，尝试解析实体 Blob 写入:', safariErr);
    // 2. Chromium 核心方案：解析出 Blob 实例后再行写入
    try {
      const resolvedBlob = await Promise.resolve(imageBlobOrPromise);
      const mimeType = resolvedBlob.type || 'image/png';
      const item = new ClipboardItem({ [mimeType]: resolvedBlob });
      await navigator.clipboard.write([item]);
      return true;
    } catch (fallbackErr) {
      console.error('剪贴板双引擎写入异常:', fallbackErr);
      throw new Error(fallbackErr.message || '浏览器拒绝了剪贴板写入');
    }
  }
}

/**
 * 触发本地图片下载
 * @param {Blob} blob
 * @param {string} filename
 */
export function downloadImageBlob(blob, filename = 'md2wx-cover.png') {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/**
 * MD2WX 富文本块渲染引擎 (浏览器端)
 * Mermaid 图表 / 数学公式 在 Web Studio 的预览水合与复制光栅化：
 *   1. prepareRichBlocks   与 CLI 端 md2wx/richrender.py 同规则抽取占位 token
 *   2. hydrateRichBlocks   预览区动态加载 mermaid/KaTeX (CDN) 就地渲染
 *   3. rasterizeRichBlocks 复制/导出前将渲染产物光栅化为 2x 高清 data URI PNG
 * 微信不支持 SVG 与外部脚本，复制产物必须为内联位图才能存活
 */

const MERMAID_ESM_URL = 'https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs';
const KATEX_JS_URL = 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js';
const KATEX_CSS_URL = 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css';

const RICH_TOKEN_RE = /@@MD(?:MERMAID|MATH)_\d+@@/g;
const MATH_BLOCK_ONELINE_RE = /\$\$(?!\s)([\s\S]+?)(?<!\s)\$\$/;
const MATH_BLOCK_DELIM_RE = /^\$\$\s*$/;
const MATH_INLINE_RE = /\$(?!\s)((?:[^$\n\\]|\\.)+?)(?<!\s)\$(?!\d)/g;

/**
 * 与 CLI 端 extract_rich_blocks 同规则预处理：
 * ```mermaid 围栏 / $$..$$ 公式块 / $..$ 行内公式 -> 占位 token
 * 返回 { md, blocks }；blocks 项含 token/kind/content/display 字段
 */
export function prepareRichBlocks(mdText) {
  const lines = String(mdText || '').split('\n');
  const outLines = [];
  const blocks = [];

  const nextToken = (kind, content, display) => {
    const token = `@@MD${kind}_${blocks.length}@@`;
    blocks.push({ token, kind: kind.toLowerCase(), content, display });
    return token;
  };

  let inFence = false;
  let fenceMarker = '';
  let mathBlockOpen = false;
  let mathBlockLines = [];

  let idx = 0;
  while (idx < lines.length) {
    let line = lines[idx];
    const stripped = line.trim();

    if (!inFence && stripped.startsWith('```')) {
      const lang = stripped.slice(3).trim().toLowerCase();
      if (lang === 'mermaid') {
        const codeLines = [];
        idx++;
        while (idx < lines.length && !lines[idx].trim().startsWith('```')) {
          codeLines.push(lines[idx]);
          idx++;
        }
        idx++;
        outLines.push(nextToken('MERMAID', codeLines.join('\n').trim(), true));
        continue;
      }
      inFence = true;
      fenceMarker = stripped.slice(0, 3);
      outLines.push(line);
      idx++;
      continue;
    }
    if (inFence) {
      outLines.push(line);
      if (stripped.startsWith(fenceMarker)) inFence = false;
      idx++;
      continue;
    }

    if (!mathBlockOpen && MATH_BLOCK_DELIM_RE.test(stripped)) {
      mathBlockOpen = true;
      mathBlockLines = [];
      idx++;
      continue;
    }
    if (mathBlockOpen) {
      if (MATH_BLOCK_DELIM_RE.test(stripped)) {
        outLines.push(nextToken('MATH', mathBlockLines.join('\n').trim(), true));
        mathBlockOpen = false;
      } else {
        mathBlockLines.push(line);
      }
      idx++;
      continue;
    }

    const onelineMath = MATH_BLOCK_ONELINE_RE.exec(stripped);
    if (onelineMath && stripped.replace(/^\$\$|\$\$$/g, '').trim() === onelineMath[1].trim()) {
      outLines.push(nextToken('MATH', onelineMath[1].trim(), true));
      idx++;
      continue;
    }

    if (line.includes('$')) {
      line = line.replace(MATH_INLINE_RE, (_, tex) => nextToken('MATH', tex, false));
    }

    outLines.push(line);
    idx++;
  }

  if (mathBlockOpen) {
    outLines.push('$$');
    outLines.push(...mathBlockLines);
  }

  return { md: outLines.join('\n'), blocks };
}

/**
 * 预览区水合：把容器内出现的富文本 token (占位 div 或行内文本节点)
 * 就地渲染为 Mermaid SVG / KaTeX 排版。CDN 加载失败时降级为代码/文本形态
 */
export async function hydrateRichBlocks(container, blocks) {
  if (!container || !blocks.length) return;
  const blockMap = new Map(blocks.map((b) => [b.token, b]));

  // 1. 占位 div (整块级 token)
  for (const block of blocks) {
    const el = container.querySelector(`[data-md-rich-token="${CSS.escape(block.token)}"]`);
    if (el) {
      await hydrateBlockElement(el, block);
    }
  }

  // 2. 行内 token (公式混排在段落/表格/引用中)
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  const targets = [];
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (node.nodeValue && RICH_TOKEN_RE.test(node.nodeValue)) {
      targets.push(node);
      RICH_TOKEN_RE.lastIndex = 0;
    }
  }
  for (const textNode of targets) {
    RICH_TOKEN_RE.lastIndex = 0;
    const parts = textNode.nodeValue.split(/(@@MD(?:MERMAID|MATH)_\d+@@)/);
    const frag = document.createDocumentFragment();
    for (const part of parts) {
      if (blockMap.has(part)) {
        const span = document.createElement('span');
        frag.appendChild(span);
        await hydrateBlockElement(span, blockMap.get(part), true);
      } else {
        frag.appendChild(document.createTextNode(part));
      }
    }
    textNode.parentNode.replaceChild(frag, textNode);
  }
}

async function hydrateBlockElement(el, block, inline = false) {
  try {
    if (block.kind === 'mermaid') {
      const mermaid = (await import(/* @vite-ignore */ MERMAID_ESM_URL)).default;
      mermaid.initialize({ startOnLoad: false, theme: 'neutral' });
      const { svg } = await mermaid.render(`md2wx-web-svg-${Math.random().toString(36).slice(2)}`, block.content);
      el.innerHTML = svg;
      const svgEl = el.querySelector('svg');
      if (svgEl) {
        svgEl.style.maxWidth = '100%';
        svgEl.style.height = 'auto';
      }
    } else {
      await ensureKatex();
      const inner = document.createElement('span');
      inner.style.display = 'inline-block';
      window.katex.render(block.content, inner, {
        displayMode: !inline && block.display !== false,
        throwOnError: false,
      });
      el.innerHTML = '';
      el.appendChild(inner);
    }
    el.dataset.hydrated = '1';
    // 行内 token 没有占位 div，打标记供 rasterizeRichBlocks 定位当前水合节点
    if (inline) {
      el.setAttribute('data-md-rich-inline', block.token);
    }
  } catch (err) {
    console.warn('富文本块渲染失败，降级为文本形态:', err);
    el.dataset.hydrated = 'error';
    if (block.kind === 'mermaid') {
      el.innerHTML = `<pre style="text-align:left; background:#18181b; color:#e4e4e7; padding:14px 16px; border-radius:8px; overflow-x:auto; font-size:13.5px; font-family:monospace;">${escapeText(block.content)}</pre>`;
    } else {
      el.textContent = block.content;
    }
  }
}

function escapeText(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      existing.addEventListener('load', () => resolve());
      existing.addEventListener('error', reject);
      if (window.katex) resolve();
      return;
    }
    const script = document.createElement('script');
    script.src = src;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('加载失败: ' + src));
    document.head.appendChild(script);
  });
}

async function ensureKatex() {
  if (window.katex) return;
  if (!document.querySelector(`link[href="${KATEX_CSS_URL}"]`)) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = KATEX_CSS_URL;
    document.head.appendChild(link);
  }
  await loadScript(KATEX_JS_URL);
  if (!window.katex) throw new Error('KaTeX 加载失败');
}

/**
 * 复制/导出前光栅化：把 hydrated 的渲染产物转为 2x 高清 data URI PNG，
 * 返回 token -> <img ...> 替换映射；未水合或光栅化失败的块返回 null (由调用方降级)
 */
export async function rasterizeRichBlocks(container, blocks) {
  const replacements = new Map();
  if (!container) return replacements;

  for (const block of blocks) {
    // 块级 token 有占位 div；行内 token 靠水合时打的 data-md-rich-inline 标记定位
    const el =
      container.querySelector(`[data-md-rich-token="${CSS.escape(block.token)}"]`) ||
      container.querySelector(`[data-md-rich-inline="${CSS.escape(block.token)}"]`);
    if (!el || el.dataset.hydrated !== '1') continue;
    try {
      let dataUrl;
      if (block.kind === 'mermaid') {
        const svgEl = el.querySelector('svg');
        if (!svgEl) continue;
        dataUrl = await svgToPngDataUrl(svgEl);
      } else {
        dataUrl = await nodeToPngDataUrl(el.firstElementChild || el);
      }
      if (dataUrl) {
        const w = el.querySelector('svg')?.getAttribute('width') || el.getBoundingClientRect().width;
        replacements.set(block.token, buildRichImgHtml(dataUrl, block, Math.round(Number(w) || 0)));
      }
    } catch (err) {
      console.warn('富文本块光栅化失败:', err);
    }
  }
  return replacements;
}

function buildRichImgHtml(dataUrl, block, logicalWidth) {
  // 2x 采样图按逻辑像素宽度回显，与正文字号协调且移动端清晰
  const widthStyle = logicalWidth > 0 ? `width: ${logicalWidth}px;` : '';
  if (block.display === false) {
    return `<img src="${dataUrl}" alt="formula" style="max-width: 100%; height: auto; vertical-align: middle; display: inline-block; ${widthStyle}" />`;
  }
  return `<div style="margin: 22px 0; text-align: center;"><img src="${dataUrl}" alt="${block.kind === 'mermaid' ? 'mermaid diagram' : 'formula'}" style="max-width: 100%; height: auto; display: inline-block; ${widthStyle}" /></div>`;
}

/** 把占位 div 与行内 token 一并替换为光栅化产物，返回可复制 HTML 字符串 */
export function substituteRichHtml(html, replacements) {
  let out = html;
  for (const [token, imgHtml] of replacements.entries()) {
    // 整块级占位 div (parser 输出的精确形态)
    out = out.split(`<div style="margin: 22px 0; text-align: center;" data-md-rich-token="${token}"></div>`).join(imgHtml);
    // 行内残留 token
    out = out.split(token).join(imgHtml);
  }
  return out;
}

async function svgToPngDataUrl(svgEl, scale = 2) {
  const rect = svgEl.getBoundingClientRect();
  const w = Math.max(1, Math.ceil(Number(svgEl.getAttribute('width')) || rect.width));
  const h = Math.max(1, Math.ceil(Number(svgEl.getAttribute('height')) || rect.height));

  const clone = svgEl.cloneNode(true);
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  clone.setAttribute('width', w);
  clone.setAttribute('height', h);
  const xhtml = new XMLSerializer().serializeToString(clone);
  const dataUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(xhtml);

  return drawImageToPngDataUrl(dataUrl, w, h, scale);
}

/**
 * DOM 节点 (KaTeX 排版) -> PNG data URI
 * 通过 foreignObject 光栅化；KaTeX 样式与字体全部内联为 data URI
 * (SVG image 独立上下文无法加载外部资源)
 */
async function nodeToPngDataUrl(node, scale = 2) {
  const rect = node.getBoundingClientRect();
  const w = Math.max(1, Math.ceil(rect.width));
  const h = Math.max(1, Math.ceil(rect.height));
  const cssText = await getKatexCssInlined();

  const clone = node.cloneNode(true);
  const xhtml = new XMLSerializer().serializeToString(clone);
  const svgString = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
<defs><style type="text/css"><![CDATA[${cssText}]]></style></defs>
<foreignObject width="${w}" height="${h}" x="0" y="0">
<div xmlns="http://www.w3.org/1999/xhtml" style="margin:0;padding:0;">${xhtml}</div>
</foreignObject>
</svg>`;
  const dataUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgString);
  return drawImageToPngDataUrl(dataUrl, w, h, scale);
}

function drawImageToPngDataUrl(dataUrl, w, h, scale = 2) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const timer = setTimeout(() => reject(new Error('光栅化超时')), 6000);
    img.onload = () => {
      clearTimeout(timer);
      try {
        const canvas = document.createElement('canvas');
        canvas.width = w * scale;
        canvas.height = h * scale;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL('image/png'));
      } catch (err) {
        clearTimeout(timer);
        reject(err);
      }
    };
    img.onerror = () => {
      clearTimeout(timer);
      reject(new Error('SVG 图像加载失败'));
    };
    img.src = dataUrl;
  });
}

let katexCssCache = null;

/** 拉取 katex.min.css 并把其中的字体文件全部内联为 data URI (会话级缓存) */
async function getKatexCssInlined() {
  if (katexCssCache) return katexCssCache;
  const res = await fetch(KATEX_CSS_URL);
  if (!res.ok) throw new Error('KaTeX CSS 拉取失败');
  let css = await res.text();

  const fontUrls = [...css.matchAll(/url\((https:\/\/[^)]+\.woff2)\)/g)].map((m) => m[1]);
  const uniq = [...new Set(fontUrls)];
  await Promise.all(
    uniq.map(async (url) => {
      try {
        const fontRes = await fetch(url);
        if (!fontRes.ok) return;
        const buf = await fontRes.arrayBuffer();
        let binary = '';
        const bytes = new Uint8Array(buf);
        for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
        const b64 = btoa(binary);
        css = css.split(url).join(`data:font/woff2;base64,${b64}`);
      } catch {
        // 单个字体失败时保留原 URL，退化字体回退
      }
    })
  );
  katexCssCache = css;
  return css;
}

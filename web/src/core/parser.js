/**
 * MD2WX 前端纯 JavaScript Markdown -> 微信内联 HTML 解析与渲染引擎
 * 1:1 复刻 Python 端核心排版与组件风格矩阵
 */
import { getTheme, DEFAULT_THEME_ID } from './themes.js';
import { highlightCode } from './highlighter.js';

/**
 * 解析并剥离 Markdown 顶部的 YAML Frontmatter
 */
export function parseFrontmatter(text) {
  const meta = {};
  let body = text;

  if (text.startsWith('---')) {
    const parts = text.split('---');
    if (parts.length >= 3) {
      const fmText = parts[1].trim();
      body = parts.slice(2).join('---').trim();

      const lines = fmText.split('\n');
      for (const line of lines) {
        if (line.includes(':')) {
          const colonIdx = line.indexOf(':');
          const k = line.slice(0, colonIdx).trim();
          let v = line.slice(colonIdx + 1).trim();

          // 去除首尾引号
          if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
            v = v.slice(1, -1);
          }

          if (v.startsWith('[') && v.endsWith(']')) {
            const tags = v
              .slice(1, -1)
              .split(',')
              .map((t) => t.trim().replace(/^['"]|['"]$/g, ''))
              .filter(Boolean);
            meta[k] = tags;
          } else {
            meta[k] = v;
          }
        }
      }
    }
  }

  return { meta, body };
}

/**
 * 剥离 Markdown 符号生成纯文本摘要
 */
export function stripMarkdown(mdText, maxLen = 120) {
  let text = mdText.replace(/!\[.*?\]\(.*?\)/g, '');
  text = text.replace(/\[(.*?)\]\(.*?\)/g, '$1');
  text = text.replace(/```[\s\S]*?```/g, '');
  text = text.replace(/[`#*_\->|]/g, '');
  const lines = text
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean);
  const plain = lines.join(' ');
  return plain.slice(0, maxLen).trim();
}

/**
 * 统一解析行内 Markdown 语法：
 * 1. 严格转义并保护行内代码，防止 <style> 破坏微信排版
 * 2. 保护超链接
 * 3. 粗体与斜体
 * 4. 还原 Tokens
 */
export function formatInline(text, accent, codeFontSize = '13.5px', footnotes = null) {
  const tokens = {};
  let tokenIdx = 0;

  // 1. 保护并转义行内代码 `...`
  text = text.replace(/`([^`]+?)`/g, (_, raw) => {
    const k = `@@MDCODE_${tokenIdx++}@@`;
    const esc = raw
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
    tokens[k] = `<code style="background: rgba(0,0,0,0.06); padding: 2px 6px; border-radius: 4px; font-size: ${codeFontSize}; color: ${accent}; font-family: monospace;">${esc}</code>`;
    return k;
  });

  // 2. 保护超链接 [...](...)，若开启脚注且非锚点链接则生成微信文末参考脚注
  text = text.replace(/\[(.*?)\]\((.*?)\)/g, (_, label, url) => {
    const k = `@@MDLINK_${tokenIdx++}@@`;
    let escLabel = label
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // 展开嵌套的 code token
    for (const [tk, tv] of Object.entries(tokens)) {
      if (escLabel.includes(tk)) {
        escLabel = escLabel.split(tk).join(tv);
      }
    }

    // 本地 file 协议转换为安全链接
    if (url.startsWith('file:///')) {
      if (url.includes('MD2WX')) {
        const sub = url.split('MD2WX/')[1];
        url = `https://github.com/zaneven/MD2WX/blob/main/${sub}`;
      } else {
        url = 'https://github.com/zaneven/MD2WX';
      }
    }

    if (footnotes && !url.startsWith('#')) {
      let fIndex = footnotes.findIndex((f) => f.url === url);
      if (fIndex === -1) {
        footnotes.push({ label: escLabel, url });
        fIndex = footnotes.length;
      } else {
        fIndex = fIndex + 1;
      }
      tokens[k] = `<span style="color: ${accent}; font-weight: 500;">${escLabel}</span><sup style="font-size: 11px; color: ${accent}; margin-left: 2px; font-weight: bold; vertical-align: super;">[${fIndex}]</sup>`;
    } else {
      tokens[k] = `<a href="${url}" style="color: ${accent}; text-decoration: none; border-bottom: 1px dashed ${accent};">${escLabel}</a>`;
    }
    return k;
  });

  // 3. 粗体与斜体
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/(^|[^*])\*([^*]+?)\*(?!\*)/g, '$1<em>$2</em>');

  // 4. 彻底还原保护的 tokens (支持嵌套多轮展开)
  let loops = 5;
  while (Object.keys(tokens).some((k) => text.includes(k)) && loops-- > 0) {
    for (const [k, v] of Object.entries(tokens)) {
      if (text.includes(k)) {
        text = text.split(k).join(v);
      }
    }
  }

  // 5. 防御性清除任何控制字符
  text = text.replace(/\x00/g, '');

  return text;
}

// ==============================================================================
// 视觉组件渲染策略 (Component Renderers)
// ==============================================================================

export function renderH1(titleText, theme) {
  const style = theme.h1_style || theme.styles?.h1 || 'underline';
  const accent = theme.accent;
  const accentBg = theme.accent_bg;
  const borderColor = theme.border_color;
  const codeBg = theme.code_bg;
  const subColor = theme.sub_color;
  const pageBg = theme.page_bg || '#ffffff';
  const isDark = ['#0b0f19', '#0f172a', '#18181b', '#09090b'].includes(pageBg);
  const titleColor = isDark ? '#f8fafc' : '#18181b';

  if (style === 'double_line') {
    return `
<div style="margin: 38px 0 26px 0; text-align: center;">
<div style="border-top: 1px solid ${borderColor}; border-bottom: 1px solid ${borderColor}; padding: 12px 14px; display: inline-block; min-width: 60%;">
<h1 style="font-size: 22px; font-weight: 700; color: ${accent}; margin: 0; line-height: 1.4; letter-spacing: 1px;">${titleText}</h1>
</div></div>`;
  } else if (style === 'capsule') {
    return `
<div style="margin: 36px 0 24px 0; text-align: center;">
<span style="display: inline-block; background: ${accent}; color: #ffffff; padding: 9px 26px; border-radius: 30px; font-size: 20px; font-weight: 700; letter-spacing: 0.8px; box-shadow: 0 4px 14px rgba(0,0,0,0.12);">
${titleText}
</span></div>`;
  } else if (style === 'terminal') {
    return `
<div style="margin: 36px 0 24px 0; padding: 14px 18px; background: ${codeBg}; border: 1px solid ${borderColor}; border-radius: 6px;">
<div style="color: ${subColor}; font-size: 12px; margin-bottom: 6px; font-family: monospace;">$ cat article.md</div>
<h1 style="font-size: 20px; font-weight: 700; color: ${accent}; margin: 0; line-height: 1.4; font-family: monospace;">&gt; ${titleText}</h1>
</div>`;
  } else if (style === 'brutalist') {
    return `
<div style="margin: 36px 0 24px 0; text-align: center;">
<div style="display: inline-block; background: ${accentBg}; border: 2.5px solid #000000; box-shadow: 4px 4px 0 #000000; padding: 10px 22px;">
<h1 style="font-size: 21px; font-weight: 800; color: #000000; margin: 0; letter-spacing: 1px;">${titleText}</h1>
</div></div>`;
  } else {
    // 默认：下划粗线 (underline)
    return `
<h1 style="font-size: 23px; font-weight: 800; color: ${titleColor}; line-height: 1.4; margin: 36px 0 22px 0; text-align: center; letter-spacing: 0.5px;">
<span style="border-bottom: 3px solid ${accent}; padding-bottom: 6px;">${titleText}</span>
</h1>`;
  }
}

export function renderH2(h2Text, theme) {
  const style = theme.h2_style || theme.styles?.h2 || 'left_bar';
  const accent = theme.accent;
  const accentBg = theme.accent_bg;
  const borderColor = theme.border_color;
  const textColor = theme.text_color;
  const pageBg = theme.page_bg || '#ffffff';
  const isDark = ['#0b0f19', '#0f172a', '#18181b', '#09090b'].includes(pageBg);
  const headingColor = isDark ? '#f8fafc' : '#18181b';

  if (style === 'pill_badge') {
    return `
<div style="margin: 34px 0 16px 0;">
<span style="display: inline-block; background: ${accent}; color: #ffffff; font-size: 16px; font-weight: 700; padding: 5px 15px; border-radius: 20px; letter-spacing: 0.5px;">
${h2Text}
</span></div>`;
  } else if (style === 'bubble_bg') {
    return `
<div style="margin: 34px 0 16px 0;">
<span style="display: inline-block; background: ${accentBg}; color: ${accent}; font-size: 17px; font-weight: 700; padding: 6px 14px; border-radius: 6px; border-left: 3px solid ${accent};">
${h2Text}
</span></div>`;
  } else if (style === 'serif_badge') {
    return `
<h2 style="font-size: 18.5px; font-weight: 700; color: ${accent}; margin: 34px 0 16px 0; padding-bottom: 6px; border-bottom: 1px solid ${borderColor}; line-height: 1.4; letter-spacing: 0.5px;">
<span style="color: ${accent}; margin-right: 6px; font-family: Georgia, serif;">§</span>${h2Text}
</h2>`;
  } else if (style === 'terminal_prompt') {
    return `
<div style="margin: 32px 0 16px 0; font-family: monospace;">
<span style="color: ${accent}; font-weight: 700; font-size: 18px; margin-right: 8px;">//</span>
<h2 style="display: inline; font-size: 17.5px; font-weight: 700; color: ${textColor}; margin: 0; font-family: monospace;">${h2Text}</h2>
</div>`;
  } else if (style === 'brutalist_box') {
    return `
<div style="margin: 34px 0 16px 0; display: inline-block; background: ${accentBg}; border: 2px solid #000000; box-shadow: 3px 3px 0 #000000; padding: 5px 14px;">
<h2 style="font-size: 17px; font-weight: 800; color: #000000; margin: 0;">${h2Text}</h2>
</div>`;
  } else if (style === 'bottom_line') {
    return `
<h2 style="font-size: 18.5px; font-weight: 700; color: ${headingColor}; margin: 34px 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid ${accent}; line-height: 1.4;">
${h2Text}
</h2>`;
  } else {
    // 默认：左侧 4px 竖条
    return `
<h2 style="font-size: 19px; font-weight: 700; color: ${headingColor}; margin: 34px 0 16px 0; padding-left: 12px; border-left: 4px solid ${accent}; line-height: 1.4;">
${h2Text}
</h2>`;
  }
}

export function renderH3(h3Text, theme) {
  const style = theme.h3_style || theme.styles?.h3 || 'diamond';
  const accent = theme.accent;
  const accentBg = theme.accent_bg;
  const subColor = theme.sub_color;
  const pageBg = theme.page_bg || '#ffffff';
  const isDark = ['#0b0f19', '#0f172a', '#18181b', '#09090b'].includes(pageBg);
  const headingColor = isDark ? '#f8fafc' : '#18181b';

  if (style === 'circle_badge') {
    return `
<h3 style="font-size: 16.5px; font-weight: 600; color: ${accent}; margin: 24px 0 12px 0; line-height: 1.4;">
<span style="display: inline-block; width: 8px; height: 8px; background: ${accent}; border-radius: 2px; margin-right: 8px; vertical-align: middle;"></span>${h3Text}
</h3>`;
  } else if (style === 'highlight_bg') {
    return `
<h3 style="font-size: 16.5px; font-weight: 600; color: ${headingColor}; margin: 24px 0 12px 0; line-height: 1.4;">
<span style="background: linear-gradient(to top, ${accentBg} 45%, transparent 45%); padding: 1px 4px;">${h3Text}</span>
</h3>`;
  } else if (style === 'slash') {
    return `
<h3 style="font-size: 16px; font-weight: 600; color: ${accent}; margin: 24px 0 12px 0; line-height: 1.4; font-family: monospace;">
<span style="color: ${subColor}; margin-right: 6px;">##</span>${h3Text}
</h3>`;
  } else {
    // 默认：菱形星号 ✦
    return `
<h3 style="font-size: 16.5px; font-weight: 600; color: ${accent}; margin: 24px 0 12px 0; line-height: 1.4;">
<span style="margin-right: 6px;">✦</span>${h3Text}
</h3>`;
  }
}

export function renderQuote(innerContent, theme) {
  const style = theme.quote_style || theme.styles?.quote || 'left_stripe';
  const accent = theme.accent;
  const quoteBg = theme.quote_bg;
  const borderColor = theme.border_color;
  const textColor = theme.text_color;
  const subColor = theme.sub_color;

  if (style === 'elegant_quote') {
    return `
<blockquote style="margin: 24px 0; padding: 16px 20px; background: ${quoteBg}; border-top: 1px solid ${borderColor}; border-bottom: 1px solid ${borderColor}; color: ${textColor}; font-size: 14.5px; position: relative;">
<div style="font-size: 28px; color: ${accent}; line-height: 1; margin-bottom: 4px; font-family: Georgia, serif;">“</div>
${innerContent}
<div style="font-size: 28px; color: ${accent}; line-height: 1; text-align: right; margin-top: 4px; font-family: Georgia, serif;">”</div>
</blockquote>`;
  } else if (style === 'bubble_card') {
    return `
<blockquote style="margin: 22px 0; padding: 16px 18px; background: ${quoteBg}; border: 1px solid ${borderColor}; border-radius: 10px; color: ${textColor}; font-size: 14.5px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
${innerContent}
</blockquote>`;
  } else if (style === 'paper_memo') {
    return `
<div style="margin: 24px 0; background: ${quoteBg}; border: 1px solid ${borderColor}; border-left: 4px solid ${accent}; border-radius: 4px; padding: 14px 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); color: ${textColor}; font-size: 14.5px;">
<div style="font-size: 11px; font-weight: 700; color: ${accent}; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">NOTE // 便签</div>
${innerContent}
</div>`;
  } else if (style === 'terminal_box') {
    return `
<div style="margin: 22px 0; padding: 12px 16px; background: ${quoteBg}; border-left: 3px solid ${accent}; border: 1px solid ${borderColor}; border-radius: 4px; font-family: monospace; font-size: 13.5px; color: ${textColor};">
<div style="color: ${subColor}; font-size: 11px; margin-bottom: 6px;">[OUTPUT / 回显]</div>
${innerContent}
</div>`;
  } else if (style === 'brutalist') {
    return `
<blockquote style="margin: 24px 0; padding: 14px 16px; background: ${quoteBg}; border: 2px solid #000000; box-shadow: 3px 3px 0 #000000; color: #000000; font-size: 14.5px; font-weight: 500;">
${innerContent}
</blockquote>`;
  } else {
    // 默认：经典左侧竖条
    return `
<blockquote style="margin: 22px 0; padding: 14px 18px; background: ${quoteBg}; border-left: 4px solid ${accent}; color: ${textColor}; font-size: 14.5px; border-radius: 0 8px 8px 0; line-height: 1.75;">
${innerContent}
</blockquote>`;
  }
}

export function renderCode(rawCode, codeLang, theme) {
  const style = theme.code_style || theme.styles?.code || 'mac_dark';
  const codeBg = theme.code_bg;
  const codeText = theme.code_text || '#e4e4e7';
  const accent = theme.accent;
  const borderColor = theme.border_color;
  const subColor = theme.sub_color;
  const highlighted = highlightCode(rawCode, codeLang);

  if (style === 'terminal') {
    const topBar = `
<div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 12px; background: #020617; border-bottom: 1px solid ${borderColor}; font-family: monospace; font-size: 11.5px; color: ${subColor};">
<span>term: ${codeLang || 'bash'}</span>
<span style="color: ${accent};">● RUNNING</span>
</div>`;
    return `
<div style="margin: 22px 0; border-radius: 6px; overflow: hidden; border: 1px solid ${borderColor}; box-shadow: 0 4px 14px rgba(0,0,0,0.15);">
${topBar}
<pre style="margin: 0; padding: 14px 16px; background: ${codeBg}; color: ${codeText}; font-size: 13.5px; line-height: 1.6; overflow-x: auto; font-family: Consolas, Monaco, monospace;"><code>${highlighted}</code></pre>
</div>`;
  } else if (style === 'clean_flat') {
    return `
<div style="margin: 22px 0; border-radius: 8px; overflow: hidden; border: 1px solid ${borderColor};">
<pre style="margin: 0; padding: 14px 16px; background: ${codeBg}; color: ${codeText}; font-size: 13.5px; line-height: 1.6; overflow-x: auto; font-family: Consolas, Monaco, monospace;"><code>${highlighted}</code></pre>
</div>`;
  } else {
    // 默认：Mac 三色小圆点
    const macDots = `
<div style="display: flex; align-items: center; padding: 8px 12px; background: #27272a; border-top-left-radius: 8px; border-top-right-radius: 8px; border-bottom: 1px solid #3f3f46;">
<span style="width: 10px; height: 10px; border-radius: 50%; background: #ef4444; display: inline-block; margin-right: 6px;"></span>
<span style="width: 10px; height: 10px; border-radius: 50%; background: #f59e0b; display: inline-block; margin-right: 6px;"></span>
<span style="width: 10px; height: 10px; border-radius: 50%; background: #10b981; display: inline-block; margin-right: 10px;"></span>
<span style="color: #a1a1aa; font-size: 12px; font-family: monospace;">${codeLang || 'code'}</span>
</div>`;
    return `
<div style="margin: 22px 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.08);">
${macDots}
<pre style="margin: 0; padding: 14px 16px; background: ${codeBg}; color: ${codeText}; font-size: 13.5px; line-height: 1.6; overflow-x: auto; font-family: Consolas, Monaco, monospace;"><code>${highlighted}</code></pre>
</div>`;
  }
}

export function renderTable(header, rows, theme) {
  const style = theme.table_style || theme.styles?.table || 'zebra';
  const accent = theme.accent;
  const accentBg = theme.accent_bg;
  const borderColor = theme.border_color;
  const textColor = theme.text_color;
  const pageBg = theme.page_bg || '#ffffff';
  const isDark = ['#0b0f19', '#0f172a', '#18181b', '#09090b'].includes(pageBg);
  const tdBgAlt = isDark ? '#1e293b' : '#fafafa';
  const tdBg = isDark ? '#0f172a' : '#ffffff';

  if (style === 'three_line') {
    let tableHtml = `
<div style="overflow-x: auto; margin: 24px 0;">
<table style="width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; border-top: 2px solid ${accent}; border-bottom: 2px solid ${accent}; background: transparent;">`;
    if (header && header.length > 0) {
      tableHtml += `<thead><tr>`;
      for (const h of header) {
        tableHtml += `<th style="padding: 10px 14px; font-weight: 700; color: ${accent}; border-bottom: 1px solid ${borderColor};">${h}</th>`;
      }
      tableHtml += `</tr></thead>`;
    }
    tableHtml += `<tbody>`;
    for (const row of rows) {
      tableHtml += `<tr style="border-bottom: 1px dashed ${borderColor};">`;
      for (const c of row) {
        const cFmt = formatInline(c, accent, '12.5px');
        tableHtml += `<td style="padding: 10px 14px; color: ${textColor}; line-height: 1.5;">${cFmt}</td>`;
      }
      tableHtml += `</tr>`;
    }
    tableHtml += `</tbody></table></div>`;
    return tableHtml;
  } else if (style === 'grid') {
    let tableHtml = `
<div style="overflow-x: auto; margin: 24px 0;">
<table style="width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; border: 2px solid ${borderColor}; background: ${tdBg};">`;
    if (header && header.length > 0) {
      tableHtml += `<thead><tr style="background: ${accentBg};">`;
      for (const h of header) {
        tableHtml += `<th style="padding: 10px 14px; font-weight: 700; color: ${accent}; border: 1px solid ${borderColor};">${h}</th>`;
      }
      tableHtml += `</tr></thead>`;
    }
    tableHtml += `<tbody>`;
    for (const row of rows) {
      tableHtml += `<tr>`;
      for (const c of row) {
        const cFmt = formatInline(c, accent, '12.5px');
        tableHtml += `<td style="padding: 10px 14px; color: ${textColor}; line-height: 1.5; border: 1px solid ${borderColor};">${cFmt}</td>`;
      }
      tableHtml += `</tr>`;
    }
    tableHtml += `</tbody></table></div>`;
    return tableHtml;
  } else {
    // 默认：现代斑马纹 (zebra)
    let tableHtml = `
<div style="overflow-x: auto; margin: 24px 0;">
<table style="width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; background: ${tdBg}; border-radius: 8px; overflow: hidden; border: 1px solid ${borderColor};">`;
    if (header && header.length > 0) {
      tableHtml += `<thead><tr style="background: ${accentBg};">`;
      for (const h of header) {
        tableHtml += `<th style="padding: 11px 14px; font-weight: 600; color: ${accent}; border-bottom: 2px solid ${borderColor};">${h}</th>`;
      }
      tableHtml += `</tr></thead>`;
    }
    tableHtml += `<tbody>`;
    for (let rIdx = 0; rIdx < rows.length; rIdx++) {
      const row = rows[rIdx];
      const bg = rIdx % 2 === 1 ? tdBgAlt : tdBg;
      tableHtml += `<tr style="background: ${bg}; border-bottom: 1px solid ${borderColor};">`;
      for (const c of row) {
        const cFmt = formatInline(c, accent, '12.5px');
        tableHtml += `<td style="padding: 10px 14px; color: ${textColor}; line-height: 1.5;">${cFmt}</td>`;
      }
      tableHtml += `</tr>`;
    }
    tableHtml += `</tbody></table></div>`;
    return tableHtml;
  }
}

export function renderListItem(itemText, theme) {
  const style = theme.list_style || theme.styles?.list || 'bullet';
  const accent = theme.accent;
  const textColor = theme.text_color;

  let bulletSymbol = '•';
  if (style === 'diamond') bulletSymbol = '◆';
  else if (style === 'square') bulletSymbol = '■';
  else if (style === 'arrow') bulletSymbol = '▸';

  return `
<section style="display: flex; align-items: flex-start; margin-bottom: 8px; line-height: 1.75; font-size: 15.5px; color: ${textColor};">
<span style="color: ${accent}; margin-right: 8px; font-size: 15px; line-height: 1.75;">${bulletSymbol}</span>
<span style="flex: 1;">${itemText}</span>
</section>`;
}

export function renderHr(theme) {
  const style = theme.hr_style || theme.styles?.hr || 'line';
  const accent = theme.accent;
  const borderColor = theme.border_color;
  const subColor = theme.sub_color;

  if (style === 'gradient') {
    return `<div style="height: 1px; background: linear-gradient(to right, transparent, ${accent}, transparent); margin: 34px auto; width: 85%;"></div>`;
  } else if (style === 'asterisk') {
    return `<div style="text-align: center; color: ${accent}; font-size: 14px; letter-spacing: 8px; margin: 32px 0;">✻  ✻  ✻</div>`;
  } else if (style === 'terminal_dash') {
    return `<div style="text-align: center; color: ${subColor}; font-family: monospace; font-size: 12px; letter-spacing: 2px; margin: 32px 0;">----------------------------------------</div>`;
  } else {
    return `<hr style="border: 0; height: 1px; background: ${borderColor}; margin: 32px auto; width: 85%;" />`;
  }
}

export function renderContainer(bodyHtml, theme) {
  const style = theme.container_style || theme.styles?.container || 'clean';
  const pageBg = theme.page_bg || '#ffffff';
  const textColor = theme.text_color;
  const borderColor = theme.border_color;
  const fontFamily =
    theme.typography?.font_family ||
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";

  const baseStyle = `max-width: 677px; margin: 0 auto; box-sizing: border-box; font-family: ${fontFamily}; background: ${pageBg}; color: ${textColor};`;

  let containerStyle = `${baseStyle} padding: 14px 8px;`;

  if (style === 'paper') {
    containerStyle = `${baseStyle} padding: 24px 16px; border: 1px solid ${borderColor}; border-radius: 4px; box-shadow: 0 2px 12px rgba(0,0,0,0.03);`;
  } else if (style === 'dark') {
    containerStyle = `${baseStyle} padding: 20px 14px; border: 1px solid ${borderColor}; border-radius: 8px;`;
  } else if (style === 'card') {
    containerStyle = `${baseStyle} padding: 24px 16px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.05);`;
  } else if (style === 'memo') {
    containerStyle = `${baseStyle} padding: 22px 14px; border-radius: 10px; border: 1px dashed ${borderColor};`;
  } else if (style === 'brutalist') {
    containerStyle = `${baseStyle} padding: 20px 14px; border: 2.5px solid #000000; box-shadow: 5px 5px 0 #000000;`;
  }

  return `<div style="${containerStyle}">\n${bodyHtml}\n</div>`;
}

// ==============================================================================
// Markdown 解析主管道 (Parser Pipeline)
// ==============================================================================

export function markdownToWechatHtml(mdText, themeName = DEFAULT_THEME_ID, customOverride = null, renderOptions = {}) {
  const theme = getTheme(themeName, customOverride);
  const accent = theme.accent;
  const textColor = theme.text_color;
  const subColor = theme.sub_color;
  const borderColor = theme.border_color || 'rgba(0, 0, 0, 0.1)';

  const typography = theme.typography || {};
  const fontSizeBase = renderOptions.fontSize || typography.font_size_base || '15.5px';
  const lineHeightBase = renderOptions.lineHeight || typography.line_height_base || '1.8';
  const letterSpacing = renderOptions.letterSpacing || typography.letter_spacing || '0.4px';
  const paragraphIndent = typography.paragraph_indent || false;
  const indentCss = paragraphIndent ? 'text-indent: 2em; ' : '';

  // 微信公众号超链接自动转文末脚注机制
  const linkToFootnote = renderOptions.linkToFootnote !== false; // 默认开启
  const footnotes = linkToFootnote ? [] : null;

  const lines = mdText.split('\n');
  const htmlParts = [];

  let inCodeBlock = false;
  let codeLang = '';
  let codeLines = [];

  let inTable = false;
  let tableLines = [];

  function flushTable() {
    if (!tableLines.length) return '';
    let header = [];
    const rows = [];
    for (let i = 0; i < tableLines.length; i++) {
      const line = tableLines[i];
      const trimmed = line.trim().replace(/^\||\|$/g, '');
      const cells = trimmed.split('|').map((c) => c.trim());
      if (i === 0) {
        header = cells;
      } else if (i === 1 && cells.every((c) => /^[-:\s]+$/.test(c))) {
        continue;
      } else {
        rows.push(cells);
      }
    }
    const rendered = renderTable(header, rows, theme);
    tableLines = [];
    inTable = false;
    return rendered;
  }

  function flushCode() {
    let rawCode = codeLines.join('\n');
    rawCode = rawCode
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    const rendered = renderCode(rawCode, codeLang, theme);
    codeLines = [];
    inCodeBlock = false;
    return rendered;
  }

  let idx = 0;
  while (idx < lines.length) {
    const line = lines[idx];
    const stripped = line.trim();

    // 1. 代码块
    if (stripped.startsWith('```')) {
      if (inCodeBlock) {
        htmlParts.push(flushCode());
      } else {
        if (inTable) htmlParts.push(flushTable());
        inCodeBlock = true;
        codeLang = stripped.slice(3).trim();
        codeLines = [];
      }
      idx++;
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      idx++;
      continue;
    }

    // 2. 表格
    if (stripped.startsWith('|') && stripped.endsWith('|')) {
      inTable = true;
      tableLines.push(stripped);
      idx++;
      continue;
    } else if (inTable) {
      htmlParts.push(flushTable());
    }

    // 3. 空行
    if (!stripped) {
      idx++;
      continue;
    }

    // 4. 分割线
    if (['---', '***', '___'].includes(stripped)) {
      htmlParts.push(renderHr(theme));
      idx++;
      continue;
    }

    // 5. 一级标题
    if (stripped.startsWith('# ')) {
      const titleText = stripped
        .slice(2)
        .trim()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
      htmlParts.push(renderH1(titleText, theme));
      idx++;
      continue;
    }

    // 6. 二级标题
    if (stripped.startsWith('## ')) {
      const h2Text = stripped
        .slice(3)
        .trim()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
      htmlParts.push(renderH2(h2Text, theme));
      idx++;
      continue;
    }

    // 7. 三级标题
    if (stripped.startsWith('### ')) {
      const h3Text = stripped
        .slice(4)
        .trim()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
      htmlParts.push(renderH3(h3Text, theme));
      idx++;
      continue;
    }

    // 8. 连续引用块聚合处理 (消除微信公众号碎片化孤立小框)
    if (stripped.startsWith('>')) {
      const quoteLines = [];
      while (idx < lines.length && lines[idx].trim().startsWith('>')) {
        let qLine = lines[idx].trim();
        if (qLine.startsWith('> ')) {
          qLine = qLine.slice(2).trim();
        } else if (qLine.startsWith('>')) {
          qLine = qLine.slice(1).trim();
        }
        quoteLines.push(qLine);
        idx++;
      }

      const formattedItems = [];
      for (const qLine of quoteLines) {
        if (!qLine) {
          formattedItems.push('<div style="height: 6px;"></div>');
          continue;
        }
        const qFmt = formatInline(qLine, accent, '13px', footnotes);
        formattedItems.push(`<div style="margin: 4px 0; line-height: 1.75;">${qFmt}</div>`);
      }

      const innerContent = formattedItems.join('\n');
      htmlParts.push(renderQuote(innerContent, theme));
      continue;
    }

    // 9. 列表项
    if (stripped.startsWith('- ') || stripped.startsWith('* ')) {
      const itemText = stripped.slice(2).trim();
      const itemFmt = formatInline(itemText, accent, '13.5px', footnotes);
      htmlParts.push(renderListItem(itemFmt, theme));
      idx++;
      continue;
    }

    // 10. 图片格式 ![alt](url)
    const imgMatch = stripped.match(/^!\[(.*?)\]\((.*?)\)$/);
    if (imgMatch) {
      const alt = imgMatch[1];
      const src = imgMatch[2];
      const caption = alt
        ? `<div style="text-align: center; color: ${subColor}; font-size: 13px; margin-top: 6px; font-style: italic;">${alt}</div>`
        : '';
      htmlParts.push(`
<div style="margin: 24px 0; text-align: center;">
<img src="${src}" alt="${alt}" style="max-width: 96%; height: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); display: inline-block;" />
${caption}
</div>`);
      idx++;
      continue;
    }

    // 11. 显式图注 (*▲ 图：...*)
    const captionMatch = stripped.match(/^\*▲ 图：(.+?)\*$/);
    if (captionMatch) {
      const capText = captionMatch[1];
      htmlParts.push(`
<div style="text-align: center; color: ${subColor}; font-size: 13px; margin: -16px 0 20px 0; font-style: italic;">
▲ 图：${capText}
</div>`);
      idx++;
      continue;
    }

    // 12. 正文段落
    const pText = formatInline(stripped, accent, '13.5px', footnotes);
    htmlParts.push(`
<p style="font-size: ${fontSizeBase}; line-height: ${lineHeightBase}; color: ${textColor}; margin: 18px 0; letter-spacing: ${letterSpacing}; ${indentCss}text-align: justify;">
${pText}
</p>`);
    idx++;
  }

  if (inTable) htmlParts.push(flushTable());
  if (inCodeBlock) htmlParts.push(flushCode());

  // 注入文末参考资料与引用外链
  if (footnotes && footnotes.length > 0) {
    const listItems = footnotes.map((fn, fIndex) => {
      return `<li style="margin: 5px 0; word-break: break-all; list-style-type: none;"><span style="color: ${accent}; font-weight: 700; margin-right: 6px;">[${fIndex + 1}]</span><span style="color: ${textColor}; font-weight: 500;">${fn.label}</span>: <span style="color: ${subColor}; font-family: monospace; font-size: 11.5px;">${fn.url}</span></li>`;
    }).join('\n');

    htmlParts.push(`
<section style="margin-top: 36px; padding: 16px 18px; border-radius: 8px; background: rgba(0,0,0,0.02); border-left: 3px solid ${accent}; border-top: 1px solid ${borderColor};">
<div style="font-size: 13.5px; font-weight: 700; color: ${accent}; margin-bottom: 10px; display: flex; align-items: center;">
<span>参考链接与资料引用</span>
</div>
<ul style="margin: 0; padding-left: 0; font-size: 12px; color: ${subColor}; line-height: 1.8;">
${listItems}
</ul>
</section>`);
  }

  const finalBody = htmlParts.join('\n');
  return renderContainer(finalBody, theme);
}

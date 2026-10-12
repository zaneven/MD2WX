/**
 * MD2WX 前端纯 JavaScript Markdown -> 微信内联 HTML 解析与渲染引擎
 * 1:1 复刻 Python 端核心排版与组件风格矩阵
 */
import { getTheme, DEFAULT_THEME_ID, isDarkTheme } from './themes.js';
import { highlightCode } from './highlighter.js';
import { renderWechatArticleHeaderCover, extractCoverMeta } from './cover.js';

/**
 * HTML 转义（普通文本通道统一使用，防止标签注入与微信粘贴丢字）
 */
export function escapeHtml(str) {
  if (str === undefined || str === null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * 解析并剥离 Markdown 顶部的 YAML Frontmatter
 * 仅当首行严格为 '---' 且解析出至少一条元数据时才认定为 Frontmatter，
 * 避免正文以 --- 分隔线开头被误判；统一换行符避免 CRLF 文档解析异常
 */
export function parseFrontmatter(text) {
  const meta = {};
  const normalized = String(text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  let body = normalized;

  if (normalized.startsWith('---\n') || normalized === '---') {
    const closing = normalized.slice(4).match(/^---\s*$/m);
    if (closing) {
      const fmText = normalized.slice(4, 4 + closing.index).trim();
      const candidateMeta = {};

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
            candidateMeta[k] = tags;
          } else {
            candidateMeta[k] = v;
          }
        }
      }

      // 只有解析出至少一条元数据才认定为 Frontmatter，否则按普通正文处理
      if (Object.keys(candidateMeta).length > 0) {
        Object.assign(meta, candidateMeta);
        body = normalized.slice(4 + closing.index + closing[0].length).replace(/^\n+/, '');
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

// 微信官方图片 CDN 域名 (外链图片检测白名单，之外的图片会被微信编辑器封禁)
export const WECHAT_CDN_HOSTS = ['mmbiz.qpic.cn', 'mmbiz.wpimg.cn'];

/**
 * 收集正文 Markdown 中的外链图片 URL (http/https 且非微信官方 CDN)。
 * 跳过代码围栏段避免误报示例代码中的链接；按出现顺序去重。
 */
export function collectExternalImageUrls(mdText) {
  const urls = [];
  const seen = new Set();
  const segments = String(mdText || '').split(/(```[\s\S]*?```|~~~[\s\S]*?~~~)/);
  for (const seg of segments) {
    if (seg.startsWith('```') || seg.startsWith('~~~')) continue;
    const imgRe = /!\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)/g;
    let m;
    while ((m = imgRe.exec(seg)) !== null) {
      let src = m[1];
      try {
        src = decodeURIComponent(src);
      } catch {
        // URL 编码异常时按原文处理
      }
      if (!/^https?:\/\//i.test(src)) continue;
      let host = '';
      try {
        host = new URL(src).hostname.toLowerCase();
      } catch {
        continue;
      }
      if (WECHAT_CDN_HOSTS.some((h) => host.includes(h))) continue;
      if (!seen.has(src)) {
        seen.add(src);
        urls.push(src);
      }
    }
  }
  return urls;
}

/**
 * 6/3 位十六进制颜色转 rgba() 字符串；非法输入原样返回
 */
function hexToRgba(hexColor, alpha) {
  let h = String(hexColor || '').replace(/^#/, '');
  if (h.length === 3) h = h.split('').map((c) => c + c).join('');
  if (h.length !== 6) return hexColor;
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  if ([r, g, b].some((n) => Number.isNaN(n))) return hexColor;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * 转义普通文本中的 HTML 敏感字符，但放过已是 HTML 实体的 &name; / &#123; / &#xAB;，
 * 避免用户手写的实体被二次转义后按字面显示
 */
function entitySafeEscape(seg) {
  return String(seg)
    .replace(/&(?!(?:[a-zA-Z][a-zA-Z0-9]*|#[0-9]+|#x[0-9a-fA-F]+);)/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// 允许放行的微信安全行内 HTML 标签（仅无属性形态；其余标签一律转义显示）
const HTML_WHITELIST_RE = /&lt;(\/?)\s*(br|b|strong|em|u|s|sub|sup|mark)\s*(\/?)\s*&gt;/gi;

function unescapeWhitelistHtml(text) {
  return text.replace(HTML_WHITELIST_RE, (_, c1, tag, c2) => `<${c1}${tag.toLowerCase()}${c2}>`);
}

/**
 * 统一解析行内 Markdown 语法 (CommonMark + GFM + 常用扩展)：
 * 1. 保护行内代码（含双反引号）与反斜杠转义字符；
 * 2. 行内/参考式图片、尖括号自动链接、超链接、参考式链接、脚注引用、裸 URL；
 * 3. 实体安全转义 + 微信安全 HTML 白名单放行；
 * 4. 加粗（** 与 __）、斜体（* 与 _）、删除线、==高亮==；
 * 5. 彻底递归还原所有 Tokens，杜绝控制字符 \x00 导致的截断。
 *
 * footnotes: 文末脚注收集器 (null = URL 渲染为锚点而非脚注)；
 * urlFootnotes: false 时 URL 一律渲染锚点 (link_to_footnote=false 场景)；
 * refDefs: 参考式链接定义表 (预扫描产出，label 小写为键)；
 * footnoteDefs: [^id] 脚注定义表 (预扫描产出)；
 * accentBg: ==高亮== 背景色 (缺省时由 accent 派生半透明色)。
 */
export function formatInline(
  text,
  accent,
  codeFontSize = '13.5px',
  footnotes = null,
  urlFootnotes = true,
  refDefs = null,
  footnoteDefs = null,
  accentBg = null
) {
  const tokens = {};
  let tokenIdx = 0;

  // 脚注编号统一分配 (URL 脚注与 [^id] 文本脚注共用一个有序列表)
  const footnoteStore = footnotes || [];

  const saveToken = (prefix, value) => {
    const k = `@@${prefix}_${tokenIdx++}@@`;
    tokens[k] = value;
    return k;
  };

  const footnoteSup = (fNum, labelHtml = '') => {
    const labelPart = labelHtml
      ? `<span style="color: ${accent}; font-weight: 500;">${labelHtml}</span>`
      : '';
    return `${labelPart}<sup style="font-size: 11px; color: ${accent}; margin-left: 2px; font-weight: bold; vertical-align: super;">[${fNum}]</sup>`;
  };

  const registerUrlFootnote = (url, label) => {
    const fIndex = footnoteStore.findIndex((f) => f.url === url);
    if (fIndex === -1) {
      footnoteStore.push({ label, url, kind: 'url' });
      return footnoteStore.length;
    }
    return fIndex + 1;
  };

  // 1. 保护并转义行内代码 `...` 与 ``...``（双反引号可内含单反引号，内容首尾各剥离一个空格）
  text = text.replace(/(`+)((?:(?!\1)[\s\S])+?)\1/g, (_, __, raw) => {
    let content = raw;
    if (content.length >= 2 && content.startsWith(' ') && content.endsWith(' ')) {
      content = content.slice(1, -1);
    }
    return saveToken(
      'MDCODE',
      `<code style="background: rgba(0,0,0,0.06); padding: 2px 6px; border-radius: 4px; font-size: ${codeFontSize}; color: ${accent}; font-family: monospace;">${escapeHtml(content)}</code>`
    );
  });

  // 1.5 反斜杠转义：\x 的下一字符按字面输出，且不参与后续任何格式化
  text = text.replace(/\\([!"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~])/g, (_, ch) =>
    saveToken('MDESC', escapeHtml(ch))
  );

  // 2. 图片：参考式 ![alt][ref] 与行内 ![alt](src "title")
  //    必须先于链接解析，否则 [alt](src) 部分会先被链接正则吞掉
  const inlineImgHtml = (alt, src) =>
    `<img src="${String(src).replace(/"/g, '&quot;')}" alt="${escapeHtml(alt)}" style="max-width: 96%; height: auto; border-radius: 8px; display: inline-block;" />`;

  text = text.replace(/!\[([^\]]*)\]\[([^\]]*)\]/g, (match, alt, ref) => {
    if (!refDefs) return match;
    const d = refDefs[ref.trim().toLowerCase()] || refDefs[alt.trim().toLowerCase()];
    if (!d) return match;
    return saveToken('MDIMG', inlineImgHtml(alt, d.url));
  });

  text = text.replace(/!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)/g, (_, alt, src) =>
    saveToken('MDIMG', inlineImgHtml(alt, src))
  );

  // 2.2 尖括号自动链接：<https://...> 剥尖括号交给裸 URL 步骤；<mail@...> 转脚注/锚点
  text = text.replace(/<(https?:\/\/[^\s<>]+)>/g, '$1');

  text = text.replace(/<([\w.+-]+@[\w-]+\.[\w.-]+)>/g, (_, addr) => {
    const url = `mailto:${addr}`;
    if (footnotes && urlFootnotes) {
      const fNum = registerUrlFootnote(url, addr);
      return saveToken('MDMAIL', footnoteSup(fNum, addr));
    }
    return saveToken('MDMAIL', `<a href="${url}" style="color: ${accent}; text-decoration: none; border-bottom: 1px dashed ${accent};">${addr}</a>`);
  });

  // 3. 保护超链接 [...](...)，若开启脚注且非锚点链接则生成微信文末参考脚注
  const saveLink = (label, url) => {
    let escLabel = escapeHtml(label);

    // 展开嵌套的 code token
    for (const [tk, tv] of Object.entries(tokens)) {
      if (escLabel.includes(tk)) {
        escLabel = escLabel.split(tk).join(tv);
      }
    }

    // URL 转义后输出，防止属性破坏
    let escUrl = String(url).replace(/"/g, '&quot;');

    // 本地 file 协议转换为安全链接
    if (escUrl.startsWith('file:///')) {
      if (escUrl.includes('MD2WX')) {
        escUrl = `https://github.com/zaneven/MD2WX/blob/main/${escUrl.split('MD2WX/')[1]}`;
      } else {
        escUrl = 'https://github.com/zaneven/MD2WX';
      }
    }

    if (footnotes && urlFootnotes && !escUrl.startsWith('#')) {
      const fNum = registerUrlFootnote(escUrl, escLabel);
      return saveToken('MDLINK', footnoteSup(fNum, escLabel));
    }
    return saveToken('MDLINK', `<a href="${escUrl}" style="color: ${accent}; text-decoration: none; border-bottom: 1px dashed ${accent};">${escLabel}</a>`);
  };

  text = text.replace(/\[(.*?)\]\((.*?)\)/g, (_, label, url) => saveLink(label, url));

  // 3.2 参考式链接 [text][ref] / 折叠式 [ref]（定义由预扫描收集，未解析时保持字面）
  const saveRefLink = (match, label, ref) => {
    if (!refDefs) return match;
    const refId = (ref || label).trim().toLowerCase();
    const d = refDefs[refId];
    if (!d) return match;
    return saveLink(label, d.url);
  };

  text = text.replace(/\[([^\]]+)\]\[([^\]]*)\]/g, saveRefLink);
  text = text.replace(/\[([^\][\s]+)\](?![\(\[])/g, (match, label) => saveRefLink(match, label, label));

  // 3.3 脚注引用 [^id]：编号按首次引用顺序并入文末脚注区 (定义由预扫描收集)
  text = text.replace(/\[\^([^\]]+)\]/g, (match, fid) => {
    if (!footnoteDefs) return match;
    const id = fid.trim().toLowerCase();
    if (!(id in footnoteDefs)) return match;
    const key = `@@FN:${id}@@`;
    const fIndex = footnoteStore.findIndex((f) => f.url === key);
    let fNum;
    if (fIndex === -1) {
      footnoteStore.push({ label: id, url: key, kind: 'text', text: footnoteDefs[id] });
      fNum = footnoteStore.length;
    } else {
      fNum = fIndex + 1;
    }
    return saveToken('MDFN', footnoteSup(fNum));
  });

  // 3.5 自动链接：裸 http(s) URL 与 Markdown 链接同等待遇，自动转文末脚注
  //     (微信不支持外链跳转，遗漏的裸 URL 在正文点击同样会被阻断)
  const autolinkUrlRe = /https?:\/\/[^\s<>()\[\]"']+[^\s<>()\[\]"'.,;:!?]/g;
  text = text.replace(autolinkUrlRe, (url) => {
    if (footnotes && urlFootnotes) {
      const label = url.length <= 60 ? url : url.slice(0, 57) + '...';
      const fNum = registerUrlFootnote(url, label);
      return saveToken('MDURL', footnoteSup(fNum, label));
    }
    const label = url.length <= 60 ? url : url.slice(0, 57) + '...';
    return saveToken('MDURL', `<a href="${url}" style="color: ${accent}; text-decoration: none; border-bottom: 1px dashed ${accent};">${label}</a>`);
  });

  // 4. 对未受 token 保护的普通文本统一转义 HTML (实体安全，防双重转义)，
  //    并放行微信安全白名单行内标签，其余 <tag> 显示为字面文本
  text = text
    .split(/(@@MD[A-Z]+_\d+@@)/)
    .map((seg) => (seg.startsWith('@@MD') ? seg : unescapeWhitelistHtml(entitySafeEscape(seg))))
    .join('');

  // 5. 粗体与斜体 (** 与 __ / * 与 _，下划线形态词边界感知：词内 _ 不触发)
  text = text.replace(/\*\*(?![\*\s])((?:[^*]|\*(?!\*))+?)(?<![\*\s])\*\*/g, '<strong>$1</strong>');
  text = text.replace(/(?<![\w\\])__(?!\s)((?:[^_]|_(?!_))+?)(?<!\s)__(?!\w)/g, '<strong>$1</strong>');
  text = text.replace(/(^|[^*])\*(?![\*\s])([^*\n]+?)(?<![\*\s])\*(?!\*)/g, '$1<em>$2</em>');
  text = text.replace(/(?<![`\w])_(?!\s)([^_\n]+?)(?<!\s)_(?!\w)/g, '<em>$1</em>');

  // 5.5 GFM 删除线 ~text~ / ~~text~~ (del 标签在微信白名单内，内联样式保证不褪色)
  text = text.replace(
    /(~{1,2})(?![\s~])((?:[^~]|~(?!~))+?)(?<![\s~])\1/g,
    `<del style="color: ${accent}; opacity: 0.72;">$2</del>`
  );

  // 5.6 扩展高亮 ==text== (主题色荧光笔效果)
  const markBg = accentBg || hexToRgba(accent, 0.15);
  text = text.replace(
    /==(?!\s)([\s\S]+?)(?<!\s)==/g,
    `<mark style="background: ${markBg}; padding: 1px 3px; border-radius: 3px;">$1</mark>`
  );

  // 6. 彻底还原保护的 tokens (支持嵌套多轮展开)
  let loops = 5;
  while (Object.keys(tokens).some((k) => text.includes(k)) && loops-- > 0) {
    for (const [k, v] of Object.entries(tokens)) {
      if (text.includes(k)) {
        text = text.split(k).join(v);
      }
    }
  }

  // 7. 防御性清除任何控制字符
  text = text.replace(/\x00/g, '');

  return text;
}

const CJK_CHAR_RE = /[一-鿿　-〿＀-￯]/;

function isCjkChar(ch) {
  return !!ch && CJK_CHAR_RE.test(ch);
}

// 列表项标记：- * + 无序，N. / N) 有序
const LIST_ITEM_RE = /^(\s*)([-*+]|\d{1,9}[.)])(\s+(.*))?$/;

/**
 * 段落行合并 (CommonMark 软换行语义)：
 * - 行尾 2+ 空格或单个反斜杠 = 硬换行，插入 @@MDBR_0@@ 占位 (行内解析后还原为 <br />)；
 * - 普通软换行：相邻字符任一侧为 CJK/全角字符时直接拼接，否则以空格拼接。
 */
function joinParagraphLines(buf) {
  const parts = buf.map((raw) => {
    let hard = false;
    let ln = raw;
    if (ln.endsWith('  ')) {
      hard = true;
      ln = ln.replace(/\s+$/, '');
    } else if (ln.endsWith('\\') && !ln.endsWith('\\\\')) {
      hard = true;
      ln = ln.slice(0, -1).replace(/\s+$/, '');
    } else {
      ln = ln.replace(/\s+$/, '');
    }
    return [hard, ln];
  });
  let result = '';
  for (let i = 0; i < parts.length; i++) {
    const [hard, ln] = parts[i];
    if (i === 0) {
      result = ln;
      continue;
    }
    const prevLn = parts[i - 1][1];
    if (parts[i - 1][0]) {
      result += '@@MDBR_0@@' + ln;
      continue;
    }
    const prevCh = prevLn ? prevLn.slice(-1) : '';
    const nextCh = ln.slice(0, 1);
    if (prevCh && nextCh && (isCjkChar(prevCh) || isCjkChar(nextCh))) {
      result += ln;
    } else {
      result += ' ' + ln;
    }
  }
  return result;
}

/**
 * 渲染有序列表项 (保留源文档编号，与无序列表同一 flex 视觉骨架)
 */
function renderOrderedListItem(itemText, number, theme) {
  const accent = theme.accent;
  const textColor = theme.text_color;
  return (
    `<section style="display: flex; align-items: flex-start; margin-bottom: 8px; line-height: 1.75; font-size: 15.5px; color: ${textColor};">` +
    `<span style="color: ${accent}; margin-right: 8px; font-size: 15px; line-height: 1.75; font-weight: 700; min-width: 20px;">${number}.</span>` +
    `<span style="flex: 1;">${itemText}</span>` +
    `</section>`
  );
}

/**
 * 渲染四级小标题 (默认：左侧短竖条 + 缩小字号；主题可用 styles.h4 覆盖)
 */
function renderH4(h4Text, theme) {
  const accent = theme.accent;
  const pageBg = theme.page_bg || '#ffffff';
  const isDark = ['#0b0f19', '#0f172a', '#18181b', '#09090b'].includes(pageBg);
  const headingColor = isDark ? '#f8fafc' : '#18181b';
  return (
    `<section style="margin: 20px 0 10px 0; line-height: 1.4; display: flex; align-items: center;">` +
    `<span style="display: inline-block; width: 3px; height: 14px; background: ${accent}; border-radius: 2px; margin-right: 8px; flex-shrink: 0;"></span>` +
    `<span style="font-size: 15.5px; font-weight: 700; color: ${accent};">${h4Text}</span>` +
    `</section>`
  );
}

/**
 * 渲染五级小标题 (默认：accent 短划前缀)
 */
function renderH5(h5Text, theme) {
  const accent = theme.accent;
  const pageBg = theme.page_bg || '#ffffff';
  const isDark = ['#0b0f19', '#0f172a', '#18181b', '#09090b'].includes(pageBg);
  const headingColor = isDark ? '#f8fafc' : '#18181b';
  return (
    `<section style="margin: 18px 0 8px 0; line-height: 1.4;">` +
    `<span style="color: ${accent}; margin-right: 6px; font-weight: 700;">—</span>` +
    `<span style="font-size: 15px; font-weight: 600; color: ${headingColor};">${h5Text}</span>` +
    `</section>`
  );
}

/**
 * 渲染六级小标题 (默认：弱化的副色小字)
 */
function renderH6(h6Text, theme) {
  const subColor = theme.sub_color;
  return (
    `<section style="margin: 16px 0 8px 0; line-height: 1.4;">` +
    `<span style="font-size: 14px; font-weight: 600; color: ${subColor}; letter-spacing: 0.5px;">${h6Text}</span>` +
    `</section>`
  );
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
  const isDark = isDarkTheme(theme);
  const titleColor = isDark ? '#f8fafc' : '#18181b';

  if (style === 'double_line') {
    return `
<section style="margin: 38px 0 26px 0; text-align: center;">
<section style="border-top: 1px solid ${borderColor}; border-bottom: 1px solid ${borderColor}; padding: 12px 14px; display: inline-block; min-width: 60%;">
<span style="font-size: 22px; font-weight: 700; color: ${accent}; margin: 0; line-height: 1.4; letter-spacing: 1px; display: block;">${titleText}</span>
</section></section>`;
  } else if (style === 'capsule') {
    return `
<section style="margin: 36px 0 24px 0; text-align: center;">
<span style="display: inline-block; background: ${accent}; color: #ffffff; padding: 9px 26px; border-radius: 30px; font-size: 20px; font-weight: 700; letter-spacing: 0.8px; box-shadow: 0 4px 14px rgba(0,0,0,0.12);">
${titleText}
</span></section>`;
  } else if (style === 'terminal') {
    return `
<section style="margin: 36px 0 24px 0; padding: 14px 18px; background: ${codeBg}; border: 1px solid ${borderColor}; border-radius: 6px;">
<div style="color: ${subColor}; font-size: 12px; margin-bottom: 6px; font-family: monospace;">$ cat article.md</div>
<span style="font-size: 20px; font-weight: 700; color: ${accent}; margin: 0; line-height: 1.4; font-family: monospace; display: block;">&gt; ${titleText}</span>
</section>`;
  } else if (style === 'brutalist') {
    return `
<section style="margin: 36px 0 24px 0; text-align: center;">
<section style="display: inline-block; background: ${accentBg}; border: 2.5px solid #000000; box-shadow: 4px 4px 0 #000000; padding: 10px 22px;">
<span style="font-size: 21px; font-weight: 800; color: #000000; margin: 0; letter-spacing: 1px; display: block;">${titleText}</span>
</section></section>`;
  } else {
    // 默认：下划粗线 (underline)
    return `
<section style="text-align: center; margin: 36px 0 22px 0;">
<span style="font-size: 23px; font-weight: 800; color: ${titleColor}; line-height: 1.4; letter-spacing: 0.5px; border-bottom: 3px solid ${accent}; padding-bottom: 6px; display: inline-block;">
${titleText}
</span></section>`;
  }
}

export function renderH2(h2Text, theme) {
  const style = theme.h2_style || theme.styles?.h2 || 'left_bar';
  const accent = theme.accent;
  const accentBg = theme.accent_bg;
  const borderColor = theme.border_color;
  const textColor = theme.text_color;
  const pageBg = theme.page_bg || '#ffffff';
  const isDark = isDarkTheme(theme);
  const headingColor = isDark ? '#f8fafc' : '#18181b';

  if (style === 'pill_badge') {
    return `
<section style="margin: 34px 0 16px 0;">
<span style="display: inline-block; background: ${accent}; color: #ffffff; font-size: 16px; font-weight: 700; padding: 5px 15px; border-radius: 20px; letter-spacing: 0.5px;">
${h2Text}
</span></section>`;
  } else if (style === 'bubble_bg') {
    return `
<section style="margin: 34px 0 16px 0;">
<span style="display: inline-block; background: ${accentBg}; color: ${accent}; font-size: 17px; font-weight: 700; padding: 6px 14px; border-radius: 6px; border-left: 3px solid ${accent};">
${h2Text}
</span></section>`;
  } else if (style === 'serif_badge') {
    return `
<section style="margin: 34px 0 16px 0; padding-bottom: 6px; border-bottom: 1px solid ${borderColor};">
<span style="color: ${accent}; margin-right: 6px; font-family: Georgia, serif; font-size: 18.5px; font-weight: 700;">§</span>
<span style="font-size: 18.5px; font-weight: 700; color: ${accent}; line-height: 1.4; letter-spacing: 0.5px;">${h2Text}</span>
</section>`;
  } else if (style === 'terminal_prompt') {
    return `
<section style="margin: 32px 0 16px 0; font-family: monospace;">
<span style="color: ${accent}; font-weight: 700; font-size: 18px; margin-right: 8px;">//</span>
<span style="display: inline; font-size: 17.5px; font-weight: 700; color: ${textColor}; margin: 0; font-family: monospace;">${h2Text}</span>
</section>`;
  } else if (style === 'brutalist_box') {
    return `
<section style="margin: 34px 0 16px 0; text-align: left;">
<section style="display: inline-block; background: ${accentBg}; border: 2px solid #000000; box-shadow: 3px 3px 0 #000000; padding: 5px 14px;">
<span style="font-size: 17px; font-weight: 800; color: #000000; margin: 0; line-height: 1.4; display: block;">${h2Text}</span>
</section></section>`;
  } else if (style === 'bottom_line') {
    return `
<section style="margin: 34px 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid ${accent};">
<span style="font-size: 18.5px; font-weight: 700; color: ${headingColor}; line-height: 1.4; display: block;">${h2Text}</span>
</section>`;
  } else {
    // 默认：左侧 4px 竖条
    return `
<section style="margin: 34px 0 16px 0; padding-left: 12px; border-left: 4px solid ${accent};">
<span style="font-size: 19px; font-weight: 700; color: ${headingColor}; line-height: 1.4; display: block;">${h2Text}</span>
</section>`;
  }
}

export function renderH3(h3Text, theme) {
  const style = theme.h3_style || theme.styles?.h3 || 'diamond';
  const accent = theme.accent;
  const accentBg = theme.accent_bg;
  const subColor = theme.sub_color;
  const pageBg = theme.page_bg || '#ffffff';
  const isDark = isDarkTheme(theme);
  const headingColor = isDark ? '#f8fafc' : '#18181b';

  if (style === 'circle_badge') {
    return `
<section style="margin: 24px 0 12px 0;">
<span style="display: inline-block; width: 8px; height: 8px; background: ${accent}; border-radius: 2px; margin-right: 8px; vertical-align: middle;"></span>
<span style="font-size: 16.5px; font-weight: 600; color: ${accent}; line-height: 1.4;">${h3Text}</span>
</section>`;
  } else if (style === 'highlight_bg') {
    return `
<section style="margin: 24px 0 12px 0;">
<span style="background: linear-gradient(to top, ${accentBg} 45%, transparent 45%); padding: 1px 4px; font-size: 16.5px; font-weight: 600; color: ${headingColor}; line-height: 1.4;">${h3Text}</span>
</section>`;
  } else if (style === 'slash') {
    return `
<section style="margin: 24px 0 12px 0; font-family: monospace;">
<span style="color: ${subColor}; margin-right: 6px;">##</span>
<span style="font-size: 16px; font-weight: 600; color: ${accent}; line-height: 1.4;">${h3Text}</span>
</section>`;
  } else {
    // 默认：纯 SVG 矢量菱形图标
    return `
<section style="margin: 24px 0 12px 0; line-height: 1.4; display: flex; align-items: center;">
<svg width="14" height="14" viewBox="0 0 24 24" fill="${accent}" style="margin-right: 6px; flex-shrink: 0;"><polygon points="12 2 15 9 22 12 15 15 12 22 9 15 2 12 9 9"/></svg>
<span style="font-size: 16.5px; font-weight: 600; color: ${accent};">${h3Text}</span>
</section>`;
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

/**
 * 将代码块 HTML 的换行结构改为微信自包含式：
 * 换行符 -> <br>，空格 -> &nbsp;，仅处理文本节点，标签与内联样式属性原样保留
 */
function wechatSafeLineStructure(htmlStr) {
  return htmlStr
    .split(/(<[^>]+>)/)
    .map((part) => (part.startsWith('<') ? part : part.replace(/\n/g, '<br>').replace(/ /g, '&nbsp;')))
    .join('');
}

export function renderCode(rawCode, codeLang, theme) {
  const style = theme.code_style || theme.styles?.code || 'mac_dark';
  const codeBg = theme.code_bg;
  const codeText = theme.code_text || '#e4e4e7';
  const accent = theme.accent;
  const borderColor = theme.border_color;
  const subColor = theme.sub_color;
  const highlighted = wechatSafeLineStructure(highlightCode(rawCode, codeLang));

  if (style === 'terminal') {
    const topBar = `
<div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 12px; background: #020617; border-bottom: 1px solid ${borderColor}; font-family: monospace; font-size: 11.5px; color: ${subColor};">
<span>term: ${codeLang || 'bash'}</span>
<span style="color: ${accent};">● RUNNING</span>
</div>`;
    return `
<div style="margin: 22px 0; border-radius: 6px; overflow: hidden; border: 1px solid ${borderColor}; box-shadow: 0 4px 14px rgba(0,0,0,0.15);">
${topBar}
<div style="overflow-x: auto; -webkit-overflow-scrolling: touch; background: ${codeBg}; padding: 14px 16px;"><pre style="margin: 0; background: ${codeBg}; color: ${codeText}; font-size: 13.5px; line-height: 1.6; font-family: 'SF Mono', SFMono-Regular, Menlo, Consolas, 'Liberation Mono', 'Courier New', monospace;"><code>${highlighted}</code></pre></div>
</div>`;
  } else if (style === 'clean_flat') {
    return `
<div style="margin: 22px 0; border-radius: 8px; overflow: hidden; border: 1px solid ${borderColor};">
<div style="overflow-x: auto; -webkit-overflow-scrolling: touch; background: ${codeBg}; padding: 14px 16px;"><pre style="margin: 0; background: ${codeBg}; color: ${codeText}; font-size: 13.5px; line-height: 1.6; font-family: 'SF Mono', SFMono-Regular, Menlo, Consolas, 'Liberation Mono', 'Courier New', monospace;"><code>${highlighted}</code></pre></div>
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
<div style="overflow-x: auto; -webkit-overflow-scrolling: touch; background: ${codeBg}; padding: 14px 16px;"><pre style="margin: 0; background: ${codeBg}; color: ${codeText}; font-size: 13.5px; line-height: 1.6; font-family: 'SF Mono', SFMono-Regular, Menlo, Consolas, 'Liberation Mono', 'Courier New', monospace;"><code>${highlighted}</code></pre></div>
</div>`;
  }
}

export function renderTable(header, rows, theme, aligns = null) {
  const alignList = aligns || [];
  const colAlign = (colIdx) => (colIdx < alignList.length ? alignList[colIdx] : 'left');
  const style = theme.table_style || theme.styles?.table || 'zebra';
  const accent = theme.accent;
  const accentBg = theme.accent_bg;
  const borderColor = theme.border_color;
  const textColor = theme.text_color;
  const pageBg = theme.page_bg || '#ffffff';
  const isDark = isDarkTheme(theme);
  const tdBgAlt = isDark ? '#1e293b' : '#fafafa';
  const tdBg = isDark ? '#0f172a' : '#ffffff';

  if (style === 'three_line') {
    let tableHtml = `
<div style="overflow-x: auto; margin: 24px 0;">
<table style="width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; border-top: 2px solid ${accent}; border-bottom: 2px solid ${accent}; background: transparent;">`;
    if (header && header.length > 0) {
      tableHtml += `<thead><tr>`;
      header.forEach((h, hIdx) => {
        tableHtml += `<th style="padding: 10px 14px; font-weight: 700; color: ${accent}; border-bottom: 1px solid ${borderColor}; text-align: ${colAlign(hIdx)};">${h}</th>`;
      });
      tableHtml += `</tr></thead>`;
    }
    tableHtml += `<tbody>`;
    for (const row of rows) {
      tableHtml += `<tr style="border-bottom: 1px dashed ${borderColor};">`;
      row.forEach((c, cIdx) => {
        const cFmt = formatInline(c, accent, '12.5px');
        tableHtml += `<td style="padding: 10px 14px; color: ${textColor}; line-height: 1.5; text-align: ${colAlign(cIdx)};">${cFmt}</td>`;
      });
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
      header.forEach((h, hIdx) => {
        tableHtml += `<th style="padding: 10px 14px; font-weight: 700; color: ${accent}; border: 1px solid ${borderColor}; text-align: ${colAlign(hIdx)};">${h}</th>`;
      });
      tableHtml += `</tr></thead>`;
    }
    tableHtml += `<tbody>`;
    for (const row of rows) {
      tableHtml += `<tr>`;
      row.forEach((c, cIdx) => {
        const cFmt = formatInline(c, accent, '12.5px');
        tableHtml += `<td style="padding: 10px 14px; color: ${textColor}; line-height: 1.5; border: 1px solid ${borderColor}; text-align: ${colAlign(cIdx)};">${cFmt}</td>`;
      });
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
      header.forEach((h, hIdx) => {
        tableHtml += `<th style="padding: 11px 14px; font-weight: 600; color: ${accent}; border-bottom: 2px solid ${borderColor}; text-align: ${colAlign(hIdx)};">${h}</th>`;
      });
      tableHtml += `</tr></thead>`;
    }
    tableHtml += `<tbody>`;
    for (let rIdx = 0; rIdx < rows.length; rIdx++) {
      const row = rows[rIdx];
      const bg = rIdx % 2 === 1 ? tdBgAlt : tdBg;
      tableHtml += `<tr style="background: ${bg}; border-bottom: 1px solid ${borderColor};">`;
      row.forEach((c, cIdx) => {
        const cFmt = formatInline(c, accent, '12.5px');
        tableHtml += `<td style="padding: 10px 14px; color: ${textColor}; line-height: 1.5; text-align: ${colAlign(cIdx)};">${cFmt}</td>`;
      });
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

export function renderTaskItem(itemText, checked, theme) {
  // GFM 任务列表项 (纯 SVG 矢量勾选框，无 Emoji，微信兼容内联样式)
  const accent = theme.accent;
  const textColor = theme.text_color;

  const checkbox = checked
    ? `<svg width="15" height="15" viewBox="0 0 24 24" style="vertical-align: -2px; flex-shrink: 0;"><rect x="2" y="2" width="20" height="20" rx="5" fill="${accent}"/><path d="M7 12.5l3.2 3.2L17 9" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`
    : `<svg width="15" height="15" viewBox="0 0 24 24" style="vertical-align: -2px; flex-shrink: 0;"><rect x="2.5" y="2.5" width="19" height="19" rx="5" fill="none" stroke="${accent}" stroke-width="2"/></svg>`;

  return `
<section style="display: flex; align-items: flex-start; margin-bottom: 8px; line-height: 1.75; font-size: 15.5px; color: ${textColor};">
<span style="margin-right: 7px; line-height: 1.75;">${checkbox}</span>
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
    return `
<div style="text-align: center; margin: 32px 0; line-height: 1;">
  <svg width="60" height="12" viewBox="0 0 60 12" fill="${accent}" style="display: inline-block;">
    <circle cx="10" cy="6" r="3"/>
    <circle cx="30" cy="6" r="3"/>
    <circle cx="50" cy="6" r="3"/>
  </svg>
</div>`;
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

  return `<section style="${containerStyle}">\n${bodyHtml}\n</section>`;
}

// ==============================================================================
// Markdown 解析主管道 (Parser Pipeline)
// ==============================================================================

// Stage A 预扫描正则：参考式链接定义与 [^id] 脚注定义
const REF_DEF_RE = /^ {0,3}\[([^^\]]+)\]:\s*<?([^\s>]+)>?(?:\s+["'(](.+?)["')])?\s*$/;
const FOOTNOTE_DEF_RE = /^ {0,3}\[\^([^\]]+)\]:\s?(.*)$/;

/**
 * Stage A 预扫描：收集参考式链接定义 [ref]: url 与脚注定义 [^id]: text，
 * 定义行从正文行流中移除（不渲染）。围栏代码块内的同名行不视为定义。
 * ref label 大小写不敏感；重复定义首个生效 (CommonMark 规则)。
 * 脚注定义 V1 仅支持单行正文（多行延续按普通段落处理）。
 */
export function preprocessLines(lines) {
  const refDefs = {};
  const footnoteDefs = {};
  const keep = [];
  let fenceCh = '';
  let fenceLen = 0;
  for (const line of lines) {
    const stripped = line.trim();
    const fenceMatch = stripped.match(/^(`{3,}|~{3,})/);
    if (fenceMatch) {
      if (!fenceCh) {
        fenceCh = fenceMatch[1][0];
        fenceLen = fenceMatch[1].length;
      } else if (fenceMatch[1][0] === fenceCh && fenceMatch[1].length >= fenceLen) {
        fenceCh = '';
      }
      keep.push(line);
      continue;
    }
    if (!fenceCh) {
      const fnMatch = line.match(FOOTNOTE_DEF_RE);
      if (fnMatch) {
        const fid = fnMatch[1].trim().toLowerCase();
        if (fid && !(fid in footnoteDefs)) {
          footnoteDefs[fid] = fnMatch[2].trim();
        }
        continue;
      }
      const refMatch = line.match(REF_DEF_RE);
      if (refMatch) {
        const label = refMatch[1].trim().toLowerCase();
        if (label && !(label in refDefs)) {
          refDefs[label] = { url: refMatch[2], title: refMatch[3] || '' };
        }
        continue;
      }
    }
    keep.push(line);
  }
  return { lines: keep, refDefs, footnoteDefs };
}

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

  // 微信公众号超链接自动转文末脚注机制 (URL 脚注开关；[^id] 文本脚注始终收集)
  const linkToFootnote = renderOptions.linkToFootnote !== false; // 默认开启
  const footnotes = [];

  const pre = preprocessLines(mdText.split('\n'));
  const lines = pre.lines;
  const refDefs = pre.refDefs;
  const footnoteDefs = pre.footnoteDefs;
  const htmlParts = [];

  // 微信公众号文章顶部自动嵌入当前主题封面卡片 (默认开启)
  const insertCover = renderOptions.insertCover !== false;
  if (insertCover) {
    const coverMeta = renderOptions.coverMeta || extractCoverMeta(mdText, themeName);
    const headerCoverHtml = renderWechatArticleHeaderCover(themeName, coverMeta);
    if (headerCoverHtml) {
      htmlParts.push(headerCoverHtml);
    }
  }

  // 块级渲染主循环 (嵌套引用会对内层行递归调用 renderBlockLines)
  function renderBlockLines(blockLines) {
    // 每层递归独立的块状态
    let inCodeBlock = false;
    let codeLang = '';
    let codeLines = [];
    let codeFenceCh = '';
    let codeFenceLen = 0;
    let inTable = false;
    let tableLines = [];
    let paraBuf = [];

    function flushTable() {
      if (!tableLines.length) return '';
      let header = [];
      let aligns = [];
      const rows = [];
      for (let i = 0; i < tableLines.length; i++) {
        const cells = tableLines[i]
          .trim()
          .replace(/^\||\|$/g, '')
          .replace(/\\\|/g, '\x00P\x00')
          .split('|')
          .map((c) => c.trim().replace(/\x00P\x00/g, '|'));
        if (i === 0) {
          header = cells;
        } else if (i === 1 && cells.every((c) => /^[-: ]*$/.test(c) && c.includes('-'))) {
          // GFM 对齐标记：:--- 左(默认)、---: 右、:---: 居中
          aligns = cells.map((c) => {
            const t = c.trim();
            if (!t.endsWith(':')) return 'left';
            return t.startsWith(':') ? 'center' : 'right';
          });
          continue;
        } else {
          rows.push(cells);
        }
      }
      const rendered = renderTable(header, rows, theme, aligns);
      tableLines = [];
      inTable = false;
      return rendered;
    }

    function flushCode() {
      // highlightCode 内部统一做 HTML 转义，此处禁止预先转义 (会造成双重转义)
      let rawCode = codeLines.join('\n');
      const rendered = renderCode(rawCode, codeLang, theme);
      codeLines = [];
      inCodeBlock = false;
      codeFenceCh = '';
      codeFenceLen = 0;
      return rendered;
    }

    const inlineFmt = (text, size = '13.5px') =>
      formatInline(text, accent, size, footnotes, linkToFootnote, refDefs, footnoteDefs, theme.accent_bg)
        .replace(/@@MDBR_0@@/g, '<br />');

    function flushPara() {
      if (!paraBuf.length) return '';
      const joined = joinParagraphLines(paraBuf);
      paraBuf = [];
      const pText = inlineFmt(joined);
      return `
<p style="font-size: ${fontSizeBase}; line-height: ${lineHeightBase}; color: ${textColor}; margin: 18px 0; letter-spacing: ${letterSpacing}; ${indentCss}text-align: justify;">
${pText}
</p>`;
    }

    // 解析列表块 (含多层嵌套)；空行结束列表，缩进 2+ 空格的 marker 归入子列表
    function parseList(i, minIndent) {
      const items = [];
      let firstIndent = null;
      while (i < blockLines.length) {
        const ln = blockLines[i];
        if (!ln.trim()) break;
        const exp = ln.replace(/\t/g, '    ');
        const lm = exp.match(LIST_ITEM_RE);
        if (!lm) break;
        const ind = lm[1].length;
        if (ind < minIndent) break;
        if (firstIndent === null) firstIndent = ind;
        if (ind < firstIndent) break;
        if (ind >= firstIndent + 2) {
          if (!items.length) break;
          const [subItems, nextI] = parseList(i, ind);
          items[items.length - 1].children.push(...subItems);
          i = nextI;
          continue;
        }
        const marker = lm[2];
        let content = (lm[3] || '').trim();
        const ordered = /^\d/.test(marker);
        const number = ordered ? parseInt(marker.match(/(\d+)/)[1], 10) : 0;
        let task = null;
        const tm = content.match(/^\[( |x|X)\]\s+(.*)$/);
        if (tm) {
          task = tm[1].toLowerCase() === 'x';
          content = tm[2];
        }
        const item = { ordered, number, task, lines: content ? [content] : [], children: [] };
        items.push(item);
        i++;
        // 同项延续行：缩进 >= 内容列的非 marker 行并入当前项
        const contentCol = firstIndent + marker.length + 1;
        while (i < blockLines.length) {
          const nxt = blockLines[i];
          if (!nxt.trim()) break;
          const nxtExp = nxt.replace(/\t/g, '    ');
          const nlm = nxtExp.match(LIST_ITEM_RE);
          if (nlm) break;
          const nInd = nxtExp.length - nxtExp.replace(/^ +/, '').length;
          if (nInd >= contentCol) {
            item.lines.push(nxtExp.trim());
            i++;
          } else {
            break;
          }
        }
      }
      return [items, i];
    }

    function renderListHtml(items) {
      return items
        .map((it) => {
          let contentHtml = '';
          if (it.lines.length) {
            contentHtml = inlineFmt(joinParagraphLines(it.lines));
          }
          if (it.children.length) {
            contentHtml += `<div style="padding-left: 16px; margin-top: 2px;">${renderListHtml(it.children)}</div>`;
          }
          if (it.task !== null) {
            return renderTaskItem(contentHtml, it.task, theme);
          }
          if (it.ordered) {
            return renderOrderedListItem(contentHtml, it.number, theme);
          }
          return renderListItem(contentHtml, theme);
        })
        .join('');
    }

    const parts = [];
    let idx = 0;
    const n = blockLines.length;
    while (idx < n) {
      const rawLine = blockLines[idx];
      const stripped = rawLine.trim();

      // 1. 围栏代码块 (``` 与 ~~~ 等价，3+ 字符；闭栏需同字符且长度不小于开栏)
      const fenceMatch = stripped.match(/^(`{3,}|~{3,})(.*)$/);
      if (fenceMatch) {
        const fCh = fenceMatch[1][0];
        if (inCodeBlock) {
          if (fCh === codeFenceCh && fenceMatch[1].length >= codeFenceLen) {
            parts.push(flushCode());
          } else {
            codeLines.push(rawLine);
          }
        } else {
          if (inTable) parts.push(flushTable());
          const fp = flushPara();
          if (fp) parts.push(fp);
          inCodeBlock = true;
          codeFenceCh = fCh;
          codeFenceLen = fenceMatch[1].length;
          codeLang = fenceMatch[2].trim();
          codeLines = [];
        }
        idx++;
        continue;
      }

      if (inCodeBlock) {
        codeLines.push(rawLine);
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
        parts.push(flushTable());
      }

      // 3. 空行：结束当前段落
      if (!stripped) {
        const fp = flushPara();
        if (fp) parts.push(fp);
        idx++;
        continue;
      }

      // 3.2 块级富文本占位 (Mermaid/块级公式，预览由 richrender.js 水合渲染，
      //     复制/导出前由 rasterizeRichBlocks 光栅化为内联 PNG)
      if (/^@@MD(?:MERMAID|MATH)_\d+@@$/.test(stripped)) {
        const fp = flushPara();
        if (fp) parts.push(fp);
        parts.push(`<div style="margin: 22px 0; text-align: center;" data-md-rich-token="${stripped}"></div>`);
        idx++;
        continue;
      }

      // 3.4 缩进代码块：4+ 空格缩进且无未决段落 (列表项内部由列表解析器自行消费)
      if (!paraBuf.length && (rawLine.startsWith('    ') || rawLine.startsWith('\t'))) {
        const fp = flushPara();
        if (fp) parts.push(fp);
        codeLines = [];
        while (
          idx < n &&
          (blockLines[idx].startsWith('    ') || blockLines[idx].startsWith('\t') || !blockLines[idx].trim())
        ) {
          const exp = blockLines[idx].replace(/\t/g, '    ');
          codeLines.push(exp.startsWith('    ') ? exp.slice(4) : exp);
          idx++;
        }
        while (codeLines.length && !codeLines[codeLines.length - 1].trim()) {
          codeLines.pop();
        }
        if (codeLines.length) {
          parts.push(renderCode(codeLines.join('\n'), 'code', theme));
        }
        continue;
      }

      // 3.4 Setext 标题：段落缓冲非空时的 === / --- 下划线 (先于分割线判定)
      const setextMatch = rawLine.match(/^ {0,3}(=+|-+)\s*$/);
      if (setextMatch && paraBuf.length) {
        const joined = joinParagraphLines(paraBuf);
        paraBuf = [];
        const level = setextMatch[1][0] === '=' ? 1 : 2;
        parts.push(level === 1 ? renderH1(inlineFmt(joined), theme) : renderH2(inlineFmt(joined), theme));
        idx++;
        continue;
      }

      // 3.6 分割线 (3+ 个 -/*/ _，允许空格分隔，如 - - - / ****)
      if (/^ {0,3}([-*_])(?:[ \t]*\1){2,}\s*$/.test(rawLine)) {
        const fp = flushPara();
        if (fp) parts.push(fp);
        parts.push(renderHr(theme));
        idx++;
        continue;
      }

      // 4. ATX 标题 # ~ ###### (去除尾部 # 修饰；文本运行行内格式化)
      const atxMatch = stripped.match(/^(#{1,6})(?:\s+(.*?))?\s*#*\s*$/);
      if (atxMatch) {
        const fp = flushPara();
        if (fp) parts.push(fp);
        const level = atxMatch[1].length;
        const hText = inlineFmt((atxMatch[2] || '').trim());
        if (level === 1) {
          parts.push(renderH1(hText, theme));
        } else if (level === 2) {
          parts.push(renderH2(hText, theme));
        } else if (level === 3) {
          parts.push(renderH3(hText, theme));
        } else if (level === 4) {
          parts.push(renderH4(hText, theme));
        } else if (level === 5) {
          parts.push(renderH5(hText, theme));
        } else {
          parts.push(renderH6(hText, theme));
        }
        idx++;
        continue;
      }

      // 5. 引用块 (剥一层 > 后递归渲染内层，支持 >> 多级嵌套；引用内空行为间隔)
      if (stripped.startsWith('>')) {
        const fp = flushPara();
        if (fp) parts.push(fp);
        if (inTable) parts.push(flushTable());
        const innerLines = [];
        while (idx < n && blockLines[idx].trim().startsWith('>')) {
          const qLine = blockLines[idx].trim();
          innerLines.push(qLine.startsWith('> ') ? qLine.slice(2).trim() : qLine.slice(1).trim());
          idx++;
        }
        const segParts = [];
        let run = [];
        const flushQuoteRun = () => {
          if (run.length) {
            segParts.push(...renderBlockLines(run.slice()));
            run = [];
          }
        };
        for (const q of innerLines) {
          if (q.trim()) {
            run.push(q);
          } else {
            flushQuoteRun();
            segParts.push('<div style="height: 6px;"></div>');
          }
        }
        flushQuoteRun();
        parts.push(renderQuote(segParts.join('\n'), theme));
        continue;
      }

      // 6. 列表 (有序/无序/任务，含多层嵌套)
      const listExp = rawLine.replace(/\t/g, '    ');
      const listMatch = listExp.match(LIST_ITEM_RE);
      if (listMatch && listMatch[1].length < 4) {
        const fp = flushPara();
        if (fp) parts.push(fp);
        if (inTable) parts.push(flushTable());
        const [items, endIdx] = parseList(idx, listMatch[1].length);
        parts.push(renderListHtml(items));
        idx = endIdx;
        continue;
      }

      // 7. 独立行图片 (命中才冲刷段落缓冲，普通段落行继续走缓冲合并)
      const imgMatch = stripped.match(/^!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)$/);
      if (imgMatch) {
        const fp = flushPara();
        if (fp) parts.push(fp);
        const alt = escapeHtml(imgMatch[1]);
        const src = imgMatch[2].replace(/"/g, '&quot;');
        const caption = alt
          ? `<div style="text-align: center; color: ${subColor}; font-size: 13px; margin-top: 6px; font-style: italic;">${alt}</div>`
          : '';
        parts.push(`
<div style="margin: 24px 0; text-align: center;">
<img src="${src}" alt="${alt}" style="max-width: 96%; height: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); display: inline-block;" />
${caption}
</div>`);
        idx++;
        continue;
      }

      // 8. 显式图注 (*▲ 图：...*)
      const captionMatch = stripped.match(/^\*▲ 图：(.+?)\*$/);
      if (captionMatch) {
        const fp = flushPara();
        if (fp) parts.push(fp);
        const capText = captionMatch[1];
        parts.push(`
<div style="text-align: center; color: ${subColor}; font-size: 13px; margin: -16px 0 20px 0; font-style: italic;">
▲ 图：${capText}
</div>`);
        idx++;
        continue;
      }

      // 9. 段落缓冲 (连续非空行合并为同一段；保留行尾空格供硬换行判定)
      paraBuf.push(rawLine.replace(/[\r\n]+$/, '').replace(/^\s+/, ''));
      idx++;
    }

    const fp = flushPara();
    if (fp) parts.push(fp);
    if (inTable) parts.push(flushTable());
    if (inCodeBlock) parts.push(flushCode());
    return parts;
  }

  htmlParts.push(...renderBlockLines(lines));



  // 注入文末参考资料与引用外链
  if (footnotes.length > 0) {
    const listItems = footnotes
      .map((fn, fIndex) => {
        const numHtml = `<span style="color: ${accent}; font-weight: 700; margin-right: 6px;">[${fIndex + 1}]</span>`;
        if (fn.kind === 'text') {
          // [^id] 脚注：渲染定义正文 (定义内的链接渲染为锚点，不再产生新脚注)
          const bodyHtml = formatInline(fn.text || '', accent, '12px', null, true, refDefs, footnoteDefs, theme.accent_bg);
          return `<li style="margin: 5px 0; word-break: break-all; list-style-type: none;">${numHtml}<span style="color: ${textColor}; font-weight: 500;">${bodyHtml}</span></li>`;
        }
        return `<li style="margin: 5px 0; word-break: break-all; list-style-type: none;">${numHtml}<span style="color: ${textColor}; font-weight: 500;">${fn.label}</span>: <span style="color: ${subColor}; font-family: monospace; font-size: 11.5px;">${fn.url}</span></li>`;
      })
      .join('\n');

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

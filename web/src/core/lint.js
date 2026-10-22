/**
 * MD2WX Web Studio - 发稿规范校验器 (web/src/core/lint.js)
 *
 * 与 CLI 端 md2wx/linter.py 严格镜像：规则编号 (code)、判定顺序、问题级别与文案
 * 完全一致，tests/test_lint_consistency.py 会在 Node 环境下逐条比对双端输出。
 *
 * 规则清单：
 *   1.  title-missing / title-too-long / title-punctuation
 *   2.  digest-missing / digest-too-long / digest-punctuation
 *   3.  cover-forbidden
 *   4.  control-chars
 *   5.  emoji-banned
 *   6.  html-unclosed
 *   7.  external-images
 *   8.  heading-skip
 *   9.  code-lang-missing
 *   10. image-alt-missing
 *   11. duplicate-image
 *   12. link-format-invalid
 *   13. punctuation-mixed
 */
import {
  parseFrontmatter,
  collectExternalImageUrls,
  expandObsidianImages,
} from './parser.js';

export const DEVLOG_TITLE_MAX_LEN = 20;
export const DEVLOG_DIGEST_MAX_LEN = 50;

const CONTROL_CHARS_RE = /[\x00-\x08\x0b\x0c\x0e-\x1f]/;
const ATX_HEADING_RE = /^(#{1,6})\s+\S/;
const FENCE_OPEN_RE = /^(```+|~~~+)\s*([^`]*)$/;
const IMAGE_RE = /!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)/g;

// Emoji 区段 (与 Python 端 _EMOJI_RE 同步，不含裸变体选择符 FE0F)
const EMOJI_RE = /[\u{1F000}-\u{1FAFF}\u2600-\u27BF\u2B00-\u2BFF\u20E3]/gu;
const HAN_RE = /[\u3400-\u4dbf\u4e00-\u9fff]/;

const HALF_TO_FULL = {
  ',': '，',
  ';': '；',
  ':': '：',
  '!': '！',
  '?': '？',
  '(': '（',
  ')': '）',
};
const TITLE_TRAILING_PUNCT = '。．.，,；;：:';
const DIGEST_TRAILING_PUNCT = '，,；;：:';

const BLOCK_TAGS = ['div', 'section', 'table', 'pre', 'style', 'script', 'iframe', 'video', 'svg'];
const BLOCK_TAG_RE = new RegExp(
  `<(/?)\\s*(${BLOCK_TAGS.join('|')})\\b[^>]*?(/?)>`,
  'gi',
);

const RE_INLINE_CODE = /(`+)(?:(?!\1)[\s\S])+?\1/g;
const RE_LINK_TARGET = /\]\(\s*<?[^)\n]*>?(?:\s+"[^"]*")?\s*\)/g;
const RE_BARE_URL = /https?:\/\/[^\s<>()\[\]]+/g;
const RE_HTML_TAG = /<\/?[A-Za-z][^>\n]*>/g;
const RE_ENTITY = /&(?:[a-zA-Z][a-zA-Z0-9]*|#[0-9]+|#x[0-9a-fA-F]+);/g;
const RE_MD_LINK = /!?\[[^\]]*\]\(\s*<?([^)\s>]*)>?(?:\s+"[^"]*")?\s*\)/g;

/** 把匹配片段替换为等长空白 (保留换行)，不改变行号/列号 */
function blank(match) {
  return String(match).replace(/[^\n]/g, ' ');
}

function maskInlineCode(line) {
  return line.replace(RE_INLINE_CODE, blank);
}

function maskProse(line) {
  return line
    .replace(RE_INLINE_CODE, blank)
    .replace(RE_LINK_TARGET, blank)
    .replace(RE_BARE_URL, blank)
    .replace(RE_HTML_TAG, blank)
    .replace(RE_ENTITY, blank);
}

/** 把围栏代码块整段替换为空行，保持行号不变 */
function stripFenced(body) {
  const out = [];
  let fenceMarker = '';
  for (const line of body.split('\n')) {
    if (fenceMarker) {
      const stripped = line.trim();
      if (stripped.startsWith(fenceMarker) && /^[`~]+$/.test(stripped)) {
        fenceMarker = '';
      }
      out.push('');
      continue;
    }
    const fence = line.match(FENCE_OPEN_RE);
    if (fence) {
      fenceMarker = fence[1];
      out.push('');
      continue;
    }
    out.push(line);
  }
  return out.join('\n');
}

function maskBody(body) {
  const proseLines = [];
  const codeLines = [];
  for (const line of stripFenced(body).split('\n')) {
    proseLines.push(maskProse(line));
    codeLines.push(maskInlineCode(line));
  }
  return { proseMasked: proseLines.join('\n'), codeMasked: codeLines.join('\n') };
}

/** 定位 frontmatter 字段所在行 (1-based)，未找到返回 1 */
function fieldLine(rawLines, key) {
  const re = new RegExp(`^\\s*${key}\\s*:`);
  for (let idx = 0; idx < rawLines.length; idx += 1) {
    const line = rawLines[idx];
    if (idx === 0 && line.trim() === '---') continue;
    if (line.trim() === '---') break;
    if (re.test(line)) return idx + 1;
  }
  return 1;
}

function firstHalfWidthPunct(text) {
  for (const ch of text) {
    if (HALF_TO_FULL[ch]) return ch;
  }
  return '';
}

/**
 * 扫描正文结构：标题、缺语言围栏、图片引用 (含重复) 与缺 alt 图片
 * 所有行号均为正文内 1-based
 */
function scanBodyStructure(body) {
  const headings = [];
  const fencesWithoutLang = [];
  const imageUrls = [];
  const imagesMissingAlt = [];
  let fenceMarker = '';

  body.split('\n').forEach((line, i) => {
    const lineNo = i + 1;
    if (fenceMarker) {
      const stripped = line.trim();
      if (stripped.startsWith(fenceMarker) && /^[`~]+$/.test(stripped)) {
        fenceMarker = '';
      }
      return;
    }

    const fence = line.match(FENCE_OPEN_RE);
    if (fence) {
      const info = (fence[2] || '').trim();
      if (!info) fencesWithoutLang.push({ line: lineNo });
      fenceMarker = fence[1];
      return;
    }

    const heading = line.match(ATX_HEADING_RE);
    if (heading) {
      headings.push({
        level: heading[1].length,
        line: lineNo,
        text: line.replace(/^#+/, '').trim(),
      });
    }

    const imgRe = new RegExp(IMAGE_RE.source, 'g');
    let img;
    while ((img = imgRe.exec(line)) !== null) {
      imageUrls.push({ url: img[2], line: lineNo });
      if (!img[1].trim()) imagesMissingAlt.push({ line: lineNo, url: img[2] });
    }
  });

  return { headings, fencesWithoutLang, imageUrls, imagesMissingAlt };
}

/** 逐行检测中文正文里的半角标点，返回 [{ line, puncts }] */
function punctuationHits(proseMasked) {
  const hits = [];
  proseMasked.split('\n').forEach((line, i) => {
    const found = [];
    for (let col = 0; col < line.length; col += 1) {
      const ch = line[col];
      if (!HALF_TO_FULL[ch]) continue;
      const before = col > 0 ? line[col - 1] : '';
      const after = col + 1 < line.length ? line[col + 1] : '';
      const adjacentHan = Boolean((before && HAN_RE.test(before)) || (after && HAN_RE.test(after)));
      if (adjacentHan) {
        if (!found.includes(ch)) found.push(ch);
        continue;
      }
      if (ch === ',' || ch === ';') {
        const prevAsciiWord = Boolean(before) && /[A-Za-z0-9]/.test(before);
        const nextIsSpace = Boolean(after) && /\s/.test(after);
        if (prevAsciiWord && nextIsSpace) {
          let probe = col + 1;
          while (probe < line.length && /\s/.test(line[probe])) probe += 1;
          if (probe < line.length && HAN_RE.test(line[probe]) && !found.includes(ch)) {
            found.push(ch);
          }
        }
      }
    }
    if (found.length) hits.push({ line: i + 1, puncts: found });
  });
  return hits;
}

/** 校验 Markdown 链接协议与格式 (纯本地，不发起网络请求) */
function linkFormatIssues(codeMasked) {
  const issues = [];
  codeMasked.split('\n').forEach((line, i) => {
    const re = new RegExp(RE_MD_LINK.source, 'g');
    let match;
    while ((match = re.exec(line)) !== null) {
      const target = (match[1] || '').trim();
      let reason = '';
      if (!target) {
        reason = '链接目标为空';
      } else if (/\s/.test(target)) {
        reason = '链接目标包含空白字符';
      } else if (target.startsWith('//')) {
        reason = '缺少 http/https 协议';
      } else {
        const schemeMatch = target.match(/^([A-Za-z][A-Za-z0-9+.-]*):/);
        if (schemeMatch) {
          const scheme = schemeMatch[1].toLowerCase();
          if (!['http', 'https', 'mailto'].includes(scheme)) {
            reason = `不支持的协议「${scheme}」`;
          }
        } else if (/^www\./i.test(target)) {
          reason = '缺少 http/https 协议';
        }
      }
      if (reason) issues.push({ line: i + 1, target, reason });
    }
  });
  return issues;
}

/**
 * 按 MD2WX 发稿规范检查 Markdown
 * @param {string} rawMd 完整 Markdown (含 frontmatter)
 * @returns {Array<{level:'error'|'warn', code:string, message:string, line:number}>}
 */
export function lintMarkdown(rawMd) {
  const issues = [];
  const add = (level, code, message, line = 1) => {
    issues.push({ level, code, message, line: Math.max(1, Math.round(line) || 1) });
  };

  const { meta, body: rawBody } = parseFrontmatter(rawMd || '');
  const normalized = String(rawMd || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const rawLines = normalized.split('\n');
  const bodyLineOffset = rawLines.length - rawBody.split('\n').length;
  const toRawLine = (bodyLine) => Math.max(1, bodyLine + bodyLineOffset);

  const body = expandObsidianImages(rawBody);
  const bodyLines = body.split('\n');
  const { proseMasked, codeMasked } = maskBody(body);

  // 1. 主标题
  let title = typeof meta.title === 'string' ? meta.title : (meta.title ? String(meta.title) : '');
  let titleLine = fieldLine(rawLines, 'title');
  if (!title) {
    for (let i = 0; i < bodyLines.length; i += 1) {
      if (bodyLines[i].trim().startsWith('# ')) {
        title = bodyLines[i].trim().slice(2).trim();
        titleLine = toRawLine(i + 1);
        break;
      }
    }
  }
  if (!title) {
    add('warn', 'title-missing', '未找到主标题 (frontmatter title 或首个 H1)，将回退为「未命名文章」。');
  } else {
    if (title.length > DEVLOG_TITLE_MAX_LEN) {
      add(
        'error',
        'title-too-long',
        `主标题 ${title.length} 字，超过规范上限 ${DEVLOG_TITLE_MAX_LEN} 字：「${title}」`,
        titleLine,
      );
    }
    const trimmed = title.replace(/\s+$/, '');
    const trailing = trimmed ? Array.from(trimmed).pop() : '';
    if (TITLE_TRAILING_PUNCT.includes(trailing)) {
      add(
        'warn',
        'title-punctuation',
        `主标题结尾不要使用标点「${trailing}」，微信会话列表按纯文本展示更清爽。`,
        titleLine,
      );
    } else {
      const half = firstHalfWidthPunct(title);
      if (half) {
        add(
          'warn',
          'title-punctuation',
          `主标题混用半角标点「${half}」，建议改为全角「${HALF_TO_FULL[half]}」。`,
          titleLine,
        );
      }
    }
  }

  // 2. 摘要 digest
  const digest = typeof meta.digest === 'string' ? meta.digest : (meta.digest ? String(meta.digest) : '');
  const digestLine = fieldLine(rawLines, 'digest');
  if (!digest) {
    add('warn', 'digest-missing', 'frontmatter 缺少 digest 摘要，发布时将回退为正文首段/引言。');
  } else {
    if (digest.length > DEVLOG_DIGEST_MAX_LEN) {
      add(
        'error',
        'digest-too-long',
        `digest 摘要 ${digest.length} 字，超过规范上限 ${DEVLOG_DIGEST_MAX_LEN} 字：「${digest}」`,
        digestLine,
      );
    }
    const trimmed = digest.replace(/\s+$/, '');
    const trailing = trimmed ? Array.from(trimmed).pop() : '';
    if (DIGEST_TRAILING_PUNCT.includes(trailing)) {
      add(
        'warn',
        'digest-punctuation',
        `digest 结尾不要使用标点「${trailing}」，微信摘要会自动截断展示。`,
        digestLine,
      );
    } else {
      const half = firstHalfWidthPunct(digest);
      if (half) {
        add(
          'warn',
          'digest-punctuation',
          `digest 混用半角标点「${half}」，建议改为全角「${HALF_TO_FULL[half]}」。`,
          digestLine,
        );
      }
    }
  }

  // 3. cover 字段禁填
  if (Object.prototype.hasOwnProperty.call(meta, 'cover')) {
    add(
      'error',
      'cover-forbidden',
      'frontmatter 填写了 cover 字段，规范要求留空由主题封面引擎自动生成。',
      fieldLine(rawLines, 'cover'),
    );
  }

  // 4. 控制字符
  const control = CONTROL_CHARS_RE.exec(body);
  if (control) {
    const controlLine = body.slice(0, control.index).split('\n').length;
    const codePoint = control[0].codePointAt(0);
    add(
      'error',
      'control-chars',
      `正文包含控制字符 U+${codePoint.toString(16).toUpperCase().padStart(4, '0')}，微信草稿箱 API 会导致正文静默截断。`,
      toRawLine(controlLine),
    );
  }

  // 5. Emoji
  proseMasked.split('\n').forEach((line, i) => {
    const found = line.match(EMOJI_RE) || [];
    if (!found.length) return;
    const sample = found[0];
    const message = found.length > 1
      ? `检测到 ${found.length} 处 Emoji（如「${sample}」），项目规范要求正文使用纯文本或矢量图标。`
      : `检测到 Emoji「${sample}」，项目规范要求正文使用纯文本或矢量图标。`;
    add('warn', 'emoji-banned', message, toRawLine(i + 1));
  });

  // 6. 未闭合块级 HTML 标签
  const openCounts = {};
  const closeCounts = {};
  const firstLines = {};
  codeMasked.split('\n').forEach((line, i) => {
    const re = new RegExp(BLOCK_TAG_RE.source, 'gi');
    let match;
    while ((match = re.exec(line)) !== null) {
      const closing = match[1];
      const tag = match[2].toLowerCase();
      const selfClosing = match[3];
      if (selfClosing) continue;
      if (closing) {
        closeCounts[tag] = (closeCounts[tag] || 0) + 1;
      } else {
        openCounts[tag] = (openCounts[tag] || 0) + 1;
        if (!(tag in firstLines)) firstLines[tag] = i + 1;
      }
    }
  });
  Object.keys(openCounts).forEach((tag) => {
    if (openCounts[tag] > (closeCounts[tag] || 0)) {
      add(
        'error',
        'html-unclosed',
        `检测到未闭合的 <${tag}> 标签，粘贴到微信后台会导致后续排版错乱，请补齐闭合标签。`,
        toRawLine(firstLines[tag]),
      );
    }
  });

  // 7. 外链图片
  const externalImages = collectExternalImageUrls(body);
  if (externalImages.length) {
    const preview = externalImages.slice(0, 3).join('、');
    const more = externalImages.length > 3 ? ` 等 ${externalImages.length} 处` : '';
    const firstExternal = externalImages[0];
    let externalLine = 1;
    for (let i = 0; i < bodyLines.length; i += 1) {
      if (bodyLines[i].includes(firstExternal)) {
        externalLine = i + 1;
        break;
      }
    }
    add(
      'warn',
      'external-images',
      `检测到外链图片${more}：${preview}。发布模式 (-p) 会自动转存微信 CDN，剪贴板模式可使用 --rehost-images 换链。`,
      toRawLine(externalLine),
    );
  }

  // 8-11. 正文结构类规范
  const structure = scanBodyStructure(body);

  // 8. 标题层级跳跃
  let prevLevel = 0;
  for (const heading of structure.headings) {
    if (prevLevel && heading.level > prevLevel + 1) {
      add(
        'warn',
        'heading-skip',
        `标题层级跳跃：H${prevLevel} 后直接出现 H${heading.level}「${heading.text.slice(0, 24)}…」，建议逐级递进。`,
        toRawLine(heading.line),
      );
      break;
    }
    prevLevel = heading.level;
  }

  // 9. 围栏代码块缺少语言标注
  if (structure.fencesWithoutLang.length) {
    add(
      'warn',
      'code-lang-missing',
      `${structure.fencesWithoutLang.length} 处围栏代码块未标注语言。纯文本块可忽略；语法代码建议补语言标注以启用高亮。`,
      toRawLine(structure.fencesWithoutLang[0].line),
    );
  }

  // 10. 图片缺少 alt
  if (structure.imagesMissingAlt.length) {
    add(
      'warn',
      'image-alt-missing',
      `${structure.imagesMissingAlt.length} 处图片缺少 alt 描述文本，建议补充说明 (微信图片折叠时无法展示语义)。`,
      toRawLine(structure.imagesMissingAlt[0].line),
    );
  }

  // 11. 重复图片
  const seenUrls = new Set();
  for (const image of structure.imageUrls) {
    if (seenUrls.has(image.url)) {
      add(
        'warn',
        'duplicate-image',
        `同一图片被重复引用：${image.url.slice(0, 60)}。建议复用同一处引用或拆分为不同说明图。`,
        toRawLine(image.line),
      );
      break;
    }
    seenUrls.add(image.url);
  }

  // 12. 链接协议 / 格式异常
  for (const item of linkFormatIssues(codeMasked)) {
    add(
      'warn',
      'link-format-invalid',
      `链接格式异常「${item.target}」：${item.reason}，微信无法识别。`,
      toRawLine(item.line),
    );
  }

  // 13. 中文正文全半角标点混用
  for (const hit of punctuationHits(proseMasked)) {
    const half = hit.puncts.map((ch) => `「${ch}」`).join('、');
    const full = hit.puncts.map((ch) => `「${HALF_TO_FULL[ch]}」`).join('、');
    add(
      'warn',
      'punctuation-mixed',
      `中文正文混用半角标点${half}，建议改为全角${full}。`,
      toRawLine(hit.line),
    );
  }

  return issues;
}

/** 是否存在阻断级问题 (error)，Web 端据此阻断复制动作 */
export function hasErrors(issues) {
  return issues.some((item) => item.level === 'error');
}

/** 统计 error / warn 数量 (与 Python 端 summarize 同口径) */
export function summarizeLint(issues) {
  const errors = issues.filter((item) => item.level === 'error').length;
  return { errors, warnings: issues.length - errors };
}

/**
 * 一键修复中文正文半角标点：只替换检测命中的半角字符，行内代码/链接/URL/HTML 标签保持原样
 * @param {string} rawMd 完整 Markdown
 * @returns {{ text: string, fixed: number }}
 */
export function autoFixPunctuation(rawMd) {
  const normalized = String(rawMd || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  let fenceMarker = '';
  let fixed = 0;
  const outLines = normalized.split('\n').map((line) => {
    if (fenceMarker) {
      const stripped = line.trim();
      if (stripped.startsWith(fenceMarker) && /^[`~]+$/.test(stripped)) fenceMarker = '';
      return line;
    }
    const fence = line.match(FENCE_OPEN_RE);
    if (fence) {
      fenceMarker = fence[1];
      return line;
    }

    const masked = maskProse(line);
    const chars = line.split('');
    for (let col = 0; col < masked.length; col += 1) {
      const ch = masked[col];
      if (!HALF_TO_FULL[ch]) continue;
      const before = col > 0 ? masked[col - 1] : '';
      const after = col + 1 < masked.length ? masked[col + 1] : '';
      let hit = Boolean((before && HAN_RE.test(before)) || (after && HAN_RE.test(after)));
      if (!hit && (ch === ',' || ch === ';')) {
        const prevAsciiWord = Boolean(before) && /[A-Za-z0-9]/.test(before);
        if (prevAsciiWord && Boolean(after) && /\s/.test(after)) {
          let probe = col + 1;
          while (probe < masked.length && /\s/.test(masked[probe])) probe += 1;
          hit = probe < masked.length && HAN_RE.test(masked[probe]);
        }
      }
      if (hit) {
        chars[col] = HALF_TO_FULL[ch];
        fixed += 1;
      }
    }
    return chars.join('');
  });
  return { text: outLines.join('\n'), fixed };
}

/** 统计正文图片数量 (含 Obsidian wiki 图片语法) */
export function countImages(mdText) {
  const { body } = parseFrontmatter(mdText || '');
  const expanded = expandObsidianImages(body);
  const re = new RegExp(IMAGE_RE.source, 'g');
  return (expanded.match(re) || []).length;
}

/** 正文字数 / 阅读时长 / 图片数量：与编辑器状态栏同口径 */
export function computeReadingStats(rawMd) {
  const { body } = parseFrontmatter(rawMd || '');
  const chineseChars = (body.match(/[\u4e00-\u9fff]/g) || []).length;
  const englishWords = (body.replace(/[\u4e00-\u9fff]/g, ' ').match(/\b\w+\b/g) || []).length;
  const count = chineseChars + englishWords;
  return {
    chars: count,
    minutes: Math.max(1, Math.ceil(count / 400)),
    images: countImages(rawMd),
  };
}

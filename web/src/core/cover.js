/**
 * MD2WX 专属主题默认封面生成引擎 (Theme-Matched WeChat Cover Generator)
 * 适配公众号两种核心比例：
 * 1. 2.35:1 (Banner - 微信公众号头条封面，推荐 2350x1000)
 * 2. 1:1 (Square - 微信公众号次条/分享朋友圈与聊天卡片，推荐 1200x1200)
 * 严格遵循规范：全站无 Emoji，全部采用高质量矢量排版
 */

import { parseFrontmatter, stripMarkdown, escapeHtml } from './parser.js';

// 封面推荐逻辑尺寸配置
export const COVER_DIMENSIONS = {
  banner: { width: 1175, height: 500, ratioName: '2.35:1 头条大图' },
  square: { width: 600, height: 600, ratioName: '1:1 次条/分享方图' }
};

/**
 * 针对各排版主题的默认设计预设
 */
export const THEME_COVER_PRESETS = {
  'tech-blue': {
    name: '现代科技蓝',
    defaultTag: '深度架构 · 极客手记',
    badgeText: 'TECH BLOG',
    volText: '2026 · VOL.02'
  },
  'acid-bold': {
    name: '先锋野兽派',
    defaultTag: '态度发声 · 拒绝平庸',
    badgeText: 'ACID BOLD',
    volText: 'VOL.02 // POP'
  },
  'dark-night': {
    name: '暗黑极客风',
    defaultTag: '赛博夜读 · 极客沉思',
    badgeText: 'NIGHT RUN',
    volText: '0x02 // CYBER'
  },
  'elegant-purple': {
    name: '先锋优雅紫',
    defaultTag: '设计美学 · 独立思考',
    badgeText: 'AESTHETIC',
    volText: '2026 · ISSUE 02'
  },
  'terminal-geek': {
    name: '极客终端',
    defaultTag: 'SHELL · 架构复盘',
    badgeText: 'BASH / DEV',
    volText: 'TERM // 2026'
  },
  'vintage-news': {
    name: '复古报刊',
    defaultTag: '人文书卷 · 思想论丛',
    badgeText: 'WEEKLY PRESS',
    volText: '第 02 期 · 专刊'
  },
  'warm-memo': {
    name: '温暖便签',
    defaultTag: '生活手记 · 日常微光',
    badgeText: 'HEALING NOTE',
    volText: '2026 · MEMO #02'
  },
  'warm-orange': {
    name: '温暖活力橙',
    defaultTag: '元气日常 · 读书感悟',
    badgeText: 'SUNSHINE',
    volText: '2026 · VOL.02'
  },
  'wechat-green': {
    name: '微信生态绿',
    defaultTag: '官方资讯 · 行业前沿',
    badgeText: 'WECHAT OFFICIAL',
    volText: '2026 · ISSUE 02'
  }
};

/**
 * 从 Markdown 文本中自动智能提取封面元数据
 */
export function extractCoverMeta(markdownText, themeId = 'tech-blue') {
  const { meta, body } = parseFrontmatter(markdownText || '');
  const preset = THEME_COVER_PRESETS[themeId] || THEME_COVER_PRESETS['tech-blue'];

  // 1. 提取标题
  let title = meta.title || '';
  if (!title) {
    const h1Match = body.match(/^#\s+(.+)$/m);
    if (h1Match) {
      title = h1Match[1].trim();
    } else {
      // 取第一行非空文字
      const firstLine = body.split('\n').map(s => s.trim()).filter(Boolean)[0];
      title = firstLine ? firstLine.replace(/^[#*_\->\s]+/, '') : '在喧嚣时代重塑深度思考';
    }
  }

  // 2. 提取摘要/副标题
  let digest = meta.digest || '';
  if (!digest) {
    const quoteMatch = body.match(/^>\s+(.+)$/m);
    if (quoteMatch) {
      digest = quoteMatch[1].replace(/[*_`]/g, '').trim();
    } else {
      digest = stripMarkdown(body, 60) || '告别排版内耗，把时间还给思考与创造。';
    }
  }

  // 3. 提取作者与标签
  let author = meta.author || '野生宝藏箱';
  let tag = Array.isArray(meta.tags) && meta.tags.length > 0 ? meta.tags.join(' · ') : preset.defaultTag;

  return {
    title: title.slice(0, 36),
    digest: digest.slice(0, 60),
    author: author.slice(0, 16),
    tag: tag.slice(0, 24),
    badge: preset.badgeText,
    vol: preset.volText,
    website: 'MD2WX.ZANEVEN.COM'
  };
}

/**
 * HTML 转义并保留多行（\r\n / \n / \r 统一转 <br>，兼容 Windows 编辑的文案）
 */
function escapeMultiline(str) {
  if (!str) return '';
  return escapeHtml(str).replace(/\r\n|\n|\r/g, '<br>');
}

/**
 * 核心渲染器：根据主题与比例生成完整的封面 DOM 结构
 * @param {string} themeId
 * @param {'banner'|'square'} ratio
 * @param {Object} meta
 * @param {boolean} showSafeGuide - 是否叠加安全参考线
 */
export function renderCoverHtml(themeId = 'tech-blue', ratio = 'banner', meta = {}, showSafeGuide = false) {
  const safeTitle = escapeMultiline(meta.title || '在喧嚣时代重塑深度思考');
  const safeDigest = escapeMultiline(meta.digest || '真正的专注，是充满干扰的世界中守住内心的秩序');
  const safeAuthor = escapeHtml(meta.author || '野生宝藏箱');
  const safeTag = escapeHtml(meta.tag || '深度架构 · 极客手记');
  const safeBadge = escapeHtml(meta.badge || 'TECH BLOG');
  const safeVol = escapeHtml(meta.vol || '2026 · VOL.02');

  const isSquare = ratio === 'square';
  const themeClass = `cover-theme-${themeId}`;
  const ratioClass = isSquare ? 'ratio-square' : 'ratio-banner';

  const safeGuideHtml = showSafeGuide ? (
    isSquare ? `
      <div class="cover-safe-guide" title="微信信息流核心安全区">
        <div class="safe-guide-border">
          <span class="safe-guide-tag">微信次条/分享方图安全区</span>
        </div>
      </div>
    ` : `
      <div class="cover-wechat-crop-guide" title="微信公众号转发卡片默认 1:1 截取区 (左侧 500x500)">
        <div class="crop-guide-left-box">
          <span class="crop-guide-tag">微信转发卡片 1:1 截取区 (左半幅)</span>
        </div>
        <div class="crop-guide-right-dim">
          <span class="crop-guide-dim-tag">2.35:1 头条大图延展区</span>
        </div>
      </div>
    `
  ) : '';

  // 各主题的差异化徽标或装饰矢量
  let decoratorHtml = '';

  if (themeId === 'terminal-geek') {
    decoratorHtml = `
      <div class="term-window-controls">
        <span class="dot red"></span>
        <span class="dot yellow"></span>
        <span class="dot green"></span>
        <span class="term-prompt-title">bash - md2wx-article.sh (80x24)</span>
      </div>
    `;
  }

  // 微信生态绿的官方认证风格标识
  const wechatBadgeHtml = themeId === 'wechat-green' ? `
    <div class="wechat-verify-badge">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#07c160" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        <path d="m9 12 2 2 4-4"/>
      </svg>
      <span>官方认证排版</span>
    </div>
  ` : '';

  if (isSquare) {
    // 1:1 次条与分享卡片排版
    return `
      <div class="cover-canvas ${themeClass} ${ratioClass}">
        ${safeGuideHtml}
        ${decoratorHtml}
        <div class="cover-inner">
          <div class="square-top-bar">
            <span class="cover-badge">${safeBadge}</span>
            <span class="cover-vol">${safeVol}</span>
          </div>

          <div class="square-content-box">
            <div class="cover-category-chip">${safeTag}</div>
            <h1 class="square-main-title">${safeTitle}</h1>
            <p class="square-digest">${safeDigest}</p>
          </div>

          <div class="square-bottom-bar">
            <div class="author-wrap">
              <div class="author-dot"></div>
              <span class="author-name">${safeAuthor}</span>
              ${wechatBadgeHtml}
            </div>
          </div>
        </div>
      </div>
    `.trim();
  }

  // 2.35:1 横向大图排版（真机大字版：坚决剔除底部微型噪点栏与卡片微缩层级，核心字号提升 40%~60%）
  return `
    <div class="cover-canvas ${themeClass} ${ratioClass}">
      ${safeGuideHtml}
      ${decoratorHtml}
      <div class="cover-inner">
        <div class="banner-top-bar">
          <div class="top-left">
            <span class="cover-badge">${safeBadge}</span>
            <span class="cover-tag-banner">${safeTag}</span>
          </div>
          <div class="top-right">
            <span class="cover-vol">${safeVol}</span>
          </div>
        </div>

        <div class="banner-body">
          <div class="banner-left-col">
            <div class="headline-indicator"></div>
            <h1 class="banner-main-title">${safeTitle}</h1>
            <div class="banner-left-meta">
              <span class="banner-author-pill">${safeAuthor}</span>
              ${wechatBadgeHtml}
            </div>
          </div>

          <div class="banner-right-card">
            <div class="card-quote-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor">
                <path d="M4.583 17.321C3.553 16.227 3 15 3 13.011c0-3.5 2.457-6.637 6.03-8.188l.893 1.378c-3.335 1.804-3.987 4.145-4.247 5.621.537-.278 1.24-.375 1.929-.311 1.804.167 3.226 1.648 3.226 3.489a3.5 3.5 0 0 1-3.5 3.5c-1.073 0-2.099-.49-2.748-1.179zm10 0C13.553 16.227 13 15 13 13.011c0-3.5 2.457-6.637 6.03-8.188l.893 1.378c-3.335 1.804-3.987 4.145-4.247 5.621.537-.278 1.24-.375 1.929-.311 1.804.167 3.226 1.648 3.226 3.489a3.5 3.5 0 0 1-3.5 3.5c-1.073 0-2.099-.49-2.748-1.179z"/>
              </svg>
            </div>
            <p class="banner-digest">${safeDigest}</p>
            <div class="card-signature">— ${safeAuthor}</div>
          </div>
        </div>
      </div>
    </div>
  `.trim();
}

/**
 * 生成可直接内嵌在微信公众号可复制正文顶部的富文本封面 HTML (自包含纯内联样式)
 * 适配手机屏幕阅读：标题与导读字号显著放大，告别蚂蚁字
 * @param {string} themeId
 * @param {Object} meta
 * @returns {string}
 */
export function renderWechatArticleHeaderCover(themeId = 'tech-blue', meta = {}) {
  const safeTitle = escapeMultiline(meta.title || '在喧嚣时代重塑深度思考');
  const safeDigest = escapeMultiline(meta.digest || '真正的专注，是在充满干扰的世界中守住内心的秩序');
  const safeAuthor = escapeHtml(meta.author || '野生宝藏箱');
  const safeBadge = escapeHtml(meta.badge || 'TECH BLOG');
  const safeVol = escapeHtml(meta.vol || '2026 · VOL.02');

  if (themeId === 'acid-bold') {
    return `
<section style="margin: 0 0 28px 0; background: #fee500; border: 3.5px solid #000000; box-shadow: 6px 6px 0 #000000; padding: 26px 20px; box-sizing: border-box; text-align: left;">
  <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
    <span style="background: #000000; color: #fee500; font-size: 13px; font-weight: 900; padding: 4px 12px; border-radius: 3px; letter-spacing: 1px;">${safeBadge}</span>
    <span style="font-size: 14px; font-weight: 900; color: #000000; font-family: monospace;">${safeVol}</span>
  </div>
  <div style="width: 50px; height: 7px; background: #000000; margin-bottom: 14px;"></div>
  <h1 style="font-size: 25px; font-weight: 900; line-height: 1.28; color: #000000; margin: 0 0 12px 0; letter-spacing: -0.3px;">${safeTitle}</h1>
  <p style="font-size: 16px; line-height: 1.6; color: #171717; margin: 0 0 18px 0; font-weight: 600;">${safeDigest}</p>
  <div style="border-top: 2.5px solid #000000; padding-top: 12px; display: flex; align-items: center; justify-content: space-between;">
    <span style="font-size: 14px; font-weight: 900; color: #000000;">${safeAuthor} // 先锋态度</span>
  </div>
</section>`.trim();
  }

  if (themeId === 'terminal-geek') {
    return `
<section style="margin: 0 0 28px 0; background: #020617; border: 1.5px solid #065f46; border-radius: 10px; overflow: hidden; box-sizing: border-box; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; text-align: left;">
  <div style="background: #090e1a; padding: 10px 14px; border-bottom: 1px solid #1e293b; display: flex; align-items: center;">
    <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #ef4444; margin-right: 6px;"></span>
    <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #f59e0b; margin-right: 6px;"></span>
    <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #10b981; margin-right: 12px;"></span>
    <span style="font-size: 12px; color: #64748b;">bash - post.sh (${safeVol})</span>
  </div>
  <div style="padding: 24px 20px;">
    <div style="font-size: 13px; color: #10b981; font-weight: 800; margin-bottom: 10px;">&gt; ./render --theme=terminal</div>
    <h1 style="font-size: 24px; font-weight: 900; line-height: 1.32; color: #34d399; margin: 0 0 12px 0; letter-spacing: 0.3px;">${safeTitle}</h1>
    <p style="font-size: 15.5px; line-height: 1.6; color: #a7f3d0; margin: 0 0 16px 0;">${safeDigest}</p>
    <div style="border-top: 1px solid #1e293b; padding-top: 12px; display: flex; align-items: center; justify-content: space-between;">
      <span style="font-size: 13px; color: #10b981; font-weight: 700;">// ${safeAuthor}</span>
    </div>
  </div>
</section>`.trim();
  }

  if (themeId === 'vintage-news') {
    return `
<section style="margin: 0 0 28px 0; background: #fdfbf7; border: 4px double #44403c; padding: 24px 20px; box-sizing: border-box; font-family: 'Songti SC', SimSun, Georgia, serif; text-align: left;">
  <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #d6d3d1; padding-bottom: 10px; margin-bottom: 16px;">
    <span style="background: #292524; color: #fef3c7; font-size: 13px; font-weight: 700; padding: 3px 10px; border-radius: 2px;">${safeBadge}</span>
    <span style="font-size: 14px; color: #78716c; font-weight: 600;">${safeVol}</span>
  </div>
  <h1 style="font-size: 25px; font-weight: 900; line-height: 1.32; color: #1c1917; margin: 0 0 12px 0; letter-spacing: 0.5px;">${safeTitle}</h1>
  <p style="font-size: 16px; line-height: 1.65; color: #44403c; margin: 0 0 16px 0;">${safeDigest}</p>
  <div style="border-top: 1px solid #d6d3d1; padding-top: 10px; display: flex; align-items: center; justify-content: space-between;">
    <span style="font-size: 14px; font-weight: 800; color: #854d0e;">社论特刊 · ${safeAuthor}</span>
  </div>
</section>`.trim();
  }

  if (themeId === 'warm-memo') {
    return `
<section style="margin: 0 0 28px 0; background: #fff7ed; border: 1.5px solid #fed7aa; border-radius: 14px; padding: 24px 20px; box-sizing: border-box; text-align: left; box-shadow: 0 4px 16px rgba(234, 88, 12, 0.06);">
  <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;">
    <span style="background: #ea580c; color: #ffffff; font-size: 13px; font-weight: 800; padding: 4px 12px; border-radius: 999px;">${safeBadge}</span>
    <span style="font-size: 13px; color: #ea580c; font-weight: 700;">${safeVol}</span>
  </div>
  <h1 style="font-size: 24px; font-weight: 900; line-height: 1.32; color: #292524; margin: 0 0 12px 0;">${safeTitle}</h1>
  <p style="font-size: 15.5px; line-height: 1.6; color: #57534e; margin: 0 0 16px 0;">${safeDigest}</p>
  <div style="border-top: 1px dashed #fed7aa; padding-top: 12px; display: flex; align-items: center; justify-content: space-between;">
    <span style="font-size: 14px; font-weight: 800; color: #ea580c;">便签手记 · ${safeAuthor}</span>
  </div>
</section>`.trim();
  }

  if (themeId === 'warm-orange') {
    return `
<section style="margin: 0 0 28px 0; border-radius: 14px; padding: 26px 20px; background: linear-gradient(135deg, #ea580c 0%, #9a3412 100%); box-shadow: 0 8px 24px rgba(234, 88, 12, 0.2); box-sizing: border-box; text-align: left;">
  <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
    <span style="background: #ffffff; color: #ea580c; font-size: 13px; font-weight: 900; padding: 4px 12px; border-radius: 4px; letter-spacing: 1px;">${safeBadge}</span>
    <span style="font-size: 13px; color: #fed7aa; font-family: monospace;">${safeVol}</span>
  </div>
  <div style="width: 44px; height: 5px; background: #fed7aa; border-radius: 2px; margin-bottom: 14px;"></div>
  <h1 style="font-size: 25px; font-weight: 900; line-height: 1.3; color: #ffffff; margin: 0 0 12px 0;">${safeTitle}</h1>
  <p style="font-size: 16px; line-height: 1.6; color: #ffedd5; margin: 0 0 18px 0; font-weight: 500;">${safeDigest}</p>
  <div style="border-top: 1px solid rgba(255,255,255,0.25); padding-top: 12px; display: flex; align-items: center; justify-content: space-between;">
    <span style="font-size: 14px; font-weight: 800; color: #fed7aa;">${safeAuthor} // 阳光日常</span>
  </div>
</section>`.trim();
  }

  if (themeId === 'wechat-green') {
    return `
<section style="margin: 0 0 28px 0; border-radius: 14px; padding: 26px 20px; background: linear-gradient(135deg, #064e3b 0%, #022c22 100%); border: 1px solid rgba(74, 222, 128, 0.25); box-sizing: border-box; text-align: left;">
  <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
    <span style="background: #07c160; color: #ffffff; font-size: 13px; font-weight: 900; padding: 4px 12px; border-radius: 4px; letter-spacing: 1px;">${safeBadge}</span>
    <span style="font-size: 13px; color: #86efac; font-family: monospace;">${safeVol}</span>
  </div>
  <div style="width: 44px; height: 5px; background: #07c160; border-radius: 2px; margin-bottom: 14px;"></div>
  <h1 style="font-size: 25px; font-weight: 900; line-height: 1.3; color: #ffffff; margin: 0 0 12px 0;">${safeTitle}</h1>
  <p style="font-size: 16px; line-height: 1.6; color: #dcfce7; margin: 0 0 18px 0; font-weight: 500;">${safeDigest}</p>
  <div style="border-top: 1px solid rgba(255,255,255,0.2); padding-top: 12px; display: flex; align-items: center; justify-content: space-between;">
    <span style="font-size: 14px; font-weight: 800; color: #4ade80;">官方认证 · ${safeAuthor}</span>
  </div>
</section>`.trim();
  }

  if (themeId === 'elegant-purple') {
    return `
<section style="margin: 0 0 28px 0; border-radius: 14px; padding: 26px 20px; background: linear-gradient(135deg, #2e1065 0%, #0f172a 100%); border: 1px solid rgba(192, 132, 252, 0.3); box-sizing: border-box; text-align: left;">
  <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
    <span style="background: #7c3aed; color: #ffffff; font-size: 13px; font-weight: 900; padding: 4px 12px; border-radius: 4px; letter-spacing: 1px;">${safeBadge}</span>
    <span style="font-size: 13px; color: #c084fc; font-family: monospace;">${safeVol}</span>
  </div>
  <div style="width: 44px; height: 5px; background: #c084fc; border-radius: 2px; margin-bottom: 14px;"></div>
  <h1 style="font-size: 25px; font-weight: 900; line-height: 1.3; color: #ffffff; margin: 0 0 12px 0;">${safeTitle}</h1>
  <p style="font-size: 16px; line-height: 1.6; color: #e9d5ff; margin: 0 0 18px 0; font-weight: 500;">${safeDigest}</p>
  <div style="border-top: 1px solid rgba(255,255,255,0.2); padding-top: 12px; display: flex; align-items: center; justify-content: space-between;">
    <span style="font-size: 14px; font-weight: 800; color: #c084fc;">美学设计 · ${safeAuthor}</span>
  </div>
</section>`.trim();
  }

  // 默认现代科技蓝 (tech-blue)
  return `
<section style="margin: 0 0 28px 0; border-radius: 14px; padding: 26px 20px; background: radial-gradient(circle at 80% 20%, #1e3a8a 0%, #0a0f1d 70%); border: 1px solid rgba(56, 189, 248, 0.3); box-shadow: 0 8px 24px rgba(0,0,0,0.15); box-sizing: border-box; text-align: left;">
  <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
    <span style="background: #2563eb; color: #ffffff; font-size: 13px; font-weight: 900; padding: 4px 12px; border-radius: 4px; letter-spacing: 1px;">${safeBadge}</span>
    <span style="font-size: 13px; color: #38bdf8; font-family: monospace; letter-spacing: 1px;">${safeVol}</span>
  </div>
  <div style="width: 44px; height: 5px; background: #38bdf8; border-radius: 2px; margin-bottom: 14px;"></div>
  <h1 style="font-size: 25px; font-weight: 900; line-height: 1.3; color: #ffffff; margin: 0 0 12px 0; letter-spacing: 0.2px;">${safeTitle}</h1>
  <p style="font-size: 16px; line-height: 1.6; color: #cbd5e1; margin: 0 0 18px 0; font-weight: 500;">${safeDigest}</p>
  <div style="border-top: 1px solid rgba(255,255,255,0.18); padding-top: 12px; display: flex; align-items: center; justify-content: space-between;">
    <span style="font-size: 14px; font-weight: 800; color: #38bdf8;">${safeAuthor} // 深度手记</span>
  </div>
</section>`.trim();
}

/**
 * MD2WX 官方落地页 (Landing Page) 客户端交互逻辑
 * 遵循规范：无任何 Emoji，全矢量 SVG，原生 JS，毫秒级响应
 */

// 13 套内置主题展示元数据
const THEMES_DATA = [
  {
    id: 'tech-blue',
    name: '现代科技蓝',
    color: '#0284c7',
    badge: 'DEFAULT',
    scene: 'AI 技术架构 · 开发者手记 · 工程复盘',
    desc: '经典极客科技风。微冷蓝双色指示条、内联自包含代码块、SF Mono 字体栈，专为深度技术硬核长文打造。',
    preview: './assets/previews/tech-blue.png',
    features: ['高对比度科技蓝边条', '终端三色指示灯代码框', '清爽三线学术表']
  },
  {
    id: 'terminal-geek',
    name: '极客终端黑',
    color: '#10b981',
    badge: 'DARK / GEEK',
    scene: 'Linux 运维 · 黑客工具 · 命令行生产力',
    desc: '全暗色终端界面美学。深墨绿荧光配色、纯等宽字体渲染、Mac 终端窗口容器，沉浸式极客代码体验。',
    preview: './assets/previews/terminal-geek.png',
    features: ['暗黑极夜高对比度', '绿色等宽字符光标', '终端窗口自包含容器']
  },
  {
    id: 'acid-bold',
    name: '先锋野兽派',
    color: '#e11d48',
    badge: 'AVANT-GARDE',
    scene: '产品发布 · 行业批判 · 先锋设计观察',
    desc: '打破常规的酸性设计。高饱和度硬核撞色、几何感重磅粗黑边框、张扬的视觉骨架，让观点过目难忘。',
    preview: './assets/previews/acid-bold.png',
    features: ['重磅加粗几何黑边', '高明度高饱和撞色', '视觉冲击力大标题']
  },
  {
    id: 'vintage-news',
    name: '复古报刊风',
    color: '#78350f',
    badge: 'EDITORIAL',
    scene: '深度商业报道 · 人文随笔 · 行业特稿',
    desc: '经典实体报刊版面复刻。双细线分割线、典雅学术三线表、经典双引号名言框，营造纸质书刊的厚重质感。',
    preview: './assets/previews/vintage-news.png',
    features: ['经典古典双细线', '报纸专栏大引号引言', '学术级顶底粗线表']
  },
  {
    id: 'warm-memo',
    name: '日系温暖便签',
    color: '#d97706',
    badge: 'CREATIVE',
    scene: '读书笔记 · 职场方法论 · 生活复盘',
    desc: '日系手账与便签质感。淡黄色柔和底纸、圆角便签卡片、清新的图钉与索引标签，温润亲切的阅读体验。',
    preview: './assets/previews/warm-memo.png',
    features: ['日系暖调柔光底色', '便签纸拟态导读卡', '圆角胶囊元数据标']
  },
  {
    id: 'elegant-purple',
    name: '学术优雅紫',
    color: '#7c3aed',
    badge: 'ACADEMIC',
    scene: '科研综述 · 行业白皮书 · 高端智库报告',
    desc: '深邃高贵的学者紫。低调稳健的排版节奏、优雅的渐变分界、严谨的文献引用样式，适合专业报告与长文。',
    preview: './assets/previews/elegant-purple.png',
    features: ['深邃优雅学者紫', '细致文末脚注文献', '对称层次标题装饰']
  },
  {
    id: 'wechat-green',
    name: '微信经典绿',
    color: '#059669',
    badge: 'OFFICIAL',
    scene: '官方通告 · 业务指南 · 平台动态',
    desc: '微信生态原生品牌绿。完美融入微信阅读体验环境，亲和自然，极简干练，受众接受度最高。',
    preview: './assets/previews/wechat-green.png',
    features: ['官方生态标志绿', '轻量扁平信息流', '高兼容性内联块']
  },
  {
    id: 'warm-orange',
    name: '暖阳活力橙',
    color: '#ea580c',
    badge: 'VIBRANT',
    scene: '个人成长 · 运营干货 · 晨间灵感',
    desc: '充满生机与活力的暖橙。点亮视觉焦点，适合快节奏干货输出、效率工具分享与灵感速记。',
    preview: './assets/previews/warm-orange.png',
    features: ['高穿透力活力橙', '醒目数字序号标记', '动态对比高光块']
  },
  {
    id: 'dark-night',
    name: '极简暗夜',
    color: '#3b82f6',
    badge: 'NIGHT MODE',
    scene: '深夜随笔 · 电影评论 · 音乐分享',
    desc: '护眼深邃纯黑。深空灰渐变过渡、冷色夜光文字、低对比度柔和背景，夜间微信阅读绝佳伴侣。',
    preview: './assets/previews/dark-night.png',
    features: ['低蓝光护眼深色', '冷调荧光微光点缀', '沉浸式无噪阅读']
  },
  {
    id: 'forest-green',
    name: '森野墨绿',
    color: '#2f6b4f',
    badge: 'NATURAL',
    scene: '自然随笔 · 慢生活记录 · 深度书评',
    desc: '深林墨绿与米纸底色的自然书卷气。衬线字体排印、菱形项目符号、渐变分割线，沉静克制的自然系书写。',
    preview: './assets/previews/forest-green.png',
    features: ['深林墨绿双色条', '米纸底衬线书卷气', '菱形符号自然节奏']
  },
  {
    id: 'terracotta-clay',
    name: '陶土亚麻',
    color: '#b25b38',
    badge: 'HANDMADE',
    scene: '生活方式 · 器物手作 · 人文随笔',
    desc: '陶土橙棕与亚麻米色调的手作质感。温润质朴的方图引言卡、高亮小节标记，器物与生活之美自然流露。',
    preview: './assets/previews/terracotta-clay.png',
    features: ['陶土暖棕低饱和', '亚麻米色温润底', '手作质感引言卡']
  },
  {
    id: 'morandi-mist',
    name: '莫兰迪雾灰',
    color: '#6e7f8d',
    badge: 'MINIMAL',
    scene: '文艺随笔 · 影评乐评 · 极简书写',
    desc: '低饱和灰蓝调的莫兰迪色系。极简左线标题、圆点序号、浅色代码块与三线学术表，安静克制的极简主义。',
    preview: './assets/previews/morandi-mist.png',
    features: ['雾霾蓝灰莫兰迪调', '浅色代码块三线表', '极简克制排版节奏']
  },
  {
    id: 'pastel-cream',
    name: '奶油粉彩',
    color: '#b76e79',
    badge: 'PASTEL',
    scene: '情感随笔 · 手账日记 · 美学生活',
    desc: '奶油白与豆沙粉的柔和低饱和配色。胶囊标题、气泡引言卡与暖粉高亮，轻甜治愈的阅读氛围。',
    preview: './assets/previews/pastel-cream.png',
    features: ['豆沙玫瑰柔粉调', '奶油白治愈底色', '气泡卡轻甜气质']
  }
];

import { applyVersion } from './version.js';

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  applyVersion();
  initCopyButtons();
  initThemeShowcase();
  initHeroThemeSwitch();
});

// Toast 提示工具
function showToast(message) {
  let toast = document.getElementById('toast-msg');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast-msg';
    toast.className = 'toast-msg';
    document.body.appendChild(toast);
  }
  toast.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
    <span>${message}</span>
  `;
  toast.classList.add('show');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.classList.remove('show');
  }, 2200);
}

// 终端与代码一键复制
function initCopyButtons() {
  document.querySelectorAll('[data-copy]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const text = btn.getAttribute('data-copy');
      if (!text) return;
      try {
        await navigator.clipboard.writeText(text);
        showToast('已复制到剪贴板：' + text);
      } catch (e) {
        showToast('复制失败，请手动复制');
      }
    });
  });
}

// 主题画廊交互
function initThemeShowcase() {
  const tabContainer = document.getElementById('theme-tab-nav');
  const infoBadge = document.getElementById('theme-info-badge');
  const infoTitle = document.getElementById('theme-info-title');
  const infoDesc = document.getElementById('theme-info-desc');
  const metaScene = document.getElementById('theme-meta-scene');
  const metaFeatures = document.getElementById('theme-meta-features');
  const previewImg = document.getElementById('theme-preview-img');

  if (!tabContainer || !infoTitle) return;

  // 渲染主题 Tabs
  tabContainer.innerHTML = THEMES_DATA.map((t, index) => `
    <button class="theme-tab-btn ${index === 0 ? 'active' : ''}" data-theme-id="${t.id}" type="button">
      <span class="theme-color-dot" style="background-color: ${t.color};"></span>
      <span>${t.name}</span>
    </button>
  `).join('');

  // 切换函数（用序号兜底快速连点：只让最后一次点击更新预览）
  let previewToken = 0;

  function switchTheme(themeId) {
    const theme = THEMES_DATA.find(t => t.id === themeId);
    if (!theme) return;

    // 更新 Tab 选中状态
    tabContainer.querySelectorAll('.theme-tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-theme-id') === themeId);
    });

    // 更新文本信息
    infoBadge.textContent = theme.badge;
    infoBadge.style.color = theme.color;
    infoTitle.textContent = theme.name;
    infoDesc.textContent = theme.desc;
    metaScene.textContent = theme.scene;
    metaFeatures.textContent = theme.features.join(' · ');

    // 预载完成后再换图，失败时也恢复亮度，避免预览一直灰着
    const token = ++previewToken;
    const nextSrc = theme.preview;
    previewImg.style.opacity = '0.3';

    const preload = new Image();
    const showPreview = () => {
      if (token !== previewToken) return;
      previewImg.src = nextSrc;
      previewImg.style.opacity = '1';
    };
    preload.onload = showPreview;
    preload.onerror = showPreview;
    preload.src = nextSrc;
  }

  // 绑定点击
  tabContainer.addEventListener('click', (e) => {
    const btn = e.target.closest('.theme-tab-btn');
    if (btn) {
      const id = btn.getAttribute('data-theme-id');
      switchTheme(id);
    }
  });

  // 初始加载第一个
  switchTheme(THEMES_DATA[0].id);
}

// Hero 演示区的主题切换
// 预览骨架由 CSS 按 data-preview-theme 整体切换，这里只负责状态与主题色
function initHeroThemeSwitch() {
  const switchBtns = document.querySelectorAll('.showcase-theme-btn');
  const previewRoot = document.querySelector('.showcase-right');
  const showcase = document.querySelector('.hero-showcase');
  const metaLabel = document.querySelector('.wx-sim-meta span:last-child');

  if (!previewRoot || switchBtns.length === 0) return;

  const HERO_THEMES = {
    'tech-blue': { label: '现代科技蓝', accent: '#38bdf8' },
    'terminal-geek': { label: '极客终端黑', accent: '#34d399' },
    'vintage-news': { label: '复古报刊', accent: '#f59e0b' },
    'acid-bold': { label: '先锋野兽派', accent: '#facc15' }
  };

  function applyTheme(themeId) {
    const theme = HERO_THEMES[themeId] || HERO_THEMES['tech-blue'];
    const key = HERO_THEMES[themeId] ? themeId : 'tech-blue';

    previewRoot.setAttribute('data-preview-theme', key);
    showcase.style.setProperty('--showcase-accent', theme.accent);
    if (metaLabel) metaLabel.textContent = `微信公众号 · ${theme.label}`;

    switchBtns.forEach((btn) => {
      const isActive = btn.getAttribute('data-theme') === key;
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-pressed', String(isActive));
    });
  }

  switchBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      applyTheme(btn.getAttribute('data-theme'));
    });
  });

  // 初始状态与 HTML 中的默认主题保持一致
  applyTheme(previewRoot.getAttribute('data-preview-theme') || 'tech-blue');
}

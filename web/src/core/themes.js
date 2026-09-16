/**
 * MD2WX 前端主题引擎
 * 内置 9 套高质感微信排版设计主题，支持深度合并与自定义扩展
 */

export const DEFAULT_THEME_ID = 'tech-blue';

export const FALLBACK_BASE_THEME = {
  id: 'tech-blue',
  name: '现代科技蓝 (默认)',
  description: '沉稳极客科技风，适合开发者手记、架构复盘与前沿技术干货',
  colors: {
    accent: '#2563eb',
    accent_bg: '#eff6ff',
    text_color: '#27272a',
    sub_color: '#71717a',
    border_color: '#e4e4e7',
    code_bg: '#18181b',
    code_text: '#e4e4e7',
    quote_bg: '#f4f4f5',
    page_bg: '#ffffff'
  },
  typography: {
    font_family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    font_size_base: '15.5px',
    line_height_base: '1.8',
    letter_spacing: '0.4px',
    paragraph_indent: false
  },
  styles: {
    container: 'clean',
    h1: 'underline',
    h2: 'left_bar',
    h3: 'diamond',
    quote: 'left_stripe',
    code: 'mac_dark',
    table: 'zebra',
    list: 'bullet',
    hr: 'line'
  }
};

export const BUILTIN_THEMES = {
  "acid-bold": {
    "id": "acid-bold",
    "name": "先锋野兽派 (Neo-Brutalism)",
    "description": "高反差黑框硬投影、粗线条几何色块、波普冲击力与态度先锋排版，青年态度发声首选",
    "colors": {
      "accent": "#000000",
      "accent_bg": "#facc15",
      "text_color": "#09090b",
      "sub_color": "#52525b",
      "border_color": "#000000",
      "code_bg": "#09090b",
      "code_text": "#facc15",
      "quote_bg": "#fef08a",
      "page_bg": "#ffffff"
    },
    "typography": {
      "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      "font_size_base": "15.5px",
      "line_height_base": "1.75",
      "letter_spacing": "0.3px",
      "paragraph_indent": false
    },
    "styles": {
      "container": "brutalist",
      "h1": "brutalist",
      "h2": "brutalist_box",
      "h3": "circle_badge",
      "quote": "brutalist",
      "code": "mac_dark",
      "table": "grid",
      "list": "square",
      "hr": "line"
    }
  },
  "dark-night": {
    "id": "dark-night",
    "name": "暗黑极客风 (Dark Night)",
    "description": "沉浸暗黑质感，深蓝灰底色与冷冽荧光蓝，适合夜间极客阅读",
    "colors": {
      "accent": "#38bdf8",
      "accent_bg": "#1e293b",
      "text_color": "#f1f5f9",
      "sub_color": "#94a3b8",
      "border_color": "#334155",
      "code_bg": "#0f172a",
      "code_text": "#e2e8f0",
      "quote_bg": "#1e293b",
      "page_bg": "#0f172a"
    },
    "typography": {
      "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      "font_size_base": "15.5px",
      "line_height_base": "1.8",
      "letter_spacing": "0.4px",
      "paragraph_indent": false
    },
    "styles": {
      "container": "dark",
      "h1": "underline",
      "h2": "left_bar",
      "h3": "diamond",
      "quote": "left_stripe",
      "code": "mac_dark",
      "table": "grid",
      "list": "bullet",
      "hr": "line"
    }
  },
  "elegant-purple": {
    "id": "elegant-purple",
    "name": "先锋优雅紫 (Modern Aesthetic)",
    "description": "现代雅致紫调，微阴影质感卡片与柔和色块排版，适合设计美学、独立思考、艺术与产品发布",
    "colors": {
      "accent": "#7c3aed",
      "accent_bg": "#f5f3ff",
      "text_color": "#27272a",
      "sub_color": "#71717a",
      "border_color": "#ede9fe",
      "code_bg": "#18181b",
      "code_text": "#f5f3ff",
      "quote_bg": "#faf5ff",
      "page_bg": "#ffffff"
    },
    "typography": {
      "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      "font_size_base": "15.5px",
      "line_height_base": "1.8",
      "letter_spacing": "0.4px",
      "paragraph_indent": false
    },
    "styles": {
      "container": "card",
      "h1": "underline",
      "h2": "bubble_bg",
      "h3": "circle_badge",
      "quote": "bubble_card",
      "code": "mac_dark",
      "table": "zebra",
      "list": "diamond",
      "hr": "gradient"
    }
  },
  "tech-blue": {
    "id": "tech-blue",
    "name": "现代科技蓝 (默认)",
    "description": "沉稳极客科技风，硅谷现代排版，适合开发者手记、架构复盘与前沿技术干货",
    "colors": {
      "accent": "#2563eb",
      "accent_bg": "#eff6ff",
      "text_color": "#27272a",
      "sub_color": "#71717a",
      "border_color": "#e4e4e7",
      "code_bg": "#18181b",
      "code_text": "#e4e4e7",
      "quote_bg": "#f4f4f5",
      "page_bg": "#ffffff"
    },
    "typography": {
      "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      "font_size_base": "15.5px",
      "line_height_base": "1.8",
      "letter_spacing": "0.4px",
      "paragraph_indent": false
    },
    "styles": {
      "container": "clean",
      "h1": "underline",
      "h2": "left_bar",
      "h3": "diamond",
      "quote": "left_stripe",
      "code": "mac_dark",
      "table": "zebra",
      "list": "bullet",
      "hr": "line"
    }
  },
  "terminal-geek": {
    "id": "terminal-geek",
    "name": "极客终端 (Terminal / Dev Note)",
    "description": "深黑终端底色、等宽代码字体、终端命令提示符与青绿发光强调色，极客笔记首选",
    "colors": {
      "accent": "#10b981",
      "accent_bg": "#064e3b",
      "text_color": "#e2e8f0",
      "sub_color": "#94a3b8",
      "border_color": "#1e293b",
      "code_bg": "#020617",
      "code_text": "#34d399",
      "quote_bg": "#0f172a",
      "page_bg": "#0b0f19"
    },
    "typography": {
      "font_family": "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
      "font_size_base": "15px",
      "line_height_base": "1.75",
      "letter_spacing": "0.3px",
      "paragraph_indent": false
    },
    "styles": {
      "container": "dark",
      "h1": "terminal",
      "h2": "terminal_prompt",
      "h3": "slash",
      "quote": "terminal_box",
      "code": "terminal",
      "table": "grid",
      "list": "arrow",
      "hr": "terminal_dash"
    }
  },
  "vintage-news": {
    "id": "vintage-news",
    "name": "复古报刊 (Vintage Press)",
    "description": "浅牛皮纸微黄底纹、粗衬线标题、古典双细线排版与学术三线表，人文书卷气",
    "colors": {
      "accent": "#854d0e",
      "accent_bg": "#fef3c7",
      "text_color": "#292524",
      "sub_color": "#78716c",
      "border_color": "#d6d3d1",
      "code_bg": "#292524",
      "code_text": "#f5f5f4",
      "quote_bg": "#fcfaf2",
      "page_bg": "#fdfbf7"
    },
    "typography": {
      "font_family": "-apple-system-font, 'Songti SC', 'Noto Serif SC', 'Source Han Serif SC', SimSun, Georgia, serif",
      "font_size_base": "15.5px",
      "line_height_base": "1.9",
      "letter_spacing": "0.6px",
      "paragraph_indent": false
    },
    "styles": {
      "container": "paper",
      "h1": "double_line",
      "h2": "serif_badge",
      "h3": "diamond",
      "quote": "elegant_quote",
      "code": "mac_dark",
      "table": "three_line",
      "list": "diamond",
      "hr": "asterisk"
    }
  },
  "warm-memo": {
    "id": "warm-memo",
    "name": "温暖便签 (Healing Note)",
    "description": "日系奶油柔色系、胶囊圆角色块、日系便签贴纸感与治愈手作排版，生活随笔首选",
    "colors": {
      "accent": "#ea580c",
      "accent_bg": "#fff7ed",
      "text_color": "#292524",
      "sub_color": "#78716c",
      "border_color": "#fed7aa",
      "code_bg": "#1c1917",
      "code_text": "#ffedd5",
      "quote_bg": "#fffbeb",
      "page_bg": "#fefcf8"
    },
    "typography": {
      "font_family": "-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif",
      "font_size_base": "15.5px",
      "line_height_base": "1.85",
      "letter_spacing": "0.4px",
      "paragraph_indent": false
    },
    "styles": {
      "container": "memo",
      "h1": "capsule",
      "h2": "pill_badge",
      "h3": "highlight_bg",
      "quote": "paper_memo",
      "code": "mac_dark",
      "table": "zebra",
      "list": "bullet",
      "hr": "gradient"
    }
  },
  "warm-orange": {
    "id": "warm-orange",
    "name": "温暖活力橙 (Warm Orange)",
    "description": "温暖活力橙色调，适合生活随笔、读书感悟、情感故事与日记",
    "colors": {
      "accent": "#ea580c",
      "accent_bg": "#fff7ed",
      "text_color": "#292524",
      "sub_color": "#78716c",
      "border_color": "#e7e5e4",
      "code_bg": "#1c1917",
      "code_text": "#f5f5f4",
      "quote_bg": "#fafaf9",
      "page_bg": "#ffffff"
    },
    "typography": {
      "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      "font_size_base": "15.5px",
      "line_height_base": "1.8",
      "letter_spacing": "0.4px",
      "paragraph_indent": false
    },
    "styles": {
      "container": "clean",
      "h1": "underline",
      "h2": "left_bar",
      "h3": "diamond",
      "quote": "left_stripe",
      "code": "mac_dark",
      "table": "zebra",
      "list": "bullet",
      "hr": "line"
    }
  },
  "wechat-green": {
    "id": "wechat-green",
    "name": "微信生态绿 (Official Green)",
    "description": "经典微信官方绿调，严谨清爽规范排版，适合行业资讯速递、官方发布与社群运营",
    "colors": {
      "accent": "#07c160",
      "accent_bg": "#f0fdf4",
      "text_color": "#1f2937",
      "sub_color": "#6b7280",
      "border_color": "#e5e7eb",
      "code_bg": "#111827",
      "code_text": "#f3f4f6",
      "quote_bg": "#f9fafb",
      "page_bg": "#ffffff"
    },
    "typography": {
      "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      "font_size_base": "15.5px",
      "line_height_base": "1.8",
      "letter_spacing": "0.4px",
      "paragraph_indent": false
    },
    "styles": {
      "container": "clean",
      "h1": "underline",
      "h2": "left_bar",
      "h3": "diamond",
      "quote": "left_stripe",
      "code": "mac_dark",
      "table": "zebra",
      "list": "bullet",
      "hr": "line"
    }
  }
};

/**
 * 递归深度合并对象
 */
export function deepMerge(base, override) {
  const result = { ...base };
  for (const [key, val] of Object.entries(override || {})) {
    if (val && typeof val === 'object' && !Array.isArray(val) && result[key] && typeof result[key] === 'object' && !Array.isArray(result[key])) {
      result[key] = deepMerge(result[key], val);
    } else {
      result[key] = val;
    }
  }
  return result;
}

/**
 * 向后兼容层包装
 */
export function wrapThemeCompatibility(theme) {
  const result = { ...theme };
  const colors = result.colors || {};
  for (const [k, v] of Object.entries(colors)) {
    if (!(k in result)) {
      result[k] = v;
    }
  }
  const typography = result.typography || {};
  for (const [k, v] of Object.entries(typography)) {
    if (!(k in result)) {
      result[k] = v;
    }
  }
  const styles = result.styles || {};
  for (const [k, v] of Object.entries(styles)) {
    const flatKey = `${k}_style`;
    if (!(flatKey in result)) {
      result[flatKey] = v;
    }
  }
  return result;
}

/**
 * 获取指定主题配置，自动注入深度兜底与兼容字段
 */
export function getTheme(themeId = DEFAULT_THEME_ID, customOverride = null) {
  let target = BUILTIN_THEMES[themeId] || BUILTIN_THEMES[DEFAULT_THEME_ID] || FALLBACK_BASE_THEME;
  let merged = deepMerge(FALLBACK_BASE_THEME, target);
  if (customOverride && typeof customOverride === 'object') {
    merged = deepMerge(merged, customOverride);
  }
  return wrapThemeCompatibility(merged);
}

/**
 * 列出所有内置主题摘要
 */
export function listThemes() {
  return Object.values(BUILTIN_THEMES).map(t => ({
    id: t.id,
    name: t.name,
    description: t.description,
    accent: t.colors?.accent || '#2563eb',
    page_bg: t.colors?.page_bg || '#ffffff',
    container: t.styles?.container || 'clean'
  }));
}

/**
 * MD2WX 前端主题引擎
 * 主题数据构建期直接导入 md2wx/themes/*.json (与 Python CLI 共用单一数据源)，
 * 前端只保留兜底合并与兼容包装逻辑
 */
import themeAcidBold from '../../../md2wx/themes/acid-bold.json';
import themeDarkNight from '../../../md2wx/themes/dark-night.json';
import themeElegantPurple from '../../../md2wx/themes/elegant-purple.json';
import themeTechBlue from '../../../md2wx/themes/tech-blue.json';
import themeTerminalGeek from '../../../md2wx/themes/terminal-geek.json';
import themeVintageNews from '../../../md2wx/themes/vintage-news.json';
import themeWarmMemo from '../../../md2wx/themes/warm-memo.json';
import themeWarmOrange from '../../../md2wx/themes/warm-orange.json';
import themeWechatGreen from '../../../md2wx/themes/wechat-green.json';

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
  'acid-bold': themeAcidBold,
  'dark-night': themeDarkNight,
  'elegant-purple': themeElegantPurple,
  'tech-blue': themeTechBlue,
  'terminal-geek': themeTerminalGeek,
  'vintage-news': themeVintageNews,
  'warm-memo': themeWarmMemo,
  'warm-orange': themeWarmOrange,
  'wechat-green': themeWechatGreen
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

/**
 * 判断主题是否为暗色配色（优先读取主题 JSON 的 dark 标记，
 * 兼容未标记主题的 page_bg 色值启发式）
 */
export function isDarkTheme(theme) {
  if (!theme) return false;
  if (theme.dark === true) return true;
  return ['#0b0f19', '#0f172a', '#18181b', '#09090b'].includes(theme.page_bg || '#ffffff');
}

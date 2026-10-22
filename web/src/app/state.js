/**
 * MD2WX Web Studio - 共享应用状态
 * 集中存放跨模块的排版与视图状态，模块间通过显式读写该对象通信
 */

import { DEFAULT_THEME_ID } from '../core/themes.js';

// App State
export const state = {
  currentThemeId: localStorage.getItem('md2wx_theme') || DEFAULT_THEME_ID,
  currentViewMode: localStorage.getItem('md2wx_view_mode') || 'mobile',
  currentFontSize: localStorage.getItem('md2wx_font_size') || '15.5px',
  currentLineHeight: localStorage.getItem('md2wx_line_height') || '1.8',
  enableFootnotes: localStorage.getItem('md2wx_enable_footnotes') !== 'false',
  enableSyncScroll: localStorage.getItem('md2wx_sync_scroll') !== 'false',
  insertCoverEnabled: localStorage.getItem('md2wx_insert_cover') !== 'false', // 排版微调：正文顶部插入封面图 (默认勾选)
  isSyncingScroll: false,
  debounceTimer: null,
  currentHtmlOutput: '',
  currentRichBlocks: [], // 当前富文本块列表 (Mermaid/公式，复制前需光栅化)
  currentCoverMeta: null, // 全局当前文章封面定制元数据，与正文顶部封面图联动
  lintIssues: [], // 最近一次发稿体检结果 (error 级阻断复制)
};

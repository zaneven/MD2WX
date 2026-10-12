/**
 * MD2WX Web Studio - 本地草稿箱模块
 * 多篇草稿列表 + 活动草稿自动保存，数据落 localStorage：
 *   md2wx_drafts        草稿数组 [{id, title, content, updatedAt}]，按 updatedAt 降序
 *   md2wx_active_draft  当前编辑中的草稿 id
 * 旧版单草稿键 md2wx_draft 首次进入时一次性迁移为列表首项，原键保留不清除 (回滚安全)
 */
import { parseFrontmatter } from '../core/parser.js';

const DRAFTS_KEY = 'md2wx_drafts';
const ACTIVE_KEY = 'md2wx_active_draft';
const LEGACY_DRAFT_KEY = 'md2wx_draft';

// 草稿列表容量上限：超出后按 updatedAt 淘汰最旧条目 (活动草稿不淘汰)
const MAX_DRAFTS = 20;

let activeId = null;

function readDrafts() {
  try {
    const raw = localStorage.getItem(DRAFTS_KEY);
    const list = raw ? JSON.parse(raw) : null;
    return Array.isArray(list) ? list : [];
  } catch (e) {
    return [];
  }
}

function writeDrafts(list) {
  try {
    localStorage.setItem(DRAFTS_KEY, JSON.stringify(list));
    return true;
  } catch (e) {
    // 超出配额：降级为剔除内嵌图片数据后重试；仍失败则放弃本次持久化
    try {
      const slim = list.map((d) => ({
        ...d,
        content: String(d.content || '').replace(
          /!\[[^\]]*\]\(data:image\/[^)]+\)/g,
          '![粘贴图片]()'
        ),
      }));
      localStorage.setItem(DRAFTS_KEY, JSON.stringify(slim));
      return true;
    } catch (e2) {
      return false;
    }
  }
}

/**
 * 从 Markdown 内容提取草稿标题：frontmatter title > 首个 H1 > 未命名草稿
 */
export function extractDraftTitle(content) {
  const text = String(content || '');
  try {
    const { meta } = parseFrontmatter(text);
    if (meta && meta.title) return String(meta.title).slice(0, 24);
  } catch (e) {
    // frontmatter 解析失败则回退 H1 提取
  }
  const h1 = text.match(/^#\s+(.+)$/m);
  if (h1) return h1[1].trim().slice(0, 24);
  return '未命名草稿';
}

function makeId() {
  return `d_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function upsertDraft(content, id = activeId) {
  const list = readDrafts();
  const now = Date.now();
  let draft = list.find((d) => d.id === id);
  if (draft) {
    draft.content = content;
    draft.title = extractDraftTitle(content);
    draft.updatedAt = now;
  } else {
    draft = { id: id || makeId(), title: extractDraftTitle(content), content, updatedAt: now };
    list.unshift(draft);
    activeId = draft.id;
    try {
      localStorage.setItem(ACTIVE_KEY, activeId);
    } catch (e) {
      // 活动指针写失败不影响内容保存
    }
  }

  // 容量淘汰：仅当非活动草稿溢出时按时间移除最旧条目
  while (list.length > MAX_DRAFTS) {
    const oldestIdx = list
      .map((d, i) => ({ updatedAt: d.updatedAt || 0, i, id: d.id }))
      .filter((x) => x.id !== activeId)
      .sort((a, b) => a.updatedAt - b.updatedAt)[0];
    if (!oldestIdx) break;
    list.splice(oldestIdx.i, 1);
  }

  writeDrafts(list);
  return draft;
}

/**
 * 自动保存活动草稿 (渲染管线每次输入触发)
 * 返回 false 表示存储彻底不可用，调用方可提示一次
 */
export function saveActiveDraft(content) {
  if (activeId === null) {
    // 极端情况：init 未跑 (如单测环境)。退化为即时建档，保证内容不丢
    return upsertDraft(content) !== undefined;
  }
  return upsertDraft(content) !== undefined;
}

/**
 * 初始化：一次性迁移旧单草稿，恢复活动草稿内容到编辑区
 * 返回应载入编辑器的 Markdown 内容
 */
export function initDrafts() {
  let list = readDrafts();

  if (list.length === 0) {
    const legacy = localStorage.getItem(LEGACY_DRAFT_KEY);
    if (legacy !== null) {
      list = [{ id: makeId(), title: extractDraftTitle(legacy), content: legacy, updatedAt: Date.now() }];
      writeDrafts(list);
    }
  }

  const storedActive = (() => {
    try {
      return localStorage.getItem(ACTIVE_KEY);
    } catch (e) {
      return null;
    }
  })();
  const active = list.find((d) => d.id === storedActive) || list[0];

  if (active) {
    activeId = active.id;
    try {
      localStorage.setItem(ACTIVE_KEY, activeId);
    } catch (e) {
      // 忽略
    }
    return active.content;
  }

  // 全新环境：建立首个空草稿
  const first = upsertDraft('');
  return first ? first.content : '';
}

/**
 * 草稿列表 (按最近更新降序)
 */
export function getDrafts() {
  return readDrafts().sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
}

export function getActiveDraftId() {
  return activeId;
}

/**
 * 载入指定草稿为活动草稿，返回其内容
 */
export function loadDraft(id) {
  const draft = readDrafts().find((d) => d.id === id);
  if (!draft) return null;
  activeId = id;
  try {
    localStorage.setItem(ACTIVE_KEY, id);
  } catch (e) {
    // 忽略
  }
  return draft.content;
}

/**
 * 新建空草稿并设为活动，返回空内容
 */
export function createDraft() {
  const draft = upsertDraft('', makeId());
  return draft ? '' : '';
}

/**
 * 删除指定草稿；若删除的是活动草稿，自动切到最近更新的草稿
 * 返回 { content } 表示编辑区应载入的新内容，无剩余草稿时 content 为空串
 */
export function deleteDraft(id) {
  let list = readDrafts().filter((d) => d.id !== id);
  writeDrafts(list);

  if (id === activeId) {
    const next = getDrafts()[0];
    if (next) {
      activeId = next.id;
      try {
        localStorage.setItem(ACTIVE_KEY, activeId);
      } catch (e) {
        // 忽略
      }
      return { content: next.content };
    }
    // 列表已空：重建一个空草稿
    const first = upsertDraft('');
    return { content: first ? '' : '' };
  }
  return null;
}

/**
 * 相对时间文案
 */
export function formatRelativeTime(ts) {
  if (!ts) return '';
  const diff = Date.now() - ts;
  if (diff < 60 * 1000) return '刚刚';
  if (diff < 60 * 60 * 1000) return `${Math.floor(diff / 60000)} 分钟前`;
  if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / 3600000)} 小时前`;
  const d = new Date(ts);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getMonth() + 1}月${d.getDate()}日 ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

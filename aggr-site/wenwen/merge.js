/* 暖文雷达 — 同事件合并 v1（代码负责稳定规则：归一化标题 + 字符 bigram 相似度 + 时间窗）
 *
 * 两种重复分开处理：
 * - 同一事件重复（多篇文章报同一件事）→ 合并为一个事件（本文件）
 * - 同类故事重复（不同事件但母题相似，如多条救人新闻）→ 由 AI 分析的 uniqueness +
 *   建议用途体现，不在合并层删除
 */
import { getDb, scheduleFlush, hashId } from './store.js';

const TIME_WINDOW_MS = 90 * 24 * 3600 * 1000; // 获奖时间相差 90 天内才可能同事件
const JACCARD_THRESHOLD = 0.6;
const EXACT_THRESHOLD = 0.45;

function normalizeTitle(t) {
  return String(t || '')
    .toLowerCase()
    .replace(/[\s\p{P}\p{S}]+/gu, '')
    .replace(/新京报快评|澎湃新闻|壹点公益|南国今报|潇湘晨报|来源|获奖/g, '')
    .trim();
}

function bigrams(s) {
  const set = new Set();
  for (let i = 0; i < s.length - 1; i++) set.add(s.slice(i, i + 2));
  return set;
}

function jaccard(a, b) {
  if (!a.size || !b.size) return 0;
  let inter = 0;
  for (const x of a) if (b.has(x)) inter++;
  return inter / (a.size + b.size - inter);
}

/**
 * 全量重建事件分组（只在新增文章后调用；并查集 + 按时间滑窗比较，避免全量两两）。
 * 用户反馈（保留/忽略）通过"与旧事件的文章重叠"继承，避免重建后丢失。
 */
export function rebuildEvents() {
  const db = getDb();
  const oldByArticle = new Map(); // articleId -> 旧事件
  for (const ev of Object.values(db.events)) {
    for (const aid of ev.articleIds || []) oldByArticle.set(aid, ev);
  }

  const prepared = Object.entries(db.articleIndex)
    .map(([id, a]) => {
      const norm = normalizeTitle(a.title);
      return {
        id,
        title: a.title || '',
        media: a.media || '',
        publishedAt: a.publishedAt || null,
        at: a.publishedAt ? Date.parse(a.publishedAt) : 0,
        norm,
        grams: bigrams(norm),
      };
    })
    .sort((x, y) => (x.at || 0) - (y.at || 0));

  const parent = new Map(prepared.map((p) => [p.id, p.id]));
  const find = (x) => {
    while (parent.get(x) !== x) {
      parent.set(x, parent.get(parent.get(x)));
      x = parent.get(x);
    }
    return x;
  };
  const union = (a, b) => {
    const ra = find(a);
    const rb = find(b);
    if (ra !== rb) parent.set(ra, rb);
  };

  for (let i = 0; i < prepared.length; i++) {
    const p = prepared[i];
    if (!p.norm) continue;
    for (let j = i + 1; j < prepared.length; j++) {
      const q = prepared[j];
      if (!q.norm) continue;
      if (q.at && p.at && q.at - p.at > TIME_WINDOW_MS) break; // 滑窗：时间窗之外不再比较
      const sim = jaccard(p.grams, q.grams);
      if (sim >= JACCARD_THRESHOLD || (sim >= EXACT_THRESHOLD && (p.norm.includes(q.norm) || q.norm.includes(p.norm)))) {
        union(p.id, q.id);
      }
    }
  }

  // 组装事件
  const groups = new Map();
  for (const p of prepared) {
    const root = find(p.id);
    if (!groups.has(root)) groups.set(root, []);
    groups.get(root).push(p);
  }

  const now = new Date().toISOString();
  const newEvents = {};
  for (const list of groups.values()) {
    list.sort((a, b) => (a.at || 0) - (b.at || 0));
    const articleIds = list.map((p) => p.id);
    const first = list[0];
    const evId = 'ev-' + hashId(articleIds.slice().sort().join('|'));
    const mediaList = [...new Set(list.map((p) => p.media).filter(Boolean))];
    const old = articleIds.map((aid) => oldByArticle.get(aid)).filter(Boolean);
    const oldEv = old.find((o) => o.userStatus) || old[0]; // 继承用户反馈与创建时间
    newEvents[evId] = {
      id: evId,
      title: first.title,
      articleIds,
      mediaList,
      category: db.articleIndex[articleIds[0]]?.category || '',
      firstAt: first.publishedAt,
      lastAt: list[list.length - 1].publishedAt || first.publishedAt,
      origin: 'ttzl',
      createdAt: oldEv?.createdAt || now,
      updatedAt: now,
      userStatus: oldEv?.userStatus || null, // null | kept | ignored
      userNoteAt: oldEv?.userNoteAt || null,
      analysis: null, // 由 analyze.js 填充；文章数变化后重新分析
      analysisAt: null,
      analysisArticleCount: 0,
    };
  }
  db.events = newEvents;
  scheduleFlush();
  return { articleCount: prepared.length, eventCount: Object.keys(newEvents).length };
}

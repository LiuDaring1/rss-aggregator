/* 暖文雷达 — 同事件合并 v0.2（稳定内容指纹 + 分析/反馈完整继承）
 *
 * 指纹 = hash(排序后文章ID + 排序后正文hash)。
 * - 新旧事件文章与内容完全一致 → 完整继承 analysis/analysisAt/analysisArticleCount
 *   /userStatus/userNoteAt/createdAt，不会因为新增了无关事件而重新分析；
 * - 文章有增删或正文变化 → 继承用户状态，但 analysis 置空等待重分析；
 * - 测试数据（isTestData）不参与事件。
 */
import { getDb, scheduleFlush, hashId } from './store.js';

const TIME_WINDOW_MS = 90 * 24 * 3600 * 1000;
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

function fingerprintOf(articleIds, db) {
  const hashes = articleIds
    .map((id) => db.articleIndex[id]?.contentHash || id)
    .sort()
    .join('|');
  return hashId(articleIds.slice().sort().join('|') + '#' + hashes);
}

export function rebuildEvents() {
  const db = getDb();
  const oldByArticle = new Map();
  for (const ev of Object.values(db.events)) {
    for (const aid of ev.articleIds || []) oldByArticle.set(aid, ev);
  }

  const prepared = Object.entries(db.articleIndex)
    .filter(([, a]) => !a.isTestData) // 测试数据不参与事件
    .map(([id, a]) => {
      const norm = normalizeTitle(a.title);
      return {
        id,
        title: a.title || '',
        media: a.media || '',
        publishedAt: a.awardDate || a.publishedAt || null,
        at: a.publishedAt ? Date.parse(a.publishedAt) || 0 : 0,
        norm,
        grams: bigrams(norm),
      };
    })
    .sort((x, y) => x.at - y.at);

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
      if (q.at && p.at && q.at - p.at > TIME_WINDOW_MS) break;
      const sim = jaccard(p.grams, q.grams);
      const contains = p.norm.includes(q.norm) || q.norm.includes(p.norm);
      if (sim >= JACCARD_THRESHOLD || (contains && sim >= 0.3)) {
        union(p.id, q.id);
      }
    }
  }

  const groups = new Map();
  for (const p of prepared) {
    const root = find(p.id);
    if (!groups.has(root)) groups.set(root, []);
    groups.get(root).push(p);
  }

  const now = new Date().toISOString();
  const newEvents = {};
  let inheritedAnalysis = 0;
  let reanalyzedNeeded = 0;
  for (const list of groups.values()) {
    list.sort((a, b) => a.at - b.at);
    const articleIds = list.map((p) => p.id);
    const first = list[0];
    const evId = 'ev-' + hashId(articleIds.slice().sort().join('|'));
    const fp = fingerprintOf(articleIds, db);

    // 通过文章重叠找到旧事件：指纹一致完整继承；文章变化则只继承用户状态
    const oldHits = new Map();
    for (const aid of articleIds) {
      const oe = oldByArticle.get(aid);
      if (oe) oldHits.set(oe.id, (oldHits.get(oe.id) || 0) + 1);
    }
    let oldEv = null;
    let maxOverlap = 0;
    for (const [oeId, overlap] of oldHits) {
      if (overlap > maxOverlap) {
        maxOverlap = overlap;
        oldEv = db.events[oeId];
      }
    }

    const unchanged = oldEv && oldEv.fingerprint === fp;
    const ev = {
      id: evId,
      title: first.title,
      articleIds,
      fingerprint: fp,
      mediaList: [...new Set(list.map((p) => p.media).filter(Boolean))],
      category: db.articleIndex[articleIds[0]]?.category || '',
      firstAt: first.publishedAt,
      lastAt: list[list.length - 1].publishedAt || first.publishedAt,
      origin: 'ttzl',
      createdAt: oldEv?.createdAt || now,
      updatedAt: now,
      userStatus: oldEv?.userStatus || null,
      userNoteAt: oldEv?.userNoteAt || null,
    };
    if (unchanged && oldEv?.analysis) {
      ev.analysis = oldEv.analysis;
      ev.analysisAt = oldEv.analysisAt;
      ev.analysisArticleCount = oldEv.analysisArticleCount;
      inheritedAnalysis++;
    } else {
      ev.analysis = null;
      ev.analysisAt = null;
      ev.analysisArticleCount = 0;
      if (oldEv?.analysis) reanalyzedNeeded++;
    }
    newEvents[evId] = ev;
  }
  db.events = newEvents;
  scheduleFlush();
  return {
    articleCount: prepared.length,
    eventCount: Object.keys(newEvents).length,
    inheritedAnalysis,
    reanalyzedNeeded,
  };
}

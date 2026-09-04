/* 暖文雷达 — HTTP API v0.2（挂载在 /wenwen/api/*，外加 /wenwen/report） */
import { initStore, getDb, scheduleFlush, loadRaw, dataDir } from './store.js';
import { collect, defaultFetcher as fetchStory } from './ttzl.js';
import { rebuildEvents } from './merge.js';
import { analyzePending, checkDistribution, USES } from './analyze.js';
import { rebuildRegistry } from './mediaName.js';
import { probeMedia } from './probe.js';
import { runCollect, runAnalyze } from './scheduler.js';

const USE_PRIORITY = { 完整加工: 0, 优先补搜: 1, 短复述或案例: 2, 继续观察: 3, 暂时不用: 4 };

function send(res, code, data, type) {
  res.writeHead(code, { 'Content-Type': type || 'application/json; charset=utf-8' });
  res.end(data);
}

function sendJson(res, code, data) {
  send(res, code, JSON.stringify(data));
}

async function readBody(req) {
  let body = '';
  for await (const chunk of req) body += chunk;
  try {
    return body ? JSON.parse(body) : {};
  } catch {
    return {};
  }
}

/** 事件 → 前端展示结构（展示判断理由与两维度，不展示综合分数） */
function eventToView(ev) {
  const db = getDb();
  const articles = ev.articleIds
    .map((aid) => db.articleIndex[aid])
    .filter(Boolean)
    .map((a) => ({
      title: a.title,
      media: a.media,
      awardDate: a.awardDate || a.publishedAt,
      url: a.url,
      contentLength: a.contentLength,
      flags: a.flags || [],
    }));
  return {
    id: ev.id,
    title: ev.title,
    mediaList: ev.mediaList,
    category: ev.category,
    firstAt: ev.firstAt,
    lastAt: ev.lastAt,
    articleCount: ev.articleIds.length,
    userStatus: ev.userStatus,
    analysis: ev.analysis,
    articles,
  };
}

function sortCandidates(list) {
  const statusRank = (s) => (s === 'kept' ? 0 : s === null ? 1 : 2);
  return list.sort((a, b) => {
    const sa = statusRank(a.userStatus);
    const sb = statusRank(b.userStatus);
    if (sa !== sb) return sa - sb;
    const ua = USE_PRIORITY[a.analysis?.suggestedUse] ?? 1.5;
    const ub = USE_PRIORITY[b.analysis?.suggestedUse] ?? 1.5;
    if (ua !== ub) return ua - ub;
    const wa = (a.analysis?.uniqueness || 0) + (a.analysis?.expandability || 0);
    const wb = (b.analysis?.uniqueness || 0) + (b.analysis?.expandability || 0);
    if (wa !== wb) return wb - wa;
    return String(b.lastAt || '').localeCompare(String(a.lastAt || ''));
  });
}

/* ---------------- 数据健康报告 ---------------- */

async function buildDataHealth() {
  const db = getDb();
  const { listRawIds } = await import('./store.js');
  const rawIds = await listRawIds();
  const indexIds = new Set(Object.keys(db.articleIndex));
  let missingContent = 0;
  let tooShort = 0;
  let badFlags = 0;
  for (const id of rawIds) {
    const raw = await loadRaw(id);
    if (!raw) { missingContent++; continue; }
    if (!raw.content || raw.content.length < 30) tooShort++;
    if (raw.flags?.length) badFlags++;
  }
  const orphanIndex = [...indexIds].filter((id) => !rawIds.includes(id)).length;
  const missingMedia = Object.values(db.articleIndex).filter((a) => !a.media).length;
  const missingDate = Object.values(db.articleIndex).filter((a) => !a.awardDate && !a.publishedAt).length;
  const testArticles = Object.values(db.articleIndex).filter((a) => a.isTestData).length;
  return {
    rawArticleCount: rawIds.length,
    indexArticleCount: indexIds.size,
    localSnapshotCount: rawIds.length - missingContent,
    missingContent,
    orphanIndex,
    missingMedia,
    missingDate,
    parseFailures: (db.meta.lastCollectErrors || []).length,
    tooShort,
    flaggedArticles: badFlags,
    testArticles,
    dedupedCount: db.dedupe?.dedupHits || 0,
    eventCount: Object.keys(db.events).length,
    dataDir: dataDir(),
    lastWriteAt: db.meta.lastWriteAt || null,
    lastCollectAt: db.meta.lastCollectAt || null,
    lastBackupAt: db.meta.lastBackupAt || null,
  };
}

/* ---------------- 路由挂载 ---------------- */

export async function mountWenwen(req, res, url) {
  await initStore();
  const db = getDb();
  const p = url.pathname;
  const q = url.searchParams;

  /* ---- 候选事件 ---- */
  if (p === '/wenwen/api/candidates' && req.method === 'GET') {
    const state = q.get('state') || 'all';
    const use = q.get('use');
    const motif = q.get('motif');
    const behavior = q.get('behavior');
    const tag = q.get('tag');
    let list = Object.values(db.events);
    if (state !== 'all') list = list.filter((ev) => (ev.userStatus || 'pending') === state);
    if (use) list = list.filter((ev) => ev.analysis?.suggestedUse === use);
    if (motif) list = list.filter((ev) => ev.analysis?.motif === motif);
    if (behavior) list = list.filter((ev) => ev.analysis?.behaviorCategory === behavior);
    if (tag) list = list.filter((ev) => ev.analysis?.discussionTags?.includes(tag));
    list = sortCandidates(list.map(eventToView));
    const meta = db.meta;
    return sendJson(res, 200, {
      total: list.length,
      events: list.slice(0, Number(q.get('limit') || 100)),
      uses: USES,
      summary: {
        articleCount: Object.keys(db.articleIndex).filter((id) => !db.articleIndex[id].isTestData).length,
        eventCount: Object.keys(db.events).length,
        analyzedCount: Object.values(db.events).filter((e) => e.analysis).length,
        registryCount: Object.keys(db.registry).length,
        connectedCount: Object.values(db.registry).filter((s) => s.probeStatus === '已稳定采集').length,
        maxStoryId: meta.ttzlMaxValidId || meta.ttzlMaxStoryId || 0,
        minBackfilledId: meta.ttzlMinBackfilledId || 0,
        lastCollectAt: meta.lastCollectAt || null,
        lastCollectStats: meta.lastCollectStats || null,
        filterWarning: meta.filterCheck?.collapsed ? meta.filterCheck.warning : null,
        ttzlTotalOnSite: 6079,
      },
    });
  }

  /* ---- 保留/忽略（即时生效） ---- */
  if (p.startsWith('/wenwen/api/events/') && p.endsWith('/feedback') && req.method === 'POST') {
    const evId = decodeURIComponent(p.slice('/wenwen/api/events/'.length, -'/feedback'.length));
    const body = await readBody(req);
    const action = body.action;
    const ev = db.events[evId];
    if (!ev) return sendJson(res, 404, { error: '事件不存在' });
    if (!['keep', 'ignore', 'reset'].includes(action)) return sendJson(res, 400, { error: 'action 必须是 keep/ignore/reset' });
    const statusMap = { keep: 'kept', ignore: 'ignored', reset: null };
    ev.userStatus = statusMap[action];
    ev.userNoteAt = new Date().toISOString();
    scheduleFlush();
    return sendJson(res, 200, { ok: true, id: evId, userStatus: ev.userStatus });
  }

  /* ---- 事件本地全文（完整留档正文，不截断） ---- */
  if (p.startsWith('/wenwen/api/events/') && p.endsWith('/full') && req.method === 'GET') {
    const evId = decodeURIComponent(p.slice('/wenwen/api/events/'.length, -'/full'.length));
    const ev = db.events[evId];
    if (!ev) return sendJson(res, 404, { error: '事件不存在' });
    const articles = [];
    for (const aid of ev.articleIds) {
      const raw = await loadRaw(aid);
      if (raw) {
        articles.push({
          id: raw.id,
          title: raw.title,
          media: raw.media,
          awardDate: raw.awardDate || (raw.publishedAt || '').slice(0, 10),
          sourcePublishedAt: raw.sourcePublishedAt || null,
          fetchedAt: raw.fetchedAt,
          url: raw.url, // 天天正能量收录页
          contentLength: (raw.content || '').length,
          content: raw.content || '',
        });
      }
    }
    return sendJson(res, 200, { id: evId, articles });
  }

  /* ---- 本地资料库：文章列表（搜索/筛选/分页） ---- */
  if (p === '/wenwen/api/library' && req.method === 'GET') {
    const sq = (q.get('q') || '').toLowerCase();
    const media = q.get('media');
    const origin = q.get('origin');
    const dateFrom = q.get('dateFrom');
    const dateTo = q.get('dateTo');
    const hasContent = q.get('hasContent'); // 1=有完整正文
    const eventId = q.get('eventId');
    const state = q.get('state'); // kept/ignored：按所属事件的用户状态
    const page = Math.max(1, Number(q.get('page') || 1));
    const pageSize = Math.min(100, Math.max(5, Number(q.get('pageSize') || 30)));

    const eventOfArticle = new Map();
    for (const ev of Object.values(db.events)) {
      for (const aid of ev.articleIds) eventOfArticle.set(aid, ev);
    }
    let rows = Object.entries(db.articleIndex)
      .filter(([, a]) => !a.isTestData)
      .map(([id, a]) => {
        const ev = eventOfArticle.get(id);
        return {
          id,
          title: a.title,
          media: a.media,
          origin: a.origin,
          awardDate: a.awardDate || a.publishedAt || null,
          contentLength: a.contentLength || 0,
          hasContent: (a.contentLength || 0) >= 30,
          flags: a.flags || [],
          eventId: ev?.id || null,
          eventTitle: ev?.title || null,
          eventPeople: ev?.analysis?.people || null,
          userStatus: ev?.userStatus || null,
          url: a.url,
        };
      });
    if (sq) {
      rows = rows.filter((r) =>
        r.title.toLowerCase().includes(sq) ||
        r.media.toLowerCase().includes(sq) ||
        (r.eventPeople || '').toLowerCase().includes(sq));
    }
    if (media) rows = rows.filter((r) => (r.media || '').toLowerCase().includes(media.toLowerCase()));
    if (origin) rows = rows.filter((r) => r.origin === origin);
    if (dateFrom) rows = rows.filter((r) => r.awardDate && r.awardDate >= dateFrom);
    if (dateTo) rows = rows.filter((r) => r.awardDate && r.awardDate <= dateTo);
    if (hasContent === '1') rows = rows.filter((r) => r.hasContent);
    if (eventId) rows = rows.filter((r) => r.eventId === eventId);
    if (state) rows = rows.filter((r) => (r.userStatus || 'pending') === state);
    rows.sort((a, b) => String(b.awardDate || '').localeCompare(String(a.awardDate || '')));
    const total = rows.length;
    return sendJson(res, 200, {
      total,
      page,
      pageSize,
      articles: rows.slice((page - 1) * pageSize, page * pageSize),
    });
  }

  /* ---- 单篇本地全文（完整正文，不截断） ---- */
  if (p.startsWith('/wenwen/api/articles/') && req.method === 'GET') {
    const aid = decodeURIComponent(p.slice('/wenwen/api/articles/'.length));
    const raw = await loadRaw(aid);
    if (!raw) return sendJson(res, 404, { error: '本地无留档' });
    const ev = Object.values(db.events).find((e) => e.articleIds?.includes(aid));
    return sendJson(res, 200, {
      id: raw.id,
      title: raw.title,
      media: raw.media,
      awardDate: raw.awardDate || (raw.publishedAt || '').slice(0, 10),
      sourcePublishedAt: raw.sourcePublishedAt || null,
      eventOccurredAt: raw.eventOccurredAt || null,
      fetchedAt: raw.fetchedAt,
      contentLength: (raw.content || '').length,
      content: raw.content || '', // 完整清洗正文，不截断
      ttzlUrl: raw.url,           // 天天正能量收录页
      sourceUrl: raw.sourceUrl || null, // 原始媒体报道（溯源后填）
      eventId: ev?.id || null,
      eventTitle: ev?.title || null,
      relatedArticles: (ev?.articleIds || []).filter((x) => x !== aid).map((x) => ({
        id: x, title: db.articleIndex[x]?.title, media: db.articleIndex[x]?.media,
      })),
    });
  }

  /* ---- 数据健康 ---- */
  if (p === '/wenwen/api/data-health' && req.method === 'GET') {
    return sendJson(res, 200, await buildDataHealth());
  }

  /* ---- 导出（JSON 全量 / Markdown 报告） ---- */
  if (p === '/wenwen/api/export' && req.method === 'GET') {
    const format = q.get('format') || 'json';
    const stamp = new Date().toISOString().slice(0, 10);
    if (format === 'md') {
      const report = await new Promise((resolve) => {
        const fakeRes = { writeHead: () => {}, end: (x) => resolve(x) };
        mountWenwenReport(req, fakeRes, new URL(`http://local/wenwen/report?limit=${q.get('limit') || 50}`));
      });
      res.writeHead(200, {
        'Content-Type': 'text/markdown; charset=utf-8',
        'Content-Disposition': `attachment; filename="wenwen-report-${stamp}.md"`,
      });
      return res.end(report);
    }
    const health = await buildDataHealth();
    res.writeHead(200, {
      'Content-Type': 'application/json; charset=utf-8',
      'Content-Disposition': `attachment; filename="wenwen-backup-${stamp}.json"`,
    });
    return res.end(JSON.stringify({ exportedAt: new Date().toISOString(), health, articleIndex: db.articleIndex, events: db.events, registry: db.registry, meta: db.meta }, null, 1));
  }

  /* ---- 信源注册表 + 探测 ---- */
  if (p === '/wenwen/api/registry' && req.method === 'GET') {
    const list = Object.values(db.registry).sort((a, b) => (b.articleCount || 0) - (a.articleCount || 0));
    const byStatus = {};
    for (const s of list) byStatus[s.probeStatus] = (byStatus[s.probeStatus] || 0) + 1;
    return sendJson(res, 200, { total: list.length, byStatus, sources: list });
  }
  if (p === '/wenwen/api/probe' && req.method === 'POST') {
    const result = await probeMedia({ limit: Math.min(50, Number(q.get('limit') || 20)) });
    return sendJson(res, 200, result);
  }

  /* ---- 状态 / 采集 / 分析 / 导入 ---- */
  if (p === '/wenwen/api/status' && req.method === 'GET') {
    const health = await buildDataHealth();
    return sendJson(res, 200, { meta: db.meta, counts: health, filterCheck: db.meta.filterCheck || null });
  }
  if (p === '/wenwen/api/collect' && req.method === 'POST') {
    const backfill = Math.min(500, Math.max(0, Number(q.get('backfill') || 0)));
    const result = await runCollect({ backfill });
    return sendJson(res, 200, result);
  }
  if (p === '/wenwen/api/analyze' && req.method === 'POST') {
    const limit = Math.min(30, Math.max(1, Number(q.get('limit') || 6)));
    const result = await runAnalyze({ limit });
    return sendJson(res, 200, result);
  }
  if (p === '/wenwen/api/rebuild' && req.method === 'POST') {
    const r1 = rebuildRegistry();
    const r2 = rebuildEvents();
    return sendJson(res, 200, { registry: r1, events: r2 });
  }
  if (p === '/wenwen/api/import' && req.method === 'POST') {
    const body = await readBody(req);
    const m = String(body.url || '').match(/storyDetails\/(\d+)/);
    if (!m) return sendJson(res, 400, { error: '目前仅支持天天正能量案例页 URL（/storyDetails/{id}）' });
    try {
      const article = await fetchStory(Number(m[1]));
      if (!article) return sendJson(res, 404, { error: '该页面无案例数据' });
      const { upsertArticle } = await import('./store.js');
      const r = await upsertArticle(article);
      rebuildRegistry();
      rebuildEvents();
      return sendJson(res, 200, { ok: true, article: { id: article.id, title: article.title }, isNew: r.isNew, duplicateOf: r.duplicateOf });
    } catch (e) {
      return sendJson(res, 502, { error: e.message });
    }
  }

  if (p === '/wenwen/report' && req.method === 'GET') {
    return mountWenwenReport(req, res, url);
  }

  sendJson(res, 404, { error: 'Not Found' });
}

/* ---- Markdown 报告（v0.2：新字段 + 时间含义区分） ---- */
export function mountWenwenReport(req, res, url) {
  const db = getDb();
  const q = url.searchParams;
  const limit = Math.min(100, Math.max(1, Number(q.get('limit') || 20)));
  const use = q.get('use');
  const motif = q.get('motif');
  let list = Object.values(db.events).filter((ev) => !ev.userStatus);
  if (use) list = list.filter((ev) => ev.analysis?.suggestedUse === use);
  if (motif) list = list.filter((ev) => ev.analysis?.motif === motif);
  list = sortCandidates(list.map(eventToView)).slice(0, limit);
  const lines = [
    '# 暖文雷达候选报告',
    '',
    `生成时间：${new Date().toLocaleString('zh-CN')}`,
    `已采集文章 ${Object.keys(db.articleIndex).length} 篇 · 事件 ${Object.keys(db.events).length} 个 · 登记信源 ${Object.keys(db.registry).length} 家`,
    '',
    '说明：以下为面向播音主持艺考「即兴口语表达」训练筛选的暖事件候选。人物、行动、细节等字段由 AI 从报道原文提取，未做事实补写。',
    '时间说明：日期均为天天正能量「获奖公示日期」（中国日期）；原始媒体报道时间在溯源完成后另行标注。',
    '',
  ];
  let i = 0;
  for (const ev of list) {
    i++;
    const a = ev.analysis;
    lines.push(`## ${i}. [${a?.suggestedUse || '待分析'}] ${ev.title}`);
    if (a) {
      lines.push(`- 一句话：${a.oneLine}`);
      lines.push(`- 特别在哪：${a.distinctiveWhy || '（未给出）'}`);
      lines.push(`- 人物：${a.people}；行动：${a.action}`);
      if (a.difficulty && a.difficulty !== '不明显') lines.push(`- 处境/成本：${a.difficulty}`);
      lines.push(`- 记忆点：${a.detail}；结果：${a.result}`);
      lines.push(`- 行为类别：${a.behaviorCategory}；母题：${a.motif}；讨论标签：${(a.discussionTags || []).join('、') || '无'}`);
      if (a.discussionAngles?.length) for (const ang of a.discussionAngles) lines.push(`- 讨论角度：${ang}`);
      if (a.missingFacts?.length) for (const m of a.missingFacts) lines.push(`- 信息缺口：${m.missing}（${m.why}；建议搜索：${m.search}）`);
      lines.push(`- 判断：${a.reason}`);
    }
    lines.push(`- 媒体：${(ev.mediaList || []).join('、')}（${ev.articleCount} 篇，获奖日期 ${(ev.firstAt || '').slice(0, 10)}）`);
    for (const art of ev.articles.slice(0, 3)) lines.push(`  - [${art.media}] ${art.title} ${art.url}`);
    lines.push('');
  }
  send(res, 200, lines.join('\n'), 'text/markdown; charset=utf-8');
}

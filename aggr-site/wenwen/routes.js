/* 暖文雷达 — HTTP API（挂载在 /wenwen/api/*） */
import { initStore, getDb, scheduleFlush } from './store.js';
import { collect } from './ttzl.js';
import { rebuildEvents } from './merge.js';
import { analyzePending } from './analyze.js';
import { fetchStory } from './ttzl.js';
import { runCollect, runAnalyze } from './scheduler.js';

const USE_PRIORITY = { 完整加工: 0, 短复述: 1, 继续观察: 2, 暂时不用: 3 };

function send(res, code, data) {
  res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(data));
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

/** 事件 → 前端展示结构（排序展示判断理由，不展示综合分数） */
function eventToView(ev) {
  const db = getDb();
  const articles = ev.articleIds
    .map((aid) => db.articleIndex[aid])
    .filter(Boolean)
    .map((a) => ({ title: a.title, media: a.media, publishedAt: a.publishedAt, url: a.url }));
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
    articles: articles.slice(0, 8),
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

export async function mountWenwen(req, res, url) {
  await initStore();
  const db = getDb();
  const p = url.pathname;
  const q = url.searchParams;

  if (p === '/wenwen/api/candidates' && req.method === 'GET') {
    const state = q.get('state') || 'all'; // all | pending | kept | ignored
    const use = q.get('use'); // 建议用途过滤
    let list = Object.values(db.events);
    if (state !== 'all') list = list.filter((ev) => (ev.userStatus || 'pending') === state);
    if (use) list = list.filter((ev) => ev.analysis?.suggestedUse === use);
    list = sortCandidates(list.map(eventToView));
    const meta = db.meta;
    return send(res, 200, {
      total: list.length,
      events: list.slice(0, Number(q.get('limit') || 100)),
      summary: {
        articleCount: Object.keys(db.articleIndex).length,
        eventCount: Object.keys(db.events).length,
        analyzedCount: Object.values(db.events).filter((e) => e.analysis).length,
        registryCount: Object.keys(db.registry).length,
        maxStoryId: meta.ttzlMaxStoryId || 0,
        lastCollectAt: meta.lastCollectAt || null,
        lastCollectStats: meta.lastCollectStats || null,
        ttzlTotalOnSite: 6079, // 站点公示的累计案例数（2026-09-04）
      },
    });
  }

  if (p.startsWith('/wenwen/api/events/') && p.endsWith('/feedback') && req.method === 'POST') {
    const evId = decodeURIComponent(p.slice('/wenwen/api/events/'.length, -'/feedback'.length));
    const body = await readBody(req);
    const action = body.action; // keep | ignore | reset
    const ev = db.events[evId];
    if (!ev) return send(res, 404, { error: '事件不存在' });
    if (!['keep', 'ignore', 'reset'].includes(action)) return send(res, 400, { error: 'action 必须是 keep/ignore/reset' });
    // 操作名与状态名对齐：keep→kept, ignore→ignored, reset→null
    const statusMap = { keep: 'kept', ignore: 'ignored', reset: null };
    ev.userStatus = statusMap[action];
    ev.userNoteAt = new Date().toISOString();
    scheduleFlush();
    return send(res, 200, { ok: true, id: evId, userStatus: ev.userStatus });
  }

  if (p === '/wenwen/api/registry' && req.method === 'GET') {
    const list = Object.values(db.registry).sort((a, b) => (b.articleCount || 0) - (a.articleCount || 0));
    const byStatus = {};
    for (const s of list) byStatus[s.probeStatus] = (byStatus[s.probeStatus] || 0) + 1;
    return send(res, 200, { total: list.length, byStatus, sources: list });
  }

  if (p === '/wenwen/api/status' && req.method === 'GET') {
    return send(res, 200, {
      meta: db.meta,
      counts: {
        articles: Object.keys(db.articleIndex).length,
        events: Object.keys(db.events).length,
        analyzed: Object.values(db.events).filter((e) => e.analysis).length,
        registry: Object.keys(db.registry).length,
      },
    });
  }

  if (p === '/wenwen/api/collect' && req.method === 'POST') {
    const backfill = Math.min(500, Math.max(0, Number(q.get('backfill') || 0)));
    const result = await runCollect({ backfill });
    return send(res, 200, result);
  }

  if (p === '/wenwen/api/analyze' && req.method === 'POST') {
    const limit = Math.min(20, Math.max(1, Number(q.get('limit') || 6)));
    const result = await runAnalyze({ limit });
    return send(res, 200, result);
  }

  if (p === '/wenwen/api/import' && req.method === 'POST') {
    // 开发者命令：临时导入单个 URL（目前支持天天正能量案例页）
    const body = await readBody(req);
    const target = String(body.url || '');
    const m = target.match(/storyDetails\/(\d+)/);
    if (!m) return send(res, 400, { error: '目前仅支持天天正能量案例页 URL（/storyDetails/{id}）' });
    try {
      const article = await fetchStory(Number(m[1]));
      if (!article) return send(res, 404, { error: '该页面无案例数据' });
      const isNew = !db.articleIndex[article.id];
      const { upsertArticle } = await import('./store.js');
      await upsertArticle(article);
      rebuildEvents();
      return send(res, 200, { ok: true, article: { id: article.id, title: article.title }, isNew });
    } catch (e) {
      return send(res, 502, { error: e.message });
    }
  }

  if (p.startsWith('/wenwen/api/events/') && p.endsWith('/full') && req.method === 'GET') {
    // 事件本地留档全文（前端"本地全文"展开用，不跳外部网站）
    const evId = decodeURIComponent(p.slice('/wenwen/api/events/'.length, -'/full'.length));
    const ev = db.events[evId];
    if (!ev) return send(res, 404, { error: '事件不存在' });
    const { loadRaw } = await import('./store.js');
    const articles = [];
    for (const aid of ev.articleIds) {
      const raw = await loadRaw(aid);
      if (raw) {
        articles.push({
          title: raw.title,
          media: raw.media,
          publishedAt: raw.publishedAt,
          url: raw.url,
          content: String(raw.content || '').slice(0, 6000),
        });
      }
    }
    return send(res, 200, { id: evId, articles });
  }

  if (p === '/wenwen/report' && req.method === 'GET') {
    // 供外部 AI 助手（如网页版 ChatGPT）直接抓取的 Markdown 候选报告
    const limit = Math.min(50, Math.max(1, Number(q.get('limit') || 20)));
    const use = q.get('use');
    let list = Object.values(db.events);
    if (use) list = list.filter((ev) => ev.analysis?.suggestedUse === use);
    list = sortCandidates(list.map(eventToView)).slice(0, limit);
    const lines = [
      '# 暖文雷达候选报告',
      '',
      `生成时间：${new Date().toLocaleString('zh-CN')}`,
      `已采集文章 ${Object.keys(db.articleIndex).length} 篇 · 事件 ${Object.keys(db.events).length} 个 · 登记信源 ${Object.keys(db.registry).length} 家`,
      '说明：以下为面向播音主持艺考「即兴口语表达」训练筛选的暖事件候选，按建议用途与判断质量排序。人物、行动、细节等字段由 AI 从报道原文提取，未做事实补写。',
    ];
    let i = 0;
    for (const ev of list) {
      i++;
      const a = ev.analysis;
      lines.push('', `## ${i}. [${a?.suggestedUse || '待分析'}] ${ev.title}`);
      if (a) {
        lines.push(`- 一句话：${a.oneLine}`);
        lines.push(`- 人物：${a.people}；行动：${a.action}`);
        if (a.difficulty && a.difficulty !== '不明显') lines.push(`- 处境/成本：${a.difficulty}`);
        lines.push(`- 记忆点：${a.detail}；结果：${a.result}`);
        lines.push(`- 行为类别：${a.behaviorCategory}；讨论方向：${(a.discussionTags || []).join('、') || '暂无'}`);
        lines.push(`- 判断：${a.reason}${a.needMoreSearch ? '（建议补充搜索）' : ''}`);
      }
      lines.push(`- 媒体：${(ev.mediaList || []).join('、')}（${ev.articleCount} 篇，获奖于 ${(ev.firstAt || '').slice(0, 10)}）`);
      for (const art of ev.articles.slice(0, 3)) lines.push(`  - [${art.media}] ${art.title} ${art.url}`);
    }
    res.writeHead(200, { 'Content-Type': 'text/markdown; charset=utf-8' });
    res.end(lines.join('\n'));
    return;
  }

  send(res, 404, { error: 'Not Found' });
}

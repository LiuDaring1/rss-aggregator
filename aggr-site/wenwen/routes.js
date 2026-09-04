/* 暖文雷达 — HTTP API v0.2.1（挂载在 /wenwen/api/*，外加 /wenwen/report） */
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import { initStore, getDb, scheduleFlush, loadRaw, dataDir } from './store.js';
import { collect, defaultFetcher as fetchStory } from './ttzl.js';
import { rebuildEvents } from './merge.js';
import { analyzePending, checkDistribution, USES } from './analyze.js';
import { ANALYSIS_RULES_VERSION } from './taxonomies.js';
import { rebuildRegistry } from './mediaName.js';
import { probeMedia } from './probe.js';
import { collectSources } from './collector.js';
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
    dataDir: 'aggr-site/data/wenwen', // 本机绝对路径不对外暴露
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
    if (state === 'unanalyzed') list = list.filter((ev) => !ev.analysis);
    else if (state !== 'all') list = list.filter((ev) => (ev.userStatus || 'pending') === state);
    if (use) list = list.filter((ev) => ev.analysis?.suggestedUse === use);
    if (motif) list = list.filter((ev) => ev.analysis?.eventMotif === motif);
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
        connectedCount: Object.values(db.registry).filter((s) => s.connected === true).length,
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

  /* ---- 数据健康（不暴露本机绝对路径） ---- */
  if (p === '/wenwen/api/data-health' && req.method === 'GET') {
    const health = await buildDataHealth();
    return sendJson(res, 200, health);
  }

  /* ---- 完整数据备份 ZIP（db + 全部本地正文快照 + manifest，无任何敏感信息） ---- */
  if (p === '/wenwen/api/backup' && req.method === 'GET') {
    const { spawn } = await import('node:child_process');
    const health = await buildDataHealth();
    const manifest = {
      generatedAt: new Date().toISOString(),
      version: '0.2.1',
      articleCount: health.rawArticleCount,
      eventCount: health.eventCount,
      note: '包含 db.json 与全部本地正文快照；不含任何密钥、Cookie、登录状态。',
    };
    const manifestPath = path.join(dataDir(), 'manifest.json');
    await fsp.writeFile(manifestPath, JSON.stringify(manifest, null, 1));
    const stamp = new Date().toISOString().slice(0, 10);
    res.writeHead(200, {
      'Content-Type': 'application/zip',
      'Content-Disposition': `attachment; filename="wenwen-full-backup-${stamp}.zip"`,
    });
    // zip 从 data 目录打包 db.json/manifest.json/raw/，路径稳定且不含敏感物
    const child = spawn('zip', ['-r', '-', 'db.json', 'manifest.json', 'raw'], { cwd: dataDir() });
    child.stdout.pipe(res);
    child.stderr.on('data', () => {});
    child.on('error', (e) => sendJson(res, 500, { error: `zip 不可用：${e.message}` }));
    child.on('close', (code) => { if (code !== 0 && !res.writableEnded) sendJson(res, 500, { error: `zip 退出码 ${code}` }); });
    return;
  }

  /* ---- 脏数据自动修复 ---- */
  if (p === '/wenwen/api/repair' && req.method === 'POST') {
    const { repairDirty } = await import('./repair.js');
    const result = await repairDirty({ max: 100 });
    return sendJson(res, 200, result);
  }

  /* ---- 按版本重分析：清空旧版本分析，等待重跑（不自动清全部） ---- */
  if (p === '/wenwen/api/reanalyze' && req.method === 'POST') {
    const body = await readBody(req);
    const onlyOutdated = body.onlyOutdated !== false; // 默认只清非当前版本的
    let cleared = 0;
    for (const ev of Object.values(db.events)) {
      const outdated = !ev.analysis || ev.analysis.version?.rules !== ANALYSIS_RULES_VERSION;
      if (onlyOutdated ? outdated : true) {
        if (ev.analysis) cleared++;
        ev.analysis = null;
      }
    }
    scheduleFlush();
    return sendJson(res, 200, { cleared, rulesVersion: ANALYSIS_RULES_VERSION });
  }

  /* ---- 分层校准报告 ---- */
  if (p === '/wenwen/api/calibration' && req.method === 'GET') {
    const db2 = getDb();
    const strata = {
      水域救援: /水|河|江|湖|海|落水|溺水/,
      火灾救援: /火|燃烧|浓烟/,
      医疗急救: /医|急救|昏迷|心脏/,
      困境成长: /高考|大学|学子|寒门|励志|病|父亲|母亲|孤儿/,
      长期公益: /坚持|公益|助学|捐赠|基金/,
      爱心餐食: /餐|食堂|早餐|饭菜|送饭/,
      适老服务: /老人|大爷|大妈|八旬|独居/,
      助残与无障碍: /盲|残|轮椅|听障|视障/,
      暖心小事: /暖心|暖|点赞|温暖/,
    };
    const picked = new Set();
    for (const [name, re] of Object.entries(strata)) {
      for (const ev of Object.values(db2.events)) {
        if (picked.size >= Number(q.get('limit') || 60)) break;
        if (picked.has(ev.id)) continue;
        if (ev.userStatus === 'ignored') continue;
        const hay = ev.title + (ev.analysis?.oneLine || '');
        if (re.test(hay)) picked.add(ev.id);
      }
    }
    // 兜底：不足则按时间补
    for (const ev of Object.values(db2.events).sort((a, b) => String(b.lastAt).localeCompare(String(a.lastAt)))) {
      if (picked.size >= Number(q.get('limit') || 60)) break;
      picked.add(ev.id);
    }
    sendJson(res, 200, {
      sampleIds: [...picked],
      sampleSize: picked.size,
      note: '分层抽样完成；用 POST /wenwen/api/analyze?limit=N 按批次分析后，distribution 即为校准分布（见 status.filterCheck）。',
    });
    return;
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
    const queue = q.get('queue') || 'auto'; // first | retry | auto
    const result = await probeMedia({ queue, limit: Math.min(50, Number(q.get('limit') || 20)) });
    return sendJson(res, 200, result);
  }
  /* ---- 多信源真实采集（RSS 通道 → 预筛 → 统一入库） ---- */
  if (p === '/wenwen/api/collect-sources' && req.method === 'POST') {
    const result = await collectSources({ limit: Math.min(20, Number(q.get('limit') || 5)) });
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
  const limitPerSection = Math.min(100, Math.max(1, Number(q.get('limit') || 30)));
  const includeIgnored = q.get('includeIgnored') === '1';

  const all = Object.values(db.events);
  const kept = sortCandidates(all.filter((ev) => ev.userStatus === 'kept').map(eventToView));
  const analyzed = all.filter((ev) => !ev.userStatus && ev.analysis).map(eventToView);
  const pending = all.filter((ev) => !ev.userStatus && !ev.analysis).map(eventToView);
  const ignored = includeIgnored ? all.filter((ev) => ev.userStatus === 'ignored').map(eventToView) : [];

  const byUse = {};
  for (const use of USES) {
    byUse[use] = sortCandidates(analyzed.filter((ev) => ev.analysis.suggestedUse === use));
  }

  // 统一统计口径（全站各处一致）
  const testCount = Object.values(db.articleIndex).filter((a) => a.isTestData).length;
  const validArticles = Object.keys(db.articleIndex).length;
  const analyzedCount = all.filter((ev) => ev.analysis).length;
  const connected = Object.values(db.registry).filter((s) => s.connected === true).length;

  const lines = [
    '# 暖文雷达候选报告',
    '',
    `生成时间：${new Date().toLocaleString('zh-CN')}`,
    '',
    '## 总体统计',
    '',
    `- 原始记录数：${validArticles + testCount}（含测试数据 ${testCount} 条，已排除）`,
    `- 有效文章数：${validArticles}`,
    `- 事件数：${all.length}`,
    `- 已分析事件数：${analyzedCount}`,
    `- 媒体实体数：${Object.keys(db.registry).length}`,
    `- 实际接入采集数：${connected}`,
    '',
    '说明：日期均为天天正能量「获奖公示日期」（中国日期）；人物、行动、细节等字段由 AI 从报道原文提取，未做事实补写。',
    '',
  ];

  const renderEvent = (ev) => {
    const a = ev.analysis;
    if (!ev.articles) console.error('[debug] 无 articles 对象 ev-id=', ev.id, '| title=', ev.title?.slice(0, 12), '| keys=', Object.keys(ev).length, '| 是否视图(有articles字段):', 'articles' in ev);
    const out = [];
    if (a) {
      out.push(`- 一句话：${a.oneLine}`);
      out.push(`- 特别在哪：${a.distinctiveWhy || '（未给出）'}`);
      out.push(`- 人物：${a.people}；行动：${a.action}`);
      if (a.difficulty && a.difficulty !== '不明显') out.push(`- 处境/成本：${a.difficulty}`);
      out.push(`- 记忆点：${a.detail}；结果：${a.result}`);
      out.push(`- 行为类别：${a.behaviorCategory}；事件母题：${a.eventMotif}；讨论主题：${(a.discussionTags || []).join('、') || '无'}`);
      for (const ang of a.discussionAngles || []) out.push(`- 讨论角度：${ang}`);
      for (const m of a.missingFacts || []) out.push(`- ${m.importance === 'critical' ? '关键缺口' : '可选补充'}：${m.missing}（${m.why}；建议搜索：${m.search}）`);
      out.push(`- 判断：${a.reason}`);
    }
    out.push(`- 媒体：${(ev.mediaList || []).join('、')}（${ev.articleCount} 篇，获奖日期 ${(ev.firstAt || '').slice(0, 10)}）`);
    for (const art of ev.articles.slice(0, 3)) out.push(`  - [${art.media}] ${art.title} ${art.url}`);
    return out;
  };

  const section = (title, list) => {
    lines.push(`## ${title}（${list.length}）`, '');
    if (!list.length) { lines.push('（无）', ''); return; }
    list.slice(0, limitPerSection).forEach((ev, i) => {
      lines.push(`### ${i + 1}. ${ev.title}`, ...renderEvent(ev), '');
    });
  };

  section('已保留', kept);
  section('完整加工候选', byUse['完整加工']);
  section('优先补搜', byUse['优先补搜']);
  section('短复述或案例', byUse['短复述或案例']);
  section('继续观察', byUse['继续观察']);
  section('暂时不用', byUse['暂时不用']);
  if (includeIgnored) section('已忽略', ignored);
  section('待 AI 分析', pending); // 待分析永远排在全部已分析分节之后

  send(res, 200, lines.join('\n'), 'text/markdown; charset=utf-8');
}

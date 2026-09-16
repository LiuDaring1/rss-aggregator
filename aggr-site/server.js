/**
 * aggr-site — 自建信息聚合站点后端
 *
 * 职责：抓取多个 RSS 源（RSSHub 路由 / 普通 RSS / we-mp-rss 公众号源），
 * 统一解析为 JSON 并提供给前端展示。
 *
 * 运行：node server.js  （默认端口 3000，可用 PORT 环境变量覆盖）
 */
import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { XMLParser } from 'fast-xml-parser';
import { mountWenwen } from './wenwen/routes.js';
import { startWenwenScheduler } from './wenwen/scheduler.js';

const PORT = Number(process.env.PORT || 3000);
const CACHE_TTL = Number(process.env.CACHE_TTL || 5 * 60 * 1000); // 源抓取缓存 5 分钟
const FETCH_TIMEOUT = Number(process.env.FETCH_TIMEOUT || 60000); // 单源抓取超时 60 秒（含详情页抓取）

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = path.join(ROOT, 'public');

/** 每次请求时读取 sources.json，改配置即时生效，无需重启 */
async function loadSources() {
  return JSON.parse(await readFile(path.join(ROOT, 'sources.json'), 'utf8')).filter(
    (s) => s.enabled !== false
  );
}

const xmlParser = new XMLParser({
  ignoreAttributes: false,
  attributeNamePrefix: '@_',
  cdataPropName: '__cdata',
  textNodeName: '#text',
  trimValues: true,
});

/* ---------------- RSS 解析 ---------------- */

function nodeText(node) {
  if (node == null) return '';
  if (typeof node === 'string') return node;
  if (Array.isArray(node)) return node.map(nodeText).join('');
  if (typeof node === 'object') {
    if (node.__cdata != null) return String(node.__cdata);
    if (node['#text'] != null) return String(node['#text']);
    return '';
  }
  return '';
}

function parseDate(value) {
  const d = new Date(String(value ?? ''));
  return isNaN(d.getTime()) ? null : d;
}

/** 把任意 RSS 2.0 / Atom XML 统一解析为条目数组 */
function parseFeed(xml, source) {
  const doc = xmlParser.parse(xml);
  const channel = doc?.rss?.channel ?? doc?.feed ?? null;
  let items = [];
  if (doc?.rss?.channel) {
    const raw = doc.rss.channel.item;
    items = (Array.isArray(raw) ? raw : raw ? [raw] : []).map((it) => ({
      title: nodeText(it.title) || '(无标题)',
      link: nodeText(it.link) || nodeText(it.guid) || '',
      summary: nodeText(it.description) || nodeText(it.summary) || '',
      content: nodeText(it['content:encoded']) || '',
      author: nodeText(it.author) || nodeText(it['dc:creator']) || '',
      pubDate: parseDate(it.pubDate ?? it['dc:date']) || new Date(0),
    }));
  } else if (doc?.feed) {
    const raw = doc.feed.entry;
    items = (Array.isArray(raw) ? raw : raw ? [raw] : []).map((it) => ({
      title: nodeText(it.title) || '(无标题)',
      link:
        nodeText(it.link?.['@_href']) ||
        nodeText(it.link) ||
        nodeText(it.id) ||
        '',
      summary:
        nodeText(it.summary) ||
        nodeText(it.content) ||
        (typeof it.content === 'string' ? it.content : ''),
      content: nodeText(it.content) || '',
      author: nodeText(it.author?.name) || '',
      pubDate: parseDate(it.updated ?? it.published) || new Date(0),
    }));
  }
  return items.map((it) => ({
    ...it,
    summary: stripHtml(it.summary || it.content || '').slice(0, 300),
    sourceId: source.id,
    sourceName: source.name,
    sourceCategory: source.category || '未分类',
  }));
}

/** 粗暴但够用的 HTML → 纯文本 */
function stripHtml(html) {
  return String(html)
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/(p|div|li|h[1-6]|tr)>/gi, '\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
}

/* ---------------- 源抓取与缓存 ---------------- */

const cache = new Map(); // sourceId -> { at, ok, items, error }

async function fetchSource(source, { force = false } = {}) {
  const hit = cache.get(source.id);
  if (!force && hit && Date.now() - hit.at < CACHE_TTL) return hit;

  if (IS_OFFLINE) {
    if (hit) return hit;
    return { at: Date.now(), ok: false, items: [], error: 'offline: 离线模式已阻断外部网络抓取' };
  }

  const entry = { at: Date.now(), ok: false, items: [], error: null };
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT);
    const res = await fetch(source.url, {
      signal: ctrl.signal,
      headers: { 'User-Agent': 'aggr-site/1.0 (+local aggregation)' },
    });
    clearTimeout(timer);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const xml = await res.text();
    entry.items = parseFeed(xml, source);
    entry.ok = true;
  } catch (e) {
    entry.error = e.message;
    // 失败只缓存 30 秒，避免瞬时网络抖动导致长时间显示失败
    cache.set(source.id, { ...entry, at: Date.now() - CACHE_TTL + 30_000 });
    return entry;
  }
  cache.set(source.id, entry);
  return entry;
}

/** 聚合所有源，按时间倒序 */
async function getAllItems() {
  const sources = await loadSources();
  const results = await Promise.all(
    sources.map(async (s) => ({ source: s, entry: await fetchSource(s) }))
  );
  const items = results
    .flatMap((r) => r.entry.items)
    .sort((a, b) => b.pubDate - a.pubDate);
  return { items, results };
}

/* ---------------- AI 热点归纳（GLM） ---------------- */

const AI_CACHE_TTL = Number(process.env.AI_CACHE_TTL || 30 * 60 * 1000); // 归纳结果缓存 30 分钟（省 token）
const AI_TIMEOUT = Number(process.env.AI_TIMEOUT || 300000); // glm-5.3-flash 始终思考，长任务 2-4 分钟
const AI_MAX_ITEMS = Number(process.env.AI_MAX_ITEMS || 60); // 最多喂给模型的文章数（越少思考越快）
const topicsCache = new Map(); // hours -> { at, data }
const topicsInflight = new Map(); // hours -> Promise（并发去重）

/** AI 配置：优先环境变量，其次 aggr-site/ai.json（含密钥，勿入库勿打包） */
async function loadAiConfig() {
  if (process.env.GLM_API_KEY) {
    return {
      apiKey: process.env.GLM_API_KEY,
      baseUrl: process.env.GLM_BASE_URL || 'https://open.bigmodel.cn/api/paas/v4',
      model: process.env.GLM_MODEL || 'glm-5.3-flash',
    };
  }
  try {
    const cfg = JSON.parse(await readFile(path.join(ROOT, 'ai.json'), 'utf8'));
    return {
      apiKey: cfg.apiKey,
      baseUrl: cfg.baseUrl || 'https://open.bigmodel.cn/api/paas/v4',
      model: cfg.model || 'glm-5.3-flash',
    };
  } catch {
    return null;
  }
}

/** 容错提取模型回复里的 JSON（有的模型会带前后缀文字） */
function extractJson(text) {
  const s = text.indexOf('{');
  const e = text.lastIndexOf('}');
  if (s < 0 || e <= s) throw new Error('AI 返回内容中没有 JSON');
  return JSON.parse(text.slice(s, e + 1));
}

async function callGlm(cfg, prompt) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), AI_TIMEOUT);
  try {
    const res = await fetch(cfg.baseUrl.replace(/\/$/, '') + '/chat/completions', {
      method: 'POST',
      signal: ctrl.signal,
      headers: { Authorization: `Bearer ${cfg.apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: cfg.model,
        messages: [
          { role: 'system', content: '你是敏锐的媒体评论分析助手，只输出 JSON，不要输出任何解释。' },
          { role: 'user', content: prompt },
        ],
        max_tokens: 30000, // glm-5.3-flash 思考量波动大（1.5万~2.5万字），余量给足防止思考占满导致正文为空
        temperature: 0.3,
        // glm-5.3-flash 始终思考（不支持关闭），且默认档位 max 极慢；
        // 用 low 档 + json_object 保证速度与输出格式
        thinking: { type: 'enabled', reasoning_effort: 'low' },
        response_format: { type: 'json_object' },
      }),
    });
    if (!res.ok) {
      throw new Error(`GLM HTTP ${res.status}: ${(await res.text()).slice(0, 200)}`);
    }
    const data = await res.json();
    const msg = data.choices?.[0]?.message || {};
    console.log(
      `[ai] finish=${data.choices?.[0]?.finish_reason} content=${(msg.content || '').length}字 reasoning=${(msg.reasoning_content || '').length}字 tokens=${data.usage?.total_tokens}`
    );
    return msg.content || '';
  } finally {
    clearTimeout(timer);
  }
}

async function buildTopics(hours, cfg) {
  const { items } = await getAllItems();
  const cutoff = Date.now() - hours * 3600 * 1000;
  const win = items.filter((it) => it.pubDate.getTime() >= cutoff).slice(0, AI_MAX_ITEMS);
  if (win.length < 3) {
    return { topics: [], articleCount: win.length, mediaCount: new Set(win.map((i) => i.sourceName)).size };
  }

  const lines = win.map((it) => ({
    媒体: it.sourceName,
    标题: it.title,
    摘要: it.summary.slice(0, 60),
    时间: `${it.pubDate.getMonth() + 1}-${it.pubDate.getDate()} ${String(it.pubDate.getHours()).padStart(2, '0')}:${String(it.pubDate.getMinutes()).padStart(2, '0')}`,
  }));
  const mediaCount = new Set(win.map((i) => i.sourceName)).size;
  const prompt = `以下是近 ${hours} 小时内 ${mediaCount} 家媒体评论栏目发表的 ${lines.length} 篇文章列表（JSON 数组）：

${JSON.stringify(lines)}

请归纳近期媒体集中关注的热点事件/话题，把围绕同一事件的评论聚为一组（多家媒体都评论的优先）。
每个热点输出：
- title：热点名，15 字以内
- heat：关注度 1-5（参与媒体越多越高）
- outlets：参与媒体名数组（用"媒体"原词，去重）
- angle：80 字以内：一句话说清事件 + 各媒体评论核心观点/分歧
- articleTitles：相关文章标题（从"标题"原样复制，最多 4 条，覆盖不同媒体）
最多 6 个热点，按 heat 降序；独家评论的事件 heat 最多 2；软文忽略。
只输出 JSON：{"topics":[{"title":"","heat":1,"outlets":[],"angle":"","articleTitles":[]}]}`;

  const text = await callGlm(cfg, prompt);
  const parsed = extractJson(text);

  // 把模型复制的标题映射回原文（带链接）；精确匹配失败再做宽松匹配
  const byTitle = new Map(win.map((it) => [it.title, it]));
  const loose = (tt) =>
    win.find((w) => w.title.includes(String(tt).slice(0, 12)) || String(tt).includes(w.title.slice(0, 12)));
  const topics = (Array.isArray(parsed.topics) ? parsed.topics : [])
    .slice(0, 6)
    .map((t) => ({
      title: t.title || '(未命名热点)',
      heat: Math.min(5, Math.max(1, Number(t.heat) || 1)),
      outlets: Array.isArray(t.outlets) ? t.outlets.filter(Boolean) : [],
      angle: String(t.angle || ''),
      articles: (Array.isArray(t.articleTitles) ? t.articleTitles : []).map((tt) => {
        const hit = byTitle.get(tt) || loose(tt);
        return { title: tt, link: hit ? hit.link : '', source: hit ? hit.sourceName : '' };
      }),
    }))
    .sort((a, b) => b.heat - a.heat);

  return { topics, articleCount: win.length, mediaCount };
}

async function getTopics(hours, force) {
  const hit = topicsCache.get(hours);
  if (!force && hit && Date.now() - hit.at < AI_CACHE_TTL) {
    return {
      ...hit.data,
      cached: true,
      model: hit.model,
      updatedAt: new Date(hit.at).toISOString(),
    };
  }
  if (topicsInflight.has(hours)) return topicsInflight.get(hours);
  const task = (async () => {
    try {
      const cfg = await loadAiConfig();
      if (!cfg || !cfg.apiKey) {
        throw new Error('未配置 AI：请在 aggr-site/ai.json 里填 apiKey（或设置环境变量 GLM_API_KEY）');
      }
      const data = await buildTopics(hours, cfg);
      topicsCache.set(hours, { at: Date.now(), data, model: cfg.model });
      return { ...data, cached: false, model: cfg.model, updatedAt: new Date().toISOString() };
    } finally {
      topicsInflight.delete(hours);
    }
  })();
  topicsInflight.set(hours, task);
  return task;
}

/* ---------------- HTTP 服务 ---------------- */

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

async function serveStatic(req, res, pathname) {
  let file = pathname === '/' ? 'index.html' : pathname.slice(1);
  // 防目录穿越
  const full = path.normalize(path.join(PUBLIC_DIR, file));
  if (!full.startsWith(PUBLIC_DIR)) {
    res.writeHead(403).end('Forbidden');
    return;
  }
  try {
    const info = await stat(full);
    if (!info.isFile()) throw new Error('not file');
    const data = await readFile(full);
    res.writeHead(200, {
      'Content-Type': MIME[path.extname(full).toLowerCase()] || 'application/octet-stream',
      'Cache-Control': 'no-cache',
    });
    res.end(data);
  } catch {
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' }).end('404 Not Found');
  }
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  try {
    if (url.pathname.startsWith('/wenwen/')) {
      await mountWenwen(req, res, url);
      return;
    }
    if (url.pathname === '/api/items') {
      const { items, results } = await getAllItems();
      const hours = Number(url.searchParams.get('hours') || 24);
      const sourceFilter = url.searchParams.get('source'); // 逗号分隔
      const limit = Number(url.searchParams.get('limit') || 200);
      let list = items;
      if (sourceFilter) {
        const ids = new Set(sourceFilter.split(','));
        list = list.filter((it) => ids.has(it.sourceId));
      }
      if (hours > 0) {
        const cutoff = Date.now() - hours * 3600 * 1000;
        list = list.filter((it) => it.pubDate.getTime() >= cutoff);
      }
      const total = list.length;
      list = list.slice(0, limit);
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(
        JSON.stringify({
          updatedAt: new Date().toISOString(),
          total,
          items: list.map((it) => ({
            ...it,
            pubDate: it.pubDate.toISOString(),
          })),
          sources: results.map((r) => ({
            id: r.source.id,
            name: r.source.name,
            category: r.source.category,
            ok: r.entry.ok,
            error: r.entry.error,
            count: r.entry.items.length,
          })),
        })
      );
      return;
    }
    if (url.pathname === '/api/sources') {
      const sources = await loadSources();
      // 顺带给出缓存里最近一次抓取的状态（不触发抓取）：
      // 连接是否正常 / 条数 / 上次抓取时间 / 该源最新文章时间
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(
        JSON.stringify({
          sources: sources.map((s) => {
            const hit = cache.get(s.id);
            const newest = hit?.items?.length
              ? hit.items.reduce((m, i) => (i.pubDate > m ? i.pubDate : m), hit.items[0].pubDate)
              : null;
            return {
              id: s.id,
              name: s.name,
              type: s.type,
              category: s.category,
              url: s.url,
              status: hit
                ? {
                    ok: hit.ok,
                    error: hit.error,
                    count: hit.items.length,
                    checkedAt: new Date(hit.at).toISOString(),
                    newestItem: newest ? newest.toISOString() : null,
                  }
                : null,
            };
          }),
        })
      );
      return;
    }
    const isReadonly = process.env.AGGR_READONLY === 'on' || (process.env.AGGR_MODE || '').includes('readonly');
    const isOffline = process.env.AGGR_OFFLINE === 'on' || (process.env.AGGR_MODE || '').includes('offline');

    if (url.pathname === '/api/health') {
      const sources = await loadSources();
      if (isOffline) {
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ ok: true, offline: true, sources: sources.map((s) => ({ id: s.id, name: s.name, offline: true, count: 0 })) }));
        return;
      }
      const force = url.searchParams.get('force') === '1'; // ?force=1 绕过缓存逐源重抓
      const results = await Promise.all(
        sources.map(async (s) => ({
          id: s.id,
          name: s.name,
          ...(await fetchSource(s, { force })),
        }))
      );
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ ok: true, sources: results }));
      return;
    }
    if (url.pathname === '/api/topics') {
      if (isOffline) {
        res.writeHead(503, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ error: '离线模式（AGGR_OFFLINE=on）：不调用外部 AI 模型' }));
        return;
      }
      const hours = Number(url.searchParams.get('hours') || 72);
      const force = url.searchParams.get('force') === '1';
      try {
        const data = await getTopics(hours, force);
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ hours, ...data }));
      } catch (e) {
        res.writeHead(503, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ error: e.message }));
      }
      return;
    }
    await serveStatic(req, res, url.pathname);
  } catch (e) {
    res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('Server Error: ' + e.message);
  }
});

server.listen(PORT, '127.0.0.1', async () => {
  const sources = await loadSources();
  const isReadonly = process.env.AGGR_READONLY === 'on' || (process.env.AGGR_MODE || '').includes('readonly');
  const isOffline = process.env.AGGR_OFFLINE === 'on' || (process.env.AGGR_MODE || '').includes('offline');

  console.log(`[aggr-site] 聚合站点已启动: http://127.0.0.1:${PORT} (显式绑定 127.0.0.1)`);
  console.log(`[aggr-site] 已配置 ${sources.length} 个信息源`);
  if (isReadonly) console.log('[aggr-site] AGGR_READONLY=on：已启用只读模式，拒绝所有写操作');
  if (isOffline) console.log('[aggr-site] AGGR_OFFLINE=on：已启用离线模式，禁止外网抓取与模型调用');

  // 交接与离线适配：若设 AGGR_AUTOTASKS=off 或处于只读/离线模式，跳过 AI 预热与调度
  if (process.env.AGGR_AUTOTASKS === 'off' || isReadonly || isOffline) {
    console.log('[aggr-site] 已跳过 AI 热点预热与暖文雷达调度（只读/离线/交接模式）');
  } else {
    // 后台预热 AI 热点归纳（72h / 7d），用户点开时大概率已有缓存
    for (const h of [72, 168]) {
      getTopics(h, false)
        .then(() => console.log(`[aggr-site] AI 热点预热完成（${h}h）`))
        .catch((e) => console.log(`[aggr-site] AI 热点预热失败（${h}h）: ${e.message}`));
    }
    // 暖文雷达：启动采集/分析调度
    await startWenwenScheduler();
  }
});

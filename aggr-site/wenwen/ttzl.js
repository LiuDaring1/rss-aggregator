/* 暖文雷达 — 天天正能量采集器
 *
 * 站点 https://ttznl.alibabafoundation.com（阿里巴巴公益基金会）
 * - 列表页 /gainEnergy 为 CSR，无公开 JSON 接口（已探测确认）
 * - 详情页 /storyDetails/{id} 为 SSR，内嵌 window.__ICE_APP_CONTEXT__ 结构化数据，
 *   含标题/正文/媒体/类别/地域/职业/身份/奖金/获奖时间，且无 WAF 拦截
 * 因此采集策略：按 storyId 扫描详情页 —— 已知最大 id 向上探测增量（连续落空自动停止），
 * 需要历史时向下回扫（backfill）。所有正文本地留档。
 */
import { getDb, upsertArticle } from './store.js';

const BASE = 'https://ttznl.alibabafoundation.com';
const UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';
const HEADERS = { 'User-Agent': UA, 'Accept-Language': 'zh-CN,zh;q=0.9' };
const SCAN_INTERVAL_MS = 500; // 对源站友好：请求间隔
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** 抓取单个案例；无此案例返回 null */
export async function fetchStory(storyId) {
  const url = `${BASE}/storyDetails/${storyId}`;
  const res = await fetch(url, { headers: HEADERS, signal: AbortSignal.timeout(20000) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const html = await res.text();
  const anchor = html.indexOf('"storyDetails/:storyId"');
  if (anchor < 0) return null; // 无此案例（页面仍 200，但无 SSR 数据）
  const seg = html.slice(anchor);
  const start = seg.indexOf('{');
  let depth = 0;
  let end = -1;
  for (let j = start; j < seg.length; j++) {
    if (seg[j] === '{') depth++;
    else if (seg[j] === '}') {
      depth--;
      if (depth === 0) { end = j + 1; break; }
    }
  }
  const parsed = JSON.parse(seg.slice(start, end));
  const data = parsed.data || parsed;
  if (!data.storyId || !data.storyTitle) return null;

  const content = stripHtml(decodeEntities(String(data.storyContent || '')));
  return {
    id: 'ttzl-' + data.storyId,
    origin: 'ttzl',
    storyId: data.storyId,
    url,
    title: decodeEntities(data.storyTitle),
    media: String(data.media || '').trim(),        // 推荐/合作媒体
    source: String(data.storySource || '').trim(), // 来源说明
    publishedAt: data.awardShowTime
      ? new Date(Number(data.awardShowTime)).toISOString()
      : null, // 获奖公示时间
    awardPrize: Number(data.awardPrize) || 0,
    category: String(data.storyTag || '').trim(),  // 站点已有类别（创益有为/善意温情…）
    cities: data.cityList || [],
    professions: data.professionList || [],
    identities: data.identityList || [],
    content: content.slice(0, 8000),
    contentLength: content.length,
    fetchedAt: new Date().toISOString(),
  };
}

function decodeEntities(s) {
  return String(s)
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&');
}

/** 与 server.js 同风格的 HTML→纯文本 */
function stripHtml(html) {
  return String(html)
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/(p|div|li|h[1-6]|tr)>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/g, "'")
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

async function fetchStorySafe(id, errors) {
  try {
    return await fetchStory(id);
  } catch (e) {
    errors.push({ id, error: e.message });
    return null;
  }
}

/**
 * 增量采集。
 * @param {object} opts
 *   upward    向上探测的新案例数上限（默认 40）
 *   backfill  本次向下回填的历史案例尝试数（默认 0；首次建库可给 200~500）
 */
export async function collect({ upward = 40, backfill = 0 } = {}) {
  const db = getDb();
  const meta = db.meta;
  meta.ttzlSeen ||= {};
  const seen = meta.ttzlSeen;
  const head = Number(meta.ttzlMaxStoryId || 45338); // 首次运行的已知头部（2026-09-04 侦察确认）
  const errors = [];
  const found = [];
  const stats = { scanned: 0, saved: 0, skipped: 0, misses: 0, errors: errors.length };

  // 1) 向上：发现新案例（连续 25 个落空即认为到顶）
  let miss = 0;
  let maxId = head;
  for (let id = head + 1; id <= head + upward && miss < 25; id++) {
    stats.scanned++;
    const a = await fetchStorySafe(id, errors);
    if (a) {
      miss = 0;
      maxId = Math.max(maxId, a.storyId);
      if (!seen[a.storyId]) { found.push(a); seen[a.storyId] = 1; stats.saved++; }
      else stats.skipped++;
    } else {
      miss++;
      stats.misses++;
    }
    await sleep(SCAN_INTERVAL_MS);
  }
  meta.ttzlMaxStoryId = Math.max(head, maxId - miss); // 顶部连续落空不计入已知

  // 2) 向下：历史回填（连续 15 个落空即停）
  if (backfill > 0) {
    miss = 0;
    const from = head;
    const to = Math.max(1, from - backfill);
    for (let id = from; id >= to && miss < 15; id--) {
      if (seen[id]) { continue; }
      stats.scanned++;
      const a = await fetchStorySafe(id, errors);
      if (a) {
        miss = 0;
        if (!seen[a.storyId]) { found.push(a); seen[a.storyId] = 1; stats.saved++; }
        else stats.skipped++;
      } else {
        miss++;
        stats.misses++;
      }
      await sleep(SCAN_INTERVAL_MS);
    }
  }

  meta.lastCollectAt = new Date().toISOString();
  meta.lastCollectStats = stats;
  meta.lastCollectErrors = errors.slice(0, 10);

  // 3) 入库（留档 + 索引 + 信源抽取）
  for (const a of found) {
    await upsertArticle(a);
  }
  return { ...stats, articles: found };
}

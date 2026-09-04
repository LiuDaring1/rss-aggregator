/* 暖文雷达 — 天天正能量采集器 v0.2.1
 *
 * 站点 https://ttznl.alibabafoundation.com（阿里巴巴公益基金会）
 * - 列表页 /gainEnergy 为 CSR，无公开 JSON 接口（已探测确认）
 * - 详情页 /storyDetails/{id} 为 SSR，内嵌 window.__ICE_APP_CONTEXT__ 结构化数据
 *
 * v0.2.1 增量规则（修复漏报）：
 *   向上扫描起点恒为「最大有效案例 ID + 1」；最大有效 ID 只在真正抓到案例时前进；
 *   连续空 ID 只结束本轮扫描，下轮仍从最大有效 ID+1 重查（未来补录的 ID 不会漏掉）。
 *   之前探测过的最高位置仅作诊断记录（ttzlProbeHeadLog），不作为扫描起点；
 *   大于最大有效 ID 的 seen 记录视为无效，定期清理。
 *   历史回填游标（ttzlMinBackfilledId）与增量游标互相独立。
 * 本地留档保存完整清洗正文（不截断）；AI 输入长度由 analyze.js 单独控制。
 * fetcher / sleepMs 可注入（自动化测试）。
 */
import { getDb, upsertArticle } from './store.js';

const BASE = 'https://ttznl.alibabafoundation.com';
const UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';
const HEADERS = { 'User-Agent': UA, 'Accept-Language': 'zh-CN,zh;q=0.9' };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** epoch(ms) → 中国日期字符串 'YYYY-MM-DD'（源站日期是中国日期，禁止经 UTC 转换显示） */
export function toChinaDate(epochMs) {
  if (!epochMs) return null;
  const d = new Date(Number(epochMs) + 8 * 3600 * 1000); // 东八区偏移后取 UTC 分量即北京日期
  if (isNaN(d.getTime())) return null;
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())}`;
}

/** 从正文开头尽力提取事件发生时间（不保证有，纯 best-effort） */
function extractOccurredAt(content, awardDate) {
  const m = /(\d{4})年(\d{1,2})月(\d{1,2})日|(\d{1,2})月(\d{1,2})日/.exec(String(content || '').slice(0, 400));
  if (!m) return null;
  if (m[1]) return `${m[1]}-${String(m[2]).padStart(2, '0')}-${String(m[3]).padStart(2, '0')}`;
  const year = (awardDate || '').slice(0, 4);
  return year ? `${year}-${String(m[4]).padStart(2, '0')}-${String(m[5]).padStart(2, '0')}` : null;
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
export function stripHtml(html) {
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

/** 解析 SSR 详情页 HTML → 结构化数据（无案例返回 null）。独立导出供测试使用。 */
export function parseStoryHtml(html) {
  const anchor = String(html || '').indexOf('"storyDetails/:storyId"');
  if (anchor < 0) return null;
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
  if (end < 0) return null;
  let parsed;
  try {
    parsed = JSON.parse(seg.slice(start, end));
  } catch {
    return null;
  }
  const data = parsed.data || parsed;
  if (!data.storyId || !data.storyTitle) return null;

  const awardDate = toChinaDate(data.awardShowTime); // 中国日期字符串，如 2026-09-03
  const content = stripHtml(decodeEntities(String(data.storyContent || '')));
  return {
    id: 'ttzl-' + data.storyId,
    origin: 'ttzl',
    storyId: data.storyId,
    url: `${BASE}/storyDetails/${data.storyId}`,
    title: decodeEntities(data.storyTitle),
    media: String(data.media || '').trim(),        // 推荐/合作媒体
    source: String(data.storySource || '').trim(), // 来源说明
    awardDate,                                     // 天天正能量公示/获奖日期
    publishedAt: awardDate,                        // 兼容旧字段
    sourcePublishedAt: null,                       // 原始媒体报道时间，溯源后填
    eventOccurredAt: extractOccurredAt(content, awardDate),
    awardPrize: Number(data.awardPrize) || 0,
    category: String(data.storyTag || '').trim(),
    cities: data.cityList || [],
    professions: data.professionList || [],
    identities: data.identityList || [],
    content, // 完整清洗正文，本地留档不截断（AI 输入限制在 analyze.js 单独处理）
    contentLength: content.length,
    fetchedAt: new Date().toISOString(),
  };
}

export async function defaultFetcher(storyId) {
  const res = await fetch(`${BASE}/storyDetails/${storyId}`, {
    headers: HEADERS,
    signal: AbortSignal.timeout(20000),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return parseStoryHtml(await res.text());
}

async function fetchSafe(fetcher, id, errors) {
  try {
    return await fetcher(id);
  } catch (e) {
    errors.push({ id, error: e.message });
    return null;
  }
}

/**
 * 增量采集 v0.2。
 * @param {object} opts
 *   upward    本轮向上探测的请求预算（默认 40，连续 25 个空 ID 提前结束）
 *   backfill  本轮向下回填的请求预算（默认 0；从 ttzlMinBackfilledId-1 继续向下，连续 15 空结束）
 *   fetcher   注入的抓取函数（测试用），默认 defaultFetcher
 *   sleepMs   请求间隔（测试可传 0）
 */
export async function collect({
  upward = 40,
  backfill = 0,
  fetcher = defaultFetcher,
  sleepMs = 500,
} = {}) {
  const db = getDb();
  const meta = db.meta;
  meta.ttzlSeen ||= {};
  const seen = meta.ttzlSeen;
  const maxValid = Number(meta.ttzlMaxValidId || 0);
  const minBackfilled = Number(meta.ttzlMinBackfilledId || 0);

  // 清理大于最大有效 ID 的无效 seen 记录（那些 ID 当时不存在，未来可能出现）
  if (maxValid > 0) {
    for (const k of Object.keys(seen)) {
      if (Number(k) > maxValid) delete seen[k];
    }
  }

  const errors = [];
  const found = [];
  const stats = { scanned: 0, saved: 0, skipped: 0, misses: 0, upwardScanned: 0, backfillScanned: 0, errors: 0 };

  const tryId = async (id) => {
    stats.scanned++;
    seen[id] = seen[id] || 1;
    const a = await fetchSafe(fetcher, id, errors);
    if (a) {
      const { isNew } = await upsertArticle(a);
      found.push(a);
      if (isNew) stats.saved++;
      else stats.skipped++;
      meta.ttzlMaxValidId = Math.max(meta.ttzlMaxValidId || 0, a.storyId);
      return a;
    }
    stats.misses++;
    return null;
  };

  // 1) 向上增量：起点恒为「最大有效 ID + 1」；连续 25 空提前结束本轮，下轮重查同区间
  let miss = 0;
  let probedTo = maxValid;
  if (maxValid > 0) {
    const upStart = maxValid + 1;
    const upEnd = upStart + upward - 1;
    for (let id = upStart; id <= upEnd && miss < 25; id++) {
      stats.upwardScanned++;
      const a = await tryId(id);
      probedTo = id;
      if (a) miss = 0;
      else miss++;
      if (sleepMs) await sleep(sleepMs);
    }
    meta.ttzlProbeHeadLog = Math.max(Number(meta.ttzlProbeHeadLog || 0), probedTo); // 仅诊断
  }

  // 2) 历史回填：从最小已回填-1 继续向下，预算 backfill 个请求，连续 15 空结束
  if (backfill > 0) {
    miss = 0;
    const anchor = minBackfilled || meta.ttzlMaxValidId || maxValid;
    if (anchor > 1) {
      let scannedDown = 0;
      let lastDown = anchor;
      for (let id = anchor - 1; id >= 1 && scannedDown < backfill && miss < 15; id--) {
        scannedDown++;
        stats.backfillScanned++;
        const a = await tryId(id);
        lastDown = id;
        if (a) {
          miss = 0;
          meta.ttzlMinBackfilledId = Math.min(meta.ttzlMinBackfilledId || Infinity, a.storyId);
        } else {
          miss++;
        }
        if (sleepMs) await sleep(sleepMs);
      }
      if (meta.ttzlMinBackfilledId === undefined || lastDown < (meta.ttzlMinBackfilledId || Infinity)) {
        meta.ttzlMinBackfilledId = lastDown;
      }
    }
  }

  meta.lastCollectAt = new Date().toISOString();
  meta.lastCollectStats = stats;
  meta.lastCollectErrors = errors.slice(0, 10);
  return { ...stats, articles: found };
}

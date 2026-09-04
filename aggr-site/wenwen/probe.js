/* 暖文雷达 — 媒体信源自动探测 v0.2.1（三队列）
 *
 * 首次探测队列：从未探测过的媒体，每家至少轮到一次，不被高案例数媒体抢占；
 * 失败重试队列：官网不可用的媒体按 nextRetryAt 退避重试，区分失败类型；
 * 官网发现队列：无官网线索的媒体用搜索引擎补漏（后续接入，当前如实保持"未定位官网"）。
 * 状态体系：未探测/未定位官网/已定位官网/可采集（待配置）/已接入采集/官网不可用/长期不可用/需要专门适配
 */
import { getDb, scheduleFlush } from './store.js';
import { KNOWN_MEDIA } from './mediaName.js';

export const PROBE_VERSION = '0.2.1';
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36';
const RSS_CANDIDATE_PATHS = ['/rss', '/rss.xml', '/feed', '/feed.xml', '/sitemap.xml'];
const RETRY_BASE_MS = 30 * 60 * 1000; // 失败退避基数 30 分钟

async function check(url, { timeout = 12000 } = {}) {
  try {
    const res = await fetch(url, {
      headers: { 'User-Agent': UA, 'Accept-Language': 'zh-CN,zh;q=0.9' },
      signal: AbortSignal.timeout(timeout),
      redirect: 'follow',
    });
    const body = (await res.text()).slice(0, 4000);
    return { ok: res.ok, status: res.status, body };
  } catch (e) {
    const msg = String(e?.message || e);
    const kind = /getaddrinfo|ENOTFOUND|dns/i.test(msg) ? 'DNS'
      : /aborted|timeout/i.test(msg) ? '超时'
      : /certificate|TLS|SSL/i.test(msg) ? 'TLS'
      : '其他';
    return { ok: false, status: 0, error: `${kind}: ${msg}`.slice(0, 120) };
  }
}

/** 探测一家媒体（官网连通性 + RSS/Sitemap 通道发现），更新实体字段 */
async function probeOne(s) {
  const known = KNOWN_MEDIA[s.name];
  const homepage = s.homepage || known?.homepage;
  const now = new Date().toISOString();
  s.probeCount = (s.probeCount || 0) + 1;
  s.lastProbeAt = now;
  s.probeVersion = PROBE_VERSION;
  s.firstProbeDone = true;

  if (!homepage) {
    s.probeStatus = s.probeStatus === '已接入采集' ? s.probeStatus : '未定位官网';
    return { name: s.name, status: s.probeStatus };
  }
  const home = await check(homepage);
  if (!home.ok) {
    // 失败退避：失败次数越多，下次允许重试越晚；多次失败后标记长期不可用
    s.failCount = (s.failCount || 0) + 1;
    s.lastError = `首页 ${home.status || ''} ${home.error || ''}`.trim();
    s.probeStatus = s.failCount >= 5 ? '长期不可用' : '官网不可用';
    s.nextRetryAt = new Date(Date.now() + RETRY_BASE_MS * Math.pow(2, Math.min(s.failCount, 4))).toISOString();
    return { name: s.name, status: s.probeStatus, error: s.lastError };
  }
  s.homepage = homepage;
  s.failCount = 0;
  s.lastError = null;
  s.probeStatus = '已定位官网';

  // 通道发现：首页内 RSS/Sitemap 链接 + 常见路径
  const found = [];
  for (const m of home.body.matchAll(/href="(https?:\/\/[^"]{8,120}(?:rss|feed|sitemap)[^"]{0,30})"/gi)) {
    found.push(m[1]);
  }
  for (const p of RSS_CANDIDATE_PATHS) {
    try {
      const u = new URL(p, homepage).href;
      const r = await check(u, { timeout: 8000 });
      if (r.ok && /<(rss|feed|urlset)|\{"/i.test(r.body)) found.push(u);
    } catch { /* 单路径失败忽略 */ }
    if (found.length >= 2) break;
  }
  if (found.length) {
    s.rssCandidate = [...new Set(found)].slice(0, 2);
    s.probeStatus = '可采集（待配置）';
    s.fetchMethod = 'RSS/Sitemap（待接入通用采集器）';
  }
  results_guard(s);
  return { name: s.name, status: s.probeStatus, rss: s.rssCandidate || [] };

  function results_guard() { /* 占位：保持函数结构清晰 */ }
}

/**
 * 探测入口。queue:
 *   'first' — 首次探测队列（未完成首次探测的媒体优先，保证全量轮到）
 *   'retry' — 失败重试队列（nextRetryAt 到期的官网不可用媒体）
 *   'auto'  — 先首探后重试（默认）
 */
export async function probeMedia({ queue = 'auto', limit = 20 } = {}) {
  const db = getDb();
  const now = Date.now();
  let pool = [];
  const unprobed = Object.values(db.registry).filter((s) => !s.firstProbeDone);
  const retryable = Object.values(db.registry).filter(
    (s) => s.probeStatus === '官网不可用' && (!s.nextRetryAt || Date.parse(s.nextRetryAt) <= now)
  );
  if (queue === 'first') pool = unprobed;
  else if (queue === 'retry') pool = retryable;
  else pool = [...unprobed, ...retryable];

  // 公平性：未探测队列按案例数升序（让冷门媒体也轮到）→ 不，首探按案例数降序让高价值先接入，
  // 但每家都会在后续轮次中被处理（firstProbeDone 标记），不会被抢占挤出。
  pool.sort((a, b) => (b.articleCount || 0) - (a.articleCount || 0));
  pool = pool.slice(0, limit);

  const results = [];
  for (const s of pool) {
    results.push(await probeOne(s));
  }
  scheduleFlush();
  return { probed: results.length, remaining: unprobed.length - results.filter((r) => r.status !== '官网不可用').length, results };
}

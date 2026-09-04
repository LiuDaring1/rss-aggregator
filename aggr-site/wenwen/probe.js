/* 暖文雷达 — 媒体信源自动探测 v0.2
 *
 * 对全部规范化媒体实体尝试官网连通性与 RSS/Sitemap 探测。
 * 诚实原则：只把实际验证过的能力写进状态；探测不到就记录原因，
 * 不用"已登记"冒充"已接入"。
 */
import { getDb, scheduleFlush } from './store.js';
import { KNOWN_MEDIA } from './mediaName.js';

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36';
const RSS_CANDIDATE_PATHS = ['/rss', '/rss.xml', '/feed', '/feed.xml', '/sitemap.xml'];

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
    return { ok: false, status: 0, error: e.message };
  }
}

/**
 * 探测一批媒体实体（每次调用处理 pending 状态的 N 家，避免长时间占用）。
 * 状态语义：
 *   已定位官网   — 官网首页可达（尚无可用抓取通道）
 *   可采集（待配置）— 官网可达且发现 RSS/Sitemap 候选通道
 *   官网不可用   — 已知官网但访问失败（记录原因）
 *   未定位官网   — 没有可信官网线索，保持原状
 */
export async function probeMedia({ limit = 20 } = {}) {
  const db = getDb();
  const pending = Object.values(db.registry)
    .filter((s) => !s.isTestData)
    .filter((s) => ['未探测', '已定位官网'].includes(s.probeStatus) || (s.probeStatus === '已定位官网' && !s.rssCandidate))
    .sort((a, b) => (b.articleCount || 0) - (a.articleCount || 0))
    .slice(0, limit);

  const results = [];
  for (const s of pending) {
    const known = KNOWN_MEDIA[s.name];
    const homepage = s.homepage || known?.homepage;
    if (!homepage) {
      // 没有官网线索：尝试按名称搜索引擎补漏留给后续；本轮如实标记
      s.probeStatus = s.probeStatus === '未探测' ? '未定位官网' : s.probeStatus;
      s.lastProbeAt = new Date().toISOString();
      results.push({ name: s.name, status: s.probeStatus });
      continue;
    }
    const home = await check(homepage);
    if (!home.ok) {
      s.probeStatus = '官网不可用';
      s.lastError = `首页 ${home.status || ''} ${home.error || ''}`.trim();
      s.lastProbeAt = new Date().toISOString();
      results.push({ name: s.name, status: s.probeStatus, error: s.lastError });
      continue;
    }
    s.homepage = homepage;
    s.probeStatus = '已定位官网';
    s.lastError = null;

    // 在首页 HTML 里找 RSS/Sitemap 链接，再试常见路径
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
    s.lastProbeAt = new Date().toISOString();
    results.push({ name: s.name, status: s.probeStatus, rss: s.rssCandidate || [] });
  }
  scheduleFlush();
  return { probed: results.length, results };
}

/* 暖文雷达 — 通用多信源采集器 v0.2.1
 *
 * 对「可采集（待配置）」的信源实体（已发现 RSS/Sitemap 通道）执行真实采集：
 *   拉取通道 → 解析条目 → 基础预筛（暖文词/降权词）→ 抓正文 → 统一入库
 *   → 同事件聚合 → AI 分析队列。
 * 预筛分级：可能是暖文 / 信息不足 / 明显无关。只有前两类进入 AI。
 * "已接入采集"状态只在真实抓到文章且完成一次增量运行后授予。
 */
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import { XMLParser } from 'fast-xml-parser';
import { getDb, upsertArticle, hashId, scheduleFlush } from './store.js';
import { stripHtml } from './ttzl.js';
import { rebuildEvents } from './merge.js';
import { rebuildRegistry } from './mediaName.js';

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36';
const xmlParser = new XMLParser({ ignoreAttributes: false, attributeNamePrefix: '@_', cdataPropName: '__cdata', textNodeName: '#text', trimValues: true });

/* ---------------- 预筛（便宜、稳定，不调用模型） ---------------- */

const WARM_WORDS = /(?:救|援|捐|赠|暖心|温暖|温情|正能量|好人|好事|拾金不昧|见义勇为|坚守|义务|免费|助学|助老|敬老|孝|爱心|公益|志愿|无偿|救助|善|事迹|感动|护送|上门|帮扶)/;
const COLD_WORDS = /会议|启动仪式|表彰|大会|慰问|调研|视察|致辞|换届|招标|通告|公示名单|干部任免|招聘公告/;

export function prefilter(title) {
  const t = String(title || '');
  if (COLD_WORDS.test(t) && !WARM_WORDS.test(t)) return '明显无关';
  if (WARM_WORDS.test(t)) return '可能是暖文';
  return '信息不足';
}

/* ---------------- 通道抓取 ---------------- */

async function fetchText(url, timeout = 20000) {
  const res = await fetch(url, {
    headers: { 'User-Agent': UA, 'Accept-Language': 'zh-CN,zh;q=0.9' },
    signal: AbortSignal.timeout(timeout),
    redirect: 'follow',
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.text();
}

/** 解析 RSS/Atom 通道为条目数组（标题/链接/时间），无效通道返回 [] */
export function parseFeedItems(xml) {
  try {
    const doc = xmlParser.parse(String(xml));
    const ch = doc?.rss?.channel ?? doc?.feed ?? null;
    if (!ch) return [];
    let raw = ch.item ?? ch.entry;
    if (!raw) return [];
    if (!Array.isArray(raw)) raw = [raw];
    return raw
      .map((it) => {
        const link = it.link?.['@_href'] || (typeof it.link === 'string' ? it.link : '') || it.guid || '';
        const title = String(it.title || '').replace(/<!\[CDATA\[|\]\]>/g, '').trim();
        const date = it.pubDate || it['dc:date'] || it.updated || it.published || '';
        const desc = stripHtml(it.description ?? it.summary ?? '').slice(0, 2000);
        return { title, link: String(link), date: date ? new Date(date) : null, desc };
      })
      .filter((x) => x.title && x.link);
  } catch {
    return [];
  }
}

/** 抓单篇文章正文（通用：取页面主文本，清洗 HTML） */
async function fetchArticleContent(url) {
  try {
    const html = await fetchText(url, 20000);
    const text = stripHtml(html);
    // 粗略去头部导航：取正文中段（通用做法，特定媒体后续专门适配）
    return text.slice(0, 12000);
  } catch {
    return '';
  }
}

/* ---------------- 采集主流程 ---------------- */

/**
 * 对可采集信源执行一轮真实采集。
 * @param {object} opts limit 每轮最多处理多少家信源；itemsPerSource 每家最多入库条数
 */
export async function collectSources({ limit = 5, itemsPerSource = 15 } = {}) {
  const db = getDb();
  const sources = Object.values(db.registry)
    .filter((s) => s.rssCandidate?.length)
    .sort((a, b) => (b.articleCount || 0) - (a.articleCount || 0))
    .slice(0, limit);

  const summary = { sourcesTried: 0, sourcesConnected: 0, articlesSaved: 0, warmKept: 0, skippedIrrelevant: 0, failures: [] };

  for (const s of sources) {
    const channel = s.rssCandidate[0];
    summary.sourcesTried++;
    try {
      const xml = await fetchText(channel, 20000);
      let items = parseFeedItems(xml);
      if (!items.length) throw new Error('通道解析不到条目');

      let saved = 0;
      let known = 0;
      let warm = 0;
      for (const item of items.slice(0, itemsPerSource)) {
        const kind = prefilter(item.title);
        if (kind === '明显无关') { summary.skippedIrrelevant++; continue; }
        if (kind === '可能是暖文') warm++;
        const url = new URL(item.link, channel).href;
        const artId = 'm-' + hashId(url);
        if (db.articleIndex[artId]) { known++; continue; } // URL 已入库

        // 暖文候选才抓正文；信息不足的只存标题条目（轻量）
        const content = kind === '可能是暖文' ? await fetchArticleContent(url) : (item.desc || '');
        if (kind === '可能是暖文' && (!content || content.length < 30)) {
          // 正文抓取失败：仍保留标题条目，标记等待补充
        }
        const article = {
          id: artId,
          origin: 'media',
          url,
          title: item.title,
          media: s.name,
          source: s.name,
          sourceUrl: url,
          awardDate: item.date && !isNaN(item.date) ? item.date.toISOString().slice(0, 10) : null,
          sourcePublishedAt: item.date && !isNaN(item.date) ? item.date.toISOString().slice(0, 10) : null,
          category: '',
          content,
          contentLength: content.length,
          fetchedAt: new Date().toISOString(),
          prefilter: kind,
        };
        const r = await upsertArticle(article);
        if (r.isNew) saved++;
      }
      summary.articlesSaved += saved;
      summary.warmKept += warm;

      // "已接入采集"只授予真实抓到文章且完成一次增量运行的源（按累计抓取口径判定）
      if (items.length) {
        s.articlesFetchedTotal = (s.articlesFetchedTotal || 0) + saved + known;
        s.lastFetchAt = new Date().toISOString();
        s.lastError = null;
        if (s.articlesFetchedTotal > 0) {
          s.connected = true;
          s.probeStatus = '已接入采集';
          s.fetchMethod = `RSS（${channel}）`;
          summary.sourcesConnected++;
        } else {
          s.probeStatus = '可采集（待配置）';
        }
      }
    } catch (e) {
      s.lastError = `通道抓取失败：${e.message}`.slice(0, 120);
      s.lastFetchAt = new Date().toISOString();
      summary.failures.push({ name: s.name, error: s.lastError });
    }
  }

  if (summary.articlesSaved > 0) {
    rebuildRegistry();
    rebuildEvents();
  }
  db.meta.lastSourceCollectAt = new Date().toISOString();
  db.meta.lastSourceCollectSummary = summary;
  scheduleFlush();
  return summary;
}

/** 全量首次探测（分批）：每轮处理一批未探测媒体，直到全部完成 */
export async function probeAllFirst({ batchSize = 20 } = {}) {
  const { probeMedia } = await import('./probe.js');
  const rounds = [];
  for (let i = 0; i < 10; i++) {
    const db = getDb();
    const remaining = Object.values(db.registry).filter((s) => !s.firstProbeDone).length;
    if (!remaining) break;
    const r = await probeMedia({ queue: 'first', limit: batchSize });
    rounds.push({ probed: r.probed, remainingAfter: remaining - r.probed });
    if (!r.probed) break;
  }
  return rounds;
}

/* 暖文雷达 — 媒体名称规范化 v0.2
 *
 * 解决：'潮新闻·钱江晚报'、'扬子晚报·紫牛新闻'、'江南晚报 大象新闻' 这类字符串
 * 被当成一家独立媒体的问题。建立「媒体主体 + 品牌/渠道 + 原始名称」三层实体。
 *
 * - splitMediaNames('江南晚报 大象新闻') → ['江南晚报', '大象新闻']（多来源拆分）
 * - resolveMedia('潮新闻·钱江晚报') → { main: '钱江晚报', brands: ['潮新闻'], rawName: 原串 }
 * - rebuildRegistry(db) → 以媒体主体为键重建信源注册表
 *
 * KNOWN_MEDIA：人工核实的媒体主体官网（探测用）。不确定的媒体保持 main=原始名，
 * 不猜测官网，探测状态如实标'未定位官网'。
 */
import { getDb, scheduleFlush } from './store.js';

/** 内容客户端/渠道 → 该客户端可能的媒体主体（仅辅助线索，不强制归属）
 *  客户端可以服务多家媒体（如 潮新闻 同时服务 浙江日报 和 钱江晚报）。
 *  归属以名称中明确出现的主体为准；名称中没有明确主体时保留原始名称，不猜。
 */
const CLIENT_BRANDS = {
  潮新闻: ['浙江日报', '钱江晚报'],
  犇视频: ['三湘都市报'],
  晨视频: ['潇湘晨报'],
  紫牛新闻: ['扬子晚报'],
  封面新闻: ['华西都市报'],
  齐鲁壹点: ['齐鲁晚报'],
  极目新闻: ['楚天都市报'],
  红星新闻: ['成都商报'],
  上游新闻: ['重庆晨报'],
  大风新闻: ['华商报'],
  大象新闻: ['河南广播电视台'],
  壹点公益: ['齐鲁晚报'],
};

/** 媒体主体 → 官网（探测种子；只登记有把握的） */
export const KNOWN_MEDIA = {
  浙江日报: { homepage: 'https://zjnews.zjol.com.cn', region: '浙江杭州' },
  钱江晚报: { homepage: 'https://tidenews.com.cn', region: '浙江杭州' },
  齐鲁晚报: { homepage: 'https://www.qlid.com', region: '山东济南' },
  扬子晚报: { homepage: 'https://www.yangtse.com', region: '江苏南京' },
  楚天都市报: { homepage: 'http://www.ctdsb.net', region: '湖北武汉' },
  华西都市报: { homepage: 'https://www.thecover.cn', region: '四川成都' },
  羊城晚报: { homepage: 'https://www.ycwb.com', region: '广东广州' },
  大河报: { homepage: 'https://www.dahebao.cn', region: '河南郑州' },
  潇湘晨报: { homepage: 'https://www.xxcb.cn', region: '湖南长沙' },
  三湘都市报: { homepage: 'https://www.sanxiapp.com', region: '湖南长沙' },
  南方都市报: { homepage: 'https://www.nandu.com', region: '广东广州' },
  澎湃新闻: { homepage: 'https://www.thepaper.cn', region: '上海' },
  新京报: { homepage: 'https://www.bjnews.com.cn', region: '北京' },
  成都商报: { homepage: 'https://www.cdsb.com', region: '四川成都' },
  华商报: { homepage: 'https://hsb.hsw.cn', region: '陕西西安' },
  河南广播电视台: { homepage: 'https://www.hntv.tv', region: '河南郑州' },
  江南晚报: { homepage: 'https://www.jnwb.net', region: '江苏无锡' },
  南国今报: { homepage: 'https://www.gxnews.com.cn', region: '广西柳州' },
  杭州日报: { homepage: 'https://www.hangzhou.com.cn', region: '浙江杭州' },
  温州都市报: { homepage: 'https://www.wzdsb.net', region: '浙江温州' },
  海峡都市报: { homepage: 'https://www.hxdsb.net', region: '福建福州' },
  半岛都市报: { homepage: 'https://bandao.cn', region: '山东青岛' },
  重庆晨报: { homepage: 'https://www.cqcb.com', region: '重庆' },
};

const SPLIT_RE = /[、，,;；/＋+&\s]+/;

/** 拆分复合字符串："江南晚报 大象新闻" → ['江南晚报','大象新闻'] */
export function splitMediaNames(str) {
  return String(str || '')
    .split(SPLIT_RE)
    .map((s) => s.trim())
    .filter((s) => s.length >= 2 && s !== '等' && !/^\d+$/.test(s));
}

/** 单个名称（可能含 · 连接的渠道/品牌）→ 媒体实体
 *  解析原则：名称中明确出现的媒体主体优先；客户端品牌只作渠道归属，
 *  且一个客户端可对应多个主体（潮新闻 → 浙江日报 或 钱江晚报）；
 *  名称中没有明确主体时保留原始名称，不猜。
 */
export function resolveMedia(name) {
  const rawName = String(name || '').trim();
  if (!rawName) return null;
  const segments = rawName.split(/[·•・]/).map((s) => s.trim()).filter(Boolean);
  if (!segments.length) return null;

  const isClient = (s) => Object.prototype.hasOwnProperty.call(CLIENT_BRANDS, s);
  // 显式主体：不是已知客户端渠道的段
  const explicitMains = segments.filter((s) => !isClient(s));
  const channels = segments.filter(isClient);

  let main;
  if (explicitMains.length) {
    // 明确主体优先：取最长的显式主体
    main = explicitMains.sort((a, b) => b.length - a.length)[0];
  } else {
    // 全部是渠道（如只有"潮新闻"单独出现）：保留原始名称作为实体，不猜主体
    main = rawName;
  }
  return {
    main,
    channels: [...new Set(channels)],
    aliases: [rawName],
    rawName,
  };
}

/**
 * 以媒体主体为键重建信源注册表（保留探测进度：同主体保留已有 homepage/probeStatus）。
 * 返回 { before, after }：规范化前后数量对比。
 */
export function rebuildRegistry() {
  const db = getDb();
  const before = Object.keys(db.registry).length;
  const entities = new Map();
  const now = new Date().toISOString();

  // 从文章索引聚合每家媒体的原始名称与文章数
  const stats = new Map(); // main -> { articleCount, rawNames:Set, firstAt, lastAt, channels:Set }
  for (const a of Object.values(db.articleIndex)) {
    if (a.isTestData) continue;
    for (const nm of splitMediaNames(a.media || '')) {
      const ent = resolveMedia(nm);
      if (!ent) continue;
      const st = stats.get(ent.main) || { articleCount: 0, rawNames: new Set(), channels: new Set(), firstAt: null, lastSuccessAt: null };
      st.articleCount += 1;
      st.rawNames.add(nm);
      for (const b of ent.channels) st.channels.add(b);
      st.firstAt ||= now;
      st.lastSuccessAt = now;
      stats.set(ent.main, st);
    }
  }

  const old = db.registry || {};
  for (const [main, st] of stats) {
    const prev = old[main] || {};
    // 探测/接入成果必须跨重建保留（rssCandidate/connected/抓取统计等）
    const carried = {
      homepage: prev.homepage || KNOWN_MEDIA[main]?.homepage || null,
      region: prev.region || KNOWN_MEDIA[main]?.region || null,
      probeStatus: prev.probeStatus || (KNOWN_MEDIA[main]?.homepage ? '已定位官网' : '未定位官网'),
      probeCount: prev.probeCount || 0,
      firstProbeDone: prev.firstProbeDone || false,
      probeVersion: prev.probeVersion || null,
      lastProbeAt: prev.lastProbeAt || null,
      nextRetryAt: prev.nextRetryAt || null,
      failCount: prev.failCount || 0,
      lastError: prev.lastError || null,
      rssCandidate: prev.rssCandidate || null,
      fetchMethod: prev.fetchMethod || null,
      connected: prev.connected || false,
      articlesFetchedTotal: prev.articlesFetchedTotal || 0,
      lastFetchAt: prev.lastFetchAt || null,
      warmHits: prev.warmHits || 0,
    };
    entities.set(main, {
      name: main,
      isEntity: true,
      brands: [...st.channels],
      channels: [...st.channels],
      aliases: [...st.rawNames],
      origin: prev.origin || 'ttzl-case',
      registeredAt: prev.registeredAt || now,
      articleCount: st.articleCount,
      firstArticleAt: st.firstAt,
      lastSuccessAt: st.lastSuccessAt,
      ...carried,
    });
  }
  db.registry = Object.fromEntries(entities);
  scheduleFlush();
  return { before, after: entities.size };
}

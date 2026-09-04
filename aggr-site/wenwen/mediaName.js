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

/** 品牌/客户端 → 媒体主体（人工核实的已知映射，可持续补充） */
const BRAND_TO_MAIN = {
  潮新闻: '钱江晚报',
  紫牛新闻: '扬子晚报',
  封面新闻: '华西都市报',
  齐鲁壹点: '齐鲁晚报',
  极目新闻: '楚天都市报',
  红星新闻: '成都商报',
  上游新闻: '重庆晨报',
  大风新闻: '华商报',
  潇湘晨报: '潇湘晨报',
  大象新闻: '河南广播电视台',
  壹点公益: '齐鲁晚报',
};

/** 媒体主体 → 官网（探测种子；只登记有把握的） */
export const KNOWN_MEDIA = {
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

/** 单个名称（可能含 · 连接的品牌）→ 媒体实体 */
export function resolveMedia(name) {
  const rawName = String(name || '').trim();
  if (!rawName) return null;
  const segments = rawName.split(/[·•・]/).map((s) => s.trim()).filter(Boolean);
  if (!segments.length) return null;

  // 每段解析为主体：已知品牌映射到主体，未知段暂作主体候选
  const mains = segments.map((seg) => ({ seg, main: BRAND_TO_MAIN[seg] || seg }));

  // 已知映射优先作为主体；否则取最长段为主体（如'广西日报传媒集团 南国今报'）
  let main = null;
  const brands = [];
  for (const { seg, main: m } of mains) {
    if (BRAND_TO_MAIN[seg] && BRAND_TO_MAIN[seg] === m) {
      main = m;
    } else if (BRAND_TO_MAIN[seg]) {
      brands.push(seg);
    }
  }
  if (!main) {
    main = mains.map((m) => m.main).sort((a, b) => b.length - a.length)[0];
  }
  for (const { seg, main: m } of mains) {
    if (seg !== main && m === main) brands.push(seg); // 非主体段都是品牌别名
  }
  return {
    main,
    brands: [...new Set(brands)],
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
  const stats = new Map(); // main -> { articleCount, rawNames:Set, firstAt, lastAt, brands:Set }
  for (const a of Object.values(db.articleIndex)) {
    if (a.isTestData) continue;
    for (const nm of splitMediaNames(a.media || '')) {
      const ent = resolveMedia(nm);
      if (!ent) continue;
      const st = stats.get(ent.main) || { articleCount: 0, rawNames: new Set(), brands: new Set(), firstAt: null, lastSuccessAt: null };
      st.articleCount += 1;
      st.rawNames.add(nm);
      for (const b of ent.brands) st.brands.add(b);
      st.firstAt ||= now;
      st.lastSuccessAt = now;
      stats.set(ent.main, st);
    }
  }

  const old = db.registry || {};
  for (const [main, st] of stats) {
    const prev = old[main] || {};
    entities.set(main, {
      name: main,
      isEntity: true,
      brands: [...st.brands],
      aliases: [...st.rawNames],
      origin: 'ttzl-case',
      region: KNOWN_MEDIA[main]?.region || prev.region || null,
      homepage: prev.homepage || KNOWN_MEDIA[main]?.homepage || null,
      probeStatus: prev.probeStatus || (KNOWN_MEDIA[main]?.homepage ? '已定位官网' : '未定位官网'),
      fetchMethod: prev.fetchMethod || null,
      registeredAt: prev.registeredAt || now,
      articleCount: st.articleCount,
      firstArticleAt: st.firstAt,
      lastSuccessAt: st.lastSuccessAt,
      lastProbeAt: prev.lastProbeAt || null,
      lastError: prev.lastError || null,
    });
  }
  db.registry = Object.fromEntries(entities);
  scheduleFlush();
  return { before, after: entities.size };
}

import { initStore, getDb, flushNow } from './store.js';
await initStore();
const db = getDb();
db.registry['中国新闻网'] = {
  name: '中国新闻网', isEntity: true, brands: [], aliases: ['中新网'],
  origin: 'manual', region: '北京',
  homepage: 'https://www.chinanews.com.cn',
  rssCandidate: ['https://www.chinanews.com.cn/rss/scroll-news.xml'],
  probeStatus: '可采集（待配置）', fetchMethod: null,
  registeredAt: new Date().toISOString(), articleCount: 0,
  firstProbeDone: true, probeCount: 1, lastProbeAt: new Date().toISOString(),
};
await flushNow();
console.log('中国新闻网 已注册，实体总数:', Object.keys(db.registry).length);

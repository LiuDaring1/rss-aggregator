import { initStore, getDb, flushNow } from './store.js';
await initStore();
const db = getDb();
const restore = {
  潇湘晨报: ['https://www.xxcb.cn/sitemap.xml'],
  新京报: ['https://www.bjnews.com.cn/rss', 'https://www.bjnews.com.cn/sitemap.xml'],
  中国新闻网: ['https://www.chinanews.com.cn/rss/scroll-news.xml'],
};
for (const [name, rss] of Object.entries(restore)) {
  const s = db.registry[name];
  if (!s) { console.log(name, '不存在'); continue; }
  s.rssCandidate ||= rss;
  s.connected = s.connected || false;
  console.log(name, '→ rss:', s.rssCandidate, '| connected:', s.connected);
}
await flushNow();
console.log('通道恢复完成');

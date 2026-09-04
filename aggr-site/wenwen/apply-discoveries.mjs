/* 浏览器官网发现结果写入注册表（只写经百度搜索+人工确认的官网） */
import { initStore, getDb, flushNow } from './store.js';
await initStore();
const db = getDb();
const found = {
  南国早报: 'https://www.ngzb.com.cn',
  齐鲁晚报: 'https://www.ql1d.com',
  三湘都市报: 'https://sxdsb-dzb.voc.com.cn',
  长沙晚报: 'https://www.cswb.cn',
  江南都市报: 'https://newspaper.jxnews.com.cn',
  三秦都市报: 'https://epaper.sanqin.com',
  川观新闻: 'https://cbgc2.scol.com.cn',
  湖北日报: 'https://www.hubeidaily.net',
};
for (const [name, hp] of Object.entries(found)) {
  const s = db.registry[name];
  if (!s) { console.log(name, '不在注册表'); continue; }
  s.homepage = hp;
  s.probeStatus = '已定位官网';
  s.firstProbeDone = true;
  s.lastProbeAt = new Date().toISOString();
  s.discoveredBy = 'baidu-browser';
  console.log(name, '→', hp);
}
await flushNow();
console.log('共更新', Object.keys(found).length, '家');

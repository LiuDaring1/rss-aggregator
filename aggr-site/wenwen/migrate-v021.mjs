/* v0.2.1 数据迁移：一次性运行
 *   node wenwen/migrate-v021.mjs
 * 内容：
 *   1) 每篇留档补 appearances=[自身来源记录]（多信源同正文不丢来源）；
 *      正文若不足 8000 且源站可能有全文，保留现状（增量采集的新数据天然完整）；
 *   2) sourceCount 按 appearances 长度刷新；
 *   3) 信源注册表按新版媒体归属规则重建（显式主体优先）；
 *   4) 游标字段迁移：ttzlProbeHead（旧扫描头）→ ttzlProbeHeadLog（仅诊断），
 *      增量起点恢复为 ttzlMaxValidId+1（未来补录 ID 不会漏）。
 * 可重复执行（幂等）。
 */
import { initStore, getDb, loadRaw, saveRaw, flushNow } from './store.js';
import { rebuildRegistry } from './mediaName.js';
import { rebuildEvents } from './merge.js';

await initStore();
const db = getDb();

let n = 0;
for (const aid of Object.keys(db.articleIndex)) {
  const raw = await loadRaw(aid);
  if (!raw) continue;
  raw.appearances ||= [{
    media: raw.media || '',
    rawMedia: raw.source || raw.media || '',
    url: raw.url,
    title: raw.title,
    awardDate: raw.awardDate || (raw.publishedAt || '').slice(0, 10),
    fetchedAt: raw.fetchedAt,
    identicalContent: true,
    suspectedRepost: false,
    sourceType: raw.origin || '',
  }];
  raw.sourceTitle = raw.title; // 源站原始标题；displayTitle 仅在系统整理时另行标记
  await saveRaw(raw);
  const idx = db.articleIndex[aid];
  idx.sourceCount = raw.appearances.length;
  n++;
}

const reg = rebuildRegistry();
const ev = rebuildEvents();

// 游标字段迁移
if (db.meta.ttzlProbeHead && !db.meta.ttzlProbeHeadLog) {
  db.meta.ttzlProbeHeadLog = db.meta.ttzlProbeHead;
}
delete db.meta.ttzlProbeHead; // 旧扫描头不再作为扫描起点

await flushNow();
console.log(`[migrate-v021] appearances 补齐 ${n} 篇 | 信源实体 ${reg.after} 家 | 事件 ${ev.eventCount} 个（${ev.inheritedAnalysis} 继承分析）`);
console.log(`[migrate-v021] 增量起点已恢复为 最大有效ID+1（诊断扫描头=${db.meta.ttzlProbeHeadLog}）`);

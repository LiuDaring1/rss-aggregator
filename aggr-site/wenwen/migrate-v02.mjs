/* v0.2 数据迁移：一次性运行
 *   node wenwen/migrate-v02.mjs
 * 内容：
 *   1) 每篇留档与索引补 awardDate（中国日期）/ contentHash / 质量标记 / eventOccurredAt
 *   2) 信源注册表按媒体主体重建（规范化）
 *   3) 事件按新指纹重建（AI 分析因 schema 升级需要重跑，用户保留/忽略状态继承）
 *   4) 采集游标迁移（ttzlMaxValidId / ttzlProbeHead / ttzlMinBackfilledId）
 */
import { initStore, getDb, loadRaw, listRawIds, flushNow } from './store.js';
import { toChinaDate } from './ttzl.js';
import { rebuildRegistry } from './mediaName.js';
import { rebuildEvents } from './merge.js';

await initStore();
const db = getDb();
const { qualityFlags } = await import('./store.js');

const ids = await listRawIds();
let migrated = 0;
for (const id of ids) {
  const raw = await loadRaw(id);
  if (!raw) continue;
  const epoch = raw.publishedAt ? Date.parse(raw.publishedAt) : null;
  const awardDate = toChinaDate(epoch) || (raw.publishedAt || '').slice(0, 10) || null;
  raw.awardDate = awardDate;
  raw.eventOccurredAt = raw.eventOccurredAt || null;
  raw.sourcePublishedAt = raw.sourcePublishedAt || null;
  raw.contentHash = undefined; // 由 upsert 逻辑重算
  delete raw.contentHash;
  // 直接内联与 store.upsertArticle 相同的标记/哈希逻辑
  const crypto = await import('node:crypto');
  raw.contentHash = crypto.createHash('sha1').update(String(raw.content || '').replace(/\s+/g, '')).digest('hex').slice(0, 20);
  const flags = [];
  if (/测试/.test(raw.title || '')) flags.push('疑似测试数据');
  if (!raw.title || String(raw.title).length < 6) flags.push('标题可能不完整');
  if (!raw.content || raw.content.length < 30) flags.push('正文异常过短');
  if (/\uFFFD/.test((raw.title || '') + (raw.content || ''))) flags.push('编码异常');
  if (!raw.media) flags.push('缺媒体');
  if (!raw.publishedAt) flags.push('缺日期');
  raw.flags = flags;
  raw.isTestData = flags.includes('疑似测试数据') || (flags.includes('正文异常过短') && !raw.media && !raw.publishedAt);
  await (await import('./store.js')).saveRaw(raw);

  const idx = db.articleIndex[id];
  if (idx) {
    idx.awardDate = awardDate;
    idx.publishedAt = awardDate;
    idx.contentHash = raw.contentHash;
    idx.contentLength = (raw.content || '').length;
    idx.flags = flags;
    idx.isTestData = raw.isTestData;
  }
  migrated++;
}

// 采集游标迁移
db.meta.ttzlSeen ||= {};
const seenIds = Object.keys(db.meta.ttzlSeen).map(Number).filter((n) => !isNaN(n));
const seenMin = seenIds.length ? Math.min(...seenIds) : null;
db.meta.ttzlMaxValidId = Number(db.meta.ttzlMaxStoryId || 45338);
db.meta.ttzlProbeHead = Number(db.meta.ttzlMaxStoryId || 45338) + 25; // v0.1 曾向上扫过 25 个空 ID
db.meta.ttzlMinBackfilledId = seenMin || Number(db.meta.ttzlMaxStoryId || 45338);
delete db.meta.ttzlMaxStoryId;

const reg = rebuildRegistry();
const ev = rebuildEvents();
await flushNow();
console.log(`[migrate-v02] 迁移 ${migrated} 篇 | 信源 ${reg.before} → ${reg.after} 家 | 事件 ${ev.eventCount} 个（${ev.inheritedAnalysis} 继承分析 / ${ev.reanalyzedNeeded} 需重分析）`);
console.log(`[migrate-v02] 游标: maxValid=${db.meta.ttzlMaxValidId} probeHead=${db.meta.ttzlProbeHead} minBackfilled=${db.meta.ttzlMinBackfilledId}`);

/* 暖文雷达 — 脏数据自动修复 v0.2.1
 *
 * 顺序（对照任务书）：
 * 1) 对缺媒体/缺日期/正文过短的天天正能量案例重新抓取一次；
 * 2) 源站重新有数据则更新；源站本身没有 → 标记"源站未提供"，不算解析失败；
 * 3) 同事件内有完整记录时，用完整记录补齐确定相同的元数据（媒体/获奖日期），
 *    并保留字段来源标记（mediaSource: 'same-event'）；
 * 4) 测试数据继续排除；正文过短不进入正式 AI 分析；标题疑似截断保留原始标题。
 */
import { getDb, loadRaw, saveRaw, scheduleFlush } from './store.js';
import { defaultFetcher as fetchStory } from './ttzl.js';

export async function repairDirty({ max = 100 } = {}) {
  const db = getDb();
  const candidates = Object.values(db.articleIndex)
    .filter((a) => a.origin === 'ttzl' && !a.isTestData)
    .filter((a) => (a.flags || []).some((f) => ['缺媒体', '缺日期', '正文异常过短'].includes(f)))
    .slice(0, max);

  const result = { refetched: 0, fixedByRefetch: 0, sourceNotProvided: 0, fixedBySibling: 0, stillDirty: 0 };
  const storyIdOf = (aid) => Number(String(aid).replace('ttzl-', ''));

  // 1) 重抓一次
  for (const a of candidates) {
    const sid = storyIdOf(a.id);
    if (!sid) continue;
    result.refetched++;
    let fresh = null;
    try {
      fresh = await fetchStory(sid);
    } catch { /* 抓取失败保持原状 */ }
    if (fresh) {
      fresh.appearances = (await loadRaw(a.id))?.appearances;
      const { isNew } = await upsertArticle(fresh); // 会重算 flags / contentHash
      if (!isNew) { /* 已存在则 upsert 覆盖更新 */ }
      const idx = db.articleIndex[a.id];
      const stillMissing = (idx.flags || []).some((f) => ['缺媒体', '缺日期'].includes(f));
      if (!stillMissing) result.fixedByRefetch++;
      await saveRaw(await loadRaw(a.id));
    } else {
      result.sourceNotProvided++;
      a.flags = [...new Set([...(a.flags || []), '源站未提供'])];
      const idx = db.articleIndex[a.id];
      if (idx) idx.flags = a.flags;
    }
  }

  // 2) 同事件内用完整记录补齐（媒体/获奖日期），保留字段来源
  for (const ev of Object.values(db.events)) {
    const arts = ev.articleIds.map((aid) => ({ aid, idx: db.articleIndex[aid], raw: null }));
    const complete = arts.filter((x) => x.idx?.media && (x.idx.awardDate || x.idx.publishedAt));
    for (const x of arts) {
      if (!x.idx || complete.some((c) => c.aid === x.aid)) continue;
      const src = complete[0];
      if (!src) continue;
      let changed = false;
      if (!x.idx.media && src.idx.media) { x.idx.media = src.idx.media; x.idx.mediaSource = 'same-event'; changed = true; result.fixedBySibling++; }
      if (!x.idx.awardDate && src.idx.awardDate) { x.idx.awardDate = src.idx.awardDate; x.idx.publishedAt = src.idx.awardDate; x.idx.dateSource = 'same-event'; changed = true; }
      if (changed) {
        const raw = await loadRaw(x.aid);
        if (raw) {
          raw.media = x.idx.media;
          raw.awardDate = x.idx.awardDate;
          raw.flags = (raw.flags || []).filter((f) => f !== '缺媒体' && f !== '缺日期');
          await saveRaw(raw);
        }
      }
    }
  }

  // 3) 统计仍然脏的数量
  result.stillDirty = Object.values(db.articleIndex).filter((a) =>
    !a.isTestData && (a.flags || []).some((f) => ['缺媒体', '缺日期', '正文异常过短'].includes(f))
  ).length;

  db.meta.lastRepairAt = new Date().toISOString();
  db.meta.lastRepairResult = result;
  scheduleFlush();
  return result;
}

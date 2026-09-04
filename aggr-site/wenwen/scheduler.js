/* 暖文雷达 — 定时调度：采集 → 合并 → 分析。
 * 单一来源失败只记录不抛出，不影响其他环节；所有任务有并发保护。
 */
import { collect } from './ttzl.js';
import { rebuildEvents } from './merge.js';
import { analyzePending } from './analyze.js';
import { getDb, initStore, flushNow } from './store.js';

const COLLECT_INTERVAL_MS = 6 * 3600 * 1000; // 采集：每 6 小时
const ANALYZE_INTERVAL_MS = 20 * 60 * 1000; // 分析：每 20 分钟（有缓存不会重复烧 token）

let collecting = false;
let analyzing = false;

export async function runCollect({ backfill = 0 } = {}) {
  if (collecting) return { skipped: true, reason: '采集进行中' };
  collecting = true;
  try {
    const result = await collect({ backfill });
    if (result.saved > 0) rebuildEvents();
    getDb().meta.lastCollectAt = new Date().toISOString();
    console.log(`[wenwen] 采集完成: 扫描${result.scanned} 新增${result.saved} 跳过${result.skipped} 落空${result.misses}`);
    return result;
  } catch (e) {
    console.error('[wenwen] 采集失败:', e.message);
    return { error: e.message };
  } finally {
    collecting = false;
    await flushNow();
  }
}

export async function runAnalyze({ limit = 6 } = {}) {
  if (analyzing) return { skipped: true, reason: '分析进行中' };
  analyzing = true;
  try {
    const result = await analyzePending({ limit });
    if (result.analyzed > 0) console.log(`[wenwen] AI 分析完成: ${result.analyzed} 个事件，剩余待分析 ${result.pendingCount}`);
    return result;
  } catch (e) {
    console.error('[wenwen] AI 分析失败:', e.message);
    return { error: e.message };
  } finally {
    analyzing = false;
    await flushNow();
  }
}

let started = false;
export async function startWenwenScheduler() {
  if (started) return;
  started = true;
  await initStore(); // 调度先于任何请求运行，必须先建好存储
  // 启动后先采集一轮（增量为空时很快），随后补一轮分析
  setTimeout(async () => {
    const r = await runCollect();
    if (!r.error && !r.skipped && (r.saved > 0 || !getDb().meta.lastStartupAnalyzed)) {
      getDb().meta.lastStartupAnalyzed = true;
      await runAnalyze({ limit: 8 });
    }
  }, 6000);
  setInterval(() => runCollect(), COLLECT_INTERVAL_MS);
  setInterval(() => runAnalyze({ limit: 5 }), ANALYZE_INTERVAL_MS);
  console.log('[wenwen] 暖文雷达调度已启动（采集 6h / 分析 20min）');
}

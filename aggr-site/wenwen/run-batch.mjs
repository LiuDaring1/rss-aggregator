/* 分析批处理：独立进程运行（运行期间站点短暂不可用）
 *   node wenwen/run-batch.mjs [rounds] [perRound]
 * 默认 4 轮 × 每轮 10 个事件。结束后输出分布。
 */
import { initStore, flushNow } from './store.js';
import { analyzePending, checkDistribution, pickPendingEvents } from './analyze.js';

const rounds = Number(process.argv[2] || 4);
const perRound = Number(process.argv[3] || 10);

await initStore();
console.log(`[batch] 开始：${rounds} 轮 × 每轮 ${perRound} 个，当前待分析 ${pickPendingEvents(9999).length}`);

let total = 0;
const failed = [];
for (let i = 1; i <= rounds; i++) {
  const t0 = Date.now();
  try {
    const r = await analyzePending({ limit: perRound });
    total += r.analyzed;
    console.log(`[batch] 轮${i}: 分析 ${r.analyzed} 失败 ${r.failed.length} 剩余 ${r.pendingCount} 用时 ${Math.round((Date.now() - t0) / 1000)}s`);
    for (const f of r.failed.slice(0, 3)) console.log(`  失败: ${f.error?.slice(0, 80)}`);
    if (!r.analyzed && !r.pendingCount) break;
  } catch (e) {
    console.error(`[batch] 轮${i} 异常:`, e.message);
    failed.push(e.message);
  }
}
const fc = checkDistribution();
await flushNow();
console.log(`[batch] 完成：本次共分析 ${total}`);
if (fc) {
  console.log(`[batch] 塌缩警告: ${fc.warning || '无'}`);
  for (const k of ['materialValue', 'infoMaturity', 'suggestedUse', 'eventMotif']) {
    console.log(' ', k, JSON.stringify(fc.distribution[k], ensure_ascii => ensure_ascii));
  }
}

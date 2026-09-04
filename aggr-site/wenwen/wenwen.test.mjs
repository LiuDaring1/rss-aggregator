/* 暖文雷达 v0.2 基础测试（node:test，零外部依赖）
 * 运行：cd aggr-site && node --test wenwen/wenwen.test.mjs
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { initStore, getDb, upsertArticle, loadRaw, hashId } from './store.js';
import { parseStoryHtml, toChinaDate, collect } from './ttzl.js';
import { rebuildEvents } from './merge.js';
import { resolveMedia, splitMediaNames } from './mediaName.js';
import { probeMedia } from './probe.js';
import { mountWenwen, mountWenwenReport } from './routes.js';

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'wenwen-test-'));
}

function makeArticle(storyId, title, content, media = '测试日报', awardShowTime = 1788364800000) {
  return {
    id: 'ttzl-' + storyId,
    origin: 'ttzl',
    storyId,
    url: `https://ttznl.alibabafoundation.com/storyDetails/${storyId}`,
    title,
    media,
    source: media,
    awardDate: toChinaDate(awardShowTime),
    publishedAt: toChinaDate(awardShowTime),
    awardPrize: 5000,
    category: '善意温情',
    cities: [], professions: [], identities: [],
    content,
    contentLength: content.length,
    fetchedAt: new Date().toISOString(),
  };
}

/* 1. 详情页解析 */
test('天天正能量详情页解析：结构化字段完整提取', () => {
  const html = `<html><script>window.__ICE_APP_CONTEXT__=Object.assign({"appData":null,"loaderData":{"layout":{},"storyDetails/:storyId":{"data":{"storyId":45338,"storyTitle":"五年走遍武陵源6个乡镇","awardShowTime":1788364800000,"awardPrize":10000,"storyTag":"创益有为","media":"三湘都市报","storySource":"三湘都市报","cityList":["湖南张家界"],"professionList":["公益人"],"identityList":["其他"],"storyContent":"&lt;p&gt;华声在线记者罗艾敏&lt;/p&gt;&lt;p&gt;50个孩子喊张爸爸&lt;/p&gt;"}}}})</script></html>`;
  const a = parseStoryHtml(html);
  assert.equal(a.storyId, 45338);
  assert.equal(a.title, '五年走遍武陵源6个乡镇');
  assert.equal(a.awardDate, '2026-09-03'); // 中国日期，不是 2026-09-02
  assert.equal(a.media, '三湘都市报');
  assert.ok(a.content.includes('华声在线记者罗艾敏'));
  assert.ok(!a.content.includes('<p>'));
  assert.equal(parseStoryHtml('<html>没有数据</html>'), null);
});

/* 4. 中国日期不提前一天 */
test('中国日期：epoch 转换为东八区日期字符串', () => {
  assert.equal(toChinaDate(1788364800000), '2026-09-03'); // UTC 是 09-02 16:00
  assert.equal(toChinaDate(0), null);
});

/* 2. 向上增量 v0.2.1：起点恒为最大有效 ID+1，重复检查不产生重复入库 */
test('向上增量：连续空 ID 后游标仍前进且不重复抓取', async () => {
  const dir = tmpDir();
  await initStore({ dataDir: dir, reset: true });
  const db = getDb();
  db.meta.ttzlMaxValidId = 100;
  db.meta.ttzlSeen = {};

  const fetched = [];
  const fetcher = async (id) => {
    fetched.push(id);
    return id === 116 ? makeArticle(116, '山路上的背篓医生', '她背起药箱走了二十年。') : null;
  };
  const r1 = await collect({ upward: 40, fetcher, sleepMs: 0 });
  assert.equal(r1.saved, 1);
  assert.equal(db.meta.ttzlMaxValidId, 116);
  assert.ok(db.meta.ttzlProbeHeadLog >= 116, '诊断扫描头覆盖到有效 ID');
  assert.equal(fetched.includes(100), false, '不重复扫描已知区间');

  // 第二轮：起点仍是最大有效 ID+1（重复检查同区间，符合防漏报设计），但不会重复入库
  const r2 = await collect({ upward: 40, fetcher, sleepMs: 0 });
  assert.equal(r2.saved, 0, '第二轮无重复入库');
  assert.equal(db.meta.ttzlMaxValidId, 116, '最大有效 ID 稳定');
  assert.equal(fetched.includes(101), true, '第二轮从 101 重新检查');
});

/* 3. 历史回填继续 */
test('历史回填：从最小已回填 ID 继续，不重复扫描', async () => {
  const dir = tmpDir();
  await initStore({ dataDir: dir, reset: true });
  const db = getDb();
  db.meta.ttzlMaxValidId = 100;
  db.meta.ttzlMinBackfilledId = 90;
  db.meta.ttzlSeen = {};

  const fetched = [];
  const fetcher = async (id) => {
    fetched.push(id);
    return id === 88 ? makeArticle(88, '悬空寺上的环卫工', '他每天攀岩捡垃圾。') : null;
  };
  await collect({ backfill: 5, fetcher, sleepMs: 0 });
  assert.equal(db.meta.ttzlMinBackfilledId, 85, '扫过 89-85');
  assert.equal(db.meta.ttzlMaxValidId, 100);
  assert.equal(fetched.filter((x) => x === 88).length, 1);

  await collect({ backfill: 5, fetcher, sleepMs: 0 });
  assert.equal(db.meta.ttzlMinBackfilledId, 80, '第二轮从 84 继续向下');
  assert.equal(fetched.filter((x) => x === 89).length, 1, '89 只在第一轮扫描过，不重复');
  assert.equal(fetched.includes(85), true, '85 第一轮扫过');
  assert.equal(fetched.filter((x) => x === 85).length, 1, '第二轮不再扫 85');
});

/* 9. contentHash / URL 去重 */
test('去重：同一正文不同 URL 不会重复入库', async () => {
  await initStore({ dataDir: tmpDir(), reset: true });
  const a1 = makeArticle(201, '事件的报道A', '完全相同的一段正文内容，足够长以计算哈希。');
  const a2 = { ...makeArticle(202, '事件的报道B', '完全相同的一段正文内容，足够长以计算哈希。') };
  const r1 = await upsertArticle(a1);
  const r2 = await upsertArticle(a2);
  assert.equal(r1.isNew, true);
  assert.equal(r2.isNew, false);
  assert.equal(r2.duplicateOf, a1.id);
  assert.equal(Object.keys(getDb().articleIndex).length, 1);
});

/* 5 + 6. 事件重建：分析继承与按需重分析 */
test('事件重建：新增无关事件不清空旧事件 AI 分析；文章变化才重分析', async () => {
  await initStore({ dataDir: tmpDir(), reset: true });
  await upsertArticle(makeArticle(301, '小伙跳水救人婉拒酬谢', '他跳入河中救起孩子，摆手拒绝酬谢。'));
  await upsertArticle(makeArticle(302, '小伙跳水救人婉拒酬谢获全城点赞', '获救孩子家人送来锦旗，他依然婉拒酬谢。'));
  const r1 = rebuildEvents();
  const ev1 = Object.values(getDb().events)[0];
  assert.equal(ev1.articleIds.length, 2, '同事件两篇被合并');

  // 模拟 AI 已分析 + 用户已保留
  ev1.analysis = { oneLine: 'x', suggestedUse: '完整加工', materialValue: '高', infoMaturity: '完整' };
  ev1.analysisAt = '2026-09-04T00:00:00Z';
  ev1.analysisArticleCount = ev1.articleIds.length;
  ev1.userStatus = 'kept';
  const fpBefore = ev1.fingerprint;

  // 新增一个完全无关的事件
  await upsertArticle(makeArticle(303, '山村教师坚守讲台三十年', '大山里的教室，她一站就是三十年。'));
  rebuildEvents();
  const ev1b = Object.values(getDb().events).find((e) => e.fingerprint === fpBefore);
  assert.ok(ev1b, '旧事件仍存在');
  assert.ok(ev1b.analysis, '新增无关事件后旧事件 AI 分析保留');
  assert.equal(ev1b.userStatus, 'kept', '用户保留状态保留');
  assert.equal(Object.keys(getDb().events).length, 2, '共两个事件');
  // 另一个独立事件也有 AI 分析（验证它不受后面合并影响）
  const ev2 = Object.values(getDb().events).find((e) => e.fingerprint !== fpBefore);
  ev2.analysis = { oneLine: 'y', suggestedUse: '短复述或案例', materialValue: '中', infoMaturity: '完整' };
  ev2.analysisAt = '2026-09-04T00:00:00Z';
  ev2.analysisArticleCount = ev2.articleIds.length;

  // 事件本身新增文章 → 指纹变化 → 只重分析该事件
  await upsertArticle(makeArticle(304, '小伙跳水救人婉拒酬谢后续：学校聘他为安全辅导员', '当地小学聘他担任安全辅导员。'));
  rebuildEvents();
  const ev1c = Object.values(getDb().events).find((e) => e.articleIds.length === 3);
  assert.ok(ev1c, '合并后事件含 3 篇');
  assert.equal(ev1c.analysis, null, '文章变化的事件重新等待分析');
  assert.equal(ev1c.userStatus, 'kept', '用户状态仍保留');
  const other = Object.values(getDb().events).find((e) => e.id !== ev1c.id);
  assert.ok(other.analysis, '无关事件的分析不受影响');
});

/* 7. 媒体名称拆分与别名归一 */
test('媒体规范化：拆分复合名，品牌归一到主体', () => {
  assert.deepEqual(splitMediaNames('江南晚报 大象新闻'), ['江南晚报', '大象新闻']);
  const e1 = resolveMedia('潮新闻·钱江晚报');
  assert.equal(e1.main, '钱江晚报');
  assert.ok(e1.channels.includes('潮新闻'));
  const e2 = resolveMedia('扬子晚报·紫牛新闻');
  assert.equal(e2.main, '扬子晚报');
  assert.equal(e2.channels.includes('紫牛新闻'), true);
  const e3 = resolveMedia('江南晚报');
  assert.equal(e3.main, '江南晚报');
});

/* 10. 测试数据不进入正式候选 */
test('测试数据：标记 isTestData 且不进入事件与候选', async () => {
  await initStore({ dataDir: tmpDir(), reset: true });
  await upsertArticle(makeArticle(401, '测试测试 1', 'x'));
  await upsertArticle(makeArticle(402, '真实暖事件：女孩用压岁钱给环卫工买早餐', '她用攒下的压岁钱请环卫工吃热早餐。'));
  const r = rebuildEvents();
  assert.equal(r.articleCount, 1, '测试数据不参与事件');
  const db = getDb();
  assert.equal(db.articleIndex['ttzl-401'].isTestData, true);
  assert.equal(Object.keys(db.events).length, 1);
});

/* 8. 本地全文完整读取（不截断） */
test('本地全文：接口返回完整正文（超过 6000 字也不截断）', async () => {
  const dir = tmpDir();
  await initStore({ dataDir: dir, reset: true });
  const longContent = '正文段落。'.repeat(2000); // 10000 字
  await upsertArticle(makeArticle(501, '长篇人物通讯', longContent));
  rebuildEvents();

  const captured = {};
  const mockRes = {
    writeHead: (c, h) => { captured.code = c; captured.headers = h; },
    end: (body) => { captured.body = body; },
  };
  await mountWenwen(
    { method: 'GET' },
    mockRes,
    new URL('http://localhost/wenwen/api/articles/ttzl-501')
  );
  const data = JSON.parse(captured.body);
  assert.equal(data.contentLength, longContent.length, '记录的正文长度正确');
  assert.equal(data.content.length, longContent.length, '返回完整正文，未被 6000 字截断');
  assert.equal(data.eventId, Object.keys(getDb().events)[0]);
  assert.equal(data.ttzlUrl.includes('storyDetails/501'), true);
});

/* ===== v0.2.1 新增测试 ===== */

/* 未来 ID：上一轮为空、下一轮出现时可以抓到（漏报回归） */
test('v021 增量：未来补录的 ID 不会因上一轮探测为空而漏掉', async () => {
  const dir = tmpDir();
  await initStore({ dataDir: dir, reset: true });
  const db = getDb();
  db.meta.ttzlMaxValidId = 100;
  db.meta.ttzlSeen = {};

  let exists = new Set();
  const fetched = [];
  const fetcher = async (id) => {
    fetched.push(id);
    return exists.has(id) ? makeArticle(id, `案例${id}`, `案例${id}的正文内容。`) : null;
  };

  // 第一轮：101-125 全部不存在
  await collect({ upward: 40, fetcher, sleepMs: 0 });
  assert.equal(db.meta.ttzlMaxValidId, 100, '最大有效 ID 未前进');
  assert.equal(fetched.includes(101), true, '第一轮扫过 101');

  // 第二轮：101 出现了 → 必须抓到
  exists = new Set([101]);
  const r = await collect({ upward: 40, fetcher, sleepMs: 0 });
  assert.equal(r.saved, 1, '抓到新出现的 101');
  assert.equal(db.meta.ttzlMaxValidId, 101, '最大有效 ID 前进到 101');
});

/* 媒体归属：潮新闻·浙江日报 不归到钱江晚报 */
test('v021 媒体归属：显式主体优先，渠道不绑定单一媒体', () => {
  const zj = resolveMedia('潮新闻·浙江日报');
  assert.equal(zj.main, '浙江日报');
  assert.ok(zj.channels.includes('潮新闻'));
  assert.equal(zj.main.includes('钱江'), false);

  const qj = resolveMedia('潮新闻·钱江晚报');
  assert.equal(qj.main, '钱江晚报');

  const bx = resolveMedia('犇视频·三湘都市报');
  assert.equal(bx.main, '三湘都市报');
  assert.ok(bx.channels.includes('犇视频'));

  const cx = resolveMedia('晨视频·潇湘晨报');
  assert.equal(cx.main, '潇湘晨报');

  // 只有渠道单独出现：保留原始名称，不猜主体
  assert.equal(resolveMedia('潮新闻').main, '潮新闻');
});

/* 已保留事件进入报告 + 待分析殿后 */
test('v021 报告：已保留进入报告、已忽略默认排除、待分析排在已分析之后', () => {
  const dir = tmpDir();
  return (async () => {
    await initStore({ dataDir: dir, reset: true });
    await upsertArticle(makeArticle(601, '保留的暖事件甲', '完整正文。'));
    await upsertArticle(makeArticle(602, '已分析的暖事件乙', '完整正文乙。'));
    await upsertArticle(makeArticle(603, '被忽略的暖事件丙', '完整正文丙。'));
    await upsertArticle(makeArticle(604, '还没分析的暖事件丁', '完整正文丁。'));
    rebuildEvents();
    const evs = Object.values(getDb().events);
    for (const ev of evs) {
      if (ev.title.includes('乙')) ev.analysis = { oneLine: '乙', suggestedUse: '短复述或案例', materialValue: '中', infoMaturity: '完整' };
      if (ev.title.includes('丙')) ev.userStatus = 'ignored';
      if (ev.title.includes('甲')) ev.userStatus = 'kept';
    }
    const captured = {};
    const mockRes = { writeHead: () => {}, end: (b) => { captured.body = b; } };
    mountWenwenReport({ method: 'GET' }, mockRes, new URL('http://localhost/wenwen/report'));
    const md = captured.body;
    assert.ok(md.includes('已保留（1）'), '已保留事件进入报告');
    assert.ok(md.includes('保留的暖事件甲'), '已保留标题在报告中');
    assert.ok(!md.includes('被忽略的暖事件丙'), '已忽略默认不进报告');
    const idxAnalyzed = md.indexOf('短复述或案例（');
    const idxPending = md.indexOf('待 AI 分析（');
    assert.ok(idxAnalyzed >= 0 && idxPending > idxAnalyzed, '待分析排在已分析之后');
    assert.ok(md.includes('还没分析的暖事件丁'), '待分析事件在报告中');
  })();
});

/* 同正文不同媒体：来源记录不丢失 */
test('v021 来源记录：同正文不同媒体全部保留', async () => {
  const dir = tmpDir();
  await initStore({ dataDir: dir, reset: true });
  const content = '完全相同的通稿正文，用于验证来源记录保留。';
  const r1 = await upsertArticle(makeArticle(701, '通稿标题', content, '甲日报'));
  const a2 = { ...makeArticle(702, '通稿标题（转载）', content, '乙晚报') };
  const r2 = await upsertArticle(a2);
  assert.equal(r2.duplicateOf, 'ttzl-701');
  assert.equal(r2.appearanceRecorded, true);
  const main = await loadRaw('ttzl-701');
  assert.equal(main.appearances.length, 2, '主记录保留两个来源');
  assert.equal(main.appearances[1].media, '乙晚报', '转载媒体记录在案');
  assert.equal(Object.keys(getDb().articleIndex).length, 1, '不重复建实体');
  assert.equal(getDb().articleIndex['ttzl-701'].sourceCount, 2);
});

/* 超 8000 字正文保存不截断 */
test('v021 本地留档：超过 8000 字的正文不截断', async () => {
  const dir = tmpDir();
  await initStore({ dataDir: dir, reset: true });
  const content = '长'.repeat(12000);
  await upsertArticle(makeArticle(801, '超长正文通讯', content));
  const raw = await loadRaw('ttzl-801');
  assert.equal(raw.content.length, 12000, '保存阶段不截断');
  assert.equal(raw.contentLength, 12000);
});

/* 信源首探公平：全部信源都能轮到首次探测 */
test('v021 探测队列：未探测信源轮流完成首次探测，不被抢占', async () => {
  const dir = tmpDir();
  await initStore({ dataDir: dir, reset: true });
  const db = getDb();
  // 三家无官网线索的实体（探测即刻完成，无网络）
  db.registry = {};
  for (const [i, name] of ['高热媒体', '中热媒体', '冷门媒体'].entries()) {
    db.registry[name] = {
      name, probeStatus: '未探测', articleCount: 100 - i * 40,
      aliases: [], channels: [], registeredAt: new Date().toISOString(),
    };
  }
  const r1 = await probeMedia({ queue: 'first', limit: 2 });
  assert.equal(r1.probed, 2);
  assert.equal(db.registry['高热媒体'].firstProbeDone, true);
  assert.equal(db.registry['中热媒体'].firstProbeDone, true);
  assert.equal(!db.registry['冷门媒体'].firstProbeDone, true, '冷门媒体等待下一轮');

  await probeMedia({ queue: 'first', limit: 2 });
  assert.equal(db.registry['冷门媒体'].firstProbeDone, true, '冷门媒体最终轮到');
  const allDone = Object.values(db.registry).every((s) => s.firstProbeDone);
  assert.equal(allDone, true, '全部信源完成首次探测');
});

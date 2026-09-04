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
import { mountWenwen } from './routes.js';

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

/* 2. 向上增量游标持续前进 */
test('向上增量：连续空 ID 后游标仍前进且不重复抓取', async () => {
  const dir = tmpDir();
  await initStore({ dataDir: dir, reset: true });
  const db = getDb();
  db.meta.ttzlMaxValidId = 100;
  db.meta.ttzlProbeHead = 100;
  db.meta.ttzlSeen = {};

  const fetched = new Set();
  const fetcher = async (id) => {
    fetched.add(id);
    return id === 116 ? makeArticle(116, '山路上的背篓医生', '她背起药箱走了二十年。') : null;
  };
  const r1 = await collect({ upward: 40, fetcher, sleepMs: 0 });
  const probe1 = db.meta.ttzlProbeHead;
  assert.equal(r1.saved, 1);
  assert.equal(db.meta.ttzlMaxValidId, 116);
  assert.ok(probe1 >= 116, '探测头覆盖到有效 ID');
  assert.equal(fetched.has(100), false, '不重复扫描已知区间');

  // 第二轮：从探测头+1 继续（区间全空），游标必须继续前进
  const r2 = await collect({ upward: 40, fetcher, sleepMs: 0 });
  const probe2 = db.meta.ttzlProbeHead;
  assert.ok(probe2 > probe1, `探测头前进 ${probe1} → ${probe2}`);
  assert.equal(r2.saved, 0, '没有新案例时不重复入库');
  for (const id of fetched) assert.ok(id > 100, '只扫描前进方向');
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
  assert.ok(e1.brands.includes('潮新闻'));
  const e2 = resolveMedia('扬子晚报·紫牛新闻');
  assert.equal(e2.main, '扬子晚报');
  assert.equal(e2.brands.includes('紫牛新闻'), true);
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

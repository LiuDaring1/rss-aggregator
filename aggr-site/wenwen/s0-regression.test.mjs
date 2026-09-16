/* S0 专项安全与数据保护回归测试 (node:test)
 * 验证:
 * 1. 损坏的 db.json 不被静默重置为空库
 * 2. collector 预筛分词正确，单字不误判为暖文；rebuildRegistry 正常导入可用
 * 3. AGGR_READONLY 拒绝写操作
 * 4. 空正文不参与 contentHash 合并
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { initStore, getDb, upsertArticle } from './store.js';
import { prefilter } from './collector.js';
import { rebuildRegistry } from './mediaName.js';
import { mountWenwen } from './routes.js';

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'wenwen-s0-'));
}

/* 1. 损坏 db.json 保护 */
test('S0-1: 损坏的 db.json 阻止初始化并抛错，严禁静默覆盖为空库', async () => {
  const dir = tmpDir();
  const dbFile = path.join(dir, 'db.json');
  fs.writeFileSync(dbFile, '{ invalid json content ...');

  await assert.rejects(
    async () => {
      await initStore({ dataDir: dir, reset: true });
    },
    /db\.json 损坏或读取失败/
  );
  // 确认原文件内容未被破坏或覆盖
  assert.equal(fs.readFileSync(dbFile, 'utf8'), '{ invalid json content ...');
});

/* 2. collector 预筛与导入修复 */
test('S0-2: collector 预筛分词严谨，非暖文关键词单字不误判；rebuildRegistry 可正常调用', () => {
  assert.equal(typeof rebuildRegistry, 'function');
  
  // 正常暖词
  assert.equal(prefilter('外卖小哥跳水救人'), '可能是暖文');
  assert.equal(prefilter('独居老人获爱心餐'), '可能是暖文');

  // 以前因为 /[救|援|...]/ 字符集合导致的单字误触发
  // 例如包含 "事" 或 "公" 或 "人" 的普通政务/招标新闻：
  assert.equal(prefilter('某单位人事任免公示通告'), '明显无关');
  assert.equal(prefilter('某市举办科技创新成果展览'), '信息不足');
});

/* 3. 空正文去重隔离 */
test('S0-3: 空正文文章不参与 contentHash 合并，不同文章各自独立记录', async () => {
  const dir = tmpDir();
  await initStore({ dataDir: dir, reset: true });
  
  const a1 = {
    id: 'm-empty-1',
    origin: 'media',
    url: 'https://example.com/1',
    title: '无正文简讯1',
    media: '报纸A',
    content: '',
  };
  const a2 = {
    id: 'm-empty-2',
    origin: 'media',
    url: 'https://example.com/2',
    title: '无正文简讯2',
    media: '报纸B',
    content: '',
  };
  
  const r1 = await upsertArticle(a1);
  const r2 = await upsertArticle(a2);

  assert.equal(r1.isNew, true);
  // a2 虽同样为空正文，但绝不能被误判为 a1 的 duplicate
  assert.equal(r2.duplicateOf, null);
  assert.equal(r2.isNew, true);
});

/* 4. 只读模式拒绝写操作 */
test('S0-4: AGGR_READONLY=on 模式下 POST 写入接口返回 403 阻断', async () => {
  const dir = tmpDir();
  await initStore({ dataDir: dir, reset: true });
  process.env.AGGR_READONLY = 'on';

  let statusCode = null;
  let responseData = null;
  const fakeReq = {
    method: 'POST',
    async *[Symbol.asyncIterator]() {
      yield JSON.stringify({ url: 'https://ttznl.alibabafoundation.com/storyDetails/45330' });
    }
  };
  const fakeRes = {
    writeHead(code, headers) { statusCode = code; },
    end(data) { responseData = JSON.parse(data); }
  };

  await mountWenwen(fakeReq, fakeRes, new URL('http://127.0.0.1:3000/wenwen/api/import'));
  assert.equal(statusCode, 403);
  assert.ok(responseData.error.includes('只读模式'));

  delete process.env.AGGR_READONLY;
});

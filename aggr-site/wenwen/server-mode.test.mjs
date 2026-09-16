import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { isReadOnlyMode, isOfflineMode } from '../config.js';
import { initStore, flushNow, saveRaw } from './store.js';

test('Mode-1: config.js 统一解析 AGGR_READONLY 与 AGGR_MODE 模式', () => {
  const origEnv = { ...process.env };
  try {
    // 默认
    delete process.env.AGGR_READONLY;
    delete process.env.AGGR_OFFLINE;
    delete process.env.AGGR_MODE;
    assert.equal(isReadOnlyMode(), false);
    assert.equal(isOfflineMode(), false);

    // AGGR_READONLY=on / 1 / true
    process.env.AGGR_READONLY = 'on';
    assert.equal(isReadOnlyMode(), true);
    process.env.AGGR_READONLY = '1';
    assert.equal(isReadOnlyMode(), true);
    process.env.AGGR_READONLY = 'true';
    assert.equal(isReadOnlyMode(), true);
    delete process.env.AGGR_READONLY;

    // AGGR_MODE=readonly
    process.env.AGGR_MODE = 'readonly';
    assert.equal(isReadOnlyMode(), true);
    assert.equal(isOfflineMode(), false);

    // AGGR_OFFLINE=on / 1 / true
    process.env.AGGR_OFFLINE = 'on';
    assert.equal(isOfflineMode(), true);
    delete process.env.AGGR_OFFLINE;

    // 复合模式: AGGR_MODE=readonly,offline
    process.env.AGGR_MODE = 'readonly,offline';
    assert.equal(isReadOnlyMode(), true);
    assert.equal(isOfflineMode(), true);
  } finally {
    process.env = origEnv;
  }
});

test('Mode-2: store 在 AGGR_MODE=readonly 下全面生效并拒绝新建目录与落盘', async () => {
  const origEnv = { ...process.env };
  const tmpDir = path.join(os.tmpdir(), `test-mode-ro-${Date.now()}`);
  try {
    delete process.env.AGGR_READONLY;
    process.env.AGGR_MODE = 'readonly'; // 仅设置 AGGR_MODE=readonly

    // 1. 尝试初始化不存在的目录 -> 必须抛错，不准静默新建
    await assert.rejects(
      () => initStore({ dataDir: tmpDir, reset: true }),
      /只读模式下拒绝新建不存在的数据目录/
    );
    assert.equal(fs.existsSync(tmpDir), false);

    // 2. 尝试 saveRaw -> 必须抛错
    await assert.rejects(
      () => saveRaw({ id: 'test-article-1', title: 'test' }),
      /只读模式下拒绝写入文章留档/
    );
  } finally {
    process.env = origEnv;
    if (fs.existsSync(tmpDir)) fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('Mode-3: server.js fetchSource 在离线模式下无未定义变量异常且正常拦截出网', async () => {
  const { fetchSource } = await import('../server.js');
  const origEnv = { ...process.env };
  try {
    process.env.AGGR_OFFLINE = 'on'; // 启用离线
    const fakeSource = {
      id: `synthetic-test-${Date.now()}`,
      url: 'https://127.0.0.1:9999/non-existent-feed.xml'
    };
    // 在空缓存状态下直接调用 fetchSource
    const result = await fetchSource(fakeSource);
    assert.equal(result.ok, false);
    assert.equal(result.items.length, 0);
    assert.match(result.error, /offline: 离线模式已阻断外部网络抓取/);
  } finally {
    process.env = origEnv;
  }
});

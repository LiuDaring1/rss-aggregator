/* 暖文雷达 — 存储层 v0.2（JSON 文件持久化，可注入数据目录便于测试）
 *
 * 数据目录 aggr-site/data/wenwen/（package.sh 已排除）：
 *   raw/<文章id>.json  原始留档（完整清洗正文 + 元数据，供 AI 全文分析与用户阅读）
 *   db.json            索引与状态：事件 / 信源实体 / 文章索引 / 采集元数据 / 用户反馈
 *
 * v0.2 变更：
 *   - initStore 支持注入 dataDir（测试用）
 *   - 文章索引增加 awardDate（中国日期字符串）/ contentHash / 质量标记
 *   - contentHash 精确去重：同正文不同 URL 不重复入库
 *   - 测试数据（标题含"测试"或正文过短）标记 isTestData，不进入事件与候选
 */
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const MODULE_DIR = path.dirname(fileURLToPath(import.meta.url));
export const DEFAULT_DATA_DIR = path.resolve(MODULE_DIR, '../data/wenwen');

let DATA_DIR = DEFAULT_DATA_DIR;
const RAW_DIR = () => path.join(DATA_DIR, 'raw');
const DB_FILE = () => path.join(DATA_DIR, 'db.json');

export function hashId(text) {
  return crypto.createHash('sha1').update(String(text)).digest('hex').slice(0, 16);
}

export function contentHashOf(text) {
  return crypto.createHash('sha1').update(String(text || '').replace(/\s+/g, '')).digest('hex').slice(0, 20);
}

let db = null;
let flushTimer = null;

export async function initStore({ dataDir, reset = false } = {}) {
  if (dataDir) DATA_DIR = dataDir;
  fs.mkdirSync(RAW_DIR(), { recursive: true });
  if (db && !reset) return db;
  if (reset) db = null;
  try {
    db = JSON.parse(await fsp.readFile(DB_FILE(), 'utf8'));
  } catch {
    db = {};
  }
  db.events ||= {};
  db.registry ||= {};
  db.articleIndex ||= {};
  db.meta ||= {};
  db.dedupe ||= { contentHashes: {}, dedupHits: 0 };
  return db;
}

export function getDb() {
  if (!db) throw new Error('store 未初始化，请先 initStore()');
  return db;
}

export function dataDir() {
  return DATA_DIR;
}

/** 防抖落盘（原子写：tmp + rename，进程中断不会损坏旧文件） */
export function scheduleFlush(delayMs = 2000) {
  if (flushTimer) return;
  flushTimer = setTimeout(() => flushNow(), delayMs);
}

export async function flushNow() {
  if (!db) return;
  if (flushTimer) { clearTimeout(flushTimer); flushTimer = null; }
  try {
    const tmp = DB_FILE() + '.tmp';
    await fsp.writeFile(tmp, JSON.stringify(db));
    await fsp.rename(tmp, DB_FILE());
    db.meta.lastWriteAt = new Date().toISOString();
  } catch (e) {
    console.error('[wenwen] db.json 写入失败:', e.message);
  }
}

/** 原始文章留档 */
export async function saveRaw(article) {
  const file = path.join(RAW_DIR(), article.id + '.json');
  const tmp = file + '.tmp';
  await fsp.writeFile(tmp, JSON.stringify(article, null, 1));
  await fsp.rename(tmp, file);
}

export async function loadRaw(id) {
  try {
    return JSON.parse(await fsp.readFile(path.join(RAW_DIR(), id + '.json'), 'utf8'));
  } catch {
    return null;
  }
}

export async function listRawIds() {
  fs.mkdirSync(RAW_DIR(), { recursive: true });
  return (await fsp.readdir(RAW_DIR())).filter((f) => f.endsWith('.json')).map((f) => f.replace('.json', ''));
}

/* ---------------- 文章入库（索引 + 留档 + 去重 + 质量标记 + 信源抽取） ---------------- */

/** 数据质量与测试数据标记（不补写事实，只标记） */
export function qualityFlags(article) {
  const flags = [];
  if (/测试/.test(article.title || '')) flags.push('疑似测试数据');
  if (!article.title || String(article.title).length < 6) flags.push('标题可能不完整');
  if (!article.content || article.content.length < 30) flags.push('正文异常过短');
  if (/�/.test((article.title || '') + (article.content || ''))) flags.push('编码异常');
  if (!article.media) flags.push('缺媒体');
  if (!article.publishedAt) flags.push('缺日期');
  return flags;
}

/**
 * 文章入库。返回 { isNew, duplicateOf }。
 * - 同一 contentHash 的文章视为精确重复，不重复入库（记录来源留档由调用方决定）。
 * - 测试数据/低质量文章正常入库，但带 flags，事件与候选阶段会排除。
 */
export async function upsertArticle(article) {
  const d = getDb();
  article.contentHash = contentHashOf(article.content);
  article.flags = qualityFlags(article);
  article.isTestData = article.flags.includes('疑似测试数据') || article.flags.includes('正文异常过短') && !article.media && !article.publishedAt;

  const dupOf = d.dedupe.contentHashes[article.contentHash];
  if (dupOf && dupOf !== article.id) {
    d.dedupe.dedupHits = (d.dedupe.dedupHits || 0) + 1;
    return { isNew: false, duplicateOf: dupOf };
  }
  d.dedupe.contentHashes[article.contentHash] = article.id;

  const isNew = !d.articleIndex[article.id];
  d.articleIndex[article.id] = {
    title: article.title,
    media: article.media || '',
    awardDate: article.awardDate || null,          // 天天正能量公示/获奖日期（中国日期字符串）
    publishedAt: article.awardDate || null,        // 兼容旧字段：排序用
    sourcePublishedAt: article.sourcePublishedAt || null, // 原始媒体文章发布时间（溯源后填）
    url: article.url,
    category: article.category || '',
    origin: article.origin || '',
    contentLength: (article.content || '').length,
    contentHash: article.contentHash,
    flags: article.flags,
    isTestData: article.isTestData,
  };
  await saveRaw(article);

  for (const name of new Set([article.media, article.source].filter(Boolean))) {
    upsertRegistrySource(name, { origin: 'ttzl-case' }, { bump: isNew });
  }
  scheduleFlush();
  return { isNew, duplicateOf: null };
}

/* ---------------- 信源实体（媒体规范化后） ---------------- */

export function upsertRegistrySource(name, patch = {}, { bump = false } = {}) {
  const d = getDb();
  const key = String(name).trim();
  if (!key) return null;
  const now = new Date().toISOString();
  const cur = d.registry[key] || {
    name: key,
    origin: null,
    homepage: null,
    probeStatus: '未探测',
    fetchMethod: null,
    registeredAt: now,
    firstArticleAt: null,
    articleCount: 0,
    lastSuccessAt: null,
    lastProbeAt: null,
    lastError: null,
  };
  if (bump) {
    cur.articleCount = (cur.articleCount || 0) + 1;
    cur.firstArticleAt ||= now;
    cur.lastSuccessAt = now;
  }
  Object.assign(cur, patch, { name: key });
  d.registry[key] = cur;
  return cur;
}

/* ---------------- 事件（同事件合并后的候选） ---------------- */

export function upsertEvent(event) {
  const d = getDb();
  d.events[event.id] = event;
  scheduleFlush();
  return event;
}

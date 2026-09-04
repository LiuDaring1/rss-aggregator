/* 暖文雷达 — 存储层（JSON 文件持久化，服从现有项目零数据库风格）
 *
 * 数据目录 aggr-site/data/wenwen/（package.sh 已排除 data/）：
 *   raw/<文章id>.json  原始留档（正文等，供后续重分析，不必再访问原网页）
 *   db.json            索引与状态：事件 / 信源注册表 / 采集元数据 / 用户反馈
 */
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const MODULE_DIR = path.dirname(fileURLToPath(import.meta.url));
export const DATA_DIR = path.resolve(MODULE_DIR, '../data/wenwen');
const RAW_DIR = path.join(DATA_DIR, 'raw');
const DB_FILE = path.join(DATA_DIR, 'db.json');

export function hashId(text) {
  return crypto.createHash('sha1').update(String(text)).digest('hex').slice(0, 16);
}

let db = null;
let flushTimer = null;

export async function initStore() {
  fs.mkdirSync(RAW_DIR, { recursive: true });
  if (db) return db;
  try {
    db = JSON.parse(await fsp.readFile(DB_FILE, 'utf8'));
  } catch {
    db = {};
  }
  db.events ||= {};      // 事件候选：evId -> event
  db.registry ||= {};    // 信源注册表：名称 -> source
  db.articleIndex ||= {}; // 文章索引：articleId -> {title, media, publishedAt, url, category, origin}
  db.meta ||= {};        // 采集元数据：ttzlMaxStoryId / ttzlSeen / lastCollectAt ...
  return db;
}

export function getDb() {
  if (!db) throw new Error('store 未初始化，请先 initStore()');
  return db;
}

/** 防抖落盘（原子写：tmp + rename） */
export function scheduleFlush(delayMs = 2000) {
  if (flushTimer) return;
  flushTimer = setTimeout(async () => {
    flushTimer = null;
    try {
      const tmp = DB_FILE + '.tmp';
      await fsp.writeFile(tmp, JSON.stringify(db));
      await fsp.rename(tmp, DB_FILE);
    } catch (e) {
      console.error('[wenwen] db.json 写入失败:', e.message);
    }
  }, delayMs);
}

export async function flushNow() {
  if (!db) return;
  if (flushTimer) { clearTimeout(flushTimer); flushTimer = null; }
  try {
    const tmp = DB_FILE + '.tmp';
    await fsp.writeFile(tmp, JSON.stringify(db));
    await fsp.rename(tmp, DB_FILE);
  } catch (e) {
    console.error('[wenwen] db.json 写入失败:', e.message);
  }
}

/** 原始文章留档 */
export async function saveRaw(article) {
  const file = path.join(RAW_DIR, article.id + '.json');
  const tmp = file + '.tmp';
  await fsp.writeFile(tmp, JSON.stringify(article, null, 1));
  await fsp.rename(tmp, file);
}

export async function loadRaw(id) {
  try {
    return JSON.parse(await fsp.readFile(path.join(RAW_DIR, id + '.json'), 'utf8'));
  } catch {
    return null;
  }
}

/* ---------------- 文章入库（索引 + 留档 + 信源抽取） ---------------- */

export async function upsertArticle(article) {
  const d = getDb();
  const isNew = !d.articleIndex[article.id];
  d.articleIndex[article.id] = {
    title: article.title,
    media: article.media || '',
    publishedAt: article.publishedAt || null,
    url: article.url,
    category: article.category || '',
    origin: article.origin || '',
  };
  await saveRaw(article);
  // 信源注册表：从案例中出现的媒体名自动抽取（阶段二的种子）
  for (const name of new Set([article.media, article.source].filter(Boolean))) {
    upsertRegistrySource(name, { origin: 'ttzl-case' }, { bump: isNew });
  }
  scheduleFlush();
  return isNew;
}

export function upsertRegistrySource(name, patch = {}, { bump = false } = {}) {
  const d = getDb();
  const key = String(name).trim();
  if (!key) return null;
  const now = new Date().toISOString();
  const cur = d.registry[key] || {
    name: key,
    aliases: [],
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

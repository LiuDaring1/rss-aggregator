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
import { isReadOnlyMode } from '../config.js';

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
  const targetDir = dataDir ? path.resolve(dataDir) : DATA_DIR;
  if (db && !reset && targetDir === DATA_DIR) {
    return db;
  }
  const targetRawDir = path.join(targetDir, 'raw');
  const targetDbFile = path.join(targetDir, 'db.json');

  const isReadOnly = isReadOnlyMode();
  if (isReadOnly && !fs.existsSync(targetDir)) {
    throw new Error(`[wenwen] 只读模式下拒绝新建不存在的数据目录: ${targetDir}`);
  }

  let loadedDb = null;
  try {
    const raw = await fsp.readFile(targetDbFile, 'utf8');
    loadedDb = JSON.parse(raw);
  } catch (err) {
    if (err.code === 'ENOENT') {
      if (isReadOnly) {
        throw new Error(`[wenwen] 只读模式下 db.json 不存在: ${targetDbFile}`);
      }
      loadedDb = {};
    } else {
      throw new Error(`[wenwen] db.json 损坏或读取失败，已阻断初始化以防空库覆盖: ${err.message}`);
    }
  }

  // 只有校验成功才原子切换当前目录与内存状态，杜绝"旧db+新目录"
  if (flushTimer) {
    clearTimeout(flushTimer);
    flushTimer = null;
  }
  DATA_DIR = targetDir;
  db = loadedDb;

  if (!isReadOnly) {
    fs.mkdirSync(RAW_DIR(), { recursive: true });
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
  const isReadOnly = isReadOnlyMode();
  if (isReadOnly) return;
  if (flushTimer) return;
  flushTimer = setTimeout(() => flushNow(), delayMs);
}

export async function flushNow() {
  if (!db) return;
  const isReadOnly = isReadOnlyMode();
  if (isReadOnly) {
    console.warn('[wenwen] 只读模式生效中，阻断 flushNow 写入');
    return;
  }
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
  const isReadOnly = isReadOnlyMode();
  if (isReadOnly) {
    throw new Error(`[wenwen] 只读模式下拒绝写入文章留档: ${article.id}`);
  }
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
  if (!fs.existsSync(RAW_DIR())) return [];
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
 * 文章入库。返回 { isNew, duplicateOf, appearanceRecorded }。
 * - 同一 contentHash 的文章视为"同一篇内容的多次出现"：不重复建实体、
 *   不重复跑 AI，但来源记录（媒体/URL/时间）追加到主记录的 appearances，
 *   多信源阶段同一通稿的各家转载不会丢失。
 * - 测试数据/低质量文章正常入库，但带 flags，事件与候选阶段会排除。
 */
export async function upsertArticle(article) {
  const d = getDb();
  article.contentHash = contentHashOf(article.content);
  article.flags = qualityFlags(article);
  article.isTestData = article.flags.includes('疑似测试数据') || article.flags.includes('正文异常过短') && !article.media && !article.publishedAt;

  const now = new Date().toISOString();
  const selfAppearance = {
    media: article.media || '',
    rawMedia: article.source || article.media || '',
    url: article.url,
    title: article.title,
    awardDate: article.awardDate || null,
    fetchedAt: article.fetchedAt || now,
    identicalContent: true,
    suspectedRepost: false,
    sourceType: article.origin || '',
  };

  const hasSubstantialContent = Boolean((article.content || '').trim());
  const dupOf = hasSubstantialContent ? d.dedupe.contentHashes[article.contentHash] : null;
  if (dupOf && dupOf !== article.id) {
    // 同正文不同来源：追加来源记录，保留每家媒体与 URL，不重复分析
    const main = await loadRaw(dupOf);
    if (main) {
      main.appearances ||= [];
      if (!main.appearances.some((ap) => ap.url === article.url)) {
        main.appearances.push({
          ...selfAppearance,
          mainId: dupOf,
          identicalContent: true,
          suspectedRepost: true,
        });
        await saveRaw(main);
        if (db.articleIndex[dupOf]) db.articleIndex[dupOf].sourceCount = main.appearances.length;
      }
    }
    d.dedupe.dedupHits = (d.dedupe.dedupHits || 0) + 1;
    return { isNew: false, duplicateOf: dupOf, appearanceRecorded: true };
  }

  // 若文章正文哈希变动，清理旧哈希记录
  const existingIndex = d.articleIndex[article.id];
  if (existingIndex && existingIndex.contentHash && existingIndex.contentHash !== article.contentHash) {
    if (d.dedupe.contentHashes[existingIndex.contentHash] === article.id) {
      delete d.dedupe.contentHashes[existingIndex.contentHash];
    }
  }

  if (hasSubstantialContent) {
    d.dedupe.contentHashes[article.contentHash] = article.id;
  }

  // 重抓/更新时保留既有 appearances 来源记录，不重置为单条
  const existingRaw = await loadRaw(article.id);
  if (existingRaw && Array.isArray(existingRaw.appearances) && existingRaw.appearances.length > 0) {
    const existingUrls = new Set(existingRaw.appearances.map((ap) => ap.url));
    article.appearances = existingRaw.appearances;
    if (!existingUrls.has(selfAppearance.url)) {
      article.appearances.push(selfAppearance);
    }
  } else {
    article.appearances = [selfAppearance];
  }

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
    sourceCount: article.appearances.length,
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

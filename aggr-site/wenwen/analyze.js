/* 暖文雷达 — AI 候选分析 v0.2.1
 *
 * v0.2.1 变更：
 * - 分类表全部来自 taxonomies.js（事件母题与社会议题分开，集中维护）；
 * - missingFacts 增加 importance（critical/optional）：只有 critical 缺口把
 *   信息成熟度压到"待补充"，可选补充不再拉低成熟度；
 * - 每条分析记录版本化（规则/提示词/分类表版本 + 事件指纹 + 模型 + 时间），
 *   支持「按版本重分析」，不自动清空旧分析；
 * - 建议用途仍由代码组合（computeSuggestedUse）。
 */
import { getDb, loadRaw, scheduleFlush, hashId } from './store.js';
import {
  EVENT_MOTIFS, SOCIAL_TOPICS, BEHAVIOR_CATEGORIES, MATERIAL_VALUES, INFO_MATURITIES,
  USES, USE_PRIORITY, GAP_IMPORTANCE, computeSuggestedUse,
  ANALYSIS_RULES_VERSION, PROMPT_VERSION, TAXONOMY_VERSION,
} from './taxonomies.js';

export {
  BEHAVIOR_CATEGORIES, SOCIAL_TOPICS, EVENT_MOTIFS, MATERIAL_VALUES, INFO_MATURITIES, USES, USE_PRIORITY,
};

async function loadAiConfig() {
  if (process.env.GLM_API_KEY) {
    return {
      apiKey: process.env.GLM_API_KEY,
      baseUrl: process.env.GLM_BASE_URL || 'https://open.bigmodel.cn/api/paas/v4',
      model: process.env.GLM_MODEL || 'glm-5.3-flash',
    };
  }
  try {
    const { readFile } = await import('node:fs/promises');
    const path = await import('node:path');
    const { fileURLToPath } = await import('node:url');
    const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
    const cfg = JSON.parse(await readFile(path.join(root, 'ai.json'), 'utf8'));
    return {
      apiKey: cfg.apiKey,
      baseUrl: cfg.baseUrl || 'https://open.bigmodel.cn/api/paas/v4',
      model: cfg.model || 'glm-5.3-flash',
    };
  } catch {
    return null;
  }
}

function extractJson(text) {
  const s = text.indexOf('{');
  const e = text.lastIndexOf('}');
  if (s < 0 || e <= s) throw new Error('AI 返回内容中没有 JSON');
  return JSON.parse(text.slice(s, e + 1));
}

async function callGlm(cfg, prompt) {
  const res = await fetch(cfg.baseUrl.replace(/\/$/, '') + '/chat/completions', {
    method: 'POST',
    signal: AbortSignal.timeout(300000),
    headers: { Authorization: `Bearer ${cfg.apiKey}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: cfg.model,
      messages: [
        {
          role: 'system',
          content:
            '你是播音主持即兴口语训练素材的资深编辑，只输出 JSON，不要输出任何解释。判断必须严格基于给出的报道原文，不要虚构文中没有的细节。',
        },
        { role: 'user', content: prompt },
      ],
      max_tokens: 12000,
      temperature: 0.2,
      thinking: { type: 'enabled', reasoning_effort: 'low' },
      response_format: { type: 'json_object' },
    }),
  });
  if (!res.ok) throw new Error(`GLM HTTP ${res.status}: ${(await res.text()).slice(0, 150)}`);
  const data = await res.json();
  return data.choices?.[0]?.message?.content || '';
}

const PROMPT = (blocks) => `下面是一个"暖事件"候选的一到三篇媒体报道（标题+正文，尽量完整）。请评估它作为播音主持艺考"即兴评述"训练材料的价值。

${blocks}

判断要求（务必客观，大多数同类事件属于"中"或"低"价值，"高"价值必须说明明确的独特增量）：
- 材料价值 materialValue：高=人物、细节、关系或社会议题有明显增量；中=事实清楚但讨论面有限；低=高度同质（如常见跳水救人/拾金不昧母题且无新内容）、常规宣传稿、缺乏具体故事。
- 信息成熟度 infoMaturity：完整=人物+处境+行为+细节+结果基本齐全；待补充=有价值但缺关键结果/原话/后续；线索=只有少量信息不能直接使用。
- discussionTags 只在事件与该主题确实相关时选择（如技术真正参与解决问题才选"科技向善"），可以为空数组。
- 不虚构：所有字段只能来自报道原文；缺什么就在 missingFacts 里列明。

只输出 JSON：
{
 "oneLine": "一句话说清事件（30字内，含人物和核心行为）",
 "people": "主要人物或群体，含职业/身份（20字内）",
 "action": "具体做了什么（40字内）",
 "difficulty": "处境、困难、选择或付出的成本（30字内，确实没有则写'不明显'）",
 "detail": "最有记忆点的一个细节（25字内）",
 "result": "事件结果（30字内，报道未交代则写'报道未提及'）",
 "behaviorCategory": "英勇救人/助人为乐/诚实守信/敬业奉献/自立自强/孝老爱亲/温情互助/其他 中选1个",
 "eventMotif": "事件母题（描述发生了什么类型的事件），从 水域救援/火灾与险情救援/道路交通救援/医疗急救/高空坠落或建筑险情救援/应急救灾/长期助学与陪伴/困境成长/技能助人/适老服务/助残与无障碍/公益空间/爱心餐食/邻里长期守望/职业岗位善意/诚信与归还/其他 中选1个",
 "discussionTags": "社会讨论主题数组，从 职业教育/青年成长/儿童监护/适老服务/公共服务/无障碍/职业责任/社区互助/规则与温度/陌生人信任/城乡关系/公益可持续/科技向善 中选0到3个，确实不相关就给空数组[]",
 "discussionAngles": ["1到4个具体的讨论角度，每个一句话，写清可以怎么展开（不要只写标签词）"],
 "distinctiveWhy": "与普通同类好人好事相比，这件事特别在哪里（一两句话；确实普通就写'属于常见母题，无特别增量'）",
 "completeness": "1到5整数：故事完整度",
 "uniqueness": "1到5整数：独特性（同母题普通事件给1-2分）",
 "expandability": "1到5整数：除赞美之外的讨论空间",
 "materialValue": "高/中/低",
 "infoMaturity": "完整/待补充/线索",
 "needMoreSearch": "布尔值",
 "missingFacts": [{"missing":"缺什么","why":"为什么影响使用","search":"应该补充搜索什么","importance":"critical（不补充就不能可靠使用）或 optional（补充后更丰富）"}],
 "reason": "判断理由（60字内，具体指出依据，不套话）"
}`;

/** 组装分析输入：主报道完整正文 + 补充报道，总输入可配置（默认 2 万字） */
export async function buildEventBlocks(ev, totalLimit) {
  const db = getDb();
  const withRaw = [];
  for (const aid of ev.articleIds.slice(0, 6)) {
    const raw = await loadRaw(aid);
    if (raw) withRaw.push(raw);
  }
  withRaw.sort((a, b) => (b.contentLength || 0) - (a.contentLength || 0));
  if (!withRaw.length) {
    const idx = ev.articleIds.map((aid) => db.articleIndex[aid]).filter(Boolean);
    return idx.map((a, i) => `【报道${i + 1}】媒体：${a.media} 日期：${(a.awardDate || a.publishedAt || '').slice(0, 10)}\n标题：${a.title}\n（正文未留档）`).join('\n\n');
  }
  let budget = totalLimit;
  const blocks = [];
  const mains = withRaw.slice(0, 3);
  mains.forEach((raw, i) => {
    // 主报道（第一篇=最长）给大预算；其余均分剩余预算
    const remaining = mains.length - i - 1;
    const share = i === 0
      ? Math.min(8000, budget)
      : Math.max(500, Math.floor(budget / Math.max(1, remaining + 1)));
    const body = String(raw.content || '').slice(0, Math.max(500, Math.min(share, budget)));
    budget -= body.length;
    const date = raw.awardDate || raw.publishedAt || '';
    blocks.push(`【报道${i + 1}${i === 0 ? '·主' : '·补充'}】媒体：${raw.media || '未知'} 日期：${date}\n标题：${raw.title}\n正文：${body}`);
  });
  return blocks.join('\n\n');
}

export async function analyzeEvent(ev, cfg, totalLimit = 20000) {
  const blocks = await buildEventBlocks(ev, totalLimit);
  const text = await callGlm(cfg, PROMPT(blocks));
  const out = extractJson(text);
  const clamp = (v) => Math.min(5, Math.max(1, Number(v) || 1));

  const materialValue = MATERIAL_VALUES.includes(out.materialValue) ? out.materialValue : '中';
  const infoMaturityRaw = INFO_MATURITIES.includes(out.infoMaturity) ? out.infoMaturity : '待补充';
  const tags = Array.isArray(out.discussionTags)
    ? out.discussionTags.filter((t) => SOCIAL_TOPICS.includes(t)).slice(0, 3)
    : [];
  const missingFacts = (Array.isArray(out.missingFacts) ? out.missingFacts : [])
    .slice(0, 5)
    .map((m) => ({
      missing: String(m?.missing || '').slice(0, 60),
      why: String(m?.why || '').slice(0, 80),
      search: String(m?.search || '').slice(0, 80),
      importance: m?.importance === 'critical' ? 'critical' : 'optional',
    }))
    .filter((m) => m.missing);
  // 只有 critical 缺口才把信息成熟度压到"待补充"（可选补充不影响成熟度）
  const hasCriticalGap = missingFacts.some((m) => m.importance === 'critical');
  const infoMaturity = infoMaturityRaw === '完整' && hasCriticalGap ? '待补充' : infoMaturityRaw;

  ev.analysis = {
    oneLine: String(out.oneLine || '').slice(0, 60),
    people: String(out.people || '').slice(0, 40),
    action: String(out.action || '').slice(0, 60),
    difficulty: String(out.difficulty || '').slice(0, 50),
    detail: String(out.detail || '').slice(0, 50),
    result: String(out.result || '').slice(0, 50),
    behaviorCategory: BEHAVIOR_CATEGORIES.includes(out.behaviorCategory) ? out.behaviorCategory : '其他',
    eventMotif: EVENT_MOTIFS.includes(out.eventMotif) ? out.eventMotif : '其他',
    discussionTags: tags,
    discussionAngles: (Array.isArray(out.discussionAngles) ? out.discussionAngles : [])
      .map((s) => String(s).slice(0, 80))
      .filter(Boolean)
      .slice(0, 4),
    distinctiveWhy: String(out.distinctiveWhy || '').slice(0, 120),
    completeness: clamp(out.completeness),
    uniqueness: clamp(out.uniqueness),
    expandability: clamp(out.expandability),
    materialValue,
    infoMaturity,
    suggestedUse: computeSuggestedUse(materialValue, infoMaturity, hasCriticalGap),
    needMoreSearch: !!out.needMoreSearch || hasCriticalGap,
    missingFacts,
    reason: String(out.reason || '').slice(0, 150),
    model: cfg.model,
    version: {
      rules: ANALYSIS_RULES_VERSION,
      prompt: PROMPT_VERSION,
      taxonomy: TAXONOMY_VERSION,
      fingerprint: ev.fingerprint || null,
      analyzedAt: new Date().toISOString(),
    },
  };
  ev.analysisAt = new Date().toISOString();
  ev.analysisArticleCount = ev.articleIds.length;
  scheduleFlush();
  return ev.analysis;
}

/** 待分析事件：未分析过，或指纹变化后文章数不同；已忽略的跳过 */
export function pickPendingEvents(limit = 6) {
  const db = getDb();
  return Object.values(db.events)
    .filter((ev) => ev.userStatus !== 'ignored')
    .filter((ev) => !ev.analysis || ev.analysisArticleCount !== ev.articleIds.length)
    .sort((a, b) => String(b.lastAt || '').localeCompare(String(a.lastAt || '')))
    .slice(0, limit);
}

/** 筛选结果自检：分布明显塌缩时提示（写日志 + meta 标记）
 * 塌缩判定：材料价值 / 建议用途 / 高独特性任一超过 80% 集中，
 * 或事件母题大量（>60%）落入"其他"。
 */
export function checkDistribution() {
  const db = getDb();
  const analyzed = Object.values(db.events).filter((e) => e.analysis);
  const n = analyzed.length;
  if (n < 8) return null;
  const dist = {};
  for (const k of ['materialValue', 'infoMaturity', 'suggestedUse', 'eventMotif']) {
    dist[k] = {};
    for (const ev of analyzed) {
      const v = ev.analysis[k] || '未知';
      dist[k][v] = (dist[k][v] || 0) + 1;
    }
  }
  const top = (obj) => Math.max(...Object.values(obj));
  const warnings = [];
  if (top(dist.materialValue) / n > 0.8) warnings.push(`材料价值 ${n > 0 ? '' : ''}超过 80% 集中于同一档`);
  if (top(dist.suggestedUse) / n > 0.8) warnings.push('建议用途超过 80% 落入同一类');
  const uniHigh = analyzed.filter((e) => e.analysis.uniqueness >= 4).length;
  if (uniHigh / n > 0.8) warnings.push('独特性分数过度集中（≥4 占比超 80%）');
  const motifOther = dist.eventMotif['其他'] || 0;
  if (motifOther / n > 0.6) warnings.push(`事件母题大量落入"其他"（${motifOther}/${n}）`);
  const result = {
    analyzedCount: n,
    distribution: dist,
    collapsed: warnings.length > 0,
    warning: warnings.join('；') || null,
    checkedAt: new Date().toISOString(),
  };
  db.meta.filterCheck = result;
  if (warnings.length) console.warn('[wenwen] ⚠️', result.warning);
  return result;
}

export async function analyzePending({ limit = 6, totalLimit } = {}) {
  const cfg = await loadAiConfig();
  if (!cfg || !cfg.apiKey) throw new Error('未配置 AI（aggr-site/ai.json 或环境变量 GLM_API_KEY）');
  const db = getDb();
  const tl = totalLimit || Number(process.env.AI_TOTAL_INPUT || 20000);
  const pending = pickPendingEvents(limit);
  let analyzed = 0;
  const failed = [];
  for (const ev of pending) {
    try {
      await analyzeEvent(ev, cfg, tl);
      analyzed++;
    } catch (e) {
      failed.push({ id: ev.id, error: e.message });
    }
  }
  const distribution = checkDistribution();
  db.meta.lastAnalyzeAt = new Date().toISOString();
  scheduleFlush();
  return { analyzed, failed, pendingCount: pickPendingEvents(9999).length, distribution };
}

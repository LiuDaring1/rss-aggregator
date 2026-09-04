/* 暖文雷达 — AI 候选分析（GLM）
 *
 * 原则（任务书六.3）：模型负责理解（人物/行为/细节/讨论方向/可扩展性），
 * 代码负责稳定规则（排序、来源统计、状态）；每个事件的分析结果缓存，
 * 文章数变化后才重新分析。模型只基于已有报道判断，不做事实脑补；
 * 事实不完整时输出 needMoreSearch=true 并建议"继续观察"。
 */
import { getDb, loadRaw, scheduleFlush } from './store.js';

export const BEHAVIOR_CATEGORIES = [
  '英勇救人', '助人为乐', '诚实守信', '敬业奉献', '自立自强', '孝老爱亲', '温情互助', '其他',
];
export const DISCUSSION_TAGS = [
  '职业教育', '青年成长', '老龄化与适老服务', '技能价值', '规则与温度', '公共服务',
  '陌生人信任', '职业责任', '科技向善', '城乡关系', '社区互助',
];
export const USES = ['完整加工', '短复述', '继续观察', '暂时不用'];

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
    const root = path.dirname(path.dirname(fileURLToPath(import.meta.url))); // aggr-site/
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
    signal: AbortSignal.timeout(180000),
    headers: { Authorization: `Bearer ${cfg.apiKey}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: cfg.model,
      messages: [
        {
          role: 'system',
          content:
            '你是播音主持即兴口语训练素材的资深编辑，只输出 JSON，不要输出任何解释。判断必须基于给出的报道原文，不要虚构文中没有的细节。',
        },
        { role: 'user', content: prompt },
      ],
      max_tokens: 8000,
      temperature: 0.2,
      thinking: { type: 'enabled', reasoning_effort: 'low' },
      response_format: { type: 'json_object' },
    }),
  });
  if (!res.ok) throw new Error(`GLM HTTP ${res.status}: ${(await res.text()).slice(0, 150)}`);
  const data = await res.json();
  return data.choices?.[0]?.message?.content || '';
}

const PROMPT = (blocks) => `下面是一个"暖事件"候选的一到三篇媒体报道（标题+正文节选）。请评估它作为播音主持艺考"即兴评述"训练材料的价值。

${blocks}

只输出 JSON：
{
 "oneLine": "一句话说清事件（30字内，含人物和核心行为）",
 "people": "主要人物或群体，含职业/身份（20字内；报道未提具体姓名则写群体描述）",
 "action": "具体做了什么（40字内）",
 "difficulty": "当时的处境、困难、选择或付出的成本（30字内，确实没有则写'不明显'）",
 "detail": "最有记忆点的一个细节：动作/物品/一句话/多年坚持（25字内）",
 "result": "事件结果（30字内，报道未交代结果则写'报道未提及'）",
 "behaviorCategory": "从这些里选1个：英勇救人/助人为乐/诚实守信/敬业奉献/自立自强/孝老爱亲/温情互助/其他",
 "discussionTags": "从这些里选0到3个：职业教育/青年成长/老龄化与适老服务/技能价值/规则与温度/公共服务/陌生人信任/职业责任/科技向善/城乡关系/社区互助",
 "completeness": "1到5的整数：故事完整度（人物+处境+行为+细节+结果是否齐全）",
 "uniqueness": "1到5的整数：独特性（区别于常见的跳水救人、拾金不昧、扶老人等同质母题的程度）",
 "expandability": "1到5的整数：可扩展性（除了赞美之外，能联系讨论标签展开的空间）",
 "needMoreSearch": "布尔值：事实是否明显不完整、值得补充搜索（如缺结果、缺当事人回应）",
 "suggestedUse": "从这些里选1个：完整加工/短复述/继续观察/暂时不用",
 "reason": "判断理由（60字内，具体指出依据，如缺什么信息、有什么独特角度；不要套话）"
}
判断标尺：完整加工=细节丰富且独特且有讨论空间；短复述=事实清楚但同质化高或讨论面窄；继续观察=只有线索或事实明显残缺；暂时不用=通稿式宣传、事实模糊、与口语训练无关。`;

/** 组装一个事件的分析输入（最多取 3 篇内容最长报道的节选） */
async function buildEventBlocks(ev) {
  const db = getDb();
  const withRaw = [];
  for (const aid of ev.articleIds.slice(0, 6)) {
    const raw = await loadRaw(aid);
    if (raw) withRaw.push(raw);
  }
  withRaw.sort((a, b) => (b.contentLength || 0) - (a.contentLength || 0));
  const blocks = withRaw.slice(0, 3).map((raw, i) => {
    const date = (raw.publishedAt || '').slice(0, 10);
    const body = String(raw.content || '').slice(0, 700);
    return `【报道${i + 1}】媒体：${raw.media || '未知'} 日期：${date}\n标题：${raw.title}\n正文节选：${body}`;
  });
  if (!blocks.length) {
    const idx = ev.articleIds.map((aid) => db.articleIndex[aid]).filter(Boolean);
    return idx.map((a, i) => `【报道${i + 1}】媒体：${a.media} 日期：${(a.publishedAt || '').slice(0, 10)}\n标题：${a.title}\n（正文未留档）`).join('\n\n');
  }
  return blocks.join('\n\n');
}

export async function analyzeEvent(ev, cfg) {
  const blocks = await buildEventBlocks(ev);
  const text = await callGlm(cfg, PROMPT(blocks));
  const out = extractJson(text);
  const clamp = (v) => Math.min(5, Math.max(1, Number(v) || 1));
  ev.analysis = {
    oneLine: String(out.oneLine || '').slice(0, 60),
    people: String(out.people || '').slice(0, 40),
    action: String(out.action || '').slice(0, 60),
    difficulty: String(out.difficulty || '').slice(0, 50),
    detail: String(out.detail || '').slice(0, 50),
    result: String(out.result || '').slice(0, 50),
    behaviorCategory: BEHAVIOR_CATEGORIES.includes(out.behaviorCategory) ? out.behaviorCategory : '其他',
    discussionTags: Array.isArray(out.discussionTags)
      ? out.discussionTags.filter((t) => DISCUSSION_TAGS.includes(t)).slice(0, 3)
      : String(out.discussionTags || '').split(/[、,，\s]+/).filter((t) => DISCUSSION_TAGS.includes(t)).slice(0, 3),
    completeness: clamp(out.completeness),
    uniqueness: clamp(out.uniqueness),
    expandability: clamp(out.expandability),
    needMoreSearch: !!out.needMoreSearch,
    suggestedUse: USES.includes(out.suggestedUse) ? out.suggestedUse : '继续观察',
    reason: String(out.reason || '').slice(0, 120),
    model: cfg.model,
  };
  ev.analysisAt = new Date().toISOString();
  ev.analysisArticleCount = ev.articleIds.length;
  scheduleFlush();
  return ev.analysis;
}

/** 待分析事件：未分析过，或合并后文章数变了；已忽略的事件不再分析（省 token） */
export function pickPendingEvents(limit = 6) {
  const db = getDb();
  return Object.values(db.events)
    .filter((ev) => ev.userStatus !== 'ignored')
    .filter((ev) => !ev.analysis || ev.analysisArticleCount !== ev.articleIds.length)
    .sort((a, b) => String(b.lastAt || '').localeCompare(String(a.lastAt || '')))
    .slice(0, limit);
}

export async function analyzePending({ limit = 6 } = {}) {
  const cfg = await loadAiConfig();
  if (!cfg || !cfg.apiKey) throw new Error('未配置 AI（aggr-site/ai.json 或环境变量 GLM_API_KEY）');
  const pending = pickPendingEvents(limit);
  let analyzed = 0;
  const failed = [];
  for (const ev of pending) {
    try {
      await analyzeEvent(ev, cfg);
      analyzed++;
    } catch (e) {
      failed.push({ id: ev.id, error: e.message });
    }
  }
  return { analyzed, failed, pendingCount: pickPendingEvents(9999).length };
}

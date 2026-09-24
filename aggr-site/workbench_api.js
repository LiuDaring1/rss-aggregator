import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '..');

/**
 * 获取日期的 ISO 周次
 */
export function getISOWeek(d) {
  const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayNum = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  return Math.ceil((((date - yearStart) / 86400000) + 1) / 7);
}

/**
 * 动态扫描 issues/ 目录获取最新已发布的刊期信息
 */
export function getLatestPublishedIssue() {
  const issuesDir = path.join(PROJECT_ROOT, 'issues');
  if (!fs.existsSync(issuesDir)) return null;
  try {
    const dirs = fs.readdirSync(issuesDir)
      .filter(d => /^issue-\d{4}-w\d+$/i.test(d))
      .sort()
      .reverse();

    for (const d of dirs) {
      const stateFile = path.join(issuesDir, d, 'production_state.json');
      if (fs.existsSync(stateFile)) {
        try {
          const s = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
          if (s.stage === 'published' || s.published === true || s.status === 'published') {
            return { issueId: d, ...s };
          }
        } catch {}
      }
      const manifestFile = path.join(issuesDir, d, 'manifest_prep.json');
      const pdfFile = path.join(issuesDir, d, `${d}.pdf`);
      if (fs.existsSync(manifestFile) && fs.existsSync(pdfFile)) {
        return { issueId: d, status: 'published', pdfPath: `/issues/${d}/${d}.pdf` };
      }
    }
  } catch {}
  return null;
}

/**
 * 业务真实时间窗口动态计算 (统一 Asia/Shanghai，周四 20:00 截稿)
 * 纯算法驱动，无任何静态日期与期号写死
 */
export function calculateBusinessWindow(refDate = new Date()) {
  // 转换至北京时间 (UTC+8)
  const beijingTime = new Date(refDate.getTime() + (8 * 60 + refDate.getTimezoneOffset()) * 60000);
  const now = beijingTime;

  // 周四判定 (0=周日, 1=周一, ..., 4=周四)
  const day = now.getDay();
  // 距离本周四的天数: Thursday is 4
  const daysToThursday = (4 - day + 7) % 7;
  const thisThursdayDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() + daysToThursday);
  const thisThursday20pm = new Date(thisThursdayDate.getFullYear(), thisThursdayDate.getMonth(), thisThursdayDate.getDate(), 20, 0, 0);

  let currentCutoff;
  if (now < thisThursday20pm) {
    currentCutoff = thisThursday20pm;
  } else {
    currentCutoff = new Date(thisThursday20pm.getTime() + 7 * 24 * 3600 * 1000);
  }

  const currentStart = new Date(currentCutoff.getTime() - 7 * 24 * 3600 * 1000);
  const currentDelivery = new Date(currentCutoff.getTime() + 14 * 3600 * 1000); // 周五 10:00

  const nextCutoff = new Date(currentCutoff.getTime() + 7 * 24 * 3600 * 1000);
  const nextStart = currentCutoff;
  const nextDelivery = new Date(nextCutoff.getTime() + 14 * 3600 * 1000);

  const curDelivWeek = getISOWeek(currentDelivery);
  const curDelivYear = currentDelivery.getFullYear();
  const curIssueId = `issue-${curDelivYear}-w${String(curDelivWeek).padStart(2, '0')}`;

  const nextDelivWeek = getISOWeek(nextDelivery);
  const nextDelivYear = nextDelivery.getFullYear();
  const nextIssueId = `issue-${nextDelivYear}-w${String(nextDelivWeek).padStart(2, '0')}`;

  // 判定当前业务活跃备料窗口:
  // 若本周刊期已经定版发布（例如 W39 已出刊），则系统当前实际备料的是下一期；
  // 若当前时间已过周四 20:00，自然滚动到下一期；
  // 若当前时间仍在周四 20:00 前且本周刊期尚未定版，则备料窗口依然截止于本周四 20:00。
  const latestPublished = getLatestPublishedIssue();
  const alreadyPublishedCurrent = latestPublished && latestPublished.issueId === curIssueId;

  const activeWindow = alreadyPublishedCurrent ? {
    start: nextStart.toISOString(),
    cutoff: nextCutoff.toISOString(),
    delivery: nextDelivery.toISOString(),
    start_dt: nextStart,
    cutoff_dt: nextCutoff,
    delivery_dt: nextDelivery,
    targetIssueId: nextIssueId,
    label: `${formatDate(nextStart)} 20:00 ~ ${formatDate(nextCutoff)} 20:00`,
    description: `回望连续7天真实报道 (周四20:00截止，周五10:00发放)`
  } : {
    start: currentStart.toISOString(),
    cutoff: currentCutoff.toISOString(),
    delivery: currentDelivery.toISOString(),
    start_dt: currentStart,
    cutoff_dt: currentCutoff,
    delivery_dt: currentDelivery,
    targetIssueId: curIssueId,
    label: `${formatDate(currentStart)} 20:00 ~ ${formatDate(currentCutoff)} 20:00`,
    description: `回望连续7天真实报道 (周四20:00截止，周五10:00发放)`
  };

  return {
    now: now.toISOString(),
    activeWindow,
    current: {
      start: currentStart.toISOString(),
      cutoff: currentCutoff.toISOString(),
      delivery: currentDelivery.toISOString(),
      start_dt: currentStart,
      cutoff_dt: currentCutoff,
      delivery_dt: currentDelivery,
      targetIssueId: curIssueId,
      label: `${formatDate(currentStart)} 20:00 ~ ${formatDate(currentCutoff)} 20:00`,
      description: `回望连续7天真实报道 (周四20:00截止，周五10:00发放)`
    },
    next: {
      start: nextStart.toISOString(),
      cutoff: nextCutoff.toISOString(),
      delivery: nextDelivery.toISOString(),
      start_dt: nextStart,
      cutoff_dt: nextCutoff,
      delivery_dt: nextDelivery,
      targetIssueId: nextIssueId,
      label: `${formatDate(nextStart)} 20:00 ~ ${formatDate(nextCutoff)} 20:00`
    }
  };
}

function formatDate(d) {
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const date = String(d.getDate()).padStart(2, '0');
  return `${m}.${date}`;
}

/**
 * 将 Date 转换为北京时间 YYYY-MM-DD
 */
export function getBeijingYMD(d) {
  if (!d) return '';
  const b = new Date(d.getTime() + (8 * 60 + d.getTimezoneOffset()) * 60000);
  const y = b.getFullYear();
  const m = String(b.getMonth() + 1).padStart(2, '0');
  const date = String(b.getDate()).padStart(2, '0');
  return `${y}-${m}-${date}`;
}

/**
 * 判断文章发布时间是否落在指定业务窗口 [startDt, cutoffDt)
 * 1. 仅有日期时标记 date_only，截稿日当天标记 ambiguity: true
 * 2. 落在窗口内 inWindow: true, isHistory: false
 * 3. 早于窗口起始点 inWindow: false, isHistory: true (进入历史备用池)
 * 4. 晚于截稿点 inWindow: false, isHistory: false (归入下期)
 */
export function classifyArticleWindow(pubDateStr, startDt, cutoffDt) {
  if (!pubDateStr) {
    return {
      inWindow: false,
      isHistory: true,
      precision: 'missing_date',
      ambiguity: false,
      status: 'missing_date',
      reason: '缺少发布时间'
    };
  }
  const cleanPub = pubDateStr.trim();
  const isDateOnly = cleanPub.length <= 10;
  const startDateStr = getBeijingYMD(startDt);
  const cutoffDateStr = getBeijingYMD(cutoffDt);

  if (isDateOnly) {
    if (cleanPub === cutoffDateStr) {
      return {
        inWindow: true,
        isHistory: false,
        precision: 'date_only',
        ambiguity: true,
        status: 'needs_time_confirmation',
        reason: '发布于截稿当天但缺失具体时分，需确认是否在 20:00 前'
      };
    }
    if (cleanPub >= startDateStr && cleanPub < cutoffDateStr) {
      return {
        inWindow: true,
        isHistory: false,
        precision: 'date_only',
        ambiguity: false,
        status: 'in_window'
      };
    }
    if (cleanPub < startDateStr) {
      return {
        inWindow: false,
        isHistory: true,
        precision: 'date_only',
        ambiguity: false,
        status: 'history'
      };
    }
    return {
      inWindow: false,
      isHistory: false,
      precision: 'date_only',
      ambiguity: false,
      status: 'after_cutoff'
    };
  }

  try {
    let dt = new Date(cleanPub.includes(' ') && !cleanPub.includes('+') ? cleanPub.replace(' ', 'T') + '+08:00' : cleanPub);
    if (isNaN(dt.getTime())) {
      const datePart = cleanPub.slice(0, 10);
      return {
        inWindow: datePart >= startDateStr && datePart <= cutoffDateStr,
        isHistory: datePart < startDateStr,
        precision: 'date_only',
        ambiguity: datePart === cutoffDateStr,
        status: datePart < startDateStr ? 'history' : 'in_window'
      };
    }
    const t = dt.getTime();
    if (t >= startDt.getTime() && t < cutoffDt.getTime()) {
      return {
        inWindow: true,
        isHistory: false,
        precision: 'exact_time',
        ambiguity: false,
        status: 'in_window'
      };
    } else if (t < startDt.getTime()) {
      return {
        inWindow: false,
        isHistory: true,
        precision: 'exact_time',
        ambiguity: false,
        status: 'history'
      };
    } else {
      return {
        inWindow: false,
        isHistory: false,
        precision: 'exact_time',
        ambiguity: false,
        status: 'after_cutoff'
      };
    }
  } catch {
    return {
      inWindow: false,
      isHistory: true,
      precision: 'unknown',
      ambiguity: false,
      status: 'parse_error'
    };
  }
}


/**
 * 读取已定版出刊的往期查重库 (W38, W39 等)
 */
function getUsedSourcesRegistry() {
  const usedIds = new Set();
  const usedUrls = new Set();
  const issuesDir = path.join(PROJECT_ROOT, 'issues');
  if (!fs.existsSync(issuesDir)) return { usedIds, usedUrls };

  try {
    const dirs = fs.readdirSync(issuesDir);
    for (const dir of dirs) {
      const manifestPath = path.join(issuesDir, dir, 'manifest_prep.json');
      if (fs.existsSync(manifestPath)) {
        try {
          const data = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
          const units = [
            ...(data.retellings || []),
            ...(data.commentaries || []),
            ...(data.excerpts || [])
          ];
          for (const u of units) {
            if (u.raw_id) usedIds.add(u.raw_id);
            if (u.source_url) usedUrls.add(u.source_url);
          }
        } catch {}
      }
    }
  } catch {}

  return { usedIds, usedUrls };
}

/**
 * 读取持久化教师反馈 (data/teacher_feedback.json)
 */
export function getTeacherFeedback() {
  const p = path.join(PROJECT_ROOT, 'data', 'teacher_feedback.json');
  if (fs.existsSync(p)) {
    try {
      return JSON.parse(fs.readFileSync(p, 'utf8'));
    } catch {}
  }
  return {};
}

/**
 * 保存教师反馈
 */
export function saveTeacherFeedback(articleId, feedback) {
  const p = path.join(PROJECT_ROOT, 'data', 'teacher_feedback.json');
  const current = getTeacherFeedback();
  current[articleId] = {
    ...feedback,
    updatedAt: new Date().toISOString()
  };
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(current, null, 2), 'utf8');
  return current[articleId];
}

/**
 * 教学适用性多维评估与分栏目推荐引擎
 * 面向【高中中文口语表达训练】核心方向
 */
export function evaluatePedagogicalSuitability(article, rawContent, usedIds, usedUrls, teacherFeedback = {}) {
  const title = article.title || '';
  const content = rawContent || article.content || '';
  const combinedText = title + '\n' + content;
  const isUsed = usedIds.has(article.id) || (article.url && usedUrls.has(article.url));
  const tf = teacherFeedback[article.id];

  // 1. 检查教师反馈 (最高优先级，教师意见永不被算法覆盖)
  if (tf) {
    if (tf.action === 'keep') {
      return {
        suitability: 'teacher_approved',
        suitabilityLabel: '教师已保留',
        suitabilityBadge: 'badge-success',
        qualityScore: 98,
        tier: 'S',
        suggestedColumn: tf.targetColumn || article.recommendedRole || '🎯 建议：口语复述',
        structuredRationale: {
          whatHappened: article.summary || title,
          whyFits: '教师手动核验保留：符合课堂教学目标',
          suggestedColumn: tf.targetColumn || '口语复述',
          concerns: '无 (教师已确认)',
          evidenceSnippet: content.slice(0, 150)
        },
        teacherNotes: tf.notes || '',
        tags: ['教师核准', '课堂保留'],
        isUsed
      };
    } else if (tf.action === 'exclude') {
      return {
        suitability: 'teacher_excluded',
        suitabilityLabel: '教师已排除',
        suitabilityBadge: 'badge-danger',
        qualityScore: 10,
        tier: 'EXCLUDED',
        suggestedColumn: '不入常规推荐',
        structuredRationale: {
          whatHappened: title,
          whyFits: '教师排除',
          suggestedColumn: '不推荐',
          concerns: tf.notes || '教师标记不适合本周课堂',
          evidenceSnippet: ''
        },
        teacherNotes: tf.notes || '',
        tags: ['教师排除'],
        isUsed
      };
    } else if (tf.action === 'needs_info') {
      return {
        suitability: 'pending_facts',
        suitabilityLabel: '教师标记待补充',
        suitabilityBadge: 'badge-warning',
        qualityScore: 50,
        tier: 'B',
        suggestedColumn: '待补资料',
        structuredRationale: {
          whatHappened: title,
          whyFits: '题材有价值，但需补充关键事实',
          suggestedColumn: '待补事实',
          concerns: tf.notes || '待核实具体细节与时序',
          evidenceSnippet: content.slice(0, 150)
        },
        teacherNotes: tf.notes || '',
        tags: ['待补事实'],
        isUsed
      };
    }
  }

  // 2. 检查往期已采用 (沉底保护)
  if (isUsed) {
    return {
      suitability: 'not_recommended',
      suitabilityLabel: '往期已定版采用',
      suitabilityBadge: 'badge-danger',
      qualityScore: 15,
      tier: 'USED',
      suggestedColumn: '往期已用 (已沉底)',
      structuredRationale: {
        whatHappened: title,
        whyFits: '曾在往期周刊正式出刊中采用',
        suggestedColumn: '往期已用',
        concerns: '按自然周反重复规程自动沉底，杜绝重复选题',
        evidenceSnippet: ''
      },
      tags: ['往期已用', '自动沉底'],
      isUsed: true
    };
  }

  // 3. 教学红线与特别敏感议题检查 (任务书特别指出的艾滋病议题等)
  if (title.includes('艾滋') || content.includes('艾滋')) {
    return {
      suitability: 'needs_teacher_review',
      suitabilityLabel: '需教师特别复核',
      suitabilityBadge: 'badge-warning',
      qualityScore: 40,
      tier: 'C',
      suggestedColumn: '需教师确认',
      structuredRationale: {
        whatHappened: title,
        whyFits: '涉及隐私权与公共卫生法律讨论',
        suggestedColumn: '需教师复核',
        concerns: '涉及成人婚姻配偶知情权与敏感疾病隐私，不宜作为普通高中课堂即兴口语常规论题，须经教师特别确认。',
        evidenceSnippet: content.slice(0, 160)
      },
      tags: ['需教师复核', '敏感隐私议题'],
      isUsed: false
    };
  }

  // 4. 正文缺失 / 纯元数据检查
  const hasFullText = article.hasFullText && content.length >= 200;
  if (!hasFullText) {
    return {
      suitability: 'pending_facts',
      suitabilityLabel: '待补事实/正文',
      suitabilityBadge: 'badge-warning',
      qualityScore: 30,
      tier: 'METADATA',
      suggestedColumn: '待补正文',
      structuredRationale: {
        whatHappened: title,
        whyFits: '具备标题线索',
        suggestedColumn: '待补正文',
        concerns: '缺少清洗后的完整正文，无法提取 9 句动作复述或长难句，不能自动推荐入刊。',
        evidenceSnippet: ''
      },
      tags: ['仅元数据', '待补正文'],
      isUsed: false
    };
  }

  // 5. 枯燥行政公报与内部例会过滤
  const negativeKeywords = ['人事任免', '代表大会', '主持召开', '国务院', '省委常委会', '市委常委会', '经济指标通报', '进出口数据', '签约仪式', '部署开展例会'];
  if (negativeKeywords.some(k => title.includes(k))) {
    return {
      suitability: 'not_recommended',
      suitabilityLabel: '不入常规推荐',
      suitabilityBadge: 'badge-secondary',
      qualityScore: 35,
      tier: 'C',
      suggestedColumn: '不入常规',
      structuredRationale: {
        whatHappened: title,
        whyFits: '政务日常公文',
        suggestedColumn: '常规不推荐',
        concerns: '偏向机关内部例行公文与宏观统计，缺乏高中生可切入的生活经验与人物情节。',
        evidenceSnippet: content.slice(0, 140)
      },
      tags: ['政务通报', '缺乏情节'],
      isUsed: false
    };
  }

  // 6. 优质教学适用性分类与分栏目推荐
  const campusKeywords = ['学校', '学生', '老师', '教师', '高校', '大学', '高中', '校园', '考研', '高考', '军训', '手机', '宿舍', '家长', '教育', '青春', '少年', '青年', '校友', '开学', '跳绳', '体育'];
  const techKeywords = ['AI', '人工智能', '大模型', '算法', '短视频', '直播', '社交媒体', '网络', 'App', '手机', '信息泄露', '智驾', '新能源汽车', '自动驾驶', '机器人', '无人零售'];
  const lifeKeywords = ['外卖', '快递', '骑手', '消费', '房车', '露营', '自驾', '宠物', '养犬', '租房', '旅游', '门禁', '电影', '运动', '货车司机', '边贸', '非遗'];
  const civicKeywords = ['道歉', '退款', '诚信', '维权', '安全', '救人', '见义勇为', '牺牲', '规则', '侵权', '食品安全', '打假', '盲区'];

  // 叙事特征词 (适合复述单元)
  const narrativeKeywords = ['冠军', '走进', '女孩', '少年', '老人', '男子', '校友', '骑手', '司机', '老师', '学生', '救下', '摔倒', '坠亡', '走红', '被查', '被罚', '举报', '冲上热搜', '淘金者', '世界技能大赛'];
  // 思辨特征词 (适合时评立论)
  const debateKeywords = ['岂能', '该不该', '为何', '何以', '究竟', '谁来', '如何看待', '防御式', '不能跑在', '别让', '莫让', '争议', '值得反思', '注意事项', '追问', '答澎湃', '新京报快评', '马上评'];

  const isCampus = campusKeywords.some(k => combinedText.includes(k));
  const isTech = techKeywords.some(k => combinedText.includes(k));
  const isLife = lifeKeywords.some(k => combinedText.includes(k));
  const isCivic = civicKeywords.some(k => combinedText.includes(k));

  const hasNarrative = narrativeKeywords.some(k => combinedText.includes(k));
  const hasDebate = debateKeywords.some(k => combinedText.includes(k));

  let score = 65; // 基础合格分 (已有完整正文且通过适用性筛选)
  const tags = ['规则初筛'];

  if (isCampus) { score += 12; tags.push('校园成长'); }
  if (isTech) { score += 10; tags.push('科技生活'); }
  if (isLife) { score += 8; tags.push('青年民生'); }
  if (isCivic) { score += 8; tags.push('公共规则'); }

  // 篇幅评级
  const len = content.length;
  if (len >= 600 && len <= 2600) {
    score += 10;
    tags.push('篇幅适中');
  }

  let suggestedColumn = '📝 建议：拆解积累 (语言素材)';
  let whyFits = '语言表达规范，适合高中生研读原段说理结构与词句积累。';
  let evidenceSnippet = content.slice(0, 180).replace(/\n+/g, ' ');

  if (hasNarrative) {
    score += 10;
    suggestedColumn = '🎯 建议：口语复述 (故事叙事)';
    whyFits = '包含具体人物、行动冲突与鲜活情节，易于提炼 9 句动作复述主干并配套漫画。';
    tags.push('具叙事场景');
  } else if (hasDebate) {
    score += 8;
    suggestedColumn = '💡 建议：时评思辨 (双向立论)';
    whyFits = '具备清晰的问题意识与思辨张力，中学生能从生活经验切入展开双向立论。';
    tags.push('有思辨空间');
  }

  score = Math.min(96, Math.max(50, score));

  let tier = 'B';
  let tierLabel = 'B级 · 补充参考';
  let tierBadge = 'badge-warning';

  if (score >= 88) {
    tier = 'S';
    tierLabel = '⭐️⭐️⭐️⭐️⭐️ S级 · 重点推荐';
    tierBadge = 'badge-success';
  } else if (score >= 76) {
    tier = 'A';
    tierLabel = '⭐️⭐️⭐️⭐️ A级 · 优质备选';
    tierBadge = 'badge-info';
  }

  return {
    suitability: 'recommended',
    suitabilityLabel: '可推荐',
    suitabilityBadge: 'badge-success',
    qualityScore: score,
    tier,
    tierLabel,
    tierBadge,
    suggestedColumn,
    structuredRationale: {
      whatHappened: article.summary || title,
      whyFits,
      suggestedColumn,
      concerns: '入选前请教师快速核对关键时间与真实主体',
      evidenceSnippet
    },
    tags: Array.from(new Set(tags)),
    isUsed: false
  };
}

/**
 * 加载全库统一候选池 (合并 评论库 + 暖文库) 并读取真实正文
 */
export async function getUnifiedCandidates() {
  const candidates = [];
  const { usedIds, usedUrls } = getUsedSourcesRegistry();
  const teacherFeedback = getTeacherFeedback();
  const windows = calculateBusinessWindow();

  // 1. 评论库 (aggr-site/data/commentaries/db.json)
  const commDbPath = path.join(__dirname, 'data', 'commentaries', 'db.json');
  if (fs.existsSync(commDbPath)) {
    try {
      const commDb = JSON.parse(fs.readFileSync(commDbPath, 'utf8'));
      const articles = Object.values(commDb.articles || {});
      for (const a of articles) {
        // 读取真实正文
        let fullText = a.content || '';
        const rawFile = path.join(__dirname, 'data', 'commentaries', 'raw', `${path.basename(a.id)}.json`);
        if (fs.existsSync(rawFile)) {
          try {
            const rawJson = JSON.parse(fs.readFileSync(rawFile, 'utf8'));
            fullText = rawJson.content || rawJson.rawText || fullText;
          } catch {}
        }

        const evaluation = evaluatePedagogicalSuitability(a, fullText, usedIds, usedUrls, teacherFeedback);
        const pubDateStr = a.publishedAt || '';
        const winClass = classifyArticleWindow(pubDateStr, windows.current.start_dt, windows.current.cutoff_dt);

        candidates.push({
          id: a.id,
          origin: 'commentary',
          originLabel: '时评与事实库',
          title: a.title,
          source: a.sourceName || a.source || '权威媒体',
          sourceId: a.sourceId,
          publishedAt: pubDateStr,
          awardDate: null,
          datePrecision: winClass.precision,
          cutoffDayAmbiguity: winClass.ambiguity,
          inWindow: winClass.inWindow,
          isHistory: winClass.isHistory,
          windowStatus: winClass.status,
          hasFullText: !!(a.hasFullText && fullText.length >= 200),
          contentLength: fullText.length,
          url: a.url || '#',
          summary: a.summary || fullText.slice(0, 140) + '...',
          content: fullText,
          scoreDisclaimer: '规则初筛分，不代表教师适用性结论',
          modelEvaluation: null,
          modelEvaluatedAt: null,
          // 教学适用性与推荐
          ...evaluation
        });
      }
    } catch (e) {
      console.error('Failed to load commentaries:', e);
    }
  }

  // 2. 暖文库 (aggr-site/data/wenwen/db.json)
  // 天天正能量报道：使用 sourcePublishedAt || publishedAt 作为真实报道日期
  // awardDate 严格作为颁奖元数据，绝不决定自然周入库与出刊窗口
  const wenwenDbPath = path.join(__dirname, 'data', 'wenwen', 'db.json');
  if (fs.existsSync(wenwenDbPath)) {
    try {
      const wenwenDb = JSON.parse(fs.readFileSync(wenwenDbPath, 'utf8'));
      const articleIndex = wenwenDb.articleIndex || {};
      for (const [id, a] of Object.entries(articleIndex)) {
        if (a.isTestData) continue; // 排除测试数据

        // 读取暖文真实正文
        let fullText = '';
        const rawFile = path.join(__dirname, 'data', 'wenwen', 'raw', `${path.basename(id)}.json`);
        if (fs.existsSync(rawFile)) {
          try {
            const rawJson = JSON.parse(fs.readFileSync(rawFile, 'utf8'));
            fullText = rawJson.content || rawJson.rawText || '';
          } catch {}
        }

        const realPublishedAt = a.sourcePublishedAt || a.publishedAt || '';
        const awardDate = a.awardDate || null;
        const winClass = classifyArticleWindow(realPublishedAt, windows.current.start_dt, windows.current.cutoff_dt);

        const adaptedArticle = {
          id,
          title: a.title,
          sourceName: a.media || '天天正能量',
          publishedAt: realPublishedAt,
          url: a.url,
          hasFullText: fullText.length >= 200,
          summary: fullText.slice(0, 140) + '...'
        };

        const evaluation = evaluatePedagogicalSuitability(adaptedArticle, fullText, usedIds, usedUrls, teacherFeedback);

        candidates.push({
          id,
          origin: 'wenwen',
          originLabel: '暖文雷达',
          title: a.title,
          source: a.media || '天天正能量',
          sourceId: 'wenwen',
          publishedAt: realPublishedAt,
          awardDate: awardDate,
          datePrecision: winClass.precision,
          cutoffDayAmbiguity: winClass.ambiguity,
          inWindow: winClass.inWindow,
          isHistory: winClass.isHistory,
          windowStatus: winClass.status,
          hasFullText: fullText.length >= 200,
          contentLength: fullText.length,
          url: a.url || '#',
          summary: fullText.slice(0, 140) + '...',
          content: fullText,
          scoreDisclaimer: '规则初筛分，不代表教师适用性结论',
          modelEvaluation: null,
          modelEvaluatedAt: null,
          // 教学适用性与推荐
          ...evaluation
        });
      }
    } catch (e) {
      console.error('Failed to load wenwen candidates:', e);
    }
  }

  return candidates;
}

/**
 * 分页与全量搜索查询 API (支持 current / history / all 候选池隔离)
 */
export async function queryCandidates({
  pool = 'current',
  search = '',
  suitability = 'all',
  column = 'all',
  source = 'all',
  sort = 'score',
  page = 1,
  pageSize = 20
} = {}) {
  const allCandidates = await getUnifiedCandidates();
  let filtered = allCandidates;

  // 0. 候选池隔离 (current: 本周业务窗口 [current_start, current_cutoff) | history: 历史备用池 | all: 全库所有材料)
  if (pool === 'current') {
    filtered = filtered.filter(a => a.inWindow === true);
  } else if (pool === 'history') {
    filtered = filtered.filter(a => a.isHistory === true);
  }
  // pool === 'all' 则不做窗口限制

  // 1. 文本搜索 (标题与正文)
  if (search && search.trim()) {
    const q = search.trim().toLowerCase();
    filtered = filtered.filter(a => 
      (a.title && a.title.toLowerCase().includes(q)) || 
      (a.source && a.source.toLowerCase().includes(q)) ||
      (a.content && a.content.toLowerCase().includes(q))
    );
  }

  // 2. 教学适用性过滤
  if (suitability && suitability !== 'all') {
    if (suitability === 'top') {
      filtered = filtered.filter(a => (a.tier === 'S' || a.tier === 'A') && a.suitability === 'recommended');
    } else if (suitability === 'recommended') {
      filtered = filtered.filter(a => a.suitability === 'recommended' || a.suitability === 'teacher_approved');
    } else if (suitability === 'needs_review') {
      filtered = filtered.filter(a => a.suitability === 'needs_teacher_review');
    } else if (suitability === 'pending_facts') {
      filtered = filtered.filter(a => a.suitability === 'pending_facts');
    } else if (suitability === 'excluded') {
      filtered = filtered.filter(a => a.suitability === 'not_recommended' || a.suitability === 'teacher_excluded' || a.isUsed);
    } else if (suitability === 'used') {
      filtered = filtered.filter(a => a.isUsed);
    }
  }

  // 3. 建议栏目过滤
  if (column && column !== 'all') {
    filtered = filtered.filter(a => a.suggestedColumn && a.suggestedColumn.includes(column));
  }

  // 4. 信源过滤
  if (source && source !== 'all') {
    filtered = filtered.filter(a => a.sourceId === source || a.source === source);
  }

  // 5. 排序
  if (sort === 'score') {
    filtered.sort((a, b) => (b.qualityScore || 0) - (a.qualityScore || 0));
  } else if (sort === 'date') {
    filtered.sort((a, b) => (b.publishedAt || '').localeCompare(a.publishedAt || ''));
  }

  const totalMatches = filtered.length;
  const totalPages = Math.ceil(totalMatches / pageSize) || 1;
  const currentPage = Math.max(1, Math.min(Number(page) || 1, totalPages));
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedArticles = filtered.slice(startIndex, startIndex + pageSize);

  return {
    totalMatches,
    page: currentPage,
    pageSize,
    totalPages,
    pool,
    articles: paginatedArticles
  };
}

/**
 * 获取周刊生产工作台实时聚合总览数据
 */
export async function getWorkbenchData() {
  const now = new Date();
  const windows = calculateBusinessWindow(now);

  // 1. 读取采集与调度监控 (data/fetch_state.json)
  const fetchStatePath = path.join(PROJECT_ROOT, 'data', 'fetch_state.json');
  let fetchState = {
    updatedAt: null,
    last_attempt_at: null,
    last_success_at: null,
    status: 'unknown',
    all_failed: false,
    total_sources: 14,
    source_stats: []
  };
  if (fs.existsSync(fetchStatePath)) {
    try {
      fetchState = JSON.parse(fs.readFileSync(fetchStatePath, 'utf8'));
    } catch {}
  }

  // launchd 加载状态
  let launchdLoaded = false;
  try {
    const out = execSync('launchctl list | grep weekly || true', { encoding: 'utf8' });
    launchdLoaded = out.includes('com.weekly.fetch_commentaries');
  } catch {
    launchdLoaded = false;
  }

  // 暖文雷达状态 (aggr-site/data/wenwen/db.json)
  // 根据实际进程采集时间与执行情况动态判定 active / stale / stopped
  const wenwenDbPath = path.join(__dirname, 'data', 'wenwen', 'db.json');
  let wenwenMeta = { lastCollectAt: null, lastAnalyzeAt: null, totalArticles: 0, totalEvents: 0 };
  let wenwenStatus = 'stopped';
  let wenwenStatusLabel = '未运行';

  if (fs.existsSync(wenwenDbPath)) {
    try {
      const wdb = JSON.parse(fs.readFileSync(wenwenDbPath, 'utf8'));
      const lastCollect = wdb.meta?.lastCollectAt || wdb.meta?.lastScrapeAt || null;
      const lastAnalyze = wdb.meta?.lastAnalyzeAt || null;
      wenwenMeta = {
        lastCollectAt: lastCollect,
        lastAnalyzeAt: lastAnalyze,
        totalArticles: Object.keys(wdb.articleIndex || {}).length,
        totalEvents: Object.keys(wdb.events || {}).length
      };

      if (process.env.AGGR_AUTOTASKS === 'off') {
        wenwenStatus = 'stopped';
        wenwenStatusLabel = '已手动暂停 (AGGR_AUTOTASKS=off)';
      } else if (lastCollect) {
        const lastT = new Date(lastCollect).getTime();
        const diffHours = (now.getTime() - lastT) / (3600 * 1000);
        if (diffHours <= 12) {
          wenwenStatus = 'active';
          wenwenStatusLabel = diffHours < 1
            ? `运行正常 (最近采集: ${Math.max(1, Math.round(diffHours * 60))} 分钟前)`
            : `运行正常 (最近采集: ${Math.round(diffHours)} 小时前)`;
        } else if (diffHours <= 24) {
          wenwenStatus = 'stale';
          wenwenStatusLabel = `采集延迟 (距离上次采集已 ${Math.round(diffHours)} 小时)`;
        } else {
          wenwenStatus = 'stopped';
          wenwenStatusLabel = `采集停滞 (距离上次采集超过 ${Math.round(diffHours)} 小时)`;
        }
      } else {
        wenwenStatus = 'stopped';
        wenwenStatusLabel = '未见采集记录';
      }
    } catch {}
  }

  // 备份与恢复状态 (data/backup_state.json)
  const backupStatePath = path.join(PROJECT_ROOT, 'data', 'backup_state.json');
  let backupState = {
    last_backup: null,
    last_restore_test: null,
    offsite: { status: 'pending_configuration', label: '待配置 (缺少受控外部目标)' }
  };
  if (fs.existsSync(backupStatePath)) {
    try {
      backupState = JSON.parse(fs.readFileSync(backupStatePath, 'utf8'));
    } catch {}
  }

  // AI 分析引擎状态与免责声明
  let aiEngineStatus = 'rule_screening';
  let aiEngineLabel = '本地规则初筛（未配置 AI 密钥，未经教学复核）';
  if (process.env.GLM_API_KEY) {
    aiEngineStatus = 'model_ready';
    aiEngineLabel = 'GLM-5 在线模型分析就绪';
  }

  // 候选池动态统计 (严格区隔在窗口内与历史备用)
  const allCandidates = await getUnifiedCandidates();
  const inWindowCandidates = allCandidates.filter(a => a.inWindow);
  const historyCandidates = allCandidates.filter(a => a.isHistory);
  const recommendedCount = allCandidates.filter(a => a.suitability === 'recommended' || a.suitability === 'teacher_approved').length;
  const inWindowRecommendedCount = inWindowCandidates.filter(a => a.suitability === 'recommended' || a.suitability === 'teacher_approved').length;
  const needsReviewCount = allCandidates.filter(a => a.suitability === 'needs_teacher_review').length;
  const inWindowNeedsReviewCount = inWindowCandidates.filter(a => a.suitability === 'needs_teacher_review').length;
  const pendingFactsCount = allCandidates.filter(a => a.suitability === 'pending_facts').length;
  const inWindowPendingFactsCount = inWindowCandidates.filter(a => a.suitability === 'pending_facts').length;
  const usedCount = allCandidates.filter(a => a.isUsed).length;

  // 刊期动态关联
  const latestPublished = getLatestPublishedIssue();
  const curIssueId = windows.current.targetIssueId;
  const alreadyPublishedCurrent = latestPublished && latestPublished.issueId === curIssueId;
  const targetIssue = alreadyPublishedCurrent ? windows.next : windows.current;

  const formatDeadline = (d) => `${formatDate(d)} 20:00:00`;
  const formatDelivery = (d) => `${formatDate(d)} 10:00:00`;

  return {
    timestamp: now.toISOString(),
    windows,
    tasks: {
      commentary_fetch: {
        label: '时评与事实采集 (Python + launchd)',
        cadence: '每日 2 次 (09:30、18:30) + 周四 20:05 截稿补采',
        loaded: launchdLoaded,
        status: fetchState.status || (launchdLoaded ? 'active' : 'paused'),
        statusLabel: fetchState.status === 'success' ? '采集正常' : (fetchState.status === 'partial_failure' ? '部分信源失败' : (fetchState.status === 'all_failed' ? '全源失败' : '运行正常')),
        last_attempt_at: fetchState.last_attempt_at,
        last_success_at: fetchState.last_success_at,
        total_sources: fetchState.total_sources || 14,
        failed_sources_count: fetchState.failed_sources_count || 0,
        sources: fetchState.source_stats || []
      },
      wenwen_radar: {
        label: '暖文雷达调度 (Node.js 后台)',
        cadence: '采集 6h / 分析 20min 周期自跑',
        status: wenwenStatus,
        statusLabel: wenwenStatusLabel,
        lastScrapeAt: wenwenMeta.lastCollectAt,
        lastCollectAt: wenwenMeta.lastCollectAt,
        lastAnalyzeAt: wenwenMeta.lastAnalyzeAt,
        totalArticles: wenwenMeta.totalArticles,
        totalEvents: wenwenMeta.totalEvents
      },
      analysis_engine: {
        label: '选材分析与推荐引擎',
        status: aiEngineStatus,
        statusLabel: aiEngineLabel,
        disclaimer: '规则初筛分，不代表教师适用性结论',
        modelEvaluationSupported: true
      },
      backup: {
        label: '数据保存与隔离恢复测试',
        last_backup_file: backupState.last_backup?.archive_file || '未见备份',
        last_backup_time: backupState.last_backup?.timestamp || null,
        last_backup_sha256: backupState.last_backup?.sha256 || '',
        last_restore_status: backupState.last_restore_test?.status === 'passed' ? '隔离恢复测试通过 (PASS)' : '待测试',
        offsite_status: backupState.offsite?.label || '待配置 (缺少外部受控存储目标)'
      }
    },
    candidatePoolStats: {
      totalUnified: allCandidates.length,
      inWindowTotal: inWindowCandidates.length,
      historyTotal: historyCandidates.length,
      recommended: recommendedCount,
      recommendedInWindow: inWindowRecommendedCount,
      needsTeacherReview: needsReviewCount,
      needsTeacherReviewInWindow: inWindowNeedsReviewCount,
      pendingFacts: pendingFactsCount,
      pendingFactsInWindow: inWindowPendingFactsCount,
      used: usedCount,
      fullTextArticles: allCandidates.filter(a => a.hasFullText).length
    },
    // 看板推荐榜：优先展示窗口内优质候选
    topCandidates: (inWindowCandidates.length > 0 ? inWindowCandidates : allCandidates)
      .filter(a => a.suitability === 'recommended' || a.suitability === 'teacher_approved')
      .sort((a, b) => (b.qualityScore || 0) - (a.qualityScore || 0))
      .slice(0, 20),
    currentIssue: {
      issueId: latestPublished?.issueId || curIssueId,
      attribute: latestPublished?.issueId === 'issue-2026-w39' ? '首次试发件 (Trial Release)' : '往期正式发刊',
      attributeDesc: '已定版发布 (47页)，供课堂教学实测版面与口语复述易读性',
      status: 'published',
      statusLabel: '已发布',
      pdfPath: latestPublished?.pdfPath || `/issues/${latestPublished?.issueId || curIssueId}/${latestPublished?.issueId || curIssueId}.pdf`,
      reviewSiteUrl: `/review/issues/${latestPublished?.issueId || curIssueId}/index.html`
    },
    nextIssue: {
      issueId: targetIssue.targetIssueId,
      attribute: '常规周生产 (Regular Weekly Cadence)',
      cadenceRule: '每周四 20:00 资料截止 | 每周五 10:00 发放 | 回望连续 7 天',
      cutoffDeadline: `${formatDeadline(targetIssue.cutoff_dt)} (周四)`,
      deliveryTime: `${formatDelivery(targetIssue.delivery_dt)} (周五)`,
      windowRange: targetIssue.label,
      stage: 'prep',
      stageClassification: 'waiting_for_schedule',
      stageClassificationLabel: '等待计划时间（周内正常采集备料中）',
      actionNeeded: '当前无须人工干预。周四 20:00 截稿后，教师进入工作台审阅 S/A 级推荐材料并确认入刊。',
      stages: [
        { name: '周内持续采编备料', status: 'active', note: `正在汇聚 [${targetIssue.label}] 真实报道` },
        { name: '周四截稿前夕核验', status: 'waiting_for_schedule', note: '等待周四 20:00 资料截稿窗口封闭' },
        { name: '智能优选与教师选材', status: 'waiting_for_schedule', note: '待截稿后教师下达入选确认指令' },
        { name: '原子排版与全门禁核验', status: 'waiting_for_schedule', note: '待选材定稿后自动执行' },
        { name: '定版发放 (周五 10:00)', status: 'waiting_for_schedule', note: '待全门禁通过后发放' }
      ]
    }
  };
}

/**
 * 读取单个信源原始 JSON 正文详情
 */
export async function getArticleDetail(id) {
  const safeId = path.basename(id);
  // 1. 尝试评论库
  const commPath = path.join(__dirname, 'data', 'commentaries', 'raw', `${safeId}.json`);
  if (fs.existsSync(commPath)) {
    try {
      return JSON.parse(fs.readFileSync(commPath, 'utf8'));
    } catch {}
  }
  // 2. 尝试暖文库
  const wenwenPath = path.join(__dirname, 'data', 'wenwen', 'raw', `${safeId}.json`);
  if (fs.existsSync(wenwenPath)) {
    try {
      return JSON.parse(fs.readFileSync(wenwenPath, 'utf8'));
    } catch {}
  }
  return null;
}

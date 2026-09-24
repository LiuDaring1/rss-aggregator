import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '..');

/**
 * 扫描往期已定版使用的信源 ID 与 URL（查重库）
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
 * 针对高中英语口语素材周刊的 5 维智能优选打分体系
 */
function scoreArticle(article, usedIds, usedUrls) {
  let score = 50; // 基础起评分
  const tags = [];
  let isUsed = false;

  // 维度 1：往期查重与降权（杜绝重复使用同一批材料）
  if (usedIds.has(article.id) || (article.url && usedUrls.has(article.url))) {
    isUsed = true;
    score -= 60;
    tags.push('往期已采用');
  }

  // 维度 2：正文完整度与篇幅区间 (满分 25 分)
  if (!article.hasFullText) {
    score -= 25;
    tags.push('仅元数据');
  } else {
    const len = article.contentLength || (article.content ? article.content.length : 0);
    if (len >= 800 && len <= 2500) {
      score += 25; // 最理想篇幅：适宜提炼 9 句复述与深度词句
      tags.push('篇幅适中');
    } else if (len >= 500 && len < 800) {
      score += 15;
      tags.push('略短');
    } else if (len > 2500 && len <= 4000) {
      score += 15;
      tags.push('较长');
    } else if (len > 4000) {
      score += 5;
      tags.push('特长通稿');
    } else {
      score += 5;
      tags.push('过短');
    }
  }

  // 维度 3：高中生口语生活与时代热点契合度 (满分 30 分)
  const title = article.title || '';
  const content = (article.content || '') + ' ' + title;

  const campusKeywords = ['学校', '学生', '老师', '教师', '高校', '大学', '高中', '校园', '考研', '高考', '军训', '手机', '宿舍', '家长', '教育', '青春', '少年', '青年', '校友', '开学', '课堂'];
  const techKeywords = ['AI', '人工智能', '大模型', '算法', '短视频', '直播', '社交媒体', '网络', 'App', '手机', '信息泄露', '隐私', '网红', '机器人'];
  const youthLifeKeywords = ['外卖', '快递', '骑手', '消费', '月饼', '宠物', '养犬', '租房', '旅游', '门禁', '电影', '运动', '低碳', '环保', '打工', '就业', '求职'];
  const civicKeywords = ['道歉', '退款', '诚信', '维权', '安全', '救人', '见义勇为', '牺牲', '规则', '侵权', '食品安全', '打假'];
  const negativeKeywords = ['人事任免', '代表大会', '主持召开', '国务院', '省委', '市委', '经济指标', '进出口数据', '签约仪式', '部署开展', '常务会议'];

  if (campusKeywords.some(k => title.includes(k) || content.includes(k))) {
    score += 15;
    tags.push('校园教育');
  }
  if (techKeywords.some(k => title.includes(k) || content.includes(k))) {
    score += 15;
    tags.push('科技生活');
  }
  if (youthLifeKeywords.some(k => title.includes(k) || content.includes(k))) {
    score += 12;
    tags.push('青年民生');
  }
  if (civicKeywords.some(k => title.includes(k) || content.includes(k))) {
    score += 12;
    tags.push('公德规则');
  }
  if (negativeKeywords.some(k => title.includes(k))) {
    score -= 30;
    tags.push('宏观政务');
  }

  // 维度 4：叙事故事性（适合第 1 分册【9篇口语复述】）
  const narrativeKeywords = ['女孩', '少年', '老人', '男子', '校友', '骑手', '老师', '学生', '救下', '摔倒', '坠亡', '走红', '被查', '被罚', '举报', '引发热议', '冲上热搜'];
  const hasNarrative = narrativeKeywords.some(k => title.includes(k));
  if (hasNarrative) {
    score += 15;
    tags.push('具叙事场景');
  }

  // 维度 5：思辨争议度（适合第 2 分册【6篇时评思辨立论】）
  const debateKeywords = ['岂能', '该不该', '为何', '何以', '究竟', '谁来', '如何看待', '防御式', '不能跑在', '别让', '莫让', '争议', '值得反思', '不该没有', '新京报快评', '马上评', '红辣椒', '浙江宣传'];
  const hasDebate = debateKeywords.some(k => title.includes(k));
  if (hasDebate) {
    score += 12;
    tags.push('有思辨空间');
  }

  // 判定建议栏目
  let recommendedRole = '常规备选';
  if (isUsed) {
    recommendedRole = '往期已用 (已沉底)';
  } else if (hasNarrative && article.hasFullText) {
    recommendedRole = '🎯 口语复述 (故事叙事)';
  } else if (hasDebate && article.hasFullText) {
    recommendedRole = '💡 时评思辨 (双向立论)';
  } else if (article.hasFullText) {
    recommendedRole = '📝 拆解积累 (语言素材)';
  } else {
    recommendedRole = '元数据参考';
  }

  // 归一化得分 [0, 100]
  score = Math.max(0, Math.min(100, score));

  // 推荐等级
  let tier = 'C';
  let tierLabel = 'C级 · 常规收录';
  let tierBadge = 'badge-secondary';

  if (isUsed) {
    tier = 'USED';
    tierLabel = '🚫 往期已用';
    tierBadge = 'badge-danger';
  } else if (score >= 90) {
    tier = 'S';
    tierLabel = '⭐️⭐️⭐️⭐️⭐️ S级 · 重点推荐';
    tierBadge = 'badge-success';
  } else if (score >= 75) {
    tier = 'A';
    tierLabel = '⭐️⭐️⭐️⭐️ A级 · 优质备选';
    tierBadge = 'badge-info';
  } else if (score >= 60) {
    tier = 'B';
    tierLabel = '⭐️⭐️⭐️ B级 · 补充参考';
    tierBadge = 'badge-warning';
  }

  return {
    score,
    tier,
    tierLabel,
    tierBadge,
    tags: Array.from(new Set(tags)),
    recommendedRole,
    isUsed,
  };
}

/**
 * 计算下次执行时间 (每天 09:30 与 18:30)
 */
function calculateNextScheduledTime(now) {
  const todayMorning = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 9, 30, 0);
  const todayEvening = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 18, 30, 0);
  const tomorrowMorning = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 9, 30, 0);

  if (now < todayMorning) return todayMorning.toISOString();
  if (now < todayEvening) return todayEvening.toISOString();
  return tomorrowMorning.toISOString();
}

/**
 * 获取周刊生产工作台实时聚合数据
 */
export async function getWorkbenchData() {
  const now = new Date();
  
  // 1. 读取采集器与调度状态 (launchd / db.json)
  const dbPath = path.join(__dirname, 'data', 'commentaries', 'db.json');
  let db = { totalArticles: 0, fullTextArticles: 0, articles: {}, updatedAt: null, sourceStats: [] };
  if (fs.existsSync(dbPath)) {
    try {
      db = JSON.parse(fs.readFileSync(dbPath, 'utf8'));
    } catch (e) {
      console.error('Failed to read db.json:', e);
    }
  }

  // 检查 launchctl 状态
  let launchdLoaded = false;
  try {
    const out = execSync('launchctl list | grep weekly || true', { encoding: 'utf8' });
    launchdLoaded = out.includes('com.weekly.fetch_commentaries');
  } catch {
    launchdLoaded = false;
  }

  // 读取最近一次执行日志
  const logPath = path.join(PROJECT_ROOT, 'data', 'logs', 'launchd_fetch.log');
  let lastLogSnippet = '';
  if (fs.existsSync(logPath)) {
    try {
      const logContent = fs.readFileSync(logPath, 'utf8');
      const lines = logContent.trim().split('\n');
      lastLogSnippet = lines.slice(-15).join('\n');
    } catch (e) {
      lastLogSnippet = String(e);
    }
  }

  const lastCrawlTimeStr = db.updatedAt || null;
  const lastCrawlDate = lastCrawlTimeStr ? new Date(lastCrawlTimeStr) : null;
  const minutesSinceLastCrawl = lastCrawlDate ? Math.round((now.getTime() - lastCrawlDate.getTime()) / 60000) : null;

  // 判定状态：因改为每日 2 次 (09:30, 18:30)，间隔可长达 15 小时；若大于 24 小时 (1440分钟) 则判定为过期
  let schedulerStatus = 'active';
  let schedulerStatusLabel = '调度服务运行正常 (每日 2 次轻量轮询)';
  if (!launchdLoaded) {
    schedulerStatus = 'paused';
    schedulerStatusLabel = '系统常驻服务未加载';
  } else if (minutesSinceLastCrawl !== null && minutesSinceLastCrawl > 1440) {
    schedulerStatus = 'stale';
    schedulerStatusLabel = '状态过期，需检查 (上次成功距今已超过24小时)';
  }

  const nextScheduledTime = calculateNextScheduledTime(now);

  // 2. 查重库载入
  const { usedIds, usedUrls } = getUsedSourcesRegistry();

  // 3. 本周新增报道统计与智能优选打分 (以 2026-09-21 零点为当前周起始)
  const articles = Object.values(db.articles || {});
  const thisWeekArticlesRaw = articles.filter(a => {
    const pub = a.publishedAt || a.date || '';
    return pub >= '2026-09-21';
  });

  const scoredArticles = thisWeekArticlesRaw.map(a => {
    const scoring = scoreArticle(a, usedIds, usedUrls);
    return {
      id: a.id,
      title: a.title,
      source: a.source || a.media || a.sourceName || '时评信源',
      publishedAt: a.publishedAt || a.date || '未知',
      hasFullText: !!a.hasFullText,
      textType: a.textType || (a.hasFullText ? 'full_text' : 'metadata_only'),
      contentLength: a.contentLength || 0,
      summary: a.summary || (a.content ? a.content.slice(0, 140) + '...' : '暂无摘要'),
      content: a.content || '',
      url: a.url || a.sourceUrl || '#',
      score: scoring.score,
      tier: scoring.tier,
      tierLabel: scoring.tierLabel,
      tierBadge: scoring.tierBadge,
      tags: scoring.tags,
      recommendedRole: scoring.recommendedRole,
      isUsed: scoring.isUsed,
    };
  });

  // 默认按智能优选评分从高到低排序，得分相同按时间倒序
  scoredArticles.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return (b.publishedAt || '').localeCompare(a.publishedAt || '');
  });

  const thisWeekFullText = scoredArticles.filter(a => a.hasFullText);
  const sTierCount = scoredArticles.filter(a => a.tier === 'S').length;
  const aTierCount = scoredArticles.filter(a => a.tier === 'A').length;
  const bTierCount = scoredArticles.filter(a => a.tier === 'B').length;
  const usedCount = scoredArticles.filter(a => a.isUsed).length;

  // 4. 读取 W39 (首次试发) 与 W40 (下周常规) 生产状态
  const w39StatePath = path.join(PROJECT_ROOT, 'issues', 'issue-2026-w39', 'production_state.json');
  let w39State = {};
  if (fs.existsSync(w39StatePath)) {
    try {
      w39State = JSON.parse(fs.readFileSync(w39StatePath, 'utf8'));
    } catch {}
  }

  const w40StatePath = path.join(PROJECT_ROOT, 'issues', 'issue-2026-w40', 'production_state.json');
  let w40State = {};
  if (fs.existsSync(w40StatePath)) {
    try {
      w40State = JSON.parse(fs.readFileSync(w40StatePath, 'utf8'));
    } catch {}
  }

  return {
    timestamp: now.toISOString(),
    scheduler: {
      loaded: launchdLoaded,
      serviceLabel: 'com.weekly.fetch_commentaries',
      status: schedulerStatus,
      statusLabel: schedulerStatusLabel,
      cadence: '每日 2 次 (09:30、18:30)',
      scheduleDescription: '每天上午 09:30 与傍晚 18:30 定时抓取，兼顾早晚新评，轻量低负载',
      lastCrawlTime: lastCrawlTimeStr,
      minutesSinceLastCrawl,
      nextScheduledTime,
      lastLogSnippet,
    },
    intakeStats: {
      totalArticles: db.totalArticles || 0,
      totalFullText: db.fullTextArticles || 0,
      thisWeekTotal: scoredArticles.length,
      thisWeekFullText: thisWeekFullText.length,
      thisWeekMetadataOnly: scoredArticles.length - thisWeekFullText.length,
      sTierCount,
      aTierCount,
      bTierCount,
      usedCount,
      activeSources: (db.sourceStats || []).filter(s => !s.last_error && (s.total_items > 0 || s.count > 0)).length,
      totalSources: (db.sourceStats || []).length,
    },
    thisWeekArticles: scoredArticles.slice(0, 60),
    currentIssue: {
      issueId: 'issue-2026-w39',
      attribute: '首次试发件 (Trial Release)',
      attributeDesc: '已定版发布，供周四打印与教学试发实测，收集版面与口语语体反馈',
      status: 'published',
      statusLabel: '已发布',
      dateWindow: '2026年9月第4周（09.21-09.27）',
      totalPages: 47,
      pdfPath: '/issues/issue-2026-w39/issue-2026-w39.pdf',
      splits: {
        retellings: '/issues/issue-2026-w39/issue-2026-w39-复述.pdf',
        commentaries: '/issues/issue-2026-w39/issue-2026-w39-评论.pdf',
        excerpts: '/issues/issue-2026-w39/issue-2026-w39-原文拆解与积累.pdf',
      },
      reviewSiteUrl: '/review/issues/issue-2026-w39/index.html',
    },
    nextIssue: {
      issueId: 'issue-2026-w40',
      attribute: '常规周生产 (Regular Weekly Cadence)',
      cadenceRule: '每周四 20:00 资料截止 | 每周五 10:00 发放 | 回望连续 7 天',
      cutoffDeadline: '2026-10-01 20:00 (下周四)',
      deliveryTime: '2026-10-02 10:00 (下周五)',
      stage: 'prep',
      stageClassification: 'waiting_for_schedule',
      stageClassificationLabel: '等待计划时间（周内正常采集备料中）',
      waitingOn: '等待到达资料截止时点 (2026-10-01 20:00)',
      actionNeeded: '当前无须人工干预。请于 10月1日晚 或 10月2日晨 进入工作台审阅选题与定版。今天重点实测 W39 试发件。',
      stages: [
        { name: '1. 采集与备料', status: 'done', note: '每天2次智能优选入库中' },
        { name: '2. 选题与核验', status: 'waiting_for_schedule', note: '待 10月1日 20:00 截止后触发' },
        { name: '3. 文本采编', status: 'pending', note: '待选题确定后由 Agent 编写' },
        { name: '4. 漫画配图', status: 'pending', note: '待采编完成后由 Agent 生成' },
        { name: '5. 终审定版', status: 'pending', note: '教师审阅确认' },
        { name: '6. 原子构建', status: 'pending', note: '全门禁 47 页原子构建' },
        { name: '7. 归档发布', status: 'pending', note: '静态站点增量发布' },
      ],
    },
    divisionOfLabor: {
      automated: [
        { task: '新闻与评论定时采集', desc: 'macOS launchd 每天 2 次（09:30、18:30）轻量轮询 11 路权威信源并原子写入本地 JSON 库', behavior: '关机暂停，开机自启；休眠唤醒后 launchd 会自动补跑最近一次错过的任务' },
        { task: '智能优选与口语打分 (0~100分)', desc: '按正文完整度、高中口语契合度、叙事动作性、思辨争议度自动量化打分，S/A级排到最前', behavior: '全自动打分与分类推荐' },
        { task: '长文质量防退化与往期防重', desc: '若外部源站发生抓取降级或短文替换，自动锁定保留既有完整正文；已用文章自动扣分沉底', behavior: '全自动拦截与标记' },
        { task: '周内候选池动态维护', desc: '按自然周窗口动态归一化 URL、识别去重，并打标往期已用记录', behavior: '全自动维护' },
      ],
      humanAgentCollab: [
        { task: '选题核验与文稿编写 (21篇)', desc: '到达周四截止点后，由 Agent 从排名前列的 S/A 级优质素材中，按照高中生口语标准编写 9 复述 + 6 评论 + 6 摘录', behavior: '需在会话中发起或通过工作台触发唤醒，会话级 Agent 不会在无提示下后台自发创作' },
        { task: '动作漫画配图 (9幅)', desc: '依据复述事实生成 3:1 横排三格/四格动作叙事插画', behavior: '由 Agent 调用配图工具生成，自动放入 illustrations/' },
        { task: '门禁校验与原子排版', desc: '执行 weekly_runner.py build，自动化验证信源原段 100% 连续匹配、47 物理页数守恒与实体事实防伪', behavior: '脚本自动执行，出任何差错立即红灯中断并高亮原因' },
        { task: '终审定版与正式出刊', desc: '周五上午教师在工作台核验大方向，一键确认发布并导出审阅站与可打印 PDF', behavior: '教师把关确认，保障教学责任' },
      ]
    }
  };
}

/**
 * 读取单个信源原始 JSON 正文详情
 */
export async function getArticleDetail(id) {
  const safeId = path.basename(id);
  const rawPath = path.join(__dirname, 'data', 'commentaries', 'raw', `${safeId}.json`);
  if (fs.existsSync(rawPath)) {
    try {
      return JSON.parse(fs.readFileSync(rawPath, 'utf8'));
    } catch (e) {
      return { error: 'Failed to read article JSON: ' + e.message };
    }
  }
  return null;
}

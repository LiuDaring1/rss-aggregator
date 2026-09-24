import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '..');

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

  // 判断状态：若大于 180 分钟 (3小时) 则判定为过期
  let schedulerStatus = 'active';
  let schedulerStatusLabel = '调度服务运行正常 (活跃)';
  if (!launchdLoaded) {
    schedulerStatus = 'paused';
    schedulerStatusLabel = '系统常驻服务未加载';
  } else if (minutesSinceLastCrawl !== null && minutesSinceLastCrawl > 180) {
    schedulerStatus = 'stale';
    schedulerStatusLabel = '状态过期，需检查 (上次成功距今已超过3小时)';
  }

  const nextScheduledTime = lastCrawlDate ? new Date(lastCrawlDate.getTime() + 3600 * 1000).toISOString() : null;

  // 2. 本周新增报道统计 (以 2026-09-21 零点为当前周起始)
  const articles = Object.values(db.articles || {});
  const thisWeekArticles = articles.filter(a => {
    const pub = a.publishedAt || a.date || '';
    return pub >= '2026-09-21';
  });
  thisWeekArticles.sort((a, b) => (b.publishedAt || b.date || '').localeCompare(a.publishedAt || a.date || ''));

  const thisWeekFullText = thisWeekArticles.filter(a => a.hasFullText);

  // 3. 读取 W39 (首次试发) 与 W40 (下周常规) 生产状态
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
      intervalMinutes: 60,
      lastCrawlTime: lastCrawlTimeStr,
      minutesSinceLastCrawl,
      nextScheduledTime,
      lastLogSnippet,
    },
    intakeStats: {
      totalArticles: db.totalArticles || 0,
      totalFullText: db.fullTextArticles || 0,
      thisWeekTotal: thisWeekArticles.length,
      thisWeekFullText: thisWeekFullText.length,
      thisWeekMetadataOnly: thisWeekArticles.length - thisWeekFullText.length,
      activeSources: (db.sourceStats || []).filter(s => !s.last_error && (s.total_items > 0 || s.count > 0)).length,
      totalSources: (db.sourceStats || []).length,
    },
    thisWeekArticles: thisWeekArticles.slice(0, 50).map(a => ({
      id: a.id,
      title: a.title,
      source: a.source || a.media || a.sourceName || '时评信源',
      publishedAt: a.publishedAt || a.date || '未知',
      hasFullText: !!a.hasFullText,
      textType: a.textType || (a.hasFullText ? 'full_text' : 'metadata_only'),
      summary: a.summary || (a.content ? a.content.slice(0, 140) + '...' : '暂无摘要'),
      content: a.content || '',
      url: a.url || a.sourceUrl || '#',
    })),
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
        { name: '1. 采集与备料', status: 'done', note: '上游定时采集持续入库中' },
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
        { task: '新闻与评论定时采集', desc: 'macOS launchd 守护进程每小时自动轮询 11 路权威信源并原子写入本地 JSON 库', behavior: '关机暂停，开机自启；休眠唤醒后 launchd 会自动补跑最近一次错过的任务' },
        { task: '长文质量防退化', desc: '若外部源站发生抓取降级或短文替换，自动锁定保留既有完整正文，打标 degraded 警告', behavior: '全自动拦截' },
        { task: '周内候选池动态扫描', desc: '按自然周窗口动态归一化 URL、识别去重，并打标往期已用记录', behavior: '全自动维护' },
      ],
      humanAgentCollab: [
        { task: '选题核验与文稿编写 (21篇)', desc: '到达周四截止点后，由 Agent 按照高中生口语标准编写 9 复述 + 6 评论 + 6 摘录', behavior: '需在会话中发起或通过工作台触发唤醒，会话级 Agent 不会在无提示下后台自发创作' },
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


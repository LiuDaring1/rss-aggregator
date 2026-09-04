/* 信息聚合站 — 前端逻辑 v0.2（评论频道 + 暖文雷达） */
(() => {
  const state = {
    items: [],
    sources: [],
    enabled: new Set(), // 勾选的源 id（多选过滤）
    solo: null, // 单独查看的源 id；null = 显示全部勾选源
    hours: 168, // 默认近 7 天（初始化时从下拉框读取）
    health: new Map(), // 源 id -> { ok, error, count, checkedAt, newest }
    view: 'feed', // feed | topics | wenwen
    mainView: 'comment', // comment | wenwen
    commentView: 'feed', // 评论频道内子视图
    wwState: 'all', // 暖文候选过滤：all | pending | kept | ignored
    wwUse: '', wwMotif: '', wwBehavior: '',
    wwSub: 'cand', // cand | lib | reg
    wwLibPage: 1,
    wwEvents: [], // 候选事件本地缓存（保留/忽略即时更新用）
  };

  const MOTIFS = ['水域救人', '火灾救援', '紧急医疗救助', '道路事故救助', '困境学子成长', '长期公益助学', '公益食堂或爱心厨房', '适老服务', '技能助人', '无障碍与助残', '邻里长期守望', '职业岗位上的额外担当', '乡村教育', '社区互助', '诚信与归还', '规则给予善意回应', '其他'];
  const BEHAVIORS = ['英勇救人', '助人为乐', '诚实守信', '敬业奉献', '自立自强', '孝老爱亲', '温情互助', '其他'];

  const el = {
    range: document.getElementById('range'),
    refresh: document.getElementById('refresh'),
    status: document.getElementById('status'),
    items: document.getElementById('items'),
    sourceList: document.getElementById('source-list'),
    sourceSummary: document.getElementById('source-summary'),
    soloBar: document.getElementById('solo-bar'),
    soloText: document.getElementById('solo-text'),
    soloExit: document.getElementById('solo-exit'),
    checkBtn: document.getElementById('check-btn'),
    checkResult: document.getElementById('check-result'),
    tabComment: document.getElementById('tab-comment'),
    tabWenwenMain: document.getElementById('tab-wenwen-main'),
    commentSubtabs: document.getElementById('comment-subtabs'),
    tabFeed: document.getElementById('tab-feed'),
    tabTopics: document.getElementById('tab-topics'),
    sidebarComment: document.getElementById('sidebar-comment'),
    sidebarWenwen: document.getElementById('sidebar-wenwen'),
    wwSideStats: document.getElementById('ww-side-stats'),
    feedView: document.getElementById('feed-view'),
    topicsView: document.getElementById('topics-view'),
    topicsMeta: document.getElementById('topics-meta'),
    topicsRegen: document.getElementById('topics-regen'),
    topicsList: document.getElementById('topics-list'),
    wenwenView: document.getElementById('wenwen-view'),
    wenwenMeta: document.getElementById('wenwen-meta'),
    wenwenCollect: document.getElementById('wenwen-collect'),
    wenwenAnalyze: document.getElementById('wenwen-analyze'),
    wwTabCand: document.getElementById('ww-tab-cand'),
    wwTabLib: document.getElementById('ww-tab-lib'),
    wwTabReg: document.getElementById('ww-tab-reg'),
    wwStateFilters: document.getElementById('ww-state-filters'),
    wwCandidates: document.getElementById('ww-candidates'),
    wwRegistry: document.getElementById('ww-registry'),
    wwFilterUse: document.getElementById('ww-filter-use'),
    wwFilterMotif: document.getElementById('ww-filter-motif'),
    wwFilterBehavior: document.getElementById('ww-filter-behavior'),
    wwLibrary: document.getElementById('ww-library'),
    wwLibHealth: document.getElementById('ww-lib-health'),
    wwLibList: document.getElementById('ww-lib-list'),
    wwLibPage: document.getElementById('ww-lib-page'),
    wwLibQ: document.getElementById('ww-lib-q'),
    wwLibMedia: document.getElementById('ww-lib-media'),
    wwLibDateFrom: document.getElementById('ww-lib-datefrom'),
    wwLibDateTo: document.getElementById('ww-lib-dateto'),
    wwLibHasContent: document.getElementById('ww-lib-hascontent'),
    wwLibState: document.getElementById('ww-lib-state'),
    wwLibSearch: document.getElementById('ww-lib-search'),
    wwLibPrev: document.getElementById('ww-lib-prev'),
    wwLibNext: document.getElementById('ww-lib-next'),
  };

  /* ---------- 工具 ---------- */

  function fmtTime(iso) {
    const d = new Date(iso);
    const now = Date.now();
    const diff = now - d.getTime();
    if (diff < 60 * 1000) return '刚刚';
    if (diff < 3600 * 1000) return `${Math.floor(diff / 60000)} 分钟前`;
    if (diff < 24 * 3600 * 1000) return `${Math.floor(diff / 3600000)} 小时前`;
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  function fmtAge(iso) {
    const d = new Date(iso);
    const diff = Date.now() - d.getTime();
    if (diff < 60 * 1000) return '刚刚';
    if (diff < 3600 * 1000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 24 * 3600 * 1000) return `${Math.floor(diff / 3600000)}小时前`;
    if (diff < 30 * 24 * 3600 * 1000) return `${Math.floor(diff / 86400000)}天前`;
    const pad = (n) => String(n).padStart(2, '0');
    return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }

  function categoryColor(name) {
    let h = 0;
    for (const ch of String(name)) h = (h * 31 + ch.codePointAt(0)) % 360;
    return `hsl(${h}, 55%, 45%)`;
  }

  /* ---------- 评论频道数据 ---------- */

  async function loadSources() {
    const res = await fetch('/api/sources');
    const data = await res.json();
    state.sources = data.sources;
    state.enabled = new Set(state.sources.map((s) => s.id));
    for (const s of state.sources) {
      if (s.status) state.health.set(s.id, { ...s.status, newest: s.status.newestItem });
    }
    renderSources();
  }

  async function refreshStats() {
    try {
      const res = await fetch('/api/sources');
      const data = await res.json();
      let changed = false;
      for (const s of data.sources) {
        if (s.status) {
          state.health.set(s.id, { ...s.status, newest: s.status.newestItem });
          changed = true;
        }
      }
      if (changed) renderSources();
    } catch {
      /* 状态刷新失败不影响主功能 */
    }
  }

  async function loadItems() {
    el.status.textContent = '加载中…';
    el.status.className = 'status loading';
    try {
      const ids = state.solo ? state.solo : [...state.enabled].join(',');
      const res = await fetch(`/api/items?hours=${state.hours}&source=${ids}&limit=300`);
      const data = await res.json();
      state.items = data.items;
      el.status.textContent = `共 ${data.total} 条 · 更新于 ${fmtTime(data.updatedAt)}`;
      el.status.className = 'status';
      renderItems();
      refreshStats();
    } catch (e) {
      el.status.textContent = `加载失败：${e.message}（后端服务是否已启动？）`;
      el.status.className = 'status error';
    }
  }

  /* ---------- 视图切换：评论频道 / 暖文雷达（并行两大信源） ---------- */

  function setMain(main) {
    state.mainView = main;
    el.tabComment.classList.toggle('active', main === 'comment');
    el.tabWenwenMain.classList.toggle('active', main === 'wenwen');
    el.commentSubtabs.hidden = main !== 'comment';
    el.sidebarComment.hidden = main !== 'comment';
    el.sidebarWenwen.hidden = main !== 'wenwen';
    if (main === 'comment') setView(state.commentView || 'feed');
    else setView('wenwen');
  }

  function setView(view) {
    state.view = view;
    if (view !== 'wenwen') state.commentView = view;
    el.tabFeed.classList.toggle('active', view === 'feed');
    el.tabTopics.classList.toggle('active', view === 'topics');
    el.feedView.hidden = view !== 'feed';
    el.topicsView.hidden = view !== 'topics';
    el.wenwenView.hidden = view !== 'wenwen';
    if (view === 'topics') loadTopics(false);
    if (view === 'wenwen') loadWenwenCandidates();
  }

  /* ---------- AI 热点归纳 ---------- */

  async function loadTopics(force) {
    el.topicsRegen.disabled = true;
    if (force || !el.topicsList.dataset.loaded) {
      el.topicsList.innerHTML = '';
      el.topicsMeta.textContent = 'AI 正在归纳近期热点…（首次约 2–4 分钟，之后 30 分钟内秒开）';
      el.topicsMeta.className = 'topics-meta running';
    }
    try {
      const res = await fetch(`/api/topics?hours=${state.hours}${force ? '&force=1' : ''}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
      renderTopics(data);
    } catch (e) {
      el.topicsMeta.textContent = `归纳失败：${e.message}`;
      el.topicsMeta.className = 'topics-meta err';
    } finally {
      el.topicsRegen.disabled = false;
    }
  }

  function renderTopics(data) {
    el.topicsList.dataset.loaded = '1';
    const gen = data.updatedAt ? fmtTime(data.updatedAt) : '';
    el.topicsMeta.textContent =
      `基于近 ${Math.round(data.hours / 24 * 10) / 10} 天 ${data.articleCount} 篇文章 · ` +
      `${data.mediaCount || 0} 家媒体 · 模型 ${data.model || 'GLM'} · ` +
      (data.cached ? `缓存生成于 ${gen}` : `生成于 ${gen}（缓存 30 分钟）`);
    el.topicsMeta.className = 'topics-meta';

    if (!data.topics || !data.topics.length) {
      el.topicsList.innerHTML =
        '<div class="empty">这个时间范围内文章太少，AI 还归纳不出热点。<br>试试把顶部时间范围调大，或点「重新归纳」。</div>';
      return;
    }

    el.topicsList.innerHTML = '';
    for (const t of data.topics) {
      const card = document.createElement('article');
      card.className = 'topic-card';

      const head = document.createElement('div');
      head.className = 'topic-head';
      const heat = document.createElement('span');
      heat.className = 'heat heat-' + t.heat;
      heat.textContent = '🔥'.repeat(Math.min(t.heat, 5));
      heat.title = `关注度 ${t.heat}/5`;
      const title = document.createElement('h3');
      title.textContent = t.title;
      head.append(heat, title);
      card.appendChild(head);

      if (t.outlets && t.outlets.length) {
        const outlets = document.createElement('div');
        outlets.className = 'topic-outlets';
        outlets.textContent = `${t.outlets.length} 家媒体：${t.outlets.join('、')}`;
        card.appendChild(outlets);
      }

      if (t.angle) {
        const angle = document.createElement('p');
        angle.className = 'topic-angle';
        angle.textContent = t.angle;
        card.appendChild(angle);
      }

      const links = (t.articles || []).filter((a) => a.link);
      if (links.length) {
        const ul = document.createElement('ul');
        ul.className = 'topic-articles';
        for (const a of links) {
          const li = document.createElement('li');
          const src = document.createElement('span');
          src.className = 'ta-src';
          src.textContent = a.source;
          const link = document.createElement('a');
          link.href = a.link;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          link.textContent = a.title;
          li.append(src, link);
          ul.appendChild(li);
        }
        card.appendChild(ul);
      }

      el.topicsList.appendChild(card);
    }
  }

  /* ---------- 暖文雷达 ---------- */

  const USE_CLASS = {
    完整加工: 'use-full', 优先补搜: 'use-search', 短复述或案例: 'use-short',
    继续观察: 'use-watch', 暂时不用: 'use-skip',
  };

  async function loadWenwenCandidates() {
    el.wenwenMeta.textContent = '加载中…';
    el.wenwenMeta.className = 'topics-meta running';
    try {
      const params = new URLSearchParams({ state: state.wwState, limit: '100' });
      if (state.wwUse) params.set('use', state.wwUse);
      if (state.wwMotif) params.set('motif', state.wwMotif);
      if (state.wwBehavior) params.set('behavior', state.wwBehavior);
      const res = await fetch(`/wenwen/api/candidates?${params}`);
      const data = await res.json();
      state.wwEvents = data.events;
      renderWenwenCandidates(data);
    } catch (e) {
      el.wenwenMeta.textContent = `加载失败：${e.message}`;
      el.wenwenMeta.className = 'topics-meta err';
    }
  }

  function fillSelect(sel, options, label) {
    sel.innerHTML = `<option value="">${label}</option>` + options.map((o) => `<option value="${o}">${o}</option>`).join('');
    sel.value = state.wwUse && label === '全部用途' ? state.wwUse : sel.value;
  }

  function renderWenwenCandidates(data) {
    const s = data.summary || {};
    el.wenwenMeta.textContent =
      `已采集案例 ${s.articleCount ?? '—'} 篇 · 合并为 ${s.eventCount ?? '—'} 个事件 · ` +
      `已分析 ${s.analyzedCount ?? '—'} · 信源 ${s.registryCount ?? '—'} 家（已接入 ${s.connectedCount ?? 0}） · ` +
      `上次采集 ${s.lastCollectAt ? fmtTime(s.lastCollectAt) : '—'}`;
    el.wenwenMeta.className = 'topics-meta' + (s.filterWarning ? ' err' : '');
    if (s.filterWarning) el.wenwenMeta.textContent += ` · ⚠️ ${s.filterWarning}`;

    el.wwSideStats.innerHTML =
      `已采集案例 <b>${s.articleCount ?? '—'}</b> 篇<br>` +
      `合并事件 <b>${s.eventCount ?? '—'}</b> 个<br>` +
      `已分析 <b>${s.analyzedCount ?? '—'}</b> 个<br>` +
      `登记信源 <b>${s.registryCount ?? '—'}</b> 家<br>` +
      `已接入采集 <b>${s.connectedCount ?? 0}</b> 家`;

    // 筛选下拉（只填一次）
    if (!el.wwFilterUse.options.length) {
      fillSelect(el.wwFilterUse, data.uses || [], '全部用途');
      fillSelect(el.wwFilterMotif, MOTIFS, '全部母题');
      fillSelect(el.wwFilterBehavior, BEHAVIORS, '全部行为');
      el.wwFilterUse.value = state.wwUse;
      el.wwFilterMotif.value = state.wwMotif;
      el.wwFilterBehavior.value = state.wwBehavior;
    }

    el.wwCandidates.innerHTML = '';
    if (!data.events.length) {
      el.wwCandidates.innerHTML =
        '<div class="empty">当前筛选下没有候选事件。可点上方「⬇ 采集新案例」或调整筛选条件。</div>';
      return;
    }
    for (const ev of data.events) renderWenwenCard(ev);
  }

  function renderWenwenCard(ev) {
    const a = ev.analysis;
    const card = document.createElement('article');
    card.className = 'ww-card' + (ev.userStatus === 'ignored' ? ' ww-ignored' : '') + (ev.userStatus === 'kept' ? ' ww-kept' : '');
    card.dataset.evId = ev.id;

    const head = document.createElement('div');
    head.className = 'topic-head';
    const use = document.createElement('span');
    use.className = 'ww-use ' + (USE_CLASS[a?.suggestedUse] || '');
    use.textContent = a?.suggestedUse || '待分析';
    use.title = '建议用途 = 材料价值 × 信息成熟度（代码组合）';
    const title = document.createElement('h3');
    title.textContent = ev.title;
    head.append(use, title);
    card.appendChild(head);

    const meta = document.createElement('div');
    meta.className = 'ww-meta';
    if (ev.userStatus === 'kept') meta.append(Object.assign(document.createElement('span'), { textContent: '⭐ 已保留' }));
    if (ev.userStatus === 'ignored') meta.append(Object.assign(document.createElement('span'), { textContent: '已忽略' }));
    if (a) {
      const mv = document.createElement('span');
      mv.textContent = `价值 ${a.materialValue} · ${a.infoMaturity}`;
      mv.title = `材料价值 ${a.materialValue} / 信息成熟度 ${a.infoMaturity}`;
      meta.append(mv);
    }
    const src = document.createElement('span');
    src.textContent =
      `${ev.mediaList.length} 家媒体 · ${ev.articleCount} 篇 · 获奖 ${(ev.firstAt || '').slice(0, 10)}` +
      (ev.category ? ` · ${ev.category}` : '');
    meta.append(src);
    card.appendChild(meta);

    if (a) {
      const one = document.createElement('p');
      one.className = 'ww-oneline';
      one.textContent = a.oneLine;
      card.appendChild(one);

      if (a.distinctiveWhy) {
        const dw = document.createElement('p');
        dw.className = 'ww-distinct';
        dw.textContent = '特别在哪：' + a.distinctiveWhy;
        card.appendChild(dw);
      }

      // 细节默认折叠，降低浏览成本
      const details = document.createElement('details');
      const sum = document.createElement('summary');
      sum.textContent = '事实与判断';
      details.appendChild(sum);
      const facts = document.createElement('dl');
      facts.className = 'ww-facts';
      for (const [k, v] of [['人物', a.people], ['行动', a.action], ['处境/成本', a.difficulty], ['记忆点', a.detail], ['结果', a.result]]) {
        if (!v) continue;
        facts.append(Object.assign(document.createElement('dt'), { textContent: k }));
        facts.append(Object.assign(document.createElement('dd'), { textContent: v }));
      }
      details.appendChild(facts);
      if (a.discussionAngles?.length) {
        const angles = document.createElement('div');
        angles.className = 'ww-angles';
        angles.append(Object.assign(document.createElement('b'), { textContent: '讨论角度：' }));
        for (const ang of a.discussionAngles) angles.append(Object.assign(document.createElement('p'), { textContent: '· ' + ang }));
        details.appendChild(angles);
      }
      if (a.missingFacts?.length) {
        const miss = document.createElement('div');
        miss.className = 'ww-missing';
        miss.append(Object.assign(document.createElement('b'), { textContent: '信息缺口：' }));
        for (const m of a.missingFacts) miss.append(Object.assign(document.createElement('p'), { textContent: `· ${m.missing}（${m.why}）` }));
        details.appendChild(miss);
      }
      const reason = document.createElement('p');
      reason.className = 'ww-reason';
      reason.textContent = '判断：' + a.reason + (a.needMoreSearch ? '（建议补充搜索）' : '');
      details.appendChild(reason);
      card.appendChild(details);
    } else {
      const wait = document.createElement('p');
      wait.className = 'ww-reason';
      wait.textContent = '尚未 AI 分析：调度器每 20 分钟自动补充，或点上方「✨ AI 分析待定事件」加急。';
      card.appendChild(wait);
    }

    const actions = document.createElement('div');
    actions.className = 'ww-actions';
    const keepBtn = document.createElement('button');
    keepBtn.textContent = ev.userStatus === 'kept' ? '★ 已保留' : '☆ 保留';
    keepBtn.className = ev.userStatus === 'kept' ? 'on' : '';
    keepBtn.addEventListener('click', () => wenwenFeedback(ev.id, ev.userStatus === 'kept' ? 'reset' : 'keep'));
    const ignoreBtn = document.createElement('button');
    ignoreBtn.textContent = ev.userStatus === 'ignored' ? '已忽略' : '忽略';
    ignoreBtn.className = ev.userStatus === 'ignored' ? 'on' : '';
    ignoreBtn.addEventListener('click', () => wenwenFeedback(ev.id, ev.userStatus === 'ignored' ? 'reset' : 'ignore'));
    actions.append(keepBtn, ignoreBtn);
    card.appendChild(actions);

    // 媒体报道列表（含天天正能量收录页链接）
    if (ev.articles?.length) {
      const ul = document.createElement('ul');
      ul.className = 'topic-articles';
      for (const art of ev.articles.slice(0, 4)) {
        const li = document.createElement('li');
        const src = document.createElement('span');
        src.className = 'ta-src';
        src.textContent = art.media || '未知媒体';
        const link = document.createElement('a');
        link.href = art.url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = art.title;
        li.append(src, link);
        ul.appendChild(li);
      }
      card.appendChild(ul);
    }

    el.wwCandidates.appendChild(card);
    return card;
  }

  /** 保留/忽略：就地更新卡片，不整页重载、不重置滚动位置 */
  async function wenwenFeedback(id, action) {
    try {
      const res = await fetch(`/wenwen/api/events/${encodeURIComponent(id)}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
      // 就地更新：本地缓存 + 替换该卡片节点
      const ev = state.wwEvents.find((e) => e.id === id);
      if (ev) {
        ev.userStatus = data.userStatus;
        const oldCard = el.wwCandidates.querySelector(`.ww-card[data-ev-id="${CSS.escape(id)}"]`);
        if (oldCard) {
          const newCard = renderWenwenCard(ev);
          oldCard.replaceWith(newCard);
        }
      }
    } catch (e) {
      el.wenwenMeta.textContent = `操作失败：${e.message}`;
      el.wenwenMeta.className = 'topics-meta err';
    }
  }

  /* ---------- 暖文雷达：本地资料库 ---------- */

  async function loadWenwenLibrary() {
    el.wwLibList.innerHTML = '<div class="empty">加载中…</div>';
    try {
      const healthRes = await fetch('/wenwen/api/data-health');
      const health = await healthRes.json();
      el.wwLibHealth.innerHTML =
        `<b>数据健康</b>：本地留档 ${health.localSnapshotCount}/${health.rawArticleCount} 篇` +
        ` · 缺正文 ${health.missingContent} · 正文过短 ${health.tooShort} · 缺媒体 ${health.missingMedia}` +
        ` · 缺日期 ${health.missingDate} · 测试数据 ${health.testArticles}（已排除）` +
        ` · 精确去重 ${health.dedupedCount} 次` +
        ` · 解析失败 ${health.parseFailures}` +
        `<br><span class="ww-lib-dir">数据目录：${health.dataDir} · 最近写入 ${health.lastWriteAt ? fmtTime(health.lastWriteAt) : '—'} · <a href="/wenwen/api/export?format=md" download="暖文报告.md">导出 Markdown 报告</a> · <a href="/wenwen/api/export?format=json" download="暖文数据备份.json">导出 JSON 备份</a></span>`;

      const p = new URLSearchParams({
        q: el.wwLibQ.value.trim(),
        media: el.wwLibMedia.value.trim(),
        dateFrom: el.wwLibDateFrom.value,
        dateTo: el.wwLibDateTo.value,
        hasContent: el.wwLibHasContent.value,
        state: el.wwLibState.value,
        page: String(state.wwLibPage),
        pageSize: '30',
      });
      const res = await fetch(`/wenwen/api/library?${p}`);
      const data = await res.json();
      renderLibrary(data);
    } catch (e) {
      el.wwLibList.innerHTML = `<div class="empty">加载失败：${e.message}</div>`;
    }
  }

  function renderLibrary(data) {
    el.wwLibPage.textContent = `${data.page} / ${Math.max(1, Math.ceil(data.total / data.pageSize))} 页 · 共 ${data.total} 篇`;
    el.wwLibList.innerHTML = '';
    if (!data.articles.length) {
      el.wwLibList.innerHTML = '<div class="empty">没有匹配的文章。</div>';
      return;
    }
    const table = document.createElement('table');
    table.className = 'ww-reg-table';
    table.innerHTML =
      '<thead><tr><th>标题</th><th>媒体</th><th>获奖日期</th><th>正文</th><th>状态</th><th></th></tr></thead>';
    const tbody = document.createElement('tbody');
    for (const art of data.articles) {
      const tr = document.createElement('tr');
      const td1 = document.createElement('td');
      td1.textContent = art.title;
      td1.title = art.eventTitle || '';
      const td2 = document.createElement('td');
      td2.textContent = art.media || '—';
      const td3 = document.createElement('td');
      td3.textContent = art.awardDate || '—';
      const td4 = document.createElement('td');
      td4.textContent = art.hasContent ? `${art.contentLength} 字` : '无';
      const td5 = document.createElement('td');
      td5.textContent = art.userStatus === 'kept' ? '⭐' : art.userStatus === 'ignored' ? '忽略' : '待定';
      const td6 = document.createElement('td');
      const readBtn = document.createElement('button');
      readBtn.className = 'ww-lib-read';
      readBtn.textContent = '阅读';
      readBtn.addEventListener('click', () => toggleArticleReader(tr, art));
      td6.appendChild(readBtn);
      tr.append(td1, td2, td3, td4, td5, td6);
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    el.wwLibList.appendChild(table);
  }

  async function toggleArticleReader(row, art) {
    const existing = row.nextElementSibling;
    if (existing?.classList?.contains('ww-reader-row')) {
      existing.remove();
      return;
    }
    const readerRow = document.createElement('tr');
    readerRow.className = 'ww-reader-row';
    const td = document.createElement('td');
    td.colSpan = 6;
    td.textContent = '加载本地全文…';
    readerRow.appendChild(td);
    row.after(readerRow);
    try {
      const res = await fetch(`/wenwen/api/articles/${encodeURIComponent(art.id)}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
      td.innerHTML = '';
      const head = document.createElement('div');
      head.className = 'ww-full-head';
      head.innerHTML =
        `<span class="ta-src">${data.media || '未知媒体'}</span>` +
        `<span class="ww-full-date">获奖 ${data.awardDate || '—'} · 抓取 ${fmtTime(data.fetchedAt)} · ${data.contentLength} 字</span>` +
        `<a href="${data.ttzlUrl}" target="_blank" rel="noopener">天天正能量收录页 ↗</a>` +
        (data.sourceUrl ? `<a href="${data.sourceUrl}" target="_blank" rel="noopener">原始媒体报道 ↗</a>` : '');
      const title = document.createElement('div');
      title.className = 'ww-full-title';
      title.textContent = data.title;
      const body = document.createElement('div');
      body.className = 'ww-full-body';
      body.style.maxHeight = '420px';
      body.textContent = data.content || '（本地无正文）';
      td.append(head, title, body);
      if (data.relatedArticles?.length) {
        const rel = document.createElement('div');
        rel.className = 'ww-reason';
        rel.textContent = '同事件其他报道：' + data.relatedArticles.map((r) => `${r.media}《${r.title}》`).join('；');
        td.append(rel);
      }
    } catch (e) {
      td.textContent = `加载失败：${e.message}`;
    }
  }

  /* ---------- 暖文雷达：信源覆盖 ---------- */

  async function loadWenwenRegistry() {
    el.wwRegistry.hidden = false;
    el.wwCandidates.hidden = true;
    el.wwLibrary.hidden = true;
    el.wwRegistry.innerHTML = '<div class="empty">加载中…</div>';
    try {
      const res = await fetch('/wenwen/api/registry');
      const data = await res.json();
      const byStatus = data.byStatus || {};
      const head = `<div class="ww-reg-summary">媒体主体共 <b>${data.total}</b> 家（由案例媒体名规范化合并而来）。探测状态分布：` +
        Object.entries(byStatus).map(([k, v]) => `${k} ${v}`).join(' · ') +
        '。点「探测信源」自动检查官网连通性与 RSS/Sitemap 通道（每轮最多 20 家）。</div>' +
        '<div style="margin-bottom:10px"><button id="ww-probe-btn">🔎 探测信源</button></div>';
      const rows = data.sources.map((s) => `
        <tr>
          <td>${s.name}${s.brands?.length ? `<div class="ww-reg-brands">品牌：${s.brands.join('、')}</div>` : ''}</td>
          <td>${(s.aliases || []).join('、')}</td>
          <td>${s.region || '—'}</td>
          <td>${s.homepage ? `<a href="${s.homepage}" target="_blank" rel="noopener">${s.homepage.replace(/^https?:\/\//, '').slice(0, 30)}</a>` : '—'}</td>
          <td>${s.probeStatus}${s.lastError ? `<div class="ww-reg-err">${s.lastError}</div>` : ''}</td>
          <td>${s.articleCount || 0}</td>
        </tr>`).join('');
      el.wwRegistry.innerHTML =
        head + `<table class="ww-reg-table"><thead><tr><th>媒体主体</th><th>原始名称/别名</th><th>地区</th><th>官网</th><th>探测状态</th><th>案例数</th></tr></thead><tbody>${rows}</tbody></table>`;
      const probeBtn = el.wwRegistry.querySelector('#ww-probe-btn');
      if (probeBtn) {
        probeBtn.addEventListener('click', async () => {
          probeBtn.disabled = true;
          probeBtn.textContent = '探测中…';
          try {
            const r = await fetch('/wenwen/api/probe', { method: 'POST' });
            const d = await r.json();
            probeBtn.textContent = `本轮探测 ${d.probed} 家`;
          } catch (e) {
            probeBtn.textContent = `探测失败：${e.message}`;
          }
          setTimeout(loadWenwenRegistry, 800);
        });
      }
    } catch (e) {
      el.wwRegistry.innerHTML = `<div class="empty">加载失败：${e.message}</div>`;
    }
  }

  /* ---------- 单独查看模式 ---------- */

  function setSolo(id) {
    state.solo = id;
    renderSoloBar();
    renderSources();
    loadItems();
  }

  function renderSoloBar() {
    const src = state.sources.find((s) => s.id === state.solo);
    if (src) {
      el.soloText.textContent = `正在单独查看：${src.name}`;
      el.soloBar.hidden = false;
    } else {
      el.soloBar.hidden = true;
    }
  }

  /* ---------- 渲染：侧栏源列表（按分类分组） ---------- */

  function toggleSource(id, on) {
    if (state.solo) state.solo = null;
    if (on) state.enabled.add(id);
    else state.enabled.delete(id);
  }

  function renderSources() {
    const enabledCount = state.enabled.size;
    el.sourceSummary.textContent = `${enabledCount}/${state.sources.length}`;
    el.sourceList.innerHTML = '';

    const groups = [];
    const byCat = new Map();
    for (const s of state.sources) {
      if (!byCat.has(s.category)) {
        const list = [];
        byCat.set(s.category, list);
        groups.push({ cat: s.category, sources: list });
      }
      byCat.get(s.category).push(s);
    }

    for (const g of groups) {
      const head = document.createElement('li');
      head.className = 'group-head';
      const gLabel = document.createElement('label');
      gLabel.className = 'cb-wrap';
      gLabel.title = '勾选/取消整个分类';
      const gCb = document.createElement('input');
      gCb.type = 'checkbox';
      const allOn = g.sources.every((s) => state.enabled.has(s.id));
      const anyOn = g.sources.some((s) => state.enabled.has(s.id));
      gCb.checked = allOn;
      gCb.indeterminate = anyOn && !allOn;
      gCb.addEventListener('change', () => {
        for (const s of g.sources) toggleSource(s.id, gCb.checked);
        renderSources();
        renderSoloBar();
        loadItems();
      });
      gLabel.appendChild(gCb);
      const gName = document.createElement('span');
      gName.className = 'group-name';
      gName.textContent = g.cat;
      gName.style.color = categoryColor(g.cat);
      gLabel.appendChild(gName);
      head.appendChild(gLabel);
      const gCount = document.createElement('span');
      gCount.className = 'group-count';
      gCount.textContent = `${g.sources.filter((s) => state.enabled.has(s.id)).length}/${g.sources.length}`;
      head.appendChild(gCount);
      el.sourceList.appendChild(head);

      for (const s of g.sources) {
        const li = document.createElement('li');
        li.className = state.solo === s.id ? 'solo' : '';

        const label = document.createElement('label');
        label.className = 'cb-wrap';
        label.title = state.solo === s.id ? '勾选将退出单独查看' : '勾选/取消该源';
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.checked = state.enabled.has(s.id);
        cb.addEventListener('change', () => {
          toggleSource(s.id, cb.checked);
          renderSources();
          renderSoloBar();
          loadItems();
        });
        label.appendChild(cb);

        const main = document.createElement('div');
        main.className = 'src-main';

        const row1 = document.createElement('div');
        row1.className = 'src-row1';
        const name = document.createElement('span');
        name.className = 'src-name';
        name.textContent = s.name;
        name.title = state.solo === s.id ? '点击返回全部' : '点击只看这个源';
        name.addEventListener('click', () => setSolo(state.solo === s.id ? null : s.id));
        row1.appendChild(name);
        main.appendChild(row1);

        const st = state.health.get(s.id);
        const meta = document.createElement('div');
        meta.className = 'src-meta';
        if (st) {
          const stDot = document.createElement('span');
          stDot.className = 'st-dot ' + (st.ok ? 'ok' : 'err');
          stDot.title = st.ok ? `连接正常 · 抓到 ${st.count} 条` : `连接异常：${st.error || '未知错误'}`;
          const stText = document.createElement('span');
          stText.textContent = st.ok ? '正常' : '异常';
          meta.append(stDot, stText);
          if (st.ok && st.newest) {
            const upd = document.createElement('span');
            upd.textContent = `· 更新 ${fmtAge(st.newest)}`;
            upd.title = `该源最新文章：${new Date(st.newest).toLocaleString('zh-CN')}`;
            meta.append(upd);
          }
        } else {
          meta.textContent = '状态未知';
        }
        main.appendChild(meta);

        li.append(label, main);
        el.sourceList.appendChild(li);
      }
    }
  }

  function renderItems() {
    if (!state.items.length) {
      el.items.innerHTML =
        '<div class="empty">当前时间范围内没有内容：源站最近可能未更新。<br>试试切换更大的时间范围，或点左侧「测试连接」确认源是否正常。</div>';
      return;
    }
    el.items.innerHTML = '';
    for (const it of state.items) {
      const card = document.createElement('article');
      card.className = 'card';

      const head = document.createElement('div');
      head.className = 'card-head';
      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.style.color = categoryColor(it.sourceCategory);
      badge.style.borderColor = categoryColor(it.sourceCategory);
      badge.textContent = it.sourceName;
      const time = document.createElement('time');
      time.textContent = fmtTime(it.pubDate);
      time.title = new Date(it.pubDate).toLocaleString('zh-CN');
      head.append(badge, time);

      const title = document.createElement('h3');
      const link = document.createElement('a');
      link.href = it.link;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = it.title;
      title.appendChild(link);

      const summary = document.createElement('p');
      summary.className = 'summary';
      summary.textContent = it.summary || '';

      card.append(head, title, summary);
      el.items.appendChild(card);
    }
  }

  /* ---------- 连接测试 ---------- */

  async function runCheck() {
    el.checkBtn.disabled = true;
    el.checkResult.textContent = '逐源重抓中…';
    el.checkResult.className = 'check-result running';
    const t0 = Date.now();
    try {
      const res = await fetch('/api/health?force=1');
      const data = await res.json();
      let okCount = 0;
      for (const r of data.sources) {
        const newest = (r.items || [])
          .map((i) => (i.pubDate ? new Date(i.pubDate).getTime() : 0))
          .reduce((m, t) => (t > m ? t : m), 0);
        state.health.set(r.id, {
          ok: r.ok, error: r.error, count: (r.items || []).length,
          checkedAt: new Date(r.at).toISOString(),
          newest: newest ? new Date(newest).toISOString() : null,
        });
        if (r.ok) okCount++;
      }
      const secs = ((Date.now() - t0) / 1000).toFixed(1);
      el.checkResult.textContent = `${okCount}/${data.sources.length} 正常 · ${secs}s`;
      el.checkResult.className = 'check-result ' + (okCount === data.sources.length ? 'all-ok' : 'some-err');
      renderSources();
    } catch (e) {
      el.checkResult.textContent = `检测失败：${e.message}`;
      el.checkResult.className = 'check-result some-err';
    } finally {
      el.checkBtn.disabled = false;
    }
  }

  /* ---------- 事件 ---------- */

  el.refresh.addEventListener('click', loadItems);
  el.range.addEventListener('change', () => {
    state.hours = Number(el.range.value);
    if (state.view === 'topics') loadTopics(true);
    else loadItems();
  });
  el.soloExit.addEventListener('click', () => setSolo(null));
  el.checkBtn.addEventListener('click', runCheck);
  el.tabComment.addEventListener('click', () => setMain('comment'));
  el.tabWenwenMain.addEventListener('click', () => setMain('wenwen'));
  el.topicsRegen.addEventListener('click', () => loadTopics(true));

  // 暖文雷达子视图
  function wwShow(sub) {
    state.wwSub = sub;
    el.wwTabCand.classList.toggle('active', sub === 'cand');
    el.wwTabLib.classList.toggle('active', sub === 'lib');
    el.wwTabReg.classList.toggle('active', sub === 'reg');
    el.wwCandidates.hidden = sub !== 'cand';
    el.wwLibrary.hidden = sub !== 'lib';
    el.wwRegistry.hidden = sub !== 'reg';
    if (sub === 'cand') loadWenwenCandidates();
    if (sub === 'lib') loadWenwenLibrary();
    if (sub === 'reg') loadWenwenRegistry();
  }
  el.wwTabCand.addEventListener('click', () => wwShow('cand'));
  el.wwTabLib.addEventListener('click', () => wwShow('lib'));
  el.wwTabReg.addEventListener('click', () => wwShow('reg'));

  for (const btn of el.wwStateFilters.querySelectorAll('button[data-state]')) {
    btn.addEventListener('click', () => {
      el.wwStateFilters.querySelectorAll('button').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.wwState = btn.dataset.state;
      loadWenwenCandidates();
    });
  }
  el.wwFilterUse.addEventListener('change', () => { state.wwUse = el.wwFilterUse.value; loadWenwenCandidates(); });
  el.wwFilterMotif.addEventListener('change', () => { state.wwMotif = el.wwFilterMotif.value; loadWenwenCandidates(); });
  el.wwFilterBehavior.addEventListener('change', () => { state.wwBehavior = el.wwFilterBehavior.value; loadWenwenCandidates(); });

  el.wenwenCollect.addEventListener('click', async () => {
    el.wenwenCollect.disabled = true;
    el.wenwenMeta.textContent = '采集中…（向上扫描新增案例）';
    el.wenwenMeta.className = 'topics-meta running';
    try {
      await fetch('/wenwen/api/collect', { method: 'POST' });
    } catch (e) {
      el.wenwenMeta.textContent = `采集失败：${e.message}`;
      el.wenwenMeta.className = 'topics-meta err';
    }
    el.wenwenCollect.disabled = false;
    loadWenwenCandidates();
  });
  el.wenwenAnalyze.addEventListener('click', async () => {
    el.wenwenAnalyze.disabled = true;
    el.wenwenMeta.textContent = 'AI 分析中…（每轮最多 10 个事件）';
    el.wenwenMeta.className = 'topics-meta running';
    try {
      await fetch('/wenwen/api/analyze?limit=10', { method: 'POST' });
    } catch (e) {
      el.wenwenMeta.textContent = `分析失败：${e.message}`;
      el.wenwenMeta.className = 'topics-meta err';
    }
    el.wenwenAnalyze.disabled = false;
    loadWenwenCandidates();
  });

  el.wwLibSearch.addEventListener('click', () => { state.wwLibPage = 1; loadWenwenLibrary(); });
  el.wwLibQ.addEventListener('keydown', (e) => { if (e.key === 'Enter') { state.wwLibPage = 1; loadWenwenLibrary(); } });
  el.wwLibPrev.addEventListener('click', () => { if (state.wwLibPage > 1) { state.wwLibPage--; loadWenwenLibrary(); } });
  el.wwLibNext.addEventListener('click', () => { state.wwLibPage++; loadWenwenLibrary(); });

  // 每 5 分钟自动刷新时间流
  setInterval(loadItems, 5 * 60 * 1000);

  state.hours = Number(el.range.value) || 168;
  loadSources().then(loadItems);
})();

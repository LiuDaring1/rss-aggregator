/* 信息聚合站 — 前端逻辑 */
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
    wwState: 'all', // 暖文雷达候选过滤：all | pending | kept | ignored
  };

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
    wwTabReg: document.getElementById('ww-tab-reg'),
    wwStateFilters: document.getElementById('ww-state-filters'),
    wwCandidates: document.getElementById('ww-candidates'),
    wwRegistry: document.getElementById('ww-registry'),
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

  // 侧栏用的简短版"最近更新"
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

  /* ---------- 数据 ---------- */

  async function loadSources() {
    const res = await fetch('/api/sources');
    const data = await res.json();
    state.sources = data.sources;
    state.enabled = new Set(state.sources.map((s) => s.id));
    // 后端缓存里可能已有上次抓取的状态，直接用于侧栏展示
    for (const s of state.sources) {
      if (s.status) state.health.set(s.id, { ...s.status, newest: s.status.newestItem });
    }
    renderSources();
  }

  // loadItems 会抓全部源并写缓存，之后顺手把侧栏状态刷新一遍
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
      // 单独查看模式：只看该源；否则看所有勾选的源
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
          ok: r.ok,
          error: r.error,
          count: (r.items || []).length,
          checkedAt: new Date(r.at).toISOString(),
          newest: newest ? new Date(newest).toISOString() : null,
        });
        if (r.ok) okCount++;
      }
      const secs = ((Date.now() - t0) / 1000).toFixed(1);
      el.checkResult.textContent = `${okCount}/${data.sources.length} 正常 · ${secs}s`;
      el.checkResult.className =
        'check-result ' + (okCount === data.sources.length ? 'all-ok' : 'some-err');
      renderSources();
    } catch (e) {
      el.checkResult.textContent = `检测失败：${e.message}`;
      el.checkResult.className = 'check-result some-err';
    } finally {
      el.checkBtn.disabled = false;
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
    if (state.solo) state.solo = null; // 单独模式下改勾选：退出单独模式
    if (on) state.enabled.add(id);
    else state.enabled.delete(id);
  }

  function renderSources() {
    const enabledCount = state.enabled.size;
    el.sourceSummary.textContent = `${enabledCount}/${state.sources.length}`;
    el.sourceList.innerHTML = '';

    // 按 category 分组（保持 sources.json 中的出现顺序）
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
      // 组头：整组勾选（全不选 = 时间流里隐藏整个分类）
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

        // 复选框：勾选/取消（多选过滤）
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

        // 主区域：第一行源名，第二行状态 + 最近更新
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
          stDot.title = st.ok
            ? `连接正常 · 抓到 ${st.count} 条`
            : `连接异常：${st.error || '未知错误'}`;
          const stText = document.createElement('span');
          stText.textContent = st.ok ? '正常' : '异常';
          stText.title = st.ok ? '' : st.error || '';
          meta.append(stDot, stText);
          if (st.ok && st.newest) {
            const upd = document.createElement('span');
            upd.textContent = `· 更新 ${fmtAge(st.newest)}`;
            upd.title = `该源最新文章：${new Date(st.newest).toLocaleString('zh-CN')}`;
            meta.append(upd);
          }
        } else {
          meta.textContent = '状态未知';
          meta.title = '尚未抓取过，点击「测试连接」或刷新列表后显示';
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

  /* ---------- 暖文雷达 ---------- */

  const USE_CLASS = { 完整加工: 'use-full', 短复述: 'use-short', 继续观察: 'use-watch', 暂时不用: 'use-skip' };

  async function loadWenwenCandidates() {
    el.wenwenMeta.textContent = '加载中…';
    el.wenwenMeta.className = 'topics-meta running';
    try {
      const res = await fetch(`/wenwen/api/candidates?state=${state.wwState}&limit=100`);
      const data = await res.json();
      renderWenwenCandidates(data);
    } catch (e) {
      el.wenwenMeta.textContent = `加载失败：${e.message}`;
      el.wenwenMeta.className = 'topics-meta err';
    }
  }

  function renderWenwenCandidates(data) {
    const s = data.summary || {};
    el.wenwenMeta.textContent =
      `已采集案例 ${s.articleCount ?? '—'} 篇 · 合并为 ${s.eventCount ?? '—'} 个事件 · ` +
      `已分析 ${s.analyzedCount ?? '—'} · 信源 ${s.registryCount ?? '—'} 家 · ` +
      `站点累计 ${s.ttzlTotalOnSite ?? '—'} 案例 · 上次采集 ${s.lastCollectAt ? fmtTime(s.lastCollectAt) : '—'}`;
    el.wenwenMeta.className = 'topics-meta';
    el.wwSideStats.innerHTML =
      `已采集案例 <b>${s.articleCount ?? '—'}</b> 篇<br>` +
      `合并事件 <b>${s.eventCount ?? '—'}</b> 个<br>` +
      `已分析 <b>${s.analyzedCount ?? '—'}</b> 个<br>` +
      `登记信源 <b>${s.registryCount ?? '—'}</b> 家<br>` +
      `上次采集 ${s.lastCollectAt ? fmtTime(s.lastCollectAt) : '—'}`;
    el.wwCandidates.innerHTML = '';
    if (!data.events.length) {
      el.wwCandidates.innerHTML =
        '<div class="empty">暂无候选事件。点上方「采集」拉取天天正能量案例，或等待定时任务运行。</div>';
      return;
    }
    for (const ev of data.events) renderWenwenCard(ev);
  }

  function renderWenwenCard(ev) {
    const a = ev.analysis;
    const card = document.createElement('article');
    card.className = 'ww-card' + (ev.userStatus === 'ignored' ? ' ww-ignored' : '') + (ev.userStatus === 'kept' ? ' ww-kept' : '');

    const head = document.createElement('div');
    head.className = 'topic-head';
    const use = document.createElement('span');
    use.className = 'ww-use ' + (USE_CLASS[a?.suggestedUse] || '');
    use.textContent = a?.suggestedUse || '待分析';
    use.title = 'AI 建议用途';
    const title = document.createElement('h3');
    title.textContent = ev.title;
    head.append(use, title);
    card.appendChild(head);

    const meta = document.createElement('div');
    meta.className = 'ww-meta';
    const kept = document.createElement('span');
    kept.textContent = ev.userStatus === 'kept' ? '⭐ 已保留' : ev.userStatus === 'ignored' ? '已忽略' : '';
    meta.append(kept);
    const src = document.createElement('span');
    src.textContent =
      `${ev.mediaList.length} 家媒体 · ${ev.articleCount} 篇 · 获奖于 ${(ev.firstAt || '').slice(0, 10)}` +
      (ev.category ? ` · ${ev.category}` : '');
    meta.append(src);
    card.appendChild(meta);

    if (a) {
      const one = document.createElement('p');
      one.className = 'ww-oneline';
      one.textContent = a.oneLine;
      card.appendChild(one);

      const facts = document.createElement('dl');
      facts.className = 'ww-facts';
      const rows = [
        ['人物', a.people], ['行动', a.action], ['处境/成本', a.difficulty],
        ['记忆点', a.detail], ['结果', a.result],
      ];
      for (const [k, v] of rows) {
        if (!v) continue;
        const dt = document.createElement('dt');
        dt.textContent = k;
        const dd = document.createElement('dd');
        dd.textContent = v;
        facts.append(dt, dd);
      }
      card.appendChild(facts);

      if (a.discussionTags?.length) {
        const tags = document.createElement('div');
        tags.className = 'ww-tags';
        for (const t of a.discussionTags) {
          const chip = document.createElement('span');
          chip.textContent = t;
          tags.appendChild(chip);
        }
        const behavior = document.createElement('span');
        behavior.className = 'ww-behavior';
        behavior.textContent = a.behaviorCategory;
        tags.prepend(behavior);
        card.appendChild(tags);
      }

      const reason = document.createElement('p');
      reason.className = 'ww-reason';
      reason.textContent = '判断：' + a.reason + (a.needMoreSearch ? '（建议补充搜索）' : '');
      card.appendChild(reason);
    } else {
      const wait = document.createElement('p');
      wait.className = 'ww-reason';
      wait.textContent = '尚未 AI 分析：点上方「补充分析」，或等待定时任务（每 20 分钟）。';
      card.appendChild(wait);
    }

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
    const fullBtn = document.createElement('button');
    fullBtn.className = 'ww-full-btn';
    fullBtn.textContent = '📄 本地全文';
    fullBtn.title = '展开系统已留档的报道原文（不跳转外部网站）';
    fullBtn.addEventListener('click', () => toggleWenwenFull(card, ev.id, fullBtn));
    actions.append(keepBtn, ignoreBtn, fullBtn);
    card.appendChild(actions);

    el.wwCandidates.appendChild(card);
  }

  /** 展开/收起本地留档全文（首次点开时才拉取） */
  async function toggleWenwenFull(card, evId, btn) {
    const existing = card.querySelector('.ww-full');
    if (existing) {
      existing.remove();
      btn.textContent = '📄 本地全文';
      return;
    }
    btn.disabled = true;
    btn.textContent = '加载中…';
    try {
      const res = await fetch(`/wenwen/api/events/${encodeURIComponent(evId)}/full`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
      const box = document.createElement('div');
      box.className = 'ww-full';
      if (!data.articles?.length) {
        box.innerHTML = '<div class="empty">本地暂无留档正文。</div>';
      } else {
        for (const art of data.articles) {
          const item = document.createElement('div');
          item.className = 'ww-full-item';
          const head = document.createElement('div');
          head.className = 'ww-full-head';
          const src = document.createElement('span');
          src.className = 'ta-src';
          src.textContent = art.media || '未知媒体';
          const date = document.createElement('span');
          date.className = 'ww-full-date';
          date.textContent = (art.publishedAt || '').slice(0, 10);
          const link = document.createElement('a');
          link.href = art.url;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          link.textContent = '原文链接 ↗';
          head.append(src, date, link);
          const t = document.createElement('div');
          t.className = 'ww-full-title';
          t.textContent = art.title;
          const body = document.createElement('div');
          body.className = 'ww-full-body';
          body.textContent = art.content || '（本地未留档正文）';
          item.append(head, t, body);
          box.appendChild(item);
        }
      }
      card.insertBefore(box, btn.parentElement);
      btn.textContent = '📄 收起全文';
    } catch (e) {
      btn.textContent = `加载失败：${e.message}`;
    } finally {
      btn.disabled = false;
    }
  }

  async function wenwenFeedback(id, action) {
    try {
      await fetch(`/wenwen/api/events/${encodeURIComponent(id)}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      loadWenwenCandidates();
    } catch (e) {
      el.wenwenMeta.textContent = `操作失败：${e.message}`;
      el.wenwenMeta.className = 'topics-meta err';
    }
  }

  async function loadWenwenRegistry() {
    el.wwRegistry.hidden = false;
    el.wwCandidates.hidden = true;
    el.wwRegistry.innerHTML = '<div class="empty">加载中…</div>';
    try {
      const res = await fetch('/wenwen/api/registry');
      const data = await res.json();
      const byStatus = data.byStatus || {};
      const head = `<div class="ww-reg-summary">共登记 ${data.total} 家信源（来自天天正能量案例自动抽取）：` +
        Object.entries(byStatus).map(([k, v]) => `${k} ${v}`).join(' · ') +
        '。官网与采集方式自动探测将在下一阶段补充。</div>';
      const rows = data.sources.map((s) => `
        <tr>
          <td>${s.name}</td>
          <td>${s.origin || ''}</td>
          <td>${s.probeStatus}</td>
          <td>${s.articleCount || 0}</td>
          <td>${s.lastSuccessAt ? fmtTime(s.lastSuccessAt) : '—'}</td>
        </tr>`).join('');
      el.wwRegistry.innerHTML =
        head + `<table class="ww-reg-table"><thead><tr><th>媒体</th><th>来源</th><th>探测状态</th><th>案例数</th><th>最近命中</th></tr></thead><tbody>${rows}</tbody></table>`;
    } catch (e) {
      el.wwRegistry.innerHTML = `<div class="empty">加载失败：${e.message}</div>`;
    }
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

  /* ---------- 事件 ---------- */

  el.refresh.addEventListener('click', loadItems);
  el.range.addEventListener('change', () => {
    state.hours = Number(el.range.value);
    if (state.view === 'topics') loadTopics(true);
    else loadItems();
  });
  el.soloExit.addEventListener('click', () => setSolo(null));
  el.checkBtn.addEventListener('click', runCheck);
  el.tabFeed.addEventListener('click', () => setView('feed'));
  el.tabTopics.addEventListener('click', () => setView('topics'));
  el.tabComment.addEventListener('click', () => setMain('comment'));
  el.tabWenwenMain.addEventListener('click', () => setMain('wenwen'));
  el.topicsRegen.addEventListener('click', () => loadTopics(true));
  // 暖文雷达
  el.wwTabCand.addEventListener('click', () => {
    el.wwTabCand.classList.add('active');
    el.wwTabReg.classList.remove('active');
    el.wwRegistry.hidden = true;
    el.wwCandidates.hidden = false;
  });
  el.wwTabReg.addEventListener('click', () => {
    el.wwTabReg.classList.add('active');
    el.wwTabCand.classList.remove('active');
    loadWenwenRegistry();
  });
  for (const btn of el.wwStateFilters.querySelectorAll('button[data-state]')) {
    btn.addEventListener('click', () => {
      el.wwStateFilters.querySelectorAll('button').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.wwState = btn.dataset.state;
      loadWenwenCandidates();
    });
  }
  el.wenwenCollect.addEventListener('click', async () => {
    el.wenwenCollect.disabled = true;
    el.wenwenMeta.textContent = '采集中…（向上扫描新增案例，约几十秒）';
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
    el.wenwenMeta.textContent = 'AI 分析中…（每轮最多 10 个事件，约 1-2 分钟）';
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

  // 每 5 分钟自动刷新
  setInterval(loadItems, 5 * 60 * 1000);

  state.hours = Number(el.range.value) || 168;
  loadSources().then(loadItems);
})();

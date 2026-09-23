# HANDOVER｜系统贯通与正常生产操作指南（Antigravity 生产定标版）

## 1. 两个工作区的分工与运行状态

| 维度 | 原工作区（后台守护） | 本工作区（生产与出刊主线） |
| :--- | :--- | :--- |
| **绝对路径** | `/Users/baiyanglin/Desktop/RSS订阅-zcode` | `/Users/baiyanglin/Desktop/口语素材周刊_Antigravity/project` |
| **Git 分支** | `main` | `antigravity-dev`（与开发主线对齐） |
| **后台服务** | 聚合站 `:3001` 与 RSSHub `:1200` 保持常驻守护 | 依赖本地 `:1200` 抓取；排版构建（`cli.py build`）100% 确定性离线 |
| **资料库通路** | 权威维护 `aggr-site/data/wenwen/` (天天正能量 283 篇) | 经软链接实时直通 `wenwen` live 目录；权威维护 `data/commentaries/` (289 篇评论，188 篇长文) |
| **教师端入口** | 运行 Web 服务：`http://127.0.0.1:3001/` | 出刊控制台：`http://127.0.0.1:3001/weekly.html` 及桌面直取目录 |

---

## 2. 核心工作链拓扑

```
[11家媒体评论源] ──(RSSHub :1200)──> scripts/fetch_commentaries.py ──> aggr-site/data/commentaries/raw/*.json
[天天正能量案例] ──(wenwen调度器)──> aggr-site/data/wenwen/raw/*.json (经软链接权威直通)
                                                │
                                                ▼
                         publishing/weekly_pipeline/prep.py
                                 (双路候选扫描与初筛，自动推导时段与复用标记)
                                                │
                                                ▼
                                    issues/<期号>/candidates_scan.json
                                                │
                                                ▼
                                    Agent 采编与结构化沉淀
                     ┌──────────────────────────┼──────────────────────────┐
                     ▼                          ▼                          ▼
           content/retellings/*.yaml   content/commentaries/*.yaml   content/excerpts/*.yaml
           (事实+导图树+参考复述)       (三页制: 引导/多观点/双主体范本) (背景+100%匹配引文+示范迁移)
                     └──────────────────────────┬──────────────────────────┘
                                                │
                                                ▼
                                    issues/<期号>/issue.yaml
                                                │
                                                ▼
                                publishing/weekly_pipeline/cli.py build
                                    (前置信源校验 + 物理页数核验)
                                                │
                                                ▼
             dist/<期号>/ (整刊 PDF、3本模块分册 PDF、学生同源 Markdown、HTML)
                                                │
                                                ▼
                   桌面直取：~/Desktop/口语素材周刊_正式生产发布_<期号>/
                   网页直读：http://127.0.0.1:3001/weekly.html
```

---

## 3. 每周稳定生产极简操作指南 (Unified Runner)

日常采编与出刊推荐直接使用统一生产调度台 `scripts/weekly_runner.py`，无需手动搬运文件或记住复杂的参数：

### 核心命令一览：
```bash
# 1. 查看生产进度看板与上游健康度 (推荐教师每周一首先运行)
python3 scripts/weekly_runner.py status --issue issue-2026-w39

# 2. 执行信源采集并初始化本周备料 (自动推导自然周时间窗并扫描候选池)
python3 scripts/weekly_runner.py prep --issue issue-2026-w39

# 3. 执行带原子防护与全门禁核验的正式构建 (Staging 隔离，失败绝不伤历史)
python3 scripts/weekly_runner.py build --issue issue-2026-w39

# 4. 导出多期审阅静态站并正式发布 (保留 W38 等历史期归档)
python3 scripts/weekly_runner.py publish --issue issue-2026-w39
```

### 任务断点续做机制 (Resumable Production)：
- 生产状态实时持久化于 `issues/<期号>/production_state.json`，串联：
  `prep` $\to$ `candidates_selected` $\to$ `drafting` $\to$ `comics` $\to$ `review` $\to$ `build` $\to$ `published`。
- 会话中断、关闭终端或切换 Agent 对话后，重新运行 `status` 或 `prep` 会自动读取当前断点并提示下一步待办。已完成定稿并冻结的单元（`frozen_units`）绝不重复重写或重新生图。

### 私有数据本地备份与灾备恢复：
```bash
# 执行本地数据备份归档 (生成 backups/commentaries_backup_YYYYMMDD_HHMMSS.tar.gz)
python3 scripts/backup_data.py --backup

# 校验备份完整性 (校验 SHA256 与 db.json / raw 文件)
python3 scripts/backup_data.py --verify backups/commentaries_backup_XXXXXXXX_XXXXXX.tar.gz

# 容灾还原演练
python3 scripts/backup_data.py --restore backups/commentaries_backup_XXXXXXXX_XXXXXX.tar.gz --data-dir aggr-site/data/commentaries
```

---

## 4. 教师查看与在线审阅站点

1. **多期静态审阅站 (永久归档)**：
   - 门户首页：`review-public/index.html` (自动展示最新已发布期次，顶部提供往期周刊归档下拉菜单)；
   - W38 永久归档：`review-public/issues/issue-2026-w38/index.html`；
   - W39 及后续归档：`review-public/issues/issue-2026-w39/index.html`；
   - 线上部署：GitHub Pages `gh-pages` 分支。
2. **聚合站后台直通 (开发测试)**：
   - 🔗 **`http://127.0.0.1:3001/weekly.html`**；
   - 可在线浏览 360+ 篇权威时评与暖文全文，并查看当期采编明细。

---

## 5. 故障恢复与常见排查

1. **全源抓取失败或网络中断**：
   - `fetch_commentaries.py` 内置全部失败系统级拦截（`exit code 2`），并在 `sources_status.json` 记录连续失败次数与真实错误堆栈，绝不清空存量数据，亦不将抓取异常伪装为正常成功。
2. **进程文件锁冲突**：
   - `fetch_commentaries.py` 采用 `fcntl.flock` 单实例文件锁（`db.json.lock`）。若同一时刻有另一个采集实例运行，将安全跳过并保护数据库不被并发写坏。
3. **RSSHub 连接失败 (`Failed to connect to 127.0.0.1:1200`)**：
   - 检查 RSSHub 进程：`ps aux | grep 1200`
   - 重启命令：`cd ~/Desktop/RSS订阅-zcode/rsshub && pnpm dev &`
4. **macOS 自动化调度 (launchd)**：
   - 调度配置文件位于 `scripts/launchd/com.weekly.fetch_commentaries.plist`。
   - 载入调度：`launchctl load ~/Library/LaunchAgents/com.weekly.fetch_commentaries.plist`。
5. **构建门禁拦截与原子回滚**：
   - 严苛门禁：正式构建必须存在 `manifest_prep.json` 且 21 单元集合严格匹配；信源原段 100% 连续子串精准比对；物理页数精确守恒。
   - 原子安全：构建产物首先在 `dist/<期号>.staging` 生成与检验，全部通过后才提升为正式发布目录；若有任何报错，staging 目录立即清理，原有正式发布文件毫发无损。

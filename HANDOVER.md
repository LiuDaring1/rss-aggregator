# HANDOVER｜系统贯通与正常生产操作指南（Antigravity 定标版，2026-09-20）

## 1. 两个工作区的分工与运行状态

| 维度 | 原工作区（后台守护） | 本工作区（生产与出刊主线） |
| :--- | :--- | :--- |
| **绝对路径** | `/Users/baiyanglin/Desktop/RSS订阅-zcode` | `/Users/baiyanglin/Desktop/口语素材周刊_Antigravity/project` |
| **Git 分支** | `main` | `antigravity-dev`（与开发主线对齐） |
| **后台服务** | 聚合站 `:3001` 与 RSSHub `:1200` 保持常驻守护 | 依赖本地 `:1200` 抓取；排版构建（`cli.py build`）100% 确定性离线 |
| **资料库** | `aggr-site/data/wenwen/` 自动增量采集天天正能量 | 双路入库：`aggr-site/data/wenwen/raw/`（暖文）与 `aggr-site/data/commentaries/raw/`（评论全文） |

---

## 2. 核心工作链拓扑

```
[11家媒体评论源] ──(RSSHub :1200)──> scripts/fetch_commentaries.py ──> aggr-site/data/commentaries/raw/*.json
[天天正能量案例] ──(wenwen调度器)──> aggr-site/data/wenwen/raw/*.json
                                                │
                                                ▼
                         publishing/weekly_pipeline/prep.py
                                 (双路候选扫描与初筛)
                                                │
                                                ▼
                                    issues/<期号>/candidates_scan.json
                                                │
                                                ▼
                                    Agent 采编与结构化沉淀
                     ┌──────────────────────────┼──────────────────────────┐
                     ▼                          ▼                          ▼
           content/retellings/*.yaml   content/commentaries/*.yaml   content/excerpts/*.yaml
           (事实+导图树+参考复述)       (三页制: 问题/4观点/双主体范本)  (语境+100%匹配引文+示范)
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
```

---

## 3. 下一次怎样出刊（极简标准生产指令）

出刊无需手工拼装 YAML 或搬运文件，遵循以下 4 步即可：

### 第一步：同步最新上游资料（评论全文与暖文）
```bash
# 1. 抓取并持久化 11 家权威评论栏目最新全文到本地资料库
python3 scripts/fetch_commentaries.py
```

### 第二步：扫描本周时间窗候选材料
```bash
# 2. 扫描指定时间窗（如 2026-09-14 至 2026-09-20）内的所有入库候选
python3 publishing/weekly_pipeline/prep.py --issue-id issue-2026-w38 --start-date 2026-09-14 --end-date 2026-09-20
```

### 第三步：Agent 依据现行标准采编与审核
- Agent 读取 `issues/<期号>/candidates_scan.json` 中的热点评论与暖性素材；
- 对照 `CURRENT_REQUIREMENTS.md`（以岩新融合定稿版为语体标准）：
  - 编写复述单元：`content/retellings/Rxx.yaml`
  - 编写评论单元：`content/commentaries/Cxx.yaml`（4组观点池，双主体段范本，首句加粗亮明分论点）
  - 编写原文拆解单元：`content/excerpts/Fxx.yaml`（并将原文保存在 `issues/<期号>/sources/Fxx_source.txt`）
  - 组装期号配置：`issues/<期号>/issue.yaml`

### 第四步：离线排版构建与交付
```bash
# 校验内容合规性
python3 publishing/weekly_pipeline/cli.py validate --content-dir content

# 确定性离线构建整刊与分册
python3 publishing/weekly_pipeline/cli.py build --issue issue-2026-w38 --outdir dist/issue-2026-w38 --formats html,pdf

# 导出到桌面供教师直取
cp -r dist/issue-2026-w38/* ~/Desktop/口语素材周刊_正式生产发布_issue-2026-w38/
```

---

## 4. 故障恢复与常见排查

1. **RSSHub 连接失败 (`Failed to connect to 127.0.0.1:1200`)**：
   - 检查 RSSHub 进程：`ps aux | grep 1200`
   - 重启命令：`cd ~/Desktop/RSS订阅-zcode/rsshub && pnpm dev &`
2. **聚合站 Web 服务检查 (`http://localhost:3001`)**：
   - 检查服务状态：`lsof -i :3001`
   - 若未启动：`cd ~/Desktop/RSS订阅-zcode/aggr-site && node server.js &`
3. **引文校验拦截 (`verify_issue_quotes failed`)**：
   - 系统内置强安全机制：所有入选 `Fxx.yaml` 的 `quote_paragraphs` 必须 100% 是 `issues/<期号>/sources/Fxx_source.txt` 的真实连续子串。若有改动，必须确保引文与原件字字一致。

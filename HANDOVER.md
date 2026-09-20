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

## 3. 下一次怎样出刊（极简标准生产指令）

出刊无需手工搬运文件，遵循以下 4 步即可：

### 第一步：同步最新上游资料（评论全文与暖文）
```bash
# 单次全量抓取并持久化 11 家权威评论栏目最新全文到本地资料库
python3 scripts/fetch_commentaries.py

# （可选）在后台常驻周期运行：
python3 scripts/fetch_commentaries.py --daemon --interval 3600 &
```

### 第二步：扫描最新候选池（自动推导自然周时间窗与回看范围）
```bash
# 自动推导自然周起止（如 2026-w39 自动计算为 09.21~09.27，回看14天），并标记往期复用
python3 publishing/weekly_pipeline/prep.py --issue issue-2026-w39
```

### 第三步：Agent 依据现行标准采编与审核
- Agent 或编辑读取 `issues/<期号>/candidates_scan.json` 中的热点评论与暖性素材；
- 对照 `CURRENT_REQUIREMENTS.md`（以岩新融合定稿版为语体标准）：
  - 编写复述单元：`content/retellings/Rxx.yaml`
  - 编写评论单元：`content/commentaries/Cxx.yaml`（多向观点池，双主体段范本，首句加粗亮明分论点）
  - 编写原文拆解单元：`content/excerpts/Fxx.yaml`（并将原文保存在 `issues/<期号>/sources/Fxx_source.txt`，标注官网原链接）
  - 组装期号配置：`issues/<期号>/issue.yaml`

### 第四步：离线排版构建与交付
```bash
# 确定性离线构建整刊与分册（支持直接传入 issues/<期号>）
python3 publishing/weekly_pipeline/cli.py build issues/issue-2026-w39

# （或使用标准完整参数指定输出路径）
python3 publishing/weekly_pipeline/cli.py build --issue issue-2026-w39 --outdir dist/issue-2026-w39 --formats html,pdf

# 镜像同步到桌面供教师直取
mkdir -p ~/Desktop/口语素材周刊_正式生产发布_issue-2026-w39
cp -rf dist/issue-2026-w39/* ~/Desktop/口语素材周刊_正式生产发布_issue-2026-w39/
```

---

## 4. 教师查看与在线资料库使用

教师打开本地运行的聚合站：  
🔗 **`http://127.0.0.1:3001/weekly.html`**（或从聚合站首页顶部导航“📖 周刊出刊台”进入）

可在浏览器中：
1. **直接阅读长文全文**：无需打开 JSON，在线浏览与检索 188 篇权威时评完整长文与字数；
2. **查验当期采编明细**：查看本期复述、评论、拆解单元的事实出处与 100% 精确匹配引文；
3. **一键打开与下载成品**：一键预览或下载 16 页整刊合订本、三本独立教学分册 PDF 及 Markdown 全文。

---

## 5. 故障恢复与常见排查

1. **RSSHub 连接失败 (`Failed to connect to 127.0.0.1:1200`)**：
   - 检查 RSSHub 进程：`ps aux | grep 1200`
   - 重启命令：`cd ~/Desktop/RSS订阅-zcode/rsshub && pnpm dev &`
2. **聚合站 Web 服务检查 (`http://localhost:3001`)**：
   - 检查服务状态：`lsof -i :3001`
   - 若未启动：`cd ~/Desktop/RSS订阅-zcode/aggr-site && node server.js &`
3. **引文校验拦截 (`verify_issue_quotes failed`)**：
   - 系统内置强门禁机制：所有入选 `Fxx.yaml` 的 `quote_paragraphs` 必须 100% 是 `issues/<期号>/sources/Fxx_source.txt` 的真实连续子串。若有改动，必须确保引文与原件字字一致。

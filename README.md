# 口语素材周刊 · 全系统架构与工程总览（Antigravity 协作版）

> **这是什么**：面向高中播音主持艺考生的口语素材周刊全自动/半自动生产系统，涵盖**评论聚合站**、**暖文雷达**、**本地正文资料库**，以及**周刊排版渲染引擎（复述 / 评论 / 原文拆解三模块）**。之前由 ZCode 开发维护，现已全面移植至 Google Antigravity 协作体系。
> 
> **协作模式**：
> - **Antigravity**：执行制作 Agent（代码实现、试写与重构、排版构建、生成 PDF、安全推送）
> - **Reviewer Agent**：主编与架构指导 Agent（审阅系统全貌、对照教学标准评估产出、下发重构方案与任务书）

---

## 🧭 系统核心文档导航（首读入口）

| 文档 | 职责说明 | 必读等级 |
| :--- | :--- | :--- |
| 📋 **[CURRENT_REQUIREMENTS.md](CURRENT_REQUIREMENTS.md)** | **当前唯一有效的产品与编辑要求**（教师最新澄清优先于一切历史文件） | ⭐⭐⭐⭐⭐ |
| 🤝 **[AGENT_SYNC.md](AGENT_SYNC.md)** | **多 Agent 协作看板**（执行制作 ↔ 审阅指导，记录最新交付物与待办清单） | ⭐⭐⭐⭐⭐ |
| 🏗️ **[HANDOVER.md](HANDOVER.md)** | **工程架构与操作指南**（服务端口、数据位置、构建命令、已知缺陷） | ⭐⭐⭐⭐ |
| 🛡️ **[CHECKS_AND_MANIFEST.md](CHECKS_AND_MANIFEST.md)** | **打包与环境验证审计**（通过/失败/未测清单、SHA-256 哈希比对） | ⭐⭐⭐⭐ |
| 📖 **[README_先读我.md](README_先读我.md)** | **交接背景与目录职责说明** | ⭐⭐⭐ |
| 📂 **[references/](references/)** | 包含 `historical-briefs/`（v0.1~v0.6 演进历程）与 `handoff-pack/` | ⭐⭐⭐ |

---

## 🏛️ 全系统端到端架构拓扑

整个系统分为三大层级，形成从“原始新闻采集”到“可打印周刊”的完整闭环：

```mermaid
flowchart TD
    subgraph 上游采集与雷达层
        S1[11家媒体评论源] -->|RSSHub 自研路由 :1200| AGGR[aggr-site :3000/3001 聚合站]
        S2[微信公众号评论] -->|we-mp-rss 授权采集 :8001| AGGR
        S3[天天正能量获奖案例] -->|wenwen 爬虫增量抓取| RAW[(本地正文资料库 raw/*.json)]
        RAW --> PREP[prep.py 备料与选材候选生成]
    end

    subgraph 中游采编加工层
        PREP --> FILTER[人工 / AI 素材核验与选材]
        FILTER --> RETELL[content/retellings/*.yaml<br/>中性事实+关键词+导图树]
        FILTER --> COMM[content/commentaries/*.yaml<br/>三页规范: 问题+多角度推演+双主体范本]
        S1 --> FRAG[content/excerpts/*.yaml<br/>话语化拆解+口语示范]
    end

    subgraph 下游排版与同源渲染层
        RETELL & COMM & FRAG --> ISSUE[issues/{issue_id}/issue.yaml 组刊清单]
        ISSUE --> CLI[weekly_pipeline/cli.py 构建管线]
        CLI --> JINJA[Jinja2 模板渲染 HTML]
        CLI --> MD_EXP[同源 Markdown 导出]
        JINJA --> CHROME[无头浏览器 Chromium 打印]
        CHROME --> PDF[整刊 PDF & 三模块独立分册 PDF]
    end
```

---

## 🏗️ 内容生产流水线与架构说明

经过流水线重构与工程解耦，系统已实现模块化、同源渲染的工业化生产链路：

1. **结构化数据单元（YAML + Pydantic Schema）**：
   - 彻底废除旧版巨石脚本（历史脚本 `weekly/sample-01-rev5/content5.py` 与 `build5.py` 已归档为历史基准，不再参与日常生产）。
   - 所有素材独立沉淀在 `content/` 目录下（`content/retellings/`、`content/commentaries/`、`content/excerpts/`），由强类型 Schema 严格校验。
2. **组刊配置（Manifest）**：
   - 每期周刊由独立的 `issues/{issue_id}/issue.yaml` 清单定义，明确选材 ID、栏目次序、期号与时间跨度。
3. **同源渲染与多格式导出**：
   - 基于 Jinja2 模板与无头 Chromium 打印，确保全刊 A4 印刷 PDF、各栏目独立分册 PDF（复述/评论/原文拆解）与同源 Markdown 审阅文本一键自动化生成，页码与版心严格一致。

---

## 🛠️ 当前标准端到端出刊工作流

所有命令均在项目根目录下执行：

```bash
# 1. 采集并持久化 11 家权威评论栏目最新全文到本地资料库
python3 scripts/fetch_commentaries.py

# 2. 扫描指定时间窗候选材料（自动汇总评论与暖文双路候选）
python3 publishing/weekly_pipeline/prep.py --issue-id issue-2026-w38 --start-date 2026-09-14 --end-date 2026-09-20

# 3. 全量素材单元 Schema 验证（校验 content/ 下所有 YAML）
python3 publishing/weekly_pipeline/cli.py validate --content-dir content

# 4. 构建指定期号周刊（生成 HTML、整刊 PDF、3本模块分册 PDF、同源 Markdown）
python3 publishing/weekly_pipeline/cli.py build --issue issue-2026-w38 --outdir dist/issue-2026-w38 --formats html,pdf

# 5. 聚合站离线测试（15 项）
cd aggr-site && npm test
```

---

## 🔒 安全与隐私红线

1. **私密教学原件绝不入库**：学生真实姓名、录音转写及课堂记录（位于本地 `references/teaching-private/`）严禁提交到任何公开仓库。
2. **密钥与数据防护**：`aggr-site/ai.json`、`we-mp-rss/config.yaml`、本地抓取数据库 `aggr-site/data/wenwen/` 受 `.gitignore` 严格保护。
3. **协作流程**：所有 Agent 在 `antigravity-dev` 分支拉取与推送，通过 `./agent-sync.sh` 脚本进行前置安全审查，用户确认后再合入 `main`。

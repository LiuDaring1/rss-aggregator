# 信息聚合站（评论频道 + 暖文雷达）

面向「播音主持艺考 · 即兴口语表达」训练的信息聚合与素材筛选系统。两大并行信源频道：

| 频道 | 内容 | 数据来源 |
| ---- | ---- | -------- |
| 📰 **评论频道** | 11 家媒体评论源的时间流 + AI 热点归纳 | 浙江宣传、澎湃·马上评、南方周末·自由谈、红星评论、新京报·快评、人民锐评、人民网·壹时评、中青评论、光明网评论员、红辣椒×2（RSSHub 自研路由） |
| 💗 **暖文雷达** | 持续发现适合口语训练的"暖事件"候选：结构化提取人物/行动/处境/记忆点/结果，按建议用途（完整加工/短复述/继续观察/暂时不用）筛选 | 天天正能量（阿里巴巴公益基金会）获奖案例，持续增量采集 |

## 🤖 AI 助手（ChatGPT 等）阅读入口

**直接把下面这个文件链接发给 AI 助手即可**（纯 Markdown，已为 AI 阅读优化）：

```
https://raw.githubusercontent.com/LiuDaring1/rss-aggregator/main/data/report.md
```

- [`data/report.md`](data/report.md) — 暖文候选报告（分章节：已保留/完整加工/优先补搜/短复述或案例/继续观察/暂时不用/待分析，含人物/行动/记忆点/母题/讨论角度/信息缺口/原文链接）
- [`data/candidates.json`](data/candidates.json) — 全部事件的结构化数据
- [`data/registry.json`](data/registry.json) — 信源覆盖表（媒体实体 + 探测状态）
- [`data/calibration-report.md`](data/calibration-report.md) — AI 筛选分层校准报告（分布 + 代表案例）
- [`data/multisource-summary.md`](data/multisource-summary.md) — 多信源接入汇总
- [`data/data-health.md`](data/data-health.md) — 数据健康报告
- [`data/status.json`](data/status.json) — 采集状态

**口语素材周刊·试制样刊（第 0 期）审阅入口**：

```
https://raw.githubusercontent.com/LiuDaring1/rss-aggregator/main/weekly/sample-01/sample.md
https://raw.githubusercontent.com/LiuDaring1/rss-aggregator/main/weekly/sample-01/editor-notes.md
```

- `sample.md` — 样刊正文（5 则新闻复述 + 3 篇暖事件精讲 + 1 处评论拆解 + 本期积累）
- `editor-notes.md` — 教师备注（选材理由、逐篇来源与事实核对、未确认信息、范本字数）
- 可打印 PDF：[`weekly/sample-01/sample.pdf`](weekly/sample-01/sample.pdf)（A4 黑白 10 页）

> 数据快照随本地系统采集进度手动/定时更新；本地服务另有实时接口 `/wenwen/report`。

## 📖 成品出口：口语素材周刊（试刊）

系统的最终用途是给播音主持艺考生做可打印的口语素材周刊。当前最新为 **rev.4**（依据任务书 v0.5 试行；**插画待回传，现为审阅稿**）：

- [`weekly/sample-01-rev4/sample.pdf`](weekly/sample-01-rev4/sample.pdf) — 审阅版（45 页）：复述 8 则（材料页＋提示页两页一题；关键词/思维导图/插画三种辅助并行；思维导图为统一虚线补写框）· 集中参考 · 评论 6 题（**每题三页**：问题／观点与细致推演／范本与拆解）· 原文拆解与积累 6 单元（区分"值得记住的表达"与"可以借鉴的讲法"，每单元配完整口语示范）
- [`weekly/sample-01-rev4/illustration-briefs.md`](weekly/sample-01-rev4/illustration-briefs.md) — 插画需求包（R01–R08：事实、画面方案、可直接复制的提示词）
- [`weekly/sample-01-rev4/editor-notes.md`](weekly/sample-01-rev4/editor-notes.md) — 教师备注（借鉴记录、回归检查对照、版面修复说明、未决项）
- [`weekly/sample-01-rev4/change-summary.md`](weekly/sample-01-rev4/change-summary.md) — rev.3→rev.4 修改对照、跨模块对应、页数
- 三模块分册：`sample-复述.pdf`（18 页）/ `sample-评论.pdf`（18 页）/ `sample-原文拆解与积累.pdf`（6 页）
- 历史版本：[`weekly/sample-01/`](weekly/sample-01/)（rev.0）、[`weekly/sample-01-rev1/`](weekly/sample-01-rev1/)、[`weekly/sample-01-rev2/`](weekly/sample-01-rev2/)、[`weekly/sample-01-rev3/`](weekly/sample-01-rev3/)；排版源码同目录（content4.py + build4.py + style4.css）

## 📋 情况说明

最新一轮的详细状态、受阻事项与下一步计划见 [docs/情况说明-20260904.md](docs/情况说明-20260904.md)。

## 当前规模（2026-09-04）

- 天天正能量获奖案例 250 条（本地全文留档）+ 中国新闻网等外部信源真实文章持续入库
- 合并后事件 260 个，其中 75 个已按 v0.2.1 规则完成 AI 结构化分析
- 媒体实体 77 家（全部完成首次探测），实际接入采集 1 家（中国新闻网 RSS）
- 筛选体系：材料价值 × 信息成熟度 → 代码组合建议用途（完整加工/优先补搜/短复述或案例/继续观察/暂时不用），附事件母题、讨论角度、信息缺口分级

## 自动化测试

```bash
cd aggr-site && npm test   # 15 项测试（解析/游标/日期/指纹继承/媒体归属/来源记录/全文等）
```

推送时 GitHub Actions 会自动运行同一组测试（`.github/workflows/test.yml`）。

## 本地数据与备份

- 数据目录：`aggr-site/data/wenwen/`（原始正文留档 + 事件/信源/反馈索引，不入库不入包）
- 页面「本地资料库」支持搜索、筛选、完整正文阅读与三种导出：
  - 导出索引与分析 JSON（不含正文）
  - 导出 Markdown 候选报告
  - 下载完整数据备份 ZIP（含全部正文快照与 manifest，无任何敏感信息）

## 架构

```
微信(扫码授权) ──> we-mp-rss:8001 ──/rss/{feed_id}/api──┐
                                                        ├──> aggr-site:3000 (自研聚合站)
各媒体站点 ──────> RSSHub:1200 ──/路由(含6条自研)────────┘         │
                                                                └──> 浏览器 / AI 助手
天天正能量官网 ──────────────> aggr-site/wenwen 采集器（SSR 直采 + GLM 分析）─┘
```

- **aggr-site**（本仓库核心，100% 自研）：零框架 Node 服务，评论时间流、AI 热点归纳（GLM）、暖文雷达（采集/合并/分析/筛选）、本地留档
- **RSSHub**（上游开源引擎，DIYgod/RSSHub）：媒体站点转 RSS，本项目贡献 6 条自研路由（见 `upstream-custom/rsshub-routes/`）
- **we-mp-rss**（上游开源引擎，rachelos/we-mp-rss）：微信公众号转 RSS，本仓库含 Python 3.14 适配文件（`upstream-custom/we-mp-rss/`）

## 快速开始

```bash
# 1) 上游引擎（标准开源安装）
git clone https://github.com/DIYgod/RSSHub rsshub && cd rsshub && pnpm install
# 把 upstream-custom/rsshub-routes/ 下的文件按文件名拷入 lib/routes/ 对应目录
#   （如 zjol_zjxc.ts → lib/routes/zjol/zjxc.ts；bjnews_utils_PATCHED.ts → lib/routes/bjnews/utils.ts）
cd ..

# 2) 聚合站
cd aggr-site && pnpm install && cd ..
# AI 能力（可选，暖文雷达与AI热点需要）：创建 aggr-site/ai.json：
#   {"apiKey":"你的智谱APIKey","baseUrl":"https://open.bigmodel.cn/api/paas/v4","model":"glm-5.3-flash"}

# 3) 一键启动（评论频道三服务）
./start-all.sh     # 聚合网页 http://127.0.0.1:3001（3000被占自动改用3001）
./stop-all.sh      # 全部停止
```

暖文雷达随聚合站自动运行（启动即采集，采集 6h/次、AI 分析 20min/次）；首次建库可在页面点「⬇ 采集新案例」后调 `POST /wenwen/api/collect?backfill=250` 回填历史。

## 目录结构

```
├── aggr-site/                 # ★ 自研聚合站（评论频道 + 暖文雷达）
│   ├── server.js              #    HTTP 服务 + 路由挂载
│   ├── public/                #    前端（时间流/AI热点/暖文雷达 三视图）
│   ├── wenwen/                #    暖文雷达模块：store/ttzl采集器/merge合并/analyze(GLM)/scheduler/routes
│   ├── sources.json           #    评论信息源配置（11个，改配置即时生效）
│   └── ai.json                #    GLM 密钥（本地创建，不入库！见 .gitignore）
├── upstream-custom/           # ★ 对上游引擎的自研贡献与本机适配
│   ├── rsshub-routes/         #    6 条自研路由 + 1 个 WAF 补丁（文件名含放置路径）
│   └── we-mp-rss/             #    Python 3.14 依赖清单 + 本机启动脚本
├── data/                      # ★ 数据快照（report.md / candidates.json / registry.json）
├── 使用说明.md / 聚合站使用说明.md / 自定义改动清单.md
└── start-all.sh / stop-all.sh / package.sh
```

> 注：RSSHub 与 we-mp-rss 是第三方开源引擎（合计数千文件），不整包入库；自研部分全部在 `upstream-custom/`。原交接文档中提到的 `RSS订阅` 本地目录含这两个引擎的完整拷贝与运行数据。

## 自研路由清单（rsshub）

| 路由 | 内容 | 备注 |
| ---- | ---- | ---- |
| `/zjol/zjxc` | 浙江宣传 | 列表+详情 |
| `/thepaper/studio/:id` | 澎湃工作室（20=马上评） | 走官方 API |
| `/gmw/guancha/:id` | 光明网评论频道栏目 | |
| `/rednet/channel/:id` | 红网红辣椒评论栏目 | 兼容新旧模板 |
| `/youth/pinglun/:cat` | 中青评论频道 | GBK 解码 |
| `/bjnews/kuaiping` | 新京报快评·风向标 | 含阿里云 WAF 对策（完整浏览器头 + 单篇降级） |

## 已知问题与路线图

- 暖文信源注册表已登记 123 家媒体（自动抽取自案例），官网定位与通用采集探测为下一阶段工作
- 同事件合并目前基于标题相似度，正文相似度与同类母题判断待升级
- AI 分析吞吐：每 20 分钟 5 个事件，待提升为批量合并调用
- 站点无鉴权，仅建议本机/可信局域网使用

## 许可与致谢

自研代码部分自由使用。感谢开源项目 [RSSHub](https://github.com/DIYgod/RSSHub)、[we-mp-rss](https://github.com/rachelos/we-mp-rss)、[天天正能量](https://ttznl.alibabafoundation.com/) 公开案例库，以及智谱 GLM。

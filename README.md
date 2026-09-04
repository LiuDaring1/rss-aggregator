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

- [`data/report.md`](data/report.md) — 暖文候选报告（按建议用途排序，含一句话概述/人物/行动/记忆点/讨论方向/判断理由/原文链接）
- [`data/candidates.json`](data/candidates.json) — 全部事件的结构化数据
- [`data/registry.json`](data/registry.json) — 信源覆盖表（123 家媒体）
- [`data/status.json`](data/status.json) — 采集状态

> 数据快照随本地系统采集进度手动/定时更新；本地服务另有实时接口 `/wenwen/report`。

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

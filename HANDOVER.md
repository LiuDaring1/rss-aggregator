# HANDOVER｜实际工程结构与使用说明（由 ZCode 按现场实际状态生成，2026-09-16）

## 1. 两个位置的关系

| | 原工作区（不动） | 本副本 |
| ---- | ---- | ---- |
| 路径 | `/Users/baiyanglin/Desktop/RSS订阅-zcode` | `/Users/baiyanglin/Desktop/口语素材周刊_Antigravity/project` |
| Git | main @ 70b6fd0，与 origin/main 同步，工作区干净 | 同一提交的完整克隆（12 个提交），origin 指向 GitHub |
| 运行 | 聚合站 :3001 与 RSSHub :1200 **正在运行** | 默认不运行；验证时用 3467 端口＋`AGGR_AUTOTASKS=off` |
| 数据 | `aggr-site/data/wenwen/`（生产） | 副本内同名相对路径（快照 2026-09-16 11:30:14，db.json 270 事件 / raw 275 篇） |

副本对原工作区**零写入**；唯一的代码差异是副本 `aggr-site/server.js` 增加了 `AGGR_AUTOTASKS=off` 开关（原工作区无此改动，diff 仅此一处，见 CHECKS）。

## 2. 工程构成与入口

```
project/
├── aggr-site/                # ★ 自研聚合站（Node 22，零框架，仅依赖 fast-xml-parser）
│   ├── server.js             #    入口：PORT 默认 3000（占用时自+1）；路由 /api/*、/wenwen/*
│   ├── public/               #    前端（时间流 / AI热点 / 暖文雷达 / 本地资料库 单页）
│   ├── wenwen/               #    暖文雷达模块（ttzl 采集器 / merge / analyze(GLM) / scheduler / routes）
│   ├── data/wenwen/          #    ★ 本地资料库快照：db.json（events 260+、articleIndex、registry、cursor、反馈）+ raw/275 篇全文
│   ├── data/*.tar.gz         #    2026-09-04 的两份历史备份
│   ├── ai.json               #    GLM API 配置（600 权限；镜像在 _private/）
│   ├── sources.json          #    11 个评论源，全部 rsshub 类型、全部启用
│   └── node_modules/         #    已随副本复制（同机同架构，可立即运行）
├── weekly/                   # ★ 周刊：sample-01/（rev.0）至 sample-01-rev5/（当前审阅基线）
├── rsshub/                   # 上游 RSSHub 本地安装（无 .git；package.json 版本 1.0.0 本地固定副本）
│   └── lib/routes/{zjol,bjnews,rednet,youth,gmw,thepaper}/  # 自研/改造路由的实际安装位置
├── we-mp-rss/                # 上游 we-mp-rss 本地安装（Python；config.yaml 含敏感值；data/ 为授权数据）
├── upstream-custom/          # 自研贡献的存放原件（rsshub-routes/*.ts、we-mp-rss/ 适配文件）
├── docs/ data/ .github/ 使用说明.md 聚合站使用说明.md 自定义改动清单.md
└── start-all.sh / stop-all.sh  # 旧工作区的一键脚本（启动 8001/1200/3000 三服务；副本内未验证）
```

被忽略但已复制的路径（原 .gitignore 规则保持不变，Antigravity 提交时不会带上它们）：`aggr-site/data/wenwen/`、`aggr-site/ai.json`、`aggr-site/node_modules/`、`rsshub/`、`we-mp-rss/`、`server.log`（未复制）。

## 3. 周刊生产链路（改哪里、怎么生成）

```
content5.py            # ★ 内容唯一来源：8 则复述（材料/关键词/导图树/参考）、6 篇评论（问题/观点/推演/范本/主线/拆解）、6 段原文拆解
      ↓ build5.py      #    组装 sample.html（关键词网络与思维导图为内嵌 SVG，由 build5.py 生成）
      ↓                 #    注意：必须传页码参数
python3 build5.py toc-pages.json
      ↓ render.sh      #    Chrome 无头打印 → sample.pdf
sample.html / sample.pdf
gen_md5.py             #    从同一 content5.py 生成 sample.md（与 PDF 同源同序）
```

- **只改 `content5.py`**，然后按上面顺序重新生成。直接改 `sample.md` / `sample.html` / `sample.pdf` 都会在下次生成时被覆盖。
- 页码回填是两遍流程：先渲染一次，用 PyMuPDF 找各单元实际页码写入 `toc-pages.json`，再带参数重渲染（rev.3–rev.5 均如此，脚本内无自动两遍）。
- 分册由 PyMuPDF 按页拆分（复述 3–20 / 评论 21–38 / 拆解 39–44，rev.5 口径），参考 rev.5 会话记录或直接重跑拆分脚本。
- 依赖：Python 3.13 + PyMuPDF（fitz）；Chrome（路径写死在 render.sh：`/Applications/Google Chrome.app/...`）；无其他 Python 依赖。
- 字体：macOS 系统字体（PingFang SC / Songti SC / Kaiti SC）。非 macOS 环境需替换 style5.css 字体栈，不从系统目录分发字体。

## 4. 当前内容对应关系（rev.5）

复述 8 则（每则材料页＋提示页，参考答案集中在「复述参考」19–20 页）：
热1 楚亮接坠童"求点赞"（3–4）｜热2 "刁蛮"病历（5–6）｜热3 巨野小学 41 人请假（7–8）｜热4 "100%椰子水"掺水（9–10）｜热5 寿司郎门店（11–12）｜暖1 葫芦爷爷（13–14）｜暖2 王植兴海中救人（15–16）｜暖3 魏治立深夜敲门（17–18）。

评论 6 题（每题三页：问题 21/24/27/30/33/36，观点与推演 22/25/28/31/34/37，范本与拆解 23/26/29/32/35/38）：
评1↔热1（采用 v0.6 附录 A"求赞—给赞"试改结构）｜评2↔热2｜评3↔热4｜评4↔暖1｜评5↔暖2｜评6↔暖3。热3、热5 无评论单元。

原文拆解 6 单元（39–44）：低保空调类比 / 敢扶细节对照 / 宿舍影响推演 / 幸存者偏差 / 婚恋错位 / 科大三件信物——与前两模块不同题，来源均为新京报、澎湃、浙江宣传、中青评论的近期原文照录。

材料正文与本地资料库的追溯：每则材料来源行标注媒体与日期；对应的天天正能量案例页全文在 `aggr-site/data/wenwen/raw/ttzl-*.json`（如热1 楚亮 = `ttzl-45330.json`，热2 修家电篇内附评论 = `ttzl-45327.json`）。第三模块引用的媒体评论全文是会话期在线抓取的，**不在本地资料库**，原文片段已完整印在刊例中。

## 5. 已知问题（教师反馈，接手后优先核对；不是要保留的规格）

1. **观点页被压成两个观点是执行误读**：观点与推演页应充分给出多个有区别、有依据的方向；最终范本才选一条主线、两个主体段。检查 `content5.py` 的 `views` 字段与生成代码是否有硬编码或自我设限。
2. 各篇仍存在的具体问题（逐篇核对，不要机械替换句子）：
   - 楚亮：问题页引用了已删短材料中没有的原话/婉拒细节；推演页替人物安排"不是要好处"的动机，与范本承认正常认可需求的方向不一致。
   - 椰子水："账"的开头、分段与拆解不完全对应。
   - 葫芦爷爷：立牌提醒不能证明"游客都守分寸"；"不收费"不等于"所有行动没有设计"。
   - 示警稿："第一轮/第二轮"仍是叙事分段；不能把未取得结果的努力排除为"不是帮助"。
   - 救援稿：不写成未成年人可照搬的教程；不由成功反推每步都正确。
   - 幸存者偏差讲解：不能断言失败者都不表达或统计总体多数。
   - 校史示范：仍是"找三样东西"式指令，要补成真正说出来的示范。
3. 任何"检查通过/已重写"的自评不代表通过；以实际文章与页面为准。

## 6. 模型分工（如实记录）

- 刊例的全部编辑文字（材料改写、观点、推演、范本、拆解、解说）由 ZCode 会话中的模型直接撰写，写入 `content*.py`；`ai.json` 里的 GLM 模型只在**站点功能**（AI 热点归纳、暖文分析）中被服务端调用，与刊例文字生成无关；`build*.py` 只做排版。
- 更换为 Antigravity 对话模型后，`aggr-site/ai.json` 的配置不会自动改变；本轮未改动任何模型配置。

## 7. 服务与运行经验（原工作区实测）

| 服务 | 端口 | 启动 | 说明 |
| ---- | ---- | ---- | ---- |
| 聚合站 | 3000（占用自+1，现 3001） | `cd aggr-site && npm start` 或 start-all.sh | 启动即触发 AI 预热与暖文采集调度；副本请加 `AGGR_AUTOTASKS=off` |
| RSSHub | 1200 | `cd rsshub && pnpm dev`（生产 `pnpm start` 需先 build） | 依赖 pnpm；首启需 `pnpm install`；自定义路由已在 lib/routes 内 |
| we-mp-rss | 8001 | Python 服务（start.sh / web.py） | 需 config.yaml（敏感，已随副本在位）与微信授权；本轮未实测 |

健康检查：聚合站 `curl :PORT/api/health`；资料库只读 `curl :PORT/wenwen/api/status`。RSSHub 无需登录；we-mp-rss 涉及微信授权，过期需用户重新扫码，不能承诺复制后永不过期。停止办法：旧工作区用 `stop-all.sh`（不要对副本误用全局 pkill）；副本测试进程按记录的 PID 单独 kill。

自动任务：聚合站启动后每 6h 采集、20min AI 分析、启动时 72h/168h 热点预热（均消耗 GLM API 额度）。付费调用：GLM API（额度与账号见 ai.json，值不外显）。

## 8. 原始来源与上游版本

- 本项目 Git：https://github.com/LiuDaring1/rss-aggregator.git （main @ 70b6fd0）
- RSSHub 上游：https://github.com/DIYgod/RSSHub （本地为固定副本，无 .git；package.json 版本 1.0.0 为本地标记，非上游版本号；恢复办法=按本目录源码使用，或上游对应版本的 lib 覆盖后装入 `upstream-custom/rsshub-routes/` 内 10 个路由文件到 `lib/routes/` 对应子目录，bjnews_utils_PATCHED.ts → `lib/routes/bjnews/utils.ts`）
- we-mp-rss 上游：https://github.com/rachelos/we-mp-rss （本地含多处本机适配文件，如 requirements-314.txt、FIX_CASCADE_CONFIG.md 等；Python 3.13 环境，依赖清单 requirements*.txt，原 .venv 未复制，需重建）
- 自定义改动总览见 `自定义改动清单.md`（原工作区维护，已随副本）。

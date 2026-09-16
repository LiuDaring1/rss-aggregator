# CHECKS_AND_MANIFEST｜打包与验证记录

打包执行：ZCode，2026-09-16 11:20–11:45。原工作区 `/Users/baiyanglin/Desktop/RSS订阅-zcode` 全程未修改（Git 状态前后一致：main @ 70b6fd0 干净且与 origin/main 同步）。

## 一、来源状态

| 项 | 结果 |
| ---- | ---- |
| 原工作区 Git | main @ 70b6fd0（rev.5），12 个提交，origin/main 同步，无未提交修改、无未跟踪遗漏（唯一下文记录的例外见第五节） |
| 运行中服务 | 聚合站 :3001（PID 17905）、RSSHub :1200（PID 79386）——原样保留，未停止、未重启、未写入 |
| package.sh | 已核对：面向公开源码分享（剔除 data、ai.json、.git、weekly 等），**不适用**于本次交接，未使用、未改动 |

## 二、复制清单

| 目标（副本内） | 来源 | 内容 |
| ---- | ---- | ---- |
| `project/`（Git 克隆） | 原仓库 `git clone --no-hardlinks` | 12 个提交完整历史；remotes：origin=GitHub（存档），zcode-local-machine=原工作区路径 |
| `project/aggr-site/data/wenwen/` | 原工作区（.gitignore 忽略项） | db.json＋raw/ **275 篇全文**＋索引；快照时间 2026-09-16 11:30:14 |
| `project/aggr-site/data/*.tar.gz` | 同上 | 2026-09-04 两份历史备份 |
| `project/aggr-site/ai.json`（600 权限） | 同上 | GLM API 配置；镜像在 `_private/aggr-site-ai.json` |
| `project/aggr-site/node_modules/` | 同上 | 2.1MB，同机同架构，副本可立即运行 |
| `project/rsshub/` | 同上（**剔除 node_modules**，源码 36MB） | 含 lib/routes 内 10 个自研/改造路由的实际安装位置 |
| `project/we-mp-rss/` | 同上（**剔除 .venv**（646MB）、__pycache__、日志） | 源码 16MB＋data/（授权数据）＋config.yaml（敏感） |
| `project/upstream-custom/`、`docs/`、`.github/`、`使用说明.md`、`聚合站使用说明.md`、`自定义改动清单.md` | Git 跟踪或未跟踪原件 | 全部随克隆或显式复制 |
| `references/teaching-private/`（10 个文件） | 参考包 | 教学原件，字节未变（抽样哈希与包内索引一致） |
| `references/historical-briefs/`（9 个文件）、`references/handoff-pack/`（4 个文件） | 参考包 | 历史任务书与本次交接任务书 |
| `CURRENT_REQUIREMENTS.md` | 参考包 02 文件 | 当前唯一有效编辑要求 |
| `_private/` | 原工作区 | aggr-site-ai.json、we-mp-rss-config.yaml（均 600 权限，不提交 Git） |

未复制：各处 node_modules（aggr-site 除外）、we-mp-rss/.venv、日志、`__pycache__`、.DS_Store——均可按清单重建（HANDOVER §2/§8）。

## 三、关键哈希（SHA-256 前 16 位）

| 文件 | 哈希 |
| ---- | ---- |
| `project/aggr-site/data/wenwen/db.json` | `fbcc2dc203948404…` |
| `project/weekly/sample-01-rev5/sample.pdf`（归档成品，未覆盖） | `fee4266e34a46e78…` |
| `project/aggr-site/ai.json` | `be96b97a487b3562…` |
| `references/teaching-private/2分钟即兴表达教材….pdf` | `21227bbf0781e344…`（与参考包 03 索引一致） |
| `references/teaching-private/课堂记录.md` | `1ee9a7c7dff1d28c…`（与参考包 03 索引一致） |

## 四、验证结果（通过 / 失败 / 未测 分列）

| 检查 | 结果 | 说明 |
| ---- | ---- | ---- |
| 数据快照一致性 | **通过** | db.json 解析成功，270 个事件；raw 275 篇与源一致；快照 2026-09-16 11:30:14 |
| 完整新闻正文可读 | **通过** | `raw/ttzl-45330.json`（rev.5 热1 来源，合肥晚报）1103 字全文＋标题＋链接可读 |
| 完整评论原文可读 | **通过** | `raw/ttzl-45327.json` 内附媒体评论《抚时感事丨一把螺丝刀…》523 字全文可读；可从 rev.5 材料页追溯到该文件 |
| 刊例重新生成 | **通过** | 副本临时目录执行 `python3 build5.py toc-pages.json && ./render.sh` → 45 页，与归档 sample.pdf **逐页文本一致**；归档成品未被覆盖；临时目录已清理 |
| 既有测试 | **通过** | 副本内 `npm test`：15 pass / 0 fail（离线，node_modules 随副本） |
| 站点只读启动 | **通过** | `AGGR_AUTOTASKS=off PORT=3467 node server.js`：首页 200；`/wenwen/api/status` 200（读取副本数据）；启动日志确认 AI 预热与采集调度已禁用；测试进程已按 PID 停止 |
| Git 边界 | **通过** | 本轮未推送、未 force push；project 远端 origin=GitHub；server.js 差异仅为副本的调度开关（diff 已留存于本文件下文）；私密配置与课堂原件不在 Git 跟踪内 |
| we-mp-rss 启动 | **未测**（涉及微信授权登录态） | 源码、config.yaml（镜像在 _private）、data/ 已复制；需用户重新扫码验证 |
| RSSHub 启动（副本内） | **未测** | 源码与路由已复制；首次运行需 `pnpm install`；原工作区实例仍在 1200 端口运行 |
| GLM API 调用 | **未测**（不批量调用） | ai.json 在位；站点 AI 功能未在本轮触发 |
| 旧任务书 sandbox 链接 | **失效**（如实记录） | 历史任务书内的旧下载链接不可用，以本目录实际文件为准 |

## 五、副本唯一代码差异（对照原工作区）

`project/aggr-site/server.js` 启动块增加 `AGGR_AUTOTASKS=off` 环境开关（跳过 AI 热点预热与暖文雷达采集/分析调度）；设为其他值或不设时行为与原版一致。diff：

```diff
464,467d463
<   // 交接适配（仅本副本）：设 AGGR_AUTOTASKS=off 可禁用 AI 预热与暖文雷达定时采集/分析，避免写库与 API 调用
<   if (process.env.AGGR_AUTOTASKS === 'off') {
<     console.log('[aggr-site] AGGR_AUTOTASKS=off：已跳过 AI 热点预热与暖文雷达调度（交接验证模式）');
<   } else {
476d471
<   }
```

## 六、缺失与遗留（不伪造"已交接"）

1. **媒体评论全文不在本地资料库**：红星、澎湃、新京报等评论原文是历次会话在线抓取的，本地只有天天正能量案例页全文（部分内附媒体评论文本，如 ttzl-45327）。第三模块引用的原文片段已完整印在刊例内，但如需整篇原文需重新在线获取。
2. **rev.5 目录缺 `illustration-briefs.md` 提交**：原工作区该文件未提交（rev.4 版内容即本期所需，R01 已是楚亮题）。副本已将 rev.4 版放入 `project/weekly/sample-01-rev5/illustration-briefs.md`，使 rev.5 文档链接生效；原仓库是否补提交由用户决定。
3. **we-mp-rss 授权与启动未验证**：涉及微信扫码，需用户参与。
4. **ZCode 会话内部记忆**（逐轮教师反馈细节中未落盘的部分）不可导出，不在交接范围；可从 CURRENT_REQUIREMENTS 与 references 恢复的部分均已恢复。

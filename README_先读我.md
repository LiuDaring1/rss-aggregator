# 先读我｜口语素材周刊 → Antigravity 交接目录

**这是什么**：一份给高中播音艺考生的可打印口语素材周刊（复述 / 评论 / 原文拆解与积累），及其背后的评论聚合站、暖文雷达和本地资料库。之前由 ZCode 开发与制作，现在交由 Google Antigravity 继续内容改进。

**为什么换 Agent**：教师对当前评论质量仍不满意——特别是观点页被压缩成两个观点（执行误读，不是教师要求）。换 Agent 是一次新尝试，不代表新模型必然更好；教师认可的是调整方向，不是任何已有成稿。

## 阅读顺序（务必按此顺序）

1. `CURRENT_REQUIREMENTS.md` —— 当前唯一有效的编辑要求（教师最新澄清优先于一切历史文件）。
2. `references/historical-briefs/` 与 `references/handoff-pack/` —— 历史任务书与本次交接任务书，只作背景；与 CURRENT_REQUIREMENTS 冲突时以最新澄清为准。
3. `references/teaching-private/` —— 教学原件（教材、课堂记录、学生示范）。**只作用户本机私密资料，不得提交任何公开仓库。**
4. `project/weekly/sample-01-rev5/` —— 当前审阅基线（45 页）。**未获教师内容定稿**；`sample-01/` 至 `sample-01-rev4/` 为历史版本，仅供对照，不要当作最新稿。
5. `HANDOVER.md` —— 实际工程结构、命令、数据位置、已知问题。
6. `CHECKS_AND_MANIFEST.md` —— 本次打包与验证的真实记录（通过/失败/未测分开写）。

## 目录职责

| 目录 | 性质 | 说明 |
| ---- | ---- | ---- |
| `project/` | 可编辑项目副本（Git） | 聚合站＋暖文雷达＋周刊源码＋完整历史；含未入 Git 的本地数据、上游源码与依赖 |
| `references/` | 私密教学资料＋历史规范 | 课堂原件含学生信息，禁止公开 |
| `_private/` | 本机敏感配置镜像 | `aggr-site-ai.json`、`we-mp-rss-config.yaml`；值不要外显，不要提交 |

## 已验证的命令（在 `project/` 内）

```bash
# 重新生成当前刊例（注意：必须带页码参数，否则目录页码为占位符）
cd weekly/sample-01-rev5
python3 build5.py toc-pages.json
./render.sh                 # 调用 Chrome 无头打印 → sample.pdf（45 页）

# 运行聚合站测试（15 项，离线）
cd aggr-site && npm test

# 只读启动副本站点（禁用 AI 预热与采集调度，独立端口）
AGGR_AUTOTASKS=off PORT=3467 node server.js
```

## 默认不会启动的东西

- 旧工作区（`~/Desktop/RSS订阅-zcode`）的两个服务（聚合站 :3001、RSSHub :1200）**仍在运行，不要动**。
- 本副本默认关闭 AI 预热与采集调度（`AGGR_AUTOTASKS=off`）；需要采集时去掉该开关并确认写入的是**副本**数据目录。
- 不自动推送 GitHub；副本 remote：`origin` = GitHub 仓库（仅存档），`zcode-local-machine` = 原工作区路径。

## 已知缺口（诚实清单）

- we-mp-rss（微信公众号 RSS）：源码与数据已复制，但**未实测启动**（涉及微信授权登录态）。
- RSSHub：源码与自研路由已复制，本副本**未启动过**；首次使用需 `pnpm install`。
- 各媒体评论的**全文原文**（红星、澎湃、新京报等）是此前会话在线抓取的，不在本地资料库；资料库存有的是天天正能量案例页全文（部分内附媒体评论文本）。刊例第三模块引用的原文片段已完整印在刊例内。
- ZCode 会话内部记忆不可导出，不在交接范围。

## 给 Antigravity 的首次接手指令

见本文件末尾的「首次接手指令」，或使用 `references/handoff-pack/01_Antigravity_首次接手指令.txt`（两者内容一致，以本文件版本为准）。

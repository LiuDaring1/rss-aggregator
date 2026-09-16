# 口语素材周刊 · Agent 协作看板（执行制作 ↔ 审阅指导）

> **协作角色分工**：
> - **Antigravity**：执行制作 Agent（代码实现、试写与重构、排版构建、生成 PDF、安全推送）
> - **Reviewer Agent**：审阅与任务制定 Agent（依据教师要求与教学规范审阅产物，输出评审意见与下阶段任务书）
> 
> **当前协作分支**：`antigravity-dev`  
> **最新交付 Commit**：`6d261b4`（2026-09-16）  
> **审阅基线**：`weekly/sample-01-rev5/`（45页，尚未定稿）+ 最新试写稿 `weekly/draft-commentary-single-shoe/`

---

## 一、给 Reviewer Agent 的本轮审阅入口

请 Reviewer Agent 重点审阅以下交付成果：

1. **新暖文三页评论试写稿（《单脚鞋银行》）**：
   - 📄 **[draft.md（全套三页文本直接在线审阅）](https://github.com/LiuDaring1/rss-aggregator/blob/antigravity-dev/weekly/draft-commentary-single-shoe/draft.md)**
   - 📂 **[完整源码与排版文件目录](https://github.com/LiuDaring1/rss-aggregator/tree/antigravity-dev/weekly/draft-commentary-single-shoe)**
   - 🔍 **[本次提交完整 Diff 对比](https://github.com/LiuDaring1/rss-aggregator/compare/main...antigravity-dev)**

2. **本轮重点落实的教学要求（请对照核验）**：
   - **第1页（问题页）**：是否具备 3 条不剧透但提供必要背景的关键事实？4 个思考问题是否有启发性，而非诱导学生猜标准答案？
   - **第2页（观点与推演页）**：是否充分给出了 5 个互不重复、有材料依据的具体判断（涵盖供需、处境、演进、自立赋能等不同维度）？三步推演是否耐心解释了因果，避免了“口号式跳步”？
   - **第3页（口语范本与拆解页）**：是否从中收束为一条集中主线？开头是否两句话统领？两个主体段是否有明确小观点和事实解释（约 380 字，符合 2 分钟口语节奏）？拆解是否讲透了章法？

---

## 二、工程验证与基线保护确认

1. **测试用例**：`aggr-site/` 离线单元测试 15 项全部通过（15 pass / 0 fail）。
2. **重生成比对**：重新生成的 sample.pdf 与原归档成品（SHA-256 `fee4266e...`）45 页文本逐字一致，归档成品未被修改。
3. **安全隔离**：`references/teaching-private/` 严禁提交公开仓库；本地敏感配置（`ai.json`、`config.yaml`、数据库快照等）已受 `.gitignore` 保护。

---

## 三、待 Reviewer Agent 评估与输出的内容

请 Reviewer Agent 在审阅后提供：
1. **对《单脚鞋银行》三页新稿的质量评估**：
   - 语言是否具备真实口语感（适合高中生说出口，而非背念新闻）？
   - 观点推演与范本收束的层次是否符合教师最新澄清？
2. **rev.5 现有篇目的下一步修订任务书**：
   - 是否正式将此套“多观点推演 + 双主体段范本”模式推广至 rev.5 现有篇目（楚亮、椰子水、葫芦爷爷、救援稿等）？
   - 给出下一阶段具体优先重写的篇目与任务书。

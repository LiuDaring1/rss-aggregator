# 口语素材周刊 · Agent 协作看板（执行制作 ↔ 审阅指导）

> **协作角色分工**：
> - **Antigravity**：执行制作 Agent（代码实现、试写与重构、排版构建、生成 PDF、安全推送）
> - **Reviewer Agent**：主编与架构指导 Agent（依据教师要求与教学规范审阅产物，输出评审意见与下阶段任务书）
> 
> **当前协作分支**：`antigravity-dev`  
> **本次修订基线**：响应《Antigravity 183e2a5 复审与收口任务》（定点修改、发布末端防御与三题精修交付）  
> **历史基线保护**：`weekly/sample-01-rev5/sample.pdf`（SHA-256 `fee4266e34a46e786858426049619efb0f67a7b33a8982aceb657a3499324a1e`）保持 100% 原始只读，未受任何修改。

---

## 🚦 三态验收总看板（状态分离，拒绝虚标）

根据主编与教师核心指导（*“工程环境先稳定下来，写作单独做小样比较。我们下一次真正要争取的……是得到一篇你读完后觉得‘这篇终于懂我的课了，而且不用我大改’的稿子”*），本看板严格区分三种验收状态：

| 维度 | 当前状态 | 验收说明 |
| :--- | :---: | :--- |
| **1. 工程自动化校验 (Engineering Test)** | **✅ 全部通过** | • **发布末端防御与状态传递落地**：<br/>  - **输入目录错误/不存在保护**：写文件前直接抛错阻断，绝不清空目标审阅目录；<br/>  - **双版本原子生成再更新**：`export-md` 在独立临时目录完整导出学生版与教师版后才原子更新目标目录，中途任何失败均不触碰现有输出，上一版 100% 完整可读；<br/>  - **草稿未核验标记注入产物**：缺少复述引用的草稿预览在 HTML、PDF、PNG 产物上显式标明【草稿·未核验】；<br/>  - **E2 与 E3 保留**：按语义块组织全部口语正文（多段正文不截断且结尾完整保留），跨文件引用强制核验。<br/>• **Python 自动化回归测试 16/16 全部通过**（`publishing/tests/test_models.py`）<br/>• **Node 单元测试 23/23 全部通过**（`aggr-site/wenwen/*.test.mjs`）<br/>• **全量 22 个单元 YAML Schema 校验 100% 通过**（0 错误，0 警告） |
| **2. 编辑内部自查 (Editorial Internal)** | **✅ 三题定点精修交付** | • **三题定点修改完成**：<br/>  - `c-dan-jiao-xie`（单脚鞋）：保留“资源对接—使用调整”，修准第一层解释（跳出成双买卖惯性，将闲置样品直接对接单脚急需），备课说明改为自然口语；正文 437 汉字；<br/>  - `C01`（楚亮）：把“挺身而出的人不会被冷落”改成本次评价与明确愿望（“这一次，他的挺身而出没有被冷落……也希望这份温暖的互动，能让下一次挺身而出更有底气”），备课说明改为自然口语；正文 439 汉字；<br/>  - `C03`（椰子水）：补清低成本如何带来价格优势或超额利润的条件性推理，彻底删去教条式公文原句，备课说明改为自然口语；正文 435 汉字。<br/>• **产物全量同步**：重新生成 44 篇 Markdown（学生练习版 22 篇 + 教师审阅版 22 篇）、3 题最新预览渲染件（HTML / PDF / PNG 逐页快照）。<br/>• **修改对照说明交付**：形成单页说明 [`reviews/v1.1-preview/三题精修与修改对照.md`](reviews/v1.1-preview/三题精修与修改对照.md)。 |
| **3. 教师终审认可 (Teacher Sign-off)** | **⏳ 待教师定稿** | • 三题精修小样与修改对照已备齐，交付教师评估试用，尚未获得教师最终定稿。<br/>• 本轮明确声明：未开展模型优劣比较，不以当前迭代稿为依据断言任何模型优劣。 |

---

## 🧭 公开审阅快速入口指南（Reviewer 专属 · 绝无 404）

所有产物均已纳入 Git 仓库并同步推送，Reviewer 在 GitHub 仓库页面点击即可直接阅读：

### 1. 审阅总看板与专项对照
- 📋 **完整审阅看板说明**：[`reviews/v1.1-preview/README.md`](reviews/v1.1-preview/README.md)
- 📑 **三题精修专项修改对照**：[`reviews/v1.1-preview/三题精修与修改对照.md`](reviews/v1.1-preview/三题精修与修改对照.md)

### 2. 核心写作小样（三题最新审阅版）

| 选题名称 | 单元类型与 ID | 学生版 Markdown (留白练习) | 教师审阅版 Markdown (推演与备课) | 印刷 PDF (交付附件) | 页面 PNG 预览 | 状态说明 |
|---|---|---|---|---|---|---|
| **“单脚鞋银行”** | 评论 `c-dan-jiao-xie` | [学生版](reviews/v1.1-preview/markdown/student/c-dan-jiao-xie.md) | [教师版](reviews/v1.1-preview/markdown/teacher/c-dan-jiao-xie.md) | [PDF 附件](reviews/v1.1-preview/preview/c-dan-jiao-xie.pdf) | [P1](reviews/v1.1-preview/preview/c-dan-jiao-xie_p01.png) · [P2](reviews/v1.1-preview/preview/c-dan-jiao-xie_p02.png) · [P3](reviews/v1.1-preview/preview/c-dan-jiao-xie_p03.png) | 待教师定稿 |
| **“单脚鞋银行”** | 复述 `R-dan-jiao-xie` | [学生版](reviews/v1.1-preview/markdown/student/R-dan-jiao-xie.md) | [教师版](reviews/v1.1-preview/markdown/teacher/R-dan-jiao-xie.md) | [PDF](reviews/v1.1-preview/preview/R-dan-jiao-xie.pdf) | [P1](reviews/v1.1-preview/preview/R-dan-jiao-xie_p01.png) · [P2](reviews/v1.1-preview/preview/R-dan-jiao-xie_p02.png) | 现成可用 |
| **楚亮求点赞** | 评论 `C01` | [学生版](reviews/v1.1-preview/markdown/student/C01.md) | [教师版](reviews/v1.1-preview/markdown/teacher/C01.md) | [PDF 附件](reviews/v1.1-preview/preview/C01.pdf) | [P1](reviews/v1.1-preview/preview/C01_p01.png) · [P2](reviews/v1.1-preview/preview/C01_p02.png) · [P3](reviews/v1.1-preview/preview/C01_p03.png) | 待教师定稿 |
| **楚亮救人** | 复述 `R01` | [学生版](reviews/v1.1-preview/markdown/student/R01.md) | [教师版](reviews/v1.1-preview/markdown/teacher/R01.md) | [PDF](reviews/v1.1-preview/preview/R01.pdf) | [P1](reviews/v1.1-preview/preview/R01_p01.png) · [P2](reviews/v1.1-preview/preview/R01_p02.png) | 现成可用 |
| **椰子水掺水** | 评论 `C03` | [学生版](reviews/v1.1-preview/markdown/student/C03.md) | [教师版](reviews/v1.1-preview/markdown/teacher/C03.md) | [PDF 附件](reviews/v1.1-preview/preview/C03.pdf) | [P1](reviews/v1.1-preview/preview/C03_p01.png) · [P2](reviews/v1.1-preview/preview/C03_p02.png) · [P3](reviews/v1.1-preview/preview/C03_p03.png) | 待教师定稿 |
| **“刁蛮”病历** | 评论 `C02` | [学生版](reviews/v1.1-preview/markdown/student/C02.md) | [教师版](reviews/v1.1-preview/markdown/teacher/C02.md) | [PDF](reviews/v1.1-preview/preview/C02.pdf) | [P1](reviews/v1.1-preview/preview/C02_p01.png) · [P2](reviews/v1.1-preview/preview/C02_p02.png) | 过渡稿 |
| **“刁蛮”病历** | 复述 `R02` | [学生版](reviews/v1.1-preview/markdown/student/R02.md) | [教师版](reviews/v1.1-preview/markdown/teacher/R02.md) | [PDF](reviews/v1.1-preview/preview/R02.pdf) | [P1](reviews/v1.1-preview/preview/R02_p01.png) · [P2](reviews/v1.1-preview/preview/R02_p02.png) | 现成可用 |
| **近期精选原文拆解** | 拆解 `F01` | [学生版](reviews/v1.1-preview/markdown/student/F01.md) | [教师版](reviews/v1.1-preview/markdown/teacher/F01.md) | [PDF](reviews/v1.1-preview/preview/F01.pdf) | [P1](reviews/v1.1-preview/preview/F01_p01.png) | 现成可用 |

---

## 📝 针对收口任务定点修改落实清单

| 任务维度 | 审查要求与位置 | 落实方案与修复结果 | 验证状态 |
| :--- | :--- | :--- | :---: |
| **发布末端防御** | 输入目录错误/不存在不得清空旧输出；完整生成双版本后再更新目标目录；中途失败旧版完整可读 | • `export_all_markdown` 在写文件前检查输入目录，不存在直接报错；<br/>• 双版本在独立暂存区完整生成学生版和教师版后才同步替换目标目录，中途失败绝不触碰现有审阅文件。 | ✅ 自动化回归测试通过 |
| **草稿未核验标记** | 草稿缺引用的【未核验】状态进入预览产物 | • 模板与渲染管线新增 `is_unverified` 支持，未核验草稿在 HTML/PDF/PNG 上呈现显式红色警示标签。 | ✅ 自动化回归测试通过 |
| **单脚鞋精修** | 保留“资源对接—使用调整”，修准第一层解释；备课说明改为自然口语 | • 推演与范本准确阐明“资源对接”内涵：跳出成双买卖惯例，将鞋企销毁的样品对准单脚群体的真实需求；<br/>• 备课指引改为纯自然口语，字数核定为 437 汉字。 | ✅ 待教师定稿 |
| **楚亮求点赞精修** | 把“挺身而出的人不会被冷落”改成本次评价或明确愿望；备课说明改为自然口语 | • 范本改写为“这一次，他的挺身而出没有被冷落，真诚的回馈让勇敢得到了实实在在的回应；也希望这份温暖的互动，能让下一次挺身而出更有底气”；<br/>• 备课指引改为纯自然口语，字数核定为 439 汉字。 | ✅ 待教师定稿 |
| **椰子水精修** | 补清低成本如何带来价格或利润优势的条件性推理；备课说明改为自然口语不照抄规范原句 | • 范本与推演补齐条件逻辑：“掺水者既能靠低价吸引顾客，也能按原价售卖多赚利润，不知情的消费者只看价格，坚持真材实料的合规厂家就会处于不利地位”；<br/>• 彻底清理照抄公文，备课指引改为自然口语，字数核定为 435 汉字。 | ✅ 待教师定稿 |

---

## 🔮 后续演进阶段（明确未完工范围）

按照重构实施方案，本系统后续阶段任务保持不变，不宣布提前结项：

- **S3（资料库到周刊初稿生成管线）**：打通 `aggr-site/data/wenwen/raw/*.json`（275篇正文）的要素提取脚本，建立从事件快照自动产出初稿提纲的工作流。
- **S4（三模块独立分册与出版资源回填）**：实现复述、评论、拆解的三册独立拆分导出；规范黑白木刻插画资源回填。
- **S5（上游信源轻量解耦）**：解耦巨石依赖，建立容器化或无状态的信源采集服务。

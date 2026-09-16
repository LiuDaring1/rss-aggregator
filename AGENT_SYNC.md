# 口语素材周刊 · Agent 协作看板（执行制作 ↔ 审阅指导）

> **协作角色分工**：
> - **Antigravity**：执行制作 Agent（代码实现、试写与重构、排版构建、生成 PDF、安全推送）
> - **Reviewer Agent**：主编与架构指导 Agent（依据教师要求与教学规范审阅产物，输出评审意见与下阶段任务书）
> 
> **当前协作分支**：`antigravity-dev`  
> **本次修订基线**：响应《183e2a5 复审结论与本轮收口任务》（针对 Commit `183e2a5` 复审回单的系统性收口与三题精修）  
> **历史基线保护**：`weekly/sample-01-rev5/sample.pdf`（SHA-256 `fee4266e34a46e786858426049619efb0f67a7b33a8982aceb657a3499324a1e`）保持 100% 原始只读，未受任何修改。

---

## 🚦 三态验收总看板（状态分离，拒绝虚标）

根据主编与教师核心指导（*“工程环境先稳定下来，写作单独做小样比较。我们下一次真正要争取的……是得到一篇你读完后觉得‘这篇终于懂我的课了，而且不用我大改’的稿子”*），本看板严格区分三种验收状态：

| 维度 | 当前状态 | 验收说明 |
| :--- | :---: | :--- |
| **1. 工程自动化校验 (Engineering Test)** | **✅ 全部通过** | • **E1 ~ E3 输出一致性硬化落地**：<br/>  - **E1 导出原子性与错误退出码**：`export-md` 全量前置校验，任一非法单元立即返回非零退出码（Exit 1），并经由临时目录原子更新，彻底阻断半新半旧或残留旧文件；<br/>  - **E2 口语范本按语义结构组织**：重写 `export_commentary_markdown`，按开头、主体段遍历与结尾语义块完整导出，多段正文不再被静默截断且结尾完整保留；<br/>  - **E3 跨文件引用强制核验**：`build`、`preview`、`export-md` 统一前置核查 `retelling_ref` 是否存在于当前期或有效复述池中。<br/>• **Python 自动化回归测试 14/14 全部通过**（`publishing/tests/test_models.py`）<br/>• **Node 单元测试 23/23 全部通过**（`aggr-site/wenwen/*.test.mjs`）<br/>• **全量 22 个单元 YAML Schema 校验 100% 通过**（0 错误，0 警告） |
| **2. 编辑内部自查 (Editorial Internal)** | **✅ 三题精修交付** | • **三题小样定向精修完成**：精修 `C01`（楚亮）、`C03`（椰子水）、`c-dan-jiao-xie`（单脚鞋），先写通自然文字再填回 YAML；补足学生可读的中间因果；收准无条件保证；剔除浮夸自评；初步感受改为普通口语话。<br/>• **产物全量更新**：重新生成 44 篇 Markdown（学生练习版 22 篇 + 教师审阅版 22 篇）、3 题精修预览件（HTML / PDF / PNG 逐页快照）。<br/>• **专项修改对照说明交付**：形成单页说明 [`reviews/v1.1-preview/三题精修与修改对照.md`](reviews/v1.1-preview/三题精修与修改对照.md)。 |
| **3. 教师终审认可 (Teacher Sign-off)** | **⏳ 待教师定稿** | • 三题精修小样与修改对照已备齐，交付教师评估试用，尚未获得教师最终定稿。<br/>• 本轮明确声明：未开展模型优劣比较，不以当前迭代稿为依据断言任何模型优劣。 |

---

## 🧭 公开审阅快速入口指南（Reviewer 专属 · 绝无 404）

所有产物均已纳入 Git 仓库并同步推送，Reviewer 在 GitHub 仓库页面点击即可直接阅读：

### 1. 审阅总看板与专项对照
- 📋 **完整审阅看板说明**：[`reviews/v1.1-preview/README.md`](reviews/v1.1-preview/README.md)
- 📑 **三题精修专项修改对照**：[`reviews/v1.1-preview/三题精修与修改对照.md`](reviews/v1.1-preview/三题精修与修改对照.md)

### 2. 核心写作小样（三题最新审阅版）

| 选题名称 | 单元类型与 ID | 学生版 Markdown (留白练习) | 教师审阅版 Markdown (推演与备课) | 印刷 PDF | 页面 PNG 预览 | 状态说明 |
|---|---|---|---|---|---|---|
| **“单脚鞋银行”** | 评论 `c-dan-jiao-xie` | [学生版](reviews/v1.1-preview/markdown/student/c-dan-jiao-xie.md) | [教师版](reviews/v1.1-preview/markdown/teacher/c-dan-jiao-xie.md) | [PDF](reviews/v1.1-preview/preview/c-dan-jiao-xie.pdf) | [P1](reviews/v1.1-preview/preview/c-dan-jiao-xie_p01.png) · [P2](reviews/v1.1-preview/preview/c-dan-jiao-xie_p02.png) · [P3](reviews/v1.1-preview/preview/c-dan-jiao-xie_p03.png) | 待教师定稿 |
| **“单脚鞋银行”** | 复述 `R-dan-jiao-xie` | [学生版](reviews/v1.1-preview/markdown/student/R-dan-jiao-xie.md) | [教师版](reviews/v1.1-preview/markdown/teacher/R-dan-jiao-xie.md) | [PDF](reviews/v1.1-preview/preview/R-dan-jiao-xie.pdf) | [P1](reviews/v1.1-preview/preview/R-dan-jiao-xie_p01.png) · [P2](reviews/v1.1-preview/preview/R-dan-jiao-xie_p02.png) | 现成可用 |
| **楚亮求点赞** | 评论 `C01` | [学生版](reviews/v1.1-preview/markdown/student/C01.md) | [教师版](reviews/v1.1-preview/markdown/teacher/C01.md) | [PDF](reviews/v1.1-preview/preview/C01.pdf) | [P1](reviews/v1.1-preview/preview/C01_p01.png) · [P2](reviews/v1.1-preview/preview/C01_p02.png) · [P3](reviews/v1.1-preview/preview/C01_p03.png) | 待教师定稿 |
| **楚亮救人** | 复述 `R01` | [学生版](reviews/v1.1-preview/markdown/student/R01.md) | [教师版](reviews/v1.1-preview/markdown/teacher/R01.md) | [PDF](reviews/v1.1-preview/preview/R01.pdf) | [P1](reviews/v1.1-preview/preview/R01_p01.png) · [P2](reviews/v1.1-preview/preview/R01_p02.png) | 现成可用 |
| **椰子水掺水** | 评论 `C03` | [学生版](reviews/v1.1-preview/markdown/student/C03.md) | [教师版](reviews/v1.1-preview/markdown/teacher/C03.md) | [PDF](reviews/v1.1-preview/preview/C03.pdf) | [P1](reviews/v1.1-preview/preview/C03_p01.png) · [P2](reviews/v1.1-preview/preview/C03_p02.png) · [P3](reviews/v1.1-preview/preview/C03_p03.png) | 待教师定稿 |
| **“刁蛮”病历** | 评论 `C02` | [学生版](reviews/v1.1-preview/markdown/student/C02.md) | [教师版](reviews/v1.1-preview/markdown/teacher/C02.md) | [PDF](reviews/v1.1-preview/preview/C02.pdf) | [P1](reviews/v1.1-preview/preview/C02_p01.png) · [P2](reviews/v1.1-preview/preview/C02_p02.png) | 过渡稿 |
| **“刁蛮”病历** | 复述 `R02` | [学生版](reviews/v1.1-preview/markdown/student/R02.md) | [教师版](reviews/v1.1-preview/markdown/teacher/R02.md) | [PDF](reviews/v1.1-preview/preview/R02.pdf) | [P1](reviews/v1.1-preview/preview/R02_p01.png) · [P2](reviews/v1.1-preview/preview/R02_p02.png) | 现成可用 |
| **近期精选原文拆解** | 拆解 `F01` | [学生版](reviews/v1.1-preview/markdown/student/F01.md) | [教师版](reviews/v1.1-preview/markdown/teacher/F01.md) | [PDF](reviews/v1.1-preview/preview/F01.pdf) | [P1](reviews/v1.1-preview/preview/F01_p01.png) | 现成可用 |

---

## 📝 针对《183e2a5 复审结论与本轮收口任务》落实清单

| 任务维度 | 审查要求与位置 | 落实方案与修复结果 | 验证状态 |
| :--- | :--- | :--- | :---: |
| **E1** | `export-md` 不得跳过坏稿仍报成功，失败不得遗留半新半旧旧稿伪装完整 | • 全量前置校验所有单元，任一失败抛出 `ValueError` 阻断并由 CLI 返回 Exit 1；<br/>• 采用 `tempfile.TemporaryDirectory` 生成完整新文件后原子性同步并清理目标目录旧 `.md` 文件。 | ✅ 自动化回归测试通过 |
| **E2** | 不能按数组前四项机械导出口语范本，杜绝多段正文导致结尾被漏或主体被标错 | • 规范化口语范本导出逻辑，直接通过 `speech.main_claim`、遍历 `speech.body` 的段落并独立输出 `speech.closing`；<br/>• 多段主体情况下完整保留所有文字与结尾，字数统计覆盖全量。 | ✅ 自动化回归测试通过 |
| **E3** | 跨文件复述引用核验应在真正输出时执行 | • 在 `export-md`、`cmd_build`、`cmd_preview` 中显式传递 `available_retellings` 参与前置校验；<br/>• 引用不存在时严格报错阻断，单篇草稿预览提示【未核验】。 | ✅ 自动化回归测试通过 |
| **C01 精修** | 楚亮求点赞：收准语气与推论，删去无条件保证与浮夸修辞，补齐瞬间代价成立推导 | • 讲透冲上前接住孩子承受疼痛，善举与代价在瞬间成立，求夸人之常情不减善举价值；<br/>• 删去“绝不会被冷落”无条件保证，将“机制托底”落实为“专项奖励与社会积极信号”；<br/>• 剔除“实锤代价、闭环”等空泛词；字数核定为 431 汉字。 | ✅ 待教师定稿 |
| **C03 精修** | 椰子水：补齐货架前无法化验与价格竞争等中间推理，统一治理表述，删生硬概念 | • 补足货架前无法化验 $\to$ 消费者依赖配料表 $\to$ 掺水降低原料成本但借纯汁名义维持售价 $\to$ 合规企业处于价格劣势的生活逻辑；<br/>• 统一定性为“让违规需要承担的代价足以抵消其图谋的好处”；<br/>• 剔除“逆向淘汰、痛感代价、商誉账本”等生硬概念；字数核定为 430 汉字。 | ✅ 待教师定稿 |
| **单脚鞋精修** | 展开两层思考推导，删套话黑话，澄清2025年30只事实边界，优化结尾 | • 推演补全第一层打破常规买卖规则对接闲置样品的思考过程；<br/>• 删去“交易惯性、痛点、行动纵深”等词，改用通俗生活用语；<br/>• 严格限定 2025 年 30 只是该团队收到的当期寄送量，不夸大为全社会总需求；<br/>• 结尾由“找鞋”自然演进到“挑鞋、配鞋”；字数核定为 442 汉字。 | ✅ 待教师定稿 |
| **教学页收口** | 初始感受口语化，长诊断入备课备注，拆解删去自评直接指向句子功能 | • 三题初步感受均改为通俗口语，分析说明放入 `editor_notes`（学生版自动隐藏）；<br/>• 拆解直接指出句子在篇章中的承接与说理功能，彻底删去“有力论证、闭环”等泛泛自评。 | ✅ 待教师定稿 |

---

## 🔮 后续演进阶段（明确未完工范围）

按照重构实施方案，本系统后续阶段任务保持不变，不宣布提前结项：

- **S3（资料库到周刊初稿生成管线）**：打通 `aggr-site/data/wenwen/raw/*.json`（275篇正文）的要素提取脚本，建立从事件快照自动产出初稿提纲的工作流。
- **S4（三模块独立分册与出版资源回填）**：实现复述、评论、拆解的三册独立拆分导出；规范黑白木刻插画资源回填。
- **S5（上游信源轻量解耦）**：解耦巨石依赖，建立容器化或无状态的信源采集服务。

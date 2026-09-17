# 口语素材周刊 · Agent 协作看板（执行制作 ↔ 审阅指导）

> **协作角色分工**：
> - **Antigravity**：执行制作 Agent（代码实现、试写与重构、排版构建、生成 PDF、安全推送）
> - **Reviewer Agent**：主编与架构指导 Agent（依据教师要求与教学规范审阅产物，输出评审意见与下阶段任务书）
> 
> **当前协作分支**：`antigravity-dev`  
> **本次修订基线**：响应《Antigravity b7b6a3b 复审与定点处理》（发布末端原子切换与回滚、三题口语化定点修准）  
> **历史基线保护**：`weekly/sample-01-rev5/sample.pdf`（SHA-256 `fee4266e34a46e786858426049619efb0f67a7b33a8982aceb657a3499324a1e`）保持 100% 原始只读，未受任何修改。

---

## 🚦 三态验收总看板（状态分离，拒绝虚标）

根据主编与教师核心指导（*“工程环境先稳定下来，写作单独做小样比较。我们下一次真正要争取的……是得到一篇你读完后觉得‘这篇终于懂我的课了，而且不用我大改’的稿子”*），本看板严格区分三种验收状态：

| 维度 | 当前状态 | 验收说明 |
| :--- | :---: | :--- |
| **1. 工程自动化校验 (Engineering Test)** | **✅ 全部通过** | • **发布末端原子目录切换与失败回滚落地**：<br/>  - **彻底移除逐个覆盖与预先删除**：新批次在独立暂存目录完整生成并记录 SHA-256 清单（`_manifest.json`）后再执行切换；<br/>  - **原子目录切换与自动回滚 (`publish_directory_atomically`)**：发生任何异常时（包含中途系统级错误），自动将备份目录恢复，保证对外审阅入口、文件集合与内容摘要 100% 保持上一版本不变；双版本与单版本统一受保护；<br/>  - **保留先前已通过功能**：输入目录错误阻断防御、草稿未核验标记注入 HTML/PDF/PNG 产物、E2 语义块导出与 E3 引用检查。<br/>• **Python 自动化回归测试 18/18 全部通过**（`publishing/tests/test_models.py`，含双版本生成后故障注入回滚与底层原子重命名回滚）<br/>• **Node 单元测试 23/23 全部通过**（`aggr-site/wenwen/*.test.mjs`）<br/>• **全量 22 个单元 YAML Schema 校验 100% 通过**（0 错误，0 警告） |
| **2. 编辑内部自查 (Editorial Internal)** | **✅ 三题定点修准交付** | • **三题定点口语化与立意修准**：<br/>  - `C01`（楚亮）：提问一删除“救人的事实和代价已经成立”预设结论；主体一替换生硬公文腔，改为自然口语“救人之后大方求夸，不会让已经给出的帮助变轻……”；轻收结尾；正文 415 汉字；<br/>  - `C03`（椰子水）：全篇彻底删除教条公文原句“让违规需要承担的代价足以抵消其图谋的好处”及“蝇头小利”，改为自然口语“不能让掺水比认真做产品更划算”，保留合规厂家吃亏与竞争推导；正文 448 汉字；<br/>  - `c-dan-jiao-xie`（单脚鞋）：彻底删除“做好事第一步是打破常规”与对成双售鞋的无根据归咎，第一层确立为“主动搭起联系桥梁，让闲置物资对准真实需求”；保留第二层使用调整；正文 449 汉字。<br/>• **产物全量同步**：重新导出 44 篇 Markdown（学生练习版 22 篇 + 教师审阅版 22 篇）、重新渲染 3 题最新 HTML / PDF / PNG 逐页快照。<br/>• **修改对照说明交付**：更新单页说明 [`reviews/v1.1-preview/三题精修与修改对照.md`](reviews/v1.1-preview/三题精修与修改对照.md)。 |
| **3. 教师终审认可 (Teacher Sign-off)** | **⏳ 待教师定稿** | • 三题精修小样与修改对照已备齐，三题 PDF 实体文件已作为附件交付供真实翻阅，尚未获得教师最终定稿。<br/>• 本轮明确声明：未开展模型优劣比较，不以当前样本为依据断言任何模型优劣。 |

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
| :--- | :--- | :--- | :--- :---: |
| **发布末端防御** | 消除清空再复制风险；双版本暂存完毕后原子切换；失败自动回滚上一版完整可读 | • 采用 `publish_directory_atomically`：先备份旧目录，再原子重命名暂存目录，失败时立即将备份完整回滚恢复；<br/>• 单版本与双版本统一受此机制保护；落盘 `_manifest.json` 记录文件摘要与数量。 | ✅ 18 项回归测试通过（含两版本生成后故障注入测试） |
| **草稿未核验标记** | 草稿缺引用的【未核验】状态进入预览产物 | • 模板与渲染管线支持 `is_unverified`，在 HTML/PDF/PNG 产物上显式标明【草稿·未核验】。 | ✅ 自动化回归测试通过 |
| **单脚鞋精修** | 删除“做好事第一步是打破常规”通则，不归咎成双售卖规则；聚焦搭起联系桥梁 | • 第一层确立为“主动搭起联系桥梁，让闲置物资对准真实需求”，讲透一边样品闲置销毁、一边单脚买鞋扔一只的错位；<br/>• 保留第二层数量与鞋型使用调整；正文 449 汉字。 | ✅ 待教师定稿 |
| **楚亮求点赞精修** | 提问删去塞入结论；主体一段公文腔改为自然口语；轻收结尾 | • 提问改为生活化提问；<br/>• 主体一段改为“救人之后大方求夸，不会让已经给出的帮助变轻……”；<br/>• 结尾轻收避免机械重复；正文 415 汉字。 | ✅ 待教师定稿 |
| **椰子水精修** | 全篇删除“代价足以抵消图谋好处”公文句与“蝇头小利”；口语化惩戒威慑 | • 替换为自然学生口语“不能让掺水比认真做产品更划算”；<br/>• 结合排查与立案事实，讲透为何严格执法能打消侥幸、保护老实做产品的厂家；正文 448 汉字。 | ✅ 待教师定稿 |

---

## 🔮 后续演进阶段（明确未完工范围）

按照重构实施方案，本系统后续阶段任务保持不变，不宣布提前结项：

- **S3（资料库到周刊初稿生成管线）**：打通 `aggr-site/data/wenwen/raw/*.json`（275篇正文）的要素提取脚本，建立从事件快照自动产出初稿提纲的工作流。
- **S4（三模块独立分册与出版资源回填）**：实现复述、评论、拆解的三册独立拆分导出；规范黑白木刻插画资源回填。
- **S5（上游信源轻量解耦）**：解耦巨石依赖，建立容器化或无状态的信源采集服务。

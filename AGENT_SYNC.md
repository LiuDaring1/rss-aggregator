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
| **1. 工程自动化校验 (Engineering Test)** | **✅ 全部通过（工程收项）** | • **发布末端原子目录切换与失败回滚（已通过 Reviewer 8 项局部故障测试）**：<br/>  - **边界明确收准**：在单进程发布、可捕获异常且文件系统允许回滚的测试场景中，上一版本能够保持或恢复完整；不扩大承诺断电、`kill -9` 或并发竞争安全；日常保持同一时间单进程导出；<br/>  - **原子目录切换与自动回滚 (`publish_directory_atomically`)**：发生任何异常时，自动将备份目录恢复，保证对外审阅入口、文件集合与内容摘要保持不变；双版本与单版本统一受保护；<br/>  - **保留先前已通过功能**：输入目录错误阻断防御、草稿未核验标记注入 HTML/PDF/PNG 产物、E2 语义块导出与 E3 引用检查。<br/>• **Python 自动化回归测试 18/18 全部通过**（`publishing/tests/test_models.py`）<br/>• **Node 单元测试 23/23 全部通过**（`aggr-site/wenwen/*.test.mjs`）<br/>• **全量 22 个单元 YAML Schema 校验 100% 通过**（0 错误，0 警告） |
| **2. 编辑内部自查 (Editorial Internal)** | **✅ 三题定点修准交付** | • **三题定点口语化与立意修准**：<br/>  - `C01`（楚亮）：提问一删除“救人的事实和代价已经成立”预设结论；主体一替换生硬公文腔，改为自然口语“救人之后大方求夸，不会让已经给出的帮助变轻……”；轻收结尾；正文 415 汉字；<br/>  - `C03`（椰子水）：全篇彻底删除教条公文原句“让违规需要承担的代价足以抵消其图谋的好处”及“蝇头小利”，改为自然口语“不能让掺水比认真做产品更划算”；消费端描述收准为“在不知道成分有差别时，顾客可能把它们当成同类产品，再按价格作选择……”；保留合规厂家吃亏与竞争推导；正文 467 汉字；<br/>  - `c-dan-jiao-xie`（单脚鞋）：彻底删除“做好事第一步是打破常规”与对成双售鞋的无根据归咎，第一层确立为“主动搭起联系桥梁，让闲置物资对准真实需求”；保留第二层使用调整；正文 449 汉字。<br/>• **字数与试读时长严格分离**：正文字数仅作静态参考，实际口语朗读时长需结合真人试读检验，未经试读不声称已通过。<br/>• **实体 PDF 交付**：物理交付至桌面文件夹 `/Users/baiyanglin/Desktop/口语素材周刊_三篇试读PDF/`，供用户直接上传至 Reviewer 审阅视觉版面。<br/>• **修改对照说明交付**：更新单页说明 [`reviews/v1.1-preview/三题精修与修改对照.md`](reviews/v1.1-preview/三题精修与修改对照.md)。 |
| **3. 教师终审认可 (Teacher Sign-off)** | **⏳ 待教师定稿（进行有限试用）** | • 三题精修小样与修改对照已备齐，三题独立 PDF 文件已物理交付桌面，供教师与 Reviewer 检查页面并挑选试读。<br/>• 本轮明确声明：未开展模型优劣比较，不以当前样本为依据断言任何模型优劣。 |

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

> 📁 **物理 PDF 独立交付路径（便于用户直接拖拽至 Reviewer 对话中审阅视觉版面）**：  
> 本地桌面目录：`/Users/baiyanglin/Desktop/口语素材周刊_三篇试读PDF/` (`C01.pdf`, `C03.pdf`, `c-dan-jiao-xie.pdf`)

---

## 📝 针对 72f01f7 复审收尾落实清单

| 任务维度 | 审查要求与位置 | 落实方案与修复结果 | 验证状态 |
| :--- | :--- | :--- | :--- :---: |
| **发布异常恢复边界收准** | 将“任何异常100%无损”收准为已验证的可捕获异常回滚；不声称断电或强制终止恢复 | • 文档与函数注解已严谨收准：“在单进程发布、可捕获异常且文件系统允许回滚的测试场景中，上一批次保持或恢复完整”；<br/>• 明确未进行断电、kill -9 或并发发布测试，日常保持单进程运行；Reviewer 8项故障注入测试已通过。 | ✅ 已严格收准 |
| **三题实体 PDF 交付** | 用户需上传文件本身给 Reviewer，交付实际物理文件 | • 物理文件已放置于桌面专属目录 `/Users/baiyanglin/Desktop/口语素材周刊_三篇试读PDF/`，可直接拖拽上传；<br/>• 同时备份于任务包目录及 artifacts 目录。 | ✅ 物理交付就绪 |
| **C03 消费端表达收准** | 改“不知情消费者只看价格……”为条件性描述 | • 收准为“在不知道成分有差别时，顾客可能把它们当成同类产品，再按价格作选择，坚持真材实料的合规厂家就会处于不利地位”；<br/>• 全量更新 Markdown、HTML、PDF 与 PNG 快照。 | ✅ 待教师定稿 |
| **字数统计与试读时间分离** | 自动字数提示与真实试读时间分开，未经试读不声称时长已通过 | • Markdown 导出模板及看板文档统一更新：字数仅为静态参考，实际口语朗读时长需由师生真人试读检验。 | ✅ 规则与产物已同步 |

---

## 🔮 后续演进阶段（明确未完工范围）

按照重构实施方案，本系统后续阶段任务保持不变，不宣布提前结项：

- **S3（资料库到周刊初稿生成管线）**：打通 `aggr-site/data/wenwen/raw/*.json`（275篇正文）的要素提取脚本，建立从事件快照自动产出初稿提纲的工作流。
- **S4（三模块独立分册与出版资源回填）**：实现复述、评论、拆解的三册独立拆分导出；规范黑白木刻插画资源回填。
- **S5（上游信源轻量解耦）**：解耦巨石依赖，建立容器化或无状态的信源采集服务。

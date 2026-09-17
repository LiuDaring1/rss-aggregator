# 口语素材周刊 · Agent 协作看板（执行制作 ↔ 审阅指导）

> **协作角色分工**：
> - **Antigravity**：执行制作 Agent（代码实现、试写与重构、排版构建、生成 PDF、安全推送）
> - **Reviewer Agent**：主编与架构指导 Agent（依据教师要求与教学规范审阅产物，输出评审意见与下阶段任务书）
> 
> **当前协作分支**：`antigravity-dev`  
> **本次修订基线**：响应《00_从小样定标到首期整刊试生产_任务书.md》（完成首期整刊 `issue-2026-w37` 试生产，打通真实备料到组刊最小连接，输出 47 页完整周刊及分册）  
> **历史基线保护**：`weekly/sample-01-rev5/sample.pdf`（SHA-256 `fee4266e34a46e786858426049619efb0f67a7b33a8982aceb657a3499324a1e`）及试读候选三篇（`C01`, `C03`, `c-dan-jiao-xie`）保持 100% 原始冻结，未受任何修改。

---

## 🚦 三态验收总看板（状态分离，拒绝虚标）

根据主编与教师核心指导（*“当前三篇小样和模板已形成试读候选，暂停主动重写。下一阶段转入第一期完整周刊试生产……教师试读现有小样与新一期准备并行”*），本看板严格区分三种验收状态：

| 维度 | 当前状态 | 验收说明 |
| :--- | :---: | :--- |
| **1. 工程自动化校验 (Engineering Test)** | **✅ 全部通过（整刊管线稳定）** | • **确定性离线组刊与印刷构建**：<br/>  - 严格离线、零外部模型调用完成 `issue-2026-w37` 组刊与 47 页 A4 印刷导出；<br/>  - 突破多篇复述参考跨页排版，动态计算答案页与目录页码映射；优化目录排版彻底消除单行溢出，实测 47 页无孤行、无空白跨页；<br/>  - 自动生成 3 模块独立分册 PDF（复述 20 页、评论 18 页、拆解 6 页）；<br/>• **Python 自动化回归测试 18/18 全部通过**（`publishing/tests/test_models.py`）<br/>• **全量 43 个单元 YAML Schema 校验 100% 通过**（22 历史单元 + 21 新期单元，0 错误，0 警告） |
| **2. 编辑内部自查 (Editorial Internal)** | **✅ 首期整刊试生产完成 (issue-2026-w37)** | • **真实时间窗选题与备料完整闭环（2026-09-07 ~ 2026-09-13）**：<br/>  - 9 篇复述（6 篇社会热点 + 3 篇正向生活/暖文，含本地天天正能量 3 篇真实信源）；<br/>  - 6 篇评论（3 篇热点 + 3 篇正向生活，与复述同源，严格执行三页制、4~5 项丰富观点池、两段主体首句加粗、去泛泛自评）；<br/>  - 6 篇原文拆解与积累（独立精选真实深度评论完整语段）；<br/>  - 全刊跨模块反查页码（“材料见第 X 页”、“关联材料见第 X 页”）经 PyMuPDF 实测 100% 精确吻合；<br/>• **插画需求包同步就绪**：输出 9 幅黑白报刊风格叙事插画完整提示词（`illustration-briefs.md`），不阻塞出刊；<br/>• **候选小样冻结保护**：先前 3 篇候选小样保持冻结，等待教师教学反馈。 |
| **3. 教师终审认可 (Teacher Sign-off)** | **⏳ 教师双轨并行审阅中** | • **轨道一（小样回课）**：教师继续在教学现场试读候选三篇（单脚鞋、楚亮、椰子水），收集学生现场开口卡壳词句反馈；<br/>• **轨道二（首期备课）**：首期整刊（`issue-2026-w37` 47页）提供给教学团队作为新一周完整备课与试生产样例，重点审阅 6 篇新评论之立意与推演是否顺畅。 |

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

### 3. 首期整刊试生产交付产物 (`issue-2026-w37` / 2026年9月第2期)

| 交付产物 | 格式与页数 | 文件路径 | 状态与审阅要点 |
|---|---|---|---|
| **首期完整周刊 (合订本)** | A4 印刷 PDF (47 页) | [`issues/issue-2026-w37/issue-2026-w37.pdf`](issues/issue-2026-w37/issue-2026-w37.pdf) | 封面(1)·目录与指令(2)·复述(3-20)·参考(21-22)·评论(23-40)·拆解(41-46)·附录(47) |
| **首期完整周刊 (学生版 MD)** | Markdown 全文 | [`issues/issue-2026-w37/issue-2026-w37.md`](issues/issue-2026-w37/issue-2026-w37.md) | 同源纯文本合订本，含完整材料、提示、观点池、范本及精选段落 |
| **模块一：口语复述分册** | A4 印刷 PDF (20 页) | [`issues/issue-2026-w37/issue-2026-w37-复述.pdf`](issues/issue-2026-w37/issue-2026-w37-复述.pdf) | 9 篇复述（6篇热点+3篇正向生活）及 2 页集中参考答案 |
| **模块二：口语评论分册** | A4 印刷 PDF (18 页) | [`issues/issue-2026-w37/issue-2026-w37-评论.pdf`](issues/issue-2026-w37/issue-2026-w37-评论.pdf) | 6 篇评论，每题 3 页（立意破题·观点推演·口语范本加粗主体） |
| **模块三：原文拆解与积累分册** | A4 印刷 PDF (6 页) | [`issues/issue-2026-w37/issue-2026-w37-原文拆解与积累.pdf`](issues/issue-2026-w37/issue-2026-w37-原文拆解与积累.pdf) | 6 篇独立精选近期深度评论语段与技法分析 |
| **插画需求包** | Markdown 需求清单 | [`issues/issue-2026-w37/illustration-briefs.md`](issues/issue-2026-w37/illustration-briefs.md) | 9 篇复述之黑白报刊风格线描插画标准提示词，不阻塞组刊 |
| **选题与备料清单** | JSON 元数据 | [`issues/issue-2026-w37/manifest_prep.json`](issues/issue-2026-w37/manifest_prep.json) | 2026-09-07~09-13 真实时间窗，覆盖南国今报、钱江晚报等真实报道 |
| **组刊配置清单** | YAML 结构定义 | [`issues/issue-2026-w37/issue.yaml`](issues/issue-2026-w37/issue.yaml) | 规范期号、时间窗口、模块列表与排版对应 |

---

## 📝 针对 2dc9395 实页审阅小修单落实清单

| 任务维度 | 审查要求与位置 | 落实方案与修复结果 | 验证状态 |
| :--- | :--- | :--- | :--- :---: |
| **技术信息清理与规范页眉** | 去掉“【单单元预览】”与长技术ID；题名化关联材料；添加 1/3, 2/3, 3/3 | • 移除预览调试串，统一为“高中口语表达 · 评论单元”；<br/>• `c-dan-jiao-xie` 替换为紧凑题号 `C-单`；<br/>• 关联材料显示为题名《单脚鞋银行》等；每页右上角标注标准页码。 | ✅ 9页全部落实 |
| **第1页思考书写区合理分配** | 扩展每题 7mm 极短单线，放大问题与材料字号，消除大面积未分配留白 | • 每题提供 2~3 行点状书写虚线（行高约 8.5mm）；<br/>• 材料与问题字号适度放大至 11.2~11.5pt，版面布局充实舒展。 | ✅ 3题均收纳良好 |
| **第2页解释正常化与排开** | 依据与说明提升至深色正常阅读层级；排开两行；推演分3段；单脚鞋保住3页 | • 字体提升至 10.2~10.6pt 深色（`#1a1a1a`）；<br/>• 分两行标为“材料中的细节”与“可以怎样理解”，消除“。；说明：”；<br/>• 推演按逻辑转折分 3 段；单脚鞋 5 个观点+3段推演完整容纳在第 2 页，经 PyMuPDF 实测严格 3 页无溢出。 | ✅ 严格收纳于第2页 |
| **第3页范本小观点视觉强化** | 对两段主体小观点首句加粗；统一时长标签 | • 范本主体两段首句通过 `<b>` 加粗强化，在连续正文中一眼看清结构，不打断朗读流；<br/>• 标签更名为“口语范本（两段主体展开）”。 | ✅ 3题均加粗显出 |
| **文句微调与自评清理** | 单脚鞋第2问改双生活细节对比；椰子水第3问改具体解决暗中掺水；清理闭环自评 | • 单脚鞋第2问与椰子水第3问已按审阅意见修改；<br/>• 楚亮教学拆解删除“完成闭环”泛泛自评。 | ✅ YAML与Markdown已同步 |

---

## 📌 验收结论与当前动作准则（基于 ec86509 实页验收）

根据《ec86509｜三篇评论PDF实页验收记录与试用建议》审阅结论：
1. **排版小修正式收项**：9 页逐页核验全部通过，无溢出、无裁字，版面空间分配与阅读层级改善，冻结为**试读候选版本**。
2. **冻结当前模板与正文，暂停主动重写**：保留 `ec86509` 产物与当前模板，不主动重写三篇评论范本，不扩大系统改动。
3. **教师终审三态分离**：自动化通过、编辑自查通过，但教师尚未定稿；等待教师实际 A4 纸面试读与真实回课检验反馈。
4. **两项非阻塞优化记入待办**：不单独发起返工，留待下次正常整刊排版与常规内容编辑时处理。
5. **周边流程照常推进**：已认可的复述（`R-dan-jiao-xie`, `R01`, `R02` 等）照常可用；既定插画流程按计划推进，无需等待整套系统完成。

---

## 📋 非阻塞优化待办清单（下次正常编辑/排版处理，不单独返工）

| 待办编号 | 涉及模块/页面 | 观察现象与优化方案 | 执行时机 |
| :--- | :--- | :--- | :--- |
| **Backlog-A** | 第一页版头布局 (`C01`, `C03` 等) | • **现象**：题号题目与关联材料同行挤占，致使楚亮“真诚给赞”折成“真诚/给赞”，椰子水题名出现短尾行。<br/>• **方案**：下次正常整刊排版时，调整版头排版，使“题号＋题目”独占一行，关联材料移至下一行小字呈现。不缩小主标题字号，不单独发起返工。 | 下次正常整刊排版 |
| **Backlog-B** | 第二页事实与推论分类 (`C03` 椰子水第2观点) | • **现象**：“材料中的细节”栏目前包含“若降价抢占市场或维持售价多获利”等条件性推演，容易混淆事实报道与逻辑推论。<br/>• **方案**：下次正常内容精修时，将条件推演调整至“可以怎样理解”栏，事实栏严格仅保留报道客观事实（标签标称 100% 与实际掺水）。当前句子已有明确“若”字，范本不推翻，不单独发起返工。 | 下次正常内容精修 |

---

## 🔮 后续演进阶段（明确未完工范围）

按照重构实施方案，本系统后续阶段任务保持不变，不宣布提前结项：

- **教师纸面试读与回课意见收集**：以 A4 打印尺寸试读单脚鞋，收集学生卡壳词句，只作局部定点微调。
- **S3（资料库到周刊初稿生成管线）**：打通 `aggr-site/data/wenwen/raw/*.json`（275篇正文）的要素提取脚本，建立从事件快照自动产出初稿提纲的工作流。
- **S4（三模块独立分册与出版资源回填）**：实现复述、评论、拆解的三册独立拆分导出；规范黑白木刻插画资源回填。
- **S5（上游信源轻量解耦）**：解耦巨石依赖，建立容器化或无状态的信源采集服务。


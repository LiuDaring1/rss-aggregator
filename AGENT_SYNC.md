# 口语素材周刊 · Agent 协作看板（执行制作 ↔ 审阅指导）

> **协作角色分工**：
> - **Antigravity**：执行制作 Agent（代码实现、试写与重构、排版构建、生成 PDF、安全推送）
> - **Reviewer Agent**：主编与架构指导 Agent（依据教师要求与教学规范审阅产物，输出评审意见与下阶段任务书）
> 
> **当前协作分支**：`antigravity-dev`  
> **本次修订基线**：响应《ec86509｜实页验收记录与试用建议》（排版小修收项冻结，两项非阻塞优化记入后续正常编辑，转入教师纸面试读）  
> **历史基线保护**：`weekly/sample-01-rev5/sample.pdf`（SHA-256 `fee4266e34a46e786858426049619efb0f67a7b33a8982aceb657a3499324a1e`）保持 100% 原始只读，未受任何修改。

---

## 🚦 三态验收总看板（状态分离，拒绝虚标）

根据主编与教师核心指导（*“工程环境先稳定下来，写作单独做小样比较。我们下一次真正要争取的……是得到一篇你读完后觉得‘这篇终于懂我的课了，而且不用我大改’的稿子”*），本看板严格区分三种验收状态：

| 维度 | 当前状态 | 验收说明 |
| :--- | :---: | :--- |
| **1. 工程自动化校验 (Engineering Test)** | **✅ 全部通过（工程收项）** | • **发布末端原子目录切换与失败回滚（已通过 Reviewer 8 项局部故障测试）**：<br/>  - **边界明确收准**：在单进程发布、可捕获异常且文件系统允许回滚的测试场景中，上一版本能够保持或恢复完整；不扩大承诺断电、`kill -9` 或并发竞争安全；日常保持同一时间单进程导出；<br/>  - **原子目录切换与自动回滚 (`publish_directory_atomically`)**：发生任何异常时，自动将备份目录恢复，保证对外审阅入口、文件集合与内容摘要保持不变；双版本与单版本统一受保护；<br/>  - **保留先前已通过功能**：输入目录错误阻断防御、草稿未核验标记注入 HTML/PDF/PNG 产物、E2 语义块导出与 E3 引用检查。<br/>• **Python 自动化回归测试 18/18 全部通过**（`publishing/tests/test_models.py`）<br/>• **Node 单元测试 23/23 全部通过**（`aggr-site/wenwen/*.test.mjs`）<br/>• **全量 22 个单元 YAML Schema 校验 100% 通过**（0 错误，0 警告） |
| **2. 编辑内部自查 (Editorial Internal)** | **✅ 排版小修已验收收项（候选版冻结）** | • **Reviewer 9 页逐页核验全部通过**（见《00_实页验收记录与试用建议.md》）：<br/>  - A4 竖版各 3 页严格无溢出、无裁字、无越界；<br/>  - 页眉页码、紧凑题号、题名化关联材料、2~3 行书写区、深色解释分行排开、主体两段加粗全部落实；<br/>  - 新旧范本正文对比 100% 一致（楚亮 415 字、椰子水 467 字、单脚鞋 449 字）。<br/>• **候选版本冻结**：保留当前模板与三篇正文，暂停主动重写；两项非阻塞优化已登记入下次正常编辑待办，不单独返工。 |
| **3. 教师终审认可 (Teacher Sign-off)** | **⏳ 教师纸面试读与回课检验中** | • 建议教师优先按 A4 实际尺寸打印《单脚鞋银行》纸质版进行试读，重点检验第 2 页解释学生能否读懂、第 3 页范本是否适合自然开口。<br/>• 在现有回课中检验实际效果，依据具体卡住的词句局部修改；不提前宣布全套教学定稿。 |

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


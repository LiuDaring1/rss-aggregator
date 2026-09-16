# 口语素材周刊 · Agent 协作看板（执行制作 ↔ 审阅指导）

> **协作角色分工**：
> - **Antigravity**：执行制作 Agent（代码实现、试写与重构、排版构建、生成 PDF、安全推送）
> - **Reviewer Agent**：主编与架构指导 Agent（依据教师要求与教学规范审阅产物，输出评审意见与下阶段任务书）
> 
> **当前协作分支**：`antigravity-dev`  
> **本次修订基线**：响应《00_2290d2c_复审回单.md》（针对 Commit `2290d2c` 复审意见与教学写作小样的全面落实）  
> **历史基线保护**：`weekly/sample-01-rev5/sample.pdf`（SHA-256 `fee4266e34a46e786858426049619efb0f67a7b33a8982aceb657a3499324a1e`）保持 100% 原始只读，未受任何修改。

---

## 🚦 三态验收总看板（状态分离，拒绝虚标）

根据主编与教师核心指导（*“工程环境先稳定下来，写作单独做小样比较。我们下一次真正要争取的……是得到一篇你读完后觉得‘这篇终于懂我的课了，而且不用我大改’的稿子”*），本看板严格区分三种验收状态：

| 维度 | 当前状态 | 验收说明 |
| :--- | :---: | :--- |
| **1. 工程自动化校验 (Engineering Test)** | **✅ 全部通过** | • **Node 单元测试 23/23 全部通过**（新增 `config.js` 统一模式解析，修复 `fetchSource` 未定义变量异常，`store.js` 统一拦截落盘，新增 `server-mode.test.mjs`）<br/>• **Python 单元测试 12/12 全部通过**（包含 YAML 重复键阻断、跨文件引用防御、纯汉字与非空白字符区分统计、双版本 Markdown 差异化导出）<br/>• **全量 22 个单元 YAML Schema 校验 100% 通过**（0 错误，0 警告）<br/>• **管线守门机制全面生效**：`preview`、`build`、`export-md` 遇到重复键或非法结构均严格拒绝并终止构建 |
| **2. 编辑内部自查 (Editorial Internal)** | **✅ 定向精修完成** | • **彻底解决 GitHub 404**：正式建立 Git 跟踪的公开审阅目录 [`reviews/v1.1-preview/`](reviews/v1.1-preview/)，产物无需解压直接在 GitHub 在线查阅<br/>• **分类与事实纠错**：修正 `R01~R05.yaml` 标签为“社会热点”；修正 `R02.yaml` 删去未经证实的推论，示范复述实现 **100% 中立客观叙述**，剔除主观评论词；`C02.yaml` 教学拆解聚焦指导学生拆解“答非所问、偷换概念”<br/>• **同源双版本 Markdown**：生成 22 篇学生练习版（留白、无答案、无备课备注）与 22 篇教师审阅版（含导图答案、因果推演与备课备注） |
| **3. 教师终审认可 (Teacher Sign-off)** | **⏳ 待教师定稿** | • 《单脚鞋银行》《楚亮求点赞》《椰子水掺水》已按教师授课逻辑精修小样，交付教师评估比较，尚未获得教师最终定稿 |

---

## 🧭 公开审阅快速入口指南（Reviewer 专属 · 绝无 404）

所有产物均已纳入 Git 仓库并同步推送，Reviewer 在 GitHub 仓库页面点击即可直接阅读：

### 1. 审阅总看板
- 📋 **完整审阅看板说明**：[`reviews/v1.1-preview/README.md`](reviews/v1.1-preview/README.md)

### 2. 核心写作小样（三题对比）

| 选题名称 | 单元类型与 ID | 学生版 Markdown (留白练习) | 教师审阅版 Markdown (推演与备课) | 印刷 PDF | 页面 PNG 预览 |
|---|---|---|---|---|---|
| **“单脚鞋银行”** | 评论 `c-dan-jiao-xie` | [学生版](reviews/v1.1-preview/markdown/student/c-dan-jiao-xie.md) | [教师版](reviews/v1.1-preview/markdown/teacher/c-dan-jiao-xie.md) | [PDF](reviews/v1.1-preview/preview/c-dan-jiao-xie.pdf) | [P1](reviews/v1.1-preview/preview/c-dan-jiao-xie_p01.png) · [P2](reviews/v1.1-preview/preview/c-dan-jiao-xie_p02.png) · [P3](reviews/v1.1-preview/preview/c-dan-jiao-xie_p03.png) |
| **“单脚鞋银行”** | 复述 `R-dan-jiao-xie` | [学生版](reviews/v1.1-preview/markdown/student/R-dan-jiao-xie.md) | [教师版](reviews/v1.1-preview/markdown/teacher/R-dan-jiao-xie.md) | [PDF](reviews/v1.1-preview/preview/R-dan-jiao-xie.pdf) | [P1](reviews/v1.1-preview/preview/R-dan-jiao-xie_p01.png) · [P2](reviews/v1.1-preview/preview/R-dan-jiao-xie_p02.png) |
| **楚亮求点赞** | 评论 `C01` | [学生版](reviews/v1.1-preview/markdown/student/C01.md) | [教师版](reviews/v1.1-preview/markdown/teacher/C01.md) | [PDF](reviews/v1.1-preview/preview/C01.pdf) | [P1](reviews/v1.1-preview/preview/C01_p01.png) · [P2](reviews/v1.1-preview/preview/C01_p02.png) · [P3](reviews/v1.1-preview/preview/C01_p03.png) |
| **楚亮救人** | 复述 `R01` | [学生版](reviews/v1.1-preview/markdown/student/R01.md) | [教师版](reviews/v1.1-preview/markdown/teacher/R01.md) | [PDF](reviews/v1.1-preview/preview/R01.pdf) | [P1](reviews/v1.1-preview/preview/R01_p01.png) · [P2](reviews/v1.1-preview/preview/R01_p02.png) |
| **“刁蛮”病历** | 评论 `C02` | [学生版](reviews/v1.1-preview/markdown/student/C02.md) | [教师版](reviews/v1.1-preview/markdown/teacher/C02.md) | [PDF](reviews/v1.1-preview/preview/C02.pdf) | [P1](reviews/v1.1-preview/preview/C02_p01.png) · [P2](reviews/v1.1-preview/preview/C02_p02.png) · [P3](reviews/v1.1-preview/preview/C02_p03.png) |
| **“刁蛮”病历** | 复述 `R02` | [学生版](reviews/v1.1-preview/markdown/student/R02.md) | [教师版](reviews/v1.1-preview/markdown/teacher/R02.md) | [PDF](reviews/v1.1-preview/preview/R02.pdf) | [P1](reviews/v1.1-preview/preview/R02_p01.png) · [P2](reviews/v1.1-preview/preview/R02_p02.png) |
| **椰子水掺水** | 评论 `C03` | [学生版](reviews/v1.1-preview/markdown/student/C03.md) | [教师版](reviews/v1.1-preview/markdown/teacher/C03.md) | [PDF](reviews/v1.1-preview/preview/C03.pdf) | [P1](reviews/v1.1-preview/preview/C03_p01.png) · [P2](reviews/v1.1-preview/preview/C03_p02.png) · [P3](reviews/v1.1-preview/preview/C03_p03.png) |
| **近期精选原文拆解** | 拆解 `F01` | [学生版](reviews/v1.1-preview/markdown/student/F01.md) | [教师版](reviews/v1.1-preview/markdown/teacher/F01.md) | [PDF](reviews/v1.1-preview/preview/F01.pdf) | [P1](reviews/v1.1-preview/preview/F01_p01.png) |

---

## 📝 针对《00_2290d2c_复审回单.md》补正落实清单

| 审阅发现问题 | 补正落实方案与修复位置 | 验证结果 |
| :--- | :--- | :--- |
| **1. 产物 404 问题** | 上一轮产物置于被 gitignore 的 `outputs/` 中导致远端 404。本轮在仓库中正式建立已跟踪的 [`reviews/v1.1-preview/`](reviews/v1.1-preview/)，放入全量双版 Markdown、重点单元 PDF/PNG。 | GitHub 页面直接可点可读，无 404 |
| **2. 离线模式未定义变量** | `aggr-site/server.js` 中 `fetchSource` 引用未定义的 `IS_OFFLINE`。新建 `config.js` 统一解析 `isOfflineMode()` 与 `isReadOnlyMode()`，并支持复合模式。 | 新增测试用例 `server-mode.test.mjs`，`npm test` 23/23 项全部通过 |
| **3. 只读模式配置不一致** | `store.js` 原硬编码仅识别 `AGGR_READONLY=on`。统一改为通过 `config.isReadOnlyMode()` 判断，无论是 `AGGR_MODE=readonly` 还是 `AGGR_READONLY=on` 均全面阻断写入。 | 模式测试验证通过，无任何未授权文件写入 |
| **4. YAML 解析与校验防御** | `cli.py`、`export_markdown.py`、`legacy_adapter.py` 仍存在裸 `yaml.safe_load`；preview/build 缺少前置重复键校验。统一采用 `load_yaml_safely` 并在各子命令前置执行 `validate_file`。 | `test_models.py` 补充重复键前置拦截测试，全部通过 |
| **5. 标签映射与 R01~R05 分类错误** | 旧版 `content5.py` 中标签为中文 `"热点"`，旧适配器匹配 `"hot"` 导致 R01~R05 误划为“暖文”。修复映射逻辑并修正 `R01.yaml ~ R05.yaml` 分类为“社会热点”。 | 单元 Schema 校验 22/22 通过，分类正确显示为社会热点 |
| **6. R02 事实边界与复述去评论化** | R02 删去未经证实的“后续医生接诊时都能看到”，修正为客观记录家长切身担忧；重写 `ref_retelling`，彻底剔除“让很多人气愤”等主观评论词，实现 100% 中立事实复述；C02 教学拆解聚焦指导学生识别答非所问。 | 复述中立事实，拆解紧扣修辞逻辑 |
| **7. 单脚鞋小样深度精修** | 摆脱概念倒推套路，讲透两层具体因果（第一层供需错位把单只鞋接起来，第二层顺着农活处境给下地的大叔换运动鞋）；剔除“凭直觉/只图体面”等臆测性措辞；字数精确核定为 428 汉字（478 字符）。 | 观点池 5 个方向，范本严格 2 个主体，口语节奏自然流畅 |
| **8. 楚亮求点赞小样深度精修** | 深入推导救人事实与承受身体伤痛代价在瞬间成立，大方求夸是正常光明的情感期待，不应受道德绑架；清晰区分九万人次点赞（情感温度）与专项奖励（机制托底）；字数核定为 420 汉字（459 字符）。 | 叙事与说理紧密贴合材料事实，破除道德苛责 |
| **9. 椰子水掺水小样深度精修** | 用货架前消费者的真实信任契约替代空泛的商业伦理术语；讲透算清违法账如何打破“造假成本低、守法吃亏”的侥幸；字数核定为 443 汉字（501 字符）。 | 论述层层递进，口语表达干脆有力 |
| **10. 字符统计精准度与双版导出** | 严格区分“纯汉字数”与“非空白字符数”，在 Markdown 导出与模型中规范标注；`export-md` 支持导出学生练习版与教师审阅版。 | `test_models.py` 自动化测试通过 |

---

## 🔮 后续演进阶段（明确未完工范围）

按照重构实施方案，本系统后续阶段任务保持不变，不宣布提前结项：

- **S3（资料库到周刊初稿生成管线）**：打通 `aggr-site/data/wenwen/raw/*.json`（275篇正文）的要素提取脚本，建立从事件快照自动产出初稿提纲的工作流。
- **S4（三模块独立分册与出版资源回填）**：实现复述、评论、拆解的三册独立拆分导出；规范黑白木刻插画资源回填。
- **S5（上游信源轻量解耦）**：解耦巨石依赖，建立容器化或无状态的信源采集服务。

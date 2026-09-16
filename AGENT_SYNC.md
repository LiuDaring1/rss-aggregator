# 口语素材周刊 · Agent 协作看板（执行制作 ↔ 审阅指导）

> **协作角色分工**：
> - **Antigravity**：执行制作 Agent（代码实现、试写与重构、排版构建、生成 PDF、安全推送）
> - **Reviewer Agent**：主编与架构指导 Agent（依据教师要求与教学规范审阅产物，输出评审意见与下阶段任务书）
> 
> **当前协作分支**：`antigravity-dev`  
> **本次修订基线**：响应《00_审核结论与补正清单.md》（针对 Commit `8692416` 审计结论的全项补正）  
> **历史基线保护**：`weekly/sample-01-rev5/sample.pdf`（SHA-256 `fee4266e34a46e786858426049619efb0f67a7b33a8982aceb657a3499324a1e`）保持 100% 原始只读，未受任何修改。

---

## 🚦 三态验收总看板（状态分离，拒绝虚标）

根据主编审计要求，本系统绝不用单一的“全部完成”模糊进度，严格区分三种状态：

| 维度 | 当前状态 | 验收说明 |
| :--- | :---: | :--- |
| **1. 工程自动化校验 (Engineering Test)** | **✅ 全部通过** | • Node 单元测试 20/20 全部通过（含 S0-1~S0-5 健壮性测试）<br/>• Python 单元测试 9/9 全部通过（含独立 Claim 字数、YAML重复键、跨文件引用、教学自夸筛查）<br/>• 全量 22 个单元 YAML Schema 校验 100% 通过（0 错误，0 警告）<br/>• CLI `preview`（单单元 HTML/PDF/PNG）与 `build`（45页整刊）均可离线确定性构建成功 |
| **2. 编辑内部自查 (Editorial Internal)** | **✅ 定向修正完成** | • 7 篇评论（C01~C06 及单脚鞋）严格按《审核结论》表 §6 逐题精修<br/>• 剔除未核对事实、删除绝对化推论与夸张险情、纠正动机净化与自相矛盾、统一术语<br/>• 彻底清理学生面 `teaching.deconstruction` 中的工程汇报与自夸词汇<br/>• 同步生成同源 Markdown 审阅文件（`outputs/markdown/`） |
| **3. 教师终审认可 (Teacher Sign-off)** | **⏳ 尚未定稿 (待教师审阅)** | • 单脚鞋及六篇评论仍属于新范式重构稿，尚未获得业务教师内容终审定稿<br/>• `legacy_unreviewed: false` 仅代表已完成结构化解耦与内部编辑自查，不代表教师最终验收 |

---

## 🧭 审阅快速入口指南（Reviewer 专用）

为免除 Reviewer 在各个历史目录与 YAML 文件之间猜疑最新版本，请统一使用以下入口：

### 1. 学生/教师同源 Markdown 在线审阅入口（最推荐）
由 `python3 publishing/weekly_pipeline/cli.py export-md` 基于最新 Pydantic 数据自动导出：
- 📄 **单脚鞋完整示范单元**：[`outputs/markdown/c-dan-jiao-xie.md`](outputs/markdown/c-dan-jiao-xie.md) 及其对应复述材料 [`outputs/markdown/R-dan-jiao-xie.md`](outputs/markdown/R-dan-jiao-xie.md)
- 📄 **重构评论六篇**：
  - [`outputs/markdown/C01.md`](outputs/markdown/C01.md)（楚亮求点赞）
  - [`outputs/markdown/C02.md`](outputs/markdown/C02.md)（刁蛮病历）
  - [`outputs/markdown/C03.md`](outputs/markdown/C03.md)（100%椰子水）
  - [`outputs/markdown/C04.md`](outputs/markdown/C04.md)（葫芦爷爷的小院）
  - [`outputs/markdown/C05.md`](outputs/markdown/C05.md)（惠东海中救人）
  - [`outputs/markdown/C06.md`](outputs/markdown/C06.md)（深夜无声警报）
- 📄 **复述与拆解单元**：`outputs/markdown/R01.md` ~ `R08.md`，`outputs/markdown/F01.md` ~ `F06.md`

### 2. 印刷级渲染快照（HTML / PDF / PNG 页面）
- **单单元三页精细预览**：
  - 单脚鞋：`outputs/preview/c-dan-jiao-xie.pdf`，页面快照 `c-dan-jiao-xie_p01.png` ~ `p03.png`
  - 单脚鞋复述：`outputs/preview/R-dan-jiao-xie.pdf`，页面快照 `R-dan-jiao-xie_p01.png` ~ `p02.png`
  - C01 ~ C06 评论快照：`outputs/preview/C01_p01.png` ~ `C06_p03.png`
  - 原文拆解快照：`outputs/preview/F01_p01.png`
- **整刊 45 页构建成品**：
  - PDF 文件：`outputs/sample-01-rev5.pdf`
  - 全套 45 页 PNG 快照：`outputs/sample-01-rev5_pages/sample-01-rev5_p01.png` ~ `p45.png`

### 3. 数据与规范源文件
- **评论单元 YAML**：`content/commentaries/`
- **复述单元 YAML**：`content/retellings/`
- **原文拆解 YAML**：`content/excerpts/`
- **刊期清单**：`issues/sample-01-rev5/issue.yaml`

---

## 📝 《00_审核结论与补正清单》全项落实对照表

| 编号 | 审核发现问题 | 补正落实方案与修复位置 | 验证结果 |
| :--- | :--- | :--- | :--- |
| **P0-01** | `agent-sync.sh` 硬编码学生姓名、整文件豁免、拉取失败盲目继续、不支持 worktree | 升级为 v1.2：彻底剥离硬编码姓名，改为从未跟踪配置文件动态读取（不存在则使用公共规则）；仅扫描暂存增量 `^\+[^+]`，取消自豁免；增加 `git rev-parse --is-inside-work-tree`；阻断 fetch 失败。 | `./agent-sync.sh status` 验证通过，无泄露警告 |
| **P1-02** | 敏感词误报删除行、输出口吻过度绝对 | 正则改为 `^\+[^+]`；扫描无命中时输出“未发现所配置规则的命中”。 | 增删敏感配置行均准确定位且不误报 |
| **P1-03** | `aggr-site` 离线断网不彻底，仍有隐式外部 fetch | `aggr-site/server.js` 中 `fetchSource` 增加 `if (IS_OFFLINE)` 拦截，缓存未命中时抛错，坚决阻断外网连接。 | 离线测试无网络请求外溢 |
| **P1-04** | `initStore` 失败污染全局目录，`flushNow` 覆写损坏库 | `aggr-site/wenwen/store.js` 采用局部变量原子初始化，校验通过才切换全局变量；增加只读守卫。新增 `S0-5` 专门回归测试。 | `npm test` 20/20 项全部通过 |
| **P1-05** | `MindmapLeaf` 语义污染、假段落号、叶子ID冲突 | `legacy_adapter.py` 重构：从 `mapkey` 智能拆出各叶子真实 `answer`；叶子 ID 递增全局唯一；`fact_refs` 诚信标记为 `["待核对"]`。 | 重新迁移后 R01~R08 导图无 ID 冲突，语义清晰 |
| **P1-06** | 迁移脚本无条件覆盖已有手工审阅单元 | `legacy_adapter.py` 增加 `_should_skip_write` 校验：已存在且未指定 `--overwrite/--force`，或标记 `legacy_unreviewed: false` 时阻止覆盖。 | 默认执行 0 覆写，已保护 C01~C06 与新单元 |
| **P1-07** | 口语正文拼装公式不一致，独立 claim 漏计 | `CommentaryUnit` 新增 `get_spoken_paragraphs()` 与 `get_full_spoken_text()`；Jinja2、Markdown 导出与校验器字数统计完全同源。 | `test_models.py` 覆盖独立 claim 用例通过 |
| **P1-08** | `render.py::preview_unit` 仅在 html 不存在时写入，产生陈旧 PDF | 改为无论何时均强制写入最新 `html_content` 到 `html_file`。 | 修改 YAML 重跑 preview 100% 刷新 PDF/PNG |
| **P1-09** | YAML 重复键被 Python 静默覆盖 | `validation.py` 引入 `UniqueKeyLoader` 与 `load_yaml_safely`，发现重复键立即抛出异常。 | `test_models.py` 重复键用例通过 |
| **P1-10** | 单脚鞋缺乏真实复述材料，packet 链断裂 | 新增 `content/retellings/R-dan-jiao-xie.yaml`（严格基于 `ttzl-45288.json` 真实素材提炼）；完善跨文件引用校验。 | 来源链闭环，全量校验 0 错误 |
| **§6-C01** | 求赞净化动机、重合观点、人次写成人、最好方式绝对化 | 承认求认可人之常情；整合观点并引入公益奖励与托底维度；明确九万人次；收准“最好方式”为“温暖回响”。 | 表达真实贴切，字数 440 字符 |
| **§6-C02** | “跟一辈子/跨医院都能看”超出材料、“唯一路径”绝对化 | 严格遵循材料中“供后续接诊调阅的医疗档案”；将“唯一路径”改为“关键一步”；清除学生拆解中自评。 | 争点清晰，字数 437 字符 |
| **§6-C03** | 立案等同于震慑已达成、椰子水/椰汁称呼混乱、开头与主体不对应 | 统一称“椰子水”；保留行动目标与预期效果的区别；总观点严格统领主体一（为什么）与主体二（怎么办）。 | 逻辑严密，字数 435 字符 |
| **§6-C04** | 游客自觉轻声未核对、自断无杂念、学生拆解含“纠正旧版” | 修正为来客应有的克制准则与倡导；保留人物真诚而不做绝对断言；彻底清除学生页工程词。 | 分寸清晰，字数 414 字符 |
| **§6-C05** | “最理智/最高智慧/确保不沉”夸大、成功个案写成通用教程 | 剔除绝对化词汇与补写的心理冲动；不输出未成年施救教程，强调量力而行与专业力量接力。 | 安全导向稳固，字数 457 字符 |
| **§6-C06** | 两段重复无增量、虚设普通人对比、“做成才是交代”过激 | 主体二转向聋哑青年克服自身沟通生理局限的道德坚韧（独立增量）；删除陪衬对比；重写结尾收束。 | 立意层次分明，字数 463 字符 |
| **§6-单脚鞋** | v4尊严金钱自相矛盾、年份与累计混同、早期志愿者主观贬低 | v4修正为参与感与自立信心；区分9年累计超2万只与2025年30只；删除对早期志愿者的臆测性评价。 | 逻辑自洽，字数 459 字符 |

---

## 🔮 后续演进阶段（明确未完工范围）

按照重构实施方案，本系统后续阶段任务保持不变，不宣布提前结项：

- **S3（资料库到周刊初稿生成管线）**：打通 `aggr-site/data/wenwen/raw/*.json`（275篇正文）的要素提取脚本，建立从事件快照自动产出初稿提纲的工作流。
- **S4（三模块独立分册与出版资源回填）**：实现复述、评论、拆解的三册独立拆分导出；规范黑白木刻插画资源回填。
- **S5（上游信源轻量解耦）**：解耦巨石依赖，建立容器化或无状态的信源采集服务。

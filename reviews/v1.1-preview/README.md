# 口语素材周刊 · v1.1-preview 审阅看板与产物索引

> **针对《Antigravity b7b6a3b 复审与定点处理》定点修改交付**  
> **分支**：`antigravity-dev`  
> **基线黄金文件**：`weekly/sample-01-rev5/sample.pdf`  
> **SHA-256 校验码**：`fee4266e34a46e786858426049619efb0f67a7b33a8982aceb657a3499324a1e` (未改动，已比对通过)  
> **专项修改对照文件**：[三题精修与修改对照.md](三题精修与修改对照.md)

---

## 一、本次定点收口核心解决的问题

1. **工程发布末端原子目录切换与失败回滚 (`publish_directory_atomically`)**：
   - **消除外层清空再复制风险**：彻底移除外层 `export_all_markdown` 针对 `out_dir/student` 和 `teacher` 先删除再逐个 `copy2` 的旧代码；
   - **独立暂存与清单摘要生成**：新批次在独立暂存目录完整生成双版本，并自动计算全量文件的 SHA-256 摘要记录于 `_manifest.json`；
   - **收准已验证边界**：在单进程发布、可捕获异常且文件系统允许回滚的测试场景中，上一版本能够保持或恢复完整；不扩大承诺断电、`kill -9` 或并发竞争安全；日常保持同一时间单进程导出；
   - **保留已通过功能**：输入目录错误阻断防御、草稿未核验显式标记进入 HTML/PDF/PNG 产物、E2 语义块导出与 E3 引用检查。
2. **学生版排版小修与教学可用性优化（2dc9395 复审落实）**：
   - **清除技术标识与题号规范**：顶部移除“【单单元预览】”调试串，显示统一规范页眉；长技术 ID 精简为 `C-单` 简洁题号；关联复述直接显示题名（如《单脚鞋银行》）；补齐 `1 / 3`、`2 / 3`、`3 / 3` 页码；
   - **第一页思考空间合理分配**：将单条 7mm 极短虚线扩展为 2~3 行点状书写虚线区，字号适度放大至 11.2~11.5pt，消除底部大面积无用留白；
   - **第二页解释正常化与排开**：依据与说明从 9.5pt 灰字提升为 10.2~10.6pt 深色字，分行标注“材料中的细节”与“可以怎样理解”，消除“。；说明：”拼合符号；推演文本字字不改、逻辑拆分 3 段；单脚鞋 5 个观点+3段推演完整容纳于第 2 页无跨页溢出；
   - **第三页范本强调与标签统一**：主体两段分论点首句直接通过 `<b>` 加粗强化，在连续正文中一眼看清结构；时长标签统一更名为“口语范本（两段主体展开）”；
   - **两处文句定点微调**：单脚鞋第1页第2问修正为两生活细节对比并提问共同点；椰子水第1页第3问改为具体解决暗中掺水问题；
   - **详见详细对照报告**：[三题精修与修改对照说明](三题精修与修改对照.md)。

---

## 二、公开审阅产物目录结构

```text
reviews/v1.1-preview/
├── README.md                          # 本看板说明文件
├── 三题精修与修改对照.md               # 针对 b7b6a3b 复审的三题精修专项对照说明
├── markdown/
│   ├── _manifest.json                 # 发布批次元数据与全量文件 SHA-256 校验清单
│   ├── student/                       # 纯学生版 Markdown（留白思考、不含内部备课备注）
│   │   ├── c-dan-jiao-xie.md
│   │   ├── C01.md ~ C06.md
│   │   ├── R-dan-jiao-xie.md
│   │   ├── R01.md ~ R08.md
│   │   └── F01.md ~ F06.md
│   └── teacher/                       # 教师审阅版 Markdown（含完整推演、范本与备课指导）
│       ├── c-dan-jiao-xie.md
│       ├── C01.md ~ C06.md
│       ├── R-dan-jiao-xie.md
│       ├── R01.md ~ R08.md
│       └── F01.md ~ F06.md
└── preview/                           # 重点单元印刷渲染件 (HTML / PDF / PNG 逐页快照)
    ├── c-dan-jiao-xie.pdf / .html / _p01.png / _p02.png / _p03.png
    ├── R-dan-jiao-xie.pdf / .html / _p01.png / _p02.png
    ├── C01.pdf / .html / _p01.png / _p02.png / _p03.png
    ├── R01.pdf / .html / _p01.png / _p02.png
    ├── C02.pdf / .html / _p01.png / _p02.png / _p03.png
    ├── R02.pdf / .html / _p01.png / _p02.png
    ├── C03.pdf / .html / _p01.png / _p02.png / _p03.png
    └── F01.pdf / .html / _p01.png
```

---

## 三、核心精修样稿索引与直达链接

| 单元名称 | 单元 ID | 学生版 Markdown | 教师审阅版 Markdown | 印刷 PDF (交付附件) | 页面 PNG 预览 | 状态说明 |
|---|---|---|---|---|---|---|
| **“单脚鞋银行” (评论)** | `c-dan-jiao-xie` | [student/c-dan-jiao-xie.md](markdown/student/c-dan-jiao-xie.md) | [teacher/c-dan-jiao-xie.md](markdown/teacher/c-dan-jiao-xie.md) | [PDF 附件](preview/c-dan-jiao-xie.pdf) | [P1](preview/c-dan-jiao-xie_p01.png) · [P2](preview/c-dan-jiao-xie_p02.png) · [P3](preview/c-dan-jiao-xie_p03.png) | 待教师定稿 |
| **“单脚鞋银行” (复述)** | `R-dan-jiao-xie` | [student/R-dan-jiao-xie.md](markdown/student/R-dan-jiao-xie.md) | [teacher/R-dan-jiao-xie.md](markdown/teacher/R-dan-jiao-xie.md) | [PDF](preview/R-dan-jiao-xie.pdf) | [P1](preview/R-dan-jiao-xie_p01.png) · [P2](preview/R-dan-jiao-xie_p02.png) | 现成可用 |
| **楚亮求点赞 (评论)** | `C01` | [student/C01.md](markdown/student/C01.md) | [teacher/C01.md](markdown/teacher/C01.md) | [PDF 附件](preview/C01.pdf) | [P1](preview/C01_p01.png) · [P2](preview/C01_p02.png) · [P3](preview/C01_p03.png) | 待教师定稿 |
| **楚亮救人 (复述)** | `R01` | [student/R01.md](markdown/student/R01.md) | [teacher/R01.md](markdown/teacher/R01.md) | [PDF](preview/R01.pdf) | [P1](preview/R01_p01.png) · [P2](preview/R01_p02.png) | 现成可用 |
| **椰子水掺水 (评论)** | `C03` | [student/C03.md](markdown/student/C03.md) | [teacher/C03.md](markdown/teacher/C03.md) | [PDF 附件](preview/C03.pdf) | [P1](preview/C03_p01.png) · [P2](preview/C03_p02.png) · [P3](preview/C03_p03.png) | 待教师定稿 |
| **“刁蛮”病历 (评论)** | `C02` | [student/C02.md](markdown/student/C02.md) | [teacher/C02.md](markdown/teacher/C02.md) | [PDF](preview/C02.pdf) | [P1](preview/C02_p01.png) · [P2](preview/C02_p02.png) | 过渡稿 |
| **“刁蛮”病历 (复述)** | `R02` | [student/R02.md](markdown/student/R02.md) | [teacher/R02.md](markdown/teacher/R02.md) | [PDF](preview/R02.pdf) | [P1](preview/R02_p01.png) · [P2](preview/R02_p02.png) | 现成可用 |
| **精选原文拆解学习** | `F01` | [student/F01.md](markdown/student/F01.md) | [teacher/F01.md](markdown/teacher/F01.md) | [PDF](preview/F01.pdf) | [P1](preview/F01_p01.png) | 现成可用 |

> 📁 **物理 PDF 独立交付路径（便于用户直接拖拽至 Reviewer 对话中审阅视觉版面）**：  
> 本地桌面目录：`/Users/baiyanglin/Desktop/口语素材周刊_三篇试读PDF/` (`C01.pdf`, `C03.pdf`, `c-dan-jiao-xie.pdf`)

---

## 四、测试与工程验收结果

1. **Node 集成测试 (`cd aggr-site && npm test`)**：
   - 23 项测试全部通过（覆盖只读隔离、离线模式拦截、无未定义异常，用时约 2.2 秒）。
2. **Python 模型与回归测试 (`PYTHONPATH=publishing python3 -m unittest publishing/tests/test_models.py`)**：
   - 18 项测试全部通过（包含 E1~E3、输入目录错误绝不清空旧输出、双版本原子目录切换与故障注入回滚、底层原子重命名异常回滚、草稿未核验标记）。
3. **全量内容与跨文件引用校验 (`cli.py validate --content-dir content`)**：
   - 22 个单元全部通过（0 错误，0 警告）。
4. **黄金基线文件未篡改校验**：
   - `weekly/sample-01-rev5/sample.pdf` 校验码保持一致（`fee4266e34a46e786858426049619efb0f67a7b33a8982aceb657a3499324a1e`）。
5. **朗读时长与字数统计说明**：
   - 自动字数提示仅供静态阅读参考，真实口语朗读时长需由真人师生试读决定，未经试读不标定为“已通过”。

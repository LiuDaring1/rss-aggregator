# 口语素材周刊 · v1.1-preview 审阅看板与产物索引

> **针对 Commit `183e2a5` 复审结论与收口任务的工程硬化与三题精修交付**  
> **分支**：`antigravity-dev`  
> **基线黄金文件**：`weekly/sample-01-rev5/sample.pdf`  
> **SHA-256 校验码**：`fee4266e34a46e786858426049619efb0f67a7b33a8982aceb657a3499324a1e` (未改动，已比对通过)  
> **专项修改对照文件**：[三题精修与修改对照.md](三题精修与修改对照.md)

---

## 一、本次收口核心解决的问题

1. **工程收口（E1 ~ E3 输出一致性硬化）**：
   - **E1 导出原子性与错误退出码**：`export-md` 在写文件前进行全量前置校验，遇到非法单元直接返回非零退出码（Exit 1），并通过临时目录原子替换发布，彻底消除半新半旧或残留旧文件的污染问题。
   - **E2 口语范本按语义结构输出**：重写 `export_commentary_markdown`，严格按开头（`main_claim`）、主体块（遍历 `body` 提取分论点与各小段）、结尾（`closing`）输出，杜绝了多段正文下索引截断导致结尾丢失的问题。
   - **E3 跨文件引用前置核验**：在 `preview`、`build`、`export-md` 中统一注入 `available_retellings` 上下文，确保复述引用完整无误。
2. **教学写作三题小样定向精修**：
   - **《楚亮求点赞》(`C01`)**：补足危急关头瞬间确立身体代价与善举事实的因果链，说明大方求赞合情合理；收准无条件保证，将虚浮的“机制托底”改为实实在在的物质奖励与社会积极信号；字数控制在 431 汉字。
   - **《椰子水掺水》(`C03`)**：补齐货架前无法化验、标签比价错觉、掺水压低成本导致合规企业吃亏等生活化推理步骤，不再堆砌概念黑话；统一步调为“让违规需要承担的代价足以抵消其图谋的好处”；字数控制在 430 汉字。
   - **《单脚鞋银行》(`c-dan-jiao-xie`)**：推演完整展开两层思考（第一层打破买卖通用规则对接闲置，第二层顺着务农防滑与磨损规律调整鞋型数量）；删去“交易惯性、行动纵深”等黑话；明确 2025 年 30 只是该团队收到的当期寄送量；字数控制在 442 汉字。
   - **详见详细对照报告**：[三题精修与修改对照说明](三题精修与修改对照.md)。

---

## 二、公开审阅产物目录结构

```text
reviews/v1.1-preview/
├── README.md                          # 本看板说明文件
├── 三题精修与修改对照.md               # 针对 183e2a5 复审的三题精修专项对照说明
├── markdown/
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

| 单元名称 | 单元 ID | 学生版 Markdown | 教师审阅版 Markdown | 印刷 PDF | 页面 PNG 预览 | 状态说明 |
|---|---|---|---|---|---|---|
| **“单脚鞋银行” (评论)** | `c-dan-jiao-xie` | [student/c-dan-jiao-xie.md](markdown/student/c-dan-jiao-xie.md) | [teacher/c-dan-jiao-xie.md](markdown/teacher/c-dan-jiao-xie.md) | [PDF](preview/c-dan-jiao-xie.pdf) | [P1](preview/c-dan-jiao-xie_p01.png) · [P2](preview/c-dan-jiao-xie_p02.png) · [P3](preview/c-dan-jiao-xie_p03.png) | 待教师定稿 |
| **“单脚鞋银行” (复述)** | `R-dan-jiao-xie` | [student/R-dan-jiao-xie.md](markdown/student/R-dan-jiao-xie.md) | [teacher/R-dan-jiao-xie.md](markdown/teacher/R-dan-jiao-xie.md) | [PDF](preview/R-dan-jiao-xie.pdf) | [P1](preview/R-dan-jiao-xie_p01.png) · [P2](preview/R-dan-jiao-xie_p02.png) | 现成可用 |
| **楚亮求点赞 (评论)** | `C01` | [student/C01.md](markdown/student/C01.md) | [teacher/C01.md](markdown/teacher/C01.md) | [PDF](preview/C01.pdf) | [P1](preview/C01_p01.png) · [P2](preview/C01_p02.png) · [P3](preview/C01_p03.png) | 待教师定稿 |
| **楚亮救人 (复述)** | `R01` | [student/R01.md](markdown/student/R01.md) | [teacher/R01.md](markdown/teacher/R01.md) | [PDF](preview/R01.pdf) | [P1](preview/R01_p01.png) · [P2](preview/R01_p02.png) | 现成可用 |
| **椰子水掺水 (评论)** | `C03` | [student/C03.md](markdown/student/C03.md) | [teacher/C03.md](markdown/teacher/C03.md) | [PDF](preview/C03.pdf) | [P1](preview/C03_p01.png) · [P2](preview/C03_p02.png) · [P3](preview/C03_p03.png) | 待教师定稿 |
| **“刁蛮”病历 (评论)** | `C02` | [student/C02.md](markdown/student/C02.md) | [teacher/C02.md](markdown/teacher/C02.md) | [PDF](preview/C02.pdf) | [P1](preview/C02_p01.png) · [P2](preview/C02_p02.png) | 过渡稿 |
| **“刁蛮”病历 (复述)** | `R02` | [student/R02.md](markdown/student/R02.md) | [teacher/R02.md](markdown/teacher/R02.md) | [PDF](preview/R02.pdf) | [P1](preview/R02_p01.png) · [P2](preview/R02_p02.png) | 现成可用 |
| **精选原文拆解学习** | `F01` | [student/F01.md](markdown/student/F01.md) | [teacher/F01.md](markdown/teacher/F01.md) | [PDF](preview/F01.pdf) | [P1](preview/F01_p01.png) | 现成可用 |

---

## 四、测试与工程验收结果

1. **Node 集成测试 (`cd aggr-site && npm test`)**：
   - 23 项测试全部通过（覆盖只读隔离、离线模式拦截、无未定义异常，用时约 2.2 秒）。
2. **Python 模型与回归测试 (`PYTHONPATH=publishing python3 -m unittest publishing/tests/test_models.py`)**：
   - 14 项测试全部通过（包含重复键拦截、E1 导出原子性与非零退出码、E2 多段正文完整输出与结尾保全、E3 跨文件引用核验）。
3. **全量内容与跨文件引用校验 (`cli.py validate --content-dir content`)**：
   - 22 个单元全部通过（0 错误，0 警告）。
4. **黄金基线文件未篡改校验**：
   - `weekly/sample-01-rev5/sample.pdf` 校验码保持一致（`fee4266e34a46e786858426049619efb0f67a7b33a8982aceb657a3499324a1e`）。

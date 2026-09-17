# 口语素材周刊 · v1.1-preview 审阅看板与产物索引

> **针对《Antigravity 183e2a5 复审与收口任务》定点修改交付**  
> **分支**：`antigravity-dev`  
> **基线黄金文件**：`weekly/sample-01-rev5/sample.pdf`  
> **SHA-256 校验码**：`fee4266e34a46e786858426049619efb0f67a7b33a8982aceb657a3499324a1e` (未改动，已比对通过)  
> **专项修改对照文件**：[三题精修与修改对照.md](三题精修与修改对照.md)

---

## 一、本次定点收口核心解决的问题

1. **工程发布末端防御与预览标记**：
   - **错误/缺失输入零破坏**：输入目录错误或不存在时，`export-md` 在写文件前直接抛错阻断，绝不清空目标审阅目录；
   - **双版本完整生成后再原子更新**：双版本模式必须在独立临时目录完整导出学生版和教师版后，才同步更新至目标审阅目录；中途任何失败均不触碰现有输出，上一版 100% 完整可读；
   - **草稿未核验进入预览产物**：当单篇草稿缺少复述引用时，【草稿·未核验】显式标记进入 HTML、PDF、PNG 预览产物。
2. **教学写作三题定点精修**：
   - **《单脚鞋银行》(`c-dan-jiao-xie`)**：保留“资源对接—使用调整”双层结构，修准第一层解释（跳出成双买卖惯性，将鞋企销毁的单只样品鞋直接对准单脚群体急需），备课备注改为亲切自然口语；正文 437 汉字；
   - **《楚亮求点赞》(`C01`)**：将“挺身而出的人不会被冷落”改成本次事件评价与明确愿望（“这一次，他的挺身而出没有被冷落……也希望这份温暖的互动，能让下一次挺身而出更有底气”），备课备注改为自然口语；正文 439 汉字；
   - **《椰子水掺水》(`C03`)**：补清低成本如何带来价格或利润优势的条件性推理（“掺水者既能靠低价吸引顾客，也能按原价售卖多赚利润，不知情的消费者只看价格，坚持真材实料的合规厂家就会处于不利地位”），备课说明改为自然口语，彻底删去教条式公文原句；正文 435 汉字。
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

---

## 四、测试与工程验收结果

1. **Node 集成测试 (`cd aggr-site && npm test`)**：
   - 23 项测试全部通过（覆盖只读隔离、离线模式拦截、无未定义异常，用时约 2.2 秒）。
2. **Python 模型与回归测试 (`PYTHONPATH=publishing python3 -m unittest publishing/tests/test_models.py`)**：
   - 16 项测试全部通过（包含 E1~E3、输入目录错误绝不清空旧输出、双版本原子发布防御、草稿未核验标记）。
3. **全量内容与跨文件引用校验 (`cli.py validate --content-dir content`)**：
   - 22 个单元全部通过（0 错误，0 警告）。
4. **黄金基线文件未篡改校验**：
   - `weekly/sample-01-rev5/sample.pdf` 校验码保持一致（`fee4266e34a46e786858426049619efb0f67a7b33a8982aceb657a3499324a1e`）。

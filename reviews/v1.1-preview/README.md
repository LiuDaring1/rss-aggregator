# 口语素材周刊 · v1.1-preview 审阅看板与产物索引

> **针对 Commit `2290d2c` 复审回单的系统性补正与写作小样精修交付**  
> **分支**：`antigravity-dev`  
> **基线黄金文件**：`weekly/sample-01-rev5/sample.pdf`  
> **SHA-256 校验码**：`fee4266e34a46e786858426049619efb0f67a7b33a8982aceb657a3499324a1e` (未改动，已比对通过)

---

## 一、本次补正核心解决的问题

1. **解决 GitHub 链接 404 问题**：
   - 上一轮 Reviewer 指出在 GitHub 上点击产物链接报 404，原因是 `outputs/` 在 `.gitignore` 中被忽略；
   - 本轮正式建立仓库跟踪的审阅产物目录 `reviews/v1.1-preview/`，所有 Markdown 审阅件、重点单元 PDF 与 PNG 页面快照均纳入 Git 跟踪，确保远端直接可点可读。
2. **聚合站服务与存储统一防御**：
   - 新增 `aggr-site/config.js`，统一解析只读与离线配置；
   - 修复 `server.js` 中 `fetchSource` 调用未定义变量 `IS_OFFLINE` 的隐患；
   - `store.js` 在 `AGGR_MODE=readonly` 和 `AGGR_READONLY=on` 下全面封锁写入；
   - 跑通全部 23 项集成测试（`npm test`）。
3. **出版管线解析器安全与端到端校验**：
   - 替换裸 `yaml.safe_load` 为带重复键拦截的 `load_yaml_safely`；
   - 在 `preview`、`build`、`export-md` 执行前统一加入强制校验，杜绝静默覆盖；
   - 补充自动化回归测试，12 项测试全部通过（`test_models.py`）。
4. **事实边界与中立复述纠错**：
   - 纠正 `legacy_adapter.py` 标签映射，`R01~R05.yaml` 分类恢复为 **社会热点**；
   - 纠正 `R02.yaml` 事实边界（删去未经证实的“后续医生接诊时都能看到”），重写口语示范为 **100% 中立客观叙述**，剔除主观评论词；
   - 纠正 `C02.yaml` 教学拆解，重点指导学生如何识别与反驳“答非所问、偷换概念”。
5. **教学写作三题小样深度精修**：
   - **《单脚鞋银行》(`c-dan-jiao-xie.yaml`)**：摆脱概念倒推，讲透两层具体因果（打破交易惯性接通供需、顺着农活处境把皮鞋换运动鞋）；剔除臆测性词汇；字数核定为 428 汉字（478 字符）。
   - **《楚亮求点赞》(`C01.yaml`)**：深入推导救人事实与身体伤痛代价在瞬间成立，大方求夸是正常光明的情感期待；清晰区分九万人次点赞（情感温度）与专项奖励（机制托底）；字数核定为 420 汉字（459 字符）。
   - **《椰子水掺水》(`C03.yaml`)**：用货架前消费者的真实契约逻辑替代抽象商业术语；讲透算清违法账如何打破“造假成本低、守法吃亏”的侥幸；字数核定为 443 汉字（501 字符）。

---

## 二、公开审阅产物目录结构

```text
reviews/v1.1-preview/
├── README.md                          # 本看板说明文件
├── markdown/
│   ├── student/                       # 纯学生版 Markdown（留白思考、不含答案、不含备课备注）
│   │   ├── c-dan-jiao-xie.md
│   │   ├── C01.md ~ C06.md
│   │   ├── R-dan-jiao-xie.md
│   │   ├── R01.md ~ R08.md
│   │   └── F01.md ~ F06.md
│   └── teacher/                       # 教师审阅版 Markdown（含导图答案、因果推演与备课备注）
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

## 三、重点审阅单元索引与直达链接

### 1. 核心精修样稿（单脚鞋、楚亮、椰子水）

| 单元名称 | 单元 ID | 学生版 Markdown | 教师审阅版 Markdown | 印刷 PDF | 页面 PNG 预览 |
|---|---|---|---|---|---|
| **“单脚鞋银行” (评论)** | `c-dan-jiao-xie` | [student/c-dan-jiao-xie.md](markdown/student/c-dan-jiao-xie.md) | [teacher/c-dan-jiao-xie.md](markdown/teacher/c-dan-jiao-xie.md) | [PDF](preview/c-dan-jiao-xie.pdf) | [P1](preview/c-dan-jiao-xie_p01.png) · [P2](preview/c-dan-jiao-xie_p02.png) · [P3](preview/c-dan-jiao-xie_p03.png) |
| **“单脚鞋银行” (复述)** | `R-dan-jiao-xie` | [student/R-dan-jiao-xie.md](markdown/student/R-dan-jiao-xie.md) | [teacher/R-dan-jiao-xie.md](markdown/teacher/R-dan-jiao-xie.md) | [PDF](preview/R-dan-jiao-xie.pdf) | [P1](preview/R-dan-jiao-xie_p01.png) · [P2](preview/R-dan-jiao-xie_p02.png) |
| **楚亮求点赞 (评论)** | `C01` | [student/C01.md](markdown/student/C01.md) | [teacher/C01.md](markdown/teacher/C01.md) | [PDF](preview/C01.pdf) | [P1](preview/C01_p01.png) · [P2](preview/C01_p02.png) · [P3](preview/C01_p03.png) |
| **楚亮救人 (复述)** | `R01` | [student/R01.md](markdown/student/R01.md) | [teacher/R01.md](markdown/teacher/R01.md) | [PDF](preview/R01.pdf) | [P1](preview/R01_p01.png) · [P2](preview/R01_p02.png) |
| **“刁蛮”病历 (评论)** | `C02` | [student/C02.md](markdown/student/C02.md) | [teacher/C02.md](markdown/teacher/C02.md) | [PDF](preview/C02.pdf) | [P1](preview/C02_p01.png) · [P2](preview/C02_p02.png) |
| **“刁蛮”病历 (复述)** | `R02` | [student/R02.md](markdown/student/R02.md) | [teacher/R02.md](markdown/teacher/R02.md) | [PDF](preview/R02.pdf) | [P1](preview/R02_p01.png) · [P2](preview/R02_p02.png) |
| **椰子水掺水 (评论)** | `C03` | [student/C03.md](markdown/student/C03.md) | [teacher/C03.md](markdown/teacher/C03.md) | [PDF](preview/C03.pdf) | [P1](preview/C03_p01.png) · [P2](preview/C03_p02.png) · [P3](preview/C03_p03.png) |
| **精选原文拆解学习** | `F01` | [student/F01.md](markdown/student/F01.md) | [teacher/F01.md](markdown/teacher/F01.md) | [PDF](preview/F01.pdf) | [P1](preview/F01_p01.png) |

---

## 四、验证结果记录

1. **Node 集成测试 (`cd aggr-site && npm test`)**：
   - 23 项测试全部通过（0 失败，用时约 2.2 秒）。
2. **Python 模型与防御测试 (`PYTHONPATH=publishing python3 -m unittest publishing/tests/test_models.py`)**：
   - 12 项测试全部通过（包含重复键防御、双版本差异化导出、汉字/字符分离统计）。
3. **全量内容与跨文件引用校验 (`cli.py validate --content-dir content`)**：
   - 22 个单元全部通过（0 错误，0 警告）。
4. **黄金基线文件未篡改校验**：
   - `shasum -a 256 weekly/sample-01-rev5/sample.pdf` 校验码保持一致。

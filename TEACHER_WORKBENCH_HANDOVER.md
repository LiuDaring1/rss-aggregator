# 高中中文口语素材周刊 · 生产运行工作台交接总说明

> 完整版教师使用与操作指引已归档至 [docs/teacher_workbench_guide.md](file:///Users/baiyanglin/Desktop/口语素材周刊_Antigravity/project/docs/teacher_workbench_guide.md)。

---

## 快速导航

- **工作台本地访问地址**：[http://127.0.0.1:3002/workbench.html](http://127.0.0.1:3002/workbench.html)
- **试发件在线审阅站 (W39)**：[http://127.0.0.1:3002/review/issues/issue-2026-w39/index.html](http://127.0.0.1:3002/review/issues/issue-2026-w39/index.html)
- **试发件 47 页完整 PDF 下载**：[http://127.0.0.1:3002/issues/issue-2026-w39/issue-2026-w39.pdf](http://127.0.0.1:3002/issues/issue-2026-w39/issue-2026-w39.pdf)

---

## 核心业务节拍速查表

| 时间节点 | 运行机制 | 教师行动 |
| :--- | :--- | :--- |
| **周一至周四 20:00 前** | 后台 `com.weekly.fetch_commentaries` 每日 2 次（09:30、18:30）静默轮询与备份 | 无需盯防，日常扫一眼工作台 Q1 绿灯即可 |
| **每周四 20:00:00** | 业务资料窗口准时截止，严禁提前锁定未结束的窗口 | 准备进入工作台审阅备选材料 |
| **每周四 20:05:00** | launchd 自动触发截稿扫尾抓取，补齐最后一批当周新发布 | 系统自动更新本周候选池与 S/A 级榜单 |
| **周四 20:10 ~ 21:00** | 教师审阅 S/A 级推荐、排除艾滋病等争议题材、标注入刊建议 | 点击 `[✓保留]`、`[✗排除]`、`[⏳待补]` 或 `[⇄改栏目]` |
| **每周五 10:00 前** | Agent 依据教师审阅意见生成正文，全门禁排版出刊 | 确认 47 页终审定版并下载打印交付早读使用 |

---

## 关键文件与数据存储位置

- **时评与事实报道库**：`aggr-site/data/commentaries/db.json` 与 `raw/*.json`（当前 366 篇）
- **暖文好事雷达库**：`aggr-site/data/wenwen/db.json` 与 `raw/*.json`（当前 284 篇）
- **教师审阅批注存储**：`data/teacher_feedback.json`（持久化存储，重跑与重启均保留）
- **抓取与健康运行状态**：`data/fetch_state.json`
- **本地归档备份存储**：`backups/weekly_data_backup_*.tar.gz`（保留最近 7 个日备份与 4 个周备份）
- **事实报道信源入库文档**：[docs/fact_sources_onboarding.md](file:///Users/baiyanglin/Desktop/口语素材周刊_Antigravity/project/docs/fact_sources_onboarding.md)
- **可靠性与选材测试套件**：[publishing/tests/test_workbench_reliability.py](file:///Users/baiyanglin/Desktop/口语素材周刊_Antigravity/project/publishing/tests/test_workbench_reliability.py)

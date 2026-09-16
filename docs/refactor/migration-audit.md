# 旧刊例数据迁移核对记录 (Migration Audit)

## 1. 迁移执行概述
- **源文件**: `weekly/sample-01-rev5/content5.py`
- **执行时间**: 2026-09-16
- **适配工具**: `publishing/weekly_pipeline/adapters/legacy_adapter.py`
- **目标目录**:
  - `content/retellings/` (8 则)
  - `content/commentaries/` (6 篇)
  - `content/excerpts/` (6 个)
  - `issues/sample-01-rev5/issue.yaml`

---

## 2. 数量与字段对照核对

| 模块 | 源数据变量 | 迁移输出路径 | 数量 | 校验状态 | 备注 |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **复述素材** | `RETELLS` | `content/retellings/R01.yaml` ~ `R08.yaml` | 8 | ✅ Pydantic 校验通过 | 保留思维导图树、关键词网络、参考复述 |
| **观点与推演** | `COMMENTS` | `content/commentaries/C01.yaml` ~ `C06.yaml` | 6 | ✅ Pydantic 校验通过 | 严格解耦：viewpoints(观点池) 与 speech.body(严格2段主体)。全部打上 `legacy_unreviewed: true` 标识 |
| **原文拆解** | `FRAGMENTS` | `content/excerpts/F01.yaml` ~ `F06.yaml` | 6 | ✅ Pydantic 校验通过 | 独立精选近期评论，保留分析、背诵、方法与迁移示范 |
| **期刊配置** | N/A (动态组装) | `issues/sample-01-rev5/issue.yaml` | 1 | ✅ Pydantic 校验通过 | 映射 R01..R08, C01..C06, F01..F06 |

---

## 3. 关键架构解耦验证

1. **观点池与范本解耦**:
   - 旧版 `content5.py` 中每个评论仅有 2 条观点（对应范本的 2 段）。
   - 迁移脚本将其转入 `learning.viewpoints`（允许任意 >= 2 个观点），并将 `speech.body` 严格限定为 2 个主体段落。
   - 所有迁移的旧评论均被标记为 `legacy_unreviewed: true`，待在 S2 阶段扩展为多元观点池（3~6 个角度）。
2. **复述素材纯中性事实**:
   - 复述文本均为客观事件报道事实，无夹带议论文评论主观断语。
3. **第三模块独立性**:
   - 6 个原文拆解均为近期真实时事评论（新京报、澎湃新闻·马上评等），未与本期第一模块复述做二次切片。

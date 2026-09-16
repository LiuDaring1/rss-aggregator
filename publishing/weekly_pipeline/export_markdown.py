# -*- coding: utf-8 -*-
"""
同源 Markdown 导出工具 (Markdown Exporter)
将 Pydantic 结构化单元导出为学生/教师易读的 Markdown 审阅文件，
确保文本与印刷版 HTML/PDF 100% 同源一致。
"""
import os
import sys
from typing import Dict, Any, List, Optional
import yaml

from weekly_pipeline.models import (
    RetellingUnit, CommentaryUnit, ExcerptUnit, IssueManifest
)

def export_retelling_markdown(unit: RetellingUnit) -> str:
    lines = []
    lines.append(f"# 【复述训练】{unit.id} · {unit.title}")
    lines.append(f"**分类**：{unit.category} | **时间地点**：{unit.date_label} | **出处**：{unit.source_label}")
    lines.append("")
    lines.append("## 一、原始材料事实")
    for p in unit.material_paragraphs:
        lines.append(f"> {p}")
        lines.append("")
    lines.append(f"**关键词网**：{' · '.join(unit.keywords)}")
    lines.append("")
    lines.append("## 二、结构思维导图")
    lines.append(f"**核心**：{unit.mindmap_tree.center}")
    for br in unit.mindmap_tree.branches:
        lines.append(f"- **{br.name}**")
        for lf in br.leaves:
            ans_str = f" → [参考答案: {lf.answer}]" if lf.answer else ""
            lines.append(f"  - [{lf.id}] {lf.hint}{ans_str}")
    lines.append("")
    lines.append("## 三、口语复述示范文本")
    lines.append(f"> {unit.ref_retelling}")
    lines.append("")
    return "\n".join(lines)

def export_commentary_markdown(unit: CommentaryUnit) -> str:
    lines = []
    lines.append(f"# 【评论演练】{unit.id} · {unit.title}")
    lines.append(f"**对应复述材料**：{unit.retelling_ref} | **数据包**：{unit.packet_ref}")
    lines.append("")
    lines.append("## 一、事实梳理与提问")
    lines.append("### 1. 核心事实梳理")
    for f in unit.learning.recap_facts:
        lines.append(f"- {f}")
    lines.append("")
    lines.append("### 2. 探究与引导提问")
    for q in unit.learning.questions:
        lines.append(f"1. {q}")
    lines.append("")
    lines.append(f"**初始感受诊断**：{unit.learning.baseline_diagnostic}")
    lines.append("")
    lines.append("## 二、多向观点池与推演")
    lines.append("| 序号 | 立论方向 (Claim) | 支撑证据 (Evidence) | 深层法理/逻辑解释 (Explanation) |")
    lines.append("|---|---|---|---|")
    for v in unit.learning.viewpoints:
        exp = v.explanation or "-"
        lines.append(f"| **{v.id}** | {v.claim} | {v.evidence} | {exp} |")
    lines.append("")
    for lesson in unit.learning.reasoning_lessons:
        lines.append(f"### 推演示例：{lesson.title} (关联观点: {', '.join(lesson.target_viewpoint_ids)})")
        lines.append(f"> {lesson.deduction_text}")
        lines.append("")
    lines.append("## 三、两分钟口语范本")
    lines.append(f"**主论点（开头）**：{unit.speech.main_claim}")
    lines.append("")
    for b in unit.speech.body:
        lines.append(f"### 主体段 {b.id}：{b.claim}")
        for p in b.paragraphs:
            # 避免如果 claim 已经包含在段落开头时的冗余输出
            lines.append(f"> {p}")
        lines.append("")
    lines.append(f"**收束总结（结尾）**：{unit.speech.closing}")
    lines.append("")
    spoken_text = unit.get_full_spoken_text()
    lines.append(f"**口语文本总字数**：{len(spoken_text.replace(' ', ''))} 汉字（适宜朗读时长约 1.5 - 2 分钟）")
    lines.append("")
    lines.append("## 四、教学拆解与备课备注")
    lines.append(f"**论述骨架**：{unit.teaching.spine}")
    lines.append("")
    lines.append("### 表达拆解教学指南")
    for d in unit.teaching.deconstruction:
        lines.append(f"- **{d.target}**：{d.instruction}")
    if unit.teaching.editor_notes:
        lines.append("")
        lines.append(f"**内部备课/审阅备注**：{unit.teaching.editor_notes}")
    return "\n".join(lines)

def export_excerpt_markdown(unit: ExcerptUnit) -> str:
    lines = []
    lines.append(f"# 【原文拆解】{unit.id} · {unit.topic}")
    lines.append(f"**来源出处**：{unit.source_name} ({unit.source_date})")
    lines.append("")
    lines.append("## 一、文章语境")
    lines.append(f"> {unit.context}")
    lines.append("")
    lines.append("## 二、评论精选原文")
    for p in unit.quote_paragraphs:
        lines.append(f"> {p}")
        lines.append("")
    lines.append("## 三、话语解析与积累")
    lines.append(f"- **解析**：{unit.analyze}")
    if unit.memorize:
        lines.append(f"- **好句摘记**：{unit.memorize}")
    if unit.method:
        lines.append(f"- **技法提炼**：{unit.method}")
    lines.append("")
    lines.append(f"## 四、迁移口语示范（{unit.demo_title}）")
    lines.append(f"> {unit.demo_text}")
    return "\n".join(lines)

def export_all_markdown(content_dir: str, out_dir: str) -> List[str]:
    os.makedirs(out_dir, exist_ok=True)
    generated = []
    
    # 导出 retellings
    r_dir = os.path.join(content_dir, "retellings")
    if os.path.exists(r_dir):
        for fn in sorted(os.listdir(r_dir)):
            if fn.endswith(".yaml"):
                with open(os.path.join(r_dir, fn), "r", encoding="utf-8") as fp:
                    u = RetellingUnit.model_validate(yaml.safe_load(fp))
                md = export_retelling_markdown(u)
                out_path = os.path.join(out_dir, f"{u.id}.md")
                with open(out_path, "w", encoding="utf-8") as fp:
                    fp.write(md)
                generated.append(out_path)
                
    # 导出 commentaries
    c_dir = os.path.join(content_dir, "commentaries")
    if os.path.exists(c_dir):
        for fn in sorted(os.listdir(c_dir)):
            if fn.endswith(".yaml"):
                with open(os.path.join(c_dir, fn), "r", encoding="utf-8") as fp:
                    u = CommentaryUnit.model_validate(yaml.safe_load(fp))
                md = export_commentary_markdown(u)
                out_path = os.path.join(out_dir, f"{u.id}.md")
                with open(out_path, "w", encoding="utf-8") as fp:
                    fp.write(md)
                generated.append(out_path)
                
    # 导出 excerpts
    f_dir = os.path.join(content_dir, "excerpts")
    if os.path.exists(f_dir):
        for fn in sorted(os.listdir(f_dir)):
            if fn.endswith(".yaml"):
                with open(os.path.join(f_dir, fn), "r", encoding="utf-8") as fp:
                    u = ExcerptUnit.model_validate(yaml.safe_load(fp))
                md = export_excerpt_markdown(u)
                out_path = os.path.join(out_dir, f"{u.id}.md")
                with open(out_path, "w", encoding="utf-8") as fp:
                    fp.write(md)
                generated.append(out_path)
                
    return generated

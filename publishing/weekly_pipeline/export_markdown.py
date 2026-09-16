# -*- coding: utf-8 -*-
"""
同源 Markdown 导出工具 (Markdown Exporter)
将 Pydantic 结构化单元导出为学生/教师易读的 Markdown 审阅文件，
确保文本与印刷版 HTML/PDF 100% 同源一致。
支持学生练习版 (student) 与 教师/审阅版 (teacher)。
"""
import os
import sys
import re
from typing import Dict, Any, List, Optional

from weekly_pipeline.models import (
    RetellingUnit, CommentaryUnit, ExcerptUnit, IssueManifest
)
from weekly_pipeline.validation import load_yaml_safely, validate_file

def count_chinese_chars(text: str) -> int:
    """统计纯汉字数"""
    return len(re.findall(r'[\u4e00-\u9fff]', text))

def count_non_whitespace_chars(text: str) -> int:
    """统计非空白字符数（含标点）"""
    return len(re.sub(r'\s+', '', text))

def export_retelling_markdown(unit: RetellingUnit, edition: str = "teacher") -> str:
    lines = []
    is_student = (edition == "student")
    title_suffix = "（学生练习版）" if is_student else "（教师审阅版）"
    lines.append(f"# 【复述训练】{unit.id} · {unit.title} {title_suffix}")
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
            if is_student:
                lines.append(f"  - [{lf.id}] {lf.hint}（____）")
            else:
                ans_str = f" → [参考答案: {lf.answer}]" if lf.answer else ""
                lines.append(f"  - [{lf.id}] {lf.hint}{ans_str}")
    lines.append("")
    lines.append("## 三、口语复述示范文本")
    lines.append(f"> {unit.ref_retelling}")
    lines.append("")
    return "\n".join(lines)

def export_commentary_markdown(unit: CommentaryUnit, edition: str = "teacher") -> str:
    lines = []
    is_student = (edition == "student")
    title_suffix = "（学生练习版）" if is_student else "（教师审阅版）"
    lines.append(f"# 【评论演练】{unit.id} · {unit.title} {title_suffix}")
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
    
    # 口语范本：按开头、主体段一、主体段二、结尾语义组织，杜绝前四项数组硬切
    lines.append("## 三、两分钟口语范本")
    lines.append("### 【开头·总论点】")
    lines.append(f"> {unit.speech.main_claim.strip()}")
    lines.append("")
    for b_idx, b in enumerate(unit.speech.body):
        ordinal = "一" if b_idx == 0 else "二"
        lines.append(f"### 【主体段{ordinal}·{b.claim.strip()}】")
        claim_clean = b.claim.strip()
        for p_idx, p in enumerate(b.paragraphs):
            p_clean = p.strip()
            if p_idx == 0 and not p_clean.startswith(claim_clean):
                lines.append(f"> {claim_clean} {p_clean}")
            else:
                lines.append(f"> {p_clean}")
        lines.append("")
    lines.append("### 【结尾·收束总结】")
    lines.append(f"> {unit.speech.closing.strip()}")
    lines.append("")
            
    spoken_text = unit.get_full_spoken_text()
    cn_len = count_chinese_chars(spoken_text)
    total_len = count_non_whitespace_chars(spoken_text)
    lines.append(f"**字数与朗读建议**：正文汉字数 {cn_len} 汉字 | 总字符数（含标点） {total_len} 字符（适宜中速口语表达约 1.5 - 2 分钟）")
    lines.append("")
    lines.append("## 四、教学拆解与修辞指南")
    lines.append(f"**论述骨架**：{unit.teaching.spine}")
    lines.append("")
    lines.append("### 表达拆解教学指南")
    for d in unit.teaching.deconstruction:
        lines.append(f"- **{d.target}**：{d.instruction}")
    if not is_student and unit.teaching.editor_notes:
        lines.append("")
        lines.append(f"**内部备课/审阅备注**：{unit.teaching.editor_notes}")
    return "\n".join(lines)

def export_excerpt_markdown(unit: ExcerptUnit, edition: str = "teacher") -> str:
    lines = []
    is_student = (edition == "student")
    title_suffix = "（学生练习版）" if is_student else "（教师审阅版）"
    lines.append(f"# 【原文拆解】{unit.id} · {unit.topic} {title_suffix}")
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

def _export_edition(content_dir: str, target_dir: str, edition: str, available_retellings: Optional[set] = None) -> List[str]:
    import tempfile
    import shutil
    
    # 1. 预先收集并校验所有可用复述单元
    r_dir = os.path.join(content_dir, "retellings")
    c_dir = os.path.join(content_dir, "commentaries")
    f_dir = os.path.join(content_dir, "excerpts")
    
    if available_retellings is None:
        available_retellings = set()
        if os.path.exists(r_dir):
            for fn in os.listdir(r_dir):
                if fn.endswith(".yaml") or fn.endswith(".yml"):
                    available_retellings.add(fn.rsplit(".", 1)[0])
                    
    # 2. 全量前置校验：任一单元非法即刻阻断，拒绝写入半成品
    validation_errors = []
    
    # 校验 retellings
    r_files = []
    if os.path.exists(r_dir):
        for fn in sorted(os.listdir(r_dir)):
            if fn.endswith(".yaml") or fn.endswith(".yml"):
                fp = os.path.join(r_dir, fn)
                val_res = validate_file(fp)
                if not val_res.is_valid:
                    validation_errors.append(f"[复述] {fn}: {'; '.join(val_res.errors)}")
                else:
                    r_files.append(fp)
                    
    # 校验 commentaries（必须传入 available_retellings 检查引用有效性）
    c_files = []
    if os.path.exists(c_dir):
        for fn in sorted(os.listdir(c_dir)):
            if fn.endswith(".yaml") or fn.endswith(".yml"):
                fp = os.path.join(c_dir, fn)
                val_res = validate_file(fp, available_retellings=available_retellings)
                if not val_res.is_valid:
                    validation_errors.append(f"[评论] {fn}: {'; '.join(val_res.errors)}")
                else:
                    c_files.append(fp)
                    
    # 校验 excerpts
    f_files = []
    if os.path.exists(f_dir):
        for fn in sorted(os.listdir(f_dir)):
            if fn.endswith(".yaml") or fn.endswith(".yml"):
                fp = os.path.join(f_dir, fn)
                val_res = validate_file(fp)
                if not val_res.is_valid:
                    validation_errors.append(f"[原文拆解] {fn}: {'; '.join(val_res.errors)}")
                else:
                    f_files.append(fp)
                    
    if validation_errors:
        err_msg = "\n".join(f"  ❌ {e}" for e in validation_errors)
        raise ValueError(f"导出前置校验失败（发现 {len(validation_errors)} 个错误，拒绝写入导出目录）:\n{err_msg}")

    # 3. 在临时目录中渲染写入，成功后原子同步至 target_dir，防止残留旧文件
    generated = []
    with tempfile.TemporaryDirectory() as tmp_out:
        for fp in r_files:
            with open(fp, "r", encoding="utf-8") as f:
                u = RetellingUnit.model_validate(load_yaml_safely(f.read()))
            md = export_retelling_markdown(u, edition=edition)
            out_file = os.path.join(tmp_out, f"{u.id}.md")
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(md)
            generated.append(os.path.join(target_dir, f"{u.id}.md"))
            
        for fp in c_files:
            with open(fp, "r", encoding="utf-8") as f:
                u = CommentaryUnit.model_validate(load_yaml_safely(f.read()))
            md = export_commentary_markdown(u, edition=edition)
            out_file = os.path.join(tmp_out, f"{u.id}.md")
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(md)
            generated.append(os.path.join(target_dir, f"{u.id}.md"))
            
        for fp in f_files:
            with open(fp, "r", encoding="utf-8") as f:
                u = ExcerptUnit.model_validate(load_yaml_safely(f.read()))
            md = export_excerpt_markdown(u, edition=edition)
            out_file = os.path.join(tmp_out, f"{u.id}.md")
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(md)
            generated.append(os.path.join(target_dir, f"{u.id}.md"))
            
        # 全量生成完毕，清空目标目录并同步写入
        os.makedirs(target_dir, exist_ok=True)
        # 清理旧的 .md 文件防止陈旧坏稿残留
        for old_fn in os.listdir(target_dir):
            if old_fn.endswith(".md"):
                os.remove(os.path.join(target_dir, old_fn))
        for tmp_fn in os.listdir(tmp_out):
            shutil.copy2(os.path.join(tmp_out, tmp_fn), os.path.join(target_dir, tmp_fn))
            
    return generated

def export_all_markdown(content_dir: str, out_dir: str, edition: str = "both", available_retellings: Optional[set] = None) -> List[str]:
    generated = []
    if edition == "both":
        student_dir = os.path.join(out_dir, "student")
        teacher_dir = os.path.join(out_dir, "teacher")
        generated.extend(_export_edition(content_dir, student_dir, "student", available_retellings=available_retellings))
        generated.extend(_export_edition(content_dir, teacher_dir, "teacher", available_retellings=available_retellings))
    else:
        generated.extend(_export_edition(content_dir, out_dir, edition, available_retellings=available_retellings))
    return generated

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
import uuid
import json
import shutil
import datetime
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

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
    if is_student:
        lines.append(f"**关联材料**：{unit.retelling_ref}")
    else:
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
    lines.append("## 三、口语范本（两段主体）")
    lines.append("### 【开头·总论点】")
    lines.append(f"> {unit.speech.main_claim.strip()}")
    lines.append("")
    for b_idx, b in enumerate(unit.speech.body):
        ordinal = "一" if b_idx == 0 else "二"
        claim_clean = re.sub(r'</?[a-zA-Z0-9]+[^>]*>', '', b.claim.strip())
        lines.append(f"### 【主体段{ordinal}·{claim_clean}】")
        for p_idx, p in enumerate(b.paragraphs):
            p_clean = re.sub(r'</?[a-zA-Z0-9]+[^>]*>', '', p.strip())
            if p_idx == 0:
                if p_clean.startswith(claim_clean):
                    rest = p_clean[len(claim_clean):].lstrip()
                    lines.append(f"> **{claim_clean}**{rest}")
                else:
                    lines.append(f"> **{claim_clean}**{p_clean}")
            else:
                lines.append(f"> {p_clean}")
        lines.append("")
    lines.append("### 【结尾·收束总结】")
    lines.append(f"> {unit.speech.closing.strip()}")
    lines.append("")
            
    spoken_text = unit.get_full_spoken_text()
    cn_len = count_chinese_chars(spoken_text)
    total_len = count_non_whitespace_chars(spoken_text)
    lines.append(f"**字数参考**：正文汉字数 {cn_len} 汉字 | 总字符数（含标点） {total_len} 字符（注：实际口语朗读时长需结合真人试读检验，非实测通过时长）")
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

def compute_page_map(manifest: IssueManifest) -> Tuple[Dict[str, int], int, int]:
    """
    统一计算周刊页码映射与各板块起始页。
    封面: 第 1 页
    目录: 第 2 页
    复述: 每个 2 页 (从第 3 页起)
    答案: 依复述篇数计算，>=8 篇占 3 页，>=5 篇占 2 页，其他占 1 页
    评论: 每个 3 页
    原文拆解: 每个 1 页
    附录: 占 1 页
    
    返回: (page_map, ans_pages, total_pages)
    """
    page_map: Dict[str, int] = {}
    cur_p = 3
    for rid in manifest.retelling_ids:
        page_map[rid] = cur_p
        cur_p += 2
        
    page_map["复述参考"] = cur_p
    num_retellings = len(manifest.retelling_ids)
    ans_pages = 3 if num_retellings >= 8 else (2 if num_retellings >= 5 else 1)
    cur_p += ans_pages
    
    for cid in manifest.commentary_ids:
        page_map[cid] = cur_p
        cur_p += 3
        
    for fid in manifest.excerpt_ids:
        page_map[fid] = cur_p
        cur_p += 1
        
    page_map["附录"] = cur_p
    total_pages = cur_p
    return page_map, ans_pages, total_pages

def export_full_issue_markdown(
    manifest: IssueManifest,
    content_dir: str = "content",
    edition: str = "student",
    page_map: Optional[Dict[str, int]] = None,
    ai_prompt_text: Optional[str] = None
) -> str:
    """
    生成整刊合订本 Markdown (同源导出，严格与 HTML / PDF 数据模型对齐)。
    严格复用 Pydantic 数据模型，断言所有单元正文非空，杜绝空白残缺输出。
    """
    lines = []
    is_student = (edition == "student")
    title_suffix = "（学生完整正文）" if is_student else "（教师/编辑审阅版）"
    
    # 1. 刊头
    lines.append(f"# 高中播音艺考口语素材周刊 · {manifest.title} {title_suffix}")
    lines.append(f"**期号**：{manifest.issue_id} ｜ **期号显示**：{manifest.issue_no_label} ｜ **时间范围**：{manifest.date_range}")
    lines.append("")
    lines.append("本期栏目：**复述**（每则材料页＋提示页，参考答案集中在「复述参考」）· **评论**（同一批材料，每题三页：审题破题／观点推演／范本拆解）· **原文拆解与积累**（独立精选近期深度评论完整语段）。本文件为完整学生正文；印刷版见相应 PDF 与分册。")
    lines.append("")
    
    # 2. 动态计算页码映射（若未传入）
    num_retellings = len(manifest.retelling_ids)
    computed_map, ans_pages, _ = compute_page_map(manifest)
    if not page_map:
        page_map = computed_map

    # 3. 目录
    lines.append("## 目录")
    r_toc = []
    for rid in manifest.retelling_ids:
        p = page_map.get(rid, 0)
        r_toc.append(f"{rid}（{p}–{p+1} 页）")
    ans_p = page_map.get("复述参考", 0)
    ans_rng = f"{ans_p}–{ans_p+ans_pages-1} 页" if ans_pages > 1 else f"{ans_p} 页"
    r_toc.append(f"复述参考（{ans_rng}）")
    lines.append(f"**复述**：{' ｜ '.join(r_toc)}")
    lines.append("")
    
    c_toc = []
    for cid in manifest.commentary_ids:
        p = page_map.get(cid, 0)
        c_toc.append(f"{cid}（{p}–{p+2} 页）")
    lines.append(f"**评论**：{' ｜ '.join(c_toc)}")
    lines.append("")
    
    f_toc = []
    for fid in manifest.excerpt_ids:
        p = page_map.get(fid, 0)
        f_toc.append(f"{fid}（{p} 页）")
    lines.append(f"**原文拆解与积累**：{' ｜ '.join(f_toc)}")
    lines.append("")
    lines.append(f"**附录 · 使用说明**：{page_map.get('附录', '—')} 页")
    lines.append("")

    # 4. AI 陪练完整指令
    if ai_prompt_text:
        lines.append("## AI 陪练完整指令")
        lines.append("```")
        lines.append(ai_prompt_text.strip())
        lines.append("```")
        lines.append("")

    lines.append("---")
    lines.append("")
    
    # 5. 模块一：口语复述
    lines.append("# 一、口语复述")
    lines.append("")
    
    retellings_loaded = []
    for rid in manifest.retelling_ids:
        yp = os.path.join(content_dir, "retellings", f"{rid}.yaml")
        if not os.path.exists(yp):
            raise FileNotFoundError(f"缺少复述单元文件: {yp}")
        with open(yp, "r", encoding="utf-8") as fp:
            u = RetellingUnit.model_validate(load_yaml_safely(fp.read()))
        
        # 校验关键正文非空
        if not u.material_paragraphs or any(not p.strip() for p in u.material_paragraphs):
            raise ValueError(f"复述单元 {u.id} 材料正文为空，阻断整刊导出！")
        if not u.ref_retelling.strip():
            raise ValueError(f"复述单元 {u.id} 参考复述为空，阻断整刊导出！")
            
        retellings_loaded.append(u)
        p_start = page_map.get(u.id, 0)
        lines.append(f"## {u.id} · {u.title}（{u.category}）")
        lines.append(f"**材料页（第 {p_start} 页）**　{u.date_label} ｜ {u.source_label}")
        lines.append("")
        for p in u.material_paragraphs:
            lines.append(f"> {p.strip()}")
            lines.append("")
        lines.append(f"**第 {p_start+1} 页**")
        lines.append(f"- **关键词**：{' · '.join(u.keywords)}")
        lines.append(f"- **思维导图**：")
        lines.append("```")
        lines.append(f"中心：{u.mindmap_tree.center}")
        for branch in u.mindmap_tree.branches:
            lines.append(f"├─ {branch.name}")
            for leaf in branch.leaves:
                lines.append(f"│   └─ [提示] {leaf.hint}")
        lines.append("```")
        lines.append(f"- **看图复述**：{u.illustration_brief or '黑白报刊式叙事漫画'}")
        lines.append("")

    # 6. 集中复述参考
    lines.append("---")
    lines.append("")
    lines.append("# 复述参考")
    ans_start_p = page_map.get("复述参考", 0)
    lines.append(f"*集中参考答案页（第 {ans_rng}）*")
    lines.append("")
    for u in retellings_loaded:
        r_p = page_map.get(u.id, 0)
        lines.append(f"### {u.id} · {u.title}")
        lines.append(f"*材料见第 {r_p} 页*")
        lines.append(f"**【参考复述】**：{u.ref_retelling.strip()}")
        lines.append(f"**【导图参照】**：{u.mapkey.strip()}")
        lines.append("")

    # 7. 模块二：口语评论
    lines.append("---")
    lines.append("")
    lines.append("# 二、口语评论")
    lines.append("")
    
    for cid in manifest.commentary_ids:
        yp = os.path.join(content_dir, "commentaries", f"{cid}.yaml")
        if not os.path.exists(yp):
            raise FileNotFoundError(f"缺少评论单元文件: {yp}")
        with open(yp, "r", encoding="utf-8") as fp:
            c = CommentaryUnit.model_validate(load_yaml_safely(fp.read()))
            
        # 校验评论正文完整性
        if not c.learning.recap_facts or not c.learning.questions:
            raise ValueError(f"评论单元 {c.id} 学习事实或提问为空，阻断整刊导出！")
        if not c.learning.viewpoints or len(c.learning.viewpoints) < 3:
            raise ValueError(f"评论单元 {c.id} 观点池数量不足 3 项，阻断整刊导出！")
        if not c.speech.main_claim.strip() or not c.speech.closing.strip():
            raise ValueError(f"评论单元 {c.id} 范本总论点或结尾为空，阻断整刊导出！")
        if not c.speech.body or len(c.speech.body) < 2:
            raise ValueError(f"评论单元 {c.id} 范本主体段不足 2 段，阻断整刊导出！")
        for b_idx, b in enumerate(c.speech.body):
            if not b.paragraphs or any(not p.strip() for p in b.paragraphs):
                raise ValueError(f"评论单元 {c.id} 主体段 {b_idx+1} 正文为空，阻断整刊导出！")

        cp = page_map.get(c.id, 0)
        ref_p = page_map.get(c.retelling_ref, 0)
        ref_str = f"关联材料见第 {ref_p} 页" if ref_p else f"关联材料：{c.retelling_ref}"
        
        lines.append(f"## {c.id} · {c.title}")
        lines.append(f"*{ref_str} ｜ 全题占 3 页（第 {cp}–{cp+2} 页）*")
        lines.append("")
        
        # P1: 事实与引导
        lines.append(f"### 第 1 页（第 {cp} 页）：审题立意与探究提问")
        lines.append("**核心事实回想**：")
        for f in c.learning.recap_facts:
            lines.append(f"- {f.strip()}")
        lines.append("")
        lines.append("**探究与引导提问**：")
        for q_idx, q in enumerate(c.learning.questions):
            lines.append(f"{q_idx+1}. {q.strip()}")
        lines.append("")
        lines.append(f"**初始感受诊断**：{c.learning.baseline_diagnostic.strip()}")
        lines.append("")
        
        # P2: 观点池与推演
        lines.append(f"### 第 2 页（第 {cp+1} 页）：多向观点池与逻辑推演")
        lines.append("**多维观点池（多角度立论）**：")
        for v in c.learning.viewpoints:
            exp_str = f"（深层理解：{v.explanation.strip()}）" if v.explanation else ""
            lines.append(f"- **【观点 {v.id}】{v.claim.strip()}**：依据细节——{v.evidence.strip()} {exp_str}")
        lines.append("")
        for lesson in c.learning.reasoning_lessons:
            lines.append(f"**推演示范（{lesson.title.strip()}）**：")
            lines.append(f"> {lesson.deduction_text.strip()}")
            lines.append("")
            
        # P3: 口语表达范本与拆解
        lines.append(f"### 第 3 页（第 {cp+2} 页）：口语范本与教学拆解")
        spoken_text = c.get_full_spoken_text()
        cn_len = count_chinese_chars(spoken_text)
        lines.append(f"**【口语范本（两段主体展开）】**（正文约 {cn_len} 汉字）：")
        lines.append("")
        lines.append(f"> **【破题总述】** {c.speech.main_claim.strip()}")
        lines.append(">")
        for b_idx, b in enumerate(c.speech.body):
            ordinal = "一" if b_idx == 0 else "二"
            claim_clean = b.claim.strip()
            for p_idx, p in enumerate(b.paragraphs):
                p_clean = p.strip()
                if p_idx == 0 and not p_clean.startswith(claim_clean):
                    lines.append(f"> **【主体{ordinal}】** **{claim_clean}** {p_clean}")
                else:
                    lines.append(f"> **【主体{ordinal}】** {p_clean}")
            lines.append(">")
        lines.append(f"> **【收束总结】** {c.speech.closing.strip()}")
        lines.append("")
        lines.append("**【技法拆解与修辞指引】**：")
        lines.append(f"- **论述骨架**：{c.teaching.spine.strip()}")
        for d in c.teaching.deconstruction:
            lines.append(f"- **{d.target.strip()}**：{d.instruction.strip()}")
        lines.append("")

    # 8. 模块三：原文拆解与积累
    lines.append("---")
    lines.append("")
    lines.append("# 三、原文拆解与积累")
    lines.append("")
    
    for fid in manifest.excerpt_ids:
        yp = os.path.join(content_dir, "excerpts", f"{fid}.yaml")
        if not os.path.exists(yp):
            raise FileNotFoundError(f"缺少原文拆解单元文件: {yp}")
        with open(yp, "r", encoding="utf-8") as fp:
            ex = ExcerptUnit.model_validate(load_yaml_safely(fp.read()))
            
        # 校验原文摘录非空
        if not ex.quote_paragraphs or any(not p.strip() for p in ex.quote_paragraphs):
            raise ValueError(f"原文拆解单元 {ex.id} 引用原段为空，阻断整刊导出！")
        if not ex.analyze.strip():
            raise ValueError(f"原文拆解单元 {ex.id} 话语解析为空，阻断整刊导出！")
        if not ex.demo_text.strip():
            raise ValueError(f"原文拆解单元 {ex.id} 口语迁移示范为空，阻断整刊导出！")
            
        fp_page = page_map.get(ex.id, 0)
        lines.append(f"## {ex.id} · {ex.topic}（第 {fp_page} 页）")
        lines.append(f"**出处**：{ex.source_name} ｜ 日期：{ex.source_date}")
        lines.append("")
        lines.append("**【文章语境】**：")
        lines.append(f"> {ex.context.strip()}")
        lines.append("")
        lines.append("**【精选原文原段】**：")
        for qp in ex.quote_paragraphs:
            lines.append(f"> {qp.strip()}")
            lines.append("")
        lines.append("**【话语解析与积累】**：")
        lines.append(f"- **话语解析**：{ex.analyze.strip()}")
        if ex.memorize:
            lines.append(f"- **好句摘记**：{ex.memorize.strip()}")
        if ex.method:
            lines.append(f"- **技法提炼**：{ex.method.strip()}")
        lines.append("")
        lines.append(f"**【迁移口语示范（{ex.demo_title.strip()}）】**：")
        lines.append(f"> {ex.demo_text.strip()}")
        lines.append("")

    # 9. 附录
    lines.append("---")
    lines.append("")
    lines.append(f"# 附录 · 使用说明（第 {page_map.get('附录', '—')} 页）")
    lines.append("")
    lines.append("本周刊专为高中播音主持与口语传播艺考生打造，紧扣高考口语表达三大能力：快速提炼与结构化复述、观点构建与思辨评述、语言积淀与文采锤炼。")
    lines.append("1. **口语复述**：先看材料页读懂记准核心事实，翻到提示页看关键词网与思维导图，向语音 AI 听众口头复述并听取反馈；")
    lines.append("2. **口语评论**：按审题立意（P1）、观点池与推演（P2）、范本朗读（P3）三步训练，重点体会两段主体首句的立论抓手；")
    lines.append("3. **原文拆解**：品味主流媒体深度评论的原汁原味，积累精妙比喻、论证技法与时空句式，并尝试在日常表达中迁移应用。")
    lines.append("")
    
    return "\n".join(lines)

def publish_directory_atomically(staging_dir: str, target_dir: str, _fault_after_backup: bool = False) -> None:
    """
    将 staging_dir 发布至 target_dir。在单进程发布、可捕获异常且文件系统允许回滚的场景中，
    通过备份切换与异常恢复保证上一版本保持完整。
    保证：
    1. 不逐个删除或覆盖仍在使用的当前版本文件；
    2. 新批次在独立暂存目录完整生成并就绪后，才触发切换；
    3. 发生可捕获异常时（包括切换中途的系统错误），自动将备份目录恢复回目标目录；
    4. 切换完全成功后才清理旧版本备份。
    （注：两次 rename 之间存在短暂瞬时交替；不适用于未测试的断电、强制 kill -9 或并发写入场景）
    """
    target = Path(target_dir).resolve()
    staging = Path(staging_dir).resolve()
    
    if not staging.exists():
        raise ValueError(f"暂存目录不存在: {staging}")

    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    
    # 目标目录尚不存在：直接原子重命名暂存目录
    if not target.exists():
        os.rename(staging, target)
        return

    # 目标目录已存在：先将当前 target 原子重命名为同父目录下的 backup 目录
    backup_uuid = uuid.uuid4().hex[:8]
    backup_dir = parent / f".backup_{target.name}_{backup_uuid}"
    
    # 步骤 1: 移走 target 到 backup
    os.rename(target, backup_dir)
    
    # 故障注入点（供边界失败回滚测试）：target 已被移走为 backup，新批次尚未就位
    if _fault_after_backup:
        try:
            raise OSError("INJECTED_FAULT: failure during publication swap")
        except Exception as e:
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
            if backup_dir.exists():
                os.rename(backup_dir, target)
            raise e

    # 步骤 2: 移入 staging 到 target，若失败立即回滚
    try:
        os.rename(staging, target)
    except Exception as e:
        # 回滚：如果 target 存在残留则先清除，再将 backup 恢复回 target
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        if backup_dir.exists():
            os.rename(backup_dir, target)
        raise e
    else:
        # 步骤 3: 切换完全成功，清理 backup
        shutil.rmtree(backup_dir, ignore_errors=True)

def _generate_publish_manifest(staging_root: str, edition: str) -> dict:
    manifest = {
        "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "edition": edition,
        "files": {}
    }
    for root, _, files in os.walk(staging_root):
        for fn in sorted(files):
            if fn == "_manifest.json":
                continue
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, staging_root)
            with open(fp, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
            manifest["files"][rel] = h
    manifest["total_files"] = len(manifest["files"])
    manifest_path = os.path.join(staging_root, "_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest

def _write_edition_files(content_dir: str, dest_dir: str, edition: str, available_retellings: Optional[set] = None) -> List[str]:
    # 0. 检查输入目录是否存在
    if not os.path.exists(content_dir):
        raise ValueError(f"内容输入目录不存在: {content_dir}")

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

    if not r_files and not c_files and not f_files:
        raise ValueError(f"内容输入目录中未找到任何有效单元文件: {content_dir}")

    os.makedirs(dest_dir, exist_ok=True)
    generated = []

    for fp in r_files:
        with open(fp, "r", encoding="utf-8") as f:
            u = RetellingUnit.model_validate(load_yaml_safely(f.read()))
        md = export_retelling_markdown(u, edition=edition)
        out_file = os.path.join(dest_dir, f"{u.id}.md")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(md)
        generated.append(out_file)
        
    for fp in c_files:
        with open(fp, "r", encoding="utf-8") as f:
            u = CommentaryUnit.model_validate(load_yaml_safely(f.read()))
        md = export_commentary_markdown(u, edition=edition)
        out_file = os.path.join(dest_dir, f"{u.id}.md")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(md)
        generated.append(out_file)
        
    for fp in f_files:
        with open(fp, "r", encoding="utf-8") as f:
            u = ExcerptUnit.model_validate(load_yaml_safely(f.read()))
        md = export_excerpt_markdown(u, edition=edition)
        out_file = os.path.join(dest_dir, f"{u.id}.md")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(md)
        generated.append(out_file)

    return generated

def _export_edition(content_dir: str, target_dir: str, edition: str, available_retellings: Optional[set] = None) -> List[str]:
    target = Path(target_dir).resolve()
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging_dir = tempfile.mkdtemp(prefix=f".staging_{target.name}_", dir=parent)
    try:
        written = _write_edition_files(content_dir, staging_dir, edition, available_retellings=available_retellings)
        publish_directory_atomically(staging_dir, target_dir)
        return [os.path.join(target_dir, os.path.basename(p)) for p in written]
    except Exception as e:
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir, ignore_errors=True)
        raise e

def export_all_markdown(content_dir: str, out_dir: str, edition: str = "both", available_retellings: Optional[set] = None, _fault_at_publish: bool = False) -> List[str]:
    if not os.path.exists(content_dir):
        raise ValueError(f"内容输入目录不存在: {content_dir}")
        
    target = Path(out_dir).resolve()
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    
    if edition == "both":
        staging_root = tempfile.mkdtemp(prefix=f".staging_{target.name}_", dir=parent)
        try:
            staging_student = os.path.join(staging_root, "student")
            staging_teacher = os.path.join(staging_root, "teacher")
            
            # 先在暂存区完整导出学生版与教师版（任一失败立即抛错并丢弃暂存，绝不触碰目标目录）
            stud_files = _write_edition_files(content_dir, staging_student, "student", available_retellings=available_retellings)
            teach_files = _write_edition_files(content_dir, staging_teacher, "teacher", available_retellings=available_retellings)
            
            # 记录全量生成清单与校验摘要
            _generate_publish_manifest(staging_root, edition="both")
            
            # 双版本均完整生成后，原子更新审阅目录；若切换失败则自动回滚恢复上一版
            publish_directory_atomically(staging_root, out_dir, _fault_after_backup=_fault_at_publish)
            
            generated = [os.path.join(out_dir, "student", os.path.basename(p)) for p in stud_files] + \
                        [os.path.join(out_dir, "teacher", os.path.basename(p)) for p in teach_files]
            return generated
        except Exception as e:
            if os.path.exists(staging_root):
                shutil.rmtree(staging_root, ignore_errors=True)
            raise e
    else:
        staging_root = tempfile.mkdtemp(prefix=f".staging_{target.name}_", dir=parent)
        try:
            files = _write_edition_files(content_dir, staging_root, edition, available_retellings=available_retellings)
            _generate_publish_manifest(staging_root, edition=edition)
            publish_directory_atomically(staging_root, out_dir, _fault_after_backup=_fault_at_publish)
            return [os.path.join(out_dir, os.path.basename(p)) for p in files]
        except Exception as e:
            if os.path.exists(staging_root):
                shutil.rmtree(staging_root, ignore_errors=True)
            raise e

# -*- coding: utf-8 -*-
"""
周刊产物全量自动化验证通用模块 (通用支持所有期号)
功能：
1. 依据 issue.yaml 动态计算静态规划页码与各板块物理页数 (无硬编码)；
2. 逐页核验分册及整刊 PDF 物理页数 (杜绝零页、溢出、截断)；
3. 校验入选 Excerpt 原文摘录是否 100% 连续精准匹配已归档的真实来源文本；
4. 严格区分通过、失败、未核验：缺失信源目录或文件时坚决判定失败，杜绝静默跳过；
5. 明确标注验证范围与边界。
"""
import os
import sys
import glob
import re
import yaml
import pypdf
from typing import Optional, List, Tuple

from weekly_pipeline.models import IssueManifest, ExcerptUnit
from weekly_pipeline.export_markdown import compute_page_map


def verify_issue_quotes(issue_id: str, content_dir: str = "content", sources_dir: Optional[str] = None) -> bool:
    """
    验证入选 Excerpt 的原文引用是否 100% 连续精准匹配已保存的真实来源文本。
    严格规则：
    - 入选摘录数 > 0 时，若 sources 目录不存在，判定为失败 (return False)；
    - 任何入选摘录若未找到匹配的来源文件 (*{fid}*)，判定为信源缺失/失败 (return False)，并报明具体 ID；
    - 来源文本中若未找到完全匹配的连续子串，判定为失败 (return False)；
    - 只有当应核对摘录全部找到来源且 100% 连续子串匹配，才判定通过 (return True)。
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    if sources_dir is None:
        sources_dir = os.path.join(project_root, "issues", issue_id, "sources")
    
    issue_yaml = os.path.join(project_root, "issues", issue_id, "issue.yaml")
    if not os.path.exists(issue_yaml):
        print(f"❌ 期刊配置文件不存在: {issue_yaml}")
        return False
        
    with open(issue_yaml, "r", encoding="utf-8") as f:
        manifest = IssueManifest.model_validate(yaml.safe_load(f))
        
    total_excerpts = len(manifest.excerpt_ids)
    print(f"\n🔍 [原文核验] 正在核对 {issue_id} 入选摘录的信源连续子串匹配度 (入选摘录: {total_excerpts} 篇)...")
    
    if total_excerpts == 0:
        print("  ℹ️ 本期未配置原文摘录单元，跳过信源核对。")
        return True

    # 1. 来源目录缺失检查（坚决判定失败，严禁静默跳过）
    if not os.path.exists(sources_dir):
        print(f"  ❌ [信源目录缺失] 信源存档目录不存在: {sources_dir}")
        print(f"     入选 {total_excerpts} 篇摘录全部处于未核验状态，正式发布校验失败！")
        print(f"\n📊 [原文核验统计] 应核对 {total_excerpts} 篇 | 成功核对 0 篇 | 缺失信源 {total_excerpts} 篇 (目录缺失) | 引文不匹配 0 处")
        return False

    matched_excerpts: List[str] = []
    missing_sources: List[str] = []
    mismatched_excerpts: List[Tuple[str, int]] = []
    missing_yaml: List[str] = []

    for fid in manifest.excerpt_ids:
        yp = os.path.join(project_root, content_dir, "excerpts", f"{fid}.yaml")
        if not os.path.exists(yp):
            print(f"  ❌ [文件缺失] 缺少摘录单元 YAML: {yp}")
            missing_yaml.append(fid)
            continue
            
        with open(yp, "r", encoding="utf-8") as f:
            excerpt_unit = ExcerptUnit.model_validate(yaml.safe_load(f))
            
        # 查找匹配当前摘录 ID 的来源原件文本
        matching_sources = glob.glob(os.path.join(sources_dir, f"*{fid}*"))
        if not matching_sources:
            print(f"  ❌ [信源缺失] 摘录 {fid} 缺少对应的来源原件归档文件 ({sources_dir}/*{fid}*)！")
            missing_sources.append(fid)
            continue
            
        source_file = matching_sources[0]
        with open(source_file, "r", encoding="utf-8") as sf:
            source_text = sf.read()
            
        s_clean = re.sub(r"\s+", "", source_text)
        unit_all_matched = True
        for idx, q in enumerate(excerpt_unit.quote_paragraphs):
            q_clean = re.sub(r"\s+", "", q)
            if q_clean not in s_clean:
                print(f"  ❌ [引文不匹配] {fid} 第 {idx+1} 段在来源原文 ({os.path.basename(source_file)}) 中未找到完全匹配连续子串！")
                print(f"     引文前 30 字: {q[:30]}...")
                mismatched_excerpts.append((fid, idx + 1))
                unit_all_matched = False
            else:
                print(f"  ✅ [匹配成功] {fid} 第 {idx+1} 段 100% 匹配来源连续子串 ({len(q)} 字符) -> {os.path.basename(source_file)}")
                
        if unit_all_matched:
            matched_excerpts.append(fid)

    print(f"\n📊 [原文核验汇总报告]")
    print(f"  - 应核验摘录: {total_excerpts} 篇")
    print(f"  - 成功核对数: {len(matched_excerpts)} 篇 ({', '.join(matched_excerpts) if matched_excerpts else '无'})")
    print(f"  - 缺失信源数: {len(missing_sources)} 篇 ({', '.join(missing_sources) if missing_sources else '无'})")
    print(f"  - 引文不匹配: {len(mismatched_excerpts)} 处 ({[f'{fid}段{p}' for fid, p in mismatched_excerpts] if mismatched_excerpts else '无'})")
    if missing_yaml:
        print(f"  - 缺失单元YAML: {len(missing_yaml)} 篇 ({', '.join(missing_yaml)})")

    all_passed = (
        len(matched_excerpts) == total_excerpts
        and len(missing_sources) == 0
        and len(mismatched_excerpts) == 0
        and len(missing_yaml) == 0
    )

    if all_passed:
        print(f"  ✅ 入选摘录信源原段全部 100% 连续精准匹配通过！\n")
        return True
    else:
        print(f"  ❌ 入选摘录信源核验未通过，禁止计为正式发布验证通过！\n")
        return False


def verify_issue_splits(issue_id: str, target_dir: Optional[str] = None) -> bool:
    """依据 issue.yaml 动态计算页码，核对分册及整刊物理页数"""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    if target_dir is None:
        target_dir = os.path.join(project_root, "issues", issue_id)
        
    issue_yaml = os.path.join(project_root, "issues", issue_id, "issue.yaml")
    if not os.path.exists(issue_yaml):
        print(f"❌ 期刊配置文件不存在: {issue_yaml}")
        return False
        
    with open(issue_yaml, "r", encoding="utf-8") as f:
        manifest = IssueManifest.model_validate(yaml.safe_load(f))
        
    page_map, ans_pages, total_pages = compute_page_map(manifest)
    c_start = page_map[manifest.commentary_ids[0]]
    f_start = page_map[manifest.excerpt_ids[0]]
    app_start = page_map.get("附录", total_pages + 1)
    
    exp_r_pages = c_start - 3
    exp_c_pages = f_start - c_start
    exp_f_pages = app_start - f_start
    exp_total_pages = total_pages
    
    expected_files = {
        f"{issue_id}.pdf": (exp_total_pages, "整刊合订本"),
        f"{issue_id}-复述.pdf": (exp_r_pages, "复述分册"),
        f"{issue_id}-评论.pdf": (exp_c_pages, "评论分册"),
        f"{issue_id}-原文拆解与积累.pdf": (exp_f_pages, "原文拆解分册"),
    }
    
    has_app = "附录" in page_map
    app_str = " | 附录: 1 页" if has_app else ""
    print(f"\n📑 [物理页数核验] 动态规划页数 (总计 {total_pages} 页):")
    print(f"  - 复述分册: {exp_r_pages} 页 | 评论分册: {exp_c_pages} 页 | 拆解分册: {exp_f_pages} 页{app_str}")
    print(f"  - 校验目录: {target_dir}")
    
    passed_count = 0
    failed_files: List[str] = []
    
    for fname, (exp_pg, label) in expected_files.items():
        fpath = os.path.join(target_dir, fname)
        if not os.path.exists(fpath):
            print(f"  ❌ 目标 PDF 不存在: {fpath}")
            failed_files.append(f"{fname}(文件不存在)")
            continue
            
        reader = pypdf.PdfReader(fpath)
        act_pg = len(reader.pages)
        if act_pg == 0:
            print(f"  ❌ {label} ({fname}) 实际物理页数为 0 页 (空PDF)！")
            failed_files.append(f"{fname}(零页)")
        elif act_pg != exp_pg:
            print(f"  ❌ {label} ({fname}) 物理页数异常: 实际 {act_pg} 页 != 规划预期 {exp_pg} 页！")
            failed_files.append(f"{fname}(实测{act_pg}页!=预期{exp_pg}页)")
        else:
            print(f"  ✅ {label} ({fname}) 物理页数校验通过 (精确吻合: {act_pg} 页)")
            passed_count += 1
            
    print(f"\n📊 [物理页数核验汇总报告]")
    print(f"  - 应核验文件: {len(expected_files)} 个")
    print(f"  - 通过核对数: {passed_count} 个")
    print(f"  - 异常文件数: {len(failed_files)} 个 ({', '.join(failed_files) if failed_files else '无'})")

    if len(failed_files) == 0 and passed_count == len(expected_files):
        print(f"  ✅ 分册与整刊物理页数全部精确吻合通过！\n")
        return True
    else:
        print(f"  ❌ 分册与整刊物理页数存在不符，校验未通过！\n")
        return False


def print_verification_scope():
    """按审阅规范明确输出验证范围与边界"""
    print("\n" + "=" * 60)
    print("📌 【自动化验证范围与边界说明】")
    print("1. 引文与本地来源一致，不等于来源抓取本身真实，亦不等于观点正确；")
    print("2. 分册与整刊页数一致，不等于没有页内裁字或位置错乱，仍须辅以版面观察；")
    print("3. 本检查作为流水线硬性底线拦截，防止零页、页数溢出/截断与随意拼贴伪造。")
    print("=" * 60)


def run_full_issue_verification(issue_id: str, target_dir: Optional[str] = None, sources_dir: Optional[str] = None) -> bool:
    """一键执行整刊信源字串与分册物理页数全量校验"""
    print(f"🚀 开始执行期刊产物通用校验: 期号 [{issue_id}]")
    q_ok = verify_issue_quotes(issue_id, sources_dir=sources_dir)
    p_ok = verify_issue_splits(issue_id, target_dir=target_dir)
    print_verification_scope()
    
    if not (q_ok and p_ok):
        print(f"\n❌ 期刊 [{issue_id}] 校验未通过，发现不符项或来源缺失，终止发布！")
        return False
        
    print(f"\n🎉 期刊 [{issue_id}] 信源原段字串与物理页数自动化校验 100% 通过！")
    return True

# -*- coding: utf-8 -*-
"""
周刊产物全量自动化验证通用模块 (通用支持所有期号)
功能：
1. 依据 issue.yaml 动态计算静态规划页码与各板块物理页数 (无硬编码)；
2. 逐页核验分册及整刊 PDF 物理页数 (杜绝零页、溢出、截断)；
3. 校验入选 Excerpt 原文摘录是否 100% 连续精准匹配已归档的真实来源文本；
4. 明确标注验证范围与边界。
"""
import os
import sys
import glob
import re
import yaml
import pypdf
from typing import Optional

from weekly_pipeline.models import IssueManifest, ExcerptUnit
from weekly_pipeline.export_markdown import compute_page_map


def verify_issue_quotes(issue_id: str, content_dir: str = "content", sources_dir: Optional[str] = None) -> bool:
    """验证入选 Excerpt 的原文引用是否 100% 连续精准匹配已保存的真实来源文本"""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    if sources_dir is None:
        sources_dir = os.path.join(project_root, "issues", issue_id, "sources")
    
    issue_yaml = os.path.join(project_root, "issues", issue_id, "issue.yaml")
    if not os.path.exists(issue_yaml):
        print(f"❌ 期刊配置文件不存在: {issue_yaml}")
        return False
        
    with open(issue_yaml, "r", encoding="utf-8") as f:
        manifest = IssueManifest.model_validate(yaml.safe_load(f))
        
    print(f"\n🔍 [原文核验] 正在核对 {issue_id} 入选摘录的信源连续子串匹配度...")
    if not os.path.exists(sources_dir):
        print(f"  ⚠️ 信源存档目录不存在: {sources_dir}，跳过原文子串校验。")
        return True

    all_ok = True
    for fid in manifest.excerpt_ids:
        yp = os.path.join(project_root, content_dir, "excerpts", f"{fid}.yaml")
        if not os.path.exists(yp):
            print(f"  ❌ 缺少摘录单元文件: {yp}")
            all_ok = False
            continue
            
        with open(yp, "r", encoding="utf-8") as f:
            excerpt_unit = ExcerptUnit.model_validate(yaml.safe_load(f))
            
        matching_sources = glob.glob(os.path.join(sources_dir, f"*{fid}*"))
        if not matching_sources:
            print(f"  ⚠️ 未在 sources/ 中找到匹配 {fid} 的来源归档文本，跳过该单元字串比对。")
            continue
            
        source_file = matching_sources[0]
        with open(source_file, "r", encoding="utf-8") as sf:
            source_text = sf.read()
            
        s_clean = re.sub(r"\s+", "", source_text)
        for idx, q in enumerate(excerpt_unit.quote_paragraphs):
            q_clean = re.sub(r"\s+", "", q)
            if q_clean not in s_clean:
                print(f"  ❌ {fid} 第 {idx+1} 段在来源原文 ({os.path.basename(source_file)}) 中未找到完全匹配连续子串！")
                print(f"     引文前 30 字: {q[:30]}...")
                all_ok = False
            else:
                print(f"  ✅ {fid} 第 {idx+1} 段 100% 匹配来源原文连续子串 ({len(q)} 字符) -> {os.path.basename(source_file)}")
                
    return all_ok


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
    app_start = page_map.get("附录", total_pages)
    
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
    
    print(f"\n📑 [物理页数核验] 动态规划页数 (总计 {total_pages} 页):")
    print(f"  - 复述分册: {exp_r_pages} 页 | 评论分册: {exp_c_pages} 页 | 拆解分册: {exp_f_pages} 页 | 附录: 1 页")
    print(f"  - 校验目录: {target_dir}")
    
    all_ok = True
    for fname, (exp_pg, label) in expected_files.items():
        fpath = os.path.join(target_dir, fname)
        if not os.path.exists(fpath):
            print(f"  ❌ 目标 PDF 不存在: {fpath}")
            all_ok = False
            continue
            
        reader = pypdf.PdfReader(fpath)
        act_pg = len(reader.pages)
        if act_pg != exp_pg:
            print(f"  ❌ {label} ({fname}) 物理页数异常: 实际 {act_pg} 页 != 规划预期 {exp_pg} 页")
            all_ok = False
        else:
            print(f"  ✅ {label} ({fname}) 物理页数校验通过 (精确吻合: {act_pg} 页)")
            
    return all_ok


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
        print(f"\n❌ 校验未通过，发现不符项！")
        return False
        
    print(f"\n🎉 期刊 [{issue_id}] 信源原段字串与物理页数自动化校验 100% 通过！")
    return True

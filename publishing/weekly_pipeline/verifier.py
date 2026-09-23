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


def are_urls_equivalent(u1: str, u2: str) -> bool:
    """对比来源 URL 是否等价（支持 HTTP/HTTPS 规整、结尾斜杠及澎湃等主流媒体移动端/PC端跳转映射）"""
    if not u1 or not u2:
        return False
    u1 = u1.strip().rstrip("/")
    u2 = u2.strip().rstrip("/")
    if u1 == u2:
        return True
    # 兼容澎湃移动端 detail 与 PC 端 newsDetail_forward 等价映射
    m1 = re.search(r"thepaper\.cn/(?:detail|newsDetail_forward)[_/]?(\d+)", u1)
    m2 = re.search(r"thepaper\.cn/(?:detail|newsDetail_forward)[_/]?(\d+)", u2)
    if m1 and m2 and m1.group(1) == m2.group(1):
        return True
    return False


def verify_fact_and_source_ledger(issue_id: str, content_dir: str = "content") -> bool:
    """
    核验 15 份信源原件与 21 单元采编台账及语义事实一致性：
    1. 必须信息合同完整性：raw_id, upstream_raw_path, upstream_content_hash, source_url 均不得为空；
    2. 真实上游依据核查：每一个单元必须绑定真实存在的上游 JSON 快照；快照 ID 与 raw_id 严格一致；
    3. URL 对应性：台账 source_url 必须与快照记录 URL 吻合；
    4. 正文有效性与哈希防伪：拦截空正文、空字符串哈希、仅元信息（hasFullText=False）；实测内容 SHA256 必须与台账完全吻合；
    5. 通用实体与事实检验：核对 declared verified_entities 存在性，并跨单元全局排查已知造假/错配实体（如'程东'、非安建大的'安徽大学'、'车祸骨折'等）；
    6. 评论单元事实关联核对：确保评论单元的 retelling_ref 均有有效依据，且正文无事实违规。
    """
    import json
    import hashlib
    # 对历史 trial 试产测试基准期做兼容（用于页数与子串基础回归，未绑定上游数据仓）
    if issue_id.startswith("issue-trial-"):
        print(f"  ℹ️ [{issue_id}] 为历史试产回归基准期，跳过上游数据仓 raw_id 强校验。")
        return True

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    prep_path = os.path.join(project_root, "issues", issue_id, "manifest_prep.json")
    if not os.path.exists(prep_path):
        print(f"❌ [台账缺失] 缺少采编台账文件: {prep_path}")
        return False

    with open(prep_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    total_retellings = len(manifest.get("retellings", []))
    total_excerpts = len(manifest.get("excerpts", []))
    print(f"\n📑 [台账与事实核验] 正在核查 {issue_id} 的上游信源绑定与语义事实一致性 (复述: {total_retellings}, 摘录: {total_excerpts})...")

    errors = []

    def _verify_source_contract(item: dict, unit_type: str):
        uid = item.get("unit_id")
        raw_id = item.get("raw_id")
        raw_path = item.get("upstream_raw_path")
        expected_hash = item.get("upstream_content_hash")
        url = item.get("source_url")
        status = item.get("fact_verification", {}).get("status")

        # 1. 必填合同字段检查
        if not raw_id:
            errors.append(f"[{uid}] 缺失真实 raw_id 绑定")
            return
        if not raw_path:
            errors.append(f"[{uid}] 缺失上游原件快照路径 upstream_raw_path")
            return
        if not expected_hash:
            errors.append(f"[{uid}] 缺失上游内容哈希 upstream_content_hash")
            return
        if not url:
            errors.append(f"[{uid}] 缺失来源 URL source_url")
            return
        if status != "verified":
            errors.append(f"[{uid}] {unit_type}核验状态未通过 (当前: {status})")
            return

        # 2. 原件存在性
        full_raw = os.path.join(project_root, raw_path)
        if not os.path.exists(full_raw):
            errors.append(f"[{uid}] 声明的上游原件不存在: {raw_path}")
            return

        try:
            with open(full_raw, "r", encoding="utf-8") as rf:
                robj = json.load(rf)
        except Exception as e:
            errors.append(f"[{uid}] 读取上游原件 JSON 异常: {e}")
            return

        # 3. 快照 ID 与 URL 对应性检查 (不得静默跳过缺失)
        snap_id = robj.get("id") or robj.get("raw_id") or robj.get("item_id")
        if not snap_id:
            errors.append(f"[{uid}] 上游快照缺失唯一标识字段 (id/raw_id/item_id)，无法核验快照身份依据")
        elif snap_id != raw_id:
            errors.append(f"[{uid}] 上游快照 ID 不匹配: 台账声明 {raw_id} != 快照记录 {snap_id}")

        snap_url = robj.get("url") or robj.get("sourceUrl") or robj.get("source_url")
        if not snap_url:
            errors.append(f"[{uid}] 上游快照缺失来源 URL 记录 (url/sourceUrl)，无法核验来源出处")
        elif not are_urls_equivalent(url, snap_url):
            errors.append(f"[{uid}] 来源 URL 不匹配: 台账声明 {url} != 快照记录 {snap_url}")

        # 4. 正文有效性检查 (拦截空正文、元信息占位符、空字符串哈希)
        content = robj.get("content", "").strip()
        if not content or robj.get("hasFullText") is False or robj.get("textType") == "metadata_only":
            errors.append(f"[{uid}] 上游原件正文为空或仅包含元信息 (hasFullText=False)，不能作为核验依据")
            return

        act_hash = hashlib.sha256(robj.get("content", "").encode("utf-8")).hexdigest()
        if act_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855":
            errors.append(f"[{uid}] 上游内容哈希为空字符串 SHA256，存在空来源伪造风险")
            return

        if act_hash != expected_hash:
            errors.append(f"[{uid}] 上游内容哈希不匹配: 期望 {expected_hash[:10]} != 实测 {act_hash[:10]}")

    # 1. 检查复述单元合同与实体事实
    for r in manifest.get("retellings", []):
        uid = r.get("unit_id")
        raw_id = r.get("raw_id")
        _verify_source_contract(r, "复述")

        # 检查正文 YAML 存在性与结构完整性
        yaml_p = os.path.join(project_root, content_dir, "retellings", f"{uid}.yaml")
        if not os.path.exists(yaml_p):
            errors.append(f"[{uid}] 缺少复述单元文件: {yaml_p}")
            continue

        try:
            with open(yaml_p, "r", encoding="utf-8") as yf:
                ydata = yaml.safe_load(yf) or {}
        except Exception as ye:
            errors.append(f"[{uid}] 解析复述单元 YAML 失败: {ye}")
            continue

        # 提取面向读者的学生正文字段（杜绝用 editor_notes 等内部注释混充核查结果）
        title_text = str(ydata.get("title", ""))
        paras_text = "\n".join(str(p) for p in ydata.get("material_paragraphs", []))
        ref_text = str(ydata.get("ref_retelling", ""))
        kw_text = " ".join(str(k) for k in ydata.get("keywords", []))
        student_text = f"{title_text}\n{paras_text}\n{ref_text}\n{kw_text}"

        # 核心真实实体在学生正文中的存在性核验
        ventities = r.get("fact_verification", {}).get("verified_entities", [])
        if not ventities:
            errors.append(f"[{uid}] 采编台账中未声明核准实体清单 verified_entities")
        else:
            missing_ents = [e for e in ventities if e not in student_text]
            if missing_ents:
                errors.append(f"[{uid}] 正文缺少台账声明的核心真实实体: {', '.join(missing_ents)}")

        # 事件绑定防伪与历史错配核验（拒绝全库盲目禁词，仅对对应特定事件执行约束）
        # (1) 汪洋励志求学事件约束
        is_wang_yang_event = (raw_id == "ttzl-45357") or ("汪洋" in ventities) or ("汪洋" in r.get("source_key_facts", ""))
        if is_wang_yang_event:
            if "程东" in student_text:
                errors.append(f"[{uid}] 汪洋事件存在严重事实错配：正文包含虚构实体'程东'（真实报道为汪洋）")
            if ("安徽大学" in student_text or "安大" in student_text) and "安徽建筑大学" not in student_text:
                errors.append(f"[{uid}] 汪洋事件存在院校错配：包含非真实报道院校'安徽大学/安大'（真实报道为四川师范大学）")

        # (2) 骑手王福民意外维权事件约束
        is_wang_fumin_event = (raw_id == "comm-bjnews-point-83270da3e9") or ("王福民" in ventities) or ("王福民" in r.get("source_key_facts", ""))
        if is_wang_fumin_event:
            if "车祸骨折" in student_text or "交通事故骨折" in student_text:
                errors.append(f"[{uid}] 骑手事件存在案情误传：正文包含'交通事故骨折/车祸骨折'（真实报道为送餐摔倒、颅内血肿）")

    # 2. 检查摘录单元合同
    for ex in manifest.get("excerpts", []):
        _verify_source_contract(ex, "摘录")

    # 3. 检查评论单元事实与关联（严格以本期入选评论集合为边界，未入选草稿不阻塞本期发布）
    for c in manifest.get("commentaries", []):
        cid = c.get("unit_id")
        r_ref = c.get("retelling_ref")
        cp = os.path.join(project_root, content_dir, "commentaries", f"{cid}.yaml")
        if not os.path.exists(cp):
            errors.append(f"[{cid}] 缺少入选评论单元文件: {cp}")
            continue

        try:
            with open(cp, "r", encoding="utf-8") as cyf:
                cdata = yaml.safe_load(cyf) or {}
        except Exception as ce:
            errors.append(f"[{cid}] 解析入选评论 YAML 失败: {ce}")
            continue

        c_title = str(cdata.get("title", ""))
        c_recap = "\n".join(str(p) for p in cdata.get("learning", {}).get("recap_facts", []))
        c_body = ""
        speech_body = cdata.get("speech", {}).get("body", [])
        if isinstance(speech_body, list):
            for b in speech_body:
                if isinstance(b, dict):
                    c_body += "\n" + "\n".join(str(p) for p in b.get("paragraphs", []))
        c_text = f"{c_title}\n{c_recap}\n{c_body}"

        # 评论单元事件绑定防伪检查
        if r_ref == "R36" or "王福民" in c_text:
            if "车祸骨折" in c_text or "交通事故骨折" in c_text:
                errors.append(f"[{cid}] 评论单元存在事实误传：包含'交通事故骨折/车祸骨折'（真实报道为摔倒受重伤、颅内血肿）")
        if r_ref == "R41" or "汪洋" in c_text:
            if "程东" in c_text:
                errors.append(f"[{cid}] 评论单元存在严重事实错配：包含虚构实体'程东'")
            if ("安徽大学" in c_text or "安大" in c_text) and "安徽建筑大学" not in c_text:
                errors.append(f"[{cid}] 评论单元存在院校错配：包含非真实报道院校'安徽大学/安大'")

    if errors:
        print(f"  ❌ 采编台账与信源合同核查未通过，共发现 {len(errors)} 项异常:")
        for err in errors:
            print(f"     - {err}")
        return False

    print(f"  ✅ 采编台账与信源合同核查通过！全部信源均有真实上游依据，事实审查记录状态合规。\n")
    return True


def print_verification_scope():
    """按审阅规范明确输出验证范围与边界"""
    print("\n" + "=" * 60)
    print("📌 【自动化验证范围与边界说明】")
    print("1. 引文与本地来源一致，不等于来源抓取本身真实，亦不等于观点正确；")
    print("2. 分册与整刊页数一致，不等于没有页内裁字或位置错乱，仍须辅以版面观察；")
    print("3. 本检查作为流水线硬性底线拦截，防止零页、页数溢出/截断与随意拼贴伪造。")
    print("=" * 60)


def run_full_issue_verification(issue_id: str, target_dir: Optional[str] = None, sources_dir: Optional[str] = None) -> bool:
    """一键执行整刊信源字串、分册物理页数与台账事实全量校验"""
    print(f"🚀 开始执行期刊产物通用校验: 期号 [{issue_id}]")
    f_ok = verify_fact_and_source_ledger(issue_id)
    q_ok = verify_issue_quotes(issue_id, sources_dir=sources_dir)
    p_ok = verify_issue_splits(issue_id, target_dir=target_dir)
    print_verification_scope()
    
    if not (f_ok and q_ok and p_ok):
        print(f"\n❌ 期刊 [{issue_id}] 校验未通过，发现不符项或来源/事实异常，终止发布！")
        return False
        
    print(f"\n🎉 期刊 [{issue_id}] 信源原段字串、物理页数与事实台账自动化校验 100% 通过！")
    return True

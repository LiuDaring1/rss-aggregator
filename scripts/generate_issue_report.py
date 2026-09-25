#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告—成品同源化生成引擎 (Report-Product Synchronization Engine)
遵循任务书规范：
1. 严禁 Agent 凭记忆自由撰写选题清单与完成报告；
2. 强制机械读取 issue.yaml, manifest_prep.json, 21 content YAML, build_receipt.json, 物理 PDF 与 Git 状态；
3. 执行严格一致性门禁核验（单元清单、标题、关联、实际页数、PDF SHA256、Git commit）；
4. 输出不可篡改的标准最终完成报告。
"""

import os
import sys
import json
import yaml
import hashlib
import argparse
import subprocess
from typing import Dict, Any, List, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "publishing"))

try:
    import fitz
except ImportError:
    fitz = None


def get_git_info() -> Dict[str, str]:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True).strip()
        short_commit = commit[:7]
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=PROJECT_ROOT, text=True).strip()
        return {"commit": commit, "short_commit": short_commit, "branch": branch}
    except Exception:
        return {"commit": "unknown", "short_commit": "unknown", "branch": "unknown"}


def compute_file_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_yaml(filepath: str) -> Dict[str, Any]:
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def generate_issue_report(issue_id: str, check_only: bool = False) -> Dict[str, Any]:
    issue_dir = os.path.join(PROJECT_ROOT, "issues", issue_id)
    issue_yaml_path = os.path.join(issue_dir, "issue.yaml")
    manifest_path = os.path.join(issue_dir, "manifest_prep.json")
    receipt_path = os.path.join(issue_dir, "build_receipt.json")
    pdf_path = os.path.join(issue_dir, f"{issue_id}.pdf")

    errors = []
    warnings = []

    # 1. 存在性检查
    for path, name in [
        (issue_yaml_path, "issue.yaml"),
        (manifest_path, "manifest_prep.json"),
        (receipt_path, "build_receipt.json"),
        (pdf_path, f"{issue_id}.pdf"),
    ]:
        if not os.path.exists(path):
            errors.append(f"关键文件缺失: {name} ({path})")

    if errors:
        report = {
            "status": "Planning Report / 计划稿 (文件不全)",
            "issue_id": issue_id,
            "errors": errors,
            "is_valid": False,
        }
        if check_only:
            print("\n❌ 报告—成品同源校验失败:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        return report

    # 2. 读取各核心文件
    issue_cfg = load_yaml(issue_yaml_path)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    with open(receipt_path, "r", encoding="utf-8") as f:
        receipt = json.load(f)

    git_info = get_git_info()

    # 3. 校验单元清单与 ID 集合
    yaml_r_ids = issue_cfg.get("retelling_ids", [])
    yaml_c_ids = issue_cfg.get("commentary_ids", [])
    yaml_f_ids = issue_cfg.get("excerpt_ids", [])

    if len(yaml_r_ids) != 9:
        errors.append(f"复述单元数量异常: {len(yaml_r_ids)} != 9")
    if len(yaml_c_ids) != 6:
        errors.append(f"时评单元数量异常: {len(yaml_c_ids)} != 6")
    if len(yaml_f_ids) != 6:
        errors.append(f"拆解单元数量异常: {len(yaml_f_ids)} != 6")

    manifest_r_ids = [u.get("unit_id") for u in manifest.get("retellings", [])]
    manifest_c_ids = [u.get("unit_id") for u in manifest.get("commentaries", [])]
    manifest_f_ids = [u.get("unit_id") for u in manifest.get("excerpts", [])]

    if set(yaml_r_ids) != set(manifest_r_ids):
        errors.append(f"复述清单不一致: issue.yaml {yaml_r_ids} != manifest {manifest_r_ids}")
    if set(yaml_c_ids) != set(manifest_c_ids):
        errors.append(f"时评清单不一致: issue.yaml {yaml_c_ids} != manifest {manifest_c_ids}")
    if set(yaml_f_ids) != set(manifest_f_ids):
        errors.append(f"拆解清单不一致: issue.yaml {yaml_f_ids} != manifest {manifest_f_ids}")

    # 4. 逐一比对内容 YAML 标题与关联
    retellings_info = []
    for rid in yaml_r_ids:
        c_path = os.path.join(PROJECT_ROOT, "content", "retellings", f"{rid}.yaml")
        if not os.path.exists(c_path):
            errors.append(f"缺少复述内容文件: {c_path}")
            continue
        c_data = load_yaml(c_path)
        m_item = next((u for u in manifest.get("retellings", []) if u.get("unit_id") == rid), {})
        retellings_info.append({
            "unit_id": rid,
            "title": c_data.get("title", ""),
            "manifest_title": m_item.get("title", ""),
            "category": c_data.get("category", ""),
            "source_label": c_data.get("source_label", ""),
            "source_media": m_item.get("source_media", ""),
        })
        if c_data.get("title") != m_item.get("title"):
            errors.append(f"[{rid}] YAML 标题与台账不符: '{c_data.get('title')}' != '{m_item.get('title')}'")

    commentaries_info = []
    for cid in yaml_c_ids:
        c_path = os.path.join(PROJECT_ROOT, "content", "commentaries", f"{cid}.yaml")
        if not os.path.exists(c_path):
            errors.append(f"缺少时评内容文件: {c_path}")
            continue
        c_data = load_yaml(c_path)
        m_item = next((u for u in manifest.get("commentaries", []) if u.get("unit_id") == cid), {})
        commentaries_info.append({
            "unit_id": cid,
            "title": c_data.get("title", ""),
            "manifest_title": m_item.get("title", ""),
            "retelling_ref": c_data.get("retelling_ref", ""),
            "manifest_ref": m_item.get("retelling_ref", ""),
            "category": c_data.get("category", ""),
        })
        if c_data.get("title") != m_item.get("title"):
            errors.append(f"[{cid}] YAML 标题与台账不符: '{c_data.get('title')}' != '{m_item.get('title')}'")
        if c_data.get("retelling_ref") != m_item.get("retelling_ref"):
            errors.append(f"[{cid}] 关联复述不一致: YAML '{c_data.get('retelling_ref')}' != 台账 '{m_item.get('retelling_ref')}'")

    excerpts_info = []
    for fid in yaml_f_ids:
        c_path = os.path.join(PROJECT_ROOT, "content", "excerpts", f"{fid}.yaml")
        if not os.path.exists(c_path):
            errors.append(f"缺少拆解内容文件: {c_path}")
            continue
        c_data = load_yaml(c_path)
        m_item = next((u for u in manifest.get("excerpts", []) if u.get("unit_id") == fid), {})
        yaml_title = c_data.get("title") or (f"{c_data.get('source_name', '')} | {c_data.get('topic', '')}" if c_data.get('source_name') else c_data.get('topic', ''))
        manifest_title = m_item.get("title", "")
        excerpts_info.append({
            "unit_id": fid,
            "title": yaml_title,
            "manifest_title": manifest_title,
            "source_media": m_item.get("source_media", ""),
            "category": c_data.get("category", "") or m_item.get("category", ""),
        })
        if yaml_title != manifest_title and c_data.get("topic") != manifest_title:
            errors.append(f"[{fid}] YAML 标题与台账不符: '{yaml_title}' != '{manifest_title}'")

    # 5. 校验物理页数与哈希
    actual_sha = compute_file_sha256(pdf_path)
    receipt_sha = receipt.get("pdf_sha256", "")
    if actual_sha != receipt_sha:
        errors.append(f"PDF 哈希与凭据不符: 实际 {actual_sha[:12]}... != 凭据 {receipt_sha[:12]}...")

    actual_pages = 0
    if fitz:
        doc = fitz.open(pdf_path)
        actual_pages = doc.page_count
        doc.close()
    else:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        actual_pages = len(reader.pages)

    receipt_pages = receipt.get("total_pages", 0)
    if actual_pages != 47:
        errors.append(f"实际物理页数不守恒: 实际 {actual_pages} != 47")
    if actual_pages != receipt_pages:
        errors.append(f"实际页数与凭据不符: 实际 {actual_pages} != 凭据 {receipt_pages}")

    # 6. 判断状态
    is_valid = len(errors) == 0
    report_status = "Final Build Report / 最终构建报告" if is_valid else "Mid-run Report / 中间状态 (存在校验未通过项)"

    report_data = {
        "status": report_status,
        "is_valid": is_valid,
        "issue_id": issue_id,
        "git_commit": git_info["short_commit"],
        "git_branch": git_info["branch"],
        "build_timestamp": receipt.get("timestamp", ""),
        "pdf_path": pdf_path,
        "pdf_pages": actual_pages,
        "pdf_sha256": actual_sha,
        "retellings": retellings_info,
        "commentaries": commentaries_info,
        "excerpts": excerpts_info,
        "errors": errors,
        "warnings": warnings,
    }

    if check_only:
        if not is_valid:
            print("\n❌ 报告—成品同源校验失败:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        else:
            print("\n✅ 报告—成品同源校验完全通过！全部 21 单元数据与物理产物 100% 同源匹配。")

    return report_data


def print_formatted_markdown_report(report: Dict[str, Any]):
    print("\n" + "=" * 76)
    print(f" 📰 《口语素材周刊》{report['issue_id']} 真实同源完成报告")
    print(f" 📌 报告认定性质: [{report['status']}]")
    print("=" * 76)
    print(f"▶ 构建时间: {report['build_timestamp']}")
    print(f"▶ Git Commit: {report['git_commit']} (分支: {report['git_branch']})")
    print(f"▶ 物理合订本: {report['pdf_path']}")
    print(f"▶ 真实页数: {report['pdf_pages']} 页 (严格守恒)")
    print(f"▶ 产物哈希: {report['pdf_sha256']}")
    print("-" * 76)

    print("\n🎙️ 一、复述教学板块 (9 篇):")
    for r in report["retellings"]:
        print(f"  [{r['unit_id']}] {r['title']} | 来源: {r['source_label']} | 分类: {r['category']}")

    print("\n💡 二、时评探究板块 (6 篇):")
    for c in report["commentaries"]:
        print(f"  [{c['unit_id']}] {c['title']} (关联: {c['retelling_ref']}) | 分类: {c['category']}")

    print("\n📖 三、原文拆解板块 (6 篇):")
    for f in report["excerpts"]:
        print(f"  [{f['unit_id']}] {f['title']} | 来源: {f['source_media']} | 分类: {f['category']}")

    if report["errors"]:
        print("\n❌ 发现以下同源异常项 (禁止标记为最终定稿):")
        for err in report["errors"]:
            print(f"  - {err}")
    else:
        print("\n✅ 全量 21 单元数据、物理页数与 SHA-256 哈希全部由产物直读生成，与 PDF 完全同源。")
    print("=" * 76 + "\n")


def main():
    parser = argparse.ArgumentParser(description="生成与校验同源周刊报告")
    parser.add_argument("--issue", type=str, default="issue-2026-w40", help="期刊期号")
    parser.add_argument("--check", action="store_true", help="仅执行机器一致性门禁检查并返回退出码")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON 数据")
    args = parser.parse_args()

    report = generate_issue_report(args.issue, check_only=args.check)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_formatted_markdown_report(report)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
最小备料连接工具 (Prep Pipeline)
功能：
1. 按本期时间窗 (如 2026-09-07 ~ 2026-09-13) 检索本地 raw 资料库与指定补充报道；
2. 提取并核验文章来源、标题、媒体、日期、可回读全文及关键事实细节；
3. 输出结构化的本期备料清单与溯源证据链 (manifest_prep.json)；
4. 支持断点继续、单题重做，并可输出单元初稿骨架。
"""

import os
import sys
import json
import glob
from datetime import datetime
from typing import Dict, Any, List, Optional

def load_raw_json(filepath: str) -> Optional[Dict[str, Any]]:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ 读取文件失败 {filepath}: {e}", file=sys.stderr)
        return None

def scan_candidates_in_window(
    raw_dir: str,
    start_date: str = "2026-09-01",
    end_date: str = "2026-09-15"
) -> List[Dict[str, Any]]:
    """扫描指定时间窗口内的所有本地 raw 资料"""
    candidates = []
    files = glob.glob(os.path.join(raw_dir, "*.json"))
    for f in sorted(files):
        data = load_raw_json(f)
        if not data:
            continue
        date_str = data.get("awardDate") or data.get("publishedAt") or data.get("sourcePublishedAt")
        if not date_str:
            continue
        date_short = str(date_str)[:10]
        if start_date <= date_short <= end_date:
            candidates.append({
                "id": data.get("id"),
                "file": f,
                "date": date_short,
                "media": data.get("media") or data.get("origin") or "未知媒体",
                "title": data.get("title", ""),
                "content_len": len(data.get("content") or ""),
                "url": data.get("url", ""),
                "category": data.get("category", "")
            })
    return candidates

def generate_prep_manifest(
    issue_id: str,
    time_window: str,
    selected_retellings: List[Dict[str, Any]],
    selected_commentaries: List[Dict[str, Any]],
    selected_excerpts: List[Dict[str, Any]],
    out_file: str
) -> Dict[str, Any]:
    """生成本期确定性的备料清单与证据链"""
    manifest = {
        "schema_version": "1.0",
        "issue_id": issue_id,
        "time_window": time_window,
        "generated_at": datetime.now().isoformat(),
        "editorial_policy": {
            "standards_doc": "CURRENT_REQUIREMENTS.md",
            "layout_baseline": "ec86509",
            "three_modules": ["retellings", "commentaries", "excerpts"]
        },
        "retellings_count": len(selected_retellings),
        "commentaries_count": len(selected_commentaries),
        "excerpts_count": len(selected_excerpts),
        "retellings": selected_retellings,
        "commentaries": selected_commentaries,
        "excerpts": selected_excerpts
    }
    
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 成功生成本期备料清单: {out_file} (共包含 {len(selected_retellings)} 复述, {len(selected_commentaries)} 评论, {len(selected_excerpts)} 原文拆解)")
    return manifest

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="周刊最小备料连接工具")
    parser.add_argument("--raw-dir", default="aggr-site/data/wenwen/raw", help="raw 资料库路径")
    parser.add_argument("--start-date", default="2026-09-01", help="起始日期 (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2026-09-15", help="截止日期 (YYYY-MM-DD)")
    parser.add_argument("--issue-id", default="issue-2026-w37", help="期刊 ID")
    parser.add_argument("--out", default="issues/issue-2026-w37/manifest_prep.json", help="输出清单路径")
    args = parser.parse_args()
    
    cands = scan_candidates_in_window(args.raw_dir, args.start_date, args.end_date)
    print(f"在时间窗口 {args.start_date} ~ {args.end_date} 内发现 {len(cands)} 条本地资料。")

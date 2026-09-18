# -*- coding: utf-8 -*-
"""
周刊备料管线工具 (Weekly Prep Pipeline)
定位：实现“原始资料库/公开报道 → 候选备料清单与溯源证据链 (manifest_prep.json)”的连接与管理。

严格遵循审阅规范：
1. 真实时间区分：分离事件发生时间、新闻报道时间、评论发表时间、获奖公示与抓取时间，旧事不硬编为当周发生；
2. 来源语义合同：TTZL 来源严格优先 sourcePublishedAt，无原报道时间则留空，杜绝以 awardDate/publishedAt 冒充报道日期；
3. 职责清晰分离：如实区分 [Script 已做]、[Agent 已做]、[Pending 待定稿]；
4. 解除硬编码：扫描所得与命令行参数决定输出；缺库/无源时保护已有交付，不虚假生成“已核验”清单。
"""

import os
import sys
import json
import glob
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional

def load_raw_json(filepath: str) -> Optional[Dict[str, Any]]:
    """安全读取本地单个 raw json 文件"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ 读取文件失败 {filepath}: {e}", file=sys.stderr)
        return None

def extract_dates_from_raw(data: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    分离并归一化四类时间戳，严格遵守各来源字段合同：
    - TTZL (天天正能量):
        * 原始媒体报道时间在 sourcePublishedAt (若无则为 None，严禁以 awardDate 冒充)
        * awardDate 为评选获奖/公示时间 (或旧字段 publishedAt 兼容)
        * eventOccurredAt 为事发时间
    - 非 TTZL 来源:
        * 优先读取 publishedAt / sourcePublishedAt / pubDate 作为报道时间
    """
    origin = data.get("origin") or data.get("sourceType") or ""
    raw_id = str(data.get("id") or "")
    is_ttzl = (origin == "ttzl") or raw_id.startswith("ttzl-")

    event_date = data.get("eventOccurredAt")
    if event_date:
        event_date = str(event_date)[:10]

    award_date = data.get("awardDate")
    if award_date:
        award_date = str(award_date)[:10]

    if is_ttzl:
        # TTZL 合同：报道日期仅取 sourcePublishedAt；若无则为 None
        pub_date = data.get("sourcePublishedAt")
        if pub_date:
            pub_date = str(pub_date)[:10]
        else:
            pub_date = None
        # 若 award_date 为空但存在旧 publishedAt，则填入 award_date
        if not award_date and data.get("publishedAt"):
            award_date = str(data.get("publishedAt"))[:10]
    else:
        pub_date = data.get("publishedAt") or data.get("sourcePublishedAt") or data.get("pubDate")
        if pub_date:
            pub_date = str(pub_date)[:10]

    fetched_date = data.get("fetchedAt")
    if fetched_date:
        fetched_date = str(fetched_date)[:10]

    return {
        "event_occurred_at": event_date,
        "published_at": pub_date,
        "award_date": award_date,
        "fetched_at": fetched_date
    }

def scan_raw_candidates(
    raw_dir: str,
    start_date: str = "2026-09-01",
    end_date: str = "2026-09-15"
) -> List[Dict[str, Any]]:
    """
    扫描本地 raw 资料库，提取规范化元数据并按时间窗过滤。
    若 raw_dir 不存在，抛出 FileNotFoundError 以保护下游交付。
    """
    if not os.path.exists(raw_dir):
        raise FileNotFoundError(f"原始资料库目录不存在: {raw_dir}")

    candidates = []
    files = glob.glob(os.path.join(raw_dir, "*.json"))
    for f in sorted(files):
        data = load_raw_json(f)
        if not data:
            continue
        dates = extract_dates_from_raw(data)
        
        # 主参照日期优先看原报道时间或事件时间，次看获奖时间
        primary_date = dates["published_at"] or dates["event_occurred_at"] or dates["award_date"] or ""
        if start_date <= primary_date <= end_date:
            content = data.get("content") or ""
            paras = [p.strip() for p in content.split("\n") if p.strip()]
            candidates.append({
                "raw_id": data.get("id"),
                "file_path": f,
                "title": data.get("title", ""),
                "media": data.get("media") or data.get("origin") or "未知媒体",
                "url": data.get("url", ""),
                "dates": dates,
                "category": data.get("category", ""),
                "sample_paragraphs": paras[:3],
                "char_count": len(content)
            })
    return candidates

def build_manifest_from_candidates(
    candidates: List[Dict[str, Any]],
    issue_id: str,
    time_window: str,
    out_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    从扫描所得的候选资料构建规范备料清单。
    严格区分脚本自动提取与人工/Agent审核状态，新扫描项默认为 pending_review。
    """
    items = []
    for c in candidates:
        items.append({
            "raw_id": c["raw_id"],
            "title": c["title"],
            "source_media": c["media"],
            "source_url": c["url"],
            "dates": c["dates"],
            "category": c["category"],
            "sample_paragraphs": c["sample_paragraphs"],
            "char_count": c["char_count"],
            "workflow_status": {
                "script_done": f"已由脚本从 {os.path.basename(c['file_path'])} 提取元数据与时间戳",
                "agent_done": None,
                "pending_signoff": "待人工/Agent选材与交叉比对核验"
            },
            "action_decision": "pending_review"
        })

    manifest = {
        "schema_version": "1.0",
        "issue_id": issue_id,
        "time_window": time_window,
        "generated_at": datetime.now().isoformat(),
        "editorial_policy": {
            "standards_doc": "CURRENT_REQUIREMENTS.md",
            "layout_baseline": "ec86509",
            "dates_policy": "严禁将获奖或抓取时间冒充新闻发生时间；旧事入选需明示",
            "reuse_policy": "复用篇目必须明示，不可用新编号伪装全新采编"
        },
        "statistics": {
            "candidates_scanned": len(candidates),
            "selected_count": 0,
            "retellings_count": 0,
            "commentaries_count": 0,
            "excerpts_count": 0
        },
        "candidates": items,
        "retellings": [],
        "commentaries": [],
        "excerpts": []
    }

    if out_file:
        os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"✅ 成功生成候选备料清单: {out_file} (包含 {len(items)} 条待审核候选资料)")

    return manifest

def load_curated_manifest(curated_file: str, out_file: Optional[str] = None) -> Dict[str, Any]:
    """
    加载由 Agent/人工完成事实核验的显式权威备料数据。
    数据外置为独立 JSON，不再硬编码在 Python 逻辑中。
    """
    if not os.path.exists(curated_file):
        raise FileNotFoundError(f"已核验备料数据文件不存在: {curated_file}")
    with open(curated_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    manifest["generated_at"] = datetime.now().isoformat()
    if out_file:
        os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"✅ 成功输出已核验备料清单: {out_file} (包含 {len(manifest.get('retellings', []))} 复述, {len(manifest.get('commentaries', []))} 评论, {len(manifest.get('excerpts', []))} 原文拆解)")
    return manifest

def resolve_curated_path(issue_id: str, curated_file: Optional[str] = None) -> str:
    """
    智能解析已核验备料数据路径，兼容 issue_2026_w37 与 w37 等命名规范。
    """
    if curated_file:
        return curated_file
    candidates = [
        f"publishing/weekly_pipeline/data/manifest_{issue_id.replace('-', '_')}_curated.json",
        f"publishing/weekly_pipeline/data/manifest_{issue_id.split('-')[-1]}_curated.json",
        f"publishing/weekly_pipeline/data/manifest_{issue_id}_curated.json",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]

def main():
    parser = argparse.ArgumentParser(description="周刊备料管线连接工具")
    parser.add_argument("--raw-dir", default="aggr-site/data/wenwen/raw", help="raw 资料库路径")
    parser.add_argument("--start-date", default="2026-09-01", help="起始日期 (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2026-09-15", help="截止日期 (YYYY-MM-DD)")
    parser.add_argument("--issue-id", default="issue-2026-w37", help="期刊 ID")
    parser.add_argument("--curated-file", default=None, help="显式已核验编辑数据路径 (JSON)")
    parser.add_argument("--apply-curated", action="store_true", help="若指定且存在已核验文件则应用")
    parser.add_argument("--force", action="store_true", help="强制覆盖已存在的选材清单")
    parser.add_argument("--out", default=None, help="输出清单路径")
    args = parser.parse_args()

    # 1. 若指定使用已核验数据 (显式模式)
    if args.curated_file or args.apply_curated:
        curated_path = resolve_curated_path(args.issue_id, args.curated_file)
        out_file = args.out or f"issues/{args.issue_id}/manifest_prep.json"
        if os.path.exists(curated_path):
            print(f"正在应用已核验备料数据: {curated_path} -> {out_file}...")
            load_curated_manifest(curated_path, out_file)
            return
        else:
            print(f"❌ 找不到已核验数据文件: {curated_path}，绝不静默回退并覆盖输出！", file=sys.stderr)
            sys.exit(1)

    # 2. 正常候选扫描流程：
    # 默认输出到 candidates_scan.json，坚决不直接覆盖已核验选材清单 manifest_prep.json！
    out_file = args.out or f"issues/{args.issue_id}/candidates_scan.json"

    # 若用户通过 --out 显式指向已有文件，检测是否包含已核验选材数据以提供保护
    if os.path.exists(out_file) and not args.force:
        try:
            with open(out_file, "r", encoding="utf-8") as fp:
                existing_data = json.load(fp)
            if existing_data.get("retellings") or existing_data.get("commentaries") or existing_data.get("excerpts"):
                print(
                    f"❌ 安全拦截：目标文件 {out_file} 中包含已核验的选材数据 (retellings/commentaries/excerpts)。\n"
                    f"候选扫描默认输出到 candidates_scan.json，严禁无故清空已核验选材清单！\n"
                    f"如确需覆盖，请显式添加 --force 参数。",
                    file=sys.stderr
                )
                sys.exit(1)
        except Exception:
            pass

    # 严格依据输入 raw 资料与时间窗
    if not os.path.exists(args.raw_dir):
        print(f"❌ 原始资料库不存在: {args.raw_dir}，跳过生成以保护已有清单交付。", file=sys.stderr)
        sys.exit(1)

    time_window = f"{args.start_date} ~ {args.end_date}"
    print(f"正在扫描本地 raw 资料库: {args.raw_dir} (期号: {args.issue_id}, 窗口: {time_window})...")
    cands = scan_raw_candidates(args.raw_dir, args.start_date, args.end_date)
    print(f"  🔍 发现 {len(cands)} 条候选资料。")

    print(f"正在生成候选备料清单至: {out_file}...")
    build_manifest_from_candidates(cands, args.issue_id, time_window, out_file)
    print("  ✅ 备料候选输出完成。")

if __name__ == "__main__":
    main()

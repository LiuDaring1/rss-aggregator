# -*- coding: utf-8 -*-
"""
周刊备料管线工具 (Weekly Prep Pipeline) v2.1

严格遵循审阅规范 (f147274)：
1. 真实时间区分与时区归一化：所有时间经 Asia/Shanghai 换算；
   - 分离新闻报道时间 (published_at)、事发时间 (event_occurred_at)、获奖公示时间 (award_date) 与抓取时间 (fetched_at)；
   - 严格区分“本期时段 (issue_window)”与“检索回看窗口 (search_window)”，杜绝旧案混称为当周首发；
2. 动态期号与时段计算：依据 --issue-id (如 issue-2026-w38) 动态推导当周起止，拒绝死板硬编码；
3. 历史复用智能检测与标记：自动检索历史各期已入选条目，命中往期则显式标明 is_reused 与 reused_in；
4. 明确展示真实数据通路：打印各 raw 资料库的绝对路径与 realpath，验证与上游守护进程连接；
5. 职责清晰分离：如实区分 [Script 已做]、[Agent 已做]、[Pending 待定稿]；
6. 保护已有交付成果：候选默认输出至 candidates_scan.json，绝不静默冲刷已核验的选材清单 manifest_prep.json。
"""

import os
import sys
import json
import glob
import re
import argparse
import datetime
import email.utils
from typing import Dict, Any, List, Optional, Tuple, Set

try:
    from zoneinfo import ZoneInfo
    BEIJING_TZ = ZoneInfo("Asia/Shanghai")
except Exception:
    BEIJING_TZ = datetime.timezone(datetime.timedelta(hours=8))

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

def parse_iso_date(pub_date_str: str) -> Tuple[str, str]:
    """统一将任意时间规范转换为中国北京时间 (Asia/Shanghai, UTC+8)"""
    if not pub_date_str or not str(pub_date_str).strip():
        return ("", "")
    s = str(pub_date_str).strip()

    try:
        dt = email.utils.parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        beijing_dt = dt.astimezone(BEIJING_TZ)
        return (beijing_dt.strftime("%Y-%m-%d"), beijing_dt.isoformat())
    except Exception:
        pass

    try:
        iso_s = s.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(iso_s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=BEIJING_TZ)
        beijing_dt = dt.astimezone(BEIJING_TZ)
        return (beijing_dt.strftime("%Y-%m-%d"), beijing_dt.isoformat())
    except Exception:
        pass

    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"]:
        try:
            dt = datetime.datetime.strptime(s, fmt)
            dt = dt.replace(tzinfo=BEIJING_TZ)
            return (dt.strftime("%Y-%m-%d"), dt.isoformat())
        except Exception:
            continue

    m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        d_str = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        return (d_str, f"{d_str}T00:00:00+08:00")

    return ("", s)

def normalize_url(u: str) -> str:
    """归一化 URL 用于跨期比对 (忽略协议、查询参数及末尾斜杠)"""
    if not u or not str(u).strip():
        return ""
    clean = re.sub(r"^https?://", "", str(u).strip()).split("?")[0].rstrip("/")
    return clean.lower()

def normalize_title(t: str) -> str:
    """归一化标题 (去除标点符号与空白)"""
    if not t:
        return ""
    return re.sub(r"[\s\W_]+", "", str(t))

def derive_week_dates(issue_id: str) -> Tuple[str, str]:
    """依据期号格式 (如 issue-2026-w38) 计算对应自然周的周一与周日日期；格式非法坚决抛错"""
    m = re.search(r"(\d{4})[-_]w(\d{1,2})", (issue_id or "").lower())
    if m:
        year = int(m.group(1))
        week = int(m.group(2))
        mon = datetime.date.fromisocalendar(year, week, 1)
        sun = datetime.date.fromisocalendar(year, week, 7)
        return (mon.isoformat(), sun.isoformat())
    raise ValueError(f"无法从期号 '{issue_id}' 识别有效年份与周数 (格式须为 issue-YYYY-wWW)，且未提供显式 --start-date/--end-date！")

def load_raw_json(filepath: str) -> Optional[Dict[str, Any]]:
    """安全读取本地单个 raw json 文件"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ 读取文件失败 {filepath}: {e}", file=sys.stderr)
        return None

def extract_dates_from_raw(data: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """分离并归一化四类时间戳，严格遵守各来源字段合同并转为北京时间"""
    origin = data.get("origin") or data.get("sourceType") or ""
    raw_id = str(data.get("id") or "")
    is_ttzl = (origin == "ttzl") or raw_id.startswith("ttzl-")

    event_date = data.get("eventOccurredAt")
    if event_date:
        event_date, _ = parse_iso_date(str(event_date))

    award_date = data.get("awardDate")
    if award_date:
        award_date, _ = parse_iso_date(str(award_date))

    if is_ttzl:
        # TTZL 合同：报道日期仅取 sourcePublishedAt；若无则为 None (严禁以 awardDate 冒充)
        raw_pub = data.get("sourcePublishedAt")
        pub_date, _ = parse_iso_date(str(raw_pub)) if raw_pub else (None, "")
        if not award_date and data.get("publishedAt"):
            award_date, _ = parse_iso_date(str(data.get("publishedAt")))
    else:
        raw_pub = data.get("publishedAt") or data.get("sourcePublishedAt") or data.get("pubDate")
        pub_date, _ = parse_iso_date(str(raw_pub)) if raw_pub else (None, "")

    raw_fetch = data.get("fetchedAt")
    fetched_date, _ = parse_iso_date(str(raw_fetch)) if raw_fetch else (None, "")

    return {
        "event_occurred_at": event_date or None,
        "published_at": pub_date or None,
        "award_date": award_date or None,
        "fetched_at": fetched_date or None
    }

def collect_historical_usage(exclude_issue_id: str = "") -> Dict[str, Any]:
    """
    全维度扫描所有历史期刊，建立已使用材料的多维引用图谱：
    包含：by_raw_id, by_url, by_title
    """
    by_raw_id: Dict[str, Set[str]] = {}
    by_url: Dict[str, Set[str]] = {}
    by_title: Dict[str, Set[str]] = {}

    issue_dirs = glob.glob(os.path.join(ROOT_DIR, "issues", "*"))
    for d in issue_dirs:
        iid = os.path.basename(d)
        if not os.path.isdir(d) or iid == exclude_issue_id:
            continue

        # 1. 扫描 sources 归档文件
        sources = glob.glob(os.path.join(d, "sources", "*"))
        for s in sources:
            fname = os.path.basename(s)
            m = re.findall(r"(ttzl-\d+|comm-[a-zA-Z0-9\-]+)", fname)
            for rid in m:
                by_raw_id.setdefault(rid, set()).add(iid)

        # 2. 扫描 manifest_prep.json
        mf = os.path.join(d, "manifest_prep.json")
        if os.path.exists(mf):
            try:
                with open(mf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sec in ["retellings", "commentaries", "excerpts"]:
                        for it in data.get(sec, []):
                            # raw_id 字段或从 local_raw_path 提取
                            rid = it.get("raw_id")
                            if not rid and it.get("local_raw_path"):
                                base = os.path.basename(it["local_raw_path"])
                                rid = os.path.splitext(base)[0]
                            if rid:
                                by_raw_id.setdefault(rid, set()).add(iid)

                            # URL 索引
                            u = it.get("source_url") or it.get("url")
                            norm_u = normalize_url(u)
                            if norm_u:
                                by_url.setdefault(norm_u, set()).add(iid)

                            # 标题索引
                            t = it.get("title")
                            norm_t = normalize_title(t)
                            if norm_t and len(norm_t) >= 4:
                                by_title.setdefault(norm_t, set()).add(iid)
            except Exception:
                pass

        # 3. 扫描 issue.yaml 关联的 content 单元
        iy = os.path.join(d, "issue.yaml")
        if os.path.exists(iy):
            try:
                with open(iy, "r", encoding="utf-8") as f:
                    import yaml
                    idata = yaml.safe_load(f)
                    all_uids = (
                        (idata.get("retelling_ids") or []) +
                        (idata.get("commentary_ids") or []) +
                        (idata.get("excerpt_ids") or [])
                    )
                    for uid in all_uids:
                        for sub in ["retellings", "commentaries", "excerpts"]:
                            ufile = os.path.join(ROOT_DIR, "content", sub, f"{uid}.yaml")
                            if os.path.exists(ufile):
                                with open(ufile, "r", encoding="utf-8") as ufp:
                                    udata = yaml.safe_load(ufp)
                                    u_url = normalize_url(udata.get("source_url") or udata.get("url"))
                                    if u_url:
                                        by_url.setdefault(u_url, set()).add(iid)
                                    u_title = normalize_title(udata.get("title"))
                                    if u_title and len(u_title) >= 4:
                                        by_title.setdefault(u_title, set()).add(iid)
            except Exception:
                pass

    return {
        "by_raw_id": {k: sorted(list(v)) for k, v in by_raw_id.items()},
        "by_url": {k: sorted(list(v)) for k, v in by_url.items()},
        "by_title": {k: sorted(list(v)) for k, v in by_title.items()}
    }

def scan_raw_candidates(
    raw_dirs: Any,
    search_start_date: str,
    search_end_date: str,
    issue_id: str = ""
) -> List[Dict[str, Any]]:
    """
    扫描本地 raw 资料库，提取元数据并按检索时间窗过滤。
    同时注入多维历史复用检测标记 (is_reused, reused_in, reuse_note)。
    """
    if isinstance(raw_dirs, str):
        dirs = [d.strip() for d in raw_dirs.split(",") if d.strip()]
    else:
        dirs = list(raw_dirs)

    valid_dirs = [d for d in dirs if os.path.exists(d)]
    if not valid_dirs:
        raise FileNotFoundError(f"原始资料库目录均不存在: {raw_dirs}")

    hist_usage = collect_historical_usage(exclude_issue_id=issue_id)
    by_raw_id = hist_usage.get("by_raw_id", {})
    by_url = hist_usage.get("by_url", {})
    by_title = hist_usage.get("by_title", {})

    candidates = []
    seen_ids = set()

    for r_dir in valid_dirs:
        r_real = os.path.realpath(r_dir)
        files = glob.glob(os.path.join(r_dir, "*.json"))
        for f in sorted(files):
            if os.path.basename(f) in ["db.json", "index.json", "sources_status.json"]:
                continue
            data = load_raw_json(f)
            if not data:
                continue

            raw_id = str(data.get("id") or "")
            if raw_id in seen_ids:
                continue
            seen_ids.add(raw_id)

            dates = extract_dates_from_raw(data)

            # 主参照日期优先看原报道时间或事件时间，次看获奖时间，再次看抓取时间
            primary_date = dates["published_at"] or dates["event_occurred_at"] or dates["award_date"] or dates["fetched_at"] or ""

            if search_start_date <= primary_date <= search_end_date:
                content = data.get("content") or ""
                paras = [p.strip() for p in content.split("\n") if p.strip()]
                origin = data.get("origin") or data.get("sourceType") or ""
                is_comm = (origin == "commentary") or raw_id.startswith("comm-")
                content_type = "commentary" if is_comm else "warm_story"

                # 正文状态
                has_full = data.get("hasFullText", len(content) >= 300)
                text_type = data.get("textType", "full_text" if has_full else "summary_only")

                # 多维历史复用检测 (raw_id + URL + 标题)
                matched_issues = set()
                if raw_id in by_raw_id:
                    matched_issues.update(by_raw_id[raw_id])

                raw_url = normalize_url(data.get("sourceUrl") or data.get("url"))
                if raw_url and raw_url in by_url:
                    matched_issues.update(by_url[raw_url])

                raw_title = normalize_title(data.get("title"))
                if raw_title and raw_title in by_title:
                    matched_issues.update(by_title[raw_title])

                used_in = sorted(list(matched_issues))
                is_reused = len(used_in) > 0
                reuse_note = f"往期已使用 ({', '.join(used_in)})；若入选本期应在清单与导言中明示复用理由与角度差异" if is_reused else None

                candidates.append({
                    "raw_id": raw_id,
                    "content_type": content_type,
                    "file_path": f,
                    "real_file_path": os.path.realpath(f),
                    "title": data.get("title", ""),
                    "media": data.get("media") or data.get("sourceName") or data.get("source") or data.get("origin") or "未知媒体",
                    "author": data.get("author", ""),
                    "url": data.get("url", ""),
                    "source_url": data.get("sourceUrl") or data.get("url", ""),
                    "feed_url": data.get("feedUrl", ""),
                    "dates": dates,
                    "category": data.get("category", ""),
                    "has_full_text": has_full,
                    "text_type": text_type,
                    "is_reused": is_reused,
                    "reused_in": used_in,
                    "reuse_note": reuse_note,
                    "sample_paragraphs": paras[:3],
                    "char_count": len(content)
                })
    return candidates

def build_manifest_from_candidates(
    candidates: List[Dict[str, Any]],
    issue_id: str,
    issue_window: str,
    search_window: str,
    out_file: Optional[str] = None
) -> Dict[str, Any]:
    """从扫描所得候选构建规范备料清单，清晰标注时间窗与复用状态"""
    items = []
    for c in candidates:
        items.append({
            "raw_id": c["raw_id"],
            "content_type": c.get("content_type", "warm_story"),
            "title": c["title"],
            "source_media": c["media"],
            "author": c.get("author", ""),
            "source_url": c["source_url"],
            "feed_url": c.get("feed_url", ""),
            "dates": c["dates"],
            "category": c["category"],
            "has_full_text": c.get("has_full_text", True),
            "text_type": c.get("text_type", "full_text"),
            "is_reused": c.get("is_reused", False),
            "reused_in": c.get("reused_in", []),
            "reuse_note": c.get("reuse_note"),
            "sample_paragraphs": c["sample_paragraphs"],
            "char_count": c["char_count"],
            "local_raw_path": c["file_path"],
            "workflow_status": {
                "script_done": f"已由脚本从 {os.path.basename(c['file_path'])} 提取元数据与时间戳",
                "agent_done": None,
                "pending_signoff": "待人工/Agent选材与交叉比对核验"
            },
            "action_decision": "pending_review"
        })

    comm_count = sum(1 for c in candidates if c.get("content_type") == "commentary")
    warm_count = sum(1 for c in candidates if c.get("content_type") == "warm_story")
    reused_count = sum(1 for c in candidates if c.get("is_reused"))

    manifest = {
        "schema_version": "2.1",
        "issue_id": issue_id,
        "issue_window": issue_window,
        "search_window": search_window,
        "generated_at": datetime.datetime.now(BEIJING_TZ).isoformat(),
        "editorial_policy": {
            "standards_doc": "CURRENT_REQUIREMENTS.md",
            "dates_policy": "严禁将获奖或抓取时间冒充新闻发生时间；旧案入选必须在选材清单中明示复用理由与往期期号",
            "reuse_policy": "复用篇目必须明示，不可用新编号伪装全新采编"
        },
        "statistics": {
            "candidates_scanned": len(candidates),
            "commentaries_scanned": comm_count,
            "warm_stories_scanned": warm_count,
            "reused_candidates_detected": reused_count,
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
        print(f"✅ 成功生成候选备料清单: {out_file}")
        print(f"   - 扫描候选总数: {len(items)} (评论: {comm_count}, 暖文: {warm_count}, 往期已用: {reused_count})")
        print(f"   - 本期出刊时段: {issue_window}")
        print(f"   - 候选检索时段: {search_window}")

    return manifest

def main():
    parser = argparse.ArgumentParser(description="周刊备料管线连接工具 v2.1")
    parser.add_argument("--raw-dir", default="aggr-site/data/wenwen/raw,aggr-site/data/commentaries/raw", help="raw 资料库路径（支持逗号分隔多个目录）")
    parser.add_argument("--issue-id", "--issue", default="issue-2026-w38", help="期刊 ID (如 issue-2026-w38)")
    parser.add_argument("--start-date", default=None, help="本期起始日期 (YYYY-MM-DD，若省略则自动从期号推算)")
    parser.add_argument("--end-date", default=None, help="本期截止日期 (YYYY-MM-DD，若省略则自动从期号推算)")
    parser.add_argument("--lookback-days", type=int, default=14, help="候选向前回看检索天数 (默认 14 天)")
    parser.add_argument("--force", action="store_true", help="强制覆盖已存在的选材清单")
    parser.add_argument("--out", default=None, help="输出清单路径")
    args = parser.parse_args()

    # 1. 动态推算本期时间窗
    default_start, default_end = derive_week_dates(args.issue_id)
    issue_start = args.start_date or default_start
    issue_end = args.end_date or default_end
    issue_window = f"{issue_start} ~ {issue_end}"

    # 2. 计算候选回看检索时段
    try:
        s_dt = datetime.date.fromisoformat(issue_start)
        search_start = (s_dt - datetime.timedelta(days=args.lookback_days)).isoformat()
    except Exception:
        search_start = issue_start
    search_end = issue_end
    search_window = f"{search_start} ~ {search_end}"

    # 3. 打印路径与真实连接状态
    raw_dir_list = [d.strip() for d in args.raw_dir.split(",") if d.strip()]
    print(f"🚀 周刊候选备料扫描启动 (期号: {args.issue_id}):")
    print(f"   📅 本期出刊时段: {issue_window}")
    print(f"   🔍 候选回看窗口: {search_window} (向前回看 {args.lookback_days} 天)")
    print("   📂 资料库通路检查:")
    valid_dirs = []
    for rd in raw_dir_list:
        if os.path.exists(rd):
            valid_dirs.append(rd)
            print(f"      ✅ 接入目录: {rd} -> realpath: {os.path.realpath(rd)}")
        else:
            print(f"      ⚠️  未找到目录: {rd}")

    if not valid_dirs:
        print(f"❌ 原始资料库均不存在: {args.raw_dir}，终止运行！", file=sys.stderr)
        sys.exit(1)

    out_file = args.out or f"issues/{args.issue_id}/candidates_scan.json"

    # 安全拦截：严禁无意覆盖带有已核验单元的清单
    if os.path.exists(out_file) and not args.force:
        try:
            with open(out_file, "r", encoding="utf-8") as fp:
                existing_data = json.load(fp)
            if existing_data.get("retellings") or existing_data.get("commentaries") or existing_data.get("excerpts"):
                print(
                    f"❌ 安全拦截：目标文件 {out_file} 中包含已核验的选材数据。\n"
                    f"候选扫描默认输出到 candidates_scan.json，如确需覆盖请加 --force 参数。",
                    file=sys.stderr
                )
                sys.exit(1)
        except Exception:
            pass

    cands = scan_raw_candidates(valid_dirs, search_start, search_end, issue_id=args.issue_id)
    build_manifest_from_candidates(cands, args.issue_id, issue_window, search_window, out_file)

if __name__ == "__main__":
    main()

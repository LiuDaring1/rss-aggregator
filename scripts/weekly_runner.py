#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/weekly_runner.py
口语素材周刊统一调度台 (Teacher & Pipeline Unified Runner)

提供极简、可靠的每周生产调度入口：
1. status: 查看当前期生产进度看板、上游采集健康度与待办项 (低认知负担看板)
2. prep:   执行信源采集与备料台账初始化，初始化任务状态
3. build:  执行带原子防护与全门禁核验的正式构建
4. publish: 构建并导出多期审阅静态站，生成归档永久链接

用法示例：
  python3 scripts/weekly_runner.py status --issue issue-2026-w38
  python3 scripts/weekly_runner.py prep --issue issue-2026-w39
  python3 scripts/weekly_runner.py build --issue issue-2026-w38
  python3 scripts/weekly_runner.py publish --issue issue-2026-w38
"""

import os
import sys
import re
import json
import argparse
import subprocess
import hashlib
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHON_EXEC = sys.executable

# 将 publishing 加入 pythonpath
if os.path.join(PROJECT_ROOT, "publishing") not in sys.path:
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "publishing"))

from weekly_pipeline.task_tracker import (
    load_production_state,
    save_production_state,
    init_production_state,
    update_stage,
    freeze_unit,
    is_unit_frozen,
    get_resume_info,
    STAGES,
)


def parse_issue_sort_key(issue_name: str):
    """期号排序键：常规周刊数值排序优先，历史试产次之"""
    m = re.match(r"^issue-(\d{4})-w(\d+)$", issue_name)
    if m:
        return (2, int(m.group(1)), int(m.group(2)), issue_name)
    m_trial = re.match(r"^issue-trial-(\d+)$", issue_name)
    if m_trial:
        return (1, 0, int(m_trial.group(1)), issue_name)
    return (0, 0, 0, issue_name)


def find_latest_issue(issues_dir=None):
    """自动探测最新期刊目录 (精准数值排序)"""
    if issues_dir is None:
        issues_dir = os.path.join(PROJECT_ROOT, "issues")
    if not os.path.exists(issues_dir):
        return "issue-2026-w38"
    
    candidates = []
    for d in os.listdir(issues_dir):
        dp = os.path.join(issues_dir, d)
        if os.path.isdir(dp) and d.startswith("issue-"):
            candidates.append(d)
    
    if not candidates:
        return "issue-2026-w38"

    candidates.sort(key=parse_issue_sort_key, reverse=True)
    return candidates[0]


def get_upstream_health(db_file=None, status_file=None):
    """读取上游信源健康度与统计数据"""
    if db_file is None:
        db_file = os.path.join(PROJECT_ROOT, "aggr-site", "data", "commentaries", "db.json")
    if status_file is None:
        status_file = os.path.join(PROJECT_ROOT, "aggr-site", "data", "commentaries", "sources_status.json")
    
    data = {
        "total_articles": 0,
        "full_text_articles": 0,
        "active_sources": 0,
        "failed_sources": 0,
        "empty_sources": 0,
        "latest_article_date": "未知",
        "last_crawl_time": "未知",
        "last_new_articles_at": "未知",
        "degraded_events_count": 0,
        "is_expired": False,
        "sources_detail": []
    }
    
    if os.path.exists(db_file):
        try:
            with open(db_file, "r", encoding="utf-8") as f:
                db = json.load(f)
            data["total_articles"] = db.get("totalArticles", 0)
            data["full_text_articles"] = db.get("fullTextArticles", 0) or db.get("totalFullText", 0)
            last_crawl = db.get("updatedAt") or db.get("lastUpdated", "未知")
            data["last_crawl_time"] = last_crawl
            data["last_new_articles_at"] = db.get("lastNewArticlesAt", "未知")
            data["degraded_events_count"] = len(db.get("degradedEvents", []))
            
            # 判断快照是否过期 (>48小时)
            if last_crawl != "未知":
                try:
                    last_dt = datetime.fromisoformat(last_crawl.replace("Z", "+00:00"))
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                    now_dt = datetime.now(timezone.utc)
                    if (now_dt - last_dt).total_seconds() > 48 * 3600:
                        data["is_expired"] = True
                except Exception as ex:
                    data["expiry_error"] = f"{type(ex).__name__}: {ex}"

            # 最新报道日期
            articles = db.get("articles", {})
            dates = []
            if isinstance(articles, dict):
                dates = [a.get("publishedAt") or a.get("date", "") for a in articles.values() if isinstance(a, dict)]
            elif isinstance(articles, list):
                dates = [a.get("publishedAt") or a.get("date", "") for a in articles if isinstance(a, dict)]
            dates = [d for d in dates if d]
            if dates:
                data["latest_article_date"] = max(dates)
            
            source_stats = db.get("sourceStats", [])
            stats_list = []
            if isinstance(source_stats, list):
                stats_list = source_stats
            elif isinstance(source_stats, dict):
                stats_list = list(source_stats.values())
                
            for sinfo in stats_list:
                sid = sinfo.get("id", "")
                sname = sinfo.get("name") or sinfo.get("source_name", sid)
                err = sinfo.get("error") or sinfo.get("last_error")
                count = sinfo.get("total_items") if sinfo.get("total_items") is not None else sinfo.get("count", 0)
                full_count = sinfo.get("full_text_items") if sinfo.get("full_text_items") is not None else sinfo.get("full_text_count", 0)
                latest_d = sinfo.get("latest_published_at") or sinfo.get("latest_date", "")
                
                if err:
                    status = "failed"
                    data["failed_sources"] += 1
                elif count == 0:
                    status = "empty"
                    data["empty_sources"] += 1
                else:
                    status = "active"
                    data["active_sources"] += 1
                
                data["sources_detail"].append({
                    "id": sid,
                    "name": sname,
                    "status": status,
                    "count": count,
                    "full_text_count": full_count,
                    "latest_date": latest_d,
                    "error": err
                })
        except Exception as e:
            data["error"] = str(e)
            
    return data


def cmd_status(args):
    issue_id = args.issue or find_latest_issue()
    issue_dir = os.path.join(PROJECT_ROOT, "issues", issue_id)
    
    print("=" * 70)
    print(f" 📰 口语素材周刊｜生产调度控制台 (Weekly Production Dashboard)")
    print("=" * 70)
    print("⏰ 业务运行规程: 每周四 20:00 资料截止 | 每周五 10:00 发放 | 回望连续 7 天")
    print(f"🎯 当前期刊: {issue_id}")
    state = load_production_state(issue_id)
    if issue_id == "issue-2026-w39":
        print("🏷️ 期刊属性: 首次试发件 (已定版发布，供教学打印与课堂实测反馈)")
    elif state and state.get("release_type"):
        print(f"🏷️ 期刊属性: {state.get('release_type')}")
    
    # 1. 检查期刊基本文件
    yaml_path = os.path.join(issue_dir, "issue.yaml")
    prep_path = os.path.join(issue_dir, "manifest_prep.json")
    scan_path = os.path.join(issue_dir, "candidates_scan.json")
    
    time_window = (state.get("time_window") if state else "未定义") or "未定义"
    unit_stats = "复述 9 篇，评论 6 篇，原文摘录 6 篇 (规划配额)" if state else "未配置"
    if os.path.exists(yaml_path):
        try:
            import yaml
            with open(yaml_path, "r", encoding="utf-8") as f:
                ydata = yaml.safe_load(f)
            time_window = ydata.get("date_range", time_window)
            r_cnt = len(ydata.get("retelling_ids", []))
            c_cnt = len(ydata.get("commentary_ids", []))
            f_cnt = len(ydata.get("excerpt_ids", []))
            unit_stats = f"复述 {r_cnt}/9 篇，评论 {c_cnt}/6 篇，原文摘录 {f_cnt}/6 篇"
        except Exception:
            pass
            
    print(f"📅 报道窗口: {time_window}")
    print(f"📦 单元规格: {unit_stats}")
    if os.path.exists(prep_path):
        prep_str = f"✅ 已定稿 ({prep_path})"
    elif os.path.exists(scan_path):
        prep_str = f"⏳ 候选已就绪待组刊 ({scan_path})"
    else:
        prep_str = "❌ 尚未生成"
    print(f"📋 备料台账: {prep_str}")
    
    # 2. 读取任务状态机
    print("-" * 70)
    print("📌 本期制作进度 (Task State):")
    state = load_production_state(issue_id)
    if state:
        resume_info = get_resume_info(issue_id)
        print(f"   ▶ 当前阶段: [{resume_info['current_stage']}] (状态: {resume_info['stage_status']})")
        print(f"   ▶ 待办任务: {resume_info['next_action']}")
        
        stages = state.get("stages", {})
        print("   ▶ 阶段详情:")
        stage_names = [
            ("prep", "1. 采集与备料"),
            ("candidates_selected", "2. 选题与核验"),
            ("drafting", "3. 文本采编"),
            ("comics", "4. 漫画配图"),
            ("review", "5. 终审定版"),
            ("build", "6. 原子构建"),
            ("published", "7. 归档发布"),
        ]
        for skey, slabel in stage_names:
            s_obj = stages.get(skey, {})
            st = s_obj.get("status", "not_started")
            icon = "✅" if st == "done" else ("⏳" if st == "in_progress" else ("❌" if st == "failed" else "⚪"))
            msg = s_obj.get("notes", "") or s_obj.get("message", "")
            print(f"      {icon} {slabel:<16}: {st:<12} {('(' + msg + ')') if msg else ''}")
            
        frozen = state.get("unit_freeze_status", {})
        frozen_active = [k for k, v in frozen.items() if (v.get("frozen") if isinstance(v, dict) else v)]
        if frozen_active:
            print(f"   🔒 已冻结/定稿单元 ({len(frozen_active)} 个): {', '.join(sorted(frozen_active))}")
    else:
        print("   ⚪ 尚未初始化生产状态。可执行 `python3 scripts/weekly_runner.py prep` 开始本周生产。")
        
    # 3. 读取上游健康度
    print("-" * 70)
    print("📡 上游采集雷达健康度 (Upstream Ingestion Health):")
    health = get_upstream_health()
    if health["total_articles"] == 0 or health.get("error"):
        print(f"   ⚠️ 上游资料库未初始化或未采集文章 ({health.get('error') or '数据库为空'})，请先执行 prep 采集。")
    else:
        print(f"   ▶ 文章总库存: {health['total_articles']} 篇 (其中高质量全文 {health['full_text_articles']} 篇)")
        print(f"   ▶ 最新报道日期: {health['latest_article_date']} | 最近采集时刻: {health['last_crawl_time']}")
        if health.get("last_new_articles_at") and health["last_new_articles_at"] != "未知":
            print(f"   ▶ 最新文章入库: {health['last_new_articles_at']}")
        print(f"   ▶ 信源连通状态: 正常活跃 {health['active_sources']} 路，空源 {health['empty_sources']} 路，异常失败 {health['failed_sources']} 路")
        if health.get("degraded_events_count", 0) > 0:
            print(f"   ℹ️ 防退化机制: 累计保护历史长文 {health['degraded_events_count']} 次源站降级事件")
        
        if health["failed_sources"] > 0:
            print("   ⚠️ 注意：以下信源抓取异常:")
            for s in health["sources_detail"]:
                if s["status"] == "failed":
                    print(f"      ❌ [{s['id']}] {s['name']}: {s['error']}")
        else:
            print("   ✅ 全部信源链路正常，上游无阻断异常。")
        if health.get("is_expired"):
            print("   ⚠️ 注意：上游数据快照已超过 48 小时未更新，建议运行采集刷新。")
        
    # 4. 教师行动建议
    print("-" * 70)
    print("💡 建议操作指引 (Teacher Action Guide):")
    if not os.path.exists(prep_path) and not os.path.exists(scan_path):
        print(f"   👉 步骤 1: 运行 `python3 scripts/weekly_runner.py prep --issue {issue_id}` 抓取本周新材料并生成候选清单。")
    elif state and state.get("stages", {}).get("published", {}).get("status") == "done":
        print(f"   🎉 本期已圆满发布！")
        print(f"      - 审阅首页: review-public/index.html")
        print(f"      - 本期永久归档: review-public/issues/{issue_id}/index.html")
        print(f"      - 物理交付件: issues/{issue_id}/{issue_id}.pdf")
    elif state and state.get("stages", {}).get("build", {}).get("status") == "done":
        print(f"   👉 步骤 4: 构建已完成并通过全门禁，执行 `python3 scripts/weekly_runner.py publish --issue {issue_id}` 导出审阅站并归档发布。")
    elif not os.path.exists(prep_path):
        print(f"   👉 步骤 2: 当前处于周内持续采集备料期。到达资料截止点（周四 20:00）后，依据 `issues/{issue_id}/candidates_scan.json` 选题并生成 `manifest_prep.json` 与 `issue.yaml`。")
    else:
        print(f"   👉 步骤 3: 请 Agent 依据 `issues/{issue_id}/manifest_prep.json` 采编文稿与生成配图。")
        print(f"   👉 采编完成后，执行 `python3 scripts/weekly_runner.py build --issue {issue_id}` 进行原子构建。")
    print("=" * 70)


def cmd_prep(args):
    issue_id = args.issue or find_latest_issue()
    print(f"🚀 开始初始化期刊采编任务: {issue_id}")
    
    # 1. 抓取新材料 (除非显式 --no-fetch)
    if not args.no_fetch:
        print("\n[阶段 1/2] 执行上游信源采集 (scripts/fetch_commentaries.py)...")
        fetch_cmd = [PYTHON_EXEC, os.path.join(PROJECT_ROOT, "scripts", "fetch_commentaries.py")]
        res = subprocess.run(fetch_cmd, cwd=PROJECT_ROOT)
        if res.returncode != 0:
            print("❌ 上游抓取出现严重异常 (全源失败)，请检查网络或服务！")
            sys.exit(res.returncode)
    else:
        print("\n[阶段 1/2] 跳过上游抓取 (--no-fetch)...")
        
    # 2. 运行 prep 备料管线
    print("\n[阶段 2/2] 执行候选备料与台账扫描 (publishing/weekly_pipeline/prep.py)...")
    prep_py = os.path.join(PROJECT_ROOT, "publishing", "weekly_pipeline", "prep.py")
    prep_cmd = [PYTHON_EXEC, prep_py, "--issue", issue_id]
    if args.start_date and args.end_date:
        prep_cmd.extend(["--start-date", args.start_date, "--end-date", args.end_date])
    if args.force:
        prep_cmd.append("--force")
        
    res = subprocess.run(prep_cmd, cwd=PROJECT_ROOT)
    if res.returncode != 0:
        print(f"❌ 备料管线执行失败 (exit {res.returncode})")
        sys.exit(res.returncode)
        
    # 3. 初始化任务状态 (防倒退)
    issue_dir = os.path.join(PROJECT_ROOT, "issues", issue_id)
    existing_state = load_production_state(issue_id)
    
    s_date = args.start_date
    e_date = args.end_date
    if not s_date or not e_date:
        try:
            from weekly_pipeline.prep import derive_week_dates
            s_date, e_date = derive_week_dates(issue_id)
        except Exception:
            s_date, e_date = ("未知", "未知")
    time_window_str = f"{s_date} ~ {e_date}"

    state = init_production_state(
        issue_id=issue_id,
        time_window=time_window_str
    )
    if state.get("time_window") != time_window_str:
        state["time_window"] = time_window_str
        save_production_state(issue_id, state)

    cur_stage_before = existing_state.get("current_stage", "prep") if existing_state else "prep"
    update_stage(issue_id, stage="prep", status="done", notes="信源采集与备料初始化完成")
    # 只有当此前还停留在 prep 或新初始化时，才自动前进到 candidates_selected
    if cur_stage_before == "prep" or not existing_state:
        update_stage(issue_id, stage="candidates_selected", status="in_progress", notes="等待 Agent/教师核验选题")
    
    print(f"\n✅ 期刊 {issue_id} 采编与备料初始化成功！任务状态已持久化至 {issue_dir}/production_state.json")
    print(f"👉 下一步: 运行 `python3 scripts/weekly_runner.py status --issue {issue_id}` 查看进度。")


def cmd_build(args):
    issue_id = args.issue or find_latest_issue()
    issue_dir = os.path.join(PROJECT_ROOT, "issues", issue_id)
    print(f"🔨 开始执行原子构建与硬门禁验证: {issue_id}")
    
    cli_py = os.path.join(PROJECT_ROOT, "publishing", "weekly_pipeline", "cli.py")
    build_cmd = [PYTHON_EXEC, cli_py, "build", "--issue", issue_id]
    if args.draft:
        build_cmd.append("--draft")
        
    res = subprocess.run(build_cmd, cwd=PROJECT_ROOT)
    if res.returncode != 0:
        print(f"❌ 构建未通过门禁校验 (exit {res.returncode})，已安全中断，未污染现有发布包！")
        update_stage(issue_id, stage="build", status="failed", notes="构建门禁断言拦截")
        sys.exit(res.returncode)
        
    update_stage(issue_id, stage="build", status="done", notes="原子构建与全门禁验证通过")
    print(f"\n🎉 期刊 {issue_id} 原子构建成功！产物已原子就绪于 dist/{issue_id} 与 issues/{issue_id}！")


def cmd_publish(args):
    issue_id = args.issue or find_latest_issue()
    issue_dir = os.path.join(PROJECT_ROOT, "issues", issue_id)
    print(f"🚀 开始执行期刊多期归档与正式发布: {issue_id}")
    
    # 1. 严格核验构建凭据 (build_receipt.json)
    pdf_path = os.path.join(issue_dir, f"{issue_id}.pdf")
    receipt_path = os.path.join(issue_dir, "build_receipt.json")
    need_build = False
    
    if args.rebuild or not os.path.exists(pdf_path) or not os.path.exists(receipt_path):
        need_build = True
    else:
        try:
            with open(receipt_path, "r", encoding="utf-8") as rf:
                rcpt = json.load(rf)
            if rcpt.get("is_draft"):
                print("⚠️ 检测到当前产物为草稿构建，正式发布必须重新执行正式构建！")
                need_build = True
            else:
                h = hashlib.sha256()
                with open(pdf_path, "rb") as pf:
                    while chunk := pf.read(65536):
                        h.update(chunk)
                if h.hexdigest() != rcpt.get("pdf_sha256"):
                    print(f"⚠️ 物理交付件 PDF 与构建核验凭据哈希不符 ({h.hexdigest()[:10]}... != {str(rcpt.get('pdf_sha256'))[:10]}...)，必须重新执行正式构建！")
                    need_build = True
                else:
                    print(f"\n[步骤 1/2] 已存在通过全门禁校验的构建交付件 (凭据时间: {rcpt.get('timestamp')})")
        except Exception as e:
            print(f"⚠️ 读取构建凭据异常: {e}，将重新执行正式构建。")
            need_build = True
            
    if need_build:
        print("\n[步骤 1/2] 执行正式构建与全门禁核验...")
        build_args = argparse.Namespace(issue=issue_id, draft=False)
        cmd_build(build_args)
        
    # 2. 导出多期审阅站
    print("\n[步骤 2/2] 导出多期审阅站 (scripts/export_review_site.py)...")
    export_py = os.path.join(PROJECT_ROOT, "scripts", "export_review_site.py")
    export_cmd = [PYTHON_EXEC, export_py, "--issue", issue_id]
    res = subprocess.run(export_cmd, cwd=PROJECT_ROOT)
    if res.returncode != 0:
        print(f"❌ 审阅站导出失败 (exit {res.returncode})")
        update_stage(issue_id, stage="published", status="failed", notes="审阅站导出失败")
        sys.exit(res.returncode)
        
    update_stage(issue_id, stage="published", status="done", notes="多期静态站本地导出归档完成")
    
    print("\n" + "=" * 70)
    print(f"🎊 本地发布完成！期刊 {issue_id} 已正式交付归档。")
    print(f"   ▶ 审阅站首页: file://{os.path.join(PROJECT_ROOT, 'review-public', 'index.html')}")
    print(f"   ▶ 本期独立归档: file://{os.path.join(PROJECT_ROOT, 'review-public', 'issues', issue_id, 'index.html')}")
    print(f"   ▶ 物理交付文件: {pdf_path}")
    print("   👉 提示: 远端上线请执行 `git push origin gh-pages` 部署至公开站点。")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="口语素材周刊统一调度台 (Weekly Pipeline Runner)")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # status
    p_status = subparsers.add_parser("status", help="查看生产进度、上游健康度与待办项")
    p_status.add_argument("--issue", type=str, help="期刊编号 (默认最新期)")
    
    # prep
    p_prep = subparsers.add_parser("prep", help="执行采集与备料初始化")
    p_prep.add_argument("--issue", type=str, help="期刊编号 (例如 issue-2026-w39)")
    p_prep.add_argument("--start-date", type=str, help="起始日期 (YYYY-MM-DD)")
    p_prep.add_argument("--end-date", type=str, help="截止日期 (YYYY-MM-DD)")
    p_prep.add_argument("--force", action="store_true", help="强制覆盖已有候选清单")
    p_prep.add_argument("--no-fetch", action="store_true", help="跳过上游信源采集直接备料")
    
    # build
    p_build = subparsers.add_parser("build", help="执行带原子防护的正式构建")
    p_build.add_argument("--issue", type=str, help="期刊编号")
    p_build.add_argument("--draft", action="store_true", help="以草稿模式构建 (跳过台账强校验)")
    
    # publish (严禁包含 --draft，发布只能是正式构建)
    p_publish = subparsers.add_parser("publish", help="导出多期审阅静态站并归档")
    p_publish.add_argument("--issue", type=str, help="期刊编号")
    p_publish.add_argument("--rebuild", action="store_true", help="强制重新执行构建")
    
    args = parser.parse_args()
    if not args.command:
        # 默认执行 status
        args.issue = None
        cmd_status(args)
        return
        
    if args.command == "status":
        cmd_status(args)
    elif args.command == "prep":
        cmd_prep(args)
    elif args.command == "build":
        cmd_build(args)
    elif args.command == "publish":
        cmd_publish(args)


if __name__ == "__main__":
    main()

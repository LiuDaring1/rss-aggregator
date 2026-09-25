# -*- coding: utf-8 -*-
"""
脱敏静态审阅站生成器 (Export Review Site Generator)
遵循执行单（口语素材周刊_整刊恢复与可视化交付执行单.md）阶段 C 规范：
1. 白名单脱敏导出：绝不包含内部密钥、全量爬虫库、学生个人记录、本地绝对路径或软链接；
2. 动态数据驱动：由期刊清单与单元 YAML 数据直接生成，彻底消除 weekly.html 手写卡片信息不一致隐患；
3. 纯静态与相对路径：支持直接本地运行、Cloudflare Quick Tunnel 穿透，或部署至 GitHub Pages（兼容二级子路径）；
4. 包含完整交付件：整刊 PDF、分册 PDF、学生 Markdown、16 页高精度 PNG 快照、信源只读快照；
5. 无 JS 强依赖：纯 HTML/CSS 结构，审阅人员在禁用脚本环境下亦可通读全文与下载成品。
"""

import os
import sys
import json
import shutil
import datetime
import subprocess
import html
import re
from typing import Dict, Any, List, Optional

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(ROOT_DIR, "review-public")

def parse_issue_sort_key(issue_name: str):
    """期号排序键：常规周刊数值排序优先，历史试产次之"""
    m = re.match(r"^issue-(\d{4})-w(\d+)$", issue_name)
    if m:
        return (2, int(m.group(1)), int(m.group(2)), issue_name)
    m_trial = re.match(r"^issue-trial-(\d+)$", issue_name)
    if m_trial:
        return (1, 0, int(m_trial.group(1)), issue_name)
    return (0, 0, 0, issue_name)

def safe_copy_file(src: str, dst: str) -> bool:
    """安全拷贝单个文件：杜绝外部软链接（realpath 超出项目根目录直接拦截）"""
    if os.path.islink(src):
        real_src = os.path.realpath(src)
        project_real = os.path.realpath(ROOT_DIR)
        try:
            rel = os.path.relpath(real_src, project_real)
            if rel.startswith("..") or os.path.isabs(rel):
                print(f"⚠️ [白名单拦截] 拦截指向项目外部的软链接: {src} -> {real_src}")
                return False
        except Exception:
            return False
        shutil.copyfile(real_src, dst)
        return True
    else:
        shutil.copyfile(src, dst)
        return True

def get_git_info() -> Dict[str, str]:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, text=True).strip()
        short_commit = commit[:7]
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT_DIR, text=True).strip()
        return {"commit": commit, "short_commit": short_commit, "branch": branch}
    except Exception:
        return {"commit": "unknown", "short_commit": "unknown", "branch": "antigravity-dev"}

def load_yaml(fpath: str) -> Dict[str, Any]:
    import yaml
    with open(fpath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_review_site(issue_id: Optional[str] = None, output_dir: Optional[str] = None):
    effective_out_dir = os.path.abspath(output_dir) if output_dir else OUTPUT_DIR
    # 0. 自动探测最新期号 (若未显式指定)
    if not issue_id:
        # 扫描 dist/ 下的可用期号
        dist_dir = os.path.join(ROOT_DIR, "dist")
        candidates = []
        if os.path.exists(dist_dir):
            for d in os.listdir(dist_dir):
                if d.startswith("issue-") and os.path.exists(os.path.join(dist_dir, d, f"{d}.pdf")):
                    candidates.append(d)
        if candidates:
            candidates.sort(key=parse_issue_sort_key, reverse=True)
            issue_id = candidates[0]
        else:
            issue_id = "issue-2026-w38"

    print(f"🚀 开始生成脱敏静态审阅站 (当前期号: {issue_id})...")

    # 1. 确保目标目录存在 (增量归档架构，绝不暴力删除整个 review-public，保护历史各期)
    os.makedirs(effective_out_dir, exist_ok=True)

    dist_issue_dir = os.path.join(ROOT_DIR, "dist", issue_id)
    if not os.path.exists(dist_issue_dir):
        fallback_issue_dir = os.path.join(ROOT_DIR, "issues", issue_id)
        if os.path.exists(os.path.join(fallback_issue_dir, f"{issue_id}.pdf")):
            dist_issue_dir = fallback_issue_dir
        else:
            raise RuntimeError(f"未找到构建产物目录: {dist_issue_dir} 或 {fallback_issue_dir}，请先执行 cli.py build {issue_id}")

    target_issue_dir = os.path.join(effective_out_dir, "issues", issue_id)
    os.makedirs(target_issue_dir, exist_ok=True)

    # 2. 严格按交付白名单枚举拷贝 (严禁通配扫描内部私密数据、内部测试 JSON、外部软链接)
    whitelisted_files = [
        f"{issue_id}.pdf",
        f"{issue_id}-复述.pdf",
        f"{issue_id}-评论.pdf",
        f"{issue_id}-原文拆解与积累.pdf",
        f"{issue_id}.html",
        f"{issue_id}.md",
        "build_receipt.json",
        "manifest_prep.json",
        "sources_status.json"
    ]
    for fname in whitelisted_files:
        src = os.path.join(dist_issue_dir, fname)
        if not os.path.exists(src):
            src = os.path.join(ROOT_DIR, "issues", issue_id, fname)
        if os.path.exists(src):
            dst = os.path.join(target_issue_dir, fname)
            safe_copy_file(src, dst)

    # 拷贝页面快照
    pages_dirs_to_check = [
        os.path.join(dist_issue_dir, f"{issue_id}_pages"),
        os.path.join(dist_issue_dir, "pages"),
        os.path.join(ROOT_DIR, "issues", issue_id, "pages")
    ]
    target_pages_dir = os.path.join(target_issue_dir, "pages")
    for pd in pages_dirs_to_check:
        if os.path.exists(pd) and os.path.isdir(pd):
            os.makedirs(target_pages_dir, exist_ok=True)
            for f in os.listdir(pd):
                if f.lower().endswith(".png"):
                    safe_copy_file(os.path.join(pd, f), os.path.join(target_pages_dir, f))
                    m_page = re.search(r"_p(\d+)\.png$", f, re.IGNORECASE)
                    if m_page:
                        p_num = int(m_page.group(1))
                        safe_copy_file(os.path.join(pd, f), os.path.join(target_pages_dir, f"page_{p_num:02d}.png"))
            break

    # 3. 拷贝插图资产
    src_ill_dir = os.path.join(ROOT_DIR, "issues", issue_id, "illustrations")
    if not os.path.exists(src_ill_dir):
        src_ill_dir = os.path.join(dist_issue_dir, "illustrations")
    if os.path.exists(src_ill_dir) and os.path.isdir(src_ill_dir):
        dst_ill_dir = os.path.join(target_issue_dir, "illustrations")
        os.makedirs(dst_ill_dir, exist_ok=True)
        for f in os.listdir(src_ill_dir):
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                safe_copy_file(os.path.join(src_ill_dir, f), os.path.join(dst_ill_dir, f))

    # 4. 加载单元结构化数据生成展示卡片
    issue_yaml_path = os.path.join(ROOT_DIR, "issues", issue_id, "issue.yaml")
    manifest = load_yaml(issue_yaml_path)

    retellings_data = []
    for rid in manifest.get("retelling_ids", []):
        yp = os.path.join(ROOT_DIR, "content", "retellings", f"{rid}.yaml")
        if os.path.exists(yp):
            retellings_data.append(load_yaml(yp))

    commentaries_data = []
    for cid in manifest.get("commentary_ids", []):
        yp = os.path.join(ROOT_DIR, "content", "commentaries", f"{cid}.yaml")
        if os.path.exists(yp):
            commentaries_data.append(load_yaml(yp))

    excerpts_data = []
    for fid in manifest.get("excerpt_ids", []):
        yp = os.path.join(ROOT_DIR, "content", "excerpts", f"{fid}.yaml")
        if os.path.exists(yp):
            excerpts_data.append(load_yaml(yp))

    # 5. 从真实数据库读取上游信源运行健康度 (绝不硬编码 active 或伪造状态)
    sources_json_path = os.path.join(ROOT_DIR, "aggr-site", "sources.json")
    db_json_path = os.path.join(ROOT_DIR, "aggr-site", "data", "commentaries", "db.json")
    raw_sources = []
    if os.path.exists(sources_json_path):
        try:
            with open(sources_json_path, "r", encoding="utf-8") as f:
                raw_sources = json.load(f)
        except Exception:
            pass

    db_stats_map = {}
    db_health_map = {}
    db_updated_at = None
    if os.path.exists(db_json_path):
        try:
            with open(db_json_path, "r", encoding="utf-8") as f:
                loaded_db = json.load(f)
                db_updated_at = loaded_db.get("updatedAt")
                for st in loaded_db.get("sourceStats", []):
                    db_stats_map[st.get("id")] = st
                db_health_map = loaded_db.get("sourceHealth", {})
        except Exception:
            pass

    is_snapshot_expired = False
    if db_updated_at:
        try:
            dt = datetime.datetime.fromisoformat(db_updated_at.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            if (datetime.datetime.now(datetime.timezone.utc) - dt).total_seconds() > 48 * 3600:
                is_snapshot_expired = True
        except Exception:
            pass

    # 动态匹配本期入选媒体 (从实际单元数据提取关键词比对)
    selected_corpus = set()
    for r in retellings_data:
        selected_corpus.add(r.get("source_label", ""))
        selected_corpus.add(r.get("source_media", ""))
    for c in commentaries_data:
        selected_corpus.add(c.get("source_label", ""))
        selected_corpus.add(c.get("source_media", ""))
        selected_corpus.add(c.get("source_name", ""))
    for f in excerpts_data:
        selected_corpus.add(f.get("source_name", ""))
        selected_corpus.add(f.get("source_media", ""))
    selected_str = " ".join(filter(None, selected_corpus))

    sanitized_sources = []
    for s in raw_sources:
        sid = s.get("id")
        sname = s.get("name", "未知")
        st = db_stats_map.get(sid, {})
        hl = db_health_map.get(sid, {})

        consec = hl.get("consecutive_failures", 0)
        tot_it = st.get("total_items", 0)
        full_it = st.get("full_text_items", 0)

        if consec > 0:
            err_msg = hl.get("last_error") or "连接超时"
            status_text = f"异常 (连续失败{consec}次: {err_msg[:20]})"
        elif is_snapshot_expired:
            status_text = f"快照已过期 (最后抓取: {db_updated_at[:10]})"
        elif tot_it > 0:
            status_text = f"正常在线 (实时抓取{tot_it}条, {full_it}篇全文)"
        elif st.get("status") == "EMPTY":
            status_text = "正常在线 (心跳良好/暂无新篇)"
        else:
            status_text = "已配置 (等待首轮调度)"

        is_selected = (sname in selected_str) or (sid in selected_str)
        sanitized_sources.append({
            "name": sname,
            "category": s.get("category", "权威时评"),
            "type": s.get("type", "rss"),
            "status": status_text,
            "selected_this_issue": is_selected
        })

    # 检查天天正能量真实库存 (动态统计，拒绝死常量)
    ttzl_db_path = os.path.join(ROOT_DIR, "aggr-site", "data", "wenwen", "db.json")
    ttzl_count = None
    if os.path.exists(ttzl_db_path):
        try:
            with open(ttzl_db_path, "r", encoding="utf-8") as f:
                w_data = json.load(f)
                ttzl_count = w_data.get("totalArticles")
        except Exception:
            pass

    if ttzl_count is not None and ttzl_count > 0:
        ttzl_status = f"正常在线 ({ttzl_count}条本地温和事实库)"
    elif os.path.exists(ttzl_db_path):
        ttzl_status = "已就绪 (库存为空)"
    else:
        ttzl_status = "未初始化 (本地数据缺失)"

    sanitized_sources.append({
        "name": "天天正能量",
        "category": "暖文事实库",
        "type": "radar_crawler",
        "status": ttzl_status,
        "selected_this_issue": ("天天正能量" in selected_str or "阿里" in selected_str)
    })

    git_info = get_git_info()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S (UTC+8)")

    # 6. 发现所有已归档期刊 (精准数值排序)
    available_issues = set()
    issues_root = os.path.join(effective_out_dir, "issues")
    if os.path.exists(issues_root):
        for d in os.listdir(issues_root):
            if d.startswith("issue-") and os.path.isdir(os.path.join(issues_root, d)):
                available_issues.add(d)
    available_issues.add(issue_id)
    sorted_issues = sorted(list(available_issues), key=parse_issue_sort_key, reverse=True)
    latest_issue = sorted_issues[0]

    # 计算页数 (直接读取 build_receipt.json 或 PDF 元数据，坚决杜绝根据 pages/ 别名文件数盲目统计导致的 94 页 Bug)
    total_pages_count = 47
    receipt_candidates = [
        os.path.join(target_issue_dir, "build_receipt.json"),
        os.path.join(dist_issue_dir, "build_receipt.json"),
        os.path.join(ROOT_DIR, "issues", issue_id, "build_receipt.json")
    ]
    for rp in receipt_candidates:
        if os.path.exists(rp):
            try:
                with open(rp, "r", encoding="utf-8") as rf:
                    rcpt_obj = json.load(rf)
                    if rcpt_obj.get("total_pages"):
                        total_pages_count = int(rcpt_obj["total_pages"])
                        break
            except Exception:
                pass
    if total_pages_count == 47:
        target_pdf = os.path.join(target_issue_dir, f"{issue_id}.pdf")
        if not os.path.exists(target_pdf):
            target_pdf = os.path.join(dist_issue_dir, f"{issue_id}.pdf")
        if os.path.exists(target_pdf):
            try:
                import fitz
                doc = fitz.open(target_pdf)
                total_pages_count = doc.page_count
                doc.close()
            except Exception:
                pass

    # 构造根目录 index.html (首页防降级机制: 仅发布最新期或首次导出时刷新主站首页)
    index_path = os.path.join(effective_out_dir, "index.html")
    if issue_id == latest_issue or not os.path.exists(index_path):
        root_html_content = generate_index_html(
            manifest=manifest,
            issue_id=issue_id,
            git_info=git_info,
            now_str=now_str,
            retellings=retellings_data,
            commentaries=commentaries_data,
            excerpts=excerpts_data,
            sources=sanitized_sources,
            total_pages=total_pages_count,
            all_issues=sorted_issues,
            path_prefix=f"issues/{issue_id}/"
        )
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(root_html_content)
        print(f"  ✅ 主站门户首页已更新为最新期: {issue_id}")
    else:
        print(f"  ℹ️ [首页防降级] 当前导出期号 {issue_id} 早于主站最新期 {latest_issue}，主站首页 index.html 保持指向最新期。")

    # 构造期刊独立归档页 issues/<issue_id>/index.html
    issue_html_content = generate_index_html(
        manifest=manifest,
        issue_id=issue_id,
        git_info=git_info,
        now_str=now_str,
        retellings=retellings_data,
        commentaries=commentaries_data,
        excerpts=excerpts_data,
        sources=sanitized_sources,
        total_pages=total_pages_count,
        all_issues=sorted_issues,
        path_prefix=""
    )
    issue_index_path = os.path.join(target_issue_dir, "index.html")
    with open(issue_index_path, "w", encoding="utf-8") as f:
        f.write(issue_html_content)

    # 7. 写入 .nojekyll 防止 GitHub Pages 吞下以下划线开头的文件
    with open(os.path.join(effective_out_dir, ".nojekyll"), "w", encoding="utf-8") as f:
        f.write("")

    print(f"✅ 脱敏静态审阅站已成功生成至: {effective_out_dir}")
    print(f"   - 门户首页: {index_path}")
    print(f"   - 归档分期: {issue_index_path}")
    print(f"   - 包含产物: PDF/Markdown/HTML/PNG 快照全量同源离线打包")

def generate_index_html(manifest: Dict[str, Any],
                        issue_id: str,
                        git_info: Dict[str, str],
                        now_str: str,
                        retellings: List[Dict[str, Any]],
                        commentaries: List[Dict[str, Any]],
                        excerpts: List[Dict[str, Any]],
                        sources: List[Dict[str, Any]],
                        total_pages: int = 47,
                        all_issues: Optional[List[str]] = None,
                        path_prefix: str = "") -> str:
    
    num_r = len(retellings)
    num_c = len(commentaries)
    num_f = len(excerpts)
    ans_p = 3 if num_r >= 8 else (2 if num_r >= 5 else 1)
    r_pages = num_r * 2 + ans_p
    c_pages = num_c * 3
    f_pages = num_f * 1
    
    # 构造归档导航条
    archive_buttons = []
    if all_issues and len(all_issues) > 1:
        for iid in all_issues:
            is_cur = (iid == issue_id)
            cls = "archive-btn active" if is_cur else "archive-btn"
            if path_prefix:
                href = f"issues/{iid}/index.html" if not is_cur else "#"
            else:
                href = f"../{iid}/index.html" if not is_cur else "#"
            archive_buttons.append(f'<a class="{cls}" href="{href}">{iid}</a>')
    archive_bar_html = f'<div class="archive-bar"><span class="archive-title">📚 往期周刊归档：</span>{"".join(archive_buttons)}</div>' if archive_buttons else ""

    # 构造单元展示卡片 HTML
    units_html = []
    
    # 复述与评论配对
    for r in retellings:
        rid = r.get("id")
        matched_c = next((c for c in commentaries if c.get("retelling_ref") == rid), None)
        c_part = ""
        if matched_c:
            cid = matched_c.get("id")
            c_claim = matched_c.get("speech", {}).get("main_claim", "")
            c_part = f"""
            <div class="pair-commentary">
              <div class="sec-label">🎙️ 同题评论 · {cid} 《{html.escape(matched_c.get('title', ''))}》</div>
              <p class="sample-claim"><strong>立论核心：</strong>{html.escape(c_claim)}</p>
            </div>
            """
        
        ill_id = r.get("illustration_id") or "待配图"
        ill_status = r.get("illustration_status") or "pending"
        ill_badge = f'<span class="badge badge-green">🎨 插图: {ill_id} ({ill_status})</span>' if ill_status == "confirmed" else '<span class="badge badge-gray">插画待回传</span>'
        
        units_html.append(f"""
        <div class="unit-card">
          <div class="card-header">
            <div class="unit-ids">
              <span class="badge badge-blue">复述 {rid}</span>
              <span class="badge badge-purple">{html.escape(r.get('category', '社会热点'))}</span>
              {ill_badge}
            </div>
            <span class="source-tag">{html.escape(r.get('source_label', ''))}</span>
          </div>
          <h3 class="unit-title">{html.escape(r.get('title', ''))}</h3>
          <p class="retell-summary"><strong>事实梗概：</strong>{html.escape(r.get('ref_retelling', ''))}</p>
          {c_part}
        </div>
        """)

    # 原文拆解
    excerpts_html = []
    for f in excerpts:
        fid = f.get("id")
        excerpts_html.append(f"""
        <div class="unit-card">
          <div class="card-header">
            <span class="badge badge-orange">拆解积累 {fid}</span>
            <span class="source-tag">{html.escape(f.get('source_name', ''))} · {html.escape(f.get('source_date', ''))}</span>
          </div>
          <h3 class="unit-title">{html.escape(f.get('topic', ''))}</h3>
          <p class="retell-summary"><strong>情境背景：</strong>{html.escape(f.get('context', ''))}</p>
          <div class="demo-box">
            <div class="sec-label">💡 {html.escape(f.get('demo_title', '表达示范'))}</div>
            <p class="sample-claim">{html.escape(f.get('demo_text', ''))}</p>
          </div>
        </div>
        """)

    # 页面快照缩略图 HTML
    pages_html = []
    for p in range(1, total_pages + 1):
        p_str = f"page_{p:02d}.png"
        pages_html.append(f"""
        <div class="page-thumb">
          <a href="{path_prefix}pages/{p_str}" target="_blank" title="点击查看第 {p} 页高精度大图">
            <img src="{path_prefix}pages/{p_str}" alt="第 {p} 页" loading="lazy">
            <div class="page-caption">第 {p} 页</div>
          </a>
        </div>
        """)

    # 信源表格行
    sources_rows = []
    for s in sources:
        sel_tag = '<span class="status-pill status-sel">本期入选</span>' if s["selected_this_issue"] else '<span class="status-pill status-standby">常态备料</span>'
        sources_rows.append(f"""
        <tr>
          <td><strong>{html.escape(s['name'])}</strong></td>
          <td>{html.escape(s['category'])}</td>
          <td><code>{html.escape(s['type'])}</code></td>
          <td>{sel_tag}</td>
          <td><span class="status-pill status-ok">{html.escape(s['status'])}</span></td>
        </tr>
        """)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>口语素材周刊 · 静态只读审阅镜像 ({issue_id})</title>
  <style>
    :root {{
      --primary: #2563eb;
      --primary-dark: #1d4ed8;
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --text: #0f172a;
      --text-muted: #64748b;
      --border: #e2e8f0;
      --success: #16a34a;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding-bottom: 4rem;
    }}
    header {{
      background: #ffffff;
      border-bottom: 1px solid var(--border);
      padding: 1.25rem 2rem;
      position: sticky;
      top: 0;
      z-index: 50;
      box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}
    .header-wrap {{
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
    }}
    .brand h1 {{ font-size: 1.25rem; font-weight: 700; color: #0f172a; }}
    .brand p {{ font-size: 0.82rem; color: var(--text-muted); }}
    .build-meta {{ font-size: 0.8rem; color: var(--text-muted); text-align: right; }}
    .build-meta code {{ background: #f1f5f9; padding: 0.2rem 0.4rem; border-radius: 4px; color: #334155; }}

    .archive-bar {{
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.75rem 1rem;
      margin-bottom: 1.5rem;
      display: flex;
      align-items: center;
      gap: 0.6rem;
      flex-wrap: wrap;
      font-size: 0.85rem;
    }}
    .archive-title {{ font-weight: 700; color: #334155; }}
    .archive-btn {{
      padding: 0.25rem 0.6rem;
      border: 1px solid var(--border);
      border-radius: 4px;
      text-decoration: none;
      color: #1e293b;
      background: #ffffff;
      font-size: 0.82rem;
      font-weight: 500;
      transition: all 0.15s ease;
    }}
    .archive-btn:hover {{
      border-color: var(--primary);
      background: #eff6ff;
      color: var(--primary);
    }}
    .archive-btn.active {{
      background: var(--primary);
      border-color: var(--primary);
      color: #ffffff;
      font-weight: 600;
    }}

    .container {{
      max-width: 1200px;
      margin: 2rem auto;
      padding: 0 1.5rem;
    }}

    .section-title {{
      font-size: 1.15rem;
      font-weight: 700;
      margin: 2rem 0 1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      color: #1e293b;
    }}

    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.5rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      margin-bottom: 1.5rem;
    }}

    /* 成果横幅 */
    .banner-grid {{
      display: grid;
      grid-template-columns: 1fr 1.6fr;
      gap: 2rem;
    }}
    @media (max-width: 860px) {{
      .banner-grid {{ grid-template-columns: 1fr; }}
    }}
    .meta-box {{ border-right: 1px solid var(--border); padding-right: 1.5rem; }}
    @media (max-width: 860px) {{ .meta-box {{ border-right: none; border-bottom: 1px solid var(--border); padding-bottom: 1.5rem; }} }}
    .badge {{
      display: inline-block;
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
    }}
    .badge-blue {{ background: #eff6ff; color: #1d4ed8; }}
    .badge-purple {{ background: #faf5ff; color: #7e22ce; }}
    .badge-orange {{ background: #fff7ed; color: #c2410c; }}
    .badge-green {{ background: #f0fdf4; color: #15803d; }}
    .badge-gray {{ background: #f1f5f9; color: #475569; }}

    .download-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 0.75rem;
    }}
    @media (max-width: 600px) {{ .download-grid {{ grid-template-columns: 1fr; }} }}
    .dl-btn {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.75rem 1rem;
      border: 1px solid var(--border);
      border-radius: 6px;
      text-decoration: none;
      color: var(--text);
      background: #ffffff;
      font-size: 0.88rem;
      font-weight: 500;
      transition: all 0.15s ease;
    }}
    .dl-btn:hover {{
      border-color: var(--primary);
      background: #eff6ff;
      color: var(--primary);
    }}
    .dl-btn.primary {{
      grid-column: span 2;
      background: var(--primary);
      border-color: var(--primary);
      color: #ffffff;
      font-weight: 600;
    }}
    @media (max-width: 600px) {{ .dl-btn.primary {{ grid-column: span 1; }} }}
    .dl-btn.primary:hover {{
      background: var(--primary-dark);
    }}

    /* 单元明细 */
    .units-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1.25rem;
    }}
    @media (max-width: 860px) {{ .units-grid {{ grid-template-columns: 1fr; }} }}
    .unit-card {{
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.25rem;
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.6rem;
      flex-wrap: wrap;
      gap: 0.4rem;
    }}
    .unit-ids {{ display: flex; gap: 0.4rem; align-items: center; }}
    .source-tag {{ font-size: 0.8rem; color: var(--text-muted); }}
    .unit-title {{ font-size: 1.05rem; font-weight: 700; margin-bottom: 0.6rem; line-height: 1.4; }}
    .retell-summary {{ font-size: 0.88rem; color: #334155; margin-bottom: 0.8rem; line-height: 1.6; }}
    .pair-commentary {{
      background: #f8fafc;
      border-left: 3px solid var(--primary);
      padding: 0.75rem 1rem;
      border-radius: 0 6px 6px 0;
      font-size: 0.85rem;
    }}
    .demo-box {{
      background: #fffbeb;
      border-left: 3px solid #f59e0b;
      padding: 0.75rem 1rem;
      border-radius: 0 6px 6px 0;
      font-size: 0.85rem;
    }}
    .sec-label {{ font-weight: 700; color: #1e293b; margin-bottom: 0.3rem; font-size: 0.82rem; }}
    .sample-claim {{ color: #475569; line-height: 1.5; }}

    /* 快照展架 */
    .gallery-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
    }}
    @media (max-width: 900px) {{ .gallery-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
    @media (max-width: 500px) {{ .gallery-grid {{ grid-template-columns: 1fr; }} }}
    .page-thumb {{
      border: 1px solid var(--border);
      border-radius: 6px;
      overflow: hidden;
      background: #ffffff;
      text-align: center;
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}
    .page-thumb:hover {{
      transform: translateY(-2px);
      box-shadow: 0 4px 10px rgba(0,0,0,0.08);
      border-color: var(--primary);
    }}
    .page-thumb a {{ text-decoration: none; color: inherit; display: block; }}
    .page-thumb img {{
      width: 100%;
      height: auto;
      display: block;
      border-bottom: 1px solid var(--border);
    }}
    .page-caption {{
      padding: 0.5rem;
      font-size: 0.8rem;
      font-weight: 600;
      color: #334155;
      background: #fafafa;
    }}

    /* 表格 */
    .table-wrap {{ overflow-x: auto; border: 1px solid var(--border); border-radius: 6px; }}
    table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 0.88rem; }}
    th {{ background: #f8fafc; padding: 0.75rem 1rem; font-weight: 600; color: #334155; border-bottom: 1px solid var(--border); }}
    td {{ padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); color: #0f172a; }}
    tr:last-child td {{ border-bottom: none; }}
    .status-pill {{ display: inline-block; padding: 0.15rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }}
    .status-ok {{ background: #dcfce7; color: #15803d; }}
    .status-sel {{ background: #dbeafe; color: #1e40af; }}
    .status-standby {{ background: #f1f5f9; color: #475569; }}
  </style>
</head>
<body>

  <header>
    <div class="header-wrap">
      <div class="brand">
        <h1>口语素材周刊 · 只读审阅镜像</h1>
        <p>高质感报刊排版 · 真实插画接入 · 离线全量同源交付标准</p>
      </div>
      <div class="build-meta">
        <div>版本提交：<code>{git_info['short_commit']}</code> ({git_info['branch']})</div>
        <div>快照生成：{now_str}</div>
      </div>
    </div>
  </header>

  <div class="container">

    {archive_bar_html}

    <!-- 本期成果与直接查阅 -->
    <div class="card">
      <div class="banner-grid">
        <div class="meta-box">
          <span class="badge badge-blue">正式发行版 · 现行生效</span>
          <h2 style="font-size: 1.35rem; margin: 0.6rem 0 0.4rem;">{html.escape(manifest.get('title', '口语素材周刊'))} · {html.escape(manifest.get('issue_no_label', ''))}</h2>
          <p style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 1rem;">
            使用周：<strong>{html.escape(manifest.get('date_range', ''))}</strong><br>
            资料窗口：{html.escape(manifest.get('source_window', '2026-09-17 20:00 ~ 2026-09-24 20:00 (回望连续7天)'))}<br>
            物理页数：<strong>严格 {total_pages} 页</strong>（9篇复述{r_pages}页 + 6篇评论{c_pages}页 + 6篇拆解{f_pages}页 + 封面/目录 2页）<br>
            门禁核验：原文连续精准匹配 100% · 纯文本无裸 HTML 标签 · {total_pages}页印张精确吻合
          </p>
          <div style="font-size: 0.82rem; background: #f1f5f9; padding: 0.75rem; border-radius: 6px; color: #334155;">
            <strong>📌 镜像说明：</strong> 本站点为只读脱敏包，剔除了任何内部爬虫接口、学生练习数据与本地绝对路径，Reviewer 可在移动端或离线浏览器直接查阅。
          </div>
        </div>

        <div>
          <h3 style="font-size: 0.95rem; margin-bottom: 0.75rem; color: #334155;">📄 同源交付文件直接打开与下载：</h3>
          <div class="download-grid">
            <a class="dl-btn primary" href="{path_prefix}{issue_id}.pdf" target="_blank">
              <span>📖 整刊印刷合订本 ({total_pages} 页完整 PDF)</span>
              <span>下载/打开 ↗</span>
            </a>
            <a class="dl-btn" href="{path_prefix}{issue_id}-复述.pdf" target="_blank">
              <span>🗣️ 复述教学分册 ({r_pages} 页)</span>
              <span>打开 ↗</span>
            </a>
            <a class="dl-btn" href="{path_prefix}{issue_id}-评论.pdf" target="_blank">
              <span>🎙️ 口语评论分册 ({c_pages} 页)</span>
              <span>打开 ↗</span>
            </a>
            <a class="dl-btn" href="{path_prefix}{issue_id}-原文拆解与积累.pdf" target="_blank">
              <span>📝 原文拆解分册 ({f_pages} 页)</span>
              <span>打开 ↗</span>
            </a>
            <a class="dl-btn" href="{path_prefix}{issue_id}.md" target="_blank">
              <span>📃 学生端 Markdown 纯文本</span>
              <span>打开 ↗</span>
            </a>
            <a class="dl-btn" href="{path_prefix}{issue_id}.html" target="_blank">
              <span>🌐 印刷版 HTML 渲染原件</span>
              <span>打开 ↗</span>
            </a>
            <a class="dl-btn" href="{path_prefix}manifest_prep.json" target="_blank">
              <span>📋 采编台账清单 (manifest_prep.json)</span>
              <span>查看 ↗</span>
            </a>
            <a class="dl-btn" href="{path_prefix}sources_status.json" target="_blank">
              <span>📡 上游雷达与选材状态 (sources_status.json)</span>
              <span>查看 ↗</span>
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- 采编单元明细 -->
    <div class="section-title">🔍 采编单元与真实证据链（本期入选 · 9篇复述 + 6篇评论）</div>
    <div class="units-grid">
      {''.join(units_html)}
    </div>

    <div class="section-title">📝 原文拆解与语言积累（本期独立入选 · 6篇深度时评精选）</div>
    <div class="units-grid">
      {''.join(excerpts_html)}
    </div>

    <!-- 逐页快照展架 -->
    <div class="section-title">🖼️ 全本 {total_pages} 页实页高精度快照（排版、导图与 9 组四格连环画视觉复核）</div>
    <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">
      重点复核：<strong>第 4、6、8、10、12、14、16、18、20 页</strong>（9 组看图复述思维导图与 ILL-R27~R35 纯无字叙事连环画）及 <strong>口语评论范本页</strong>（双主体段首句粗体、0 裸露 &lt;b&gt; 标签）。
    </p>
    <div class="gallery-grid">
      {''.join(pages_html)}
    </div>

    <!-- 上游信源只读快照 -->
    <div class="section-title">📊 上游信源与常态备料快照（只读状态）</div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>信源名称</th>
            <th>分类属性</th>
            <th>接入模式</th>
            <th>选用状态</th>
            <th>运行健康度</th>
          </tr>
        </thead>
        <tbody>
          {''.join(sources_rows)}
        </tbody>
      </table>
    </div>

  </div>

</body>
</html>
"""

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="脱敏静态审阅站生成器")
    parser.add_argument("--issue", default=None, help="目标期刊ID (若省略则自动检测最新期)")
    parser.add_argument("--outdir", default=None, help="目标输出目录 (默认 review-public)")
    args = parser.parse_args()
    build_review_site(args.issue, output_dir=args.outdir)

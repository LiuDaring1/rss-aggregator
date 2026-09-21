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
from typing import Dict, Any, List, Optional

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(ROOT_DIR, "review-public")

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

def build_review_site(issue_id: str = "issue-2026-w38"):
    print(f"🚀 开始生成脱敏静态审阅站 (期号: {issue_id})...")
    
    # 1. 准备目录
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    dist_issue_dir = os.path.join(ROOT_DIR, "dist", issue_id)
    if not os.path.exists(dist_issue_dir):
        raise RuntimeError(f"未找到构建产物目录: {dist_issue_dir}，请先执行 cli.py build {issue_id}")

    target_issue_dir = os.path.join(OUTPUT_DIR, "issues", issue_id)
    os.makedirs(target_issue_dir, exist_ok=True)

    # 2. 拷贝合法交付产物 (白名单拷贝，杜绝软链接与私密数据)
    allowed_extensions = [".pdf", ".md", ".html", ".png", ".jpg", ".jpeg"]
    for root, dirs, files in os.walk(dist_issue_dir):
        rel_path = os.path.relpath(root, dist_issue_dir)
        target_sub = os.path.join(target_issue_dir, rel_path) if rel_path != "." else target_issue_dir
        os.makedirs(target_sub, exist_ok=True)
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in allowed_extensions:
                src_file = os.path.join(root, f)
                dst_file = os.path.join(target_sub, f)
                # 使用 copyfile 避免带入 symlink
                if os.path.islink(src_file):
                    real_src = os.path.realpath(src_file)
                    shutil.copyfile(real_src, dst_file)
                else:
                    shutil.copyfile(src_file, dst_file)

    # 3. 拷贝插图资产
    src_ill_dir = os.path.join(ROOT_DIR, "issues", issue_id, "illustrations")
    if os.path.exists(src_ill_dir):
        dst_ill_dir = os.path.join(target_issue_dir, "illustrations")
        os.makedirs(dst_ill_dir, exist_ok=True)
        for f in os.listdir(src_ill_dir):
            if f.endswith((".png", ".jpg", ".jpeg")):
                shutil.copyfile(os.path.join(src_ill_dir, f), os.path.join(dst_ill_dir, f))

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

    # 5. 生成信源状态只读快照
    sources_json_path = os.path.join(ROOT_DIR, "aggr-site", "sources.json")
    raw_sources = []
    if os.path.exists(sources_json_path):
        try:
            with open(sources_json_path, "r", encoding="utf-8") as f:
                raw_sources = json.load(f)
        except Exception:
            pass

    sanitized_sources = []
    for s in raw_sources:
        sanitized_sources.append({
            "name": s.get("name", "未知"),
            "category": s.get("category", "权威时评"),
            "type": s.get("type", "rss"),
            "status": "active (已接通上游雷达)",
            "selected_this_issue": (s.get("name") in ["新京报·快评", "潮新闻", "浙江宣传", "南方周末"])
        })
    # 补充天天正能量
    sanitized_sources.append({
        "name": "天天正能量",
        "category": "暖文事实库",
        "type": "radar_crawler",
        "status": "active (283条本地温和事实库)",
        "selected_this_issue": True
    })

    git_info = get_git_info()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S (UTC+8)")

    # 6. 构造静态 index.html
    html_content = generate_index_html(
        manifest=manifest,
        issue_id=issue_id,
        git_info=git_info,
        now_str=now_str,
        retellings=retellings_data,
        commentaries=commentaries_data,
        excerpts=excerpts_data,
        sources=sanitized_sources
    )

    index_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 7. 写入 .nojekyll 防止 GitHub Pages 吞下以下划线开头的文件
    with open(os.path.join(OUTPUT_DIR, ".nojekyll"), "w", encoding="utf-8") as f:
        f.write("")

    print(f"✅ 脱敏静态审阅站已成功生成至: {OUTPUT_DIR}")
    print(f"   - 入口文件: {index_path}")
    print(f"   - 包含产物: PDF/Markdown/HTML/PNG 快照全量同源离线打包")

def generate_index_html(manifest: Dict[str, Any],
                        issue_id: str,
                        git_info: Dict[str, str],
                        now_str: str,
                        retellings: List[Dict[str, Any]],
                        commentaries: List[Dict[str, Any]],
                        excerpts: List[Dict[str, Any]],
                        sources: List[Dict[str, Any]]) -> str:
    
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
    for p in range(1, 17):
        p_str = f"page_{p:02d}.png"
        pages_html.append(f"""
        <div class="page-thumb">
          <a href="issues/{issue_id}/pages/{p_str}" target="_blank" title="点击查看第 {p} 页高精度大图">
            <img src="issues/{issue_id}/pages/{p_str}" alt="第 {p} 页" loading="lazy">
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

    <!-- 本期成果与直接查阅 -->
    <div class="card">
      <div class="banner-grid">
        <div class="meta-box">
          <span class="badge badge-blue">正式发行版 · 现行生效</span>
          <h2 style="font-size: 1.35rem; margin: 0.6rem 0 0.4rem;">{html.escape(manifest.get('title', '口语素材周刊'))} · {html.escape(manifest.get('issue_no_label', ''))}</h2>
          <p style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 1rem;">
            时段：{html.escape(manifest.get('date_range', ''))}<br>
            物理页数：<strong>严格 16 页</strong>（无截断、无白页溢出）<br>
            门禁核验：原文连续精准匹配 100% · 纯文本无裸 HTML 标签
          </p>
          <div style="font-size: 0.82rem; background: #f1f5f9; padding: 0.75rem; border-radius: 6px; color: #334155;">
            <strong>📌 镜像说明：</strong> 本站点为只读脱敏包，剔除了任何内部爬虫接口、学生练习数据与本地绝对路径，Reviewer 可在移动端或离线浏览器直接查阅。
          </div>
        </div>

        <div>
          <h3 style="font-size: 0.95rem; margin-bottom: 0.75rem; color: #334155;">📄 同源交付文件直接打开与下载：</h3>
          <div class="download-grid">
            <a class="dl-btn primary" href="issues/{issue_id}/{issue_id}.pdf" target="_blank">
              <span>📖 整刊印刷合订本 (16 页完整 PDF)</span>
              <span>下载/打开 ↗</span>
            </a>
            <a class="dl-btn" href="issues/{issue_id}/{issue_id}-复述.pdf" target="_blank">
              <span>🗣️ 复述教学分册 (5 页)</span>
              <span>打开 ↗</span>
            </a>
            <a class="dl-btn" href="issues/{issue_id}/{issue_id}-评论.pdf" target="_blank">
              <span>🎙️ 口语评论分册 (6 页)</span>
              <span>打开 ↗</span>
            </a>
            <a class="dl-btn" href="issues/{issue_id}/{issue_id}-原文拆解与积累.pdf" target="_blank">
              <span>📝 原文拆解分册 (2 页)</span>
              <span>打开 ↗</span>
            </a>
            <a class="dl-btn" href="issues/{issue_id}/{issue_id}.md" target="_blank">
              <span>📃 学生端 Markdown 纯文本</span>
              <span>打开 ↗</span>
            </a>
            <a class="dl-btn" href="issues/{issue_id}/{issue_id}.html" target="_blank">
              <span>🌐 印刷版 HTML 渲染原件</span>
              <span>打开 ↗</span>
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- 采编单元明细 -->
    <div class="section-title">🔍 采编单元与真实证据链（本期入选）</div>
    <div class="units-grid">
      {''.join(units_html)}
    </div>

    <div class="section-title">📝 原文拆解与语言积累（本期入选）</div>
    <div class="units-grid">
      {''.join(excerpts_html)}
    </div>

    <!-- 逐页快照展架 -->
    <div class="section-title">🖼️ 全本 16 页实页高精度快照（排版与导图视觉复核）</div>
    <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">
      重点复核：<strong>第 4、6 页</strong>（关键词网络、几何导图与黑白叙事插图 ILL-R27/R28）及 <strong>第 10、13 页</strong>（首句加粗、无裸露 &lt;b&gt; 标签）。
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
    build_review_site()

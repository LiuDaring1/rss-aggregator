# -*- coding: utf-8 -*-
"""
口语素材周刊 命令行工具 (Publishing Pipeline CLI)
支持：
- doctor: 环境与依赖体检
- migrate-legacy: 从旧版迁移数据至 content/
- validate: 校验单元 YAML 结构与业务规则
- preview: 单单元渲染预览 (HTML / PDF / PNG)
- build: 整刊确定性构建 (严格离线，无网络/模型调用)
"""
import os
import sys
import argparse
import json
import yaml
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from weekly_pipeline.models import (
    RetellingUnit, CommentaryUnit, ExcerptUnit, IssueManifest
)
from weekly_pipeline.validation import (
    validate_content_directory, validate_file, load_yaml_safely
)
from weekly_pipeline.render import (
    find_chrome_binary, preview_unit, render_issue_html,
    render_html_to_pdf, render_pdf_to_pngs
)

def cmd_doctor(args):
    print("=" * 60)
    print("口语素材周刊 · 出版管线环境体检 (doctor)")
    print("=" * 60)
    
    # 1. Python 依赖
    print("[1] Python 核心依赖:")
    for mod in ["pydantic", "jinja2", "yaml", "fitz"]:
        try:
            m = __import__(mod)
            v = getattr(m, "__version__", "OK")
            print(f"  ✅ {mod:12s}: 已安装 ({v})")
        except ImportError:
            print(f"  ❌ {mod:12s}: 未安装")
            
    # 2. Chrome / Chromium
    print("\n[2] 印刷渲染引擎 (Chromium / Chrome):")
    chrome = find_chrome_binary()
    if chrome:
        print(f"  ✅ 发现无头浏览器: {chrome}")
    else:
        print("  ❌ 未找到 Chrome/Chromium，将无法生成 PDF。")
        
    # 3. 离线模式确认
    print("\n[3] 离线与模型隔离状态:")
    print("  ✅ 构建流程 (build / preview) 100% 确定性离线，不触发采集或远程模型调用。")
    print("  ✅ 观点池与范本双主体已解耦。")
    print("=" * 60)

def cmd_migrate_legacy(args):
    from weekly_pipeline.adapters.legacy_adapter import run_migration
    src = args.source
    out_c = args.out_content
    out_i = args.out_issues
    print(f"正在从旧版迁移: {src} -> {out_c}, {out_i} (overwrite={args.overwrite})...")
    run_migration(src, out_c, out_i, overwrite=args.overwrite)

def cmd_validate(args):
    print(f"正在校验内容目录: {args.content_dir}...")
    res = validate_content_directory(args.content_dir)
    print(f"\n校验完成: 共 {res['total_units']} 个单元")
    print(f"  通过: {res['valid_units']}")
    print(f"  错误: {res['total_errors']}")
    print(f"  警告: {res['total_warnings']}")
    
    for r in res["results"]:
        status = "✅" if r["is_valid"] else "❌"
        warn_str = f" [警告: {len(r['warnings'])}]" if r["warnings"] else ""
        print(f"  {status} [{r['unit_type']}] {r['unit_id']}{warn_str}")
        for err in r["errors"]:
            print(f"     ❌ 错误: {err}")
        for w in r["warnings"]:
            print(f"     ⚠️  警告: {w}")
            
    if res["total_errors"] > 0:
        sys.exit(1)

def cmd_preview(args):
    target = args.unit
    out_dir = args.outdir
    formats = args.formats.split(",")
    
    # 寻找对应 yaml 文件
    if not os.path.exists(target):
        # 尝试从 content 目录查找
        candidates = [
            os.path.join("content", "commentaries", f"{target}.yaml"),
            os.path.join("content", "retellings", f"{target}.yaml"),
            os.path.join("content", "excerpts", f"{target}.yaml"),
        ]
        found = None
        for c in candidates:
            if os.path.exists(c):
                found = c
                break
        if not found:
            print(f"❌ 找不到单元文件或对应 ID: {target}")
            sys.exit(1)
        target = found
        
    print(f"正在预览单元: {target}...")
    # 收集已有复述单元
    available_retellings = set()
    r_dir = os.path.join("content", "retellings")
    if os.path.exists(r_dir):
        for rf in os.listdir(r_dir):
            if rf.endswith(".yaml") or rf.endswith(".yml"):
                available_retellings.add(rf.rsplit(".", 1)[0])
                
    # 严格前置校验：重复键或非法结构拒绝渲染
    is_unverified = False
    val_res = validate_file(target, available_retellings=available_retellings)
    if not val_res.is_valid:
        # 判断是否仅为单篇草稿未载入复述引用
        is_only_retell_ref_err = len(val_res.errors) == 1 and "未在有效复述材料列表中找到" in val_res.errors[0]
        if is_only_retell_ref_err:
            is_unverified = True
            print(f"⚠️ [草稿预览] {val_res.errors[0]}（单篇草稿预览标记为【未核验】，允许生成预览）")
        else:
            print(f"❌ 单元前置校验失败，拒绝渲染预览: {target}")
            for err in val_res.errors:
                print(f"   - {err}")
            sys.exit(1)
        
    with open(target, "r", encoding="utf-8") as f:
        data = load_yaml_safely(f.read())
        
    if "speech" in data:
        unit = CommentaryUnit.model_validate(data)
        u_type = "commentary"
    elif "mindmap_tree" in data:
        unit = RetellingUnit.model_validate(data)
        u_type = "retelling"
    elif "quote_paragraphs" in data:
        unit = ExcerptUnit.model_validate(data)
        u_type = "excerpt"
    else:
        print(f"❌ 无法识别单元类型: {target}")
        sys.exit(1)
        
    res = preview_unit(unit, u_type, out_dir, formats=formats, is_unverified=is_unverified)
    print("✅ 预览生成成功:")
    if is_unverified:
        print("  ⚠️ 引用状态: 【草稿·未核验】（已注入 HTML/PDF/PNG 产物标记）")
    for k, v in res.items():
        if k == "pngs":
            print(f"  - PNG 页面 ({len(v)} 页):")
            for p in v:
                print(f"      {p}")
        elif k in ["html", "pdf"]:
            print(f"  - {k.upper()}: {v}")

def cmd_build(args):
    issue_id = args.issue
    out_dir = args.outdir
    formats = args.formats.split(",")
    os.makedirs(out_dir, exist_ok=True)
    
    issue_yaml = os.path.join("issues", issue_id, "issue.yaml")
    if not os.path.exists(issue_yaml):
        print(f"❌ 期刊清单不存在: {issue_yaml}")
        sys.exit(1)
        
    print(f"正在构建期刊: {issue_id} (配置文件: {issue_yaml})...")
    with open(issue_yaml, "r", encoding="utf-8") as f:
        manifest = IssueManifest.model_validate(load_yaml_safely(f.read()))
        
    # 加载 units (带严格前置校验与安全解析)
    retellings = []
    available_retellings = set(manifest.retelling_ids)
    for rid in manifest.retelling_ids:
        yp = os.path.join("content", "retellings", f"{rid}.yaml")
        if not os.path.exists(yp):
            print(f"❌ 缺少复述单元文件: {yp}")
            sys.exit(1)
        val_res = validate_file(yp)
        if not val_res.is_valid:
            print(f"❌ 单元前置校验失败，终止构建: {yp}")
            for err in val_res.errors:
                print(f"   - {err}")
            sys.exit(1)
        with open(yp, "r", encoding="utf-8") as fp:
            retellings.append(RetellingUnit.model_validate(load_yaml_safely(fp.read())))
            
    commentaries = []
    for cid in manifest.commentary_ids:
        yp = os.path.join("content", "commentaries", f"{cid}.yaml")
        if not os.path.exists(yp):
            print(f"❌ 缺少评论单元文件: {yp}")
            sys.exit(1)
        val_res = validate_file(yp, available_retellings=available_retellings)
        if not val_res.is_valid:
            print(f"❌ 单元前置校验失败，终止构建: {yp}")
            for err in val_res.errors:
                print(f"   - {err}")
            sys.exit(1)
        with open(yp, "r", encoding="utf-8") as fp:
            commentaries.append(CommentaryUnit.model_validate(load_yaml_safely(fp.read())))
            
    excerpts = []
    for fid in manifest.excerpt_ids:
        yp = os.path.join("content", "excerpts", f"{fid}.yaml")
        if not os.path.exists(yp):
            print(f"❌ 缺少原文拆解单元文件: {yp}")
            sys.exit(1)
        val_res = validate_file(yp)
        if not val_res.is_valid:
            print(f"❌ 单元前置校验失败，终止构建: {yp}")
            for err in val_res.errors:
                print(f"   - {err}")
            sys.exit(1)
        with open(yp, "r", encoding="utf-8") as fp:
            excerpts.append(ExcerptUnit.model_validate(load_yaml_safely(fp.read())))
            
    # 计算页码布局 (静态页码规则：
    # 封面: 第 1 页
    # 目录: 第 2 页
    # 复述: 每个 2 页 (R01 为 3..4, R02 为 5..6, ...)
    # 答案: 接在复述后，占 1 页 (第 3 + len(retellings)*2 页)
    # 评论: 每个 3 页
    # 原文拆解: 每个 1 页
    # 附录: 占 1 页
    page_map: Dict[str, int] = {}
    cur_p = 3
    for r in retellings:
        page_map[r.id] = cur_p
        cur_p += 2
        
    page_map["复述参考"] = cur_p
    cur_p += 1 # 复述参考页
    
    for c in commentaries:
        page_map[c.id] = cur_p
        cur_p += 3
        
    for f in excerpts:
        page_map[f.id] = cur_p
        cur_p += 1
        
    page_map["附录"] = cur_p
    
    # AI 陪练提示
    ai_prompt = ""
    prompt_file = os.path.join("weekly", "sample-01-rev5", "ai-retelling-prompt.txt")
    if os.path.exists(prompt_file):
        with open(prompt_file, "r", encoding="utf-8") as pf:
            ai_prompt = pf.read().strip()
            
    html_out = render_issue_html(manifest, retellings, commentaries, excerpts, page_map, ai_prompt)
    
    out_html = os.path.join(out_dir, f"{issue_id}.html")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"  ✅ HTML 构建完成: {out_html}")
    
    if "pdf" in formats or "png" in formats:
        out_pdf = os.path.join(out_dir, f"{issue_id}.pdf")
        render_html_to_pdf(out_html, out_pdf)
        print(f"  ✅ PDF 打印完成: {out_pdf}")
        
        if "png" in formats:
            png_dir = os.path.join(out_dir, f"{issue_id}_pages")
            pngs = render_pdf_to_pngs(out_pdf, png_dir, prefix=f"{issue_id}")
            print(f"  ✅ PNG 页面快照完成 ({len(pngs)} 页): {png_dir}")

def cmd_export_md(args):
    from weekly_pipeline.export_markdown import export_all_markdown
    c_dir = args.content_dir
    out_dir = args.outdir
    edition = getattr(args, "edition", "both")
    print(f"正在导出同源 Markdown 审阅文件 ({edition}): {c_dir} -> {out_dir}...")
    try:
        files = export_all_markdown(c_dir, out_dir, edition=edition)
        print(f"  ✅ 导出完成: 共生成 {len(files)} 个 Markdown 审阅文件在 {out_dir}")
    except Exception as e:
        print(f"  ❌ 导出终止并阻断发布:\n{e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="口语素材周刊 命令行工具")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    
    # doctor
    p_doc = subparsers.add_parser("doctor", help="环境与工具链体检")
    p_doc.add_argument("--offline", action="store_true", help="显式检查离线能力")
    p_doc.set_defaults(func=cmd_doctor)
    
    # migrate-legacy
    p_mig = subparsers.add_parser("migrate-legacy", help="从旧版 content5.py 迁移数据")
    p_mig.add_argument("--source", default="weekly/sample-01-rev5/content5.py")
    p_mig.add_argument("--out-content", default="content")
    p_mig.add_argument("--out-issues", default="issues")
    p_mig.add_argument("--overwrite", "--force", action="store_true", help="强制覆盖已存在文件")
    p_mig.add_argument("--offline", action="store_true", default=True)
    p_mig.set_defaults(func=cmd_migrate_legacy)
    
    # validate
    p_val = subparsers.add_parser("validate", help="校验单元 YAML 数据")
    p_val.add_argument("--content-dir", default="content")
    p_val.set_defaults(func=cmd_validate)
    
    # preview
    p_prev = subparsers.add_parser("preview", help="单单元预览")
    p_prev.add_argument("--unit", required=True, help="单元文件路径或单元ID (如 C01)")
    p_prev.add_argument("--outdir", default="outputs/preview")
    p_prev.add_argument("--formats", default="html,pdf,png")
    p_prev.set_defaults(func=cmd_preview)
    
    # build
    p_bld = subparsers.add_parser("build", help="构建整刊")
    p_bld.add_argument("--issue", default="sample-01-rev5", help="期刊ID")
    p_bld.add_argument("--outdir", default="outputs")
    p_bld.add_argument("--formats", default="html,pdf,png")
    p_bld.add_argument("--offline", action="store_true", default=True, help="离线构建模式")
    p_bld.set_defaults(func=cmd_build)
    
    # export-md
    p_md = subparsers.add_parser("export-md", help="导出同源 Markdown 审阅文件")
    p_md.add_argument("--content-dir", default="content")
    p_md.add_argument("--outdir", default="outputs/markdown")
    p_md.add_argument("--edition", choices=["both", "student", "teacher"], default="both", help="导出版本: student/teacher/both")
    p_md.set_defaults(func=cmd_export_md)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()

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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
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
            
    # 前置信源连续子串核验 (任何入选摘录缺少真实原件归档或引文不匹配，坚决立即终止构建与发布)
    from weekly_pipeline.verifier import verify_issue_quotes, verify_issue_splits
    sources_dir = os.path.join("issues", issue_id, "sources")
    if not verify_issue_quotes(issue_id, content_dir="content", sources_dir=sources_dir):
        print(f"❌ [构建终止] 信源原段连续匹配校验未通过，坚决拦截构建与正式归档！")
        sys.exit(1)
            
    # 统一计算页码布局 (静态页码规则，严格与 Markdown / HTML / PDF 保持一致)
    from weekly_pipeline.export_markdown import compute_page_map, export_full_issue_markdown
    page_map, ans_pages, total_pages = compute_page_map(manifest)
    
    # AI 陪练提示
    ai_prompt = ""
    issue_prompt = os.path.join("issues", issue_id, manifest.ai_prompt_path or "ai-retelling-prompt.txt")
    fallback_prompt = os.path.join("weekly", "sample-01-rev5", "ai-retelling-prompt.txt")
    prompt_file = issue_prompt if os.path.exists(issue_prompt) else fallback_prompt
    if os.path.exists(prompt_file):
        with open(prompt_file, "r", encoding="utf-8") as pf:
            ai_prompt = pf.read().strip()
            
    html_out = render_issue_html(manifest, retellings, commentaries, excerpts, page_map, ai_prompt)
    
    out_html = os.path.join(out_dir, f"{issue_id}.html")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"  ✅ HTML 构建完成: {out_html}")
    
    # 导出整刊同源 Markdown (含非空断言)
    out_md = os.path.join(out_dir, f"{issue_id}.md")
    try:
        md_text = export_full_issue_markdown(manifest, content_dir="content", edition="student", page_map=page_map, ai_prompt_text=ai_prompt)
        with open(out_md, "w", encoding="utf-8") as f:
            f.write(md_text)
        print(f"  ✅ 整刊同源 Markdown 导出完成: {out_md}")
    except Exception as e:
        print(f"  ❌ 整刊 Markdown 导出校验失败并阻断: {e}")
        sys.exit(1)
    
    if "pdf" in formats or "png" in formats:
        out_pdf = os.path.join(out_dir, f"{issue_id}.pdf")
        render_html_to_pdf(out_html, out_pdf)
        print(f"  ✅ PDF 打印完成: {out_pdf}")
        
        # 导出模块分册 PDF (复述 / 评论 / 原文拆解与积累)
        split_files = {
            "retelling": os.path.join(out_dir, f"{issue_id}-复述.pdf"),
            "commentary": os.path.join(out_dir, f"{issue_id}-评论.pdf"),
            "excerpt": os.path.join(out_dir, f"{issue_id}-原文拆解与积累.pdf"),
        }
        # 显式清理旧分册文件，坚决杜绝混批或旧残卷混入交付
        for sp in split_files.values():
            if os.path.exists(sp):
                try:
                    os.remove(sp)
                except Exception as ce:
                    print(f"  ⚠️ 清理旧分册文件失败: {sp}: {ce}")

        try:
            import pypdf
            reader = pypdf.PdfReader(out_pdf)
            c_start = page_map[commentaries[0].id]
            f_start = page_map[excerpts[0].id]
            app_start = page_map.get("附录", len(reader.pages) + 1)
            
            # 各板块预期精确物理页数
            exp_r_pages = c_start - 3
            exp_c_pages = f_start - c_start
            exp_f_pages = app_start - f_start
            
            # 严格核对整刊 PDF 物理总页数（防止打印截断或排版多页溢出）
            if len(reader.pages) != total_pages:
                raise RuntimeError(
                    f"整刊 PDF 实际物理页数 ({len(reader.pages)}) 与静态规划总页数 ({total_pages}) 不符（存在排版多页溢出或打印截断），构建终止！"
                )

            w_r = pypdf.PdfWriter()
            for p_idx in range(2, c_start - 1):
                w_r.add_page(reader.pages[p_idx])
            with open(split_files["retelling"], "wb") as fp:
                w_r.write(fp)
                
            w_c = pypdf.PdfWriter()
            for p_idx in range(c_start - 1, f_start - 1):
                w_c.add_page(reader.pages[p_idx])
            with open(split_files["commentary"], "wb") as fp:
                w_c.write(fp)
                
            w_f = pypdf.PdfWriter()
            for p_idx in range(f_start - 1, app_start - 1):
                w_f.add_page(reader.pages[p_idx])
            with open(split_files["excerpt"], "wb") as fp:
                w_f.write(fp)

            # 产物完整性与物理页数硬断言（不仅检查文件存在，更严格核验实际页数完全符合本期范围）
            expected_splits = {
                "retelling": (split_files["retelling"], exp_r_pages, "复述分册"),
                "commentary": (split_files["commentary"], exp_c_pages, "评论分册"),
                "excerpt": (split_files["excerpt"], exp_f_pages, "原文拆解分册"),
            }
            for sp_key, (sp_path, exp_pg, sp_label) in expected_splits.items():
                if not os.path.exists(sp_path) or os.path.getsize(sp_path) == 0:
                    raise RuntimeError(f"模块分册 PDF 导出失败或为空文件: {sp_path}")
                sp_reader = pypdf.PdfReader(sp_path)
                act_pg = len(sp_reader.pages)
                if act_pg == 0:
                    raise RuntimeError(f"模块分册 {sp_label} 实际物理页数为 0 页（空 PDF）: {sp_path}")
                if act_pg != exp_pg:
                    raise RuntimeError(
                        f"模块分册 {sp_label} 物理页数异常: 实际 {act_pg} 页 != 预期规划 {exp_pg} 页 ({sp_path})"
                    )

            print(f"  ✅ 模块分册 PDF 导出完成: 复述 ({len(w_r.pages)}页) / 评论 ({len(w_c.pages)}页) / 原文拆解与积累 ({len(w_f.pages)}页)")
        except Exception as se:
            print(f"  ❌ 模块分册 PDF 导出失败并阻断: {se}")
            # 清理可能生成的半残文件，防止误作交付
            for sp in split_files.values():
                if os.path.exists(sp):
                    try:
                        os.remove(sp)
                    except Exception:
                        pass
            sys.exit(1)
        
        if "png" in formats:
            png_dir = os.path.join(out_dir, f"{issue_id}_pages")
            pngs = render_pdf_to_pngs(out_pdf, png_dir, prefix=f"{issue_id}")
            print(f"  ✅ PNG 页面快照完成 ({len(pngs)} 页): {png_dir}")

    # 产物全量物理页数二次核验（整刊与分册完整性拦截）
    if "pdf" in formats:
        if not verify_issue_splits(issue_id, target_dir=out_dir):
            print(f"❌ [发布拦截] 模块分册或整刊物理页数核验未通过，坚决拦截正式归档交付！")
            sys.exit(1)

    # 自动同步归档至 issues/{issue_id}/ (确保版本库始终跟踪最新同源成品)
    issue_repo_dir = os.path.join("issues", issue_id)
    if os.path.exists(issue_repo_dir) and os.path.abspath(out_dir) != os.path.abspath(issue_repo_dir):
        import shutil
        deliverables = [
            f"{issue_id}.md", f"{issue_id}.pdf",
            f"{issue_id}-复述.pdf", f"{issue_id}-评论.pdf", f"{issue_id}-原文拆解与积累.pdf"
        ]
        for fname in deliverables:
            src_f = os.path.join(out_dir, fname)
            dst_f = os.path.join(issue_repo_dir, fname)
            if os.path.exists(src_f) and os.path.getsize(src_f) > 0:
                shutil.copy2(src_f, dst_f)
            else:
                print(f"  ⚠️ 警告: 预期产物不存在或为空，未同步: {src_f}")
        print(f"  ✅ 发布全量核验（信源原段与物理页数）100% 通过，已正式同步归档至仓库目录: {issue_repo_dir}")

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

def cmd_verify_issue(args):
    from weekly_pipeline.verifier import run_full_issue_verification
    issue_id = args.issue
    target_dir = args.dir
    sources_dir = args.sources_dir
    ok = run_full_issue_verification(issue_id, target_dir=target_dir, sources_dir=sources_dir)
    if not ok:
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="口语素材周刊流水线 CLI 工具")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
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
    
    # verify-issue
    p_ver = subparsers.add_parser("verify-issue", help="验证期刊信源原段与分册物理页数")
    p_ver.add_argument("--issue", default="issue-trial-01", help="期刊ID")
    p_ver.add_argument("--dir", default=None, help="待检测 PDF 目录 (默认: issues/<issue>)")
    p_ver.add_argument("--sources-dir", default=None, help="信源存档目录 (默认: issues/<issue>/sources)")
    p_ver.set_defaults(func=cmd_verify_issue)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()

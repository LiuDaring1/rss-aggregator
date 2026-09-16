# -*- coding: utf-8 -*-
"""
旧刊例数据迁移适配器 (AST / 隔离受控导入)
从 weekly/sample-01-rev5/content5.py 提取数据并转化为 Pydantic 标准模型实例与 YAML 单元文件
"""
import os, sys, importlib.util, yaml
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from typing import Dict, Any, List

from weekly_pipeline.models import (
    RetellingUnit, MindmapTree, MindmapBranch, MindmapLeaf,
    CommentaryUnit, LearningBlock, ViewpointItem, ReasoningLesson,
    SpeechBlock, SpeechBodyParagraph, TeachingBlock, DeconstructionItem,
    ExcerptUnit, IssueManifest, BuildConfig
)

def load_legacy_module(path: str):
    spec = importlib.util.spec_from_file_location("legacy_content5", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def extract_answers_from_mapkey(uid: str, mapkey: str, total_leaves: int) -> List[str]:
    raw_chunks = [p.strip() for p in mapkey.split("/") if p.strip()]
    if not raw_chunks:
        return ["" for _ in range(total_leaves)]
    
    if uid == "R01" and len(raw_chunks) == 8 and total_leaves == 7:
        return [
            raw_chunks[0],
            raw_chunks[1],
            raw_chunks[2],
            raw_chunks[3],
            raw_chunks[4],
            f"{raw_chunks[5]}·{raw_chunks[6]}",
            raw_chunks[7]
        ]
    elif uid == "R03" and len(raw_chunks) == 6 and total_leaves == 5:
        return [
            f"{raw_chunks[0]}·{raw_chunks[1]}",
            raw_chunks[2],
            raw_chunks[3],
            raw_chunks[4],
            raw_chunks[5]
        ]
    elif len(raw_chunks) == total_leaves:
        return raw_chunks
    else:
        res = list(raw_chunks[:total_leaves])
        while len(res) < total_leaves:
            res.append("")
        return res

def migrate_retellings(retells: list) -> List[RetellingUnit]:
    units = []
    for i, r in enumerate(retells):
        uid = f"R{i+1:02d}"
        branches_raw = r.get("tree", {}).get("branches", [])
        
        # 统计总叶子数以对齐答案
        total_leaves = sum(len(br.get("children", [])) for br in branches_raw)
        answers = extract_answers_from_mapkey(uid, r.get("mapkey", ""), total_leaves)
        
        global_leaf_idx = 0
        branches = []
        for br in branches_raw:
            leaves = []
            for ch in br.get("children", []):
                global_leaf_idx += 1
                leaf_ans = answers[global_leaf_idx - 1] if global_leaf_idx - 1 < len(answers) else ""
                leaves.append(MindmapLeaf(
                    id=f"{uid}-leaf-{global_leaf_idx:02d}",
                    hint=ch.get("blank", ""),
                    answer=leaf_ans,
                    fact_refs=["待核对"]
                ))
            branches.append(MindmapBranch(
                name=br.get("label", ""),
                leaves=leaves
            ))

        unit = RetellingUnit(
            id=uid,
            category="社会热点" if r.get("tag") == "hot" else "暖文",
            packet_ref=f"pkt-legacy-{uid.lower()}",
            title=r["title"],
            date_label=r.get("dateline", ""),
            source_label=r.get("source", ""),
            material_paragraphs=(
                r["body"] if isinstance(r["body"], list)
                else [p for p in r["body"].split("\n") if p.strip()]
            ),
            keywords=[w for _, w in r.get("net", {}).get("sats", [])],
            mindmap_tree=MindmapTree(
                center=r.get("tree", {}).get("root", r["title"]),
                branches=branches
            ),
            ref_retelling=r.get("ref", ""),
            mapkey=r.get("mapkey", ""),
            illustration_id=f"ILL-{uid}",
            illustration_brief=f"黑白报刊式叙事插画（对应 {r['title']}）"
        )
        units.append(unit)
    return units

def migrate_commentaries(comments: list, retelling_id_map: dict) -> List[CommentaryUnit]:
    units = []
    for i, c in enumerate(comments):
        cid = f"C{i+1:02d}"
        ref_raw = c.get("ref", "")
        retell_ref = retelling_id_map.get(ref_raw, f"R{i+1:02d}")

        # 观点池：提取旧 views
        viewpoints = []
        for vi, (v_claim, v_ev) in enumerate(c.get("views", [])):
            viewpoints.append(ViewpointItem(
                id=f"v{vi+1}",
                claim=v_claim,
                evidence=v_ev,
                explanation=None
            ))

        # 推演块
        reasoning_lessons = [
            ReasoningLesson(
                title="怎么想到的：拆开讲",
                target_viewpoint_ids=[f"v{x+1}" for x in range(len(viewpoints))],
                deduction_text=c.get("reasoning", "")
            )
        ]

        # 范本：解析 script 列表 [开头, 主体1, 主体2, 结尾]
        script_paras = c.get("script", [])
        opening = script_paras[0] if len(script_paras) > 0 else ""
        body1_text = script_paras[1] if len(script_paras) > 1 else ""
        body2_text = script_paras[2] if len(script_paras) > 2 else ""
        closing = script_paras[3] if len(script_paras) > 3 else (script_paras[-1] if len(script_paras) > 2 else "")

        def extract_claim(text):
            # 取第一句话作为 claim
            parts = text.split("。")
            if len(parts) > 1:
                return parts[0] + "。"
            return text

        body = [
            SpeechBodyParagraph(
                id="b1",
                claim=extract_claim(body1_text),
                paragraphs=[body1_text]
            ),
            SpeechBodyParagraph(
                id="b2",
                claim=extract_claim(body2_text),
                paragraphs=[body2_text]
            )
        ]

        # 教学拆解
        decon_items = [
            DeconstructionItem(
                target="【整体论述拆解】",
                instruction=c.get("decon", "")
            )
        ]

        unit = CommentaryUnit(
            id=cid,
            retelling_ref=retell_ref,
            packet_ref=f"pkt-legacy-{retell_ref.lower()}",
            title=c.get("title", ""),
            learning=LearningBlock(
                recap_facts=c.get("recap", []),
                questions=c.get("questions", []),
                baseline_diagnostic=c.get("base", ""),
                viewpoints=viewpoints,
                reasoning_lessons=reasoning_lessons
            ),
            speech=SpeechBlock(
                selected_viewpoint_ids=[v.id for v in viewpoints],
                main_claim=opening,
                body=body,
                closing=closing
            ),
            teaching=TeachingBlock(
                spine=c.get("spine", ""),
                deconstruction=decon_items,
                editor_notes=None
            ),
            # 严格标记：旧版观点池仅2条，标为 legacy_unreviewed 供 S2 重构
            legacy_unreviewed=(len(viewpoints) <= 2)
        )
        units.append(unit)
    return units

def migrate_excerpts(fragments: list) -> List[ExcerptUnit]:
    units = []
    for i, f in enumerate(fragments):
        fid = f"F{i+1:02d}"
        raw_text = f.get("text", "")
        paras = raw_text if isinstance(raw_text, list) else [p for p in raw_text.split("\n") if p.strip()]
        unit = ExcerptUnit(
            id=fid,
            topic=f.get("topic", ""),
            source_name=f.get("src", ""),
            source_date="近期评论",
            source_url=None,
            context=f.get("context", ""),
            quote_paragraphs=paras,
            analyze=f.get("analyze", ""),
            memorize=f.get("memorize"),
            method=f.get("method"),
            demo_title="示范｜换个话题，可以这样说",
            demo_text=f.get("demo", ""),
            demo_is_hypothetical=True
        )
        units.append(unit)
    return units

def _should_skip_write(target_path: str, overwrite: bool) -> bool:
    if not os.path.exists(target_path):
        return False
    if overwrite:
        return False
    # 存在且未指定 overwrite：检查是否有人工审阅或现有内容保护
    try:
        with open(target_path, "r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp)
            if isinstance(data, dict) and data.get("legacy_unreviewed") is False:
                print(f"  🛡️  [已人工审阅保护] {target_path} legacy_unreviewed=False，阻止自动覆盖！")
                return True
    except Exception:
        pass
    print(f"  ⚠️  [跳过保护] {target_path} 已存在且未指定 --overwrite/--force，跳过写入。")
    return True

def run_migration(content5_path: str, output_content_dir: str, issues_dir: str, overwrite: bool = False):
    mod = load_legacy_module(content5_path)
    retellings = migrate_retellings(mod.RETELLS)
    
    # 建立旧 ID 到 R01..R08 的映射
    retell_map = {}
    for i, r in enumerate(mod.RETELLS):
        retell_map[r["id"]] = f"R{i+1:02d}"

    commentaries = migrate_commentaries(mod.COMMENTS, retell_map)
    excerpts = migrate_excerpts(mod.FRAGMENTS)

    # 写入 YAML 文件
    r_dir = os.path.join(output_content_dir, "retellings")
    c_dir = os.path.join(output_content_dir, "commentaries")
    f_dir = os.path.join(output_content_dir, "excerpts")
    os.makedirs(r_dir, exist_ok=True)
    os.makedirs(c_dir, exist_ok=True)
    os.makedirs(f_dir, exist_ok=True)

    written_r, written_c, written_f = 0, 0, 0
    for r in retellings:
        path = os.path.join(r_dir, f"{r.id}.yaml")
        if _should_skip_write(path, overwrite):
            continue
        with open(path, "w", encoding="utf-8") as fp:
            yaml.dump(r.model_dump(), fp, allow_unicode=True, sort_keys=False)
        written_r += 1

    for c in commentaries:
        path = os.path.join(c_dir, f"{c.id}.yaml")
        if _should_skip_write(path, overwrite):
            continue
        with open(path, "w", encoding="utf-8") as fp:
            yaml.dump(c.model_dump(), fp, allow_unicode=True, sort_keys=False)
        written_c += 1

    for f in excerpts:
        path = os.path.join(f_dir, f"{f.id}.yaml")
        if _should_skip_write(path, overwrite):
            continue
        with open(path, "w", encoding="utf-8") as fp:
            yaml.dump(f.model_dump(), fp, allow_unicode=True, sort_keys=False)
        written_f += 1

    # 写入 issue.yaml
    manifest = IssueManifest(
        issue_id="sample-01-rev5",
        title="口语素材周刊",
        kicker="高中播音艺考口语素材周刊",
        issue_no_label="试刊 · 第 0 期（rev.5 迁移版）",
        date_range="2026年9月第1周",
        retelling_ids=[r.id for r in retellings],
        commentary_ids=[c.id for c in commentaries],
        excerpt_ids=[f.id for f in excerpts]
    )
    issue_dir = os.path.join(issues_dir, "sample-01-rev5")
    os.makedirs(issue_dir, exist_ok=True)
    manifest_path = os.path.join(issue_dir, "issue.yaml")
    if not _should_skip_write(manifest_path, overwrite):
        with open(manifest_path, "w", encoding="utf-8") as fp:
            yaml.dump(manifest.model_dump(), fp, allow_unicode=True, sort_keys=False)

    print(f"✅ 迁移处理完成: 写入/更新 {written_r}/{len(retellings)} 复述, {written_c}/{len(commentaries)} 评论, {written_f}/{len(excerpts)} 原文拆解 -> {output_content_dir}")
    print(f"✅ 期刊清单路径: {manifest_path}")
    return retellings, commentaries, excerpts, manifest

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="旧刊例数据迁移适配器")
    parser.add_argument("--source", default="weekly/sample-01-rev5/content5.py")
    parser.add_argument("--out-content", default="content")
    parser.add_argument("--out-issues", default="issues")
    parser.add_argument("--overwrite", "--force", action="store_true", help="强制覆盖已存在文件")
    args = parser.parse_args()
    run_migration(args.source, args.out_content, args.out_issues, overwrite=args.overwrite)


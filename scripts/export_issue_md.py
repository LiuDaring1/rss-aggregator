# -*- coding: utf-8 -*-
"""
生成整刊完整 Markdown 学生文本 (issue-2026-w37.md)
"""
import os
import yaml

def generate_issue_md():
    manifest_path = "issues/issue-2026-w37/issue.yaml"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    lines = []
    lines.append("# 高中播音艺考口语素材周刊 · 2026 年 9 月第 2 期（issue-2026-w37）\n")
    lines.append("本期栏目：**复述**（每则材料页＋提示页，参考答案集中在「复述参考」）· **评论**（同一批材料，每题三页：审题破题／观点推演／范本拆解）· **原文拆解与积累**（独立精选近期深度评论完整语段）。本文件为完整学生正文；打印版见 `issue-2026-w37.pdf` 与三模块分册 PDF。\n")

    lines.append("## 目录\n")
    lines.append("**复述**：R09（3–4 页）｜R10（5–6 页）｜R11（7–8 页）｜R12（9–10 页）｜R13（11–12 页）｜R14（13–14 页）｜R15（15–16 页）｜R16（17–18 页）｜R17（19–20 页）｜复述参考（21–22 页）\n")
    lines.append("**评论**：C07（23–25 页）｜C08（26–28 页）｜C09（29–31 页）｜C10（32–34 页）｜C11（35–37 页）｜C12（38–40 页）\n")
    lines.append("**原文拆解与积累**：F07（41 页）｜F08（42 页）｜F09（43 页）｜F10（44 页）｜F11（45 页）｜F12（46 页）\n")
    lines.append("**附录 · 使用说明**：47 页\n")

    # Prompt
    prompt_path = "issues/issue-2026-w37/ai-retelling-prompt.txt"
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as pf:
            lines.append("## AI 陪练完整指令\n\n```\n" + pf.read().strip() + "\n```\n")

    lines.append("\n---\n\n# 一、复述\n")

    retell_units = []
    for rid in manifest["retelling_ids"]:
        with open(f"content/retellings/{rid}.yaml", "r", encoding="utf-8") as f:
            u = yaml.safe_load(f)
            retell_units.append(u)
            lines.append(f"## {u['id']} · {u['title']}（{u.get('category', '热点')}）\n")
            lines.append(f"**材料页**　{u['date_label']}\n")
            for p in u["material_paragraphs"]:
                lines.append(f"{p}\n")
            lines.append(f"*{u['source_label']}*\n")
            lines.append(f"**提示页**")
            kw_str = " · ".join(u.get("keywords", []))
            lines.append(f"- 关键词：{kw_str}")
            tree = u.get("mindmap_tree", {})
            lines.append("- 思维导图（虚线待补写）：")
            lines.append("```")
            lines.append(f"中心：{tree.get('center', '')}")
            for branch in tree.get("branches", []):
                lines.append(f"├─ {branch.get('name', '')}")
                for leaf in branch.get("leaves", []):
                    lines.append(f"│   └─ [提示] {leaf.get('hint', '')}")
            lines.append("```")
            lines.append(f"- 插画需求：{u.get('illustration_brief', '黑白报刊式插画')}\n")

    lines.append("\n---\n\n# 复述参考\n")
    for u in retell_units:
        lines.append(f"### {u['id']} · {u['title']}")
        lines.append(f"**参考复述**：{u.get('ref_retelling', '')}\n")
        lines.append(f"**导图参照**：{u.get('mapkey', '')}\n")

    lines.append("\n---\n\n# 二、评论\n")
    for cid in manifest["commentary_ids"]:
        with open(f"content/commentaries/{cid}.yaml", "r", encoding="utf-8") as f:
            c = yaml.safe_load(f)
            lines.append(f"## {c['id']} · {c['title']}")
            lines.append(f"*对应复述·{c.get('retelling_ref', '')} 材料页*\n")
            # Page 1
            lines.append("### 第 1 页：审题破题与问题链")
            p1 = c.get("page1", {})
            lines.append(f"**材料核心事实**：{p1.get('recall_material', '')}\n")
            lines.append(f"**一句话立意**：{p1.get('takeaway_quote', '')}\n")
            lines.append("**破题思考**：")
            for bp in p1.get("breakdown_points", []):
                lines.append(f"- **{bp.get('title', '')}**：{bp.get('desc', '')}")
            lines.append("\n**追问链条**：")
            for q in p1.get("question_chain", []):
                lines.append(f"1. {q}")
            lines.append("")
            
            # Page 2
            lines.append("### 第 2 页：观点池与逻辑推演")
            p2 = c.get("page2", {})
            lines.append("**多维观点池**：")
            for vp in p2.get("viewpoints_pool", []):
                lines.append(f"- **{vp.get('title', '')}**：{vp.get('desc', '')}")
            lines.append("\n**结构推演（从因果推导到解决路径）**：")
            for step in p2.get("deduction_steps", []):
                lines.append(f"- **{step.get('step', '')}**：{step.get('content', '')}")
            lines.append("")
            
            # Page 3
            lines.append("### 第 3 页：口语表达范本与实战拆解")
            p3 = c.get("page3", {})
            sp = p3.get("speech", {})
            lines.append(f"**【口语范本】（时长约 {sp.get('timing_seconds', 150)} 秒）**\n")
            lines.append(f"{sp.get('opening', '')}\n")
            for b in sp.get("body_paragraphs", []):
                lines.append(f"{b}\n")
            lines.append(f"{sp.get('closing', '')}\n")
            lines.append("**【技法拆解】**：")
            for d in p3.get("dissection", []):
                lines.append(f"- **{d.get('technique', '')}**：{d.get('desc', '')}")
            lines.append("\n")

    lines.append("\n---\n\n# 三、原文拆解与积累\n")
    for fid in manifest["excerpt_ids"]:
        with open(f"content/excerpts/{fid}.yaml", "r", encoding="utf-8") as f:
            ex = yaml.safe_load(f)
            lines.append(f"## {ex['id']} · {ex.get('topic', '')}")
            lines.append(f"*出处：{ex.get('source', '')}*\n")
            lines.append(f"**【原文精选】**\n\n> {ex.get('quote', '')}\n")
            lines.append(f"**【技法拆解】**：{ex.get('technique', '')}\n")
            lines.append(f"**【口语迁移】**：{ex.get('takeaway', '')}\n")

    lines.append("\n---\n\n# 附录 · 使用说明\n")
    lines.append("本周刊专为高中播音主持与口语传播艺考生打造，紧扣高考口语表达三大能力：快速提炼与结构化复述、观点构建与思辨评述、语言积淀与文采锤炼。\n")

    out_md = "output/issue-2026-w37/issue-2026-w37.md"
    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ 生成整刊 Markdown: {out_md} ({len(lines)} 行)")

if __name__ == "__main__":
    generate_issue_md()

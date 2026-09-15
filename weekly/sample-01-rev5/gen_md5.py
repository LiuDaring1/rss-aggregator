# -*- coding: utf-8 -*-
"""gen_md5.py — 从 content5.py 生成学生正文 sample.md（与 PDF 同源同序）"""
import os
from content5 import RETELLS, COMMENTS, FRAGMENTS
from pages_data import PAGES

HERE = os.path.dirname(os.path.abspath(__file__))

def tree_lines(item):
    out = [f"中心：{item['tree']['root']}"]
    for br in item["tree"]["branches"]:
        out.append(f"├─ {br['label']}")
        for ch in br["children"]:
            out.append(f"│   └─ [虚线补写框] {ch['blank']}")
    return "\n".join(out)

ILL_CAPS = {
 "热1": "小吃街上张开双臂的接护身影，头顶小小的下坠剪影，一旁手机飘出爱心（示意）",
 "热2": "夜色中家长抱女儿赶往医院急诊，手持空白病历卡（示意）",
 "热3": "清晨校门口，家长带孩子与行李箱走向校本部（示意）",
 "热4": "货架前拿起椰子水细看配料表，旁边放大镜（示意）",
 "热5": "回转寿司吧台，店员收拾餐盘、家长牵孩子欠身（示意）",
 "暖1": "葫芦架下老人探身与栅栏外游客打招呼，架上恰好七个葫芦（示意）",
 "暖2": "海浪中三人抱紧救生圈，远处救援艇驶来（示意）",
 "暖3": "深夜村庄，青年在门前抬手敲门，远处天际映着火光（示意）",
}

out = []
out.append("# 口语素材周刊 · 2026 年 9 月第 1 期（试刊）\n")
out.append("本期栏目：**复述**（每则材料页＋提示页，参考答案集中在「复述参考」）· **评论**（同一批材料，每题三页：问题／观点与推演／范本与拆解）· **原文拆解与积累**（独立精选近期评论完整段落）。本文件为完整学生正文；打印版见 sample.pdf 与三模块分册 PDF。\n")
out.append("\n## 目录\n")
out.append("**复述**：" + "｜".join(f"{it['id']}（{PAGES[it['id']]}–{PAGES[it['id']]+1} 页）" for it in RETELLS) + f"｜复述参考（{PAGES.get('复述参考',19)}–20 页）\n")
out.append("**评论**：" + "｜".join(f"评{i+1}（{PAGES['评%d'%(i+1)]}–{PAGES['评%d'%(i+1)]+2} 页）" for i in range(6)) + "\n")
out.append("**原文拆解与积累**：" + "｜".join(f"拆{i+1}（{PAGES['拆%d'%(i+1)]} 页）" for i in range(6)) + "\n")
out.append("\n## AI 陪练完整指令\n\n```\n" + open(os.path.join(HERE, "ai-retelling-prompt.txt"), encoding="utf-8").read().strip() + "\n```\n")

out.append("\n---\n\n# 一、复述\n")
for it in RETELLS:
    out.append(f"\n## {it['id']} · {it['title']}（{it['tag']}）\n")
    out.append(f"**材料页**　{it['dateline']}\n")
    for para in it["body"]:
        out.append(para + "\n")
    out.append(f"*{it['source']}*\n")
    out.append("\n**提示页**")
    out.append("- 关键词：" + "；".join(f"{c}：{w}" for c, w in it["net"]["sats"]) + f"。中心：{it['net']['center']}。")
    out.append("- 思维导图（虚线框＝待补写）：\n\n```\n" + tree_lines(it) + "\n```")
    out.append("- 插画：" + ILL_CAPS[it['id']] + "（黑白报刊式插画，待回传整合）\n")

out.append("\n# 复述参考\n")
for it in RETELLS:
    out.append(f"\n**{it['id']} · {it['title']}**（材料见第 {PAGES[it['id']]} 页）\n\n{it['ref']}\n")
    out.append(f"*导图参照：{it['mapkey']}*\n")

out.append("\n---\n\n# 二、评论\n")
for c in COMMENTS:
    out.append(f"\n## 评：{c['title']}（对应复述·{c['ref']} 材料页）\n")
    out.append("**回想材料**：" + "；".join(c["recap"]))
    out.append("\n**思考问题**")
    for i, q in enumerate(c["questions"], 1):
        out.append(f"{i}. {q}")
    out.append(f"\n**观点参考**\n\n{c['base']}")
    for v, how in c["views"]:
        out.append(f"- {v}（依据与来源：{how}）")
    out.append(f"\n**怎么想到的：拆开讲**\n\n{c['reasoning']}\n")
    out.append("**口语范本**\n")
    for para in c["script"]:
        out.append(para + "\n")
    out.append(f"**全文主线**　{c['spine']}\n")
    out.append(f"**拆解**　{c['decon']}\n")

out.append("\n---\n\n# 三、原文拆解与积累\n")
out.append("片段均为近期评论原文照录，删节以「……」标示。\n")
for f in FRAGMENTS:
    out.append(f"\n## {f['id']} · {f['topic']}（{f['src']}）\n")
    out.append(f"**前因后果**　{f['context']}\n")
    out.append("**原文片段**\n")
    for para in f["text"].split("\n"):
        out.append(f"> {para}\n>\n" if para else "")
    out.append(f"**重点拆解**　{f['analyze']}\n")
    out.append(f"**值得记住的表达**　{f['memorize']}\n")
    out.append(f"**可以借鉴的讲法**　{f['method']}\n")
    out.append(f"**换个话题，可以这样说**　{f['demo']}\n")

out.append("\n---\n\n# 附录 · 使用说明\n")
out.append("1. AI 陪练用于有设备的时段；纸面资料可独立使用。完整指令见目录页下方，也可向老师索取可复制文本。")
out.append("2. 提示页的「关键词」「思维导图」「插画」可以任选、结合使用；不必按顺序练三遍。")
out.append("3. 思维导图的虚线框补的是完整意思：可以写短语、分点，或一两句话；要点对照「复述参考」的导图参照。")
out.append("4. 本期插画以需求包方式制作回传，到版前提示页第三栏标注“待整合”。\n")

open(os.path.join(HERE, "sample.md"), "w", encoding="utf-8").write("\n".join(out))
print("sample.md written,", len("\n".join(out)), "chars")

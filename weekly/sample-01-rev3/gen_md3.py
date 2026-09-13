# -*- coding: utf-8 -*-
"""gen_md3.py — 从 content3.py 生成学生正文 sample.md"""
import os
from content3 import RETELLS, COMMENTS, FRAGMENTS
HERE = os.path.dirname(os.path.abspath(__file__))

PROMPT = open(os.path.join(HERE, "ai-retelling-prompt.txt"), encoding="utf-8").read().split("【实测状态】")[0].rstrip()

PAGES = {"热1":3,"热2":5,"热3":7,"热4":9,"热5":11,"暖1":13,"暖2":15,"暖3":17,
         "评1":21,"评2":23,"评3":25,"评4":27,"评5":29,"评6":31,
         "拆1":33,"拆2":34,"拆3":35,"拆4":36,"拆5":37,"拆6":38}

def tree_lines(item):
    out = []
    r = item["tree"]
    out.append(f"中心：{r['root']}")
    for br in r["branches"]:
        out.append(f"├─ {br['label']}")
        for ch in br["children"]:
            if isinstance(ch, dict):
                out.append(f"│   └─ [整块补写] {ch['blank']}")
            else:
                out.append(f"│   └─ {ch}")
    return "\n".join(out)

ILL_CAPS = {
 "热1": "影院灯光下，孩子仰望银幕上的动画剪影（示意）",
 "热2": "夜色中家长抱女儿赶往医院急诊（示意）",
 "热3": "清晨校门口，家长带孩子与搬离的行李（示意）",
 "热4": "货架前拿起草椰子水细看配料表（示意）",
 "热5": "回转寿司吧台，店员收拾餐盘、家长带孩子起身（示意）",
 "暖1": "葫芦架下老人探身与栅栏外游客打招呼（示意）",
 "暖2": "海浪中救生圈与远处驶来的救援艇（示意）",
 "暖3": "深夜村庄，青年在门前抬手敲门，远处天际映着火光（示意）",
}

out = []
out.append("# 口语素材周刊 · 2026 年 9 月第 1 期（试刊）\n")
out.append("本期栏目：**复述**（每则材料页＋提示页两页，全部参考答案集中在「复述参考」）· **评论**（同一批材料，先思考页后参考页）· **原文拆解与积累**（独立精选近期评论完整段落）。本文件为完整学生正文；打印版见 sample.pdf 与三模块分册 PDF。\n")
out.append("\n## 目录\n")
out.append("**复述**：" + "｜".join(f"{it['id']} {it['title'].split('：')[0]}（{PAGES[it['id']]}–{PAGES[it['id']]+1} 页）" for it in RETELLS))
out.append(f"｜复述参考（19–20 页）\n")
out.append("**评论**：" + "｜".join(f"评{i+1}（{PAGES['评%d'%(i+1)]} 页）" for i in range(6)) + "\n")
out.append("**原文拆解与积累**：" + "｜".join(f"拆{i+1}（{PAGES['拆%d'%(i+1)]} 页）" for i in range(6)) + "\n")
out.append("\n## AI 陪练完整指令\n\n```\n" + PROMPT + "\n```\n")

out.append("\n---\n\n# 一、复述\n")
for it in RETELLS:
    out.append(f"\n## {it['id']} · {it['title']}（{it['tag']}）\n")
    out.append(f"**材料页**　{it['dateline']}\n")
    for para in it["body"]:
        out.append(para + "\n")
    out.append(f"*{it['source']}*\n")
    out.append("\n**提示页**")
    out.append("- 关键词网络：" + "；".join(f"{c}：{w}" for c, w in it["net"]["sats"]) + f"。中心：{it['net']['center']}。")
    out.append("- 思维导图（虚线框＝整块补写区）：\n\n```\n" + tree_lines(it) + "\n```")
    out.append("- 插画：" + ILL_CAPS[it['id']] + "（黑白报刊式插画，待回传整合）\n")
    out.append(f"**复述参考**（见「复述参考」，第 19–20 页）\n\n{it['ref']}\n")
    out.append(f"*导图参照：{it['mapkey']}*\n")

out.append("\n---\n\n# 二、评论\n")
out.append("与「复述」同一批材料。每单元先思考，参考内容随后；观点与问题相互支持，不必一一对应。\n")
for c in COMMENTS:
    out.append(f"\n## {c['id']} · {c['title']}（对应复述·{c['ref']} 材料页）\n")
    out.append("**回想材料**：" + "；".join(c["recap"]))
    out.append("\n**先想几个问题**")
    for i, q in enumerate(c["questions"], 1):
        out.append(f"{i}. {q}")
    out.append(f"\n**观点参考**\n\n{c['base']}")
    for v, how in c["views"]:
        out.append(f"- {v}（依据与来源：{how}）")
    out.append(f"\n**推演讲解**\n\n{c['reasoning']}\n")
    out.append("**口语范本**\n")
    for para in c["script"]:
        out.append(para + "\n")
    out.append(f"**范本拆解**　{c['review']}\n")

out.append("\n---\n\n# 三、原文拆解与积累\n")
out.append("片段均为近期评论原文照录，删节以「……」标示。\n")
for f in FRAGMENTS:
    out.append(f"\n## {f['id']} · {f['topic']}（{f['src']}）\n")
    out.append(f"**前因后果**　{f['context']}\n")
    out.append(f"**原文片段**\n")
    for para in f["text"].split("\n"):
        out.append(f"> {para}\n>\n" if para else "")
    out.append(f"**重点拆解**　{f['analyze']}\n")
    out.append(f"**积累与使用**　可背：{f['memorize']}　用位：{f['use_where']}\n")
    out.append(f"使用示例：{f['use_demo']}\n")

out.append("\n---\n\n# 附录 · 使用与边界说明\n")
out.append("1. AI 陪练用于有设备的时段；纸面资料可独立使用。指令全文见目录页下方，也可向老师索取可复制文本。")
out.append("2. 「提示页」三样东西各有分工：关键词网络提示信息，思维导图组织信息，插画唤起场景——不必逐字背图上的话。")
out.append("3. 参考复述示范取舍与顺序，意思准确的说法都算对；导图虚线框补的是完整意思，不要求逐字一致。")
out.append("4. 本期插画以需求包方式另行制作回传，到版前提示页第三栏标注“待整合”。\n")

open(os.path.join(HERE, "sample.md"), "w", encoding="utf-8").write("\n".join(out))
print("sample.md written,", len("\n".join(out)), "chars")

# -*- coding: utf-8 -*-
"""gen_md.py — 从 content.py 生成学生正文 sample.md（与 PDF 同源）"""
import os
from content import RETELLS, COMMENTS, FRAGMENTS, DOUBAO_PROMPT

HERE = os.path.dirname(os.path.abspath(__file__))
STORY_CAPS = {
 "热1": ["此前：教师被不实投诉缠住，反复自证清白", "9月4日发布会：教育部表态“让老师身后有盾”", "三项举措：规范程序、澄清正名、“零容忍”"],
 "热2": ["5岁女孩全身过敏，连夜就医，夜班医生拒诊", "事后，医生在电子病历里写下“刁蛮”等标注", "家长上网维权，回应称“小事”并指其“抹黑”"],
 "热3": ["本学期启用新校区，家长反映气味刺鼻", "学生头晕流鼻血，56人班级41人请假", "官方通报：六年级全体迁回校本部"],
 "热4": ["饮料标注“100%椰子水”，被当作承诺", "媒体调查：部分产品配料表与实际不符", "广东排查：23家存在问题，5家立案查处"],
 "热5": ["北京一家寿司郎门店，家长带孩子在餐位就餐", "孩子在座位上小便，家长用塑料杯接住，视频流传", "门店全面消杀、餐具废弃；家长道歉愿赔偿"],
 "暖1": ["绍兴小院，一藤七个大葫芦，台风后恰好七颗", "全国游客赶来打卡，寻找童年记忆", "不收费不围卖，立牌提醒“别把爷爷累着”"],
 "暖2": ["傍晚的海里，一百多米外传来呼救", "他送出救生圈，拖出二十多米后体力耗尽", "留圈等待，独自回岸；摩托艇三次救回三人"],
 "暖3": ["凌晨返家，发现两公里外火光冲天", "喇叭、杂物无效后，挨家挨户砸门示警", "9名群众安全撤离，火灾无人员伤亡"],
}

out = []
out.append("# 口语素材周刊 · 2026 年 9 月第 1 期（试刊）\n")
out.append("本期栏目：**复述**（每则含材料页、提示页、参考页，PDF 中实排三页）· **评论**（同一批材料练观点）· **原文拆解与积累**（真实评论片段精读）。本文件为完整学生正文；打印版见 sample.pdf 与三模块分册 PDF。\n")

out.append("\n## 目录\n")
out.append("**复述**：热1 教育部表态让老师身后有“盾”（PDF 3–5 页）｜热2 “刁蛮”病历（6–8）｜热3 新校区 41 人请假（9–11）｜热4 “100%椰子水”掺水（12–14）｜热5 寿司郎门店男童餐位小便（15–17）｜暖1 葫芦爷爷（18–20）｜暖2 王植兴海中救人（21–23）｜暖3 魏治立深夜敲门（24–26）")
out.append("**评论**：评1–评6（PDF 28–33 页，与复述热1/热2/热4/暖1/暖2/暖3 同题）")
out.append("**原文拆解与积累**：拆1–拆7（PDF 35–41 页）｜附录：AI 陪练完整指令（42 页）\n")

out.append("\n---\n\n# 一、复述\n")
for it in RETELLS:
    out.append(f"\n## {it['id']} · {it['title']}（{it['tag']}）\n")
    out.append(f"**材料页**　{it['dateline']}\n")
    for para in it["body"]:
        out.append(para + "\n")
    out.append(f"*{it['source']}*\n")
    out.append("【提示页】三张图各有用法：先用关键词网络唤起人和事，再用填空导图理清顺序，最后用事实示意图对一遍场景。")
    out.append("- 关键词网络：" + "；".join(f"{c}：{w}" for c, w in it["net"]["sats"]) + f"。中心：{it['net']['center']}。")
    out.append("- 思维导图（填空）：" + " ｜ ".join(f"{i+1}{lab}：{content}" for i, (lab, content) in enumerate(it["map"])))
    caps = STORY_CAPS[it["id"]]
    out.append("- 事实示意图（示意，非新闻图片）：" + " → ".join(caps))
    out.append(f"\n【参考页 · 参考复述】\n\n{it['ref']}\n")
    out.append(f"*填空参照：{it['mapkey']}*\n")

out.append("\n---\n\n# 二、评论\n")
out.append("与「复述」同一批材料：复述面向不了解事件的听众，评论面向读过题干的考官——先亮观点，再讲道理。\n")
for c in COMMENTS:
    out.append(f"\n## {c['id']} · {c['title']}（对应复述·{c['ref']}）\n")
    out.append("**思考问题**")
    for i, q in enumerate(c["questions"], 1):
        out.append(f"{i}. {q}")
    out.append(f"\n**观点参考**\n\n{c['base']}")
    for tag, v, how in c["views"]:
        out.append(f"- {tag}　{v}（怎么想到：{how}）")
    out.append("\n**口语范本**\n")
    for para in c["script"]:
        out.append(para + "\n")
    out.append(f"**范本拆解**　{c['review']}\n")

out.append("\n---\n\n# 三、原文拆解与积累\n")
out.append("片段均为真实评论原文照录，删节处以「……」标示。\n")
for f in FRAGMENTS:
    out.append(f"\n## {f['id']} · {f['group']}（{f['ref']}）\n")
    out.append(f"**前因后果**　{f['context']}（{f['src']}）\n")
    out.append(f"**原文片段**\n\n> {f['text']}\n")
    out.append(f"**局部拆解**　{f['analyze']}\n")
    out.append(f"**积累与使用**　可背：{f['memorize']}　用位：{f['use_where']}\n")
    out.append(f"使用示例：{f['use_demo']}\n")

out.append("\n---\n\n# 附录 · AI 陪练完整指令\n")
out.append("```\n" + DOUBAO_PROMPT + "\n```\n")

open(os.path.join(HERE, "sample.md"), "w", encoding="utf-8").write("\n".join(out))
print("sample.md written,", len("\n".join(out)), "chars")

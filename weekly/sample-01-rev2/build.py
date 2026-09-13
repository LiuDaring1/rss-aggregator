# -*- coding: utf-8 -*-
"""build.py — 组装口语素材周刊 rev.2（三模块）
用法: python3 build.py   → 生成 sample.html
"""
import json, os, sys
from content import RETELLS, COMMENTS, FRAGMENTS, DOUBAO_PROMPT

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------- SVG 图示生成 ----------------

FONT = "PingFang SC, Hiragino Sans GB, sans-serif"

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def text_el(x, y, s, size=13, weight="normal", anchor="middle", fill="#000"):
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">{esc(s)}</text>'

def box(x, y, w, h, stroke_w=1.2, fill="#fff", dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="#000" stroke-width="{stroke_w}"{d}/>'

def line(x1, y1, x2, y2, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#000" stroke-width="1"/>{d and ""}'

def gen_net(item):
    """关键词网络：中心事件 + 卫星（类别+短词）"""
    W, H = 720, 235
    cx, cy = 360, 117
    cw = max(150, 15 * len(item["net"]["center"])) if len(item["net"]["center"]) < 14 else 210
    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">',
             f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>']
    # 卫星位置
    pos = [(120, 38), (600, 38), (52, 117), (668, 117), (120, 196), (600, 196)]
    for (cat, word), (x, y) in zip(item["net"]["sats"], pos):
        parts.append(line(cx, cy, x, y, dash="3,3"))
    for (cat, word), (x, y) in zip(item["net"]["sats"], pos):
        w = max(92, int(len(word) * 14.5))
        bx, by = x - w / 2, y - 16
        parts.append(box(bx, by, w, 34, stroke_w=1.1))
        parts.append(text_el(x, y - 4, cat, size=10, fill="#444"))
        parts.append(text_el(x, y + 12, word, size=13.5, weight="600"))
    ccw = max(170, int(len(item["net"]["center"]) * 16.5))
    parts.append(box(cx - ccw / 2, cy - 19, ccw, 38, stroke_w=1.8))
    parts.append(text_el(cx, cy + 6, item["net"]["center"], size=15.5, weight="700"))
    parts.append("</svg>")
    return "".join(parts)

def wrap_lines(s, width):
    """按宽度粗略折行（全角字符）"""
    lines, cur, n = [], "", 0
    for ch in s:
        cur += ch; n += 1
        if n >= width:
            lines.append(cur); cur = ""; n = 0
    if cur: lines.append(cur)
    return lines

def gen_map(item):
    """可填空思维导图：横向流程框"""
    steps = item["map"]
    n = len(steps)
    W = 720
    H = 88 + 34 * n if n <= 3 else 62 + 26 * n
    # 纵向列表式（步骤多时）或横向（步骤少时）
    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">',
             f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>']
    if n <= 4:
        bw, gap = (W - 40 - (n - 1) * 26) / n, 26
        for i, (label, content) in enumerate(steps):
            x = 20 + i * (bw + gap)
            parts.append(box(x, 26, bw, H - 52, stroke_w=1.2))
            parts.append(text_el(x + bw / 2, 46, f"{'①②③④⑤⑥'[i]} {label}", size=12.5, weight="700"))
            y = 66
            for ln in wrap_lines(content, max(8, int(bw / 15.5))):
                parts.append(text_el(x + 8, y, ln, size=11.5, anchor="start"))
                y += 17
            if i < n - 1:
                ax = x + bw + 4
                parts.append(f'<path d="M {ax} {H/2} L {ax+gap-8} {H/2}" stroke="#000" stroke-width="1.4" marker-end="url(#arr)"/>')
    else:
        bh = (H - 30 - (n - 1) * 12) / n
        for i, (label, content) in enumerate(steps):
            y = 18 + i * (bh + 12)
            parts.append(box(96, y, W - 150, bh, stroke_w=1.2))
            parts.append(text_el(78, y + bh / 2 + 4, f"{'①②③④⑤⑥'[i]} {label}", size=12.5, weight="700", anchor="end"))
            parts.append(text_el(108, y + bh / 2 + 4, content, size=12.5, anchor="start"))
            if i < n - 1:
                parts.append(f'<path d="M {W/2} {y+bh} L {W/2} {y+bh+12}" stroke="#000" stroke-width="1.4" marker-end="url(#arr)"/>')
    parts.append('<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#000"/></marker></defs>')
    parts.append("</svg>")
    return "".join(parts)

STORY_GLYPHS = {
    "desk":    '<rect x="30" y="46" width="60" height="10" fill="none" stroke="#000" stroke-width="2"/><rect x="36" y="56" width="6" height="22" fill="#000"/><rect x="78" y="56" width="6" height="22" fill="#000"/>',
    "podium":  '<rect x="42" y="38" width="38" height="8" fill="none" stroke="#000" stroke-width="2"/><rect x="56" y="46" width="10" height="30" fill="#000"/><circle cx="61" cy="26" r="9" fill="none" stroke="#000" stroke-width="2"/>',
    "shield":  '<path d="M61 16 L82 24 L82 44 Q82 60 61 68 Q40 60 40 44 L40 24 Z" fill="none" stroke="#000" stroke-width="2.4"/>',
    "mooncross": '<path d="M36 20 a16 16 0 1 0 14 24 a13 13 0 1 1 -14 -24" fill="none" stroke="#000" stroke-width="2"/><rect x="72" y="22" width="26" height="26" fill="none" stroke="#000" stroke-width="2"/><line x1="85" y1="26" x2="85" y2="44" stroke="#000" stroke-width="2"/><line x1="76" y1="35" x2="94" y2="35" stroke="#000" stroke-width="2"/>',
    "doc":     '<rect x="46" y="14" width="30" height="42" fill="none" stroke="#000" stroke-width="2"/><line x1="52" y1="26" x2="70" y2="26" stroke="#000" stroke-width="1.6"/><line x1="52" y1="34" x2="70" y2="34" stroke="#000" stroke-width="1.6"/><line x1="52" y1="42" x2="64" y2="42" stroke="#000" stroke-width="1.6"/>',
    "phone":   '<rect x="48" y="14" width="26" height="44" rx="4" fill="none" stroke="#000" stroke-width="2"/><circle cx="61" cy="50" r="2.4" fill="#000"/>',
    "school":  '<path d="M28 40 L61 18 L94 40 Z" fill="none" stroke="#000" stroke-width="2"/><rect x="36" y="40" width="50" height="30" fill="none" stroke="#000" stroke-width="2"/><rect x="54" y="52" width="14" height="18" fill="none" stroke="#000" stroke-width="1.8"/>',
    "note41":  '<rect x="34" y="18" width="30" height="38" fill="none" stroke="#000" stroke-width="2"/><rect x="44" y="26" width="30" height="38" fill="none" stroke="0" /><rect x="46" y="28" width="28" height="36" fill="none" stroke="#000" stroke-width="1.6"/><text x="60" y="90" font-family="FONTX" font-size="0"> </text>',
    "arrowschool": '<rect x="12" y="24" width="42" height="32" fill="none" stroke="#000" stroke-width="2"/><path d="M62 40 L96 40" stroke="#000" stroke-width="2.4"/><path d="M90 34 L98 40 L90 46" fill="none" stroke="#000" stroke-width="2.4"/><rect x="102" y="20" width="34" height="40" fill="none" stroke="#000" stroke-width="2"/>',
    "bottle":  '<path d="M52 22 h18 v10 q10 8 10 20 v14 q0 8 -8 8 h-22 q-8 0 -8 -8 v-14 q0 -12 10 -20 Z" fill="none" stroke="#000" stroke-width="2"/><rect x="54" y="14" width="14" height="8" fill="none" stroke="#000" stroke-width="2"/>',
    "magnify": '<circle cx="52" cy="34" r="17" fill="none" stroke="#000" stroke-width="2.4"/><line x1="64" y1="46" x2="82" y2="64" stroke="#000" stroke-width="3.4"/>',
    "stamp":   '<rect x="34" y="52" width="54" height="12" fill="none" stroke="#000" stroke-width="2"/><path d="M48 52 v-14 a13 13 0 0 1 26 0 v14" fill="none" stroke="#000" stroke-width="2"/>',
    "shop":    '<path d="M24 28 L98 28 L92 44 L30 44 Z" fill="none" stroke="#000" stroke-width="2"/><rect x="32" y="44" width="58" height="34" fill="none" stroke="#000" stroke-width="2"/><rect x="38" y="54" width="20" height="24" fill="none" stroke="#000" stroke-width="1.6"/>',
    "cup":     '<path d="M44 22 h34 l-6 40 h-22 Z" fill="none" stroke="#000" stroke-width="2"/>',
    "spray":   '<rect x="46" y="32" width="24" height="34" rx="4" fill="none" stroke="#000" stroke-width="2"/><rect x="52" y="24" width="12" height="8" fill="none" stroke="#000" stroke-width="2"/><path d="M70 26 l10 -6 M72 34 l12 0 M70 40 l10 6" stroke="#000" stroke-width="1.8"/>',
    "gourd":   '<path d="M42 26 q-10 12 0 22 q-12 14 8 20 h22 q20 -6 8 -20 q10 -10 0 -22 Z" fill="none" stroke="#000" stroke-width="2"/>',
    "camera":  '<rect x="34" y="26" width="54" height="34" rx="5" fill="none" stroke="#000" stroke-width="2"/><circle cx="61" cy="43" r="11" fill="none" stroke="#000" stroke-width="2"/><rect x="48" y="20" width="14" height="7" fill="none" stroke="#000" stroke-width="1.8"/>',
    "sign":    '<line x1="61" y1="20" x2="61" y2="66" stroke="#000" stroke-width="2.4"/><rect x="24" y="20" width="74" height="18" fill="none" stroke="#000" stroke-width="2"/>',
    "wave":    '<path d="M14 44 q12 -12 24 0 t24 0 t24 0 t24 0" fill="none" stroke="#000" stroke-width="2.2"/><path d="M14 56 q12 -12 24 0 t24 0 t24 0 t24 0" fill="none" stroke="#000" stroke-width="1.6"/>',
    "ring":    '<circle cx="61" cy="40" r="22" fill="none" stroke="#000" stroke-width="2.6"/><line x1="83" y1="40" x2="83" y2="40" stroke="#000"/>',
    "boat":    '<path d="M30 46 h62 l-10 14 h-42 Z" fill="none" stroke="#000" stroke-width="2"/><line x1="61" y1="18" x2="61" y2="46" stroke="#000" stroke-width="2"/><path d="M61 20 q18 8 0 22" fill="none" stroke="#000" stroke-width="1.8"/>',
    "door":    '<rect x="42" y="14" width="38" height="52" fill="none" stroke="#000" stroke-width="2.2"/><circle cx="72" cy="42" r="3" fill="#000"/><path d="M30 30 q-6 10 0 20" fill="none" stroke="#000" stroke-width="2.2"/>',
    "fire":    '<path d="M61 14 q16 14 8 26 q14 -2 12 16 q-2 18 -20 18 q-18 0 -20 -18 q-2 -16 12 -20 q-6 -12 8 -22" fill="none" stroke="#000" stroke-width="2.2"/>',
    "moto":    '<circle cx="34" cy="52" r="11" fill="none" stroke="#000" stroke-width="2.2"/><circle cx="88" cy="52" r="11" fill="none" stroke="#000" stroke-width="2.2"/><path d="M34 52 l18 -14 h20 l16 14" fill="none" stroke="#000" stroke-width="2.2"/><line x1="52" y1="38" x2="52" y2="30" stroke="#000" stroke-width="2"/>',
    "people":  '<circle cx="42" cy="24" r="7" fill="none" stroke="#000" stroke-width="2"/><path d="M32 60 v-14 q0 -10 10 -10 q10 0 10 10 v14" fill="none" stroke="#000" stroke-width="2"/><circle cx="80" cy="24" r="7" fill="none" stroke="#000" stroke-width="2"/><path d="M70 60 v-14 q0 -10 10 -10 q10 0 10 10 v14" fill="none" stroke="#000" stroke-width="2"/>',
}

def gen_story(item):
    """事实示意图：3 帧连环示意（非新闻图片）"""
    W, H = 720, 208
    fw, fh, gap = 208, 130, 30
    x0 = (W - 3 * fw - 2 * gap) / 2
    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">',
             f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>']
    for i, (glyph, cap) in enumerate(item["story"]):
        x = x0 + i * (fw + gap)
        parts.append(box(x, 10, fw, fh, stroke_w=1.4))
        parts.append(f'<g transform="translate({x + fw/2 - 61}, 28)">{STORY_GLYPHS[glyph]}</g>')
        cy = 10 + fh + 4
        for j, ln in enumerate(wrap_lines(cap, 15)[:2]):
            parts.append(text_el(x + fw / 2, cy + 16 + j * 15, ln, size=11.5))
        if i < 2:
            parts.append(f'<path d="M {x+fw+6} {10+fh/2} L {x+fw+gap-6} {10+fh/2}" stroke="#000" stroke-width="1.6" marker-end="url(#arr2)"/>')
    parts.append('<defs><marker id="arr2" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#000"/></marker></defs>')
    parts.append("</svg>")
    return "".join(parts)

# 复述项的故事板数据（帧: [图形, 说明] —— 说明只用已核实事实）
STORIES = {
 "热1": [("people", "此前：教师被不实投诉缠住，反复自证清白"),
          ("podium", "9月4日发布会：教育部表态“让老师身后有盾”"),
          ("shield", "三项举措：规范程序、澄清正名、“零容忍”")],
 "热2": [("mooncross", "5岁女孩全身过敏，连夜就医，夜班医生拒诊"),
          ("doc", "事后，医生在电子病历里写下“刁蛮”等标注"),
          ("phone", "家长上网维权，回应称“小事”并指其“抹黑”")],
 "热3": [("school", "本学期启用新校区，家长反映气味刺鼻"),
          ("note41", "学生头晕流鼻血，56人班级41人请假"),
          ("arrowschool", "官方通报：六年级全体迁回校本部")],
 "热4": [("bottle", "饮料标注“100%椰子水”，被当作承诺"),
          ("magnify", "媒体调查：部分产品配料表与实际不符"),
          ("stamp", "广东排查：23家存在问题，5家立案查处")],
 "热5": [("shop", "北京一家寿司郎门店，家长带孩子在餐位就餐"),
          ("cup", "孩子在座位上小便，家长用塑料杯接住，视频流传"),
          ("spray", "门店全面消杀、餐具废弃；家长道歉愿赔偿")],
 "暖1": [("gourd", "绍兴小院，一藤七个大葫芦，台风后恰好七颗"),
          ("camera", "全国游客赶来打卡，寻找童年记忆"),
          ("sign", "不收费不围卖，立牌提醒“别把爷爷累着”")],
 "暖2": [("wave", "傍晚的海里，一百多米外传来呼救"),
          ("ring", "他送出救生圈，拖出二十多米后体力耗尽"),
          ("boat", "留圈等待，独自回岸；摩托艇三次救回三人")],
 "暖3": [("moto", "凌晨返家，发现两公里外火光冲天"),
          ("door", "喇叭、杂物无效后，挨家挨户砸门示警"),
          ("people", "9名群众安全撤离，火灾无人员伤亡")],
}

# ---------------- HTML 组装 ----------------

def p(*xs):
    return "".join(xs)

def build(pages=None):
    pages = pages or {}
    H = []
    H.append("""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<title>口语素材周刊 · 2026年9月第1期（试刊）</title><link rel="stylesheet" href="style.css"></head><body>""")

    # 封面
    H.append("""
<div class="cover">
  <div class="kicker">播音主持艺考 · 即兴口语表达</div>
  <h1>口语素材周刊</h1>
  <div class="issue">2026 年 9 月第 1 期（试刊）</div>
  <div class="cover-note">
    本期三个栏目：<b>复述</b>——把事实看得清、说得清，每则配材料页、提示页、参考页；<br>
    <b>评论</b>——就同一批材料练习观点表达，先亮判断，再讲道理；<br>
    <b>原文拆解与积累</b>——把真实评论里的好片段印出来，学会拆、学着用。
  </div>
</div>""")

    # 目录（页码占位，两遍填充）
    toc = ['<div class="tocpage"><h2 class="toc-h">目录</h2><div class="toc-cols">']
    toc.append('<div class="toc-col"><div class="toc-sec">复述</div>')
    for it in RETELLS:
        pg = pages.get(it["id"], "—")
        rng = f"{pg}" if pg == "—" else f"{pg}–{pg+2}"
        tagcls = "tag-hot" if it["tag"] == "热点" else "tag-warm"
        toc.append(f'<div class="toc-item"><span class="tag {tagcls}">{it["tag"]}</span><span class="toc-t">{it["title"]}</span><span class="toc-p">{rng}</span></div>')
    toc.append('</div><div class="toc-col"><div class="toc-sec">评论</div>')
    for c in COMMENTS:
        pg = pages.get(c["id"], "—")
        toc.append(f'<div class="toc-item"><span class="toc-t">{c["title"]}</span><span class="toc-p">{pg}</span></div>')
    toc.append('</div><div class="toc-col"><div class="toc-sec">原文拆解与积累</div>')
    for f in FRAGMENTS:
        pg = pages.get(f["id"], "—")
        toc.append(f'<div class="toc-item"><span class="toc-t">[{f["group"]}] {f["ref"]}片段</span><span class="toc-p">{pg}</span></div>')
    toc.append('</div></div>')
    ap = pages.get("附录", "—")
    toc.append(f'<div class="toc-append">附录 · AI 陪练完整指令 <span class="toc-p">{ap}</span></div></div>')
    H.append(p(*toc))

    # 复述：每则三页
    for it in RETELLS:
        story = STORIES[it["id"]]
        item = dict(it); item["story"] = story
        H.append(f"""
<section class="rp rmat">
  <div class="rhead"><span class="rno">{it['id']}</span><span class="tag {'tag-hot' if it['tag']=='热点' else 'tag-warm'}">{it['tag']}</span><h3>{it['title']}</h3></div>
  <div class="dateline">{it['dateline']}</div>
  {''.join(f'<p class="matbody">{x}</p>' for x in it['body'])}
  <div class="src">{it['source']}</div>
  <div class="aifoot">AI 陪练提示：把本页拍给豆包等 AI，让它当你的复述听众，指出你复述里的事实错误和遗漏（完整指令见本期最后一页）。</div>
</section>
<section class="rp rhint">
  <div class="rhead"><span class="rno">{it['id']}</span><h3>提示页 · 先想后说</h3></div>
  <div class="hint-note">三张图各有用法：先用<b>关键词网络</b>唤起人和事 → 再用<b>填空导图</b>理清顺序 → 最后用<b>事实示意图</b>对一遍场景。</div>
  <div class="hint-blk"><div class="hint-cap">① 关键词网络</div>{gen_net(item)}</div>
  <div class="hint-blk"><div class="hint-cap">② 思维导图（填空）</div>{gen_map(item)}</div>
  <div class="hint-blk"><div class="hint-cap">③ 事实示意图（示意，非新闻图片）</div>{gen_story(item)}</div>
</section>
<section class="rp rref">
  <div class="rhead"><span class="rno">{it['id']}</span><h3>参考页 · 参考复述</h3></div>
  <p class="refbody">{it['ref']}</p>
  <div class="mapkey">填空参照：{it['mapkey']}</div>
</section>""")

    # 评论模块
    H.append('<section class="modhead"><h2>评论</h2><div class="modnote">与「复述」同一批材料：复述面向不了解事件的听众，评论面向读过题干的考官——先亮观点，再讲道理。每单元页首标注对应复述页。</div></section>')
    for c in COMMENTS:
        rp = pages.get(c["ref"], "—")
        rpdisp = rp if rp == "—" else f"第 {rp} 页"
        views = "".join(
            f'<li><b>{v[0]}</b>　{v[1]}<div class="how">怎么想到：{v[2]}</div></li>' for v in c["views"])
        qs = "".join(f"<li>{q}</li>" for q in c["questions"])
        script = "".join(f'<p>{x}</p>' for x in c["script"])
        H.append(f"""
<section class="cu">
  <div class="cuhead"><span class="rno">{c['id']}</span><h3>{c['title']}</h3><span class="backref">对应复述 · {c['ref']}（{rpdisp}）</span></div>
  <div class="cu-blk"><div class="lbl">思考问题</div><ol class="qs">{qs}</ol></div>
  <div class="cu-blk"><div class="lbl">观点参考</div><div class="baseline">{c['base']}</div><ol class="views">{views}</ol></div>
  <div class="cu-blk"><div class="lbl">口语范本</div><div class="script cu-script">{script}</div></div>
  <div class="cu-blk"><div class="lbl">范本拆解</div><p class="review">{c['review']}</p></div>
</section>""")

    # 原文拆解与积累
    H.append('<section class="modhead"><h2>原文拆解与积累</h2><div class="modnote">这是原文精读：把真实评论里写得好（或值得学）的片段印在纸上，弄清它为什么好、怎么拿来用。片段均为原文照录，删节处以「……」标示。</div></section>')
    order_hint = "本期片段按用途排列：开头立意（拆1–2）· 主体说理（拆3–4）· 观点金句（拆5）· 描写衔接（拆6）· 结尾收束（拆7）"
    H.append(f'<div class="frag-toc">{order_hint}</div>')
    for f in FRAGMENTS:
        H.append(f"""
<section class="fu">
  <div class="cuhead"><span class="rno">{f['id']}</span><h3>{f['group']} · {f['ref']}</h3></div>
  <div class="cu-blk"><div class="lbl">前因后果</div><p class="ctx">{f['context']}<span class="src">（{f['src']}）</span></p></div>
  <div class="quote fragtext"><p class="ni">{f['text']}</p></div>
  <div class="cu-blk"><div class="lbl">局部拆解</div><p class="ctx">{f['analyze']}</p></div>
  <div class="cu-blk"><div class="lbl">积累与使用</div><p class="ctx"><b>可背：</b>{f['memorize']}　<b>用位：</b>{f['use_where']}</p><p class="ctx"><b>使用示例：</b>{f['use_demo']}</p></div>
</section>""")

    # 附录
    H.append('<section class="appendix"><h2>附录 · AI 陪练完整指令</h2><pre class="prompt">' + esc(DOUBAO_PROMPT) + '</pre></section>')
    H.append("</body></html>")
    return p(*H)

if __name__ == "__main__":
    pages = None
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        pages = json.load(open(sys.argv[1]))
    html = build(pages)
    open(os.path.join(HERE, "sample.html"), "w", encoding="utf-8").write(html)
    print("sample.html written, bytes:", len(html))

# -*- coding: utf-8 -*-
"""build4.py — 组装 rev.4（v0.5：两页一题+三页评论+统一虚线导图+无制作说明框）"""
import json, os, sys
from content4 import RETELLS, COMMENTS, FRAGMENTS

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "PingFang SC, Hiragino Sans GB, sans-serif"
PROMPT = ""
_p = os.path.join(HERE, "ai-retelling-prompt.txt")
if os.path.exists(_p):
    PROMPT = open(_p, encoding="utf-8").read().strip()

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def text_el(x, y, s, size=13, weight="normal", anchor="middle", fill="#000"):
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">{esc(s)}</text>'

def wrap_lines(s, width):
    lines, cur, n = [], "", 0
    for ch in s:
        cur += ch; n += 1
        if n >= width:
            lines.append(cur); cur = ""; n = 0
    if cur: lines.append(cur)
    return lines or [""]

def gen_net(item):
    """关键词网络：固定画布 720×235，所有框体收敛在安全区内"""
    W, H = 720, 235
    cx, cy = 360, 117
    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">',
             f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>']
    pos = [(128, 38), (592, 38), (70, 117), (650, 117), (128, 196), (592, 196)]
    for (cat, word), (x, y) in zip(item["net"]["sats"], pos):
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x}" y2="{y}" stroke="#000" stroke-width="1" stroke-dasharray="3,3"/>')
    for (cat, word), (x, y) in zip(item["net"]["sats"], pos):
        w = min(180, max(88, int(len(word) * 13.5)))
        bx = min(max(6, x - w / 2), W - 6 - w)   # 收进画布
        parts.append(f'<rect x="{bx:.0f}" y="{y-16}" width="{w}" height="34" fill="#fff" stroke="#000" stroke-width="1.1"/>')
        parts.append(text_el(bx + w / 2, y - 4, cat, size=10, fill="#444"))
        parts.append(text_el(bx + w / 2, y + 12, word, size=12.8, weight="600"))
    ccw = min(240, max(150, int(len(item["net"]["center"]) * 15.5)))
    ccx = min(max(6, cx - ccw / 2), W - 6 - ccw)
    parts.append(f'<rect x="{ccx:.0f}" y="{cy-19}" width="{ccw}" height="38" fill="#fff" stroke="#000" stroke-width="1.8"/>')
    parts.append(text_el(ccx + ccw / 2, cy + 6, item["net"]["center"], size=15, weight="700"))
    parts.append("</svg>")
    return "".join(parts)

def gen_tree(item):
    """统一虚线补写导图：根/主枝为普通文字，全部叶节点为虚线大空框（含短提示）；连线逐子连接"""
    root = item["tree"]["root"]
    branches = item["tree"]["branches"]
    rows = []  # (branch_idx, hint, tall)
    for bi, br in enumerate(branches):
        for ch in br["children"]:
            tall = bool(ch.get("tall"))
            rows.append((bi, ch["blank"], tall))
    H = 14 + sum((56 if t else 42) + 7 for _, _, t in rows) + 6
    W = 720
    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">',
             f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>']
    child_x, child_w = 350, 362
    y = 14
    span = {}
    for bi, hint, tall in rows:
        h = 56 if tall else 42
        span.setdefault(bi, [y, y + h])
        span[bi][1] = y + h
        parts.append(f'<rect x="{child_x}" y="{y}" width="{child_w}" height="{h}" fill="#fff" stroke="#000" stroke-width="1.2" stroke-dasharray="5,3"/>')
        parts.append(text_el(child_x + 9, y + 16, hint, size=11, fill="#555", anchor="start"))
        y += h + 7
    # 主枝（普通文字，位于其子节点组的中线左侧）
    branch_x = 210
    b_mid = {}
    for bi, br in enumerate(branches):
        y0, y1 = span[bi]
        my = (y0 + y1) / 2
        b_mid[bi] = my
        parts.append(text_el(branch_x + 46, my + 5, br["label"], size=13, weight="700"))
        # 主枝 → 每个子节点：从文字右缘出发，竖干到子节点中线，再水平接入虚线框左边
        parts.append(f'<path d="M {branch_x+100} {my} H {child_x-8} V {(y0+y1)/2:.0f} H {child_x-2}" stroke="#000" stroke-width="1" fill="none"/>')
    # 根（普通文字）→ 各主枝：竖干连接
    rx = 20
    ry = H / 2
    parts.append(text_el(rx, ry + 5, root, size=14, weight="700", anchor="start"))
    spine_x = branch_x - 14
    ys = sorted(v for v in b_mid.values())
    parts.append(f'<path d="M {rx+8*len(root)+8} {ry} H {spine_x}" stroke="#000" stroke-width="1.2" fill="none"/>')
    parts.append(f'<path d="M {spine_x} {ys[0]:.0f} V {ys[-1]:.0f}" stroke="#000" stroke-width="1.2" fill="none"/>')
    for bi, my in b_mid.items():
        parts.append(f'<path d="M {spine_x} {my:.0f} H {branch_x-2}" stroke="#000" stroke-width="1.2" fill="none"/>')
    parts.append(text_el(W - 6, H - 3, "虚线框＝待补写（要点见「复述参考」导图参照）", size=9.5, fill="#555", anchor="end"))
    parts.append("</svg>")
    return "".join(parts)

def ill_placeholder(item):
    no = "R%02d-ILL01" % (RETELLS.index(item) + 1)
    return f"""<div class="illhold">
  <div class="ill-no">插画位 {no} · 插画待回传</div>
  <div class="ill-note">黑白报刊式叙事插画（需求见 illustration-briefs.md）</div>
</div>"""

def build(pages=None):
    pages = pages or {}
    H = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>口语素材周刊 · 2026年9月第1期（试刊）</title><link rel="stylesheet" href="style4.css"></head><body>']

    H.append("""
<div class="cover">
  <div class="kicker">播音主持艺考 · 即兴口语表达</div>
  <h1>口语素材周刊</h1>
  <div class="issue">2026 年 9 月第 1 期（试刊）</div>
</div>""")

    toc = ['<div class="tocpage"><h2 class="toc-h">目录</h2><div class="toc-cols">']
    toc.append('<div class="toc-col"><div class="toc-sec">复述</div>')
    for it in RETELLS:
        pg = pages.get(it["id"], "—")
        rng = f"{pg}–{pg+1}" if pg != "—" else "—"
        tagcls = "tag-hot" if it["tag"] == "热点" else "tag-warm"
        toc.append(f'<div class="toc-item"><span class="tag {tagcls}">{it["tag"]}</span><span class="toc-t">{it["title"]}</span><span class="toc-p">{rng}</span></div>')
    refp = pages.get("复述参考", "—")
    toc.append(f'<div class="toc-item toc-sub"><span class="toc-t">复述参考</span><span class="toc-p">{refp}</span></div>')
    toc.append('</div><div class="toc-col"><div class="toc-sec">评论</div>')
    for c in COMMENTS:
        pg = pages.get(c["id"], "—")
        toc.append(f'<div class="toc-item"><span class="toc-t">{c["title"]}</span><span class="toc-p">{pg}</span></div>')
    toc.append('</div><div class="toc-col"><div class="toc-sec">原文拆解与积累</div>')
    for f in FRAGMENTS:
        pg = pages.get(f["id"], "—")
        toc.append(f'<div class="toc-item"><span class="toc-t">{f["topic"]}</span><span class="toc-p">{pg}</span></div>')
    toc.append('</div></div>')
    ap = pages.get("附录", "—")
    toc.append(f"""
<div class="promptbox-aftertoc">
  <div class="pb-cap">AI 陪练完整指令（复制给豆包等语音 AI；材料页脚为简短版）</div>
  <pre class="pb-text">{esc(PROMPT)}</pre>
</div>
<div class="toc-append">附录 · 使用说明 <span class="toc-p">{ap}</span></div></div>""")
    H.append("".join(toc))

    # 复述：每则两页
    for it in RETELLS:
        H.append(f"""
<section class="rp rmat">
  <div class="rhead"><span class="rno">{it['id']}</span><span class="tag {'tag-hot' if it['tag']=='热点' else 'tag-warm'}">{it['tag']}</span><h3>{it['title']}</h3></div>
  <div class="dateline">{it['dateline']}</div>
  {''.join(f'<p class="matbody">{x}</p>' for x in it['body'])}
  <div class="src">{it['source']}</div>
  <div class="aifoot">AI 陪练提示：把本页拍给语音 AI 当复述听众，说完“我复述完毕”再听反馈（完整指令见目录页）。</div>
</section>
<section class="rp rhint">
  <div class="rhead"><span class="rno">{it['id']}</span><h3>提示页</h3></div>
  <div class="hint-blk"><div class="hint-cap">关键词</div>{gen_net(it)}</div>
  <div class="hint-blk"><div class="hint-cap">思维导图</div>{gen_tree(it)}</div>
  <div class="hint-blk"><div class="hint-cap">插画</div>{ill_placeholder(it)}</div>
</section>""")

    # 集中参考
    H.append('<section class="refsec"><h2>复述参考</h2></section>')
    for it in RETELLS:
        mp = pages.get(it["id"], "—")
        H.append(f"""
<div class="ans">
  <div class="anshead"><span class="rno">{it['id']}</span><span class="ans-t">{it['title']}</span><span class="backref">材料见第 {mp} 页</span></div>
  <p class="refbody">{it['ref']}</p>
  <div class="mapkey">导图参照：{it['mapkey']}</div>
</div>""")

    # 评论：问题页 / 观点与推演页 / 范本与拆解页
    for c in COMMENTS:
        mp = pages.get(c["ref"], "—")
        qs = "".join(f'<li>{q}<div class="wl"></div></li>' for q in c["questions"])
        recap = "".join(f"<li>{x}</li>" for x in c["recap"])
        views = "".join(f'<li>{v[0]}<div class="how">依据与来源：{v[1]}</div></li>' for v in c["views"])
        script = "".join(f'<p>{x}</p>' for x in c["script"])
        H.append(f"""
<section class="cq">
  <div class="cuhead"><span class="rno">{c['id']}</span><h3>{c['title']}</h3><span class="backref">对应复述·{c['ref']} 材料页（第 {mp} 页）</span></div>
  <div class="cu-blk"><div class="lbl">回想材料</div><ul class="recap">{recap}</ul></div>
  <div class="cu-blk"><div class="lbl">思考问题</div><ol class="qs">{qs}</ol></div>
  <div class="cqfoot">观点与推演见下一页。</div>
</section>
<section class="cview">
  <div class="cuhead"><span class="rno">{c['id']}</span><h3>{c['title']} · 观点与推演</h3></div>
  <div class="cu-blk"><div class="lbl">观点参考</div><div class="baseline">{c['base']}</div><ul class="views">{views}</ul></div>
  <div class="cu-blk"><div class="lbl">怎么想到的：拆开讲</div><p class="ctx reason">{c['reasoning']}</p></div>
</section>
<section class="cscript">
  <div class="cuhead"><span class="rno">{c['id']}</span><h3>{c['title']} · 口语范本与拆解</h3></div>
  <div class="cu-blk"><div class="lbl">口语范本</div><div class="script cu-script">{script}</div></div>
  <div class="cu-blk"><div class="lbl">全文主线</div><p class="ctx">{c['spine']}</p></div>
  <div class="cu-blk"><div class="lbl">拆解</div><p class="ctx">{c['decon']}</p></div>
</section>""")

    # 原文拆解与积累
    for fi, f in enumerate(FRAGMENTS):
        textparas = "".join(f'<p class="ni">{x}</p>' for x in f["text"].split("\n"))
        modn = '<div class="modhead-inline"><h2>原文拆解与积累</h2></div>' if fi == 0 else ""
        H.append(f"""
<section class="fu">{modn}
  <div class="cuhead"><span class="rno">{f['id']}</span><h3>{f['topic']}</h3><span class="backref">{f['src']}</span></div>
  <div class="cu-blk"><div class="lbl">前因后果</div><p class="ctx">{f['context']}</p></div>
  <div class="quote fragtext">{textparas}</div>
  <div class="cu-blk"><div class="lbl">重点拆解</div><p class="ctx">{f['analyze']}</p></div>
  <div class="cu-blk"><div class="lbl">积累与使用</div>
    <p class="ctx"><b>值得记住的表达</b>　{f['memorize']}</p>
    <p class="ctx"><b>可以借鉴的讲法</b>　{f['method']}</p>
    <p class="ctx"><b>换个话题，可以这样说</b>　{f['demo']}</p>
  </div>
</section>""")

    H.append('<section class="appendix"><h2>附录 · 使用说明</h2><div class="prompt"><p>1. AI 陪练用于有设备的时段；纸面资料可独立使用。完整指令见目录页下方，也可向老师索取可复制文本。</p><p>2. 提示页的「关键词」「思维导图」「插画」可以任选、结合使用；不必按顺序练三遍。</p><p>3. 思维导图的虚线框补的是完整意思：可以写短语、分点，或一两句话；要点对照「复述参考」的导图参照。</p><p>4. 本期插画以需求包方式制作回传，到版前提示页第三栏标注“待整合”。</p></div></section>')
    H.append("</body></html>")
    return "".join(H)

if __name__ == "__main__":
    pages = None
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        pages = json.load(open(sys.argv[1]))
    html = build(pages)
    open(os.path.join(HERE, "sample.html"), "w", encoding="utf-8").write(html)
    print("sample.html written, bytes:", len(html))

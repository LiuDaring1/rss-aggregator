# -*- coding: utf-8 -*-
"""build3.py — 组装 rev.3（两页一题+集中答案+插画预留）"""
import json, os, sys
from content3 import RETELLS, COMMENTS, FRAGMENTS

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "PingFang SC, Hiragino Sans GB, sans-serif"
PROMPT = ""
if os.path.exists(os.path.join(HERE, "ai-retelling-prompt.txt")):
    PROMPT = open(os.path.join(HERE, "ai-retelling-prompt.txt"), encoding="utf-8").read()
    # 目录页展示版：去掉实测状态段（该信息在 txt 文件与教师备注中保留）
    PROMPT = PROMPT.split("【实测状态】")[0].rstrip()

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
    W, H = 720, 235
    cx, cy = 360, 117
    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">',
             f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>']
    pos = [(120, 38), (600, 38), (52, 117), (668, 117), (120, 196), (600, 196)]
    for (cat, word), (x, y) in zip(item["net"]["sats"], pos):
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x}" y2="{y}" stroke="#000" stroke-width="1" stroke-dasharray="3,3"/>')
    for (cat, word), (x, y) in zip(item["net"]["sats"], pos):
        w = max(92, int(len(word) * 14.5))
        parts.append(f'<rect x="{x-w/2}" y="{y-16}" width="{w}" height="34" fill="#fff" stroke="#000" stroke-width="1.1"/>')
        parts.append(text_el(x, y - 4, cat, size=10, fill="#444"))
        parts.append(text_el(x, y + 12, word, size=13.5, weight="600"))
    ccw = max(170, int(len(item["net"]["center"]) * 16.5))
    parts.append(f'<rect x="{cx-ccw/2}" y="{cy-19}" width="{ccw}" height="38" fill="#fff" stroke="#000" stroke-width="1.8"/>')
    parts.append(text_el(cx, cy + 6, item["net"]["center"], size=15.5, weight="700"))
    parts.append("</svg>")
    return "".join(parts)

def gen_tree(item):
    """树状思维导图（留空版）：根 → 主枝 → 子节点；dict(child)=整块留空"""
    root = item["tree"]["root"]
    branches = item["tree"]["branches"]
    # 行高计算
    rows = []  # (branch_idx, child, height)
    for bi, br in enumerate(branches):
        for ch in br["children"]:
            h = 50 if (isinstance(ch, dict) and ch.get("tall")) else 36
            rows.append((bi, ch, h))
    H = 16 + sum(h + 8 for _, _, h in rows) + 8
    W = 720
    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">',
             f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>']
    # 子节点列
    child_x, child_w = 392, 316
    y = 16
    branch_span = {}
    for bi, ch, h in rows:
        branch_span.setdefault(bi, [y, y + h])
        branch_span[bi][1] = y + h
        cy_mid = y + h / 2
        if isinstance(ch, dict):
            parts.append(f'<rect x="{child_x}" y="{y}" width="{child_w}" height="{h}" fill="#fff" stroke="#000" stroke-width="1.2" stroke-dasharray="4,3"/>')
            for j, ln in enumerate(wrap_lines("✎ " + ch["blank"], 26)[:1 if h <= 40 else 2]):
                parts.append(text_el(child_x + 10, y + 20 + j * 16, ln, size=11, fill="#555", anchor="start"))
        else:
            parts.append(f'<rect x="{child_x}" y="{y}" width="{child_w}" height="{h}" fill="#fff" stroke="#000" stroke-width="1.1"/>')
            lns = wrap_lines(ch, 25)[:2]
            for j, ln in enumerate(lns):
                parts.append(text_el(child_x + 10, y + 22 + j * 16, ln, size=12, anchor="start"))
        y += h + 8
    # 主枝节点
    for bi, br in enumerate(branches):
        y0, y1 = branch_span[bi]
        by = (y0 + y1) / 2
        parts.append(f'<path d="M 190 {by} H 230" stroke="#000" stroke-width="1.1"/>')
        parts.append(f'<rect x="232" y="{by-16}" width="152" height="32" fill="#fff" stroke="#000" stroke-width="1.5"/>')
        parts.append(text_el(308, by + 5, br["label"], size=13, weight="700"))
        # 连到每个子节点
        y0, y1 = branch_span[bi]
        parts.append(f'<path d="M 384 {by} V {(y0+y1)/2} H 392" stroke="#000" stroke-width="1" fill="none"/>')
    # 根节点
    ry = H / 2
    rw = max(150, int(len(root) * 15.5))
    parts.append(f'<rect x="12" y="{ry-20}" width="{rw}" height="40" fill="#fff" stroke="#000" stroke-width="1.8"/>')
    parts.append(text_el(12 + rw / 2, ry + 5, root, size=13.5, weight="700"))
    for bi in branch_span:
        y0, y1 = branch_span[bi]
        parts.append(f'<path d="M {12+rw} {ry} H 210 V {(y0+y1)/2} H 232" stroke="#000" stroke-width="1.2" fill="none"/>')
    parts.append(text_el(W - 6, H - 4, "虚线框＝整块补写区（答案见「复述参考」）", size=9.5, fill="#555", anchor="end"))
    parts.append("</svg>")
    return "".join(parts)

def ill_placeholder(item):
    no = "R%02d-ILL01" % (RETELLS.index(item) + 1)
    return f"""<div class="illhold">
  <div class="ill-no">插画位 {no} · 插画待回传</div>
  <div class="ill-note">黑白报刊式叙事插画（需求见 illustration-briefs.md，{esc(item['title'][:18])}…）</div>
</div>"""

def build(pages=None):
    pages = pages or {}
    H = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>口语素材周刊 · 2026年9月第1期（试刊）</title><link rel="stylesheet" href="style3.css"></head><body>']

    H.append("""
<div class="cover">
  <div class="kicker">播音主持艺考 · 即兴口语表达</div>
  <h1>口语素材周刊</h1>
  <div class="issue">2026 年 9 月第 1 期（试刊）</div>
  <div class="cover-note">
    <b>复述</b>——每则两页：材料页＋提示页；全部参考答案集中在复述栏目末尾的「复述参考」。<br>
    <b>评论</b>——就同一批材料先想后说：每单元先思考页，参考内容在下一页。<br>
    <b>原文拆解与积累</b>——独立精选近期评论里的完整好段，学它为什么好、怎么用。<br>
    <span class="small">AI 陪练：材料页脚有简短提示，完整指令见目录页下方与附录。</span>
  </div>
</div>""")

    # 目录 + 陪练用法
    toc = ['<div class="tocpage"><h2 class="toc-h">目录</h2><div class="toc-cols">']
    toc.append('<div class="toc-col"><div class="toc-sec">复述</div>')
    for it in RETELLS:
        pg = pages.get(it["id"], "—")
        rng = f"{pg}–{pg+1}" if pg != "—" else "—"
        tagcls = "tag-hot" if it["tag"] == "热点" else "tag-warm"
        toc.append(f'<div class="toc-item"><span class="tag {tagcls}">{it["tag"]}</span><span class="toc-t">{it["title"]}</span><span class="toc-p">{rng}</span></div>')
    refp = pages.get("复述参考", "—")
    toc.append(f'<div class="toc-item toc-sub"><span class="toc-t">复述参考（全部题的参考答案）</span><span class="toc-p">{refp}</span></div>')
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
  <div class="pb-cap">AI 陪练完整指令（复制给豆包等语音 AI；材料页脚有简短版）</div>
  <pre class="pb-text">{esc(PROMPT)}</pre>
</div>
<div class="toc-append">附录 · 使用与边界说明 <span class="toc-p">{ap}</span></div></div>""")
    H.append("".join(toc))

    # 复述：每则两页
    for it in RETELLS:
        H.append(f"""
<section class="rp rmat">
  <div class="rhead"><span class="rno">{it['id']}</span><span class="tag {'tag-hot' if it['tag']=='热点' else 'tag-warm'}">{it['tag']}</span><h3>{it['title']}</h3></div>
  <div class="dateline">{it['dateline']}</div>
  {''.join(f'<p class="matbody">{x}</p>' for x in it['body'])}
  <div class="src">{it['source']}</div>
  <div class="aifoot">AI 陪练提示：把本页拍给豆包等 AI，让它当你的复述听众，听你说完“我复述完毕”再纠错（完整指令见目录页）。</div>
</section>
<section class="rp rhint">
  <div class="rhead"><span class="rno">{it['id']}</span><h3>提示页 · 先想后说</h3></div>
  <div class="hint-note">先用<b>关键词网络</b>唤起人和事 → 再在<b>思维导图</b>的虚线框里补整块信息、理清分支 → 最后看<b>插画</b>对一遍场景。</div>
  <div class="hint-blk"><div class="hint-cap">① 关键词网络</div>{gen_net(it)}</div>
  <div class="hint-blk"><div class="hint-cap">② 思维导图（虚线框整块补写，答案见「复述参考」）</div>{gen_tree(it)}</div>
  <div class="hint-blk"><div class="hint-cap">③ 插画</div>{ill_placeholder(it)}</div>
</section>""")

    # 集中参考
    H.append('<section class="refsec"><h2>复述参考</h2><div class="modnote">八道题的参考复述集中在这里。先自己讲，再对照；参考复述示范事实取舍与叙述顺序，不要求逐字一致。</div></section>')
    for it in RETELLS:
        mp = pages.get(it["id"], "—")
        H.append(f"""
<div class="ans">
  <div class="anshead"><span class="rno">{it['id']}</span><span class="ans-t">{it['title']}</span><span class="backref">材料见第 {mp} 页</span></div>
  <p class="refbody">{it['ref']}</p>
  <div class="mapkey">导图参照：{it['mapkey']}</div>
</div>""")

    # 评论：思考页 + 参考页
    for ci, c in enumerate(COMMENTS):
        mp = pages.get(c["ref"], "—")
        qs = "".join(f'<li>{q}<div class="wl"></div></li>' for q in c["questions"])
        recap = "".join(f"<li>{x}</li>" for x in c["recap"])
        modn = '<div class="modhead-inline"><h2>评论</h2><div class="modnote">与「复述」同一批材料。复述面向不了解事件的听众，评论面向读过题干的考官：先亮观点，再讲道理。每单元先看思考页，参考内容从下一页开始。</div></div>' if ci == 0 else ""
        H.append(f"""
<section class="cq">{modn}
  <div class="cuhead"><span class="rno">{c['id']}</span><h3>{c['title']}</h3><span class="backref">对应复述·{c['ref']} 材料页（第 {mp} 页）</span></div>
  <div class="cu-blk"><div class="lbl">回想材料</div><ul class="recap">{recap}</ul></div>
  <div class="cu-blk"><div class="lbl">先想几个问题</div><ol class="qs">{qs}</ol></div>
  <div class="cqfoot">观点参考、推演讲解、口语范本与拆解，从下一页开始。</div>
</section>
<section class="ca">
  <div class="cuhead"><span class="rno">{c['id']}</span><h3>{c['title']} · 参考</h3></div>
  <div class="cu-blk"><div class="lbl">观点参考</div><div class="baseline">{c['base']}</div><ul class="views">{''.join(f'<li>{v[0]}<div class="how">依据与来源：{v[1]}</div></li>' for v in c['views'])}</ul></div>
  <div class="cu-blk"><div class="lbl">推演讲解</div><p class="ctx">{c['reasoning']}</p></div>
  <div class="cu-blk"><div class="lbl">口语范本</div><div class="script cu-script">{''.join(f'<p>{x}</p>' for x in c['script'])}</div></div>
  <div class="cu-blk"><div class="lbl">范本拆解</div><p class="review">{c['review']}</p></div>
</section>""")

    # 原文拆解与积累
    for fi, f in enumerate(FRAGMENTS):
        textparas = "".join(f'<p class="ni">{x}</p>' for x in f["text"].split("\n"))
        modn2 = '<div class="modhead-inline"><h2>原文拆解与积累</h2><div class="modnote">独立精选近期评论里的完整段落（与本期两模块题目不重复）。片段均为原文照录，删节以「……」标示；来源、日期随文标注。</div></div>' if fi == 0 else ""
        H.append(f"""
<section class="fu">{modn2}
  <div class="cuhead"><span class="rno">{f['id']}</span><h3>{f['topic']}</h3><span class="backref">{f['src']}</span></div>
  <div class="cu-blk"><div class="lbl">前因后果</div><p class="ctx">{f['context']}</p></div>
  <div class="quote fragtext">{textparas}</div>
  <div class="cu-blk"><div class="lbl">重点拆解</div><p class="ctx">{f['analyze']}</p></div>
  <div class="cu-blk"><div class="lbl">积累与使用</div><p class="ctx"><b>可背：</b>{f['memorize']}　<b>用位：</b>{f['use_where']}</p><p class="ctx"><b>使用示例：</b>{f['use_demo']}</p></div>
</section>""")

    # 附录
    H.append('<section class="appendix"><h2>附录 · 使用与边界说明</h2><div class="prompt"><p>1. AI 陪练用于有设备的时段；纸面资料可独立使用。指令全文见目录页下方，也可向老师索取可复制文本。</p><p>2. 「提示页」三样东西各有分工：关键词网络提示信息，思维导图组织信息，插画唤起场景——不必逐字背图上的话。</p><p>3. 参考复述示范取舍与顺序，意思准确的说法都算对；导图虚线框补的是完整意思，不要求逐字一致。</p><p>4. 本期插画以需求包方式另行制作回传，到版前此处标注“待整合”（见各提示页插画位）。</p></div></section>')
    H.append("</body></html>")
    return "".join(H)

if __name__ == "__main__":
    pages = None
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        pages = json.load(open(sys.argv[1]))
    html = build(pages)
    open(os.path.join(HERE, "sample.html"), "w", encoding="utf-8").write(html)
    print("sample.html written, bytes:", len(html))

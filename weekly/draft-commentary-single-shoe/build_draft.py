# -*- coding: utf-8 -*-
import os, sys
from content_draft import DRAFT_COMMENTARY

DIR = os.path.dirname(os.path.abspath(__file__))

def build_html():
    c = DRAFT_COMMENTARY
    
    # 1. Recap
    recap_html = "".join(f"<li>{r}</li>" for r in c["recap"])
    
    # Questions
    qs_html = "".join(f"<li>{q}<div class='wl'></div></li>" for q in c["questions"])
    
    # 2. Views
    views_html = "".join(
        f"<li><strong>{v[0]}</strong><div class='how'>依据与来源：{v[1]}</div></li>"
        for v in c["views"]
    )
    
    # Reasoning
    reason_paras = "".join(f"<p>{p}</p>" for p in c["reasoning"].strip().split("\n") if p.strip())
    
    # 3. Script
    script_html = "".join(f"<p>{p}</p>" for p in c["script"])
    
    # Decon
    decon_paras = "".join(f"<p>{p}</p>" for p in c["decon"].strip().split("\n") if p.strip())
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{c['title']} · 评论三页单元新稿</title>
<link rel="stylesheet" href="style_draft.css">
</head>
<body>

<!-- 第1页：问题页 -->
<section class="cq">
  <div class="cuhead">
    <span class="rno">{c['id']}</span>
    <h3>{c['title']}</h3>
    <span class="backref">来源：{c['story_source']}</span>
  </div>
  
  <div class="cu-blk">
    <div class="lbl">回想材料 · 关键事实</div>
    <ul class="recap">{recap_html}</ul>
  </div>
  
  <div class="cu-blk" style="margin-top: 5mm;">
    <div class="lbl">思考问题 · 带着问题看材料</div>
    <ol class="qs">{qs_html}</ol>
  </div>
  
  <div class="pagefoot">
    <span>口语素材周刊 · 评论模块示范单元（新稿）</span>
    <span>第 1 页 / 共 3 页 · 问题页</span>
  </div>
</section>

<!-- 第2页：观点与推演页 -->
<section class="cview">
  <div class="cuhead">
    <span class="rno">{c['id']}</span>
    <h3>{c['title']} · 观点与推演</h3>
    <span class="backref">多方向思考 · 逐一耐心推演</span>
  </div>
  
  <div class="cu-blk">
    <div class="lbl">思考入口与直觉诊断</div>
    <div class="baseline">{c['base']}</div>
  </div>
  
  <div class="cu-blk">
    <div class="lbl">观点参考 · 5个互不重复的具体思考方向</div>
    <ul class="views">{views_html}</ul>
  </div>
  
  <div class="cu-blk reason-box">
    <div class="lbl">怎么想到的：拆开讲（逻辑推演链条）</div>
    <div class="ctx reason">{reason_paras}</div>
  </div>
  
  <div class="pagefoot">
    <span>口语素材周刊 · 评论模块示范单元（新稿）</span>
    <span>第 2 页 / 共 3 页 · 观点与推演页</span>
  </div>
</section>

<!-- 第3页：口语范本与拆解页 -->
<section class="cscript">
  <div class="cuhead">
    <span class="rno">{c['id']}</span>
    <h3>{c['title']} · 口语范本与拆解</h3>
    <span class="backref">收束为主线 · 两个主体段展开</span>
  </div>
  
  <div class="cu-blk">
    <div class="lbl">全文主线（从多种思考中选定一条深入组织）</div>
    <div class="spine-box">{c['spine']}</div>
  </div>
  
  <div class="cu-blk">
    <div class="lbl">口语范本（2分钟口语考场表达示范，约380字）</div>
    <div class="script cu-script">{script_html}</div>
  </div>
  
  <div class="cu-blk" style="margin-top: 2.5mm;">
    <div class="lbl">论述拆解与教学指导</div>
    <div class="decon-list">{decon_paras}</div>
  </div>
  
  <div class="pagefoot">
    <span>口语素材周刊 · 评论模块示范单元（新稿）</span>
    <span>第 3 页 / 共 3 页 · 范本与拆解页</span>
  </div>
</section>

</body>
</html>
"""
    out_path = os.path.join(DIR, "draft.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"draft.html generated successfully ({len(html)} bytes)")

if __name__ == "__main__":
    build_html()

# -*- coding: utf-8 -*-
"""
口语素材周刊 渲染模块 (Jinja2 + Chromium + PyMuPDF)
遵循：
1. 确定性渲染，无网络与模型调用
2. Jinja2 开启 StrictUndefined 与 HTML 转义
3. 双主体与观点池解耦，渲染所有观点
4. 支持单单元预览（HTML/PDF/PNG）与整刊构建
"""
import os
import sys
import subprocess
import html
from typing import Dict, Any, List, Optional
from jinja2 import Environment, FileSystemLoader, StrictUndefined

# 确保路径解析
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from weekly_pipeline.models import (
    RetellingUnit, CommentaryUnit, ExcerptUnit, IssueManifest, MindmapTree
)

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(PACKAGE_DIR, "templates")
ASSETS_DIR = os.path.join(PACKAGE_DIR, "assets")
STYLE_CSS_PATH = os.path.join(ASSETS_DIR, "style.css")

def get_style_css() -> str:
    if os.path.exists(STYLE_CSS_PATH):
        with open(STYLE_CSS_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def get_jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        undefined=StrictUndefined,
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True
    )
    return env

# ==============================================================================
# SVG 图示生成 (无头纯 Python 矢量绘制，兼容 A4 打印)
# ==============================================================================

FONT_FAMILY = "PingFang SC, Hiragino Sans GB, sans-serif"

def esc(s: str) -> str:
    return html.escape(str(s))

def text_el(x: float, y: float, s: str, size: float = 13, weight: str = "normal",
            anchor: str = "middle", fill: str = "#000") -> str:
    return (f'<text x="{x}" y="{y}" font-family="{FONT_FAMILY}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">{esc(s)}</text>')

def generate_keywords_svg(center: str, keywords: List[str]) -> str:
    """生成 6 卫星节点关键词网络 SVG"""
    W, H = 720, 235
    cx, cy = 360, 117
    parts = [
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>'
    ]
    pos = [(128, 38), (592, 38), (70, 117), (650, 117), (128, 196), (592, 196)]
    
    # 取前 6 个或补齐
    kw_items = keywords[:6]
    while len(kw_items) < len(pos):
        kw_items.append("要点")
        
    for kw, (x, y) in zip(kw_items, pos):
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x}" y2="{y}" stroke="#000" stroke-width="1" stroke-dasharray="3,3"/>')
        
    for kw, (x, y) in zip(kw_items, pos):
        w = min(180, max(90, int(len(kw) * 14)))
        bx = min(max(6, x - w / 2), W - 6 - w)
        parts.append(f'<rect x="{bx:.0f}" y="{y-16}" width="{w}" height="34" fill="#fff" stroke="#000" stroke-width="1.1"/>')
        parts.append(text_el(bx + w / 2, y + 5, kw, size=12.5, weight="600"))
        
    ccw = min(240, max(150, int(len(center) * 15.5)))
    ccx = min(max(6, cx - ccw / 2), W - 6 - ccw)
    parts.append(f'<rect x="{ccx:.0f}" y="{cy-19}" width="{ccw}" height="38" fill="#fff" stroke="#000" stroke-width="1.8"/>')
    parts.append(text_el(ccx + ccw / 2, cy + 6, center, size=14.5, weight="700"))
    parts.append("</svg>")
    return "".join(parts)

def generate_mindmap_svg(tree: MindmapTree) -> str:
    """根据 MindmapTree 模型生成思维导图 SVG"""
    root = tree.center
    branches = tree.branches
    rows = []
    for bi, br in enumerate(branches):
        for leaf in br.leaves:
            # 兼容 tall 判断
            tall = len(leaf.hint) > 10
            rows.append((bi, leaf.hint, tall))
            
    if not rows:
        return f'<svg viewBox="0 0 720 100" xmlns="http://www.w3.org/2000/svg"><text x="360" y="50" text-anchor="middle">{esc(root)}</text></svg>'
        
    H = 14 + sum((56 if t else 42) + 7 for _, _, t in rows) + 6
    W = 720
    parts = [
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>'
    ]
    child_x, child_w = 350, 362
    y = 14
    span: Dict[int, List[float]] = {}
    
    for bi, hint, tall in rows:
        h = 56 if tall else 42
        span.setdefault(bi, [y, y + h])
        span[bi][1] = y + h
        parts.append(f'<rect x="{child_x}" y="{y}" width="{child_w}" height="{h}" fill="#fff" stroke="#000" stroke-width="1.2" stroke-dasharray="5,3"/>')
        parts.append(text_el(child_x + 9, y + 16, hint, size=11, fill="#555", anchor="start"))
        y += h + 7
        
    branch_x = 210
    b_mid: Dict[int, float] = {}
    for bi, br in enumerate(branches):
        if bi not in span:
            continue
        y0, y1 = span[bi]
        my = (y0 + y1) / 2
        b_mid[bi] = my
        parts.append(text_el(branch_x + 46, my + 5, br.name, size=13, weight="700"))
        parts.append(f'<path d="M {branch_x+100} {my} H {child_x-8} V {my:.0f} H {child_x-2}" stroke="#000" stroke-width="1" fill="none"/>')
        
    rx = 20
    ry = H / 2
    parts.append(text_el(rx, ry + 5, root, size=14, weight="700", anchor="start"))
    spine_x = branch_x - 14
    if b_mid:
        ys = sorted(b_mid.values())
        parts.append(f'<path d="M {rx+8*len(root)+8} {ry} H {spine_x}" stroke="#000" stroke-width="1.2" fill="none"/>')
        parts.append(f'<path d="M {spine_x} {ys[0]:.0f} V {ys[-1]:.0f}" stroke="#000" stroke-width="1.2" fill="none"/>')
        for bi, my in b_mid.items():
            parts.append(f'<path d="M {spine_x} {my:.0f} H {branch_x-2}" stroke="#000" stroke-width="1.2" fill="none"/>')
            
    parts.append(text_el(W - 6, H - 3, "虚线框＝待补写（要点见「复述参考」导图参照）", size=9.5, fill="#555", anchor="end"))
    parts.append("</svg>")
    return "".join(parts)


# ==============================================================================
# HTML 页面渲染
# ==============================================================================

def render_unit_preview_html(unit: Any, unit_type: str, backref_page: Optional[int] = None, is_unverified: bool = False) -> str:
    """渲染单单元预览 HTML"""
    env = get_jinja_env()
    template = env.get_template("unit_preview.html.jinja2")
    style_css = get_style_css()
    
    unit_data: Dict[str, Any] = {
        "unit": unit,
        "backref_page": backref_page,
        "is_unverified": is_unverified
    }
    if unit_type == "retelling":
        unit_data["keywords_svg"] = generate_keywords_svg(
            unit.mindmap_tree.center, unit.keywords
        )
        unit_data["mindmap_svg"] = generate_mindmap_svg(unit.mindmap_tree)
        unit_data["illustration_html"] = None
    elif unit_type == "commentary":
        retelling_title = ""
        try:
            import yaml
            ref_path = os.path.join(PACKAGE_DIR, f"../../content/retellings/{unit.retelling_ref}.yaml")
            if os.path.exists(ref_path):
                with open(ref_path, "r", encoding="utf-8") as f:
                    r_raw = yaml.safe_load(f)
                    rt = r_raw.get("title", "")
                    if "：" in rt:
                        retelling_title = rt.split("：")[0].strip().replace("“", "").replace("”", "")
                    else:
                        retelling_title = rt.strip().replace("“", "").replace("”", "")
        except Exception:
            pass
        unit_data["retelling_title"] = retelling_title
        
    badge_title = " · 草稿（未核验）" if is_unverified else ""
    html_out = template.render(
        title=f"口语周刊 · 单元预览{badge_title} [{unit.id}] {getattr(unit, 'title', getattr(unit, 'topic', ''))}",
        style_css=style_css,
        unit_type=unit_type,
        unit_data=unit_data
    )
    return html_out

def render_issue_html(manifest: IssueManifest,
                      retellings: List[RetellingUnit],
                      commentaries: List[CommentaryUnit],
                      excerpts: List[ExcerptUnit],
                      page_map: Optional[Dict[str, Any]] = None,
                      ai_prompt: str = "") -> str:
    """渲染整刊 HTML"""
    env = get_jinja_env()
    template = env.get_template("full_issue.html.jinja2")
    style_css = get_style_css()
    page_map = page_map or {}
    
    retellings_data = []
    for r in retellings:
        retellings_data.append({
            "unit": r,
            "keywords_svg": generate_keywords_svg(r.mindmap_tree.center, r.keywords),
            "mindmap_svg": generate_mindmap_svg(r.mindmap_tree),
            "illustration_html": None
        })
        
    commentaries_data = []
    for c in commentaries:
        backref = page_map.get(c.retelling_ref)
        retelling_title = ""
        for r in retellings:
            if r.id == c.retelling_ref:
                rt = getattr(r, "title", "")
                if "：" in rt:
                    retelling_title = rt.split("：")[0].strip().replace("“", "").replace("”", "")
                else:
                    retelling_title = rt.strip().replace("“", "").replace("”", "")
                break
        commentaries_data.append({
            "unit": c,
            "backref_page": backref,
            "retelling_title": retelling_title
        })
        
    excerpts_data = [{"unit": f} for f in excerpts]
    
    html_out = template.render(
        title=f"{manifest.title} · {manifest.issue_no_label}",
        style_css=style_css,
        manifest=manifest,
        retellings=retellings,
        commentaries=commentaries,
        excerpts=excerpts,
        retellings_data=retellings_data,
        commentaries_data=commentaries_data,
        excerpts_data=excerpts_data,
        page_map=page_map,
        ai_prompt=ai_prompt
    )
    return html_out


# ==============================================================================
# PDF 导出与 PNG 页面快照生成
# ==============================================================================

def find_chrome_binary() -> Optional[str]:
    """寻找 Chrome / Chromium 路径"""
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "google-chrome",
        "chromium",
        "chromium-browser"
    ]
    for c in candidates:
        if os.path.exists(c) and os.access(c, os.X_OK):
            return c
        # 检查 PATH
        path = subprocess.run(["which", c], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if path.returncode == 0 and path.stdout.strip():
            return path.stdout.strip()
    return None

def render_html_to_pdf(html_path: str, output_pdf_path: str) -> None:
    """使用 Chrome 无头模式精确打印 A4 PDF"""
    chrome_bin = find_chrome_binary()
    if not chrome_bin:
        raise RuntimeError("未在系统中找到 Chrome 或 Chromium，无法执行无头 PDF 渲染。")
        
    abs_html = os.path.abspath(html_path)
    abs_pdf = os.path.abspath(output_pdf_path)
    os.makedirs(os.path.dirname(abs_pdf), exist_ok=True)
    
    cmd = [
        chrome_bin,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={abs_pdf}",
        "--virtual-time-budget=5000",
        f"file://{abs_html}"
    ]
    
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Chrome PDF 导出失败: {proc.stderr}")
    if not os.path.exists(abs_pdf) or os.path.getsize(abs_pdf) == 0:
        raise RuntimeError(f"Chrome PDF 导出未生成有效文件: {abs_pdf}")

def render_pdf_to_pngs(pdf_path: str, output_dir: str, prefix: str = "page", dpi: int = 150) -> List[str]:
    """使用 PyMuPDF (fitz) 将 PDF 的每一页高质量导出为 PNG 预览图"""
    import fitz
    
    abs_pdf = os.path.abspath(pdf_path)
    abs_out_dir = os.path.abspath(output_dir)
    os.makedirs(abs_out_dir, exist_ok=True)
    
    doc = fitz.open(abs_pdf)
    png_paths = []
    
    for i, page in enumerate(doc):
        # 150 DPI 适合审阅
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        out_png = os.path.join(abs_out_dir, f"{prefix}_p{i+1:02d}.png")
        pix.save(out_png)
        png_paths.append(out_png)
        
    return png_paths

def preview_unit(unit: Any, unit_type: str, out_dir: str,
                 formats: Optional[List[str]] = None,
                 backref_page: Optional[int] = None,
                 is_unverified: bool = False) -> Dict[str, Any]:
    """快捷单单元全格式预览接口"""
    formats = formats or ["html", "pdf", "png"]
    os.makedirs(out_dir, exist_ok=True)
    
    unit_id = unit.id
    html_content = render_unit_preview_html(unit, unit_type, backref_page=backref_page, is_unverified=is_unverified)
    
    results: Dict[str, Any] = {"unit_id": unit_id, "unit_type": unit_type, "is_unverified": is_unverified}
    
    # 强制覆盖写入最新 HTML，确保无头浏览器打印的始终是最新内容
    html_file = os.path.join(out_dir, f"{unit_id}.html")
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    if "html" in formats:
        results["html"] = html_file
        
    if "pdf" in formats or "png" in formats:
        pdf_file = os.path.join(out_dir, f"{unit_id}.pdf")
        render_html_to_pdf(html_file, pdf_file)
        results["pdf"] = pdf_file
        
        if "png" in formats:
            pngs = render_pdf_to_pngs(pdf_file, out_dir, prefix=f"{unit_id}")
            results["pngs"] = pngs
            
    return results

# -*- coding: utf-8 -*-
"""
验证新材料选材原段子串完整性与分册页数准确性
"""
import os
import sys
import yaml
import pypdf

def verify_quotes():
    sources = {
        "F13": ("content/excerpts/F13.yaml", "issues/issue-trial-01/sources/F13_shilaohua.txt"),
        "F14": ("content/excerpts/F14.yaml", "issues/issue-trial-01/sources/F14_darenan.txt"),
    }
    all_ok = True
    for fid, (y_path, s_path) in sources.items():
        if not os.path.exists(y_path) or not os.path.exists(s_path):
            print(f"❌ 缺失文件: {y_path} 或 {s_path}")
            all_ok = False
            continue
        with open(y_path, "r", encoding="utf-8") as f:
            y_data = yaml.safe_load(f)
        with open(s_path, "r", encoding="utf-8") as f:
            s_text = f.read()

        quotes = y_data.get("quote_paragraphs", [])
        for idx, q in enumerate(quotes):
            # 必须为完整连续子串 (允许去空白匹配)
            q_clean = q.replace(" ", "").replace("\n", "").strip()
            s_clean = s_text.replace(" ", "").replace("\n", "").strip()
            if q_clean not in s_clean:
                print(f"❌ {fid} 第 {idx+1} 段在来源原文中未找到完全匹配连续子串！")
                print(f"   引文前30字: {q[:30]}...")
                all_ok = False
            else:
                print(f"✅ {fid} 第 {idx+1} 段 100% 匹配来源原文连续子串 ({len(q)} 字符)")

    return all_ok

def verify_split_pages(issue_pdf_dir="outputs/issue-trial-01"):
    expected = {
        "issue-trial-01-复述.pdf": 7,
        "issue-trial-01-评论.pdf": 6,
        "issue-trial-01-原文拆解与积累.pdf": 2,
    }
    all_ok = True
    for fname, exp_pg in expected.items():
        fpath = os.path.join(issue_pdf_dir, fname)
        if not os.path.exists(fpath):
            print(f"❌ 分册文件不存在: {fpath}")
            all_ok = False
            continue
        reader = pypdf.PdfReader(fpath)
        act_pg = len(reader.pages)
        if act_pg != exp_pg:
            print(f"❌ 分册 {fname} 页数异常: 实际 {act_pg} 页 != 预期 {exp_pg} 页")
            all_ok = False
        else:
            print(f"✅ 分册 {fname} 物理页数校验通过 ({act_pg} 页)")
    return all_ok

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "issues/issue-trial-01"
    q_ok = verify_quotes()
    print("-" * 50)
    p_ok = verify_split_pages(target_dir)
    if not (q_ok and p_ok):
        sys.exit(1)
    print(f"\n🎉 全部信源原段匹配与分册物理页数校验 100% 通过 ({target_dir})！")

# -*- coding: utf-8 -*-
"""
生成整刊完整 Markdown 学生文本 (同源导出并校验非空)
"""
import os
import sys
import yaml

# 注入项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../publishing")))

from weekly_pipeline.models import IssueManifest
from weekly_pipeline.export_markdown import export_full_issue_markdown

def generate_issue_md(issue_id: str = "issue-2026-w37", out_file: str = "issues/issue-2026-w37/issue-2026-w37.md"):
    manifest_path = os.path.join("issues", issue_id, "issue.yaml")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"未找到期号配置文件: {manifest_path}")
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = yaml.safe_load(f)
    manifest = IssueManifest.model_validate(manifest_data)
    
    # AI prompt
    prompt_text = ""
    prompt_file = os.path.join("issues", issue_id, manifest.ai_prompt_path or "ai-retelling-prompt.txt")
    if os.path.exists(prompt_file):
        with open(prompt_file, "r", encoding="utf-8") as pf:
            prompt_text = pf.read().strip()
            
    md_content = export_full_issue_markdown(
        manifest=manifest,
        content_dir="content",
        edition="student",
        ai_prompt_text=prompt_text
    )
    
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print(f"✅ 成功生成整刊 Markdown (非空断言通过): {out_file} ({len(md_content.splitlines())} 行)")
    return out_file

if __name__ == "__main__":
    generate_issue_md()


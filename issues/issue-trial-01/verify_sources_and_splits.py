# -*- coding: utf-8 -*-
"""
周刊产物全量自动化验证通用工具 (客户端快捷入口)
直接调用 weekly_pipeline.verifier 核心引擎。
"""
import os
import sys
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
PUBLISHING_DIR = os.path.join(PROJECT_ROOT, "publishing")
if PUBLISHING_DIR not in sys.path:
    sys.path.insert(0, PUBLISHING_DIR)

from weekly_pipeline.verifier import run_full_issue_verification, verify_issue_quotes, verify_issue_splits


def main():
    parser = argparse.ArgumentParser(description="周刊自动化信源字串与分册物理页数通用校验器")
    parser.add_argument("--issue", default="issue-trial-01", help="期号ID (如 issue-trial-01, issue-2026-w37)")
    parser.add_argument("--dir", default=None, help="待检测 PDF 目录 (默认: issues/<issue>)")
    parser.add_argument("--sources-dir", default=None, help="信源存档目录 (默认: issues/<issue>/sources)")
    
    args, unknown = parser.parse_known_args()
    target_dir = args.dir
    if unknown and not target_dir:
        target_dir = unknown[0]
        
    ok = run_full_issue_verification(args.issue, target_dir=target_dir, sources_dir=args.sources_dir)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

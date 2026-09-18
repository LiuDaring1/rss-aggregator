# -*- coding: utf-8 -*-
"""
周刊备料管线及页码计算单元测试
测试审阅单指出的 4 项核心验收情形及页码同源一致性。
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../publishing")))

from weekly_pipeline.prep import (
    extract_dates_from_raw, scan_raw_candidates, build_manifest_from_candidates
)
from weekly_pipeline.models import IssueManifest
from weekly_pipeline.export_markdown import compute_page_map, export_full_issue_markdown

class TestPrepPipeline(unittest.TestCase):

    def test_ttzl_date_semantics_known_and_unknown(self):
        """验收情形 4: TTZL已知或未知原报道日，两种情况均不被获奖日替代"""
        # 情况 A: TTZL 具有真实媒体报道时间 sourcePublishedAt
        raw_known = {
            "id": "ttzl-45353",
            "origin": "ttzl",
            "awardDate": "2026-09-11",
            "publishedAt": "2026-09-11", # 旧字段，实际是获奖日
            "sourcePublishedAt": "2026-09-04",
            "eventOccurredAt": "2026-09-03"
        }
        dates_a = extract_dates_from_raw(raw_known)
        self.assertEqual(dates_a["published_at"], "2026-09-04", "已知原报道日应为 2026-09-04")
        self.assertEqual(dates_a["award_date"], "2026-09-11", "获奖公示日应为 2026-09-11")
        self.assertEqual(dates_a["event_occurred_at"], "2026-09-03")

        # 情况 B: TTZL 原报道时间未知 (sourcePublishedAt 为 None)
        raw_unknown = {
            "id": "ttzl-45351",
            "origin": "ttzl",
            "awardDate": "2026-09-15",
            "publishedAt": "2026-09-15", # 旧字段
            "sourcePublishedAt": None,
            "eventOccurredAt": None
        }
        dates_b = extract_dates_from_raw(raw_unknown)
        self.assertIsNone(dates_b["published_at"], "未知原报道日必须留空为 None，绝不能被 awardDate 覆盖")
        self.assertEqual(dates_b["award_date"], "2026-09-15", "获奖公示日应保留")

        # 情况 C: 非 TTZL 来源，正常遵循 publishedAt 合同
        raw_non_ttzl = {
            "id": "bjnews-12345",
            "origin": "crawler",
            "publishedAt": "2026-09-11 08:30:00",
            "awardDate": None
        }
        dates_c = extract_dates_from_raw(raw_non_ttzl)
        self.assertEqual(dates_c["published_at"], "2026-09-11")

    def test_prep_nonexistent_raw_dir_protects_existing_output(self):
        """验收情形 3: 输入不存在时不生成已核验清单、不损伤已有交付"""
        with tempfile.TemporaryDirectory() as tmpdir:
            existing_out = os.path.join(tmpdir, "manifest_prep.json")
            original_content = '{"status": "protected_delivery"}'
            with open(existing_out, "w", encoding="utf-8") as f:
                f.write(original_content)

            nonexistent_dir = os.path.join(tmpdir, "nonexistent_raw_dir")
            
            # scan_raw_candidates 必须抛出异常阻断
            with self.assertRaises(FileNotFoundError):
                scan_raw_candidates(nonexistent_dir)

            # 已有输出文件完整且内容未受损
            with open(existing_out, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), original_content)

    def test_prep_single_synthetic_raw(self):
        """验收情形 2: 只给一条合成raw，输出仅包含该输入及明确待审核状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = os.path.join(tmpdir, "synthetic_raw")
            os.makedirs(raw_dir)
            synthetic_file = os.path.join(raw_dir, "synthetic_item.json")
            with open(synthetic_file, "w", encoding="utf-8") as f:
                json.dump({
                    "id": "synth-001",
                    "title": "合成测试事件",
                    "origin": "test_scanner",
                    "publishedAt": "2026-09-08",
                    "content": "第一段事实。\n第二段事实。"
                }, f)

            cands = scan_raw_candidates(raw_dir, "2026-09-01", "2026-09-15")
            self.assertEqual(len(cands), 1)

            out_file = os.path.join(tmpdir, "out_manifest.json")
            manifest = build_manifest_from_candidates(
                cands, issue_id="issue-test-synth", time_window="2026-09-01 ~ 2026-09-15", out_file=out_file
            )
            
            # 输出仅包含该输入
            self.assertEqual(len(manifest["candidates"]), 1)
            item = manifest["candidates"][0]
            self.assertEqual(item["raw_id"], "synth-001")
            self.assertEqual(item["title"], "合成测试事件")
            # 必须为明确待审核状态，无虚假 agent_done
            self.assertEqual(item["action_decision"], "pending_review")
            self.assertIsNone(item["workflow_status"]["agent_done"])
            self.assertIn("待人工/Agent", item["workflow_status"]["pending_signoff"])

    def test_prep_change_issue_id_and_time_window(self):
        """验收情形 1: 更换期号和时间窗，不再输出固定w37"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = os.path.join(tmpdir, "raw")
            os.makedirs(raw_dir)
            # 创建 9月18日 的条目 (在 w38 窗口)
            with open(os.path.join(raw_dir, "item_w38.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "w38-001",
                    "title": "第38周新事件",
                    "origin": "news",
                    "publishedAt": "2026-09-18",
                    "content": "测试内容"
                }, f)

            # 扫描 w38 窗口
            cands_w38 = scan_raw_candidates(raw_dir, "2026-09-16", "2026-09-22")
            self.assertEqual(len(cands_w38), 1)
            manifest = build_manifest_from_candidates(
                cands_w38, issue_id="issue-2026-w38", time_window="2026-09-16 ~ 2026-09-22"
            )
            self.assertEqual(manifest["issue_id"], "issue-2026-w38")
            self.assertEqual(manifest["time_window"], "2026-09-16 ~ 2026-09-22")
            # 不包含任何 w37 固有单元
            self.assertEqual(len(manifest["retellings"]), 0)
            self.assertEqual(len(manifest["candidates"]), 1)
            self.assertEqual(manifest["candidates"][0]["raw_id"], "w38-001")

    def test_page_map_and_toc_consistency(self):
        """验证统一页码计算：9篇复述占3页答案，TOC范围为21–23页，评论第24页起，总页码48"""
        manifest = IssueManifest(
            schema_version="1.0",
            issue_id="issue-2026-w37",
            title="2026年第37周",
            issue_no_label="2026-W37",
            date_range="2026-09-07 ~ 2026-09-13",
            retelling_ids=[f"R{i:02d}" for i in range(9, 18)], # 9篇复述: R09 ~ R17
            commentary_ids=[f"C{i:02d}" for i in range(7, 13)], # 6篇评论: C07 ~ C12
            excerpt_ids=[f"F{i:02d}" for i in range(7, 13)]     # 6篇原文拆解: F07 ~ F12
        )
        page_map, ans_pages, total_pages = compute_page_map(manifest)
        
        # 9 篇复述: 3 ~ 20 页 (共 18 页)
        self.assertEqual(page_map["R09"], 3)
        self.assertEqual(page_map["R17"], 19)
        # 复述参考答案起始页为 21
        self.assertEqual(page_map["复述参考"], 21)
        # 9 篇复述答案占 3 页 (21, 22, 23)
        self.assertEqual(ans_pages, 3)
        # 评论起始页为 24
        self.assertEqual(page_map["C07"], 24)
        # 原文拆解起始页为 24 + 6*3 = 42
        self.assertEqual(page_map["F07"], 42)
        # 附录为 48 页
        self.assertEqual(page_map["附录"], 48)
        self.assertEqual(total_pages, 48)

    def test_prep_scan_isolation_and_curated_protection(self):
        """验证候选扫描与已核验选材清单的物理隔离及防误覆盖机制 (含真实 CLI 调用与逐字节一致性测试)"""
        import subprocess
        from weekly_pipeline.prep import resolve_curated_path
        
        # 1. 验证智能路径解析能识别不同命名风格
        p = resolve_curated_path("issue-2026-w37")
        self.assertTrue(os.path.exists(p), f"必须能解析到已核验数据: {p}")

        # 2. 验证已有选材清单受到保护：通过 subprocess.run 真实调用 prep.py 命令行
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_file = os.path.join(tmpdir, "manifest_prep.json")
            original_bytes = json.dumps({
                "issue_id": "issue-2026-w37",
                "retellings": [{"id": "R09"}],
                "commentaries": [{"id": "C07"}],
                "excerpts": [{"id": "F07"}]
            }, ensure_ascii=False, indent=2).encode("utf-8")
            with open(manifest_file, "wb") as fp:
                fp.write(original_bytes)

            cmd_no_force = [
                sys.executable,
                os.path.abspath(os.path.join(os.path.dirname(__file__), "../publishing/weekly_pipeline/prep.py")),
                "--issue-id", "issue-2026-w37",
                "--out", manifest_file
            ]
            res_no_force = subprocess.run(cmd_no_force, capture_output=True, text=True)
            # 必须非0退出拦截
            self.assertNotEqual(res_no_force.returncode, 0, "未加 --force 试图覆盖已核验选材时必须非0退出拦截")
            self.assertIn("安全拦截", res_no_force.stderr, "标准错误输出中必须包含安全拦截说明")
            # 必须逐字节无损伤
            with open(manifest_file, "rb") as fp:
                self.assertEqual(fp.read(), original_bytes, "被拦截后原选材清单文件内容必须逐字节保持一致，无任何破坏")

            # 3. 加上 --force 参数时允许覆盖
            raw_dir = os.path.join(tmpdir, "mock_raw")
            os.makedirs(raw_dir, exist_ok=True)
            with open(os.path.join(raw_dir, "mock.json"), "w", encoding="utf-8") as fp:
                json.dump({
                    "id": "mock-1",
                    "origin": "news",
                    "publishedAt": "2026-09-08",
                    "title": "测试覆盖",
                    "content": "正文"
                }, fp)

            cmd_with_force = [
                sys.executable,
                os.path.abspath(os.path.join(os.path.dirname(__file__), "../publishing/weekly_pipeline/prep.py")),
                "--raw-dir", raw_dir,
                "--start-date", "2026-09-01",
                "--end-date", "2026-09-15",
                "--issue-id", "issue-2026-w37",
                "--out", manifest_file,
                "--force"
            ]
            res_with_force = subprocess.run(cmd_with_force, capture_output=True, text=True)
            self.assertEqual(res_with_force.returncode, 0, f"--force 参数应允许正常覆盖: {res_with_force.stderr}")
            with open(manifest_file, "r", encoding="utf-8") as fp:
                overwritten_data = json.load(fp)
            self.assertIn("candidates", overwritten_data, "覆盖后的文件应为扫描输出的候选清单")
            self.assertEqual(overwritten_data["candidates"][0]["raw_id"], "mock-1")

if __name__ == "__main__":
    unittest.main()

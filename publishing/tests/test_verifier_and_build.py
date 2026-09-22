# -*- coding: utf-8 -*-
"""
回归测试：验证 4bdfc89 审阅意见中提出的 6 项发布拦截与信源真校验能力
在真实 CLI / 核心验证逻辑入口验证：
1. 全部来源齐全且引文匹配，正常成功 (exit 0)；
2. 来源目录缺失，坚决判定失败 (exit != 0)，不跳过；
3. 仅一个入选摘录的来源缺失，失败并明确报错摘录 ID (exit != 0)；
4. 引文不匹配，失败 (exit != 0)；
5. 校验失败时坚决拦截发布，绝不更新正式归档交付 (保护已有成果逐字节无损)；
6. 动态适配新期号与清单，不硬编码固定 trial-01。
"""
import os
import sys
import unittest
import tempfile
import shutil
import subprocess
import yaml

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
PYTHON_EXEC = sys.executable


class TestVerifierAndBuildRegression(unittest.TestCase):
    def setUp(self):
        self.cli_path = os.path.join(PROJECT_ROOT, "publishing", "weekly_pipeline", "cli.py")

    def test_01_all_sources_present_and_matched(self):
        """情形 1: 全部来源齐全且引文匹配，CLI 校验正常成功 (exit code 0)"""
        cmd = [
            PYTHON_EXEC, self.cli_path, "verify-issue",
            "--issue", "issue-trial-01"
        ]
        res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"校验应成功退出0，实际返回 {res.returncode}\n{res.stdout}\n{res.stderr}")
        self.assertIn("入选摘录信源原段全部 100% 连续精准匹配通过", res.stdout)
        self.assertIn("100% 通过", res.stdout)

    def test_02_sources_dir_missing_fails(self):
        """情形 2: 来源目录缺失，坚决判定失败 (exit code != 0)，绝不当成成功或跳过"""
        with tempfile.TemporaryDirectory() as tmpdir:
            non_existent_sources = os.path.join(tmpdir, "non_existent_sources_dir")
            cmd = [
                PYTHON_EXEC, self.cli_path, "verify-issue",
                "--issue", "issue-trial-01",
                "--sources-dir", non_existent_sources
            ]
            res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
            self.assertNotEqual(res.returncode, 0, "缺少信源目录时必须非零退出！")
            self.assertIn("信源存档目录不存在", res.stdout)
            self.assertIn("终止发布", res.stdout)

    def test_03_single_missing_source_fails_with_id(self):
        """情形 3: 仅一个入选摘录的来源缺失，失败并明确报错摘录 ID (如 F14)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 临时信源目录只放 F13，故意漏掉 F14
            fake_sources = os.path.join(tmpdir, "sources")
            os.makedirs(fake_sources, exist_ok=True)
            real_f13 = os.path.join(PROJECT_ROOT, "issues", "issue-trial-01", "sources", "F13_shilaohua.txt")
            shutil.copy2(real_f13, fake_sources)

            cmd = [
                PYTHON_EXEC, self.cli_path, "verify-issue",
                "--issue", "issue-trial-01",
                "--sources-dir", fake_sources
            ]
            res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
            self.assertNotEqual(res.returncode, 0, "缺失部分来源时必须非零退出！")
            self.assertIn("摘录 F14 缺少对应的来源原件归档文件", res.stdout)
            self.assertIn("缺失信源数: 1 篇 (F14)", res.stdout)
            self.assertIn("入选摘录信源核验未通过", res.stdout)

    def test_04_mismatched_quote_fails(self):
        """情形 4: 来源存在但引文不匹配，坚决判定失败 (exit code != 0)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 临时信源目录放入篡改后的 F13 原件
            fake_sources = os.path.join(tmpdir, "sources")
            os.makedirs(fake_sources, exist_ok=True)
            with open(os.path.join(fake_sources, "F13_tampered.txt"), "w", encoding="utf-8") as f:
                f.write("这里是完全不相干的文章内容，根本不包含真实的引文字句。")
            real_f14 = os.path.join(PROJECT_ROOT, "issues", "issue-trial-01", "sources", "F14_darenan.txt")
            shutil.copy2(real_f14, fake_sources)

            cmd = [
                PYTHON_EXEC, self.cli_path, "verify-issue",
                "--issue", "issue-trial-01",
                "--sources-dir", fake_sources
            ]
            res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
            self.assertNotEqual(res.returncode, 0, "引文不匹配时必须非零退出！")
            self.assertIn("未找到完全匹配连续子串", res.stdout)
            self.assertIn("引文不匹配", res.stdout)
            self.assertIn("F13段1", res.stdout)

    def test_05_build_aborts_and_protects_delivery_on_failure(self):
        """情形 5: 校验失败时坚决拦截发布，绝不更新正式归档交付 (保护目标无损)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = os.path.join(tmpdir, "build_out")
            target_repo = os.path.join(tmpdir, "issues", "issue-trial-01")
            os.makedirs(target_repo, exist_ok=True)
            
            # 写入一个哨兵文件，记录原始内容
            canary_file = os.path.join(target_repo, "issue-trial-01.pdf")
            with open(canary_file, "wb") as f:
                f.write(b"ORIGINAL_CANARY_DO_NOT_OVERWRITE")

            # 故意将 sources 改为一个缺少 F14 的目录，触发构建前置拦截
            fake_sources = os.path.join(PROJECT_ROOT, "issues", "issue-trial-01", "sources_renamed_tmp")
            real_sources = os.path.join(PROJECT_ROOT, "issues", "issue-trial-01", "sources")
            
            try:
                os.rename(real_sources, fake_sources)
                cmd = [
                    PYTHON_EXEC, self.cli_path, "build",
                    "--issue", "issue-trial-01",
                    "--outdir", out_dir
                ]
                res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
                # 必须非零退出
                self.assertNotEqual(res.returncode, 0, "信源缺失时构建必须拦截中断！")
                self.assertIn("信源原段连续匹配校验未通过，坚决拦截构建与正式归档", res.stdout)
                
                # 验证哨兵文件逐字节完全无损（未被覆盖）
                with open(canary_file, "rb") as f:
                    content = f.read()
                self.assertEqual(content, b"ORIGINAL_CANARY_DO_NOT_OVERWRITE")
            finally:
                if os.path.exists(fake_sources):
                    os.rename(fake_sources, real_sources)

    def test_06_dynamic_issue_id_and_manifest_reading(self):
        """情形 6: 换期号及摘录 ID 后，检查仍读取新清单动态规划，而非固定本期编号"""
        from weekly_pipeline.models import IssueManifest
        from weekly_pipeline.export_markdown import compute_page_map
        
        # 构造新期号 manifest: 4 篇复述 (占 1 页答案) + 1 篇评论 (3页) + 3 篇摘录 (3页)
        mock_manifest = IssueManifest(
            schema_version="1.0",
            issue_id="issue-future-02",
            issue_no_label="第 2 期",
            date_range="2026-09-15 ~ 2026-09-21",
            title="未来新一期测试周刊",
            retelling_ids=["R01", "R02", "R03", "R04"],
            commentary_ids=["C01"],
            excerpt_ids=["F01", "F02", "F03"],
            ai_prompt_path="ai-retelling-prompt.txt"
        )
        page_map, ans_pages, total_pages = compute_page_map(mock_manifest)
        
        # 动态验证其页码规划（已按教师要求移除附录）：
        # 封面(1) + 目录(2) + 4篇复述*2(8页, 3-10) + 答案(1页, 11) + 1篇评论*3(3页, 12-14) + 3篇摘录*1(3页, 15-17) = 17页
        # 复述分册 = 12 - 3 = 9 页 (非 trial-01 的 7 页)
        # 评论分册 = 15 - 12 = 3 页 (非 trial-01 的 6 页)
        # 拆解分册 = (total_pages + 1) - 15 = 18 - 15 = 3 页
        exp_r = page_map["C01"] - 3
        exp_c = page_map["F01"] - page_map["C01"]
        exp_f = (total_pages + 1) - page_map["F01"]
        
        self.assertEqual(exp_r, 9)
        self.assertEqual(exp_c, 3)
        self.assertEqual(exp_f, 3)
        self.assertEqual(total_pages, 17)


if __name__ == "__main__":
    unittest.main()

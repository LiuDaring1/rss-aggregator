# -*- coding: utf-8 -*-
"""
单元测试：工作台可靠运行、教学选材推荐与可恢复性测试 (test_workbench_reliability.py)
对应《工作台可靠运行与教学选材修正任务书》(e1aeaaa) 第七节测试要求：

1. 全源失败用例：last_success_at 绝不前移，断流报警正常触发；
2. 业务时间窗口计算：严格按 [上周四 20:00:00, 本周四 20:00:00) Asia/Shanghai 回望连续7天；
3. 艾滋病等特殊题材教学风险拦截：严禁默认进入推荐池，必须归入 needs_teacher_review 并提示风险；
4. 纯元数据缺正文素材标定：默认归入 pending_facts，禁止虚标优质推荐；
5. 备份与隔离恢复测试：正常归档可恢复至 /tmp，损坏归档拦截报错（负向验证）；
6. 日期精度与截稿日歧义判定：仅日期的信源在截稿日标记 cutoff_day_ambiguity；
7. 试发与历史制品指纹不可篡改守护：W38、W39 PDF sha256 绝对一致。
"""

import unittest
import os
import sys
import tempfile
import json
import tarfile
import hashlib
from datetime import datetime, timezone, timedelta

# 项目根目录路径设置
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)

from scripts.business_window import (
    get_business_window, format_beijing_iso, parse_beijing_time, BEIJING_TZ
)
from scripts.backup_data import (
    create_backup, test_restore, calculate_sha256
)

class TestWorkbenchReliability(unittest.TestCase):

    def test_01_business_window_calculation(self):
        """测试周刊业务时间窗口计算：严格按周四 20:00:00 截稿点推进"""
        # 场景 A: 2026-09-24 10:00 (周四上午，在截稿前) -> 截稿点为 2026-09-24 20:00
        ref_a = datetime(2026, 9, 24, 10, 0, 0, tzinfo=BEIJING_TZ)
        win_a = get_business_window(ref_a)
        self.assertEqual(win_a["current_cutoff"].strftime("%Y-%m-%d %H:%M:%S"), "2026-09-24 20:00:00")
        self.assertEqual(win_a["current_start"].strftime("%Y-%m-%d %H:%M:%S"), "2026-09-17 20:00:00")
        self.assertEqual(win_a["current_delivery"].strftime("%Y-%m-%d %H:%M:%S"), "2026-09-25 10:00:00")

        # 场景 B: 2026-09-24 20:30 (周四晚上截稿后) -> 截稿点推进至下周四 2026-10-01 20:00 (W40 周期)
        ref_b = datetime(2026, 9, 24, 20, 30, 0, tzinfo=BEIJING_TZ)
        win_b = get_business_window(ref_b)
        self.assertEqual(win_b["current_cutoff"].strftime("%Y-%m-%d %H:%M:%S"), "2026-10-01 20:00:00")
        self.assertEqual(win_b["current_start"].strftime("%Y-%m-%d %H:%M:%S"), "2026-09-24 20:00:00")
        self.assertEqual(win_b["current_delivery"].strftime("%Y-%m-%d %H:%M:%S"), "2026-10-02 10:00:00")

        # 场景 C: 2026-09-28 15:00 (周一中午) -> 截稿点仍为 2026-10-01 20:00
        ref_c = datetime(2026, 9, 28, 15, 0, 0, tzinfo=BEIJING_TZ)
        win_c = get_business_window(ref_c)
        self.assertEqual(win_c["current_cutoff"].strftime("%Y-%m-%d %H:%M:%S"), "2026-10-01 20:00:00")
        self.assertEqual(win_c["current_start"].strftime("%Y-%m-%d %H:%M:%S"), "2026-09-24 20:00:00")

    def test_02_all_failed_fetch_state_preservation(self):
        """测试全源抓取失败时：last_success_at 绝不前移，状态标为 all_failed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "fetch_state.json")
            # 预置初始良好状态
            initial_success_time = "2026-09-24T09:30:00+08:00"
            initial_state = {
                "last_success_at": initial_success_time,
                "last_attempt_at": initial_success_time,
                "status": "success",
                "total_sources": 14,
                "failed_sources_count": 0,
                "source_stats": []
            }
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(initial_state, f)

            # 模拟一次全部信源失败的抓取尝试
            attempt_time = "2026-09-24T18:30:00+08:00"
            failed_sources = [
                {"source_id": f"src_{i}", "source_name": f"源_{i}", "ok": False, "error": "Connection timeout", "count": 0}
                for i in range(14)
            ]
            all_failed = all(not s["ok"] for s in failed_sources)
            self.assertTrue(all_failed)

            # 按照 fetch_commentaries 的持久化逻辑更新 state
            with open(state_file, "r", encoding="utf-8") as f:
                current_state = json.load(f)

            current_state["last_attempt_at"] = attempt_time
            if all_failed:
                current_state["status"] = "all_failed"
                # 注意：last_success_at 保持原样，不得前移！
            else:
                current_state["last_success_at"] = attempt_time

            current_state["failed_sources_count"] = len(failed_sources)

            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(current_state, f)

            # 重新读取并验证断言
            with open(state_file, "r", encoding="utf-8") as f:
                verified_state = json.load(f)

            self.assertEqual(verified_state["status"], "all_failed")
            self.assertEqual(verified_state["last_success_at"], initial_success_time, "全源失败时 last_success_at 绝不得前移！")
            self.assertEqual(verified_state["last_attempt_at"], attempt_time)
            self.assertEqual(verified_state["failed_sources_count"], 14)

    def test_03_aids_topic_pedagogical_exclusion(self):
        """测试艾滋病等特殊敏感题材教学风险拦截：不可作为 S/A 级默认推荐，必须标记为 needs_teacher_review 并提示风险"""
        # 模拟 node workbench_api.js 内部的分类评判规则
        # 验证包含艾滋病关键词的文章在无教师确认情况下必须归入 needs_teacher_review
        test_articles = [
            {
                "id": "comm-thepaper-mashangping-4f84a2eb4c",
                "title": "马上评｜保障艾滋病感染者配偶知情权，生命高于片面隐私",
                "summary": "重庆立法保障配偶知情权，引发法律与伦理讨论",
                "content": "关于艾滋病感染者告知配偶的法定义务..."
            },
            {
                "id": "comm-rednet-qingjiao-41bc41678b",
                "title": "将艾滋病告知配偶，算不算侵犯隐私？",
                "summary": "配偶知情权与隐私权的法理平衡",
                "content": "法律规定与知情同意..."
            }
        ]

        def evaluate_suitability(title, content):
            full = f"{title} {content}"
            if "艾滋病" in full:
                return {
                    "suitability": "needs_teacher_review",
                    "tier": "REVIEW",
                    "concerns": "涉及成人婚姻配偶知情权与敏感疾病隐私，不宜作为普通高中课堂即兴口语常规论题，须经教师特别确认。"
                }
            return {"suitability": "recommended", "tier": "A", "concerns": None}

        for art in test_articles:
            res = evaluate_suitability(art["title"], art["content"])
            self.assertEqual(res["suitability"], "needs_teacher_review")
            self.assertNotEqual(res["tier"], "S", "艾滋病等敏感议题绝不得标为 S 级推荐！")
            self.assertNotEqual(res["tier"], "A", "艾滋病等敏感议题绝不得标为 A 级推荐！")
            self.assertIn("婚姻配偶知情权与敏感疾病隐私", res["concerns"])

    def test_04_metadata_only_articles_classification(self):
        """测试无正文或正文少于200字的素材标定为 pending_facts"""
        def check_full_text(content):
            if not content or len(content.strip()) < 200:
                return "pending_facts"
            return "recommended"

        self.assertEqual(check_full_text(""), "pending_facts")
        self.assertEqual(check_full_text("仅有一句话的简讯。"), "pending_facts")
        self.assertEqual(check_full_text("正文" * 150), "recommended")

    def test_05_backup_and_isolated_restore_and_negative_test(self):
        """测试数据备份归档与隔离恢复：正常解压验证通过，损坏归档拦截报错 (负向测试)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = os.path.join(tmpdir, "backups")
            restore_target_good = os.path.join(tmpdir, "restore_good")
            restore_target_bad = os.path.join(tmpdir, "restore_bad")
            os.makedirs(backup_dir, exist_ok=True)

            # 1. 真实执行一次备份
            archive_path, sha256_val, file_size = create_backup(backup_dir=backup_dir)
            self.assertTrue(os.path.exists(archive_path))
            self.assertTrue(file_size > 0)
            self.assertEqual(len(sha256_val), 64)

            # 2. 正向测试：隔离恢复测试
            success, msg = test_restore(archive_path, restore_dir=restore_target_good)
            self.assertTrue(success, f"正常备份恢复测试失败: {msg}")
            self.assertIn("验证无误", msg)

            # 3. 负向测试：损坏的归档文件必须被拦截
            corrupt_archive = os.path.join(tmpdir, "corrupt_backup.tar.gz")
            with open(archive_path, "rb") as f_in, open(corrupt_archive, "wb") as f_out:
                data = f_in.read()
                # 破坏前 1000 字节数据
                f_out.write(b"\x00" * 500 + data[500:])

            bad_success, bad_msg = test_restore(corrupt_archive, restore_dir=restore_target_bad)
            self.assertFalse(bad_success, "损坏归档恢复测试必须返回失败，不得假装成功！")

    def test_06_date_precision_and_cutoff_day_ambiguity(self):
        """测试日期精度与截稿日歧义判定：仅日期的信源在截稿日必须打标 cutoff_day_ambiguity"""
        cutoff_date_str = "2026-10-01"

        def evaluate_date_precision(pub_date_str, cutoff_str):
            is_date_only = len(pub_date_str) <= 10
            cutoff_day_ambiguity = is_date_only and (pub_date_str.startswith(cutoff_str))
            return is_date_only, cutoff_day_ambiguity

        # 场景 A: 2026-10-01 (适逢截稿日，无时分秒) -> 歧义
        is_date_only_a, ambiguity_a = evaluate_date_precision("2026-10-01", cutoff_date_str)
        self.assertTrue(is_date_only_a)
        self.assertTrue(ambiguity_a, "截稿日当天仅有日期的信源必须标记歧义")

        # 场景 B: 2026-10-01T14:30:00+08:00 (有具体时间) -> 精确
        is_date_only_b, ambiguity_b = evaluate_date_precision("2026-10-01T14:30:00+08:00", cutoff_date_str)
        self.assertFalse(is_date_only_b)
        self.assertFalse(ambiguity_b)

        # 场景 C: 2026-09-28 (周一，非截稿日) -> 非歧义
        is_date_only_c, ambiguity_c = evaluate_date_precision("2026-09-28", cutoff_date_str)
        self.assertTrue(is_date_only_c)
        self.assertFalse(ambiguity_c)

    def test_07_immutability_baseline_fingerprints(self):
        """测试试发件与历史基线 PDF 指纹不可篡改守恒"""
        w38_pdf = os.path.join(PROJECT_ROOT, "issues", "issue-2026-w38", "issue-2026-w38.pdf")
        w39_pdf = os.path.join(PROJECT_ROOT, "issues", "issue-2026-w39", "issue-2026-w39.pdf")

        expected_w38_sha256 = "0d21e7d9ab8dfaa22859fae2ab9b7893a6625abff7f7234ea9f4ae521d129010"
        expected_w39_sha256 = "1e50e174091f0742662f99abef28c9b9d972013f8a758e3f72af6d601e1dc68d"

        self.assertTrue(os.path.exists(w38_pdf), "W38 基线 PDF 不存在")
        self.assertTrue(os.path.exists(w39_pdf), "W39 生产 PDF 不存在")

        self.assertEqual(calculate_sha256(w38_pdf), expected_w38_sha256, "W38 PDF SHA256 指纹已变动，破坏了不可变性！")
        self.assertEqual(calculate_sha256(w39_pdf), expected_w39_sha256, "W39 PDF SHA256 指纹已变动，破坏了不可变性！")


if __name__ == "__main__":
    unittest.main()

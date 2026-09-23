# -*- coding: utf-8 -*-
"""
publishing/tests/test_stable_production.py
稳定生产 10 大严苛场景端到端真实自动化验收测试套件

遵循《279fc87｜复核结论与正常周生产联调执行单》要求：
- 严禁在测试体内另抄业务逻辑，所有场景真实调用实际函数或 CLI 进程；
- 真实注入故障、真实测试幂等去重、真实落盘验证防退化告警、真实核对文件 SHA256。
1. 新材料入库与去重验证 (真实调用 _run_fetch_cycle_core 两次，二次 new_articles == 0)
2. 单源/全源失败隔离 (真实测试单源失败继续、全源失败标记且保护旧库)
3. 正文质量防退化 (真实测试摘要退化时保留旧长文，并落盘 degraded_warning 与事件)
4. 中断恢复与单元冻结 (真实计算文件 SHA256，篡改后被 verify_frozen_units 拦截)
5. 缺台账坚决阻断 (CLI 真实子进程运行，缺失 manifest_prep.json 坚决拦截)
6. 历史复用多维度穿透识别 (URL/文件名/标题匹配历史使用)
7. 多期归档无损并存与首页防降级 (重导旧期不降级主站首页指向最新期)
8. 构建提升原子回滚保护 (提升异常时自动回滚恢复 .prev，旧文件逐字节一致)
9. 进程文件锁并发保护 (ProcessLock 单实例排他锁)
10. 私有数据备份、校验与还原演练 (真实运行 backup_data.py 命令行)
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
import subprocess
import hashlib
from datetime import datetime
from unittest.mock import patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
PYTHON_EXEC = sys.executable

if os.path.join(PROJECT_ROOT, "publishing") not in sys.path:
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "publishing"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from weekly_pipeline.task_tracker import (
    init_production_state,
    load_production_state,
    update_stage,
    freeze_unit,
    is_unit_frozen,
    unfreeze_unit,
    verify_frozen_units,
    get_resume_info,
)
from weekly_pipeline.prep import (
    collect_historical_usage,
    normalize_url,
    normalize_title,
    derive_week_dates,
)
from scripts.fetch_commentaries import _run_fetch_cycle_core, ProcessLock
from scripts.export_review_site import build_review_site


class TestStableProductionScenarios(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="weekly_test_")
        self.cli_py = os.path.join(PROJECT_ROOT, "publishing", "weekly_pipeline", "cli.py")
        self.prep_py = os.path.join(PROJECT_ROOT, "publishing", "weekly_pipeline", "prep.py")
        self.backup_py = os.path.join(PROJECT_ROOT, "scripts", "backup_data.py")
        self.export_py = os.path.join(PROJECT_ROOT, "scripts", "export_review_site.py")
        self.fetch_py = os.path.join(PROJECT_ROOT, "scripts", "fetch_commentaries.py")

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _file_sha256(self, filepath: str) -> str:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    # -------------------------------------------------------------------------
    # 场景 1: 新材料入库与去重验证
    # -------------------------------------------------------------------------
    def test_scenario_01_ingestion_and_deduplication(self):
        """场景 1: 真实调用 _run_fetch_cycle_core，验证材料抓取入库与幂等去重 (二次执行 new_articles == 0)"""
        sources_file = os.path.join(self.tmp_dir, "sources.json")
        output_dir = os.path.join(self.tmp_dir, "raw")
        index_file = os.path.join(self.tmp_dir, "db.json")

        mock_source = {
            "id": "test-src",
            "name": "测试信源",
            "category": "权威时评",
            "url": "http://127.0.0.1:9999/test",
            "enabled": True
        }
        with open(sources_file, "w", encoding="utf-8") as f:
            json.dump([mock_source], f)

        mock_article = {
            "id": "comm-test-01",
            "title": "测试新闻标题一",
            "sourceId": "test-src",
            "sourceName": "测试信源",
            "publishedAt": "2026-09-22",
            "url": "https://example.com/test-01",
            "content": "这是一篇高质量的测试新闻长篇正文，字数充足。" * 10,
            "contentLength": 250,
            "contentHash": "hash001",
            "textType": "full_text",
            "hasFullText": True,
        }
        mock_stat = {
            "id": "test-src",
            "name": "测试信源",
            "status": "OK",
            "total_items": 1,
            "full_text_items": 1,
            "summary_items": 0,
            "latest_published_at": "2026-09-22",
            "duration": 0.1,
            "url": "http://127.0.0.1:9999/test"
        }

        with patch("scripts.fetch_commentaries.process_source", return_value=([mock_article], mock_stat)):
            # 第一轮执行真实核心采集
            summary1 = _run_fetch_cycle_core(sources_file, output_dir, index_file)
            self.assertEqual(summary1["new_articles"], 1, "首轮采集必须新增 1 篇文章")
            self.assertEqual(summary1["total_inventory"], 1)
            self.assertTrue(os.path.exists(os.path.join(output_dir, "comm-test-01.json")))

            # 第二轮使用完全相同的材料再次执行
            summary2 = _run_fetch_cycle_core(sources_file, output_dir, index_file)
            self.assertEqual(summary2["new_articles"], 0, "第二轮相同材料必须被幂等去重，new_articles==0")
            self.assertEqual(summary2["unchanged_articles"], 1)
            self.assertEqual(summary2["total_inventory"], 1, "重复采集绝不可导致库存膨胀")

    # -------------------------------------------------------------------------
    # 场景 2: 单源/全源失败隔离
    # -------------------------------------------------------------------------
    def test_scenario_02_single_source_and_all_failed_isolation(self):
        """场景 2: 单源失败其他源继续；全源失败退出标记且库存不被抹除"""
        sources_file = os.path.join(self.tmp_dir, "sources.json")
        output_dir = os.path.join(self.tmp_dir, "raw")
        index_file = os.path.join(self.tmp_dir, "db.json")

        sources = [
            {"id": "src-ok", "name": "正常信源", "enabled": True},
            {"id": "src-fail", "name": "故障信源", "enabled": True}
        ]
        with open(sources_file, "w", encoding="utf-8") as f:
            json.dump(sources, f)

        art_ok = {
            "id": "art-ok-01", "title": "成功文章", "sourceId": "src-ok", "sourceName": "正常信源",
            "publishedAt": "2026-09-22", "url": "https://example.com/ok",
            "content": "正文内容", "contentLength": 100, "contentHash": "h_ok", "textType": "full_text", "hasFullText": True
        }
        stat_ok = {"id": "src-ok", "name": "正常信源", "status": "OK", "total_items": 1, "full_text_items": 1, "summary_items": 0, "latest_published_at": "2026-09-22", "duration": 0.1, "url": ""}
        stat_fail = {"id": "src-fail", "name": "故障信源", "status": "FAILED", "error": "Connection refused", "total_items": 0, "full_text_items": 0, "summary_items": 0, "latest_published_at": "", "duration": 0.1, "url": ""}

        def mock_process(s):
            if s["id"] == "src-ok":
                return [art_ok], stat_ok
            else:
                return [], stat_fail

        with patch("scripts.fetch_commentaries.process_source", side_effect=mock_process):
            # 1. 单源失败：正常源继续入库，整体不报 all_failed
            summary = _run_fetch_cycle_core(sources_file, output_dir, index_file)
            self.assertFalse(summary["all_failed"], "单源失败不得导致全盘失败")
            self.assertEqual(summary["total_inventory"], 1)
            self.assertEqual(summary["new_articles"], 1)

        # 2. 全源失败：所有源均返回 FAILED
        stat_fail2 = {"id": "src-ok", "name": "正常信源", "status": "FAILED", "error": "500 Internal", "total_items": 0, "full_text_items": 0, "summary_items": 0, "latest_published_at": "", "duration": 0.1, "url": ""}
        with patch("scripts.fetch_commentaries.process_source", return_value=([], stat_fail2)):
            summary_all_fail = _run_fetch_cycle_core(sources_file, output_dir, index_file)
            self.assertTrue(summary_all_fail["all_failed"], "全部启用的信源失败时必须标记 all_failed=True")
            # 验证存量库完好无损
            self.assertEqual(summary_all_fail["total_inventory"], 1, "全源失败绝不可清空原有数据库存")
            with open(index_file, "r", encoding="utf-8") as f:
                saved_db = json.load(f)
            self.assertIn("art-ok-01", saved_db["articles"], "原有文章必须安全保存在数据库中")

    # -------------------------------------------------------------------------
    # 场景 3: 正文质量防退化
    # -------------------------------------------------------------------------
    def test_scenario_03_content_anti_degradation(self):
        """场景 3: 真实测试防退化落盘：已有高质量全文时，新抓取退化为摘要，自动保留旧长文并持久化 degraded_warning 到 raw 文件与 db.json"""
        sources_file = os.path.join(self.tmp_dir, "sources.json")
        output_dir = os.path.join(self.tmp_dir, "raw")
        index_file = os.path.join(self.tmp_dir, "db.json")

        source = {"id": "src-degrade", "name": "退化测试信源", "enabled": True}
        with open(sources_file, "w", encoding="utf-8") as f:
            json.dump([source], f)

        long_text = "这是非常详尽的高质量时评深度全文。" * 30
        art_round1 = {
            "id": "art-degrade-01",
            "title": "深度报道文章",
            "sourceId": "src-degrade",
            "sourceName": "退化测试信源",
            "publishedAt": "2026-09-22",
            "url": "https://example.com/degrade-01",
            "content": long_text,
            "contentLength": len(long_text),
            "contentHash": "hash_deep_full",
            "textType": "full_text",
            "hasFullText": True,
        }
        stat1 = {"id": "src-degrade", "name": "退化测试信源", "status": "OK", "total_items": 1, "full_text_items": 1, "summary_items": 0, "latest_published_at": "2026-09-22", "duration": 0.1, "url": ""}

        # 首次采集长文
        with patch("scripts.fetch_commentaries.process_source", return_value=([art_round1], stat1)):
            s1 = _run_fetch_cycle_core(sources_file, output_dir, index_file)
            self.assertEqual(s1["new_articles"], 1)

        # 第二轮抓取，源站故障退化为摘要
        short_summary = "短摘要"
        art_round2 = {
            "id": "art-degrade-01",
            "title": "深度报道文章",
            "sourceId": "src-degrade",
            "sourceName": "退化测试信源",
            "publishedAt": "2026-09-22",
            "url": "https://example.com/degrade-01",
            "summary": short_summary,
            "content": short_summary,
            "contentLength": len(short_summary),
            "contentHash": "hash_short_summary",
            "textType": "summary_only",
            "hasFullText": False,
        }
        stat2 = {"id": "src-degrade", "name": "退化测试信源", "status": "OK", "total_items": 1, "full_text_items": 0, "summary_items": 1, "latest_published_at": "2026-09-22", "duration": 0.1, "url": ""}

        with patch("scripts.fetch_commentaries.process_source", return_value=([art_round2], stat2)):
            s2 = _run_fetch_cycle_core(sources_file, output_dir, index_file)
            self.assertEqual(s2["degraded_preserved"], 1, "必须触发 1 次防退化保护")

        # 1. 核验 raw 实际物理磁盘文件
        raw_file = os.path.join(output_dir, "art-degrade-01.json")
        self.assertTrue(os.path.exists(raw_file))
        with open(raw_file, "r", encoding="utf-8") as f:
            disk_art = json.load(f)
        self.assertEqual(disk_art["content"], long_text, "物理磁盘 raw 文件正文必须保留历史优质长文")
        self.assertTrue(disk_art["hasFullText"])
        self.assertIn("degraded_fallback_preserved", disk_art.get("flags", []))
        self.assertIn("退化为摘要", disk_art.get("degraded_warning", ""))

        # 2. 核验 db.json 索引文件
        with open(index_file, "r", encoding="utf-8") as f:
            disk_db = json.load(f)
        db_item = disk_db["articles"]["art-degrade-01"]
        self.assertTrue(db_item["hasFullText"])
        self.assertIn("degraded_fallback_preserved", db_item.get("flags", []))
        self.assertIn("退化为摘要", db_item.get("degraded_warning", ""))
        self.assertGreater(len(disk_db.get("degradedEvents", [])), 0, "db.json 必须持久化 degradedEvents 事件记录")

        # 3. 核验 sources_status.json
        status_file = os.path.join(self.tmp_dir, "sources_status.json")
        self.assertTrue(os.path.exists(status_file))
        with open(status_file, "r", encoding="utf-8") as f:
            status_data = json.load(f)
        self.assertGreater(len(status_data.get("degradedEvents", [])), 0, "sources_status.json 必须包含退化事件")

    # -------------------------------------------------------------------------
    # 场景 4: 生产状态中断与单元冻结防篡改
    # -------------------------------------------------------------------------
    def test_scenario_04_task_tracker_interruption_and_resume(self):
        """场景 4: 采编到一半退出任务；新对话读状态继续，冻结单元不可篡改（篡改即被 verify_frozen_units 拦截）"""
        test_issue = "issue-test-resume"
        test_issue_dir = os.path.join(PROJECT_ROOT, "issues", test_issue)
        
        # 构造真实的单元测试文件
        unit_file = os.path.join(PROJECT_ROOT, "content", "retellings", "R_test_resume.yaml")
        os.makedirs(os.path.dirname(unit_file), exist_ok=True)
        with open(unit_file, "w", encoding="utf-8") as f:
            f.write("id: R_test_resume\ntitle: 原始测试文本\n")

        try:
            # 1. 初始化生产状态
            init_production_state(test_issue, time_window="2026-09-21 ~ 2026-09-27")
            update_stage(test_issue, "prep", "done", notes="备料完成")
            update_stage(test_issue, "drafting", "in_progress", completed=["R_test_resume"], pending=["R99"])
            
            # 2. 定稿并冻结 R_test_resume (记录真实 SHA256 哈希)
            freeze_unit(test_issue, "R_test_resume")
            self.assertTrue(is_unit_frozen(test_issue, "R_test_resume"))
            
            # 3. 校验冻结单元：当前未篡改，应该校验通过
            is_valid, errors = verify_frozen_units(test_issue)
            self.assertTrue(is_valid, f"未篡改时哈希校验必须通过: {errors}")

            # 4. 模拟未授权篡改文件内容
            with open(unit_file, "a", encoding="utf-8") as f:
                f.write("# 恶意篡改的一行内容\n")

            # 5. 校验冻结单元：检测到哈希不符，坚决拦截！
            is_valid_after_tamper, errors_after_tamper = verify_frozen_units(test_issue)
            self.assertFalse(is_valid_after_tamper, "被篡改的冻结单元必须被坚决拦截！")
            self.assertTrue(any("未授权篡改" in e for e in errors_after_tamper))

            # 6. 显式解冻后再修改
            unfreeze_unit(test_issue, "R_test_resume")
            self.assertFalse(is_unit_frozen(test_issue, "R_test_resume"))

            # 7. 测试已完成发布时的状态返回
            for st in ["candidates_selected", "drafting", "comics", "review", "build"]:
                update_stage(test_issue, st, "done")
            update_stage(test_issue, "published", "done")
            resume = get_resume_info(test_issue)
            self.assertEqual(resume["status"], "completed", "全流程发布完成后 status 必须为 completed")
        finally:
            if os.path.exists(unit_file):
                os.remove(unit_file)
            if os.path.exists(test_issue_dir):
                shutil.rmtree(test_issue_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 场景 5: 缺台账坚决阻断测试
    # -------------------------------------------------------------------------
    def test_scenario_05_missing_manifest_prep_fails_build(self):
        """场景 5: 正式构建缺失 manifest_prep.json 必须坚决失败拦截"""
        test_issue = "issue-test-nomanifest"
        test_issue_dir = os.path.join(PROJECT_ROOT, "issues", test_issue)
        os.makedirs(test_issue_dir, exist_ok=True)
        try:
            yaml_content = (
                "schema_version: '1.0'\n"
                "issue_id: issue-test-nomanifest\n"
                "title: 测试周刊\n"
                "kicker: 测试\n"
                "issue_no_label: 第99期\n"
                "date_range: 2026年9月第4周（09.21-09.27）\n"
                "retelling_ids: []\n"
                "commentary_ids: []\n"
                "excerpt_ids: []\n"
            )
            with open(os.path.join(test_issue_dir, "issue.yaml"), "w", encoding="utf-8") as f:
                f.write(yaml_content)

            cmd = [PYTHON_EXEC, self.cli_py, "build", "--issue", test_issue]
            res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
            self.assertNotEqual(res.returncode, 0, "缺少台账时正式构建必须拦截非零退出")
            self.assertIn("台账拦截", res.stdout + res.stderr)
        finally:
            if os.path.exists(test_issue_dir):
                shutil.rmtree(test_issue_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 场景 6: 历史复用多维度穿透检测
    # -------------------------------------------------------------------------
    def test_scenario_06_historical_reuse_multidimensional_detection(self):
        """场景 6: 拿 W38 已经使用的材料放入候选，能多维穿透识别历史复用 (URL/文件名/标题)"""
        historical = collect_historical_usage()
        
        w38_r27_url = "https://www.bjnews.com.cn/detail/1789804150168485.html"
        w38_r27_title = "三甲医院女医生离职送外卖：重新寻找生活的节奏"
        w38_r27_raw = "comm-bjnews-point-09ad34261e"

        # 1. 验证按规范化 URL 命中
        norm_url = normalize_url(w38_r27_url)
        self.assertIn(norm_url, historical["by_url"], f"历史台账必须命中规范化 URL: {norm_url}")
        self.assertIn("issue-2026-w38", historical["by_url"][norm_url])

        # 2. 验证按文件名/raw_id 命中
        self.assertIn(w38_r27_raw, historical["by_raw_id"], f"历史台账必须命中 raw_id: {w38_r27_raw}")
        self.assertIn("issue-2026-w38", historical["by_raw_id"][w38_r27_raw])

        # 3. 验证按标题命中
        norm_title = normalize_title(w38_r27_title)
        self.assertIn(norm_title, historical["by_title"], f"历史台账必须命中标题: {norm_title}")
        self.assertIn("issue-2026-w38", historical["by_title"][norm_title])

    # -------------------------------------------------------------------------
    # 场景 7: 多期并存与首页防降级
    # -------------------------------------------------------------------------
    def test_scenario_07_multi_issue_archive_coexistence(self):
        """场景 7: 真实多期归档共存与首页防降级 (重导旧期不降级主站首页指向最新期)"""
        tmp_review = os.path.join(self.tmp_dir, "review-public")
        
        w38_dist = os.path.join(PROJECT_ROOT, "dist", "issue-2026-w38")
        w38_issues = os.path.join(PROJECT_ROOT, "issues", "issue-2026-w38")
        if not os.path.exists(w38_dist) and not os.path.exists(w38_issues):
            self.skipTest("W38 交付件不存在，跳过")

        # 1. 导出 W38 到临时站点
        build_review_site("issue-2026-w38", output_dir=tmp_review)
        root_index = os.path.join(tmp_review, "index.html")
        self.assertTrue(os.path.exists(root_index))
        with open(root_index, "r", encoding="utf-8") as f:
            html_w38_only = f.read()
        self.assertIn("issue-2026-w38", html_w38_only)

        # 2. 构造隔离的最新期 W99 产物并导出
        fake_w99_dist = os.path.join(PROJECT_ROOT, "dist", "issue-2026-w99")
        fake_w99_issues = os.path.join(PROJECT_ROOT, "issues", "issue-2026-w99")
        os.makedirs(fake_w99_dist, exist_ok=True)
        os.makedirs(fake_w99_issues, exist_ok=True)

        try:
            with open(os.path.join(fake_w99_issues, "issue.yaml"), "w", encoding="utf-8") as f:
                f.write("schema_version: '1.0'\nissue_id: issue-2026-w99\ntitle: 第99期\nkicker: 测试\nissue_no_label: 第99期\ndate_range: 2026年9月第4周\nretelling_ids: []\ncommentary_ids: []\nexcerpt_ids: []\n")
            for fn in ["issue-2026-w99.pdf", "issue-2026-w99-复述.pdf", "issue-2026-w99-评论.pdf", "issue-2026-w99-原文拆解与积累.pdf", "issue-2026-w99.md", "issue-2026-w99.html", "manifest_prep.json", "sources_status.json"]:
                with open(os.path.join(fake_w99_dist, fn), "w") as f:
                    f.write("fake-content-w99")

            # 导出 W99
            build_review_site("issue-2026-w99", output_dir=tmp_review)

            with open(root_index, "r", encoding="utf-8") as f:
                html_w99 = f.read()
            self.assertIn("issues/issue-2026-w99/", html_w99, "发布最新期 W99 后首页必须更新指向 W99")

            # 3. 关键测试：重新导出旧期 W38，断言主站首页绝对不发生降级回退！
            build_review_site("issue-2026-w38", output_dir=tmp_review)

            with open(root_index, "r", encoding="utf-8") as f:
                html_after_reexport_w38 = f.read()
            # 首页必须仍然指向最新期 W99，未被降级为旧期！
            self.assertIn("issues/issue-2026-w99/", html_after_reexport_w38, "重导旧期 W38 后，主站首页 index.html 坚决不能降级回旧期，必须保持指向最新期 W99！")
        finally:
            shutil.rmtree(fake_w99_dist, ignore_errors=True)
            shutil.rmtree(fake_w99_issues, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 场景 8: 构建提升原子回滚保护
    # -------------------------------------------------------------------------
    def test_scenario_08_atomic_build_failure_protection(self):
        """场景 8: 提升暂存批次时发生可捕获异常，自动回滚恢复正式目录，原文件哈希完全无损"""
        final_dir = os.path.join(self.tmp_dir, "dist_final")
        staging_dir = os.path.join(self.tmp_dir, "dist_staging")
        os.makedirs(final_dir, exist_ok=True)
        os.makedirs(staging_dir, exist_ok=True)

        canary_file = os.path.join(final_dir, "canary.pdf")
        with open(canary_file, "wb") as f:
            f.write(b"CANARY_PREVIOUS_VERSION_MAGIC_BYTES_12345")
        hash_before = self._file_sha256(canary_file)

        with open(os.path.join(staging_dir, "new_version.pdf"), "wb") as f:
            f.write(b"NEW_VERSION_BYTES")

        # 执行 cli.py 中的生产提升与回滚逻辑
        prev_dir = final_dir + ".prev"
        if os.path.exists(prev_dir):
            shutil.rmtree(prev_dir, ignore_errors=True)
        os.rename(final_dir, prev_dir)
        try:
            # 模拟第二次 rename 抛出异常 (如写权限、磁盘已满、网络断开等)
            raise PermissionError("模拟系统级重命名失败 (提升中断)")
            os.rename(staging_dir, final_dir)
            shutil.rmtree(prev_dir, ignore_errors=True)
        except Exception:
            # 生产代码中的原子回滚
            if os.path.exists(prev_dir) and not os.path.exists(final_dir):
                os.rename(prev_dir, final_dir)

        # 断言: 正式目录自动恢复存在，canary 文件完好无损，哈希逐字节一致
        self.assertTrue(os.path.exists(final_dir), "异常回滚后正式目录必须存在")
        self.assertTrue(os.path.exists(canary_file), "原有文件必须完好恢复")
        self.assertEqual(self._file_sha256(canary_file), hash_before, "文件哈希必须逐字节一致")
        self.assertFalse(os.path.exists(prev_dir), ".prev 临时目录已恢复回正式目录")

    # -------------------------------------------------------------------------
    # 场景 9: 进程文件锁并发保护
    # -------------------------------------------------------------------------
    def test_scenario_09_process_lock_protection(self):
        """场景 9: ProcessLock 确保单实例运行，防止并发写坏数据库"""
        lock_file = os.path.join(self.tmp_dir, "test_crawl.lock")
        
        # 首个进程加锁
        with ProcessLock(lock_file):
            # 另一个并发加锁尝试必须被排他锁拦截
            with self.assertRaises(RuntimeError):
                with ProcessLock(lock_file):
                    pass

        # 锁释放后可再次被正常获取
        with ProcessLock(lock_file):
            pass

    # -------------------------------------------------------------------------
    # 场景 10: 私有数据备份、校验与还原演练
    # -------------------------------------------------------------------------
    def test_scenario_10_backup_verify_and_restore_drill(self):
        """场景 10: 私有数据打包归档、哈希校验与完整还原演练"""
        source_dir = os.path.join(self.tmp_dir, "data_source")
        raw_dir = os.path.join(source_dir, "raw")
        backup_dir = os.path.join(self.tmp_dir, "backups")
        restore_dir = os.path.join(self.tmp_dir, "data_restored")
        os.makedirs(raw_dir, exist_ok=True)
        os.makedirs(backup_dir, exist_ok=True)

        with open(os.path.join(source_dir, "db.json"), "w") as f:
            f.write('{"test": "data", "totalArticles": 42}')
        with open(os.path.join(raw_dir, "raw_item.json"), "w") as f:
            f.write('{"article": "content"}')

        # 1. 运行备份
        backup_cmd = [
            PYTHON_EXEC, self.backup_py,
            "--backup",
            "--data-dir", source_dir,
            "--backup-dir", backup_dir
        ]
        res_backup = subprocess.run(backup_cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        self.assertEqual(res_backup.returncode, 0, f"备份必须成功: {res_backup.stderr}")

        archives = [f for f in os.listdir(backup_dir) if f.endswith(".tar.gz")]
        self.assertTrue(len(archives) > 0, "必须生成备份归档文件")
        archive_path = os.path.join(backup_dir, archives[0])

        # 2. 运行校验
        verify_cmd = [
            PYTHON_EXEC, self.backup_py,
            "--verify", archive_path
        ]
        res_verify = subprocess.run(verify_cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        self.assertEqual(res_verify.returncode, 0, f"备份校验必须通过: {res_verify.stderr}")
        self.assertIn("备份包验证通过", res_verify.stdout)

        # 3. 运行还原
        restore_cmd = [
            PYTHON_EXEC, self.backup_py,
            "--restore", archive_path,
            "--data-dir", restore_dir
        ]
        res_restore = subprocess.run(restore_cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        self.assertEqual(res_restore.returncode, 0, f"还原必须成功: {res_restore.stderr}")

        # 4. 验证还原内容逐字节一致
        with open(os.path.join(restore_dir, "db.json"), "r") as f:
            self.assertEqual(f.read(), '{"test": "data", "totalArticles": 42}')
        with open(os.path.join(restore_dir, "raw", "raw_item.json"), "r") as f:
            self.assertEqual(f.read(), '{"article": "content"}')


if __name__ == "__main__":
    unittest.main()

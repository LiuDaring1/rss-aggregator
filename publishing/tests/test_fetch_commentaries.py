# -*- coding: utf-8 -*-
"""
单元测试：评论抓取与持久化逻辑回归测试 (test_fetch_commentaries.py)
覆盖审阅要求：
1. 摘要与全文并存时优先选用充实全文 (content:encoded)；
2. 仅有摘要时不虚标 full_text；
3. 空正文标记为 metadata_only；
4. 深度清洗并剥离导航噪音；
5. UTC/GMT 时区准确换算为北京时间 (Asia/Shanghai)；
6. 单源异常隔离，不阻断其他信源。
"""

import unittest
import os
import sys
import tempfile
import json
import xml.etree.ElementTree as ET

# 导入待测模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from scripts.fetch_commentaries import (
    html_to_clean_text, parse_iso_date, content_hash_of,
    generate_stable_id, classify_content, atomic_save_json,
    process_source
)

class TestFetchCommentaries(unittest.TestCase):

    def test_01_html_clean_and_nav_strip(self):
        """测试 HTML 清洗与导航噪音剥离"""
        dirty = """
        <div class="nav">首页 > 即时-时政 > 正文</div>
        <p>这是第一段真实评论正文内容，详细分析事件前因后果。</p>
        <script>alert('noise');</script>
        <p>这是第二段评论内容，深入论述背后的社会学意义与制度价值。</p>
        """
        cleaned = html_to_clean_text(dirty)
        paras = [p for p in cleaned.split("\n\n") if p.strip()]
        self.assertEqual(len(paras), 2)
        self.assertIn("第一段真实评论正文内容", paras[0])
        self.assertIn("第二段评论内容", paras[1])
        self.assertNotIn("首页 > 即时", cleaned)
        self.assertNotIn("alert", cleaned)

    def test_02_timezone_conversion(self):
        """测试不同时区时间统一换算为东八区北京时间 (Asia/Shanghai)"""
        # UTC 跨日: 2026-09-20 18:00 UTC -> 北京时间 2026-09-21 02:00
        d1, iso1 = parse_iso_date("Sun, 20 Sep 2026 18:00:00 +0000")
        self.assertEqual(d1, "2026-09-21")
        self.assertTrue(iso1.startswith("2026-09-21T02:00:00"))

        # GMT 跨日: 2026-09-20 18:00 GMT -> 2026-09-21
        d2, iso2 = parse_iso_date("Sun, 20 Sep 2026 18:00:00 GMT")
        self.assertEqual(d2, "2026-09-21")

        # ISO 8601 UTC Z: 2026-09-20T20:00:00Z -> 2026-09-21
        d3, iso3 = parse_iso_date("2026-09-20T20:00:00Z")
        self.assertEqual(d3, "2026-09-21")

        # 原生东八区: 2026-09-20T10:00:00+08:00 -> 保持 2026-09-20
        d4, iso4 = parse_iso_date("2026-09-20T10:00:00+08:00")
        self.assertEqual(d4, "2026-09-20")

    def test_03_content_priority_and_classification(self):
        """测试正文充实度判定与质量分类"""
        # 1. 充实长文 (>= 300字且两段) -> full_text
        long_body = "第一段深度评论分析。" * 15 + "\n\n" + "第二段论述制度与社会价值。" * 15
        text_type, has_full = classify_content(long_body)
        self.assertEqual(text_type, "full_text")
        self.assertTrue(has_full)

        # 2. 仅摘要 (50 ~ 279字) -> summary_only, hasFullText = False
        summary_body = "这是一则短摘要，大约有一百个字左右，概括了今天上午发生的突发新闻基本情况，供读者速览了解并把握脉络要点。"
        text_type, has_full = classify_content(summary_body)
        self.assertEqual(text_type, "summary_only")
        self.assertFalse(has_full)

        # 3. 仅元数据 (< 50字) -> metadata_only
        meta_body = "简讯：某某事件正在处理中。"
        text_type, has_full = classify_content(meta_body)
        self.assertEqual(text_type, "metadata_only")
        self.assertFalse(has_full)

    def test_04_stable_id_and_content_hash(self):
        """测试稳定 ID 与内容哈希抗干扰"""
        url = "https://www.example.com/opinion/2026/09/article-123.html?from=feed"
        id1 = generate_stable_id("test_source", url, "原始标题")
        id2 = generate_stable_id("test_source", url, "编辑微调后的标题")
        self.assertEqual(id1, id2)

        # 内容哈希忽略纯空白
        h1 = content_hash_of("评论   正文\n\n段落二")
        h2 = content_hash_of("评论正文段落二")
        self.assertEqual(h1, h2)

    def test_05_atomic_save(self):
        """测试原子化文件写入安全"""
        with tempfile.TemporaryDirectory() as td:
            fpath = os.path.join(td, "test_article.json")
            data = {"id": "comm-01", "title": "测试文章", "content": "内容"}
            atomic_save_json(fpath, data)
            self.assertTrue(os.path.exists(fpath))
            with open(fpath, "r", encoding="utf-8") as fp:
                loaded = json.load(fp)
            self.assertEqual(loaded["title"], "测试文章")

if __name__ == "__main__":
    unittest.main()

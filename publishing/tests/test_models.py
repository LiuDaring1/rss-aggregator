# -*- coding: utf-8 -*-
"""
出版模块单元测试 (Unit Tests)
测试重点：
1. 观点池与双主体解耦：观点池支持 2, 5, 7+ 条任意长度，模板不截断
2. 范本主体严格限定为 2 段
3. 校验器字数统计与警告机制
"""
import os
import sys
import unittest
from pydantic import ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from weekly_pipeline.models import (
    CommentaryUnit, LearningBlock, ViewpointItem, ReasoningLesson,
    SpeechBlock, SpeechBodyParagraph, TeachingBlock, DeconstructionItem
)
from weekly_pipeline.render import render_unit_preview_html
from weekly_pipeline.validation import (
    validate_commentary, count_chinese_chars, count_non_whitespace_chars
)

def create_sample_commentary(viewpoint_count: int, body_count: int = 2) -> CommentaryUnit:
    """辅助创建测试用 Commentary 实例"""
    vps = [
        ViewpointItem(
            id=f"v{i+1}",
            claim=f"这是第 {i+1} 个角度的具体主张判断",
            evidence=f"材料中关于第 {i+1} 个观点的对应事实证据",
            explanation=f"关于第 {i+1} 个观点的补充说明"
        )
        for i in range(viewpoint_count)
    ]
    
    body = [
        SpeechBodyParagraph(
            id=f"b{i+1}",
            claim=f"主体段分论点 {i+1}：具体而有递进的主张",
            paragraphs=[f"主体段分论点 {i+1}：具体而有递进的主张。这是详细的口语展开阐述部分，摆事实讲道理。"]
        )
        for i in range(body_count)
    ]
    
    return CommentaryUnit(
        id="C_TEST",
        retelling_ref="R01",
        title="测试评论标题",
        learning=LearningBlock(
            recap_facts=["事实1", "事实2"],
            questions=["问题1", "问题2"],
            baseline_diagnostic="直观第一印象诊断",
            viewpoints=vps,
            reasoning_lessons=[
                ReasoningLesson(
                    title="教学推演示例",
                    target_viewpoint_ids=[v.id for v in vps[:2]],
                    deduction_text="从事实A推导到结论B的完整因果链条。"
                )
            ]
        ),
        speech=SpeechBlock(
            selected_viewpoint_ids=[v.id for v in vps[:2]],
            main_claim="总观点：明确的评价导向与结构统领。",
            body=body,
            closing="收束结尾：回顾核心判断，完成口语表达闭环。"
        ),
        teaching=TeachingBlock(
            spine="开头 -> 主体一 -> 主体二 -> 结尾",
            deconstruction=[
                DeconstructionItem(
                    target="【主体一拆解】",
                    instruction="先立小观点，再给事实支撑。"
                )
            ]
        )
    )

class PipelineModelTestCase(unittest.TestCase):

    def test_viewpoints_open_ended(self):
        """验证观点池支持 2, 5, 7 条，并在 HTML 模板中全部呈现，不发生截断"""
        for count in [2, 5, 7, 9]:
            cu = create_sample_commentary(viewpoint_count=count, body_count=2)
            self.assertEqual(len(cu.learning.viewpoints), count)
            
            # 渲染为 HTML
            html_out = render_unit_preview_html(cu, "commentary")
            
            # 验证所有观点的主张均被渲染，无遗漏
            for i in range(count):
                self.assertIn(f"第 {i+1} 个角度的具体主张判断", html_out)
                self.assertIn(f"材料中关于第 {i+1} 个观点的对应事实证据", html_out)

    def test_speech_body_strictly_two(self):
        """验证范本主体段落必须为严格 2 段，不能是 1 段或 3 段"""
        # 2 段正常通过
        cu_valid = create_sample_commentary(viewpoint_count=3, body_count=2)
        self.assertEqual(len(cu_valid.speech.body), 2)
        
        # 1 段抛出 ValidationError
        with self.assertRaises(ValidationError) as exc1:
            create_sample_commentary(viewpoint_count=3, body_count=1)
        self.assertIn("最终口语范本必须且只能由 2 个主体段展开", str(exc1.exception))
        
        # 3 段抛出 ValidationError
        with self.assertRaises(ValidationError) as exc2:
            create_sample_commentary(viewpoint_count=3, body_count=3)
        self.assertIn("最终口语范本必须且只能由 2 个主体段展开", str(exc2.exception))

    def test_validation_warnings(self):
        """验证观点池 <= 2 条时触发编辑警告，但工程模型仍合法"""
        cu_2 = create_sample_commentary(viewpoint_count=2, body_count=2)
        res = validate_commentary(cu_2.model_dump())
        self.assertTrue(res.is_valid)
        self.assertTrue(any("观点池仅包含 2 条观点" in w for w in res.warnings))
        
        cu_5 = create_sample_commentary(viewpoint_count=5, body_count=2)
        res_5 = validate_commentary(cu_5.model_dump())
        self.assertTrue(res_5.is_valid)
        self.assertFalse(any("观点池仅包含" in w for w in res_5.warnings))

    def test_migrated_content_directory(self):
        """验证已迁移与新增的全部 YAML 单元结构合规"""
        from weekly_pipeline.validation import validate_content_directory
        res = validate_content_directory("content")
        self.assertGreaterEqual(res["total_units"], 20)
        self.assertEqual(res["valid_units"], res["total_units"])
        self.assertEqual(res["total_errors"], 0)

    def test_chinese_char_counter(self):
        """测试汉字计数与字数警告"""
        sample_text = "这是一段用于测试汉字计数的示例文本（包含标点符号 123 和 English words）！"
        han = count_chinese_chars(sample_text)
        self.assertEqual(han, 24)

    def test_spoken_assembly_and_character_count_independent_claim(self):
        """测试主体段 claim 独立写时，不会发生漏计或未拼接至口语流中的问题"""
        # 创建一个 claim 独立、paragraphs[0] 不含 claim 的评论单元
        body = [
            SpeechBodyParagraph(
                id="b1",
                claim="分论点一：独立小观点。",
                paragraphs=["这是正文，开头并没有重复小观点。"]
            ),
            SpeechBodyParagraph(
                id="b2",
                claim="分论点二：第二个小观点。",
                paragraphs=["这是第二段正文，也没有重复小观点。"]
            )
        ]
        cu = CommentaryUnit(
            id="C_CLAIM_TEST",
            retelling_ref="R01",
            title="测试独立观点评论",
            learning=LearningBlock(
                recap_facts=["事实1", "事实2"],
                questions=["问题1", "问题2"],
                viewpoints=[
                    ViewpointItem(id="v1", claim="观点1", evidence="证据1"),
                    ViewpointItem(id="v2", claim="观点2", evidence="证据2"),
                ],
                reasoning_lessons=[
                    ReasoningLesson(title="推演", target_viewpoint_ids=["v1"], deduction_text="推演文本")
                ]
            ),
            speech=SpeechBlock(
                selected_viewpoint_ids=["v1", "v2"],
                main_claim="总观点开头。",
                body=body,
                closing="结尾收束。"
            ),
            teaching=TeachingBlock(
                spine="结构",
                deconstruction=[DeconstructionItem(target="【拆解】", instruction="讲解")]
            )
        )
        
        # 1. 验证 get_spoken_paragraphs 自动把 claim 拼接到段首
        paras = cu.get_spoken_paragraphs()
        self.assertEqual(len(paras), 4) # 开头, b1, b2, 结尾
        self.assertTrue(paras[1].startswith("分论点一：独立小观点。 这是正文"))
        self.assertTrue(paras[2].startswith("分论点二：第二个小观点。 这是第二段正文"))
        
        # 2. 验证 get_full_spoken_text 包含全部 claim 字符
        full_text = cu.get_full_spoken_text()
        self.assertIn("分论点一：独立小观点", full_text)
        self.assertIn("分论点二：第二个小观点", full_text)
        
        # 3. 验证校验器采用统一公式计算字数
        res = validate_commentary(cu.model_dump())
        self.assertTrue(res.is_valid)

    def test_yaml_duplicate_keys_detection(self):
        """测试 YAML 重复键检测防御机制"""
        from weekly_pipeline.validation import load_yaml_safely
        yaml_with_dups = """
id: C99
title: 包含重复键的YAML
learning:
  questions:
    - 问题1
  questions:
    - 问题2被重复覆盖
"""
        with self.assertRaises(ValueError) as ctx:
            load_yaml_safely(yaml_with_dups)
        self.assertIn("发现重复的 YAML 键 'questions'", str(ctx.exception))

    def test_cross_file_retelling_reference_validation(self):
        """测试跨文件引用校验：评论单元引用不存在的复述材料时应报错"""
        cu = create_sample_commentary(viewpoint_count=3, body_count=2)
        cu.retelling_ref = "R99_NON_EXISTENT"
        
        # 传入有效复述ID列表，R99 不在其中
        available_r = {"R01", "R02", "R03"}
        res = validate_commentary(cu.model_dump(), available_retellings=available_r)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("未在有效复述材料列表中找到" in err for err in res.errors))

    def test_deconstruction_engineering_praise_flagged(self):
        """测试学生拆解中出现工程自夸词（如‘纠正旧版’）会被警告"""
        cu = create_sample_commentary(viewpoint_count=3, body_count=2)
        cu.teaching.deconstruction.append(
            DeconstructionItem(target="【纠正旧版】", instruction="本段彻底修复了上一版的缺陷")
        )
        res = validate_commentary(cu.model_dump())
        self.assertTrue(res.is_valid) # 警告不阻断工程编译
        self.assertTrue(any("教学拆解属于面向学生的印刷内容，不应包含工程执行评述" in w for w in res.warnings))

    def test_chinese_char_counting_vs_non_whitespace(self):
        """测试字符统计严格区分纯汉字与非空白字符"""
        sample_str = "单脚鞋银行 100%！"
        # 汉字：单脚鞋银行 (5)
        # 非空白字符：单脚鞋银行100%！ (10)
        self.assertEqual(count_chinese_chars(sample_str), 5)
        self.assertEqual(count_non_whitespace_chars(sample_str), 10)

    def test_markdown_export_dual_editions(self):
        """测试学生版与教师审阅版 Markdown 导出的差异性"""
        from weekly_pipeline.export_markdown import (
            export_retelling_markdown, export_commentary_markdown
        )
        from weekly_pipeline.models import MindmapTree, MindmapBranch, MindmapLeaf, RetellingUnit
        
        # 1. 复述单元测试
        ru = RetellingUnit(
            id="R_TEST",
            category="社会热点",
            packet_ref="pkt-test",
            title="测试复述",
            date_label="2026年9月",
            source_label="测试来源",
            material_paragraphs=["材料段落"],
            keywords=["关键词1"],
            mindmap_tree=MindmapTree(
                center="核心",
                branches=[
                    MindmapBranch(name="分支1", leaves=[
                        MindmapLeaf(id="leaf-01", hint="提示线索", answer="绝密答案")
                    ])
                ]
            ),
            mapkey="绝密答案",
            ref_retelling="示范复述"
        )
        md_student_r = export_retelling_markdown(ru, edition="student")
        md_teacher_r = export_retelling_markdown(ru, edition="teacher")
        self.assertIn("学生练习版", md_student_r)
        self.assertNotIn("绝密答案", md_student_r) # 学生版隐藏答案
        self.assertIn("（____）", md_student_r)
        self.assertIn("教师审阅版", md_teacher_r)
        self.assertIn("绝密答案", md_teacher_r) # 教师版显示答案
        
        # 2. 评论单元测试
        cu = create_sample_commentary(viewpoint_count=3, body_count=2)
        cu.teaching.editor_notes = "内部机密备课备注：仅限教研团队使用"
        md_student_c = export_commentary_markdown(cu, edition="student")
        md_teacher_c = export_commentary_markdown(cu, edition="teacher")
        self.assertIn("学生练习版", md_student_c)
        self.assertNotIn("内部机密备课备注", md_student_c) # 学生版隐藏内部备注
        self.assertIn("教师审阅版", md_teacher_c)
        self.assertIn("内部机密备课备注", md_teacher_c) # 教师版展示内部备注
        self.assertIn("正文汉字数", md_student_c)
        self.assertIn("总字符数（含标点）", md_student_c)

    def test_validate_file_aborts_on_duplicate_keys(self):
        """测试 validate_file 遇到重复键直接判定无效并返回明确错误"""
        import tempfile
        from weekly_pipeline.validation import validate_file
        
        dup_yaml = """
schema_version: '1.0'
id: C_DUP
title: 重复键测试
category: 社会热点
category: 重复的社会热点
"""
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as tf:
            tf.write(dup_yaml)
            tf_path = tf.name
            
        try:
            val_res = validate_file(tf_path)
            self.assertFalse(val_res.is_valid)
            self.assertTrue(any("发现重复的 YAML 键 'category'" in err for err in val_res.errors))
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_e2_export_commentary_markdown_multi_paragraph_body(self):
        """E2回归测试：主体段包含多个小段时，Markdown导出绝不截断结尾，完整呈现所有段落"""
        from weekly_pipeline.export_markdown import export_commentary_markdown
        from weekly_pipeline.models import SpeechBodyParagraph
        
        cu = create_sample_commentary(viewpoint_count=3, body_count=2)
        # 第一主体包含 2 小段，第二主体包含 1 小段（总共 1 开头 + 2 主体一 + 1 主体二 + 1 结尾 = 5 段）
        cu.speech.body = [
            SpeechBodyParagraph(
                id="b1",
                claim="分论点一：第一层理由说明",
                paragraphs=[
                    "第一小段详细论述事实与原因。",
                    "第二小段递进阐释影响与推导。"
                ]
            ),
            SpeechBodyParagraph(
                id="b2",
                claim="分论点二：第二层推进思考",
                paragraphs=[
                    "第二主体唯一小段论述治理与制度。"
                ]
            )
        ]
        cu.speech.closing = "真正的结尾收束总结段落，绝不应丢失。"
        
        md_text = export_commentary_markdown(cu, edition="teacher")
        
        # 断言所有小段都在导出 Markdown 中出现
        self.assertIn("第一小段详细论述事实与原因", md_text)
        self.assertIn("第二小段递进阐释影响与推导", md_text)
        self.assertIn("第二主体唯一小段论述治理与制度", md_text)
        # 核心断言：结尾收束段落必须保留并正确标示，绝不可被误标或截断
        self.assertIn("### 【结尾·收束总结】", md_text)
        self.assertIn("真正的结尾收束总结段落，绝不应丢失", md_text)

    def test_e1_and_e3_export_md_aborts_on_invalid_file_and_missing_retelling(self):
        """E1与E3回归测试：导出时若发现非法单元或缺少引用，立即抛出异常并阻断，不留残留半成品"""
        import tempfile
        import shutil
        from weekly_pipeline.export_markdown import export_all_markdown
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            c_dir = os.path.join(tmp_dir, "content")
            out_dir = os.path.join(tmp_dir, "out")
            r_dir = os.path.join(c_dir, "retellings")
            com_dir = os.path.join(c_dir, "commentaries")
            os.makedirs(r_dir, exist_ok=True)
            os.makedirs(com_dir, exist_ok=True)
            os.makedirs(out_dir, exist_ok=True)
            
            # 1. 评论单元引用了不存在的复述单元 R_NON_EXISTENT
            bad_commentary = """
schema_version: '1.0'
id: C_BAD
retelling_ref: R_NON_EXISTENT
title: 测试坏评论
learning:
  recap_facts: [事实1, 事实2]
  questions: [问题1, 问题2]
  viewpoints:
    - id: v1
      claim: 观点1
      evidence: 证据1
    - id: v2
      claim: 观点2
      evidence: 证据2
  reasoning_lessons: []
speech:
  selected_viewpoint_ids: [v1, v2]
  main_claim: 总观点
  body:
    - id: b1
      claim: 分论点1
      paragraphs: [分论点1内容]
    - id: b2
      claim: 分论点2
      paragraphs: [分论点2内容]
  closing: 结尾
teaching:
  spine: 骨架
  deconstruction:
    - target: 目标
      instruction: 指导
"""
            with open(os.path.join(com_dir, "C_BAD.yaml"), "w", encoding="utf-8") as f:
                f.write(bad_commentary)
                
            # 执行 export_all_markdown，断言其由于缺少复述引用而抛出 ValueError
            with self.assertRaises(ValueError) as ctx:
                export_all_markdown(c_dir, out_dir, edition="teacher")
            self.assertIn("未在有效复述材料列表中找到", str(ctx.exception))
            
            # 断言 out_dir 下未残留任何 C_BAD.md
            self.assertFalse(os.path.exists(os.path.join(out_dir, "C_BAD.md")))

    def test_export_preserves_old_output_on_nonexistent_or_invalid_input(self):
        """测试错误或不存在的输入目录绝不会清空或破坏已有旧输出"""
        import tempfile
        from weekly_pipeline.export_markdown import export_all_markdown
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = os.path.join(tmp_dir, "reviews", "markdown")
            stud_dir = os.path.join(out_dir, "student")
            teach_dir = os.path.join(out_dir, "teacher")
            os.makedirs(stud_dir, exist_ok=True)
            os.makedirs(teach_dir, exist_ok=True)
            
            old_stud_file = os.path.join(stud_dir, "C01.md")
            old_teach_file = os.path.join(teach_dir, "C01.md")
            with open(old_stud_file, "w", encoding="utf-8") as f:
                f.write("OLD_STUDENT_CONTENT")
            with open(old_teach_file, "w", encoding="utf-8") as f:
                f.write("OLD_TEACHER_CONTENT")
                
            # 1. 尝试使用完全不存在的输入目录
            non_existent_dir = os.path.join(tmp_dir, "does_not_exist")
            with self.assertRaises(ValueError) as ctx:
                export_all_markdown(non_existent_dir, out_dir, edition="both")
            self.assertIn("不存在", str(ctx.exception))
            
            # 断言已有旧输出完好无损，绝未被清空
            self.assertTrue(os.path.exists(old_stud_file))
            self.assertTrue(os.path.exists(old_teach_file))
            with open(old_stud_file, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "OLD_STUDENT_CONTENT")
            with open(old_teach_file, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "OLD_TEACHER_CONTENT")

            # 2. 尝试使用空输入目录
            empty_dir = os.path.join(tmp_dir, "empty_content")
            os.makedirs(empty_dir, exist_ok=True)
            with self.assertRaises(ValueError) as ctx2:
                export_all_markdown(empty_dir, out_dir, edition="both")
            self.assertIn("未找到任何有效单元文件", str(ctx2.exception))
            
            # 断言已有旧输出依旧完好无损
            with open(old_stud_file, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "OLD_STUDENT_CONTENT")

    def test_preview_unit_unverified_badge_rendered(self):
        """测试草稿缺引用时的【未核验】状态能真实渲染进预览产物 HTML"""
        import tempfile
        from weekly_pipeline.render import preview_unit
        cu = create_sample_commentary(viewpoint_count=3, body_count=2)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            res = preview_unit(cu, "commentary", tmp_dir, formats=["html"], is_unverified=True)
            self.assertTrue(res.get("is_unverified"))
            html_file = res.get("html")
            self.assertTrue(os.path.exists(html_file))
            
            with open(html_file, "r", encoding="utf-8") as f:
                html_content = f.read()
                
            self.assertIn("【草稿·未核验】", html_content)
            self.assertIn("（未核验）", html_content)

    def test_publication_switch_fault_injection_preserves_old_output(self):
        """测试发布末端原子切换与回滚：双版本均生成后注入故障，确保旧版本完整保留无损"""
        import tempfile
        from pathlib import Path
        from weekly_pipeline.export_markdown import export_all_markdown, publish_directory_atomically

        def snapshot(root: Path):
            return {
                str(p.relative_to(root)): p.read_text(encoding="utf-8")
                for p in sorted(root.rglob("*.md"))
            }

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            content_dir = root / "content"
            published_dir = root / "published"
            
            # 准备合成的有效输入内容
            (content_dir / "retellings").mkdir(parents=True)
            for uid in ["R01", "R02"]:
                retell_yaml = f"""schema_version: '1.0'
id: {uid}
category: 社会热点
packet_ref: pkt-{uid}
title: 测试复述{uid}
date_label: 2026年9月
source_label: 财经网
material_paragraphs:
  - 事实段落1
keywords: [词1, 词2]
mindmap_tree:
  center: 核心
  branches:
    - name: 分支
      leaves:
        - id: L1
          hint: 提示
          answer: 答案
ref_retelling: 这是示范文本
mapkey: 答案1
"""
                (content_dir / "retellings" / f"{uid}.yaml").write_text(retell_yaml, encoding="utf-8")

            # 准备已有旧版输出（含 student, teacher，以及已被淘汰的废弃文件 obsolete.md）
            for sub in ["student", "teacher"]:
                sub_dir = published_dir / sub
                sub_dir.mkdir(parents=True)
                (sub_dir / "R01.md").write_text(f"OLD_VERSION_{sub}_R01", encoding="utf-8")
                (sub_dir / "obsolete.md").write_text(f"OLD_VERSION_{sub}_OBSOLETE", encoding="utf-8")

            before_snapshot = snapshot(published_dir)
            self.assertEqual(len(before_snapshot), 4)

            # 场景 1: 双版本导出 —— 两个版本均在暂存区生成完毕后，在发布切换阶段注入故障
            with self.assertRaises(OSError) as ctx:
                export_all_markdown(str(content_dir), str(published_dir), edition="both", _fault_at_publish=True)
            self.assertIn("INJECTED_FAULT", str(ctx.exception))

            # 核心断言：发布切换失败后，旧发布目录的文件集合、路径与内容摘要 100% 保持未改变！
            after_fault_snapshot = snapshot(published_dir)
            self.assertEqual(before_snapshot, after_fault_snapshot)
            self.assertTrue((published_dir / "student" / "obsolete.md").exists())
            self.assertTrue((published_dir / "teacher" / "obsolete.md").exists())

            # 场景 2: 正常发布 —— 两版本一起切换至新批次，旧废弃文件被清理
            generated = export_all_markdown(str(content_dir), str(published_dir), edition="both")
            self.assertEqual(len(generated), 4) # student: R01, R02; teacher: R01, R02
            
            self.assertTrue((published_dir / "student" / "R01.md").exists())
            self.assertTrue((published_dir / "student" / "R02.md").exists())
            self.assertTrue((published_dir / "teacher" / "R01.md").exists())
            self.assertTrue((published_dir / "teacher" / "R02.md").exists())
            # obsolete 文件在新版本中已被安全清除
            self.assertFalse((published_dir / "student" / "obsolete.md").exists())
            self.assertFalse((published_dir / "teacher" / "obsolete.md").exists())
            # 记录了发布清单与文件摘要
            self.assertTrue((published_dir / "_manifest.json").exists())

            # 场景 3: 单版本导出 —— 同样具备发布末端失败回滚保护
            single_published_dir = root / "single_published"
            single_published_dir.mkdir(parents=True)
            (single_published_dir / "R01.md").write_text("OLD_SINGLE_R01", encoding="utf-8")
            (single_published_dir / "obsolete.md").write_text("OLD_SINGLE_OBSOLETE", encoding="utf-8")
            
            single_before = snapshot(single_published_dir)
            with self.assertRaises(OSError):
                export_all_markdown(str(content_dir), str(single_published_dir), edition="student", _fault_at_publish=True)
            
            single_after = snapshot(single_published_dir)
            self.assertEqual(single_before, single_after)

    def test_publish_directory_atomically_rename_exception_rollback(self):
        """测试底层 publish_directory_atomically 在 rename 异常时的回滚保全能力"""
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from weekly_pipeline.export_markdown import publish_directory_atomically

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "published"
            staging = root / "staging"
            target.mkdir()
            staging.mkdir()
            (target / "old.txt").write_text("OLD_CONTENT", encoding="utf-8")
            (staging / "new.txt").write_text("NEW_CONTENT", encoding="utf-8")

            real_rename = os.rename
            calls = []
            def fake_rename(src, dst):
                calls.append((src, dst))
                # 第二次 rename 是将 staging 移到 target，此时模拟文件系统故障
                if len(calls) == 2:
                    raise OSError("Simulated filesystem rename failure")
                return real_rename(src, dst)

            with patch("os.rename", side_effect=fake_rename):
                with self.assertRaises(OSError):
                    publish_directory_atomically(str(staging), str(target))

            # 断言 target 被安全回滚，旧文件与内容完好无损
            self.assertTrue((target / "old.txt").exists())
            self.assertEqual((target / "old.txt").read_text(encoding="utf-8"), "OLD_CONTENT")

if __name__ == "__main__":
    unittest.main()

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

if __name__ == "__main__":
    unittest.main()

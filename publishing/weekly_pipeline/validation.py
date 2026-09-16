# -*- coding: utf-8 -*-
"""
口语素材周刊 内容与结构校验模块 (Validation Module)
分离：
1. 工程模型校验 (Pydantic Schema)
2. 编辑内容规则校验 (字数、观点池充分性、口语节奏、必填结构)
"""
import os
import re
import yaml
from typing import Dict, Any, List, Optional, Tuple
from pydantic import ValidationError

from weekly_pipeline.models import (
    RetellingUnit, CommentaryUnit, ExcerptUnit, IssueManifest
)

def count_chinese_chars(text: str) -> int:
    """统计中文字符数（不含标点、英文字符与空白）"""
    return len(re.findall(r'[\u4e00-\u9fa5]', text))

def count_non_whitespace_chars(text: str) -> int:
    """统计非空白字符总数（含汉字与标点）"""
    return len(re.sub(r'\s+', '', text))

class ValidationResult:
    def __init__(self, unit_id: str, unit_type: str):
        self.unit_id = unit_id
        self.unit_type = unit_type
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.metrics: Dict[str, Any] = {}

    def add_error(self, msg: str):
        self.is_valid = False
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "unit_type": self.unit_type,
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "metrics": self.metrics
        }

def validate_commentary(data: Dict[str, Any]) -> ValidationResult:
    uid = data.get("id", "UNKNOWN")
    res = ValidationResult(uid, "commentary")
    
    # 1. 工程模式 Pydantic 校验
    try:
        model = CommentaryUnit.model_validate(data)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            res.add_error(f"Schema校验错误 [{loc}]: {err['msg']}")
        return res
        
    # 2. 编辑业务规则校验
    # 观点池数量：任务书要求观点池至少2个，推荐3-6个多元角度
    vp_count = len(model.learning.viewpoints)
    res.metrics["viewpoint_count"] = vp_count
    if vp_count <= 2:
        res.add_warning(
            f"观点池仅包含 {vp_count} 条观点（建议提供 3~6 个多角度思考切入点，避免与范本双主体机械等同）。"
        )
        
    # 主体段数量校验：严格2段
    body_count = len(model.speech.body)
    res.metrics["body_paragraph_count"] = body_count
    if body_count != 2:
        res.add_error(f"范本主体段落必须为严格 2 段，当前为 {body_count} 段。")
        
    # 观点分论点 (claim) 校验
    claims = [b.claim for b in model.speech.body]
    if len(claims) == 2 and claims[0] == claims[1]:
        res.add_error("范本两个主体段落的分论点 (claim) 完全相同，缺少思考递进或不同增量。")
        
    # 结尾收束检查
    if not model.speech.closing or not model.speech.closing.strip():
        res.add_error("范本缺少独立收束结尾 (closing)。")
        
    # 字数统计与播报时长估算 (高中生口语 200~230字/分钟)
    all_speech_texts = [model.speech.main_claim]
    for b in model.speech.body:
        all_speech_texts.extend(b.paragraphs)
    all_speech_texts.append(model.speech.closing)
    full_speech = "".join(all_speech_texts)
    
    han_count = count_chinese_chars(full_speech)
    total_non_ws = count_non_whitespace_chars(full_speech)
    res.metrics["han_char_count"] = han_count
    res.metrics["total_chars_non_ws"] = total_non_ws
    
    # 建议正文字数在 350~420 汉字之间（对应约 1分40秒 ~ 2分10秒）
    if han_count > 460:
        res.add_warning(
            f"范本汉字数达到 {han_count} 字（非空白 {total_non_ws} 字符），口语播报负担过重，易超出2分钟限制，建议精简至约 370~400 汉字。"
        )
    elif han_count < 280:
        res.add_warning(
            f"范本汉字数仅 {han_count} 字，论述展开可能不充分，建议控制在约 370~400 汉字。"
        )
        
    # 拆解自夸词筛查
    self_praise_words = ["开头亮剑", "极具张力", "妙不可言", "大师手笔", "无懈可击"]
    for decon in model.teaching.deconstruction:
        for sp in self_praise_words:
            if sp in decon.instruction:
                res.add_warning(f"教学拆解中包含自我夸饰词汇 '{sp}'，应改为具体论证机制分析。")
                
    return res

def validate_retelling(data: Dict[str, Any]) -> ValidationResult:
    uid = data.get("id", "UNKNOWN")
    res = ValidationResult(uid, "retelling")
    try:
        model = RetellingUnit.model_validate(data)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            res.add_error(f"Schema校验错误 [{loc}]: {err['msg']}")
        return res
        
    # 校验正文段落
    if not model.material_paragraphs:
        res.add_error("复述材料段落为空。")
        
    # 校验思维导图分支
    if not model.mindmap_tree.branches:
        res.add_warning("思维导图缺少主枝 (branches)。")
        
    res.metrics["material_paragraphs_count"] = len(model.material_paragraphs)
    res.metrics["keyword_count"] = len(model.keywords)
    res.metrics["branch_count"] = len(model.mindmap_tree.branches)
    return res

def validate_excerpt(data: Dict[str, Any]) -> ValidationResult:
    uid = data.get("id", "UNKNOWN")
    res = ValidationResult(uid, "excerpt")
    try:
        model = ExcerptUnit.model_validate(data)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            res.add_error(f"Schema校验错误 [{loc}]: {err['msg']}")
        return res
        
    if not model.quote_paragraphs:
        res.add_error("原文摘录段落为空。")
    if not model.demo_text or not model.demo_text.strip():
        res.add_error("缺少换话题示范 (demo_text)。")
        
    res.metrics["quote_paragraphs_count"] = len(model.quote_paragraphs)
    return res

def validate_file(yaml_path: str) -> ValidationResult:
    """自动判断类型并校验单个 YAML 文件"""
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        res = ValidationResult(os.path.basename(yaml_path), "unknown")
        res.add_error("文件不是有效的 YAML 字典对象。")
        return res
        
    if "retelling_ref" in data and "speech" in data:
        return validate_commentary(data)
    elif "mindmap_tree" in data and "material_paragraphs" in data:
        return validate_retelling(data)
    elif "quote_paragraphs" in data and "demo_text" in data:
        return validate_excerpt(data)
    else:
        res = ValidationResult(os.path.basename(yaml_path), "unknown")
        res.add_error("无法识别该 YAML 对应的周刊单元类型。")
        return res

def validate_content_directory(content_dir: str) -> Dict[str, Any]:
    """遍历校验整库"""
    results = []
    total = 0
    passed = 0
    warn_count = 0
    err_count = 0
    
    for root, _, files in os.walk(content_dir):
        for f in sorted(files):
            if f.endswith(".yaml") or f.endswith(".yml"):
                p = os.path.join(root, f)
                total += 1
                res = validate_file(p)
                results.append(res.to_dict())
                if res.is_valid:
                    passed += 1
                else:
                    err_count += len(res.errors)
                warn_count += len(res.warnings)
                
    return {
        "total_units": total,
        "valid_units": passed,
        "total_errors": err_count,
        "total_warnings": warn_count,
        "results": results
    }

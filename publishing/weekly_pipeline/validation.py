# -*- coding: utf-8 -*-
"""
口语素材周刊 内容与结构校验模块 (Validation Module)
分离：
1. 工程模型校验 (Pydantic Schema)
2. 编辑内容规则校验 (字数、观点池充分性、口语节奏、必填结构、重复键与跨文件引用)
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

# ==============================================================================
# YAML 重复键检测 Loader
# ==============================================================================

class UniqueKeyLoader(yaml.SafeLoader):
    pass

def construct_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"发现重复的 YAML 键 '{key}'", key_node.start_mark
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping

UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping
)

def safe_load_yaml_unique(stream_or_str: str) -> Any:
    try:
        return yaml.load(stream_or_str, Loader=UniqueKeyLoader)
    except yaml.constructor.ConstructorError as e:
        # 提取重复键名以便给出友好错误
        msg = str(e)
        raise ValueError(f"检测到重复的键: {msg}") from e

load_yaml_safely = safe_load_yaml_unique

# ==============================================================================
# 校验结果对象
# ==============================================================================

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

# ==============================================================================
# 各单元校验函数
# ==============================================================================

def validate_commentary(data: Dict[str, Any], available_retellings: Optional[set] = None) -> ValidationResult:
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
        
    # 2. 跨文件引用校验：retelling_ref
    if available_retellings is not None:
        if model.retelling_ref not in available_retellings:
            res.add_error(
                f"引用的复述单元 '{model.retelling_ref}' 未在有效复述材料列表中找到（请补充该复述单元或检查 ID）。"
            )

    # 3. 内部引用校验：selected_viewpoint_ids 必须属于 viewpoints
    valid_vp_ids = {v.id for v in model.learning.viewpoints}
    for sv_id in model.speech.selected_viewpoint_ids:
        if sv_id not in valid_vp_ids:
            res.add_error(f"范本选定的观点ID '{sv_id}' 在观点池中不存在。")

    for lesson in model.learning.reasoning_lessons:
        for tv_id in lesson.target_viewpoint_ids:
            if tv_id not in valid_vp_ids:
                res.add_warning(f"推演课程关联的观点ID '{tv_id}' 在观点池中不存在。")

    # 4. 观点池数量：建议 3-6 个多元角度
    vp_count = len(model.learning.viewpoints)
    res.metrics["viewpoint_count"] = vp_count
    if vp_count <= 2:
        res.add_warning(
            f"观点池仅包含 {vp_count} 条观点（建议提供 3~6 个多角度思考切入点，避免与范本双主体机械等同）。"
        )
        
    # 5. 主体段数量校验：严格 2 段
    body_count = len(model.speech.body)
    res.metrics["body_paragraph_count"] = body_count
    if body_count != 2:
        res.add_error(f"范本主体段落必须为严格 2 段，当前为 {body_count} 段。")
        
    # 6. 分论点 (claim) 校验
    claims = [b.claim for b in model.speech.body]
    if len(claims) == 2 and claims[0] == claims[1]:
        res.add_error("范本两个主体段落的分论点 (claim) 完全相同，缺少思考递进或不同增量。")
        
    # 7. 结尾收束检查
    if not model.speech.closing or not model.speech.closing.strip():
        res.add_error("范本缺少独立收束结尾 (closing)。")
        
    # 8. 统一口语正文字数统计 (使用 model.get_full_spoken_text())
    full_speech = model.get_full_spoken_text()
    han_count = count_chinese_chars(full_speech)
    total_non_ws = count_non_whitespace_chars(full_speech)
    res.metrics["han_char_count"] = han_count
    res.metrics["total_chars_non_ws"] = total_non_ws
    
    # 建议正文字数在 350~430 汉字之间（对应约 1分40秒 ~ 2分15秒）
    if han_count > 460:
        res.add_warning(
            f"范本汉字数达到 {han_count} 字（非空白 {total_non_ws} 字符），口语播报负担过重，易超出2分钟限制，建议精简至约 370~410 汉字。"
        )
    elif han_count < 280:
        res.add_warning(
            f"范本汉字数仅 {han_count} 字，论述展开可能不充分，建议控制在约 370~410 汉字。"
        )
        
    # 9. 拆解自夸词与工程报告词筛查
    bad_decon_words = [
        "开头亮剑", "极具张力", "妙不可言", "大师手笔", "无懈可击",
        "纠正旧版", "彻底修复", "彻底废除", "严格控制"
    ]
    for decon in model.teaching.deconstruction:
        for bw in bad_decon_words:
            if bw in decon.instruction:
                res.add_warning(
                    f"教学拆解属于面向学生的印刷内容，不应包含工程执行评述或自我夸饰词汇 '{bw}'，学生版拆解应客观分析句段机制，不展示工程评价。"
                )
                
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
        
    if not model.material_paragraphs:
        res.add_error("复述材料段落为空。")
        
    # 校验思维导图分枝与叶节点 ID 唯一性
    leaf_ids = []
    for br in model.mindmap_tree.branches:
        for leaf in br.leaves:
            leaf_ids.append(leaf.id)
            if not leaf.hint or not leaf.hint.strip():
                res.add_warning(f"叶节点 '{leaf.id}' 的 hint 为空。")
                
    dup_leaf_ids = [lid for lid in set(leaf_ids) if leaf_ids.count(lid) > 1]
    if dup_leaf_ids:
        res.add_error(f"思维导图叶节点 ID 存在重复: {dup_leaf_ids}")
        
    res.metrics["material_paragraphs_count"] = len(model.material_paragraphs)
    res.metrics["keyword_count"] = len(model.keywords)
    res.metrics["branch_count"] = len(model.mindmap_tree.branches)
    res.metrics["leaf_count"] = len(leaf_ids)
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

def validate_file(yaml_path: str, available_retellings: Optional[set] = None) -> ValidationResult:
    """自动判断类型并校验单个 YAML 文件，启用重复键检测"""
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = safe_load_yaml_unique(f.read())
    except Exception as e:
        res = ValidationResult(os.path.basename(yaml_path), "unknown")
        res.add_error(f"YAML 解析失败（可能包含格式错误或重复键）: {e}")
        return res

    if not isinstance(data, dict):
        res = ValidationResult(os.path.basename(yaml_path), "unknown")
        res.add_error("文件不是有效的 YAML 字典对象。")
        return res
        
    if "retelling_ref" in data and "speech" in data:
        return validate_commentary(data, available_retellings=available_retellings)
    elif "mindmap_tree" in data and "material_paragraphs" in data:
        return validate_retelling(data)
    elif "quote_paragraphs" in data and "demo_text" in data:
        return validate_excerpt(data)
    else:
        res = ValidationResult(os.path.basename(yaml_path), "unknown")
        res.add_error("无法识别该 YAML 对应的周刊单元类型。")
        return res

def validate_content_directory(content_dir: str) -> Dict[str, Any]:
    """遍历校验整库，含跨文件一致性检查"""
    results = []
    total = 0
    passed = 0
    warn_count = 0
    err_count = 0
    
    if not os.path.exists(content_dir):
        return {
            "total_units": 0,
            "valid_units": 0,
            "total_errors": 1,
            "total_warnings": 0,
            "results": [{"unit_id": "DIR", "unit_type": "dir", "is_valid": False, "errors": [f"内容目录不存在: {content_dir}"], "warnings": [], "metrics": {}}]
        }

    # 预先收集所有存在的 retelling ID
    available_retellings = set()
    r_dir = os.path.join(content_dir, "retellings")
    if os.path.exists(r_dir):
        for rf in os.listdir(r_dir):
            if rf.endswith(".yaml") or rf.endswith(".yml"):
                available_retellings.add(rf.rsplit(".", 1)[0])

    for root, _, files in os.walk(content_dir):
        for f in sorted(files):
            if f.endswith(".yaml") or f.endswith(".yml"):
                p = os.path.join(root, f)
                total += 1
                res = validate_file(p, available_retellings=available_retellings)
                results.append(res.to_dict())
                if res.is_valid:
                    passed += 1
                else:
                    err_count += len(res.errors)
                warn_count += len(res.warnings)
                
    if total == 0:
        err_count += 1
        results.append({
            "unit_id": "EMPTY",
            "unit_type": "dir",
            "is_valid": False,
            "errors": [f"内容目录为空: {content_dir}"],
            "warnings": [],
            "metrics": {}
        })

    return {
        "total_units": total,
        "valid_units": passed,
        "total_errors": err_count,
        "total_warnings": warn_count,
        "results": results
    }

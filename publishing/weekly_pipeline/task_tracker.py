# -*- coding: utf-8 -*-
"""
周刊生产任务状态机与中断恢复管理器 (Weekly Task Tracker)

满足《从版式定标转入每周稳定生产》第 4.3 节：
1. 生产状态文件化：将进度持久化于 issues/<issue_id>/production_state.json；
2. 串联 7 大生产阶段：prep -> candidates_selected -> drafting -> comics -> review -> build -> published；
3. 断点续做能力：切换 Agent 或会话时，读取任务状态继续，已核准文稿与配图不重复重新生成；
4. 失败精准归因：记录各阶段失败原因、待办项与成品位置。
"""

import os
import json
import datetime
from typing import Dict, Any, List, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
    BEIJING_TZ = ZoneInfo("Asia/Shanghai")
except Exception:
    BEIJING_TZ = datetime.timezone(datetime.timedelta(hours=8))

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

STAGES = [
    "prep",                 # 1. 候选扫描与初筛
    "candidates_selected",  # 2. 确定 9+6+6 材料与台账初步建立
    "drafting",             # 3. 编写 YAML (retellings, commentaries, excerpts)
    "comics",               # 4. 看图复述漫画配图与分镜拼装
    "review",               # 5. 教师/编辑审阅与前置自查
    "build",                # 6. 确定性构建与门禁核验
    "published"             # 7. 正式交付与审阅站部署
]

def get_state_file_path(issue_id: str) -> str:
    return os.path.join(ROOT_DIR, "issues", issue_id, "production_state.json")

def load_production_state(issue_id: str) -> Optional[Dict[str, Any]]:
    """读取指定期刊的生产状态记录"""
    sp = get_state_file_path(issue_id)
    if os.path.exists(sp):
        try:
            with open(sp, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def save_production_state(issue_id: str, state: Dict[str, Any]):
    """原子化保存生产状态"""
    sp = get_state_file_path(issue_id)
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    state["last_updated_at"] = datetime.datetime.now(BEIJING_TZ).isoformat()
    tmp_path = sp + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, sp)

def init_production_state(
    issue_id: str,
    time_window: str = "",
    target_units: Optional[Dict[str, List[str]]] = None
) -> Dict[str, Any]:
    """初始化新一期的生产状态记录"""
    existing = load_production_state(issue_id)
    if existing:
        return existing

    now_iso = datetime.datetime.now(BEIJING_TZ).isoformat()
    if not target_units:
        target_units = {
            "retellings": [],
            "commentaries": [],
            "excerpts": []
        }

    stages_data = {}
    for st in STAGES:
        stages_data[st] = {
            "status": "pending",
            "updated_at": None,
            "completed_items": [],
            "pending_items": [],
            "failed_items": [],
            "notes": ""
        }

    state = {
        "schema_version": "1.0",
        "issue_id": issue_id,
        "time_window": time_window,
        "created_at": now_iso,
        "last_updated_at": now_iso,
        "current_stage": "prep",
        "target_quota": {
            "retellings": 9,
            "commentaries": 6,
            "excerpts": 6,
            "total_pages": 47
        },
        "target_units": target_units,
        "unit_freeze_status": {},  # {unit_id: True} 标记已冻结单元
        "stages": stages_data,
        "artifacts": {}
    }
    save_production_state(issue_id, state)
    return state

def update_stage(
    issue_id: str,
    stage: str,
    status: str,
    completed: Optional[List[str]] = None,
    pending: Optional[List[str]] = None,
    failed: Optional[List[Dict[str, Any]]] = None,
    notes: str = "",
    artifacts: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """更新某个生产阶段的执行进度"""
    state = load_production_state(issue_id) or init_production_state(issue_id)
    if stage not in state["stages"]:
        raise ValueError(f"未知的生产阶段: {stage}，可用阶段: {STAGES}")

    st_obj = state["stages"][stage]
    st_obj["status"] = status
    st_obj["updated_at"] = datetime.datetime.now(BEIJING_TZ).isoformat()
    if completed is not None:
        st_obj["completed_items"] = completed
    if pending is not None:
        st_obj["pending_items"] = pending
    if failed is not None:
        st_obj["failed_items"] = failed
    if notes:
        st_obj["notes"] = notes

    if artifacts:
        state.setdefault("artifacts", {}).update(artifacts)

    # 自动推进当前阶段指针 (单向推进保护：刷新前序阶段不得倒退已有主生产进度)
    cur_stage = state.get("current_stage", STAGES[0])
    cur_idx = STAGES.index(cur_stage) if cur_stage in STAGES else 0
    idx = STAGES.index(stage)

    if status == "done":
        if idx >= cur_idx and idx + 1 < len(STAGES):
            state["current_stage"] = STAGES[idx + 1]
    elif status in ["in_progress", "failed"]:
        if idx >= cur_idx:
            state["current_stage"] = stage

    save_production_state(issue_id, state)
    return state

import hashlib

def find_unit_file(unit_id: str) -> Optional[str]:
    """寻找单元文件路径 (相对于 ROOT_DIR)"""
    candidates = [
        os.path.join("content", "retellings", f"{unit_id}.yaml"),
        os.path.join("content", "commentaries", f"{unit_id}.yaml"),
        os.path.join("content", "excerpts", f"{unit_id}.yaml"),
    ]
    for c in candidates:
        full = os.path.join(ROOT_DIR, c)
        if os.path.exists(full):
            return c
    return None

def compute_file_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def freeze_unit(issue_id: str, unit_id: str):
    """标记单元已定稿冻结，记录文件哈希，避免后续流程被重复重写或意外篡改"""
    state = load_production_state(issue_id) or init_production_state(issue_id)
    rel_path = find_unit_file(unit_id)
    file_hash = None
    if rel_path:
        full_path = os.path.join(ROOT_DIR, rel_path)
        file_hash = compute_file_sha256(full_path)

    freeze_record = {
        "frozen": True,
        "frozen_at": datetime.datetime.now(BEIJING_TZ).isoformat(),
        "sha256": file_hash,
        "rel_path": rel_path
    }
    state.setdefault("unit_freeze_status", {})[unit_id] = freeze_record
    save_production_state(issue_id, state)

def is_unit_frozen(issue_id: str, unit_id: str) -> bool:
    """检查单元是否已定稿冻结"""
    state = load_production_state(issue_id)
    if not state:
        return False
    entry = state.get("unit_freeze_status", {}).get(unit_id)
    if isinstance(entry, dict):
        return entry.get("frozen", False)
    return bool(entry)

def unfreeze_unit(issue_id: str, unit_id: str):
    """显式解冻单元，允许重新编辑与生成"""
    state = load_production_state(issue_id) or init_production_state(issue_id)
    if unit_id in state.get("unit_freeze_status", {}):
        if isinstance(state["unit_freeze_status"][unit_id], dict):
            state["unit_freeze_status"][unit_id]["frozen"] = False
        else:
            state["unit_freeze_status"][unit_id] = False
    save_production_state(issue_id, state)

def verify_frozen_units(issue_id: str) -> Tuple[bool, List[str]]:
    """核对所有已冻结单元的文件哈希，确保未经显式解冻前内容未被篡改"""
    state = load_production_state(issue_id)
    if not state:
        return (True, [])

    errors = []
    frozen_map = state.get("unit_freeze_status", {})
    for unit_id, val in frozen_map.items():
        is_frz = val.get("frozen", False) if isinstance(val, dict) else bool(val)
        if is_frz and isinstance(val, dict):
            rel_path = val.get("rel_path") or find_unit_file(unit_id)
            expected_hash = val.get("sha256")
            if rel_path and expected_hash:
                full_path = os.path.join(ROOT_DIR, rel_path)
                if not os.path.exists(full_path):
                    errors.append(f"已冻结单元 {unit_id} 的源文件不存在: {rel_path}")
                else:
                    curr_hash = compute_file_sha256(full_path)
                    if curr_hash != expected_hash:
                        errors.append(
                            f"已冻结单元 {unit_id} 发生未授权篡改! "
                            f"记录哈希: {expected_hash[:10]}... 当前哈希: {curr_hash[:10]}... "
                            f"(文件: {rel_path})"
                        )
    return (len(errors) == 0, errors)

def get_resume_info(issue_id: str) -> Dict[str, Any]:
    """获取断点续做指引信息"""
    state = load_production_state(issue_id)
    if not state:
        return {
            "status": "not_started",
            "issue_id": issue_id,
            "next_action": "执行 prep.py 进行首轮候选扫描",
            "current_stage": "prep"
        }

    cur_stage = state.get("current_stage", "prep")
    pub_stage = state.get("stages", {}).get("published", {})
    if pub_stage.get("status") == "done":
        return {
            "status": "completed",
            "issue_id": issue_id,
            "current_stage": "published",
            "stage_status": "done",
            "pending_items": [],
            "failed_items": [],
            "notes": pub_stage.get("notes", ""),
            "next_action": "本期已完成全部生产与归档发布，可供教学使用"
        }

    st_data = state["stages"].get(cur_stage, {})
    return {
        "status": "in_progress",
        "issue_id": issue_id,
        "current_stage": cur_stage,
        "stage_status": st_data.get("status"),
        "pending_items": st_data.get("pending_items", []),
        "failed_items": st_data.get("failed_items", []),
        "notes": st_data.get("notes", ""),
        "next_action": f"从阶段 [{cur_stage}] 继续执行未完结项: {st_data.get('pending_items', []) or '待触发该阶段任务'}"
    }

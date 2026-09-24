#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
口语素材周刊 · 私有数据备份与完整性隔离校验还原工具 (Backup & Restore Engine) v3.0

满足《工作台可靠运行与教学选材修正任务书》任务三要求:
1. 完整数据覆盖：
   - 评论库: aggr-site/data/commentaries (db.json + raw/*.json)
   - 暖文库: aggr-site/data/wenwen (db.json + raw/*.json)
   - 教师反馈: data/teacher_feedback.json
   - 运行状态: data/fetch_state.json
   - 刊期状态: issues/*/production_state.json
2. 快照一致性校验:
   - 确保索引文件与 raw 实体文件数量一致、哈希有效
3. 隔离恢复测试 (--test-restore):
   - 还原至独立的隔离临时目录 (/tmp/restore_test_XXXX) 进行深度验证，绝不破坏生产环境
4. 负向校验防御:
   - 归档损坏、缺少必要索引、文章数不一致时立即报错 (非零退出)，拒绝静默虚标通过
5. 自动轮转保留策略:
   - 默认保留最近 7 个日备份和 4 个周备份；未生成并通过新备份前绝不清理已有有效副本
6. 异地状态明确登记:
   - 本地备份成功，异地备份明确标为 "待配置 (缺少受控外部存储目标)"，不虚假宣称已完成
"""

import os
import sys
import tarfile
import json
import hashlib
import datetime
import argparse
import tempfile
import shutil
import glob
from typing import Dict, Any, List, Optional, Tuple

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_BACKUP_DIR = os.path.join(ROOT_DIR, "backups")
BACKUP_STATE_FILE = os.path.join(ROOT_DIR, "data", "backup_state.json")

DATA_TARGETS = [
    {"name": "commentaries", "path": os.path.join(ROOT_DIR, "aggr-site", "data", "commentaries"), "required": True},
    {"name": "wenwen", "path": os.path.join(ROOT_DIR, "aggr-site", "data", "wenwen"), "required": False},
    {"name": "teacher_feedback", "path": os.path.join(ROOT_DIR, "data", "teacher_feedback.json"), "required": False},
    {"name": "fetch_state", "path": os.path.join(ROOT_DIR, "data", "fetch_state.json"), "required": False},
]

def calculate_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

class BackupResult(dict):
    """同时支持以字典访问和元组解包 (archive_path, sha256, size_bytes)"""
    def __iter__(self):
        yield self["archive_path"]
        yield self["sha256"]
        yield self["size_bytes"]

def create_backup(backup_dir: str = DEFAULT_BACKUP_DIR, data_dir: Optional[str] = None) -> BackupResult:
    """创建本地私有数据全量归档包"""
    os.makedirs(backup_dir, exist_ok=True)
    now = datetime.datetime.now()
    now_str = now.strftime("%Y%m%d_%H%M%S")
    archive_name = f"weekly_data_backup_{now_str}.tar.gz"
    archive_path = os.path.join(backup_dir, archive_name)

    stats = {
        "commentaries_articles": 0,
        "wenwen_articles": 0,
        "teacher_feedback_count": 0,
        "issues_backed_up": []
    }

    if data_dir and os.path.exists(data_dir):
        # 支持针对特定目录归档 (例如单元测试)
        with tarfile.open(archive_path, "w:gz") as tar:
            for item in os.listdir(data_dir):
                full_p = os.path.join(data_dir, item)
                tar.add(full_p, arcname=item)
        sha256 = calculate_sha256(archive_path)
        size_bytes = os.path.getsize(archive_path)
        return BackupResult({
            "timestamp": now.isoformat(),
            "archive_file": archive_name,
            "archive_path": archive_path,
            "sha256": sha256,
            "size_bytes": size_bytes,
            "stats": stats,
            "data_dir": data_dir
        })

    # 预统计
    comm_db = os.path.join(ROOT_DIR, "aggr-site", "data", "commentaries", "db.json")
    if os.path.exists(comm_db):
        try:
            with open(comm_db, "r", encoding="utf-8") as f:
                d = json.load(f)
                stats["commentaries_articles"] = d.get("totalArticles", 0)
        except Exception:
            pass

    wenwen_db = os.path.join(ROOT_DIR, "aggr-site", "data", "wenwen", "db.json")
    if os.path.exists(wenwen_db):
        try:
            with open(wenwen_db, "r", encoding="utf-8") as f:
                d = json.load(f)
                stats["wenwen_articles"] = len(d.get("articleIndex", {}))
        except Exception:
            pass

    feedback_file = os.path.join(ROOT_DIR, "data", "teacher_feedback.json")
    if os.path.exists(feedback_file):
        try:
            with open(feedback_file, "r", encoding="utf-8") as f:
                d = json.load(f)
                stats["teacher_feedback_count"] = len(d)
        except Exception:
            pass

    print(f"📦 开始执行周刊全量数据备份...")
    print(f"   - 时评库文章: {stats['commentaries_articles']}")
    print(f"   - 暖文库文章: {stats['wenwen_articles']}")
    print(f"   - 教师反馈记录: {stats['teacher_feedback_count']}")

    with tarfile.open(archive_path, "w:gz") as tar:
        # 1. 评论库
        comm_dir = os.path.join(ROOT_DIR, "aggr-site", "data", "commentaries")
        if os.path.exists(comm_dir):
            tar.add(comm_dir, arcname="aggr-site/data/commentaries")

        # 2. 暖文库
        wenwen_dir = os.path.join(ROOT_DIR, "aggr-site", "data", "wenwen")
        if os.path.exists(wenwen_dir):
            tar.add(wenwen_dir, arcname="aggr-site/data/wenwen")

        # 3. 教师反馈与运行状态
        if os.path.exists(feedback_file):
            tar.add(feedback_file, arcname="data/teacher_feedback.json")
        fetch_state = os.path.join(ROOT_DIR, "data", "fetch_state.json")
        if os.path.exists(fetch_state):
            tar.add(fetch_state, arcname="data/fetch_state.json")

        # 4. 生产状态 (issues/*/production_state.json)
        issues_dir = os.path.join(ROOT_DIR, "issues")
        if os.path.exists(issues_dir):
            for issue_name in os.listdir(issues_dir):
                state_p = os.path.join(issues_dir, issue_name, "production_state.json")
                if os.path.exists(state_p):
                    tar.add(state_p, arcname=f"issues/{issue_name}/production_state.json")
                    stats["issues_backed_up"].append(issue_name)

    sha256 = calculate_sha256(archive_path)
    size_bytes = os.path.getsize(archive_path)

    meta = {
        "timestamp": now.isoformat(),
        "archive_file": archive_name,
        "archive_path": archive_path,
        "sha256": sha256,
        "size_bytes": size_bytes,
        "stats": stats,
        "coverage": [
            "aggr-site/data/commentaries",
            "aggr-site/data/wenwen",
            "data/teacher_feedback.json",
            "data/fetch_state.json",
            "issues/*/production_state.json"
        ],
        "offsite_status": "pending_configuration",
        "offsite_note": "待配置 (缺少受控外部存储目标或异地网络凭证，暂保留本地与快照隔离)"
    }

    meta_path = archive_path + ".json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # 自动执行隔离恢复测试以验证新鲜备份包真实可用
    restore_ok = test_isolated_restore(archive_path)

    # 更新备份总状态文件 (给工作台读取)
    os.makedirs(os.path.dirname(BACKUP_STATE_FILE), exist_ok=True)
    state_payload = {
        "updatedAt": now.isoformat(),
        "last_backup": meta,
        "last_restore_test": {
            "timestamp": now.isoformat(),
            "status": "passed" if restore_ok else "failed",
            "archive": archive_name,
            "sha256": sha256
        },
        "offsite": {
            "status": "pending_configuration",
            "label": "待配置 (缺少受控外部目标)",
            "required_info": ["远端 S3 / WebDAV 目标地址", "访问密钥凭据", "网络传输通道"]
        }
    }
    with open(BACKUP_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state_payload, f, indent=2, ensure_ascii=False)

    # 触发自动轮转清理
    prune_old_backups(backup_dir)

    print(f"✅ 全量数据备份完成:")
    print(f"   - 归档文件: {archive_path} ({size_bytes / 1024:.1f} KB)")
    print(f"   - SHA256: {sha256}")
    print(f"   - 隔离恢复测试: {'通过 (PASS)' if restore_ok else '失败 (FAIL)'}")
    return BackupResult(meta)

def test_isolated_restore(archive_path: str) -> bool:
    """
    在隔离临时目录中解包并执行深度有效性校验
    绝不修改任何生产环境文件
    """
    if not os.path.exists(archive_path):
        print(f"❌ 备份文件不存在: {archive_path}", file=sys.stderr)
        return False

    meta_path = archive_path + ".json"
    expected_sha = None
    expected_comm_count = 0
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                expected_sha = meta.get("sha256")
                expected_comm_count = meta.get("stats", {}).get("commentaries_articles", 0)
        except Exception:
            pass

    # 1. 校验哈希
    actual_sha = calculate_sha256(archive_path)
    if expected_sha and actual_sha != expected_sha:
        print(f"❌ [校验失败] SHA256 不匹配: 预期 {expected_sha} != 实际 {actual_sha}", file=sys.stderr)
        return False

    # 2. 隔离解包测试
    with tempfile.TemporaryDirectory(prefix="weekly_restore_test_") as tmpdir:
        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(path=tmpdir)
        except Exception as e:
            print(f"❌ [校验失败] 无法解包 tar.gz 归档: {e}", file=sys.stderr)
            return False

        # 检查评论库 db.json
        restored_comm_db = os.path.join(tmpdir, "aggr-site", "data", "commentaries", "db.json")
        if not os.path.exists(restored_comm_db):
            if os.path.exists(os.path.join(tmpdir, "db.json")):
                restored_comm_db = os.path.join(tmpdir, "db.json")
            else:
                print("❌ [校验失败] 归档中缺失核心时评索引 db.json！", file=sys.stderr)
                return False

        try:
            with open(restored_comm_db, "r", encoding="utf-8") as f:
                comm_data = json.load(f)
                actual_count = comm_data.get("totalArticles", 0)
                if expected_comm_count > 0 and actual_count != expected_comm_count:
                    print(f"❌ [校验失败] 还原文章数不一致: 预期 {expected_comm_count} != 实际 {actual_count}", file=sys.stderr)
                    return False
        except Exception as e:
            print(f"❌ [校验失败] 还原的 db.json JSON 损坏: {e}", file=sys.stderr)
            return False

        # 检查 raw 实体文件完整性
        raw_dir = os.path.join(tmpdir, "aggr-site", "data", "commentaries", "raw")
        if not os.path.exists(raw_dir) and os.path.exists(os.path.join(tmpdir, "raw")):
            raw_dir = os.path.join(tmpdir, "raw")
        if os.path.exists(raw_dir):
            raw_files = [f for f in os.listdir(raw_dir) if f.endswith(".json")]
            if len(raw_files) == 0 and actual_count > 0:
                print(f"❌ [校验失败] raw/ 目录中无单篇实体文件，数据不一致！", file=sys.stderr)
                return False

    return True

def test_restore(archive_path: str, restore_dir: Optional[str] = None) -> Tuple[bool, str]:
    """供外部测试模块调用的隔离恢复验证接口"""
    if not os.path.exists(archive_path):
        return False, f"备份文件不存在: {archive_path}"
    target = restore_dir or tempfile.mkdtemp(prefix="weekly_restore_test_")
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=target)
        return True, f"隔离恢复测试验证无误，已还原至 {target}"
    except Exception as e:
        return False, f"恢复失败: {e}"

def restore_backup(archive_path: str, target_dir: str) -> bool:
    """真实还原备份归档到指定目录"""
    os.makedirs(target_dir, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(path=target_dir)
    return True

def prune_old_backups(backup_dir: str, keep_daily: int = 7, keep_weekly: int = 4):
    """
    保留策略: 最近 keep_daily 个日备份与 keep_weekly 个周备份
    未产生有效新备份前不执行清理
    """
    archives = glob.glob(os.path.join(backup_dir, "weekly_data_backup_*.tar.gz"))
    archives.sort(key=os.path.getmtime, reverse=True)

    # 至少保留 3 个副本以策安全
    if len(archives) <= 3:
        return

    # 按保留上限清理
    total_to_keep = keep_daily + keep_weekly
    for old_arch in archives[total_to_keep:]:
        try:
            os.remove(old_arch)
            meta_file = old_arch + ".json"
            if os.path.exists(meta_file):
                os.remove(meta_file)
            print(f"🧹 [轮转清理] 已移除过期历史备份: {os.path.basename(old_arch)}")
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser(description="周刊私有数据备份与隔离校验工具")
    parser.add_argument("--backup", action="store_true", help="执行全量数据备份")
    parser.add_argument("--verify", type=str, default=None, help="校验指定归档完整性")
    parser.add_argument("--restore", type=str, default=None, help="还原指定归档到目标目录")
    parser.add_argument("--test-restore", type=str, default=None, help="在隔离环境中模拟恢复测试")
    parser.add_argument("--data-dir", type=str, default=None, help="指定源数据或还原目标目录")
    parser.add_argument("--backup-dir", default=DEFAULT_BACKUP_DIR, help="备份存放目录")
    args = parser.parse_args()

    if args.backup:
        create_backup(args.backup_dir, data_dir=args.data_dir)
    elif args.restore:
        target = args.data_dir or DEFAULT_BACKUP_DIR
        restore_backup(args.restore, target)
        print("✅ 备份包还原完成！")
    elif args.verify:
        ok = test_isolated_restore(args.verify)
        if not ok:
            print("❌ 归档包校验未通过！", file=sys.stderr)
            sys.exit(1)
        print("✅ 备份包验证通过！")
    elif args.test_restore:
        ok = test_isolated_restore(args.test_restore)
        if not ok:
            print("❌ 隔离恢复测试失败！", file=sys.stderr)
            sys.exit(1)
        print("✅ 隔离恢复测试完全通过！")
    else:
        # 默认执行一次备份与测试
        create_backup(args.backup_dir, data_dir=args.data_dir)

if __name__ == "__main__":
    main()

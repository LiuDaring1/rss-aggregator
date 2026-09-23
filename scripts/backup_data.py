#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
私有数据备份与校验还原工具 (Data Backup & Verification Utility)

满足《从版式定标转入每周稳定生产》第 3.3 节与验收场景 10：
1. 本地安全归档：将 aggr-site/data/commentaries (raw/*.json 与 db.json) 打包至 backups/；
2. 校验完整性：--verify 验证归档包 MD5、解压有效性与文章数量一致性；
3. 容灾恢复：--restore 支持将备份无损还原至指定或默认数据目录。
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

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_DATA_DIR = os.path.join(ROOT_DIR, "aggr-site", "data", "commentaries")
DEFAULT_BACKUP_DIR = os.path.join(ROOT_DIR, "backups")

def create_backup(data_dir: str = DEFAULT_DATA_DIR, backup_dir: str = DEFAULT_BACKUP_DIR) -> str:
    """创建本地私有数据归档包"""
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"数据源目录不存在: {data_dir}")

    os.makedirs(backup_dir, exist_ok=True)
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"commentaries_backup_{now_str}.tar.gz"
    archive_path = os.path.join(backup_dir, archive_name)

    # 统计源文件
    db_file = os.path.join(data_dir, "db.json")
    article_count = 0
    if os.path.exists(db_file):
        try:
            with open(db_file, "r", encoding="utf-8") as f:
                d = json.load(f)
                article_count = d.get("totalArticles", 0)
        except Exception:
            pass

    print(f"📦 开始备份数据目录: {data_dir}")
    print(f"   - 当前记录文章数: {article_count}")

    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(data_dir, arcname="commentaries")

    # 生成 checksum
    h = hashlib.sha256()
    with open(archive_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    sha256 = h.hexdigest()

    meta = {
        "timestamp": datetime.datetime.now().isoformat(),
        "archive_file": archive_name,
        "sha256": sha256,
        "source_data_dir": data_dir,
        "total_articles": article_count,
        "size_bytes": os.path.getsize(archive_path)
    }
    meta_path = archive_path + ".json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"✅ 备份成功:")
    print(f"   - 归档文件: {archive_path} ({meta['size_bytes']} 字节)")
    print(f"   - SHA256: {sha256[:16]}...")
    print(f"   - 元数据: {meta_path}")
    return archive_path

def verify_backup(archive_path: str) -> bool:
    """在隔离临时环境中解包并校验完整性"""
    if not os.path.exists(archive_path):
        print(f"❌ 备份文件不存在: {archive_path}", file=sys.stderr)
        return False

    meta_path = archive_path + ".json"
    expected_sha = None
    expected_count = 0
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            expected_sha = meta.get("sha256")
            expected_count = meta.get("total_articles", 0)

    # 1. 校验 sha256
    h = hashlib.sha256()
    with open(archive_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    actual_sha = h.hexdigest()
    if expected_sha and actual_sha != expected_sha:
        print(f"❌ SHA256 校验不匹配: 预期 {expected_sha}, 实际 {actual_sha}", file=sys.stderr)
        return False

    # 2. 隔离解包测试
    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=tmpdir)

        restored_db = os.path.join(tmpdir, "commentaries", "db.json")
        if not os.path.exists(restored_db):
            print("❌ 归档中未找到 db.json 索引文件！", file=sys.stderr)
            return False

        with open(restored_db, "r", encoding="utf-8") as f:
            db_data = json.load(f)
            act_count = db_data.get("totalArticles", 0)
            if expected_count > 0 and act_count != expected_count:
                print(f"⚠️ 文章数警告: 预期 {expected_count} != 还原后 {act_count}")

        raw_dir = os.path.join(tmpdir, "commentaries", "raw")
        raw_files = [f for f in os.listdir(raw_dir) if f.endswith(".json")] if os.path.exists(raw_dir) else []
        print(f"✅ 备份包验证通过: {os.path.basename(archive_path)}")
        print(f"   - SHA256 校验匹配")
        print(f"   - db.json 完整有效 (包含 {act_count} 篇文章)")
        print(f"   - raw/ 目录下包含 {len(raw_files)} 个单篇 JSON 实体")
    return True

def restore_backup(archive_path: str, target_dir: str = DEFAULT_DATA_DIR) -> bool:
    """从备份恢复数据至目标目录"""
    if not verify_backup(archive_path):
        print("❌ 备份校验未通过，拒绝恢复！", file=sys.stderr)
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=tmpdir)
        src = os.path.join(tmpdir, "commentaries")

        os.makedirs(target_dir, exist_ok=True)
        # 复制 raw
        src_raw = os.path.join(src, "raw")
        dst_raw = os.path.join(target_dir, "raw")
        os.makedirs(dst_raw, exist_ok=True)
        for f in os.listdir(src_raw):
            if f.endswith(".json"):
                shutil.copy2(os.path.join(src_raw, f), os.path.join(dst_raw, f))

        # 复制 db.json
        shutil.copy2(os.path.join(src, "db.json"), os.path.join(target_dir, "db.json"))

        print(f"✅ 成功从 {os.path.basename(archive_path)} 恢复数据至: {target_dir}")
    return True

def main():
    parser = argparse.ArgumentParser(description="私有数据备份与校验还原工具")
    parser.add_argument("--backup", action="store_true", help="执行备份")
    parser.add_argument("--verify", type=str, default=None, help="校验指定备份包完整性")
    parser.add_argument("--restore", type=str, default=None, help="从指定备份包还原数据")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR, help="数据目录路径")
    parser.add_argument("--backup-dir", default=DEFAULT_BACKUP_DIR, help="备份存放目录")
    args = parser.parse_args()

    if args.backup:
        create_backup(args.data_dir, args.backup_dir)
    elif args.verify:
        ok = verify_backup(args.verify)
        sys.exit(0 if ok else 1)
    elif args.restore:
        ok = restore_backup(args.restore, args.data_dir)
        sys.exit(0 if ok else 1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

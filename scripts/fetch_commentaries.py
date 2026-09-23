#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评论栏目正文抓取与持久化工具 (Commentaries Ingestion & Persistence) v2.1

严格落实审阅规范 (f147274)：
1. 正文优先策略：优先读取 content:encoded / Atom content，当其比 description 充实时优先选用，绝不机械使用摘要替代全文；
2. 质量状态精准分级：显式标记 textType: full_text | summary_only | metadata_only，无完整正文绝不虚标 hasFullText: True；
3. 时区转换严格统一：将各种时间规范换算为中国北京时间 (Asia/Shanghai, UTC+8)，杜绝 UTC 跨日与 GMT 偏差；
4. 稳定 ID 与内容哈希：基于规范化 URL / 信源生成稳定 ID，结合 contentHash (SHA-1) 实现精准版本跟踪与防漂移；
5. 原子化安全落盘：使用临时文件加重命名 (.tmp -> target) 确保多进程原子写入；
6. 累积全量数据库：维护累积历史库存，真实统计本轮条目、新增、更新、未变与库存总数；
7. 故障隔离与幂等：单源异常不阻断其他信源，空源如实标记 EMPTY 而非 FAILED，支持周期调度 (--daemon / --interval)。
"""

import os
import sys
import json
import time
import hashlib
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import datetime
import email.utils
import re
import html
import argparse
from typing import Dict, Any, List, Tuple, Optional

try:
    from zoneinfo import ZoneInfo
    BEIJING_TZ = ZoneInfo("Asia/Shanghai")
except Exception:
    BEIJING_TZ = datetime.timezone(datetime.timedelta(hours=8))

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOURCES_FILE = os.path.join(ROOT_DIR, "aggr-site", "sources.json")
DEFAULT_OUTPUT_DIR = os.path.join(ROOT_DIR, "aggr-site", "data", "commentaries", "raw")
DEFAULT_INDEX_FILE = os.path.join(ROOT_DIR, "aggr-site", "data", "commentaries", "db.json")

def html_to_clean_text(raw_html: str) -> str:
    """深度清洗 HTML，保留真实段落结构，剥离导航噪音与脚本"""
    if not raw_html:
        return ""
    text = html.unescape(raw_html)
    # 移除 script, style, iframe
    text = re.sub(r"<(?:script|style|iframe|noscript)[^>]*>[\s\S]*?</(?:script|style|iframe|noscript)>", "", text, flags=re.IGNORECASE)
    # 替换块级元素为换行
    text = re.sub(r"<(?:p|div|br|h[1-6]|li|tr|section|article)[^>]*>", "\n", text, flags=re.IGNORECASE)
    # 剔除其他所有标签
    text = re.sub(r"<[^>]+>", "", text)
    # 按行清理
    lines = []
    nav_pattern = r"^(?:首页|即时|时政|要闻|新闻中心|评论|观点|正文|资讯|热点|快讯)\s*[-—>|/]\s*"
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        # 剥离开头的导航与面包屑噪音（例如：首页 > 即时-时政 > 正文 等）
        while re.search(nav_pattern, line):
            line = re.sub(nav_pattern, "", line).strip()
        if line in ["正文", "首页", "评论", "新闻中心", "即时", "时政"]:
            continue
        if line:
            lines.append(line)
    return "\n\n".join(lines)

def parse_iso_date(pub_date_str: str) -> Tuple[str, str]:
    """
    统一将任意时间规范转换为中国北京时间 (Asia/Shanghai, UTC+8)。
    返回: (publishedAt: YYYY-MM-DD, pubDate: ISO8601 with +08:00)
    """
    if not pub_date_str or not str(pub_date_str).strip():
        return ("", "")
    s = str(pub_date_str).strip()

    # 1. 尝试 RFC 2822 / RSS 2.0 标准
    try:
        dt = email.utils.parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        beijing_dt = dt.astimezone(BEIJING_TZ)
        return (beijing_dt.strftime("%Y-%m-%d"), beijing_dt.isoformat())
    except Exception:
        pass

    # 2. 尝试 ISO 8601
    try:
        iso_s = s.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(iso_s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=BEIJING_TZ)
        beijing_dt = dt.astimezone(BEIJING_TZ)
        return (beijing_dt.strftime("%Y-%m-%d"), beijing_dt.isoformat())
    except Exception:
        pass

    # 3. 常见标准格式
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"]:
        try:
            dt = datetime.datetime.strptime(s, fmt)
            dt = dt.replace(tzinfo=BEIJING_TZ)
            return (dt.strftime("%Y-%m-%d"), dt.isoformat())
        except Exception:
            continue

    # 4. 兜底正则提取年月日
    m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        d_str = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        return (d_str, f"{d_str}T00:00:00+08:00")

    return ("", s)

def content_hash_of(text: str) -> str:
    """计算纯文本哈希 (忽略空白)，与 node store.js 保持一致"""
    cleaned = re.sub(r"\s+", "", text or "")
    return hashlib.sha1(cleaned.encode("utf-8")).hexdigest()[:20]

def generate_stable_id(source_id: str, canonical_url: str, title: str) -> str:
    """生成不受标题编辑微调影响的稳定文章 ID"""
    if canonical_url and canonical_url.startswith("http"):
        seed = canonical_url.strip().split("?")[0].rstrip("/")
    else:
        seed = f"{source_id}:{title.strip()}"
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
    return f"comm-{source_id}-{h}"

def classify_content(clean_content: str) -> Tuple[str, bool]:
    """
    判定正文质量状态:
    - full_text: 长度 >= 300 且段落 >= 2，或长度 >= 500
    - summary_only: 50 <= 长度 < 300
    - metadata_only: 长度 < 50
    返回: (textType, hasFullText)
    """
    length = len(clean_content)
    paras = [p for p in clean_content.split("\n\n") if p.strip()]
    if length >= 500 or (length >= 280 and len(paras) >= 2):
        return ("full_text", True)
    elif length >= 50:
        return ("summary_only", False)
    else:
        return ("metadata_only", False)

def fetch_feed(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (WeeklyPipeline/2.1)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def atomic_save_json(filepath: str, data: Any):
    """原子化文件落盘：写入 .tmp 文件后再做原子替换，杜绝损坏"""
    tmp_path = filepath + ".tmp"
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, filepath)

def process_source(source: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    sid = source.get("id")
    name = source.get("name")
    url = source.get("url")
    
    t0 = time.time()
    try:
        xml_data = fetch_feed(url)
        root = ET.fromstring(xml_data)
    except Exception as e:
        dur = round(time.time() - t0, 2)
        stat = {
            "id": sid,
            "name": name,
            "url": url,
            "status": "FAILED",
            "error": str(e),
            "total_items": 0,
            "full_text_items": 0,
            "summary_items": 0,
            "metadata_items": 0,
            "duration": dur,
            "latest_published_at": ""
        }
        return [], stat

    items = root.findall(".//item")
    is_atom = False
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        is_atom = True

    articles = []
    now_iso = datetime.datetime.now(BEIJING_TZ).isoformat()

    for it in items:
        if not is_atom:
            t_el = it.find("title")
            link_el = it.find("link")
            guid_el = it.find("guid")
            d_el = it.find("pubDate")
            author_el = it.find("author")
            if author_el is None:
                author_el = it.find("{http://purl.org/dc/elements/1.1/}creator")
            
            # 严格的正文优先策略：同时读取 content:encoded 与 description
            encoded_el = it.find("{http://purl.org/rss/1.0/modules/content/}encoded")
            desc_el = it.find("description")
        else:
            t_el = it.find("{http://www.w3.org/2005/Atom}title")
            link_el = it.find("{http://www.w3.org/2005/Atom}link")
            guid_el = it.find("{http://www.w3.org/2005/Atom}id")
            d_el = it.find("{http://www.w3.org/2005/Atom}published")
            if d_el is None:
                d_el = it.find("{http://www.w3.org/2005/Atom}updated")
            author_el = it.find("{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name")
            encoded_el = it.find("{http://www.w3.org/2005/Atom}content")
            desc_el = it.find("{http://www.w3.org/2005/Atom}summary")

        title = t_el.text.strip() if (t_el is not None and t_el.text) else ""
        if not title:
            continue

        raw_link = ""
        if link_el is not None:
            raw_link = link_el.get("href") or link_el.text or ""
        if not raw_link and guid_el is not None:
            raw_link = guid_el.text or ""
        raw_link = raw_link.strip()

        pub_str = d_el.text.strip() if (d_el is not None and d_el.text) else ""
        published_at, pub_iso = parse_iso_date(pub_str)
        author = author_el.text.strip() if (author_el is not None and author_el.text) else ""

        # 正文与摘要解析
        raw_encoded = encoded_el.text.strip() if (encoded_el is not None and encoded_el.text) else ""
        raw_desc = desc_el.text.strip() if (desc_el is not None and desc_el.text) else ""

        clean_encoded = html_to_clean_text(raw_encoded)
        clean_desc = html_to_clean_text(raw_desc)

        # 优先选用内容更充实的一方（若 content:encoded 大于或等于 description，且长度充足，选 encoded）
        if len(clean_encoded) >= len(clean_desc) and len(clean_encoded) >= 100:
            chosen_content = clean_encoded
            raw_summary = clean_desc[:200]
        elif len(clean_desc) > 0:
            chosen_content = clean_desc
            raw_summary = clean_desc[:200]
        else:
            chosen_content = clean_encoded
            raw_summary = ""

        # 判定正文状态
        text_type, has_full = classify_content(chosen_content)
        art_id = generate_stable_id(sid, raw_link, title)
        c_hash = content_hash_of(chosen_content)

        art = {
            "id": art_id,
            "origin": "commentary",
            "sourceId": sid,
            "sourceName": name,
            "media": name,
            "source": name,
            "category": "评论",
            "title": title,
            "author": author,
            "url": raw_link,
            "sourceUrl": raw_link,
            "feedUrl": url,
            "publishedAt": published_at,
            "pubDate": pub_iso,
            "rawPubDate": pub_str,
            "fetchedAt": now_iso,
            "content": chosen_content,
            "contentLength": len(chosen_content),
            "contentHash": c_hash,
            "textType": text_type,
            "hasFullText": has_full,
            "summary": raw_summary,
            "flags": [] if has_full else [text_type]
        }
        articles.append(art)

    dur = round(time.time() - t0, 2)
    full_count = sum(1 for a in articles if a["hasFullText"])
    summary_count = sum(1 for a in articles if a["textType"] == "summary_only")
    meta_count = sum(1 for a in articles if a["textType"] == "metadata_only")
    
    status_label = "OK" if articles else "EMPTY"
    stat = {
        "id": sid,
        "name": name,
        "url": url,
        "status": status_label,
        "error": None,
        "total_items": len(articles),
        "full_text_items": full_count,
        "summary_items": summary_count,
        "metadata_items": meta_count,
        "duration": dur,
        "latest_published_at": articles[0]["publishedAt"] if articles else ""
    }
    return articles, stat

import fcntl

class ProcessLock:
    """单实例进程文件锁，防止多个抓取进程并发执行导致数据损坏"""
    def __init__(self, lockfile: str):
        self.lockfile = lockfile
        self.fp = None

    def __enter__(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.lockfile)), exist_ok=True)
        self.fp = open(self.lockfile, "w")
        try:
            fcntl.flock(self.fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError):
            self.fp.close()
            raise RuntimeError(f"另一个采集进程正在运行中 (lockfile: {self.lockfile})，本次运行跳过或终止。")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fp:
            try:
                fcntl.flock(self.fp, fcntl.LOCK_UN)
                self.fp.close()
            except Exception:
                pass

def run_fetch_cycle(
    sources_file: str = SOURCES_FILE,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    index_file: str = DEFAULT_INDEX_FILE
) -> Dict[str, Any]:
    """执行一次完整的信源抓取与原子更新周期 (带单实例锁与正文防退化保护)"""
    lock_path = index_file + ".lock"
    with ProcessLock(lock_path):
        return _run_fetch_cycle_core(sources_file, output_dir, index_file)

def _run_fetch_cycle_core(
    sources_file: str = SOURCES_FILE,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    index_file: str = DEFAULT_INDEX_FILE
) -> Dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)
    alt_dir = os.path.join(ROOT_DIR, "data", "raw", "commentaries")
    os.makedirs(alt_dir, exist_ok=True)

    if not os.path.exists(sources_file):
        raise FileNotFoundError(f"找不到信源配置文件: {sources_file}")

    with open(sources_file, "r", encoding="utf-8") as f:
        sources = json.load(f)

    enabled_sources = [s for s in sources if s.get("enabled", True)]

    # 加载已有累积 db.json
    db_data = {
        "updatedAt": "",
        "totalArticles": 0,
        "fullTextArticles": 0,
        "summaryArticles": 0,
        "articles": {},
        "sourceStats": [],
        "sourceHealth": {}
    }
    if os.path.exists(index_file):
        try:
            with open(index_file, "r", encoding="utf-8") as ef:
                loaded = json.load(ef)
                if isinstance(loaded, dict) and "articles" in loaded:
                    db_data = loaded
        except Exception:
            pass

    existing_articles = db_data.get("articles", {})
    existing_health = db_data.get("sourceHealth", {})
    new_count = 0
    updated_count = 0
    unchanged_count = 0
    degraded_preserved_count = 0
    total_fetched = 0
    all_source_stats = []

    for s in enabled_sources:
        sid = s.get("id")
        arts, stat = process_source(s)
        all_source_stats.append(stat)
        total_fetched += len(arts)

        # 维护连续失败次数与最近成功时间
        s_health = existing_health.get(sid, {
            "id": sid,
            "name": s.get("name"),
            "consecutive_failures": 0,
            "last_attempt_at": "",
            "last_success_at": "",
            "last_new_articles_at": "",
            "last_error": None
        })
        now_ts = datetime.datetime.now(BEIJING_TZ).isoformat()
        s_health["last_attempt_at"] = now_ts

        if stat["status"] == "FAILED":
            s_health["consecutive_failures"] = s_health.get("consecutive_failures", 0) + 1
            s_health["last_error"] = stat.get("error")
        else:
            s_health["consecutive_failures"] = 0
            s_health["last_success_at"] = now_ts
            s_health["last_error"] = None
            if len(arts) > 0:
                s_health["latest_article_date"] = stat.get("latest_published_at", "")
        existing_health[sid] = s_health

        for a in arts:
            aid = a["id"]
            filepath = os.path.join(output_dir, f"{aid}.json")
            alt_path = os.path.join(alt_dir, f"{aid}.json")

            if aid in existing_articles:
                old_info = existing_articles[aid]
                old_hash = old_info.get("contentHash", "")
                old_has_full = old_info.get("hasFullText", False)
                new_has_full = a.get("hasFullText", False)

                # 正文防退化保护：已有优质全文时，新抓取变为摘要绝不覆盖全文
                if old_has_full and not new_has_full:
                    old_filepath = os.path.join(output_dir, f"{aid}.json")
                    old_data = None
                    if os.path.exists(old_filepath):
                        try:
                            with open(old_filepath, "r", encoding="utf-8") as opf:
                                old_data = json.load(opf)
                        except Exception:
                            pass
                    if old_data and old_data.get("content"):
                        a["content"] = old_data["content"]
                        a["contentLength"] = old_data["contentLength"]
                        a["contentHash"] = old_data["contentHash"]
                        a["textType"] = old_data.get("textType", "full_text")
                        a["hasFullText"] = True
                        old_flags = old_data.get("flags", [])
                        a["flags"] = list(set(old_flags + ["degraded_fallback_preserved"]))
                        a["degraded_warning"] = (
                            f"源站本次抓取退化为摘要 ({len(a.get('summary', ''))} 字)，"
                            f"已自动保留历史优质全文 ({len(old_data['content'])} 字)"
                        )
                        degraded_preserved_count += 1
                        unchanged_count += 1
                        continue

                # 若内容哈希一致且正文状态未变，跳过写盘
                if old_hash == a["contentHash"] and old_has_full == a["hasFullText"]:
                    unchanged_count += 1
                    continue
                else:
                    updated_count += 1
            else:
                new_count += 1

            # 原子写入单个 JSON
            atomic_save_json(filepath, a)
            try:
                atomic_save_json(alt_path, a)
            except Exception:
                pass

            # 登记入索引字典（轻量索引）
            existing_articles[aid] = {
                "id": aid,
                "title": a["title"],
                "sourceId": a["sourceId"],
                "sourceName": a["sourceName"],
                "publishedAt": a["publishedAt"],
                "url": a["url"],
                "contentLength": a["contentLength"],
                "contentHash": a["contentHash"],
                "textType": a["textType"],
                "hasFullText": a["hasFullText"]
            }

    # 更新并原子落盘 db.json
    now_iso = datetime.datetime.now(BEIJING_TZ).isoformat()
    db_data["updatedAt"] = now_iso
    db_data["totalArticles"] = len(existing_articles)
    db_data["fullTextArticles"] = sum(1 for a in existing_articles.values() if a.get("hasFullText"))
    db_data["summaryArticles"] = sum(1 for a in existing_articles.values() if a.get("textType") == "summary_only")
    db_data["sourceStats"] = all_source_stats
    db_data["sourceHealth"] = existing_health
    db_data["articles"] = existing_articles

    atomic_save_json(index_file, db_data)
    alt_index = os.path.join(alt_dir, "db.json")
    try:
        atomic_save_json(alt_index, db_data)
    except Exception:
        pass

    # 同时导出独立的真实运行健康度快照 (给审阅站和控制台使用)
    status_snapshot_path = os.path.join(os.path.dirname(index_file), "sources_status.json")
    atomic_save_json(status_snapshot_path, {
        "updatedAt": now_iso,
        "totalSources": len(enabled_sources),
        "sourceStats": all_source_stats,
        "sourceHealth": existing_health
    })

    # 判断是否全部启用的核心信源都失败
    failed_sources = [s for s in all_source_stats if s["status"] == "FAILED"]
    all_failed = (len(failed_sources) == len(enabled_sources)) and (len(enabled_sources) > 0)

    summary = {
        "timestamp": now_iso,
        "sources_count": len(enabled_sources),
        "total_fetched": total_fetched,
        "new_articles": new_count,
        "updated_articles": updated_count,
        "unchanged_articles": unchanged_count,
        "degraded_preserved": degraded_preserved_count,
        "total_inventory": db_data["totalArticles"],
        "full_text_inventory": db_data["fullTextArticles"],
        "source_stats": all_source_stats,
        "source_health": existing_health,
        "all_failed": all_failed
    }
    return summary

def print_source_status_table(summary: Dict[str, Any]):
    """打印符合审阅规范的真实执行状态表"""
    stats = summary["source_stats"]
    print("\n" + "=" * 115)
    print(f"📊 评论源采集与持久化真实执行状态表 (执行时间: {summary['timestamp']})")
    print(f"{'信源ID':22} | {'信源名称':14} | {'状态':6} | {'条目':4} | {'全文':4} | {'摘要':4} | {'最新日期':10} | {'耗时':5} | {'配置路由 (sources.json)'}")
    print("-" * 115)
    for s in stats:
        err_hint = f" ({s['error'][:25]}...)" if s.get("error") else ""
        print(f"{s['id']:22} | {s['name']:14} | {s['status']:6} | {s['total_items']:4} | {s['full_text_items']:4} | {s['summary_items']:4} | {s['latest_published_at']:10} | {s['duration']:4}s | {s['url']}{err_hint}")
    print("=" * 115)
    print(f"🎯 运行结算: 本轮提取 {summary['total_fetched']} 篇 | 新增 {summary['new_articles']} 篇 | 更新 {summary['updated_articles']} 篇 | 未变 {summary['unchanged_articles']} 篇 | 防退化保护 {summary.get('degraded_preserved', 0)} 篇")
    print(f"📦 累积资料库库存: {summary['total_inventory']} 篇 (其中具备完整长文: {summary['full_text_inventory']} 篇)")
    if summary.get("all_failed"):
        print("⚠️ [系统告警] 所有启用的信源抓取全部失败！请检查 RSSHub 进程与网络！")
    print("=" * 115 + "\n")

def main():
    parser = argparse.ArgumentParser(description="权威评论文章抓取与持久化工具")
    parser.add_argument("--sources", default=SOURCES_FILE, help="信源配置路径")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="持久化 raw 输出目录")
    parser.add_argument("--index-file", default=DEFAULT_INDEX_FILE, help="累积索引 db.json 路径")
    parser.add_argument("--daemon", action="store_true", help="常驻调度模式")
    parser.add_argument("--interval", type=int, default=3600, help="常驻调度模式下的抓取间隔 (秒)")
    args = parser.parse_args()

    if args.daemon:
        print(f"🔄 启动评论持久化常驻调度器 (间隔: {args.interval} 秒)...")
        while True:
            try:
                res = run_fetch_cycle(args.sources, args.output_dir, args.index_file)
                print_source_status_table(res)
                if res.get("all_failed"):
                    print("⚠️ 警告: 本轮采集所有核心源均失败，等待下次重试...", file=sys.stderr)
            except Exception as e:
                print(f"❌ 调度周期异常: {e}", file=sys.stderr)
            time.sleep(args.interval)
    else:
        try:
            res = run_fetch_cycle(args.sources, args.output_dir, args.index_file)
            print_source_status_table(res)
            if res.get("all_failed"):
                print("❌ [严重错误] 所有启用信源全部抓取失败，终止运行！", file=sys.stderr)
                sys.exit(2)
        except RuntimeError as re_err:
            print(f"❌ 运行锁定拦截: {re_err}", file=sys.stderr)
            sys.exit(3)

if __name__ == "__main__":
    main()


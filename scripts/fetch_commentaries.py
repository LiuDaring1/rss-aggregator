#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评论栏目正文抓取与持久化工具 (Commentaries Ingestion & Persistence)

职责：
1. 读取 aggr-site/sources.json 中的 11 个权威评论信源；
2. 通过本地 RSSHub 服务抓取最新 XML Feed；
3. 解析完整元数据与正文（保留段落结构，剔除 HTML 标签）；
4. 以原子化 JSON 文件持久化落盘至 data/commentaries/raw/ 与 aggr-site/data/commentaries/raw/；
5. 生成汇总索引 db.json，供 prep.py 候选提取与采编 Agent 读取。
"""

import os
import sys
import json
import time
import hashlib
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import re
import html

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOURCES_FILE = os.path.join(ROOT_DIR, "aggr-site", "sources.json")
OUTPUT_DIR = os.path.join(ROOT_DIR, "aggr-site", "data", "commentaries", "raw")
INDEX_FILE = os.path.join(ROOT_DIR, "aggr-site", "data", "commentaries", "db.json")

def html_to_clean_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = html.unescape(raw_html)
    # 替换块级标签为换行
    text = re.sub(r"<(?:p|div|br|h[1-6]|li|tr|section|article)[^>]*>", "\n", text, flags=re.IGNORECASE)
    # 剔除其他所有标签
    text = re.sub(r"<[^>]+>", "", text)
    # 清理行并保留段落结构
    lines = [line.strip() for line in text.split("\n")]
    cleaned = "\n\n".join(line for line in lines if line)
    return cleaned

def parse_iso_date(pub_date_str: str) -> tuple[str, str]:
    """解析 pubDate/updated 字符串为 (publishedAt: YYYY-MM-DD, pubDate: ISO)"""
    if not pub_date_str:
        return ("", "")
    # 尝试多种日期解析
    for fmt in [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            dt = datetime.strptime(pub_date_str.strip(), fmt)
            return (dt.strftime("%Y-%m-%d"), dt.isoformat())
        except Exception:
            continue
    # 兜底正则提取 YYYY-MM-DD
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", pub_date_str)
    if m:
        d_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        return (d_str, f"{d_str}T00:00:00Z")
    return ("", pub_date_str)

def fetch_feed(url: str, timeout: int = 10) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (WeeklyPipeline/2.0)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def process_source(source: dict) -> list[dict]:
    sid = source.get("id")
    name = source.get("name")
    url = source.get("url")
    print(f"  📡 正在抓取 [{name}] ({sid}) <- {url} ...", flush=True)

    try:
        xml_data = fetch_feed(url)
        root = ET.fromstring(xml_data)
    except Exception as e:
        print(f"     ❌ 抓取失败: {e}", flush=True)
        return []

    items = root.findall(".//item")
    is_atom = False
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        is_atom = True

    articles = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for it in items:
        if not is_atom:
            t_el = it.find("title")
            link_el = it.find("link")
            guid_el = it.find("guid")
            d_el = it.find("pubDate")
            author_el = it.find("author")
            if author_el is None:
                author_el = it.find("{http://purl.org/dc/elements/1.1/}creator")
            desc_el = it.find("description")
            if desc_el is None:
                desc_el = it.find("{http://purl.org/rss/1.0/modules/content/}encoded")
        else:
            t_el = it.find("{http://www.w3.org/2005/Atom}title")
            link_el = it.find("{http://www.w3.org/2005/Atom}link")
            guid_el = it.find("{http://www.w3.org/2005/Atom}id")
            d_el = it.find("{http://www.w3.org/2005/Atom}published")
            if d_el is None:
                d_el = it.find("{http://www.w3.org/2005/Atom}updated")
            author_el = it.find("{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name")
            desc_el = it.find("{http://www.w3.org/2005/Atom}content")
            if desc_el is None:
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

        raw_content = desc_el.text.strip() if (desc_el is not None and desc_el.text) else ""
        clean_content = html_to_clean_text(raw_content)

        # 唯一 ID
        hash_seed = f"{sid}:{title}:{raw_link}"
        art_hash = hashlib.md5(hash_seed.encode("utf-8")).hexdigest()[:10]
        art_id = f"comm-{sid}-{art_hash}"

        has_full = len(clean_content) >= 150

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
            "publishedAt": published_at,
            "pubDate": pub_iso,
            "rawPubDate": pub_str,
            "fetchedAt": now_iso,
            "content": clean_content,
            "contentLength": len(clean_content),
            "hasFullText": has_full,
            "flags": [] if has_full else ["no_full_text"]
        }
        articles.append(art)

    print(f"     ✅ 提取成功: {len(articles)} 条 (正文充足: {sum(1 for a in articles if a['hasFullText'])})", flush=True)
    return articles

def main():
    print(f"🚀 开始采集与持久化权威评论文章...")
    print(f"   信源配置: {SOURCES_FILE}")
    print(f"   存储目录: {OUTPUT_DIR}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # 同时建立 data/raw/commentaries 软链或目录同步
    alt_dir = os.path.join(ROOT_DIR, "data", "raw", "commentaries")
    os.makedirs(alt_dir, exist_ok=True)

    if not os.path.exists(SOURCES_FILE):
        print(f"❌ 找不到信源配置文件: {SOURCES_FILE}", file=sys.stderr)
        sys.exit(1)

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)

    enabled_sources = [s for s in sources if s.get("enabled", True)]
    print(f"   已启用信源: {len(enabled_sources)} 个\n")

    all_articles = []
    source_stats = []

    for s in enabled_sources:
        t0 = time.time()
        arts = process_source(s)
        dur = round(time.time() - t0, 2)
        full_count = sum(1 for a in arts if a["hasFullText"])
        source_stats.append({
            "id": s["id"],
            "name": s["name"],
            "url": s["url"],
            "status": "OK" if arts else "FAILED",
            "total_items": len(arts),
            "full_text_items": full_count,
            "duration": dur,
            "latest_published_at": arts[0]["publishedAt"] if arts else ""
        })

        # 持久化单个 JSON
        for a in arts:
            filename = f"{a['id']}.json"
            filepath = os.path.join(OUTPUT_DIR, filename)
            # 若文件已存在且已有正文，则不重复覆盖，保护内容
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as ef:
                        old_data = json.load(ef)
                        if old_data.get("contentLength", 0) >= a["contentLength"] and old_data.get("contentLength", 0) > 0:
                            all_articles.append(old_data)
                            continue
                except Exception:
                    pass

            with open(filepath, "w", encoding="utf-8") as out:
                json.dump(a, out, ensure_ascii=False, indent=2)

            # 同时写到 alt_dir
            alt_path = os.path.join(alt_dir, filename)
            try:
                with open(alt_path, "w", encoding="utf-8") as out:
                    json.dump(a, out, ensure_ascii=False, indent=2)
            except Exception:
                pass

            all_articles.append(a)

    # 写入索引 db.json
    db_data = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "totalArticles": len(all_articles),
        "fullTextArticles": sum(1 for a in all_articles if a.get("hasFullText")),
        "sourceStats": source_stats
    }
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)

    alt_index = os.path.join(alt_dir, "db.json")
    try:
        with open(alt_index, "w", encoding="utf-8") as f:
            json.dump(db_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    print("\n" + "=" * 80)
    print("📊 评论源采集与入库状态汇总：")
    print(f"{'信源ID':22} | {'信源名称':14} | {'状态':6} | {'条目':4} | {'完整正文':8} | {'最新报道日期':12} | {'耗时'}")
    print("-" * 80)
    for stat in source_stats:
        print(f"{stat['id']:22} | {stat['name']:14} | {stat['status']:6} | {stat['total_items']:4} | {stat['full_text_items']:8} | {stat['latest_published_at']:12} | {stat['duration']}s")
    print("=" * 80)
    print(f"🎉 评论文章落盘完成！总文章数: {len(all_articles)}, 具备完整正文: {db_data['fullTextArticles']}")
    print(f"   索引文件: {INDEX_FILE}")

if __name__ == "__main__":
    main()

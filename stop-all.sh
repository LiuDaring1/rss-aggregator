#!/bin/bash
# 一键停止：we-mp-rss(8001) + RSSHub(1200) + 聚合站点(3000)
pkill -f "main.py -job" 2>/dev/null && echo "[OK] we-mp-rss 已停止" || echo "[-] we-mp-rss 未在运行"
pkill -f "tsx watch" 2>/dev/null && echo "[OK] RSSHub 已停止" || echo "[-] RSSHub 未在运行"
pkill -f "node server.js" 2>/dev/null && echo "[OK] 聚合站点已停止" || echo "[-] 聚合站点未在运行"

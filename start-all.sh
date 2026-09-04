#!/bin/bash
# 一键启动全部三个服务：we-mp-rss(8001) + RSSHub(1200) + 聚合站点(3000)
# 已启动过的服务会跳过。日志：we-mp-rss/we-mp-rss.log、rsshub/rsshub.log、aggr-site/server.log
set -e
cd "$(dirname "$0")"

# 启动 we-mp-rss（微信公众号聚合）
if curl -s -m 2 -o /dev/null http://127.0.0.1:8001/; then
  echo "[OK] we-mp-rss 已在运行 (8001)"
else
  echo "[..] 启动 we-mp-rss (8001) ..."
  nohup we-mp-rss/start-local.sh > we-mp-rss/we-mp-rss.log 2>&1 &
  echo "[OK] we-mp-rss 启动中，日志: we-mp-rss/we-mp-rss.log"
fi

# 启动 RSSHub（dev 模式，tsx watch，改路由代码热重载）
if curl -s -m 2 -o /dev/null http://127.0.0.1:1200/; then
  echo "[OK] RSSHub 已在运行 (1200)"
else
  echo "[..] 启动 RSSHub (1200) ..."
  (cd rsshub && nohup pnpm dev > rsshub.log 2>&1 &)
  echo "[OK] RSSHub 启动中，日志: rsshub/rsshub.log"
fi

# 启动聚合站点（默认 3000；若被其他程序占用则自动改用 3001）
# 用 /api/sources 识别自家服务，避免其他程序恰好占着端口被误判为"已在运行"
aggr_ours() { curl -s -m 2 "http://127.0.0.1:$1/api/sources" | grep -q '"id"'; }
AGGR_PORT=""
for p in 3000 3001; do
  if aggr_ours "$p"; then AGGR_PORT=$p; break; fi
done
if [ -n "$AGGR_PORT" ]; then
  echo "[OK] 聚合站点已在运行 ($AGGR_PORT)"
else
  AGGR_PORT=3000
  if curl -s -m 2 -o /dev/null http://127.0.0.1:3000/; then
    AGGR_PORT=3001
    echo "[..] 3000 被其他程序占用，聚合站点自动改用 3001 ..."
  else
    echo "[..] 启动聚合站点 ($AGGR_PORT) ..."
  fi
  (cd aggr-site && PORT=$AGGR_PORT nohup node server.js > server.log 2>&1 &)
  echo "[OK] 聚合站点启动中，日志: aggr-site/server.log"
fi

echo ""
echo "聚合网页:   http://127.0.0.1:$AGGR_PORT"
echo "RSSHub:     http://127.0.0.1:1200"
echo "we-mp-rss:  http://127.0.0.1:8001 (admin / admin@123)"

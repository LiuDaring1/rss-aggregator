#!/bin/bash
# 生成源码包：只含源码与配置模板，剔除依赖目录、运行时数据、日志、git 与缓存。
# 用法：./package.sh  →  生成 RSS订阅-源码包-<YYYYMMDD>.tar.gz
cd "$(dirname "$0")"

STAMP=$(date +%Y%m%d)
OUT="RSS订阅-源码包-${STAMP}.tar.gz"

EXCLUDES=(
  --exclude='*/node_modules' --exclude='node_modules'
  --exclude='*/__pycache__' --exclude='__pycache__'
  --exclude='*/.venv' --exclude='.venv'
  --exclude='*/.git' --exclude='.git'
  --exclude='*/data' --exclude='data'                    # we-mp-rss 运行时数据（含微信授权，勿打包！）
  --exclude='*/*.log' --exclude='*.log'                  # 运行日志
  --exclude='*/.npm-cache' --exclude='.npm-cache'
  --exclude='*/.pipcache' --exclude='.pipcache'
  --exclude='*/.arts' --exclude='.arts'                  # agent 运行时产物
  --exclude='*.tar.gz'                                   # 打包产物自身
  --exclude='we-mp-rss/tmp_shot_qr.png'                  # 临时二维码截图
  --exclude='rsshub/logs'                                # RSSHub 日志目录
  --exclude='aggr-site/ai.json'                          # GLM API 密钥（敏感，勿打包！）
)

tar -czf "$OUT" "${EXCLUDES[@]}" aggr-site rsshub we-mp-rss \
  README.md 使用说明.md 聚合站使用说明.md 自定义改动清单.md \
  start-all.sh stop-all.sh package.sh

echo "已生成: $OUT"
echo "（已剔除 node_modules/.venv/data/.git/日志/缓存，解压后需按 README 第 8 节重装依赖）"

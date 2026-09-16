#!/bin/bash
# ==============================================================================
# 口语素材周刊 · Agent 安全同步脚本
# 用法：
#   ./agent-sync.sh status               # 查看当前同步状态与安全检测
#   ./agent-sync.sh push "提交说明"       # 执行前置安全审查并推送到 GitHub
# ==============================================================================
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
BRANCH="antigravity-dev"

ACTION="${1:-status}"

# 安全自检：严禁泄露密钥与私密数据
security_check() {
    echo "🔍 正在进行前置安全审查..."
    
    # 1. 检查是否意外暂存敏感文件
    SENSITIVE_PATTERNS=("ai.json" "config.yaml" "teaching-private" ".env" "token" "password")
    for pattern in "${SENSITIVE_PATTERNS[@]}"; do
        if git status --porcelain | grep -i "$pattern" | grep -v "agent-sync.sh" > /dev/null; then
            echo "❌ 安全拦截：检测到敏感关键字文件准备提交: $pattern"
            echo "请检查 .gitignore 并剔除该文件后再尝试推送！"
            exit 1
        fi
    done

    # 2. 检查 git 跟踪列表中是否误入敏感文件
    if git ls-files | grep -E "ai\.json|config\.yaml|teaching-private" > /dev/null; then
        echo "❌ 安全拦截：Git 索引中已存在敏感配置或私密教学文件！"
        exit 1
    fi

    echo "✅ 前置安全审查通过：无敏感配置泄漏风险。"
}

case "$ACTION" in
    status)
        echo "=== 当前工作区状态 ==="
        git status -s
        echo "=== 远端连接情况 ==="
        git remote -v
        security_check
        ;;
    push)
        MSG="$2"
        if [ -z "$MSG" ]; then
            echo "❌ 请提供提交说明，例如: ./agent-sync.sh push '新增单脚鞋银行评论单元新稿'"
            exit 1
        fi

        CURRENT_BRANCH="$(git symbolic-ref --short HEAD)"
        if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
            echo "⚠️ 当前分支为 $CURRENT_BRANCH，自动切换至工作分支 $BRANCH..."
            git checkout -B "$BRANCH"
        fi

        security_check

        echo "📦 正在暂存合规变动..."
        git add .

        echo "🔄 检查远端最新提交并 rebase..."
        git fetch origin "$BRANCH" 2>/dev/null || true
        if git rev-parse --verify "origin/$BRANCH" >/dev/null 2>&1; then
            git pull --rebase origin "$BRANCH"
        fi

        echo "✍️ 正在提交..."
        git commit -m "$MSG" || echo "工作区无新增变动可提交"

        echo "🚀 正在推送到 GitHub (origin/$BRANCH)..."
        git push -u origin "$BRANCH"

        echo "🎉 成功推送到 GitHub 远端分支: origin/$BRANCH"
        echo "💡 后续 Agent 可通过 'git checkout $BRANCH && git pull' 同步进度与看板 AGENT_SYNC.md。"
        ;;
    *)
        echo "用法: ./agent-sync.sh [status|push '说明']"
        exit 1
        ;;
esac

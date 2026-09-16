#!/bin/bash
# ==============================================================================
# 口语素材周刊 · Agent 安全同步脚本 v1.1
# 用法：
#   ./agent-sync.sh status               # 查看当前同步状态与安全检测
#   ./agent-sync.sh push "提交说明"       # 执行前置安全审查并推送到 GitHub
# ==============================================================================
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if [ ! -d ".git" ]; then
    echo "❌ 错误：必须在 Git 仓库根目录运行此脚本！"
    exit 1
fi

BRANCH="antigravity-dev"
ACTION="${1:-status}"

security_check() {
    echo "🔍 正在进行前置深度安全审查..."
    
    # 1. 检查工作区是否有敏感文件准备暂存
    SENSITIVE_FILES=("aggr-site/ai.json" "we-mp-rss/config.yaml" "references/teaching-private" "_private" ".env")
    for pattern in "${SENSITIVE_FILES[@]}"; do
        if git status --porcelain | grep -E "(^|\s)$pattern" > /dev/null; then
            echo "❌ 安全拦截：检测到敏感文件变更尝试进入版本控制: $pattern"
            echo "请检查 .gitignore 并从暂存区剔除该文件后再尝试推送！"
            exit 1
        fi
    done

    # 2. 检查 git 索引/暂存区中是否误入敏感配置或私密教学文件
    if git ls-files | grep -E "ai\.json|config\.yaml|teaching-private|_private" > /dev/null; then
        echo "❌ 安全拦截：Git 跟踪列表中已存在敏感配置或私密文件！"
        exit 1
    fi

    # 3. 检查暂存区内容是否包含敏感词模式（API Key、学生真实隐私，排除脚本自身）
    if ! git diff --cached --quiet 2>/dev/null; then
        if git diff --cached -- ':!agent-sync.sh' | grep -E -i '("apiKey"\s*:\s*"[^"]{10,}"|sk-[a-zA-Z0-9]{20,}|Bearer\s+[a-zA-Z0-9]{20,}|鲁怡涵|徐思琪|朱思睿|陆萌)' > /dev/null; then
            echo "❌ 安全拦截：暂存区代码中检测到疑似明文密钥或学生真实姓名等隐私信息！"
            exit 1
        fi
    fi

    echo "✅ 前置安全审查通过：无敏感配置或学生隐私泄漏风险。"
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

        CURRENT_BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || echo 'HEAD')"
        if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
            echo "❌ 当前分支为 [$CURRENT_BRANCH]，不是目标协作分支 [$BRANCH]！"
            echo "请显式执行 'git checkout $BRANCH' 后再运行本脚本，禁止隐式破坏性分支切换。"
            exit 1
        fi

        echo "📦 正在暂存合规变动..."
        git add -A

        security_check

        echo "✍️ 正在提交..."
        if git diff --cached --quiet; then
            echo "ℹ️ 暂存区无新增变动可提交"
        else
            git commit -m "$MSG"
        fi

        echo "🔄 检查远端最新提交并尝试 rebase..."
        git fetch origin "$BRANCH" 2>/dev/null || true
        if git rev-parse --verify "origin/$BRANCH" >/dev/null 2>&1; then
            if ! git rebase "origin/$BRANCH"; then
                echo "❌ 远端存在冲突，Rebase 中断！请手动解决冲突后再推送，严禁覆盖他人提交。"
                exit 1
            fi
        fi

        echo "🚀 正在推送到 GitHub (origin/$BRANCH)..."
        git push origin "$BRANCH"

        echo "🎉 成功安全推送到 GitHub 远端分支: origin/$BRANCH"
        ;;
    *)
        echo "用法: ./agent-sync.sh [status|push '说明']"
        exit 1
        ;;
esac

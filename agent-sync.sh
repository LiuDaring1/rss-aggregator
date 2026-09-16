#!/bin/bash
# ==============================================================================
# 口语素材周刊 · Agent 安全同步脚本 v1.2
# 用法：
#   ./agent-sync.sh status                         # 查看当前同步状态与安全检测
#   ./agent-sync.sh push "提交说明" [files...]      # 校验已暂存文件并安全推送
# ==============================================================================
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "❌ 错误：必须在 Git 工作树内运行此脚本！"
    exit 1
fi

BRANCH="antigravity-dev"
ACTION="${1:-status}"
LOCAL_PATTERNS_FILE="local-data/sensitive_patterns.txt"

# 基础通用凭据检测规则（公开通用，绝不硬编码任何个人隐私）
BASE_CREDENTIAL_PATTERN='("apiKey"\s*:\s*"[^"]{10,}"|sk-[a-zA-Z0-9]{20,}|Bearer\s+[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36,})'

security_check() {
    echo "🔍 正在进行前置深度安全审查..."
    
    # 1. 检查是否有明确的私密/配置路径进入暂存或已跟踪
    SENSITIVE_PATHS=("aggr-site/ai.json" "we-mp-rss/config.yaml" "references/teaching-private" "_private" ".env")
    for pattern in "${SENSITIVE_PATHS[@]}"; do
        if git status --porcelain | grep -E "^[AMDRC].*${pattern}" > /dev/null 2>&1; then
            echo "❌ 安全拦截：检测到敏感文件变更处于暂存区: $pattern"
            echo "请从暂存区剔除该文件后再尝试操作！"
            exit 1
        fi
        if git ls-files | grep -E "${pattern}" > /dev/null 2>&1; then
            echo "❌ 安全拦截：Git 跟踪列表中已存在敏感路径: $pattern"
            exit 1
        fi
    done

    # 2. 组合扫描规则（含本地未跟踪配置）
    SCAN_PATTERNS="$BASE_CREDENTIAL_PATTERN"
    if [ -f "$LOCAL_PATTERNS_FILE" ]; then
        while IFS= read -r line || [ -n "$line" ]; do
            # 忽略注释和空行
            clean_line="$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
            if [ -n "$clean_line" ] && [[ ! "$clean_line" =~ ^# ]]; then
                SCAN_PATTERNS="${SCAN_PATTERNS}|${clean_line}"
            fi
        done < "$LOCAL_PATTERNS_FILE"
    fi

    # 3. 检查暂存区“新增内容”行（杜绝删除行被误报，无全文件豁免）
    if ! git diff --cached --quiet 2>/dev/null; then
        # 仅匹配本次暂存新增的代码行 (以 + 开头，排除 +++ 文件头)
        STAGED_ADDITIONS="$(git diff --cached -U0 | grep -E '^\+[^+]' || true)"
        if [ -n "$STAGED_ADDITIONS" ]; then
            if echo "$STAGED_ADDITIONS" | grep -E -i "$SCAN_PATTERNS" > /dev/null 2>&1; then
                echo "❌ 安全拦截：暂存区新增内容中检测到疑似明文密钥或未授权隐私信息！"
                echo "拦截说明：命中配置的敏感特征规则。请核查暂存文件，绝不在公开代码提交凭证。"
                exit 1
            fi
        fi
    fi

    # 4. 检查本地尚未推送到远端的新增提交
    if git rev-parse --verify "origin/$BRANCH" >/dev/null 2>&1; then
        PENDING_ADDITIONS="$(git log "origin/$BRANCH..HEAD" -p -U0 2>/dev/null | grep -E '^\+[^+]' || true)"
        if [ -n "$PENDING_ADDITIONS" ]; then
            if echo "$PENDING_ADDITIONS" | grep -E -i "$SCAN_PATTERNS" > /dev/null 2>&1; then
                echo "❌ 安全拦截：待推送到远端的本地提交中包含疑似敏感凭据！"
                exit 1
            fi
        fi
    fi

    echo "✅ 前置安全审查通过：未发现所配置规则的命中。"
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
        shift 2 || true
        EXTRA_FILES=("$@")

        if [ -z "$MSG" ]; then
            echo "❌ 请提供提交说明，例如: ./agent-sync.sh push 'fix: 补正导图答案与单元校验'"
            exit 1
        fi

        CURRENT_BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || echo 'HEAD')"
        if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
            echo "❌ 当前分支为 [$CURRENT_BRANCH]，不是目标协作分支 [$BRANCH]！"
            echo "请显式执行 'git checkout $BRANCH' 后再运行本脚本，禁止隐式破坏性分支切换。"
            exit 1
        fi

        # 如果命令行提供了具体文件，显式暂存它们；否则要求暂存区已有文件
        if [ ${#EXTRA_FILES[@]} -gt 0 ]; then
            echo "📦 显式暂存指定文件: ${EXTRA_FILES[*]}..."
            git add "${EXTRA_FILES[@]}"
        fi

        if git diff --cached --quiet; then
            echo "❌ 暂存区无已暂存的文件变动！"
            echo "请先使用 'git add <file>...' 显式暂存合规文件，或在 push 命令后指定文件。"
            exit 1
        fi

        security_check

        echo "✍️ 正在提交..."
        git commit -m "$MSG"

        echo "🔄 检查远端最新提交并尝试 rebase..."
        if ! git fetch origin "$BRANCH"; then
            echo "❌ 获取远端 origin/$BRANCH 失败，请检查网络或远端权限，推送已终止。"
            exit 1
        fi

        if ! git rebase "origin/$BRANCH"; then
            echo "❌ 远端存在冲突，Rebase 中断！请手动解决冲突后再推送，严禁覆盖他人提交。"
            exit 1
        fi

        # 提交后再做一次待推送范围安全检查
        security_check

        echo "🚀 正在推送到 GitHub (origin/$BRANCH)..."
        git push origin "$BRANCH"

        echo "🎉 成功安全推送到 GitHub 远端分支: origin/$BRANCH"
        ;;
    *)
        echo "用法: ./agent-sync.sh status"
        echo "      ./agent-sync.sh push '提交说明' [file1 file2 ...]"
        exit 1
        ;;
esac

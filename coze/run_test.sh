#!/bin/bash

# Coze Studio 测试运行脚本
# 使用方法: ./run_test.sh API_KEY BOT_ID [BASE_URL]

set -e

# 检查参数
if [ $# -lt 2 ]; then
    echo "使用方法: $0 API_KEY BOT_ID [BASE_URL]"
    echo ""
    echo "参数说明:"
    echo "  API_KEY   Coze API 密钥 (必需)"
    echo "  BOT_ID    Coze Bot ID (必需)"
    echo "  BASE_URL  Coze API 基础URL (可选，默认 https://api.coze.com)"
    echo ""
    echo "示例:"
    echo "  $0 pat_xxx 7445781234567890123"
    echo "  $0 pat_xxx 7445781234567890123 https://api.coze.com"
    exit 1
fi

API_KEY="$1"
BOT_ID="$2"
BASE_URL="${3:-http://8.163.26.178:21998}"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=================================================="
echo "Coze Studio 测试脚本"
echo "=================================================="
echo "API Key: ${API_KEY:0:10}..." 
echo "Bot ID: $BOT_ID"
echo "Base URL: $BASE_URL"
echo "Project Root: $PROJECT_ROOT"
echo "=================================================="

# 进入项目根目录
cd "$PROJECT_ROOT"

# 检查 uv 是否可用
if ! command -v uv &> /dev/null; then
    echo "❌ 错误: uv 未安装或不在 PATH 中"
    echo "请安装 uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# 同步依赖
echo "🔄 同步项目依赖..."
uv sync

# 运行测试
echo "🚀 开始运行测试..."
echo ""

uv run python coze/test_coze_studio.py \
    --api-key "$API_KEY" \
    --bot-id "$BOT_ID" \
    --base-url "$BASE_URL" \
    --save-report \
    --report-file "coze_test_report_$(date +%Y%m%d_%H%M%S).json"

echo ""
echo "✅ 测试完成！"
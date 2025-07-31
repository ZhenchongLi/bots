#!/bin/bash

# 获取当前默认管理员API密钥的辅助脚本

echo "🔍 正在查找当前的默认管理员API密钥..."
echo ""

# 检查服务是否在运行
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ 服务器未运行在 http://localhost:8000"
    echo "📝 请先启动服务: ./run.sh"
    exit 1
fi

# 查看最近的日志输出寻找API密钥
echo "📋 请从服务器启动日志中找到类似下面的输出："
echo ""
echo "🔑 Default Admin API Key: officeai-admin-xxxxxxxxxxxxx"
echo ""
echo "💡 然后设置环境变量并运行测试："
echo "   export OFFICEAI_ADMIN_KEY='officeai-admin-xxxxxxxxxxxxx'"
echo "   ./test_officeai_api.sh"
echo ""
echo "或者直接运行："
echo "   OFFICEAI_ADMIN_KEY='officeai-admin-xxxxxxxxxxxxx' ./test_officeai_api.sh"
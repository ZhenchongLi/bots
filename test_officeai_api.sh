#!/bin/bash

# OfficeAI API 测试脚本
# 注意：API密钥现在由系统自动生成和管理，每次启动可能不同
# 请从服务器启动日志中获取当前的默认管理员API密钥

# 默认使用环境变量中的API密钥，如果没有则提示用户
if [ -z "$OFFICEAI_ADMIN_KEY" ]; then
    echo "⚠️  请设置环境变量 OFFICEAI_ADMIN_KEY"
    echo "📋 从服务器启动日志中复制默认管理员API密钥，例如："
    echo "   export OFFICEAI_ADMIN_KEY='officeai-admin-xxxxxxxxxxxxx'"
    echo ""
    echo "💡 或者直接设置并运行："
    echo "   OFFICEAI_ADMIN_KEY='your-admin-key-here' ./test_officeai_api.sh"
    echo ""
    exit 1
fi

API_KEY="$OFFICEAI_ADMIN_KEY"
BASE_URL="http://localhost:8000"

echo "🤖 OfficeAI API 测试开始"
echo "=================================="
echo "🔑 使用API密钥: ${API_KEY:0:20}..."
echo "📝 注意：不管客户端传递什么模型名，服务端都会使用 .env 配置的实际模型"
echo "🔄 模型名映射：客户端任意模型名 ➜ 服务端配置的 ACTUAL_NAME 模型"
echo "🗄️  客户端信息已持久化存储在数据库中"

echo ""
echo "1. 📋 测试模型列表 (返回代理模型信息)"
echo "curl -H \"Authorization: Bearer $API_KEY\" $BASE_URL/v1/models"
echo ""
curl -H "Authorization: Bearer $API_KEY" $BASE_URL/v1/models | jq .

echo ""
echo "=================================="
echo "2. 💬 测试聊天完成 (客户端模型名会被替换为配置的实际模型)"
echo 'curl -X POST -H "Authorization: Bearer $API_KEY" \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '\''{"model":"gpt-4","messages":[{"role":"user","content":"Hello, how are you?"}],"max_tokens":50}'\'' \'
echo "  $BASE_URL/v1/chat/completions"
echo "👆 虽然传递了 gpt-4，但实际调用的是 .env 中配置的模型"
echo ""
curl -X POST -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"Hello, how are you?"}],"max_tokens":50}' \
  $BASE_URL/v1/chat/completions | jq .

echo ""
echo "=================================="
echo "3. 🔑 查看现有API密钥"
echo "curl -H \"Authorization: Bearer $API_KEY\" $BASE_URL/admin/api-keys"
echo ""
curl -H "Authorization: Bearer $API_KEY" $BASE_URL/admin/api-keys | jq .

echo ""
echo "=================================="
echo "4. ➕ 创建新的API密钥"
echo 'curl -X POST -H "Authorization: Bearer $API_KEY" \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '\''{"key_id":"my_test_key","description":"我的测试密钥","permissions":["chat","completion"],"expires_days":30}'\'' \'
echo "  $BASE_URL/admin/api-keys"
echo ""
NEW_KEY_RESPONSE=$(curl -s -X POST -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"key_id":"my_test_key","description":"我的测试密钥","permissions":["chat","completion"],"expires_days":30}' \
  $BASE_URL/admin/api-keys)

echo $NEW_KEY_RESPONSE | jq .

# 提取新创建的API key
NEW_API_KEY=$(echo $NEW_KEY_RESPONSE | jq -r '.api_key // empty')

if [ ! -z "$NEW_API_KEY" ] && [ "$NEW_API_KEY" != "null" ]; then
    echo ""
    echo "=================================="
    echo "5. ✅ 测试新创建的API密钥"
    echo "新密钥: $NEW_API_KEY"
    echo ""
    echo "测试新密钥访问模型列表:"
    curl -H "Authorization: Bearer $NEW_API_KEY" $BASE_URL/v1/models | jq .
    
    echo ""
    echo "测试新密钥聊天功能 (传递 claude-3-opus，实际使用配置的模型):"
    curl -X POST -H "Authorization: Bearer $NEW_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"model":"claude-3-opus","messages":[{"role":"user","content":"Test with new key"}]}' \
      $BASE_URL/v1/chat/completions | jq .
fi

echo ""
echo "=================================="
echo "6. 📊 测试完整性检查"
echo ""

# 测试多种不同模型名 (都会被替换为配置的实际模型)
echo "测试不同客户端模型名 (都会使用相同的配置模型):"
echo ""
echo "🔹 测试1: 传递 gemini-pro"
curl -X POST -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini-pro","messages":[{"role":"user","content":"Test 1"}]}' \
  $BASE_URL/v1/chat/completions | jq .

echo ""
echo "🔹 测试2: 传递 claude-3-sonnet"
curl -X POST -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-3-sonnet","messages":[{"role":"user","content":"Test 2"}]}' \
  $BASE_URL/v1/chat/completions | jq .

echo ""
echo "🔹 测试3: 传递 llama-2-70b"
curl -X POST -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-2-70b","messages":[{"role":"user","content":"Test 3"}]}' \
  $BASE_URL/v1/chat/completions | jq .

echo ""
echo "👆 所有不同的客户端模型名都会被替换为 .env 中配置的同一个实际模型"

echo ""
echo "测试无效API密钥 (应该返回401错误):"
curl -H "Authorization: Bearer invalid-key-123" $BASE_URL/v1/models | jq .

echo ""
echo "🎉 测试完成!"
echo "=================================="
echo ""
echo "📋 关于新的客户端认证系统："
echo "  • API密钥现在持久化存储在数据库中"
echo "  • 服务启动时自动检查并创建默认客户端"
echo "  • 同一个数据库实例重启后API密钥保持不变"
echo "  • 支持通过管理API创建和管理多个客户端密钥"
echo ""
echo "🔧 管理建议："
echo "  • 生产环境中应创建新的管理员密钥并撤销默认密钥"
echo "  • 为不同应用创建具有特定权限的专用API密钥"
echo "  • 定期轮换API密钥以确保安全性"
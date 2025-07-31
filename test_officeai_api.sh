#!/bin/bash

# OfficeAI API 测试脚本
# API Key: officeai-admin-79222376bda3186039336d460f7150c7

API_KEY="default-441e7c0b5a98e746662047cb948a4431"
BASE_URL="http://localhost:8000"

echo "🤖 OfficeAI API 测试开始"
echo "=================================="
echo "📝 注意：不管客户端传递什么模型名，服务端都会使用 .env 配置的实际模型"
echo "🔄 模型名映射：客户端任意模型名 ➜ 服务端配置的 ACTUAL_NAME 模型"

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
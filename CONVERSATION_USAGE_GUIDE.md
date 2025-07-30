# 会话记录功能使用指南

## 功能概述

已为OfficeAI API代理服务添加了会话记录功能，可以保存用户的历史对话到数据库中。该功能支持：

- 自动记录用户与AI的对话
- 按用户分组管理会话
- 获取历史对话记录
- 会话标题管理
- 支持多种AI模型的对话记录

## API接口

### 1. 创建会话
```http
POST /conversations/
Content-Type: application/json
Authorization: Bearer your-api-key

{
  "user_identifier": "user123",
  "title": "我的会话",
  "session_id": "optional-custom-session-id"
}
```

### 2. 获取用户的所有会话
```http
GET /conversations/user/user123?limit=50&offset=0
Authorization: Bearer your-api-key
```

### 3. 获取特定会话及其消息
```http
GET /conversations/{session_id}
Authorization: Bearer your-api-key
```

### 4. 向会话添加消息
```http
POST /conversations/{session_id}/messages
Content-Type: application/json
Authorization: Bearer your-api-key

{
  "role": "user",
  "content": "你好，请帮我解释一下Python装饰器",
  "model_name": "gpt-3.5-turbo",
  "token_count": 15
}
```

### 5. 获取会话的所有消息
```http
GET /conversations/{session_id}/messages?limit=100
Authorization: Bearer your-api-key
```

### 6. 更新会话标题
```http
PUT /conversations/{session_id}
Content-Type: application/json
Authorization: Bearer your-api-key

{
  "title": "新的会话标题"
}
```

### 7. 删除会话
```http
DELETE /conversations/{session_id}
Authorization: Bearer your-api-key
```

## 自动会话记录

### 在OpenAI API调用中启用会话记录

在调用OpenAI API时，可以通过添加特定的HTTP头来启用自动会话记录：

```http
POST /v1/chat/completions
Content-Type: application/json
Authorization: Bearer your-api-key
X-Session-ID: unique-session-id
X-User-ID: user123

{
  "model": "officeai",
  "messages": [
    {
      "role": "user", 
      "content": "你好，请介绍一下Python"
    }
  ]
}
```

**重要的HTTP头：**
- `X-Session-ID`: 会话唯一标识符，如果会话不存在会自动创建
- `X-User-ID`: 用户标识符（可选，默认使用客户端IP）

### 自动记录的内容

当你使用上述HTTP头调用OpenAI API时，系统会自动：

1. 记录用户的输入消息
2. 记录AI的回复消息
3. 保存使用的模型名称
4. 记录时间戳
5. 如果会话不存在，会自动创建新会话

## 使用示例

### Python客户端示例

```python
import requests
import uuid

# API配置
base_url = "http://localhost:8000"
api_key = "your-api-key"
session_id = str(uuid.uuid4())
user_id = "user123"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# 1. 发起对话并自动记录
chat_response = requests.post(
    f"{base_url}/v1/chat/completions",
    headers={
        **headers,
        "X-Session-ID": session_id,
        "X-User-ID": user_id
    },
    json={
        "model": "officeai",
        "messages": [
            {"role": "user", "content": "你好，请介绍一下Python编程语言"}
        ]
    }
)

print("AI回复:", chat_response.json())

# 2. 获取会话历史
history_response = requests.get(
    f"{base_url}/conversations/{session_id}",
    headers=headers
)

print("会话历史:", history_response.json())

# 3. 获取用户的所有会话
user_conversations = requests.get(
    f"{base_url}/conversations/user/{user_id}",
    headers=headers
)

print("用户所有会话:", user_conversations.json())
```

### JavaScript/Node.js示例

```javascript
const axios = require('axios');
const { v4: uuidv4 } = require('uuid');

const baseURL = 'http://localhost:8000';
const apiKey = 'your-api-key';
const sessionId = uuidv4();
const userId = 'user123';

const headers = {
    'Authorization': `Bearer ${apiKey}`,
    'Content-Type': 'application/json'
};

async function chatWithHistory() {
    try {
        // 发起对话并自动记录
        const chatResponse = await axios.post(`${baseURL}/v1/chat/completions`, {
            model: 'officeai',
            messages: [
                { role: 'user', content: '请解释什么是机器学习' }
            ]
        }, {
            headers: {
                ...headers,
                'X-Session-ID': sessionId,
                'X-User-ID': userId
            }
        });

        console.log('AI回复:', chatResponse.data);

        // 获取会话历史
        const historyResponse = await axios.get(
            `${baseURL}/conversations/${sessionId}`,
            { headers }
        );

        console.log('会话历史:', historyResponse.data);

    } catch (error) {
        console.error('错误:', error.response?.data || error.message);
    }
}

chatWithHistory();
```

### cURL示例

```bash
# 设置变量
API_KEY="your-api-key"
BASE_URL="http://localhost:8000"
SESSION_ID=$(uuidgen)
USER_ID="user123"

# 1. 发起对话并自动记录
curl -X POST "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: ${SESSION_ID}" \
  -H "X-User-ID: ${USER_ID}" \
  -d '{
    "model": "officeai",
    "messages": [
      {"role": "user", "content": "什么是深度学习？"}
    ]
  }'

# 2. 获取会话历史
curl -X GET "${BASE_URL}/conversations/${SESSION_ID}" \
  -H "Authorization: Bearer ${API_KEY}"

# 3. 手动添加消息到会话
curl -X POST "${BASE_URL}/conversations/${SESSION_ID}/messages" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": "请给我更多关于深度学习的信息",
    "model_name": "gpt-3.5-turbo"
  }'
```

## 数据库结构

### 会话表 (conversations)
- `id`: 主键
- `session_id`: 会话唯一标识符
- `title`: 会话标题
- `user_identifier`: 用户标识符
- `created_at`: 创建时间
- `updated_at`: 更新时间

### 消息表 (conversation_messages)
- `id`: 主键
- `conversation_id`: 关联的会话ID
- `role`: 消息角色 ('user', 'assistant', 'system')
- `content`: 消息内容
- `model_name`: 使用的模型名称
- `token_count`: 令牌数量
- `timestamp`: 消息时间戳

## 注意事项

1. **认证**: 所有API调用都需要有效的API密钥
2. **会话ID**: 建议使用UUID作为会话ID以确保唯一性
3. **用户标识**: 如果不提供X-User-ID头，系统会使用客户端IP作为用户标识
4. **性能**: 会话记录是异步进行的，不会影响API调用的性能
5. **错误处理**: 会话记录失败不会导致主要API调用失败

## API文档

启动服务器后，可以访问 `http://localhost:8000/docs` 查看完整的API文档。
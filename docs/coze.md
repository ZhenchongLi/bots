
# Coze Bot API 与 OpenAI API 兼容方案

基于统一 AI API 代理服务的 Coze Bot 适配器实现，提供完全兼容 OpenAI API 的接口。

## 1. 核心架构概述

### 适配器模式
- 使用适配器模式实现 Coze v3 API 与 OpenAI API 的透明转换
- Python 程序可以使用标准的 OpenAI Python SDK，无需修改现有代码
- 系统自动处理请求/响应格式转换和模型名称映射
- 支持流式和非流式响应

## 2. 请求转换详细方案

### 2.1 请求 URL 构建

```python
# 客户端调用 OpenAI 兼容接口
client_url = "http://localhost:8000/v1/chat/completions"

# 内部转换为 Coze v3 API
coze_url = f"{base_url}/v3/chat"
```

### 2.2 认证头设置

```python
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
```

### 2.3 请求体转换逻辑

**OpenAI 格式输入:**
```json
{
    "model": "bot-7533263489985413120",
    "messages": [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"}
    ],
    "stream": true,
    "user": "user123"
}
```

**转换为 Coze v3 格式:**
```json
{
    "bot_id": "7533263489985413120",
    "user_id": "user123",
    "additional_messages": [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"}
    ],
    "stream": true
}
```

### 2.4 转换实现代码

```python
def convert_openai_to_coze_v3(openai_request):
    # 提取 Bot ID
    model = openai_request["model"]
    if model.startswith("bot-"):
        bot_id = model[4:]  # 去掉 "bot-" 前缀
    else:
        bot_id = model

    messages = openai_request["messages"]
    
    # v3 API 使用 additional_messages 格式
    additional_messages = []
    for message in messages:
        additional_messages.append({
            "role": message["role"],
            "content": message["content"]
        })

    coze_request = {
        "bot_id": bot_id,
        "user_id": openai_request.get("user", "default_user"),
        "additional_messages": additional_messages,
        "stream": openai_request.get("stream", False)
    }

    return coze_request
```

## 3. 响应转换详细方案

### 3.1 流式响应转换

**Coze v3 流式响应格式:**
```
event:conversation.chat.created
data:{"id":"7533416170062348288","conversation_id":"7533416170037182464","bot_id":"7533263489985413120","status":"in_progress"}

event:conversation.chat.in_progress
data:{"id":"7533416170062348288","conversation_id":"7533416170037182464","bot_id":"7533263489985413120","status":"in_progress"}

event:conversation.chat.completed
data:{"id":"7533416170062348288","conversation_id":"7533416170037182464","bot_id":"7533263489985413120","status":"completed"}
```

**转换为 OpenAI 流式格式:**
```
data: {"id":"coze-7533416170062348288","object":"chat.completion.chunk","created":1754010135,"model":"bot-7533263489985413120","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"coze-7533416170062348288","object":"chat.completion.chunk","created":1754010135,"model":"bot-7533263489985413120","choices":[{"index":0,"delta":{},"finish_reason":null}]}

data: {"id":"coze-7533416170062348288","object":"chat.completion.chunk","created":1754010135,"model":"bot-7533263489985413120","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### 3.2 非流式响应转换

**Coze 响应格式:**
```json
{
    "conversation_id": "123456",
    "messages": [
        {
            "type": "answer",
            "content": "Hello there! How can I help you today?",
            "role": "assistant"
        }
    ]
}
```

**转换为 OpenAI 格式:**
```json
{
    "id": "chatcmpl-123456",
    "object": "chat.completion",
    "created": 1677652288,
    "model": "bot-7533263489985413120",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Hello there! How can I help you today?"
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30
    }
}
```

### 3.3 响应转换实现代码

```python
def convert_coze_to_openai_stream(coze_response, conversation_id):
    """转换 Coze 流式响应为 OpenAI 格式"""
    if coze_response.get("message", {}).get("type") != "answer":
        return None

    content = coze_response.get("message", {}).get("content", "")
    is_final = coze_response.get("event") == "conversation.message.completed"

    openai_chunk = {
        "id": f"coze-{conversation_id}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "coze-bot",
        "choices": [{
            "index": 0,
            "delta": {"content": content} if content else {},
            "finish_reason": "stop" if is_final else None
        }]
    }

    return f"data: {json.dumps(openai_chunk)}\n\n"

def convert_coze_to_openai_response(coze_response):
    """转换 Coze 非流式响应为 OpenAI 格式"""
    response_text = ""

    # 提取 answer 类型的消息
    for message in coze_response.get("messages", []):
        if message.get("type") == "answer":
            response_text = message.get("content", "")
            break

    openai_response = {
        "id": f"chatcmpl-{coze_response.get('conversation_id', 'unknown')}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "coze-bot",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response_text
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 0,  # Coze 不提供 token 统计
            "completion_tokens": 0,
            "total_tokens": 0
        }
    }

    return openai_response
```

## 4. Python 程序使用方案

### 4.1 标准 OpenAI SDK 使用

```python
import openai

# 配置客户端
client = openai.OpenAI(
    api_key="your-proxy-api-key",  # 代理服务生成的API密钥
    base_url="http://localhost:8000/v1"  # 代理服务地址
)

# 使用 Coze Bot（模型名格式：bot-{COZE_BOT_ID}）
response = client.chat.completions.create(
    model="bot-7533263489985413120",
    messages=[
        {"role": "user", "content": "Hello"}
    ],
    stream=False
)

print(response.choices[0].message.content)
```

### 4.2 流式调用

```python
stream = client.chat.completions.create(
    model="bot-7533263489985413120",
    messages=[
        {"role": "user", "content": "Write a story"}
    ],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="")
```

### 4.3 错误处理

```python
try:
    response = client.chat.completions.create(
        model="bot-7533263489985413120",
        messages=[{"role": "user", "content": "Hello"}]
    )
except openai.APIError as e:
    print(f"API Error: {e}")
except openai.RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
```

## 5. 关键映射规则

### 5.1 停止原因映射

```python
STOP_REASON_MAPPING = {
    "end_turn": "stop",
    "stop_sequence": "stop",
    "max_tokens": "length"
}
```

### 5.2 消息类型过滤

- 只处理 `type: "answer"` 的消息
- 忽略其他类型消息（如工具调用、思考过程等）

### 5.3 模型名称处理

- OpenAI 格式：`bot-{COZE_BOT_ID}`
- Coze 格式：`{COZE_BOT_ID}`
- 自动添加/移除 `bot-` 前缀

## 6. 部署和配置

### 6.1 服务配置

在 `.env` 文件中配置 Coze Bot 适配器：

```env
# Coze Bot 配置
TYPE=coze
API_KEY=you_coze_api
BASE_URL=http://your-coze-api-host:port
ACTUAL_NAME=bot-{your-coze-bot-id}

# 其他配置
ENABLED=true
MAX_TOKENS=4096
SUPPORTS_STREAMING=true
SUPPORTS_FUNCTION_CALLING=false
```

### 6.2 启动服务

```bash
# 使用 UV 启动
uv run python start.py

# 或使用启动脚本
./run.sh

# 或使用 Docker
docker-compose up -d
```

## 7. 实际测试示例

### 7.1 流式调用测试

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer your-api-key" \
     -d '{
       "model": "bot-7533263489985413120",
       "stream": true,
       "messages": [{"role": "user", "content": "你好"}]
     }'
```

**预期响应:**
```
data: {"id":"coze-7533416170062348288","object":"chat.completion.chunk","created":1754010135,"model":"bot-7533263489985413120","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"coze-7533416170062348288","object":"chat.completion.chunk","created":1754010135,"model":"bot-7533263489985413120","choices":[{"index":0,"delta":{},"finish_reason":null}]}

data: {"id":"coze-7533416170062348288","object":"chat.completion.chunk","created":1754010135,"model":"bot-7533263489985413120","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### 7.2 健康检查

```bash
curl http://localhost:8000/health
# 响应: {"status":"healthy","service":"openai-proxy"}
```

## 8. 优势和特点

- **完全透明**: Python 程序无需修改，直接使用 OpenAI SDK
- **v3 API 支持**: 使用最新的 Coze v3 API 接口
- **流式支持**: 完整支持流式和非流式调用
- **自动映射**: 自动处理模型名称格式转换（bot-{ID} ↔ {ID}）
- **错误处理**: 统一的错误格式和处理机制
- **生产就绪**: 完整的日志记录、监控和测试覆盖

## 9. 技术细节

### 9.1 架构组件

- **适配器管理器**: `src/adapters/manager.py` - 负责路由和端点映射
- **Coze 适配器**: `src/adapters/coze_adapter.py` - 实现具体的格式转换
- **流式处理**: 使用 `httpx.AsyncClient.stream()` 处理 SSE 响应
- **模型管理**: 自动提取和验证 bot_id

### 9.2 关键配置

- **端点映射**: `/chat/completions` → `/v3/chat`
- **模型格式**: `bot-{COZE_BOT_ID}` → `{COZE_BOT_ID}`
- **认证方式**: Bearer Token 认证
- **超时设置**: 300秒默认超时

这个方案让你可以在 Python 程序中无缝使用 Coze Bot，就像使用 OpenAI API 一样简单。
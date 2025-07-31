# Coze 智能体集成指南

## 概述

现在支持的模型协议是 OpenAI 的，如果想要支持 Coze 的智能体作为模型输入，需要创建一个适配器（Adapter），将系统内部标准的 OpenAI 请求格式转换为 Coze API 要求的格式。

## 核心思路

保持项目对外的接口（OpenAI 格式）不变，在内部新增一个专门处理 Coze 请求的"翻译层"。

## 核心概念：创建 Coze 平台客户端

需要创建一个新的 `CozeClient`，它将和现有的 `OpenAIClient`、`AnthropicClient` 等平级。这个客户端的职责是：

1. 接收一个 OpenAI 格式的请求数据
2. 将其转换为 Coze API 的请求格式
3. 调用 Coze API
4. 接收 Coze 的响应
5. 将 Coze 的响应格式再转换回 OpenAI 的响应格式，然后返回

---

## 实现步骤详解

### 第1步：更新配置 (src/config/settings.py)

首先，让系统知道"Coze"是一个新的平台类型。

#### 1. 添加新的平台类型

在 `PlatformType` 枚举中增加 `COZE`：

```python
class PlatformType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    # ...
    COZE = "coze"  # 新增
```

#### 2. 添加 Coze 特定的配置项

Coze API 需要 Bot ID 和 Personal Access Token。在 `Settings` 类中增加相应的字段，以便从 `.env` 文件中读取：

```python
class Settings(BaseSettings):
    # ...
    
    # Coze-specific settings
    coze_bot_id: Optional[str] = None
    coze_personal_access_token: Optional[str] = None
    coze_base_url: str = "https://api.coze.com/open_api/v2/chat"
    
    # ...
```

### 第2步：创建 Coze 客户端 (src/core/platform_clients.py)

这是最核心的一步。需要在这个文件中创建一个新的类 `CozeClient`：

```python
# In src/core/platform_clients.py

# ... other imports

class CozeClient:
    def __init__(self, api_key: str, bot_id: str, base_url: str):
        # Coze uses a Personal Access Token as the API key
        self.personal_access_token = api_key
        self.bot_id = bot_id
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def chat_completion(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translates an OpenAI-like request to Coze format, sends it,
        and translates the response back.
        """
        # 1. 翻译请求 (OpenAI -> Coze)
        coze_payload = self._translate_request_to_coze(request_data)

        headers = {
            "Authorization": f"Bearer {self.personal_access_token}",
            "Content-Type": "application/json"
        }

        # 2. 调用 Coze API
        response = await self.client.post(self.base_url, json=coze_payload, headers=headers)
        response.raise_for_status()  # 抛出HTTP错误
        coze_response_data = response.json()

        # 3. 翻译响应 (Coze -> OpenAI)
        openai_response = self._translate_response_to_openai(coze_response_data)

        return openai_response

    def _translate_request_to_coze(self, openai_request: Dict[str, Any]) -> Dict[str, Any]:
        # 从OpenAI的消息列表中提取最后一条作为查询
        last_message = openai_request["messages"][-1]
        query = last_message["content"]

        # 提取历史消息
        chat_history = []
        for msg in openai_request["messages"][:-1]:
            role = "user" if msg["role"] == "user" else "assistant"
            chat_history.append({"role": role, "content": msg["content"]})

        return {
            "bot_id": self.bot_id,
            "user": openai_request.get("user", "default_user"),  # Coze需要一个user_id
            "query": query,
            "chat_history": chat_history,
            "stream": openai_request.get("stream", False),
        }

    def _translate_response_to_openai(self, coze_response: Dict[str, Any]) -> Dict[str, Any]:
        # 从Coze的响应中找到答案
        answer_message = ""
        for msg in coze_response.get("messages", []):
            if msg.get("type") == "answer":
                answer_message = msg.get("content")
                break

        return {
            "id": coze_response.get("conversation_id", "chatcmpl-coze-mock-id"),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": f"coze-{self.bot_id}",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": answer_message,
                },
                "finish_reason": "stop",
            }],
            "usage": {  # Coze不提供token用量，所以我们只能模拟
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }

    # 你还需要实现一个 stream_chat_completion 方法来处理流式响应
    async def stream_chat_completion(self, request_data: Dict[str, Any]):
        # ... 实现流式请求的翻译和响应解析 ...
        # 这部分会更复杂，需要逐块解析Coze的SSE事件流，并将其转换为OpenAI格式的SSE事件流
        pass
```

### 第3步：在工厂函数中注册新的客户端

在 `platform_clients.py` 文件中，应该有一个工厂函数（例如 `get_platform_client`），需要在这里添加对 `CozeClient` 的支持：

```python
# In src/core/platform_clients.py

def get_platform_client(platform: PlatformType) -> Any:
    if platform == PlatformType.OPENAI:
        # ...
    elif platform == PlatformType.ANTHROPIC:
        # ...
    elif platform == PlatformType.COZE:  # 新增
        return CozeClient(
            api_key=settings.coze_personal_access_token,
            bot_id=settings.coze_bot_id,
            base_url=settings.coze_base_url
        )
    else:
        raise ValueError(f"Unsupported platform type: {platform}")
```

### 第4步：更新 .env 配置文件

最后，用户只需要在他们的 `.env` 文件中配置好 Coze 的相关信息，应用就能自动切换：

```bash
# .env file

# 将平台类型设置为coze
TYPE=coze

# 你的Coze Bot ID
COZE_BOT_ID="73xxxxxxxxxxxxxx"

# 你的Coze Personal Access Token
COZE_PERSONAL_ACCESS_TOKEN="pat_xxxxxxxxxxxxxxxx"

# (可选) 如果需要覆盖默认API地址
# COZE_BASE_URL="https://api.coze.com/open_api/v2/chat"

# 其他配置保持不变...
ENABLE_CLIENT_AUTH=True
# ...
```

---

## 总结工作流程

1. **用户请求**：客户端向你的服务发起一个标准的 OpenAI API 请求（例如 `POST /v1/chat/completions`）
2. **配置加载**：应用启动时，settings 读取到 `TYPE=coze`
3. **模型路由**：ModelManager 发现平台类型是 `coze`
4. **客户端创建**：`get_platform_client` 工厂函数被调用，创建并返回一个 `CozeClient` 实例
5. **请求翻译**：`CozeClient.chat_completion` 方法被调用，它将 OpenAI 格式的请求体翻译成 Coze API 需要的格式
6. **API调用**：CozeClient 向 Coze 服务器发起请求
7. **响应翻译**：CozeClient 收到 Coze 的响应，并将其翻译回标准的 OpenAI ChatCompletion 格式
8. **返回用户**：最终的 OpenAI 格式响应被返回给客户端

通过这种方式，可以在不改变项目现有接口和核心逻辑的前提下，优雅地将 Coze 作为一种新的模型后端集成进来。

## 注意事项

- 流式响应的实现会更复杂，需要逐块解析 Coze 的 SSE 事件流，并将其转换为 OpenAI 格式的 SSE 事件流
- Coze 不提供 token 用量信息，所以在响应中只能模拟这部分数据
- 需要确保错误处理和异常情况的处理与现有系统保持一致
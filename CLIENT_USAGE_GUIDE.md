# 客户端使用指南 📖

本指南详细介绍如何在各种编程语言和环境中使用 OpenAI API 统一代理服务。

## 📋 目录

- [基础配置](#基础配置)
- [Python 客户端](#python-客户端)
- [JavaScript/Node.js 客户端](#javascriptnodejs-客户端)
- [cURL 命令行](#curl-命令行)
- [HTTP 客户端库](#http-客户端库)
- [流式响应处理](#流式响应处理)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)

## 🔧 基础配置

### 服务端点

确保你的代理服务正在运行，默认地址为：

```
Base URL: http://localhost:8000
Health Check: http://localhost:8000/health
API Docs: http://localhost:8000/docs
```

### 认证

所有请求都需要在 Header 中包含 API 密钥：

```http
Authorization: Bearer your-api-key-here
```

## 🐍 Python 客户端

### 使用官方 OpenAI Python 库

```python
from openai import OpenAI

# 配置客户端指向你的代理服务
client = OpenAI(
    api_key="your-api-key-here",
    base_url="http://localhost:8000"  # 你的代理服务地址
)

# 基本聊天完成
def basic_chat():
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # 根据你的配置调整
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! How are you?"}
        ],
        max_tokens=150,
        temperature=0.7
    )
    
    print(response.choices[0].message.content)

# 流式聊天完成
def streaming_chat():
    stream = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Tell me a story about AI"}
        ],
        stream=True,
        max_tokens=200
    )
    
    print("Response: ", end="")
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()

# 函数调用支持
def function_calling():
    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather information for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    }
                },
                "required": ["location"]
            }
        }
    }]
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "What's the weather like in Beijing?"}
        ],
        tools=tools,
        tool_choice="auto"
    )
    
    return response

if __name__ == "__main__":
    basic_chat()
    streaming_chat()
```

### 使用 httpx 异步客户端

```python
import httpx
import asyncio
import json

class AsyncOpenAIClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def chat_completion(self, messages, model="gpt-3.5-turbo", **kwargs):
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    async def stream_chat_completion(self, messages, model="gpt-3.5-turbo", **kwargs):
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            **kwargs
        }
        
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, json=payload, headers=self.headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            continue

# 使用示例
async def main():
    client = AsyncOpenAIClient(
        base_url="http://localhost:8000",
        api_key="your-api-key-here"
    )
    
    # 普通请求
    response = await client.chat_completion([
        {"role": "user", "content": "Hello, world!"}
    ])
    print(response["choices"][0]["message"]["content"])
    
    # 流式请求
    print("Streaming response:")
    async for chunk in client.stream_chat_completion([
        {"role": "user", "content": "Tell me about Python"}
    ]):
        if "choices" in chunk and chunk["choices"]:
            delta = chunk["choices"][0].get("delta", {})
            if "content" in delta:
                print(delta["content"], end="", flush=True)
    print()

if __name__ == "__main__":
    asyncio.run(main())
```

## 🌐 JavaScript/Node.js 客户端

### 使用官方 OpenAI JavaScript 库

```javascript
import OpenAI from 'openai';

// 配置客户端
const openai = new OpenAI({
  apiKey: 'your-api-key-here',
  baseURL: 'http://localhost:8000', // 你的代理服务地址
});

// 基本聊天完成
async function basicChat() {
  try {
    const response = await openai.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages: [
        { role: 'system', content: 'You are a helpful assistant.' },
        { role: 'user', content: 'Hello! How can you help me today?' }
      ],
      max_tokens: 150,
      temperature: 0.7
    });
    
    console.log(response.choices[0].message.content);
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

// 流式聊天完成
async function streamingChat() {
  try {
    const stream = await openai.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages: [
        { role: 'user', content: 'Write a short poem about technology' }
      ],
      stream: true,
      max_tokens: 200
    });
    
    console.log('Streaming response:');
    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content || '';
      if (content) {
        process.stdout.write(content);
      }
    }
    console.log('\n');
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

// 获取模型列表
async function listModels() {
  try {
    const response = await openai.models.list();
    console.log('Available models:');
    response.data.forEach(model => {
      console.log(`- ${model.id}`);
    });
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

// 运行示例
basicChat();
streamingChat();
listModels();
```

### 使用 Fetch API

```javascript
class OpenAIProxyClient {
  constructor(baseURL, apiKey) {
    this.baseURL = baseURL.replace(/\/$/, '');
    this.headers = {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    };
  }

  async chatCompletion(messages, options = {}) {
    const response = await fetch(`${this.baseURL}/chat/completions`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        model: 'gpt-3.5-turbo',
        messages,
        ...options
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  async *streamChatCompletion(messages, options = {}) {
    const response = await fetch(`${this.baseURL}/chat/completions`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        model: 'gpt-3.5-turbo',
        messages,
        stream: true,
        ...options
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data.trim() === '[DONE]') return;
          
          try {
            yield JSON.parse(data);
          } catch (e) {
            // Skip invalid JSON
          }
        }
      }
    }
  }
}

// 使用示例
const client = new OpenAIProxyClient('http://localhost:8000', 'your-api-key-here');

// 普通请求
client.chatCompletion([
  { role: 'user', content: 'Hello, world!' }
]).then(response => {
  console.log(response.choices[0].message.content);
});

// 流式请求
(async () => {
  console.log('Streaming response:');
  for await (const chunk of client.streamChatCompletion([
    { role: 'user', content: 'Tell me about JavaScript' }
  ])) {
    const content = chunk.choices?.[0]?.delta?.content;
    if (content) {
      process.stdout.write(content);
    }
  }
  console.log('\n');
})();
```

## 💻 cURL 命令行

### 基本请求

```bash
# 健康检查
curl -X GET http://localhost:8000/health

# 获取模型列表
curl -X GET http://localhost:8000/models \
  -H "Authorization: Bearer your-api-key-here"

# 非流式聊天完成
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is the capital of France?"}
    ],
    "max_tokens": 100,
    "temperature": 0.7
  }'

# 流式聊天完成
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Write a haiku about programming"}
    ],
    "stream": true,
    "max_tokens": 100
  }'

# 函数调用
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "What'\''s the weather like in Tokyo?"}
    ],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get weather information",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {"type": "string"}
          },
          "required": ["location"]
        }
      }
    }],
    "tool_choice": "auto"
  }'
```

## 🔌 HTTP 客户端库

### Go 语言

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
)

type ChatRequest struct {
    Model       string    `json:"model"`
    Messages    []Message `json:"messages"`
    MaxTokens   int       `json:"max_tokens,omitempty"`
    Temperature float64   `json:"temperature,omitempty"`
    Stream      bool      `json:"stream,omitempty"`
}

type Message struct {
    Role    string `json:"role"`
    Content string `json:"content"`
}

type ChatResponse struct {
    Choices []Choice `json:"choices"`
}

type Choice struct {
    Message Message `json:"message"`
    Delta   Message `json:"delta"`
}

func chatCompletion(baseURL, apiKey string, req ChatRequest) (*ChatResponse, error) {
    jsonData, err := json.Marshal(req)
    if err != nil {
        return nil, err
    }

    httpReq, err := http.NewRequest("POST", baseURL+"/chat/completions", bytes.NewBuffer(jsonData))
    if err != nil {
        return nil, err
    }

    httpReq.Header.Set("Content-Type", "application/json")
    httpReq.Header.Set("Authorization", "Bearer "+apiKey)

    client := &http.Client{}
    resp, err := client.Do(httpReq)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    body, err := io.ReadAll(resp.Body)
    if err != nil {
        return nil, err
    }

    var chatResp ChatResponse
    err = json.Unmarshal(body, &chatResp)
    if err != nil {
        return nil, err
    }

    return &chatResp, nil
}

func main() {
    req := ChatRequest{
        Model: "gpt-3.5-turbo",
        Messages: []Message{
            {Role: "user", Content: "Hello, world!"},
        },
        MaxTokens:   150,
        Temperature: 0.7,
    }

    resp, err := chatCompletion("http://localhost:8000", "your-api-key-here", req)
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }

    if len(resp.Choices) > 0 {
        fmt.Println(resp.Choices[0].Message.Content)
    }
}
```

### Java 语言

```java
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.URI;
import java.time.Duration;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.annotation.JsonProperty;

public class OpenAIProxyClient {
    private final String baseUrl;
    private final String apiKey;
    private final HttpClient client;
    private final ObjectMapper mapper;

    public OpenAIProxyClient(String baseUrl, String apiKey) {
        this.baseUrl = baseUrl.replaceAll("/$", "");
        this.apiKey = apiKey;
        this.client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(30))
            .build();
        this.mapper = new ObjectMapper();
    }

    public ChatResponse chatCompletion(ChatRequest request) throws Exception {
        String json = mapper.writeValueAsString(request);
        
        HttpRequest httpRequest = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/chat/completions"))
            .header("Content-Type", "application/json")
            .header("Authorization", "Bearer " + apiKey)
            .POST(HttpRequest.BodyPublishers.ofString(json))
            .build();

        HttpResponse<String> response = client.send(httpRequest, 
            HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() != 200) {
            throw new RuntimeException("HTTP error: " + response.statusCode());
        }

        return mapper.readValue(response.body(), ChatResponse.class);
    }

    // 数据类定义
    public static class ChatRequest {
        public String model = "gpt-3.5-turbo";
        public Message[] messages;
        @JsonProperty("max_tokens")
        public Integer maxTokens;
        public Double temperature;

        public ChatRequest(Message[] messages) {
            this.messages = messages;
        }
    }

    public static class Message {
        public String role;
        public String content;

        public Message(String role, String content) {
            this.role = role;
            this.content = content;
        }
    }

    public static class ChatResponse {
        public Choice[] choices;
    }

    public static class Choice {
        public Message message;
    }

    // 使用示例
    public static void main(String[] args) {
        try {
            OpenAIProxyClient client = new OpenAIProxyClient(
                "http://localhost:8000", 
                "your-api-key-here"
            );

            Message[] messages = {
                new Message("user", "Hello, how are you?")
            };

            ChatRequest request = new ChatRequest(messages);
            request.maxTokens = 150;
            request.temperature = 0.7;

            ChatResponse response = client.chatCompletion(request);
            
            if (response.choices.length > 0) {
                System.out.println(response.choices[0].message.content);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

## 🌊 流式响应处理

### Python 流式处理

```python
import json
import httpx

async def handle_stream_response(url, headers, payload):
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", url, json=payload, headers=headers) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content:
                            print(content, end="", flush=True)
                    except (json.JSONDecodeError, KeyError):
                        continue
    print()  # 换行
```

### JavaScript 流式处理

```javascript
async function handleStreamResponse(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data.trim() === '[DONE]') return;
          
          try {
            const parsed = JSON.parse(data);
            const content = parsed.choices?.[0]?.delta?.content;
            if (content) {
              process.stdout.write(content);
            }
          } catch (e) {
            // Skip invalid JSON
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
```

## ⚠️ 错误处理

### 常见错误码

```python
# 错误处理示例
import httpx

class OpenAIProxyError(Exception):
    def __init__(self, status_code, message, details=None):
        self.status_code = status_code
        self.message = message
        self.details = details
        super().__init__(f"HTTP {status_code}: {message}")

async def safe_api_call(url, headers, payload):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 400:
                raise OpenAIProxyError(400, "Bad Request", response.json())
            elif response.status_code == 401:
                raise OpenAIProxyError(401, "Unauthorized - Check API key")
            elif response.status_code == 429:
                raise OpenAIProxyError(429, "Rate limit exceeded")
            elif response.status_code == 500:
                raise OpenAIProxyError(500, "Internal server error")
            else:
                raise OpenAIProxyError(response.status_code, "Unknown error")
                
    except httpx.TimeoutException:
        raise OpenAIProxyError(408, "Request timeout")
    except httpx.ConnectError:
        raise OpenAIProxyError(503, "Service unavailable")
```

### 重试机制

```python
import asyncio
import random

async def retry_with_backoff(func, max_retries=3, base_delay=1.0):
    for attempt in range(max_retries):
        try:
            return await func()
        except OpenAIProxyError as e:
            if e.status_code in [500, 502, 503, 504] and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"Retry attempt {attempt + 1} after {delay:.2f}s")
                await asyncio.sleep(delay)
            else:
                raise
```

## 🎯 最佳实践

### 1. 连接池管理

```python
# 使用连接池提高性能
import httpx

class OpenAIProxyClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
    
    async def close(self):
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
```

### 2. 请求缓存

```python
import hashlib
import json
from functools import wraps

def cache_response(ttl=300):  # 5分钟缓存
    cache = {}
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = hashlib.md5(
                json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True).encode()
            ).hexdigest()
            
            # 检查缓存
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    return result
            
            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            return result
        
        return wrapper
    return decorator
```

### 3. 批量请求处理

```python
import asyncio

async def batch_requests(client, requests, batch_size=5):
    """批量处理请求，避免过载"""
    results = []
    
    for i in range(0, len(requests), batch_size):
        batch = requests[i:i + batch_size]
        batch_tasks = [client.chat_completion(req) for req in batch]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        results.extend(batch_results)
        
        # 批次间短暂延迟
        if i + batch_size < len(requests):
            await asyncio.sleep(0.1)
    
    return results
```

### 4. 监控和日志

```python
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def logged_api_call(func, *args, **kwargs):
    start_time = time.time()
    try:
        result = await func(*args, **kwargs)
        duration = time.time() - start_time
        logger.info(f"API call succeeded in {duration:.2f}s")
        return result
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"API call failed after {duration:.2f}s: {e}")
        raise
```

### 5. 环境配置

```python
import os
from dataclasses import dataclass

@dataclass
class Config:
    base_url: str = os.getenv("OPENAI_PROXY_URL", "http://localhost:8000")
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    timeout: int = int(os.getenv("OPENAI_TIMEOUT", "30"))
    max_retries: int = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
    
    def __post_init__(self):
        if not self.api_key:
            raise ValueError("API key is required")

# 使用配置
config = Config()
client = OpenAIProxyClient(config.base_url, config.api_key)
```

## 🔍 调试技巧

### 启用详细日志

```bash
# 设置环境变量启用详细日志
export LOG_LEVEL=debug
export HTTPX_LOG_LEVEL=debug

# 运行你的客户端代码
python your_client.py
```

### 请求响应调试

```python
import httpx

# 启用详细的HTTP日志
import logging
logging.basicConfig()
logging.getLogger("httpx").setLevel(logging.DEBUG)

# 或者手动打印请求响应
async def debug_request(url, headers, payload):
    print(f"Request URL: {url}")
    print(f"Request Headers: {headers}")
    print(f"Request Payload: {json.dumps(payload, indent=2)}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        return response
```

## 📞 支持与反馈

如果在使用过程中遇到问题：

1. 检查服务健康状态：`GET /health`
2. 查看服务日志：`./logs/proxy.log`
3. 参考 API 文档：`http://localhost:8000/docs`
4. 提交 Issue 或联系开发团队

---

**🎉 恭喜！你现在已经掌握了使用 OpenAI API 统一代理服务的各种方法。开始构建你的 AI 应用吧！**
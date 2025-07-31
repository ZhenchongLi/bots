# 模型适配器开发指南

本指南将帮助开发者为 AI API 代理系统添加新的模型平台适配器。

## 概述

适配器模式允许系统支持不同的 AI 平台，同时保持与 OpenAI API 格式的兼容性。每个适配器负责：

1. 将 OpenAI 格式的请求转换为目标平台格式
2. 将目标平台的响应转换回 OpenAI 格式
3. 处理平台特定的认证和配置

## 适配器架构

```
src/adapters/
├── base.py                 # 基础适配器类和注册机制
├── manager.py             # 适配器管理器
├── proxy.py              # 适配器代理（向后兼容）
├── coze_adapter.py       # Coze Bot 适配器示例
└── your_platform_adapter.py  # 你的新适配器
```

## 开发步骤

### 1. 创建适配器类

在 `src/adapters/` 目录下创建新的适配器文件，继承 `BasePlatformAdapter`：

```python
# src/adapters/your_platform_adapter.py
from typing import Dict, Any, Optional, List
import httpx
import structlog
from .base import BasePlatformAdapter

logger = structlog.get_logger()

class YourPlatformAdapter(BasePlatformAdapter):
    """你的平台适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化适配器"""
        super().__init__(config)
        
        # 平台特定的配置
        self.custom_setting = config.get("custom_setting")
        
        # 验证必需的配置
        if not self.custom_setting:
            raise ValueError("custom_setting is required for YourPlatform adapter")
    
    def get_platform_name(self) -> str:
        """返回平台名称"""
        return "your_platform"
    
    def get_supported_endpoints(self) -> List[str]:
        """返回支持的端点列表"""
        return ["/chat/completions", "/embeddings"]  # 根据平台支持情况调整
```

### 2. 实现请求转换

实现 `transform_request` 方法，将 OpenAI 格式转换为目标平台格式：

```python
    async def transform_request(self, endpoint: str, openai_request: Dict[str, Any]) -> Dict[str, Any]:
        """将 OpenAI 请求转换为平台格式"""
        if endpoint == "/chat/completions" and "messages" in openai_request:
            # 转换消息格式
            platform_request = {
                "input": self._convert_messages(openai_request["messages"]),
                "model": openai_request.get("model", "default"),
                "custom_setting": self.custom_setting
            }
            
            # 转换可选参数
            if "max_tokens" in openai_request:
                platform_request["max_length"] = openai_request["max_tokens"]
            if "temperature" in openai_request:
                platform_request["temperature"] = openai_request["temperature"]
            
            return platform_request
        
        elif endpoint == "/embeddings":
            # 处理嵌入请求
            return {
                "text": openai_request.get("input", ""),
                "model": openai_request.get("model", "embedding-model")
            }
        
        # 不支持的端点，返回原始请求
        return openai_request
    
    def _convert_messages(self, messages: List[Dict[str, Any]]) -> str:
        """将 OpenAI 消息格式转换为平台特定格式"""
        # 示例：简单地提取最后一条用户消息
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return ""
```

### 3. 实现响应转换

实现 `transform_response` 方法，将平台响应转换为 OpenAI 格式：

```python
    async def transform_response(self, endpoint: str, platform_response: Dict[str, Any]) -> Dict[str, Any]:
        """将平台响应转换为 OpenAI 格式"""
        if endpoint == "/chat/completions":
            return self._transform_chat_response(platform_response)
        elif endpoint == "/embeddings":
            return self._transform_embedding_response(platform_response)
        
        return platform_response
    
    def _transform_chat_response(self, platform_response: Dict[str, Any]) -> Dict[str, Any]:
        """转换聊天响应"""
        content = platform_response.get("output", "")
        
        return {
            "id": f"chatcmpl-{hash(content) % 10000:04d}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": self.config.get("actual_name", "your-platform-model"),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": platform_response.get("input_tokens", 0),
                "completion_tokens": platform_response.get("output_tokens", 0),
                "total_tokens": platform_response.get("total_tokens", 0)
            }
        }
    
    def _transform_embedding_response(self, platform_response: Dict[str, Any]) -> Dict[str, Any]:
        """转换嵌入响应"""
        embeddings = platform_response.get("vector", [])
        
        return {
            "object": "list",
            "data": [{
                "object": "embedding",
                "embedding": embeddings,
                "index": 0
            }],
            "model": self.config.get("actual_name", "embedding-model"),
            "usage": {
                "prompt_tokens": platform_response.get("tokens", 0),
                "total_tokens": platform_response.get("tokens", 0)
            }
        }
```

### 4. 实现 HTTP 请求

实现 `make_request` 方法处理实际的 HTTP 请求：

```python
    async def make_request(
        self, 
        method: str, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """发送 HTTP 请求到平台 API"""
        request_headers = self.prepare_headers(headers)
        request_headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # 添加平台特定的头部
            "X-Custom-Header": "value"
        })
        
        logger.debug("Making request to platform API", 
                    method=method, 
                    url=url,
                    has_json_data=json_data is not None)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=json_data,
                    params=params,
                )
                
                result = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content": response.content,
                    "json": None
                }
                
                # 解析 JSON 响应
                try:
                    if response.content:
                        result["json"] = response.json()
                except Exception as e:
                    logger.warning("Failed to parse JSON response", error=str(e))
                
                return result
                
        except httpx.TimeoutException:
            logger.error("Timeout making request to platform API", url=url)
            raise
        except Exception as e:
            logger.error("Error making request to platform API", url=url, error=str(e))
            raise
```

### 5. 添加配置验证和模型信息

```python
    def validate_config(self) -> bool:
        """验证适配器配置"""
        if not super().validate_config():
            return False
        
        if not self.custom_setting:
            logger.error("custom_setting is required for YourPlatform adapter")
            return False
        
        return True
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        info = super().get_model_info()
        info.update({
            "custom_setting": self.custom_setting,
            "supports_streaming": self.config.get("supports_streaming", False),
            "supports_function_calling": False  # 根据平台能力调整
        })
        return info
```

### 6. 注册适配器

在 `src/adapters/manager.py` 中注册新适配器：

```python
def _register_builtin_adapters(self):
    """注册内置适配器"""
    # 现有适配器
    adapter_registry.register("coze", CozeAdapter)
    
    # 添加你的适配器
    from .your_platform_adapter import YourPlatformAdapter
    adapter_registry.register("your_platform", YourPlatformAdapter)
    
    logger.info("Registered built-in adapters", 
               platforms=adapter_registry.list_platforms())
```

### 7. 更新配置支持

在 `src/core/model_manager.py` 的 `_add_platform_specific_config` 方法中添加平台特定配置：

```python
def _add_platform_specific_config(self, config: Dict[str, Any]) -> None:
    """添加平台特定配置"""
    platform_type = config.get("type")
    
    # 现有平台配置...
    
    elif platform_type == "your_platform":
        # 你的平台特定设置
        custom_setting = os.getenv("CUSTOM_SETTING")
        another_setting = os.getenv("ANOTHER_SETTING", "default_value")
        
        if custom_setting:
            config["custom_setting"] = custom_setting
        if another_setting:
            config["another_setting"] = another_setting
```

### 8. 更新环境变量示例

在 `.env.example` 中添加新平台的配置示例：

```bash
# Your Platform 配置示例
# TYPE=your_platform
# API_KEY=your-platform-api-key
# BASE_URL=https://api.yourplatform.com/v1
# ACTUAL_NAME=your-platform-model
# CUSTOM_SETTING=required-setting-value
# ANOTHER_SETTING=optional-setting-value
```

### 9. 编写测试

创建测试文件 `tests/test_your_platform_adapter.py`：

```python
import pytest
from unittest.mock import patch, MagicMock
from src.adapters.your_platform_adapter import YourPlatformAdapter

class TestYourPlatformAdapter:
    @pytest.fixture
    def adapter_config(self):
        return {
            "api_key": "test-api-key",
            "base_url": "https://api.yourplatform.com/v1",
            "custom_setting": "test-value",
            "timeout": 300
        }
    
    @pytest.fixture
    def adapter(self, adapter_config):
        return YourPlatformAdapter(adapter_config)
    
    def test_adapter_initialization(self, adapter_config):
        adapter = YourPlatformAdapter(adapter_config)
        assert adapter.api_key == "test-api-key"
        assert adapter.custom_setting == "test-value"
    
    @pytest.mark.asyncio
    async def test_transform_request(self, adapter):
        openai_request = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 100
        }
        
        result = await adapter.transform_request("/chat/completions", openai_request)
        
        assert result["input"] == "Hello"
        assert result["max_length"] == 100
        assert result["custom_setting"] == "test-value"
```

## 最佳实践

### 1. 错误处理

- 始终验证必需的配置参数
- 优雅地处理 API 错误和超时
- 记录详细的错误信息用于调试

### 2. 日志记录

- 使用结构化日志记录重要事件
- 避免记录敏感信息（如 API 密钥）
- 在调试模式下记录请求和响应详情

### 3. 性能优化

- 重用 HTTP 连接池
- 合理设置超时时间
- 考虑实现请求缓存（如果适用）

### 4. 安全考虑

- 验证和清理输入数据
- 使用安全的 HTTP 头部
- 避免在日志中暴露敏感信息

### 5. 测试覆盖

- 编写单元测试覆盖所有主要功能
- 测试错误场景和边界情况
- 使用模拟对象避免实际 API 调用

## 部署和使用

1. **配置环境变量**：在 `.env` 文件中设置平台配置
2. **重启服务**：重启 API 代理服务以加载新适配器
3. **验证功能**：发送测试请求验证适配器工作正常

## 示例使用

配置完成后，客户端可以正常使用 OpenAI 格式的 API：

```python
import openai

client = openai.OpenAI(
    api_key="your-proxy-api-key",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="any-model-name",  # 会被替换为实际模型名
    messages=[{"role": "user", "content": "Hello"}]
)
```

系统会自动使用相应的适配器处理请求。

## 贡献代码

如果你开发了一个通用的适配器，欢迎提交 Pull Request 贡献给项目！请确保：

1. 代码遵循项目的编码规范
2. 包含完整的测试用例
3. 更新相关文档
4. 添加配置示例

---

需要帮助？请查看现有的 `CozeAdapter` 实现作为参考，或在 GitHub 上提出 Issue。
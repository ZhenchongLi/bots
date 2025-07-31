# 响应后处理钩子系统

## 概述

如果想在请求之后添加业务逻辑，然后返回，又不想影响现有框架的实现，可以通过"钩子（Hooks）"或"中间件（Middleware）"模式来解决。这允许在不修改核心业务流程的情况下，注入自定义逻辑。

## 核心思路

创建一个"钩子管理器"，应用在启动时可以向这个管理器注册一个或多个"后处理钩子函数"。在 API 返回响应之前，会调用这个管理器来执行所有已注册的钩子，让它们依次对响应数据进行处理或执行附加操作（如计费、审计、内容过滤等）。

---

## 实现步骤

### 第1步：创建钩子管理器

在 `src` 目录下创建一个新的子目录 `hooks`，用于存放所有的自定义逻辑。

#### 1. 创建目录结构

```bash
src/hooks/
├── __init__.py
├── manager.py
└── custom_hooks.py
```

#### 2. 创建钩子管理器 (src/hooks/manager.py)

```python
# src/hooks/manager.py
from typing import List, Callable, Awaitable, Dict, Any
import structlog

logger = structlog.get_logger(__name__)

# 定义钩子函数的类型签名
# 它接收响应和原始请求，并返回修改后的响应
PostprocessHook = Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[Dict[str, Any]]]

class HookManager:
    def __init__(self):
        self.postprocess_hooks: List[PostprocessHook] = []

    def register_postprocess_hook(self, hook: PostprocessHook):
        """注册一个响应后处理钩子"""
        logger.info(f"Registering post-processing hook: {hook.__name__}")
        self.postprocess_hooks.append(hook)

    async def run_postprocess_hooks(self, response_data: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """依次执行所有已注册的后处理钩子"""
        modified_response = response_data
        for hook in self.postprocess_hooks:
            try:
                modified_response = await hook(modified_response, request_data)
            except Exception as e:
                logger.error(f"Error executing hook {hook.__name__}", exc_info=e)
                # 如果一个钩子失败，可以选择是继续还是中断
        return modified_response

# 创建一个全局唯一的钩子管理器实例
hook_manager = HookManager()
```

### 第2步：创建自定义业务逻辑钩子

创建 `src/hooks/custom_hooks.py`，实现具体的业务逻辑：

```python
# src/hooks/custom_hooks.py
from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__)

async def add_disclaimer_hook(response: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
    """
    在聊天回复的末尾附加一个免责声明。
    """
    logger.info("Executing 'add_disclaimer_hook'")

    if "choices" in response and response["choices"]:
        # 为非流式响应添加
        original_content = response["choices"][0]["message"]["content"]
        disclaimer = "\n\n[免责声明：此内容由AI生成，请谨慎核实。]"
        response["choices"][0]["message"]["content"] = original_content + disclaimer

    # 注意：对于流式响应，处理会更复杂，需要在每个数据块中识别最后一块并注入
    # 为简化示例，这里我们主要展示非流式处理

    return response

async def audit_log_hook(response: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
    """
    记录审计日志，比如token用量和请求用户。
    """
    client_name = request.get("x-client-name", "unknown")  # 假设客户端名在请求中
    usage = response.get("usage", {})

    logger.info(
        "Audit Log",
        client=client_name,
        model=response.get("model"),
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
    )

    # 这个钩子不修改响应，只是记录日志，所以直接返回原响应
    return response
```

### 第3步：在应用启动时注册钩子

修改 `src/main.py`，在 `startup_event` 中告诉钩子管理器要使用哪些钩子：

```python
# src/main.py

# ... 其他 imports
from src.hooks.manager import hook_manager
from src.hooks.custom_hooks import add_disclaimer_hook, audit_log_hook  # 导入你的钩子

# ...

@app.on_event("startup")
async def startup_event():
    # ... (现有的启动逻辑)

    # 注册你的后处理钩子
    # 注册的顺序就是它们执行的顺序
    hook_manager.register_postprocess_hook(audit_log_hook)
    hook_manager.register_postprocess_hook(add_disclaimer_hook)

    logger.info("Application startup complete.")
```

### 第4步：在API层调用钩子管理器

这是最后一步，也是对现有代码唯一需要修改的地方。在 `src/api/openai_api.py` 中返回响应之前，调用钩子管理器：

```python
# src/api/openai_api.py

# ... 其他 imports
from src.hooks.manager import hook_manager  # 导入钩子管理器

# ...

@router.post("/v1/chat/completions", tags=["Chat"])
async def chat_completions(
    # ... 函数签名不变
):
    # ... (现有的认证、请求处理逻辑)

    try:
        # ...
        client = get_platform_client(platform_type)

        if request.stream:
            # ... (流式处理逻辑)
            # 注意：在流式响应中应用钩子比较复杂，需要修改生成器函数
            # 这里我们先处理非流式的情况
            pass
        else:
            # 非流式响应
            response_data = await client.chat_completion(processed_request)

            # 在这里调用钩子管理器！
            final_response = await hook_manager.run_postprocess_hooks(response_data, processed_request)

            return JSONResponse(content=final_response)

    # ... (异常处理逻辑)
```

---

## 钩子函数示例

### 计费钩子

```python
async def billing_hook(response: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
    """计费逻辑钩子"""
    usage = response.get("usage", {})
    total_tokens = usage.get("total_tokens", 0)
    
    # 执行计费逻辑
    await record_usage(
        user_id=request.get("user_id"),
        tokens=total_tokens,
        model=response.get("model")
    )
    
    return response
```

### 内容过滤钩子

```python
async def content_filter_hook(response: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
    """内容过滤钩子"""
    if "choices" in response and response["choices"]:
        content = response["choices"][0]["message"]["content"]
        
        # 检查是否包含敏感内容
        if contains_sensitive_content(content):
            response["choices"][0]["message"]["content"] = "[内容已被过滤]"
    
    return response
```

### 缓存钩子

```python
async def cache_hook(response: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
    """缓存响应钩子"""
    # 生成缓存键
    cache_key = generate_cache_key(request)
    
    # 将响应存储到缓存
    await cache_client.set(cache_key, response, expire=3600)
    
    return response
```

---

## 流式响应处理

对于流式响应，钩子的处理会更复杂。需要在流式生成器中集成钩子系统：

```python
async def stream_with_hooks(generator, request_data):
    """带钩子的流式响应处理器"""
    chunks = []
    async for chunk in generator:
        chunks.append(chunk)
        yield chunk
    
    # 在流结束后，重构完整响应并应用钩子
    complete_response = reconstruct_response_from_chunks(chunks)
    processed_response = await hook_manager.run_postprocess_hooks(complete_response, request_data)
    
    # 如果钩子修改了内容，发送修正块
    if response_was_modified(complete_response, processed_response):
        correction_chunk = create_correction_chunk(processed_response)
        yield correction_chunk
```

---

## 总结

通过以上步骤，成功建立了一个可插拔的业务逻辑层：

### 优势

- **完全解耦**：业务逻辑（如免责声明、计费、审计）完全独立于核心的 API 代理框架，存放在 `src/hooks` 目录中
- **易于管理**：想增加、删除或调整业务逻辑，只需要修改 `src/hooks/custom_hooks.py` 和 `src/main.py` 中的注册部分
- **侵入性极小**：对核心代码的改动只有两处：`main.py` 里添加注册代码，`openai_api.py` 里添加一行调用代码
- **可扩展性强**：可以轻松添加新的钩子类型（预处理钩子、错误处理钩子等）

### 适用场景

- 响应内容修改（免责声明、格式化等）
- 审计日志记录
- 计费和用量统计
- 内容过滤和安全检查
- 缓存管理
- 性能监控
- 用户行为分析

这个方案优雅地满足了在不影响现有框架的情况下添加业务逻辑的需求，并为未来扩展更多业务功能打下了坚实的基础。
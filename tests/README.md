# 测试文档

本文档描述了 OpenAI 代理服务的测试套件。

## 测试结构

```
tests/
├── __init__.py
├── conftest.py              # 测试配置和共享 fixtures
├── test_config.py           # 配置测试
├── test_model_manager.py    # 模型管理器测试
├── test_api.py             # API 端点测试
├── test_platform_clients.py # 平台客户端测试
├── test_integration.py     # 集成测试
└── README.md               # 本文档
```

## 测试类型

### 1. 单元测试 (Unit Tests)
- **test_config.py**: 测试配置加载和验证
- **test_model_manager.py**: 测试模型管理逻辑
- **test_platform_clients.py**: 测试各平台客户端
- **test_api.py**: 测试 API 端点行为

### 2. 集成测试 (Integration Tests)
- **test_integration.py**: 测试完整的请求流程

## 运行测试

### 安装测试依赖
```bash
uv sync --group dev
```

### 运行所有测试
```bash
# 使用测试脚本（推荐）
./run_tests.sh

# 或直接使用 pytest
uv run pytest tests/ -v
```

### 运行特定测试
```bash
# 运行单个测试文件
uv run pytest tests/test_config.py -v

# 运行特定测试类
uv run pytest tests/test_api.py::TestAPIEndpoints -v

# 运行特定测试方法
uv run pytest tests/test_api.py::TestAPIEndpoints::test_health_endpoint -v

# 运行匹配模式的测试
uv run pytest tests/ -k "health" -v
```

### 运行测试分类
```bash
# 运行单元测试
uv run pytest tests/ -m unit -v

# 运行集成测试  
uv run pytest tests/ -m integration -v
```

### 生成覆盖率报告
```bash
# 生成覆盖率报告
uv run pytest tests/ --cov=src --cov-report=html:htmlcov

# 查看覆盖率报告
open htmlcov/index.html
```

## 测试配置

测试使用以下配置文件：
- `pytest.ini`: pytest 配置
- `conftest.py`: 共享的 fixtures 和配置

### 主要 Fixtures

#### conftest.py 中的 Fixtures:
- `test_settings`: 测试用的设置配置
- `mock_settings`: 模拟的设置，用于隔离测试
- `client`: 测试客户端，用于 API 测试
- `mock_httpx_client`: 模拟的 HTTP 客户端
- `temp_db`: 临时数据库用于测试

## 测试覆盖范围

### 配置测试 (test_config.py)
- ✅ 默认设置值
- ✅ 环境变量加载
- ✅ 平台类型枚举
- ✅ 成本字段验证
- ✅ 无效配置处理

### 模型管理器测试 (test_model_manager.py)
- ✅ 模型管理器初始化
- ✅ 模型可用性检查
- ✅ 模型请求验证
- ✅ 模型请求处理
- ✅ 模型列表获取
- ✅ 配置重载

### API 测试 (test_api.py)
- ✅ 健康检查端点
- ✅ 模型列表端点
- ✅ 代理请求处理
- ✅ 错误处理
- ✅ 流式响应
- ✅ 不同 HTTP 方法

### 平台客户端测试 (test_platform_clients.py)
- ✅ 客户端工厂
- ✅ OpenAI 客户端
- ✅ Anthropic 客户端
- ✅ Google 客户端
- ✅ Azure OpenAI 客户端
- ✅ 自定义客户端

### 集成测试 (test_integration.py)
- ✅ 完整的聊天补全流程
- ✅ 错误处理流程
- ✅ 流式响应流程
- ✅ 多平台集成

## 编写新测试

### 测试命名规则
- 测试函数以 `test_` 开头
- 测试类以 `Test` 开头
- 测试文件以 `test_` 开头

### 示例测试
```python
import pytest
from unittest.mock import patch

def test_example_function():
    \"\"\"测试示例函数。\"\"\"
    # Arrange
    input_data = "test_input"
    expected_output = "expected_output"
    
    # Act
    result = example_function(input_data)
    
    # Assert
    assert result == expected_output

@pytest.mark.asyncio
async def test_async_function():
    \"\"\"测试异步函数。\"\"\"
    result = await async_function()
    assert result is not None

def test_with_mock():
    \"\"\"使用 mock 的测试。\"\"\"
    with patch('module.function') as mock_func:
        mock_func.return_value = "mocked_value"
        result = function_that_calls_mocked()
        assert result == "mocked_value"
        mock_func.assert_called_once()
```

### Async 测试
对于异步函数，使用 `@pytest.mark.asyncio` 装饰器：

```python
@pytest.mark.asyncio
async def test_async_endpoint():
    async with httpx.AsyncClient() as client:
        response = await client.get("/endpoint")
        assert response.status_code == 200
```

### Mock 使用
使用 `unittest.mock` 来模拟外部依赖：

```python
from unittest.mock import patch, MagicMock, AsyncMock

# 模拟同步函数
with patch('module.function') as mock_func:
    mock_func.return_value = "test"

# 模拟异步函数
mock_func = AsyncMock(return_value="test")
```

## 持续集成

这些测试可以集成到 CI/CD 流水线中：

```yaml
# GitHub Actions 示例
- name: Run tests
  run: |
    uv sync --group dev
    uv run pytest tests/ --cov=src --cov-fail-under=80
```

## 调试测试

### 调试失败的测试
```bash
# 显示详细错误信息
uv run pytest tests/ -vvv

# 在第一个失败时停止
uv run pytest tests/ -x

# 显示本地变量
uv run pytest tests/ -l

# 进入 pdb 调试器
uv run pytest tests/ --pdb
```

### 测试性能
```bash
# 显示最慢的测试
uv run pytest tests/ --durations=10
```

## 最佳实践

1. **隔离性**: 每个测试应该独立运行，不依赖其他测试的状态
2. **可重复性**: 测试结果应该一致和可预测
3. **快速性**: 单元测试应该快速执行
4. **清晰性**: 测试意图应该清晰明确
5. **覆盖性**: 重要的代码路径都应该被测试覆盖

## 故障排除

### 常见问题

1. **导入错误**: 确保 `PYTHONPATH` 正确设置
2. **异步测试失败**: 确保使用 `@pytest.mark.asyncio`
3. **数据库错误**: 使用内存数据库进行测试
4. **环境变量冲突**: 在测试中使用 `patch.dict(os.environ)`

### 获取帮助
如果测试失败或有疑问，请检查：
1. 测试输出的详细错误信息
2. 相关的测试文档
3. 项目的 issues 页面
# OpenAI API 统一代理服务 - 开发指南

## 🎯 项目概述

这是一个高性能、生产就绪的统一 AI API 代理服务，提供完全兼容 OpenAI API 的接口，支持多平台 AI 服务（OpenAI、Claude、Gemini、Azure OpenAI、Coze Bot 等）透明转发。

## 🛠️ 开发环境要求

- Python 3.9+
- uv (包管理器) - **必须使用 uv 来管理包和运行 Python 命令**
- SQLite 3.x
- Docker (可选，用于容器化部署)

## 📦 依赖管理

### 核心原则
- **始终使用 uv 来管理包和运行 Python 命令**
- 使用 memoization 优化性能
- 保持代码简洁和高质量

### 安装依赖
```bash
# 安装 uv (如果尚未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 同步依赖
uv sync

# 安装开发依赖
uv sync --extra dev
```

## 🚀 启动服务

### 开发模式
```bash
# 使用启动脚本（推荐）
./run.sh

# 或直接运行
uv run python start.py

# 或使用模块方式
uv run python -m src.main
```

### 生产模式
```bash
# 使用 Docker Compose
docker-compose up -d

# 或直接使用 Docker
docker build -t openai-proxy .
docker run -d -p 8000:8000 --env-file .env openai-proxy
```

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
uv run pytest

# 运行特定测试模块
uv run pytest tests/test_api.py

# 运行测试并生成覆盖率报告
uv run pytest --cov=src --cov-report=html

# 快速测试脚本
./run_tests.sh
```

### 测试要求
- 保持 90%+ 的测试覆盖率
- 所有新功能必须有相应的测试
- 测试使用完全隔离的环境（内存数据库、Mock 服务）

## 🔧 代码质量

### 代码格式化和检查
```bash
# 代码格式化
uv run black src/ tests/
uv run isort src/ tests/

# 代码检查
uv run flake8 src/ tests/

# 类型检查
uv run mypy src/

# 运行所有质量检查
uv run pre-commit run --all-files
```

### 代码规范
- 使用 Black 进行代码格式化（行长度 88）
- 使用 isort 进行导入排序
- 使用 flake8 进行代码检查
- 使用 mypy 进行类型检查
- 遵循 PEP 8 标准

## 🏗️ 项目架构

### 目录结构
```
src/
├── api/                    # API 路由层
│   ├── auth_api.py        # 认证管理接口
│   ├── conversation_api.py # 对话管理接口
│   ├── openai_api.py      # OpenAI 标准接口
│   ├── proxy.py           # 代理接口实现
│   └── responses.py       # 响应格式化
├── adapters/              # 平台适配器
│   ├── base.py           # 基础适配器
│   ├── coze_adapter.py   # Coze Bot 适配器
│   ├── manager.py        # 适配器管理器
│   └── proxy.py          # 代理适配器
├── auth/                  # 认证系统
│   └── client_auth.py    # 客户端认证管理
├── config/                # 配置管理
│   └── settings.py       # 环境配置
├── core/                  # 核心业务逻辑
│   ├── model_manager.py  # 模型管理器
│   └── platform_clients.py # 平台客户端
├── database/              # 数据层
│   ├── connection.py     # 数据库连接
│   ├── conversation_repository.py # 对话数据仓库
│   └── repository.py     # 基础数据仓库
├── log_config/            # 日志系统
│   ├── config.py         # 日志配置
│   └── middleware.py     # 日志中间件
├── models/                # 数据模型
│   ├── client.py         # 客户端模型
│   ├── conversation.py   # 对话模型
│   ├── openai.py         # OpenAI 模型
└── main.py               # 应用入口点
```

### 核心组件

#### 1. 模型管理器 (ModelManager)
- 位置: `src/core/model_manager.py`
- 功能: 管理 AI 模型配置和实例化
- 支持多平台配置

#### 2. 平台客户端 (PlatformClient)
- 位置: `src/core/platform_clients.py`
- 功能: 封装各平台 API 调用
- 支持的平台: OpenAI, Anthropic, Google, Azure OpenAI, Coze Bot

#### 3. 适配器系统
- 位置: `src/adapters/`
- 功能: 统一不同平台的 API 接口差异
- 可扩展设计，支持新平台接入

#### 4. 认证系统
- 位置: `src/auth/`
- 功能: API 密钥管理和客户端认证
- 支持默认客户端自动初始化

## ⚙️ 配置管理

### 环境配置
配置文件: `src/config/settings.py`

主要配置项:
- 服务器配置 (host, port, log_level)
- 数据库配置 (database_url)
- 认证配置 (enable_client_auth, allow_anonymous_access)
- AI 平台配置 (type, api_key, base_url, actual_name)

### 环境变量
创建并配置 `.env` 文件:
```env
# 服务配置
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info

# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./data/proxy.db

# 认证配置
ENABLE_CLIENT_AUTH=true
ALLOW_ANONYMOUS_ACCESS=false

# AI 模型配置
TYPE=openai
API_KEY=your_api_key_here
BASE_URL=https://api.openai.com/v1
ACTUAL_NAME=gpt-3.5-turbo
```

## 🔌 添加新平台支持

### 1. 定义平台类型
在 `src/config/settings.py` 中添加新的 `PlatformType`:
```python
class PlatformType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    # ... 现有平台
    NEW_PLATFORM = "new_platform"  # 添加新平台
```

### 2. 创建平台客户端
在 `src/core/platform_clients.py` 中添加新的客户端类:
```python
class NewPlatformClient(BasePlatformClient):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
    
    async def chat_completion(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # 实现聊天完成接口
        pass
```

### 3. 创建适配器
在 `src/adapters/` 目录下创建新的适配器文件:
```python
class NewPlatformAdapter(BaseAdapter):
    def transform_request(self, openai_request: Dict[str, Any]) -> Dict[str, Any]:
        # 将 OpenAI 格式请求转换为目标平台格式
        pass
    
    def transform_response(self, platform_response: Dict[str, Any]) -> Dict[str, Any]:
        # 将平台响应转换为 OpenAI 格式
        pass
```

### 4. 注册适配器
在 `src/adapters/manager.py` 中注册新适配器:
```python
def get_adapter(platform_type: str) -> BaseAdapter:
    adapters = {
        "openai": OpenAIAdapter(),
        "anthropic": AnthropicAdapter(),
        # ... 现有适配器
        "new_platform": NewPlatformAdapter(),  # 添加新适配器
    }
    return adapters.get(platform_type, OpenAIAdapter())
```

## 📊 日志和监控

### 日志配置
- 结构化日志 (structlog)
- JSON 格式输出
- 自动过滤敏感信息
- 支持文件和控制台输出

### 监控指标
- 请求处理时间
- 错误率统计
- 平台响应延迟
- 并发请求数量

## 🔐 安全考虑

### API 密钥管理
- 使用环境变量存储敏感信息
- 自动过滤日志中的密钥信息
- 支持客户端 API 密钥轮换

### 生产部署安全
- 启用客户端认证
- 使用 HTTPS 传输
- 限制 CORS 域名
- 配置防火墙规则

## 🚢 部署指南

### Docker 部署
```bash
# 构建镜像
docker build -t openai-proxy .

# 运行容器
docker run -d \
  --name openai-proxy \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  openai-proxy
```

### 生产环境建议
- 使用非 root 用户运行
- 配置资源限制
- 启用日志轮转
- 设置健康检查
- 配置负载均衡

## 🧩 扩展开发

### 添加新功能
1. 编写功能代码
2. 添加相应测试
3. 更新文档
4. 运行质量检查
5. 确保测试覆盖率

### 调试技巧
```bash
# 查看实时日志
tail -f logs/proxy.log

# 检查服务状态
curl http://localhost:8000/health

# 查看数据库内容
uv run python -c "
from src.database.connection import get_db_session
from src.models.conversation import ConversationMessage
async def check_logs():
    async with get_db_session() as session:
        # 查询逻辑
"
```

## 🔄 版本发布

### 发布流程
1. 更新版本号 (`pyproject.toml`)
2. 运行完整测试套件
3. 生成变更日志
4. 创建发布标签
5. 构建 Docker 镜像
6. 部署到生产环境

### 版本命名
- 主版本: 重大架构变更
- 次版本: 新功能添加
- 修补版本: 错误修复

---

## 📝 重要提醒

- **始终使用 uv 管理包和运行 Python 命令**
- 在适当的地方使用 memoization 优化性能
- 保持高代码质量和测试覆盖率
- 遵循现有的代码风格和架构模式
- 注意安全性，保护 API 密钥和敏感数据
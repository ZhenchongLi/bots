# OpenAI API 统一代理服务

一个简洁的单模型代理服务，提供OpenAI API兼容接口，透明转发并记录请求。

## 功能特性

- **单模型代理**: 专注于单个AI模型的代理服务，配置简单
- **多平台支持**: 支持连接OpenAI、Claude、Gemini等多个AI平台
- **格式转换**: 自动处理不同AI服务间的API格式差异  
- **日志记录**: 自动记录每个请求和响应的内容到SQLite数据库和日志文件
- **异步处理**: 基于FastAPI的高性能异步处理

## 技术栈

- **FastAPI**: 轻量级高效Web服务框架
- **SQLAlchemy**: 数据库ORM，异步支持
- **SQLite**: 请求响应日志存储
- **Structlog**: 结构化日志记录
- **Uvicorn**: ASGI服务器

## 快速开始

### 1. 安装依赖

使用uv管理依赖：

```bash
# 安装uv (如果尚未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 同步依赖
uv sync
```

### 2. 配置环境变量

复制环境变量模板：
```bash
cp .env.example .env
```

编辑 `.env` 文件，配置你的AI模型：
```env
# 平台类型 (openai, anthropic, google, azure_openai, custom)
TYPE=openai
# API密钥
API_KEY=your_api_key_here
# API基础URL
BASE_URL=https://api.openai.com/v1
# 实际模型名称
ACTUAL_NAME=gpt-3.5-turbo
```

### 3. 运行服务

使用启动脚本：
```bash
./run.sh
```

或直接使用uv运行：
```bash
uv run python start.py
```

或使用uv运行模块：
```bash
uv run python -m src.main
```

### 4. 测试代理

服务启动后，你可以将OpenAI API请求发送到 `http://localhost:8000` 而不是 `https://api.openai.com/v1`。

例如：
```bash
curl http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## 项目结构

```
├── src/
│   ├── api/           # API路由（代理接口）
│   ├── core/          # 核心业务逻辑（模型管理、平台客户端）
│   ├── config/        # 配置管理
│   ├── database/      # 数据库连接和仓库
│   ├── logging/       # 日志配置和中间件
│   └── models/        # 数据模型
├── tests/             # 测试文件
├── logs/              # 日志文件目录
├── data/              # 数据库文件目录
└── pyproject.toml     # 项目配置和依赖
```

## 配置说明

主要配置项在 `.env` 文件中：

### 基础配置
- `HOST`: 服务监听地址 (默认: 0.0.0.0)
- `PORT`: 服务监听端口 (默认: 8000)
- `DATABASE_URL`: SQLite数据库URL（默认存储在data目录）
- `LOG_FILE_PATH`: 日志文件路径（默认存储在logs目录）

### 单模型配置
- `TYPE`: 平台类型 (openai, anthropic, google, azure_openai, custom)
- `API_KEY`: API密钥
- `BASE_URL`: API基础URL
- `ACTUAL_NAME`: 实际模型名称
- `ENABLED`: 是否启用 (默认: true)
- `MAX_TOKENS`: 最大令牌数 (默认: 4096)
- `SUPPORTS_STREAMING`: 是否支持流式输出 (默认: true)
- `SUPPORTS_FUNCTION_CALLING`: 是否支持函数调用 (默认: true)

## 平台配置示例

### OpenAI 配置
```env
TYPE=openai
API_KEY=sk-your-openai-api-key
BASE_URL=https://api.openai.com/v1
ACTUAL_NAME=gpt-4
```

### Claude 配置
```env
TYPE=anthropic
API_KEY=sk-ant-your-claude-key
BASE_URL=https://api.anthropic.com/v1
ACTUAL_NAME=claude-3-sonnet-20240229
```

### Gemini 配置
```env
TYPE=google
API_KEY=your-google-api-key
BASE_URL=https://generativelanguage.googleapis.com/v1
ACTUAL_NAME=gemini-pro
```

### Azure OpenAI 配置
```env
TYPE=azure_openai
API_KEY=your-azure-api-key
BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
ACTUAL_NAME=gpt-4
```

### 本地模型配置 (Ollama)
```env
TYPE=custom
API_KEY=not-needed
BASE_URL=http://localhost:11434/v1
ACTUAL_NAME=llama2
```

## API 接口

### 获取可用模型
```bash
GET /models
```

### 健康检查
```bash
GET /health
```

## 日志记录

系统会自动记录所有通过代理的请求和响应：

1. **数据库日志**: 存储在SQLite数据库中，包含请求/响应的完整信息
2. **文件日志**: 结构化JSON格式的日志文件

## 使用说明

本代理服务会将所有请求中的模型名称替换为配置的 `ACTUAL_NAME`，然后转发到对应的AI平台。你可以使用任何模型名称发起请求，服务会自动处理。

## 开发

### 安装开发依赖

```bash
uv sync --extra dev
```

### 代码格式化

```bash
uv run black src/
uv run isort src/
```

### 类型检查

```bash
uv run mypy src/
```

## 注意事项

1. 确保为所选AI平台配置正确的API密钥和BASE_URL
2. 生产环境中请配置适当的CORS策略
3. 定期清理旧的日志文件以节省存储空间
4. 修改配置后需要重启服务才能生效
5. 所有客户端请求中的模型名称会被自动替换为ACTUAL_NAME
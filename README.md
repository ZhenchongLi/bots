# OpenAI API 统一代理服务

一个统一的代理服务，支持任意OpenAI API兼容请求，透明转发并记录请求。

## 功能特性

- **代理功能**: 接收OpenAI API规范的请求，无修改转发至实际OpenAI API
- **日志记录**: 自动记录每个请求和响应的内容到SQLite数据库和日志文件
- **向量存储**: 预留Qdrant向量数据库集成，支持未来的智能分析需求
- **异步处理**: 基于FastAPI的高性能异步处理

## 技术栈

- **FastAPI**: 轻量级高效Web服务框架
- **SQLAlchemy**: 数据库ORM，异步支持
- **SQLite**: 请求响应日志存储
- **Qdrant**: 向量数据库（可选）
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

编辑 `.env` 文件，设置你的OpenAI API密钥：
```env
OPENAI_API_KEY=your_openai_api_key_here
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
│   ├── api/           # API路由
│   ├── core/          # 核心业务逻辑
│   ├── config/        # 配置管理
│   ├── database/      # 数据库连接和仓库
│   ├── logging/       # 日志配置和中间件
│   └── models/        # 数据模型
├── tests/             # 测试文件
├── logs/              # 日志文件目录
└── requirements.txt   # 依赖列表
```

## 配置说明

主要配置项在 `.env` 文件中：

### 基础配置
- `OPENAI_API_KEY`: OpenAI API密钥（必需）
- `OPENAI_BASE_URL`: OpenAI API基础URL
- `HOST`: 服务监听地址
- `PORT`: 服务监听端口
- `DATABASE_URL`: SQLite数据库URL
- `QDRANT_URL`: Qdrant向量数据库URL（可选）
- `LOG_FILE_PATH`: 日志文件路径

### 模型配置
- `AVAILABLE_MODELS`: 可用模型列表（逗号分隔）
- `VALIDATE_MODELS`: 是否验证模型名称（true/false）
- `ALLOW_UNKNOWN_MODELS`: 是否允许未知模型（true/false）
- `MODEL_MAPPINGS`: 模型映射（JSON格式，用于模型别名）

## 模型管理

### 支持的OpenAI模型
默认支持以下模型：
- GPT系列: `gpt-4`, `gpt-4-turbo`, `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`
- 嵌入模型: `text-embedding-ada-002`, `text-embedding-3-small`, `text-embedding-3-large`
- 音频模型: `whisper-1`, `tts-1`, `tts-1-hd`
- 图像模型: `dall-e-2`, `dall-e-3`

### 模型别名和映射
可以通过环境变量或管理API配置模型别名：

```env
# 将claude映射到gpt-4，llama映射到gpt-3.5-turbo
MODEL_MAPPINGS={"claude":"gpt-4","llama":"gpt-3.5-turbo"}
```

### 管理API端点

#### 获取可用模型
```bash
GET /models
```

#### 管理API (需要管理员权限)
```bash
# 获取模型配置
GET /admin/models

# 添加新模型
POST /admin/models
{
  "name": "new-model-name",
  "display_name": "New Model",
  "description": "Model description"
}

# 删除模型
DELETE /admin/models/{model_name}

# 添加模型映射
POST /admin/model-mappings
{
  "alias": "my-model",
  "actual_model": "gpt-4"
}

# 删除模型映射
DELETE /admin/model-mappings/{alias}

# 重新加载配置
POST /admin/reload-config
```

### 兼容其他OpenAI-like API
要连接到其他OpenAI兼容的API（如Azure OpenAI、本地部署的模型等）：

1. 修改 `OPENAI_BASE_URL` 为目标API地址
2. 设置对应的 `OPENAI_API_KEY`
3. 根据目标API支持的模型更新 `AVAILABLE_MODELS`
4. 使用 `MODEL_MAPPINGS` 创建模型别名以保持兼容性

例如连接到Azure OpenAI：
```env
OPENAI_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
OPENAI_API_KEY=your-azure-api-key
AVAILABLE_MODELS=gpt-35-turbo,gpt-4
MODEL_MAPPINGS={"gpt-3.5-turbo":"gpt-35-turbo"}
```

## 日志记录

系统会自动记录所有通过代理的请求和响应：

1. **数据库日志**: 存储在SQLite数据库中，包含请求/响应的完整信息
2. **文件日志**: 结构化JSON格式的日志文件
3. **向量存储**: 可选的Qdrant向量数据库存储（用于未来的相似性搜索）

## 健康检查

访问 `http://localhost:8000/health` 检查服务状态。

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

1. 确保设置正确的OpenAI API密钥
2. 生产环境中请配置适当的CORS策略
3. 定期清理旧的日志文件以节省存储空间
4. Qdrant集成是可选的，如不需要可忽略相关配置
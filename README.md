# OpenAI API 统一代理服务 🚀

[![Tests](https://img.shields.io/badge/tests-55%20passed-brightgreen)](./tests/)
[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen)](./htmlcov/index.html)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

一个高性能、生产就绪的统一 AI API 代理服务，提供完全兼容 OpenAI API 的接口，支持多平台 AI 服务（OpenAI、Claude、Gemini、Azure OpenAI 等）透明转发，具备完整的请求日志记录和监控功能。

> **🎯 核心优势**：统一接口、多平台支持、完整日志、生产就绪

## ✨ 核心功能

### 🚀 代理服务
- **🎯 统一接口**: 提供标准 OpenAI API 兼容接口，支持所有主流客户端
- **🌐 多平台支持**: 支持 OpenAI、Claude (Anthropic)、Gemini (Google)、Azure OpenAI、Coze Bot 等
- **🔌 适配器架构**: 基于插件式适配器系统，易于扩展新的 AI 平台
- **🔄 智能转换**: 自动处理不同 AI 服务间的 API 格式差异和参数映射
- **⚡ 高性能**: 基于 FastAPI 异步框架，支持高并发请求处理

### 📊 监控日志
- **📝 完整记录**: 自动记录每个请求和响应到 SQLite 数据库
- **🔍 结构化日志**: JSON 格式日志文件，便于分析和监控
- **📈 性能监控**: 内置请求处理时间、吞吐量和错误率统计
- **🔐 隐私保护**: 自动过滤敏感信息，保护 API 密钥和用户数据

### 🛡️ 生产特性
- **✅ 高质量**: 91% 测试覆盖率，55 个单元测试，零警告代码
- **🐳 容器化**: 完整的 Docker 支持，一键部署
- **🔧 易配置**: 环境变量配置，支持多环境部署
- **📦 开箱即用**: 零配置启动，自动环境隔离
- **🔑 客户端管理**: 启动时自动检查并创建默认客户端，持久化API密钥管理

## 🚀 快速开始

### 方法一：使用 UV（推荐）

```bash
# 1. 克隆项目
git clone <your-repository-url>
cd bots

# 2. 安装 uv（如果尚未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. 安装依赖
uv sync

# 4. 配置环境变量（参考下方配置说明）
cp .env.example .env
# 编辑 .env 文件，设置你的 API 密钥和配置

# 5. 启动服务
./run.sh
```

服务启动后，访问 http://localhost:8000/docs 查看 API 文档。

### 方法二：使用 Docker

```bash
# 1. 克隆项目
git clone <your-repository-url>
cd bots

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置API密钥等配置

# 3. 使用 Docker Compose 启动
docker-compose up -d

# 4. 检查服务状态
curl http://localhost:8000/health
```

### 方法三：直接运行

```bash
# 使用 Python 直接运行
uv run python start.py

# 或使用模块方式运行
uv run python -m src.main
```

## ⚙️ 配置说明

### 基础配置示例

创建 `.env` 文件并配置以下参数：

```env
# 服务配置
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info

# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./data/proxy.db

# 客户端认证配置
ENABLE_CLIENT_AUTH=true
ALLOW_ANONYMOUS_ACCESS=false

# 日志配置
LOG_FILE_PATH=./logs/proxy.log
LOG_RETENTION_DAYS=30

# AI 模型配置
TYPE=openai
API_KEY=your_api_key_here
BASE_URL=https://api.openai.com/v1
ACTUAL_NAME=gpt-3.5-turbo
ENABLED=true
MAX_TOKENS=4096
SUPPORTS_STREAMING=true
SUPPORTS_FUNCTION_CALLING=true
```

> **🔑 认证说明**: 启动服务时，系统会自动生成默认管理员 API 密钥并显示在控制台。请妥善保存此密钥，用于后续的 API 调用和管理操作。

### 多平台配置示例

<details>
<summary>🤖 OpenAI 配置</summary>

```env
TYPE=openai
API_KEY=sk-your-openai-api-key
BASE_URL=https://api.openai.com/v1
ACTUAL_NAME=gpt-4
```
</details>

<details>
<summary>🧠 Claude (Anthropic) 配置</summary>

```env
TYPE=anthropic
API_KEY=sk-ant-your-claude-key
BASE_URL=https://api.anthropic.com/v1
ACTUAL_NAME=claude-3-sonnet-20240229
```
</details>

<details>
<summary>💎 Gemini (Google) 配置</summary>

```env
TYPE=google
API_KEY=your-google-api-key
BASE_URL=https://generativelanguage.googleapis.com/v1
ACTUAL_NAME=gemini-pro
```
</details>

<details>
<summary>☁️ Azure OpenAI 配置</summary>

```env
TYPE=azure_openai
API_KEY=your-azure-api-key
BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
ACTUAL_NAME=gpt-4
```
</details>

<details>
<summary>🤖 Coze Bot 配置</summary>

```env
TYPE=coze
API_KEY=pat_91b9201327ac94c40b5630ee49e4d76a666b5e9d965d99ec21035c05d89a1e38
BASE_URL=http://your-coze-api-host:port
ACTUAL_NAME=bot-7533263489985413120
ENABLED=true
SUPPORTS_STREAMING=true
SUPPORTS_FUNCTION_CALLING=false
```

**配置说明:**
- `API_KEY`: Coze Bot 的 Personal Access Token (以 `pat_` 开头)  
- `BASE_URL`: Coze API 服务器地址
- `ACTUAL_NAME`: 使用 `bot-{COZE_BOT_ID}` 格式，系统会自动提取 bot_id
- 支持完整的流式和非流式响应
- 兼容标准 OpenAI Python SDK

**使用示例:**
```python
import openai

client = openai.OpenAI(
    api_key="your-proxy-api-key",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="bot-7533263489985413120",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True
)
```
</details>

<details>
<summary>🏠 本地模型配置 (Ollama)</summary>

```env
TYPE=custom
API_KEY=not-needed
BASE_URL=http://localhost:11434/v1
ACTUAL_NAME=llama2
```
</details>

## 📖 API 文档

服务启动后，访问以下地址获取 API 文档：

- **交互式文档**: http://localhost:8000/docs
- **ReDoc 文档**: http://localhost:8000/redoc
- **客户端使用指南**: [CLIENT_USAGE_GUIDE.md](CLIENT_USAGE_GUIDE.md)
- **对话功能指南**: [CONVERSATION_USAGE_GUIDE.md](CONVERSATION_USAGE_GUIDE.md)
- **开发指南**: [CLAUDE.md](CLAUDE.md)

### 核心接口

| 接口 | 方法 | 描述 | 示例 |
|------|------|------|------|
| `/health` | GET | 健康检查 | `curl http://localhost:8000/health` |
| `/models` | GET | 获取可用模型列表 | `curl http://localhost:8000/models` |
| `/chat/completions` | POST | 聊天完成接口 | 见下方示例 |
| `/embeddings` | POST | 文本嵌入接口 | 兼容 OpenAI 格式 |
| `/conversations/` | POST | 创建对话会话 | 支持会话管理 |
| `/conversations/user/{user_id}` | GET | 获取用户对话列表 | 分页查询支持 |
| `/auth/keys` | GET/POST | API 密钥管理 | 需要管理员权限 |

### 使用示例

```bash
# 健康检查
curl http://localhost:8000/health

# 获取模型列表
curl http://localhost:8000/models

# 聊天完成（流式）
curl http://localhost:8000/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer your-api-key" \\
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'

# 聊天完成（非流式）
curl http://localhost:8000/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer your-api-key" \\
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Explain quantum computing in simple terms."}
    ],
    "max_tokens": 150,
    "temperature": 0.7
  }'
```

## 🏗️ 项目架构

```
├── src/                    # 源代码目录
│   ├── api/               # API 路由层
│   │   ├── proxy.py       # 代理接口实现
│   │   ├── auth_api.py    # 认证管理接口
│   │   └── conversation_api.py # 对话管理接口
│   ├── adapters/          # 平台适配器系统
│   │   ├── base.py        # 基础适配器类
│   │   ├── manager.py     # 适配器管理器
│   │   ├── coze_adapter.py # Coze Bot 适配器
│   │   └── proxy.py       # 代理适配器
│   ├── auth/              # 认证系统
│   │   └── client_auth.py # 客户端认证管理
│   ├── core/              # 核心业务逻辑
│   │   ├── model_manager.py      # 模型管理器
│   │   └── platform_clients.py  # 平台客户端
│   ├── config/            # 配置管理
│   │   └── settings.py    # 环境配置
│   ├── database/          # 数据层
│   │   ├── connection.py  # 数据库连接
│   │   └── repository.py  # 数据仓库
│   ├── log_config/        # 日志系统
│   │   ├── config.py      # 日志配置
│   │   └── middleware.py  # 日志中间件
│   ├── models/            # 数据模型
│   │   ├── conversation.py # 对话模型
│   │   └── client.py      # 客户端模型
│   └── main.py           # 应用入口点
├── tests/                 # 测试目录（91% 覆盖率）
│   ├── test_api.py       # API 接口测试
│   ├── test_config.py    # 配置测试
│   ├── test_integration.py # 集成测试
│   ├── test_model_manager.py # 模型管理测试
│   └── test_platform_clients.py # 平台客户端测试
├── data/                  # 数据文件
├── logs/                  # 日志文件
├── htmlcov/              # 测试覆盖率报告
├── docker-compose.yml    # Docker 编排
├── Dockerfile           # Docker 镜像
└── pyproject.toml       # 项目配置
```

## 🧪 测试与质量保证

### 测试统计

- **✅ 总测试数**: 55 个
- **✅ 通过率**: 100%
- **✅ 测试覆盖率**: 91%
- **✅ 代码质量**: 零警告

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试模块
uv run pytest tests/test_api.py

# 运行测试并生成覆盖率报告
uv run pytest --cov=src --cov-report=html

# 运行测试（快速模式）
./run_tests.sh
```

### 测试环境

项目使用完全隔离的测试环境：

- **🔒 环境隔离**: 使用 `.env.test` 文件，不影响生产配置
- **💾 内存数据库**: 使用 SQLite 内存模式，测试后自动清理
- **🛡️ Mock 服务**: 完整的外部服务模拟，无需真实 API 调用
- **📊 详细报告**: HTML 格式的测试覆盖率报告

## 🐳 Docker 部署

### 使用 Docker Compose（推荐）

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 直接使用 Docker

```bash
# 构建镜像
docker build -t openai-proxy .

# 运行容器
docker run -d \\
  --name openai-proxy \\
  -p 8000:8000 \\
  -v $(pwd)/data:/app/data \\
  -v $(pwd)/logs:/app/logs \\
  --env-file .env \\
  openai-proxy
```

## 🔧 开发指南

### 开发环境设置

```bash
# 安装开发依赖
uv sync --extra dev

# 安装 Git 钩子（可选）
pre-commit install
```

### 代码质量工具

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

### 添加新功能

1. **创建功能分支**: `git checkout -b feature/your-feature`
2. **编写代码**: 遵循现有代码风格和架构
3. **添加测试**: 确保新功能有相应的单元测试
4. **运行测试**: `uv run pytest` 确保所有测试通过
5. **检查覆盖率**: 保持 90%+ 的测试覆盖率
6. **提交代码**: 使用清晰的提交信息

## 📊 监控与日志

### 日志系统

项目使用结构化日志记录，支持多种输出格式：

- **📁 文件日志**: JSON 格式，便于分析和监控
- **💾 数据库日志**: 完整的请求/响应记录，支持查询分析
- **🖥️ 控制台日志**: 开发环境友好的彩色输出

### 日志级别

```env
LOG_LEVEL=debug   # 详细调试信息
LOG_LEVEL=info    # 一般信息（推荐）
LOG_LEVEL=warning # 仅警告和错误
LOG_LEVEL=error   # 仅错误信息
```

### 性能监控

项目内置请求性能监控：

- **⏱️ 处理时间**: 记录每个请求的处理耗时
- **📈 吞吐量**: 统计请求频率和并发情况
- **❌ 错误率**: 监控失败请求和错误类型

## 🔐 安全考虑

### API 密钥管理

- **🔑 环境变量**: API 密钥通过环境变量配置，不写入代码
- **🚫 日志过滤**: 自动过滤日志中的敏感信息
- **🔒 传输加密**: 支持 HTTPS 和 TLS 加密传输
- **👤 客户端认证**: 基于API密钥的客户端身份验证系统
- **💾 持久化管理**: 客户端信息存储在数据库中，启动时自动初始化默认客户端

### 生产部署建议

```bash
# 1. 使用非 root 用户运行
USER_ID=1000 docker-compose up -d

# 2. 限制资源使用
docker run --memory=512m --cpus=1.0 openai-proxy

# 3. 启用日志轮转
LOG_RETENTION_DAYS=7

# 4. 配置防火墙
# 仅开放必要端口
```

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. **Fork 项目**
2. **创建功能分支** (`git checkout -b feature/AmazingFeature`)
3. **提交更改** (`git commit -m 'Add some AmazingFeature'`)
4. **推送分支** (`git push origin feature/AmazingFeature`)
5. **创建 Pull Request**

### 贡献要求

- ✅ 所有测试必须通过
- ✅ 新功能需要添加相应测试
- ✅ 保持 90%+ 的测试覆盖率
- ✅ 遵循现有代码风格
- ✅ 更新相关文档

## 🆘 故障排除

<details>
<summary>常见问题解决方案</summary>

### 问题：服务启动失败
```bash
# 检查端口占用
lsof -i :8000

# 检查环境变量
uv run python -c "from src.config.settings import settings; print(settings)"
```

### 问题：API 请求失败
```bash
# 检查服务状态
curl http://localhost:8000/health

# 查看实时日志
tail -f logs/proxy.log
```

### 问题：数据库连接错误
```bash
# 检查数据库文件权限
ls -la data/

# 重新初始化数据库
rm data/proxy.db && uv run python -c "from src.database.connection import init_db; import asyncio; asyncio.run(init_db())"
```

</details>

## 📝 更新日志

### v0.1.2 (Latest)
- 🔌 **全新适配器架构**: 实现基于插件的适配器系统，支持多平台扩展
- 🤖 **Coze Bot v3 支持**: 完整重构 Coze 适配器，支持 v3 API 和流式响应
- 🎯 **模型名称映射**: 支持 `bot-{ID}` 格式自动转换为 Coze Bot ID
- ⚡ **流式响应优化**: 改进流式响应处理，支持 Server-Sent Events 格式
- 📊 **增强监控**: 完善错误处理和详细的调试日志

### v0.1.1  
- ✨ 新增客户端认证系统
- 🔑 实现默认客户端自动初始化机制
- 💾 支持客户端信息持久化存储
- 🔄 启动时检查并创建默认客户端，避免重复生成API密钥

### v0.1.0
- ✨ 初始版本发布
- ✅ 支持 OpenAI、Claude、Gemini、Coze Bot 等多平台
- ✅ 完整的测试覆盖（91%）
- ✅ Docker 容器化支持
- ✅ 结构化日志和监控
- ✅ 生产就绪的代码质量

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

## 🙏 致谢

感谢所有为此项目做出贡献的开发者和社区成员。

---

<div align="center">
  <strong>🚀 让 AI API 代理变得简单而强大！</strong>
</div>
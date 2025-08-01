# Coze Studio 测试工具

这个目录包含了用于测试 Coze Bot 集成功能的测试脚本和工具。

## 文件说明

- `test_coze_studio.py` - 主要的测试脚本，用于测试 Coze Bot 的各种功能

## 使用方法

### 基本用法

```bash
# 进入项目根目录
cd /path/to/bots

# 运行测试脚本
uv run python coze/test_coze_studio.py \
  --api-key "YOUR_COZE_API_KEY" \
  --bot-id "YOUR_BOT_ID" \
  --base-url "https://api.coze.com"
```

### 参数说明

- `--api-key`: Coze API 密钥（必需）
- `--bot-id`: Coze Bot ID（必需）
- `--base-url`: Coze API 基础URL（可选，默认为 https://api.coze.com）
- `--save-report`: 保存测试报告到文件
- `--report-file`: 指定测试报告文件名

### 示例

```bash
# 基本测试
uv run python coze/test_coze_studio.py \
  --api-key "pat_xxx" \
  --bot-id "7445781234567890123"

# 测试并保存报告
uv run python coze/test_coze_studio.py \
  --api-key "pat_xxx" \
  --bot-id "7445781234567890123" \
  --save-report \
  --report-file "my_test_report.json"
```

## 测试内容

该测试脚本会执行以下测试：

1. **适配器配置验证** - 验证 Coze 适配器配置是否正确
2. **模型信息获取** - 测试获取模型信息功能
3. **基本聊天完成** - 测试非流式聊天完成功能
4. **多轮对话** - 测试多轮对话支持
5. **流式聊天** - 测试流式响应功能
6. **错误处理** - 测试错误处理机制

## 输出格式

测试脚本会输出详细的日志信息，包括：
- 每个测试的执行状态
- 请求和响应的详细信息
- 最终的测试汇总报告

## 测试报告

如果使用 `--save-report` 参数，测试结果会保存为 JSON 格式的报告文件，包含：
- 测试统计信息
- 每个测试的详细结果
- 时间戳和错误消息

## 故障排除

### 常见问题

1. **认证失败**
   - 检查 API 密钥是否正确
   - 确认 API 密钥有足够的权限

2. **Bot ID 无效**
   - 确认 Bot ID 格式正确
   - 检查 Bot 是否已发布并可用

3. **网络连接问题**
   - 检查网络连接
   - 确认防火墙设置
   - 验证 base-url 是否正确

4. **依赖问题**
   - 确保在项目根目录运行
   - 使用 `uv sync` 安装所有依赖

### 调试模式

要获取更详细的调试信息，可以设置环境变量：

```bash
export LOG_LEVEL=debug
uv run python coze/test_coze_studio.py --api-key "..." --bot-id "..."
```

## 贡献

如果发现问题或需要添加新的测试功能，请：
1. 在项目中创建 issue
2. 提交 pull request
3. 确保新代码通过现有测试
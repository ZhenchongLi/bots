#!/usr/bin/env python3
"""
简单的手动测试脚本，验证核心功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.settings import Settings, PlatformType
from src.core.model_manager import ModelManager
from src.core.platform_clients import PlatformClientFactory

def test_settings():
    """测试设置配置"""
    print("1. 测试设置配置...")
    
    # 清除环境变量
    env_backup = {}
    for key in ["TYPE", "API_KEY", "BASE_URL", "ACTUAL_NAME"]:
        env_backup[key] = os.environ.get(key)
        if key in os.environ:
            del os.environ[key]
    
    try:
        settings = Settings()
        assert settings.type == PlatformType.OPENAI
        assert settings.base_url == "https://api.openai.com/v1"
        assert settings.actual_name == "gpt-3.5-turbo"
        print("✅ 设置配置测试通过")
    finally:
        # 恢复环境变量
        for key, value in env_backup.items():
            if value is not None:
                os.environ[key] = value

def test_model_manager():
    """测试模型管理器"""
    print("2. 测试模型管理器...")
    
    # 模拟配置
    class MockSettings:
        type = PlatformType.OPENAI
        api_key = "test-key"
        base_url = "https://api.openai.com/v1"
        actual_name = "gpt-4"
        enabled = True
        default_headers = {}
        timeout = 300
        display_name = None
        description = None
        max_tokens = 4096
        supports_streaming = True
        supports_function_calling = True
        cost_per_1k_input_tokens = None
        cost_per_1k_output_tokens = None
    
    # 创建模型管理器
    manager = ModelManager()
    manager.config = {
        "type": PlatformType.OPENAI,
        "api_key": "test-key",
        "base_url": "https://api.openai.com/v1",
        "actual_name": "gpt-4",
        "enabled": True,
        "default_headers": {},
        "timeout": 300,
        "display_name": None,
        "description": None,
        "max_tokens": 4096,
        "supports_streaming": True,
        "supports_function_calling": True,
        "cost_per_1k_input_tokens": None,
        "cost_per_1k_output_tokens": None,
    }
    
    # 测试模型可用性
    assert manager.is_model_available() == True
    
    # 测试模型请求处理
    request_data = {"model": "gpt-3.5-turbo", "messages": []}
    processed_data, actual_model = manager.process_model_request(request_data)
    assert processed_data["model"] == "gpt-4"
    assert actual_model == "gpt-4"
    
    print("✅ 模型管理器测试通过")

def test_platform_clients():
    """测试平台客户端"""
    print("3. 测试平台客户端...")
    
    config = {
        "type": PlatformType.OPENAI,
        "api_key": "test-key",
        "base_url": "https://api.openai.com/v1",
        "timeout": 300
    }
    
    # 测试客户端工厂
    client = PlatformClientFactory.create_client(PlatformType.OPENAI, config)
    assert client is not None
    assert hasattr(client, 'make_request')
    
    # 测试不同平台的客户端创建
    platforms = [PlatformType.OPENAI, PlatformType.ANTHROPIC, PlatformType.GOOGLE, PlatformType.AZURE_OPENAI]
    for platform in platforms:
        client = PlatformClientFactory.create_client(platform, config)
        assert client is not None
    
    print("✅ 平台客户端测试通过")

def main():
    """运行所有测试"""
    print("运行简单测试...")
    print("=" * 50)
    
    try:
        test_settings()
        test_model_manager()
        test_platform_clients()
        
        print("=" * 50)
        print("🎉 所有测试通过！")
        print()
        print("核心功能验证成功：")
        print("- ✅ 配置系统正常")
        print("- ✅ 模型管理器正常")
        print("- ✅ 平台客户端正常")
        print()
        print("你可以继续运行完整的 pytest 测试套件。")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
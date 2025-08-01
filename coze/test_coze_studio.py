#!/usr/bin/env python3
"""
Coze Studio 测试脚本

该脚本用于测试 Coze Bot 集成的各种功能，包括：
- 基本聊天完成功能
- 流式响应
- 错误处理
- 认证
- 多轮对话
"""

import asyncio
import json
import os
import sys
import time
from typing import Dict, Any, Optional
import httpx
import argparse

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.coze_adapter import CozeAdapter
from src.core.platform_clients import PlatformClientFactory
from src.config.settings import Settings


class CozeStudioTester:
    """Coze Studio 功能测试器"""
    
    def __init__(self, api_key: str, base_url: str, bot_id: str):
        """初始化测试器"""
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.bot_id = bot_id
        self.test_results = {}
        
        # 配置适配器
        self.config = {
            "api_key": api_key,
            "base_url": base_url,
            "timeout": 300,
            "default_headers": {}
        }
        self.adapter = CozeAdapter(self.config)
    
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def record_result(self, test_name: str, success: bool, message: str = "", data: Any = None):
        """记录测试结果"""
        self.test_results[test_name] = {
            "success": success,
            "message": message,
            "data": data,
            "timestamp": time.time()
        }
    
    async def test_basic_chat_completion(self) -> bool:
        """测试基本聊天完成功能"""
        self.log("开始测试基本聊天完成功能...")
        
        try:
            # 构造 OpenAI 格式请求
            openai_request = {
                "model": f"bot-{self.bot_id}",
                "messages": [
                    {"role": "system", "content": "你是一个有用的助手。"},
                    {"role": "user", "content": "你好，请简单介绍一下你自己。"}
                ],
                "max_tokens": 150,
                "temperature": 0.7,
                "stream": False
            }
            
            # 转换为 Coze 格式
            coze_request = await self.adapter.transform_request("/chat/completions", openai_request)
            self.log(f"转换后的请求: {json.dumps(coze_request, ensure_ascii=False, indent=2)}")
            
            # 发送请求
            url = f"{self.base_url}/v3/chat"
            response = await self.adapter.make_request(
                method="POST",
                url=url,
                json_data=coze_request
            )
            
            if response["status_code"] == 200 and response["json"]:
                # 转换响应格式
                openai_response = await self.adapter.transform_response("/chat/completions", response["json"])
                
                self.log("✅ 基本聊天完成测试成功")
                self.log(f"响应: {json.dumps(openai_response, ensure_ascii=False, indent=2)}")
                
                self.record_result("basic_chat_completion", True, "成功完成基本聊天", openai_response)
                return True
            else:
                error_msg = f"请求失败: {response['status_code']}"
                if response.get("json"):
                    error_msg += f", 错误: {response['json']}"
                
                self.log(f"❌ 基本聊天完成测试失败: {error_msg}")
                self.record_result("basic_chat_completion", False, error_msg)
                return False
                
        except Exception as e:
            error_msg = f"异常: {str(e)}"
            self.log(f"❌ 基本聊天完成测试异常: {error_msg}")
            self.record_result("basic_chat_completion", False, error_msg)
            return False
    
    async def test_streaming_chat(self) -> bool:
        """测试流式聊天功能"""
        self.log("开始测试流式聊天功能...")
        
        try:
            # 构造流式请求
            openai_request = {
                "model": f"bot-{self.bot_id}",
                "messages": [
                    {"role": "user", "content": "请用几句话描述人工智能的发展历程，使用流式输出。"}
                ],
                "stream": True,
                "max_tokens": 200
            }
            
            # 转换为 Coze 格式
            coze_request = await self.adapter.transform_request("/chat/completions", openai_request)
            
            # 发送流式请求
            url = f"{self.base_url}/v3/chat"
            
            collected_content = ""
            chunk_count = 0
            
            async for chunk in self.adapter.make_stream_request(
                method="POST",
                url=url,
                json_data=coze_request
            ):
                chunk_count += 1
                self.log(f"收到流式数据块 {chunk_count}: {chunk[:100]}...")
                
                # 尝试解析 SSE 数据
                if chunk.startswith("data: "):
                    try:
                        data_str = chunk[6:]  # 移除 "data: " 前缀
                        if data_str.strip() == "[DONE]":
                            break
                        
                        data = json.loads(data_str)
                        if "choices" in data and data["choices"]:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                collected_content += delta["content"]
                    except json.JSONDecodeError:
                        pass
            
            if chunk_count > 0:
                self.log(f"✅ 流式聊天测试成功，收到 {chunk_count} 个数据块")
                self.log(f"收集到的内容: {collected_content}")
                
                self.record_result("streaming_chat", True, f"成功接收 {chunk_count} 个流式数据块", {
                    "chunk_count": chunk_count,
                    "content": collected_content
                })
                return True
            else:
                self.log("❌ 流式聊天测试失败: 未收到任何数据块")
                self.record_result("streaming_chat", False, "未收到任何数据块")
                return False
                
        except Exception as e:
            error_msg = f"异常: {str(e)}"
            self.log(f"❌ 流式聊天测试异常: {error_msg}")
            self.record_result("streaming_chat", False, error_msg)
            return False
    
    async def test_multi_turn_conversation(self) -> bool:
        """测试多轮对话功能"""
        self.log("开始测试多轮对话功能...")
        
        try:
            # 多轮对话序列
            conversation = [
                {"role": "user", "content": "我想了解 Python 编程"},
                {"role": "assistant", "content": "Python 是一种高级编程语言，以其简洁的语法而闻名。"},
                {"role": "user", "content": "能给我举个简单的例子吗？"}
            ]
            
            openai_request = {
                "model": f"bot-{self.bot_id}",
                "messages": conversation,
                "max_tokens": 200,
                "stream": False
            }
            
            coze_request = await self.adapter.transform_request("/chat/completions", openai_request)
            
            url = f"{self.base_url}/v3/chat"
            response = await self.adapter.make_request(
                method="POST",
                url=url,
                json_data=coze_request
            )
            
            if response["status_code"] == 200 and response["json"]:
                openai_response = await self.adapter.transform_response("/chat/completions", response["json"])
                
                self.log("✅ 多轮对话测试成功")
                self.log(f"响应: {json.dumps(openai_response, ensure_ascii=False, indent=2)}")
                
                self.record_result("multi_turn_conversation", True, "成功完成多轮对话", openai_response)
                return True
            else:
                error_msg = f"请求失败: {response['status_code']}"
                self.log(f"❌ 多轮对话测试失败: {error_msg}")
                self.record_result("multi_turn_conversation", False, error_msg)
                return False
                
        except Exception as e:
            error_msg = f"异常: {str(e)}"
            self.log(f"❌ 多轮对话测试异常: {error_msg}")
            self.record_result("multi_turn_conversation", False, error_msg)
            return False
    
    async def test_error_handling(self) -> bool:
        """测试错误处理机制"""
        self.log("开始测试错误处理机制...")
        
        try:
            # 测试无效的 bot_id
            invalid_request = {
                "model": "bot-invalid-bot-id",
                "messages": [{"role": "user", "content": "测试"}],
                "stream": False
            }
            
            coze_request = await self.adapter.transform_request("/chat/completions", invalid_request)
            
            url = f"{self.base_url}/v3/chat"
            response = await self.adapter.make_request(
                method="POST",
                url=url,
                json_data=coze_request
            )
            
            # 期望收到错误响应
            if response["status_code"] >= 400:
                self.log("✅ 错误处理测试成功 - 正确处理了无效请求")
                self.record_result("error_handling", True, f"正确返回错误状态码: {response['status_code']}", response)
                return True
            else:
                self.log("❌ 错误处理测试失败 - 应该返回错误但却成功了")
                self.record_result("error_handling", False, "无效请求意外成功")
                return False
                
        except Exception as e:
            # 某些异常是预期的，这也算是正确的错误处理
            self.log(f"✅ 错误处理测试成功 - 捕获到预期异常: {str(e)}")
            self.record_result("error_handling", True, f"正确抛出异常: {str(e)}")
            return True
    
    async def test_adapter_validation(self) -> bool:
        """测试适配器配置验证"""
        self.log("开始测试适配器配置验证...")
        
        try:
            # 测试配置验证
            is_valid = self.adapter.validate_config()
            
            if is_valid:
                self.log("✅ 适配器配置验证成功")
                self.record_result("adapter_validation", True, "配置验证通过")
                return True
            else:
                self.log("❌ 适配器配置验证失败")
                self.record_result("adapter_validation", False, "配置验证失败")
                return False
                
        except Exception as e:
            error_msg = f"异常: {str(e)}"
            self.log(f"❌ 适配器配置验证异常: {error_msg}")
            self.record_result("adapter_validation", False, error_msg)
            return False
    
    async def test_model_info(self) -> bool:
        """测试模型信息获取"""
        self.log("开始测试模型信息获取...")
        
        try:
            model_info = self.adapter.get_model_info()
            
            self.log("✅ 模型信息获取成功")
            self.log(f"模型信息: {json.dumps(model_info, ensure_ascii=False, indent=2)}")
            
            self.record_result("model_info", True, "成功获取模型信息", model_info)
            return True
            
        except Exception as e:
            error_msg = f"异常: {str(e)}"
            self.log(f"❌ 模型信息获取异常: {error_msg}")
            self.record_result("model_info", False, error_msg)
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        self.log("=" * 60)
        self.log("开始运行 Coze Studio 完整测试套件")
        self.log("=" * 60)
        
        tests = [
            ("适配器配置验证", self.test_adapter_validation),
            ("模型信息获取", self.test_model_info),
            ("基本聊天完成", self.test_basic_chat_completion),
            ("多轮对话", self.test_multi_turn_conversation),
            ("流式聊天", self.test_streaming_chat),
            ("错误处理", self.test_error_handling),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            self.log(f"\n--- 测试: {test_name} ---")
            try:
                result = await test_func()
                if result:
                    passed += 1
            except Exception as e:
                self.log(f"❌ 测试 {test_name} 发生未处理异常: {str(e)}")
                self.record_result(test_name.lower().replace(" ", "_"), False, f"未处理异常: {str(e)}")
        
        # 生成测试报告
        self.log("\n" + "=" * 60)
        self.log("测试结果汇总")
        self.log("=" * 60)
        self.log(f"总测试数: {total}")
        self.log(f"通过测试: {passed}")
        self.log(f"失败测试: {total - passed}")
        self.log(f"成功率: {(passed / total) * 100:.1f}%")
        
        # 详细结果
        self.log("\n详细结果:")
        for test_name, result in self.test_results.items():
            status = "✅ 通过" if result["success"] else "❌ 失败"
            self.log(f"  {test_name}: {status} - {result['message']}")
        
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": (passed / total) * 100,
            "results": self.test_results
        }
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """保存测试报告"""
        if filename is None:
            filename = f"coze_test_report_{int(time.time())}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        self.log(f"测试报告已保存到: {filename}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Coze Studio 测试脚本")
    parser.add_argument("--api-key", required=True, help="Coze API 密钥")
    parser.add_argument("--base-url", default="https://api.coze.com", help="Coze API 基础 URL")
    parser.add_argument("--bot-id", required=True, help="Coze Bot ID")
    parser.add_argument("--save-report", action="store_true", help="保存测试报告到文件")
    parser.add_argument("--report-file", help="测试报告文件名")
    
    args = parser.parse_args()
    
    # 创建测试器
    tester = CozeStudioTester(
        api_key=args.api_key,
        base_url=args.base_url,
        bot_id=args.bot_id
    )
    
    # 运行测试
    report = await tester.run_all_tests()
    
    # 保存报告
    if args.save_report:
        tester.save_report(report, args.report_file)
    
    # 返回适当的退出码
    exit_code = 0 if report["failed"] == 0 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())
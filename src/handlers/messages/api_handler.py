"""
API响应处理模块
负责与大语言模型API进行交互
"""

import logging
import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Tuple, Union
from src.handlers.messages.base_handler import BaseHandler

# 获取logger
logger = logging.getLogger('main')

class APIHandler(BaseHandler):
    """API处理器，负责与大语言模型API交互"""
    
    def __init__(self, message_manager=None, config=None, api_clients=None):
        """
        初始化API处理器
        
        Args:
            message_manager: 消息管理器实例的引用
            config: 配置信息字典
            api_clients: API客户端实例字典，键为模型名称
        """
        super().__init__(message_manager)
        self.config = config or {}
        self.api_clients = api_clients or {}
        
        # 从config.yaml加载模型配置
        try:
            from src.config import config as global_config
            # 根据配置文件结构访问LLM配置
            # 配置对象使用SettingReader类实现，LLM配置通过llm属性访问
            self.default_model = global_config.llm.model
            self.temperature = global_config.llm.temperature
            self.max_tokens = global_config.llm.max_tokens
            
            logger.info(f"从config.yaml加载LLM配置: 模型={self.default_model}, 温度={self.temperature}, 最大tokens={self.max_tokens}")
        except Exception as e:
            logger.error(f"加载config.yaml中的模型配置失败: {str(e)}")
            # 使用默认配置作为备选
            self.default_model = self.config.get('default_model', 'gpt-3.5-turbo')
            self.temperature = self.config.get('temperature', 0.7)
            self.max_tokens = self.config.get('max_tokens', 1000)
            logger.info(f"使用默认LLM配置: 模型={self.default_model}, 温度={self.temperature}, 最大tokens={self.max_tokens}")
        
        # 其他配置项
        self.fallback_models = []  # 不再使用备用模型
        self.retry_count = self.config.get('api_retry_count', 3)
        self.retry_delay = self.config.get('api_retry_delay', 2)
        self.timeout = self.config.get('api_timeout', 60)
        
        # API调用统计
        self.api_stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'retry_calls': 0,
            'token_usage': {},
            'model_usage': {},
            'average_latency': {}
        }
    
    async def get_api_response(self, 
                              messages: Union[str, List[Dict[str, str]]], 
                              model: str = None,
                              temperature: float = None,
                              max_tokens: int = None,
                              stream: bool = False,
                              **kwargs) -> Tuple[bool, Dict[str, Any]]:
        """
        向API发送请求并获取响应
        
        Args:
            messages: 消息列表或字符串内容
            model: 模型名称(若未指定，则使用config.yaml中的model)
            temperature: 温度参数(若未指定，则使用config.yaml中的temperature)
            max_tokens: 最大生成的token数(若未指定，则使用config.yaml中的max_tokens)
            stream: 是否使用流式传输
            **kwargs: 其他API参数
            
        Returns:
            Tuple[bool, Dict]: (是否成功, 响应数据)
        """
        # 使用配置中的默认值，或者参数传入的值
        model_name = model or self.default_model
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        # 如果messages是字符串，转换为标准消息格式
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        
        # 构建API请求
        request_data = {
            'model': model_name,
            'messages': messages,
            'temperature': temp,
            'max_tokens': tokens,
            'stream': stream,
            **kwargs
        }
        
        # 记录请求信息
        user_message = messages[-1]['content'] if isinstance(messages, list) and messages else "空消息"
        logger.debug(f"API请求: 模型={model_name}, 温度={temp}, 最大token={tokens}, 内容前50字符: {user_message[:50]}...")
        
        # 开始时间
        start_time = time.time()
        
        # 更新统计信息
        self.api_stats['total_calls'] += 1
        self.api_stats['model_usage'][model_name] = self.api_stats['model_usage'].get(model_name, 0) + 1
        
        # 获取API客户端(使用默认客户端)
        # 从api_clients中获取第一个可用的客户端
        client = None
        if self.api_clients:
            client = next(iter(self.api_clients.values()))
        
        if not client and self.message_manager and hasattr(self.message_manager, 'api_clients'):
            client = next(iter(self.message_manager.api_clients.values()), None)
        
        if not client:
            logger.error(f"找不到可用的API客户端")
            self.api_stats['failed_calls'] += 1
            return False, {"error": "找不到可用的API客户端"}
        
        for attempt in range(self.retry_count):
            try:
                if stream:
                    return await self._handle_stream_response(client, request_data, start_time, model_name)
                else:
                    return await self._handle_normal_response(client, request_data, start_time, model_name)
                    
            except Exception as e:
                # 记录错误并重试
                logger.warning(f"API调用失败 (尝试 {attempt+1}/{self.retry_count}): {str(e)}")
                
                if attempt < self.retry_count - 1:
                    # 更新统计信息
                    self.api_stats['retry_calls'] += 1
                    
                    # 等待一段时间后重试
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    
                    # 不再使用备用模型，因为我们只使用一个客户端
                else:
                    # 所有重试都失败
                    self.api_stats['failed_calls'] += 1
                    duration = time.time() - start_time
                    logger.error(f"API调用最终失败，耗时 {duration:.2f}秒: {str(e)}")
                    return False, {"error": f"API调用失败: {str(e)}"}
        
        # 不应该到达这里，但为了安全起见
        return False, {"error": "API调用过程中发生未知错误"}
    
    async def _handle_normal_response(self, client, request_data, start_time, model):
        """处理普通（非流式）API响应"""
        try:
            # 使用同步方式调用API，并确保正确处理响应
            from openai import OpenAIError
            try:
                response = client.chat.completions.create(**request_data)
                
                # 计算耗时
                duration = time.time() - start_time
                
                # 解析响应
                if hasattr(response, 'choices') and len(response.choices) > 0:
                    # 更新统计信息
                    self.api_stats['successful_calls'] += 1
                    self._update_latency_stats(model, duration)
                    self._update_token_usage(model, response)
                    
                    # 记录成功信息
                    logger.info(f"API调用成功: 模型={model}, 耗时={duration:.2f}秒")
                    
                    # 构建响应数据
                    result = {
                        "success": True,
                        "model": model,
                        "response": response,
                        "content": response.choices[0].message.content,
                        "finish_reason": response.choices[0].finish_reason,
                        "latency": duration
                    }
                    
                    # 如果响应包含token使用信息
                    if hasattr(response, 'usage'):
                        result["usage"] = {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens
                        }
                    
                    return True, result
                else:
                    # API调用可能成功但响应格式不符合预期
                    self.api_stats['failed_calls'] += 1
                    logger.warning(f"API响应格式异常: {response}")
                    return False, {"error": "API响应格式异常", "raw_response": str(response)}
            except OpenAIError as oe:
                logger.error(f"OpenAI API错误: {str(oe)}")
                return False, {"error": f"OpenAI API错误: {str(oe)}"}
        except Exception as e:
            logger.error(f"处理API响应时出错: {str(e)}")
            return False, {"error": f"处理API响应时出错: {str(e)}"}
    
    async def _handle_stream_response(self, client, request_data, start_time, model):
        """处理流式API响应"""
        try:
            # 使用同步方式调用流式API
            from openai import OpenAIError
            try:
                stream_response = client.chat.completions.create(**request_data)
                
                # 收集流式响应数据
                collected_chunks = []
                collected_messages = []
                
                # 处理流式响应
                for chunk in stream_response:
                    collected_chunks.append(chunk)
                    if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                        chunk_message = chunk.choices[0].delta
                        if hasattr(chunk_message, 'content') and chunk_message.content:
                            collected_messages.append(chunk_message.content)
                
                # 计算耗时
                duration = time.time() - start_time
                
                # 合并所有消息内容
                full_message = "".join(collected_messages)
                
                # 更新统计信息
                self.api_stats['successful_calls'] += 1
                self._update_latency_stats(model, duration)
                
                # 记录成功信息
                logger.info(f"流式API调用成功: 模型={model}, 耗时={duration:.2f}秒")
                
                # 返回合并后的结果
                return True, {
                    "success": True,
                    "model": model,
                    "content": full_message,
                    "finish_reason": "stop",  # 假设流式传输正常结束
                    "latency": duration
                }
            except OpenAIError as oe:
                logger.error(f"OpenAI流式API错误: {str(oe)}")
                return False, {"error": f"OpenAI流式API错误: {str(oe)}"}
        except Exception as e:
            logger.error(f"处理流式API响应时出错: {str(e)}")
            return False, {"error": f"处理流式API响应时出错: {str(e)}"}
    
    def get_api_client(self, model_name):
        """获取指定模型的API客户端"""
        # 直接查找匹配的模型
        if model_name in self.api_clients:
            return self.api_clients[model_name]
        
        # 查找模型前缀匹配
        for client_name, client in self.api_clients.items():
            if model_name.startswith(client_name):
                return client
        
        # 未找到匹配的客户端
        return None
    
    def _update_latency_stats(self, model, duration):
        """更新延迟统计信息"""
        if model not in self.api_stats['average_latency']:
            self.api_stats['average_latency'][model] = {
                'total': duration,
                'count': 1,
                'average': duration
            }
        else:
            stats = self.api_stats['average_latency'][model]
            stats['total'] += duration
            stats['count'] += 1
            stats['average'] = stats['total'] / stats['count']
    
    def _update_token_usage(self, model, response):
        """从响应对象更新token使用统计"""
        if hasattr(response, 'usage'):
            usage = response.usage
            if model not in self.api_stats['token_usage']:
                self.api_stats['token_usage'][model] = {
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_tokens': 0
                }
            
            model_stats = self.api_stats['token_usage'][model]
            model_stats['prompt_tokens'] += usage.prompt_tokens
            model_stats['completion_tokens'] += usage.completion_tokens
            model_stats['total_tokens'] += usage.total_tokens
    
    def _update_token_usage_from_dict(self, model, usage_dict):
        """从字典更新token使用统计"""
        if not usage_dict:
            return
            
        if model not in self.api_stats['token_usage']:
            self.api_stats['token_usage'][model] = {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            }
        
        model_stats = self.api_stats['token_usage'][model]
        model_stats['prompt_tokens'] += usage_dict.get('prompt_tokens', 0)
        model_stats['completion_tokens'] += usage_dict.get('completion_tokens', 0)
        model_stats['total_tokens'] += usage_dict.get('total_tokens', 0)
    
    def get_api_stats(self):
        """获取API调用统计信息"""
        return self.api_stats
    
    def reset_api_stats(self):
        """重置API调用统计信息"""
        self.api_stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'retry_calls': 0,
            'token_usage': {},
            'model_usage': {},
            'average_latency': {}
        }
        
        return True

if __name__ == "__main__":
    import asyncio
    import logging
    import json
    import os
    import sys
    
    # 确保能够找到src模块
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # 配置基本日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('test')
    
    # 导入openai
    try:
        from openai import OpenAI
    except ImportError:
        logger.error("未找到OpenAI库，请安装: pip install openai")
        sys.exit(1)
    
    async def test_api_with_config():
        """使用配置文件中的LLM配置测试API调用"""
        print("开始测试API处理器(使用配置文件中的LLM配置)...")
        
        try:
            # 导入真实配置
            from src.config import config as global_config
            
            # 显示LLM配置信息
            print(f"\n配置文件中的LLM配置:")
            print(f"模型: {global_config.llm.model}")
            print(f"温度: {global_config.llm.temperature}")
            print(f"最大tokens: {global_config.llm.max_tokens}")
            print(f"API基础URL: {global_config.llm.base_url}")
            
            # 创建OpenAI客户端
            client = OpenAI(
                api_key=global_config.llm.api_key,
                base_url=global_config.llm.base_url
            )
            
            # 创建API处理器的测试实例
            class TestMessageManager:
                def __init__(self, client):
                    self.api_clients = {'default': client}
                
                def get_module(self, name):
                    return None
            
            # 初始化APIHandler
            message_manager = TestMessageManager(client)
            handler = APIHandler(message_manager)
            
            # 测试API调用
            print("\n测试API调用...")
            test_message = "你好，这是一条使用真实配置的测试消息。请生成一条简短的聊天发起语"
            print(f"发送消息: {test_message}")
            
            success, response = await handler.get_api_response(test_message)
            
            if success:
                print(f"\nAPI调用成功！")
                print(f"使用模型: {response.get('model', '未知')}")
                print(f"响应内容: {response.get('content', '无内容')}")
                if "usage" in response:
                    print(f"Token使用情况: {response['usage']}")
                print(f"响应时间: {response.get('latency', 0):.2f}秒")
            else:
                print(f"\nAPI调用失败!")
                print(f"错误信息: {response.get('error', '未知错误')}")
            
            print("\nAPI测试完成")
            
        except ImportError as e:
            logger.error(f"导入配置文件失败: {str(e)}")
        except Exception as e:
            logger.error(f"测试API时出错: {str(e)}")
    
    # 运行测试
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_api_with_config())
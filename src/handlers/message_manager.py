"""
消息管理器模块
作为整个系统的核心控制器，协调各模块工作
"""

import logging
import asyncio
import time
import json
import os
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

from src.api_client.wrapper import APIWrapper

# 获取logger
logger = logging.getLogger('main')

class MessageManager:
    """
    消息管理器类
    作为整个系统的核心控制器，协调各模块的工作
    """
    
    def __init__(self, config=None):
        """
        初始化消息管理器
        
        Args:
            config: 配置信息字典
        """
        self.config = config or {}
        self.modules = {}  # 存储各个模块的实例
        self.running = False
        self.is_initialized = False
        self.message_queue = asyncio.Queue()
        self.message_handlers = {}  # 消息处理器映射表
        self.event_handlers = {}    # 事件处理器
        
        # 统计信息
        self.stats = {
            'messages_processed': 0,
            'errors_encountered': 0,
            'start_time': time.time(),
            'message_types': {}
        }
        
        # 为兼容性保留wx属性，将由main.py设置
        self.wx = None
    
    async def initialize(self):
        """初始化消息管理器和各个模块"""
        if self.is_initialized:
            logger.warning("消息管理器已经初始化，跳过重复初始化")
            return True
            
        try:
            logger.info("开始初始化消息管理器...")
            
            # 导入必要的模块
            from src.handlers.messages.base_handler import BaseHandler
            from src.handlers.messages.preprocessing import MessagePreprocessor
            from src.handlers.messages.postprocessing import MessagePostprocessor
            from src.handlers.messages.queue_manager import QueueManager
            from src.handlers.memory_manager import MemoryManager
            from src.handlers.messages.private_handler import PrivateMessageHandler
            from src.handlers.messages.group_handler import GroupMessageHandler
            from src.handlers.rag import RAGManager
            from src.handlers.messages.api_handler import APIHandler
            from src.handlers.image import ImageHandler
            from src.handlers.voice import VoiceHandler
            from src.handlers.emoji import EmojiHandler
            from src.handlers.messages.message_processor import MessageProcessor
            
            # 创建各个模块实例
            self.modules['preprocessor'] = MessagePreprocessor(self)
            self.modules['postprocessor'] = MessagePostprocessor(self)
            self.modules['queue_manager'] = QueueManager(self)
            
            # 创建RAG管理器
            self.modules['rag_manager'] = RAGManager(self)
            
            # 创建内存管理器 - 使用正确的参数
            memory_config = self.config.get('memory', {})
            self.modules['memory_manager'] = MemoryManager(
                message_manager=self, 
                memory_handler=None,  # memory_handler稍后将从init_memory获取
                rag_manager=self.modules['rag_manager']
            )
            
            # 创建其他处理器
            try:
                self.modules['private_handler'] = PrivateMessageHandler(self)
                logger.info("成功创建私聊处理器")
            except Exception as e:
                logger.error(f"创建私聊处理器失败: {str(e)}")
                self.modules['private_handler'] = None
                
            try:
                self.modules['group_handler'] = GroupMessageHandler(self)
                logger.info("成功创建群聊处理器")
            except Exception as e:
                logger.error(f"创建群聊处理器失败: {str(e)}")
                self.modules['group_handler'] = None
            
            # 创建图像处理器
            self.modules['image_handler'] = ImageHandler(self, self.config.get('image', {}))
            
            # 创建语音处理器
            self.modules['voice_handler'] = VoiceHandler(self, self.config.get('voice', {}))
            
            # 创建表情处理器
            self.modules['emoji_handler'] = EmojiHandler(
                root_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')), 
                config=self.config.get('emoji', {})
            )
            
            # 创建消息处理器
            self.modules['message_processor'] = MessageProcessor(self, self.config)
            
            # 创建API处理器
            api_config = self.config.get('api', {})
            api_clients = self._initialize_api_clients(api_config)
            self.modules['api_handler'] = APIHandler(self, api_config, api_clients)
            
            # 注册消息处理器
            self._register_message_handlers()
            
            # 注册事件处理器
            self._register_event_handlers()
            
            # 标记为已初始化
            self.is_initialized = True
            logger.info("消息管理器初始化完成")
            
            # 初始化内存处理器并更新memory_manager的引用
            try:
                from src.handlers.memory_manager import init_memory
                from src.config import config
                
                # 创建API包装器
                api_wrapper = APIWrapper(
                    api_key=config.llm.api_key,
                    base_url=config.llm.base_url
                )
                
                # 获取项目根目录
                root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
                
                # 初始化内存系统
                memory_processor = init_memory(root_dir, api_wrapper)
                
                # 更新memory_manager的内存处理器引用
                if memory_processor and 'memory_manager' in self.modules:
                    self.modules['memory_manager'].memory_handler = memory_processor
                    logger.info("已将内存处理器连接到内存管理器")
            except Exception as e:
                logger.error(f"初始化内存处理器失败: {str(e)}")
            
            return True
            
        except Exception as e:
            logger.error(f"初始化消息管理器失败: {str(e)}")
            return False
    
    def _initialize_api_clients(self, api_config):
        """初始化API客户端"""
        api_clients = {}
        try:
            # 从配置文件获取LLM配置
            from src.config import config
            
            # 获取API密钥和基础URL
            api_key = config.llm.api_key
            base_url = config.llm.base_url
            model = config.llm.model
            
            logger.info(f"从config.yaml加载LLM配置: 模型={model}, 基础URL={base_url}")
            
            # 初始化OpenAI客户端
            try:
                import openai
                client = openai.OpenAI(api_key=api_key, base_url=base_url)
                api_clients['default'] = client
                logger.info("API客户端初始化成功")
                
                # 添加模型名称作为键，指向同一个客户端
                api_clients[model] = client
                logger.info(f"已为模型 {model} 配置API客户端")
            except Exception as e:
                logger.error(f"初始化API客户端失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"初始化API客户端失败: {str(e)}")
        
        return api_clients
    
    def _register_message_handlers(self):
        """注册消息处理器"""
        # 初始化消息处理器字典
        self.message_handlers = {}
        
        # 检查并注册私聊处理器
        if 'private_handler' in self.modules and self.modules['private_handler'] is not None:
            self.message_handlers['private'] = self.modules['private_handler'].handle_message
            logger.info("已注册私聊处理器")
        else:
            logger.warning("找不到私聊处理器，跳过注册")
            
        # 检查并注册群聊处理器
        if 'group_handler' in self.modules and self.modules['group_handler'] is not None:
            self.message_handlers['group'] = self.modules['group_handler'].handle_message
            logger.info("已注册群聊处理器")
        else:
            logger.warning("找不到群聊处理器，跳过注册")
            
        # 可以添加更多消息类型的处理器
    
    def _register_event_handlers(self):
        """注册事件处理器"""
        # 这里可以注册各种事件的处理函数
        self.event_handlers = {
            'message_received': [],
            'message_processed': [],
            'error_occurred': [],
            'system_started': [],
            'system_stopped': []
        }
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """
        注册事件处理器
        
        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
        logger.debug(f"注册事件处理器: {event_type}")
    
    async def trigger_event(self, event_type: str, data: Any = None):
        """
        触发事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        if event_type not in self.event_handlers:
            return
            
        for handler in self.event_handlers[event_type]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"执行事件处理器时出错 ({event_type}): {str(e)}")
    
    async def start(self):
        """启动消息管理器"""
        if not self.is_initialized:
            success = await self.initialize()
            if not success:
                logger.error("由于初始化失败，无法启动消息管理器")
                return False
        
        if self.running:
            logger.warning("消息管理器已经在运行中")
            return True
            
        self.running = True
        logger.info("消息管理器启动成功")
        
        # 触发系统启动事件
        await self.trigger_event('system_started')
        
        # 启动消息处理循环
        asyncio.create_task(self._message_processing_loop())
        
        return True
    
    async def stop(self):
        """停止消息管理器"""
        if not self.running:
            logger.warning("消息管理器未在运行")
            return True
            
        self.running = False
        logger.info("消息管理器已停止")
        
        # 触发系统停止事件
        await self.trigger_event('system_stopped')
        
        return True
    
    async def process_message(self, message_data: Dict[str, Any]):
        """
        处理接收到的消息
        
        Args:
            message_data: 消息数据，包含消息类型和内容
        """
        # 触发消息接收事件
        await self.trigger_event('message_received', message_data)
        
        # 更新统计信息
        self.stats['messages_processed'] += 1
        message_type = message_data.get('message_type', 'unknown')
        self.stats['message_types'][message_type] = self.stats['message_types'].get(message_type, 0) + 1
        
        # 将消息放入队列
        await self.message_queue.put(message_data)
        logger.debug(f"消息已加入队列: {message_type}")
    
    async def _message_processing_loop(self):
        """消息处理循环"""
        logger.info("消息处理循环已启动")
        
        while self.running:
            try:
                # 从队列获取消息
                message_data = await self.message_queue.get()
                
                # 处理消息
                await self._process_single_message(message_data)
                
                # 标记任务完成
                self.message_queue.task_done()
                
            except asyncio.CancelledError:
                logger.info("消息处理循环被取消")
                break
            except Exception as e:
                logger.error(f"消息处理循环中发生错误: {str(e)}")
                self.stats['errors_encountered'] += 1
                
                # 触发错误事件
                await self.trigger_event('error_occurred', {
                    'error': str(e),
                    'stage': 'message_processing_loop'
                })
                
                # 短暂暂停避免死循环
                await asyncio.sleep(1)
    
    async def _process_single_message(self, message_data: Dict[str, Any]):
        """
        处理单条消息
        
        Args:
            message_data: 消息数据
        """
        message_type = message_data.get('message_type', 'unknown')
        message_id = message_data.get('message_id', 'unknown')
        
        logger.debug(f"处理消息: {message_type} (ID: {message_id})")
        
        try:
            # 预处理消息
            preprocessed_data = await self.modules['preprocessor'].preprocess_message(message_data)
            
            # 根据消息类型调用对应的处理器
            if message_type in self.message_handlers:
                handler = self.message_handlers[message_type]
                response = await handler(preprocessed_data)
                
                # 处理处理器返回的字典格式
                if isinstance(response, dict) and 'success' in response:
                    if not response['success']:
                        logger.warning(f"消息处理失败: {response.get('error', '未知错误')}")
                        # 如果处理失败，使用错误消息作为返回值
                        if 'error' in response:
                            response = f"错误: {response['error']}"
                        else:
                            response = "处理消息时发生未知错误"
                    else:
                        # 处理成功，使用result作为返回值
                        response = response.get('result', None)
            else:
                logger.warning(f"未找到消息类型的处理器: {message_type}")
                response = f"未支持的消息类型: {message_type}"
            
            # 后处理响应
            final_response = await self.modules['postprocessor'].process_response(
                response, message_data
            )
            
            # 触发消息处理完成事件
            await self.trigger_event('message_processed', {
                'original_message': message_data,
                'processed_response': final_response
            })
            
            return final_response
            
        except Exception as e:
            logger.error(f"处理消息时出错 (ID: {message_id}): {str(e)}")
            self.stats['errors_encountered'] += 1
            
            # 触发错误事件
            await self.trigger_event('error_occurred', {
                'error': str(e),
                'stage': 'process_single_message',
                'message_id': message_id
            })
            
            return f"处理消息时出错: {str(e)}"
    
    def get_module(self, module_name: str):
        """
        获取指定名称的模块实例
        
        Args:
            module_name: 模块名称
            
        Returns:
            模块实例或None
        """
        return self.modules.get(module_name)
    
    def get_stats(self):
        """获取统计信息"""
        # 计算运行时间
        uptime = time.time() - self.stats['start_time']
        
        # 收集所有模块的统计信息
        module_stats = {}
        for name, module in self.modules.items():
            if hasattr(module, 'get_stats'):
                module_stats[name] = module.get_stats()
        
        # 构建完整统计信息
        full_stats = {
            **self.stats,
            'uptime': uptime,
            'uptime_formatted': self._format_uptime(uptime),
            'queue_size': self.message_queue.qsize(),
            'modules': module_stats
        }
        
        return full_stats
    
    def _format_uptime(self, seconds: float) -> str:
        """格式化运行时间"""
        days, remainder = divmod(int(seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}天")
        if hours > 0 or days > 0:
            parts.append(f"{hours}小时")
        if minutes > 0 or hours > 0 or days > 0:
            parts.append(f"{minutes}分")
        parts.append(f"{seconds}秒")
        
        return "".join(parts)
    
    async def get_api_response(self, content, username=None):
        """
        代理到API处理器的get_api_response方法，获取API响应
        
        Args:
            content: 消息内容
            username: 用户名（不再用作模型名）
            
        Returns:
            Tuple[bool, Any]: (是否成功, 响应数据或错误信息)
        """
        api_handler = self.get_module('api_handler')
        if not api_handler:
            logger.error("API处理器未初始化")
            return False, {"error": "API处理器未初始化"}
            
        try:
            # 直接使用内容调用API，不将用户名用作模型
            result = await api_handler.get_api_response(content)
            
            if result and isinstance(result, tuple) and len(result) == 2:
                success, response = result
                if success and 'content' in response:
                    return success, response['content']
                return success, response
            return False, {"error": "API响应格式异常"}
            
        except Exception as e:
            logger.error(f"调用API时发生错误: {str(e)}")
            return False, {"error": f"API调用失败: {str(e)}"}
    
    async def process_private_message(self, content, chat_id, sender_name, username, is_image_recognition=False):
        """
        处理私聊消息
        
        Args:
            content: 消息内容
            chat_id: 聊天ID
            sender_name: 发送者名称
            username: 用户名
            is_image_recognition: 是否是图像识别结果
            
        Returns:
            处理结果
        """
        logger.info(f"处理私聊消息 - 聊天ID: {chat_id}, 发送者: {sender_name}, 内容: {content[:30]}...")
        
        try:
            # 获取私聊处理器
            private_handler = self.get_module('private_handler')
            if not private_handler:
                error_msg = "找不到私聊处理器"
                logger.error(error_msg)
                
                # 尝试重新初始化私聊处理器
                try:
                    from src.handlers.messages.private_handler import PrivateMessageHandler
                    self.modules['private_handler'] = PrivateMessageHandler(self)
                    private_handler = self.modules['private_handler']
                    logger.info("成功重新创建私聊处理器")
                    
                    # 更新消息处理器映射
                    if 'private' not in self.message_handlers and private_handler is not None:
                        self.message_handlers['private'] = private_handler.handle_message
                        logger.info("已重新注册私聊处理器")
                except Exception as e:
                    logger.error(f"重新创建私聊处理器失败: {str(e)}")
                    return {"success": False, "error": error_msg}
            
            if not private_handler:
                return {"success": False, "error": "无法创建私聊处理器"}
                
            # 处理私聊消息
            result = await private_handler.handle_message(
                content=content,
                chat_id=chat_id,
                sender_name=sender_name,
                username=username,
                is_image_recognition=is_image_recognition
            )
            
            return {"success": True, "result": result}
            
        except Exception as e:
            error_msg = f"处理私聊消息时发生错误: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    # 以下是为了兼容旧代码的方法
    
    async def handle_text_message(self, content: str, chat_id: str, sender_name: str, 
                                 username: str, is_group: bool, **kwargs):
        """
        处理文本消息
        
        Args:
            content: 消息内容
            chat_id: 聊天ID
            sender_name: 发送者名称
            username: 用户名
            is_group: 是否是群聊
            **kwargs: 额外参数
            
        Returns:
            处理结果
        """
        logger.info(f"处理文本消息 - 聊天ID: {chat_id}, 发送者: {sender_name}, 内容: {content[:30]}...")
        
        try:
            # 根据是否是群聊选择不同的处理器
            if is_group:
                group_handler = self.get_module('group_handler')
                if not group_handler:
                    logger.error("找不到群聊处理器")
                    return None
                    
                return await group_handler.handle_message(
                    content=content,
                    group_id=chat_id,
                    sender_name=sender_name,
                    username=username,
                    **kwargs
                )
            else:
                private_handler = self.get_module('private_handler')
                if not private_handler:
                    logger.error("找不到私聊处理器")
                    return None
                    
                return await private_handler.handle_message(
                    content=content,
                    chat_id=chat_id,
                    sender_name=sender_name,
                    username=username,
                    **kwargs
                )
        except Exception as e:
            logger.error(f"处理文本消息时发生异常: {str(e)}")
            return None
    
    async def handle_image_message(self, image_path: str, chat_id: str, sender_name: str, 
                                  username: str, is_group: bool, **kwargs):
        """
        处理图片消息
        
        Args:
            image_path: 图片路径
            chat_id: 聊天ID
            sender_name: 发送者名称
            username: 用户名
            is_group: 是否是群聊
            **kwargs: 额外参数
            
        Returns:
            处理结果
        """
        logger.info(f"处理图片消息 - 聊天ID: {chat_id}, 发送者: {sender_name}, 图片: {image_path}")
        
        try:
            # 获取图像处理器
            image_handler = self.get_module('image_handler')
            if not image_handler:
                logger.error("找不到图像处理器")
                return None
                
            # 使用图像处理器处理图片
            is_processed = False
            
            # 检查是否支持回调方式处理
            if hasattr(image_handler, 'process_image') and callable(image_handler.process_image):
                # 定义回调函数，用于处理识别结果
                async def callback(recognition_result):
                    if not recognition_result:
                        return
                        
                    logger.info(f"图片识别结果: {recognition_result[:100]}...")
                    
                    # 根据是否是群聊选择不同的处理器
                    if is_group:
                        group_handler = self.get_module('group_handler')
                        if group_handler:
                            await group_handler.handle_message(
                                content=recognition_result,
                                group_id=chat_id,
                                sender_name=sender_name,
                                username=username,
                                is_image_recognition=True,
                                **kwargs
                            )
                    else:
                        private_handler = self.get_module('private_handler')
                        if private_handler:
                            await private_handler.handle_message(
                                content=recognition_result,
                                chat_id=chat_id,
                                sender_name=sender_name,
                                username=username,
                                is_image_recognition=True,
                                **kwargs
                            )
                
                # 处理图片
                is_processed = image_handler.process_image(image_path, callback)
            
            return is_processed
        
        except Exception as e:
            logger.error(f"处理图片消息时发生异常: {str(e)}")
            return None
    
    async def handle_voice_message(self, voice_path: str, chat_id: str, sender_name: str, 
                                  username: str, is_group: bool, **kwargs):
        """
        处理语音消息
        
        Args:
            voice_path: 语音文件路径
            chat_id: 聊天ID
            sender_name: 发送者名称
            username: 用户名
            is_group: 是否是群聊
            **kwargs: 额外参数
            
        Returns:
            处理结果
        """
        logger.info(f"处理语音消息 - 聊天ID: {chat_id}, 发送者: {sender_name}, 语音: {voice_path}")
        
        try:
            # 获取语音处理器
            voice_handler = self.get_module('voice_handler')
            if not voice_handler:
                logger.error("找不到语音处理器")
                return None
                
            # 识别语音内容
            recognized_text = await voice_handler.recognize_voice(voice_path)
            if not recognized_text:
                logger.warning(f"语音识别失败: {voice_path}")
                return None
                
            logger.info(f"语音识别结果: {recognized_text[:100]}...")
            
            # 根据是否是群聊选择不同的处理器
            if is_group:
                group_handler = self.get_module('group_handler')
                if not group_handler:
                    logger.error("找不到群聊处理器")
                    return None
                    
                return await group_handler.handle_message(
                    content=recognized_text,
                    group_id=chat_id,
                    sender_name=sender_name,
                    username=username,
                    is_voice_recognition=True,
                    **kwargs
                )
            else:
                private_handler = self.get_module('private_handler')
                if not private_handler:
                    logger.error("找不到私聊处理器")
                    return None
                    
                return await private_handler.handle_message(
                    content=recognized_text,
                    chat_id=chat_id,
                    sender_name=sender_name,
                    username=username,
                    is_voice_recognition=True,
                    **kwargs
                )
        
        except Exception as e:
            logger.error(f"处理语音消息时发生异常: {str(e)}")
            return None
    
    async def handle_at_message(self, content: str, group_id: str, sender_name: str, 
                               username: str, timestamp: str, **kwargs):
        """
        处理@消息
        
        Args:
            content: 消息内容
            group_id: 群ID
            sender_name: 发送者名称
            username: 用户名
            timestamp: 时间戳
            **kwargs: 额外参数
            
        Returns:
            处理结果
        """
        logger.info(f"处理@消息 - 群ID: {group_id}, 发送者: {sender_name}, 内容: {content[:30]}...")
        
        try:
            # 获取群聊处理器
            group_handler = self.get_module('group_handler')
            if not group_handler:
                logger.error("找不到群聊处理器")
                return None
                
            # 处理@消息
            return await group_handler.handle_at_message(
                content=content,
                group_id=group_id,
                sender_name=sender_name,
                username=username,
                timestamp=timestamp,
                **kwargs
            )
        
        except Exception as e:
            logger.error(f"处理@消息时发生异常: {str(e)}")
            return None
            
    def process_cached_user_messages(self, username, messages):
        """
        处理缓存的用户消息
        
        Args:
            username: 用户ID
            messages: 消息列表
            
        Returns:
            处理结果
        """
        try:
            if not messages:
                logger.warning(f"没有要处理的缓存消息: {username}")
                return None
                
            # 获取私聊处理器
            private_handler = self.get_module('private_handler')
            if not private_handler:
                logger.error("找不到私聊处理器")
                return None
                
            # 使用异步转同步的方式处理消息
            try:
                import asyncio
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            if loop.is_running():
                # 如果事件循环已经在运行，使用run_coroutine_threadsafe
                future = asyncio.run_coroutine_threadsafe(
                    private_handler.process_cached_messages(username, messages), 
                    loop
                )
                response = future.result()
            else:
                # 否则使用run_until_complete
                response = loop.run_until_complete(
                    private_handler.process_cached_messages(username, messages)
                )
                
            logger.info(f"缓存消息处理完成: {username}, 回复: {response[:50] if response else 'None'}...")
            return response
            
        except Exception as e:
            logger.error(f"处理缓存用户消息失败: {str(e)}")
            return None
    
    def process_group_at_message(self, message_data):
        """
        处理群聊@消息
        
        Args:
            message_data: 消息数据
            
        Returns:
            处理结果
        """
        try:
            if not message_data:
                logger.warning("没有要处理的群聊@消息")
                return None
                
            # 提取消息信息
            group_id = message_data.get('group_id')
            sender_name = message_data.get('sender_name')
            username = message_data.get('username')
            content = message_data.get('content')
            
            if not group_id or not content:
                logger.warning("群聊@消息缺少关键信息")
                return None
                
            # 获取群聊处理器
            group_handler = self.get_module('group_handler')
            if not group_handler:
                logger.error("找不到群聊处理器")
                return None
                
            # 使用异步转同步的方式处理消息
            try:
                import asyncio
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            if loop.is_running():
                # 如果事件循环已经在运行，使用run_coroutine_threadsafe
                future = asyncio.run_coroutine_threadsafe(
                    group_handler.handle_at_message(
                        content=content,
                        group_id=group_id,
                        sender_name=sender_name,
                        username=username,
                        timestamp=None
                    ),
                    loop
                )
                response = future.result()
            else:
                # 否则使用run_until_complete
                response = loop.run_until_complete(
                    group_handler.handle_at_message(
                        content=content,
                        group_id=group_id,
                        sender_name=sender_name,
                        username=username,
                        timestamp=None
                    )
                )
                
            logger.info(f"群聊@消息处理完成: {group_id}, 回复: {response[:50] if response else 'None'}...")
            return response
            
        except Exception as e:
            logger.error(f"处理群聊@消息失败: {str(e)}")
            return None
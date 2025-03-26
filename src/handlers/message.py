"""
消息处理器入口点
调用message_manager进行实际处理
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime

from src.handlers.message_manager import MessageManager

# 获取logger
logger = logging.getLogger('main')

class MessageHandler:
    """
    消息处理器类
    作为系统入口点，调用MessageManager进行实际处理
    """
    
    def __init__(self, root_dir, llm, robot_name, prompt_content, image_handler,
                 emoji_handler, voice_handler, memory_handler, config=None, is_debug=False):

        """
        初始化消息处理器
        
        Args:
            root_dir: 根目录路径
            llm: 语言模型实例
            robot_name: 机器人名称
            prompt_content: 提示内容
            image_handler: 图片处理器
            emoji_handler: 表情处理器
            voice_handler: 语音处理器
            memory_handler: 记忆处理器
            config: 配置信息字典(可选)
            is_debug: 是否调试模式(可选)
        """
        self.root_dir = root_dir
        self.config = config or {}
        self.message_manager = MessageManager(self.config)
        self._initialized = False
        # 为兼容性保留wx属性，将由main.py设置
        self.wx = None
        self.is_debug = is_debug
    
    async def initialize(self):
        """初始化消息处理器"""
        if self._initialized:
            logger.info("消息处理器已经初始化")
            return True
            
        logger.info("开始初始化消息处理器...")
        
        # 初始化消息管理器
        result = await self.message_manager.initialize()
        if not result:
            logger.error("初始化消息管理器失败")
            return False
        
        self._initialized = True
        logger.info("消息处理器初始化完成")
        return True
    
    async def start(self):
        """启动消息处理器"""
        if not self._initialized:
            result = await self.initialize()
            if not result:
                logger.error("由于初始化失败，无法启动消息处理器")
                return False
        
        # 启动消息管理器
        result = await self.message_manager.start()
        if not result:
            logger.error("启动消息管理器失败")
            return False
            
        logger.info("消息处理器启动成功")
        return True
    
    async def stop(self):
        """停止消息处理器"""
        result = await self.message_manager.stop()
        if not result:
            logger.error("停止消息管理器失败")
            return False
            
        logger.info("消息处理器已停止")
        return True
    
    async def handle_message(self, message_data: Dict[str, Any]):
        """
        处理接收到的消息
        
        Args:
            message_data: 消息数据，包含消息类型和内容
            
        Returns:
            Dict: 处理结果
        """
        if not self._initialized:
            logger.warning("消息处理器未初始化，尝试进行初始化")
            result = await self.initialize()
            if not result:
                logger.error("初始化失败，无法处理消息")
                return {
                    'success': False,
                    'error': "消息处理器初始化失败"
                }
        
        # 调用消息管理器处理消息
        return await self.message_manager.process_message(message_data)
    
    async def get_api_response(self, *args, **kwargs):
        """
        获取API响应
        
        Args:
            *args: 传递给API处理器的位置参数
            **kwargs: 传递给API处理器的关键字参数
            
        Returns:
            Tuple[bool, Dict]: (是否成功, 响应数据)
        """
        if not self._initialized:
            logger.warning("消息处理器未初始化，尝试进行初始化")
            result = await self.initialize()
            if not result:
                logger.error("初始化失败，无法获取API响应")
                return False, {"error": "消息处理器初始化失败"}
        
        # 调用消息管理器获取API响应
        return await self.message_manager.get_api_response(*args, **kwargs)
    
    def get_stats(self):
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息字典
        """
        return self.message_manager.get_stats()
    
    # 以下为辅助方法，用于异步操作和获取模块
    
    def _run_async(self, coroutine):
        """
        运行异步协程并返回结果
        
        Args:
            coroutine: 要运行的协程
            
        Returns:
            协程的运行结果
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            # 如果事件循环已经在运行，使用run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(coroutine, loop)
            return future.result()
        else:
            # 否则使用run_until_complete
            return loop.run_until_complete(coroutine)
    
    # 获取模块实例的方法
    
    def get_module(self, module_name: str):
        """
        获取指定名称的模块实例
        
        Args:
            module_name: 模块名称
            
        Returns:
            模块实例或None
        """
        return self.message_manager.get_module(module_name)
    
    @property
    def voice_handler(self):
        """获取语音处理器"""
        return self.message_manager.get_module('voice_handler')
    
    @property
    def image_handler(self):
        """获取图像处理器"""
        return self.message_manager.get_module('image_handler')
    
    @property
    def emoji_handler(self):
        """获取表情处理器"""
        return self.message_manager.get_module('emoji_handler')
    
    @property
    def memory_handler(self):
        """获取内存处理器"""
        return self.message_manager.get_module('memory_manager')
    
    # 简化的消息处理方法，用于与旧API兼容
    
    def handle_user_message(self, content, chat_id, sender_name, username, is_group=False, is_image_recognition=False, is_at=False):
        """
        处理用户消息（兼容旧API）
        
        Args:
            content: 消息内容
            chat_id: 聊天ID
            sender_name: 发送者名称
            username: 用户名
            is_group: 是否是群聊
            is_image_recognition: 是否是图像识别
            is_at: 是否是@消息
        
        Returns:
            处理结果
        """
        if is_group and is_at:
            # 处理群聊@消息
            return self._run_async(self.message_manager.handle_at_message(
                content=content, group_id=chat_id, sender_name=sender_name, 
                username=username, timestamp=None
            ))
        else:
            # 处理文本消息
            return self._run_async(self.message_manager.handle_text_message(
                content=content, chat_id=chat_id, sender_name=sender_name,
                username=username, is_group=is_group, is_image_recognition=is_image_recognition
            ))

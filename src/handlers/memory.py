"""
兼容层 - 旧接口的适配器
提供与原始内存系统兼容的API，适配新的模块化内存系统
"""
import os
import logging
import asyncio
import functools
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from datetime import datetime

# 导入新的记忆模块
from src.handlers.handler_init import (
    setup_memory, remember, retrieve, is_important, 
    get_memory_handler, get_memory_stats, 
    clear_memories, save_memories, init_rag_from_config,
    setup_rag, get_rag
)
from src.api_client.wrapper import APIWrapper

# 设置日志
logger = logging.getLogger('main')

# 显示弃用警告
logger.warning("src.handlers.memory模块已弃用，请使用src.handlers.memory_manager模块")

# 全局变量
_initialized = False
_memory_handler = None

# 在文件开头添加这三个类的定义，以确保它们在被引用前已定义
# SimpleEmbeddingModel类定义
class SimpleEmbeddingModel:
    """简单的嵌入模型模拟类，提供get_cache_stats方法"""
    def __init__(self):
        self._cache_hits = 0
        self._cache_misses = 0
        logging.getLogger('main').info("创建简单嵌入模型模拟类")
    
    def get_cache_stats(self):
        """获取缓存统计信息"""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total) * 100 if total > 0 else 0
        return {
            'cache_size': 0,
            'hit_rate_percent': hit_rate
        }

# SimpleRag类定义
class SimpleRag:
    """简单的RAG模拟类，提供基本的embedding_model属性"""
    def __init__(self):
        # 创建一个简单的模拟嵌入模型
        self.embedding_model = SimpleEmbeddingModel()
        logging.getLogger('main').info("创建简单RAG模拟类")

# FakeShortTermMemory类定义
class FakeShortTermMemory:
    """
    提供与short_term_memory兼容的接口的假类
    """
    def __init__(self, memory_handler):
        self.memory_handler = memory_handler
        self.rag = SimpleRag()  # 一个简单的RAG模拟
        logging.getLogger('main').info("创建假短期记忆类以兼容旧接口")
    
    def add_memory(self, user_id=None, memory_key=None, memory_value=None):
        """
        添加记忆
        
        Args:
            user_id: 用户ID
            memory_key: 记忆键
            memory_value: 记忆值
            
        Returns:
            bool: 是否成功添加
        """
        try:
            # 使用memory_handler的remember方法添加记忆
            logging.getLogger('main').info(f"通过假短期记忆类添加记忆 - 用户: {user_id}, 记忆键长度: {len(memory_key) if memory_key else 0}")
            return self.memory_handler.remember(memory_key, memory_value)
        except Exception as e:
            logging.getLogger('main').error(f"通过假短期记忆类添加记忆失败: {str(e)}")
            return False

def _run_async(coro):
    """
    运行异步函数并返回结果
    
    Args:
        coro: 异步协程对象
        
    Returns:
        协程运行结果
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # 如果没有事件循环，创建一个新的
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        # 使用future来异步运行协程
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()
    else:
        # 直接运行协程
        return loop.run_until_complete(coro)

# 将对init_memory的调用转发到记忆管理器模块
def init_memory(root_dir, api_wrapper=None):
    """
    初始化记忆系统 - 转发到记忆管理器模块
    
    Args:
        root_dir: 根目录路径
        api_wrapper: API调用封装器，可选
        
    Returns:
        memory_handler: 记忆处理器
    """
    from src.handlers.memory_manager import init_memory as init_memory_manager
    return init_memory_manager(root_dir, api_wrapper)

# 下面是兼容性类，仅用于保持旧代码能够正常运行
class MemoryHandler:
    """兼容性类，转发调用到记忆管理器模块"""
    
    def __init__(self, root_dir=None, api_key=None, base_url=None, model=None, **kwargs):
        """
        初始化记忆处理器
        
        Args:
            root_dir: 根目录路径，可选
            api_key: API密钥，可选
            base_url: API基础URL，可选
            model: 模型名称，可选
            **kwargs: 其他参数
        """
        self.root_dir = root_dir
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model
        self.initialized = False
        self.api_wrapper = None
        
        if api_key and base_url:
            self.api_wrapper = APIWrapper(api_key=api_key, base_url=base_url)
        
        # 初始化时转发到记忆管理器模块
        self._initialize()
    
    def _initialize(self):
        """初始化记忆处理器"""
        try:
            from src.handlers.memory_manager import init_memory as init_memory_manager
            # 直接转发调用
            self._memory_processor = init_memory_manager(self.root_dir, self.api_wrapper)
            self.initialized = True
        except Exception as e:
            logger.error(f"初始化记忆处理器失败: {str(e)}")
            self._memory_processor = None
    
    # 以下方法都是转发调用到真实的记忆管理器
    
    def remember(self, user_message, assistant_response, user_id=None):
        """转发调用到remember函数"""
        from src.handlers.memory_manager import remember
        return remember(user_message, assistant_response, user_id)
    
    def retrieve(self, query, top_k=5):
        """转发调用到retrieve函数"""
        from src.handlers.memory_manager import retrieve
        return retrieve(query, top_k)
    
    def is_important(self, text):
        """转发调用到is_important函数"""
        from src.handlers.memory_manager import is_important
        return is_important(text)
    
    # 其他方法也都是转发调用
    
    def get_memory_stats(self):
        """获取记忆统计信息"""
        from src.handlers.memory_manager import get_memory_stats
        return get_memory_stats()
    
    def get_relevant_memories(self, query, username=None, top_k=5):
        """获取相关记忆"""
        from src.handlers.memory_manager import get_relevant_memories
        return get_relevant_memories(query, username, top_k)
    
    def clear_memories(self):
        """清空记忆"""
        from src.handlers.memory_manager import clear_memories
        return clear_memories()
    
    def save(self):
        """保存记忆"""
        from src.handlers.memory_manager import save_memories
        return save_memories()
    
    # 为兼容性提供一个short_term_memory属性
    @property
    def short_term_memory(self):
        """为兼容性提供的短期记忆属性"""
        return FakeShortTermMemory(self)
        
    # 兼容旧版API的别名方法
    clear = clear_memories
    add_memory = remember

# 导出模块中所有重要内容
__all__ = [
    'init_memory', 'MemoryHandler',
    'remember', 'retrieve', 'is_important',
    'get_memory_handler', 'get_memory_stats',
    'clear_memories', 'save_memories',
    'init_rag_from_config', 'setup_rag', 'get_rag'
] 
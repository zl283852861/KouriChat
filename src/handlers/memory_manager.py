"""
记忆管理器 - 顶层接口
负责与主程序交互，管理记忆的初始化、调用等
"""
import os
import logging
import asyncio
import math
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

# 导入中层记忆处理器
from src.handlers.memories.memory_processor import MemoryProcessor
from src.api_client.wrapper import APIWrapper
from src.handlers.messages.base_handler import BaseHandler

# 设置日志
logger = logging.getLogger('main')

# 全局变量
_initialized = False
_memory_processor = None

class MemoryManager(BaseHandler):
    """记忆管理器，负责对话记忆的存储和检索"""
    
    def __init__(self, message_manager=None, memory_handler=None, rag_manager=None):
        """
        初始化记忆管理器
        
        Args:
            message_manager: 消息管理器实例的引用
            memory_handler: 记忆处理器实例的引用
            rag_manager: RAG管理器实例的引用
        """
        super().__init__(message_manager)
        
        self.memory_handler = memory_handler
        self.rag_manager = rag_manager
        self.use_semantic_search = rag_manager is not None
        
        # 设置各权重比例
        self.time_weight = 0.4  # 时间权重比例
        self.semantic_weight = 0.4  # 语义相关性权重比例
        self.user_weight = 0.2  # 用户相关性权重比例
        
        # 定义上下文轮数
        self.private_context_turns = 5
        self.group_context_turns = 3
        
        # 权重阈值和衰减参数
        self.weight_threshold = 0.3  # 筛选记忆的权重阈值
        self.decay_rate = 0.05  # 时间衰减率
        self.decay_method = 'exponential'  # 衰减方法：'exponential'或'linear'

    async def remember(self, user_message, assistant_response, user_id=None):
        """
        记住对话内容
        
        Args:
            user_message: 用户消息
            assistant_response: 助手回复
            user_id: 用户ID（可选）
            
        Returns:
            bool: 是否成功记住
        """
        try:
            if not self.memory_handler:
                logger.error("记忆处理器未初始化")
                return False
            
            # 移除"[当前用户问题]"标记
            if isinstance(user_message, str) and "[当前用户问题]" in user_message:
                user_message = user_message.replace("[当前用户问题]", "").strip()
            
            # 存储到记忆系统
            return self.memory_handler.add_memory(user_id, user_message, assistant_response)
        except Exception as e:
            logger.error(f"存储记忆失败: {str(e)}")
            return False
    
    async def retrieve(self, query, top_k=5):
        """
        检索相关记忆
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            str: 格式化的记忆文本
        """
        try:
            if not self.memory_handler:
                logger.error("记忆处理器未初始化")
                return ""
            
            # 使用记忆系统检索
            return self.memory_handler.retrieve(query, top_k)
        except Exception as e:
            logger.error(f"检索记忆失败: {str(e)}")
            return ""
    
    async def get_relevant_memories(self, query, username=None, top_k=5):
        """
        获取相关记忆
        将检索结果转换为结构化格式
        
        Args:
            query: 查询文本
            username: 用户名（可选）
            top_k: 返回的记忆条数
            
        Returns:
            list: 相关记忆内容列表，每项包含message和reply
        """
        try:
            if self.use_semantic_search and self.rag_manager:
                # 使用RAG系统进行语义检索
                logger.info(f"使用语义检索获取相关记忆 - 查询: {query[:30]}..., 用户: {username}")
                results = await self.rag_manager.query(query, top_k)
                
                # 处理检索结果
                memories = []
                for item in results:
                    metadata = item.get("metadata", {})
                    # 构建记忆项
                    memory_item = {
                        "message": metadata.get("user_message", ""),
                        "reply": metadata.get("assistant_response", ""),
                        "score": item.get("score", 0.0),
                        "user_id": metadata.get("user_id", "")
                    }
                    memories.append(memory_item)
                
                logger.info(f"语义检索找到 {len(memories)} 条相关记忆")
                return memories
            else:
                # 使用普通记忆检索
                logger.info(f"使用普通检索获取相关记忆 - 查询: {query[:30]}..., 用户: {username}")
                return self.memory_handler.get_relevant_memories(query, username, top_k)
        except Exception as e:
            logger.error(f"获取相关记忆失败: {str(e)}")
            return []
    
    async def is_important(self, text):
        """
        判断文本是否包含重要信息
        
        Args:
            text: 需要判断的文本
            
        Returns:
            bool: 是否包含重要信息
        """
        try:
            if not self.memory_handler:
                logger.error("记忆处理器未初始化")
                return False
            
            # 使用记忆系统判断重要性
            return self.memory_handler.is_important(text)
        except Exception as e:
            logger.error(f"判断文本重要性失败: {str(e)}")
            return False
    
    def get_stats(self):
        """
        获取记忆统计信息
        
        Returns:
            dict: 包含记忆统计信息的字典
        """
        try:
            if not self.memory_handler:
                return {
                    "memory_count": 0,
                    "embedding_count": 0,
                    "initialized": False
                }
            
            # 从记忆处理器获取统计信息
            return self.memory_handler.get_memory_stats()
        except Exception as e:
            logger.error(f"获取记忆统计失败: {str(e)}")
            return {
                "memory_count": 0,
                "embedding_count": 0,
                "initialized": True,
                "error": str(e)
            }

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

def init_memory(root_dir, api_wrapper=None):
    """
    初始化记忆系统
    
    Args:
        root_dir: 根目录路径
        api_wrapper: API调用封装器，可选
        
    Returns:
        memory_processor: 记忆处理器
    """
    global _initialized, _memory_processor
    
    if _initialized and _memory_processor:
        logger.info("记忆系统已初始化，重用现有实例")
        return _memory_processor
    
    try:
        # 从配置获取RAG设置
        from src.config import config
        
        # 初始化记忆系统
        logger.info(f"初始化记忆系统，根目录: {root_dir}")
        
        # 如果api_wrapper为None，创建一个
        if api_wrapper is None:
            from src.api_client.wrapper import APIWrapper
            api_wrapper = APIWrapper(
                api_key=config.llm.api_key,
                base_url=config.llm.base_url
            )
        
        # 从config.yaml获取RAG配置
        rag_config = {
            'api_key': config.rag.api_key,
            'base_url': config.rag.base_url or config.llm.base_url,  # 如果RAG基础URL为空，使用LLM的基础URL
            'embedding_model': config.rag.embedding_model,
            'reranker_model': config.rag.reranker_model,
            'local_embedding_model_path': config.rag.local_embedding_model_path,
            'top_k': config.rag.top_k,
            'is_rerank': config.rag.is_rerank,
            'auto_adapt_siliconflow': config.rag.auto_adapt_siliconflow
        }
        
        logger.info(f"使用RAG配置: 嵌入模型={rag_config['embedding_model']}, TopK={rag_config['top_k']}")
        
        # 初始化内存处理器
        from src.handlers.memories.memory_processor import MemoryProcessor
        _memory_processor = MemoryProcessor(root_dir, api_wrapper, rag_config)
        _initialized = True
        
        return _memory_processor
    except Exception as e:
        logger.error(f"初始化记忆系统失败: {str(e)}", exc_info=True)
        # 创建一个默认的MemoryProcessor作为回退方案
        from src.handlers.memories.memory_processor import MemoryProcessor
        _memory_processor = MemoryProcessor(root_dir)
        return _memory_processor

# 记忆API - 同步版本
def remember(user_message, assistant_response, user_id=None):
    """
    记住对话内容 - 同步版本
    
    Args:
        user_message: 用户消息
        assistant_response: 助手回复
        user_id: 用户ID（可选）
        
    Returns:
        bool: 是否成功记住
    """
    global _memory_processor
    
    if not _memory_processor:
        logger.error("记忆处理器未初始化")
        return False
        
    try:
        # 移除"[当前用户问题]"标记
        if isinstance(user_message, str) and "[当前用户问题]" in user_message:
            user_message = user_message.replace("[当前用户问题]", "").strip()
            
        # 如果_memory_processor是异步方法，使用_run_async运行它
        if asyncio.iscoroutinefunction(_memory_processor.remember):
            return _run_async(_memory_processor.remember(user_message, assistant_response, user_id))
        else:
            # 直接调用，如果MemoryProcessor.remember已改为同步方法
            return _memory_processor.remember(user_message, assistant_response, user_id)
    except Exception as e:
        logger.error(f"调用remember方法时出错: {str(e)}")
        return False

# 检索API - 同步版本
def retrieve(query, top_k=5):
    """
    检索相关记忆 - 同步版本
    
    Args:
        query: 查询文本
        top_k: 返回结果数量
        
    Returns:
        str: 格式化的记忆文本
    """
    global _memory_processor
    
    if not _memory_processor:
        logger.error("记忆处理器未初始化")
        return ""
        
    try:
        # 如果_memory_processor是异步方法，使用_run_async运行它
        if asyncio.iscoroutinefunction(_memory_processor.retrieve):
            return _run_async(_memory_processor.retrieve(query, top_k))
        else:
            # 直接调用同步方法
            return _memory_processor.retrieve(query, top_k)
    except Exception as e:
        logger.error(f"检索记忆失败: {str(e)}")
        return ""

# 重要性判断API - 同步版本
def is_important(text):
    """
    判断文本是否包含重要信息 - 同步版本
    
    Args:
        text: 需要判断的文本
        
    Returns:
        bool: 是否包含重要信息
    """
    global _memory_processor
    
    if not _memory_processor:
        logger.error("记忆处理器未初始化")
        return False
        
    try:
        # 如果_memory_processor是异步方法，使用_run_async运行它
        if asyncio.iscoroutinefunction(_memory_processor.is_important):
            return _run_async(_memory_processor.is_important(text))
        else:
            # 直接调用，如果MemoryProcessor.is_important已改为同步方法
            return _memory_processor.is_important(text)
    except Exception as e:
        logger.error(f"判断文本重要性失败: {str(e)}")
        return False

# 获取记忆处理器实例
def get_memory_processor():
    """
    获取记忆处理器实例
    
    Returns:
        MemoryProcessor: 记忆处理器实例
    """
    global _memory_processor
    return _memory_processor

# 获取记忆统计信息
def get_memory_stats():
    """
    获取记忆统计信息
    
    Returns:
        dict: 包含记忆统计信息的字典
    """
    global _memory_processor
    
    if not _memory_processor:
        return {
            "memory_count": 0,
            "embedding_count": 0,
            "initialized": False
        }
    
    try:
        stats = _memory_processor.get_stats()
        stats["initialized"] = True
        return stats
    except Exception as e:
        logger.error(f"获取记忆统计失败: {str(e)}")
        return {
            "memory_count": getattr(_memory_processor, "memory_count", 0),
            "embedding_count": getattr(_memory_processor, "embedding_count", 0),
            "initialized": True
        }

# 清空记忆
def clear_memories():
    """
    清空所有记忆
    
    Returns:
        bool: 是否成功清空
    """
    global _memory_processor
    
    if not _memory_processor:
        logger.error("记忆处理器未初始化")
        return False
        
    return _memory_processor.clear_memories()

# 保存记忆
def save_memories():
    """
    保存所有记忆
    
    Returns:
        bool: 是否成功保存
    """
    global _memory_processor
    
    if not _memory_processor:
        logger.error("记忆处理器未初始化")
        return False
        
    return _memory_processor.save()

# 初始化RAG
def init_rag_from_config(config_path):
    """
    从配置文件初始化RAG系统
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        object: RAG实例
    """
    global _memory_processor
    
    if not _memory_processor:
        logger.error("记忆处理器未初始化")
        return None
    
    try:
        # 优先从config.yaml获取配置
        from src.config import config
        
        # 创建RAG配置字典
        rag_config = {
            'api_key': config.rag.api_key,
            'base_url': config.rag.base_url or (config.llm.base_url if hasattr(config, 'llm') else ""),
            'embedding_model': config.rag.embedding_model,
            'reranker_model': config.rag.reranker_model,
            'local_embedding_model_path': config.rag.local_embedding_model_path,
            'top_k': config.rag.top_k,
            'is_rerank': config.rag.is_rerank,
            'auto_adapt_siliconflow': config.rag.auto_adapt_siliconflow
        }
        
        logger.info(f"使用config.yaml配置初始化RAG: 嵌入模型={rag_config['embedding_model']}, TopK={rag_config['top_k']}")
        
        # 使用新的方法进行初始化
        if hasattr(_memory_processor, 'init_rag_from_config'):
            return _memory_processor.init_rag_from_config(rag_config)
        else:
            # 兼容旧方法
            return _memory_processor.init_rag(config_path)
    except Exception as e:
        logger.warning(f"从config.yaml初始化RAG失败: {str(e)}，尝试使用提供的配置路径")
        # 如果从config.yaml初始化失败，尝试使用提供的配置路径
        return _memory_processor.init_rag(config_path)

# 获取RAG实例
def get_rag():
    """
    获取RAG实例
    
    Returns:
        object: RAG实例
    """
    global _memory_processor
    
    if not _memory_processor:
        logger.error("记忆处理器未初始化")
        return None
        
    return _memory_processor.get_rag()

# 获取相关记忆
def get_relevant_memories(query, username=None, top_k=5):
    """
    获取相关记忆
    将检索结果转换为结构化格式
    
    Args:
        query: 查询文本
        username: 用户名（可选）
        top_k: 返回的记忆条数
        
    Returns:
        list: 相关记忆内容列表，每项包含message和reply
    """
    global _memory_processor
    
    if not _memory_processor:
        logger.error("记忆处理器未初始化")
        return []
    
    try:
        # 如果_memory_processor是异步方法，使用_run_async运行它
        if hasattr(_memory_processor, 'get_relevant_memories'):
            if asyncio.iscoroutinefunction(_memory_processor.get_relevant_memories):
                return _run_async(_memory_processor.get_relevant_memories(query, username, top_k))
            else:
                # 直接调用同步方法
                return _memory_processor.get_relevant_memories(query, username, top_k)
        else:
            # 如果未实现该方法，尝试使用retrieve方法并处理结果
            logger.warning("记忆处理器没有get_relevant_memories方法，尝试使用retrieve方法")
            memories_text = retrieve(query, top_k)
            
            # 解析记忆文本并转换格式
            memories = []
            if memories_text and memories_text != "没有找到相关记忆":
                lines = memories_text.split('\n\n')
                for line in lines:
                    if not line.strip() or line.startswith('相关记忆:'):
                        continue
                        
                    parts = line.split('\n')
                    if len(parts) >= 2:
                        user_part = parts[0].strip()
                        ai_part = parts[1].strip()
                        
                        # 提取用户消息和AI回复
                        user_msg = user_part[user_part.find(': ')+2:] if ': ' in user_part else user_part
                        ai_msg = ai_part[ai_part.find(': ')+2:] if ': ' in ai_part else ai_part
                        
                        # 添加到记忆列表
                        memories.append({
                            'message': user_msg,
                            'reply': ai_msg
                        })
            
            return memories
    except Exception as e:
        logger.error(f"获取相关记忆失败: {str(e)}")
        return [] 
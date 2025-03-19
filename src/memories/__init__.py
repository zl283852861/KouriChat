"""
记忆系统包初始化文件 - 提供对外接口和函数
"""
import os
import asyncio
import logging
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
import uuid
import tiktoken
import pickle
import pytz
from src.api_client.wrapper import APIWrapper
from src.config import config

# 引入记忆处理器
from src.memories.memory_handler import MemoryHandler

# 导入RAG相关类和函数
from src.memories.memory.core.rag import (
    RAG, EmbeddingModel, ReRanker, 
    LocalEmbeddingModel, OnlineEmbeddingModel, SiliconFlowEmbeddingModel, HybridEmbeddingModel,
    CrossEncoderReRanker, OnlineCrossEncoderReRanker, SiliconFlowReRanker, SiliconFlowNativeReRanker,
    load_from_config, create_default_config
)

# 设置日志
logger = logging.getLogger('main')

# 全局单例实例
_memory_handler = None  # 记忆处理器实例
_rag_instance = None    # RAG实例
_embedding_model = None # 嵌入模型实例
_reranker = None        # 重排序器实例

def setup_memory(root_dir: str, api_wrapper: APIWrapper = None, embedding_model = None) -> MemoryHandler:
    """
    初始化记忆系统
    
    Args:
        root_dir: 根目录路径
        api_wrapper: API调用封装器
        embedding_model: 嵌入模型，如果提供则优先使用
        
    Returns:
        MemoryHandler: 记忆处理器实例
    """
    global _memory_handler
    
    try:
        logger.info("开始初始化记忆系统...")
        _memory_handler = MemoryHandler(root_dir, api_wrapper, embedding_model)
        logger.info(f"记忆系统初始化完成，当前记忆数量: {_memory_handler.memory_count}")
        return _memory_handler
    except Exception as e:
        logger.error(f"记忆系统初始化失败: {str(e)}")
        # 创建一个空的处理器作为回退方案
        _memory_handler = MemoryHandler()
        return _memory_handler

def setup_rag(embedding_model: EmbeddingModel, reranker: ReRanker = None) -> RAG:
    """
    设置RAG系统
    
    Args:
        embedding_model: 嵌入模型
        reranker: 重排序器（可选）
    
    Returns:
        RAG: RAG实例
    """
    global _rag_instance, _embedding_model, _reranker
    
    try:
        logger.info("开始初始化RAG系统...")
        _embedding_model = embedding_model
        _reranker = reranker
        _rag_instance = RAG(embedding_model=embedding_model, reranker=reranker)
        logger.info("RAG系统初始化完成")
        return _rag_instance
    except Exception as e:
        logger.error(f"RAG系统初始化失败: {str(e)}")
        return None

def get_memory_handler() -> Optional[MemoryHandler]:
    """
    获取记忆处理器实例
    
    Returns:
        Optional[MemoryHandler]: 记忆处理器实例，如未初始化则返回None
    """
    global _memory_handler
    return _memory_handler

def get_rag() -> Optional[RAG]:
    """
    获取RAG实例
    
    Returns:
        Optional[RAG]: RAG实例，如未初始化则返回None
    """
    global _rag_instance, _embedding_model, _reranker
    
    if _rag_instance is None and _embedding_model is not None:
        # 如果有嵌入模型但没有RAG实例，创建一个
        _rag_instance = RAG(embedding_model=_embedding_model, reranker=_reranker)
    
    return _rag_instance

def init_rag_from_config(config_path: str = None) -> Optional[RAG]:
    """
    从配置文件初始化RAG系统
    
    Args:
        config_path: 配置文件路径，如果为None则尝试查找默认路径
    
    Returns:
        Optional[RAG]: RAG实例，如初始化失败则返回None
    """
    global _rag_instance
    
    try:
        logger.info(f"从配置文件初始化RAG系统: {config_path or '(使用默认路径)'}")
        _rag_instance = load_from_config(config_path)
        if _rag_instance:
            logger.info("从配置文件成功加载RAG系统")
            
            # 尝试从JSON文件导入记忆
            try:
                import os
                json_path = os.path.join(os.getcwd(), "data", "memory", "rag-memory.json")
                if os.path.exists(json_path) and hasattr(_rag_instance, 'import_from_json'):
                    logger.info(f"检测到JSON记忆文件，尝试导入: {json_path}")
                    _rag_instance.import_from_json(json_path)
                    logger.info("记忆导入完成")
            except Exception as e:
                logger.error(f"导入JSON记忆失败: {str(e)}")
        else:
            logger.warning("从配置文件加载RAG系统失败")
        return _rag_instance
    except Exception as e:
        logger.error(f"从配置文件初始化RAG系统失败: {str(e)}")
        return None

# 导出主要类，便于直接从包导入
from src.memories.memory_handler import MemoryHandler
from src.memories.embedding_handler import EmbeddingHandler
from src.memories.rag_memory import RAGMemory
from src.memories.memory_operations import MemoryOperations

# 导出实用函数
async def remember(user_message: str, assistant_response: str, user_id: str = None) -> bool:
    """
    记住对话内容
    
    Args:
        user_message: 用户消息
        assistant_response: 助手回复
        user_id: 用户ID（可选）
        
    Returns:
        bool: 是否成功记住
    """
    handler = get_memory_handler()
    if not handler:
        logger.warning("记忆系统未初始化，无法记住对话")
        return False
    
    # 如果handler有add_memory方法，优先使用（可以传递user_id）
    if hasattr(handler, 'add_memory'):
        return handler.add_memory(user_message, assistant_response, user_id)
    elif hasattr(handler, '_add_to_rag_directly'):
        # 直接调用内部方法，可以传递user_id
        try:
            await handler.remember(user_message, assistant_response)
            if user_id:
                # 如果需要user_id，额外调用_add_to_rag_directly
                handler._add_to_rag_directly(user_message, assistant_response, user_id)
            return True
        except Exception as e:
            logger.error(f"记住对话失败: {str(e)}")
            return False
    else:
        # 兼容旧版本接口，但不能传递user_id
        logger.warning("使用兼容模式记忆，无法保存用户ID")
        return await handler.remember(user_message, assistant_response)

async def retrieve(query: str, top_k: int = 5) -> str:
    """
    检索记忆
    
    Args:
        query: 查询文本
        top_k: 返回的记忆条数
        
    Returns:
        str: 格式化的记忆内容
    """
    handler = get_memory_handler()
    if not handler:
        logger.warning("记忆系统未初始化，无法检索记忆")
        return ""
        
    return await handler.retrieve(query, top_k)

async def is_important(text: str) -> bool:
    """
    检查文本是否包含重要关键词，需要长期记忆
    
    Args:
        text: 要检查的文本
        
    Returns:
        bool: 是否需要长期记忆
    """
    handler = get_memory_handler()
    if not handler:
        return False
        
    return await handler.is_important(text)

def clear_memories():
    """
    清空所有记忆
    """
    handler = get_memory_handler()
    if handler:
        handler.clear_memories()

def save_memories():
    """
    手动保存记忆数据
    """
    logger.info("开始手动保存所有记忆数据...")
    
    # 保存MemoryHandler数据
    handler = get_memory_handler()
    if handler:
        try:
            logger.info("正在保存MemoryHandler数据...")
            handler.save()
            logger.info("MemoryHandler数据保存成功")
            
            # 检查是否有短期记忆系统
            if hasattr(handler, 'short_term_memory') and handler.short_term_memory:
                try:
                    logger.info("检测到短期记忆系统，尝试保存...")
                    handler.short_term_memory.save_memory()
                    logger.info("短期记忆系统数据保存成功")
                except Exception as stm_err:
                    logger.error(f"保存短期记忆系统数据失败: {str(stm_err)}")
        except Exception as h_err:
            logger.error(f"保存MemoryHandler数据失败: {str(h_err)}")
    else:
        logger.warning("未找到MemoryHandler实例，跳过保存")
        
    # 保存RAG实例数据
    rag_instance = get_rag()
    if rag_instance and hasattr(rag_instance, 'save'):
        try:
            logger.info("正在保存RAG实例数据...")
            rag_instance.save()
            logger.info("RAG实例数据保存成功")
            
            # 检查是否已导出到JSON
            json_path = os.path.join(os.getcwd(), "data", "memory", "rag-memory.json")
            if os.path.exists(json_path):
                logger.info(f"已验证RAG记忆JSON文件存在: {json_path}")
                # 获取文件大小
                try:
                    import os
                    file_size = os.path.getsize(json_path)
                    logger.info(f"RAG记忆JSON文件大小: {file_size} 字节")
                except Exception as fs_err:
                    logger.warning(f"获取JSON文件大小失败: {str(fs_err)}")
            else:
                logger.warning(f"RAG记忆JSON文件不存在: {json_path}")
                
                # 尝试手动导出JSON
                if hasattr(rag_instance, 'export_to_json'):
                    try:
                        logger.info("尝试手动导出RAG记忆到JSON...")
                        export_result = rag_instance.export_to_json()
                        if export_result:
                            logger.info("手动导出RAG记忆到JSON成功")
                        else:
                            logger.warning("手动导出RAG记忆到JSON返回失败结果")
                    except Exception as export_err:
                        logger.error(f"手动导出RAG记忆到JSON失败: {str(export_err)}")
        except Exception as e:
            logger.error(f"保存RAG实例数据失败: {str(e)}")
    else:
        if not rag_instance:
            logger.warning("未找到RAG实例，跳过保存")
        else:
            logger.warning("RAG实例没有save方法，跳过保存")
            
    logger.info("所有记忆数据保存完成")

async def update_embeddings():
    """
    更新所有记忆的嵌入向量
    """
    handler = get_memory_handler()
    if handler:
        await handler.update_embedding_for_all()

def get_memory_stats() -> Dict[str, int]:
    """
    获取记忆统计信息
    
    Returns:
        Dict[str, int]: 包含记忆条数和嵌入向量条数的统计信息
    """
    handler = get_memory_handler()
    if not handler:
        return {"memory_count": 0, "embedding_count": 0}
        
    return {
        "memory_count": handler.memory_count,
        "embedding_count": handler.embedding_count
    }

def get_formatted_memories() -> Dict:
    """
    获取格式化的记忆数据（直接从JSON文件读取新格式）
    
    Returns:
        Dict: 记忆数据，格式为 {conversation_key: [记忆条目]}
    """
    try:
        import os
        import json
        
        json_path = os.path.join(os.getcwd(), "data", "memory", "rag-memory.json")
        
        if not os.path.exists(json_path):
            logger.warning(f"记忆文件不存在: {json_path}")
            return {}
            
        with open(json_path, 'r', encoding='utf-8') as f:
            memories = json.load(f)
            
        logger.info(f"从JSON加载了 {len(memories)} 条对话记忆")
        return memories
    except Exception as e:
        logger.error(f"获取格式化记忆失败: {str(e)}")
        return {}
        
def get_memory_by_conversation(conversation_id: str) -> List[Dict]:
    """
    获取特定对话ID的记忆
    
    Args:
        conversation_id: 对话ID，如'conversation0'
        
    Returns:
        List[Dict]: 对话记忆列表
    """
    memories = get_formatted_memories()
    return memories.get(conversation_id, [])

def fix_memory_file_format():
    """
    检查并修复记忆文件中的字段名称问题
    """
    try:
        import os
        import json
        import logging
        import re
        
        logger = logging.getLogger('main')
        json_path = os.path.join(os.getcwd(), "data", "memory", "rag-memory.json")
        
        if not os.path.exists(json_path):
            logger.warning(f"记忆文件不存在，无需修复: {json_path}")
            return False
            
        # 加载JSON数据
        with open(json_path, 'r', encoding='utf-8') as f:
            conversations = json.load(f)
        
        # 导入清理函数
        try:
            from src.memories.memory_utils import clean_dialog_memory
        except ImportError:
            # 定义一个简单的备用清理函数
            def clean_dialog_memory(sender_text, receiver_text):
                """简易版清理函数"""
                if sender_text:
                    sender_text = re.sub(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\]', '', sender_text)
                    sender_text = re.sub(r'ta 私聊对你说：', '', sender_text)
                    sender_text = re.sub(r'\n+', ' ', sender_text)
                    sender_text = re.sub(r'请注意：你的回复应当.*$', '', sender_text, flags=re.DOTALL)
                    sender_text = sender_text.strip()
                
                if receiver_text:
                    receiver_text = receiver_text.replace('\\', ' ')
                    receiver_text = ' '.join(receiver_text.split())
                
                return sender_text, receiver_text
        
        # 检查并修复字段名问题
        modified = False
        for conv_key, conv_data in conversations.items():
            for entry in conv_data:
                if "is_ initiative" in entry:
                    entry["is_initiative"] = entry.pop("is_ initiative")
                    modified = True
                
                # 清理对话文本
                if "sender_text" in entry and "receiver_text" in entry:
                    clean_sender, clean_receiver = clean_dialog_memory(entry["sender_text"], entry["receiver_text"])
                    if clean_sender != entry["sender_text"] or clean_receiver != entry["receiver_text"]:
                        entry["sender_text"] = clean_sender
                        entry["receiver_text"] = clean_receiver
                        modified = True
                        logger.info(f"清理了对话文本格式: {conv_key}")
        
        # 如果修改了，保存回文件
        if modified:
            logger.info(f"修复了字段命名问题和文本格式，保存更新")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(conversations, f, ensure_ascii=False, indent=2)
            return True
        else:
            logger.info("记忆文件格式正确，无需修复")
            return False
            
    except Exception as e:
        logger.error(f"修复记忆文件格式失败: {str(e)}")
        return False

# 确保所有函数都被导出
__all__ = [
    # 内存处理函数
    'setup_memory', 'get_memory_handler', 'get_memory_stats',
    'remember', 'retrieve', 'is_important',
    'clear_memories', 'save_memories', 'update_embeddings',
    'get_formatted_memories', 'get_memory_by_conversation', 'fix_memory_file_format',
    
    # 主要类
    'MemoryHandler', 'EmbeddingHandler', 'RAGMemory', 'MemoryOperations',
    
    # RAG相关
    'setup_rag', 'get_rag', 'init_rag_from_config',
    'RAG', 'EmbeddingModel', 'ReRanker',
    'LocalEmbeddingModel', 'OnlineEmbeddingModel', 'SiliconFlowEmbeddingModel', 'HybridEmbeddingModel',
    'CrossEncoderReRanker', 'OnlineCrossEncoderReRanker', 'SiliconFlowReRanker', 'SiliconFlowNativeReRanker',
    'load_from_config', 'create_default_config'
] 
"""
记忆模块初始化文件 - 导出记忆核心相关类和兼容接口
"""

# 导出RAG记忆类
from src.memories.rag_memory import RAGMemory 
from src.memories.memory.core.rag import RAG, EmbeddingModel, ReRanker, LocalEmbeddingModel, OnlineEmbeddingModel, HybridEmbeddingModel

# 维护兼容性的单例实例
_memory_instance = None
_memory_setting = None
_rag_instance = None
_embedding_model = None
_reranker = None

# 导出记忆相关模块
from src.memories.memory_handler import MemoryHandler
from src.memories.memory_operations import MemoryOperations
from src.memories.embedding_handler import EmbeddingHandler

__all__ = ['RAGMemory', 'MemoryHandler', 'MemoryOperations', 'EmbeddingHandler', 
           'RAG', 'EmbeddingModel', 'ReRanker', 'LocalEmbeddingModel', 'OnlineEmbeddingModel', 'HybridEmbeddingModel',
           'setup_memory', 'get_memory', 'start_memory', 'setup_rag', 'get_rag']

# 兼容接口：设置记忆
def setup_memory(memory_path: str):
    """
    设置 Memory 需要的配置
    :param memory_path: 记忆文件路径
    """
    global _memory_setting
    _memory_setting = {
        "path": memory_path
    }

# 兼容接口：设置RAG
def setup_rag(embedding_model: EmbeddingModel, reranker: ReRanker = None):
    """
    设置 RAG 需要的配置
    :param embedding_model: 嵌入模型
    :param reranker: 重排序器
    """
    global _embedding_model, _reranker, _rag_instance
    _embedding_model = embedding_model
    _reranker = reranker
    _rag_instance = RAG(embedding_model=embedding_model, reranker=reranker)
    
# 兼容接口：获取RAG单例实例
def get_rag() -> RAG:
    """
    获取 RAG 单例实例
    """
    global _rag_instance, _embedding_model, _reranker
    if _rag_instance is None:
        if _embedding_model is None:
            raise ValueError("请先调用setup_rag进行配置")
        _rag_instance = RAG(embedding_model=_embedding_model, reranker=_reranker)
    return _rag_instance
    
# 兼容接口：获取记忆单例实例
def get_memory():
    """
    获取 Memory 单例实例
    """
    global _memory_instance, _memory_setting
    if _memory_instance is None:
        if _memory_setting is None:
            raise ValueError("请先调用setup_memory进行配置")
        # 使用RAGMemory代替原始Memory类
        _memory_instance = RAGMemory(root_dir=os.path.dirname(os.path.dirname(_memory_setting['path'])))
    return _memory_instance

# 兼容接口：启动记忆系统  
def start_memory():
    """
    启动记忆系统，加载数据
    """
    # 导入需要的库
    import os
    import logging
    from typing import List, Dict, Tuple
    
    logger = logging.getLogger('main')
    
    try:
        # 获取记忆实例
        memory = get_memory()
        
        # 加载记忆数据
        if hasattr(memory, 'load_memories'):
            memory.load_memories()
            logger.info("记忆系统已启动，记忆数据加载完成")
            
            # 打印加载的数据统计
            if hasattr(memory, 'memory_data'):
                key_value_pairs = list(memory.memory_data.items())
                logger.info(f"已加载记忆条目: {len(key_value_pairs)}条")
            
            return True
    except Exception as e:
        logger.error(f"启动记忆系统失败: {str(e)}")
        return False
        
    return True

# 需要的导入
import os

from src.memories.memory.core.memory import Memory
from src.memories.memory.core.rag import RAG, EmbeddingModel, ReRanker, LocalEmbeddingModel, OnlineEmbeddingModel, HybridEmbeddingModel

_memory_instance = None
_rag_instance = None
_rag_settings = None
_memory_setting = None


def setup_rag(embedding_model: EmbeddingModel, reranker: ReRanker = None):
    """
    设置 RAG 所需的配置
    :param embedding_model: 嵌入模型
    :param reranker: 重排模型
    """
    global _rag_settings
    _rag_settings = {
        "embedding": embedding_model,
        "reranker": reranker
    }


def setup_memory(memory_path: str):
    """
    设置 Memory 需要的配置
    :param memory_path: 记忆文件路径
    """
    global _memory_setting
    _memory_setting = {
        "path": memory_path
    }


def get_memory():
    """
    获取 Memory 单例实例
    """
    global _memory_instance, _memory_setting
    if _memory_instance is None:
        if _memory_setting is None:
            raise RuntimeError("Please call setup() first to initialize settings")
        _memory_instance = Memory(config_path=_memory_setting['path'])
    return _memory_instance


def get_rag() -> RAG:
    """
    获取 RAG 单例实例
    """
    global _rag_instance, _rag_settings
    if _rag_instance is None:
        if _rag_settings is None:
            raise RuntimeError("Please call setup() first to initialize settings")
        _rag_instance = RAG(
            embedding_model=_rag_settings['embedding'],
            reranker=_rag_settings['reranker']
        )
    return _rag_instance


def start_memory():
    """初始化记忆系统并加载现有记忆到RAG"""
    import logging
    logger = logging.getLogger('main')
    
    try:
        rag = get_rag()
        memory = get_memory()
        
        # 记录初始化信息
        logger.info("开始初始化记忆系统")
        
        # 获取键值对并记录数量
        key_value_pairs = memory.get_key_value_pairs()
        if key_value_pairs:
            pair_count = len(key_value_pairs)
            logger.info(f"发现现有记忆: {pair_count} 条")
            
            # 添加到RAG系统
            rag.add_documents(key_value_pairs)
            logger.info(f"已将 {pair_count} 条记忆添加到RAG系统")
        else:
            logger.info("未发现现有记忆")
        
        # 注册记忆钩子
        @memory.add_memory_hook
        def hook(key, value):
            """记忆文档增加时的钩子函数，对RAG内部文档进行增量维护"""
            try:
                # 检查格式并记录详细信息
                logger.debug(f"钩子函数触发 - 键: {key[:50]}..., 值: {value[:50]}...")
                
                # 使用正确的格式添加文档
                if isinstance(key, str) and isinstance(value, str):
                    document = f"{key}: {value}"
                    rag.add_documents([document])
                    logger.info(f"已通过钩子添加合并格式记忆到RAG系统: {document[:50]}...")
                else:
                    # 尝试不同的格式添加
                    try:
                        rag.add_documents([f"{key}: {value}"])
                        logger.info(f"已通过钩子添加记忆到RAG系统(格式1): {key[:30]}...")
                    except Exception:
                        try:
                            rag.add_documents([key, value])
                            logger.info(f"已通过钩子添加记忆到RAG系统(格式2): {key[:30]}...")
                        except Exception:
                            # 最后尝试原始形式
                            rag.add_documents([(key, value)])
                            logger.info(f"已通过钩子添加记忆到RAG系统(元组格式): {key[:30]}...")
            except Exception as e:
                logger.error(f"钩子添加记忆到RAG失败: {str(e)}")
                import traceback
                logger.error(f"详细错误堆栈: {traceback.format_exc()}")
        
        logger.info("记忆系统初始化完成")
        
    except Exception as e:
        logger.error(f"初始化记忆系统失败: {str(e)}", exc_info=True)

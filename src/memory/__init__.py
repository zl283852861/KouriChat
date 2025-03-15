from src.memory.core.rag_memory import RAGMemory
from src.memory.core.rag import RAGMemory as RAG, OnlineEmbeddingModel, OnlineCrossEncoderReRanker

_memory = None
_rag = None


def setup_memory(config_path='../config/rag_memory.json'):
    global _memory
    _memory = RAGMemory(config_path=config_path)
    return _memory


def get_memory():
    global _memory
    if _memory is None:
        _memory = setup_memory()
    return _memory


def setup_rag(embedding_model=None, reranker=None):
    global _rag
    _rag = RAG(embedding_model=embedding_model, reranker=reranker)
    return _rag


def get_rag():
    global _rag
    if _rag is None:
        _rag = setup_rag()
    return _rag


def start_memory():
    """启动记忆系统"""
    memory = get_memory()
    rag = get_rag()
    
    # 将现有记忆加载到RAG中
    documents = []
    for key, value in memory.settings.items():
        documents.append(f"{key}: {value}")
    
    if documents:
        rag.add_documents(documents)
    
    # 添加记忆钩子
    @memory.add_memory_hook
    def memory_hook(key, value):
        rag.add_documents([f"{key}: {value}"])

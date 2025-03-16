from src.memories.memory import *
from src.memories.memory.core.rag import ReRanker, EmbeddingModel

class ShortTermMemory:
    _instance = None
    
    @classmethod
    def get_instance(cls, memory_path=None, embedding_model=None, reranker=None, force_new=False):
        """
        获取单例实例
        :param memory_path: 记忆路径
        :param embedding_model: 嵌入模型
        :param reranker: 重排序器
        :param force_new: 是否强制创建新实例
        :return: ShortTermMemory实例
        """
        if force_new or cls._instance is None:
            if memory_path is not None and embedding_model is not None:
                instance = cls(memory_path, embedding_model, reranker)
                if not force_new:
                    cls._instance = instance
                return instance
            elif cls._instance is None:
                raise ValueError("首次创建实例需要提供所有必要参数")
        return cls._instance
    
    def __init__(self, memory_path: str, embedding_model: EmbeddingModel, reranker: ReRanker = None):
        setup_memory(memory_path)
        setup_rag(embedding_model, reranker)
        self.memory = get_memory()
        self.rag = get_rag()
        
        # 移除这里的自动添加，改为在需要时手动调用_load_memory
        self._handle_save_memory = None
        self._handle_start_hook = None
    
    def handle_save_memory(self, func):
        """
        这个方法用于绑定保存记忆的函数
        """
        self._handle_save_memory = func

    def save_memory(self):
        """
        这个方法用于保存记忆
        """
        if self._handle_save_memory:
            self._handle_save_memory(lambda: self.memory.save())
        else:
            self.memory.save()
    
    def add_start_hook(self, func):
        """
        这个方法用于绑定开始记忆的钩子
        """
        self._handle_start_hook = func
    
    def start_memory(self):
        """
        这个方法用于开始记忆文档维护
        """
        if self._handle_start_hook:
            self._handle_start_hook()
        start_memory()

    def add_memory(self, memory_key, memory_value):
        """添加记忆到短期记忆"""
        # 打印调用跟踪
        import traceback
        stack = traceback.extract_stack()
        caller = stack[-2]
        print(f"记忆添加调用源: {caller.filename}:{caller.lineno}")
        
        # 增强重复检查
        if memory_key in self.memory.settings:
            print(f"跳过重复记忆键: {memory_key[:30]}...")
            return
        
        # 检查值是否已存在
        if memory_value in self.memory.settings.values():
            print(f"跳过重复记忆值: {memory_value[:30]}...")
            return
        
        # 检查RAG中是否已存在
        if self.rag and hasattr(self.rag, 'documents'):
            if memory_key in self.rag.documents or memory_value in self.rag.documents:
                print(f"跳过RAG中已存在的记忆")
                return
        
        # 添加到Memory
        self.memory[memory_key] = memory_value
        
        # 将记忆写入RAG系统
        memory_pair = [(memory_key, memory_value)]
        self.rag.add_documents(documents=memory_pair)
        
        # 保存记忆状态
        self.save_memory()
        
        print(f"已添加新记忆: {memory_key[:50]}...")

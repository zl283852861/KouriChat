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
        # 导入线程池
        import concurrent.futures
        import logging
        self.logger = logging.getLogger('main')
        
        setup_memory(memory_path)
        setup_rag(embedding_model, reranker)
        self.memory = get_memory()
        self.rag = get_rag()
        
        # 创建线程池用于异步处理嵌入和记忆操作
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="memory_worker")
        self.memory_ops_queue = []  # 记录进行中的操作
        
        # 移除这里的自动添加，改为在需要时手动调用_load_memory
        self._handle_save_memory = None
        self._handle_start_hook = None
        
        self.logger.info("短期记忆系统初始化完成，启用异步处理线程池")
    
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
        
    def _async_add_memory(self, memory_key, memory_value, user_id=None):
        """
        异步处理记忆添加的内部方法
        
        Args:
            memory_key: 记忆键（用户输入）
            memory_value: 记忆值（AI回复）
            user_id: 用户ID（可选）
        """
        try:
            # 详细记录函数调用
            self.logger.debug(f"异步添加记忆 - 键长度: {len(memory_key)}, 值长度: {len(memory_value)}")
            
            # 增强重复检查
            if memory_key in self.memory.settings:
                self.logger.warning(f"跳过重复记忆键: {memory_key[:30]}...")
                return
            
            # 检查值是否已存在
            if memory_value in self.memory.settings.values():
                self.logger.warning(f"跳过重复记忆值: {memory_value[:30]}...")
                return
            
            # 检查RAG中是否已存在
            if self.rag and hasattr(self.rag, 'documents'):
                if memory_key in self.rag.documents or memory_value in self.rag.documents:
                    self.logger.warning(f"跳过RAG中已存在的记忆")
                    return
            
            # 添加到记忆系统
            self.memory.add(memory_key, memory_value)
            
            # 更新RAG系统
            if self.rag:
                # 添加记忆到RAG系统，包含用户ID信息
                document_info = f"USER:{user_id} - " if user_id else ""
                self.rag.add([
                    f"{document_info}{memory_key}",
                    f"{document_info}{memory_value}"
                ])
                
            self.logger.info(f"成功异步添加记忆 - 键: {memory_key[:30]}...")
            return True
        except Exception as e:
            self.logger.error(f"异步添加记忆失败: {str(e)}")
            return False

    def add_memory(self, memory_key, memory_value, user_id=None):
        """
        添加记忆到短期记忆 - 异步处理方式
        
        Args:
            memory_key: 记忆键（用户输入）
            memory_value: 记忆值（AI回复）
            user_id: 用户ID（可选）
            
        Returns:
            bool: 是否成功添加到处理队列
        """
        # 输入验证
        if not memory_key or not memory_value:
            self.logger.error("无法添加空记忆")
            return False
            
        if isinstance(memory_key, str) and "API调用失败" in memory_key:
            self.logger.warning(f"记忆键包含API错误信息，跳过添加: {memory_key[:50]}...")
            return False
            
        if isinstance(memory_value, str) and "API调用失败" in memory_value:
            self.logger.warning(f"记忆值包含API错误信息，跳过添加: {memory_value[:50]}...")
            return False
        
        # 保护性检查，确保不添加过长的记忆
        try:
            if len(memory_key) > 2000 or len(memory_value) > 2000:
                self.logger.warning(f"记忆过长，截断处理: key={len(memory_key)}, value={len(memory_value)}")
                memory_key = memory_key[:2000] + "..." if len(memory_key) > 2000 else memory_key
                memory_value = memory_value[:2000] + "..." if len(memory_value) > 2000 else memory_value
        except Exception as e:
            self.logger.error(f"检查记忆长度时出错: {str(e)}")
        
        # 提交到线程池异步处理
        try:
            self.logger.info(f"提交记忆到异步处理线程: {memory_key[:30]}...")
            # 如果提供了user_id，将其作为额外参数传递给异步处理函数
            if user_id:
                future = self.thread_pool.submit(self._async_add_memory, memory_key, memory_value, user_id)
            else:
                future = self.thread_pool.submit(self._async_add_memory, memory_key, memory_value)
                
            self.memory_ops_queue.append(future)
            
            # 清理已完成的操作
            self.memory_ops_queue = [f for f in self.memory_ops_queue if not f.done()]
            self.logger.info(f"当前进行中的记忆操作数: {len(self.memory_ops_queue)}")
            
            return True
        except Exception as e:
            self.logger.error(f"提交记忆到线程池失败: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
            
    def __del__(self):
        """在对象销毁时关闭线程池"""
        if hasattr(self, 'thread_pool'):
            try:
                self.thread_pool.shutdown(wait=False)
                self.logger.info("记忆处理线程池已关闭")
            except Exception as e:
                self.logger.error(f"关闭记忆处理线程池失败: {str(e)}")

    # 添加下载模型的命令处理方法    
    def command_download_model(self):
        """Web控制台命令：下载本地备用嵌入模型"""
        try:
            if hasattr(self.memory.rag, 'embedding_model') and self.memory.rag.embedding_model:
                if hasattr(self.memory.rag.embedding_model, 'download_model_web_cmd'):
                    return self.memory.rag.embedding_model.download_model_web_cmd()
                elif hasattr(self.memory.rag.embedding_model, '_download_local_model'):
                    self.memory.rag.embedding_model._download_local_model()
                    return "本地备用嵌入模型下载完成"
                else:
                    return "当前嵌入模型不支持下载"
            else:
                return "无法找到嵌入模型实例"
        except Exception as e:
            import traceback
            error_info = traceback.format_exc()
            return f"下载模型出错: {str(e)}\n{error_info}"

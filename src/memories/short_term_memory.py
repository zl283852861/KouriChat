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
        
    def _async_add_memory(self, memory_key, memory_value):
        """线程池中执行的实际添加记忆操作"""
        import traceback
        
        try:
            # 添加到Memory
            self.memory[memory_key] = memory_value
            self.logger.info(f"已添加记忆到Memory对象")
            
            # 将记忆写入RAG系统
            # 确保使用正确的元组格式
            memory_pair = [(memory_key, memory_value)]
            self.rag.add_documents(documents=memory_pair)
            self.logger.info(f"已添加记忆到RAG系统")
            
            # 保存记忆状态
            self.save_memory()
            self.logger.info(f"已保存记忆状态")
            
            # 验证添加是否成功
            if memory_key in self.memory.settings:
                self.logger.info(f"验证成功: 记忆键已存在于Memory对象中")
                return True
            else:
                self.logger.warning(f"验证失败: 记忆键未存在于Memory对象中")
                return False
                
        except Exception as e:
            # 记录详细错误信息
            self.logger.error(f"[异步处理]添加记忆时发生错误: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    def add_memory(self, memory_key, memory_value):
        """添加记忆到短期记忆 - 异步处理方式"""
        # 打印调用跟踪
        import traceback
        
        # 详细记录函数调用
        stack = traceback.extract_stack()
        caller = stack[-2]
        self.logger.info(f"记忆添加调用源: {caller.filename}:{caller.lineno}")
        
        # 输出更多调试信息
        self.logger.info(f"添加记忆 - 键长度: {len(memory_key)}, 值长度: {len(memory_value)}")
        self.logger.info(f"键开头: {memory_key[:30]}..., 值开头: {memory_value[:30]}...")
        
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
        
        # 提交到线程池异步处理
        try:
            self.logger.info(f"提交记忆到异步处理线程: {memory_key[:30]}...")
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

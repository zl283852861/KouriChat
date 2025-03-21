from src.memories.memory import *
from src.memories.memory.core.rag import ReRanker, EmbeddingModel
from src.memories import setup_memory, setup_rag, get_memory, get_rag, start_memory
import os
import logging
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Callable, Union

# 添加对clean_dialog_memory的导入
from src.memories.memory_utils import clean_memory_content, clean_dialog_memory

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
        
        # 初始化记忆系统
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
            if hasattr(self.memory, 'settings') and memory_key in self.memory.settings:
                self.logger.warning(f"跳过重复记忆键: {memory_key[:30]}...")
                return
            elif hasattr(self.memory, 'memory_data') and memory_key in self.memory.memory_data:
                self.logger.warning(f"跳过重复记忆键: {memory_key[:30]}...")
                return
            
            # 检查值是否已存在
            if hasattr(self.memory, 'settings') and memory_value in self.memory.settings.values():
                self.logger.warning(f"跳过重复记忆值: {memory_value[:30]}...")
                return
            elif hasattr(self.memory, 'memory_data') and memory_value in self.memory.memory_data.values():
                self.logger.warning(f"跳过重复记忆值: {memory_value[:30]}...")
                return
            
            # 检查RAG中是否已存在
            if self.rag and hasattr(self.rag, 'documents'):
                if memory_key in self.rag.documents or memory_value in self.rag.documents:
                    self.logger.warning(f"跳过RAG中已存在的记忆")
                    return
            
            # 添加到记忆系统
            if hasattr(self.memory, 'add'):
                self.memory.add(memory_key, memory_value)
            elif hasattr(self.memory, 'add_memory'):
                self.memory.add_memory(memory_key, memory_value)
            
            # 更新RAG系统
            if self.rag:
                # 添加记忆到RAG系统，使用新格式
                rag_result = self._add_memory_to_rag_new_format(memory_key, memory_value, user_id)
                
                # 添加文档后保存记忆
                self.save_memory()
                
                if rag_result:
                    self.logger.info(f"成功异步添加记忆到RAG系统 - 键: {memory_key[:30]}...")
                else:
                    self.logger.warning(f"异步添加记忆到RAG系统失败 - 键: {memory_key[:30]}...")
                    return False
            else:
                self.logger.info(f"成功异步添加记忆 - 键: {memory_key[:30]}...")
            return True
        except Exception as e:
            self.logger.error(f"异步添加记忆失败: {str(e)}")
            return False

    def _add_memory_to_rag_new_format(self, memory_key, memory_value, user_id=None):
        """
        使用新格式将记忆添加到RAG系统
        
        Args:
            memory_key: 记忆键（用户输入）
            memory_value: 记忆值（AI回复）
            user_id: 用户ID（可选）
        """
        try:
            import os
            import json
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                  
            # 从config或环境变量获取当前角色名
            avatar_name = "AI助手"
            try:
                from src.config import config
                avatar_dir = config.behavior.context.avatar_dir
                # 提取最后一个目录作为角色名
                avatar_name = os.path.basename(avatar_dir)
            except Exception as e:
                self.logger.warning(f"获取角色名失败: {str(e)}")
                  
            # 确定是否为主动消息 (简单判断：如果消息中包含"主人"或类似词，可能是主动消息)
            is_initiative = "主人" in memory_key or "您好" in memory_key
                  
            # 尝试分析情感
            emotion = "None"
            try:
                # 导入情感分析模块
                from src.handlers.emotion import SentimentResourceLoader, SentimentAnalyzer
                # 创建分析器
                resource_loader = SentimentResourceLoader()
                analyzer = SentimentAnalyzer(resource_loader)
                # 分析情感
                sentiment_result = analyzer.analyze(memory_value)
                emotion = sentiment_result.get('sentiment_type', 'None').lower()
            except Exception as e:
                self.logger.warning(f"情感分析失败: {str(e)}")
            
            # 清理对话文本，过滤格式
            cleaned_memory_key, cleaned_memory_value = clean_dialog_memory(memory_key, memory_value)
            
            # 准备新格式的记忆数据
            memory_entry = {
                "bot_time": current_time,
                "sender_id": user_id or "未知用户",
                "sender_text": cleaned_memory_key,  # 使用清理后的文本
                "receiver_id": avatar_name,
                "receiver_text": cleaned_memory_value,  # 使用清理后的文本
                "emotion": emotion,
                "is_initiative": is_initiative
            }
            
            # 加载现有的记忆文件
            json_path = os.path.join(os.getcwd(), "data", "memory", "rag-memory.json")
            memory_data = {}
            
            # 确保目录存在
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            # 尝试加载现有记忆
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        memory_data = json.load(f)
                    self.logger.info(f"成功加载现有记忆文件")
                    
                    # 检查是否包含会话数据和向量数据
                    conversations_count = len([k for k in memory_data.keys() if k.startswith("conversation")])
                    has_embeddings = "embeddings" in memory_data
                    
                    self.logger.info(f"记忆文件包含 {conversations_count} 个会话" + 
                                   (", 包含向量嵌入数据" if has_embeddings else ", 不包含向量嵌入数据"))
                    
                except Exception as e:
                    self.logger.warning(f"加载记忆JSON失败，将创建新文件: {str(e)}")
                    memory_data = {}
            
            # 提取现有的会话数据
            conversations = {k: v for k, v in memory_data.items() if k.startswith("conversation")}
            
            # 生成新的对话索引
            next_index = 0
            for key in conversations.keys():
                if key.startswith("conversation"):
                    try:
                        index = int(key.replace("conversation", ""))
                        next_index = max(next_index, index + 1)
                    except:
                        pass
            
            # 添加新记忆
            conversation_key = f"conversation{next_index}"
            conversations[conversation_key] = [memory_entry]  # 使用列表包装单个条目，与现有格式一致
            
            # 构建新的记忆数据，保留非会话数据（如embeddings）
            new_memory_data = {k: v for k, v in memory_data.items() if not k.startswith("conversation")}
            # 添加会话数据
            for k, v in conversations.items():
                new_memory_data[k] = v
            
            # 保存更新后的记忆
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(new_memory_data, f, ensure_ascii=False, indent=2)
                
                self.logger.info(f"已将记忆添加到JSON格式文件，索引: {next_index}")
                self.logger.info(f"成功将对话保存到RAG系统: user_id={user_id}, emotion={emotion}")
                
                return True
            except Exception as file_err:
                self.logger.error(f"保存JSON文件失败: {str(file_err)}")
                return False
            
        except Exception as e:
            self.logger.error(f"使用新格式添加记忆失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
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
            # 尝试多种可能的属性路径
            embedding_model = None
            
            # 检查memory.rag.embedding_model
            if hasattr(self.memory, 'rag') and hasattr(self.memory.rag, 'embedding_model'):
                embedding_model = self.memory.rag.embedding_model
            # 直接检查rag
            elif self.rag and hasattr(self.rag, 'embedding_model'):
                embedding_model = self.rag.embedding_model
            
            if embedding_model:
                if hasattr(embedding_model, 'download_model_web_cmd'):
                    return embedding_model.download_model_web_cmd()
                elif hasattr(embedding_model, '_download_local_model'):
                    embedding_model._download_local_model()
                    return "本地备用嵌入模型下载完成"
                else:
                    return "当前嵌入模型不支持下载"
            else:
                return "无法找到嵌入模型实例"
        except Exception as e:
            import traceback
            error_info = traceback.format_exc()
            return f"下载模型出错: {str(e)}\n{error_info}"

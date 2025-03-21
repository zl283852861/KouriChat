"""
记忆处理器 - 中层代码
负责管控记忆的过滤格式化、写入、读取等功能
"""
import os
import logging
import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from datetime import datetime

# 导入底层核心
from src.handlers.memories.core.memory_utils import clean_memory_content, get_memory_path
from src.handlers.memories.core.rag import RagManager
from src.api_client.wrapper import APIWrapper
from src.utils.logger import get_logger

# 设置日志
logger = logging.getLogger('main')

class MemoryProcessor:
    """
    记忆处理器，中层模块，管理所有记忆操作
    """
    
    _instance = None  # 单例实例
    _initialized = False  # 初始化标志
    
    def __new__(cls, *args, **kwargs):
        """
        实现单例模式
        """
        if cls._instance is None:
            logger.info("创建记忆处理器单例实例")
            cls._instance = super(MemoryProcessor, cls).__new__(cls)
        return cls._instance
        
    def __init__(self, root_dir: str = None, api_wrapper: APIWrapper = None, rag_config_path: str = None):
        """
        初始化记忆处理器
        
        Args:
            root_dir: 项目根目录
            api_wrapper: API调用包装器
            rag_config_path: RAG配置文件路径
        """
        # 避免重复初始化
        if MemoryProcessor._initialized:
            return
            
        # 设置根目录
        self.root_dir = root_dir or os.getcwd()
        self.api_wrapper = api_wrapper
        
        # 初始化基本属性
        self.memory_data = {}  # 记忆数据
        self.embedding_data = {}  # 嵌入向量数据
        self.memory_hooks = []  # 记忆钩子
        self.memory_count = 0  # 记忆数量
        self.embedding_count = 0  # 嵌入向量数量
        
        # 记忆文件路径
        self.memory_path = get_memory_path(self.root_dir)
        logger.info(f"记忆文件路径: {self.memory_path}")
        
        # 初始化组件
        logger.info("初始化记忆处理器")
        self._load_memory()
        
        # 初始化RAG
        self.rag_manager = None
        if rag_config_path:
            self.init_rag(rag_config_path)
        
        # 标记为已初始化
        MemoryProcessor._initialized = True
        logger.info("记忆处理器初始化完成")
        
    def _load_memory(self):
        """加载记忆数据"""
        try:
            if os.path.exists(self.memory_path):
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.memory_data = data.get("memories", {})
                    self.embedding_data = data.get("embeddings", {})
                    
                # 确保每个用户的记忆是列表格式
                for user_id in self.memory_data:
                    if not isinstance(self.memory_data[user_id], list):
                        self.memory_data[user_id] = []
                        
                self.memory_count = sum(len(memories) for memories in self.memory_data.values())
                self.embedding_count = len(self.embedding_data)
                logger.info(f"从 {self.memory_path} 加载了 {self.memory_count} 条记忆和 {self.embedding_count} 条嵌入向量")
            else:
                logger.info(f"记忆文件 {self.memory_path} 不存在，将创建新文件")
                self.memory_data = {}
                self.embedding_data = {}
                self.save()
        except Exception as e:
            logger.error(f"加载记忆数据失败: {str(e)}")
            # 重置数据
            self.memory_data = {}
            self.embedding_data = {}
    
    def init_rag(self, config_path):
        """
        初始化RAG系统
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            RagManager: RAG管理器实例
        """
        try:
            logger.info(f"初始化RAG系统，配置文件: {config_path}")
            self.rag_manager = RagManager(config_path, self.api_wrapper)
            logger.info("RAG系统初始化成功")
            return self.rag_manager
        except Exception as e:
            logger.error(f"初始化RAG系统失败: {str(e)}")
            return None
            
    def get_rag(self):
        """
        获取RAG管理器
        
        Returns:
            RagManager: RAG管理器实例
        """
        return self.rag_manager
    
    def save(self):
        """
        保存记忆数据
        
        Returns:
            bool: 是否成功保存
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
            
            # 保存数据
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump({
                    "memories": self.memory_data,
                    "embeddings": self.embedding_data,
                }, f, ensure_ascii=False, indent=2)
                
            logger.info(f"记忆数据已保存到 {self.memory_path}")
            return True
        except Exception as e:
            logger.error(f"保存记忆数据失败: {str(e)}")
            return False
            
    def clear_memories(self):
        """
        清空所有记忆
        
        Returns:
            bool: 是否成功清空
        """
        try:
            self.memory_data = {}
            self.embedding_data = {}
            self.memory_count = 0
            self.embedding_count = 0
            
            # 清空RAG存储
            if self.rag_manager:
                self.rag_manager.clear_storage()
                
            self.save()
            logger.info("已清空所有记忆")
            return True
        except Exception as e:
            logger.error(f"清空记忆失败: {str(e)}")
            return False
        
    def add_memory_hook(self, hook: Callable):
        """
        添加记忆钩子
        
        Args:
            hook: 钩子函数，接收记忆键和值作为参数
        """
        self.memory_hooks.append(hook)
        logger.debug(f"已添加记忆钩子: {hook.__name__}")
        
    def remember(self, user_message: str, assistant_response: str, user_id: str = None) -> bool:
        """
        记住对话内容
        
        Args:
            user_message: 用户消息
            assistant_response: 助手回复
            user_id: 用户ID（必需）
            
        Returns:
            bool: 是否成功记住
        """
        try:
            if not user_id:
                logger.error("记住对话失败：未提供用户ID")
                return False
            
            # 清理内容
            clean_user_msg, clean_assistant_msg = clean_memory_content(user_message, assistant_response)
            
            # 过滤掉AI回复中的\字符，仅在保存记忆时
            clean_assistant_msg = clean_assistant_msg.replace('\\', '')
            
            # 初始化用户的记忆列表（如果不存在）
            if user_id not in self.memory_data:
                self.memory_data[user_id] = []
            
            # 创建新的记忆条目
            memory_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "human_message": clean_user_msg,
                "assistant_message": clean_assistant_msg
            }
            
            # 添加到记忆列表
            self.memory_data[user_id].append(memory_entry)
            self.memory_count = sum(len(memories) for memories in self.memory_data.values())
            
            # 添加到RAG系统
            if self.rag_manager:
                # 获取当前角色名
                avatar_name = "AI助手"
                try:
                    from src.config import config
                    avatar_dir = config.behavior.context.avatar_dir
                    avatar_name = os.path.basename(avatar_dir)
                except Exception as e:
                    logger.debug(f"获取角色名失败: {str(e)}")
                
                # 构建记忆文档
                memory_doc = {
                    "id": f"memory_{int(time.time())}",
                    "content": f"{user_id}: {clean_user_msg}\n{avatar_name}: {clean_assistant_msg}",
                    "metadata": {
                        "sender": user_id,
                        "receiver": avatar_name,
                        "sender_text": clean_user_msg,
                        "receiver_text": clean_assistant_msg,
                        "timestamp": memory_entry["timestamp"],
                        "type": "chat"
                    }
                }
                
                # 预处理过滤 - 检查内容质量
                if self._is_valid_for_rag(clean_user_msg, clean_assistant_msg):
                    # 使用线程池异步处理RAG添加操作
                    import threading
                    rag_thread = threading.Thread(
                        target=self._add_to_rag_thread,
                        args=(memory_doc,)
                    )
                    rag_thread.daemon = True
                    rag_thread.start()
            
            # 调用钩子
            for hook in self.memory_hooks:
                hook(user_id, memory_entry)
            
            # 保存到文件
            self.save()
            logger.info(f"成功记住对话，当前记忆数量: {self.memory_count}")
            return True
        except Exception as e:
            logger.error(f"记住对话失败: {str(e)}")
            return False
    
    def _add_to_rag_thread(self, memory_doc):
        """
        在线程中添加记忆到RAG系统
        
        Args:
            memory_doc: 记忆文档
        """
        try:
            if not self.rag_manager:
                return
                
            # 创建事件循环
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # 在事件循环中运行异步方法
                loop.run_until_complete(self.rag_manager.add_document(memory_doc))
                loop.close()
                
                logger.debug(f"成功添加记忆到RAG系统: {memory_doc['id']}")
            except Exception as e:
                logger.error(f"在线程中添加记忆到RAG系统失败: {str(e)}")
        except Exception as e:
            logger.error(f"添加记忆到RAG系统失败: {str(e)}")
    
    def _is_valid_for_rag(self, sender_text: str, receiver_text: str) -> bool:
        """
        检查内容是否适合添加到RAG系统
        
        Args:
            sender_text: 发送者文本
            receiver_text: 接收者文本
            
        Returns:
            bool: 是否适合添加到RAG
        """
        # 检查长度
        if len(sender_text) < 5 or len(receiver_text) < 5:
            return False
            
        # 检查是否包含特定的无意义内容
        noise_patterns = [
            "你好", "在吗", "谢谢", "没事了", "好的", "嗯嗯", "好", "是的", "不是",
            "你是谁", "你叫什么", "再见", "拜拜", "晚安", "早安", "午安"
        ]
        
        if sender_text.strip() in noise_patterns or receiver_text.strip() in noise_patterns:
            return False
            
        return True
        
    def retrieve(self, query: str, top_k: int = 5) -> str:
        """
        检索相关记忆（同步方法）
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            str: 格式化的记忆文本
        """
        try:
            if not self.rag_manager:
                logger.warning("RAG系统未初始化，无法检索记忆")
                return ""
            
            # 创建事件循环来运行异步查询
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # 如果没有事件循环，创建一个新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            # 在事件循环中运行异步查询
            if loop.is_running():
                # 使用future来异步运行协程
                future = asyncio.run_coroutine_threadsafe(self.rag_manager.query(query, top_k), loop)
                results = future.result()
            else:
                # 直接运行协程
                results = loop.run_until_complete(self.rag_manager.query(query, top_k))
            
            if not results or len(results) == 0:
                logger.info(f"未找到与查询 '{query}' 相关的记忆")
                return ""
                
            # 格式化结果
            formatted_results = []
            for i, result in enumerate(results):
                content = result.get('content', '')
                metadata = result.get('metadata', {})
                score = result.get('score', 0)
                
                timestamp = metadata.get('timestamp', '未知时间')
                formatted_results.append(f"记忆 {i+1} [{timestamp}] (相关度: {score:.2f}):\n{content}\n")
                
            return "\n".join(formatted_results)
        except Exception as e:
            logger.error(f"检索记忆失败: {str(e)}")
            return ""
    
    def is_important(self, text: str) -> bool:
        """
        判断文本是否包含重要信息（同步方法）
        
        Args:
            text: 需要判断的文本
            
        Returns:
            bool: 是否包含重要信息
        """
        try:
            # 如果有RAG管理器，使用它的方法判断
            if self.rag_manager:
                # 创建事件循环来运行异步查询
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    # 如果没有事件循环，创建一个新的
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                # 在事件循环中运行异步查询
                if loop.is_running():
                    # 使用future来异步运行协程
                    future = asyncio.run_coroutine_threadsafe(self.rag_manager.is_important(text), loop)
                    return future.result()
                else:
                    # 直接运行协程
                    return loop.run_until_complete(self.rag_manager.is_important(text))
                
            # 否则使用简单的规则判断
            # 1. 长度判断
            if len(text) > 100:  # 长文本更可能包含重要信息
                return True
                
            # 2. 关键词判断
            important_keywords = [
                "记住", "牢记", "不要忘记", "重要", "必须", "一定要",
                "地址", "电话", "密码", "账号", "名字", "生日",
                "喜欢", "讨厌", "爱好", "兴趣"
            ]
            
            for keyword in important_keywords:
                if keyword in text:
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"判断文本重要性失败: {str(e)}")
            return False
            
    async def generate_summary(self, limit: int = 20) -> str:
        """
        生成记忆摘要
        
        Args:
            limit: 摘要包含的记忆条数
            
        Returns:
            str: 记忆摘要
        """
        try:
            if not self.api_wrapper:
                logger.error("未提供API包装器，无法生成摘要")
                return ""
                
            # 如果有RAG管理器，使用它的方法生成摘要
            if self.rag_manager:
                return await self.rag_manager.generate_summary(limit)
                
            # 否则从基本记忆中生成
            if not self.memory_data:
                return "没有可用的记忆。"
                
            # 选择最新的几条记忆
            recent_memories = list(self.memory_data.items())[-limit:]
            
            # 格式化记忆
            memory_text = ""
            for i, (key, value) in enumerate(recent_memories):
                memory_text += f"记忆 {i+1}:\n用户: {key}\nAI: {value}\n\n"
                
            # 构造摘要请求
            prompt = f"""请根据以下对话记忆，总结出重要的信息点：

{memory_text}

请提供一个简洁的摘要，包含关键信息点和重要的细节。"""

            # 调用API生成摘要
            response = await self.api_wrapper.async_completion(
                prompt=prompt,
                temperature=0.3,
                max_tokens=500
            )
            
            return response.get("content", "无法生成摘要")
        except Exception as e:
            logger.error(f"生成记忆摘要失败: {str(e)}")
            return "生成摘要时出错"

    def get_stats(self):
        """
        获取记忆统计信息
        
        Returns:
            Dict: 包含记忆统计信息的字典
        """
        stats = {
            "memory_count": self.memory_count,
            "embedding_count": self.embedding_count,
        }
        
        # 如果有RAG管理器，添加嵌入模型缓存统计
        if self.rag_manager:
            try:
                embedding_model = self.rag_manager.embedding_model
                if embedding_model and hasattr(embedding_model, 'get_cache_stats'):
                    cache_stats = embedding_model.get_cache_stats()
                    
                    # 合并缓存统计到结果中
                    if isinstance(cache_stats, dict):
                        stats["cache_hits"] = cache_stats.get("hits", 0)
                        stats["cache_misses"] = cache_stats.get("misses", 0)
                        stats["cache_size"] = cache_stats.get("size", 0)
                        stats["cache_hit_rate_percent"] = 0
                        
                        # 计算命中率
                        total = stats["cache_hits"] + stats["cache_misses"]
                        if total > 0:
                            stats["cache_hit_rate_percent"] = (stats["cache_hits"] / total) * 100
            except Exception as e:
                logger.error(f"获取嵌入模型缓存统计失败: {str(e)}")
                
        return stats
    
    # 为与顶层接口兼容，添加别名
    get_memory_stats = get_stats 
    
    def get_relevant_memories(self, query, username=None, top_k=5):
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
            # 使用同步方式获取记忆文本
            memories_text = self.retrieve(query, top_k)
            
            # 检查结果
            if not memories_text or memories_text == "没有找到相关记忆":
                logger.info("没有找到相关记忆")
                return []
            
            # 解析记忆文本并转换格式
            memories = []
            lines = memories_text.split('\n\n')
            
            for line in lines:
                if not line.strip():
                    continue
                    
                if line.startswith('相关记忆:'):
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
            
            logger.info(f"解析出 {len(memories)} 条相关记忆")
            return memories
        except Exception as e:
            logger.error(f"获取相关记忆失败: {str(e)}")
            return []

    def add_memory(self, user_id: str, human_message: str, assistant_message: str):
        """
        添加新的记忆
        
        Args:
            user_id: 用户ID
            human_message: 用户消息
            assistant_message: 助手回复
            
        Returns:
            bool: 是否成功添加
        """
        try:
            if user_id not in self.memory_data:
                self.memory_data[user_id] = []
            
            memory_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "human_message": human_message,
                "assistant_message": assistant_message
            }
            
            self.memory_data[user_id].append(memory_entry)
            self.memory_count += 1
            
            # 调用记忆钩子
            for hook in self.memory_hooks:
                hook(user_id, memory_entry)
            
            # 保存到文件
            self.save()
            return True
        except Exception as e:
            logger.error(f"添加记忆失败: {str(e)}")
            return False 
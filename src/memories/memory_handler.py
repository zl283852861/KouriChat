"""
记忆处理器主模块 - 作为上层接口统一管理所有记忆功能
"""
import os
import logging
import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

# 引入内部模块
from src.memories.memory_utils import memory_cache, clean_memory_content, get_importance_keywords, get_memory_path
from src.api_client.wrapper import APIWrapper
from src.utils.logger import get_logger
from src.config import config

# 设置日志
logger = logging.getLogger('main')

class MemoryHandler:
    """
    记忆处理器，作为系统中所有记忆功能的统一入口
    """
    
    _instance = None  # 单例实例
    _initialized = False  # 初始化标志
    
    def __new__(cls, *args, **kwargs):
        """
        实现单例模式
        """
        if cls._instance is None:
            logger.info("创建记忆处理器单例实例")
            cls._instance = super(MemoryHandler, cls).__new__(cls)
        return cls._instance
        
    def __init__(self, root_dir: str = None, api_wrapper: APIWrapper = None, embedding_model = None):
        """
        初始化记忆处理器
        
        Args:
            root_dir: 项目根目录
            api_wrapper: API调用包装器
            embedding_model: 直接提供的嵌入模型
        """
        # 避免重复初始化
        if MemoryHandler._initialized:
            return
            
        # 设置根目录
        self.root_dir = root_dir or os.getcwd()
        self.api_wrapper = api_wrapper
        self.embedding_model = embedding_model  # 保存嵌入模型
        
        # 初始化基本属性
        self.memory_data = {}  # 记忆数据
        self.embedding_data = {}  # 嵌入向量数据
        self.memory_hooks = []  # 记忆钩子
        self.memory_count = 0  # 记忆数量
        self.embedding_count = 0  # 嵌入向量数量
        
        # 记忆文件路径
        self.memory_path = get_memory_path(self.root_dir)
        
        # 初始化组件
        logger.info("初始化记忆处理器")
        self._load_memory()
        
        # 标记为已初始化
        MemoryHandler._initialized = True
        logger.info("记忆处理器初始化完成")
        
    def _load_memory(self):
        """加载记忆数据"""
        try:
            if os.path.exists(self.memory_path):
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.memory_data = data.get("memories", {})
                    self.embedding_data = data.get("embeddings", {})
                    
                self.memory_count = len(self.memory_data)
                self.embedding_count = len(self.embedding_data)
                logger.info(f"从 {self.memory_path} 加载了 {self.memory_count} 条记忆和 {self.embedding_count} 条嵌入向量")
            else:
                logger.info(f"记忆文件 {self.memory_path} 不存在，将创建新文件")
                self.save()
        except Exception as e:
            logger.error(f"加载记忆数据失败: {str(e)}")
            # 重置数据
            self.memory_data = {}
            self.embedding_data = {}
            
    def save(self):
        """保存记忆数据"""
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
        except Exception as e:
            logger.error(f"保存记忆数据失败: {str(e)}")
            
    def clear_memories(self):
        """清空所有记忆"""
        self.memory_data = {}
        self.embedding_data = {}
        self.memory_count = 0
        self.embedding_count = 0
        self.save()
        logger.info("已清空所有记忆")
        
    def add_memory_hook(self, hook: Callable):
        """
        添加记忆钩子
        
        Args:
            hook: 钩子函数，接收记忆键和值作为参数
        """
        self.memory_hooks.append(hook)
        logger.debug(f"已添加记忆钩子: {hook.__name__}")
        
    @memory_cache
    async def remember(self, user_message: str, assistant_response: str) -> bool:
        """
        记住对话内容
        
        Args:
            user_message: 用户消息
            assistant_response: 助手回复
            
        Returns:
            bool: 是否成功记住
        """
        try:
            # 清理内容
            clean_key, clean_value = clean_memory_content(user_message, assistant_response)
            
            # 添加到记忆
            self.memory_data[clean_key] = clean_value
            self.memory_count = len(self.memory_data)
            
            # 尝试添加到RAG系统（如果存在）
            try:
                from src.memories.short_term_memory import ShortTermMemory
                stm = ShortTermMemory.get_instance(force_new=False)
                if stm:
                    # 通过ShortTermMemory添加记忆（会处理新格式）
                    stm._add_memory_to_rag_new_format(clean_key, clean_value)
                    logger.info("通过ShortTermMemory更新了RAG记忆")
                else:
                    # 没有ShortTermMemory实例，直接添加标准格式记忆
                    self._add_to_rag_directly(clean_key, clean_value)
            except Exception as e:
                logger.warning(f"尝试更新RAG记忆失败，将直接添加: {str(e)}")
                self._add_to_rag_directly(clean_key, clean_value)
            
            # 调用钩子
            for hook in self.memory_hooks:
                hook(clean_key, clean_value)
                
            # 保存
            self.save()
            logger.info(f"成功记住对话，当前记忆数量: {self.memory_count}")
            return True
        except Exception as e:
            logger.error(f"记住对话失败: {str(e)}")
            return False
        
    def _add_to_rag_directly(self, clean_key: str, clean_value: str, user_id: str = None):
        """
        直接以标准格式添加记忆到RAG系统
        
        Args:
            clean_key: 清理后的记忆键
            clean_value: 清理后的记忆值
            user_id: 用户ID（可选）
        """
        try:
            import os
            import json
            from datetime import datetime
            from src.memories import get_rag
            
            rag_instance = get_rag()
            if not rag_instance:
                logger.warning("RAG实例不可用，跳过添加")
                return
                
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # 从config或环境变量获取当前角色名
            avatar_name = "AI助手"
            try:
                from src.config import config
                avatar_dir = config.behavior.context.avatar_dir
                # 提取最后一个目录作为角色名
                avatar_name = os.path.basename(avatar_dir)
            except Exception as e:
                logger.warning(f"获取角色名失败: {str(e)}")
                
            # 确定是否为主动消息 (简单判断：如果消息中包含"主人"或类似词，可能是主动消息)
            is_initiative = "主人" in clean_key or "您好" in clean_key
            
            # 旧格式标准文本（用于RAG内部存储）
            user_doc = f"[{current_time}]对方(ID:{user_id or '未知用户'}): {clean_key}"
            ai_doc = f"[{current_time}] 你: {clean_value}"
            
            # 添加到RAG系统 - 旧格式（确保内部索引兼容性）
            if hasattr(rag_instance, 'add_documents'):
                rag_instance.add_documents(texts=[user_doc, ai_doc])
                
            # 准备新格式的记忆数据
            memory_entry = {
                "bot_time": current_time,
                "sender_id": user_id or "未知用户",
                "sender_text": clean_key,
                "receiver_id": avatar_name,
                "receiver_text": clean_value,
                "emotion": "None",  # 简化版本不进行情感分析
                "is_initiative": is_initiative
            }
            
            # 加载现有的记忆文件
            json_path = os.path.join(os.getcwd(), "data", "memory", "rag-memory.json")
            conversations = {}
            
            # 确保目录存在
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            # 尝试加载现有记忆
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        conversations = json.load(f)
                except Exception as e:
                    logger.warning(f"加载记忆JSON失败，将创建新文件: {str(e)}")
            
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
            conversations[conversation_key] = [memory_entry]
            
            # 保存更新后的记忆
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(conversations, f, ensure_ascii=False, indent=2)
                
            logger.info(f"已将记忆直接添加到JSON格式文件，索引: {next_index}")
            
        except Exception as e:
            logger.error(f"直接添加记忆到RAG失败: {str(e)}")
        
    @memory_cache
    async def retrieve(self, query: str, top_k: int = 5) -> str:
        """
        检索记忆
        
        Args:
            query: 查询文本
            top_k: 返回的记忆条数
            
        Returns:
            str: 格式化的记忆内容
        """
        try:
            if not self.memory_data:
                return "没有找到相关记忆"
                
            # 简单实现：根据字符串匹配检索
            # 真实场景下应该使用嵌入向量相似度检索
            results = []
            for key, value in self.memory_data.items():
                if query.lower() in key.lower() or query.lower() in value.lower():
                    results.append((key, value))
                    
            # 限制返回数量
            results = results[:top_k]
            
            if not results:
                return "没有找到相关记忆"
                
            # 格式化结果
            formatted = "相关记忆:\n\n"
            for i, (key, value) in enumerate(results, 1):
                formatted += f"{i}. 用户: {key}\n   回复: {value}\n\n"
                
            return formatted
        except Exception as e:
            logger.error(f"检索记忆失败: {str(e)}")
            return "检索记忆时出错"
        
    @memory_cache
    async def is_important(self, text: str) -> bool:
        """
        检查文本是否包含重要关键词，需要长期记忆
        
        Args:
            text: 要检查的文本
            
        Returns:
            bool: 是否需要长期记忆
        """
        try:
            # 获取重要性关键词
            keywords = get_importance_keywords()
            
            # 检查文本是否包含关键词
            return any(keyword in text for keyword in keywords)
        except Exception as e:
            logger.error(f"检查重要记忆失败: {str(e)}")
            return False
            
    async def add_embedding(self, key: str) -> bool:
        """
        为记忆添加嵌入向量
        
        Args:
            key: 记忆键
            
        Returns:
            bool: 是否成功添加
        """
        try:
            # 检查API包装器和嵌入模型
            if not self.api_wrapper and not self.embedding_model:
                logger.warning("缺少API包装器或嵌入模型，无法生成嵌入向量")
                return False
                
            # 检查记忆是否存在
            if key not in self.memory_data:
                logger.warning(f"记忆 {key} 不存在，无法添加嵌入向量")
                return False
                
            # 获取记忆内容
            memory_content = f"{key} {self.memory_data[key]}"
            
            # 使用嵌入模型（如果有）或API调用生成嵌入向量
            if self.embedding_model:
                # 直接使用嵌入模型
                if hasattr(self.embedding_model, 'embed'):
                    embedding = self.embedding_model.embed([memory_content])[0]
                    logger.debug(f"使用自定义嵌入模型生成向量，维度: {len(embedding)}")
                else:
                    # 假设是API的模型参数
                    model = self.embedding_model
                    response = await self.api_wrapper.embeddings.create(
                        model=model,
                        input=memory_content
                    )
                    embedding = response.data[0].embedding
            else:
                # 使用API生成嵌入向量
                model = "text-embedding-3-small"  # 默认嵌入模型
                response = await self.api_wrapper.embeddings.create(
                    model=model,
                    input=memory_content
                )
                # 提取嵌入向量
                embedding = response.data[0].embedding
            
            # 保存嵌入向量
            self.embedding_data[key] = embedding
            self.embedding_count = len(self.embedding_data)
            
            # 保存
            self.save()
            logger.info(f"成功为记忆 {key[:30]}... 添加嵌入向量")
            return True
        except Exception as e:
            logger.error(f"为记忆添加嵌入向量失败: {str(e)}")
            return False
            
    @memory_cache
    async def update_embedding_for_all(self, batch_size: int = 5):
        """
        为所有没有嵌入向量的记忆添加嵌入向量
        
        Args:
            batch_size: 每批处理的记忆数量
        """
        try:
            # 找出所有没有嵌入向量的记忆
            missing_embeddings = [
                key for key in self.memory_data.keys() 
                if key not in self.embedding_data
            ]
            
            total = len(missing_embeddings)
            if total == 0:
                logger.info("所有记忆都已有嵌入向量")
                return
                
            logger.info(f"开始为 {total} 条记忆添加嵌入向量")
            
            # 分批处理
            for i in range(0, total, batch_size):
                batch = missing_embeddings[i:i+batch_size]
                
                # 并行处理当前批次
                tasks = [self.add_embedding(key) for key in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 统计成功数
                success_count = sum(1 for r in results if r is True)
                logger.info(f"已处理 {i+len(batch)}/{total} 条记忆，当前批次成功: {success_count}/{len(batch)}")
                
                # 保存当前进度
                if success_count > 0:
                    self.save()
                    
                # 暂停一下，避免API限制
                await asyncio.sleep(1)
                
            logger.info(f"嵌入向量更新完成，共成功添加 {self.embedding_count - (total - len(missing_embeddings))} 条向量")
        except Exception as e:
            logger.error(f"批量更新嵌入向量失败: {str(e)}")
            
    @memory_cache
    async def generate_summary(self, limit: int = 20) -> str:
        """
        生成记忆摘要
        
        Args:
            limit: 考虑的记忆条数
            
        Returns:
            str: 记忆摘要
        """
        try:
            if not self.memory_data:
                return "没有记忆可供摘要"
                
            # 获取最新的记忆
            memories = list(self.memory_data.items())
            recent_memories = memories[-limit:] if len(memories) > limit else memories
            
            # 格式化摘要
            summary = f"最近 {len(recent_memories)} 条记忆摘要:\n\n"
            for i, (key, value) in enumerate(recent_memories, 1):
                summary += f"{i}. 用户: {key[:50]}...\n   回复: {value[:50]}...\n\n"
                
            return summary
        except Exception as e:
            logger.error(f"生成记忆摘要失败: {str(e)}")
            return "生成记忆摘要时出错"
    
    def get_config(self) -> Dict:
        """
        获取配置信息
        
        Returns:
            Dict: 配置信息
        """
        return {
            "memory_count": self.memory_count,
            "embedding_count": self.embedding_count,
            "memory_path": self.memory_path
        }
    
    def set_use_local_embedding(self, value: bool):
        """
        设置是否使用本地嵌入模型
        
        Args:
            value: 是否使用本地模型
        """
        # 这里需要根据实际情况实现
        logger.warning("设置本地嵌入模型功能未实现") 
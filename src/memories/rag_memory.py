"""
RAG记忆模块 - 提供基于检索增强生成的记忆系统
"""
import os
import logging
import json
import time
from typing import Dict, List, Any, Optional, Tuple, Callable

# 引入内部模块
from src.memories.embedding_handler import EmbeddingHandler
from src.memories.memory_utils import get_memory_path

# 设置日志
logger = logging.getLogger('main')

class RAGMemory:
    """基于检索增强生成(RAG)的记忆系统"""
    
    def __init__(self, root_dir: str, embedding_handler: EmbeddingHandler = None):
        """
        初始化RAG记忆系统
        
        Args:
            root_dir: 根目录路径
            embedding_handler: 嵌入处理器
        """
        self.root_dir = root_dir
        self.embedding_handler = embedding_handler
        
        # 基本数据结构
        self.memory_data = {}  # 记忆数据: {key: value}
        self.embedding_data = {}  # 嵌入向量数据: {key: [vector]}
        self.hooks = []  # 钩子函数列表
        
        # 配置信息
        self.config = {
            "max_memories": 1000,  # 最大记忆条数
            "similarity_threshold": 0.75,  # 相似度阈值
            "auto_save": True  # 自动保存
        }
        
        # 记忆文件路径
        self.memory_path = get_memory_path(root_dir)
        self.config_path = os.path.join(os.path.dirname(self.memory_path), "rag-config.json")
        
        # 加载数据
        self._load_config()
        self._load_memories()
        
        logger.info(f"RAG记忆系统初始化完成，当前记忆数量: {len(self.memory_data)}")
        
    def _load_config(self):
        """加载配置信息"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                logger.info(f"从 {self.config_path} 加载配置完成")
            else:
                logger.info(f"配置文件 {self.config_path} 不存在，使用默认配置")
                self.save_config()
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")
            
    def _load_memories(self):
        """加载记忆数据"""
        try:
            if os.path.exists(self.memory_path):
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.memory_data = data.get("memories", {})
                    self.embedding_data = data.get("embeddings", {})
                logger.info(f"从 {self.memory_path} 加载了 {len(self.memory_data)} 条记忆")
            else:
                logger.info(f"记忆文件 {self.memory_path} 不存在，将创建新文件")
                self.save_memories()
        except Exception as e:
            logger.error(f"加载记忆数据失败: {str(e)}")
            # 重置数据
            self.memory_data = {}
            self.embedding_data = {}
            
    def save_config(self):
        """保存配置信息"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # 保存配置
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
                
            logger.info(f"配置已保存到 {self.config_path}")
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")
            
    def save_memories(self):
        """保存记忆数据"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
            
            # 保存数据
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump({
                    "memories": self.memory_data,
                    "embeddings": self.embedding_data
                }, f, ensure_ascii=False, indent=2)
                
            logger.info(f"记忆数据已保存到 {self.memory_path}")
        except Exception as e:
            logger.error(f"保存记忆数据失败: {str(e)}")
            
    def set(self, key: str, value: str) -> bool:
        """
        设置记忆
        
        Args:
            key: 记忆键
            value: 记忆值
            
        Returns:
            bool: 是否成功设置
        """
        try:
            # 添加到记忆
            self.memory_data[key] = value
            
            # 如果超过最大记忆数，删除最旧的
            if len(self.memory_data) > self.config["max_memories"]:
                oldest_key = next(iter(self.memory_data))
                del self.memory_data[oldest_key]
                if oldest_key in self.embedding_data:
                    del self.embedding_data[oldest_key]
                logger.debug(f"记忆数量超过限制，删除最旧记忆: {oldest_key}")
                
            # 执行钩子函数
            for hook in self.hooks:
                hook(key, value)
                
            # 如果设置了自动保存，则保存数据
            if self.config["auto_save"]:
                self.save_memories()
                
            return True
        except Exception as e:
            logger.error(f"设置记忆失败: {str(e)}")
            return False
            
    def get(self, key: str) -> Optional[str]:
        """
        获取记忆
        
        Args:
            key: 记忆键
            
        Returns:
            Optional[str]: 记忆值，如不存在则返回None
        """
        return self.memory_data.get(key)
        
    def get_all(self) -> Dict[str, str]:
        """
        获取所有记忆
        
        Returns:
            Dict[str, str]: 所有记忆
        """
        return self.memory_data.copy()
        
    def clear(self):
        """清空所有记忆"""
        self.memory_data = {}
        self.embedding_data = {}
        
        # 保存空数据
        self.save_memories()
        logger.info("已清空所有记忆")
        
    async def add_embedding(self, key: str) -> bool:
        """
        为记忆添加嵌入向量
        
        Args:
            key: 记忆键
            
        Returns:
            bool: 是否成功添加
        """
        try:
            # 检查嵌入处理器
            if not self.embedding_handler:
                logger.warning("嵌入处理器未初始化，无法添加嵌入向量")
                return False
                
            # 检查记忆是否存在
            if key not in self.memory_data:
                logger.warning(f"记忆 {key} 不存在，无法添加嵌入向量")
                return False
                
            # 获取记忆内容
            memory_content = f"{key} {self.memory_data[key]}"
            
            # 生成嵌入向量
            embedding = await self.embedding_handler.get_embedding(memory_content)
            
            # 保存嵌入向量
            self.embedding_data[key] = embedding
            
            # 如果设置了自动保存，则保存数据
            if self.config["auto_save"]:
                self.save_memories()
                
            return True
        except Exception as e:
            logger.error(f"为记忆添加嵌入向量失败: {str(e)}")
            return False
            
    async def search(self, query: str, top_k: int = 5) -> List[Tuple[str, str, float]]:
        """
        搜索相关记忆
        
        Args:
            query: 查询文本
            top_k: 返回的记忆条数
            
        Returns:
            List[Tuple[str, str, float]]: 记忆列表，每项为(键, 值, 相似度)
        """
        try:
            # 检查嵌入处理器
            if not self.embedding_handler:
                logger.warning("嵌入处理器未初始化，无法进行向量搜索")
                return []
                
            # 如果没有记忆或嵌入向量，返回空列表
            if not self.memory_data or not self.embedding_data:
                return []
                
            # 获取查询文本的嵌入向量
            query_embedding = await self.embedding_handler.get_embedding(query)
            
            # 计算相似度并排序
            results = []
            for key, embedding in self.embedding_data.items():
                if key in self.memory_data:
                    similarity = self.embedding_handler.compute_similarity(query_embedding, embedding)
                    if similarity >= self.config["similarity_threshold"]:
                        results.append((key, self.memory_data[key], similarity))
                        
            # 按相似度排序
            results.sort(key=lambda x: x[2], reverse=True)
            
            # 返回前top_k个结果
            return results[:top_k]
        except Exception as e:
            logger.error(f"搜索相关记忆失败: {str(e)}")
            return []
            
    def add_memory_hook(self, hook: Callable[[str, str], None]):
        """
        添加记忆钩子
        
        Args:
            hook: 钩子函数，接收记忆键和值作为参数
        """
        self.hooks.append(hook)
        logger.debug(f"已添加记忆钩子函数: {hook.__name__}")
        
    def remove_memory_hook(self, hook: Callable[[str, str], None]):
        """
        移除记忆钩子
        
        Args:
            hook: 要移除的钩子函数
        """
        if hook in self.hooks:
            self.hooks.remove(hook)
            logger.debug(f"已移除记忆钩子函数: {hook.__name__}")
        else:
            logger.warning(f"钩子函数 {hook.__name__} 不存在，无法移除") 
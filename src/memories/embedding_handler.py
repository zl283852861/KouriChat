"""
嵌入向量处理模块 - 提供向量嵌入和相似度计算功能
"""
import os
import logging
import json
import traceback
import time
import numpy as np
from typing import List, Dict, Any, Tuple, Optional, Union, Callable

# 引入内部模块
from src.memories.memory_utils import (
    memory_cache, EMBEDDING_MODEL, EMBEDDING_FALLBACK_MODEL, LOCAL_EMBEDDING_MODEL_PATH
)
from src.api_client.wrapper import APIWrapper  # 用于API调用的包装器
from src.utils.logger import get_logger
from src.config import config

# 设置日志
logger = logging.getLogger('main')

class EmbeddingHandler:
    """嵌入向量处理器，提供向量嵌入和相似度计算功能"""
    
    def __init__(self, api_wrapper: Optional[APIWrapper] = None):
        """
        初始化嵌入处理器
        
        Args:
            api_wrapper: API调用封装器
        """
        self.api_wrapper = api_wrapper
        self._local_model = None
        self.model = EMBEDDING_MODEL
        self.use_local_model = False
        
        logger.info(f"初始化嵌入处理器，默认模型: {self.model}")
        
        # 尝试初始化本地模型（如果需要）
        try:
            # 当需要本地模型时再进行加载，避免启动时资源占用
            pass
        except Exception as e:
            logger.warning(f"初始化本地嵌入模型失败: {str(e)}")
            
    @property
    def use_local_model(self) -> bool:
        """是否使用本地模型"""
        return self._use_local_model
        
    @use_local_model.setter
    def use_local_model(self, value: bool):
        """设置是否使用本地模型"""
        if value and self._local_model is None:
            self._init_local_model()
        self._use_local_model = value
            
    def _init_local_model(self):
        """初始化本地嵌入模型"""
        try:
            from sentence_transformers import SentenceTransformer
            
            # 检查模型本地路径
            if os.path.exists(LOCAL_EMBEDDING_MODEL_PATH):
                self._local_model = SentenceTransformer(LOCAL_EMBEDDING_MODEL_PATH)
                logger.info(f"已从本地路径加载嵌入模型: {LOCAL_EMBEDDING_MODEL_PATH}")
            else:
                # 如果本地没有，尝试从Hugging Face下载
                logger.info(f"正在从HuggingFace下载嵌入模型: {LOCAL_EMBEDDING_MODEL_PATH}")
                self._local_model = SentenceTransformer(LOCAL_EMBEDDING_MODEL_PATH)
                logger.info(f"成功下载并加载嵌入模型: {LOCAL_EMBEDDING_MODEL_PATH}")
                
            logger.info("本地嵌入模型初始化成功")
        except Exception as e:
            logger.error(f"初始化本地嵌入模型失败: {str(e)}")
            logger.error(traceback.format_exc())
            self._local_model = None
            self._use_local_model = False
            raise

    @memory_cache
    async def get_embedding(self, text: str) -> List[float]:
        """
        获取文本的嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            List[float]: 嵌入向量
        """
        try:
            if self._use_local_model:
                return await self._get_local_embedding(text)
            else:
                return await self._get_api_embedding(text)
        except Exception as e:
            logger.error(f"获取嵌入向量失败: {str(e)}")
            # 返回空向量作为回退方案
            return [0.0] * 768  # 默认维度
            
    async def _get_api_embedding(self, text: str) -> List[float]:
        """
        使用API获取嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            List[float]: 嵌入向量
        """
        if not self.api_wrapper:
            logger.error("未提供API包装器，无法获取嵌入向量")
            return [0.0] * 768
        
        try:
            # 使用主要模型
            response = await self.api_wrapper.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"主要嵌入模型 {self.model} 失败，尝试备用模型: {str(e)}")
            
            try:
                # 使用备用模型
                response = await self.api_wrapper.embeddings.create(
                    model=EMBEDDING_FALLBACK_MODEL,
                    input=text
                )
                return response.data[0].embedding
            except Exception as e2:
                logger.error(f"备用嵌入模型也失败: {str(e2)}")
                raise
                
    async def _get_local_embedding(self, text: str) -> List[float]:
        """
        使用本地模型获取嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            List[float]: 嵌入向量
        """
        # 这里需要实现本地模型的嵌入向量生成
        # 例如使用sentence-transformers等库
        logger.warning("本地嵌入模型功能尚未实现")
        return [0.0] * 768
        
    def compute_similarity(self, vector1: List[float], vector2: List[float]) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            vector1: 第一个向量
            vector2: 第二个向量
            
        Returns:
            float: 余弦相似度，范围为[-1, 1]
        """
        try:
            # 转换为numpy数组
            v1 = np.array(vector1)
            v2 = np.array(vector2)
            
            # 计算余弦相似度
            dot_product = np.dot(v1, v2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            
            # 避免除零错误
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return dot_product / (norm1 * norm2)
        except Exception as e:
            logger.error(f"计算相似度失败: {str(e)}")
            return 0.0

    @staticmethod
    def cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            vector_a: 第一个向量
            vector_b: 第二个向量
            
        Returns:
            float: 余弦相似度 (-1到1之间，1表示完全相同，-1表示完全相反)
        """
        if not vector_a or not vector_b:
            return 0.0
            
        # 转换为numpy数组
        a = np.array(vector_a)
        b = np.array(vector_b)
        
        # 检查是否为零向量
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        # 计算余弦相似度
        return np.dot(a, b) / (norm_a * norm_b)
        
    @staticmethod
    def find_most_similar(
        query_embedding: List[float], 
        embedding_dict: Dict[str, List[float]], 
        top_k: int = 5,
        threshold: float = 0.75
    ) -> List[Tuple[str, float]]:
        """
        在嵌入字典中查找与查询嵌入最相似的项
        
        Args:
            query_embedding: 查询嵌入向量
            embedding_dict: 键为文档ID，值为嵌入向量的字典
            top_k: 返回的最相似项数量
            threshold: 相似度阈值，低于该值的结果将被过滤
            
        Returns:
            List[Tuple[str, float]]: 包含(文档ID, 相似度)的元组列表，按相似度降序排序
        """
        if not query_embedding or not embedding_dict:
            return []
            
        # 计算所有嵌入与查询嵌入的相似度
        similarities = []
        for doc_id, embedding in embedding_dict.items():
            similarity = EmbeddingHandler.cosine_similarity(query_embedding, embedding)
            similarities.append((doc_id, similarity))
            
        # 按相似度降序排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # 过滤低于阈值的结果
        filtered_similarities = [(doc_id, sim) for doc_id, sim in similarities if sim >= threshold]
        
        # 返回top_k个结果
        return filtered_similarities[:top_k] 
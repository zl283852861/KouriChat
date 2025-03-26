"""
RAG管理模块
负责向量存储和语义搜索功能，整合原先的messages/rag_manager.py和memories/core/rag.py
"""

import logging
import asyncio
import os
import yaml
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union

# 获取logger
logger = logging.getLogger('main')

# 尝试导入APIWrapper
try:
    from src.api_client.wrapper import APIWrapper
except ImportError:
    logger.error("无法导入APIWrapper，嵌入功能将不可用")
    
    # 定义一个空的APIWrapper类，避免未定义错误
    class APIWrapper:
        def __init__(self, api_key=None, base_url=None):
            self.api_key = api_key
            self.base_url = base_url
            logger.warning("使用了空的APIWrapper类，实际功能将不可用")

class RAGManager:
    """RAG管理器，负责向量存储和语义搜索"""
    
    def __init__(self, message_manager=None, rag_manager=None, config=None):
        """
        初始化RAG管理器
        
        Args:
            message_manager: 消息管理器实例的引用
            rag_manager: 底层RAG系统对象实例，如果提供则使用现有实例
            config: 配置信息字典
        """
        self.message_manager = message_manager
        self.config = config or {}
        self.rag_manager = rag_manager
        
        # 如果未提供rag_manager，则创建一个新的
        if not self.rag_manager:
            # 尝试从配置中获取API包装器
            api_wrapper = self._get_api_wrapper()
            
            # 尝试加载或创建RAG管理器
            self.rag_manager = self._create_rag_manager(api_wrapper)
    
    def _get_api_wrapper(self):
        """获取API包装器"""
        try:
            # 尝试从消息管理器获取API处理器
            if self.message_manager:
                api_handler = self.message_manager.get_module('api_handler')
                if api_handler and hasattr(api_handler, 'api_wrapper'):
                    return api_handler.api_wrapper
            
            # 否则尝试从配置文件创建
            from src.config import config
            
            # 创建API包装器
            api_wrapper = APIWrapper(
                api_key=config.llm.api_key,
                base_url=config.llm.base_url
            )
            
            return api_wrapper
        except Exception as e:
            logger.error(f"获取API包装器失败: {str(e)}")
            return None
    
    def _create_rag_manager(self, api_wrapper):
        """创建RAG管理器"""
        try:
            # 尝试导入核心RAG模块
            from src.handlers.memories.core.rag import RagManager
            
            # 获取配置文件路径
            config_path = None
            try:
                # 尝试获取系统根目录
                if self.message_manager and hasattr(self.message_manager, 'config'):
                    root_dir = self.message_manager.config.get('root_dir')
                    if root_dir:
                        config_path = os.path.join(root_dir, 'src', 'config', 'rag_config.yaml')
            except Exception as e:
                logger.error(f"获取配置文件路径失败: {str(e)}")
            
            # 创建RAG管理器
            rag_manager = RagManager(
                config_path=config_path,
                api_wrapper=api_wrapper,
                config_dict=self.config.get('rag', {})
            )
            
            logger.info("成功创建RAG管理器")
            return rag_manager
        except Exception as e:
            logger.error(f"创建RAG管理器失败: {str(e)}")
            return None
    
    async def initialize(self):
        """初始化RAG管理器"""
        try:
            logger.info("初始化RAG管理器...")
            
            # 没有特殊的初始化步骤，确保rag_manager存在即可
            if not self.rag_manager:
                # 创建API包装器
                api_wrapper = self._get_api_wrapper()
                
                # 创建RAG管理器
                self.rag_manager = self._create_rag_manager(api_wrapper)
            
            if not self.rag_manager:
                logger.error("RAG管理器初始化失败：无法创建底层RAG系统")
                return False
            
            logger.info("RAG管理器初始化完成")
            return True
        except Exception as e:
            logger.error(f"初始化RAG管理器失败: {str(e)}")
            return False
    
    async def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        执行语义搜索查询
        
        Args:
            query_text: 查询文本
            top_k: 返回结果数量
            
        Returns:
            List[Dict]: 查询结果列表，包含相似度分数和元数据
        """
        if not self.rag_manager:
            logger.warning("RAG管理器未初始化，无法执行查询")
            return []
            
        try:
            # 调用底层RAG系统执行查询
            results = await self.rag_manager.query(query_text, top_k)
            
            # 处理结果
            processed_results = []
            
            for i, result in enumerate(results):
                # 提取元数据
                metadata = result.get("metadata", {})
                score = result.get("score", 0.0)
                
                # 记录日志
                logger.debug(f"RAG查询结果 #{i+1}: 分数={score:.4f}, 类型={metadata.get('type', 'unknown')}")
                
                # 添加到结果集
                processed_results.append({
                    "score": score,
                    "metadata": metadata,
                    "text": result.get("text", ""),
                    "id": result.get("id", "")
                })
            
            return processed_results
            
        except Exception as e:
            logger.error(f"执行RAG查询失败: {str(e)}")
            return []
    
    async def store_message(self, message_data: Dict[str, Any]) -> bool:
        """
        将消息存储到向量数据库
        
        Args:
            message_data: 消息数据，包含消息内容和元数据
            
        Returns:
            bool: 是否成功存储
        """
        if not self.rag_manager:
            logger.warning("RAG管理器未初始化，无法存储消息")
            return False
            
        try:
            # 从消息数据中提取必要字段
            content = message_data.get("content", "")
            metadata = message_data.get("metadata", {})
            
            # 检查是否有必要的字段
            if not content:
                logger.warning("消息内容为空，跳过存储")
                return False
            
            # 调用底层RAG系统存储消息
            result = await self.rag_manager.add_document({
                "text": content,
                "metadata": metadata
            })
            
            return result
            
        except Exception as e:
            logger.error(f"存储消息到向量数据库失败: {str(e)}")
            return False
    
    async def batch_store_messages(self, message_list: List[Dict[str, Any]]) -> int:
        """
        批量存储消息到向量数据库
        
        Args:
            message_list: 消息列表
            
        Returns:
            int: 成功存储的消息数量
        """
        if not self.rag_manager:
            logger.warning("RAG管理器未初始化，无法批量存储消息")
            return 0
            
        if not message_list:
            logger.warning("消息列表为空，跳过批量存储")
            return 0
            
        try:
            success_count = 0
            for message_data in message_list:
                # 从消息数据中提取必要字段
                content = message_data.get("content", "")
                metadata = message_data.get("metadata", {})
                
                # 检查是否有必要的字段
                if not content:
                    logger.warning("消息内容为空，跳过存储")
                    continue
                
                # 调用底层RAG系统存储消息
                result = await self.rag_manager.add_document({
                    "text": content,
                    "metadata": metadata
                })
                
                if result:
                    success_count += 1
            
            logger.info(f"批量存储完成: {success_count}/{len(message_list)} 条消息成功存储")
            return success_count
            
        except Exception as e:
            logger.error(f"批量存储消息到向量数据库失败: {str(e)}")
            return 0
    
    async def delete_by_ids(self, ids: List[str]) -> int:
        """
        通过ID列表删除向量数据库中的记录
        
        Args:
            ids: 记录ID列表
            
        Returns:
            int: 成功删除的记录数量
        """
        if not self.rag_manager:
            logger.warning("RAG管理器未初始化，无法删除记录")
            return 0
            
        if not ids:
            logger.warning("ID列表为空，跳过删除")
            return 0
            
        try:
            # 调用底层RAG系统的删除方法
            result = await self.rag_manager.delete_by_ids(ids)
            
            logger.info(f"成功删除 {result} 条记录")
            return result
                
        except Exception as e:
            logger.error(f"删除向量数据库记录失败: {str(e)}")
            return 0
    
    async def delete_by_filter(self, filter_dict: Dict[str, Any]) -> int:
        """
        通过过滤条件删除向量数据库中的记录
        
        Args:
            filter_dict: 过滤条件字典，键为元数据字段，值为匹配值
            
        Returns:
            int: 成功删除的记录数量
        """
        if not self.rag_manager:
            logger.warning("RAG管理器未初始化，无法通过过滤条件删除记录")
            return 0
            
        if not filter_dict:
            logger.warning("过滤条件为空，跳过删除")
            return 0
            
        try:
            # 这个功能依赖于底层RAG实现
            if hasattr(self.rag_manager, 'delete_by_filter'):
                result = await self.rag_manager.delete_by_filter(filter_dict)
                logger.info(f"通过过滤条件成功删除 {result} 条记录")
                return result
            else:
                logger.warning("底层RAG系统不支持通过过滤条件删除记录")
                return 0
                
        except Exception as e:
            logger.error(f"通过过滤条件删除向量数据库记录失败: {str(e)}")
            return 0
    
    async def get_document_count(self) -> int:
        """
        获取向量数据库中的文档数量
        
        Returns:
            int: 文档数量
        """
        if not self.rag_manager:
            logger.warning("RAG管理器未初始化，无法获取文档数量")
            return 0
            
        try:
            if hasattr(self.rag_manager, 'get_document_count'):
                count = self.rag_manager.get_document_count()
                return count
            else:
                # 尝试访问document_count属性
                return getattr(self.rag_manager, 'document_count', 0)
                
        except Exception as e:
            logger.error(f"获取文档数量失败: {str(e)}")
            return 0
    
    async def get_latest_documents(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取最新的文档
        
        Args:
            limit: 返回结果数量限制
            
        Returns:
            List[Dict]: 文档列表
        """
        if not self.rag_manager:
            logger.warning("RAG管理器未初始化，无法获取最新文档")
            return []
            
        try:
            if hasattr(self.rag_manager, 'get_latest_documents'):
                documents = self.rag_manager.get_latest_documents(limit)
                return documents
            else:
                logger.warning("底层RAG系统不支持获取最新文档")
                return []
                
        except Exception as e:
            logger.error(f"获取最新文档失败: {str(e)}")
            return []
    
    async def clear_storage(self) -> bool:
        """
        清空向量存储
        
        Returns:
            bool: 是否成功清空
        """
        if not self.rag_manager:
            logger.warning("RAG管理器未初始化，无法清空存储")
            return False
            
        try:
            if hasattr(self.rag_manager, 'clear_storage'):
                result = self.rag_manager.clear_storage()
                return result
            else:
                logger.warning("底层RAG系统不支持清空存储")
                return False
                
        except Exception as e:
            logger.error(f"清空存储失败: {str(e)}")
            return False
            
    def get_api_wrapper(self):
        """获取API包装器"""
        if hasattr(self.rag_manager, 'api_wrapper'):
            return self.rag_manager.api_wrapper
        return None 
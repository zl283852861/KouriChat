"""
记忆操作模块 - 提供高级记忆操作和处理功能
"""
import os
import logging
import time
from typing import Dict, List, Any, Optional, Tuple

# 引入内部模块
from src.memories.rag_memory import RAGMemory
from src.memories.memory_utils import memory_cache, get_importance_keywords

# 设置日志
logger = logging.getLogger('main')

class MemoryOperations:
    """提供高级记忆操作和处理功能的类"""
    
    def __init__(self, memory_system: RAGMemory):
        """
        初始化记忆操作
        
        Args:
            memory_system: RAG记忆系统实例
        """
        self.memory_system = memory_system
        logger.info("记忆操作模块初始化完成")
        
    @memory_cache
    async def remember_conversation(self, user_message: str, assistant_response: str) -> bool:
        """
        记住对话内容
        
        Args:
            user_message: 用户消息
            assistant_response: 助手回复
            
        Returns:
            bool: 是否成功记住
        """
        try:
            # 添加到记忆系统
            key = f"USER: {user_message}"
            value = f"ASSISTANT: {assistant_response}"
            
            # 使用记忆系统的set方法
            return self.memory_system.set(key, value)
        except Exception as e:
            logger.error(f"记住对话内容失败: {str(e)}")
            return False
            
    @memory_cache
    async def retrieve_memories(self, query: str, top_k: int = 5) -> str:
        """
        检索相关记忆
        
        Args:
            query: 查询文本
            top_k: 返回的记忆条数
            
        Returns:
            str: 格式化的记忆内容
        """
        try:
            # 执行语义搜索
            results = await self.memory_system.search(query, top_k)
            
            if not results:
                return "没有找到相关记忆。"
                
            # 格式化结果
            formatted = "找到以下相关记忆：\n\n"
            
            for i, (key, value, similarity) in enumerate(results, 1):
                # 提取用户和助手的内容
                user_content = key.replace("USER: ", "")
                assistant_content = value.replace("ASSISTANT: ", "")
                
                # 添加到格式化结果
                formatted += f"{i}. 用户: {user_content}\n"
                formatted += f"   助手: {assistant_content}\n"
                formatted += f"   (相似度: {similarity:.2f})\n\n"
                
            return formatted
        except Exception as e:
            logger.error(f"检索记忆失败: {str(e)}")
            return "检索记忆时出错。"
            
    @memory_cache
    async def check_important_memory(self, text: str) -> bool:
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
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    logger.info(f"文本包含重要关键词 '{keyword}'，标记为重要记忆")
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"检查重要记忆失败: {str(e)}")
            return False
            
    @memory_cache
    async def generate_memory_summary(self, limit: int = 20) -> str:
        """
        生成记忆摘要
        
        Args:
            limit: 考虑的记忆条数
            
        Returns:
            str: 记忆摘要
        """
        try:
            # 获取所有记忆
            memories = self.memory_system.get_all()
            
            if not memories:
                return "无记忆数据可供摘要。"
                
            # 获取最新的记忆
            recent_items = list(memories.items())[-limit:]
            
            # 生成摘要
            summary = f"最近 {len(recent_items)} 条记忆摘要：\n\n"
            
            for i, (key, value) in enumerate(recent_items, 1):
                # 提取用户和助手的内容
                user_content = key.replace("USER: ", "")
                assistant_content = value.replace("ASSISTANT: ", "")
                
                # 截断长内容
                if len(user_content) > 50:
                    user_content = user_content[:50] + "..."
                if len(assistant_content) > 50:
                    assistant_content = assistant_content[:50] + "..."
                    
                # 添加到摘要
                summary += f"{i}. 用户: {user_content}\n"
                summary += f"   助手: {assistant_content}\n\n"
                
            return summary
        except Exception as e:
            logger.error(f"生成记忆摘要失败: {str(e)}")
            return "生成记忆摘要时出错。"
            
    async def find_similar_conversations(self, content: str, threshold: float = 0.7, limit: int = 3) -> List[Tuple[str, str, float]]:
        """
        查找与给定内容相似的对话
        
        Args:
            content: 查询内容
            threshold: 相似度阈值
            limit: 返回结果数量限制
            
        Returns:
            List[Tuple[str, str, float]]: 相似对话列表，每项为(用户内容, 助手回复, 相似度)
        """
        try:
            # 使用记忆系统的搜索功能
            results = await self.memory_system.search(content, limit)
            
            # 过滤结果
            filtered_results = [(key.replace("USER: ", ""), 
                               value.replace("ASSISTANT: ", ""), 
                               similarity)
                              for key, value, similarity in results
                              if similarity >= threshold]
                              
            return filtered_results
        except Exception as e:
            logger.error(f"查找相似对话失败: {str(e)}")
            return [] 
"""
RAG核心模块 - 提供记忆检索增强生成功能
实现与嵌入、检索、重排序相关的底层功能
"""
import os
import yaml
import json
import logging
import asyncio
import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from datetime import datetime

# 设置日志
logger = logging.getLogger('main')

class RagManager:
    """
    RAG管理器 - 管理检索增强生成相关功能
    """
    
    def __init__(self, config_path: str, api_wrapper = None, storage_dir = None):
        """
        初始化RAG管理器
        
        Args:
            config_path: 配置文件路径
            api_wrapper: API调用包装器
            storage_dir: 存储目录，如果提供则覆盖默认存储路径
        """
        self.config_path = config_path
        self.api_wrapper = api_wrapper
        self.storage_dir = storage_dir
        
        # 加载配置
        self.config = self._load_config()
        
        # 获取当前角色名
        try:
            from src.config import config
            self.avatar_name = config.behavior.context.avatar_dir
        except Exception as e:
            logger.error(f"获取角色名失败: {str(e)}")
            self.avatar_name = "default"
        
        # 初始化组件
        self.embedding_model = self._init_embedding_model()
        self.storage = self._init_storage()
        self.reranker = self._init_reranker() if self.config.get("is_rerank", False) else None
        
        # 记录状态
        self.document_count = 0
        
        logger.info(f"RAG管理器初始化完成，角色: {self.avatar_name}，使用嵌入模型: {self.config.get('embedding_model', {}).get('name', 'default')}")
        
    def _load_config(self) -> Dict:
        """
        加载配置文件
        
        Returns:
            Dict: 配置字典
        """
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
                return self._create_default_config()
                
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                
            logger.info(f"已加载RAG配置: {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}，使用默认配置")
            return self._create_default_config()
            
    def _create_default_config(self) -> Dict:
        """
        创建默认配置
        
        Returns:
            Dict: 默认配置字典
        """
        default_config = {
            "api_key": "",
            "base_url": "",
            "embedding_model": {
                "type": "openai",
                "name": "text-embedding-3-large",
                "dimensions": 1536
            },
            "storage": {
                "type": "json",
                "path": "./data/rag_storage.json"
            },
            "top_k": 5,
            "is_rerank": False,
            "reranker": {
                "type": "api",
                "name": "rerank-large"
            },
            "local_model": {
                "enabled": False,
                "path": "./models/embedding_model"
            }
        }
        
        return default_config
        
    def _init_embedding_model(self):
        """
        初始化嵌入模型
        
        Returns:
            嵌入模型实例
        """
        model_config = self.config.get("embedding_model", {})
        model_type = model_config.get("type", "openai")
        model_name = model_config.get("name", "text-embedding-3-large")
        
        # 检查是否启用本地模型
        local_model_config = self.config.get("local_model", {})
        use_local_model = local_model_config.get("enabled", False)
        local_model_path = local_model_config.get("path", "")
        
        if use_local_model and os.path.exists(local_model_path):
            try:
                logger.info(f"尝试加载本地嵌入模型: {local_model_path}")
                # 这里可以实现本地模型的加载逻辑
                # 为了降低内存占用，本地模型加载可以懒加载或使用更轻量的实现
                return LocalEmbeddingModel(local_model_path)
            except Exception as e:
                logger.error(f"加载本地嵌入模型失败: {str(e)}，将使用API模型")
        
        # 如果api_wrapper为None，尝试初始化一个
        if self.api_wrapper is None:
            try:
                # # 导入APIWrapper
                # try:
                #     from src.utils.api_wrapper import APIWrapper
                # except ImportError:
                #     logger.error("无法导入APIWrapper，嵌入功能将不可用")
                #     return ApiEmbeddingModel(None, model_name, model_type)
                
                # 尝试从配置文件获取RAG专用的API密钥和URL
                try:
                    from src.config import config
                    
                    # 使用字典方式访问配置
                    categories = getattr(config, 'categories', {})
                    rag_settings = {}
                    
                    # 尝试不同的访问方式
                    if isinstance(categories, dict) and 'rag_settings' in categories:
                        rag_settings = categories['rag_settings'].get('settings', {})
                    elif hasattr(categories, 'rag_settings'):
                        rag_settings = getattr(categories.rag_settings, 'settings', {})
                    
                    # 读取API密钥
                    api_key = None
                    if isinstance(rag_settings, dict) and 'api_key' in rag_settings:
                        api_key = rag_settings['api_key'].get('value', '')
                    elif hasattr(rag_settings, 'api_key'):
                        api_key = getattr(rag_settings.api_key, 'value', '')
                    
                    # 读取base_url
                    base_url = None
                    if isinstance(rag_settings, dict) and 'base_url' in rag_settings:
                        base_url = rag_settings['base_url'].get('value', '')
                    elif hasattr(rag_settings, 'base_url'):
                        base_url = getattr(rag_settings.base_url, 'value', '')
                    
                    # 如果找到了API密钥，创建API包装器
                    if api_key:
                        self.api_wrapper = APIWrapper(
                            api_key=api_key,
                            base_url=base_url if base_url else None
                        )
                        logger.info("成功从配置文件创建RAG专用API包装器")
                except Exception as config_error:
                    logger.error(f"从配置文件获取RAG API设置失败: {str(config_error)}")
                    
            except Exception as e:
                logger.error(f"初始化API包装器失败: {str(e)}")
        
        # 使用API模型
        logger.info(f"使用API嵌入模型: {model_name}")
        return ApiEmbeddingModel(self.api_wrapper, model_name, model_type)
    
    def _init_storage(self):
        """
        初始化存储系统
        
        Returns:
            存储系统实例
        """
        storage_config = self.config.get("storage", {})
        storage_type = storage_config.get("type", "json")
        
        # 如果提供了storage_dir，使用该目录
        if self.storage_dir:
            # 使用提供的存储目录，文件名固定为rag_storage.json，确保与私聊一致
            storage_filename = "rag_storage.json"
            avatar_storage_path = os.path.join(self.storage_dir, storage_filename)
            
            # 确保路径有效
            os.makedirs(self.storage_dir, exist_ok=True)
            
            logger.info(f"初始化RAG存储: {storage_type}, 使用自定义路径: {avatar_storage_path}")
            return JsonStorage(avatar_storage_path)
        
        # 否则使用角色专属的存储路径，确保与memory.json在同一文件夹
        base_storage_path = storage_config.get("path", "./data/rag_storage.json")
        storage_filename = os.path.basename(base_storage_path)
        
        # 角色记忆目录为 data/avatars/角色名/
        avatar_storage_dir = os.path.join("data", "avatars", self.avatar_name)
        avatar_storage_path = os.path.join(avatar_storage_dir, storage_filename)
        
        # 确保路径有效
        os.makedirs(avatar_storage_dir, exist_ok=True)
        
        logger.info(f"初始化RAG存储: {storage_type}, 路径: {avatar_storage_path}")
        return JsonStorage(avatar_storage_path)
    
    def _init_reranker(self):
        """
        初始化重排序器
        
        Returns:
            重排序器实例
        """
        if not self.config.get("is_rerank", False):
            return None
            
        reranker_config = self.config.get("reranker", {})
        reranker_type = reranker_config.get("type", "api")
        reranker_name = reranker_config.get("name", "rerank-large")
        
        logger.info(f"初始化重排序器: {reranker_type}, 模型: {reranker_name}")
        
        # 使用API重排序器
        return ApiReranker(self.api_wrapper, reranker_name)
    
    def _ensure_valid_path(self, path: str) -> str:
        """
        确保路径有效（处理相对路径等）
        
        Args:
            path: 原始路径
            
        Returns:
            str: 有效的绝对路径
        """
        # 如果是相对路径，转换为绝对路径
        if not os.path.isabs(path):
            # 相对于配置文件的路径
            config_dir = os.path.dirname(os.path.abspath(self.config_path))
            abs_path = os.path.join(config_dir, path)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            
            return abs_path
        
        # 确保目录存在
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        return path
    
    async def add_document(self, document: Dict, user_id: str = None) -> bool:
        """
        添加文档到RAG系统
        
        Args:
            document: 文档字典，包含id、content和metadata
            user_id: 用户ID，用于标识文档所属用户
            
        Returns:
            bool: 是否成功添加
        """
        try:
            # 检查文档格式
            if not self._validate_document(document):
                logger.warning(f"文档格式无效: {document}")
                return False
                
            # 生成嵌入向量
            content = document.get("content", "")
            embedding = await self.embedding_model.get_embedding(content)
            
            if embedding is None:
                logger.warning("生成嵌入向量失败，跳过添加文档")
                return False
                
            # 添加嵌入向量到文档
            document["embedding"] = embedding
            
            # 添加用户ID到元数据
            if user_id:
                if "metadata" not in document:
                    document["metadata"] = {}
                document["metadata"]["user_id"] = user_id
            
            # 保存到存储
            success = self.storage.add_document(document)
            
            if success:
                self.document_count = self.storage.get_document_count()
                logger.info(f"成功添加文档到RAG系统，当前文档数: {self.document_count}")
            
            return success
        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            return False
            
    async def update_document(self, document: Dict) -> bool:
        """
        更新RAG系统中的文档
        
        Args:
            document: 文档字典，包含id、content和metadata
            
        Returns:
            bool: 是否成功更新
        """
        try:
            # 检查文档格式
            if not self._validate_document(document):
                logger.warning(f"文档格式无效: {document}")
                return False
                
            # 检查是否需要更新嵌入向量
            if "embedding" not in document:
                # 生成嵌入向量
                content = document.get("content", "")
                embedding = await self.embedding_model.get_embedding(content)
                
                if embedding is None:
                    logger.warning("生成嵌入向量失败，跳过更新文档")
                    return False
                    
                # 添加嵌入向量到文档
                document["embedding"] = embedding
            
            # 保存到存储
            # 这里假设storage有update_document方法，如果没有需要实现
            if hasattr(self.storage, 'update_document'):
                success = self.storage.update_document(document)
            else:
                # 如果storage没有update_document方法，使用add_document替代
                # 这依赖于storage的add_document实现，它应该能处理现有文档的更新
                success = self.storage.add_document(document)
            
            if success:
                logger.info(f"成功更新文档")
            
            return success
        except Exception as e:
            logger.error(f"更新文档失败: {str(e)}")
            return False
            
    def _validate_document(self, document: Dict) -> bool:
        """
        验证文档格式
        
        Args:
            document: 待验证的文档
            
        Returns:
            bool: 文档是否有效
        """
        # 检查必要字段
        if not document.get("id") or not document.get("content"):
            return False
            
        # 检查内容长度
        content = document.get("content", "")
        if len(content) < 10:  # 过短的内容可能没有价值
            return False
            
        return True
    
    async def query(self, query_text: str, top_k: int = None) -> List[Dict]:
        """
        查询相关文档
        
        Args:
            query_text: 查询文本
            top_k: 返回结果数量，如果为None则使用配置中的值
            
        Returns:
            List[Dict]: 相关文档列表
        """
        try:
            # 使用配置的top_k值（如果未指定）
            if top_k is None:
                top_k = self.config.get("top_k", 5)
                
            # 生成查询嵌入向量
            query_embedding = await self.embedding_model.get_embedding(query_text)
            
            if query_embedding is None:
                logger.warning("生成查询嵌入向量失败")
                return []
                
            # 从存储中检索相关文档，使用角色名作为过滤条件
            # 这确保只检索当前角色的记忆
            results = self.storage.search(
                query_embedding, 
                top_k * 2,  # 检索更多结果以便重排序
                avatar_name=self.avatar_name  # 使用当前角色名作为过滤条件
            )
            
            if not results:
                logger.info("未找到相关文档")
                return []
                
            # 如果启用了重排序，对结果进行重排序
            if self.reranker and len(results) > 1:
                reranked_results = await self.reranker.rerank(query_text, results)
                results = reranked_results[:top_k]  # 截取top_k个结果
            else:
                results = results[:top_k]  # 直接截取top_k个结果
                
            logger.info(f"查询成功，找到 {len(results)} 个相关文档，角色: {self.avatar_name}")
            return results
        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            return []
    
    async def is_important(self, text: str) -> bool:
        """
        判断文本是否包含重要信息
        
        Args:
            text: 待判断的文本
            
        Returns:
            bool: 是否包含重要信息
        """
        # 先使用规则判断
        if self._rule_based_importance(text):
            return True
            
        # 如果有API，使用LLM判断
        if self.api_wrapper:
            try:
                # 使用LLM判断
                prompt = f"""请分析以下文本是否包含"重要信息"。重要信息是指:
1. 关于用户的个人情况、喜好、习惯、需求、限制条件等关键信息
2. 用户明确要求记住或标记为重要的内容
3. 包含数字、日期、地点、人名等特定事实类信息
4. 表达了用户的强烈情感或态度

文本: "{text}"

请直接回答"是"或"否"。"""

                response = await self.api_wrapper.async_completion(
                    prompt=prompt,
                    temperature=0.1,
                    max_tokens=10
                )
                
                response_text = response.get("content", "").strip().lower()
                return "是" in response_text or "yes" in response_text
            except Exception as e:
                logger.error(f"使用LLM判断重要性失败: {str(e)}")
                
        # 默认返回基于规则的判断
        return self._rule_based_importance(text)
    
    def _rule_based_importance(self, text: str) -> bool:
        """
        基于规则判断文本重要性
        
        Args:
            text: 待判断的文本
            
        Returns:
            bool: 是否包含重要信息
        """
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
                
        # 3. 包含数字、日期等特定格式
        if re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', text):  # 日期格式
            return True
            
        if re.search(r'\d{3,}', text):  # 至少3位数的数字
            return True
            
        return False
    
    async def generate_summary(self, user_id: str = None, limit: int = 20) -> str:
        """
        生成记忆摘要
        
        Args:
            user_id: 用户ID，如果提供则只总结该用户的记忆
            limit: 摘要包含的记忆条数
            
        Returns:
            str: 记忆摘要
        """
        try:
            if not self.api_wrapper:
                logger.error("未提供API包装器，无法生成摘要")
                return ""
                
            # 获取最新的记忆
            documents = self.storage.get_latest_documents(limit, user_id)
            
            if not documents:
                return "没有可用的记忆。"
                
            # 格式化记忆
            memory_text = ""
            for i, doc in enumerate(documents):
                content = doc.get("content", "")
                metadata = doc.get("metadata", {})
                timestamp = metadata.get("timestamp", "未知时间")
                
                memory_text += f"记忆 {i+1} [{timestamp}]:\n{content}\n\n"
                
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
            
    def clear_storage(self, user_id: str = None) -> bool:
        """
        清空存储
        
        Args:
            user_id: 用户ID，如果提供则只清空该用户的记忆
            
        Returns:
            bool: 是否成功清空
        """
        try:
            success = self.storage.clear(user_id)
            if success:
                self.document_count = self.storage.get_document_count()
                if user_id:
                    logger.info(f"已清空用户 {user_id} 的RAG存储")
                else:
                    logger.info("已清空RAG存储")
            return success
        except Exception as e:
            logger.error(f"清空存储失败: {str(e)}")
            return False

    # 在RagManager类中添加群聊上下文相关方法
    async def group_chat_query(self, group_id: str, current_timestamp: str = None, top_k: int = 7) -> List[Dict]:
        """
        查询群聊最近的对话消息
        
        Args:
            group_id: 群聊ID
            current_timestamp: 当前消息时间戳，如果提供则会排除该消息
            top_k: 返回的上下文消息数量，默认为7轮
            
        Returns:
            List[Dict]: 最近的消息列表
        """
        try:
            # 确保存储文件已加载
            if hasattr(self.storage, 'data') and 'group_chats' not in self.storage.data:
                self.storage.data['group_chats'] = {}
            
            # 如果群聊ID不存在于存储中，返回空列表
            if 'group_chats' not in self.storage.data or group_id not in self.storage.data['group_chats']:
                logger.warning(f"群聊 {group_id} 在RAG存储中不存在")
                return []
            
            # 获取群聊消息列表
            messages = self.storage.data['group_chats'][group_id]
            
            # 按时间戳倒序排序
            messages.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # 如果提供了当前消息时间戳，排除该消息
            if current_timestamp:
                messages = [msg for msg in messages if msg.get('timestamp') != current_timestamp]
            
            # 获取最近的top_k条消息
            recent_messages = messages[:top_k]
            
            # 按时间正序排序返回
            recent_messages.sort(key=lambda x: x.get('timestamp', ''))
            
            logger.info(f"获取到群聊 {group_id} 最近 {len(recent_messages)} 轮对话")
            return recent_messages
            
        except Exception as e:
            logger.error(f"查询群聊上下文失败: {str(e)}")
            return []
    
    async def add_group_chat_message(self, group_id: str, message: Dict) -> bool:
        """
        添加群聊消息到RAG系统
        
        Args:
            group_id: 群聊ID
            message: 消息字典，包含timestamp、sender_name、human_message等字段
            
        Returns:
            bool: 是否成功添加
        """
        try:
            # 确保存储文件已加载
            if hasattr(self.storage, 'data') and 'group_chats' not in self.storage.data:
                self.storage.data['group_chats'] = {}
            
            # 确保群聊ID存在于存储中
            if 'group_chats' not in self.storage.data:
                self.storage.data['group_chats'] = {}
            
            if group_id not in self.storage.data['group_chats']:
                self.storage.data['group_chats'][group_id] = []
            
            # 检查是否存在相同时间戳的消息
            timestamp = message.get('timestamp', '')
            existing_messages = [msg for msg in self.storage.data['group_chats'][group_id] 
                               if msg.get('timestamp') == timestamp]
            
            if existing_messages:
                # 更新已存在的消息
                for existing_msg in existing_messages:
                    existing_msg.update(message)
            else:
                # 添加新消息
                self.storage.data['group_chats'][group_id].append(message)
            
            # 保存数据
            self.storage._save_data()
            
            # 同时，也生成嵌入向量并添加到传统的document格式
            # 这是为了保持与API兼容性，允许使用语义搜索
            content = f"{message.get('sender_name', '')}: {message.get('human_message', '')}"
            if message.get('assistant_message'):
                content += f"\n{self.avatar_name}: {message.get('assistant_message')}"
            
            doc_id = f"group_chat_{group_id}_{int(time.time())}"
            if 'id' in message:
                doc_id = message['id']
            
            document = {
                "id": doc_id,
                "content": content,
                "metadata": {
                    "timestamp": message.get('timestamp', ''),
                    "sender_name": message.get('sender_name', ''),
                    "human_message": message.get('human_message', ''),
                    "assistant_message": message.get('assistant_message'),
                    "is_at": message.get('is_at', False),
                    "group_id": group_id,
                    "ai_name": message.get('ai_name', self.avatar_name)
                }
            }
            
            # 生成嵌入向量
            embedding = await self.embedding_model.get_embedding(content)
            if embedding:
                document["embedding"] = embedding
                self.storage.add_document(document)
            
            return True
        except Exception as e:
            logger.error(f"添加群聊消息到RAG系统失败: {str(e)}")
            return False
    
    async def update_group_chat_response(self, group_id: str, timestamp: str, response: str) -> bool:
        """
        更新群聊助手回复
        
        Args:
            group_id: 群聊ID
            timestamp: 消息时间戳
            response: 助手回复
            
        Returns:
            bool: 是否成功更新
        """
        try:
            # 确保存储文件已加载
            if hasattr(self.storage, 'data') and 'group_chats' not in self.storage.data:
                self.storage.data['group_chats'] = {}
            
            # 如果群聊ID不存在于存储中，返回失败
            if 'group_chats' not in self.storage.data or group_id not in self.storage.data['group_chats']:
                logger.warning(f"群聊 {group_id} 在RAG存储中不存在")
                return False
            
            # 查找对应时间戳的消息
            found = False
            for message in self.storage.data['group_chats'][group_id]:
                if message.get('timestamp') == timestamp:
                    message['assistant_message'] = response
                    found = True
                    break
            
            if not found:
                logger.warning(f"未找到时间戳为 {timestamp} 的群聊消息")
                return False
            
            # 保存数据
            self.storage._save_data()
            
            # 同时更新document格式中的数据
            # 查询对应的文档
            query = f"timestamp:{timestamp} AND group_id:{group_id}"
            results = await self.query(query, top_k=1)
            
            if results:
                doc = results[0]
                doc["metadata"]["assistant_message"] = response
                sender_name = doc["metadata"]["sender_name"]
                human_message = doc["metadata"]["human_message"]
                doc["content"] = f"{sender_name}: {human_message}\n{self.avatar_name}: {response}"
                
                # 更新文档
                await self.update_document(doc)
            
            return True
        except Exception as e:
            logger.error(f"更新群聊助手回复失败: {str(e)}")
            return False

# 嵌入模型实现
class ApiEmbeddingModel:
    """API嵌入模型"""
    
    def __init__(self, api_wrapper, model_name, model_type="openai"):
        """
        初始化API嵌入模型
        
        Args:
            api_wrapper: API调用包装器
            model_name: 模型名称
            model_type: 模型类型
        """
        self.api_wrapper = api_wrapper
        self.model_name = model_name
        self.model_type = model_type
        self.cache = {}  # 简单缓存，避免重复计算
        self.cache_hits = 0
        self.cache_misses = 0
        self.max_cache_size = 1000
        
    async def get_embedding(self, text: str) -> List[float]:
        """
        获取文本的嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            List[float]: 嵌入向量
        """
        # 检查缓存
        if text in self.cache:
            self.cache_hits += 1
            return self.cache[text]
            
        self.cache_misses += 1
        
        try:
            if not self.api_wrapper:
                logger.error("API包装器未初始化，无法获取嵌入向量")
                return None
                
            # 使用API获取嵌入向量
            try:
                # 首先尝试异步方法
                if hasattr(self.api_wrapper, 'async_embedding'):
                    embedding = await self.api_wrapper.async_embedding(text, self.model_name)
                # 如果不存在异步方法，则使用同步方法
                elif hasattr(self.api_wrapper, 'embedding'):
                    embedding = self.api_wrapper.embedding(text, self.model_name)
                else:
                    # 直接调用底层API
                    response = await self.api_wrapper.embeddings.create(
                        model=self.model_name,
                        input=text
                    )
                    if hasattr(response, 'data') and len(response.data) > 0:
                        embedding = response.data[0].embedding
                    elif isinstance(response, dict) and 'data' in response:
                        embedding = response['data'][0]['embedding']
                    else:
                        logger.error(f"无法解析嵌入向量响应: {response}")
                        return None
            except Exception as e:
                logger.error(f"调用嵌入API失败: {str(e)}")
                return None
                
            # 缓存结果
            self.cache[text] = embedding
            
            # 限制缓存大小
            if len(self.cache) > self.max_cache_size:
                # 删除最旧的项
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                
            return embedding
        except Exception as e:
            logger.error(f"获取嵌入向量失败: {str(e)}")
            return None
            
    def get_cache_stats(self) -> Dict:
        """
        获取缓存统计信息
        
        Returns:
            Dict: 缓存统计信息
        """
        return {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "size": len(self.cache),
            "max_size": self.max_cache_size
        }

class LocalEmbeddingModel:
    """本地嵌入模型"""
    
    def __init__(self, model_path):
        """
        初始化本地嵌入模型
        
        Args:
            model_path: 模型路径
        """
        self.model_path = model_path
        self.model = None
        self.cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.max_cache_size = 1000
        
        # 懒加载模型，降低内存占用
        
    async def get_embedding(self, text: str) -> List[float]:
        """
        获取文本的嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            List[float]: 嵌入向量
        """
        # 检查缓存
        if text in self.cache:
            self.cache_hits += 1
            return self.cache[text]
            
        self.cache_misses += 1
        
        try:
            # 懒加载模型
            if self.model is None:
                self._load_model()
                
            if self.model is None:
                logger.error("本地模型加载失败，无法获取嵌入向量")
                return None
                
            # 使用本地模型获取嵌入向量
            embedding = self._get_embedding_with_local_model(text)
            
            # 缓存结果
            self.cache[text] = embedding
            
            # 限制缓存大小
            if len(self.cache) > self.max_cache_size:
                # 删除最旧的项
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                
            return embedding
        except Exception as e:
            logger.error(f"获取嵌入向量失败: {str(e)}")
            return None
            
    def _load_model(self):
        """加载本地模型"""
        try:
            # 这里实现本地模型加载逻辑
            # 由于可能占用较多内存，所以采用懒加载方式
            logger.info(f"加载本地嵌入模型: {self.model_path}")
            
            # 示例：加载ONNX模型
            try:
                import onnxruntime as ort  # type: ignore
                self.model = ort.InferenceSession(self.model_path)
                logger.info("成功加载本地嵌入模型")
            except ImportError:
                logger.error("未安装onnxruntime，无法加载本地模型")
                self.model = None
                
        except Exception as e:
            logger.error(f"加载本地模型失败: {str(e)}")
            self.model = None
            
    def _get_embedding_with_local_model(self, text: str) -> List[float]:
        """
        使用本地模型获取嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            List[float]: 嵌入向量
        """
        # 这里实现使用本地模型的嵌入逻辑
        # 示例：使用ONNX模型
        try:
            if hasattr(self.model, "run"):
                # 预处理文本
                # 简单实现，实际应该根据模型要求进行预处理
                inputs = {"input_ids": [ord(c) for c in text[:512]]}
                
                # 运行模型
                outputs = self.model.run(None, inputs)
                
                # 返回嵌入向量
                embedding = outputs[0].tolist()[0]
                return embedding
            else:
                logger.error("模型未正确加载，无法获取嵌入向量")
                return None
        except Exception as e:
            logger.error(f"使用本地模型获取嵌入向量失败: {str(e)}")
            return None
            
    def get_cache_stats(self) -> Dict:
        """
        获取缓存统计信息
        
        Returns:
            Dict: 缓存统计信息
        """
        return {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "size": len(self.cache),
            "max_size": self.max_cache_size
        }

# 重排序器实现
class ApiReranker:
    """API重排序器"""
    
    def __init__(self, api_wrapper, model_name):
        """
        初始化API重排序器
        
        Args:
            api_wrapper: API调用包装器
            model_name: 模型名称
        """
        self.api_wrapper = api_wrapper
        self.model_name = model_name
        
    async def rerank(self, query: str, results: List[Dict]) -> List[Dict]:
        """
        重排序检索结果
        
        Args:
            query: 查询文本
            results: 检索结果列表
            
        Returns:
            List[Dict]: 重排序后的结果列表
        """
        try:
            if not self.api_wrapper:
                logger.error("API包装器未初始化，无法进行重排序")
                return results
                
            if not results or len(results) <= 1:
                return results
                
            # 使用LLM进行重排序
            prompt = self._create_rerank_prompt(query, results)
            
            response = await self.api_wrapper.async_completion(
                prompt=prompt,
                temperature=0.1,
                max_tokens=500
            )
            
            # 解析重排序结果
            reranked_results = self._parse_rerank_response(response.get("content", ""), results)
            
            # 如果解析失败，返回原始结果
            if not reranked_results:
                return results
                
            return reranked_results
        except Exception as e:
            logger.error(f"重排序失败: {str(e)}")
            return results
            
    def _create_rerank_prompt(self, query: str, results: List[Dict]) -> str:
        """
        创建重排序提示
        
        Args:
            query: 查询文本
            results: 检索结果列表
            
        Returns:
            str: 重排序提示
        """
        prompt = f"""请根据查询问题对以下文档片段进行相关性排序，从最相关到最不相关。
仅基于文档与查询的相关性进行排序，不考虑文档的其他方面。

查询问题: {query}

文档片段:
"""

        for i, result in enumerate(results):
            content = result.get("content", "")
            prompt += f"\n文档{i+1}: {content}\n"
            
        prompt += """
请按相关性从高到低列出文档编号，使用以下格式:
排序结果: [最相关文档编号], [次相关文档编号], ...
"""
        
        return prompt
        
    def _parse_rerank_response(self, response: str, results: List[Dict]) -> List[Dict]:
        """
        解析重排序响应
        
        Args:
            response: LLM响应文本
            results: 原始检索结果
            
        Returns:
            List[Dict]: 重排序后的结果列表
        """
        try:
            # 提取排序结果
            import re
            match = re.search(r'排序结果:?\s*(.+)', response)
            
            if not match:
                logger.warning("未能从响应中提取排序结果")
                return []
                
            # 解析文档编号
            order_text = match.group(1)
            order_parts = re.findall(r'\d+', order_text)
            
            if not order_parts:
                logger.warning("未能解析文档编号")
                return []
                
            # 将文本编号转换为整数索引
            try:
                orders = [int(part) - 1 for part in order_parts]
            except ValueError:
                logger.warning("文档编号解析错误")
                return []
                
            # 按照排序重组结果
            reranked_results = []
            seen_indices = set()
            
            for idx in orders:
                if 0 <= idx < len(results) and idx not in seen_indices:
                    reranked_results.append(results[idx])
                    seen_indices.add(idx)
                    
            # 添加未包含在排序中的结果
            for i, result in enumerate(results):
                if i not in seen_indices:
                    reranked_results.append(result)
                    
            return reranked_results
        except Exception as e:
            logger.error(f"解析重排序响应失败: {str(e)}")
            return []

# 存储实现
class JsonStorage:
    """JSON文件存储"""
    
    def __init__(self, file_path):
        """
        初始化JSON存储
        
        Args:
            file_path: JSON文件路径
        """
        self.file_path = file_path
        self.data = self._load_data()
        
    def _load_data(self) -> Dict:
        """
        加载数据
        
        Returns:
            Dict: 数据字典
        """
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 确保基本结构存在
                    if "documents" not in data:
                        data["documents"] = []
                    if "group_chats" not in data:
                        data["group_chats"] = {}
                    return data
            else:
                # 初始化空数据
                data = {
                    "documents": [],
                    "group_chats": {}  # 添加群聊数据结构
                }
                self._save_data(data)
                return data
        except Exception as e:
            logger.error(f"加载数据失败: {str(e)}")
            return {"documents": [], "group_chats": {}}
            
    def _save_data(self, data: Dict = None):
        """
        保存数据
        
        Args:
            data: 要保存的数据字典
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            
            # 如果未提供数据，使用当前数据
            if data is None:
                data = self.data
                
            # 保存数据
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存数据失败: {str(e)}")
            
    def add_document(self, document: Dict) -> bool:
        """
        添加文档
        
        Args:
            document: 文档字典
            
        Returns:
            bool: 是否成功添加
        """
        try:
            # 检查文档ID是否已存在
            doc_id = document.get("id")
            
            for existing_doc in self.data["documents"]:
                if existing_doc.get("id") == doc_id:
                    # 更新现有文档
                    existing_doc.update(document)
                    self._save_data()
                    return True
                    
            # 添加新文档
            self.data["documents"].append(document)
            self._save_data()
            return True
        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            return False
            
    def search(self, query_embedding: List[float], top_k: int = 5, avatar_name: str = None) -> List[Dict]:
        """
        搜索相关文档
        
        Args:
            query_embedding: 查询嵌入向量
            top_k: 返回结果数量
            avatar_name: 角色名，如果提供则只搜索该角色的记忆
            
        Returns:
            List[Dict]: 相关文档列表
        """
        try:
            if not self.data["documents"]:
                return []
                
            # 计算余弦相似度
            results = []
            
            for doc in self.data["documents"]:
                # 如果指定了角色名，则只检索该角色的记忆
                if avatar_name and doc.get("metadata", {}).get("user_id") != avatar_name:
                    continue
                    
                doc_embedding = doc.get("embedding")
                
                if not doc_embedding:
                    continue
                    
                # 计算相似度
                similarity = self._cosine_similarity(query_embedding, doc_embedding)
                
                # 添加到结果列表
                results.append({
                    "id": doc.get("id"),
                    "content": doc.get("content"),
                    "metadata": doc.get("metadata", {}),
                    "score": similarity
                })
                
            # 按相似度降序排序
            results.sort(key=lambda x: x["score"], reverse=True)
            
            # 返回前top_k个结果
            return results[:top_k]
        except Exception as e:
            logger.error(f"搜索文档失败: {str(e)}")
            return []
            
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            float: 余弦相似度
        """
        try:
            # 转换为numpy数组
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            # 计算点积
            dot_product = np.dot(vec1, vec2)
            
            # 计算范数
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            # 计算相似度
            similarity = dot_product / (norm1 * norm2)
            
            return float(similarity)
        except Exception as e:
            logger.error(f"计算余弦相似度失败: {str(e)}")
            return 0.0
            
    def get_document_count(self, avatar_name: str = None) -> int:
        """
        获取文档数量
        
        Args:
            avatar_name: 角色名，如果提供则只计算该角色的记忆数量
            
        Returns:
            int: 文档数量
        """
        if avatar_name:
            return len([doc for doc in self.data.get("documents", []) 
                       if doc.get("metadata", {}).get("user_id") == avatar_name])
        return len(self.data.get("documents", []))
        
    def get_latest_documents(self, limit: int = 20, avatar_name: str = None) -> List[Dict]:
        """
        获取最新文档
        
        Args:
            limit: 返回的文档数量
            avatar_name: 角色名，如果提供则只返回该角色的记忆
            
        Returns:
            List[Dict]: 文档列表
        """
        try:
            documents = self.data.get("documents", [])
            
            # 如果指定了角色名，只获取该角色的文档
            if avatar_name:
                documents = [doc for doc in documents 
                           if doc.get("metadata", {}).get("user_id") == avatar_name]
            
            # 如果数据中包含创建时间，按时间排序
            try:
                documents_with_time = []
                
                for doc in documents:
                    # 尝试从元数据中获取时间
                    metadata = doc.get("metadata", {})
                    timestamp = metadata.get("timestamp", "")
                    
                    # 如果没有时间信息，尝试从ID中提取
                    if not timestamp and "memory_" in doc.get("id", ""):
                        try:
                            time_part = doc.get("id", "").split("memory_")[1]
                            timestamp = time_part
                        except:
                            pass
                            
                    # 添加到列表
                    documents_with_time.append((doc, timestamp))
                    
                # 按时间戳降序排序（最新的在前面）
                documents_with_time.sort(key=lambda x: x[1], reverse=True)
                
                # 提取文档
                sorted_documents = [doc for doc, _ in documents_with_time]
                return sorted_documents[:limit]
            except Exception as e:
                logger.error(f"排序文档失败: {str(e)}")
                
            # 如果排序失败，直接返回最新的文档
            return documents[-limit:]
        except Exception as e:
            logger.error(f"获取最新文档失败: {str(e)}")
            return []
            
    def clear(self, avatar_name: str = None) -> bool:
        """
        清空存储
        
        Args:
            avatar_name: 角色名，如果提供则只清空该角色的记忆
            
        Returns:
            bool: 是否成功清空
        """
        try:
            if avatar_name:
                # 只清空指定角色的记忆
                self.data["documents"] = [doc for doc in self.data.get("documents", [])
                                        if doc.get("metadata", {}).get("user_id") != avatar_name]
            else:
                # 清空所有记忆
                self.data = {"documents": []}
            
            self._save_data()
            return True
        except Exception as e:
            logger.error(f"清空存储失败: {str(e)}")
            return False

def create_default_config(config_path: str):
    """
    创建默认RAG配置文件
    
    Args:
        config_path: 配置文件路径
    """
    try:
        default_config = {
            "api_key": "",
            "base_url": "",
            "embedding_model": {
                "type": "openai",
                "name": "text-embedding-3-large",
                "dimensions": 1536
            },
            "storage": {
                "type": "json",
                "path": "./data/rag_storage.json"
            },
            "top_k": 5,
            "is_rerank": False,
            "reranker": {
                "type": "api",
                "name": "rerank-large"
            },
            "local_model": {
                "enabled": False,
                "path": "./models/embedding_model"
            }
        }
        
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # 保存配置
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
            
        logger.info(f"已创建默认RAG配置文件: {config_path}")
        return default_config
    except Exception as e:
        logger.error(f"创建默认配置文件失败: {str(e)}")
        return None

# 添加必要的导入
import re  # 用于正则表达式操作 
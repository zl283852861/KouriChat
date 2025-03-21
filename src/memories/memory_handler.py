"""
记忆处理器主模块 - 作为上层接口统一管理所有记忆功能
"""
import os
import logging
import json
import time
import asyncio
import re
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

# 引入内部模块
from src.memories.memory_utils import memory_cache, clean_memory_content, get_importance_keywords, get_memory_path, clean_dialog_memory
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
                    logger.debug("通过ShortTermMemory更新了RAG记忆")
                else:
                    # 没有ShortTermMemory实例，直接添加标准格式记忆
                    self._add_to_rag_directly(clean_key, clean_value)
            except Exception as e:
                logger.debug(f"尝试更新RAG记忆失败，将直接添加: {str(e)}")
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
            import re
            from datetime import datetime
            from src.memories import get_rag
            from src.memories.memory_utils import clean_dialog_memory
            
            rag_instance = get_rag()
            if not rag_instance:
                logger.debug("RAG实例不可用，跳过添加")
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
                logger.debug(f"获取角色名失败: {str(e)}")
                
            # 使用memory_utils中的清理函数进一步清理对话内容
            sender_text, _ = clean_dialog_memory(clean_key, "")
            _, receiver_text = clean_dialog_memory("", clean_value)
            
            # 预处理过滤 - 检查内容质量
            if not self._is_valid_for_rag(sender_text, receiver_text):
                logger.debug("预处理过滤：内容质量不符合要求，跳过添加到RAG")
                return
            
            # 确定是否为主动消息 (当消息由AI主动发起或由定时任务触发时，标记为主动消息)
            # 改进主动消息识别逻辑
            is_initiative = False
            
            # 1. 检查特征词，判断是否为AI主动发起的消息
            initiative_keywords = [
                "主人", "您好", "早上好", "晚上好", "下午好", 
                "好久不见", "想你了", "有空吗", "在吗",
                "最近怎么样", "最近好吗", "有什么新鲜事", 
                "今天天气", "睡得好吗", "吃饭了吗"
            ]
            
            # 2. 检查是否包含系统标记的主动消息特征
            system_initiative_signals = [
                "[系统指令]", "系统设置的角色", "在微信上找对方聊天", 
                "(此时时间为", "定时消息", "自动消息"
            ]
            
            # 3. 检查典型的问候模式，通常是主动消息的特征
            greeting_patterns = [
                r"^(?:早上|晚上|中午|下午)好",
                r"^你好[啊呀哇吖呢]*[，。!！~]*$",
                r"^(?:在吗|在不在|忙吗|有空吗)[?？]*$",
                r"^(?:最近|近来)(?:怎么样|如何|好吗)[?？]*$"
            ]
            
            # 检查是否匹配任何主动消息特征
            # 检查特征词
            if any(keyword in sender_text or keyword in receiver_text for keyword in initiative_keywords):
                is_initiative = True
                logger.debug(f"通过特征词检测到主动消息")
            
            # 检查系统标记
            elif any(signal in sender_text for signal in system_initiative_signals):
                is_initiative = True
                logger.debug(f"通过系统标记检测到主动消息")
            
            # 检查问候模式
            else:
                for pattern in greeting_patterns:
                    if re.search(pattern, sender_text, re.IGNORECASE) or re.search(pattern, receiver_text, re.IGNORECASE):
                        is_initiative = True
                        logger.debug(f"通过问候模式检测到主动消息")
                        break
            
            # 准备RAG索引用的文本 - 使用清理后的文本
            user_doc = f"[{current_time}]对方(ID:{user_id or '未知用户'}): {sender_text}"
            ai_doc = f"[{current_time}] 你: {receiver_text}"
            
            # 添加到RAG系统 - 更干净的格式
            if hasattr(rag_instance, 'add_documents'):
                rag_instance.add_documents(texts=[user_doc, ai_doc])
                logger.debug(f"已将清理后的记忆文本添加到RAG索引")
                
            # 准备新格式的记忆数据 - 使用清理后的内容
            memory_entry = {
                "bot_time": current_time,
                "sender_id": user_id or "未知用户",
                "sender_text": sender_text,
                "receiver_id": avatar_name,
                "receiver_text": receiver_text,
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
                        
                    # 清理现有的memories键，将其转移到conversation格式
                    if "memories" in conversations and conversations["memories"]:
                        logger.debug("检测到旧格式memories键，将转换为conversation格式")
                        old_memories = conversations["memories"]
                        next_conv_index = 0
                        
                        # 确定下一个可用的conversation索引
                        for key in conversations.keys():
                            if key.startswith("conversation"):
                                try:
                                    index = int(key.replace("conversation", ""))
                                    next_conv_index = max(next_conv_index, index + 1)
                                except:
                                    pass
                                    
                        # 将旧memories转换为新格式
                        for old_key, old_value in old_memories.items():
                            # 清理旧格式内容
                            clean_sender, clean_receiver = clean_dialog_memory(old_key, old_value)
                            old_entry = {
                                "bot_time": current_time,  # 使用当前时间
                                "sender_id": "migrated_user",
                                "sender_text": clean_sender,
                                "receiver_id": avatar_name,
                                "receiver_text": clean_receiver,
                                "emotion": "None",
                                "is_initiative": False
                            }
                            # 添加到conversations
                            conversations[f"conversation{next_conv_index}"] = [old_entry]
                            next_conv_index += 1
                            
                        # 清理旧的memories键
                        conversations.pop("memories", None)
                        logger.debug(f"成功迁移 {len(old_memories)} 条旧格式记忆")
                        
                    # 合并现有对话 - 如果有相同用户ID的对话，则追加而不是创建新对话
                    if user_id:
                        # 查找该用户的最新对话
                        user_conversations = []
                        for key, value in conversations.items():
                            if key.startswith("conversation") and value and isinstance(value, list) and len(value) > 0:
                                if value[0].get("sender_id") == user_id:
                                    user_conversations.append((key, value))
                        
                        # 如果找到该用户的对话，追加到最后一个
                        if user_conversations:
                            # 按对话序号排序
                            user_conversations.sort(key=lambda x: int(x[0].replace("conversation", "")))
                            last_conv_key, last_conv_value = user_conversations[-1]
                            
                            # 如果最后一个对话不超过10条，则追加
                            if len(last_conv_value) < 10:
                                conversations[last_conv_key].append(memory_entry)
                                logger.debug(f"将新记忆添加到现有对话 {last_conv_key}")
                                # 保存更新后的记忆
                                with open(json_path, 'w', encoding='utf-8') as f:
                                    json.dump(conversations, f, ensure_ascii=False, indent=2)
                                logger.debug(f"记忆已添加到现有对话并保存")
                                return
                except Exception as e:
                    logger.debug(f"加载或处理记忆JSON失败: {str(e)}")
            
            # 生成新的对话索引
            next_index = 0
            for key in conversations.keys():
                if key.startswith("conversation"):
                    try:
                        index = int(key.replace("conversation", ""))
                        next_index = max(next_index, index + 1)
                    except:
                        pass
            
            # 添加新记忆作为新对话
            conversation_key = f"conversation{next_index}"
            conversations[conversation_key] = [memory_entry]
            
            # 保存更新后的记忆
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(conversations, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"已将干净的记忆添加到JSON文件，索引: {next_index}")
            
        except Exception as e:
            logger.debug(f"直接添加记忆到RAG失败: {str(e)}")
        
    def _is_valid_for_rag(self, sender_text: str, receiver_text: str) -> bool:
        """
        检查对话内容是否适合添加到RAG系统
        
        Args:
            sender_text: 发送者文本
            receiver_text: 接收者文本
            
        Returns:
            bool: 是否适合添加到RAG
        """
        # 检查文本长度
        if not sender_text.strip() or not receiver_text.strip():
            return False
            
        if len(sender_text.strip()) < 3 or len(receiver_text.strip()) < 3:
            logger.debug("文本长度过短，不适合添加到RAG")
            return False
            
        # 过滤系统指令和控制信息
        system_patterns = [
            r"请注意[:：]", 
            r"当任务完成时", 
            r"请记住你是", 
            r"请扮演", 
            r"你的回复应该",
            r"你现在是一个",
            r"你现在应该扮演",
            r"你是一个AI",
            r"我是你的主人",
            r"请你记住",
            r"请保持简洁",
            r"请回复得",
            r"我希望你的回复",
            r"在此消息之后",
            r"我想要你",
            r"API调用",
            r"更新出错",
            r"请等待",
            r"请稍等",
            r"正在处理",
            r"出错了"
        ]
        
        for pattern in system_patterns:
            if re.search(pattern, sender_text, re.IGNORECASE) or re.search(pattern, receiver_text, re.IGNORECASE):
                logger.debug(f"文本包含系统指令模式，不适合添加到RAG: {pattern}")
                return False
                
        # 检查是否包含特殊格式或指令
        special_format_patterns = [
            r"```", r"<", r"<function",
            r"\[\[", r"\]\]", r"/start", r"/help",
            r"/command", r"<div>", r"<span>",
            r"<img", r"<code>"
        ]
        
        for pattern in special_format_patterns:
            if re.search(pattern, sender_text) or re.search(pattern, receiver_text):
                logger.debug(f"文本包含特殊格式，不适合添加到RAG: {pattern}")
                return False
                
        # 过滤无意义的短对话
        meaningless_patterns = [
            r"^[。.！!？?]+$",  # 只有标点符号
            r"^(是的?|对的?|嗯+|好的?|行的?|可以的?|没问题|ok|okay)$",  # 简单肯定
            r"^(不是|不对|不行|不可以|别|算了|算了吧)$",  # 简单否定
            r"^[啊哦嗯哈呵嘿]+$"  # 只有语气词
        ]
        
        # 检查接收者文本是否为无意义回复
        for pattern in meaningless_patterns:
            if re.search(pattern, receiver_text.lower().strip()):
                logger.debug(f"AI回复过于简单，不适合添加到RAG: {receiver_text}")
                return False
                
        return True
        
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
import os
import logging
import functools  # 添加functools导入用于创建装饰器
from typing import List, Optional, Dict  # 添加 Dict 导入
from datetime import datetime
from src.memories.key_memory import KeyMemory
from src.memories.long_term_memory import LongTermMemory
from src.memories.memory.core.rag import RAG, OnlineCrossEncoderReRanker, OnlineEmbeddingModel, LocalEmbeddingModel, HybridEmbeddingModel, EmbeddingModel
from src.memories.memory_saver import MySQLMemorySaver, SQLiteMemorySaver
from src.memories.short_term_memory import ShortTermMemory
from src.services.ai.llm_service import LLMService
from src.handlers.emotion import SentimentAnalyzer
# 从config模块获取配置
from src.config import config
from src.services.ai.llms.openai_llm import OpenAILLM
import time  # 添加time模块导入，用于超时控制
import re  # 添加正则表达式模块用于解析用户ID
import concurrent.futures

# 定义嵌入模型
EMBEDDING_MODEL = "text-embedding-3-large"  # 默认嵌入模型
EMBEDDING_FALLBACK_MODEL = "text-embedding-ada-002"  # 备用嵌入模型
LOCAL_EMBEDDING_MODEL_PATH = "paraphrase-multilingual-MiniLM-L12-v2"  # 本地嵌入模型路径

logger = logging.getLogger('main')

# 创建memory_cache装饰器，用于记忆函数装饰
def memory_cache(func):
    """
    记忆缓存装饰器，用于缓存记忆相关函数的结果
    当前主要用于记录函数调用情况和错误处理
    
    Args:
        func: 被装饰的函数
        
    Returns:
        包装后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # 记录函数调用
            logger.debug(f"调用记忆函数: {func.__name__}")
            # 执行原函数
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            # 记录错误
            logger.error(f"记忆函数 {func.__name__} 执行出错: {str(e)}")
            # 根据需要决定是否重新抛出异常
            raise
    return wrapper

# 定义需要重点关注的关键词列表
KEYWORDS = [
    "记住了没？", "记好了", "记住", "别忘了", "牢记", "记忆深刻", "不要忘记", "铭记",
    "别忘掉", "记在心里", "时刻记得", "莫失莫忘", "印象深刻", "难以忘怀", "念念不忘", "回忆起来",
    "永远不忘", "留意", "关注", "提醒", "提示", "警示", "注意", "特别注意",
    "记得检查", "请记得", "务必留意", "时刻提醒自己", "定期回顾", "随时注意", "不要忽略", "确认一下",
    "核对", "检查", "温馨提示", "小心"
]

def get_saver(is_long_term: bool = False):
    if config["categories"]["memory_settings"]["db_settings"]["type"] == "sqlite":
        return SQLiteMemorySaver(
            table_name=config["categories"]["memory_settings"]["long_term_memory"]["table_name"] if is_long_term else config["categories"]["memory_settings"]["key_memory"]["table_name"],
            db_path=config["categories"]["memory_settings"]["db_settings"]["sqlite_path"]
        )
    elif config["categories"]["memory_settings"]["db_settings"]["type"] == "mysql":
        return MySQLMemorySaver(
            table_name=config["categories"]["memory_settings"]["long_term_memory"]["table_name"] if is_long_term else config["categories"]["memory_settings"]["key_memory"]["table_name"],
            db_settings={
                "host": config["categories"]["memory_settings"]["db_settings"]["host"],
                "port": config["categories"]["memory_settings"]["db_settings"]["port"],
                "user": config["categories"]["memory_settings"]["db_settings"]["user"],
                "password": config["categories"]["memory_settings"]["db_settings"]["password"],
                "database": config["categories"]["memory_settings"]["db_settings"]["database"],
            }
        )
    else:
        raise ValueError("不支持的数据库类型")

class MemoryHandler:
    def __init__(self, root_dir: str, api_key: str, base_url: str, model: str,
                 max_token: int, temperature: float, max_groups: int,
                 llm: LLMService,bot_name: str = None, sentiment_analyzer: SentimentAnalyzer = None):
        # 基础参数
        self.root_dir = root_dir
        self.api_key = api_key
        self.base_url = base_url
        self.max_token = max_token
        self.temperature = temperature
        self.max_groups = max_groups
        self.model = model
        self.llm = llm

        # 从config模块获取配置
        from src.config import config
        self.config = config  # 保存config对象的引用
        self.bot_name = bot_name or config.robot_wx_name
        self.listen_list = config.user.listen_list

        # 记忆目录结构
        self.memory_base_dir = os.path.join(root_dir, "data", "memory")
        os.makedirs(self.memory_base_dir, exist_ok=True)

        # 创建API嵌入模型
        api_key = config.rag.api_key
        base_url = config.rag.base_url
        embedding_model_name = config.rag.embedding_model
        reranker_model_name = config.rag.reranker_model or model
        
        # 打印调试信息
        logger.info(f"嵌入模型配置 - 类型: {type(embedding_model_name)}")
        logger.info(f"基础URL配置 - 类型: {type(base_url)}")
        
        # 检查是否为硅基流动API
        is_siliconflow = False
        if isinstance(base_url, str) and "siliconflow" in base_url.lower():
            is_siliconflow = True
        
        # 准备模型名称
        model_name_str = embedding_model_name
        if isinstance(embedding_model_name, dict) and 'value' in embedding_model_name:
            model_name_str = embedding_model_name['value']
        
        # 创建API嵌入模型
        logger.info(f"创建API嵌入模型，模型名称: {model_name_str}, API URL: {base_url}")
        
        api_embedding_model = None
        # 尝试创建嵌入模型
        try:
            if is_siliconflow:
                # 对于硅基流动API，使用专用的SiliconFlowEmbeddingModel
                from src.memories.memory.core.rag import SiliconFlowEmbeddingModel
                
                # 检查模型名称是否兼容硅基流动API
                siliconflow_models = ["BAAI/bge-large-zh-v1.5", "BAAI/bge-m3", "BAAI/bge-base-zh-v1.5"]
                if str(model_name_str) not in siliconflow_models and config.rag.auto_adapt_siliconflow:
                    logger.info(f"模型名称'{model_name_str}'可能不兼容硅基流动API，将使用BAAI/bge-m3")
                    model_name_str = "BAAI/bge-m3"
                
                logger.info(f"使用SiliconFlowEmbeddingModel，模型名称: {model_name_str}")
                api_embedding_model = SiliconFlowEmbeddingModel(
                    model_name=model_name_str,
                    api_key=api_key,
                    api_url=base_url
                )
            else:
                # 对于其他API，使用通用的OnlineEmbeddingModel
                logger.info(f"使用OnlineEmbeddingModel，模型名称: {model_name_str}")
                api_embedding_model = OnlineEmbeddingModel(
                    model_name=model_name_str,
                    api_key=api_key,
                    base_url=base_url
                )
        except Exception as e:
            logger.error(f"创建嵌入模型失败: {str(e)}")
            logger.info("尝试使用本地模型作为备用")
            
            # 创建一个本地嵌入模型作为备用
            try:
                from src.memories.memory.core.rag import LocalEmbeddingModel
                LOCAL_EMBEDDING_MODEL_PATH = config.rag.local_embedding_model_path
                api_embedding_model = LocalEmbeddingModel(LOCAL_EMBEDDING_MODEL_PATH)
            except Exception as e2:
                logger.error(f"创建本地嵌入模型也失败: {str(e2)}")
                
                # 创建一个空的嵌入模型类，避免程序崩溃
                class EmptyEmbeddingModel(EmbeddingModel):
                    def embed(self, texts: List[str]) -> List[List[float]]:
                        logger.warning("使用空嵌入模型，返回零向量")
                        return [[0.0] * 1536 for _ in range(len(texts))]
                
                api_embedding_model = EmptyEmbeddingModel()
        
        # 创建混合嵌入模型，优先使用API模型，允许用户选择是否下载本地备用模型
        try:
            LOCAL_EMBEDDING_MODEL_PATH = config.rag.local_embedding_model_path
            hybrid_embedding_model = HybridEmbeddingModel(
                api_model=api_embedding_model,
                local_model_path=LOCAL_EMBEDDING_MODEL_PATH,
                local_model_enabled=config.rag.local_model_enabled
            )
        except Exception as e:
            logger.error(f"创建混合嵌入模型失败: {str(e)}")
            logger.warning("将使用API嵌入模型，不包含本地备用")
            hybrid_embedding_model = api_embedding_model
        
        # 初始化Rag记忆的方法
        # 2025-03-15修改，使用ShortTermMemory单例模式
        try:
            self.short_term_memory = ShortTermMemory.get_instance(
                memory_path=os.path.join(self.memory_base_dir, "rag-memory.json"),
                embedding_model=hybrid_embedding_model,
                reranker=OnlineCrossEncoderReRanker(
                    model_name=reranker_model_name,
                    api_key=api_key,
                    base_url=base_url
                ) if config.rag.is_rerank is True else None
            )
            logger.info("成功初始化短期记忆系统")
        except Exception as e:
            logger.error(f"初始化短期记忆系统失败: {str(e)}")
            # 尝试使用简化参数创建
            try:
                self.short_term_memory = ShortTermMemory.get_instance(
                    memory_path=os.path.join(self.memory_base_dir, "rag-memory.json"),
                    embedding_model=hybrid_embedding_model
                )
                logger.info("使用简化参数成功初始化短期记忆系统")
            except Exception as e2:
                logger.error(f"使用简化参数初始化短期记忆系统也失败: {str(e2)}")
                # 创建一个空的ShortTermMemory实例，避免程序崩溃
                self.short_term_memory = {}
                logger.critical("使用空字典替代短期记忆系统，功能将受限")
        
        try:
            self.key_memory = KeyMemory.get_instance(
                get_saver(is_long_term=False)
            )
            logger.info("成功初始化关键记忆系统")
        except Exception as e:
            logger.error(f"初始化关键记忆系统失败: {str(e)}")
            # 创建一个空的KeyMemory实例，避免程序崩溃
            self.key_memory = {}
            logger.critical("使用空字典替代关键记忆系统，功能将受限")
            
        try:
            self.long_term_memory = LongTermMemory.get_instance(
                get_saver(is_long_term=True),
                OpenAILLM(
                    api_key=config.llm.api_key,
                    url=config.llm.base_url,
                    model_name=config.llm.model,
                    max_tokens=config.llm.max_tokens,
                    temperature=config.llm.temperature,
                    max_context_messages=config.behavior.context.max_groups,
                    logger=logger,
                    singleton=True  # 确保使用单例模式
                ),
                config["categories"]["memory_settings"]["long_term_memory"]["process_prompt"]
            )
            logger.info("成功初始化长期记忆系统")
        except Exception as e:
            logger.error(f"初始化长期记忆系统失败: {str(e)}")
            # 创建一个空的LongTermMemory实例，避免程序崩溃
            self.long_term_memory = {}
            logger.critical("使用空字典替代长期记忆系统，功能将受限")
            
        self.is_rerank = config.rag.is_rerank
        self.top_k = config.rag.top_k
        
        # 安全地启动短期记忆和添加钩子
        try:
            if hasattr(self.short_term_memory, 'start_memory'):
                self.short_term_memory.start_memory()
                logger.info("短期记忆系统已启动")
            self.add_short_term_memory_hook()
            logger.info("短期记忆钩子已添加")
        except Exception as e:
            logger.error(f"启动短期记忆系统或添加钩子失败: {str(e)}")

        # 尝试初始化长期记忆和关键记忆的组合rag
        try:
            self.lg_tm_m_and_k_m = RAG(
                embedding_model=hybrid_embedding_model,
                reranker=OnlineCrossEncoderReRanker(
                    model_name=reranker_model_name,
                    api_key=api_key,
                    base_url=base_url
                ) if config.rag.is_rerank is True else None
            )
            self.init_lg_tm_m_and_k_m()
            logger.info("长期记忆和关键记忆的组合RAG系统已初始化")
        except Exception as e:
            logger.error(f"初始化长期记忆和关键记忆的组合RAG系统失败: {str(e)}")
            # 创建一个空的RAG对象
            self.lg_tm_m_and_k_m = None
            logger.critical("长期记忆和关键记忆的组合RAG系统初始化失败，该功能将不可用")
        
        # 安全添加长期记忆处理任务
        try:
            self.add_long_term_memory_process_task()
            logger.info("长期记忆处理任务已添加")
        except Exception as e:
            logger.error(f"添加长期记忆处理任务失败: {str(e)}")
        
        # 安全初始化记忆系统
        try:
            self.initialize_memory()
            logger.info("记忆系统初始化完成")
        except Exception as e:
            logger.error(f"初始化记忆系统失败: {str(e)}")
    
    def init_lg_tm_m_and_k_m(self):
        """
        初始化长期记忆和关键记忆的组合rag库
        """
        try:
            # 检查lg_tm_m_and_k_m是否为None
            if self.lg_tm_m_and_k_m is None:
                logger.warning("长期记忆和关键记忆的组合RAG系统不可用，跳过初始化")
                return False
                
            # 检查组件是否可用
            memories_available = False
            
            # 尝试获取长期记忆
            if not isinstance(self.long_term_memory, dict) and hasattr(self.long_term_memory, 'get_memories'):
                try:
                    long_term_memories = self.long_term_memory.get_memories()
                    if long_term_memories:
                        self.lg_tm_m_and_k_m.add_documents(long_term_memories)
                        logger.info(f"已添加 {len(long_term_memories) if isinstance(long_term_memories, list) else '未知数量'} 条长期记忆到组合RAG")
                        memories_available = True
                except Exception as e:
                    logger.error(f"添加长期记忆到组合RAG时出错: {str(e)}")
            else:
                logger.warning("长期记忆不可用，跳过添加到组合RAG")
            
            # 尝试获取关键记忆
            if not isinstance(self.key_memory, dict) and hasattr(self.key_memory, 'get_memory'):
                try:
                    key_memories = self.key_memory.get_memory()
                    if key_memories:
                        self.lg_tm_m_and_k_m.add_documents(key_memories)
                        logger.info(f"已添加 {len(key_memories) if isinstance(key_memories, list) else '未知数量'} 条关键记忆到组合RAG")
                        memories_available = True
                except Exception as e:
                    logger.error(f"添加关键记忆到组合RAG时出错: {str(e)}")
            else:
                logger.warning("关键记忆不可用，跳过添加到组合RAG")
                
            if not memories_available:
                logger.warning("没有可用的记忆添加到组合RAG")
                
            return memories_available
        except Exception as e:
            logger.error(f"初始化组合RAG时发生错误: {str(e)}")
            return False

    def clean_memory_content(self, memory_key, memory_value):
        """
        清理记忆内容，去除记忆检索的额外信息，只保留时间戳和基本内容
        
        Args:
            memory_key: 记忆键（用户输入部分）
            memory_value: 记忆值（AI回复部分）
        
        Returns:
            tuple: (清理后的记忆键, 清理后的记忆值)
        """
        # 打印原始内容进行调试
        logger.debug(f"开始清理记忆内容 - 原始键: {memory_key[:100]}")
        logger.debug(f"开始清理记忆内容 - 原始值: {memory_value[:100]}")
        
        # 首先检查AI响应是否包含错误信息
        api_error_keywords = [
            "API调用失败", "API call failed", 
            "Connection error", "连接错误",
            "服务暂时不可用", "请稍后重试",
            "无法回应", "暂时无法回应",
            "Error:", "错误:", "异常:"
        ]
        
        # 直接在clean_memory_content中检查错误，确保不会遗漏
        if any(keyword in memory_value for keyword in api_error_keywords):
            logger.warning(f"在clean_memory_content中检测到API错误信息: {memory_value[:100]}")
            # 返回None表示无效记忆
            return None, None
        
        # 提取时间戳
        timestamp_pattern = r'^\[(.*?)\]'
        timestamp_match = re.search(timestamp_pattern, memory_key)
        timestamp = timestamp_match.group(1) if timestamp_match else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.debug(f"提取的时间戳: {timestamp}")
        
        # 提取用户ID (如果需要)
        user_id_pattern = r'对方\(ID:(.*?)\)'
        user_id_match = re.search(user_id_pattern, memory_key)
        user_id = user_id_match.group(1) if user_id_match else ""
        logger.debug(f"提取的用户ID: {user_id}")
        
        # 提取用户实际输入内容的多种模式尝试
        user_content = ""
        
        # 模式1: "ta 私聊对你说：" 格式
        pattern1 = r'ta 私聊对你说：\s*(.*?)(?:\n\n请注意：|$)'
        match1 = re.search(pattern1, memory_key, re.DOTALL)
        
        # 模式2: "对方(ID:xxx): " 后的内容
        pattern2 = r'对方\(ID:[^)]*\):\s*(.*?)(?:\n\n请注意：|$)'
        match2 = re.search(pattern2, memory_key, re.DOTALL)
        
        # 模式3: 直接从冒号后提取
        pattern3 = r':\s*(.*?)(?:\n\n请注意：|$)'
        match3 = re.search(pattern3, memory_key, re.DOTALL)
        
        # 尝试按顺序匹配
        if match1:
            user_content = match1.group(1).strip()
            logger.debug(f"使用模式1提取用户内容: {user_content[:50]}...")
        elif match2:
            user_content = match2.group(1).strip()
            logger.debug(f"使用模式2提取用户内容: {user_content[:50]}...")
        elif match3:
            user_content = match3.group(1).strip()
            logger.debug(f"使用模式3提取用户内容: {user_content[:50]}...")
        else:
            # 回退：清理特定模式并保留其余内容
            user_content = re.sub(r'\[.*?\]', '', memory_key)  # 移除时间戳
            user_content = re.sub(r'对方\(ID:[^)]*\):', '', user_content)  # 移除ID标记
            user_content = re.sub(r'\n\n请注意：.*$', '', user_content, flags=re.DOTALL)  # 移除提示词
            user_content = user_content.strip()
            logger.debug(f"回退方法提取用户内容: {user_content[:50]}...")
        
        # 提取AI回复内容
        ai_content = ""
        
        # AI回复模式1: "你: " 后的内容
        ai_pattern1 = r'你:\s*(.*?)(?:\n\n以上是用户的沟通内容|$)'
        ai_match1 = re.search(ai_pattern1, memory_value, re.DOTALL)
        
        # AI回复模式2: 移除记忆检索部分并从"你: "后提取
        if ai_match1:
            ai_content = ai_match1.group(1).strip()
            logger.debug(f"使用模式1提取AI内容: {ai_content[:50]}...")
        else:
            # 回退：清理特定模式并保留其余内容
            ai_content = re.sub(r'\[.*?\]', '', memory_value)  # 移除时间戳
            ai_content = re.sub(r'你:', '', ai_content)  # 移除"你:"标记
            ai_content = re.sub(r'\n\n以上是用户的沟通内容.*$', '', ai_content, flags=re.DOTALL)  # 移除记忆检索部分
            ai_content = ai_content.strip()
            logger.debug(f"回退方法提取AI内容: {ai_content[:50]}...")
        
        # 再次检查AI内容是否存在错误信息（可能在提取过程中丢失了一些标记）
        if any(keyword in ai_content for keyword in api_error_keywords):
            logger.warning(f"在清理后的AI内容中检测到API错误信息: {ai_content[:100]}")
            return None, None
            
        # 检查AI内容长度是否过短
        if len(ai_content.strip()) < 10:
            logger.warning(f"AI内容过短，可能是错误信息: {ai_content}")
            return None, None
        
        # 构造最终的干净记忆格式（格式严格统一）
        clean_key = f"[{timestamp}] 对方: {user_content}"
        clean_value = f"[{timestamp}] 你: {ai_content}"
        
        logger.info(f"清理后的用户输入: {clean_key[:100]}")
        logger.info(f"清理后的AI回复: {clean_value[:100]}")
        
        return clean_key, clean_value

    @memory_cache
    def add_short_term_memory(self, user_id, memory_key, memory_value):
        """添加短期记忆"""
        try:
            # 检查short_term_memory是否是有效的对象而不是空字典
            if isinstance(self.short_term_memory, dict):
                logger.warning(f"短期记忆系统是空字典，无法添加记忆，用户ID: {user_id}")
                return False
                
            # 检查short_term_memory对象是否有add_memory方法
            if not hasattr(self.short_term_memory, 'add_memory'):
                logger.warning(f"短期记忆对象没有add_memory方法，尝试使用备选方法存储，用户ID: {user_id}")
                
                # 尝试使用可能存在的其他方法
                if hasattr(self.short_term_memory, 'memory') and hasattr(self.short_term_memory.memory, '__setitem__'):
                    # 直接使用字典赋值
                    self.short_term_memory.memory[memory_key] = memory_value
                    logger.info(f"使用备选方法成功添加短期记忆，用户ID: {user_id}")
                    return True
                else:
                    logger.error(f"无法找到有效的短期记忆存储方法，用户ID: {user_id}")
                    return False
            
            # 正常情况：使用ShortTermMemory的add_memory方法添加记忆
            result = self.short_term_memory.add_memory(memory_key, memory_value)
            if result:
                logger.info(f"添加短期记忆成功，用户ID: {user_id}, 记忆键: {memory_key[:50]}...")
            else:
                logger.warning(f"添加短期记忆失败，用户ID: {user_id}")
            return result
        except Exception as e:
            logger.exception(f"添加短期记忆时发生错误: {str(e)}")
            return False

    def add_short_term_memory_hook(self):
        """
        短期记忆添加钩子，将自身方法注册为LLM的上下文处理器
        在每次对话后被调用，处理用户输入和AI响应以保存到记忆中
        """
        @self.llm.llm.context_handler
        def short_term_memory_add(user_id, user_content, ai_response):
            """
            短期记忆添加钩子的实际处理函数
            
            当上下文内容超过限制并被移除时自动调用
            确保对话内容被保存到短期记忆中以便后续检索
            
            Args:
                user_id: 用户ID
                user_content: 用户输入内容
                ai_response: AI回复内容
                
            Returns:
                bool: 是否成功添加到短期记忆
            """
            try:
                # 添加当前时间戳
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.debug(f"开始处理短期记忆添加 - 用户ID: {user_id}")
                logger.debug(f"原始用户输入: {user_content[:100]}")
                logger.debug(f"原始AI响应: {ai_response[:100]}")
                
                # ===== API调用失败检测 - 增强版 =====
                # 检查是否包含API调用失败的错误信息
                api_error_keywords = [
                    "API调用失败", "API call failed", 
                    "Connection error", "连接错误",
                    "服务暂时不可用", "请稍后重试",
                    "无法回应", "暂时无法回应",
                    "Error:", "错误:", "异常:"
                ]
                
                # 检查AI响应是否包含错误信息
                if any(keyword in ai_response for keyword in api_error_keywords):
                    logger.warning(f"检测到API调用失败信息，用户ID: {user_id}, 内容: {ai_response[:100]}")
                    logger.warning(f"跳过记忆添加")
                    # 不添加这条记忆，直接返回
                    return False
                
                # 检查AI响应长度是否过短（可能是错误信息）
                if len(ai_response.strip()) < 10:
                    logger.warning(f"AI响应过短，可能是错误信息: {ai_response}")
                    logger.warning(f"跳过记忆添加")
                    return False
                
                # 预处理用户输入 - 检查并提取实际内容
                processed_user_content = user_content
                
                # 构建原始记忆格式
                memory_key = f"[{timestamp}] 对方(ID:{user_id}): {processed_user_content}"
                memory_value = f"[{timestamp}] 你: {ai_response}"
                
                # 使用clean_memory_content方法清理记忆
                logger.debug(f"开始清理记忆内容 - 用户ID: {user_id}")
                cleaned_key, cleaned_value = self.clean_memory_content(memory_key, memory_value)
                
                # 检查清理结果是否有效
                if cleaned_key is None or cleaned_value is None:
                    logger.warning(f"清理后的记忆内容无效，跳过记忆添加 - 用户ID: {user_id}")
                    return False
                
                # 记录清理前后长度变化
                original_length = len(memory_key) + len(memory_value)
                cleaned_length = len(cleaned_key) + len(cleaned_value)
                compression_ratio = (original_length - cleaned_length) / original_length * 100 if original_length > 0 else 0
                
                logger.info(f"记忆清理完成 - 用户ID: {user_id}")
                logger.info(f"原始记忆长度: {original_length} 字符")
                logger.info(f"清理后长度: {cleaned_length} 字符")
                logger.info(f"压缩率: {compression_ratio:.2f}%")
                
                # 添加到短期记忆
                logger.debug(f"尝试添加到短期记忆 - 用户ID: {user_id}")
                result = self.add_short_term_memory(user_id, cleaned_key, cleaned_value)
                if result:
                    logger.info(f"成功添加短期记忆 - 用户ID: {user_id}")
                else:
                    logger.warning(f"添加短期记忆失败 - 用户ID: {user_id}")
                
                return result
            except Exception as e:
                logger.exception(f"添加短期记忆时发生错误: {str(e)}")
                return False
                
        # 记录添加钩子
        logger.info("已注册短期记忆添加钩子")
        return True

    def _add_important_memory(self, message: str, user_id: str):
        """
        添加重要记忆 - 修改为接收用户输入内容
        
        Args:
            message: 用户输入内容
            user_id: 用户ID
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        memory_content = f'["{timestamp} 用户{user_id}的重要记忆"] = "[{timestamp}] 重要记忆内容: {message}"'

        # 写入关键记忆
        self.key_memory.add_memory(memory_content)
        logger.info(f"成功写入重要记忆: 用户{user_id} - {message[:50]}...")

    def check_important_memory(self, message: str, user_id: str):
        """
        检查消息是否包含关键词并添加重要记忆
        
        Args:
            message: 用户输入的消息
            user_id: 用户ID
        
        Returns:
            bool: 是否找到关键词
        """
        if any(keyword in message for keyword in KEYWORDS):
            self._add_important_memory(message, user_id)
            return True
        return False

    def get_relevant_memories(self, query: str, user_id: Optional[str] = None) -> List[str]:
        """获取相关记忆，只在用户主动询问时检索重要记忆和长期记忆"""
        import concurrent.futures
        import time
        
        # 保护性检查
        if not query:
            logger.warning("查询为空，无法检索记忆")
            return []
            
        # 保护性检查，确保user_id始终有值
        if user_id is None:
            user_id = "unknown"
            logger.warning(f"查询记忆时用户ID为空，使用默认值: {user_id}")
        
        content = f"[{user_id}]:{query}"
        logger.info(f"开始记忆查询，用户: {user_id}, 查询内容: {query[:50]}...")
        
        # 创建一个结果容器
        memories_result = {
            'long_term': [],
            'short_term': []
        }
        
        def _query_long_term():
            """查询长期记忆与关键记忆"""
            try:
                # 检查组合RAG是否可用
                if self.lg_tm_m_and_k_m is None:
                    logger.warning("长期记忆RAG不可用，跳过查询")
                    return []
                    
                # 使用异步模式查询
                return self.lg_tm_m_and_k_m.query(content, self.top_k, self.is_rerank, async_mode=True, timeout=4.0)
            except Exception as e:
                logger.error(f"查询长期记忆时出错: {str(e)}")
                return []
        
        def _query_short_term():
            """查询短期记忆"""
            try:
                # 检查短期记忆是否可用
                if isinstance(self.short_term_memory, dict):
                    logger.warning("短期记忆不可用，跳过查询")
                    return []
                    
                # 检查rag属性是否存在
                if not hasattr(self.short_term_memory, 'rag') or self.short_term_memory.rag is None:
                    logger.warning("短期记忆RAG不可用，跳过查询")
                    return []
                    
                # 使用异步模式查询
                return self.short_term_memory.rag.query(content, self.top_k, self.is_rerank, async_mode=True, timeout=4.0)
            except Exception as e:
                logger.error(f"查询短期记忆时出错: {str(e)}")
                return []
        
        # 设置超时时间 (秒)
        timeout = 5.0
        
        # 使用线程池异步执行查询
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # 提交查询任务
            long_term_future = executor.submit(_query_long_term)
            short_term_future = executor.submit(_query_short_term)
            
            # 等待查询完成或超时
            start_time = time.time()
            
            # 处理长期记忆查询结果
            try:
                # 最多等待剩余的超时时间
                remaining_time = max(0.1, timeout - (time.time() - start_time))
                memories_result['long_term'] = long_term_future.result(timeout=remaining_time)
                logger.info(f"长期记忆查询成功，找到 {len(memories_result['long_term'])} 条记忆")
            except concurrent.futures.TimeoutError:
                logger.warning(f"长期记忆查询超时，已跳过")
            except Exception as e:
                logger.error(f"获取长期记忆查询结果时出错: {str(e)}")
            
            # 处理短期记忆查询结果
            try:
                # 最多等待剩余的超时时间
                remaining_time = max(0.1, timeout - (time.time() - start_time))
                memories_result['short_term'] = short_term_future.result(timeout=remaining_time)
                logger.info(f"短期记忆查询成功，找到 {len(memories_result['short_term'])} 条记忆")
            except concurrent.futures.TimeoutError:
                logger.warning(f"短期记忆查询超时，已跳过")
            except Exception as e:
                logger.error(f"获取短期记忆查询结果时出错: {str(e)}")
        
        # 合并并去重所有记忆
        all_memories = []
        
        # 保护性检查
        if isinstance(memories_result.get('long_term'), list):
            all_memories.extend(memories_result['long_term'])
        
        if isinstance(memories_result.get('short_term'), list):
            all_memories.extend(memories_result['short_term'])
        
        # 保护性检查，确保只处理字符串
        all_memories = [m for m in all_memories if isinstance(m, str)]
        
        # 使用集合去重
        unique_memories = list(set(all_memories))
        
        # 按时间戳排序（如果记忆包含时间戳）
        try:
            unique_memories.sort(key=lambda x: x.split(']')[0] if ']' in x else x)
        except Exception as e:
            logger.error(f"排序记忆时出错: {str(e)}")
            # 出错时不排序
        
        logger.info(f"记忆查询完成，共找到 {len(unique_memories)} 条去重后的记忆")
        return unique_memories

    def add_long_term_memory_process_task(self):
        """
        添加长期记忆处理任务
        这个方法会启动一个线程，定期处理长期记忆，按用户ID分开处理
        """
        try:
            # 从配置获取保存间隔时间(分钟)
            from src.config import config
            # 修正配置路径 - 使用正确的配置路径结构
            # 可能配置在 categories.memory_settings.long_term_memory.save_interval
            save_interval = config["categories"]["memory_settings"]["long_term_memory"]["save_interval"]
            
            # 创建并启动定时器线程
            def process_memory():
                try:
                    # 获取所有短期记忆，并按用户ID进行分组
                    all_memories = self.short_term_memory.memory.get_key_value_pairs()
                    
                    # 空记忆检查
                    if not all_memories:
                        logger.info("没有短期记忆需要处理")
                        return
                        
                    user_memories = {}
                    
                    # 解析记忆并按用户ID分组
                    for key, value in all_memories:
                        # 假设格式为 "[timestamp] 对方(ID:user_id): content"
                        user_id_match = re.search(r'对方\(ID:(.*?)\):', key)
                        if user_id_match:
                            user_id = user_id_match.group(1)
                            if user_id not in user_memories:
                                user_memories[user_id] = []
                            user_memories[user_id].append((key, value))
                    
                    # 针对每个用户分别处理长期记忆
                    for user_id, memories in user_memories.items():
                        # 调用长期记忆处理方法，传入用户ID和该用户的记忆
                        logger.info(f"处理用户 {user_id} 的长期记忆，共 {len(memories)} 条记录")
                        self.long_term_memory.add_memory(memories, user_id)
                    
                    # 清空短期记忆文档和索引
                    self.short_term_memory.memory.settings.clear()
                    self.short_term_memory.rag.documents.clear()
                    self.short_term_memory.rag.index.clear()

                    logger.info(f"成功处理全部短期记忆到长期记忆")
                except Exception as e:
                    logger.error(f"处理长期记忆失败: {str(e)}")
                
                # 处理完成后执行去重
                logger.info("长期记忆处理完成，执行去重清理...")
                if hasattr(self.short_term_memory, 'rag'):
                    self.short_term_memory.rag.deduplicate_documents()
                if hasattr(self, 'lg_tm_m_and_k_m'):
                    self.lg_tm_m_and_k_m.deduplicate_documents()
                
                logger.info("去重清理完成")
            
            import threading
            import time
            
            def timer_thread():
                while True:
                    # 休眠指定时间间隔(转换为秒)
                    time.sleep(save_interval * 60)
                    # 先休眠再处理
                    process_memory()
            
            thread = threading.Thread(target=timer_thread, daemon=True)
            thread.start()
            
            logger.info(f"已启动长期记忆处理线程,间隔时间:{save_interval}分钟")
            
        except Exception as e:
            logger.error(f"启动长期记忆处理线程失败: {str(e)}")

    def initialize_memory(self):
        """初始化记忆系统，执行首次去重"""
        # 系统初始化时执行一次全面去重
        if hasattr(self.short_term_memory, 'rag'):
            self.short_term_memory.rag.deduplicate_documents()
        
        # 初始化后定期执行去重的定时任务
        self._setup_deduplication_task()

    def _setup_deduplication_task(self):
        """设置定期去重任务"""
        import threading
        import time
        
        def deduplication_thread():
            while True:
                # 每24小时执行一次去重
                time.sleep(24 * 60 * 60)  # 24小时
                try:
                    logger.info("执行定期去重任务...")
                    # 对短期记忆进行去重
                    if hasattr(self.short_term_memory, 'rag'):
                        self.short_term_memory.rag.deduplicate_documents()
                    
                    # 对长期记忆进行去重 (如果需要)
                    if hasattr(self, 'lg_tm_m_and_k_m'):
                        self.lg_tm_m_and_k_m.deduplicate_documents()
                    
                    logger.info("定期去重任务完成")
                except Exception as e:
                    logger.error(f"定期去重任务失败: {str(e)}")
        
        # 启动定期去重线程
        thread = threading.Thread(target=deduplication_thread, daemon=True)
        thread.start()
        logger.info("已启动定期去重任务线程")

    def add_short_memory(self, user_message, ai_message, user_id):
        """
        添加对话到短期记忆
        
        Args:
            user_message: 用户消息
            ai_message: AI回复
            user_id: 用户ID
        """
        try:
            self.logger.info(f"主动添加对话到短期记忆 - 用户: {user_id}")
            
            # 获取调用堆栈信息，用于调试
            import traceback
            caller = traceback.extract_stack()[-2]
            self.logger.info(f"记忆添加调用源: {caller.filename}:{caller.lineno}")
            
            # 检查消息是否为None或空
            if user_message is None or ai_message is None:
                self.logger.error(f"添加记忆时发现空消息: user_message={user_message}, ai_message={ai_message}")
                return False
                
            # 检查AI消息是否包含错误信息
            if isinstance(ai_message, str) and "API调用失败" in ai_message:
                self.logger.warning(f"跳过包含API错误的消息添加: {ai_message[:100]}...")
                return False
            
            # 构建记忆键和值
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            memory_key = f"{timestamp} 对方: {user_message}"
            memory_value = f"{timestamp} 你: {ai_message}"
            
            # 应用清理函数
            cleaned_key, cleaned_value = self.clean_memory_content(memory_key, memory_value)
            
            # 检查清理后的内容是否有效
            if not cleaned_key or not cleaned_value:
                self.logger.warning("清理后的记忆内容为空，跳过添加")
                return False
                
            # 记录原始和清理后的内容长度
            self.logger.debug(f"原始内容长度: key={len(memory_key)}, value={len(memory_value)}")
            self.logger.debug(f"清理后内容长度: key={len(cleaned_key)}, value={len(cleaned_value)}")
            
            # 添加到短期记忆
            self.short_term_memory.add_memory(
                user_id=user_id,
                memory_key=cleaned_key,
                memory_value=cleaned_value
            )
            return True
        except Exception as e:
            self.logger.error(f"保存对话记忆失败: {str(e)}")
            return False

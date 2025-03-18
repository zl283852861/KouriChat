import os
import logging
from typing import List, Optional, Dict  # 添加 Dict 导入
from datetime import datetime
from src.memories.key_memory import KeyMemory
from src.memories.long_term_memory import LongTermMemory
from src.memories.memory.core.rag import RAG, OnlineCrossEncoderReRanker, OnlineEmbeddingModel, LocalEmbeddingModel, HybridEmbeddingModel
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
        reranker_model_name = config.rag.reranker_model
        
        # 如果未设置嵌入模型特定配置，则使用LLM模块的同样配置
        if not api_key or not isinstance(api_key, str) or not api_key.strip():
            logger.info("未设置嵌入API密钥，使用LLM模块配置")
            api_key = config.llm.api_key
            
        if not base_url or not isinstance(base_url, str) or not base_url.strip():
            logger.info("未设置嵌入API基础URL，使用LLM模块配置")
            base_url = config.llm.base_url
        
        # 根据LLM提供商自动匹配合适的嵌入模型和重排模型
        is_siliconflow = False
        if base_url and "siliconflow" in base_url.lower():
            is_siliconflow = True
            # 检查是否启用了自动适配功能
            auto_adapt = True
            if hasattr(config.rag, 'auto_adapt_siliconflow'):
                auto_adapt = config.rag.auto_adapt_siliconflow
                
            if auto_adapt:
                logger.info("检测到使用硅基流动API，且自动适配已开启")
                if embedding_model_name == "text-embedding-3-large" or not embedding_model_name:
                    embedding_model_name = "BAAI/bge-m3"
                    logger.info(f"自动调整嵌入模型为: {embedding_model_name}")
                # 保持重排模型为原有LLM
                if reranker_model_name != config.llm.model:
                    reranker_model_name = config.llm.model
                    logger.info(f"自动调整重排模型为当前LLM模型: {reranker_model_name}")
            else:
                logger.info("检测到使用硅基流动API，但自动适配已关闭，使用原始配置")
        else:
            logger.info(f"使用标准API服务，嵌入模型: {embedding_model_name}")
            if not reranker_model_name or reranker_model_name.strip() == "":
                reranker_model_name = config.llm.model
                logger.info(f"未指定重排模型，使用当前LLM模型: {reranker_model_name}")
        
        logger.info(f"嵌入模型配置: 模型={embedding_model_name}, 基础URL={base_url}")
        logger.info(f"重排模型配置: 模型={reranker_model_name}, 基础URL={base_url}")
        
        # 确保API参数有效
        if not api_key or not isinstance(api_key, str) or not api_key.strip():
            logger.warning("所有配置源中均未设置有效的API密钥，使用空值")
            api_key = "sk-dummy-key"
        
        # 创建嵌入模型
        api_embedding_model = OnlineEmbeddingModel(
            api_key=api_key,
            base_url=base_url,
            model_name=embedding_model_name
        )
        
        # 获取本地模型自动下载配置
        # 可以在配置中添加auto_download_local_model选项，或者使用环境变量
        # auto_download可以有三种状态:
        # - True: 自动下载，不询问
        # - False: 不下载，不询问
        # - None: 交互模式，询问用户是否下载
        auto_download = None  # 默认为交互模式
        
        # 尝试从配置中获取
        if hasattr(config.rag, 'auto_download_local_model'):
            config_value = config.rag.auto_download_local_model
            # 检查配置值类型和内容
            if isinstance(config_value, bool):
                auto_download = config_value
                logger.info(f"从配置中获取本地模型自动下载设置: {auto_download} (布尔值)")
            elif isinstance(config_value, str):
                if config_value.lower() in ('true', 'yes', 'y', '1'):
                    auto_download = True
                    logger.info(f"从配置中获取本地模型自动下载设置: {auto_download} (字符串转布尔值)")
                elif config_value.lower() in ('interactive', 'ask', 'prompt', 'i'):
                    auto_download = None
                    logger.info("从配置中获取本地模型自动下载设置: 交互模式")
                elif config_value.lower() in ('false', 'no', 'n', '0'):
                    auto_download = False
                    logger.info(f"从配置中获取本地模型自动下载设置: {auto_download} (字符串转布尔值)")
        
        # 尝试从环境变量获取
        env_auto_download = os.environ.get('AUTO_DOWNLOAD_LOCAL_MODEL')
        if env_auto_download is not None:
            if env_auto_download.lower() in ('true', '1', 'yes', 'y'):
                auto_download = True
                logger.info(f"从环境变量获取本地模型自动下载设置: {auto_download}")
            elif env_auto_download.lower() in ('interactive', 'ask', 'prompt', 'i'):
                auto_download = None
                logger.info("从环境变量获取本地模型自动下载设置: 交互模式")
            elif env_auto_download.lower() in ('false', '0', 'no', 'n'):
                auto_download = False
                logger.info(f"从环境变量获取本地模型自动下载设置: {auto_download}")
        
        # 获取首次运行标志，如果是首次运行且没有明确设置，则使用交互模式
        first_run_flag_file = os.path.join(os.path.expanduser("~"), ".kourichat_first_run")
        is_first_run = not os.path.exists(first_run_flag_file)
        
        if is_first_run and auto_download is not None:
            # 首次运行时，若配置不是交互模式，记录信息但仍使用交互模式
            logger.info(f"首次运行检测，虽然配置为 {auto_download}，但将使用交互模式询问用户")
            auto_download = None
            
            # 创建首次运行标志文件
            try:
                with open(first_run_flag_file, 'w') as f:
                    f.write(f"首次运行时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            except:
                logger.warning("无法创建首次运行标志文件")
        
        logger.info(f"最终本地模型下载设置: {'交互模式' if auto_download is None else auto_download}")
        
        # 创建混合嵌入模型，优先使用API模型，允许用户选择是否下载本地备用模型
        hybrid_embedding_model = HybridEmbeddingModel(
            api_model=api_embedding_model,
            local_model_path=LOCAL_EMBEDDING_MODEL_PATH,
            auto_download=auto_download
        )

        # 初始化Rag记忆的方法
        # 2025-03-15修改，使用ShortTermMemory单例模式
        self.short_term_memory = ShortTermMemory.get_instance(
            memory_path=os.path.join(self.memory_base_dir, "rag-memory.json"),
            embedding_model=hybrid_embedding_model,
            reranker=OnlineCrossEncoderReRanker(
                api_key=api_key,
                base_url=base_url,
                model_name=reranker_model_name
            ) if config.rag.is_rerank is True else None
        )
        self.key_memory = KeyMemory.get_instance(
            get_saver(is_long_term=False)
        )
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
        self.is_rerank = config.rag.is_rerank
        self.top_k = config.rag.top_k
        self.short_term_memory.start_memory()
        self.add_short_term_memory_hook()

        # 初始化一个长期记忆和关键记忆的组合rag，也使用混合嵌入模型
        self.lg_tm_m_and_k_m = RAG(
            embedding_model=hybrid_embedding_model,
            reranker=OnlineCrossEncoderReRanker(
                api_key=api_key,
                base_url=base_url,
                model_name=reranker_model_name
            ) if config.rag.is_rerank is True else None
        )
        self.init_lg_tm_m_and_k_m()
        self.add_long_term_memory_process_task()
        self.initialize_memory()
    
    def init_lg_tm_m_and_k_m(self):
        """
        初始化长期记忆和关键记忆的组合rag库
        """
        self.lg_tm_m_and_k_m.add_documents(self.long_term_memory.get_memories())
        self.lg_tm_m_and_k_m.add_documents(self.key_memory.get_memory())

    def clean_memory_content(self, memory_key, memory_value):
        """
        清理记忆内容，去除记忆检索的额外信息
        
        Args:
            memory_key: 记忆键（AI回复部分）
            memory_value: 记忆值（用户输入部分）
        
        Returns:
            tuple: (清理后的记忆键, 清理后的记忆值)
        """
        # 提取AI回复（键）
        ai_pattern = r'^\[(.*?)\] 对方\(ID:(.*?)\): (.*?)$'
        ai_match = re.match(ai_pattern, memory_key)
        if ai_match:
            timestamp, user_id, ai_response = ai_match.groups()
            clean_key = f"[{timestamp}] 对方(ID:{user_id}): {ai_response}"
        else:
            clean_key = memory_key
        
        # 提取用户输入（值）- 改进正则表达式以更精确匹配
        user_pattern = r'^\[(.*?)\] 你: (.*?)(?:\n以上是用户的沟通内容.*)?$'
        user_match = re.match(user_pattern, memory_value, re.DOTALL)
        if user_match:
            timestamp, user_input = user_match.groups()
            clean_value = f"[{timestamp}] 你: {user_input}"
        else:
            clean_value = memory_value
        
        return clean_key, clean_value

    def add_short_term_memory_hook(self):
        """添加短期记忆监听器方法"""
        @self.llm.llm.context_handler
        def short_term_memory_add(context_key, user_response, ai_response):
            try:
                # 添加日志开始
                logger.info(f"开始添加短期记忆 - 用户ID: {context_key}")
                
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 检查是否包含记忆检索内容，并清理
                if "\n以上是用户的沟通内容；以下是记忆中检索的内容：" in user_response:
                    user_response = user_response.split("\n以上是用户的沟通内容")[0]
                    logger.info("清理了包含记忆检索的内容")
                    
                memory_key = f"[{timestamp}] 对方(ID:{context_key}): {user_response}"
                memory_value = f"[{timestamp}] 你: {ai_response}"
                
                # 记录原始内容长度
                logger.info(f"原始记忆长度 - 键: {len(memory_key)}, 值: {len(memory_value)}")
                
                # 再次清理确保干净
                memory_key, memory_value = self.clean_memory_content(memory_key, memory_value)
                
                # 记录清理后内容长度
                logger.info(f"清理后记忆长度 - 键: {len(memory_key)}, 值: {len(memory_value)}")
                
                # 使用add_memory方法，确保执行去重检查
                self.short_term_memory.add_memory(memory_key, memory_value)
                
                # 验证记忆是否添加成功
                if memory_key in self.short_term_memory.memory.settings:
                    logger.info(f"短期记忆添加成功 - 用户ID: {context_key}")
                else:
                    logger.warning(f"短期记忆可能未添加成功 - 用户ID: {context_key}")
            except Exception as e:
                logger.error(f"添加短期记忆失败: {str(e)}", exc_info=True)

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
        
        content = f"[{user_id}]:{query}"
        
        # 创建一个结果容器
        memories_result = {
            'long_term': [],
            'short_term': []
        }
        
        def _query_long_term():
            """查询长期记忆与关键记忆"""
            try:
                # 使用异步模式查询
                return self.lg_tm_m_and_k_m.query(content, self.top_k, self.is_rerank, async_mode=True, timeout=4.0)
            except Exception as e:
                logger.error(f"查询长期记忆时出错: {str(e)}")
                return []
        
        def _query_short_term():
            """查询短期记忆"""
            try:
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
        all_memories = memories_result['long_term'] + memories_result['short_term']
        
        # 使用集合去重
        unique_memories = list(set(all_memories))
        
        # 按时间戳排序（如果记忆包含时间戳）
        unique_memories.sort(key=lambda x: x.split(']')[0] if ']' in x else x)
        
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

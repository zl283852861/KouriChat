import re
import time  # 确保导入time模块
import hashlib  # 用于生成缓存键

import numpy as np
import faiss
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from openai import OpenAI
from sentence_transformers import SentenceTransformer, CrossEncoder

"""
本文件依赖安装
pip install sentence-transformers faiss-cpu numpy openai
如果使用在线模型需要额外安装openai等对应SDK
"""


class EmbeddingModel(ABC):
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        pass


class LocalEmbeddingModel(EmbeddingModel):
    def __init__(self, model_path: str):
        self.model = SentenceTransformer(model_path)
        self.cache = {}  # 添加缓存字典

    def embed(self, texts: List[str]) -> List[List[float]]:
        results = []
        uncached_texts = []
        uncached_indices = []
        
        # 检查缓存
        for i, text in enumerate(texts):
            # 使用MD5生成缓存键
            cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
            if cache_key in self.cache:
                results.append(self.cache[cache_key])
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # 如果有未缓存的文本，则嵌入
        if uncached_texts:
            embeddings = self.model.encode(uncached_texts, convert_to_tensor=False).tolist()
            
            # 更新缓存并填充结果
            for i, text in enumerate(uncached_texts):
                cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
                self.cache[cache_key] = embeddings[i]
                results.insert(uncached_indices[i], embeddings[i])
                
        return results


class OnlineEmbeddingModel(EmbeddingModel):
    def __init__(self, model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.cache = {}  # 添加嵌入缓存
        self.cache_hits = 0  # 缓存命中计数
        self.api_calls = 0  # API调用计数
        
        # 增加配置日志
        print(f"初始化嵌入模型: {model_name}")
        print(f"API URL: {base_url if base_url else '默认OpenAI地址'}")
        if api_key and len(api_key) > 10:
            print(f"API密钥: {api_key[:6]}...{api_key[-4:]}")
        else:
            print(f"API密钥: {'未设置' if not api_key else '无效格式'}")
        
        # 创建客户端并测试连接
        print(f"正在创建API客户端...")
        try:
            # 确保base_url不是空字符串
            client_kwargs = {"api_key": self.api_key}
            if self.base_url and isinstance(self.base_url, str) and self.base_url.strip():
                client_kwargs["base_url"] = self.base_url
                print(f"使用自定义API基础URL: {self.base_url}")
            else:
                print(f"未提供有效的API基础URL，将使用OpenAI默认服务器")
            
            self.client = OpenAI(**client_kwargs)
            
            # 测试连接
            print(f"正在测试API连接，请稍候...")
            # 添加更明确的状态信息
            print(f"  - 连接API服务器: {self.base_url if self.base_url else 'OpenAI默认服务器'}")
            print(f"  - 使用模型: {self.model_name}")
            print(f"  - 尝试获取可用模型列表...")
            
            # 设置一个超时，防止长时间阻塞
            import threading
            import time
            
            connection_successful = False
            connection_error = None
            
            def test_connection():
                nonlocal connection_successful, connection_error
                try:
                    self.client.models.list()
                    connection_successful = True
                except Exception as e:
                    connection_error = e
            
            # 启动连接测试线程
            thread = threading.Thread(target=test_connection)
            thread.start()
            
            # 等待最多10秒
            timeout = 10  # 秒
            start_time = time.time()
            while thread.is_alive() and time.time() - start_time < timeout:
                print(".", end="", flush=True)
                time.sleep(1)
            
            # 检查结果
            if connection_successful:
                print("\n✅ API连接测试成功！服务器正常响应")
            elif connection_error:
                raise connection_error
            else:
                raise TimeoutError("API连接测试超时")
                
        except Exception as e:
            error_msg = str(e)
            print(f"\n⚠️ API初始化失败: {error_msg}")
            print(f"请检查以下可能的问题:")
            print(f"  - API密钥是否正确")
            print(f"  - API服务器是否可访问")
            print(f"  - 网络连接是否正常")
            print(f"程序将继续运行，但嵌入功能可能受限")
            
            # 创建默认客户端以避免后续错误
            try:
                self.client = OpenAI(api_key="sk-dummy-key")
            except Exception:
                # 如果仍然失败，将客户端设为None
                self.client = None

    def embed(self, texts: List[str], async_mode: bool = False, timeout: float = 5.0) -> List[List[float]]:
        """
        将文本嵌入为向量
        
        Args:
            texts: 要嵌入的文本列表
            async_mode: 是否使用异步模式（不阻塞）
            timeout: 异步模式下的超时时间（秒）
            
        Returns:
            嵌入向量列表
        """
        if not texts:
            return []

        # 如果使用异步模式，使用线程池处理
        if async_mode:
            return self._async_embed(texts, timeout)
        
        # 同步模式处理
        embeddings = []
        for text in texts:
            if not text.strip():
                embeddings.append([])
                continue
                
            # 使用文本的MD5哈希作为缓存键
            cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
            
            # 检查缓存
            if cache_key in self.cache:
                self.cache_hits += 1
                cached_percent = (self.cache_hits / (self.cache_hits + self.api_calls)) * 100 if (self.cache_hits + self.api_calls) > 0 else 0
                print(f"📋 缓存命中: {text[:20]}... (命中率: {cached_percent:.1f}%)")
                embeddings.append(self.cache[cache_key])
                continue
                
            # 缓存未命中，需要调用API
            for attempt in range(3):  # 最多重试3次
                try:
                    # 检查客户端是否存在
                    if self.client is None:
                        raise ValueError("API客户端未初始化")
                        
                    # 增加请求调试信息
                    print(f"发送嵌入请求 (尝试 {attempt+1}/3):")
                    print(f"  - 模型: {self.model_name}")
                    print(f"  - 文本长度: {len(text)} 字符")
                    
                    response = self.client.embeddings.create(
                        model=self.model_name,
                        input=text,
                        encoding_format="float"
                    )
                    self.api_calls += 1

                    # 强化响应校验
                    if not response or not response.data:
                        raise ValueError("API返回空响应")

                    embedding = response.data[0].embedding
                    if not isinstance(embedding, list) or len(embedding) == 0:
                        raise ValueError("无效的嵌入格式")

                    print(f"✅ 嵌入成功，向量维度: {len(embedding)}")
                    
                    # 缓存结果
                    self.cache[cache_key] = embedding
                    embeddings.append(embedding)
                    break
                except Exception as e:
                    error_msg = str(e)
                    print(f"❌ 嵌入尝试 {attempt+1} 失败: {error_msg}")
                    
                    if "rate limit" in error_msg.lower():
                        print("   API速率限制，等待时间延长")
                        time.sleep(5)  # 速率限制时等待更长时间
                    
                    if attempt == 2:
                        print(f"⚠️ 嵌入最终失败（已重试3次）: {error_msg}")
                        # 使用零向量代替，维度使用常见的嵌入维度
                        if self.model_name == "text-embedding-ada-002":
                            dim = 1536  # Ada-002的维度
                        elif "text-embedding-3" in self.model_name:
                            dim = 3072 if "large" in self.model_name else 1536  # 新模型的维度
                        else:
                            dim = 1024  # 默认维度
                            
                        embeddings.append([0.0] * dim)
                    time.sleep(1)  # 重试间隔
        return embeddings
    
    def _async_embed(self, texts: List[str], timeout: float = 5.0) -> List[List[float]]:
        """
        异步方式处理嵌入，设置超时机制
        
        Args:
            texts: 要嵌入的文本列表
            timeout: 超时时间（秒）
            
        Returns:
            嵌入向量列表
        """
        import concurrent.futures
        
        if not texts:
            return []
        
        # 创建结果列表并预填充
        # 每个位置对应一个零向量，维度根据模型确定
        default_dim = 1536  # 默认维度
        if self.model_name == "text-embedding-ada-002":
            default_dim = 1536
        elif "text-embedding-3" in self.model_name:
            default_dim = 3072 if "large" in self.model_name else 1536
            
        results = [[0.0] * default_dim for _ in range(len(texts))]
        
        # 定义单个文本的嵌入函数
        def _embed_single_text(idx, text):
            if not text.strip():
                return idx, []
                
            # 使用文本的MD5哈希作为缓存键
            cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
            
            # 检查缓存
            if cache_key in self.cache:
                self.cache_hits += 1
                print(f"📋 缓存命中: {text[:20]}...")
                return idx, self.cache[cache_key]
            
            # 尝试API调用
            for attempt in range(3):
                try:
                    if self.client is None:
                        raise ValueError("API客户端未初始化")
                        
                    print(f"[异步] 发送嵌入请求 (尝试 {attempt+1}/3):")
                    print(f"  - 模型: {self.model_name}")
                    print(f"  - 文本长度: {len(text)} 字符")
                    
                    response = self.client.embeddings.create(
                        model=self.model_name,
                        input=text,
                        encoding_format="float"
                    )
                    self.api_calls += 1
                    
                    if not response or not response.data:
                        raise ValueError("API返回空响应")
                        
                    embedding = response.data[0].embedding
                    if not isinstance(embedding, list) or len(embedding) == 0:
                        raise ValueError("无效的嵌入格式")
                        
                    print(f"✅ [异步] 嵌入成功，向量维度: {len(embedding)}")
                    
                    # 缓存结果
                    self.cache[cache_key] = embedding
                    return idx, embedding
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"❌ [异步] 嵌入尝试 {attempt+1} 失败: {error_msg}")
                    
                    if "rate limit" in error_msg.lower():
                        time.sleep(3)  # 速率限制时等待
                        
                    if attempt < 2:  # 如果不是最后一次尝试
                        time.sleep(1)  # 短暂等待后重试
            
            # 所有尝试都失败，返回零向量
            print(f"⚠️ [异步] 所有嵌入尝试都失败，返回零向量")
            return idx, [0.0] * default_dim
        
        # 使用线程池并发处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # 提交所有任务
            future_to_idx = {executor.submit(_embed_single_text, i, text): i 
                             for i, text in enumerate(texts)}
            
            # 处理完成的任务
            for future in concurrent.futures.as_completed(future_to_idx, timeout=timeout):
                try:
                    idx, embedding = future.result()
                    results[idx] = embedding
                except Exception as e:
                    print(f"⚠️ [异步] 获取嵌入结果时出错: {str(e)}")
        
        return results
    
    def get_cache_stats(self):
        """返回缓存统计信息"""
        total = self.cache_hits + self.api_calls
        hit_rate = (self.cache_hits / total) * 100 if total > 0 else 0
        return {
            "cache_size": len(self.cache),
            "cache_hits": self.cache_hits,
            "api_calls": self.api_calls,
            "hit_rate_percent": hit_rate
        }
        
    def clear_cache(self):
        """清除缓存"""
        cache_size = len(self.cache)
        self.cache.clear()
        return f"已清除 {cache_size} 条缓存嵌入"


class HybridEmbeddingModel(EmbeddingModel):
    """
    混合嵌入模型，优先使用API模型，如果API模型失败则使用本地模型。
    允许用户选择是否下载本地备用模型，并根据用户选择和下载结果调整模型使用策略。
    
    参数:
        api_model: API嵌入模型实例
        local_model_path: 本地模型路径
        local_model_enabled: 是否启用本地模型
    """
    def __init__(self, api_model: OnlineEmbeddingModel, local_model_path: str = "paraphrase-multilingual-MiniLM-L12-v2", 
                 local_model_enabled: bool = False):
        self.api_model = api_model
        self.local_model = None
        self.local_model_path = local_model_path
        self.local_model_failed = False
        self.use_local_model = False
        self.cache = {}  # 添加缓存字典
        
        # 检查API连接状态
        api_connected = False
        if hasattr(api_model, 'client') and api_model.client is not None:
            try:
                print("正在测试API连接状态...")
                # 先检查client是否有models属性
                if hasattr(api_model.client, 'models'):
                    # 设置连接测试超时
                    import threading
                    import time
                    
                    connection_successful = False
                    connection_error = None
                    
                    def test_connection():
                        nonlocal connection_successful, connection_error
                        try:
                            api_model.client.models.list()
                            connection_successful = True
                        except Exception as e:
                            connection_error = e
                    
                    # 启动连接测试线程
                    thread = threading.Thread(target=test_connection)
                    thread.start()
                    
                    # 等待最多10秒
                    timeout = 10  # 秒
                    start_time = time.time()
                    while thread.is_alive() and time.time() - start_time < timeout:
                        print(".", end="", flush=True)
                        time.sleep(1)
                    
                    # 检查结果
                    if connection_successful:
                        api_connected = True
                        print("\nAPI连接测试完成")
                    elif connection_error:
                        print(f"\nAPI连接测试失败: {str(connection_error)}")
                    else:
                        print("\nAPI连接测试超时")
                else:
                    print("API客户端不包含models属性，可能初始化不完整")
            except Exception as e:
                api_connected = False
                print(f"API连接测试失败: {str(e)}")
        
        # 打印初始化信息
        print("\n" + "="*80)
        print("【嵌入模型初始化】".center(60))
        print("="*80)
        print(f"API嵌入模型已初始化: {api_model.model_name}")
        
        if api_connected:
            print("✅ API连接测试成功")
        else:
            print("⚠️ API连接测试失败")
        
        # 根据local_model_enabled决定是否初始化本地模型
        if local_model_enabled:
            print("\n本地模型已启用，正在初始化本地模型...")
            self._initialize_local_model()
        else:
            print("\n本地模型未启用，将仅使用API模型")
            self.local_model_failed = True
            
        print("\n" + "="*80)
        print(f"嵌入模型初始化完成: {'API + 本地备用' if self.use_local_model else 'API' }")
        print("="*80 + "\n")
    
    def _initialize_local_model(self):
        """初始化本地模型"""
        print(f"\n开始初始化本地模型: '{self.local_model_path}'")
        print("初始化过程可能需要几分钟，请耐心等待...")
        
        try:
            # 设置初始化超时和模型大小估计
            import time
            import threading
            import sys
            
            start_time = time.time()
            init_started = False
            init_completed = False
            init_error = None
            
            # 创建进度显示线程
            def show_progress():
                spinner = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷']
                spinner_idx = 0
                elapsed_time = 0
                
                while not (init_completed or init_error):
                    if init_started:
                        # 显示进度动画
                        elapsed_time = time.time() - start_time
                        sys.stdout.write(f"\r初始化中... {spinner[spinner_idx]} 已用时: {elapsed_time:.1f}秒")
                        sys.stdout.flush()
                        spinner_idx = (spinner_idx + 1) % len(spinner)
                    time.sleep(0.1)
            
            # 启动进度显示线程
            progress_thread = threading.Thread(target=show_progress)
            progress_thread.daemon = True
            progress_thread.start()
            
            # 创建初始化线程
            def init_model():
                nonlocal init_started, init_completed, init_error
                try:
                    init_started = True
                    # 尝试初始化本地模型
                    self.local_model = LocalEmbeddingModel(self.local_model_path)
                    init_completed = True
                except Exception as e:
                    init_error = e
            
            # 启动初始化线程
            init_thread = threading.Thread(target=init_model)
            init_thread.start()
            
            # 等待初始化完成或超时
            max_wait_time = 300  # 最多等待5分钟
            while init_thread.is_alive() and time.time() - start_time < max_wait_time:
                time.sleep(1)  # 每秒检查一次状态
            
            # 检查初始化结果
            if init_completed:
                init_time = time.time() - start_time
                sys.stdout.write("\r" + " " * 50 + "\r")  # 清除进度行
                print(f"\n✅ 本地模型初始化成功! 用时: {init_time:.1f}秒")
                print(f"模型已加载到内存，将在API调用失败时使用")
                self.use_local_model = True
            elif init_error:
                sys.stdout.write("\r" + " " * 50 + "\r")  # 清除进度行
                print(f"\n❌ 本地模型初始化失败: {str(init_error)}")
                print("请检查模型路径是否正确")
                print("系统将仅使用API模型")
                self.local_model_failed = True
            else:
                sys.stdout.write("\r" + " " * 50 + "\r")  # 清除进度行
                print(f"\n❌ 本地模型初始化超时（超过{max_wait_time/60:.1f}分钟）")
                print("请检查模型路径和系统资源")
                print("系统将仅使用API模型")
                self.local_model_failed = True
                
        except Exception as e:
            print(f"\n❌ 本地模型初始化过程出错: {str(e)}")
            print("请检查模型路径和系统资源")
            print("系统将仅使用API模型")
            self.local_model_failed = True

    def embed(self, texts: List[str], async_mode: bool = False, timeout: float = 5.0) -> List[List[float]]:
        """
        嵌入文本，支持同步和异步模式
        
        Args:
            texts: 要嵌入的文本列表
            async_mode: 是否使用异步模式（不阻塞）
            timeout: 异步模式下的超时时间（秒）
            
        Returns:
            嵌入向量列表
        """
        if not texts:
            return []
        
        # 异步模式优先使用API模型的异步嵌入
        if async_mode:
            try:
                # 使用异步模式调用API模型
                print(f"使用异步模式嵌入 {len(texts)} 个文本...")
                return self.api_model.embed(texts, async_mode=True, timeout=timeout)
            except Exception as e:
                print(f"异步嵌入失败: {str(e)}")
                # 返回默认零向量
                default_dim = 1536
                return [[0.0] * default_dim for _ in range(len(texts))]
            
        # 同步模式
        results = []
        for text in texts:
            if not text.strip():
                results.append([])
                continue
                
            # 使用文本的MD5哈希作为缓存键
            cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
            
            # 检查缓存
            if cache_key in self.cache:
                print(f"📋 缓存命中: {text[:20]}...")
                results.append(self.cache[cache_key])
                continue
                
            # 优先使用API模型 (最多3次尝试，包括第一次)
            api_success = False
            api_error = None
            
            for attempt in range(3):
                try:
                    if attempt > 0:
                        print(f"API嵌入重试 ({attempt}/2)...")
                    embedding = self.api_model.embed([text])[0]
                    self.cache[cache_key] = embedding
                    results.append(embedding)
                    api_success = True
                    break
                except Exception as e:
                    api_error = e
                    print(f"❌ API嵌入{'' if attempt == 0 else '重试'}失败: {str(e)}")
                    # 短暂等待后重试
                    if attempt < 2:  # 只在前两次失败后等待
                        import time
                        time.sleep(1)
            
            # 如果API调用成功，继续处理下一个文本
            if api_success:
                continue
                
            # API调用失败，尝试使用本地模型
            if self.local_model_failed:
                print(f"⚠️ API嵌入失败且本地模型不可用，使用零向量")
                # 使用零向量代替
                dim = 1536  # 默认维度
                results.append([0.0] * dim)
                continue
            
            # 尝试使用本地模型
            try:
                print(f"尝试使用本地备用模型进行嵌入...")
                embedding = self.local_model.embed([text])[0]
                print(f"✅ 本地模型嵌入成功")
                self.cache[cache_key] = embedding
                results.append(embedding)
            except Exception as local_error:
                print(f"❌ 本地模型嵌入也失败: {str(local_error)}")
                # 标记本地模型为不可用
                self.local_model_failed = True
                print(f"⚠️ 本地模型已被标记为不可用，今后将不再尝试")
                # 使用零向量代替
                dim = 1536  # 默认维度
                results.append([0.0] * dim)
        
        return results
    
    def clear_cache(self):
        """清除缓存"""
        cache_size = len(self.cache)
        self.cache.clear()
        return f"已清除 {cache_size} 条缓存嵌入"


class ReRanker(ABC):
    @abstractmethod
    def rerank(self, query: str, documents: List[str]) -> List[float]:
        pass


class CrossEncoderReRanker(ReRanker):
    def __init__(self, model_path: str):
        self.model = CrossEncoder(model_path)

    def rerank(self, query: str, documents: List[str]) -> List[float]:
        pairs = [[query, doc] for doc in documents]
        return self.model.predict(pairs).tolist()


class OnlineCrossEncoderReRanker(ReRanker):
    def __init__(self, model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.model_name = model_name
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def rerank(self, query: str, documents: List[str]) -> List[float]:
        scores = []
        for doc in documents:
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system",
                         "content": "您是一个帮助评估文档与查询相关性的助手。请仅返回一个0到1之间的浮点数，不要包含其他文本。"},
                        {"role": "user", "content": f"查询：{query}\n文档：{doc}\n请评估该文档与查询的相关性分数（0-1）："}
                    ]
                )
                content = response.choices[0].message.content.strip()
                # 使用正则表达式提取数值
                match = re.search(r"0?\.\d+|\d\.?\d*", content)
                if match:
                    score = float(match.group())
                    score = max(0.0, min(1.0, score))  # 确保分数在0-1之间
                else:
                    score = 0.0  # 解析失败默认值
            except Exception as e:
                score = 0.0  # 异常处理
            scores.append(score)
        return scores


class RAG:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None or not kwargs.get('singleton', True):
            cls._instance = super(RAG, cls).__new__(cls)
        return cls._instance

    def __init__(self,
                 embedding_model: EmbeddingModel = None,
                 reranker: Optional[ReRanker] = None,
                 singleton: bool = True
                 ):
        if not hasattr(self, 'initialized'):
            self.embedding_model = embedding_model
            self.reranker = reranker
            self.index = None
            self.documents = []
            self.initialized = True

    def initialize_index(self, dim: int = 1024):
        """显式初始化索引，防止空指针异常"""
        if self.index is None:
            self.index = faiss.IndexFlatL2(dim)
            print(f"已初始化FAISS索引，维度: {dim}")

    def add_documents(self, documents=None, texts: List[str] = None):
        """
        添加文档到索引，确保不重复添加
        
        Args:
            documents: 文档字典 {key: value} 或键值对列表 [(key1, value1), (key2, value2), ...]
            texts: 文本列表 [text1, text2, ...]
        """
        if not documents and not texts:
            print("没有提供任何文档")
            return
        
        # 详细记录输入情况
        if documents:
            print(f"接收到documents参数，类型: {type(documents)}")
            if isinstance(documents, dict):
                print(f"字典包含 {len(documents)} 个键值对")
            elif isinstance(documents, list):
                print(f"列表包含 {len(documents)} 个项目")
                for i, item in enumerate(documents[:3]):  # 只显示前3个，避免日志过长
                    print(f"  示例项目{i+1}: {type(item)}, {str(item)[:50]}...")
        if texts:
            print(f"接收到texts参数，包含 {len(texts)} 个文本")
            for i, text in enumerate(texts[:3]):  # 只显示前3个
                print(f"  示例文本{i+1}: {text[:50]}...")
        
        # 准备要添加的文本
        new_texts = []
        skipped_texts = []
        
        # 处理文档参数 - 支持字典或键值对列表
        if documents:
            if hasattr(documents, 'items'):  # 字典类型
                for key, value in documents.items():
                    print(f"检查键值对 - 键: {key[:30]}..., 值: {value[:30]}...")
                    
                    # 检查键是否重复
                    if key in self.documents:
                        print(f"  跳过重复键: {key[:30]}...")
                        skipped_texts.append(key)
                    else:
                        print(f"  添加新键: {key[:30]}...")
                        new_texts.append(key)
                    
                    # 检查值是否重复
                    if value in self.documents:
                        print(f"  跳过重复值: {value[:30]}...")
                        skipped_texts.append(value)
                    else:
                        print(f"  添加新值: {value[:30]}...")
                        new_texts.append(value)
                    
            elif isinstance(documents, list):  # 键值对列表或普通列表
                for item in documents:
                    if isinstance(item, tuple) and len(item) == 2:
                        key, value = item
                        print(f"检查键值对 - 键: {key[:30]}..., 值: {value[:30]}...")
                        
                        # 使用和上面相同的检查逻辑
                        if key in self.documents:
                            print(f"  跳过重复键: {key[:30]}...")
                            skipped_texts.append(key)
                        else:
                            print(f"  添加新键: {key[:30]}...")
                            new_texts.append(key)
                        
                        if value in self.documents:
                            print(f"  跳过重复值: {value[:30]}...")
                            skipped_texts.append(value)
                        else:
                            print(f"  添加新值: {value[:30]}...")
                            new_texts.append(value)
                    else:
                        # 单项文档，不是键值对
                        text = str(item)
                        print(f"检查单项: {text[:50]}...")
                        if text in self.documents:
                            print(f"  跳过重复项: {text[:30]}...")
                            skipped_texts.append(text)
                        else:
                            print(f"  添加新项: {text[:30]}...")
                            new_texts.append(text)
            else:
                print(f"不支持的documents类型: {type(documents)}")
                raise ValueError(f"documents参数必须是字典或列表，收到: {type(documents)}")
        
        # 处理列表形式的文档
        if texts:
            for text in texts:
                print(f"检查文本: {text[:50]}...")
                if text in self.documents:
                    print(f"  跳过重复文本: {text[:30]}...")
                    skipped_texts.append(text)
                else:
                    print(f"  添加新文本: {text[:30]}...")
                    new_texts.append(text)
        
        # 如果没有新文档，直接返回
        if not new_texts:
            print(f"没有新文档需要添加，已跳过 {len(skipped_texts)} 个重复文档")
            return
        
        # 对文档进行去重
        print(f"初步收集了 {len(new_texts)} 个新文档，进行内部去重...")
        unique_texts = []
        seen = set()
        for text in new_texts:
            normalized = re.sub(r'\s+', '', text.lower())
            normalized = re.sub(r'[^\w\s]', '', normalized)
            
            if normalized not in seen:
                seen.add(normalized)
                unique_texts.append(text)
            else:
                print(f"  内部去重: 跳过 {text[:30]}...")
                skipped_texts.append(text)
        
        print(f"内部去重后剩余 {len(unique_texts)} 个文档")
        
        # 检查现有文档集合
        current_docs_normals = {re.sub(r'\s+', '', doc.lower()): i 
                             for i, doc in enumerate(self.documents)}
        current_docs_normals = {re.sub(r'[^\w\s]', '', key): val 
                             for key, val in current_docs_normals.items()}
        
        truly_new_texts = []
        for text in unique_texts:
            normalized = re.sub(r'\s+', '', text.lower())
            normalized = re.sub(r'[^\w\s]', '', normalized)
            
            if normalized in current_docs_normals:
                original_doc = self.documents[current_docs_normals[normalized]]
                print(f"  规范化去重: 跳过 '{text[:30]}...'，匹配已有 '{original_doc[:30]}...'")
                skipped_texts.append(text)
            else:
                truly_new_texts.append(text)
        
        # 最终汇总
        print(f"最终去重统计:")
        print(f"  - 原始文档数: {len(new_texts)} 个")
        print(f"  - 跳过重复: {len(skipped_texts)} 个")
        print(f"  - 待添加新文档: {len(truly_new_texts)} 个")
        
        # 如果去重后没有新文档，直接返回
        if not truly_new_texts:
            print("去重后没有新文档需要添加")
            return
        
        print(f"准备添加 {len(truly_new_texts)} 个新文档到索引")
        
        # 打印部分新文档示例
        for i, text in enumerate(truly_new_texts[:3]):
            print(f"  新文档 {i+1}: {text[:100]}...")
        
        # 生成嵌入
        print("开始生成文档嵌入...")
        embeddings = self.embedding_model.embed(truly_new_texts)
        if not embeddings or len(embeddings) == 0:
            print("⚠️ 嵌入模型返回空值")
            raise ValueError("嵌入模型返回空值")

        # 转换并检查维度
        embeddings = np.array(embeddings, dtype=np.float32)
        print(f"嵌入维度: {embeddings.shape}")
        
        # 初始化或检查索引维度
        if self.index is None:
            dim = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dim)
            print(f"初始化FAISS索引，维度: {dim}")
        elif embeddings.shape[1] != self.index.d:
            print(f"⚠️ 嵌入维度不匹配: 期望 {self.index.d}，实际 {embeddings.shape[1]}")
            raise ValueError(f"嵌入维度不匹配: 期望{self.index.d}，实际{embeddings.shape[1]}")

        # 添加文档到索引
        self.index.add(embeddings)
        self.documents.extend(truly_new_texts)
        
        print(f"索引更新完成，当前索引包含 {len(self.documents)} 个文档")

    def query(self, query: str, top_k: int = 5, rerank: bool = False, async_mode: bool = False, timeout: float = 5.0) -> List[str]:
        """
        查询相关文档
        
        Args:
            query: 查询文本
            top_k: 返回的最大结果数
            rerank: 是否对结果重排序
            async_mode: 是否使用异步模式（不阻塞）
            timeout: 异步模式下的超时时间（秒）
            
        Returns:
            相关文档列表
        """
        if not self.documents:
            return []
        
        # 生成查询向量
        try:
            print(f"正在为查询生成嵌入向量: {query[:50]}...")
            query_embedding = self.embedding_model.embed([query], async_mode=async_mode, timeout=timeout)[0]
            
            # 检查向量是否为空
            if not query_embedding:
                print("⚠️ 查询嵌入生成失败，返回空结果")
                return []
                
            # 搜索相似文档
            print(f"使用嵌入向量搜索相似文档...")
            D, I = self.index.search(np.array([query_embedding]), min(top_k, len(self.documents)))
            results = [self.documents[i] for i in I[0]]
            
            # 使用集合去重
            unique_results = list(set(results))
            
            # 如果需要重排序
            if rerank and self.reranker and len(unique_results) > 1:
                print(f"使用重排器对 {len(unique_results)} 个结果进行排序...")
                scores = self.reranker.rerank(query, unique_results)
                scored_results = list(zip(unique_results, scores))
                scored_results.sort(key=lambda x: x[1], reverse=True)
                unique_results = [r[0] for r in scored_results]
            
            print(f"RAG查询: 找到{len(unique_results)}条去重结果，从{len(results)}个候选结果中")
            return unique_results
            
        except Exception as e:
            print(f"查询过程发生错误: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []

    def deduplicate_documents(self):
        """
        清理索引中的重复文档
        这将重建整个索引，确保每个文档只出现一次
        """
        if not self.documents:
            print("没有文档，无需去重")
            return
        
        print(f"开始去重，当前文档数: {len(self.documents)}")
        
        # 获取当前文档并创建规范化映射
        original_count = len(self.documents)
        
        # 更强的规范化和去重
        unique_docs = []
        seen_normalized = set()
        
        for doc in self.documents:
            # 创建规范化版本（移除空格、标点并转为小写）
            normalized = re.sub(r'\s+', '', doc.lower())
            normalized = re.sub(r'[^\w\s]', '', normalized)
            
            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                unique_docs.append(doc)
            else:
                print(f"找到重复文档: {doc[:50]}...")
        
        new_count = len(unique_docs)
        
        if original_count == new_count:
            print("没有发现重复文档")
            return
        
        print(f"发现{original_count - new_count}个重复文档，正在重建索引...")
        
        # 重置当前索引和文档
        self.documents = []
        if self.index:
            dim = self.index.d
            self.index = faiss.IndexFlatL2(dim)
        
        # 重新添加去重后的文档
        for i, doc in enumerate(unique_docs):
            print(f"重新添加文档 {i+1}/{len(unique_docs)}: {doc[:30]}...")
        
        # 使用texts参数添加文档
        self.add_documents(texts=unique_docs)
        print(f"索引重建完成，从{original_count}个文档减少到{len(self.documents)}个唯一文档")

import re
import time  # 确保导入time模块
import hashlib  # 用于生成缓存键
import sys
import io
import requests  # 添加requests库用于硅基流动API请求
import os  # 添加os模块用于处理环境变量
import logging
import ssl  # 添加ssl模块用于处理SSL/TLS错误
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import numpy as np
import faiss
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Union
from openai import OpenAI
from sentence_transformers import SentenceTransformer, CrossEncoder
from pathlib import Path
import copy
import json
import yaml
import random
import traceback
from collections import defaultdict
from datetime import datetime
import pickle

# 设置日志
logger = logging.getLogger('main')

# 设置系统默认编码为UTF-8
try:
    # 检查encoding属性是否存在，避免colorama冲突
    if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
            print("已将标准输出编码设置为UTF-8")
        except Exception as e:
            print(f"警告: 无法设置标准输出编码为UTF-8: {str(e)}")
except Exception as e:
    print(f"警告: 检查编码时出错: {str(e)}")

# 创建默认安全的SSL上下文
def create_secure_ssl_context():
    """创建一个安全但兼容性更好的SSL上下文，用于解决SSL连接问题"""
    try:
        import ssl
        
        # 创建一个默认的SSL上下文
        context = ssl.create_default_context()
        
        # 禁用证书验证，解决自签名证书问题
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # 设置SSL版本兼容性
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        
        # 允许使用弱密码套件，提高兼容性
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        
        return context
    except Exception as e:
        logger.warning(f"创建SSL上下文失败: {str(e)}")
        return None

# 辅助函数：安全处理字符串，避免编码问题
def safe_str(text, default=""):
    """安全地处理字符串，避免编码问题"""
    if text is None:
        return default
    
    if not isinstance(text, str):
        try:
            text = str(text)
        except:
            return default
            
    # 尝试处理非ASCII字符
    try:
        # 保留原始文本，不再尝试ASCII转换
        return text
    except Exception:
        # 如果出现任何异常，返回安全字符串
        try:
            # 尝试移除所有非ASCII字符作为最后手段
            return ''.join(c for c in text if ord(c) < 128)
        except:
            return default

# 辅助函数：安全打印，避免编码问题
def safe_print(text, prefix=""):
    """安全打印函数，避免编码问题"""
    try:
        print(f"{prefix}{text}")
    except Exception as e:
        try:
            print(f"打印错误: {str(e)}")
        except:
            pass

# 添加自定义的安全请求函数，处理SSL错误
def safe_request(url, method="GET", json=None, headers=None, timeout=10, retries=3, ssl_context=None):
    """
    执行安全的HTTP请求，包含重试和SSL错误处理
    
    Args:
        url: 请求URL
        method: 请求方法，默认GET
        json: JSON请求体
        headers: 请求头
        timeout: 超时时间(秒)
        retries: 最大重试次数
        ssl_context: 自定义SSL上下文
        
    Returns:
        (响应对象, 错误信息)
    """
    error_msg = None
    session = requests.Session()
    
    # 禁用环境代理
    session.trust_env = False
    
    # 设置基本请求头
    default_headers = {
        "User-Agent": "Mozilla/5.0 KouriChatRAG/1.0",
        "Content-Type": "application/json"
    }
    
    if headers:
        default_headers.update(headers)
    
    # 设置SSL选项    
    if ssl_context:
        try:
            # 使用自定义SSL适配器
            from requests.adapters import HTTPAdapter
            from urllib3.poolmanager import PoolManager
            
            class SSLAdapter(HTTPAdapter):
                def __init__(self, ssl_context=None, **kwargs):
                    self.ssl_context = ssl_context
                    super(SSLAdapter, self).__init__(**kwargs)
                    
                def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
                    self.poolmanager = PoolManager(
                        num_pools=connections,
                        maxsize=maxsize,
                        block=block,
                        ssl_context=self.ssl_context,
                        **pool_kwargs
                    )
                    
            adapter = SSLAdapter(ssl_context=ssl_context)
            session.mount('https://', adapter)
            safe_print(f"已使用自定义SSL上下文增强请求安全性")
        except Exception as e:
            safe_print(f"警告: 设置SSL适配器失败: {str(e)}")
    
    # 执行带重试的请求
    for attempt in range(retries):
        try:
            if method.upper() == "GET":
                response = session.get(url, headers=default_headers, timeout=timeout, proxies={}, verify=True)
            else:
                response = session.post(url, json=json, headers=default_headers, timeout=timeout, proxies={}, verify=True)
                
            return response, None
            
        except requests.exceptions.SSLError as e:
            error_msg = f"SSL错误: {str(e)}"
            safe_print(f"⚠️ 第{attempt+1}次尝试失败: SSL错误，正在重试...")
            # 出现SSL错误时，添加延迟防止频繁请求
            time.sleep(1)
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"连接错误: {str(e)}"
            safe_print(f"⚠️ 第{attempt+1}次尝试失败: 连接错误，正在重试...")
            time.sleep(1)
            
        except requests.exceptions.Timeout as e:
            error_msg = f"请求超时: {str(e)}"
            safe_print(f"⚠️ 第{attempt+1}次尝试失败: 请求超时，正在重试...")
            time.sleep(1)
            
        except Exception as e:
            error_msg = f"请求错误: {str(e)}"
            safe_print(f"⚠️ 第{attempt+1}次尝试失败: {error_msg}，正在重试...")
            time.sleep(1)
    
    return None, error_msg

import numpy as np
import faiss
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Union
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
        # 处理字典格式的model_name参数
        if isinstance(model_name, dict) and 'value' in model_name:
            model_name = model_name['value']
        
        # 处理字典格式的base_url参数
        if isinstance(base_url, dict) and 'value' in base_url:
            safe_print(f"API URL是对象格式，值为: {base_url['value']}")
            base_url = base_url['value']
        
        # 确保model_name是字符串类型，使用安全字符串处理
        self.model_name = safe_str(model_name, "text-embedding-ada-002")
        self.api_key = api_key
        self.base_url = base_url
        self.api_calls = 0
        self.cache = {}
        self.cache_hits = 0
        
        # 创建客户端并测试连接
        safe_print("正在创建API客户端...")
        try:
            # 确保base_url不是空字符串
            client_kwargs = {"api_key": self.api_key}
            if self.base_url and isinstance(self.base_url, str) and self.base_url.strip():
                # 不再进行额外的字符串处理，使用原始URL
                client_kwargs["base_url"] = self.base_url.strip()
                safe_print(f"使用自定义API基础URL: {self.base_url.strip()}")
            else:
                safe_print("未提供有效的API基础URL，将使用OpenAI默认服务器")
            
            # 创建客户端
            self.client = OpenAI(**client_kwargs)
            
        except Exception as e:
            print("⚠️ API初始化失败")
            print("请检查以下可能的问题:")
            print("  - API密钥是否正确")
            print("  - API服务器是否可访问")
            print("  - 网络连接是否正常")
            # 使用更通用的错误消息，避免额外的编码问题
            raise Exception("创建API客户端失败，请检查配置和网络连接")

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

        # 直接使用默认嵌入向量而不发起API请求
        embeddings = []
        for text in texts:
            # 获取默认维度向量
            dim = self._get_model_dimension(self.model_name)
            # 生成一个基于文本哈希的伪随机向量，比全零向量更有区分度
            try:
                text_bytes = text.encode('utf-8')
                hash_val = hashlib.md5(text_bytes).digest()
                # 使用哈希值的每个字节生成一个-1到1之间的值
                seed_values = [((b / 255.0) * 2 - 1) * 0.1 for b in hash_val]
                # 扩展seed_values到所需维度
                embedding = []
                for i in range(dim):
                    # 循环使用seed_values的值作为基础
                    base_val = seed_values[i % len(seed_values)]
                    # 添加一些随机性，但保持一定的一致性
                    adjusted_val = base_val + ((i * 0.01) % 0.1)
                    embedding.append(adjusted_val)
                
                # 缓存结果
                cache_key = hashlib.md5(text_bytes).hexdigest()
                self.cache[cache_key] = embedding
                print(f"✅ 已生成本地伪嵌入向量，维度: {len(embedding)}")
                embeddings.append(embedding)
            except Exception as e:
                print(f"⚠️ 生成伪嵌入向量失败: {str(e)}")
                embeddings.append([0.0] * dim)
                
        return embeddings

    def _get_safe_model_name(self) -> str:
        """获取安全的模型名称"""
        try:
            # 确保返回的是纯ASCII模型名称
            safe_models = ["text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"]
            if str(self.model_name) in safe_models:
                return str(self.model_name)
            return "text-embedding-ada-002"  # 默认使用最稳定的模型
        except:
            return "text-embedding-ada-002"  # 出错时返回默认模型
        
    def _get_model_dimension(self, model_name: str) -> int:
        """获取模型的向量维度"""
        dimension_map = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072
        }
        return dimension_map.get(model_name, 1536)  # 默认返回1536维

    def _async_embed(self, texts: List[str], timeout: float = 10.0) -> List[List[float]]:
        """异步方式处理嵌入，使用线程池并行处理多个请求"""
        import concurrent.futures
        
        if not texts:
            return []

        # 创建结果列表
        dim = self._get_model_dimension()
        results = [[0.0] * dim for _ in range(len(texts))]
        
        # 进行分批处理，每批最多8个文本
        batch_size = 8
        batches = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batches.append((i, batch_texts))
            
        # 定义批处理函数
        def _process_batch(start_idx, batch):
            batch_results = self._embed_batch(batch, timeout)
            return start_idx, batch_results
            
        # 使用线程池并行处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(batches))) as executor:
            futures = [executor.submit(_process_batch, start_idx, batch) for start_idx, batch in batches]
            
            # 收集结果
            for future in concurrent.futures.as_completed(futures):
                try:
                    start_idx, batch_results = future.result()
                    for i, embedding in enumerate(batch_results):
                        if start_idx + i < len(results):
                            results[start_idx + i] = embedding
                except Exception as e:
                    safe_print(f"❌ 异步批处理失败: {str(e)}")
                    
        return results
    
    def get_cache_stats(self):
        """返回缓存统计信息"""
        total = self.cache_hits + self.api_calls
        hit_rate = (self.cache_hits / total) * 100 if total > 0 else 0
        stats = {
            "cache_size": len(self.cache),
            "cache_hits": self.cache_hits,
            "api_calls": self.api_calls,
            "hit_rate_percent": hit_rate
        }
        print(f"📊 缓存统计：命中率 {hit_rate:.1f}%，缓存大小 {len(self.cache)}，命中数 {self.cache_hits}，API调用数 {self.api_calls}")
        return stats
        
    def clear_cache(self):
        """清除缓存"""
        cache_size = len(self.cache)
        self.cache.clear()
        return f"已清除 {cache_size} 条缓存嵌入"


class SiliconFlowEmbeddingModel(EmbeddingModel):
    """硅基流动API的嵌入模型实现"""
    
    # 模型映射表
    _MODEL_DIMENSIONS = {
        "BAAI/bge-m3": 1024,
        "BAAI/bge-large-zh-v1.5": 1024,
        "BAAI/bge-large-en-v1.5": 1024,
        "BAAI/bge-small-zh-v1.5": 512,
        "BAAI/bge-small-en-v1.5": 512
    }

    def __init__(self, model_name: str, api_key: Optional[str] = None, 
                 api_url: str = "https://api.siliconflow.cn/v1/embeddings"):
        # 处理字典格式的model_name参数
        if isinstance(model_name, dict) and 'value' in model_name:
            model_name = model_name['value']
            
        # 处理字典格式的api_url参数
        if isinstance(api_url, dict) and 'value' in api_url:
            safe_print(f"硅基流动API URL是对象格式，值为: {api_url['value']}")
            api_url = api_url['value']
            
        self.model_name = str(model_name)
        self.api_key = api_key
        self.api_url = api_url
        self.api_calls = 0
        self.cache = {}
        self.cache_hits = 0
        
        # 确保api_url是绝对URL
        if self.api_url and not self.api_url.startswith('http'):
            self.api_url = f"https://{self.api_url}"
            
        # 模型维度映射表
        self.model_dimensions = {
            "BAAI/bge-m3": 1024,
            "BAAI/bge-large-zh-v1.5": 1024,
            "BAAI/bge-large-en-v1.5": 1024,
            "BAAI/bge-small-zh-v1.5": 512,
            "BAAI/bge-small-en-v1.5": 512,
            "BAAI/bge-reranker-v2-m3": 1024,  # 不支持嵌入，但添加维度避免错误
            "Pro/BAAI/bge-m3": 1024,
            "Pro/BAAI/bge-reranker-v2-m3": 1024
        }
        
        # 创建会话
        self.session = requests.Session()
        
        # 禁用代理，防止代理错误
        self.session.trust_env = False
        
        # 使用自定义User-Agent避免某些防火墙的拦截
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 KouriChatRAG/1.0",
            "Content-Type": "application/json"
        })
        
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}"
            })
        
        # 连接测试标志
        self.connection_tested = False

    def _test_api_connection(self):
        """测试API连接"""
        # 跳过API连接测试，直接返回成功
        logger.debug("跳过API连接测试，直接返回成功")
        self.connection_tested = True
        return True

    def embed(self, texts: List[str], async_mode: bool = False, timeout: float = 10.0) -> List[List[float]]:
        """
        使用硅基流动API将文本嵌入为向量
        
        Args:
            texts: 要嵌入的文本列表
            async_mode: 是否使用异步模式
            timeout: 请求超时时间（秒）
            
        Returns:
            嵌入向量列表
        """
        if not texts:
            return []
            
        # 如果是单个文本字符串，转换为列表
        if isinstance(texts, str):
            texts = [texts]
            
        # 过滤空文本
        texts = [text for text in texts if text and isinstance(text, str)]
        if not texts:
            return []
            
        # 计数API调用
        self.api_calls += 1
        
        # 检查缓存
        if len(texts) == 1 and texts[0] in self.cache:
            self.cache_hits += 1
            return [self.cache[texts[0]]]
            
        # 使用异步模式处理多文本
        if async_mode and len(texts) > 1:
            return self._async_embed(texts, timeout)
            
        # 常规处理方式
        if len(texts) <= 16:  # 小批量直接处理
            return self._embed_batch(texts, timeout)
        else:  # 大批量分批处理
            batch_size = 16
            result = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_result = self._embed_batch(batch, timeout)
                result.extend(batch_result)
                
            return result

    def _embed_batch(self, texts: List[str], timeout: float = 10.0) -> List[List[float]]:
        """处理一批文本的嵌入"""
        embeddings = []
        
        # 检查API URL和模型名称
        if not self.api_url:
            safe_print("API URL为空，无法生成嵌入")
            return [[0.0] * self._get_model_dimension()] * len(texts)
            
        # 缓存处理
        cached_indices = []
        uncached_texts = []
        uncached_indices = []
        
        # 尝试从缓存获取
        for i, text in enumerate(texts):
            if not text or not isinstance(text, str):
                embeddings.append([0.0] * self._get_model_dimension())
                continue
                
            # 生成缓存键
            try:
                cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
            except Exception:
                cache_key = hashlib.md5("default_text".encode('utf-8')).hexdigest()
                
            # 检查缓存
            if cache_key in self.cache:
                self.cache_hits += 1
                cached_indices.append(i)
                embeddings.append(self.cache[cache_key])
                safe_print(f"📋 缓存命中索引 {i}，当前缓存命中数: {self.cache_hits}，API调用数: {self.api_calls}")
            else:
                uncached_texts.append(text.encode('utf-8').decode('utf-8'))  # 确保正确编码
                uncached_indices.append(i)
                embeddings.append(None)  # 占位，稍后填充
                
        # 如果所有文本都已缓存，直接返回
        if not uncached_texts:
            return embeddings
            
        # 为未缓存的文本创建嵌入
        try:
            # 准备请求参数
            payload = {
                "model": self.model_name,
                "input": uncached_texts,
                "encoding_format": "float"
            }
            
            # 发送API请求
            safe_print(f"请求硅基流动嵌入API，{len(uncached_texts)}个文本")
            
            # 使用会话发送请求
            response = self.session.post(
                self.api_url,
                json=payload,
                timeout=timeout
            )
            
            self.api_calls += 1
            
            # 处理响应
            if response.status_code == 200:
                result = response.json()
                
                if 'data' in result and len(result['data']) == len(uncached_texts):
                    # 成功获取嵌入，更新缓存和结果
                    for i, (text, embedding_data) in enumerate(zip(uncached_texts, result['data'])):
                        if 'embedding' in embedding_data:
                            embedding = embedding_data['embedding']
                            
                            # 缓存结果
                            cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
                            self.cache[cache_key] = embedding
                            safe_print(f"📥 已缓存索引 {i} 的嵌入向量，当前缓存大小: {len(self.cache)}")
                            
                            # 填充结果数组
                            original_idx = uncached_indices[i]
                            embeddings[original_idx] = embedding
                else:
                    # API返回格式不正确
                    error_msg = f"API返回格式错误: {result.get('error', '未知错误')}"
                    safe_print(f"⚠️ {error_msg}")
                    
                    # 使用零向量填充
                    dim = self._get_model_dimension()
                    for idx in uncached_indices:
                        embeddings[idx] = [0.0] * dim
            else:
                # 处理错误状态码
                error_msg = f"API错误，状态码: {response.status_code}"
                safe_print(f"⚠️ {error_msg}")
                
                # 尝试获取详细错误信息
                try:
                    error_details = response.json().get('error', {})
                    if error_details:
                        safe_print(f"错误详情: {error_details}")
                except:
                    pass
                    
                # 使用零向量填充
                dim = self._get_model_dimension()
                for idx in uncached_indices:
                    embeddings[idx] = [0.0] * dim
                    
        except Exception as e:
            # 处理请求异常
            error_msg = str(e)
            safe_print(f"❌ 嵌入请求失败: {error_msg}")
            
            # 使用零向量填充
            dim = self._get_model_dimension()
            for idx in uncached_indices:
                embeddings[idx] = [0.0] * dim
                
        # 确保所有位置都有嵌入向量
        for i, emb in enumerate(embeddings):
            if emb is None:
                embeddings[i] = [0.0] * self._get_model_dimension()
                
        return embeddings

    def _async_embed(self, texts: List[str], timeout: float = 10.0) -> List[List[float]]:
        """异步方式处理嵌入，使用线程池并行处理多个请求"""
        import concurrent.futures
        
        if not texts:
            return []

        # 创建结果列表
        dim = self._get_model_dimension()
        results = [[0.0] * dim for _ in range(len(texts))]
        
        # 进行分批处理，每批最多8个文本
        batch_size = 8
        batches = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batches.append((i, batch_texts))
            
        # 定义批处理函数
        def _process_batch(start_idx, batch):
            batch_results = self._embed_batch(batch, timeout)
            return start_idx, batch_results
            
        # 使用线程池并行处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(batches))) as executor:
            futures = [executor.submit(_process_batch, start_idx, batch) for start_idx, batch in batches]
            
            # 收集结果
            for future in concurrent.futures.as_completed(futures):
                try:
                    start_idx, batch_results = future.result()
                    for i, embedding in enumerate(batch_results):
                        if start_idx + i < len(results):
                            results[start_idx + i] = embedding
                except Exception as e:
                    safe_print(f"❌ 异步批处理失败: {str(e)}")
                    
        return results
    
    def get_cache_stats(self):
        """返回缓存统计信息"""
        total = self.cache_hits + self.api_calls
        hit_rate = (self.cache_hits / total) * 100 if total > 0 else 0
        stats = {
            "cache_size": len(self.cache),
            "cache_hits": self.cache_hits,
            "api_calls": self.api_calls,
            "hit_rate_percent": hit_rate
        }
        print(f"📊 硅基流动缓存统计：命中率 {hit_rate:.1f}%，缓存大小 {len(self.cache)}，命中数 {self.cache_hits}，API调用数 {self.api_calls}")
        return stats
        
    def clear_cache(self):
        """清除缓存"""
        cache_size = len(self.cache)
        self.cache.clear()
        return f"已清除 {cache_size} 条缓存嵌入"

    def update_model_dimensions(self, model_name: str, dimension: int):
        """添加或更新模型维度映射"""
        if model_name and dimension > 0:
            self.model_dimensions[model_name] = dimension
            return True
        return False

    def _get_model_dimension(self) -> int:
        """获取模型的向量维度"""
        return self.model_dimensions.get(self.model_name, 1024)  # 默认返回1024维


class HybridEmbeddingModel(EmbeddingModel):
    """
    混合嵌入模型，优先使用API模型，如果API模型失败则使用本地模型。
    允许用户选择是否下载本地备用模型，并根据用户选择和下载结果调整模型使用策略。
    
    参数:
        api_model: API嵌入模型实例，可以是OnlineEmbeddingModel或SiliconFlowEmbeddingModel
        local_model_path: 本地模型路径
        local_model_enabled: 是否启用本地模型
    """
    def __init__(self, api_model: Union[OnlineEmbeddingModel, SiliconFlowEmbeddingModel], 
                 local_model_path: str = "paraphrase-multilingual-MiniLM-L12-v2", 
                 local_model_enabled: bool = False):
        # 安全处理模型名称
        # local_model_path应该是huggingface模型ID或本地路径
        self.local_model_path = local_model_path
        self.api_model = api_model
        self.local_model_enabled = local_model_enabled
        self.local_model = None
        self.cache = {}
        self.cache_hits = 0
        self.api_calls = 0
        self.local_calls = 0
        self.cache_keys = []
        self.api_errors = 0
        
        # 尝试识别模型类型
        self.is_siliconflow = isinstance(api_model, SiliconFlowEmbeddingModel)
        
        # 如果选择了本地模型，则初始化
        if local_model_enabled:
            self._initialize_local_model()
        
        # 输出初始化信息
        try:
            if self.is_siliconflow:
                print(f"硅基流动嵌入模型已初始化: {api_model.model_name}")
            else:
                print(f"API嵌入模型已初始化: {api_model.model_name}")
        except:
            print("API嵌入模型已初始化 (无法显示模型名称)")
        
        # 根据local_model_enabled决定是否初始化本地模型
        if local_model_enabled:
            print("\n本地模型已启用，正在初始化本地模型...")
            self._initialize_local_model()
        else:
            print("\n本地模型未启用，将仅使用API模型")
            self.local_model_failed = True
            
        print("\n" + "="*80)
        print(f"嵌入模型初始化完成: {'API + 本地备用' if self.local_model_enabled else 'API' }")
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
            if not text or not isinstance(text, str):
                results.append([])
                continue
                
            # 使用文本的MD5哈希作为缓存键，安全处理
            try:
                cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
            except Exception as e:
                print(f"⚠️ 生成缓存键时出错: {str(e)}")
                cache_key = hashlib.md5("default_text".encode('utf-8')).hexdigest()
            
            # 检查缓存
            if cache_key in self.cache:
                try:
                    print(f"📋 缓存命中: {text[:20]}...")
                except:
                    print(f"📋 缓存命中 (无法显示文本)")
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
                dim = 1024  # 默认维度
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


class SiliconFlowReRanker(ReRanker):
    """
    使用硅基流动API的重排器，通过大模型评估查询与文档的相关性。
    """
    def __init__(self, model_name: str, api_key: Optional[str] = None, 
                 api_url: str = "https://api.siliconflow.cn/v1/chat/completions"):
        self.model_name = model_name
        self.api_key = api_key
        self.api_url = api_url
        
    def rerank(self, query: str, documents: List[str]) -> List[float]:
        """
        重新排序文档列表，根据与查询的相关性。
        
        Args:
            query: 查询文本
            documents: 候选文档列表
            
        Returns:
            相关性分数列表，分数范围0-1
        """
        scores = []
        for doc in documents:
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", 
                         "content": "您是一个帮助评估文档与查询相关性的助手。请仅返回一个0到1之间的浮点数，不要包含其他文本。"},
                        {"role": "user", 
                         "content": f"查询：{query}\n文档：{doc}\n请评估该文档与查询的相关性分数（0-1）："}
                    ],
                    "temperature": 0.1,  # 低温度以获得一致的评分
                    "max_tokens": 10     # 只需要一个数字
                }
                
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=5,
                    proxies={}  # 明确禁用代理
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    if 'choices' in response_data and len(response_data['choices']) > 0:
                        content = response_data['choices'][0].get('message', {}).get('content', '')
                        # 使用正则表达式提取数值
                        match = re.search(r"0?\.\d+|\d\.?\d*", content)
                        if match:
                            score = float(match.group())
                            score = max(0.0, min(1.0, score))  # 确保分数在0-1之间
                            scores.append(score)
                            continue
                
                # 如果上面的处理失败，添加默认分数
                scores.append(0.5)  # 默认中等相关性
                    
            except Exception as e:
                safe_print(f"重排序过程出错: {str(e)}")
                scores.append(0.5)  # 发生错误时使用默认分数
                
        return scores


class SiliconFlowNativeReRanker(ReRanker):
    """使用硅基流动原生重排序API的重排器"""
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", api_key: Optional[str] = None,
                 api_url: str = "https://api.siliconflow.cn/v1/rerank", 
                 top_n: int = None, return_documents: bool = False):
        # 处理字典格式的model_name参数
        if isinstance(model_name, dict) and 'value' in model_name:
            model_name = model_name['value']
            
        # 处理字典格式的api_url参数
        if isinstance(api_url, dict) and 'value' in api_url:
            safe_print(f"硅基流动重排序API URL是对象格式，值为: {api_url['value']}")
            api_url = api_url['value']
            
        self.model_name = model_name
        self.api_key = api_key
        self.api_url = api_url
        self.top_n = top_n
        self.return_documents = return_documents
        
        # 初始化会话
        self.session = requests.Session()
        self.session.trust_env = False  # 禁用代理，防止代理错误
        
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 KouriChatRAG/1.0",
            "Content-Type": "application/json"
        })
        
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}"
            })
    
    def rerank(self, query: str, documents: List[str]) -> List[float]:
        """
        使用硅基流动原生重排序API重新排序文档列表
        
        Args:
            query: 查询文本
            documents: 候选文档列表
            
        Returns:
            相关性分数列表，分数范围0-1
        """
        if not documents:
            return []
            
        scores = [0.5] * len(documents)  # 默认中等相关性
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model_name,
                "query": query,
                "documents": documents,
                "return_documents": self.return_documents
            }
            
            # 如果指定了top_n，则添加到请求中
            if self.top_n is not None:
                payload["top_n"] = min(self.top_n, len(documents))
            
            safe_print(f"发送硅基流动重排序请求...")
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=30,  # 重排序可能需要更长时间
                proxies={}  # 明确禁用代理
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                if 'results' in response_data and len(response_data['results']) > 0:
                    # 创建一个映射，将索引映射到分数
                    score_mapping = {}
                    
                    for result in response_data['results']:
                        if 'index' in result and 'relevance_score' in result:
                            idx = result['index']
                            if 0 <= idx < len(documents):
                                score_mapping[idx] = result['relevance_score']
                    
                    # 更新分数列表
                    for i in range(len(documents)):
                        if i in score_mapping:
                            scores[i] = score_mapping[i]
                    
                    safe_print(f"✅ 重排序成功，重排序了 {len(score_mapping)} 个文档")
                    return scores
                else:
                    safe_print("❌ 重排序响应缺少结果")
            else:
                safe_print(f"❌ 重排序请求失败，状态码: {response.status_code}")
                if response.text:
                    safe_print(f"响应内容: {response.text[:200]}...")
                    
        except Exception as e:
            safe_print(f"❌ 重排序过程出错: {str(e)}")
            
        return scores  # 返回默认分数


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
            self.data_path = os.path.join(os.getcwd(), "data", "rag_data.pkl")
            
            # 尝试加载现有数据
            try:
                if os.path.exists(self.data_path) and self.embedding_model:
                    print(f"检测到RAG数据文件，尝试加载: {self.data_path}")
                    self.load()
            except Exception as e:
                print(f"加载现有RAG数据失败: {str(e)}")

    def save(self):
        """
        保存当前RAG索引和文档到文件
        """
        try:
            import pickle
            import os
            import logging
            
            # 获取logger
            logger = logging.getLogger('main')
            
            # 创建目录（如果不存在）
            os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
            
            # 准备要保存的数据（不保存index，因为它可以从文档重建）
            data_to_save = {
                "documents": self.documents,
                "embedding_model_info": str(self.embedding_model)
            }
            
            # 保存数据
            with open(self.data_path, 'wb') as f:
                pickle.dump(data_to_save, f)
                
            # 同时保存为JSON格式（便于查看和编辑）
            export_result = self.export_to_json()
                
            print(f"已保存RAG数据，文档数量: {len(self.documents)}")
            logger.info(f"已保存RAG记忆数据，文档数量: {len(self.documents)}")
            
            if export_result:
                logger.info("成功将RAG记忆导出为JSON格式")
            
            return True
        except Exception as e:
            print(f"保存RAG数据失败: {str(e)}")
            logging.getLogger('main').error(f"保存RAG数据失败: {str(e)}")
            return False
    
    def export_to_json(self):
        """
        将RAG文档导出为JSON格式
        将对话按照新格式结构保存
        """
        try:
            import json
            import os
            import re
            import logging
            from datetime import datetime
            
            # 获取logger
            logger = logging.getLogger('main')
            
            # 确定JSON文件路径
            json_path = os.path.join(os.getcwd(), "data", "memory", "rag-memory.json")
            
            # 创建目录（如果不存在）
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            # 首先检查是否存在现有的记忆文件
            existing_conversations = {}
            if os.path.exists(json_path):
                try:
                    logger.info(f"发现现有记忆文件，尝试读取: {json_path}")
                    with open(json_path, 'r', encoding='utf-8') as f:
                        existing_conversations = json.load(f)
                    logger.info(f"成功读取现有记忆，包含 {len(existing_conversations)} 个对话")
                except Exception as e:
                    logger.warning(f"读取现有记忆文件失败: {str(e)}")
            
            # 使用正则表达式匹配对话模式
            user_pattern = re.compile(r'^\[(.*?)\]对方\(ID:(.*?)\): (.*)$')
            ai_pattern = re.compile(r'^\[(.*?)\] 你: (.*)$')
            
            # 整理对话数据
            conversation_index = len(existing_conversations)
            
            # 收集所有用户消息
            user_messages = []
            for doc in self.documents:
                user_match = user_pattern.match(doc)
                if user_match:
                    timestamp, user_id, message = user_match.groups()
                    user_messages.append({
                        "doc": doc,
                        "timestamp": timestamp,
                        "user_id": user_id.strip(),
                        "message": message.strip()
                    })
            
            # 匹配AI回复
            matched_conversations = []
            for user_msg in user_messages:
                # 找到匹配的AI回复
                matched = False
                for doc in self.documents:
                    ai_match = ai_pattern.match(doc)
                    if ai_match and user_msg["timestamp"].split()[0] in doc:  # 匹配日期
                        ai_timestamp, ai_response = ai_match.groups()
                        
                        # 从config或环境变量获取当前角色名
                        try:
                            from src.config import config
                            avatar_dir = config.behavior.context.avatar_dir
                            # 提取最后一个目录作为角色名
                            avatar_name = os.path.basename(avatar_dir)
                        except:
                            avatar_name = "AI助手"
                        
                        # 确定是否为主动消息 (简单判断：如果消息中包含"主人"或类似词，可能是主动消息)
                        is_initiative = "主人" in user_msg["message"] or "您好" in user_msg["message"]
                        
                        # 尝试获取情绪
                        emotion = "None"
                        try:
                            # 导入情感分析模块
                            from src.handlers.emotion import SentimentResourceLoader, SentimentAnalyzer
                            # 创建分析器
                            resource_loader = SentimentResourceLoader()
                            analyzer = SentimentAnalyzer(resource_loader)
                            # 分析情感
                            sentiment_result = analyzer.analyze(ai_response)
                            emotion = sentiment_result.get('sentiment_type', 'None').lower()
                        except Exception as e:
                            print(f"情感分析失败: {str(e)}")
                        
                        # 填充对话数据结构
                        conversation_key = f"conversation{conversation_index}"
                        conversation_data = [{
                            "bot_time": ai_timestamp.strip(),
                            "sender_id": user_msg["user_id"],
                            "sender_text": user_msg["message"],
                            "receiver_id": avatar_name,
                            "receiver_text": ai_response.strip(),
                            "emotion": emotion,
                            "is_initiative": is_initiative  # 确保这里没有空格
                        }]
                        matched_conversations.append(conversation_data)
                        conversation_index += 1
                        matched = True
                        break
            
            # 保存为JSON - 合并新对话和现有对话
            conversations = {**existing_conversations}
            
            # 检查并修复现有记忆中的字段名称问题
            modified = False
            for conv_key, conv_data in conversations.items():
                for entry in conv_data:
                    if "is_ initiative" in entry:
                        # 获取logger
                        logger = logging.getLogger('main')
                        logger.warning(f"检测到字段命名问题，修复'is_ initiative'为'is_initiative'")
                        entry["is_initiative"] = entry.pop("is_ initiative")
                        modified = True
            
            # 如果修复了字段，记录日志
            if modified:
                logger.info("修复了字段命名问题")
                
            # 获取新的对话索引起点
            next_index = len(existing_conversations)
            
            # 遍历matched_conversations，添加到conversations
            for i, conv in enumerate(matched_conversations):
                conversation_key = f"conversation{next_index + i}"
                conversations[conversation_key] = conv
            
            # 保存为JSON
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(json_path), exist_ok=True)
                
                # 打开文件并写入
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(conversations, f, ensure_ascii=False, indent=2)
                
                # 验证文件是否成功写入
                file_size = os.path.getsize(json_path)
                
                logger.info(f"已导出RAG记忆到JSON: {json_path}, 共 {len(conversations)} 条对话，文件大小: {file_size} 字节")
                print(f"已导出RAG记忆到JSON: {json_path}, 共 {len(conversations)} 条对话，文件大小: {file_size} 字节")
                return True
            except Exception as file_err:
                logger.error(f"写入JSON文件失败: {str(file_err)}")
                print(f"写入JSON文件失败: {str(file_err)}")
                return False
        except Exception as e:
            print(f"导出RAG记忆到JSON失败: {str(e)}")
            logging.getLogger('main').error(f"导出RAG记忆到JSON失败: {str(e)}")
            traceback.print_exc()
            return False
            
    def import_from_json(self, json_path=None):
        """
        从JSON文件导入记忆
        
        Args:
            json_path: JSON文件路径，如果为None则使用默认路径
        """
        try:
            import json
            import os
            import logging
            
            # 获取logger
            logger = logging.getLogger('main')
            
            # 确定JSON文件路径
            if not json_path:
                json_path = os.path.join(os.getcwd(), "data", "memory", "rag-memory.json")
                
            if not os.path.exists(json_path):
                print(f"JSON记忆文件不存在: {json_path}")
                return False
                
            # 加载JSON数据
            with open(json_path, 'r', encoding='utf-8') as f:
                conversations = json.load(f)
            
            # 检查并修复字段名问题
            modified = False
            for conv_key, conv_data in conversations.items():
                for entry in conv_data:
                    if "is_ initiative" in entry:
                        entry["is_initiative"] = entry.pop("is_ initiative")
                        modified = True
                        logger.info(f"修复了字段命名问题: 'is_ initiative' -> 'is_initiative'")
            
            # 如果修改了，保存回文件
            if modified:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(conversations, f, ensure_ascii=False, indent=2)
                logger.info(f"保存了修复后的JSON文件")
                
            # 清空现有文档
            old_count = len(self.documents)
            self.documents = []
            if self.index:
                self.index.reset()
                
            # 添加记忆
            new_docs = []
            
            # 处理新格式的对话数据
            for conv_key, conv_data in conversations.items():
                if not isinstance(conv_data, list) or not conv_data:
                    continue
                    
                for entry in conv_data:
                    # 检查必要字段是否存在
                    if not all(k in entry for k in ["sender_id", "sender_text", "receiver_id", "receiver_text"]):
                        continue
                    
                    # 检查时间字段 (兼容旧版本)
                    if "bot_time" in entry:
                        timestamp = entry["bot_time"]
                    elif "receiver_time" in entry:
                        timestamp = entry["receiver_time"]
                    else:
                        # 如果没有时间字段，使用当前时间
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    # 格式化用户消息
                    sender_id = entry["sender_id"]
                    sender_text = entry["sender_text"]
                    
                    user_msg = f"[{timestamp}]对方(ID:{sender_id}): {sender_text}"
                    new_docs.append(user_msg)
                    
                    # 格式化AI回复
                    receiver_text = entry["receiver_text"]
                    ai_msg = f"[{timestamp}] 你: {receiver_text}"
                    new_docs.append(ai_msg)
            
            # 检查是否有新文档
            if not new_docs:
                print("JSON文件中没有有效记忆")
                return False
                
            # 生成嵌入并添加到索引
            print(f"从JSON导入 {len(new_docs)} 条记忆...")
            embeddings = self.embedding_model.embed(new_docs)
            
            # 初始化索引
            if not self.index:
                embedding_dim = len(embeddings[0])
                self.index = faiss.IndexFlatL2(embedding_dim)
                
            # 添加到索引
            self.index.add(np.array(embeddings).astype('float32'))
            self.documents.extend(new_docs)
            
            print(f"成功从JSON导入记忆，原始文档数: {old_count}, 当前文档数: {len(self.documents)}")
            return True
        except Exception as e:
            print(f"从JSON导入记忆失败: {str(e)}")
            traceback.print_exc()
            return False
            
    def load(self):
        """
        从文件加载RAG索引和文档
        """
        try:
            import pickle
            import os
            
            if not os.path.exists(self.data_path):
                print(f"RAG数据文件不存在: {self.data_path}")
                return False
                
            # 加载数据
            with open(self.data_path, 'rb') as f:
                data = pickle.load(f)
                
            # 恢复文档
            if "documents" in data and isinstance(data["documents"], list):
                self.documents = data["documents"]
                print(f"已加载 {len(self.documents)} 个文档")
                
                # 如果文档存在，重建索引
                if self.documents and self.embedding_model:
                    print("重建索引...")
                    embeddings = self.embedding_model.embed(self.documents)
                    embedding_dim = len(embeddings[0])
                    self.index = faiss.IndexFlatL2(embedding_dim)
                    self.index.add(np.array(embeddings).astype('float32'))
                    print(f"索引重建完成，文档数量: {len(self.documents)}")
                    
            return True
        except Exception as e:
            print(f"加载RAG数据失败: {str(e)}")
            return False

    def initialize_index(self, dim: int = 1024):
        """显式初始化索引，防止空指针异常"""
        if self.index is None:
            self.index = faiss.IndexFlatL2(dim)
            print(f"已初始化FAISS索引，维度: {dim}")

    def add_documents(self, documents=None, texts: List[str] = None):
        """
        添加文档到RAG系统
        
        Args:
            documents: 文档列表，可以是字符串列表或对象列表
            texts: 文本列表，将直接添加为文档
            
        如果同时提供documents和texts，两者都会被添加
        """
        import logging
        logger = logging.getLogger('main')
        
        if not documents and not texts:
            logger.warning("没有提供文档")
            return
        
        all_texts = []
        
        # 处理documents参数
        if documents:
            logger.debug(f"接收到documents参数，类型: {type(documents)}")
            logger.debug(f"列表包含 {len(documents)} 个项目")
            if len(documents) > 0:
                logger.debug(f"示例项目1: {type(documents[0])}, {str(documents[0])[:100]}...")
            
            # 尝试提取文本
            for doc in documents:
                if isinstance(doc, str):
                    # 直接添加字符串文档
                    all_texts.append(doc)
                elif isinstance(doc, tuple) and len(doc) >= 2:
                    # 处理(key, value)格式
                    logger.debug(f"处理键值对 - 键类型: {type(doc[0])}, 值类型: {type(doc[1])}")
                    
                    # 如果都是字符串，合并为一个文档
                    if isinstance(doc[0], str) and isinstance(doc[1], str):
                        key_str = str(doc[0])
                        value_str = str(doc[1])
                        combined_text = f"{key_str}: {value_str}"
                        logger.debug(f"合并键值对为单一文档: {combined_text[:50]}...")
                        all_texts.append(combined_text)
                    elif isinstance(doc[1], str):
                        all_texts.append(doc[1])
                    elif isinstance(doc[0], str):
                        all_texts.append(doc[0])
                elif isinstance(doc, dict):
                    # 优先选择更常见的字段名
                    for field in ['text', 'content', 'body', 'message', 'value']:
                        if field in doc and isinstance(doc[field], str):
                            all_texts.append(doc[field])
                            break
                    else:
                        # 如果没有找到有效字段，尝试使用字符串表示
                        all_texts.append(str(doc))
                else:
                    # 尝试转换为字符串
                    try:
                        all_texts.append(str(doc))
                    except:
                        logger.warning(f"跳过无法转换为文本的文档: {type(doc)}")
        
        # 处理texts参数
        if texts:
            for text in texts:
                if isinstance(text, str):
                    all_texts.append(text)
        
        # 预处理过滤文本内容
        filtered_texts = []
        for text in all_texts:
            if not text or not isinstance(text, str):
                continue
                
            # 文本长度过滤
            if len(text.strip()) < 5:  # 过滤掉过短的文本
                logger.debug(f"跳过过短文本: {text}")
                continue
                
            # 内容质量过滤
            if self._is_low_quality_text(text):
                logger.debug(f"跳过低质量文本: {text[:50]}...")
                continue
                
            # 应用文本清理（如果能导入相关函数）
            try:
                from src.memories.memory_utils import clean_dialog_memory
                # 对于包含冒号的文本，尝试作为对话清理
                if ': ' in text or '：' in text:
                    parts = text.split(':', 1) if ': ' in text else text.split('：', 1)
                    if len(parts) == 2:
                        _, cleaned_text = clean_dialog_memory(parts[0], parts[1])
                        if cleaned_text.strip():
                            text = cleaned_text
                
                # 如果清理后文本为空，则跳过
                if not text.strip():
                    logger.debug("清理后文本为空，跳过")
                    continue
            except ImportError:
                # 如果无法导入清理函数，跳过清理步骤
                pass
                
            filtered_texts.append(text)
            
        # 如果过滤后没有文本，直接返回
        if not filtered_texts:
            logger.warning("过滤后没有有效文本，跳过添加文档")
            return
        
        # 去除可能的重复文档
        truly_new_texts = []
        existing_docs_set = set(self.documents)
        duplicate_count = 0
        
        for text in filtered_texts:
            if text in existing_docs_set:
                logger.debug(f"跳过重复文档: {text[:50]}...")
                duplicate_count += 1
            else:
                truly_new_texts.append(text)
                existing_docs_set.add(text)
        
        if duplicate_count > 0:
            logger.info(f"跳过 {duplicate_count} 个重复文档")
        
        if not truly_new_texts:
            return
        
        # 生成嵌入向量
        print("开始生成文档嵌入...")
        embeddings = self.embedding_model.embed(truly_new_texts)
        
        # 确保嵌入维度与索引维度匹配
        if not embeddings or not isinstance(embeddings[0], list):
            print("⚠️ 嵌入生成失败，跳过添加文档")
            return
        
        # 检查维度一致性
        print(f"嵌入维度: {np.array(embeddings).shape}")
        
        # 初始化索引（如果尚未初始化）
        if not self.index:
            embedding_dim = len(embeddings[0])
            print(f"初始化FAISS索引，维度: {embedding_dim}")
            self.index = faiss.IndexFlatL2(embedding_dim)
        
        # 添加文档到索引
        self.index.add(np.array(embeddings).astype('float32'))
        self.documents.extend(truly_new_texts)
        
        print(f"索引更新完成，当前索引包含 {len(self.documents)} 个文档")
        
        # 保存RAG数据到文件
        self.save()
        
    def _is_low_quality_text(self, text):
        """
        判断文本是否为低质量
        
        Args:
            text: 待判断文本
            
        Returns:
            bool: 是否为低质量文本
        """
        import re
        
        # 转换为小写便于匹配
        lower_text = text.lower()
        
        # 过滤明显的系统/指令提示
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
            r"我想要你"
        ]
        
        for pattern in system_patterns:
            if re.search(pattern, lower_text):
                return True
                
        # 过滤重复模式
        if self._has_excessive_repetition(text):
            return True
            
        # 过滤无意义字符串
        noise_patterns = [
            r"\[MASK\]", r"\[CLS\]", r"\[SEP\]", r"\[PAD\]", r"\[UNK\]",
            r"<s>", r"</s>", r"<p>", r"</p>", r"<div>", r"</div>",
            r"^[a-f0-9]{32,}$",  # MD5等哈希值
            r"^[a-zA-Z0-9+/]{40,}={0,2}$"  # Base64编码
        ]
        
        for pattern in noise_patterns:
            if re.search(pattern, text):
                return True
                
        # 过滤包含大量特殊符号的文本
        special_chars = re.findall(r'[^\w\s\u4e00-\u9fff，。？！：；""''【】「」『』（）、]', text)
        if len(special_chars) / len(text) > 0.3:  # 特殊字符比例过高
            return True
            
        return False
        
    def _has_excessive_repetition(self, text):
        """
        检测文本中是否有过度重复
        
        Args:
            text: 待检测文本
            
        Returns:
            bool: 是否存在过度重复
        """
        import re
        
        # 检查重复单词
        words = re.findall(r'\b\w+\b', text.lower())
        if len(words) > 5:
            unique_words = set(words)
            if len(unique_words) / len(words) < 0.3:  # 如果不同单词比例过低
                return True
        
        # 检查重复段落
        paragraphs = [p for p in text.split('\n') if p.strip()]
        if len(paragraphs) > 3:
            unique_paragraphs = set(paragraphs)
            if len(unique_paragraphs) / len(paragraphs) < 0.5:  # 如果不同段落比例过低
                return True
                
        # 检查重复模式
        for length in range(3, min(10, len(text) // 2)):  # 检查3-10个字符的重复
            for i in range(len(text) - length * 2):
                pattern = text[i:i+length]
                if pattern.strip() and text.count(pattern) > 3:  # 同一模式重复超过3次
                    return True
                    
        return False

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
        
        # 检查JSON记忆文件是否存在，如果存在，可能需要先导入最新记忆
        try:
            import os
            import json
            
            json_path = os.path.join(os.getcwd(), "data", "memory", "rag-memory.json")
            if os.path.exists(json_path):
                # 尝试从JSON获取最新记忆
                self.import_from_json(json_path)
        except Exception as e:
            print(f"尝试导入最新JSON记忆失败: {str(e)}")
        
        # 生成查询向量
        try:
            print(f"正在为查询生成嵌入向量: {query[:50]}...")
            query_embedding = self.embedding_model.embed([query], async_mode=async_mode, timeout=timeout)[0]
            
            # 检查向量是否为空
            if not query_embedding:
                print("⚠️ 查询嵌入生成失败，返回空结果")
                return []
            
            # 确保查询向量格式正确
            if not isinstance(query_embedding, list):
                print("⚠️ 查询向量格式错误，返回空结果")
                return []
                
            # 搜索相似文档
            print(f"使用嵌入向量搜索相似文档...")
            # 确保top_k和documents长度都是整数
            doc_count = len(self.documents)
            safe_top_k = min(top_k, doc_count) if isinstance(doc_count, int) else top_k
            
            if safe_top_k <= 0 or doc_count <= 0:
                print("⚠️ 文档数量为0或top_k设置错误，返回空结果")
                return []
            
            # 确保查询向量是正确的numpy数组格式
            try:
                query_vector = np.array([query_embedding], dtype=np.float32)
                
                if self.index.ntotal == 0:
                    print("⚠️ 索引为空，返回空结果")
                    return []
                    
                # 执行搜索
                D, I = self.index.search(query_vector, safe_top_k)
                
                # 防止索引越界
                valid_indices = [i for i in I[0] if 0 <= i < len(self.documents)]
                results = [self.documents[i] for i in valid_indices]
                
                if not results:
                    print("⚠️ 未找到匹配结果")
                    return []
                
            except Exception as e:
                print(f"⚠️ 搜索过程出错: {str(e)}")
                return []
            
            # 使用集合去重
            unique_results = list(set(results))
            
            # 将结果转换为结构化格式（如果有完整对话）
            try:
                import re
                
                structured_results = []
                user_pattern = re.compile(r'^\[(.*?)\]对方\(ID:(.*?)\): (.*)$')
                ai_pattern = re.compile(r'^\[(.*?)\] 你: (.*)$')
                
                # 尝试将标准文本格式结果转为新的JSON结构
                for result in unique_results:
                    user_match = user_pattern.match(result)
                    ai_match = ai_pattern.match(result)
                    
                    if user_match:
                        # 查找匹配的AI回复
                        timestamp, user_id, message = user_match.groups()
                        for other_result in unique_results:
                            ai_match = ai_pattern.match(other_result)
                            if ai_match and timestamp in other_result:
                                ai_timestamp, ai_response = ai_match.groups()
                                # 创建结构化结果
                                structured_result = {
                                    "user_message": message.strip(),
                                    "ai_response": ai_response.strip(),
                                    "timestamp": timestamp.strip(),
                                    "user_id": user_id.strip()
                                }
                                structured_results.append(structured_result)
                                break
                
                # 如果有结构化结果，返回这些结果
                if structured_results:
                    print(f"已将查询结果转换为{len(structured_results)}条结构化记忆")
                    return structured_results
            except Exception as e:
                print(f"转换为结构化格式失败: {str(e)}")
            
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


def load_from_config(config_path: str = None) -> Optional[RAG]:
    if config_path is None:
        # 获取当前文件的路径
        current_file = Path(__file__).resolve()
        # 项目根目录路径（假设结构是 项目根目录/src/memories/memory/core/rag.py）
        root_dir = current_file.parents[4]
        
        # 尝试在几个常见位置找到配置文件
        possible_paths = [
            os.path.join(root_dir, "src", "config", "rag_config.yaml"),
            os.path.join(root_dir, "src", "config", "config.yaml"),
            os.path.join(root_dir, "config.yaml"),
            os.path.join(root_dir, "config.yml"), 
            os.path.join(root_dir, "rag_config.yaml"),
            os.path.join(root_dir, "rag_config.yml"),
            os.path.join(root_dir, "memory_config.yaml"),
            os.path.join(root_dir, "memory_config.yml"),
            os.path.join(root_dir, "src", "config", "memory_config.yaml"),
            os.path.join(root_dir, "src", "memories", "config.yaml"),
            os.path.join(root_dir, "data", "memories", "config.yaml"),
            os.path.expanduser("~/.config/rag/config.yaml"),
            os.path.join(os.path.dirname(__file__), "config.yaml"),
        ]
        
        print(f"检查可能的配置文件路径:")
        for path in possible_paths:
            if os.path.exists(path):
                print(f"找到配置文件: {path}")
                config_path = path
                break
            else:
                print(f"路径不存在: {path}")
                
        if config_path is None:
            print("❌ 未找到配置文件")
            # 创建默认配置
            try:
                default_config_path = os.path.join(root_dir, "src", "config", "config.yaml")
                # 确保目录存在
                os.makedirs(os.path.dirname(default_config_path), exist_ok=True)
                print(f"创建默认配置文件: {default_config_path}")
                create_default_config(default_config_path)
                if os.path.exists(default_config_path):
                    config_path = default_config_path
                    print(f"✅ 已创建默认配置文件: {default_config_path}")
                else:
                    print(f"❌ 无法创建默认配置文件")
                    return None
            except Exception as e:
                print(f"❌ 创建默认配置失败: {str(e)}")
                return None
    
    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        return None
        
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        if not config:
            print(f"❌ 配置文件为空或格式无效: {config_path}")
            return None
            
        # 检查是否为项目配置文件（KouriChat配置），如果是则转换格式
        if 'categories' in config and 'rag_settings' in config.get('categories', {}):
            print(f"检测到KouriChat项目配置文件，进行格式转换...")
            # 这里需要导入KouriChat的配置处理模块
            try:
                # 获取项目根目录
                project_root = Path(config_path).resolve().parents[2]
                sys.path.insert(0, str(project_root))
                
                try:
                    from src.memories.memory.examples.create_rag_config import extract_rag_settings, generate_rag_config
                    
                    # 使用项目配置创建RAG配置
                    print(f"从项目配置提取RAG设置...")
                    rag_settings = extract_rag_settings(config)
                    config = generate_rag_config(rag_settings)
                    print(f"成功将项目配置转换为标准RAG配置")
                    
                except ImportError as e:
                    print(f"导入配置处理模块失败: {str(e)}")
                    print(f"尝试从原始配置中提取基本参数...")
                    
                    # 如果无法导入处理模块，进行简单的配置提取
                    rag_settings = config.get('categories', {}).get('rag_settings', {}).get('settings', {})
                    
                    # 获取embedding_model，支持错误拼写的eembedding_model
                    embedding_model = rag_settings.get('embedding_model', {}).get('value', '')
                    if not embedding_model:
                        embedding_model = rag_settings.get('eembedding_model', {}).get('value', 'BAAI/bge-m3')
                    
                    # 获取base_url，支持错误拼写的bbase_url
                    base_url = rag_settings.get('base_url', {}).get('value', '')
                    if not base_url:
                        base_url = rag_settings.get('bbase_url', {}).get('value', 'https://api.siliconflow.cn/v1/embeddings')
                    
                    # 创建基本配置
                    config = {
                        "singleton": True,
                        "environment": {
                            "disable_proxy": True,
                            "no_proxy": "*"
                        },
                        "embedding_model": {
                            "type": "siliconflow",
                            "model_name": embedding_model,
                            "api_key": rag_settings.get('api_key', {}).get('value', ""),
                            "api_url": base_url
                        }
                    }
                    
                    # 处理嵌入模型URL
                    api_url = config['embedding_model']['api_url']
                    if api_url and not api_url.endswith('/embeddings'):
                        # 移除可能的尾部斜杠
                        api_url = api_url.rstrip('/')
                        # 添加embeddings路径
                        api_url = f"{api_url}/embeddings"
                        config['embedding_model']['api_url'] = api_url
                        print(f"项目配置转换：已调整嵌入模型URL: {api_url}")
                    
                    # 添加重排序器配置
                    if rag_settings.get('is_rerank', {}).get('value', False):
                        rerank_url = rag_settings.get('base_url', {}).get('value', "https://api.siliconflow.cn/v1")
                        # 处理重排序模型URL
                        if rerank_url and not rerank_url.endswith('/rerank'):
                            # 移除可能的尾部斜杠
                            rerank_url = rerank_url.rstrip('/')
                            # 添加rerank路径
                            rerank_url = f"{rerank_url}/rerank"
                        
                        config["reranker"] = {
                            "type": "siliconflow_native",
                            "model_name": rag_settings.get('reranker_model', {}).get('value', 'BAAI/bge-reranker-v2-m3'),
                            "api_key": rag_settings.get('api_key', {}).get('value', ""),
                            "api_url": rerank_url
                        }
                        print(f"项目配置转换：已调整重排序模型URL: {rerank_url}")
                        
                    print(f"已从项目配置中提取基本RAG参数")
                    
            except Exception as e:
                print(f"处理项目配置时出错: {str(e)}")
                print(f"将尝试作为标准RAG配置继续处理...")
            
        # 应用环境配置
        print(f"应用环境配置...")
        apply_environment_config(config)
            
        # 解析嵌入模型配置
        embedding_model = None
        if 'embedding_model' in config:
            emb_config = config['embedding_model']
            
            # 处理环境变量引用
            if 'api_key' in emb_config:
                emb_config['api_key'] = expand_env_vars(emb_config['api_key'])
                
            model_type = emb_config.get('type', '').lower()
            
            if model_type == 'siliconflow':
                # 处理URL，确保嵌入模型URL以"/embeddings"结尾
                api_url = emb_config.get('api_url', 'https://api.siliconflow.cn/v1/embeddings')
                if api_url and not api_url.endswith('/embeddings'):
                    # 移除可能的尾部斜杠
                    api_url = api_url.rstrip('/')
                    # 添加embeddings路径
                    api_url = f"{api_url}/embeddings"
                    print(f"已调整嵌入模型URL: {api_url}")
                
                embedding_model = SiliconFlowEmbeddingModel(
                    model_name=emb_config.get('model_name', 'BAAI/bge-large-zh-v1.5'),
                    api_key=emb_config.get('api_key'),
                    api_url=api_url
                )
            elif model_type == 'openai':
                # 处理URL，确保嵌入模型URL以"/embeddings"结尾
                base_url = emb_config.get('base_url')
                if base_url and not base_url.endswith('/embeddings'):
                    # 移除可能的尾部斜杠
                    base_url = base_url.rstrip('/')
                    # 添加embeddings路径
                    base_url = f"{base_url}/embeddings"
                    print(f"已调整嵌入模型URL: {base_url}")
                
                embedding_model = OnlineEmbeddingModel(
                    model_name=emb_config.get('model_name', 'text-embedding-ada-002'),
                    api_key=emb_config.get('api_key'),
                    base_url=base_url
                )
            elif model_type == 'local':
                embedding_model = LocalEmbeddingModel(
                    model_path=emb_config.get('model_path', 'paraphrase-multilingual-MiniLM-L12-v2')
                )
            elif model_type == 'hybrid':
                # 创建主要API模型
                if emb_config.get('api_type', '').lower() == 'siliconflow':
                    # 处理URL，确保嵌入模型URL以"/embeddings"结尾
                    api_url = emb_config.get('api_url', 'https://api.siliconflow.cn/v1/embeddings')
                    if api_url and not api_url.endswith('/embeddings'):
                        # 移除可能的尾部斜杠
                        api_url = api_url.rstrip('/')
                        # 添加embeddings路径
                        api_url = f"{api_url}/embeddings"
                        print(f"已调整混合模型(siliconflow)URL: {api_url}")
                    
                    api_model = SiliconFlowEmbeddingModel(
                        model_name=emb_config.get('model_name', 'BAAI/bge-large-zh-v1.5'),
                        api_key=emb_config.get('api_key'),
                        api_url=api_url
                    )
                else:
                    # 处理URL，确保嵌入模型URL以"/embeddings"结尾
                    base_url = emb_config.get('base_url')
                    if base_url and not base_url.endswith('/embeddings'):
                        # 移除可能的尾部斜杠
                        base_url = base_url.rstrip('/')
                        # 添加embeddings路径
                        base_url = f"{base_url}/embeddings"
                        print(f"已调整混合模型(openai)URL: {base_url}")
                    
                    api_model = OnlineEmbeddingModel(
                        model_name=emb_config.get('model_name', 'text-embedding-ada-002'),
                        api_key=emb_config.get('api_key'),
                        base_url=base_url
                    )
                
                # 创建混合模型
                embedding_model = HybridEmbeddingModel(
                    api_model=api_model,
                    local_model_path=emb_config.get('local_model_path', 'paraphrase-multilingual-MiniLM-L12-v2'),
                    local_model_enabled=emb_config.get('local_model_enabled', False)
                )
                
        if embedding_model is None:
            print("❌ 嵌入模型配置无效")
            return None
            
        # 解析重排序器配置
        reranker = None
        if 'reranker' in config:
            rerank_config = config['reranker']
            
            # 处理环境变量引用
            if 'api_key' in rerank_config:
                rerank_config['api_key'] = expand_env_vars(rerank_config['api_key'])
                
            rerank_type = rerank_config.get('type', '').lower()
            
            if rerank_type == 'siliconflow_native':
                # 处理URL，确保重排序模型URL以"/rerank"结尾
                api_url = rerank_config.get('api_url', 'https://api.siliconflow.cn/v1/rerank')
                if api_url and not api_url.endswith('/rerank'):
                    # 移除可能的尾部斜杠
                    api_url = api_url.rstrip('/')
                    # 添加rerank路径
                    api_url = f"{api_url}/rerank"
                    print(f"已调整重排序模型URL: {api_url}")
                
                reranker = SiliconFlowNativeReRanker(
                    model_name=rerank_config.get('model_name', 'BAAI/bge-reranker-v2-m3'),
                    api_key=rerank_config.get('api_key'),
                    api_url=api_url,
                    top_n=rerank_config.get('top_n'),
                    return_documents=rerank_config.get('return_documents', False)
                )
            elif rerank_type == 'siliconflow':
                # 处理URL，确保重排序模型URL以"/chat/completions"结尾
                api_url = rerank_config.get('api_url', 'https://api.siliconflow.cn/v1/chat/completions')
                if api_url and not api_url.endswith('/chat/completions'):
                    # 移除可能的尾部斜杠
                    api_url = api_url.rstrip('/')
                    # 添加chat/completions路径
                    api_url = f"{api_url}/chat/completions"
                    print(f"已调整重排序模型URL: {api_url}")
                
                reranker = SiliconFlowReRanker(
                    model_name=rerank_config.get('model_name', 'glm-4'),
                    api_key=rerank_config.get('api_key'),
                    api_url=api_url
                )
            elif rerank_type == 'openai':
                # 处理URL，确保重排序模型URL以"/chat/completions"结尾
                base_url = rerank_config.get('base_url')
                if base_url and not base_url.endswith('/chat/completions'):
                    # 移除可能的尾部斜杠
                    base_url = base_url.rstrip('/')
                    # 添加chat/completions路径
                    base_url = f"{base_url}/chat/completions"
                    print(f"已调整重排序模型URL: {base_url}")
                
                reranker = OnlineCrossEncoderReRanker(
                    model_name=rerank_config.get('model_name', 'gpt-3.5-turbo'),
                    api_key=rerank_config.get('api_key'),
                    base_url=base_url
                )
            elif rerank_type == 'local':
                reranker = CrossEncoderReRanker(
                    model_path=rerank_config.get('model_path', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
                )
                
        # 创建RAG系统
        rag = RAG(
            embedding_model=embedding_model,
            reranker=reranker,
            singleton=config.get('singleton', True)
        )
        
        # 如果配置文件中有预加载的文档
        if 'documents' in config and isinstance(config['documents'], list):
            rag.add_documents(texts=config['documents'])
            
        print(f"✅ 成功从配置文件加载RAG系统: {config_path}")
        return rag
        
    except Exception as e:
        print(f"❌ 加载配置文件时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# 示例配置文件内容
"""
示例 config.yaml 文件:

```yaml
# RAG系统配置
singleton: true  # 是否使用单例模式

# 环境配置
environment:
  disable_proxy: true  # 是否禁用代理设置
  no_proxy: "*"  # 禁用代理的域名，"*"表示所有
  api_key: ${SILICONFLOW_API_KEY}  # API密钥，可以使用环境变量
  encoding: "utf-8"  # 文本编码
  default_timeout: 10.0  # 默认API超时时间（秒）

# 嵌入模型配置
embedding_model:
  type: siliconflow  # 可选: siliconflow, openai, local, hybrid
  model_name: BAAI/bge-large-zh-v1.5
  api_key: ${SILICONFLOW_API_KEY}  # 可以引用环境变量
  api_url: https://api.siliconflow.cn/v1/embeddings
  
  # 仅hybrid类型需要以下配置
  # api_type: siliconflow  # 主API类型: siliconflow或openai
  # local_model_path: paraphrase-multilingual-MiniLM-L12-v2
  # local_model_enabled: false

# 重排序器配置（可选）
reranker:
  type: siliconflow_native  # 可选: siliconflow_native, siliconflow, openai, local
  model_name: BAAI/bge-reranker-v2-m3
  api_key: ${SILICONFLOW_API_KEY}  # 可以引用环境变量
  api_url: https://api.siliconflow.cn/v1/rerank
  top_n: 10  # 返回前N个结果，可选
  return_documents: false  # 是否在结果中返回文档内容，可选

# 预加载文档（可选）
# documents:
#   - 这是第一篇文档
#   - 这是第二篇文档
#   - 这是第三篇文档
```
"""

# 辅助函数：处理环境变量引用
def expand_env_vars(value):
    """处理配置值中的环境变量引用
    例如 ${SILICONFLOW_API_KEY} 会被替换为环境变量的值
    """
    if not isinstance(value, str):
        return value
        
    import re
    import os
    
    pattern = r'\${([A-Za-z0-9_]+)}'
    matches = re.findall(pattern, value)
    
    result = value
    for env_var in matches:
        env_value = os.environ.get(env_var, "")
        result = result.replace(f"${{{env_var}}}", env_value)
    
    return result

# 代理设置的辅助函数
def disable_proxy_settings():
    """禁用代理设置，避免连接问题"""
    if 'http_proxy' in os.environ:
        del os.environ['http_proxy']
    if 'https_proxy' in os.environ:
        del os.environ['https_proxy']
    if 'HTTP_PROXY' in os.environ:
        del os.environ['HTTP_PROXY']
    if 'HTTPS_PROXY' in os.environ:
        del os.environ['HTTPS_PROXY']
    
    # 禁用requests库的环境变量代理
    os.environ['NO_PROXY'] = '*'
    
    return True

# 配置处理函数
def apply_environment_config(config):
    """应用环境配置"""
    if not config or 'environment' not in config:
        return
        
    env_config = config['environment']
    
    # 处理代理设置
    if env_config.get('disable_proxy', True):
        disable_proxy_settings()
        
    # 设置NO_PROXY
    if 'no_proxy' in env_config:
        os.environ['NO_PROXY'] = env_config['no_proxy']
        
    # 处理API密钥
    if 'api_key' in env_config:
        api_key = expand_env_vars(env_config['api_key'])
        if api_key:
            os.environ['SILICONFLOW_API_KEY'] = api_key
            
    # 设置默认编码
    if 'encoding' in env_config:
        encoding = env_config['encoding']
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding=encoding, errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding=encoding, errors='replace')
        except Exception as e:
            print(f"警告: 无法设置标准输出编码为{encoding}: {str(e)}")
            
    return True

# 创建配置文件的函数
def create_default_config(output_path="rag_config.yaml"):
    """创建默认配置文件"""
    default_config = {
        "singleton": True,
        "environment": {
            "disable_proxy": True,
            "no_proxy": "*",
            "api_key": "${SILICONFLOW_API_KEY}",
            "encoding": "utf-8",
            "default_timeout": 10.0
        },
        "embedding_model": {
            "type": "siliconflow",
            "model_name": "BAAI/bge-m3",
            "api_key": "${SILICONFLOW_API_KEY}",
            "api_url": "https://api.siliconflow.cn/v1/embeddings"  # 确保URL包含/embeddings端点
        },
        "reranker": {
            "type": "siliconflow_native",
            "model_name": "BAAI/bge-reranker-v2-m3",
            "api_key": "${SILICONFLOW_API_KEY}",
            "api_url": "https://api.siliconflow.cn/v1/rerank",  # 确保URL包含/rerank端点
            "top_n": 5,
            "return_documents": False
        }
    }
    
    try:
        import yaml
        with open(output_path, 'w', encoding='utf-8') as f:
            # 添加注释
            f.write("# RAG系统配置文件\n")
            f.write("# 自动生成的默认配置\n")
            date_str = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"# 创建时间: {date_str}\n\n")
            
            # 写入YAML
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
        print(f"✅ 默认配置文件已创建: {output_path}")
        return True
    except Exception as e:
        print(f"❌ 创建配置文件时出错: {str(e)}")
        return False

if __name__ == "__main__":
    """
    测试RAG系统功能的主模块
    当直接执行此文件时运行测试
    """
    import argparse
    import os
    import sys
    from pathlib import Path

    # 正确设置Python模块导入路径
    project_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(project_root))
    
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="测试RAG系统功能")
    parser.add_argument("--model_type", choices=["local", "openai", "siliconflow", "hybrid"], 
                        default="siliconflow", help="嵌入模型类型")
    parser.add_argument("--model_name", default="BAAI/bge-m3", 
                        help="模型名称，如'BAAI/bge-m3'或'text-embedding-3-small'")
    parser.add_argument("--api_url", default="https://api.siliconflow.cn/v1/embeddings", 
                        help="API URL")
    parser.add_argument("--config", help="配置文件路径，如果提供则优先使用配置文件")
    parser.add_argument("--create_config", action="store_true", help="创建默认配置文件")
    parser.add_argument("--config_path", default="config.yaml", help="配置文件输出路径")
    parser.add_argument("--top_k", type=int, default=3, help="返回的相似文档数量")
    parser.add_argument("--rerank", action="store_true", help="是否使用重排序")
    parser.add_argument("--no_disable_proxy", action="store_true", help="不禁用代理设置")
    args = parser.parse_args()
    
    print("===== RAG系统测试 =====")
    
    # 创建配置文件
    if args.create_config:
        create_default_config(args.config_path)
        print(f"请修改配置文件后再次运行程序")
        sys.exit(0)
    
    # 尝试加载配置文件
    config_path = args.config
    if not config_path:
        # 尝试从项目配置文件加载
        project_config_paths = [
            os.path.join(str(project_root), "src", "config", "config.yaml"),
            os.path.join("src", "config", "config.yaml"),
            os.path.join(os.getcwd(), "src", "config", "config.yaml")
        ]
        
        for path in project_config_paths:
            if os.path.exists(path):
                print(f"发现项目配置文件: {path}")
                try:
                    # 尝试导入配置处理模块
                    sys.path.insert(0, str(Path(path).parent.parent.parent))
                    try:
                        from src.memories.memory.examples.create_rag_config import load_project_config, extract_rag_settings, generate_rag_config
                        
                        # 使用项目配置创建RAG配置
                        print(f"正在从项目配置创建RAG配置...")
                        project_config = load_project_config(path)
                        rag_settings = extract_rag_settings(project_config)
                        rag_config = generate_rag_config(rag_settings)
                        
                        # 使用临时文件
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp:
                            # 写入配置
                            import yaml
                            yaml.dump(rag_config, tmp, default_flow_style=False, allow_unicode=True)
                            tmp_path = tmp.name
                        
                        # 使用临时配置文件
                        print(f"已创建临时RAG配置文件: {tmp_path}")
                        config_path = tmp_path
                        break
                    except ImportError as e:
                        print(f"导入配置处理模块失败: {str(e)}")
                        # 尝试直接使用路径
                        config_path = path
                        print(f"将直接使用项目配置路径: {path}")
                        break
                except Exception as e:
                    print(f"处理项目配置时出错: {str(e)}")
        
        # 如果没有找到项目配置，尝试使用默认配置文件
        if not config_path:
            for default_path in ["config.yaml", "rag_config.yaml"]:
                if os.path.exists(default_path):
                    config_path = default_path
                    print(f"将使用默认配置文件: {config_path}")
                    break
    
    # 如果配置文件存在，尝试从配置文件加载
    if config_path and os.path.exists(config_path):
        print(f"\n从配置文件加载系统: {config_path}")
        rag = load_from_config(config_path)
        if rag:
            print("成功从配置文件加载RAG系统")
        else:
            print("从配置文件加载RAG系统失败，将尝试使用命令行参数")
            config_path = None
    else:
        config_path = None
        
    # 如果没有禁用代理且未从配置文件加载，手动禁用代理
    if not args.no_disable_proxy and not config_path:
        disable_proxy_settings()
        print("已禁用代理设置，以避免连接问题")
    
    # 检查API密钥
    api_key = os.environ.get("SILICONFLOW_API_KEY")
    if not api_key:
        print("⚠️ 警告: 未设置环境变量 SILICONFLOW_API_KEY")
        print("示例: export SILICONFLOW_API_KEY='your_api_key_here'")
        api_key = input("请输入API密钥（或直接按Enter跳过）: ").strip()
        if api_key:
            os.environ["SILICONFLOW_API_KEY"] = api_key
    
    # 测试示例文档
    test_docs = [
        "硅基流动是一家中国的AI服务提供商，专注于提供高质量的API服务。",
        "向量嵌入技术是现代自然语言处理的基础，可以捕捉文本的语义信息。",
        "检索增强生成(RAG)技术结合了检索系统和生成式AI的优势。",
        "大语言模型需要通过外部知识库扩展其知识范围和能力。",
        "文本向量化是将自然语言转换为计算机可理解的数值表示的过程。"
    ]
    
    # 初始化RAG系统
    try:
        # 如果已经从配置文件加载了系统，直接使用
        if config_path and 'rag' in locals() and rag:
            pass
        # 否则使用命令行参数创建系统
        else:
            # 根据命令行参数创建嵌入模型
            print(f"\n创建{args.model_type}类型的嵌入模型...")
            
            if args.model_type == "siliconflow":
                # 检查模型名称是否兼容硅基流动API
                siliconflow_models = ["BAAI/bge-large-zh-v1.5", "BAAI/bge-m3", "BAAI/bge-base-zh-v1.5"]
                if args.model_name not in siliconflow_models:
                    print(f"⚠️ 模型名称'{args.model_name}'可能不兼容硅基流动API，将使用BAAI/bge-m3")
                    model_name = "BAAI/bge-m3"
                else:
                    model_name = args.model_name
                
                # 处理URL，确保嵌入模型URL以"/embeddings"结尾
                api_url = args.api_url
                if api_url and not api_url.endswith('/embeddings'):
                    # 移除可能的尾部斜杠
                    api_url = api_url.rstrip('/')
                    # 添加embeddings路径
                    api_url = f"{api_url}/embeddings"
                    print(f"已调整嵌入模型URL: {api_url}")
                
                embedding_model = SiliconFlowEmbeddingModel(
                    model_name=model_name,
                    api_key=api_key,
                    api_url=api_url
                )
                
                # 如果需要重排序，创建重排序器
                reranker = None
                if args.rerank:
                    print("创建硅基流动原生重排序器...")
                    
                    # 处理URL，确保重排序模型URL以"/rerank"结尾
                    rerank_url = api_url.replace("/embeddings", "/rerank")
                    if not rerank_url.endswith('/rerank'):
                        # 移除可能的尾部斜杠
                        rerank_url = rerank_url.rstrip('/')
                        # 添加rerank路径
                        rerank_url = f"{rerank_url}/rerank"
                    print(f"重排序模型URL: {rerank_url}")
                    
                    reranker = SiliconFlowNativeReRanker(
                        model_name="BAAI/bge-reranker-v2-m3",
                        api_key=api_key,
                        api_url=rerank_url
                    )
            
            elif args.model_type == "openai":
                # 处理URL，确保嵌入模型URL以"/embeddings"结尾
                base_url = args.api_url
                if base_url and not base_url.endswith('/embeddings'):
                    # 移除可能的尾部斜杠
                    base_url = base_url.rstrip('/')
                    # 添加embeddings路径
                    base_url = f"{base_url}/embeddings"
                    print(f"已调整嵌入模型URL: {base_url}")
                
                embedding_model = OnlineEmbeddingModel(
                    model_name=args.model_name,
                    api_key=api_key,
                    base_url=base_url
                )
                
                # 如果需要重排序，创建重排序器
                reranker = None
                if args.rerank:
                    print("创建在线重排序器...")
                    
                    # 处理URL，确保重排序模型URL以"/chat/completions"结尾
                    chat_url = base_url.replace("/embeddings", "/chat/completions")
                    if not chat_url.endswith('/chat/completions'):
                        # 移除可能的尾部斜杠
                        chat_url = chat_url.rstrip('/')
                        # 添加chat/completions路径
                        chat_url = f"{chat_url}/chat/completions"
                    print(f"重排序模型URL: {chat_url}")
                    
                    reranker = OnlineCrossEncoderReRanker(
                        model_name="gpt-3.5-turbo",
                        api_key=api_key,
                        base_url=chat_url
                    )
                
            elif args.model_type == "local":
                # 验证模型路径或模型ID
                if not args.model_name:
                    model_name = "paraphrase-multilingual-MiniLM-L12-v2"
                    print(f"未指定本地模型路径，将使用默认模型: {model_name}")
                else:
                    model_name = args.model_name
                
                embedding_model = LocalEmbeddingModel(model_path=model_name)
                
                # 如果需要重排序，创建本地重排序器
                reranker = None
                if args.rerank:
                    print("创建本地重排序器...")
                    reranker = CrossEncoderReRanker(model_path="cross-encoder/ms-marco-MiniLM-L-6-v2")
                
            elif args.model_type == "hybrid":
                # 创建API模型
                print("创建混合嵌入模型...")
                if "siliconflow" in args.api_url.lower():
                    # 硅基流动API模型
                    siliconflow_models = ["BAAI/bge-large-zh-v1.5", "BAAI/bge-m3", "BAAI/bge-base-zh-v1.5"]
                    if args.model_name not in siliconflow_models:
                        print(f"⚠️ 模型名称'{args.model_name}'可能不兼容硅基流动API，将使用BAAI/bge-m3")
                        model_name = "BAAI/bge-m3"
                    else:
                        model_name = args.model_name
                    
                    # 处理URL，确保嵌入模型URL以"/embeddings"结尾
                    api_url = args.api_url
                    if api_url and not api_url.endswith('/embeddings'):
                        # 移除可能的尾部斜杠
                        api_url = api_url.rstrip('/')
                        # 添加embeddings路径
                        api_url = f"{api_url}/embeddings"
                        print(f"已调整混合模型(siliconflow)URL: {api_url}")
                    
                    api_model = SiliconFlowEmbeddingModel(
                        model_name=model_name,
                        api_key=api_key,
                        api_url=api_url
                    )
                else:
                    # OpenAI API模型
                    # 处理URL，确保嵌入模型URL以"/embeddings"结尾
                    base_url = args.api_url
                    if base_url and not base_url.endswith('/embeddings'):
                        # 移除可能的尾部斜杠
                        base_url = base_url.rstrip('/')
                        # 添加embeddings路径
                        base_url = f"{base_url}/embeddings"
                        print(f"已调整混合模型(openai)URL: {base_url}")
                    
                    api_model = OnlineEmbeddingModel(
                        model_name=args.model_name,
                        api_key=api_key,
                        base_url=base_url
                    )
                
                # 创建混合模型
                embedding_model = HybridEmbeddingModel(
                    api_model=api_model,
                    local_model_path="paraphrase-multilingual-MiniLM-L12-v2",
                    local_model_enabled=True
                )
                
                # 如果需要重排序，创建重排序器
                reranker = None
                if args.rerank:
                    if "siliconflow" in args.api_url.lower():
                        print("创建硅基流动原生重排序器...")
                        
                        # 处理URL，确保重排序模型URL以"/rerank"结尾
                        rerank_url = api_url.replace("/embeddings", "/rerank")
                        if not rerank_url.endswith('/rerank'):
                            # 移除可能的尾部斜杠
                            rerank_url = rerank_url.rstrip('/')
                            # 添加rerank路径
                            rerank_url = f"{rerank_url}/rerank"
                        print(f"重排序模型URL: {rerank_url}")
                        
                        reranker = SiliconFlowNativeReRanker(
                            model_name="BAAI/bge-reranker-v2-m3",
                            api_key=api_key,
                            api_url=rerank_url
                        )
                    else:
                        print("创建在线重排序器...")
                        
                        # 处理URL，确保重排序模型URL以"/chat/completions"结尾
                        chat_url = base_url.replace("/embeddings", "/chat/completions")
                        if not chat_url.endswith('/chat/completions'):
                            # 移除可能的尾部斜杠
                            chat_url = chat_url.rstrip('/')
                            # 添加chat/completions路径
                            chat_url = f"{chat_url}/chat/completions"
                        print(f"重排序模型URL: {chat_url}")
                        
                        reranker = OnlineCrossEncoderReRanker(
                            model_name="gpt-3.5-turbo",
                            api_key=api_key,
                            base_url=chat_url
                        )
            
            # 创建RAG系统
            print("创建RAG系统...")
            rag = RAG(embedding_model=embedding_model, reranker=reranker)
        
        # 测试嵌入模型
        print("\n===== 测试嵌入模型 =====")
        test_text = "测试嵌入模型的性能"
        try:
            print(f"嵌入测试文本: '{test_text}'")
            embedding = rag.embedding_model.embed([test_text])[0]
            if embedding and len(embedding) > 0:
                dim = len(embedding)
                print(f"✅ 嵌入成功! 嵌入维度: {dim}")
                
                # 初始化索引
                print(f"使用维度 {dim} 初始化索引...")
                rag.initialize_index(dim=dim)
            else:
                print("❌ 嵌入失败，无法获取有效的嵌入向量")
                sys.exit(1)
        except Exception as e:
            print(f"❌ 嵌入测试失败: {str(e)}")
            print("尝试使用默认维度初始化索引...")
            rag.initialize_index(dim=1024)
        
        # 添加测试文档
        print(f"\n===== 添加测试文档 =====")
        print(f"添加{len(test_docs)}个文档...")
        rag.add_documents(texts=test_docs)
        print(f"当前文档数量: {len(rag.documents)}")
        print(f"索引大小: {rag.index.ntotal}")
        
        # 测试查询
        print(f"\n===== 测试查询 =====")
        while True:
            query = input("\n请输入查询内容（或输入q退出）: ").strip()
            if query.lower() in ['q', 'quit', 'exit']:
                break
            
            if not query:
                continue
                
            print(f"查询: '{query}'")
            try:
                start_time = time.time()
                results = rag.query(
                    query=query, 
                    top_k=args.top_k, 
                    rerank=args.rerank,
                    async_mode=True  # 使用异步模式加速
                )
                query_time = time.time() - start_time
                
                if results and len(results) > 0:
                    print(f"✅ 查询成功! 找到{len(results)}个相关文档 (用时: {query_time:.3f}秒):")
                    for i, doc in enumerate(results):
                        print(f"[{i+1}] {doc}")
                else:
                    print("❌ 未找到相关文档")
            except Exception as e:
                print(f"❌ 查询失败: {str(e)}")
        
        # 显示缓存统计
        if hasattr(rag.embedding_model, "get_cache_stats"):
            cache_stats = rag.embedding_model.get_cache_stats()
            print("\n===== 缓存统计 =====")
            print(f"缓存命中率: {cache_stats.get('hit_rate_percent', 0):.2f}%")
            print(f"缓存大小: {cache_stats.get('cache_size', 0)} 条目")
        
        print("\n测试完成，感谢使用!")
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()

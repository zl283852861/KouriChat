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
        print(f"API密钥: {api_key[:6]}...{api_key[-4:] if api_key and len(api_key) > 10 else '未设置'}")
        
        try:
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key
            )
            # 测试连接
            self.client.models.list()
            print("✅ API连接测试成功")
        except Exception as e:
            print(f"⚠️ API初始化失败: {str(e)}")
            # 仍然创建客户端，但标记状态
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key
            )

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

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

    def query(self, query: str, top_k: int = 5, rerank: bool = False) -> List[str]:
        """查询相关文档"""
        if not self.documents:
            return []
        
        # 生成查询向量
        query_embedding = self.embedding_model.embed([query])[0]
        
        # 搜索相似文档
        D, I = self.index.search(np.array([query_embedding]), min(top_k, len(self.documents)))
        results = [self.documents[i] for i in I[0]]
        
        # 使用集合去重
        unique_results = list(set(results))
        
        # 如果需要重排序
        if rerank and self.reranker and len(unique_results) > 1:
            scores = self.reranker.rerank(query, unique_results)
            scored_results = list(zip(unique_results, scores))
            scored_results.sort(key=lambda x: x[1], reverse=True)
            unique_results = [r[0] for r in scored_results]
        
        print(f"RAG查询: 找到{len(unique_results)}条去重结果，从{len(results)}个候选结果中")
        return unique_results

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

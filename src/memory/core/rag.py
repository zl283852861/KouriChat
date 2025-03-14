import re

import numpy as np
import faiss
from abc import ABC, abstractmethod
from typing import List, Optional
import openai
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

    def embed(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, convert_to_tensor=False).tolist()


class OnlineEmbeddingModel(EmbeddingModel):
    def __init__(self, model_name: str, api_key: Optional[str] = None, url: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key
        self.url = url
        self.client = OpenAI(base_url=self.url, api_key=self.api_key)  # 实例化新的客户端

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        使用在线嵌入模型生成文本嵌入向量
        """
        embeddings = []
        for text in texts:
            try:
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=text
                )
                # 检查返回值是否是预期的嵌入向量数据结构
                if hasattr(response, 'data') and len(response.data) > 0 and hasattr(response.data[0], 'embedding'):
                    embedding = response.data[0].embedding
                    embeddings.append(embedding)
                else:
                    print(f"Unexpected response format for text '{text}': {response}")
                    raise ValueError(f"Unexpected response format for text '{text}'")
            except Exception as e:
                print(f"Error embedding text '{text}': {e}")
                raise e
        return embeddings


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
                        {"role": "system", "content": "您是一个帮助评估文档与查询相关性的助手。请仅返回一个0到1之间的浮点数，不要包含其他文本。"},
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

    def add_documents(self, documents: List[str]):
        if not documents:
            return

        # 生成嵌入
        embeddings = self.embedding_model.embed(documents)
        embeddings = np.array(embeddings, dtype=np.float32)

        # 初始化FAISS索引
        if self.index is None:
            dim = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dim)

        # 添加文档到索引
        self.index.add(embeddings)
        self.documents.extend(documents)

    def query(self, query: str, top_k: int = 5, rerank: bool = False) -> List[str]:
        # 生成查询嵌入
        query_embedding = self.embedding_model.embed([query])[0]
        query_embedding = np.array([query_embedding], dtype=np.float32)

        # 初步检索
        distances, indices = self.index.search(query_embedding, top_k * 2 if rerank else top_k)

        # 获取候选文档
        candidate_docs = [self.documents[i] for i in indices[0]]

        # 重排逻辑
        if rerank and self.reranker:
            scores = self.reranker.rerank(query, candidate_docs)
            sorted_pairs = sorted(zip(candidate_docs, scores), key=lambda x: x[1], reverse=True)
            return [doc for doc, _ in sorted_pairs[:top_k]]

        return candidate_docs[:top_k]

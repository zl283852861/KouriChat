import re
import time
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
    # 添加类变量，记录全局本地模型状态
    _global_local_model = None
    _global_local_model_initialized = False
    _prefer_local_model = False  # 新增：是否优先使用本地模型
    
    def __init__(self, model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )
        self._failure_count = 0
        self._last_failure_time = 0
        self._max_failures = 3
        self._cooldown_period = 300
        
        # 使用类变量而不是实例变量
        self._local_model = OnlineEmbeddingModel._global_local_model
        self._local_model_initialized = OnlineEmbeddingModel._global_local_model_initialized
        
        # 如果全局模型未初始化，尝试初始化
        if not OnlineEmbeddingModel._global_local_model_initialized:
            self._init_local_model()

    def _init_local_model(self):
        """初始化本地备用模型"""
        # 如果全局模型已初始化，直接使用
        if OnlineEmbeddingModel._global_local_model_initialized:
            self._local_model = OnlineEmbeddingModel._global_local_model
            self._local_model_initialized = True
            return
            
        try:
            print("初始化本地备用模型...")
            # 使用一个小型的本地模型作为备用
            local_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
            
            # 更新类变量
            OnlineEmbeddingModel._global_local_model = local_model
            OnlineEmbeddingModel._global_local_model_initialized = True
            OnlineEmbeddingModel._prefer_local_model = True  # 设置为优先使用本地模型
            
            # 更新实例变量
            self._local_model = local_model
            self._local_model_initialized = True
            
            print("本地备用模型初始化成功，已设置为默认使用本地模型")
        except Exception as e:
            print(f"初始化本地备用模型失败: {str(e)}")
            OnlineEmbeddingModel._global_local_model_initialized = False
            self._local_model_initialized = False

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
            
        # 检查是否优先使用本地模型
        if OnlineEmbeddingModel._prefer_local_model:
            # 确保本地模型已初始化
            if not self._local_model_initialized:
                self._init_local_model()
                
            if self._local_model_initialized and self._local_model:
                print("使用本地模型生成嵌入向量（优先模式）")
                try:
                    local_embeddings = self._local_model.encode(texts, convert_to_tensor=False).tolist()
                    # 确保所有嵌入向量维度一致（本地模型应该是768维）
                    expected_dim = 768
                    return [emb if len(emb) == expected_dim else [0.0] * expected_dim for emb in local_embeddings]
                except Exception as e:
                    print(f"本地模型生成嵌入向量失败: {str(e)}")
                    # 如果本地模型失败，尝试使用在线API（不改变优先级设置）
                    print("尝试使用在线API作为备用...")
            else:
                print("本地模型未初始化，尝试使用在线API...")
        
        # 检查在线API是否可用
        current_time = time.time()
        if self._failure_count >= self._max_failures and current_time - self._last_failure_time < self._cooldown_period:
            print(f"嵌入服务暂时不可用，将在{int(self._cooldown_period - (current_time - self._last_failure_time))}秒后重试")
            # 尝试使用本地模型
            if not self._local_model_initialized:
                self._init_local_model()
                
            if self._local_model_initialized and self._local_model:
                print("使用本地备用模型生成嵌入向量")
                try:
                    local_embeddings = self._local_model.encode(texts, convert_to_tensor=False).tolist()
                    # 确保所有嵌入向量维度一致（本地模型应该是768维）
                    expected_dim = 768
                    return [emb if len(emb) == expected_dim else [0.0] * expected_dim for emb in local_embeddings]
                except Exception as e:
                    print(f"本地模型生成嵌入向量失败: {str(e)}")
                    
            # 如果本地模型也失败，返回零向量
            return [[0.0] * 768 for _ in texts]  # 使用768维，与本地模型一致
            
        embeddings = []
        use_local_model = OnlineEmbeddingModel._prefer_local_model  # 使用全局设置
        expected_dim = 768 if OnlineEmbeddingModel._prefer_local_model else 1536  # 根据模型选择默认维度
        
        # 检查是否已经有嵌入向量，确定期望的维度
        if hasattr(self, 'index') and self.index is not None and hasattr(self.index, 'd'):
            expected_dim = self.index.d
            print(f"使用现有索引维度: {expected_dim}")
        
        # 定义空响应检测函数
        def is_empty_response(resp):
            if resp is None:
                return True
            if isinstance(resp, str):
                # 检查是否为空字符串或只包含空白字符
                return not resp.strip()
            return False
        
        for text in texts:
            if not text.strip():
                embeddings.append([0.0] * expected_dim)  # 使用期望的维度
                continue

            # 如果已经决定使用本地模型，跳过API调用
            if use_local_model:
                if not self._local_model_initialized:
                    self._init_local_model()
                    
                if self._local_model_initialized and self._local_model:
                    try:
                        embedding = self._local_model.encode([text], convert_to_tensor=False)[0].tolist()
                        # 如果维度不匹配，调整维度
                        if len(embedding) != expected_dim:
                            if len(embedding) < expected_dim:
                                # 如果维度小于期望维度，填充零
                                embedding = embedding + [0.0] * (expected_dim - len(embedding))
                            else:
                                # 如果维度大于期望维度，截断
                                embedding = embedding[:expected_dim]
                        embeddings.append(embedding)
                    except Exception as e:
                        print(f"本地模型生成单个嵌入向量失败: {str(e)}")
                        embeddings.append([0.0] * expected_dim)
                else:
                    embeddings.append([0.0] * expected_dim)
                continue

            # 只尝试一次API调用，如果失败立即切换到本地模型
            try:
                # 打印调试信息
                print(f"尝试获取嵌入向量，模型: {self.model_name}, 文本长度: {len(text)}")
                
                # 创建新的客户端实例，避免可能的状态问题
                client = OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key
                )
                
                # 设置超时，防止请求卡住
                response = client.embeddings.create(
                    model=self.model_name,
                    input=text,
                    encoding_format="float",
                    timeout=10.0  # 设置10秒超时
                )
                
                # 打印响应类型，帮助调试
                print(f"响应类型: {type(response)}")
                
                # 检查响应是否为空
                if is_empty_response(response):
                    print("收到空响应，切换到本地模型")
                    raise ValueError("API返回空响应")
                
                # 检查响应是否为字符串
                if isinstance(response, str):
                    # 打印响应前30个字符，避免过多空行
                    clean_resp = response.replace('\n', '\\n')
                    print(f"收到字符串响应: {clean_resp[:30]}...")
                    raise ValueError("API返回字符串而非对象")

                if not response:
                    print("响应为None，切换到本地模型")
                    raise ValueError("API返回空响应")
                    
                # 检查response是否有data属性
                if not hasattr(response, 'data') or not response.data:
                    print(f"响应缺少data属性或data为空: {response}")
                    raise ValueError("响应缺少data属性")

                embedding = response.data[0].embedding
                
                # 检查嵌入向量格式
                if not isinstance(embedding, list) or len(embedding) == 0:
                    print(f"无效的嵌入格式: {type(embedding)}")
                    raise ValueError("无效的嵌入格式")
                    
                # 如果这是第一个成功的嵌入，更新期望维度
                if not embeddings and len(embedding) != expected_dim:
                    expected_dim = len(embedding)
                    print(f"更新期望维度为: {expected_dim}")
                    
                # 确保维度一致
                if len(embedding) != expected_dim:
                    print(f"嵌入向量维度不一致: 期望{expected_dim}，实际{len(embedding)}")
                    if len(embedding) < expected_dim:
                        # 如果维度小于期望维度，填充零
                        embedding = embedding + [0.0] * (expected_dim - len(embedding))
                    else:
                        # 如果维度大于期望维度，截断
                        embedding = embedding[:expected_dim]

                embeddings.append(embedding)
                self._failure_count = 0

            except Exception as e:
                print(f"嵌入失败: {str(e)}")
                self._failure_count += 1
                self._last_failure_time = time.time()
                
                # 直接切换到本地模型
                print("直接切换到本地模型")
                use_local_model = True
                # 设置全局优先使用本地模型
                OnlineEmbeddingModel._prefer_local_model = True
                print("已设置默认使用本地模型")
                
                # 初始化本地模型
                if not self._local_model_initialized:
                    self._init_local_model()
                    
                if self._local_model_initialized and self._local_model:
                    try:
                        embedding = self._local_model.encode([text], convert_to_tensor=False)[0].tolist()
                        # 确保维度一致
                        if len(embedding) != expected_dim:
                            if len(embedding) < expected_dim:
                                # 如果维度小于期望维度，填充零
                                embedding = embedding + [0.0] * (expected_dim - len(embedding))
                            else:
                                # 如果维度大于期望维度，截断
                                embedding = embedding[:expected_dim]
                        embeddings.append(embedding)
                    except Exception as local_e:
                        print(f"本地模型生成嵌入向量失败: {str(local_e)}")
                        embeddings.append([0.0] * expected_dim)
                else:
                    embeddings.append([0.0] * expected_dim)
        
        # 最终检查，确保所有嵌入向量维度一致
        for i, emb in enumerate(embeddings):
            if len(emb) != expected_dim:
                print(f"修正嵌入向量维度: 索引{i}, 期望{expected_dim}, 实际{len(emb)}")
                if len(emb) < expected_dim:
                    embeddings[i] = emb + [0.0] * (expected_dim - len(emb))
                else:
                    embeddings[i] = emb[:expected_dim]
                    
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
                        {"role": "system",
                         "content": "您是一个帮助评估文档与查询相关性的助手。请仅返回一个0到1之间的浮点数，不要包含其他文本。"},
                        {"role": "user", "content": f"查询：{query}\n文档：{doc}\n请评估该文档与查询的相关性分数（0-1）："}
                    ]
                )
                content = response.choices[0].message.content.strip()
                match = re.search(r"0?\.\d+|\d\.?\d*", content)
                if match:
                    score = float(match.group())
                    score = max(0.0, min(1.0, score))
                else:
                    score = 0.0
            except Exception as e:
                score = 0.0
            scores.append(score)
        return scores


class RAGMemory:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None or not kwargs.get('singleton', True):
            cls._instance = super(RAGMemory, cls).__new__(cls)
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

    def add_documents(self, documents: List[str]):
        if not documents:
            return

        try:
            # 生成嵌入
            print(f"开始为{len(documents)}个文档生成嵌入向量")
            embeddings = self.embedding_model.embed(documents)
            if not embeddings or len(embeddings) == 0:
                print("嵌入模型返回空值，跳过添加文档")
                return

            # 过滤掉空的嵌入向量并检查维度一致性
            valid_embeddings = []
            valid_documents = []
            embedding_dims = set()
            
            for i, embedding in enumerate(embeddings):
                if not embedding or len(embedding) == 0:
                    print(f"跳过空的嵌入向量，文档: {documents[i][:50]}...")
                    continue
                    
                # 记录嵌入向量的维度
                embedding_dims.add(len(embedding))
                valid_embeddings.append(embedding)
                valid_documents.append(documents[i])
            
            if not valid_embeddings:
                print("没有有效的嵌入向量，跳过添加文档")
                return
                
            # 检查是否有多种维度
            if len(embedding_dims) > 1:
                print(f"检测到多种嵌入向量维度: {embedding_dims}")
                # 选择最常见的维度
                dim_counts = {}
                for emb in valid_embeddings:
                    dim = len(emb)
                    dim_counts[dim] = dim_counts.get(dim, 0) + 1
                
                most_common_dim = max(dim_counts.items(), key=lambda x: x[1])[0]
                print(f"选择最常见的维度: {most_common_dim}")
                
                # 过滤出维度一致的嵌入向量
                consistent_embeddings = []
                consistent_documents = []
                for i, emb in enumerate(valid_embeddings):
                    if len(emb) == most_common_dim:
                        consistent_embeddings.append(emb)
                        consistent_documents.append(valid_documents[i])
                    else:
                        print(f"跳过维度不一致的嵌入向量: 期望{most_common_dim}，实际{len(emb)}")
                
                valid_embeddings = consistent_embeddings
                valid_documents = consistent_documents
                
                if not valid_embeddings:
                    print("过滤后没有维度一致的嵌入向量，跳过添加文档")
                    return
            
            # 转换为NumPy数组前再次检查维度一致性
            try:
                # 尝试转换为NumPy数组
                embeddings_array = np.array(valid_embeddings, dtype=np.float32)
                
                # 检查数组形状
                if len(embeddings_array.shape) != 2:
                    print(f"无效的嵌入维度: {embeddings_array.shape}，跳过添加文档")
                    
                    # 尝试手动创建一致维度的数组
                    print("尝试手动创建一致维度的数组...")
                    dim = len(valid_embeddings[0])
                    consistent_embeddings = []
                    consistent_documents = []
                    
                    for i, emb in enumerate(valid_embeddings):
                        if len(emb) == dim:
                            consistent_embeddings.append(emb)
                            consistent_documents.append(valid_documents[i])
                    
                    if not consistent_embeddings:
                        print("无法创建一致维度的数组，跳过添加文档")
                        return
                        
                    # 重新尝试创建数组
                    embeddings_array = np.array(consistent_embeddings, dtype=np.float32)
                    valid_embeddings = consistent_embeddings
                    valid_documents = consistent_documents
            except Exception as e:
                print(f"创建NumPy数组失败: {str(e)}")
                
                # 尝试逐个添加文档
                print("尝试逐个添加文档...")
                for i, (doc, emb) in enumerate(zip(valid_documents, valid_embeddings)):
                    try:
                        # 初始化索引（如果需要）
                        if self.index is None:
                            dim = len(emb)
                            self.index = faiss.IndexFlatL2(dim)
                            print(f"初始化FAISS索引，维度: {dim}")
                        
                        # 检查维度是否匹配
                        if len(emb) != self.index.d:
                            print(f"跳过维度不匹配的文档: 期望{self.index.d}，实际{len(emb)}")
                            continue
                            
                        # 添加单个文档
                        emb_array = np.array([emb], dtype=np.float32)
                        self.index.add(emb_array)
                        self.documents.append(doc)
                        print(f"成功添加单个文档 ({i+1}/{len(valid_documents)})")
                    except Exception as doc_e:
                        print(f"添加单个文档失败: {str(doc_e)}")
                
                print(f"逐个添加完成，成功添加{len(self.documents)}个文档")
                return

            # 初始化或检查索引维度
            if self.index is None:
                dim = embeddings_array.shape[1]
                self.index = faiss.IndexFlatL2(dim)
                print(f"初始化FAISS索引，维度: {dim}")
            elif embeddings_array.shape[1] != self.index.d:
                print(f"嵌入维度不匹配: 期望{self.index.d}，实际{embeddings_array.shape[1]}")
                
                # 如果维度不匹配，我们需要重新创建索引
                print("维度不匹配，重新创建索引...")
                
                # 保存旧文档和嵌入
                old_documents = self.documents.copy() if self.documents else []
                
                # 创建新索引
                dim = embeddings_array.shape[1]
                self.index = faiss.IndexFlatL2(dim)
                self.documents = []
                print(f"创建新索引，维度: {dim}")
                
                # 添加新文档
                self.index.add(embeddings_array)
                self.documents.extend(valid_documents)
                print(f"成功添加{len(valid_documents)}个新文档到索引")
                
                # 如果有旧文档，尝试重新嵌入它们
                if old_documents:
                    print(f"尝试重新嵌入{len(old_documents)}个旧文档...")
                    try:
                        # 分批处理旧文档，避免一次处理太多
                        batch_size = 10
                        for i in range(0, len(old_documents), batch_size):
                            batch = old_documents[i:i+batch_size]
                            try:
                                self.add_documents(batch)
                                print(f"成功重新嵌入批次 {i//batch_size + 1}/{(len(old_documents)-1)//batch_size + 1}")
                            except Exception as batch_e:
                                print(f"重新嵌入批次失败: {str(batch_e)}")
                    except Exception as e:
                        print(f"重新嵌入旧文档失败: {str(e)}")
                
                return
            
            # 添加文档到索引
            self.index.add(embeddings_array)
            self.documents.extend(valid_documents)
            print(f"成功添加{len(valid_documents)}个文档到索引")
            
        except Exception as e:
            print(f"添加文档失败: {str(e)}")
            # 不抛出异常，让程序继续运行

    def query(self, query: str, top_k: int = 5, rerank: bool = False) -> List[str]:
        # 添加空库保护
        if not self.documents:
            print("文档库为空，无法执行查询")
            return []

        try:
            # 确保索引已初始化
            if self.index is None:
                print("索引未初始化，尝试初始化...")
                try:
                    sample_embed = self.embedding_model.embed(["sample text"])[0]
                    if not sample_embed or len(sample_embed) == 0:
                        print("无法获取样本嵌入向量，返回空结果")
                        return []
                    self.initialize_index(len(sample_embed))
                except Exception as e:
                    print(f"初始化索引失败: {str(e)}")
                    return []

            # 生成查询嵌入
            print(f"为查询生成嵌入向量: {query[:50]}...")
            query_embedding = self.embedding_model.embed([query])[0]
            
            if not query_embedding or len(query_embedding) == 0:
                print("查询嵌入向量为空，返回空结果")
                return []
                
            # 检查维度是否匹配
            if len(query_embedding) != self.index.d:
                print(f"查询嵌入维度不匹配: 期望{self.index.d}，实际{len(query_embedding)}")
                
                # 如果维度不匹配，我们可以尝试重新初始化索引
                print("尝试使用新维度重新初始化索引...")
                old_documents = self.documents.copy()
                self.documents = []
                self.index = None
                self.initialize_index(len(query_embedding))
                
                # 重新添加文档
                if old_documents:
                    print(f"尝试重新嵌入{len(old_documents)}个文档...")
                    try:
                        self.add_documents(old_documents)
                    except Exception as e:
                        print(f"重新嵌入文档失败: {str(e)}")
                        return []
                else:
                    print("没有文档可以重新嵌入，返回空结果")
                    return []
            
            query_embedding = np.array([query_embedding], dtype=np.float32)

            # 动态调整搜索数量
            actual_top_k = min(top_k * 2 if rerank else top_k, len(self.documents))
            if actual_top_k == 0:
                print("没有足够的文档进行搜索，返回空结果")
                return []

            # 执行搜索
            distances, indices = self.index.search(query_embedding, actual_top_k)

            # 安全过滤无效索引
            valid_indices = [i for i in indices[0] if 0 <= i < len(self.documents)]
            if not valid_indices:
                print("搜索结果中没有有效索引，返回空结果")
                return []
                
            candidate_docs = [self.documents[i] for i in valid_indices]

            # 如果需要重排序且有重排序器
            if rerank and self.reranker and len(candidate_docs) > 1:
                try:
                    print("执行重排序...")
                    scores = self.reranker.rerank(query, candidate_docs)
                    # 将文档和分数配对，然后按分数排序
                    doc_scores = list(zip(candidate_docs, scores))
                    doc_scores.sort(key=lambda x: x[1], reverse=True)
                    # 提取排序后的文档
                    candidate_docs = [doc for doc, _ in doc_scores[:top_k]]
                except Exception as e:
                    print(f"重排序失败: {str(e)}")
                    # 如果重排序失败，使用原始顺序
                    candidate_docs = candidate_docs[:top_k]
            else:
                # 不需要重排序，直接截取前top_k个
                candidate_docs = candidate_docs[:top_k]

            print(f"查询成功，返回{len(candidate_docs)}个结果")
            return candidate_docs

        except Exception as e:
            print(f"查询失败: {str(e)}")
            return []  # 返回空列表，不影响程序运行

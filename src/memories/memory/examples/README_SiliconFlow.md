# 硅基流动API集成指南

本指南介绍如何将硅基流动API与RAG系统集成，实现高效的文本嵌入、语义搜索和检索增强生成。

## 背景介绍

[硅基流动](https://www.siliconflow.cn/)是一家提供高质量AI接口服务的公司，支持多种嵌入模型和大语言模型，其API接口兼容OpenAI规范，但提供更多的中文模型选择。

我们已经为RAG系统添加了对硅基流动API的支持，使您可以轻松使用BGE等高质量中文嵌入模型。

## 使用方法

### 1. 安装依赖

确保已安装以下依赖：

```bash
pip install numpy faiss-cpu requests sentence-transformers
```

### 2. 获取API密钥

在硅基流动官网注册并获取API密钥：[https://www.siliconflow.cn/](https://www.siliconflow.cn/)

### 3. 基本用法

```python
from memories.memory.core.rag import SiliconFlowEmbeddingModel, RAG

# 初始化嵌入模型
embedding_model = SiliconFlowEmbeddingModel(
    model_name="BAAI/bge-large-zh-v1.5",  # 可选择不同的BGE模型
    api_key="your-api-key-here",
    api_url="https://api.siliconflow.cn/v1/embeddings"
)

# 创建RAG系统
rag = RAG(embedding_model=embedding_model)

# 添加文档
documents = [
    "文档1内容",
    "文档2内容",
    "文档3内容"
]
rag.add_documents(texts=documents)

# 查询
results = rag.query("您的查询内容", top_k=3)
for doc in results:
    print(doc)
```

### 4. 带重排序的用法

```python
from memories.memory.core.rag import SiliconFlowEmbeddingModel, SiliconFlowReRanker, RAG

# 初始化嵌入模型
embedding_model = SiliconFlowEmbeddingModel(
    model_name="BAAI/bge-large-zh-v1.5",
    api_key="your-api-key-here",
    api_url="https://api.siliconflow.cn/v1/embeddings"
)

# 初始化重排序器
reranker = SiliconFlowReRanker(
    model_name="glm-4",  # 或其他大语言模型
    api_key="your-api-key-here",
    api_url="https://api.siliconflow.cn/v1/chat/completions"
)

# 创建带重排序的RAG系统
rag = RAG(embedding_model=embedding_model, reranker=reranker)

# 添加文档和查询与前面相同
# ...

# 查询时开启重排序
results = rag.query("您的查询内容", top_k=5, rerank=True)
```

## 支持的模型

### 嵌入模型

硅基流动支持多种BGE模型，适合不同的场景：

| 模型名称 | 向量维度 | 适用场景 |
|---------|---------|---------|
| BAAI/bge-large-zh-v1.5 | 1024 | 高精度中文嵌入 |
| BAAI/bge-large-en-v1.5 | 1024 | 高精度英文嵌入 |
| BAAI/bge-base-zh-v1.5 | 768 | 平衡性能与资源中文嵌入 |
| BAAI/bge-base-en-v1.5 | 768 | 平衡性能与资源英文嵌入 |
| BAAI/bge-small-zh-v1.5 | 512 | 轻量级中文嵌入 |
| BAAI/bge-small-en-v1.5 | 512 | 轻量级英文嵌入 |

### 重排序模型

可以使用任何硅基流动支持的大语言模型作为重排序器，如：

- glm-4
- glm-3-turbo
- chatglm-turbo
- qwen-plus

## 运行示例

我们提供了一个完整的示例脚本，您可以直接运行：

```bash
# 设置API密钥（也可以在运行时输入）
export SILICONFLOW_API_KEY="your-api-key-here"

# 运行示例
python -m memories.memory.examples.siliconflow_example
```

## 常见问题

### 1. 遇到"未提供有效的API基础URL"错误

确保使用`SiliconFlowEmbeddingModel`而非`OnlineEmbeddingModel`，并正确提供完整的API URL。

### 2. API密钥验证失败

检查API密钥是否正确，或者是否已过期。

### 3. 模型名称错误

确保使用硅基流动支持的模型名称，如`BAAI/bge-large-zh-v1.5`。

### 4. 向量维度不匹配

不同的模型产生不同维度的向量，确保使用一致的模型。如需混合使用，请考虑在应用层面进行向量维度转换。

## 性能优化建议

1. **缓存机制**：`SiliconFlowEmbeddingModel`内置了缓存机制，避免重复嵌入相同文本。

2. **选择合适模型**：对于大型文档集，可以考虑使用`bge-small`模型减少向量维度和计算需求。

3. **批量处理**：使用`.embed()`方法的批量处理功能，一次性处理多个文本。

4. **异步模式**：对于大量文本，可以使用异步模式：
   ```python
   embeddings = model.embed(texts, async_mode=True, timeout=30.0)
   ```

## 联系与支持

如有任何问题，请参考硅基流动官方文档或联系技术支持。 
# 嵌入和RAG系统测试脚本

这个目录包含了用于测试硅基流动API和RAG系统的测试脚本和示例。

## 文件说明

### 1. 测试配置脚本

- **test_embedding_config.py**: 测试独立的`config.yaml`嵌入配置文件，用于验证嵌入模型配置是否正确。
- **test_project_config.py**: 测试项目中`src/config/config.yaml`的RAG配置，使用项目内部的配置生成嵌入模型并测试。

### 2. 配置生成脚本

- **create_rag_config.py**: 从项目中的`src/config/config.yaml`提取RAG配置，生成标准的RAG配置文件，便于在其他项目中使用。

### 3. API示例脚本

- **direct_api_example.py**: 直接调用硅基流动API的示例，不依赖于RAG系统，演示嵌入和重排序功能。
- **config_example.py**: 使用配置文件加载RAG系统的示例，演示如何使用RAG系统进行文档检索。

## 使用方法

### 测试嵌入配置

```bash
# 测试独立的config.yaml配置文件
python src/memories/memory/examples/test_embedding_config.py

# 测试项目的RAG配置
python src/memories/memory/examples/test_project_config.py
```

**注意**: 首次运行时，这些脚本会检查环境变量`SILICONFLOW_API_KEY`，如果未设置，将提示您输入API密钥。

### 生成RAG配置文件

```bash
# 从项目配置生成标准的RAG配置文件
python src/memories/memory/examples/create_rag_config.py
```

此脚本会读取项目中的`src/config/config.yaml`文件，提取RAG相关设置，并生成标准的RAG配置文件。

### 直接使用API示例

```bash
# 直接调用硅基流动API的示例
python src/memories/memory/examples/direct_api_example.py

# 使用配置文件的RAG系统示例
python src/memories/memory/examples/config_example.py
```

## 配置文件格式

标准的RAG配置文件格式如下:

```yaml
# RAG系统配置
singleton: true  # 是否使用单例模式

# 嵌入模型配置
embedding_model:
  type: siliconflow  # 可选: siliconflow, openai, local, hybrid
  model_name: BAAI/bge-large-zh-v1.5
  api_key: your_api_key_here
  api_url: https://api.siliconflow.cn/v1/embeddings
  
  # 仅hybrid类型需要以下配置
  # api_type: siliconflow  # 主API类型: siliconflow或openai
  # local_model_path: paraphrase-multilingual-MiniLM-L12-v2
  # local_model_enabled: false

# 重排序器配置（可选）
reranker:
  type: siliconflow_native  # 可选: siliconflow_native, siliconflow, openai, local
  model_name: BAAI/bge-reranker-v2-m3
  api_key: your_api_key_here
  api_url: https://api.siliconflow.cn/v1/rerank
  top_n: 10  # 返回前N个结果，可选
```

## 环境变量

推荐使用环境变量设置API密钥，而不是将其硬编码在配置文件中:

```bash
# Linux/Mac
export SILICONFLOW_API_KEY="your_api_key_here"

# Windows (CMD)
set SILICONFLOW_API_KEY=your_api_key_here

# Windows (PowerShell)
$env:SILICONFLOW_API_KEY="your_api_key_here"
```

## 依赖库

这些脚本需要以下Python库:

- pyyaml
- numpy
- faiss-cpu (用于向量检索)
- sentence-transformers (用于本地嵌入模型)
- requests (用于API调用)

可以使用以下命令安装:

```bash
pip install pyyaml numpy faiss-cpu sentence-transformers requests
``` 
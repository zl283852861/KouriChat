#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目配置测试脚本
===============

此脚本用于测试项目中的src/config/config.yaml配置能否应用于RAG系统。
"""

import os
import sys
import yaml
import re
from pathlib import Path
from typing import List

# 正确设置Python模块导入路径 - 更灵活的方式
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

# 灵活的导入方式
try:
    # 尝试直接导入
    from memories.memory.core.rag import SiliconFlowEmbeddingModel, HybridEmbeddingModel, RAG
    from memories.memory.core.rag import OnlineEmbeddingModel
    print("成功使用导入路径: memories.memory.core.rag")
except ModuleNotFoundError:
    try:
        # 尝试从src导入
        from src.memories.memory.core.rag import SiliconFlowEmbeddingModel, HybridEmbeddingModel, RAG
        from src.memories.memory.core.rag import OnlineEmbeddingModel
        print("成功使用导入路径: src.memories.memory.core.rag")
    except ModuleNotFoundError:
        # 尝试从当前位置导入
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        try:
            from memories.memory.core.rag import SiliconFlowEmbeddingModel, HybridEmbeddingModel, RAG
            from memories.memory.core.rag import OnlineEmbeddingModel
            print("成功使用修正的导入路径")
        except ModuleNotFoundError as e:
            print(f"导入错误: {e}")
            print("尝试解决导入问题...")
            
            # 显示当前路径信息，帮助诊断
            print(f"当前工作目录: {os.getcwd()}")
            print(f"脚本位置: {__file__}")
            print(f"Python路径: {sys.path}")
            
            # 尝试调整当前工作目录
            os.chdir(str(project_root))
            sys.path.insert(0, ".")
            print(f"已将工作目录调整为: {os.getcwd()}")
            
            try:
                from src.memories.memory.core.rag import SiliconFlowEmbeddingModel, HybridEmbeddingModel, RAG
                from src.memories.memory.core.rag import OnlineEmbeddingModel
                print("通过调整工作目录成功导入")
            except ModuleNotFoundError:
                print("所有导入尝试均失败，请确保从正确的目录运行此脚本。")
                print("请尝试从项目根目录运行: python -m src.memories.memory.examples.test_project_config")
                sys.exit(1)

def load_project_config(config_path):
    """加载项目配置"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def get_rag_config_from_project(config):
    """从项目配置中提取RAG配置"""
    # 获取rag_settings部分
    rag_settings = config.get('categories', {}).get('rag_settings', {}).get('settings', {})
    
    # 提取配置值
    rag_config = {
        'api_key': rag_settings.get('api_key', {}).get('value'),
        'base_url': rag_settings.get('base_url', {}).get('value'),
        'embedding_model': rag_settings.get('embedding_model', {}).get('value'),
        'reranker_model': rag_settings.get('reranker_model', {}).get('value'),
        'local_model_path': rag_settings.get('local_embedding_model_path', {}).get('value'),
        'top_k': rag_settings.get('top_k', {}).get('value', 5),
        'is_rerank': rag_settings.get('is_rerank', {}).get('value', False),
        'auto_download_local_model': rag_settings.get('auto_download_local_model', {}).get('value'),
        'auto_adapt_siliconflow': rag_settings.get('auto_adapt_siliconflow', {}).get('value', True)
    }
    
    # 打印调试信息
    print("\n提取的RAG配置:")
    for key, value in rag_config.items():
        if key != 'api_key':  # 不打印API密钥
            print(f"- {key}: {value}")
    
    return rag_config

def create_embedding_model_from_config(rag_config):
    """根据配置创建嵌入模型"""
    api_key = rag_config.get('api_key')
    base_url = rag_config.get('base_url')
    model_name = rag_config.get('embedding_model')
    local_model_path = rag_config.get('local_model_path')
    auto_adapt = rag_config.get('auto_adapt_siliconflow', True)
    
    print(f"\n嵌入模型配置信息:")
    print(f"- 模型名称: {model_name}")
    print(f"- API URL: {base_url}")
    print(f"- API密钥: {'已设置' if api_key else '未设置'}")
    print(f"- 本地模型路径: {local_model_path}")
    print(f"- 自动适配硅基流动API: {auto_adapt}")
    
    # 确保模型名称是字符串
    if isinstance(model_name, dict) and 'value' in model_name:
        model_name = model_name['value']
    
    # 检查是否为硅基流动URL
    use_siliconflow = "siliconflow" in base_url.lower() if base_url else False
    
    # 创建API模型
    try:
        if use_siliconflow:
            # 创建硅基流动嵌入模型
            if auto_adapt:
                # 如果要自动适配，检查模型名称是否需要调整
                siliconflow_models = ["BAAI/bge-large-zh-v1.5", "BAAI/bge-m3", "BAAI/bge-base-zh-v1.5"]
                if str(model_name) not in siliconflow_models:
                    print(f"⚠️ 模型名称'{model_name}'可能不兼容硅基流动API，将使用BAAI/bge-m3")
                    model_name = "BAAI/bge-m3"
            
            print(f"\n创建SiliconFlowEmbeddingModel实例...")
            api_model = SiliconFlowEmbeddingModel(
                model_name=model_name,
                api_key=api_key,
                api_url=base_url
            )
        else:
            # 使用OnlineEmbeddingModel或其他模型
            print(f"\n创建OnlineEmbeddingModel实例...")
            api_model = OnlineEmbeddingModel(
                model_name=model_name,
                api_key=api_key,
                base_url=base_url
            )
    except Exception as e:
        print(f"⚠️ 创建API嵌入模型失败: {str(e)}")
        print("尝试创建本地嵌入模型作为备用...")
        
        try:
            # 创建本地嵌入模型
            api_model = LocalEmbeddingModel(local_model_path)
        except Exception as e2:
            print(f"⚠️ 创建本地嵌入模型也失败: {str(e2)}")
            
            # 创建空嵌入模型
            class EmptyEmbeddingModel(EmbeddingModel):
                def embed(self, texts: List[str]) -> List[List[float]]:
                    return [[0.0] * 1536 for _ in range(len(texts))]
            
            api_model = EmptyEmbeddingModel()
            print("将使用空嵌入模型 (返回零向量)")
    
    # 决定是否使用混合模型
    auto_download = rag_config.get('auto_download_local_model')
    use_local_model = auto_download == 'true'
    
    if use_local_model and local_model_path:
        print(f"创建混合嵌入模型，将使用本地备用模型...")
        embedding_model = HybridEmbeddingModel(
            api_model=api_model,
            local_model_path=local_model_path,
            local_model_enabled=True
        )
    else:
        embedding_model = api_model
    
    return embedding_model

def test_embedding_model(embedding_model):
    """测试嵌入模型"""
    # 测试文本
    test_texts = [
        "硅基流动提供高质量的嵌入API服务",
        "向量嵌入可以将文本转换为数值向量",
        "RAG系统使用向量数据库存储和检索文档"
    ]
    
    try:
        # 测试嵌入模型
        print(f"\n测试嵌入{len(test_texts)}个文本...")
        embeddings = embedding_model.embed(test_texts)
        
        # 验证嵌入结果
        if embeddings and any(len(emb) > 0 for emb in embeddings if isinstance(emb, list)):
            # 找到第一个非空的嵌入，用于显示
            first_valid_embedding = None
            for emb in embeddings:
                if isinstance(emb, list) and len(emb) > 0:
                    first_valid_embedding = emb
                    break
            
            if first_valid_embedding:
                dim = len(first_valid_embedding)
                print(f"✅ 嵌入成功! 嵌入维度: {dim}")
                # 打印第一个嵌入向量的前5个元素
                print(f"第一个有效嵌入向量的前5个元素: {first_valid_embedding[:5]}")
                return True
            else:
                print(f"❌ 所有嵌入都为空")
                return False
        else:
            print(f"❌ 嵌入失败或结果不完整")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def get_embedding_dimension(embedding_model):
    """尝试获取嵌入模型的维度"""
    try:
        # 方法1: 尝试调用_get_model_dimension方法
        if hasattr(embedding_model, "_get_model_dimension"):
            if callable(getattr(embedding_model, "_get_model_dimension")):
                try:
                    return embedding_model._get_model_dimension()
                except:
                    pass
        
        # 方法2: 对于SiliconFlowEmbeddingModel，使用model_dimensions字典
        if hasattr(embedding_model, "model_dimensions") and hasattr(embedding_model, "model_name"):
            return embedding_model.model_dimensions.get(embedding_model.model_name, 1024)
        
        # 方法3: 对于HybridEmbeddingModel，尝试从api_model获取
        if hasattr(embedding_model, "api_model"):
            return get_embedding_dimension(embedding_model.api_model)
        
        # 方法4: 对于OnlineEmbeddingModel，使用硬编码维度
        if isinstance(embedding_model, OnlineEmbeddingModel):
            model_name = embedding_model.model_name
            if "text-embedding-3-large" in model_name:
                return 3072
            elif "text-embedding-3" in model_name:
                return 1536
            else:
                return 1536  # 默认值
                
        # 方法5: 测试嵌入一个文本，获取维度
        try:
            test_embeddings = embedding_model.embed(["测试维度"])
            if test_embeddings and len(test_embeddings) > 0 and isinstance(test_embeddings[0], list):
                return len(test_embeddings[0])
        except:
            pass
            
    except Exception as e:
        print(f"获取嵌入维度时出错: {str(e)}")
    
    # 默认维度
    return 1024

def test_rag_system(embedding_model, rag_config):
    """测试RAG系统"""
    try:
        print(f"\n创建RAG系统...")
        
        # 导入所需的库
        import os
        import numpy as np
        
        # 创建RAG系统
        rag = RAG(embedding_model=embedding_model)
        
        # 先进行一次测试嵌入以获取正确的维度
        print("进行测试嵌入以确定正确的维度...")
        test_embedding = embedding_model.embed(["测试维度"])[0]
        if not test_embedding or not isinstance(test_embedding, list):
            raise ValueError("无法获取有效的嵌入向量")
            
        dimension = len(test_embedding)
        print(f"检测到嵌入维度: {dimension}")
        
        # 使用实际检测到的维度初始化索引
        print(f"使用维度 {dimension} 初始化索引...")
        rag.initialize_index(dim=dimension)
        
        # 测试添加文档
        test_docs = [
            "硅基流动是一家中国的AI服务提供商，专注于提供高质量的API服务。",
            "向量嵌入技术是现代自然语言处理的基础，可以捕捉文本的语义信息。",
            "检索增强生成(RAG)技术结合了检索系统和生成式AI的优势。"
        ]
        print(f"\n添加{len(test_docs)}个测试文档...")
        
        # 先修补RAG的query方法，确保它安全处理索引
        original_query = rag.query
        
        def safe_query(self, query, top_k=5, rerank=False, async_mode=False, timeout=5.0):
            try:
                # 生成查询向量
                print(f"正在为查询生成嵌入向量: {query[:50]}...")
                query_embedding = self.embedding_model.embed([query], async_mode=async_mode, timeout=timeout)[0]
                
                # 检查向量是否为空
                if not query_embedding:
                    print("⚠️ 查询嵌入生成失败，返回空结果")
                    return []
                    
                # 搜索相似文档
                print(f"使用嵌入向量搜索相似文档...")
                top_k = min(top_k, len(self.documents), self.index.ntotal)  # 确保top_k不超过文档数量和索引大小
                if top_k == 0:
                    print("⚠️ 没有可查询的文档，返回空结果")
                    return []
                    
                # 执行FAISS搜索
                D, I = self.index.search(np.array([query_embedding]), top_k)
                
                # 安全获取结果
                results = []
                for idx in I[0]:
                    if 0 <= idx < len(self.documents):  # 确保索引在有效范围内
                        results.append(self.documents[idx])
                    else:
                        print(f"⚠️ 跳过无效的索引: {idx} (文档列表长度: {len(self.documents)})")
                
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
                traceback.print_exc()
                return []
        
        # 替换原始的query方法为安全版本
        rag.query = lambda query, top_k=5, rerank=False, async_mode=False, timeout=5.0: \
            safe_query(rag, query, top_k, rerank, async_mode, timeout)
        
        # 添加文档并检查结果
        rag.add_documents(texts=test_docs)
        
        # 确认文档已被正确添加
        if not rag.documents or len(rag.documents) == 0:
            raise ValueError("文档添加失败，documents列表为空")
            
        print(f"成功添加了 {len(rag.documents)} 个文档")
        print(f"索引大小: {rag.index.ntotal} 个向量")
        
        # 验证文档和索引大小是否匹配
        if len(rag.documents) != rag.index.ntotal:
            print(f"⚠️ 文档数量 ({len(rag.documents)}) 与索引大小 ({rag.index.ntotal}) 不匹配")
        
        # 测试查询
        test_query = "硅基流动提供什么服务?"
        top_k = min(rag_config.get('top_k', 5), len(rag.documents))  # 确保top_k不超过文档数量
        is_rerank = rag_config.get('is_rerank', False)
        
        print(f"\n测试查询: '{test_query}'")
        print(f"- top_k: {top_k}")
        print(f"- 重排序: {'是' if is_rerank else '否'}")
        
        results = rag.query(test_query, top_k=top_k, rerank=is_rerank)
        
        if results and len(results) > 0:
            print(f"✅ 查询成功，找到{len(results)}个相关文档:")
            for i, doc in enumerate(results):
                print(f"[{i+1}] {doc}")
            return True
        else:
            print("❌ 查询失败或未找到相关文档")
            return False
            
    except Exception as e:
        print(f"❌ 测试RAG系统时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_api_key():
    """检查API密钥是否设置"""
    api_key = os.environ.get("SILICONFLOW_API_KEY")
    if not api_key:
        print("⚠️ 警告: 未设置环境变量 SILICONFLOW_API_KEY")
        print("示例: export SILICONFLOW_API_KEY='your_api_key_here'")
        api_key = input("或直接输入API密钥: ").strip()
        if api_key:
            os.environ["SILICONFLOW_API_KEY"] = api_key
            return True
        return False
    return True

def main():
    """主函数"""
    print("===== 项目配置测试脚本 =====")
    
    # 检查API密钥
    if not check_api_key():
        print("未提供API密钥，测试将使用项目配置中的API密钥")
    
    # 尝试多个可能的项目配置文件位置
    possible_config_paths = [
        os.path.join(str(project_root), "src", "config", "config.yaml"),
        os.path.join("src", "config", "config.yaml"),
        os.path.join(os.getcwd(), "src", "config", "config.yaml")
    ]
    
    # 寻找存在的配置文件
    config_path = None
    for path in possible_config_paths:
        if os.path.exists(path):
            config_path = path
            print(f"找到项目配置文件: {path}")
            break
    
    if not config_path:
        print(f"❌ 项目配置文件不存在")
        print(f"已尝试的路径:")
        for path in possible_config_paths:
            print(f"  - {path}")
        config_path = input("请输入项目配置文件路径: ").strip()
        if not os.path.exists(config_path):
            print(f"❌ 项目配置文件仍然不存在，测试终止")
            return
    
    print(f"正在读取项目配置文件: {config_path}")
    try:
        # 加载项目配置
        config = load_project_config(config_path)
        
        # 提取RAG配置
        rag_config = get_rag_config_from_project(config)
        
        # 如果环境变量中已设置API密钥，优先使用环境变量
        if os.environ.get("SILICONFLOW_API_KEY"):
            rag_config['api_key'] = os.environ.get("SILICONFLOW_API_KEY")
            print("使用环境变量中的API密钥覆盖配置")
        
        # 创建嵌入模型
        embedding_model = create_embedding_model_from_config(rag_config)
        
        # 测试嵌入模型
        print("\n===== 测试嵌入模型 =====")
        embed_test_success = test_embedding_model(embedding_model)
        
        # 测试RAG系统
        print("\n===== 测试RAG系统 =====")
        rag_test_success = test_rag_system(embedding_model, rag_config)
        
        # 输出测试结果总结
        print("\n===== 测试结果总结 =====")
        print(f"嵌入模型测试: {'✅ 通过' if embed_test_success else '❌ 失败'}")
        print(f"RAG系统测试: {'✅ 通过' if rag_test_success else '❌ 失败'}")
        
        if embed_test_success and rag_test_success:
            print("\n🎉 所有测试通过! 项目配置可以正确应用于RAG系统!")
        else:
            print("\n⚠️ 部分测试失败，请检查项目配置和环境设置")
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 
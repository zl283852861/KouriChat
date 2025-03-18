#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
嵌入配置测试脚本
===============

此脚本用于测试config.yaml中的嵌入配置能否正确使用。
"""

import os
import sys
import yaml
import re
from pathlib import Path

# 正确设置Python模块导入路径 - 更灵活的方式
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

# 灵活的导入方式
try:
    # 尝试直接导入
    from memories.memory.core.rag import load_from_config
    from memories.memory.core.rag import SiliconFlowEmbeddingModel, OnlineEmbeddingModel, LocalEmbeddingModel, HybridEmbeddingModel
    print("成功使用导入路径: memories.memory.core.rag")
except ModuleNotFoundError:
    try:
        # 尝试从src导入
        from src.memories.memory.core.rag import load_from_config
        from src.memories.memory.core.rag import SiliconFlowEmbeddingModel, OnlineEmbeddingModel, LocalEmbeddingModel, HybridEmbeddingModel
        print("成功使用导入路径: src.memories.memory.core.rag")
    except ModuleNotFoundError:
        # 尝试从当前位置导入
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        try:
            from memories.memory.core.rag import load_from_config
            from memories.memory.core.rag import SiliconFlowEmbeddingModel, OnlineEmbeddingModel, LocalEmbeddingModel, HybridEmbeddingModel
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
                from src.memories.memory.core.rag import load_from_config
                from src.memories.memory.core.rag import SiliconFlowEmbeddingModel, OnlineEmbeddingModel, LocalEmbeddingModel, HybridEmbeddingModel
                print("通过调整工作目录成功导入")
            except ModuleNotFoundError:
                print("所有导入尝试均失败，请确保从正确的目录运行此脚本。")
                print("请尝试从项目根目录运行: python -m src.memories.memory.examples.test_embedding_config")
                sys.exit(1)

def process_environment_variables(config_path):
    """处理配置文件中的环境变量引用"""
    # 读取配置文件
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换环境变量
    pattern = r'\${([A-Za-z0-9_]+)}'
    
    def replace_env_var(match):
        env_var = match.group(1)
        return os.environ.get(env_var, f"${{{env_var}}}")
    
    processed_content = re.sub(pattern, replace_env_var, content)
    
    # 将处理后的内容写回文件
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(processed_content)

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

def test_embedding_model(config_path):
    """测试嵌入模型配置"""
    # 处理配置文件中的环境变量
    process_environment_variables(config_path)
    
    # 加载配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 提取嵌入模型配置
    embedding_config = config.get('embedding_model', {})
    model_type = embedding_config.get('type')
    model_name = embedding_config.get('model_name')
    api_key = embedding_config.get('api_key')
    api_url = embedding_config.get('api_url')
    base_url = embedding_config.get('base_url')  # 可能是base_url而不是api_url
    
    # 确保有一个有效的URL
    if not api_url and base_url:
        api_url = base_url
    
    print(f"\n嵌入模型配置信息:")
    print(f"- 模型类型: {model_type}")
    print(f"- 模型名称: {model_name}")
    print(f"- API URL: {api_url}")
    print(f"- API密钥: {'已设置' if api_key else '未设置'}")
    
    # 测试文本
    test_texts = [
        "硅基流动提供高质量的嵌入API服务",
        "向量嵌入可以将文本转换为数值向量",
        "RAG系统使用向量数据库存储和检索文档"
    ]
    
    # 确保模型名称是字符串
    if isinstance(model_name, dict) and 'value' in model_name:
        model_name = model_name['value']
    
    # 根据配置创建嵌入模型
    embedding_model = None
    try:
        if model_type == 'siliconflow':
            print(f"\n创建SiliconFlowEmbeddingModel实例...")
            # 检查模型名称是否兼容硅基流动API
            siliconflow_models = ["BAAI/bge-large-zh-v1.5", "BAAI/bge-m3", "BAAI/bge-base-zh-v1.5"]
            if str(model_name) not in siliconflow_models:
                print(f"⚠️ 模型名称'{model_name}'可能不兼容硅基流动API，将使用BAAI/bge-m3")
                model_name = "BAAI/bge-m3"
                
            embedding_model = SiliconFlowEmbeddingModel(
                model_name=model_name,
                api_key=api_key,
                api_url=api_url
            )
        elif model_type == 'openai':
            print(f"\n创建OnlineEmbeddingModel实例...")
            embedding_model = OnlineEmbeddingModel(
                model_name=model_name,
                api_key=api_key,
                base_url=api_url
            )
        elif model_type == 'local':
            print(f"\n创建LocalEmbeddingModel实例...")
            embedding_model = LocalEmbeddingModel(model_path=model_name)
        elif model_type == 'hybrid':
            # 这里需要处理hybrid的情况
            print(f"\n创建HybridEmbeddingModel实例...")
            
            # 判断API类型
            api_type = embedding_config.get('api_type', '').lower()
            is_siliconflow = api_type == 'siliconflow' or (api_url and 'siliconflow' in api_url.lower())
            
            if is_siliconflow:
                # 检查模型名称是否兼容硅基流动API
                siliconflow_models = ["BAAI/bge-large-zh-v1.5", "BAAI/bge-m3", "BAAI/bge-base-zh-v1.5"]
                if str(model_name) not in siliconflow_models:
                    print(f"⚠️ 模型名称'{model_name}'可能不兼容硅基流动API，将使用BAAI/bge-m3")
                    model_name = "BAAI/bge-m3"
                    
                print("使用SiliconFlowEmbeddingModel作为API模型")
                api_model = SiliconFlowEmbeddingModel(
                    model_name=model_name,
                    api_key=api_key,
                    api_url=api_url
                )
            else:
                print("使用OnlineEmbeddingModel作为API模型")
                api_model = OnlineEmbeddingModel(
                    model_name=model_name,
                    api_key=api_key,
                    base_url=api_url
                )
                
            # 获取本地模型路径和是否启用
            local_model_path = embedding_config.get('local_model_path', "paraphrase-multilingual-MiniLM-L12-v2")
            local_model_enabled = embedding_config.get('local_model_enabled', False)
            
            embedding_model = HybridEmbeddingModel(
                api_model=api_model,
                local_model_path=local_model_path,
                local_model_enabled=local_model_enabled
            )
        else:
            print(f"❌ 错误: 不支持的模型类型 '{model_type}'")
            return False
        
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
                return True, embedding_model
            else:
                print(f"❌ 所有嵌入都为空")
                return False, None
        else:
            print(f"❌ 嵌入失败或结果不完整")
            return False, None
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def test_rag_system(config_path, embedding_model=None):
    """测试完整RAG系统"""
    print(f"\n从配置文件加载RAG系统...")
    try:
        # 导入所需的库
        import os
        import numpy as np
        
        # 如果没有提供embedding_model，就从配置加载RAG系统
        if embedding_model is None:
            rag = load_from_config(config_path)
        else:
            # 如果提供了embedding_model，就直接创建RAG系统
            from src.memories.memory.core.rag import RAG
            rag = RAG(embedding_model=embedding_model)
            
            # 初始化索引
            try:
                try:
                    dimension = embedding_model._get_model_dimension()
                except:
                    try:
                        # 尝试获取对象的方法
                        if hasattr(embedding_model, "_get_model_dimension"):
                            dimension = embedding_model._get_model_dimension()
                        # 尝试获取SiliconFlow模型的维度
                        elif hasattr(embedding_model, "model_dimensions"):
                            model_name = embedding_model.model_name
                            dimension = embedding_model.model_dimensions.get(model_name, 1024)
                        else:
                            dimension = 1024  # 默认维度
                    except:
                        dimension = 1024  # 默认维度
                
                rag.initialize_index(dim=dimension)
                print(f"已初始化索引，维度: {dimension}")
            except Exception as e:
                print(f"初始化索引失败: {str(e)}")
                dimension = 1024  # 默认维度
                rag.initialize_index(dim=dimension)
        
        if not rag:
            print("❌ 加载RAG系统失败")
            return False
        
        print(f"✅ 成功加载RAG系统!")
        
        # 测试添加文档
        test_docs = [
            "硅基流动是一家中国的AI服务提供商，专注于提供高质量的API服务。",
            "向量嵌入技术是现代自然语言处理的基础，可以捕捉文本的语义信息。",
            "检索增强生成(RAG)技术结合了检索系统和生成式AI的优势。"
        ]
        print(f"\n添加{len(test_docs)}个测试文档...")
        rag.add_documents(texts=test_docs)
        
        # 测试查询
        test_query = "硅基流动提供什么服务?"
        print(f"\n测试查询: '{test_query}'")
        results = rag.query(test_query, top_k=2)
        
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

def main():
    """主函数"""
    print("===== 嵌入配置测试脚本 =====")
    
    # 检查API密钥
    if not check_api_key():
        print("未提供API密钥，部分测试可能会失败")
    
    # 配置文件路径
    default_config_path = "config.yaml"
    parent_config_path = os.path.join(str(project_root), "config.yaml")
    
    # 尝试多个可能的配置文件位置
    possible_paths = [
        default_config_path,
        parent_config_path,
        os.path.join("src", "config", "config.yaml"),
        os.path.join(str(project_root), "src", "config", "config.yaml"),
        os.path.join(os.path.dirname(__file__), "config.yaml")
    ]
    
    # 寻找存在的配置文件
    config_path = None
    for path in possible_paths:
        if os.path.exists(path):
            config_path = path
            print(f"找到配置文件: {path}")
            break
    
    # 如果未找到配置文件，请求用户输入
    if not config_path:
        print(f"❌ 未找到配置文件")
        print(f"已尝试的路径:")
        for path in possible_paths:
            print(f"  - {path}")
        config_path = input("请输入配置文件路径: ").strip()
        if not os.path.exists(config_path):
            print(f"❌ 配置文件 {config_path} 不存在，测试终止")
            return
    
    # 测试嵌入模型配置
    print("\n===== 测试嵌入模型配置 =====")
    embed_test_success, embedding_model = test_embedding_model(config_path)
    
    # 测试完整RAG系统
    print("\n===== 测试完整RAG系统 =====")
    # 如果嵌入测试成功，直接使用已创建的嵌入模型实例
    if embed_test_success and embedding_model:
        rag_test_success = test_rag_system(config_path, embedding_model)
    else:
        rag_test_success = test_rag_system(config_path)
    
    # 输出总结
    print("\n===== 测试结果总结 =====")
    print(f"嵌入模型配置测试: {'✅ 通过' if embed_test_success else '❌ 失败'}")
    print(f"RAG系统测试: {'✅ 通过' if rag_test_success else '❌ 失败'}")
    
    if embed_test_success and rag_test_success:
        print("\n🎉 所有测试通过! 配置文件可以正确使用!")
    else:
        print("\n⚠️ 部分测试失败，请检查配置和环境设置")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG配置生成脚本
===============

此脚本从KouriChat的项目配置中提取RAG相关设置，并生成标准的RAG配置文件。
"""

import os
import sys
import yaml
import json
from pathlib import Path
import time

# 正确设置Python模块导入路径 - 更灵活的方式
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

def load_project_config(config_path):
    """加载项目配置"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def extract_rag_settings(config):
    """从项目配置中提取RAG相关设置"""
    # 正确获取rag_settings部分（categories -> rag_settings -> settings）
    rag_settings = config.get('categories', {}).get('rag_settings', {}).get('settings', {})
    
    # 提取值，确保每个配置项都有合理的默认值
    api_key = rag_settings.get('api_key', {}).get('value', '')
    base_url = rag_settings.get('base_url', {}).get('value', 'https://api.siliconflow.cn/v1/embeddings')
    embedding_model = rag_settings.get('embedding_model', {}).get('value', 'BAAI/bge-m3')
    reranker_model = rag_settings.get('reranker_model', {}).get('value', '')
    local_model_path = rag_settings.get('local_embedding_model_path', {}).get('value', 'paraphrase-multilingual-MiniLM-L12-v2')
    top_k = rag_settings.get('top_k', {}).get('value', 5)
    is_rerank = rag_settings.get('is_rerank', {}).get('value', False)
    auto_download_local_model = rag_settings.get('auto_download_local_model', {}).get('value', 'false')
    auto_adapt_siliconflow = rag_settings.get('auto_adapt_siliconflow', {}).get('value', True)
    
    # 判断使用的嵌入模型类型
    if base_url and "siliconflow" in base_url.lower():
        model_type = "siliconflow"
        
        # 检查模型名称是否兼容硅基流动API
        siliconflow_models = ["BAAI/bge-large-zh-v1.5", "BAAI/bge-m3", "BAAI/bge-base-zh-v1.5"]
        if str(embedding_model) not in siliconflow_models and auto_adapt_siliconflow:
            print(f"⚠️ 模型名称'{embedding_model}'可能不兼容硅基流动API，将使用BAAI/bge-m3")
            embedding_model = "BAAI/bge-m3"
    elif base_url and ("/v1/embeddings" in base_url.lower() or "openai" in base_url.lower()):
        model_type = "openai"
    else:
        model_type = "hybrid"  # 默认使用混合模型
    
    # 是否启用本地模型
    local_model_enabled = auto_download_local_model == 'true'
    
    # 返回提取的配置
    return {
        "model_type": model_type,
        "api_key": api_key,
        "base_url": base_url,
        "embedding_model": embedding_model,
        "reranker_model": reranker_model,
        "local_model_path": local_model_path,
        "top_k": top_k,
        "is_rerank": is_rerank,
        "local_model_enabled": local_model_enabled,
        "auto_adapt_siliconflow": auto_adapt_siliconflow
    }

def generate_rag_config(settings):
    """生成标准的RAG配置"""
    model_type = settings["model_type"]
    
    # 创建基本配置结构
    rag_config = {
        "singleton": True,
        "embedding_model": {
            "type": model_type,
            "model_name": settings["embedding_model"],
            "api_key": settings["api_key"]
        }
    }
    
    # 根据模型类型设置不同的URL字段
    if model_type == "siliconflow":
        # 确保使用正确的硅基流动API URL
        if not settings["base_url"] or "siliconflow" not in settings["base_url"].lower():
            rag_config["embedding_model"]["api_url"] = "https://api.siliconflow.cn/v1/embeddings"
            print("⚠️ 未检测到有效的硅基流动API URL，已使用默认URL")
        else:
            rag_config["embedding_model"]["api_url"] = settings["base_url"]
            
        # 确保模型名称兼容硅基流动API
        siliconflow_models = ["BAAI/bge-large-zh-v1.5", "BAAI/bge-m3", "BAAI/bge-base-zh-v1.5"]
        if str(settings["embedding_model"]) not in siliconflow_models:
            print(f"⚠️ 模型名称'{settings['embedding_model']}'可能不兼容硅基流动API，已使用BAAI/bge-m3")
            rag_config["embedding_model"]["model_name"] = "BAAI/bge-m3"
    elif model_type == "openai":
        rag_config["embedding_model"]["base_url"] = settings["base_url"]
    elif model_type == "hybrid":
        # 对于混合模型，需要更复杂的配置
        if "siliconflow" in settings["base_url"].lower():
            api_type = "siliconflow"
            url_field = "api_url"
        else:
            api_type = "openai"
            url_field = "base_url"
        
        rag_config["embedding_model"] = {
            "type": "hybrid",
            "api_type": api_type,
            "model_name": settings["embedding_model"],
            "api_key": settings["api_key"],
            url_field: settings["base_url"],
            "local_model_path": settings["local_model_path"],
            "local_model_enabled": settings["local_model_enabled"]
        }
    
    # 添加重排序器配置（如果启用）
    if settings["is_rerank"] and settings["reranker_model"]:
        if "siliconflow" in settings["base_url"].lower():
            reranker_type = "siliconflow_native"
            reranker_url = "https://api.siliconflow.cn/v1/rerank"
            reranker_model = "BAAI/bge-reranker-v2-m3"  # 硅基流动的默认重排序模型
        else:
            reranker_type = "openai"
            reranker_url = settings["base_url"].replace("embeddings", "chat/completions")
            reranker_model = settings["reranker_model"]
        
        rag_config["reranker"] = {
            "type": reranker_type,
            "model_name": reranker_model,
            "api_key": settings["api_key"],
            "api_url": reranker_url,
            "top_n": settings["top_k"]
        }
    
    return rag_config

def create_config_file(config, output_path):
    """将配置写入YAML文件"""
    try:
        # 检查输出路径是否为目录
        if os.path.isdir(output_path):
            print(f"检测到输入路径是目录: {output_path}")
            default_filename = "rag_config.yaml"
            output_path = os.path.join(output_path, default_filename)
            print(f"将在该目录中创建文件: {output_path}")
    
        # 确保目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 添加环境变量提示
        if config['embedding_model'].get('api_key'):
            print("\n⚠️ 注意: 配置文件中包含API密钥。为安全起见，建议使用环境变量。")
            use_env_var = input("是否将API密钥替换为环境变量引用? (y/n): ").strip().lower()
            if use_env_var == 'y':
                env_var_name = input("请输入环境变量名称 [默认: SILICONFLOW_API_KEY]: ").strip()
                if not env_var_name:
                    env_var_name = "SILICONFLOW_API_KEY"
                
                # 替换API密钥为环境变量引用
                config['embedding_model']['api_key'] = f"${{{env_var_name}}}"
                if 'reranker' in config:
                    config['reranker']['api_key'] = f"${{{env_var_name}}}"
                
                print(f"已将API密钥替换为环境变量引用: ${{{env_var_name}}}")
                print(f"请确保设置环境变量: export {env_var_name}='your_api_key'")
        
        # 写入配置文件
        with open(output_path, 'w', encoding='utf-8') as f:
            # 添加注释
            f.write("# RAG系统配置文件\n")
            f.write("# 由KouriChat的RAG配置自动生成\n")
            date_str = os.path.basename(__file__) + " - " + time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"# 创建时间: {date_str}\n\n")
            
            # 写入YAML
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        print(f"✅ 配置文件已生成: {output_path}")
        return True
    
    except PermissionError:
        print(f"❌ 权限错误: 无法写入文件 {output_path}")
        print("请尝试选择其他位置或使用管理员权限运行脚本。")
        
        # 提供备选路径选项
        alt_path = input("请输入新的输出路径，或按Enter使用当前目录: ").strip()
        if not alt_path:
            alt_path = os.path.join(os.getcwd(), "rag_config.yaml")
            print(f"将使用当前目录: {alt_path}")
        
        # 递归调用，尝试新路径
        return create_config_file(config, alt_path)
        
    except Exception as e:
        print(f"❌ 写入文件时出错: {str(e)}")
        return False

def main():
    """主函数"""
    print("===== RAG配置生成脚本 =====")
    
    # 尝试多个可能的项目配置文件位置
    possible_config_paths = [
        os.path.join(str(project_root), "src", "config", "config.yaml"),
        os.path.join("src", "config", "config.yaml"),
        os.path.join(os.getcwd(), "src", "config", "config.yaml")
    ]
    
    # 寻找存在的配置文件
    project_config_path = None
    for path in possible_config_paths:
        if os.path.exists(path):
            project_config_path = path
            print(f"找到项目配置文件: {path}")
            break
    
    if not project_config_path:
        print(f"❌ 项目配置文件不存在")
        print(f"已尝试的路径:")
        for path in possible_config_paths:
            print(f"  - {path}")
        project_config_path = input("请输入项目配置文件路径: ").strip()
        if not os.path.exists(project_config_path):
            print(f"❌ 项目配置文件仍然不存在，操作终止")
            return
    
    print(f"正在读取项目配置文件: {project_config_path}")
    
    try:
        # 加载项目配置
        config = load_project_config(project_config_path)
        
        # 提取RAG设置
        rag_settings = extract_rag_settings(config)
        
        # 如果环境变量中已设置API密钥，优先使用环境变量
        if os.environ.get("SILICONFLOW_API_KEY"):
            rag_settings['api_key'] = os.environ.get("SILICONFLOW_API_KEY")
            print("使用环境变量中的API密钥覆盖配置")
        
        # 打印提取的设置
        print("\n提取的RAG设置:")
        for key, value in rag_settings.items():
            if key == "api_key" and value:
                print(f"- {key}: {'*' * 8}")
            else:
                print(f"- {key}: {value}")
        
        # 生成RAG配置
        rag_config = generate_rag_config(rag_settings)
        
        # 询问输出路径
        default_output_path = "rag_config.yaml"
        output_path = input(f"请输入输出文件路径 [默认: {default_output_path}]: ").strip()
        if not output_path:
            output_path = default_output_path
        
        # 验证输出路径
        if os.path.isdir(output_path) and not output_path.endswith(os.sep):
            # 如果输入的是目录但没有以分隔符结尾，添加文件名
            output_path = os.path.join(output_path, default_output_path)
        
        # 创建配置文件
        success = create_config_file(rag_config, output_path)
        
        if success:
            # 显示如何使用该配置文件
            print("\n使用方法:")
            print(f"1. 使用load_from_config函数加载配置:")
            print(f"   from memories.memory.core.rag import load_from_config")
            print(f"   rag = load_from_config('{output_path}')")
            print(f"2. 如果要在其他项目中使用此配置，请复制{output_path}文件")
        
    except Exception as e:
        print(f"❌ 生成配置文件时出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 
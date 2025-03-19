#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG配置验证脚本
===============

此脚本用于验证RAG配置的加载和处理功能。
"""

import os
import sys
import traceback
import time
from pathlib import Path

# 记录日志到文件
log_file = os.path.join(os.path.dirname(__file__), "validate_config.log")
with open(log_file, "w", encoding="utf-8") as f:
    f.write(f"验证开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

def log(message):
    """将消息记录到日志文件"""
    print(message)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{message}\n")

# 获取当前文件的绝对路径
current_file = os.path.abspath(__file__)
# 获取项目根目录（注意：这里去掉一层src）
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
# 添加项目根目录到Python路径
sys.path.insert(0, project_root)

log(f"项目根目录: {project_root}")

def validate_config():
    """验证配置加载功能"""
    try:
        log("正在导入RAG模块...")
        # 尝试直接导入
        from src.memories.memory.core.rag import load_from_config
        log("成功导入RAG模块")
    except ModuleNotFoundError as e:
        log(f"直接导入失败: {e}")
        # 如果直接导入失败，尝试相对导入
        sys.path.append(os.getcwd())
        try:
            from memories.memory.core.rag import load_from_config
            log("成功通过相对路径导入RAG模块")
        except ModuleNotFoundError as e:
            log(f"相对导入失败: {e}")
            log(f"尝试从项目根目录导入: {project_root}")
            from src.memories.memory.core.rag import load_from_config
            log("成功通过项目根目录导入RAG模块")
    
    log("===== RAG配置验证脚本 =====")
    
    # 直接使用项目配置文件
    config_path = os.path.join(project_root, "src", "config", "config.yaml")
    log(f"配置路径: {config_path}")
    log(f"文件存在: {os.path.exists(config_path)}")
    
    if not os.path.exists(config_path):
        # 尝试查找其他可能的配置文件
        possible_paths = [
            os.path.join(project_root, "config.yaml"),
            os.path.join(project_root, "config.yml"), 
            os.path.join(project_root, "rag_config.yaml"),
            os.path.join(project_root, "rag_config.yml"),
            os.path.expanduser("~/.config/rag/config.yaml"),
            os.path.join(os.path.dirname(__file__), "config.yaml")
        ]
        
        log("尝试其他可能的配置文件路径:")
        for path in possible_paths:
            log(f"- {path} (存在: {os.path.exists(path)})")
            if os.path.exists(path):
                config_path = path
                log(f"发现配置文件: {path}")
                break
        
        if not os.path.exists(config_path):
            log("未找到配置文件，请手动指定")
            config_path = input("请输入配置文件路径: ")
            if not os.path.exists(config_path):
                log(f"错误: 文件不存在: {config_path}")
                return
    
    # 加载配置
    log(f"\n尝试加载配置文件: {config_path}")
    try:
        rag = load_from_config(config_path)
        
        if rag:
            log("\n✅ 配置加载成功!")
            log("\n配置信息:")
            
            # 显示嵌入模型信息
            if hasattr(rag, 'embedding_model'):
                embedding_model = rag.embedding_model
                log("\n嵌入模型信息:")
                
                if hasattr(embedding_model, 'model_name'):
                    log(f"模型名称: {embedding_model.model_name}")
                    
                if hasattr(embedding_model, 'api_type'):
                    log(f"API类型: {embedding_model.api_type}")
                    
                if hasattr(embedding_model, 'api_model') and embedding_model.api_model:
                    log(f"API模型: {embedding_model.api_model.__class__.__name__}")
                    
                if hasattr(embedding_model, 'local_model_enabled'):
                    log(f"本地模型启用: {embedding_model.local_model_enabled}")
                    
                if hasattr(embedding_model, 'local_model_path'):
                    log(f"本地模型路径: {embedding_model.local_model_path}")
            
            # 显示重排模型信息
            if hasattr(rag, 'reranker') and rag.reranker:
                log("\n重排模型信息:")
                log(f"重排模型类型: {rag.reranker.__class__.__name__}")
                
                if hasattr(rag.reranker, 'model_name'):
                    log(f"重排模型名称: {rag.reranker.model_name}")
        else:
            log("\n❌ 配置加载失败!")
    except Exception as e:
        log(f"\n❌ 加载配置时出现异常: {str(e)}")
        with open(log_file, "a", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        traceback.print_exc()
    
    log(f"\n日志文件位置: {log_file}")

if __name__ == "__main__":
    validate_config() 
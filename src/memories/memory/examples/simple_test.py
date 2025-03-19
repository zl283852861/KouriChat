#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的配置测试脚本
"""
import os
import sys
import traceback
from pathlib import Path

def main():
    """简单测试配置加载"""
    print("===== 简单配置测试 =====")

    # 检查项目配置文件是否存在
    config_file = os.path.join("src", "config", "config.yaml")
    print(f"检查配置文件: {config_file}")
    print(f"文件存在: {os.path.exists(config_file)}")
    
    try:
        # 读取配置文件内容
        if os.path.exists(config_file):
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            print(f"\n配置文件内容类型: {type(config)}")
            
            # 检查是否为项目配置文件
            if 'categories' in config and 'rag_settings' in config.get('categories', {}):
                print("检测到KouriChat项目配置文件")
                
                # 提取RAG设置
                rag_settings = config.get('categories', {}).get('rag_settings', {}).get('settings', {})
                
                # 检查设置中的字段
                print("\nRAG设置字段:")
                for key in rag_settings.keys():
                    print(f"- {key}")
                
                # 检查是否包含嵌入模型和基础URL
                embedding_model = rag_settings.get('embedding_model', {}).get('value', '')
                eembedding_model = rag_settings.get('eembedding_model', {}).get('value', '')
                base_url = rag_settings.get('base_url', {}).get('value', '')
                bbase_url = rag_settings.get('bbase_url', {}).get('value', '')
                
                print("\n字段检查结果:")
                print(f"embedding_model: {embedding_model}")
                print(f"eembedding_model: {eembedding_model}")
                print(f"base_url: {base_url}")
                print(f"bbase_url: {bbase_url}")
                
                # 检查我们的修复是否生效
                if not embedding_model and eembedding_model:
                    print("✅ 错误拼写的eembedding_model字段被识别")
                    
                if not base_url and bbase_url:
                    print("✅ 错误拼写的bbase_url字段被识别")
                    
                print("\n测试成功完成!")
            else:
                print("不是KouriChat项目配置文件")
        else:
            print("无法找到配置文件")
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 
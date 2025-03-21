#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
记忆修复脚本 - 运行入口
"""
import sys
import os
import logging
import json
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('memory_fix')

def main():
    """主函数"""
    logger.info("开始修复记忆文件...")
    
    # 确保当前目录是项目根目录
    current_dir = Path.cwd()
    if not (current_dir / "src" / "tools").exists():
        logger.error("当前目录不是项目根目录，请从项目根目录运行此脚本")
        return 1
    
    # 添加src目录到Python路径
    sys.path.insert(0, str(current_dir))
    
    # 导入修复函数
    try:
        from src.tools.memory_fix import fix_memory_format
        
        # 运行修复函数
        result = fix_memory_format()
        
        if result:
            logger.info("记忆文件修复成功！")
        else:
            logger.info("记忆文件无需修复或修复失败")
            
        # 尝试读取并显示修复后的文件内容
        json_path = current_dir / "data" / "memory" / "rag-memory.json"
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                logger.info(f"记忆文件包含 {len(data)} 个对话")
                # 打印部分内容
                for key, conversations in list(data.items())[:3]:  # 只显示前3个对话
                    logger.info(f"对话 {key}:")
                    for i, entry in enumerate(conversations[:2]):
                        logger.info(f"  - 条目 {i}: {entry.get('sender_text', '无发送者文本')[:30]}... -> {entry.get('receiver_text', '无接收者文本')[:30]}...")
            except Exception as e:
                logger.error(f"读取记忆文件失败: {str(e)}")
        
        return 0 if result else 1
    except ImportError as e:
        logger.error(f"导入修复函数失败: {str(e)}")
        return 1
    except Exception as e:
        logger.error(f"修复过程中出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
记忆格式迁移脚本 - 运行入口
"""
import sys
import os
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('memory_migration')

def main():
    """主函数"""
    logger.info("开始记忆格式迁移...")
    
    # 确保当前目录是项目根目录
    current_dir = Path.cwd()
    if not (current_dir / "src" / "tools").exists():
        logger.error("当前目录不是项目根目录，请从项目根目录运行此脚本")
        return 1
    
    # 添加src目录到Python路径
    sys.path.insert(0, str(current_dir))
    
    # 导入并运行迁移函数
    try:
        from src.tools.memory_migration import migrate_memory_format
        
        result = migrate_memory_format()
        
        if result:
            logger.info("记忆格式迁移成功！")
            return 0
        else:
            logger.error("记忆格式迁移失败")
            return 1
    except Exception as e:
        logger.error(f"迁移过程中出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
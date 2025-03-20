#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
KouriChat 工具集脚本
此脚本用于启动各种工具功能
"""

import os
import sys
import argparse
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('tools')

def main():
    """
    主函数，负责解析命令行参数并启动相应工具
    """
    # 初始化参数解析器
    parser = argparse.ArgumentParser(description='KouriChat工具集')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 记忆迁移命令
    migrate_parser = subparsers.add_parser('migrate_memory', help='迁移记忆格式')
    
    # 记忆修复命令
    fix_parser = subparsers.add_parser('fix_memory', help='修复记忆格式')
    
    # 解析参数
    args = parser.parse_args()
    
    # 添加项目根目录到Python路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.append(current_dir)
    
    # 根据命令执行相应功能
    if args.command == 'migrate_memory':
        from src.tools.run_memory_migration import main as migrate_main
        return migrate_main()
    elif args.command == 'fix_memory':
        from src.tools.run_memory_fix import main as fix_main
        return fix_main()
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
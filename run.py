#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
KouriChat 主启动脚本
此脚本用于启动KouriChat程序
"""

import os
import sys

def main():
    """
    主函数，负责启动KouriChat程序
    """
    try:
        # 添加项目根目录到Python路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.append(current_dir)
        
        # 导入并运行main函数
        from src.main import main as start_kourichat
        
        # 判断是否使用调试模式
        debug_mode = '--debug' in sys.argv
        
        # 启动程序
        start_kourichat(debug_mode=debug_mode)
    except Exception as e:
        print(f"启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        input("按任意键退出...")
        sys.exit(1)

if __name__ == "__main__":
    main() 
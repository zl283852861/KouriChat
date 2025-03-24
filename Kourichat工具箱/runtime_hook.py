# -*- coding: utf-8 -*-
import os
import sys

# 确保当前目录在路径中
if getattr(sys, 'frozen', False):
    # 运行在打包环境中
    bundle_dir = sys._MEIPASS
    # 将bundle_dir添加到sys.path
    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)

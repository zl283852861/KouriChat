"""
Kouri Chat 工具箱主入口

此模块是应用程序的启动入口，负责初始化环境和启动主应用程序。
"""

import os
import sys
import customtkinter as ctk

# 添加当前目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置外观模式和默认颜色主题
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# 在main.py的开头添加以下代码（在导入customtkinter之前）
os.environ['CTK_MAX_FPS'] = '60'  # 限制最大帧率

# 导入应用程序类
from core.app import KouriChatApp

if __name__ == "__main__":
    try:
        # 创建并启动应用程序
        app = KouriChatApp()
        app.mainloop()
    except Exception as e:
        import traceback
        error_message = f"启动错误: {str(e)}\n\n{traceback.format_exc()}"
        print(error_message)
        
        # 显示错误对话框
        try:
            from tkinter import messagebox
            messagebox.showerror("启动错误", error_message)
        except:
            pass 
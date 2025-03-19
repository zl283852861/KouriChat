import customtkinter as ctk
import sys
import os

# 添加当前目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置外观模式和默认颜色主题
ctk.set_appearance_mode("System")  # 系统模式，会根据系统设置自动切换
ctk.set_default_color_theme("blue")  # 默认颜色主题

# 导入应用程序类
from core.app import KouriChatApp

if __name__ == "__main__":
    try:
        app = KouriChatApp()
        app.mainloop()
    except Exception as e:
        import traceback
        error_message = f"启动错误: {str(e)}\n\n{traceback.format_exc()}"
        print(error_message)  # 打印到控制台
        
        # 尝试显示错误对话框
        try:
            from tkinter import messagebox
            messagebox.showerror("启动错误", error_message)
        except:
            pass 
import customtkinter as ctk
from PIL import Image
import os

class IconButton(ctk.CTkButton):
    """带图标的按钮组件"""
    
    def __init__(self, master, icon_path=None, icon_size=(20, 20), **kwargs):
        # 加载图标
        self.icon_image = None
        if icon_path and os.path.exists(icon_path):
            try:
                image = Image.open(icon_path)
                self.icon_image = ctk.CTkImage(light_image=image, dark_image=image, size=icon_size)
            except Exception as e:
                print(f"加载图标失败: {e}")
        
        # 初始化按钮
        super().__init__(master, image=self.icon_image, compound="left", **kwargs) 
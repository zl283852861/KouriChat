import customtkinter as ctk

class LabeledEntry(ctk.CTkFrame):
    """带标签的输入框组件"""
    
    def __init__(self, master, label_text, width=200, height=30, **kwargs):
        super().__init__(master, width=width, height=height, **kwargs)
        
        # 确保框架可以扩展
        self.grid_columnconfigure(1, weight=1)
        
        # 创建标签
        self.label = ctk.CTkLabel(self, text=label_text)
        self.label.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
        
        # 创建输入框
        self.entry = ctk.CTkEntry(self, width=width)
        self.entry.grid(row=0, column=1, pady=5, sticky="ew")
        
        # 设置默认字体
        self.entry.configure(font=("Arial Unicode MS", 12))
    
    def get(self):
        """获取输入框内容"""
        return self.entry.get()
    
    def set(self, text):
        """设置输入框内容"""
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
    
    def clear(self):
        """清空输入框内容"""
        self.entry.delete(0, "end") 
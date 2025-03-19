import customtkinter as ctk

class ScrollableTextBox(ctk.CTkFrame):
    """可滚动的文本框组件"""
    
    def __init__(self, master, width=200, height=200, **kwargs):
        super().__init__(master, width=width, height=height, **kwargs)
        
        # 确保框架可以扩展
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # 创建文本框
        self.textbox = ctk.CTkTextbox(self, width=width, height=height)
        self.textbox.grid(row=0, column=0, sticky="nsew")
        
        # 设置默认字体
        self.textbox.configure(font=("Arial Unicode MS", 12))
    
    def set_text(self, text):
        """设置文本内容"""
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)
    
    def get_text(self):
        """获取文本内容"""
        return self.textbox.get("1.0", "end-1c")
    
    def append_text(self, text):
        """追加文本内容"""
        self.textbox.insert("end", text)
        self.textbox.see("end")  # 滚动到底部
    
    def clear(self):
        """清空文本内容"""
        self.textbox.delete("1.0", "end") 
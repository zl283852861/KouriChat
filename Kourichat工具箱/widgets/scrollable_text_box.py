import customtkinter as ctk

class ScrollableTextBox(ctk.CTkFrame):
    """可滚动的文本框组件"""
    
    def __init__(self, master, width=200, height=200, font=None, fg_color=None, border_color=None, **kwargs):
        # 移除text_color参数，它将在textbox中单独设置
        frame_kwargs = {k: v for k, v in kwargs.items() if k != 'text_color'}
        super().__init__(master, width=width, height=height, fg_color=fg_color, **frame_kwargs)
        
        # 创建文本框
        self.textbox = ctk.CTkTextbox(
            self,
            width=width,
            height=height,
            font=font,
            fg_color=fg_color,
            border_width=1,
            border_color=border_color,
            text_color=kwargs.get('text_color'),  # 在textbox中设置文本颜色
            wrap="word"
        )
        self.textbox.pack(fill="both", expand=True)
    
    def get_text(self):
        """获取文本内容"""
        return self.textbox.get("1.0", "end-1c")
    
    def set_text(self, text):
        """设置文本内容"""
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)
    
    def clear(self):
        """清空文本内容"""
        self.textbox.delete("1.0", "end")
    
    def append_text(self, text):
        """追加文本内容"""
        self.textbox.insert("end", text)
        self.textbox.see("end")  # 滚动到底部 
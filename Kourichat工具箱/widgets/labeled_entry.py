import customtkinter as ctk

class LabeledEntry(ctk.CTkFrame):
    """带标签的输入框组件"""
    
    def __init__(
        self, 
        master, 
        label_text="", 
        placeholder_text="", 
        default_value="",
        show=None,
        label_font=None,
        entry_font=None,
        label_color=None,
        entry_fg_color=None,
        entry_border_color=None,
        entry_text_color=None,
        **kwargs
    ):
        # 移除自定义参数
        frame_kwargs = {k: v for k, v in kwargs.items() if k not in [
            'placeholder_text', 'default_value', 'label_font', 'entry_font',
            'label_color', 'entry_fg_color', 'entry_border_color', 'entry_text_color'
        ]}
        super().__init__(master, **frame_kwargs)
        
        # 标签
        self.label = ctk.CTkLabel(
            self,
            text=label_text,
            font=label_font,
            text_color=label_color,
            anchor="w"
        )
        self.label.pack(side="left", padx=(0, 10))
        
        # 输入框
        self.entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder_text,
            font=entry_font,
            fg_color=entry_fg_color,
            border_color=entry_border_color,
            text_color=entry_text_color,
            show=show
        )
        self.entry.pack(side="left", fill="x", expand=True)
        
        # 设置默认值
        if default_value:
            self.entry.insert(0, default_value)
    
    def get(self):
        """获取输入框的值"""
        return self.entry.get()
    
    def set(self, value):
        """设置输入框的值"""
        self.entry.delete(0, "end")
        self.entry.insert(0, value)
    
    def clear(self):
        """清空输入框"""
        self.entry.delete(0, "end") 
import customtkinter as ctk
import webbrowser

class HelpPage:
    """帮助页面类"""
    
    def __init__(self, app):
        self.app = app
        self.setup_help_page()
    
    def setup_help_page(self):
        """设置帮助页面内容"""
        # 页面标题
        title_label = ctk.CTkLabel(
            self.app.help_frame, 
            text="帮助与关于", 
            font=self.app.title_font
        )
        title_label.pack(pady=(20, 20))
        
        # 创建滚动框架
        help_scroll_frame = ctk.CTkScrollableFrame(self.app.help_frame)
        help_scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 关于应用
        about_label = ctk.CTkLabel(
            help_scroll_frame, 
            text="关于 Kouri Chat 工具箱", 
            font=ctk.CTkFont(family="Arial Unicode MS", size=16, weight="bold")
        )
        about_label.pack(anchor="w", pady=(0, 10))
        
        about_text = ctk.CTkLabel(
            help_scroll_frame, 
            text="Kouri Chat 工具箱是一个基于大型语言模型的多功能工具箱，提供角色人设生成、图片识别和生成等功能。",
            font=self.app.default_font,
            wraplength=800,
            justify="left"
        )
        about_text.pack(anchor="w", pady=(0, 20))
        
        # 功能说明
        features_label = ctk.CTkLabel(
            help_scroll_frame, 
            text="功能说明", 
            font=ctk.CTkFont(family="Arial Unicode MS", size=16, weight="bold")
        )
        features_label.pack(anchor="w", pady=(0, 10))
        
        features = [
            "人设生成：根据简短描述生成详细的角色人设，支持润色和导入导出。",
            "API配置：配置不同API的连接参数，支持多种服务提供商。",
            "图片功能：上传图片进行内容识别，或根据文本描述生成图片。",
            "主题设置：切换应用的外观主题，支持亮色、暗色和跟随系统。"
        ]
        
        for feature in features:
            feature_text = ctk.CTkLabel(
                help_scroll_frame, 
                text=f"• {feature}",
                font=self.app.default_font,
                wraplength=800,
                justify="left"
            )
            feature_text.pack(anchor="w", pady=(0, 5))
        
        # 使用说明
        usage_label = ctk.CTkLabel(
            help_scroll_frame, 
            text="使用说明", 
            font=ctk.CTkFont(family="Arial Unicode MS", size=16, weight="bold")
        )
        usage_label.pack(anchor="w", pady=(20, 10))
        
        usage_text = ctk.CTkLabel(
            help_scroll_frame, 
            text="1. 首先在API配置页面设置您的API密钥和服务器地址。\n"
                 "2. 在人设页面输入角色描述，点击生成按钮创建角色人设。\n"
                 "3. 在图片页面可以上传图片进行识别或输入描述生成图片。\n"
                 "4. 在主题页面可以切换应用的外观主题。",
            font=self.app.default_font,
            wraplength=800,
            justify="left"
        )
        usage_text.pack(anchor="w", pady=(0, 20))
        
        # 联系方式
        contact_label = ctk.CTkLabel(
            help_scroll_frame, 
            text="联系方式", 
            font=ctk.CTkFont(family="Arial Unicode MS", size=16, weight="bold")
        )
        contact_label.pack(anchor="w", pady=(0, 10))
        
        contact_text = ctk.CTkLabel(
            help_scroll_frame, 
            text="主项目官方网站：https://kourichat.com/\n"
                 "主项目GitHub：https://github.com/KouriChat/KouriChat\n"
                 "工具箱QQ群：639849597\n"
                 "GitHub：https://github.com/linxiajin08/linxiajinKouri",
            font=self.app.default_font,
            wraplength=800,
            justify="left"
        )
        contact_text.pack(anchor="w", pady=(0, 20))
        
        # 版权信息
        copyright_text = ctk.CTkLabel(
            help_scroll_frame, 
            text="© 2024-2025 Kouri Chat. 保留所有权利。",
            font=ctk.CTkFont(family="Arial Unicode MS", size=10),
            text_color=("gray50", "gray70")
        )
        copyright_text.pack(anchor="w", pady=(20, 0))
        
        # 访问官网按钮
        website_button = ctk.CTkButton(
            self.app.help_frame,
            text="访问项目地址",
            command=lambda: webbrowser.open("https://github.com/linxiajin08/linxiajinKouri"),
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        website_button.pack(pady=(0, 20)) 
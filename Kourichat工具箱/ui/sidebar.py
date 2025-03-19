import customtkinter as ctk
import webbrowser

class Sidebar:
    """侧边栏类"""
    
    def __init__(self, app):
        self.app = app
        self.setup_sidebar()
        
    def setup_sidebar(self):
        """设置侧边栏"""
        # 创建侧边栏框架
        self.sidebar_frame = ctk.CTkFrame(self.app, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)  # 底部空白区域可扩展
        
        # 添加应用标题
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="Kouri Chat",
            font=ctk.CTkFont(family="Arial Unicode MS", size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 20))
        
        # 添加侧边栏按钮
        self.sidebar_buttons = []
        
        # 人设按钮
        self.character_button = ctk.CTkButton(
            self.sidebar_frame,
            text="人设",
            font=ctk.CTkFont(family="Arial Unicode MS", size=14),
            command=self.app.show_character_page,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color=("black", "white")  # 确保在亮色/暗色主题下文字都可见
        )
        self.character_button.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.sidebar_buttons.append(self.character_button)
        
        # API配置按钮
        self.api_config_button = ctk.CTkButton(
            self.sidebar_frame,
            text="API配置",
            font=ctk.CTkFont(family="Arial Unicode MS", size=14),
            command=self.app.show_api_config_page,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color=("black", "white")  # 确保在亮色/暗色主题下文字都可见
        )
        self.api_config_button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.sidebar_buttons.append(self.api_config_button)
        
        # 图片按钮
        self.image_button = ctk.CTkButton(
            self.sidebar_frame,
            text="图片",
            font=ctk.CTkFont(family="Arial Unicode MS", size=14),
            command=self.app.show_image_page,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color=("black", "white")  # 确保在亮色/暗色主题下文字都可见
        )
        self.image_button.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.sidebar_buttons.append(self.image_button)
        
        # 帮助按钮
        self.help_button = ctk.CTkButton(
            self.sidebar_frame,
            text="帮助",
            font=ctk.CTkFont(family="Arial Unicode MS", size=14),
            command=self.app.show_help_page,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color=("black", "white")  # 确保在亮色/暗色主题下文字都可见
        )
        self.help_button.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        self.sidebar_buttons.append(self.help_button)
        
        # 底部版本信息
        self.version_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="V11.0",
            font=ctk.CTkFont(family="Arial Unicode MS", size=10),
            text_color=("black", "white")
        )
        self.version_label.grid(row=8, column=0, padx=20, pady=(5, 20))
        
        # 添加主题切换开关 - 移到版本号上方
        self.app.appearance_mode_switch = ctk.CTkSwitch(
            self.sidebar_frame,
            text="暗色模式",
            font=ctk.CTkFont(family="Arial Unicode MS", size=12),
            command=self.app.toggle_theme,
            text_color=("black", "white"),
            progress_color=("gray70", "gray30")
        )
        self.app.appearance_mode_switch.grid(row=7, column=0, padx=20, pady=(10, 10), sticky="w")
        
        # 根据当前主题设置开关状态
        if self.app.current_theme == "dark":
            self.app.appearance_mode_switch.select()
        else:
            self.app.appearance_mode_switch.deselect()
    
    def highlight_button(self, active_button):
        """高亮当前选中的侧边栏按钮"""
        for button in self.sidebar_buttons:
            if button == active_button:
                button.configure(fg_color=("gray75", "gray25"))
            else:
                button.configure(fg_color="transparent") 
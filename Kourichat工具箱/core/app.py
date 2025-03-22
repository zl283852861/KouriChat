"""
主应用程序模块，提供应用程序的核心功能
"""

from tkinter import messagebox
import customtkinter as ctk

from core.config import APIConfig
from core.theme_manager import ThemeManager
from ui.sidebar import Sidebar
from ui.pages.character_page import CharacterPage
from ui.pages.api_config_page import APIConfigPage
from ui.pages.image_page import ImagePage
from ui.pages.help_page import HelpPage
from ui.transition import PageTransition
from ui.theme_transition import ThemeTransition

class KouriChatApp(ctk.CTk):
    """Kouri Chat 应用程序主类，管理UI和用户交互"""
    
    def __init__(self):
        super().__init__()
        
        # 设置窗口属性
        self.title("Kouri Chat 工具箱 V12.0")
        self.geometry("1000x700")
        self.minsize(800, 600)
        
        # 设置默认字体
        self.default_font = ("Arial Unicode MS", 12)
        self.title_font = ("Arial Unicode MS", 16, "bold")
        
        # 设置默认按钮颜色
        ctk.set_default_color_theme("blue")
        self.button_color = "#eea2a4"  # 粉色按钮
        self.button_hover_color = "#e58a8c"  # 粉色按钮悬停颜色
        self.purple_color = "#9370DB"  # 紫色
        self.purple_hover_color = "#8A5DC8"  # 紫色悬停颜色
        
        # 加载配置
        self.config = APIConfig.read_config()
        
        # 设置主题
        self.current_theme = self.config.get("theme", "system")
        self.apply_theme()
        
        # 创建主框架
        self.setup_main_layout()
        
        # 初始化页面内容
        self.character_page = CharacterPage(self)
        self.api_config_page = APIConfigPage(self)
        self.image_page = ImagePage(self)
        self.help_page = HelpPage(self)
        
        # 初始化过渡效果
        self.transition = PageTransition(self)
        self.theme_transition = ThemeTransition(self)
        
        # 默认显示人设页面
        self.show_character_page()
        
        # 初始化生成的人设内容
        self.generated_profile = None
        
        # 设置窗口最大化
        self.after(100, self.maximize_window)
    
    def maximize_window(self):
        """将窗口最大化"""
        self.state("zoomed")
    
    def setup_main_layout(self):
        """设置主布局"""
        # 配置网格布局
        self.grid_columnconfigure(1, weight=1)  # 内容区域可扩展
        self.grid_rowconfigure(0, weight=1)  # 行可扩展
        
        # 创建侧边栏
        self.sidebar = Sidebar(self)
        
        # 创建内容区域
        self.setup_content_area()
    
    def setup_content_area(self):
        """设置内容区域"""
        # 创建内容区域框架
        self.content_frame = ctk.CTkFrame(self, corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        
        # 创建各个页面的框架
        self.character_frame = ctk.CTkFrame(self.content_frame, corner_radius=0)
        self.api_config_frame = ctk.CTkFrame(self.content_frame, corner_radius=0)
        self.image_frame = ctk.CTkFrame(self.content_frame, corner_radius=0)
        self.help_frame = ctk.CTkFrame(self.content_frame, corner_radius=0)
    
    def apply_theme(self):
        """应用主题"""
        ThemeManager.apply_theme(self, self.current_theme)
    
    def toggle_theme(self):
        """切换明暗主题"""
        ThemeManager.toggle_theme(self)
    
    def show_character_page(self):
        """显示人设页面"""
        self.clear_content_frame()
        self.character_frame.pack(fill="both", expand=True)
        self.highlight_sidebar_button(self.sidebar.character_button)
    
    def show_api_config_page(self):
        """显示API配置页面"""
        self.clear_content_frame()
        self.api_config_frame.pack(fill="both", expand=True)
        self.highlight_sidebar_button(self.sidebar.api_config_button)
    
    def show_image_page(self):
        """显示图片页面"""
        self.clear_content_frame()
        self.image_frame.pack(fill="both", expand=True)
        self.highlight_sidebar_button(self.sidebar.image_button)
    
    def show_help_page(self):
        """显示帮助页面"""
        self.clear_content_frame()
        self.help_frame.pack(fill="both", expand=True)
        self.highlight_sidebar_button(self.sidebar.help_button)
    
    def clear_content_frame(self):
        """清除内容区域"""
        for frame in [self.character_frame, self.api_config_frame, 
                     self.image_frame, self.help_frame]:
            frame.pack_forget()
    
    def highlight_sidebar_button(self, active_button):
        """高亮侧边栏按钮"""
        self.sidebar.highlight_button(active_button)
    
    def save_all_configs(self):
        """保存所有API配置"""
        # 保存人设API配置
        self.api_config_page.save_character_config()
        
        # 保存图片识别API配置
        self.api_config_page.save_recognition_config()
        
        # 保存图片生成API配置
        self.api_config_page.save_generation_config()
        
        messagebox.showinfo("保存成功", "所有API配置已保存！")

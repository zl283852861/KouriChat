import customtkinter as ctk
from tkinter import messagebox
import threading
import requests
import json
import os

from widgets.labeled_entry import LabeledEntry
from core.config import APIConfig
from core.error_handler import handle_api_error
from api.tester import APITester
from ..theme import Theme

class APIConfigPage:
    """API配置页面类"""
    
    def __init__(self, app):
        self.app = app
        
        # 添加API密钥申请网址
        self.api_key_websites = {
            "Kourichat": "https://api.ciallo.ac.cn/token",
            "DeepSeek": "https://platform.deepseek.com/api_keys",
            "硅基流动": "https://cloud.siliconflow.cn/account/ak?referrer=clxty1xuy0014lvqwh5z50i88",
            "moonshot": "https://platform.moonshot.cn/console/api-keys"
        }
        
        # 添加默认 API 地址映射
        self.api_base_urls = {
            "Kourichat": "https://api.ciallo.ac.cn",
            "DeepSeek": "https://api.deepseek.com",
            "硅基流动": "https://api.siliconflow.cn",
            "moonshot": "https://api.moonshot.cn",
            "自定义": ""
        }
        
        # 根据主题模式设置按钮文字颜色
        # 使用 ctk.get_appearance_mode() 而不是 self.app._get_appearance_mode()
        current_mode = ctk.get_appearance_mode()
        
        # 直接设置固定的颜色，不再依赖于模式判断
        if current_mode.lower() == "light":
            self.secondary_button_text_color = "#000000"  # 浅色模式 -> 黑色文字
        else:
            self.secondary_button_text_color = "#FFFFFF"  # 深色模式 -> 白色文字

        # 设置API配置页面
        self.setup_api_config_page()
    
    def setup_api_config_page(self):
        """设置API配置页面"""
        # 创建主容器
        main_container = ctk.CTkFrame(
            self.app.api_config_frame, 
            fg_color="transparent"
        )
        main_container.pack(fill="both", expand=True, padx=40, pady=30)
        
        # 页面标题
        title_frame = ctk.CTkFrame(
            main_container,
            fg_color=Theme.CARD_BG,
            corner_radius=15,
            height=80
        )
        title_frame.pack(fill="x", pady=(0, 20))
        title_frame.pack_propagate(False)
        
        # 标题和按钮容器
        title_container = ctk.CTkFrame(title_frame, fg_color="transparent")
        title_container.pack(expand=True, fill="both", padx=30)
        
        title_label = ctk.CTkLabel(
            title_container,
            text="API配置中心",
            font=Theme.get_font(size=32, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        title_label.pack(side="left", expand=True, anchor="w")
        
        # 保存所有配置按钮
        save_all_button = ctk.CTkButton(
            title_container,
            text="保存所有配置", 
            command=self.save_all_configs,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8,
            border_spacing=10
        )
        save_all_button.pack(side="right", padx=5)
        
        # 创建选项卡视图
        self.tab_view = ctk.CTkTabview(
            main_container,
            fg_color=Theme.CARD_BG,
            segmented_button_fg_color=Theme.BG_SECONDARY,
            segmented_button_selected_color=Theme.BUTTON_PRIMARY,
            segmented_button_selected_hover_color=Theme.BUTTON_PRIMARY_HOVER,
            segmented_button_unselected_color=Theme.BG_SECONDARY,
            segmented_button_unselected_hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            corner_radius=15
        )
        self.tab_view.pack(fill="both", expand=True)
        
        # 配置标签页按钮样式
        self.tab_view._segmented_button.configure(
            font=Theme.get_font(size=16, weight="bold"),
            height=45,
            corner_radius=8
        )
        
        # 添加选项卡
        self.character_tab = self.tab_view.add("人设API")
        self.recognition_tab = self.tab_view.add("图片识别API")
        self.generation_tab = self.tab_view.add("图片生成API")
        
        # 设置标签页按钮的样式和宽度
        for button in self.tab_view._segmented_button._buttons_dict.values():
            button.configure(
                width=160,
                fg_color=Theme.BG_SECONDARY,
                hover_color=Theme.BUTTON_SECONDARY_HOVER,
                border_width=0,
                corner_radius=8,
                text_color_disabled=Theme.TEXT_SECONDARY
            )
        
        # 设置选项卡内容
        self.setup_character_api_tab(self.character_tab)
        self.setup_recognition_api_tab(self.recognition_tab)
        self.setup_generation_api_tab(self.generation_tab)
        
        # 加载配置
        self.load_config()
    
    def setup_character_api_tab(self, parent_frame):
        """设置人设API选项卡"""
        # 渠道选择
        channel_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        channel_frame.pack(fill="x", padx=20, pady=10)
        
        channel_label = ctk.CTkLabel(
            channel_frame, 
            text="选择渠道:", 
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_PRIMARY
        )
        channel_label.pack(side="left")
        
        # 渠道选项
        self.character_channels = {
            "Kourichat": ["kourichat-r1", "kourichat-v3"],
            "DeepSeek": ["deepseek-chat", "deepseek-reasoner"],
            "硅基流动": ["deepseek-ai/DeepSeek-V3", "deepseek-ai/DeepSeek-R1", "Pro/deepseek-ai/DeepSeek-V3", "Pro/deepseek-ai/DeepSeek-R1"],
            "自定义": ["custom"]
        }
        
        self.character_channel_var = ctk.StringVar(value=list(self.character_channels.keys())[0])
        
        channel_menu = ctk.CTkOptionMenu(
            channel_frame, 
            values=list(self.character_channels.keys()),
            variable=self.character_channel_var,
            command=self.on_character_channel_changed,
            font=Theme.get_font(size=14),
            fg_color=Theme.BG_TERTIARY,
            button_color=Theme.BUTTON_SECONDARY,
            button_hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            width=150
        )
        channel_menu.pack(side="right")
        
        # API配置区域
        config_frame = ctk.CTkFrame(
            parent_frame,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=10
        )
        config_frame.pack(fill="both", expand=True, padx=30, pady=20)
        
        # URL输入框
        self.character_url_entry = LabeledEntry(
            config_frame,
            label_text="服务器地址:",
            placeholder_text="请输入API服务器地址",
            label_font=Theme.get_font(size=14),
            entry_font=Theme.get_font(size=14),
            label_color=Theme.TEXT_PRIMARY,
            entry_fg_color=Theme.BG_TERTIARY,
            entry_text_color=Theme.TEXT_PRIMARY,
            entry_border_color=None
        )
        self.character_url_entry.pack(fill="x", padx=20, pady=(20, 10))
        
        # API密钥输入框和申请按钮
        api_key_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        api_key_frame.pack(fill="x", padx=20, pady=10)
        
        self.character_key_entry = LabeledEntry(
            api_key_frame,
            label_text="API密钥:",
            placeholder_text="请输入API密钥",
            show="*",
            label_font=Theme.get_font(size=14),
            entry_font=Theme.get_font(size=14),
            label_color=Theme.TEXT_PRIMARY,
            entry_fg_color=Theme.BG_TERTIARY,
            entry_text_color=Theme.TEXT_PRIMARY,
            entry_border_color=None
        )
        self.character_key_entry.pack(fill="x", side="left", expand=True, padx=(0, 10))
        
        # 申请API密钥按钮
        self.character_apply_key_button = ctk.CTkButton(
            api_key_frame,
            text="申请密钥",
            command=lambda: self.open_api_key_website(self.character_channel_var.get()),
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_SECONDARY,
            hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            height=38,
            width=100,
            corner_radius=8
        )
        self.character_apply_key_button.pack(side="right")
        
        # 模型选择区域
        model_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        model_frame.pack(fill="x", padx=20, pady=10)
        
        model_label = ctk.CTkLabel(
            model_frame, 
            text="选择模型:", 
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_PRIMARY
        )
        model_label.pack(side="left", padx=(0, 10))
        
        self.character_model_var = ctk.StringVar(value=self.character_channels["Kourichat"][0])
        
        self.character_model_menu = ctk.CTkOptionMenu(
            model_frame, 
            values=self.character_channels["Kourichat"],
            variable=self.character_model_var,
            font=Theme.get_font(size=14),
            fg_color=Theme.BG_TERTIARY,
            button_color=Theme.BUTTON_SECONDARY,
            button_hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            width=200
        )
        self.character_model_menu.pack(side="left", padx=(0, 10))
        
        # 自定义模型输入框
        self.character_model_entry = LabeledEntry(
            config_frame,
            label_text="自定义模型:",
            placeholder_text="可选，输入自定义模型名称",
            label_font=Theme.get_font(size=14),
            entry_font=Theme.get_font(size=14),
            label_color=Theme.TEXT_PRIMARY,
            entry_fg_color=Theme.BG_TERTIARY,
            entry_text_color=Theme.TEXT_PRIMARY,
            entry_border_color=None
        )
        self.character_model_entry.pack(fill="x", padx=20, pady=10)
        
        # 按钮区域
        button_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        # 测试连接按钮
        test_button = ctk.CTkButton(
            button_frame,
            text="测试连接",
            command=self.test_character_api,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8
        )
        test_button.pack(side="left", padx=(0, 10))
        
        # 保存配置按钮
        save_button = ctk.CTkButton(
            button_frame,
            text="保存配置",
            command=self.save_character_config,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8
        )
        save_button.pack(side="left", padx=(0, 10))
        
        # 重置按钮
        self.character_reset_button = ctk.CTkButton(
            button_frame,
            text="重置",
            command=self.reset_character_config,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_SECONDARY,
            hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=self.secondary_button_text_color,
            height=38,
            width=80,
            corner_radius=8
        )
        self.character_reset_button.pack(side="right")
    
    def setup_recognition_api_tab(self, parent_frame):
        """设置识别API选项卡"""
        # 渠道选择
        channel_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        channel_frame.pack(fill="x", padx=20, pady=10)
        
        channel_label = ctk.CTkLabel(
            channel_frame, 
            text="选择渠道:", 
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_PRIMARY
        )
        channel_label.pack(side="left")
        
        # 渠道选项
        self.recognition_channels = {
            "Kourichat": ["kourichat-vision", "gemini-2.0-flash", "gemini-2.0-pro"],
            "硅基流动": ["Qwen/Qwen2.5-VL-72B-Instruct", "deepseek-ai/deepseek-vl2", "Qwen/QVQ-72B-Preview"],
            "moonshot": ["moonshot-v1-8k-vision-preview"],
            "自定义": ["custom"]
        }
        
        self.recognition_channel_var = ctk.StringVar(value=list(self.recognition_channels.keys())[0])
        
        channel_menu = ctk.CTkOptionMenu(
            channel_frame, 
            values=list(self.recognition_channels.keys()),
            variable=self.recognition_channel_var,
            command=self.update_recognition_channel,
            font=Theme.get_font(size=14),
            fg_color=Theme.BG_TERTIARY,
            button_color=Theme.BUTTON_SECONDARY,
            button_hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            width=150
        )
        channel_menu.pack(side="right")
        
        # API配置区域
        config_frame = ctk.CTkFrame(
            parent_frame,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=10
        )
        config_frame.pack(fill="both", expand=True, padx=30, pady=20)
        
        # URL输入框
        self.recognition_url_entry = LabeledEntry(
            config_frame,
            label_text="服务器地址:",
            placeholder_text="请输入API服务器地址",
            label_font=Theme.get_font(size=14),
            entry_font=Theme.get_font(size=14),
            label_color=Theme.TEXT_PRIMARY,
            entry_fg_color=Theme.BG_TERTIARY,
            entry_text_color=Theme.TEXT_PRIMARY,
            entry_border_color=None
        )
        self.recognition_url_entry.pack(fill="x", padx=20, pady=(20, 10))
        
        # API密钥输入框和申请按钮
        api_key_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        api_key_frame.pack(fill="x", padx=20, pady=10)
        
        self.recognition_key_entry = LabeledEntry(
            api_key_frame,
            label_text="API密钥:",
            placeholder_text="请输入API密钥",
            show="*",
            label_font=Theme.get_font(size=14),
            entry_font=Theme.get_font(size=14),
            label_color=Theme.TEXT_PRIMARY,
            entry_fg_color=Theme.BG_TERTIARY,
            entry_text_color=Theme.TEXT_PRIMARY,
            entry_border_color=None
        )
        self.recognition_key_entry.pack(fill="x", side="left", expand=True, padx=(0, 10))
        
        # 申请API密钥按钮
        self.recognition_apply_key_button = ctk.CTkButton(
            api_key_frame,
            text="申请密钥",
            command=lambda: self.open_api_key_website(self.recognition_channel_var.get()),
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_SECONDARY,
            hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            height=38,
            width=100,
            corner_radius=8
        )
        self.recognition_apply_key_button.pack(side="right")
        
        # 模型选择区域
        model_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        model_frame.pack(fill="x", padx=20, pady=10)
        
        model_label = ctk.CTkLabel(
            model_frame, 
            text="选择模型:", 
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_PRIMARY
        )
        model_label.pack(side="left", padx=(0, 10))
        
        self.recognition_model_var = ctk.StringVar(value=self.recognition_channels["Kourichat"][0])
        
        self.recognition_model_menu = ctk.CTkOptionMenu(
            model_frame, 
            values=self.recognition_channels["Kourichat"],
            variable=self.recognition_model_var,
            font=Theme.get_font(size=14),
            fg_color=Theme.BG_TERTIARY,
            button_color=Theme.BUTTON_SECONDARY,
            button_hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            width=200
        )
        self.recognition_model_menu.pack(side="left", padx=(0, 10))
        
        # 自定义模型输入框
        self.recognition_model_entry = LabeledEntry(
            config_frame,
            label_text="自定义模型:",
            placeholder_text="可选，输入自定义模型名称",
            label_font=Theme.get_font(size=14),
            entry_font=Theme.get_font(size=14),
            label_color=Theme.TEXT_PRIMARY,
            entry_fg_color=Theme.BG_TERTIARY,
            entry_text_color=Theme.TEXT_PRIMARY,
            entry_border_color=None
        )
        self.recognition_model_entry.pack(fill="x", padx=20, pady=10)
        
        # 按钮区域
        button_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        # 保存按钮
        save_button = ctk.CTkButton(
            button_frame,
            text="保存配置",
            command=self.save_recognition_config,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8,
            border_spacing=10
        )
        save_button.pack(side="left", padx=5)
        
        # 测试按钮
        test_button = ctk.CTkButton(
            button_frame, 
            text="测试连接", 
            command=self.test_recognition_api,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8,
            border_spacing=10
        )
        test_button.pack(side="left", padx=5)
        
        # 重置按钮
        self.recognition_reset_button = ctk.CTkButton(
            button_frame,
            text="重置",
            command=self.reset_recognition_config,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_SECONDARY,
            hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=self.secondary_button_text_color,
            height=38,
            width=80,
            corner_radius=8
        )
        self.recognition_reset_button.pack(side="right")
    
    def setup_generation_api_tab(self, parent_frame):
        """设置生成API选项卡"""
        # 渠道选择 - 移除渠道选择框，直接显示固定渠道
        channel_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        channel_frame.pack(fill="x", padx=20, pady=10)
        
        channel_label = ctk.CTkLabel(
            channel_frame, 
            text="渠道:", 
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_PRIMARY
        )
        channel_label.pack(side="left")
        
        # 固定显示硅基流动渠道
        channel_value_label = ctk.CTkLabel(
            channel_frame, 
            text="硅基流动 (仅支持此渠道)",
            font=Theme.get_font(size=14, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        channel_value_label.pack(side="right")
        
        # 渠道选项 - 只保留硅基流动
        self.generation_channels = {
            "硅基流动": ["Kwai-Kolors/Kolors"],
        }
        
        # 固定渠道变量
        self.generation_channel_var = ctk.StringVar(value="硅基流动")
        
        # API配置区域
        config_frame = ctk.CTkFrame(
            parent_frame,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=10
        )
        config_frame.pack(fill="both", expand=True, padx=30, pady=20)
        
        # URL输入框 - 显示但禁用编辑
        self.generation_url_entry = LabeledEntry(
            config_frame,
            label_text="服务器地址:",
            placeholder_text="硅基流动API地址",
            label_font=Theme.get_font(size=14),
            entry_font=Theme.get_font(size=14),
            label_color=Theme.TEXT_PRIMARY,
            entry_fg_color=Theme.BG_TERTIARY,
            entry_text_color=Theme.TEXT_PRIMARY,
            entry_border_color=None
        )
        self.generation_url_entry.pack(fill="x", padx=20, pady=(20, 10))
        
        # 设置并禁用URL输入框
        self.generation_url_entry.set(self.api_base_urls["硅基流动"])
        self.generation_url_entry.entry.configure(state="disabled")
        
        # API密钥输入框
        api_key_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        api_key_frame.pack(fill="x", padx=20, pady=10)
        
        self.generation_key_entry = LabeledEntry(
            api_key_frame,
            label_text="API密钥:",
            placeholder_text="请输入API密钥",
            show="*",
            label_font=Theme.get_font(size=14),
            entry_font=Theme.get_font(size=14),
            label_color=Theme.TEXT_PRIMARY,
            entry_fg_color=Theme.BG_TERTIARY,
            entry_text_color=Theme.TEXT_PRIMARY,
            entry_border_color=None
        )
        self.generation_key_entry.pack(fill="x", side="left", expand=True, padx=(0, 10))
        
        # 申请API密钥按钮
        self.generation_apply_key_button = ctk.CTkButton(
            api_key_frame,
            text="申请密钥",
            command=lambda: self.open_api_key_website("硅基流动"),
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_SECONDARY,
            hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            height=38,
            width=100,
            corner_radius=8
        )
        self.generation_apply_key_button.pack(side="right")
        
        # 模型选择区域
        model_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        model_frame.pack(fill="x", padx=20, pady=10)
        
        model_label = ctk.CTkLabel(
            model_frame, 
            text="选择模型:", 
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_PRIMARY
        )
        model_label.pack(side="left", padx=(0, 10))
        
        self.generation_model_var = ctk.StringVar(value=self.generation_channels["硅基流动"][0])
        
        self.generation_model_menu = ctk.CTkOptionMenu(
            model_frame, 
            values=self.generation_channels["硅基流动"],
            variable=self.generation_model_var,
            font=Theme.get_font(size=14),
            fg_color=Theme.BG_TERTIARY,
            button_color=Theme.BUTTON_SECONDARY,
            button_hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            width=200
        )
        self.generation_model_menu.pack(side="left", padx=(0, 10))
        
        # 自定义模型输入框
        self.generation_model_entry = LabeledEntry(
            config_frame,
            label_text="自定义模型:",
            placeholder_text="不支持自定义模型",
            label_font=Theme.get_font(size=14),
            entry_font=Theme.get_font(size=14),
            label_color=Theme.TEXT_PRIMARY,
            entry_fg_color=Theme.BG_TERTIARY,
            entry_text_color=Theme.TEXT_PRIMARY,
            entry_border_color=None
        )
        self.generation_model_entry.pack(fill="x", padx=20, pady=10)
        self.generation_model_entry.entry.configure(state="disabled")
        
        # 按钮区域
        button_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        # 保存按钮
        save_button = ctk.CTkButton(
            button_frame,
            text="保存配置",
            command=self.save_generation_config,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8,
            border_spacing=10
        )
        save_button.pack(side="left", padx=5)
        
        # 测试按钮
        test_button = ctk.CTkButton(
            button_frame, 
            text="测试连接", 
            command=self.test_generation_api,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8,
            border_spacing=10
        )
        test_button.pack(side="left", padx=5)
        
        # 重置按钮
        self.generation_reset_button = ctk.CTkButton(
            button_frame,
            text="重置",
            command=self.reset_generation_config,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_SECONDARY,
            hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=self.secondary_button_text_color,
            height=38,
            width=80,
            corner_radius=8
        )
        self.generation_reset_button.pack(side="right")
    
    def on_character_channel_changed(self, event=None):
        try:
            # 获取选中的渠道
            selected_channel = self.character_channel_var.get()
            
            # 如果有默认 API 地址，则自动填充
            if selected_channel in self.api_base_urls:
                self.character_url_entry.entry.delete(0, ctk.END)
                self.character_url_entry.entry.insert(0, self.api_base_urls[selected_channel])
            
            # 更新模型下拉菜单
            models = self.character_channels[selected_channel]
            self.character_model_var.set(models[0])
            self.character_model_menu.configure(values=models)
            
            # 如果选择自定义，启用自定义模型输入框
            if selected_channel == "自定义":
                self.character_model_entry.entry.configure(state="normal")
            else:
                self.character_model_entry.entry.configure(state="disabled")
                self.character_model_entry.entry.delete(0, "end")
        except Exception as e:
            import traceback
            print(f"错误发生在 on_character_channel_changed: {str(e)}")
            print(traceback.format_exc())
    
    def update_recognition_channel(self, choice):
        """更新识别API渠道选择"""
        # 获取当前选择的渠道对应的模型列表
        models = self.recognition_channels[choice]
        
        # 如果有默认 API 地址，则自动填充
        if choice in self.api_base_urls:
            self.recognition_url_entry.entry.delete(0, ctk.END)
            self.recognition_url_entry.entry.insert(0, self.api_base_urls[choice])
        
        # 更新模型下拉菜单
        self.recognition_model_var.set(models[0])
        self.recognition_model_menu.configure(values=models)
        
        # 如果选择自定义，启用自定义模型输入框
        if choice == "自定义":
            self.recognition_model_entry.entry.configure(state="normal")
        else:
            self.recognition_model_entry.entry.configure(state="disabled")
            self.recognition_model_entry.entry.delete(0, "end")
    
    def update_generation_channel(self, choice=None):
        """更新生成API渠道选择 - 现在只是一个占位方法"""
        # 固定使用硅基流动
        choice = "硅基流动"
        
        # 获取当前选择的渠道对应的模型列表
        models = self.generation_channels[choice]
        
        # 如果有默认 API 地址，则自动填充
        if choice in self.api_base_urls:
            self.generation_url_entry.entry.delete(0, ctk.END)
            self.generation_url_entry.entry.insert(0, self.api_base_urls[choice])
        
        # 更新模型下拉菜单
        self.generation_model_var.set(models[0])
        self.generation_model_menu.configure(values=models)
        
        # 始终禁用自定义模型输入框
        self.generation_model_entry.entry.configure(state="disabled")
        self.generation_model_entry.entry.delete(0, "end")
    
    def save_character_config(self):
        """保存人设API配置"""
        # 获取配置信息
        config = {
            "url": self.character_url_entry.get().strip(),
            "api_key": self.character_key_entry.get().strip(),
            "channel": self.character_channel_var.get(),
            "model": self.character_model_entry.get().strip() or self.character_model_var.get()
        }
        
        # 验证配置
        if not config["url"]:
            messagebox.showwarning("警告", "请输入API服务器地址！")
            return
        
        if not config["api_key"]:
            messagebox.showwarning("警告", "请输入API密钥！")
            return
        
        # 更新配置
        self.app.config["character_api"] = config
        
        # 保存到文件
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.app.config, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("成功", "人设API配置已保存！")
        except Exception as e:
            messagebox.showerror("保存失败", f"保存配置文件时出错: {str(e)}")
    
    def save_recognition_config(self):
        """保存识别API配置"""
        # 获取配置信息
        config = {
            "url": self.recognition_url_entry.get().strip(),
            "api_key": self.recognition_key_entry.get().strip(),
            "channel": self.recognition_channel_var.get(),
            "model": self.recognition_model_entry.get().strip() or self.recognition_model_var.get()
        }
        
        # 验证配置
        if not config["url"]:
            messagebox.showwarning("警告", "请输入API服务器地址！")
            return
        
        if not config["api_key"]:
            messagebox.showwarning("警告", "请输入API密钥！")
            return
        
        # 更新配置
        self.app.config["recognition_api"] = config
        
        # 保存到文件
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.app.config, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("成功", "识别API配置已保存！")
        except Exception as e:
            messagebox.showerror("保存失败", f"保存配置文件时出错: {str(e)}")
    
    def save_generation_config(self):
        """保存生成API配置"""
        # 获取配置信息
        config = {
            "url": self.generation_url_entry.get().strip(),
            "api_key": self.generation_key_entry.get().strip(),
            "channel": self.generation_channel_var.get(),
            "model": self.generation_model_entry.get().strip() or self.generation_model_var.get()
        }
        
        # 验证配置
        if not config["url"]:
            messagebox.showwarning("警告", "请输入API服务器地址！")
            return
        
        if not config["api_key"]:
            messagebox.showwarning("警告", "请输入API密钥！")
            return
        
        # 更新配置
        self.app.config["generation_api"] = config
        
        # 保存到文件
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.app.config, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("成功", "生成API配置已保存！")
        except Exception as e:
            messagebox.showerror("保存失败", f"保存配置文件时出错: {str(e)}")
    
    def test_character_api(self):
        """测试人设API连接"""
        # 获取当前配置
        url = self.character_url_entry.entry.get()
        api_key = self.character_key_entry.entry.get()
        model = self.character_model_entry.entry.get() or self.character_model_var.get()
        
        if not url or not api_key or not model:
            messagebox.showwarning("提示", "请填写完整的API配置信息！")
            return
        
        # 创建API测试器
        api_tester = APITester(url, api_key, model)
        
        # 在后台线程中测试API
        def test_in_thread():
            try:
                # 测试API连接
                result = api_tester.test_character_api()
                
                # 更新UI
                self.app.after(0, lambda: messagebox.showinfo("成功", result))
                    
            except Exception as e:
                error_msg = handle_api_error(e, "人设API")
                self.app.after(0, lambda: messagebox.showerror("错误", error_msg))
        
        # 启动线程
        threading.Thread(target=test_in_thread, daemon=True).start()
    
    def test_recognition_api(self):
        """测试识别API连接"""
        # 获取当前配置
        url = self.recognition_url_entry.entry.get()
        api_key = self.recognition_key_entry.entry.get()
        model = self.recognition_model_entry.entry.get() or self.recognition_model_var.get()
        
        if not url or not api_key or not model:
            messagebox.showwarning("提示", "请填写完整的API配置信息！")
            return
        
        # 创建API测试器
        api_tester = APITester(url, api_key, model)
        
        # 在后台线程中测试API
        def test_in_thread():
            try:
                # 测试API连接
                result = api_tester.test_recognition_api()
                
                # 更新UI
                self.app.after(0, lambda: messagebox.showinfo("成功", result))
                    
            except Exception as e:
                error_msg = handle_api_error(e, "识别API")
                self.app.after(0, lambda: messagebox.showerror("错误", error_msg))
        
        # 启动线程
        threading.Thread(target=test_in_thread, daemon=True).start()
    
    def test_generation_api(self):
        """测试生成API连接"""
        # 获取当前配置
        url = self.generation_url_entry.entry.get()
        api_key = self.generation_key_entry.entry.get()
        model = self.generation_model_entry.entry.get() or self.generation_model_var.get()
        
        if not url or not api_key or not model:
            messagebox.showwarning("提示", "请填写完整的API配置信息！")
            return
        
        # 创建API测试器
        api_tester = APITester(url, api_key, model)
        
        # 在后台线程中测试API
        def test_in_thread():
            try:
                # 测试API连接
                result = api_tester.test_generation_api()
                
                # 更新UI
                self.app.after(0, lambda: messagebox.showinfo("成功", result))
                    
            except Exception as e:
                error_msg = handle_api_error(e, "生成API")
                self.app.after(0, lambda: messagebox.showerror("错误", error_msg))
        
        # 启动线程
        threading.Thread(target=test_in_thread, daemon=True).start()
    
    def reset_character_config(self):
        """重置人设API配置"""
        # 重置渠道选择
        self.character_channel_var.set(list(self.character_channels.keys())[0])
        self.on_character_channel_changed()
        
        # 重置API密钥
        self.character_key_entry.set("")
        
        # 重置模型选择
        channel = self.character_channel_var.get()
        self.character_model_var.set(self.character_channels[channel][0])
        self.character_model_entry.set("")
        
        messagebox.showinfo("提示", "人设API配置已重置！")
    
    def reset_recognition_config(self):
        """重置识别API配置"""
        # 重置渠道选择
        self.recognition_channel_var.set(list(self.recognition_channels.keys())[0])
        self.update_recognition_channel(list(self.recognition_channels.keys())[0])
        
        # 重置API密钥
        self.recognition_key_entry.set("")
        
        # 重置模型选择
        channel = self.recognition_channel_var.get()
        self.recognition_model_var.set(self.recognition_channels[channel][0])
        self.recognition_model_entry.set("")
        
        messagebox.showinfo("提示", "识别API配置已重置！")
    
    def reset_generation_config(self):
        """重置生成API配置"""
        # 重置API密钥
        self.generation_key_entry.set("")
        
        # 重置API地址为默认值
        if "硅基流动" in self.api_base_urls:
            self.generation_url_entry.set(self.api_base_urls["硅基流动"])
        else:
            self.generation_url_entry.set("")
        
        # 重置模型选择
        self.generation_model_var.set(self.generation_channels["硅基流动"][0])
        self.generation_model_entry.set("")
        
        messagebox.showinfo("提示", "生成API配置已重置！")
    
    def load_config(self):
        """加载配置"""
        try:
            # 获取配置文件路径
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
            
            # 如果配置文件存在，则加载配置
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    self.app.config = json.load(f)
                
                # 更新人设API配置界面
                character_config = self.app.config.get("character_api", {})
                if character_config:
                    self.character_url_entry.set(character_config.get("url", ""))
                    self.character_key_entry.set(character_config.get("api_key", ""))
                    
                    channel = character_config.get("channel")
                    if channel in self.character_channels:
                        self.character_channel_var.set(channel)
                        self.on_character_channel_changed()
                    
                    model = character_config.get("model", "")
                    if channel in self.character_channels and model in self.character_channels[channel]:
                        self.character_model_var.set(model)
                    else:
                        self.character_model_entry.set(model)
                
                # 更新识别API配置界面
                recognition_config = self.app.config.get("recognition_api", {})
                if recognition_config:
                    self.recognition_url_entry.set(recognition_config.get("url", ""))
                    self.recognition_key_entry.set(recognition_config.get("api_key", ""))
                    
                    channel = recognition_config.get("channel")
                    if channel in self.recognition_channels:
                        self.recognition_channel_var.set(channel)
                        self.update_recognition_channel(channel)
                    
                    model = recognition_config.get("model", "")
                    if channel in self.recognition_channels and model in self.recognition_channels[channel]:
                        self.recognition_model_var.set(model)
                    else:
                        self.recognition_model_entry.set(model)
                
                # 更新生成API配置界面
                generation_config = self.app.config.get("generation_api", {})
                if generation_config:
                    self.generation_url_entry.set(generation_config.get("url", ""))
                    self.generation_key_entry.set(generation_config.get("api_key", ""))
                    
                    channel = generation_config.get("channel")
                    if channel in self.generation_channels:
                        self.generation_channel_var.set(channel)
                        self.update_generation_channel(channel)
                    
                    model = generation_config.get("model", "")
                    if channel in self.generation_channels and model in self.generation_channels[channel]:
                        self.generation_model_var.set(model)
                    else:
                        self.generation_model_entry.set(model)
            
        except Exception as e:
            messagebox.showerror("加载失败", f"加载配置文件时出错: {str(e)}")
    
    def save_all_configs(self):
        """保存所有API配置"""
        # 获取所有配置信息
        character_config = {
            "url": self.character_url_entry.get().strip(),
            "api_key": self.character_key_entry.get().strip(),
            "channel": self.character_channel_var.get(),
            "model": self.character_model_entry.get().strip() or self.character_model_var.get()
        }
        
        recognition_config = {
            "url": self.recognition_url_entry.get().strip(),
            "api_key": self.recognition_key_entry.get().strip(),
            "channel": self.recognition_channel_var.get(),
            "model": self.recognition_model_entry.get().strip() or self.recognition_model_var.get()
        }
        
        generation_config = {
            "url": self.generation_url_entry.get().strip(),
            "api_key": self.generation_key_entry.get().strip(),
            "channel": self.generation_channel_var.get(),
            "model": self.generation_model_entry.get().strip() or self.generation_model_var.get()
        }
        
        # 验证配置
        missing_configs = []
        
        if not character_config["url"] or not character_config["api_key"]:
            missing_configs.append("人设API")
        
        if not recognition_config["url"] or not recognition_config["api_key"]:
            missing_configs.append("识别API")
        
        if not generation_config["url"] or not generation_config["api_key"]:
            missing_configs.append("生成API")
        
        if missing_configs:
            messagebox.showwarning(
                "警告",
                f"以下API配置信息不完整：\n{', '.join(missing_configs)}\n\n请补充完整后再保存！"
            )
            return
        
        # 更新配置
        self.app.config.update({
            "character_api": character_config,
            "recognition_api": recognition_config,
            "generation_api": generation_config
        })
        
        # 保存到文件
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.app.config, f, ensure_ascii=False, indent=4)
            
            messagebox.showinfo("成功", "所有API配置已保存！")
            
        except Exception as e:
            messagebox.showerror("保存失败", f"保存配置文件时出错: {str(e)}")

    def open_api_key_website(self, channel):
        """打开对应渠道的API密钥申请网站"""
        if channel in self.api_key_websites:
            import webbrowser
            webbrowser.open(self.api_key_websites[channel])
        else:
            messagebox.showinfo("提示", "该渠道暂无API密钥申请网站")

    def update_button_colors(self, event=None):
        """更新按钮颜色以适应主题变化"""
        # 直接使用 Theme 类中定义的文本颜色
        # Theme.TEXT_PRIMARY 是一个元组 (light_mode_color, dark_mode_color)
        # CustomTkinter 会自动根据当前主题选择正确的颜色
        text_color = Theme.TEXT_PRIMARY
        
        print(f"Using Theme.TEXT_PRIMARY: {text_color}")
        
        # 更新所有灰色按钮的文字颜色
        # 人设API页面
        self.character_apply_key_button.configure(text_color=text_color)
        self.character_reset_button.configure(text_color=text_color)
        
        # 识别API页面
        self.recognition_apply_key_button.configure(text_color=text_color)
        self.recognition_reset_button.configure(text_color=text_color)
        
        # 生成API页面
        self.generation_apply_key_button.configure(text_color=text_color)
        self.generation_reset_button.configure(text_color=text_color)
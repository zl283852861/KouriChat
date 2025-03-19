import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
import sys
import webbrowser

# 导入配置模块
from core.config import APIConfig
from core.error_handler import handle_api_error

# 导入API测试模块
from api.tester import APITester

# 导入自定义组件
from widgets.scrollable_text_box import ScrollableTextBox
from widgets.labeled_entry import LabeledEntry
from widgets.icon_button import IconButton

class KouriChatApp(ctk.CTk):
    """Kouri Chat 应用程序主类"""
    
    def __init__(self):
        super().__init__()
        
        # 设置窗口属性
        self.title("Kouri Chat 工具箱 V11.0")
        self.geometry("1000x700")
        self.minsize(800, 600)  # 设置最小窗口大小
        
        # 设置默认字体 - 使用Arial Unicode MS
        self.default_font = ("Arial Unicode MS", 12)
        self.title_font = ("Arial Unicode MS", 16, "bold")
        
        # 设置默认按钮颜色
        ctk.set_default_color_theme("blue")  # 先设置默认主题
        self.button_color = "#eea2a4"  # 粉色按钮
        self.button_hover_color = "#e58a8c"  # 粉色按钮悬停颜色
        self.purple_color = "#9370DB"  # 更浅的紫色 (Medium Purple)
        self.purple_hover_color = "#8A5DC8"  # 紫色悬停颜色
        
        # 加载配置
        self.config = APIConfig.read_config()
        
        # 设置主题
        self.current_theme = self.config.get("theme", "system")
        self.apply_theme()
        
        # 创建主框架
        self.setup_main_layout()
        
        # 初始化页面内容
        self.setup_character_page()
        self.setup_api_config_page()
        self.setup_image_page()
        self.setup_help_page()
        
        # 默认显示人设页面
        self.show_character_page()
        
        # 初始化生成的人设内容
        self.generated_profile = None
    
    def setup_main_layout(self):
        """设置主布局"""
        # 配置网格布局
        self.grid_columnconfigure(1, weight=1)  # 内容区域可扩展
        self.grid_rowconfigure(0, weight=1)  # 行可扩展
        
        # 创建侧边栏
        self.setup_sidebar()
        
        # 创建内容区域
        self.setup_content_area()
    
    def setup_sidebar(self):
        """设置侧边栏"""
        # 创建侧边栏框架
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
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
            command=self.show_character_page,
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
            command=self.show_api_config_page,
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
            command=self.show_image_page,
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
            command=self.show_help_page,
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
        self.appearance_mode_switch = ctk.CTkSwitch(
            self.sidebar_frame,
            text="切换模式",
            font=ctk.CTkFont(family="Arial Unicode MS", size=12),
            command=self.toggle_theme,
            text_color=("black", "white"),
            progress_color=("gray70", "gray30")
        )
        self.appearance_mode_switch.grid(row=7, column=0, padx=20, pady=(10, 10), sticky="w")
        
        # 根据当前主题设置开关状态
        if self.current_theme == "dark":
            self.appearance_mode_switch.select()
        else:
            self.appearance_mode_switch.deselect()
    
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
    
    def setup_character_page(self):
        """设置人设页面内容"""
        # 页面标题
        title_label = ctk.CTkLabel(
            self.character_frame, 
            text="角色人设生成", 
            font=self.title_font
        )
        title_label.pack(pady=(20, 20))
        
        # 创建主内容框架
        main_frame = ctk.CTkFrame(self.character_frame)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 配置网格布局
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # 左侧输入区域
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # 角色描述标签
        desc_label = ctk.CTkLabel(
            input_frame, 
            text="角色描述:", 
            font=self.default_font
        )
        desc_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # 角色描述输入框
        self.character_desc_text = ctk.CTkTextbox(
            input_frame, 
            height=100, 
            font=self.default_font,
            wrap="word"
        )
        self.character_desc_text.pack(fill="x", padx=10, pady=5)
        
        # 生成按钮
        generate_button = ctk.CTkButton(
            input_frame, 
            text="生成人设", 
            command=self.generate_character,
            font=self.default_font,
            fg_color=self.button_color,
            hover_color=self.button_hover_color
        )
        generate_button.pack(padx=10, pady=10)
        
        # 润色要求标签
        polish_label = ctk.CTkLabel(
            input_frame, 
            text="润色要求:", 
            font=self.default_font
        )
        polish_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # 润色要求输入框
        self.polish_desc_text = ctk.CTkTextbox(
            input_frame, 
            height=100, 
            font=self.default_font,
            wrap="word"
        )
        self.polish_desc_text.pack(fill="x", padx=10, pady=5)
        
        # 润色按钮
        polish_button = ctk.CTkButton(
            input_frame, 
            text="润色人设", 
            command=self.polish_character,
            font=self.default_font,
            fg_color=self.button_color,
            hover_color=self.button_hover_color
        )
        polish_button.pack(padx=10, pady=10)
        
        # 导入/导出按钮框架
        io_frame = ctk.CTkFrame(input_frame)
        io_frame.pack(fill="x", padx=10, pady=10)
        
        # 配置网格布局，使按钮均匀分布
        io_frame.grid_columnconfigure(0, weight=1)
        io_frame.grid_columnconfigure(1, weight=1)
        io_frame.grid_columnconfigure(2, weight=1)
        
        # 导入按钮
        import_button = ctk.CTkButton(
            io_frame, 
            text="导入人设", 
            command=self.import_profile,
            font=self.default_font,
            width=100,
            fg_color=self.button_color,
            hover_color=self.button_hover_color
        )
        import_button.grid(row=0, column=0, padx=5, pady=5)
        
        # 导出按钮
        export_button = ctk.CTkButton(
            io_frame, 
            text="导出人设", 
            command=self.export_profile,
            font=self.default_font,
            width=100,
            fg_color=self.button_color,
            hover_color=self.button_hover_color
        )
        export_button.grid(row=0, column=1, padx=5, pady=5)
        
        # 清空按钮
        clear_button = ctk.CTkButton(
            io_frame, 
            text="清空", 
            command=self.clear_character_inputs,
            font=self.default_font,
            width=100,
            fg_color=self.button_color,
            hover_color=self.button_hover_color
        )
        clear_button.grid(row=0, column=2, padx=5, pady=5)
        
        # 右侧结果区域
        result_frame = ctk.CTkFrame(main_frame)
        result_frame.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")
        
        # 结果标签
        result_label = ctk.CTkLabel(
            result_frame, 
            text="生成结果:", 
            font=self.default_font
        )
        result_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # 结果文本框
        self.character_result_text = ScrollableTextBox(result_frame)
        self.character_result_text.pack(fill="both", expand=True, padx=10, pady=10)
    
    def setup_api_config_page(self):
        """设置API配置页面内容"""
        # 页面标题
        title_label = ctk.CTkLabel(
            self.api_config_frame, 
            text="API配置", 
            font=self.title_font
        )
        title_label.pack(pady=(20, 20))
        
        # 创建选项卡控件
        self.api_tabview = ctk.CTkTabview(self.api_config_frame)
        self.api_tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 添加选项卡
        self.api_tabview.add("人设API")
        self.api_tabview.add("图片识别API")
        self.api_tabview.add("图片生成API")
        
        # 设置各个选项卡的内容
        self.setup_character_api_tab(self.api_tabview.tab("人设API"))
        self.setup_recognition_api_tab(self.api_tabview.tab("图片识别API"))
        self.setup_generation_api_tab(self.api_tabview.tab("图片生成API"))
        
        # 底部按钮框架
        button_frame = ctk.CTkFrame(self.api_config_frame)
        button_frame.pack(pady=20)
        
        # 保存所有配置按钮
        save_all_button = ctk.CTkButton(
            button_frame, 
            text="保存所有配置", 
            command=self.save_all_configs,
            font=self.default_font,
            fg_color="#c5708b",  # 深粉红色
            hover_color="#b5607b"  # 深粉红色悬停颜色
        )
        save_all_button.pack()
    
    def setup_character_api_tab(self, parent_frame):
        """设置人设API选项卡内容"""
        # 读取配置
        config = self.config
        character_config = config.get("character_api", {})
        
        # 渠道选择框架
        channel_frame = ctk.CTkFrame(parent_frame)
        channel_frame.pack(fill="x", padx=10, pady=10)
        
        # 渠道选择标签
        channel_label = ctk.CTkLabel(
            channel_frame, 
            text="选择渠道:", 
            font=self.default_font
        )
        channel_label.pack(side="left", padx=10)
        
        # 渠道选择下拉菜单 - 修改颜色
        self.character_channel_var = ctk.StringVar(value="硅基流动")
        self.character_channel_options = ["硅基流动", "DeepSeek官网", "KouriChat", "自定义"]
        self.character_channel_dropdown = ctk.CTkOptionMenu(
            channel_frame, 
            variable=self.character_channel_var,
            values=self.character_channel_options,
            command=self.update_character_channel,
            font=self.default_font,
            fg_color=self.purple_color,  # 深紫色
            button_color=self.purple_color,  # 深紫色
            button_hover_color=self.purple_hover_color  # 深紫色悬停颜色
        )
        self.character_channel_dropdown.pack(side="left", padx=10)
        
        # 申请密钥按钮 - 修改颜色
        apply_key_button = ctk.CTkButton(
            channel_frame,
            text="申请密钥",
            command=self.apply_character_key,
            font=self.default_font,
            fg_color=self.purple_color,  # 深紫色
            hover_color=self.purple_hover_color  # 深紫色悬停颜色
        )
        apply_key_button.pack(side="left", padx=10)
        
        # URL输入框 - 移除font参数
        url_frame = LabeledEntry(
            parent_frame, 
            label_text="URL地址:"
        )
        url_frame.pack(fill="x", padx=10, pady=10)
        
        # 设置标签字体
        url_frame.label.configure(font=self.default_font)
        # 设置输入框字体
        url_frame.entry.configure(font=self.default_font)
        
        self.character_url_entry = url_frame.entry
        self.character_url_entry.insert(0, character_config.get("url", "https://api.siliconflow.cn/"))
        
        # API密钥输入框 - 移除font参数
        key_frame = LabeledEntry(
            parent_frame, 
            label_text="API密钥:"
        )
        key_frame.pack(fill="x", padx=10, pady=10)
        
        # 设置标签字体
        key_frame.label.configure(font=self.default_font)
        # 设置输入框字体
        key_frame.entry.configure(font=self.default_font)
        
        self.character_key_entry = key_frame.entry
        self.character_key_entry.insert(0, character_config.get("api_key", ""))
        
        # 模型选择框架
        model_frame = ctk.CTkFrame(parent_frame)
        model_frame.pack(fill="x", padx=10, pady=10)
        
        # 模型选择标签
        model_label = ctk.CTkLabel(
            model_frame, 
            text="模型名称:", 
            font=self.default_font
        )
        model_label.pack(side="left", padx=10)
        
        # 模型选择下拉菜单 - 修改颜色
        self.character_model_var = ctk.StringVar(value="deepseek-ai/DeepSeek-V3")
        self.character_model_options = {
            "硅基流动": ["deepseek-ai/DeepSeek-V3", "自定义"],
            "DeepSeek官网": ["deepseek-chat", "deepseek-reasoner", "自定义"],
            "KouriChat": ["kourichat-v3", "kourichat-r1", "自定义"],
            "自定义": ["自定义"]
        }
        self.character_model_dropdown = ctk.CTkOptionMenu(
            model_frame, 
            variable=self.character_model_var,
            values=self.character_model_options["硅基流动"],
            command=self.update_character_model,
            font=self.default_font,
            width=200,
            fg_color=self.purple_color,  # 深紫色
            button_color=self.purple_color,  # 深紫色
            button_hover_color=self.purple_hover_color  # 深紫色悬停颜色
        )
        self.character_model_dropdown.pack(side="left", padx=10)
        
        # 模型输入框
        self.character_model_entry = ctk.CTkEntry(
            model_frame,
            font=self.default_font,
            width=200,
            state="disabled"
        )
        self.character_model_entry.pack(side="left", padx=10)
        
        # 测试按钮 - 移动到模型名称这一行，并缩小
        test_button = ctk.CTkButton(
            model_frame,
            text="测试",
            command=self.test_character_api,
            font=self.default_font,
            width=80,  # 缩小宽度
            fg_color=self.button_color,
            hover_color=self.button_hover_color
        )
        test_button.pack(side="left", padx=10)
        
        # 保存按钮框架
        save_frame = ctk.CTkFrame(parent_frame)
        save_frame.pack(fill="x", padx=10, pady=10)
        
        # 保存按钮 - 居中
        save_button = ctk.CTkButton(
            save_frame,
            text="保存配置",
            command=self.save_character_config,
            font=self.default_font,
            width=150,
            fg_color=self.button_color,
            hover_color=self.button_hover_color
        )
        save_button.pack(pady=10, padx=20, anchor="center")
    
    def setup_recognition_api_tab(self, parent_frame):
        """设置图片识别API选项卡内容"""
        # 读取配置
        config = self.config
        recognition_config = config.get("recognition_api", {})
        
        # 渠道选择框架
        channel_frame = ctk.CTkFrame(parent_frame)
        channel_frame.pack(fill="x", padx=10, pady=10)
        
        # 渠道选择标签
        channel_label = ctk.CTkLabel(
            channel_frame, 
            text="选择渠道:", 
            font=self.default_font
        )
        channel_label.pack(side="left", padx=(10, 5))
        
        # 渠道选择下拉菜单
        self.recognition_channel_var = ctk.StringVar()
        self.recognition_channel_options = ["硅基流动", "月之暗面", "自定义"]  # 定义选项变量
        
        # 根据当前配置设置默认选项
        current_url = recognition_config.get("url", config.get("real_server_base_url", "https://api.siliconflow.cn/"))
        
        if current_url == "https://api.siliconflow.cn/":
            self.recognition_channel_var.set(self.recognition_channel_options[0])
        elif current_url == "https://api.moonshot.cn":
            self.recognition_channel_var.set(self.recognition_channel_options[1])
        else:
            self.recognition_channel_var.set(self.recognition_channel_options[2])  # 自定义
        
        channel_dropdown = ctk.CTkOptionMenu(
            channel_frame, 
            variable=self.recognition_channel_var,
            values=self.recognition_channel_options,  # 使用定义的选项变量
            command=self.update_recognition_channel,
            font=self.default_font,
            fg_color=self.purple_color,  # 深紫色
            button_color=self.purple_color,  # 深紫色
            button_hover_color=self.purple_hover_color  # 深紫色悬停颜色
        )
        channel_dropdown.pack(side="left", padx=5)
        
        # 申请密钥按钮 - 修改颜色
        apply_key_button = ctk.CTkButton(
            channel_frame,
            text="申请密钥",
            command=self.apply_recognition_key,
            font=self.default_font,
            fg_color=self.purple_color,  # 深紫色
            hover_color=self.purple_hover_color  # 深紫色悬停颜色
        )
        apply_key_button.pack(side="left", padx=20)
        
        # API配置框架
        api_config_frame = ctk.CTkFrame(parent_frame)
        api_config_frame.pack(fill="x", padx=10, pady=10)
        
        # URL地址
        url_label = ctk.CTkLabel(
            api_config_frame, 
            text="URL地址:", 
            font=self.default_font
        )
        url_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.recognition_url_entry = ctk.CTkEntry(
            api_config_frame, 
            width=400, 
            font=self.default_font
        )
        self.recognition_url_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.recognition_url_entry.insert(0, recognition_config.get("url", config.get("real_server_base_url", "https://api.siliconflow.cn/")))
        
        # API密钥
        key_label = ctk.CTkLabel(
            api_config_frame, 
            text="API密钥:", 
            font=self.default_font
        )
        key_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        
        self.recognition_key_entry = ctk.CTkEntry(
            api_config_frame, 
            width=400, 
            font=self.default_font,
            show="*"  # 密码显示为星号
        )
        self.recognition_key_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self.recognition_key_entry.insert(0, recognition_config.get("api_key", config.get("api_key", "")))
        
        # 模型名称
        model_label = ctk.CTkLabel(
            api_config_frame, 
            text="模型名称:", 
            font=self.default_font
        )
        model_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        
        # 模型选择框架
        model_frame = ctk.CTkFrame(api_config_frame)
        model_frame.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        
        # 模型选择下拉菜单
        self.recognition_model_var = ctk.StringVar()
        self.recognition_model_options = {
            "硅基流动": ["Qwen/Qwen2-VL-72B-Instruct", "自定义"],
            "月之暗面": ["moonshot-v1-8k-vision-preview", "自定义"],
            "自定义": ["自定义"]
        }
        
        # 根据当前渠道设置模型选项
        current_channel = self.recognition_channel_var.get()
        model_options = self.recognition_model_options.get(current_channel, ["自定义"])
        
        # 设置当前模型
        current_model = recognition_config.get("model", config.get("model", "deepseek-ai/DeepSeek-V3"))
        if current_model in model_options:
            self.recognition_model_var.set(current_model)
        else:
            self.recognition_model_var.set("自定义")
        
        self.recognition_model_dropdown = ctk.CTkOptionMenu(
            model_frame, 
            variable=self.recognition_model_var,
            values=self.recognition_model_options["硅基流动"],
            command=self.update_recognition_model,
            font=self.default_font,
            width=200,
            fg_color=self.purple_color,  # 深紫色
            button_color=self.purple_color,  # 深紫色
            button_hover_color=self.purple_hover_color  # 深紫色悬停颜色
        )
        self.recognition_model_dropdown.pack(side="left", padx=5)
        
        # 自定义模型输入框
        self.recognition_model_entry = ctk.CTkEntry(
            model_frame, 
            width=200, 
            font=self.default_font
        )
        self.recognition_model_entry.pack(side="left", padx=5)
        if self.recognition_model_var.get() == "自定义":
            self.recognition_model_entry.insert(0, current_model)
        else:
            self.recognition_model_entry.configure(state="disabled")
        
        # 按钮框架
        button_frame = ctk.CTkFrame(parent_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # 配置网格布局，使按钮均匀分布
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        # 保存按钮
        save_button = ctk.CTkButton(
            button_frame,
            text="保存配置",
            command=self.save_recognition_config,
            font=self.default_font,
            width=150,
            fg_color=self.button_color,
            hover_color=self.button_hover_color
        )
        save_button.grid(row=0, column=0, padx=10, pady=10)
        
        # 测试按钮 - 移动到模型名称这一行，并缩小
        test_button = ctk.CTkButton(
            button_frame,
            text="测试",
            command=self.test_recognition_api,
            font=self.default_font,
            width=80,  # 缩小宽度
            fg_color=self.button_color,
            hover_color=self.button_hover_color
        )
        test_button.grid(row=0, column=1, padx=10, pady=10)
    
    def setup_generation_api_tab(self, parent_frame):
        """设置图片生成API选项卡内容"""
        # 读取配置
        config = self.config
        generation_config = config.get("generation_api", {})
        
        # 渠道选择框架
        channel_frame = ctk.CTkFrame(parent_frame)
        channel_frame.pack(fill="x", padx=10, pady=10)
        
        # 渠道选择标签
        channel_label = ctk.CTkLabel(
            channel_frame, 
            text="选择渠道:", 
            font=self.default_font
        )
        channel_label.pack(side="left", padx=(10, 5))
        
        # 渠道选择下拉菜单 - 修改颜色
        self.generation_channel_var = ctk.StringVar()
        generation_channels = ["硅基流动", "自定义"]
        
        # 根据当前配置设置默认选项
        current_url = generation_config.get("url", config.get("real_server_base_url", "https://api.siliconflow.cn/"))
        
        if current_url == "https://api.siliconflow.cn/":
            self.generation_channel_var.set(generation_channels[0])
        else:
            self.generation_channel_var.set(generation_channels[1])  # 自定义
        
        channel_dropdown = ctk.CTkOptionMenu(
            channel_frame, 
            variable=self.generation_channel_var,
            values=generation_channels,
            command=self.update_generation_channel,
            font=self.default_font,
            width=150,
            fg_color=self.purple_color,  # 更浅的紫色
            button_color=self.purple_color,  # 更浅的紫色
            button_hover_color=self.purple_hover_color  # 紫色悬停颜色
        )
        channel_dropdown.pack(side="left", padx=5)
        
        # 申请密钥按钮 - 修改颜色
        apply_key_button = ctk.CTkButton(
            channel_frame,
            text="申请密钥",
            command=self.apply_generation_key,
            font=self.default_font,
            width=100,
            fg_color=self.purple_color,  # 更浅的紫色
            hover_color=self.purple_hover_color  # 紫色悬停颜色
        )
        apply_key_button.pack(side="left", padx=20)
        
        # API配置框架
        api_config_frame = ctk.CTkFrame(parent_frame)
        api_config_frame.pack(fill="x", padx=10, pady=10)
        
        # URL地址
        url_label = ctk.CTkLabel(
            api_config_frame, 
            text="URL地址:", 
            font=self.default_font
        )
        url_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.generation_url_entry = ctk.CTkEntry(
            api_config_frame, 
            width=400, 
            font=self.default_font
        )
        self.generation_url_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.generation_url_entry.insert(0, generation_config.get("url", config.get("real_server_base_url", "https://api.siliconflow.cn/")))
        
        # API密钥
        key_label = ctk.CTkLabel(
            api_config_frame, 
            text="API密钥:", 
            font=self.default_font
        )
        key_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        
        self.generation_key_entry = ctk.CTkEntry(
            api_config_frame, 
            width=400, 
            font=self.default_font,
            show="*"  # 密码显示为星号
        )
        self.generation_key_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self.generation_key_entry.insert(0, generation_config.get("api_key", config.get("api_key", "")))
        
        # 模型名称
        model_label = ctk.CTkLabel(
            api_config_frame, 
            text="模型名称:", 
            font=self.default_font
        )
        model_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        
        # 模型选择框架
        model_frame = ctk.CTkFrame(api_config_frame)
        model_frame.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        
        # 模型选择下拉菜单 - 修改颜色
        self.generation_model_var = ctk.StringVar()
        self.generation_model_options = {
            "硅基流动": ["Kwai-Kolors/Kolors", "自定义"],
            "自定义": ["自定义"]
        }
        
        # 根据当前渠道设置模型选项
        current_channel = self.generation_channel_var.get()
        model_options = self.generation_model_options.get(current_channel, ["自定义"])
        
        # 设置当前模型
        current_model = generation_config.get("model", config.get("model", "deepseek-ai/DeepSeek-V3"))
        if current_model in model_options:
            self.generation_model_var.set(current_model)
        else:
            self.generation_model_var.set("自定义")
        
        self.generation_model_dropdown = ctk.CTkOptionMenu(
            model_frame, 
            variable=self.generation_model_var,
            values=model_options,
            command=self.update_generation_model,
            font=self.default_font,
            width=200,
            fg_color=self.purple_color,  # 更浅的紫色
            button_color=self.purple_color,  # 更浅的紫色
            button_hover_color=self.purple_hover_color  # 紫色悬停颜色
        )
        self.generation_model_dropdown.pack(side="left", padx=5)
        
        # 自定义模型输入框
        self.generation_model_entry = ctk.CTkEntry(
            model_frame, 
            width=200, 
            font=self.default_font
        )
        self.generation_model_entry.pack(side="left", padx=5)
        if self.generation_model_var.get() == "自定义":
            self.generation_model_entry.insert(0, current_model)
        else:
            self.generation_model_entry.configure(state="disabled")
        
        # 图片尺寸配置
        size_label = ctk.CTkLabel(
            api_config_frame, 
            text="默认图片尺寸:", 
            font=self.default_font
        )
        size_label.grid(row=3, column=0, padx=10, pady=10, sticky="w")
        
        # 图片尺寸下拉菜单
        self.generation_size_var = ctk.StringVar()
        size_options = ["1024x1024", "960x1280", "768x1024", "720x1440", "720x1280", "512x512"]
        
        # 设置当前尺寸
        current_size = generation_config.get("size", config.get("image_config", {}).get("generate_size", "1024x1024"))
        if current_size in size_options:
            self.generation_size_var.set(current_size)
        else:
            self.generation_size_var.set("1024x1024")
        
        size_dropdown = ctk.CTkOptionMenu(
            api_config_frame, 
            variable=self.generation_size_var,
            values=size_options,
            font=self.default_font,
            width=200,
            fg_color="#c5708b",  # 深粉红色
            button_color="#c5708b",  # 深粉红色
            button_hover_color="#b5607b"  # 深粉红色悬停颜色
        )
        size_dropdown.grid(row=3, column=1, padx=10, pady=10, sticky="w")
        
        # 按钮框架
        button_frame = ctk.CTkFrame(parent_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # 配置网格布局，使按钮均匀分布
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        # 保存按钮
        save_button = ctk.CTkButton(
            button_frame,
            text="保存配置",
            command=self.save_generation_config,
            font=self.default_font,
            width=150,
            fg_color=self.button_color,
            hover_color=self.button_hover_color
        )
        save_button.grid(row=0, column=0, padx=10, pady=10)
        
        # 测试按钮
        test_button = ctk.CTkButton(
            button_frame,
            text="测试",
            command=self.test_generation_api,
            font=self.default_font,
            width=150,
            fg_color=self.button_color,
            hover_color=self.button_hover_color
        )
        test_button.grid(row=0, column=1, padx=10, pady=10)
    
    def setup_image_page(self):
        """设置图片页面内容"""
        # 页面标题
        title_label = ctk.CTkLabel(
            self.image_frame, 
            text="图片功能", 
            font=self.title_font
        )
        title_label.pack(pady=(20, 20))
        
        # 创建选项卡控件
        self.image_tabview = ctk.CTkTabview(self.image_frame)
        self.image_tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 添加选项卡
        self.image_tabview.add("图片识别")
        self.image_tabview.add("图片生成")
        
        # 设置各个选项卡的内容
        self.setup_image_recognition_tab(self.image_tabview.tab("图片识别"))
        self.setup_image_generation_tab(self.image_tabview.tab("图片生成"))
    
    def setup_image_recognition_tab(self, parent_frame):
        """设置图片识别选项卡内容"""
        # 标题
        title_label = ctk.CTkLabel(
            parent_frame, 
            text="图片识别", 
            font=ctk.CTkFont(family="黑体", size=16, weight="bold")
        )
        title_label.pack(pady=(10, 20))
        
        # 上传图片框架
        upload_frame = ctk.CTkFrame(parent_frame)
        upload_frame.pack(fill="x", padx=20, pady=10)
        
        # 上传按钮
        upload_button = ctk.CTkButton(
            upload_frame, 
            text="上传图片", 
            command=self.upload_image_for_recognition,
            font=self.default_font
        )
        upload_button.pack(pady=10)
        
        # 图片预览框架
        preview_frame = ctk.CTkFrame(parent_frame)
        preview_frame.pack(fill="x", padx=20, pady=10)
        
        # 预览标签
        preview_label = ctk.CTkLabel(
            preview_frame, 
            text="图片预览:", 
            font=self.default_font
        )
        preview_label.pack(anchor="w", padx=10, pady=5)
        
        # 图片预览区域
        self.recognition_image_label = ctk.CTkLabel(
            preview_frame, 
            text="请上传图片",
            width=300,
            height=200
        )
        self.recognition_image_label.pack(pady=10)
        
        # 识别结果框架
        result_frame = ctk.CTkFrame(parent_frame)
        result_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 识别结果标签
        result_label = ctk.CTkLabel(
            result_frame, 
            text="识别结果:", 
            font=self.default_font
        )
        result_label.pack(anchor="w", padx=10, pady=5)
        
        # 识别结果文本框
        self.recognition_result_text = ScrollableTextBox(result_frame)
        self.recognition_result_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 复制结果按钮
        copy_button = ctk.CTkButton(
            result_frame, 
            text="复制结果", 
            command=lambda: self.copy_to_clipboard(self.recognition_result_text.get_text()),
            font=self.default_font
        )
        copy_button.pack(pady=10)
    
    def setup_image_generation_tab(self, parent_frame):
        """设置图片生成选项卡内容"""
        # 标题
        title_label = ctk.CTkLabel(
            parent_frame, 
            text="图片生成", 
            font=ctk.CTkFont(family="黑体", size=16, weight="bold")
        )
        title_label.pack(pady=(10, 20))
        
        # 提示词输入框架
        prompt_frame = ctk.CTkFrame(parent_frame)
        prompt_frame.pack(fill="x", padx=20, pady=10)
        
        # 提示词标签
        prompt_label = ctk.CTkLabel(
            prompt_frame, 
            text="提示词:", 
            font=self.default_font
        )
        prompt_label.pack(anchor="w", padx=10, pady=5)
        
        # 提示词文本框
        self.generation_prompt_text = ctk.CTkTextbox(
            prompt_frame, 
            height=100, 
            font=self.default_font,
            wrap="word"
        )
        self.generation_prompt_text.pack(fill="x", padx=10, pady=5)
        
        # 图片尺寸选择框架
        size_frame = ctk.CTkFrame(parent_frame)
        size_frame.pack(fill="x", padx=20, pady=10)
        
        # 图片尺寸标签
        size_label = ctk.CTkLabel(
            size_frame, 
            text="图片尺寸:", 
            font=self.default_font
        )
        size_label.pack(side="left", padx=10)
        
        # 图片尺寸下拉菜单
        # 根据硅基流动API文档支持的尺寸
        self.image_size_var = ctk.StringVar()
        
        # 从配置中获取默认尺寸
        config = self.config
        generation_config = config.get("generation_api", {})
        default_size = generation_config.get("size", config.get("image_config", {}).get("generate_size", "1024x1024"))
        self.image_size_var.set(default_size)
        
        size_options = ["1024x1024", "960x1280", "768x1024", "720x1440", "720x1280", "512x512"]
        size_dropdown = ctk.CTkOptionMenu(
            size_frame, 
            variable=self.image_size_var,
            values=size_options,
            font=self.default_font,
            fg_color="#c5708b",  # 深粉红色
            button_color="#c5708b",  # 深粉红色
            button_hover_color="#b5607b"  # 深粉红色悬停颜色
        )
        size_dropdown.pack(side="left", padx=10)
        
        # 生成按钮
        generate_button = ctk.CTkButton(
            parent_frame, 
            text="生成图片", 
            command=self.generate_image,
            font=self.default_font
        )
        generate_button.pack(pady=10)
        
        # 进度条
        self.generation_progress = ctk.CTkProgressBar(parent_frame, width=300)
        self.generation_progress.pack(pady=5)
        self.generation_progress.set(0)  # 初始值为0
        
        # 图片预览框架
        preview_frame = ctk.CTkFrame(parent_frame)
        preview_frame.pack(fill="x", padx=20, pady=10)
        
        # 预览标签
        preview_label = ctk.CTkLabel(
            preview_frame, 
            text="图片预览:", 
            font=self.default_font
        )
        preview_label.pack(anchor="w", padx=10, pady=5)
        
        # 图片预览区域
        self.generation_image_label = ctk.CTkLabel(
            preview_frame, 
            text="生成的图片将显示在这里",
            width=300,
            height=300
        )
        self.generation_image_label.pack(pady=10)
        
        # 保存图片按钮
        self.save_image_button = ctk.CTkButton(
            parent_frame, 
            text="保存图片", 
            command=self.save_generated_image,
            font=self.default_font,
            state="disabled"  # 初始状态为禁用
        )
        self.save_image_button.pack(pady=10)
    
    def update_character_channel(self, selection):
        """根据选择的渠道更新URL和模型下拉菜单"""
        # 更新URL
        if selection == "硅基流动":
            self.character_url_entry.delete(0, "end")
            self.character_url_entry.insert(0, "https://api.siliconflow.cn/")
        elif selection == "DeepSeek官网":
            self.character_url_entry.delete(0, "end")
            self.character_url_entry.insert(0, "https://api.deepseek.com")
        elif selection == "KouriChat":
            self.character_url_entry.delete(0, "end")
            self.character_url_entry.insert(0, "https://api.kourichat.com")
        
        # 更新模型下拉菜单
        model_options = self.character_model_options.get(selection, ["自定义"])
        
        # 重新创建下拉菜单
        self.character_model_dropdown.configure(values=model_options)
        
        # 设置默认模型
        if selection == "硅基流动":
            self.character_model_var.set("deepseek-ai/DeepSeek-V3")
        elif selection == "DeepSeek官网":
            self.character_model_var.set("deepseek-chat")
        elif selection == "KouriChat":
            self.character_model_var.set("kourichat-v3")
        else:
            self.character_model_var.set("自定义")
        
        # 更新模型输入框状态
        self.update_character_model(self.character_model_var.get())
    
    def update_character_model(self, selection):
        """根据选择的模型更新输入框状态"""
        if selection == "自定义":
            self.character_model_entry.configure(state="normal")
            self.character_model_entry.delete(0, "end")
        else:
            self.character_model_entry.delete(0, "end")
            self.character_model_entry.configure(state="disabled")
    
    def apply_character_key(self):
        """打开申请密钥的网页"""
        channel = self.character_channel_var.get()
        if channel == "硅基流动":
            webbrowser.open("https://www.siliconflow.cn/")
        elif channel == "DeepSeek官网":
            webbrowser.open("https://www.deepseek.com/")
        elif channel == "KouriChat":
            webbrowser.open("https://www.kourichat.com/")
        else:
            messagebox.showinfo("提示", "请先选择一个渠道")
    
    def save_character_config(self):
        """保存人设API配置"""
        # 获取当前配置
        config = self.config
        
        # 获取模型名称
        model = self.character_model_var.get()
        if model == "自定义":
            model = self.character_model_entry.get()
        
        # 更新配置
        if "character_api" not in config:
            config["character_api"] = {}
        
        config["character_api"]["url"] = self.character_url_entry.get()
        config["character_api"]["api_key"] = self.character_key_entry.get()
        config["character_api"]["model"] = model
        
        # 保存配置
        APIConfig.save_config(config)
        messagebox.showinfo("保存成功", "人设API配置已保存！")
    
    def test_character_api(self):
        """测试人设API连接"""
        # 先保存配置
        self.save_character_config()
        
        # 获取配置
        config = self.config
        character_config = config.get("character_api", {})
        
        url = character_config.get("url")
        api_key = character_config.get("api_key")
        model = character_config.get("model")
        
        if not url or not api_key or not model:
            messagebox.showwarning("配置错误", "请填写URL地址、API密钥和模型名称！")
            return
        
        try:
            # 创建API测试器
            tester = APITester(url, api_key, model)
            
            # 显示测试中提示
            messagebox.showinfo("测试中", "正在测试API连接，请稍候...")
            
            # 测试API
            response = tester.test_standard_api()
            
            if response.status_code == 200:
                messagebox.showinfo("测试成功", "人设API连接测试成功！")
            else:
                messagebox.showerror("测试失败", f"API返回错误: {response.status_code}\n{response.text}")
        
        except Exception as e:
            error_msg = handle_api_error(e, "人设API")
            messagebox.showerror("测试失败", error_msg)
    
    def update_recognition_channel(self, selection):
        """根据选择的渠道更新URL和模型下拉菜单"""
        # 更新URL
        if selection == "硅基流动":
            self.recognition_url_entry.delete(0, "end")
            self.recognition_url_entry.insert(0, "https://api.siliconflow.cn/")
        elif selection == "DeepSeek官网":
            self.recognition_url_entry.delete(0, "end")
            self.recognition_url_entry.insert(0, "https://api.deepseek.com")
        elif selection == "KouriChat":
            self.recognition_url_entry.delete(0, "end")
            self.recognition_url_entry.insert(0, "https://api.kourichat.com")
        
        # 更新模型下拉菜单
        model_options = self.recognition_model_options.get(selection, ["自定义"])
        
        # 重新创建下拉菜单
        self.recognition_model_dropdown.configure(values=model_options)
        
        # 设置默认模型
        if selection == "硅基流动":
            self.recognition_model_var.set("deepseek-ai/DeepSeek-V3")
        elif selection == "DeepSeek官网":
            self.recognition_model_var.set("deepseek-vision")
        elif selection == "KouriChat":
            self.recognition_model_var.set("kourichat-vision")
        else:
            self.recognition_model_var.set("自定义")
        
        # 更新模型输入框状态
        self.update_recognition_model(self.recognition_model_var.get())
    
    def update_recognition_model(self, selection):
        """根据选择的模型更新输入框状态"""
        if selection == "自定义":
            self.recognition_model_entry.configure(state="normal")
            self.recognition_model_entry.delete(0, "end")
        else:
            self.recognition_model_entry.delete(0, "end")
            self.recognition_model_entry.configure(state="disabled")
    
    def apply_recognition_key(self):
        """打开申请密钥的网页"""
        channel = self.recognition_channel_var.get()
        if channel == "硅基流动":
            webbrowser.open("https://www.siliconflow.cn/")
        elif channel == "DeepSeek官网":
            webbrowser.open("https://www.deepseek.com/")
        elif channel == "KouriChat":
            webbrowser.open("https://www.kourichat.com/")
        else:
            messagebox.showinfo("提示", "请先选择一个渠道")
    
    def save_recognition_config(self):
        """保存图片识别API配置"""
        # 获取当前配置
        config = self.config
        
        # 获取模型名称
        model = self.recognition_model_var.get()
        if model == "自定义":
            model = self.recognition_model_entry.get()
        
        # 更新配置
        if "recognition_api" not in config:
            config["recognition_api"] = {}
        
        config["recognition_api"]["url"] = self.recognition_url_entry.get()
        config["recognition_api"]["api_key"] = self.recognition_key_entry.get()
        config["recognition_api"]["model"] = model
        
        # 保存配置
        APIConfig.save_config(config)
        messagebox.showinfo("保存成功", "图片识别API配置已保存！")
    
    def test_recognition_api(self):
        """测试图片识别API连接"""
        # 先保存配置
        self.save_recognition_config()
        
        # 获取配置
        config = self.config
        recognition_config = config.get("recognition_api", {})
        
        url = recognition_config.get("url")
        api_key = recognition_config.get("api_key")
        model = recognition_config.get("model")
        
        if not url or not api_key or not model:
            messagebox.showwarning("配置错误", "请填写URL地址、API密钥和模型名称！")
            return
        
        try:
            # 创建API测试器
            tester = APITester(url, api_key, model)
            
            # 显示测试中提示
            messagebox.showinfo("测试中", "正在测试API连接，请稍候...")
            
            # 测试API
            response = tester.test_standard_api()
            
            if response.status_code == 200:
                messagebox.showinfo("测试成功", "图片识别API连接测试成功！")
            else:
                messagebox.showerror("测试失败", f"API返回错误: {response.status_code}\n{response.text}")
        
        except Exception as e:
            error_msg = handle_api_error(e, "图片识别API")
            messagebox.showerror("测试失败", error_msg)
    
    def update_generation_channel(self, selection):
        """根据选择的渠道更新URL和模型下拉菜单"""
        # 更新URL
        if selection == "硅基流动":
            self.generation_url_entry.delete(0, "end")
            self.generation_url_entry.insert(0, "https://api.siliconflow.cn/")
        elif selection == "DeepSeek官网":
            self.generation_url_entry.delete(0, "end")
            self.generation_url_entry.insert(0, "https://api.deepseek.com")
        elif selection == "KouriChat":
            self.generation_url_entry.delete(0, "end")
            self.generation_url_entry.insert(0, "https://api.kourichat.com")
        
        # 更新模型下拉菜单
        model_options = self.generation_model_options.get(selection, ["自定义"])
        
        # 重新创建下拉菜单
        self.generation_model_dropdown.configure(values=model_options)
        
        # 设置默认模型
        if selection == "硅基流动":
            self.generation_model_var.set("deepseek-ai/DeepSeek-V3")
        elif selection == "DeepSeek官网":
            self.generation_model_var.set("deepseek-image")
        elif selection == "KouriChat":
            self.generation_model_var.set("kourichat-image")
        else:
            self.generation_model_var.set("自定义")
        
        # 更新模型输入框状态
        self.update_generation_model(self.generation_model_var.get())
    
    def update_generation_model(self, selection):
        """根据选择的模型更新输入框状态"""
        if selection == "自定义":
            self.generation_model_entry.configure(state="normal")
            self.generation_model_entry.delete(0, "end")
        else:
            self.generation_model_entry.delete(0, "end")
            self.generation_model_entry.configure(state="disabled")
    
    def apply_generation_key(self):
        """打开申请密钥的网页"""
        channel = self.generation_channel_var.get()
        if channel == "硅基流动":
            webbrowser.open("https://www.siliconflow.cn/")
        elif channel == "DeepSeek官网":
            webbrowser.open("https://www.deepseek.com/")
        elif channel == "KouriChat":
            webbrowser.open("https://www.kourichat.com/")
        else:
            messagebox.showinfo("提示", "请先选择一个渠道")
    
    def save_generation_config(self):
        """保存图片生成API配置"""
        # 获取当前配置
        config = self.config
        
        # 获取模型名称
        model = self.generation_model_var.get()
        if model == "自定义":
            model = self.generation_model_entry.get()
        
        # 更新配置
        if "generation_api" not in config:
            config["generation_api"] = {}
        
        config["generation_api"]["url"] = self.generation_url_entry.get()
        config["generation_api"]["api_key"] = self.generation_key_entry.get()
        config["generation_api"]["model"] = model
        config["generation_api"]["size"] = self.image_size_var.get()
        
        # 保存配置
        APIConfig.save_config(config)
        messagebox.showinfo("保存成功", "图片生成API配置已保存！")
    
    def test_generation_api(self):
        """测试图片生成API连接"""
        # 先保存配置
        self.save_generation_config()
        
        # 获取配置
        config = self.config
        generation_config = config.get("generation_api", {})
        
        url = generation_config.get("url")
        api_key = generation_config.get("api_key", config.get("api_key"))
        model = generation_config.get("model", config.get("model"))
        
        if not url or not api_key or not model:
            messagebox.showwarning("配置错误", "请填写URL地址、API密钥和模型名称！")
            return
        
        try:
            # 创建API测试器
            tester = APITester(url, api_key, model)
            
            # 显示测试中提示
            messagebox.showinfo("测试中", "正在测试API连接，请稍候...")
            
            # 测试API
            response = tester.test_standard_api()
            
            if response.status_code == 200:
                messagebox.showinfo("测试成功", "图片生成API连接测试成功！")
            else:
                messagebox.showerror("测试失败", f"API返回错误: {response.status_code}\n{response.text}")
        
        except Exception as e:
            error_msg = handle_api_error(e, "图片生成API")
            messagebox.showerror("测试失败", error_msg)
    
    def upload_image_for_recognition(self):
        """上传图片进行识别"""
        # 打开文件选择对话框
        file_path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif")]
        )
        
        if not file_path:
            return
        
        try:
            # 读取图片并显示预览
            from PIL import Image, ImageTk
            image = Image.open(file_path)
            
            # 调整图片大小以适应预览区域
            max_size = 300
            width, height = image.size
            if width > height:
                new_width = max_size
                new_height = int(height * max_size / width)
            else:
                new_height = max_size
                new_width = int(width * max_size / height)
            
            image = image.resize((new_width, new_height), Image.LANCZOS)
            
            # 转换为CTkImage
            ct_image = ctk.CTkImage(light_image=image, dark_image=image, size=(new_width, new_height))
            
            # 更新预览标签
            self.recognition_image_label.configure(image=ct_image, text="")
            self.recognition_image_label.image = ct_image  # 保持引用
            
            # 获取API配置
            config = APIConfig.read_config()
            recognition_config = config.get("recognition_api", {})
            
            url = recognition_config.get("url", config.get("real_server_base_url"))
            api_key = recognition_config.get("api_key", config.get("api_key"))
            model = recognition_config.get("model", config.get("model"))
            
            if not url or not api_key or not model:
                messagebox.showwarning("配置错误", "请先在API配置页面设置图片识别API！")
                return
            
            # 显示加载中提示
            self.recognition_result_text.set_text("正在识别图片，请稍候...")
            self.update()  # 更新UI
            
            # 创建API请求
            tester = APITester(url, api_key, model)
            response = tester.recognize_image(file_path)
            
            # 显示识别结果
            self.recognition_result_text.clear()
            if response and response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    self.recognition_result_text.set_text(content)
                else:
                    self.recognition_result_text.set_text("无法解析识别结果，请检查API响应格式。")
            else:
                self.recognition_result_text.set_text(f"识别失败: {response.text if response else '无响应'}")
        
        except Exception as e:
            error_msg = handle_api_error(e, "图片识别")
            self.recognition_result_text.set_text(f"识别出错: {error_msg}")
    
    def generate_image(self):
        """生成图片"""
        # 获取提示词
        prompt = self.generation_prompt_text.get("1.0", "end-1c").strip()
        if not prompt:
            messagebox.showwarning("提示", "请输入提示词！")
            return
        
        # 获取API配置
        config = APIConfig.read_config()
        generation_config = config.get("generation_api", {})
        
        url = generation_config.get("url", config.get("real_server_base_url"))
        api_key = generation_config.get("api_key", config.get("api_key"))
        model = generation_config.get("model", config.get("model"))
        
        # 获取选择的图片尺寸
        size = self.image_size_var.get()
        
        if not url or not api_key or not model:
            messagebox.showwarning("配置错误", "请先在API配置页面设置图片生成API！")
            return
        
        try:
            # 显示加载中提示
            self.generation_image_label.configure(text="正在生成图片，请稍候...")
            self.generation_image_label.update()
            
            # 设置进度条动画
            self.generation_progress.set(0.1)  # 初始进度
            self.update()
            
            # 创建API请求
            tester = APITester(url, api_key, model)
            
            # 模拟进度更新
            import threading
            def update_progress():
                progress = 0.1
                while progress < 0.95:
                    time.sleep(0.5)
                    progress += 0.05
                    self.generation_progress.set(progress)
                    self.update()
            
            # 启动进度更新线程
            import time
            progress_thread = threading.Thread(target=update_progress)
            progress_thread.daemon = True
            progress_thread.start()
            
            # 发送API请求
            response = tester.generate_image(prompt, size)
            
            # 完成进度条
            self.generation_progress.set(1.0)
            self.update()
            
            if response and response.status_code == 200:
                result = response.json()
                if "data" in result and len(result["data"]) > 0 and "url" in result["data"][0]:
                    image_url = result["data"][0]["url"]
                    
                    # 下载图片
                    import requests
                    import io
                    image_response = requests.get(image_url)
                    if image_response.status_code == 200:
                        # 将图片数据转换为PIL图像
                        from PIL import Image
                        image = Image.open(io.BytesIO(image_response.content))
                        
                        # 保存原始图像用于后续保存
                        self.generated_image = image
                        
                        # 调整图片大小以适应预览区域
                        max_size = 300
                        width, height = image.size
                        if width > height:
                            new_width = max_size
                            new_height = int(height * max_size / width)
                        else:
                            new_height = max_size
                            new_width = int(width * max_size / height)
                        
                        display_image = image.resize((new_width, new_height), Image.LANCZOS)
                        
                        # 转换为CTkImage
                        ct_image = ctk.CTkImage(light_image=display_image, dark_image=display_image, size=(new_width, new_height))
                        
                        # 更新预览标签
                        self.generation_image_label.configure(image=ct_image, text="")
                        self.generation_image_label.image = ct_image  # 保持引用
                        
                        # 启用保存按钮
                        self.save_image_button.configure(state="normal")
                    else:
                        self.generation_image_label.configure(text=f"下载图片失败: {image_response.status_code}")
                else:
                    self.generation_image_label.configure(text="无法解析生成结果，请检查API响应格式。")
            else:
                self.generation_image_label.configure(text=f"生成失败: {response.text if response else '无响应'}")
        
        except Exception as e:
            error_msg = handle_api_error(e, "图片生成")
            self.generation_image_label.configure(text=f"生成出错: {error_msg}")
            self.generation_progress.set(0)  # 重置进度条
    
    def save_generated_image(self):
        """保存生成的图片"""
        if not hasattr(self, 'generated_image'):
            messagebox.showwarning("提示", "没有可保存的图片！")
            return
        
        # 打开文件保存对话框
        file_path = filedialog.asksaveasfilename(
            title="保存图片",
            defaultextension=".png",
            filetypes=[("PNG图片", "*.png"), ("JPEG图片", "*.jpg"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # 保存图片
            self.generated_image.save(file_path)
            messagebox.showinfo("成功", f"图片已保存到: {file_path}")
        except Exception as e:
            messagebox.showerror("保存失败", f"保存图片时出错: {str(e)}")
    
    def copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("提示", "内容已复制到剪贴板")
    
    def change_theme(self, theme_name):
        """切换主题"""
        theme_name = theme_name.lower()
        if theme_name == self.current_theme:
            return
        
        self.current_theme = theme_name
        
        # 更新配置
        self.config["theme"] = theme_name
        APIConfig.save_config(self.config)
        
        # 应用主题
        self.apply_theme()
        
        messagebox.showinfo("主题切换", f"已切换到{theme_name}主题，部分更改可能需要重启应用后生效。")
    
    def apply_theme(self):
        """应用主题"""
        # CustomTkinter 已经内置了主题支持，我们只需要设置外观模式
        if self.current_theme == "light":
            ctk.set_appearance_mode("light")
        elif self.current_theme == "dark":
            ctk.set_appearance_mode("dark")
        else:  # system
            ctk.set_appearance_mode("system")
    
    def show_character_page(self):
        """显示人设页面"""
        self.clear_content_frame()
        self.character_frame.pack(fill="both", expand=True)
        
        # 高亮当前选中的侧边栏按钮
        self.highlight_sidebar_button(self.character_button)
    
    def show_api_config_page(self):
        """显示API配置页面"""
        self.clear_content_frame()
        self.api_config_frame.pack(fill="both", expand=True)
        
        # 高亮当前选中的侧边栏按钮
        self.highlight_sidebar_button(self.api_config_button)
    
    def show_image_page(self):
        """显示图片页面"""
        self.clear_content_frame()
        self.image_frame.pack(fill="both", expand=True)
        
        # 高亮当前选中的侧边栏按钮
        self.highlight_sidebar_button(self.image_button)
    
    def setup_theme_page(self):
        """设置主题页面内容"""
        # 页面标题
        title_label = ctk.CTkLabel(
            self.theme_frame, 
            text="主题设置", 
            font=self.title_font
        )
        title_label.pack(pady=(20, 20))
        
        # 主题选择框架
        theme_frame = ctk.CTkFrame(self.theme_frame)
        theme_frame.pack(pady=20)
        
        # 主题选择标签
        theme_label = ctk.CTkLabel(
            theme_frame, 
            text="选择主题:", 
            font=self.default_font
        )
        theme_label.pack(side="left", padx=10)
        
        # 主题选择下拉菜单
        self.theme_var = ctk.StringVar(value=self.current_theme.capitalize())
        themes = ["Light", "Dark", "System"]
        theme_dropdown = ctk.CTkOptionMenu(
            theme_frame, 
            variable=self.theme_var,
            values=themes,
            command=self.change_theme,
            font=self.default_font
        )
        theme_dropdown.pack(side="left", padx=10)
        
        # 主题预览框架
        preview_frame = ctk.CTkFrame(self.theme_frame)
        preview_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 预览标题
        preview_title = ctk.CTkLabel(
            preview_frame, 
            text="主题预览", 
            font=ctk.CTkFont(family="黑体", size=16, weight="bold")
        )
        preview_title.pack(pady=10)
        
        # 预览内容
        preview_text = ctk.CTkLabel(
            preview_frame, 
            text="这是正文文本示例，用于展示不同主题下的文本显示效果。", 
            font=self.default_font
        )
        preview_text.pack(pady=10)
        
        # 预览按钮
        preview_button = ctk.CTkButton(
            preview_frame, 
            text="示例按钮", 
            font=self.default_font
        )
        preview_button.pack(pady=10)
        
        # 预览输入框
        preview_entry = ctk.CTkEntry(
            preview_frame,
            placeholder_text="示例输入框",
            font=self.default_font,
            width=300
        )
        preview_entry.pack(pady=10)
        
        # 预览复选框
        preview_checkbox = ctk.CTkCheckBox(
            preview_frame,
            text="示例复选框",
            font=self.default_font
        )
        preview_checkbox.pack(pady=10)
    
    def show_theme_page(self):
        """显示主题页面"""
        self.clear_content_frame()
        self.theme_frame.pack(fill="both", expand=True)
        
        # 高亮当前选中的侧边栏按钮
        self.highlight_sidebar_button(self.theme_button)
    
    def show_help_page(self):
        """显示帮助页面"""
        self.clear_content_frame()
        self.help_frame.pack(fill="both", expand=True)
        
        # 高亮当前选中的侧边栏按钮
        self.highlight_sidebar_button(self.help_button)
    
    def clear_content_frame(self):
        """清除内容区域"""
        for frame in [self.character_frame, self.api_config_frame, 
                     self.image_frame, self.help_frame]:  # 移除了 self.theme_frame
            frame.pack_forget()
    
    def highlight_sidebar_button(self, active_button):
        """高亮当前选中的侧边栏按钮"""
        for button in self.sidebar_buttons:
            if button == active_button:
                button.configure(fg_color=("gray75", "gray25"))
            else:
                button.configure(fg_color="transparent")
    
    def save_all_configs(self):
        """保存所有API配置"""
        # 保存人设API配置
        self.save_character_config()
        
        # 保存图片识别API配置
        self.save_recognition_config()
        
        # 保存图片生成API配置
        self.save_generation_config()
        
        messagebox.showinfo("保存成功", "所有API配置已保存！")
    def generate_character(self):
        """生成角色人设"""
        # 获取角色描述
        character_desc = self.character_desc_text.get("1.0", "end-1c").strip()
        if not character_desc:
            messagebox.showwarning("提示", "请输入角色描述！")
            return
        
        # 获取API配置
        config = APIConfig.read_config()
        character_config = config.get("character_api", {})
        
        url = character_config.get("url", config.get("real_server_base_url"))
        api_key = character_config.get("api_key", config.get("api_key"))
        model = character_config.get("model", config.get("model"))
        
        if not url or not api_key or not model:
            messagebox.showwarning("配置错误", "请先在API配置页面设置人设API！")
            return
        
        try:
            # 显示加载中提示
            self.character_result_text.set_text("正在生成人设，请稍候...")
            self.update()  # 更新UI
            
            # 创建API请求
            tester = APITester(url, api_key, model)
            self.generated_profile = tester.generate_character_profile(character_desc)
            
            # 显示生成结果
            self.character_result_text.set_text(self.generated_profile)
            
        except Exception as e:
            error_msg = handle_api_error(e, "人设生成")
            self.character_result_text.set_text(f"生成失败:\n{error_msg}")
    
    def polish_character(self):
        """润色角色人设"""
        # 检查是否有已生成的人设
        if not self.generated_profile:
            messagebox.showwarning("提示", "请先生成人设或导入人设！")
            return
        
        # 获取润色要求
        polish_desc = self.polish_desc_text.get("1.0", "end-1c").strip()
        if not polish_desc:
            messagebox.showwarning("提示", "请输入润色要求！")
            return
        
        # 获取API配置
        config = APIConfig.read_config()
        character_config = config.get("character_api", {})
        
        url = character_config.get("url", config.get("real_server_base_url"))
        api_key = character_config.get("api_key", config.get("api_key"))
        model = character_config.get("model", config.get("model"))
        
        if not url or not api_key or not model:
            messagebox.showwarning("配置错误", "请先在API配置页面设置人设API！")
            return
        
        try:
            # 显示加载中提示
            self.character_result_text.set_text("正在润色人设，请稍候...")
            self.update()  # 更新UI
            
            # 创建API请求
            tester = APITester(url, api_key, model)
            self.generated_profile = tester.polish_character_profile(self.generated_profile, polish_desc)
            
            # 显示润色结果
            self.character_result_text.set_text(self.generated_profile)
            
        except Exception as e:
            error_msg = handle_api_error(e, "人设润色")
            self.character_result_text.set_text(f"润色失败:\n{error_msg}")

    def import_profile(self):
        """导入角色人设"""
        # 打开文件选择对话框
        file_path = filedialog.askopenfilename(
            title="选择人设文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # 读取文件内容
            with open(file_path, "r", encoding="utf-8") as f:
                profile_text = f.read()
            
            # 显示导入的人设
            self.character_result_text.set_text(profile_text)
            
            # 保存为当前人设
            self.generated_profile = profile_text
            
            messagebox.showinfo("导入成功", "人设已成功导入！")
            
        except Exception as e:
            messagebox.showerror("导入失败", f"读取人设文件时出错: {str(e)}")
    
    def export_profile(self):
        """导出角色人设"""
        # 检查是否有已生成的人设
        if not self.generated_profile:
            messagebox.showwarning("提示", "没有可导出的人设！")
            return
        
        # 打开文件保存对话框
        file_path = filedialog.asksaveasfilename(
            title="保存人设文件",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # 保存人设到文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.generated_profile)
            
            messagebox.showinfo("导出成功", f"人设已保存到: {file_path}")
            
        except Exception as e:
            messagebox.showerror("导出失败", f"保存人设文件时出错: {str(e)}")

    def clear_character_inputs(self):
        """清空人设输入框"""
        self.character_desc_text.delete("1.0", "end")
        self.polish_desc_text.delete("1.0", "end")
        self.character_result_text.set_text("")
        self.generated_profile = None
        messagebox.showinfo("提示", "已清空所有输入和结果！")

    def setup_help_page(self):
        """设置帮助页面内容"""
        # 页面标题
        title_label = ctk.CTkLabel(
            self.help_frame, 
            text="帮助与关于", 
            font=self.title_font
        )
        title_label.pack(pady=(20, 20))
        
        # 创建滚动框架
        help_scroll_frame = ctk.CTkScrollableFrame(self.help_frame)
        help_scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 关于应用
        about_label = ctk.CTkLabel(
            help_scroll_frame, 
            text="关于 Kouri Chat 工具箱", 
            font=ctk.CTkFont(family="黑体", size=16, weight="bold")
        )
        about_label.pack(anchor="w", pady=(0, 10))
        
        about_text = ctk.CTkLabel(
            help_scroll_frame, 
            text="Kouri Chat 工具箱是一个基于大型语言模型的多功能工具箱，提供角色人设生成、图片识别和生成等功能。",
            font=self.default_font,
            wraplength=800,
            justify="left"
        )
        about_text.pack(anchor="w", pady=(0, 20))
        
        # 功能说明
        features_label = ctk.CTkLabel(
            help_scroll_frame, 
            text="功能说明", 
            font=ctk.CTkFont(family="黑体", size=16, weight="bold")
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
                font=self.default_font,
                wraplength=800,
                justify="left"
            )
            feature_text.pack(anchor="w", pady=(0, 5))
        
        # 使用说明
        usage_label = ctk.CTkLabel(
            help_scroll_frame, 
            text="使用说明", 
            font=ctk.CTkFont(family="黑体", size=16, weight="bold")
        )
        usage_label.pack(anchor="w", pady=(20, 10))
        
        usage_text = ctk.CTkLabel(
            help_scroll_frame, 
            text="1. 首先在API配置页面设置您的API密钥和服务器地址。\n"
                 "2. 在人设页面输入角色描述，点击生成按钮创建角色人设。\n"
                 "3. 在图片页面可以上传图片进行识别或输入描述生成图片。\n"
                 "4. 在主题页面可以切换应用的外观主题。",
            font=self.default_font,
            wraplength=800,
            justify="left"
        )
        usage_text.pack(anchor="w", pady=(0, 20))
        
        # 联系方式
        contact_label = ctk.CTkLabel(
            help_scroll_frame, 
            text="联系方式", 
            font=ctk.CTkFont(family="黑体", size=16, weight="bold")
        )
        contact_label.pack(anchor="w", pady=(0, 10))
        
        contact_text = ctk.CTkLabel(
            help_scroll_frame, 
            text="主项目官方网站：https://kourichat.com/\n"
                 "主项目GitHub：https://github.com/KouriChat/KouriChat\n"
                 "工具箱QQ群：639849597\n"
                 "GitHub：https://github.com/linxiajin08/linxiajinKouri",
            font=self.default_font,
            wraplength=800,
            justify="left"
        )
        contact_text.pack(anchor="w", pady=(0, 20))
        
        # 版权信息
        copyright_text = ctk.CTkLabel(
            help_scroll_frame, 
            text="© 2024-2025 Kouri Chat. 保留所有权利。",
            font=ctk.CTkFont(family="黑体", size=10),
            text_color=("gray50", "gray70")
        )
        copyright_text.pack(anchor="w", pady=(20, 0))
        
        # 访问官网按钮
        website_button = ctk.CTkButton(
            self.help_frame,
            text="访问项目地址",
            command=lambda: webbrowser.open("https://github.com/linxiajin08/linxiajinKouri"),
            font=self.default_font,
            fg_color=self.button_color,
            hover_color=self.button_hover_color
        )
        website_button.pack(pady=(0, 20))

    def toggle_theme(self):
        """切换明暗主题"""
        if self.appearance_mode_switch.get() == 1:  # 开关打开，使用暗色主题
            self.current_theme = "dark"
            ctk.set_appearance_mode("dark")
        else:  # 开关关闭，使用亮色主题
            self.current_theme = "light"
            ctk.set_appearance_mode("light")
        
        # 更新配置
        self.config["theme"] = self.current_theme
        APIConfig.save_config(self.config)

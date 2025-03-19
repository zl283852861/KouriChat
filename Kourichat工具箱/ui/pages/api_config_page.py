import customtkinter as ctk
from tkinter import messagebox
import threading
import requests

from widgets.labeled_entry import LabeledEntry
from core.config import APIConfig
from core.error_handler import handle_api_error
from api.tester import APITester

class APIConfigPage:
    """API配置页面类"""
    
    def __init__(self, app):
        self.app = app
        self.setup_api_config_page()
    
    def setup_api_config_page(self):
        """设置API配置页面内容"""
        # 页面标题
        title_label = ctk.CTkLabel(
            self.app.api_config_frame, 
            text="API配置", 
            font=self.app.title_font
        )
        title_label.pack(pady=(20, 20))
        
        # 创建选项卡控件
        self.tabview = ctk.CTkTabview(self.app.api_config_frame)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 添加选项卡
        self.tabview.add("人设API")
        self.tabview.add("图片识别API")
        self.tabview.add("图片生成API")
        
        # 设置各个选项卡内容
        self.setup_character_api_tab(self.tabview.tab("人设API"))
        self.setup_recognition_api_tab(self.tabview.tab("图片识别API"))
        self.setup_generation_api_tab(self.tabview.tab("图片生成API"))
        
        # 底部按钮框架
        button_frame = ctk.CTkFrame(self.app.api_config_frame)
        button_frame.pack(pady=20)
        
        # 保存所有配置按钮
        save_all_button = ctk.CTkButton(
            button_frame, 
            text="保存所有配置", 
            command=self.app.save_all_configs,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        save_all_button.pack()
    
    def setup_character_api_tab(self, parent_frame):
        """设置人设API选项卡内容"""
        # 读取配置
        config = self.app.config
        character_config = config.get("character_api", {})
        
        # 渠道选择框架
        channel_frame = ctk.CTkFrame(parent_frame)
        channel_frame.pack(fill="x", padx=10, pady=10)
        
        # 渠道选择标签
        channel_label = ctk.CTkLabel(
            channel_frame, 
            text="选择渠道:", 
            font=self.app.default_font
        )
        channel_label.pack(side="left", padx=10)
        
        # 渠道选择下拉菜单
        self.character_channel_var = ctk.StringVar()
        self.character_channel_options = ["硅基流动", "DeepSeek官网", "KouriChat", "自定义"]
        
        # 根据当前配置设置默认选项
        current_url = character_config.get("url", config.get("real_server_base_url", "https://api.siliconflow.cn/"))
        
        if current_url == "https://api.siliconflow.cn/":
            self.character_channel_var.set(self.character_channel_options[0])
        elif current_url == "https://api.deepseek.com":
            self.character_channel_var.set(self.character_channel_options[1])
        elif current_url == "https://api.kourichat.com":
            self.character_channel_var.set(self.character_channel_options[2])
        else:
            self.character_channel_var.set(self.character_channel_options[3])  # 自定义
        
        channel_dropdown = ctk.CTkOptionMenu(
            channel_frame, 
            variable=self.character_channel_var,
            values=self.character_channel_options,
            command=self.update_character_channel,
            font=self.app.default_font,
            fg_color=self.app.purple_color,
            button_color=self.app.purple_color,
            button_hover_color=self.app.purple_hover_color
        )
        channel_dropdown.pack(side="left", padx=10)
        
        # 模型选择下拉菜单
        self.character_model_var = ctk.StringVar()
        self.character_model_options = {
            "硅基流动": ["deepseek-ai/DeepSeek-V3", "Qwen/Qwen2-72B-Instruct", "自定义"],
            "DeepSeek官网": ["deepseek-chat", "deepseek-coder", "自定义"],
            "KouriChat": ["kourichat-v3", "自定义"],
            "自定义": ["自定义"]
        }
        
        # 设置默认模型
        current_model = character_config.get("model", config.get("model", ""))
        channel = self.character_channel_var.get()
        
        if current_model in self.character_model_options.get(channel, []):
            self.character_model_var.set(current_model)
        else:
            # 如果当前模型不在选项中，设置为自定义
            self.character_model_var.set("自定义")
        
        # 模型选择框架
        model_frame = ctk.CTkFrame(parent_frame)
        model_frame.pack(fill="x", padx=10, pady=10)
        
        # 模型选择标签
        model_label = ctk.CTkLabel(
            model_frame, 
            text="选择模型:", 
            font=self.app.default_font
        )
        model_label.pack(side="left", padx=10)
        
        # 模型选择下拉菜单
        self.character_model_dropdown = ctk.CTkOptionMenu(
            model_frame, 
            variable=self.character_model_var,
            values=self.character_model_options[channel],
            command=self.update_character_model,
            font=self.app.default_font,
            fg_color=self.app.purple_color,
            button_color=self.app.purple_color,
            button_hover_color=self.app.purple_hover_color
        )
        self.character_model_dropdown.pack(side="left", padx=10)
        
        # API配置框架
        api_config_frame = ctk.CTkFrame(parent_frame)
        api_config_frame.pack(fill="x", padx=10, pady=10)
        
        # 服务器地址输入框
        self.character_url_entry = LabeledEntry(
            api_config_frame, 
            label_text="服务器地址:"
        )
        self.character_url_entry.pack(fill="x", padx=10, pady=5)
        
        # 设置当前URL
        self.character_url_entry.set(current_url)
        
        # API密钥输入框
        self.character_api_key_entry = LabeledEntry(
            api_config_frame, 
            label_text="API密钥:"
        )
        self.character_api_key_entry.pack(fill="x", padx=10, pady=5)
        
        # 设置当前API密钥
        self.character_api_key_entry.set(character_config.get("api_key", config.get("api_key", "")))
        
        # 自定义模型输入框
        self.character_custom_model_entry = LabeledEntry(
            api_config_frame, 
            label_text="自定义模型:"
        )
        self.character_custom_model_entry.pack(fill="x", padx=10, pady=5)
        
        # 如果当前模型是自定义的，设置自定义模型输入框
        if self.character_model_var.get() == "自定义":
            self.character_custom_model_entry.set(current_model)
        
        # 按钮框架
        button_frame = ctk.CTkFrame(parent_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # 测试连接按钮
        test_button = ctk.CTkButton(
            button_frame, 
            text="测试连接", 
            command=self.test_character_api,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        test_button.pack(side="left", padx=10, pady=10)
        
        # 保存配置按钮
        save_button = ctk.CTkButton(
            button_frame, 
            text="保存配置", 
            command=self.save_character_config,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        save_button.pack(side="left", padx=10, pady=10)
        
        # 测试结果标签
        self.character_test_result_label = ctk.CTkLabel(
            parent_frame, 
            text="", 
            font=self.app.default_font,
            wraplength=500
        )
        self.character_test_result_label.pack(fill="x", padx=10, pady=10)
    
    def setup_recognition_api_tab(self, parent_frame):
        """设置图片识别API选项卡内容"""
        # 读取配置
        config = self.app.config
        recognition_config = config.get("recognition_api", {})
        
        # 渠道选择框架
        channel_frame = ctk.CTkFrame(parent_frame)
        channel_frame.pack(fill="x", padx=10, pady=10)
        
        # 渠道选择标签
        channel_label = ctk.CTkLabel(
            channel_frame, 
            text="选择渠道:", 
            font=self.app.default_font
        )
        channel_label.pack(side="left", padx=10)
        
        # 渠道选择下拉菜单
        self.recognition_channel_var = ctk.StringVar()
        self.recognition_channel_options = ["硅基流动", "月之暗面", "自定义"]
        
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
            values=self.recognition_channel_options,
            command=self.update_recognition_channel,
            font=self.app.default_font,
            fg_color=self.app.purple_color,
            button_color=self.app.purple_color,
            button_hover_color=self.app.purple_hover_color
        )
        channel_dropdown.pack(side="left", padx=10)
        
        # 模型选择下拉菜单
        self.recognition_model_var = ctk.StringVar()
        self.recognition_model_options = {
            "硅基流动": ["Qwen/Qwen-VL-Max", "Qwen/Qwen-VL-Plus", "自定义"],
            "月之暗面": ["moonshot-v1-32k", "moonshot-v1-128k", "自定义"],
            "自定义": ["自定义"]
        }
        
        # 设置默认模型
        current_model = recognition_config.get("model", config.get("model", ""))
        channel = self.recognition_channel_var.get()
        
        if current_model in self.recognition_model_options.get(channel, []):
            self.recognition_model_var.set(current_model)
        else:
            # 如果当前模型不在选项中，设置为自定义
            self.recognition_model_var.set("自定义")
        
        # 模型选择框架
        model_frame = ctk.CTkFrame(parent_frame)
        model_frame.pack(fill="x", padx=10, pady=10)
        
        # 模型选择标签
        model_label = ctk.CTkLabel(
            model_frame, 
            text="选择模型:", 
            font=self.app.default_font
        )
        model_label.pack(side="left", padx=10)
        
        # 模型选择下拉菜单
        self.recognition_model_dropdown = ctk.CTkOptionMenu(
            model_frame, 
            variable=self.recognition_model_var,
            values=self.recognition_model_options[channel],
            command=self.update_recognition_model,
            font=self.app.default_font,
            fg_color=self.app.purple_color,
            button_color=self.app.purple_color,
            button_hover_color=self.app.purple_hover_color
        )
        self.recognition_model_dropdown.pack(side="left", padx=10)
        
        # API配置框架
        api_config_frame = ctk.CTkFrame(parent_frame)
        api_config_frame.pack(fill="x", padx=10, pady=10)
        
        # 服务器地址输入框
        self.recognition_url_entry = LabeledEntry(
            api_config_frame, 
            label_text="服务器地址:"
        )
        self.recognition_url_entry.pack(fill="x", padx=10, pady=5)
        
        # 设置当前URL
        self.recognition_url_entry.set(current_url)
        
        # API密钥输入框
        self.recognition_api_key_entry = LabeledEntry(
            api_config_frame, 
            label_text="API密钥:"
        )
        self.recognition_api_key_entry.pack(fill="x", padx=10, pady=5)
        
        # 设置当前API密钥
        self.recognition_api_key_entry.set(recognition_config.get("api_key", config.get("api_key", "")))
        
        # 自定义模型输入框
        self.recognition_custom_model_entry = LabeledEntry(
            api_config_frame, 
            label_text="自定义模型:"
        )
        self.recognition_custom_model_entry.pack(fill="x", padx=10, pady=5)
        
        # 如果当前模型是自定义的，设置自定义模型输入框
        if self.recognition_model_var.get() == "自定义":
            self.recognition_custom_model_entry.set(current_model)
        
        # 按钮框架
        button_frame = ctk.CTkFrame(parent_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # 测试连接按钮
        test_button = ctk.CTkButton(
            button_frame, 
            text="测试连接", 
            command=self.test_recognition_api,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        test_button.pack(side="left", padx=10, pady=10)
        
        # 保存配置按钮
        save_button = ctk.CTkButton(
            button_frame, 
            text="保存配置", 
            command=self.save_recognition_config,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        save_button.pack(side="left", padx=10, pady=10)
        
        # 测试结果标签
        self.recognition_test_result_label = ctk.CTkLabel(
            parent_frame, 
            text="", 
            font=self.app.default_font,
            wraplength=500
        )
        self.recognition_test_result_label.pack(fill="x", padx=10, pady=10)
    
    def setup_generation_api_tab(self, parent_frame):
        """设置图片生成API选项卡内容"""
        # 读取配置
        config = self.app.config
        generation_config = config.get("generation_api", {})
        
        # 渠道选择框架
        channel_frame = ctk.CTkFrame(parent_frame)
        channel_frame.pack(fill="x", padx=10, pady=10)
        
        # 渠道选择标签
        channel_label = ctk.CTkLabel(
            channel_frame, 
            text="选择渠道:", 
            font=self.app.default_font
        )
        channel_label.pack(side="left", padx=10)
        
        # 渠道选择下拉菜单
        self.generation_channel_var = ctk.StringVar()
        self.generation_channel_options = ["硅基流动", "自定义"]
        
        # 根据当前配置设置默认选项
        current_url = generation_config.get("url", config.get("real_server_base_url", "https://api.siliconflow.cn/"))
        
        if current_url == "https://api.siliconflow.cn/":
            self.generation_channel_var.set(self.generation_channel_options[0])
        else:
            self.generation_channel_var.set(self.generation_channel_options[1])  # 自定义
        
        channel_dropdown = ctk.CTkOptionMenu(
            channel_frame, 
            variable=self.generation_channel_var,
            values=self.generation_channel_options,
            command=self.update_generation_channel,
            font=self.app.default_font,
            fg_color=self.app.purple_color,
            button_color=self.app.purple_color,
            button_hover_color=self.app.purple_hover_color
        )
        channel_dropdown.pack(side="left", padx=10)
        
        # 模型选择下拉菜单
        self.generation_model_var = ctk.StringVar()
        self.generation_model_options = {
            "硅基流动": ["Kwai-Kolors/Kolors", "自定义"],
            "自定义": ["自定义"]
        }
        
        # 设置默认模型
        current_model = generation_config.get("model", "")
        channel = self.generation_channel_var.get()
        
        if current_model in self.generation_model_options.get(channel, []):
            self.generation_model_var.set(current_model)
        else:
            # 如果当前模型不在选项中，设置为自定义
            self.generation_model_var.set("自定义")
        
        # 模型选择框架
        model_frame = ctk.CTkFrame(parent_frame)
        model_frame.pack(fill="x", padx=10, pady=10)
        
        # 模型选择标签
        model_label = ctk.CTkLabel(
            model_frame, 
            text="选择模型:", 
            font=self.app.default_font
        )
        model_label.pack(side="left", padx=10)
        
        # 模型选择下拉菜单
        self.generation_model_dropdown = ctk.CTkOptionMenu(
            model_frame, 
            variable=self.generation_model_var,
            values=self.generation_model_options[channel],
            command=self.update_generation_model,
            font=self.app.default_font,
            fg_color=self.app.purple_color,
            button_color=self.app.purple_color,
            button_hover_color=self.app.purple_hover_color
        )
        self.generation_model_dropdown.pack(side="left", padx=10)
        
        # 图片尺寸配置
        size_label = ctk.CTkLabel(
            model_frame, 
            text="默认图片尺寸:", 
            font=self.app.default_font
        )
        size_label.pack(side="left", padx=(20, 10))
        
        # 图片尺寸下拉菜单
        self.generation_size_var = ctk.StringVar()
        size_options = ["1024x1024", "960x1280", "768x1024", "720x1440", "720x1280", "512x512"]
        
        # 设置默认尺寸
        current_size = generation_config.get("generate_size", config.get("image_config", {}).get("generate_size", "512x512"))
        if current_size in size_options:
            self.generation_size_var.set(current_size)
        else:
            self.generation_size_var.set("512x512")
        
        size_dropdown = ctk.CTkOptionMenu(
            model_frame, 
            variable=self.generation_size_var,
            values=size_options,
            font=self.app.default_font,
            fg_color=self.app.purple_color,
            button_color=self.app.purple_color,
            button_hover_color=self.app.purple_hover_color
        )
        size_dropdown.pack(side="left", padx=10)
        
        # API配置框架
        api_config_frame = ctk.CTkFrame(parent_frame)
        api_config_frame.pack(fill="x", padx=10, pady=10)
        
        # 服务器地址输入框
        self.generation_url_entry = LabeledEntry(
            api_config_frame, 
            label_text="服务器地址:"
        )
        self.generation_url_entry.pack(fill="x", padx=10, pady=5)
        
        # 设置当前URL
        self.generation_url_entry.set(current_url)
        
        # API密钥输入框
        self.generation_api_key_entry = LabeledEntry(
            api_config_frame, 
            label_text="API密钥:"
        )
        self.generation_api_key_entry.pack(fill="x", padx=10, pady=5)
        
        # 设置当前API密钥
        self.generation_api_key_entry.set(generation_config.get("api_key", config.get("api_key", "")))
        
        # 自定义模型输入框
        self.generation_custom_model_entry = LabeledEntry(
            api_config_frame, 
            label_text="自定义模型:"
        )
        self.generation_custom_model_entry.pack(fill="x", padx=10, pady=5)
        
        # 如果当前模型是自定义的，设置自定义模型输入框
        if self.generation_model_var.get() == "自定义":
            self.generation_custom_model_entry.set(current_model)
        
        # 按钮框架
        button_frame = ctk.CTkFrame(parent_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # 测试连接按钮
        test_button = ctk.CTkButton(
            button_frame, 
            text="测试连接", 
            command=self.test_generation_api,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        test_button.pack(side="left", padx=10, pady=10)
        
        # 保存配置按钮
        save_button = ctk.CTkButton(
            button_frame, 
            text="保存配置", 
            command=self.save_generation_config,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        save_button.pack(side="left", padx=10, pady=10)
        
        # 测试结果标签
        self.generation_test_result_label = ctk.CTkLabel(
            parent_frame, 
            text="", 
            font=self.app.default_font,
            wraplength=500
        )
        self.generation_test_result_label.pack(fill="x", padx=10, pady=10)
    
    # 更新渠道和模型的回调函数
    def update_character_channel(self, channel):
        """更新人设API渠道"""
        # 更新URL
        if channel == "硅基流动":
            self.character_url_entry.set("https://api.siliconflow.cn/")
        elif channel == "DeepSeek官网":
            self.character_url_entry.set("https://api.deepseek.com")
        elif channel == "KouriChat":
            self.character_url_entry.set("https://api.kourichat.com")
        
        # 更新模型下拉菜单
        self.character_model_dropdown.configure(values=self.character_model_options[channel])
        
        # 设置默认模型
        if channel != "自定义":
            self.character_model_var.set(self.character_model_options[channel][0])
        else:
            self.character_model_var.set("自定义")
    
    def update_character_model(self, model):
        """更新人设API模型"""
        # 如果选择自定义模型，清空自定义模型输入框
        if model == "自定义":
            self.character_custom_model_entry.set("")
    
    def update_recognition_channel(self, channel):
        """更新图片识别API渠道"""
        # 更新URL
        if channel == "硅基流动":
            self.recognition_url_entry.set("https://api.siliconflow.cn/")
        elif channel == "月之暗面":
            self.recognition_url_entry.set("https://api.moonshot.cn")
        
        # 更新模型下拉菜单
        self.recognition_model_dropdown.configure(values=self.recognition_model_options[channel])
        
        # 设置默认模型
        if channel != "自定义":
            self.recognition_model_var.set(self.recognition_model_options[channel][0])
        else:
            self.recognition_model_var.set("自定义")
    
    def update_recognition_model(self, model):
        """更新图片识别API模型"""
        # 如果选择自定义模型，清空自定义模型输入框
        if model == "自定义":
            self.recognition_custom_model_entry.set("")
    
    def update_generation_channel(self, channel):
        """更新图片生成API渠道"""
        # 更新URL
        if channel == "硅基流动":
            self.generation_url_entry.set("https://api.siliconflow.cn/")
        
        # 更新模型下拉菜单
        self.generation_model_dropdown.configure(values=self.generation_model_options[channel])
        
        # 设置默认模型
        if channel != "自定义":
            self.generation_model_var.set(self.generation_model_options[channel][0])
        else:
            self.generation_model_var.set("自定义")
    
    def update_generation_model(self, model):
        """更新图片生成API模型"""
        # 如果选择自定义模型，清空自定义模型输入框
        if model == "自定义":
            self.generation_custom_model_entry.set("")
    
    # 测试API连接的函数
    def test_character_api(self):
        """测试人设API连接"""
        # 获取当前配置
        url = self.character_url_entry.get()
        api_key = self.character_api_key_entry.get()
        model = self.character_model_var.get()
        
        # 如果选择自定义模型，使用自定义模型输入框的值
        if model == "自定义":
            model = self.character_custom_model_entry.get()
        
        # 检查必要参数
        if not url or not api_key or not model:
            self.character_test_result_label.configure(
                text="请填写完整的API配置信息！",
                text_color="red"
            )
            return
        
        # 显示测试中提示
        self.character_test_result_label.configure(
            text="正在测试连接，请稍候...",
            text_color=("gray70", "gray30")
        )
        
        # 创建API测试器
        api_tester = APITester(url, api_key, model)
        
        # 在后台线程中测试连接
        def test_in_thread():
            try:
                # 测试连接
                response = api_tester.test_standard_api()
                
                # 检查响应
                if response.status_code == 200:
                    self.app.after(0, lambda: self.character_test_result_label.configure(
                        text="连接成功！服务器响应正常。",
                        text_color="green"
                    ))
                else:
                    self.app.after(0, lambda: self.character_test_result_label.configure(
                        text=f"连接失败！状态码: {response.status_code}, 错误: {response.text}",
                        text_color="red"
                    ))
                    
            except Exception as e:
                error_msg = handle_api_error(e, "人设API")
                self.app.after(0, lambda: self.character_test_result_label.configure(
                    text=error_msg,
                    text_color="red"
                ))
        
        # 启动线程
        threading.Thread(target=test_in_thread, daemon=True).start()
    
    def test_recognition_api(self):
        """测试图片识别API连接"""
        # 获取当前配置
        url = self.recognition_url_entry.get()
        api_key = self.recognition_api_key_entry.get()
        model = self.recognition_model_var.get()
        
        # 如果选择自定义模型，使用自定义模型输入框的值
        if model == "自定义":
            model = self.recognition_custom_model_entry.get()
        
        # 检查必要参数
        if not url or not api_key or not model:
            self.recognition_test_result_label.configure(
                text="请填写完整的API配置信息！",
                text_color="red"
            )
            return
        
        # 显示测试中提示
        self.recognition_test_result_label.configure(
            text="正在测试连接，请稍候...",
            text_color=("gray70", "gray30")
        )
        
        # 创建API测试器
        api_tester = APITester(url, api_key, model)
        
        # 在后台线程中测试连接
        def test_in_thread():
            try:
                # 测试连接
                response = api_tester.recognition_api.test_connection()
                
                # 检查响应
                if response.status_code == 200:
                    self.app.after(0, lambda: self.recognition_test_result_label.configure(
                        text="连接成功！服务器响应正常。",
                        text_color="green"
                    ))
                else:
                    self.app.after(0, lambda: self.recognition_test_result_label.configure(
                        text=f"连接失败！状态码: {response.status_code}, 错误: {response.text}",
                        text_color="red"
                    ))
                    
            except Exception as e:
                error_msg = handle_api_error(e, "图片识别API")
                self.app.after(0, lambda: self.recognition_test_result_label.configure(
                    text=error_msg,
                    text_color="red"
                ))
        
        # 启动线程
        threading.Thread(target=test_in_thread, daemon=True).start()
    
    def test_generation_api(self):
        """测试图片生成API连接"""
        # 获取当前配置
        url = self.generation_url_entry.get()
        api_key = self.generation_api_key_entry.get()
        model = self.generation_model_var.get()
        
        # 如果选择自定义模型，使用自定义模型输入框的值
        if model == "自定义":
            model = self.generation_custom_model_entry.get()
        
        # 检查必要参数
        if not url or not api_key or not model:
            self.generation_test_result_label.configure(
                text="请填写完整的API配置信息！",
                text_color="red"
            )
            return
        
        # 显示测试中提示
        self.generation_test_result_label.configure(
            text="正在测试连接，请稍候...",
            text_color=("gray70", "gray30")
        )
        
        # 创建API测试器
        api_tester = APITester(url, api_key, model)
        
        # 在后台线程中测试连接
        def test_in_thread():
            try:
                # 测试连接
                response = api_tester.generation_api.test_connection()
                
                # 检查响应
                if response.status_code == 200:
                    self.app.after(0, lambda: self.generation_test_result_label.configure(
                        text="连接成功！服务器响应正常。",
                        text_color="green"
                    ))
                else:
                    self.app.after(0, lambda: self.generation_test_result_label.configure(
                        text=f"连接失败！状态码: {response.status_code}, 错误: {response.text}",
                        text_color="red"
                    ))
                    
            except Exception as e:
                error_msg = handle_api_error(e, "图片生成API")
                self.app.after(0, lambda: self.generation_test_result_label.configure(
                    text=error_msg,
                    text_color="red"
                ))
        
        # 启动线程
        threading.Thread(target=test_in_thread, daemon=True).start()
    
    # 保存配置的函数
    def save_character_config(self):
        """保存人设API配置"""
        # 获取当前配置
        url = self.character_url_entry.get()
        api_key = self.character_api_key_entry.get()
        model = self.character_model_var.get()
        
        # 如果选择自定义模型，使用自定义模型输入框的值
        if model == "自定义":
            model = self.character_custom_model_entry.get()
        
        # 检查必要参数
        if not url or not api_key or not model:
            messagebox.showwarning("警告", "请填写完整的API配置信息！")
            return
        
        # 更新配置
        config = self.app.config
        if "character_api" not in config:
            config["character_api"] = {}
        
        config["character_api"]["url"] = url
        config["character_api"]["api_key"] = api_key
        config["character_api"]["model"] = model
        
        # 保存配置
        APIConfig.save_config(config)
        
        # 显示成功消息
        messagebox.showinfo("成功", "人设API配置已保存！")
    
    def save_recognition_config(self):
        """保存图片识别API配置"""
        # 获取当前配置
        url = self.recognition_url_entry.get()
        api_key = self.recognition_api_key_entry.get()
        model = self.recognition_model_var.get()
        
        # 如果选择自定义模型，使用自定义模型输入框的值
        if model == "自定义":
            model = self.recognition_custom_model_entry.get()
        
        # 检查必要参数
        if not url or not api_key or not model:
            messagebox.showwarning("警告", "请填写完整的API配置信息！")
            return
        
        # 更新配置
        config = self.app.config
        if "recognition_api" not in config:
            config["recognition_api"] = {}
        
        config["recognition_api"]["url"] = url
        config["recognition_api"]["api_key"] = api_key
        config["recognition_api"]["model"] = model
        
        # 保存配置
        APIConfig.save_config(config)
        
        # 显示成功消息
        messagebox.showinfo("成功", "图片识别API配置已保存！")
    
    def save_generation_config(self):
        """保存图片生成API配置"""
        # 获取当前配置
        url = self.generation_url_entry.get()
        api_key = self.generation_api_key_entry.get()
        model = self.generation_model_var.get()
        
        # 如果选择自定义模型，使用自定义模型输入框的值
        if model == "自定义":
            model = self.generation_custom_model_entry.get()
        
        # 检查必要参数
        if not url or not api_key or not model:
            messagebox.showwarning("警告", "请填写完整的API配置信息！")
            return
        
        # 更新配置
        config = self.app.config
        if "generation_api" not in config:
            config["generation_api"] = {}
        
        config["generation_api"]["url"] = url
        config["generation_api"]["api_key"] = api_key
        config["generation_api"]["model"] = model
        
        # 保存配置
        APIConfig.save_config(config)
        
        # 显示成功消息
        messagebox.showinfo("成功", "图片生成API配置已保存！")
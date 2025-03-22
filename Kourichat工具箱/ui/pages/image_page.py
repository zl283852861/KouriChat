import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import os
import io
import base64
from PIL import Image, ImageTk
import requests
import webbrowser

from widgets.scrollable_text_box import ScrollableTextBox
from widgets.loading_animation import LoadingAnimation
from api.tester import APITester
from core.error_handler import handle_api_error
from ..theme import Theme

class ImagePage:
    """图片页面类"""
    
    def __init__(self, app):
        self.app = app
        self.current_image_path = None
        self.current_image_data = None
        self.setup_image_page()
    
    def setup_image_page(self):
        """设置图片页面内容"""
        # 创建主容器
        main_container = ctk.CTkFrame(
            self.app.image_frame, 
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
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="图片功能中心",
            font=Theme.get_font(size=32, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        title_label.pack(expand=True)
        
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
        self.recognition_tab = self.tab_view.add("图片识别")
        self.generation_tab = self.tab_view.add("图片生成")
        
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
        
        # 设置各个选项卡内容
        self.setup_recognition_tab(self.recognition_tab)
        self.setup_generation_tab(self.generation_tab)
    
    def setup_recognition_tab(self, parent_frame):
        """设置图片识别选项卡内容"""
        # 创建左右分栏
        content_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=30, pady=20)
        
        # 配置网格布局
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)
        
        # 左侧图片区域
        image_frame = ctk.CTkFrame(
            content_frame, 
            fg_color=Theme.CARD_BG,
            corner_radius=15
        )
        image_frame.grid(row=0, column=0, padx=15, pady=10, sticky="nsew")
        
        # 右侧结果区域
        result_frame = ctk.CTkFrame(
            content_frame, 
            fg_color=Theme.CARD_BG,
            corner_radius=15
        )
        result_frame.grid(row=0, column=1, padx=15, pady=10, sticky="nsew")
        
        # 设置左侧图片区域
        self.setup_recognition_image_area(image_frame)
        
        # 设置右侧结果区域
        self.setup_recognition_result_area(result_frame)
    
    def setup_recognition_image_area(self, parent_frame):
        """设置图片识别的图片区域"""
        # 标题
        title_frame = ctk.CTkFrame(parent_frame, fg_color="transparent", height=50)
        title_frame.pack(fill="x", padx=20, pady=(20, 0))
        title_frame.pack_propagate(False)
        
        image_title = ctk.CTkLabel(
            title_frame, 
            text="上传图片", 
            font=Theme.get_font(size=20, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        image_title.pack(side="left")
        
        # 图片显示区域 - 直接使用标签
        self.recognition_image_label = ctk.CTkLabel(
            parent_frame, 
            text='点击"选择图片"上传待识别的图片',
            font=Theme.get_font(size=14),
            fg_color=Theme.BG_TERTIARY,
            corner_radius=10,
            height=300,
            text_color=Theme.TEXT_SECONDARY
        )
        self.recognition_image_label.pack(fill="x", padx=20, pady=15)
        
        # 按钮区域
        button_frame = ctk.CTkFrame(parent_frame, fg_color="transparent", height=60)
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        button_frame.pack_propagate(False)
        
        # 选择图片按钮
        select_button = ctk.CTkButton(
            button_frame, 
            text="选择图片", 
            command=self.select_image_for_recognition,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8
        )
        select_button.pack(side="left", padx=5)
        
        # 识别图片按钮
        recognize_button = ctk.CTkButton(
            button_frame, 
            text="开始识别", 
            command=self.recognize_image,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8
        )
        recognize_button.pack(side="left", padx=5)
        
        # 清空按钮
        clear_button = ctk.CTkButton(
            button_frame, 
            text="清空", 
            command=self.clear_recognition,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_DANGER,
            hover_color=Theme.BUTTON_DANGER_HOVER,
            height=38,
            width=100,
            corner_radius=8
        )
        clear_button.pack(side="left", padx=5)
    
    def setup_recognition_result_area(self, parent_frame):
        """设置图片识别的结果区域"""
        # 标题
        title_frame = ctk.CTkFrame(parent_frame, fg_color="transparent", height=50)
        title_frame.pack(fill="x", padx=20, pady=(20, 0))
        title_frame.pack_propagate(False)
        
        result_title = ctk.CTkLabel(
            title_frame, 
            text="识别结果", 
            font=Theme.get_font(size=20, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        result_title.pack(side="left")
        
        # 结果文本框
        self.recognition_result_text = ScrollableTextBox(
            parent_frame,
            font=Theme.get_font(size=14),
            fg_color=Theme.BG_TERTIARY,
            text_color=Theme.TEXT_PRIMARY,
            border_color=None,
            height=300
        )
        self.recognition_result_text.pack(fill="both", expand=True, padx=20, pady=15)
        
        # 创建结果文本框的加载动画标签
        self.recognition_result_label = ctk.CTkLabel(
            self.recognition_result_text,
            text="",
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_SECONDARY
        )
        self.recognition_result_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # 创建加载动画实例
        self.recognition_result_loading = LoadingAnimation(self.recognition_result_label, self.app)
        
        # 按钮区域
        button_frame = ctk.CTkFrame(parent_frame, fg_color="transparent", height=60)
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        button_frame.pack_propagate(False)
        
        # 复制按钮
        copy_button = ctk.CTkButton(
            button_frame, 
            text="复制结果", 
            command=self.copy_recognition_result,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8
        )
        copy_button.pack(side="left", padx=20)
    
    def setup_generation_tab(self, parent_frame):
        """设置图片生成选项卡内容"""
        # 创建主容器
        main_container = ctk.CTkFrame(parent_frame, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=30, pady=20)
        
        # 配置网格布局
        main_container.grid_columnconfigure(0, weight=1)  # 左侧面板
        main_container.grid_columnconfigure(1, weight=1)  # 右侧面板
        
        # 创建左侧面板
        left_panel = ctk.CTkFrame(main_container, fg_color="transparent")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        
        # 创建提示词输入区域
        prompt_frame = ctk.CTkFrame(left_panel, fg_color=Theme.CARD_BG, corner_radius=10)
        prompt_frame.pack(fill="both", expand=True)
        
        # 提示词标题
        prompt_title = ctk.CTkLabel(
            prompt_frame,
            text="提示词",
            font=Theme.get_font(size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        prompt_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # 提示词输入框
        self.prompt_textbox = ScrollableTextBox(
            prompt_frame,
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_PRIMARY,
            fg_color=Theme.BG_TERTIARY,
            border_width=0,
            corner_radius=8
        )
        self.prompt_textbox.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # 创建参数设置区域
        settings_frame = ctk.CTkFrame(left_panel, fg_color=Theme.CARD_BG, corner_radius=10)
        settings_frame.pack(fill="x", pady=20)
        
        # 参数设置标题
        settings_title = ctk.CTkLabel(
            settings_frame,
            text="参数设置",
            font=Theme.get_font(size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        settings_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # 参数设置网格
        settings_grid = ctk.CTkFrame(settings_frame, fg_color="transparent")
        settings_grid.pack(fill="x", padx=20, pady=(0, 20))
        
        # 配置参数网格布局
        settings_grid.grid_columnconfigure(1, weight=1)
        
        # 尺寸选择
        size_label = ctk.CTkLabel(
            settings_grid,
            text="尺寸:",
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_PRIMARY
        )
        size_label.grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        
        self.size_var = ctk.StringVar(value="512x512")
        size_menu = ctk.CTkOptionMenu(
            settings_grid,
            values=["256x256", "512x512", "1024x1024"],
            variable=self.size_var,
            font=Theme.get_font(size=14),
            fg_color=Theme.BG_TERTIARY,
            button_color=Theme.BUTTON_SECONDARY,
            button_hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            width=120
        )
        size_menu.grid(row=0, column=1, sticky="w", pady=5)
        
        # 数量选择
        count_label = ctk.CTkLabel(
            settings_grid,
            text="数量:",
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_PRIMARY
        )
        count_label.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)
        
        self.count_var = ctk.StringVar(value="1")
        count_menu = ctk.CTkOptionMenu(
            settings_grid,
            values=["1", "2", "3", "4"],
            variable=self.count_var,
            font=Theme.get_font(size=14),
            fg_color=Theme.BG_TERTIARY,
            button_color=Theme.BUTTON_SECONDARY,
            button_hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            width=120
        )
        count_menu.grid(row=1, column=1, sticky="w", pady=5)
        
        # 创建按钮区域
        button_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 20))
        
        # 生成按钮
        generate_button = ctk.CTkButton(
            button_frame,
            text="生成图片",
            command=self.generate_image,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8
        )
        generate_button.pack(side="left", padx=5)
        
        # 清空按钮
        clear_button = ctk.CTkButton(
            button_frame,
            text="清空",
            command=self.clear_generation,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_DANGER,
            hover_color=Theme.BUTTON_DANGER_HOVER,
            height=38,
            width=100,
            corner_radius=8
        )
        clear_button.pack(side="right", padx=5)
        
        # 创建右侧面板
        right_panel = ctk.CTkFrame(main_container, fg_color="transparent")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(15, 0))
        
        # 创建生成结果区域
        result_frame = ctk.CTkFrame(right_panel, fg_color=Theme.CARD_BG, corner_radius=10)
        result_frame.pack(fill="both", expand=True)
        
        # 生成结果标题
        result_title = ctk.CTkLabel(
            result_frame,
            text="生成结果",
            font=Theme.get_font(size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        result_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # 生成结果显示区域
        self.generation_result_area = ctk.CTkFrame(
            result_frame,
            fg_color=Theme.BG_TERTIARY,
            corner_radius=8
        )
        self.generation_result_area.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # 图片显示标签
        self.generation_image_label = ctk.CTkLabel(
            self.generation_result_area,
            text="未生成图片",
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_SECONDARY
        )
        self.generation_image_label.pack(expand=True)
        
        # 创建加载动画实例
        self.generation_loading = LoadingAnimation(self.generation_image_label, self.app)
        
        # 创建图片操作按钮区域
        image_button_frame = ctk.CTkFrame(result_frame, fg_color="transparent")
        image_button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # 保存图片按钮
        save_button = ctk.CTkButton(
            image_button_frame,
            text="保存图片",
            command=self.save_generated_image,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8
        )
        save_button.pack(side="left", padx=5)
        
        # 打开图片按钮
        open_button = ctk.CTkButton(
            image_button_frame,
            text="打开图片",
            command=self.open_generated_image,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8
        )
        open_button.pack(side="right", padx=5)
    
    def setup_generation_image_area(self, parent_frame):
        """设置图片生成的图片区域"""
        # 标题
        title_frame = ctk.CTkFrame(parent_frame, fg_color="transparent", height=50)
        title_frame.pack(fill="x", padx=20, pady=(20, 0))
        title_frame.pack_propagate(False)
        
        image_title = ctk.CTkLabel(
            title_frame, 
            text="生成结果", 
            font=Theme.get_font(size=20, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        image_title.pack(side="left")
        
        # 图片显示区域
        image_container = ctk.CTkFrame(
            parent_frame,
            fg_color=Theme.BG_TERTIARY,
            corner_radius=10,
            height=300
        )
        image_container.pack(fill="x", padx=20, pady=15)
        image_container.pack_propagate(False)
        
        self.generation_image_label = ctk.CTkLabel(
            image_container, 
            text='输入提示词并点击"开始生成"',
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_SECONDARY
        )
        self.generation_image_label.pack(expand=True)
        
        # 按钮区域
        button_frame = ctk.CTkFrame(parent_frame, fg_color="transparent", height=60)
        button_frame.pack(fill="x", padx=20, pady=(10, 20))
        button_frame.pack_propagate(False)
        
        button_container = ctk.CTkFrame(button_frame, fg_color="transparent")
        button_container.pack(expand=True)
        
        # 保存按钮
        save_button = ctk.CTkButton(
            button_container, 
            text="保存图片", 
            command=self.save_generated_image,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8
        )
        save_button.pack(side="left", padx=5)
        
        # 打开按钮
        open_button = ctk.CTkButton(
            button_container, 
            text="打开图片", 
            command=self.open_generated_image,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8
        )
        open_button.pack(side="left", padx=5)
    
    # 图片识别相关函数
    def select_image_for_recognition(self):
        """选择图片进行识别"""
        # 打开文件选择对话框
        file_path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("所有文件", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            # 保存图片路径
            self.current_image_path = file_path
            
            # 加载图片并调整大小
            image = Image.open(file_path)
            image = self.resize_image(image, (300, 300))
            
            # 转换为CTkImage
            ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
            
            # 显示图片
            self.recognition_image_label.configure(image=ctk_image, text="")
            
            # 保存图片引用，防止被垃圾回收
            self.recognition_image_label.image = ctk_image
            
        except Exception as e:
            messagebox.showerror("错误", f"加载图片时出错: {str(e)}")
    
    def recognize_image(self):
        """识别图片内容"""
        # 检查是否已选择图片
        if not self.current_image_path:
            messagebox.showwarning("提示", "请先选择一张图片！")
            return
        
        # 获取API配置
        config = self.app.config
        recognition_config = config.get("recognition_api", {})
        
        url = recognition_config.get("url", config.get("real_server_base_url", ""))
        api_key = recognition_config.get("api_key", config.get("api_key", ""))
        model = recognition_config.get("model", config.get("model", ""))
        
        if not url or not api_key or not model:
            messagebox.showwarning("提示", "请先在API配置页面设置图片识别API参数！")
            return
        
        # 显示识别中动画
        self.recognition_loading.start("正在识别图片")
        self.recognition_result_loading.start("正在分析图片内容")
        self.recognition_result_text.clear()
        
        # 创建API测试器
        api_tester = APITester(url, api_key, model)
        
        # 在后台线程中识别图片
        def recognize_in_thread():
            try:
                # 识别图片
                result = api_tester.recognize_image(self.current_image_path)
                
                # 停止加载动画
                self.app.after(0, self.recognition_loading.stop)
                self.app.after(0, self.recognition_result_loading.stop)
                
                # 更新UI
                self.app.after(0, lambda: self.recognition_result_text.set_text(result))
                self.app.after(0, lambda: self.recognition_result_label.configure(text=""))
                
            except Exception as e:
                error_msg = handle_api_error(e, "图片识别API")
                self.app.after(0, self.recognition_loading.stop)
                self.app.after(0, self.recognition_result_loading.stop)
                self.app.after(0, lambda: self.recognition_result_text.set_text(error_msg))
                self.app.after(0, lambda: self.recognition_result_label.configure(text=""))
        
        # 启动线程
        threading.Thread(target=recognize_in_thread, daemon=True).start()
    
    def copy_recognition_result(self):
        """复制识别结果"""
        result = self.recognition_result_text.get_text()
        if not result:
            messagebox.showwarning("提示", "没有可复制的识别结果！")
            return
        
        # 复制到剪贴板
        self.app.clipboard_clear()
        self.app.clipboard_append(result)
        
        messagebox.showinfo("成功", "识别结果已复制到剪贴板！")
    
    def clear_recognition(self):
        """清空识别相关内容"""
        self.current_image_path = None
        self.recognition_image_label.configure(image=None, text="未选择图片")
        self.recognition_result_text.clear()
        self.recognition_result_label.configure(text="")
    
    # 图片生成相关函数
    def generate_image(self):
        """生成图片"""
        # 获取图片描述
        prompt = self.prompt_textbox.get_text()
        if not prompt:
            messagebox.showwarning("提示", "请输入图片描述！")
            return
        
        # 获取图片尺寸和数量
        size = self.size_var.get()
        count = int(self.count_var.get())
        
        # 获取API配置
        config = self.app.config
        generation_config = config.get("generation_api", {})
        
        url = generation_config.get("url", config.get("real_server_base_url", ""))
        api_key = generation_config.get("api_key", config.get("api_key", ""))
        model = generation_config.get("model", config.get("model", ""))
        
        if not url or not api_key or not model:
            messagebox.showwarning("提示", "请先在API配置页面设置图片生成API参数！")
            return
        
        # 显示生成中提示
        self.generation_image_label.configure(text="正在生成图片...")
        
        # 创建API测试器
        api_tester = APITester(url, api_key, model)
        
        # 在后台线程中生成图片
        def generate_in_thread():
            try:
                # 生成图片
                image_data = api_tester.generate_image(prompt, size)
                
                # 保存图片数据
                self.current_image_data = image_data
                
                # 加载图片
                if image_data.startswith("http"):
                    # 如果是URL，下载图片
                    response = requests.get(image_data)
                    response.raise_for_status()
                    image = Image.open(io.BytesIO(response.content))
                else:
                    # 如果是base64数据
                    base64_data = image_data.split(",")[1]
                    image = Image.open(io.BytesIO(base64.b64decode(base64_data)))
                
                # 调整图片大小
                image = self.resize_image(image, (400, 400))
                
                # 转换为CTkImage
                ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
                
                # 显示图片
                self.app.after(0, lambda: self.generation_image_label.configure(image=ctk_image, text=""))
                
            except Exception as e:
                error_msg = handle_api_error(e, "图片生成API")
                self.app.after(0, lambda: self.generation_image_label.configure(image=None, text=error_msg))
        
        # 启动线程
        threading.Thread(target=generate_in_thread, daemon=True).start()
    
    def save_generated_image(self):
        """保存生成的图片"""
        # 检查是否已生成图片
        if not self.current_image_data:
            messagebox.showwarning("提示", "请先生成一张图片！")
            return
        
        # 打开文件保存对话框
        file_path = filedialog.asksaveasfilename(
            title="保存图片",
            defaultextension=".png",
            filetypes=[
                ("PNG图片", "*.png"),
                ("JPEG图片", "*.jpg"),
                ("所有文件", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            # 保存图片
            if self.current_image_data.startswith("http"):
                # 如果是URL，下载图片
                response = requests.get(self.current_image_data)
                response.raise_for_status()
                with open(file_path, "wb") as f:
                    f.write(response.content)
            else:
                # 如果是base64数据
                base64_data = self.current_image_data.split(",")[1]
                with open(file_path, "wb") as f:
                    f.write(base64.b64decode(base64_data))
            
            messagebox.showinfo("成功", f"图片已保存到: {file_path}")
            
        except Exception as e:
            messagebox.showerror("保存失败", f"保存图片时出错: {str(e)}")
    
    def open_generated_image(self):
        """在默认图片查看器中打开生成的图片"""
        # 检查是否已生成图片
        if not self.current_image_data:
            messagebox.showwarning("提示", "请先生成一张图片！")
            return
        
        try:
            # 保存图片
            if self.current_image_data.startswith("http"):
                # 如果是URL，直接在浏览器中打开
                webbrowser.open(self.current_image_data)
                return
            
            # 创建临时文件
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_file.close()
            
            # 保存图片到临时文件
            base64_data = self.current_image_data.split(",")[1]
            with open(temp_file.name, "wb") as f:
                f.write(base64.b64decode(base64_data))
            
            # 在默认应用中打开图片
            if os.name == 'nt':  # Windows
                os.startfile(temp_file.name)
            elif os.name == 'posix':  # macOS, Linux
                import subprocess
                if os.uname().sysname == 'Darwin':  # macOS
                    subprocess.call(('open', temp_file.name))
                else:  # Linux
                    subprocess.call(('xdg-open', temp_file.name))
            
        except Exception as e:
            messagebox.showerror("打开失败", f"打开图片时出错: {str(e)}")
    
    def clear_generation(self):
        """清空生成相关内容"""
        def fade_out():
            self.prompt_textbox.clear()
            self.generation_image_label.configure(image=None, text="未生成图片")
            self.current_image_data = None
        
        # 添加淡出效果
        self.app.after(100, fade_out)
    
    def resize_image(self, image, max_size):
        """调整图片大小，保持宽高比"""
        width, height = image.size
        
        # 计算缩放比例
        if width > height:
            ratio = max_size[0] / width
        else:
            ratio = max_size[1] / height
        
        # 计算新尺寸
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        
        # 调整大小
        return image.resize((new_width, new_height), Image.LANCZOS)
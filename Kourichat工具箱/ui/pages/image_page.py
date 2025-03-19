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
from api.tester import APITester
from core.error_handler import handle_api_error

class ImagePage:
    """图片页面类"""
    
    def __init__(self, app):
        self.app = app
        self.current_image_path = None
        self.current_image_data = None
        self.setup_image_page()
    
    def setup_image_page(self):
        """设置图片页面内容"""
        # 页面标题
        title_label = ctk.CTkLabel(
            self.app.image_frame, 
            text="图片功能", 
            font=self.app.title_font
        )
        title_label.pack(pady=(20, 20))
        
        # 创建选项卡控件
        self.tabview = ctk.CTkTabview(self.app.image_frame)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 添加选项卡
        self.tabview.add("图片识别")
        self.tabview.add("图片生成")
        
        # 设置各个选项卡内容
        self.setup_recognition_tab(self.tabview.tab("图片识别"))
        self.setup_generation_tab(self.tabview.tab("图片生成"))
    
    def setup_recognition_tab(self, parent_frame):
        """设置图片识别选项卡内容"""
        # 创建左右分栏
        content_frame = ctk.CTkFrame(parent_frame)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 配置网格布局
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # 左侧图片区域
        image_frame = ctk.CTkFrame(content_frame)
        image_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # 右侧结果区域
        result_frame = ctk.CTkFrame(content_frame)
        result_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # 设置左侧图片区域
        self.setup_recognition_image_area(image_frame)
        
        # 设置右侧结果区域
        self.setup_recognition_result_area(result_frame)
    
    def setup_recognition_image_area(self, parent_frame):
        """设置图片识别的图片区域"""
        # 标题
        image_title = ctk.CTkLabel(
            parent_frame, 
            text="上传图片", 
            font=ctk.CTkFont(family="Arial Unicode MS", size=14, weight="bold")
        )
        image_title.pack(pady=(10, 5))
        
        # 图片显示区域
        self.recognition_image_label = ctk.CTkLabel(
            parent_frame, 
            text="未选择图片",
            font=self.app.default_font,
            width=300,
            height=300
        )
        self.recognition_image_label.pack(pady=10)
        
        # 按钮框架
        button_frame = ctk.CTkFrame(parent_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # 选择图片按钮
        select_button = ctk.CTkButton(
            button_frame, 
            text="选择图片", 
            command=self.select_image_for_recognition,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        select_button.pack(side="left", padx=10, pady=10)
        
        # 识别图片按钮
        recognize_button = ctk.CTkButton(
            button_frame, 
            text="识别图片", 
            command=self.recognize_image,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        recognize_button.pack(side="left", padx=10, pady=10)
        
        # 清空按钮
        clear_button = ctk.CTkButton(
            button_frame, 
            text="清空", 
            command=self.clear_recognition,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        clear_button.pack(side="left", padx=10, pady=10)
    
    def setup_recognition_result_area(self, parent_frame):
        """设置图片识别的结果区域"""
        # 标题
        result_title = ctk.CTkLabel(
            parent_frame, 
            text="识别结果", 
            font=ctk.CTkFont(family="Arial Unicode MS", size=14, weight="bold")
        )
        result_title.pack(pady=(10, 5))
        
        # 结果文本框
        self.recognition_result_text = ScrollableTextBox(parent_frame)
        self.recognition_result_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 复制按钮
        copy_button = ctk.CTkButton(
            parent_frame, 
            text="复制结果", 
            command=self.copy_recognition_result,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        copy_button.pack(pady=(0, 10))
    
    def setup_generation_tab(self, parent_frame):
        """设置图片生成选项卡内容"""
        # 创建上下分栏
        content_frame = ctk.CTkFrame(parent_frame)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 配置网格布局
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=0)  # 输入区域不需要扩展
        content_frame.grid_rowconfigure(1, weight=1)  # 图片区域可以扩展
        
        # 上方输入区域
        input_frame = ctk.CTkFrame(content_frame)
        input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        # 下方图片区域
        image_frame = ctk.CTkFrame(content_frame)
        image_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        # 设置上方输入区域
        self.setup_generation_input_area(input_frame)
        
        # 设置下方图片区域
        self.setup_generation_image_area(image_frame)
    
    def setup_generation_input_area(self, parent_frame):
        """设置图片生成的输入区域"""
        # 标题
        input_title = ctk.CTkLabel(
            parent_frame, 
            text="输入图片描述", 
            font=ctk.CTkFont(family="Arial Unicode MS", size=14, weight="bold")
        )
        input_title.pack(pady=(10, 5))
        
        # 描述输入框
        self.generation_prompt_text = ctk.CTkTextbox(
            parent_frame, 
            height=100, 
            font=self.app.default_font,
            wrap="word"
        )
        self.generation_prompt_text.pack(fill="x", padx=10, pady=(0, 10))
        
        # 尺寸选择框架
        size_frame = ctk.CTkFrame(parent_frame)
        size_frame.pack(fill="x", padx=10, pady=5)
        
        # 尺寸选择标签
        size_label = ctk.CTkLabel(
            size_frame, 
            text="图片尺寸:", 
            font=self.app.default_font
        )
        size_label.pack(side="left", padx=10)
        
        # 尺寸选择下拉菜单
        self.generation_size_var = ctk.StringVar(value="1024x1024")
        size_options = ["256x256", "512x512", "1024x1024"]
        
        size_dropdown = ctk.CTkOptionMenu(
            size_frame, 
            variable=self.generation_size_var,
            values=size_options,
            font=self.app.default_font,
            fg_color=self.app.purple_color,
            button_color=self.app.purple_color,
            button_hover_color=self.app.purple_hover_color
        )
        size_dropdown.pack(side="left", padx=10)
        
        # 按钮框架
        button_frame = ctk.CTkFrame(parent_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # 生成图片按钮
        generate_button = ctk.CTkButton(
            button_frame, 
            text="生成图片", 
            command=self.generate_image,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        generate_button.pack(side="left", padx=10, pady=10)
        
        # 清空按钮
        clear_button = ctk.CTkButton(
            button_frame, 
            text="清空", 
            command=self.clear_generation,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        clear_button.pack(side="left", padx=10, pady=10)
    
    def setup_generation_image_area(self, parent_frame):
        """设置图片生成的图片区域"""
        # 标题
        image_title = ctk.CTkLabel(
            parent_frame, 
            text="生成结果", 
            font=ctk.CTkFont(family="Arial Unicode MS", size=14, weight="bold")
        )
        image_title.pack(pady=(10, 5))
        
        # 图片显示区域
        self.generation_image_label = ctk.CTkLabel(
            parent_frame, 
            text="未生成图片",
            font=self.app.default_font,
            width=400,
            height=400
        )
        self.generation_image_label.pack(expand=True, pady=10)
        
        # 按钮框架
        button_frame = ctk.CTkFrame(parent_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # 保存图片按钮
        save_button = ctk.CTkButton(
            button_frame, 
            text="保存图片", 
            command=self.save_generated_image,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        save_button.pack(side="left", padx=10, pady=10)
        
        # 打开图片按钮
        open_button = ctk.CTkButton(
            button_frame, 
            text="打开图片", 
            command=self.open_generated_image,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        open_button.pack(side="left", padx=10, pady=10)
    
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
        
        # 显示识别中提示
        self.recognition_result_text.set_text("正在识别图片，请稍候...")
        
        # 创建API测试器
        api_tester = APITester(url, api_key, model)
        
        # 在后台线程中识别图片
        def recognize_in_thread():
            try:
                # 识别图片
                result = api_tester.recognize_image(self.current_image_path)
                
                # 更新UI
                self.app.after(0, lambda: self.recognition_result_text.set_text(result))
                
            except Exception as e:
                error_msg = handle_api_error(e, "图片识别API")
                self.app.after(0, lambda: self.recognition_result_text.set_text(error_msg))
        
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
    
    # 图片生成相关函数
    def generate_image(self):
        """生成图片"""
        # 获取图片描述
        prompt = self.generation_prompt_text.get("1.0", "end-1c").strip()
        if not prompt:
            messagebox.showwarning("提示", "请输入图片描述！")
            return
        
        # 获取图片尺寸
        size = self.generation_size_var.get()
        
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
        self.generation_image_label.configure(image=None, text="正在生成图片，请稍候...")
        
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
                
                # 更新UI
                self.app.after(0, lambda: self.generation_image_label.configure(image=ctk_image, text=""))
                
                # 保存图片引用，防止被垃圾回收
                self.app.after(0, lambda: setattr(self.generation_image_label, "image", ctk_image))
                
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
        self.generation_prompt_text.delete("1.0", "end")
        self.generation_image_label.configure(image=None, text="未生成图片")
        self.current_image_data = None
    
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
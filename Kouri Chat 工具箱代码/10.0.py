import json
import requests
import logging
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
from PIL import Image, ImageTk
import io
import webbrowser
import os
import tkhtmlview  
import base64  
import re  
import platform
import winreg

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class APIConfig:
    @staticmethod
    def read_config():
        try:
            with open('api_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"real_server_base_url": "https://api.siliconflow.cn/", "api_key": "", "model": "deepseek-ai/DeepSeek-V3", "messages": [], "image_config": {"generate_size": "512x512"}, "theme": "light"}
        except json.JSONDecodeError:
            messagebox.showerror("配置文件错误", "配置格式错误，请检查格式。")
            return {"real_server_base_url": "https://api.siliconflow.cn/", "api_key": "", "model": "deepseek-ai/DeepSeek-V3", "messages": [], "image_config": {"generate_size": "512x512"}, "theme": "light"}

    @staticmethod
    def save_config(config):
        with open('api_config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)

class APITester:
    def __init__(self, base_url, api_key, model, image_config=None):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.image_config = image_config or {"generate_size": "512x512"}

    def test_standard_api(self):
        """测试标准API连接"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, are you working?"}
            ]
        }
        
        response = requests.post(
            f"{self.base_url.rstrip('/')}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=10
        )
        
        return response
    
    def recognize_image(self, base64_image):
        """识别图片内容"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that can analyze images."},
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": "请描述这张图片的内容。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ]
        }
        
        response = requests.post(
            f"{self.base_url.rstrip('/')}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30  # 图片识别可能需要更长时间
        )
        
        return response
    
    def generate_image(self, prompt, size):
        """生成图片"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": size
        }
        
        response = requests.post(
            f"{self.base_url.rstrip('/')}/v1/images/generations",
            headers=headers,
            json=data,
            timeout=30  # 图片生成可能需要更长时间
        )
        
        return response

    def generate_character_profile(self, character_desc):
        prompt = f"请根据以下描述生成一个详细的角色人设，要贴合实际，至少1000字，包含以下内容：\n1. 角色名称\n2. 性格特点\n3. 外表特征\n4. 时代背景\n5. 人物经历\n描述：{character_desc}\n请以清晰的格式返回。"
        data = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        response = requests.post(f'{self.base_url}/v1/chat/completions', headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {self.api_key}'}, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def polish_character_profile(self, profile, polish_desc):
        prompt = f"请根据以下要求润色角色人设：\n润色要求：{polish_desc}\n人设内容：{profile}\n请返回润色后的完整人设。修改的内容至少500字"
        data = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        response = requests.post(f'{self.base_url}/v1/chat/completions', headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {self.api_key}'}, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

def handle_api_error(e, server_type):
    error_msg = f"警告：访问{server_type}遇到问题："
    if isinstance(e, requests.exceptions.ConnectionError):
        error_msg += "网络连接失败\n🔧 请检查：1.服务器是否启动 2.地址端口是否正确 3.网络是否通畅 4.防火墙设置"
    elif isinstance(e, requests.exceptions.Timeout):
        error_msg += "请求超时\n🔧 建议：1.稍后重试 2.检查网络速度 3.确认服务器负载情况"
    elif isinstance(e, requests.exceptions.SSLError):
        error_msg += "SSL证书验证失败\n🔧 请尝试：1.更新根证书 2.临时关闭证书验证（测试环境）"
    elif isinstance(e, requests.exceptions.HTTPError):
        status_code = e.response.status_code
        common_solution = "\n💡 解决方法：查看API文档，确认请求参数格式和权限设置"
        status_map = {
            400: ("请求格式错误", "检查JSON格式、参数名称和数据类型"),
            401: ("身份验证失败", "1.确认API密钥 2.检查授权头格式"),
            403: ("访问被拒绝", "确认账户权限或套餐是否有效"),
            404: ("接口不存在", "检查URL地址和接口版本号"),
            429: ("请求过于频繁", "降低调用频率或升级套餐"),
            500: ("服务器内部错误", "等待5分钟后重试，若持续报错请联系服务商"),
            502: ("网关错误", "服务器端网络问题，建议等待后重试"),
            503: ("服务不可用", "服务器维护中，请关注官方状态页")
        }
        desc, solution = status_map.get(status_code, (f"HTTP {status_code}错误", "查看对应状态码文档"))
        error_msg += f"{desc}\n🔧 {solution}{common_solution}"
    elif isinstance(e, ValueError) and 'Incorrect padding' in str(e):
        error_msg += "API密钥格式错误\n🔧 请检查密钥是否完整（通常以'sk-'开头，共64字符）"
    else:
        error_msg += f"未知错误：{type(e).__name__}\n🔧 建议：1.查看错误详情 2.联系技术支持"
    logging.error(error_msg)
    return error_msg

def test_servers():
    config = APIConfig.read_config()
    if not config.get("real_server_base_url") or not config.get("api_key") or not config.get("model"):
        messagebox.showwarning("配置错误", "请填写URL地址、API 密钥和模型名称！")
        return

    real_tester = APITester(config.get('real_server_base_url'), config.get('api_key'), config.get('model'), config.get('image_config'))

    try:
        start_time = time.time()
        logging.info("正在测试连接时间...")
        response = requests.get(config.get('real_server_base_url'), timeout=5)
        end_time = time.time()
        connection_time = round((end_time - start_time) * 1000, 2)
        logging.info(f"连接成功，响应时间: {connection_time} ms")

        logging.info("正在向实际 AI 对话服务器发送请求...")
        response = real_tester.test_standard_api()
        if response is None:
            error_msg = "实际服务器返回空响应，请检查服务器状态或请求参数"
            logging.error(error_msg)
            return error_msg
        if response.status_code != 200:
            error_msg = f"服务器返回异常状态码: {response.status_code}，错误信息: {response.text}"
            logging.error(error_msg)
            return error_msg
        response_text = response.text
        logging.info(f"实际 AI 对话服务器原始响应: {response_text}")
        try:
            response_json = response.json()
            logging.info(f"标准 API 端点响应: {response_json}")
            success_msg = f"实际 AI 对话服务器响应正常，连接时间: {connection_time} ms。\n响应内容:\n{response_json}"
            logging.info(success_msg)
            return success_msg
        except ValueError as json_error:
            error_msg = f"解析实际 AI 对话服务器响应时出现 JSON 解析错误: {json_error}。响应内容: {response_text}"
            logging.error(error_msg)
            return error_msg
    except Exception as e:
        return handle_api_error(e, "实际 AI 对话服务器")

class KouriChatToolbox:
    def __init__(self, root):
        self.root = root
        self.root.title("Kouri Chat 工具箱V10.0")  # 更新版本号
        self.root.geometry("1000x700")
        
        # 设置全局字体
        self.default_font = ("黑体", 10)
        
        # 主题设置
        self.theme_colors = {
            "light": {
                "bg": "#ffffff",
                "fg": "#000000",
                "console_bg": "#f9f9f9",
                "console_fg": "#000000",
                "highlight_bg": "#e0e0e0",
                "sidebar_bg": "#f0f0f0",
                "sidebar_fg": "#000000",
                "sidebar_active": "#d0d0d0"
            },
            "dark": {
                "bg": "#2d2d2d",
                "fg": "#ffffff",
                "console_bg": "#1e1e1e",
                "console_fg": "#ffffff",
                "highlight_bg": "#3d3d3d",
                "sidebar_bg": "#333333",
                "sidebar_fg": "#ffffff",
                "sidebar_active": "#444444"
            },
            "system": None  # 将根据系统设置动态确定
        }
        
        self.current_theme = "light"  # 默认主题
        self.apply_font_settings()
        
        # 创建主框架
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)
        
        # 创建侧边栏和内容区域
        self.setup_sidebar()
        self.setup_content_area()
        
        self.generated_profile = None
        self.load_config()
        self.apply_theme()
        
        # 默认显示人设页面
        self.show_character_page()

    def apply_font_settings(self):
        # 设置应用程序的默认字体
        self.root.option_add("*Font", self.default_font)
        
        # 为tk部件设置字体
        style = ttk.Style()
        style.configure("TLabel", font=self.default_font)
        style.configure("TButton", font=self.default_font)
        style.configure("TEntry", font=self.default_font)
        style.configure("TCheckbutton", font=self.default_font)
        style.configure("TRadiobutton", font=self.default_font)
        style.configure("TCombobox", font=self.default_font)

    def apply_theme(self, theme=None):
        """应用主题到界面"""
        # 如果没有指定主题，则使用当前主题
        if theme is None:
            # 获取当前主题颜色
            config = APIConfig.read_config()
            self.current_theme = config.get("theme", "light")
        else:
            self.current_theme = theme
        
        # 如果是系统主题，则检测系统设置
        if self.current_theme == "system":
            system_theme = self.detect_system_theme()
            colors = self.theme_colors[system_theme]
        else:
            colors = self.theme_colors[self.current_theme]
        
        # 更新根窗口背景色
        self.root.configure(background=colors["bg"])
        
        # 递归更新所有部件的颜色
        self._update_widget_colors(self.root, colors)
        
        # 更新侧边栏颜色
        self.sidebar_frame.configure(bg=colors["sidebar_bg"])
        for button in self.sidebar_buttons:
            button.configure(
                bg=colors["sidebar_bg"],
                fg=colors["sidebar_fg"],
                activebackground=colors.get("sidebar_active", colors["highlight_bg"]),
                activeforeground=colors["sidebar_fg"]
            )

    def _update_widget_colors(self, widget, colors):
        """递归更新所有部件的颜色"""
        try:
            widget_type = widget.winfo_class()
            
            # 根据部件类型设置颜色
            if widget_type in ("Frame", "Labelframe"):
                widget.configure(background=colors["bg"])
                if widget_type == "Labelframe":
                    widget.configure(foreground=colors["fg"])
            
            elif widget_type == "Label":
                widget.configure(background=colors["bg"], foreground=colors["fg"])
            
            elif widget_type == "Button":
                widget.configure(
                    background=colors["highlight_bg"],
                    foreground=colors["fg"],
                    activebackground=colors["highlight_bg"],
                    activeforeground=colors["fg"]
                )
            
            elif widget_type == "Entry":
                widget.configure(
                    background=colors["console_bg"],
                    foreground=colors["fg"],
                    insertbackground=colors["fg"]  # 光标颜色
                )
            
            # 递归处理所有子部件
            for child in widget.winfo_children():
                self._update_widget_colors(child, colors)
        except:
            # 忽略无法设置颜色的部件
            pass

    def setup_sidebar(self):
        # 创建侧边栏框架
        self.sidebar_frame = tk.Frame(self.main_frame, width=150)
        self.sidebar_frame.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar_frame.pack_propagate(False)  # 防止框架缩小
        
        # 创建侧边栏按钮
        self.sidebar_buttons = []
        
        # 添加应用标题
        title_label = tk.Label(self.sidebar_frame, text="Kouri Chat", font=("黑体", 14, "bold"))
        title_label.pack(pady=(20, 30))
        
        # 添加侧边栏按钮
        sidebar_items = [
            ("人设", self.show_character_page),
            ("API配置", self.show_api_config_page),
            ("图片", self.show_image_page),
            ("主题", self.show_theme_page),
            ("帮助", self.show_help_page)
        ]
        
        for text, command in sidebar_items:
            btn = tk.Button(
                self.sidebar_frame, 
                text=text, 
                font=("黑体", 12),
                bd=0,  # 无边框
                padx=10,
                pady=8,
                anchor="w",
                width=12,
                command=command
            )
            btn.pack(fill="x", padx=0, pady=5)
            self.sidebar_buttons.append(btn)

    def setup_content_area(self):
        # 创建内容区域框架
        self.content_frame = tk.Frame(self.main_frame)
        self.content_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        # 创建各个页面的框架
        self.character_frame = tk.Frame(self.content_frame)
        self.api_config_frame = tk.Frame(self.content_frame)
        self.image_frame = tk.Frame(self.content_frame)
        self.theme_frame = tk.Frame(self.content_frame)
        self.help_frame = tk.Frame(self.content_frame)
        
        # 设置各个页面的内容
        self.setup_character_page()
        self.setup_api_config_page()
        self.setup_image_page()
        self.setup_theme_page()
        self.setup_help_page()

    def clear_content_frame(self):
        # 隐藏所有页面
        for frame in [self.character_frame, self.api_config_frame, self.image_frame, self.theme_frame, self.help_frame]:
            frame.pack_forget()

    def show_character_page(self):
        self.clear_content_frame()
        self.character_frame.pack(fill="both", expand=True)

    def show_api_config_page(self):
        self.clear_content_frame()
        self.api_config_frame.pack(fill="both", expand=True)

    def show_image_page(self):
        self.clear_content_frame()
        self.image_frame.pack(fill="both", expand=True)

    def show_theme_page(self):
        self.clear_content_frame()
        self.theme_frame.pack(fill="both", expand=True)

    def show_help_page(self):
        self.clear_content_frame()
        self.help_frame.pack(fill="both", expand=True)

    def load_config(self):
        """加载配置到UI"""
        config = APIConfig.read_config()
        
        # 加载人设API配置
        character_config = config.get("character_api", {})
        if hasattr(self, 'character_url_entry'):
            self.character_url_entry.delete(0, tk.END)
            self.character_url_entry.insert(0, character_config.get("url", config.get("real_server_base_url", "")))
            
            self.character_key_entry.delete(0, tk.END)
            self.character_key_entry.insert(0, character_config.get("api_key", config.get("api_key", "")))
            
            self.character_model_entry.delete(0, tk.END)
            self.character_model_entry.insert(0, character_config.get("model", config.get("model", "")))
        
        # 加载图片识别API配置
        recognition_config = config.get("recognition_api", {})
        if hasattr(self, 'recognition_url_entry'):
            self.recognition_url_entry.delete(0, tk.END)
            self.recognition_url_entry.insert(0, recognition_config.get("url", config.get("real_server_base_url", "")))
            
            self.recognition_key_entry.delete(0, tk.END)
            self.recognition_key_entry.insert(0, recognition_config.get("api_key", config.get("api_key", "")))
            
            self.recognition_model_entry.delete(0, tk.END)
            self.recognition_model_entry.insert(0, recognition_config.get("model", config.get("model", "")))
        
        # 加载图片生成API配置
        generation_config = config.get("generation_api", {})
        if hasattr(self, 'generation_url_entry'):
            self.generation_url_entry.delete(0, tk.END)
            self.generation_url_entry.insert(0, generation_config.get("url", config.get("real_server_base_url", "https://api.siliconflow.cn/")))
            
            self.generation_key_entry.delete(0, tk.END)
            self.generation_key_entry.insert(0, generation_config.get("api_key", config.get("api_key", "")))
            
            self.generation_model_entry.delete(0, tk.END)
            self.generation_model_entry.insert(0, generation_config.get("model", config.get("model", "")))
        
        # 加载图片尺寸设置
        if hasattr(self, 'image_size_var'):
            image_size = generation_config.get("generate_size", 
                                              config.get("image_config", {}).get("generate_size", "512x512"))
        self.image_size_var.set(image_size)
        
        # 加载主题设置
        self.current_theme = config.get("theme", "light")

    def save_config(self):
        config = {
            "real_server_base_url": self.server_url_entry.get(),
            "api_key": self.api_key_entry.get(),
            "model": self.model_entry.get(),
            "image_config": {"generate_size": "512x512"},
            "theme": self.current_theme
        }
        APIConfig.save_config(config)
        messagebox.showinfo("保存成功", "配置已保存！")

    def change_theme(self, theme_name):
        """切换主题"""
        theme = theme_name.lower()
        if theme == "system":
            # 获取系统主题
            actual_theme = self.detect_system_theme()
        else:
            actual_theme = theme
        
        # 应用主题
        self.apply_theme(theme)
        
        # 更新预览
        for widget in self.theme_frame.winfo_children():
            if isinstance(widget, tk.LabelFrame) and widget.cget("text") == "主题预览":
                preview_frame = widget
                preview_title = None
                preview_text = None
                preview_button = None
                preview_entry = None
                
                for child in preview_frame.winfo_children():
                    if isinstance(child, tk.Label) and child.cget("text") == "这是标题文本":
                        preview_title = child
                    elif isinstance(child, tk.Label) and "示例" in child.cget("text"):
                        preview_text = child
                    elif isinstance(child, tk.Button):
                        preview_button = child
                    elif isinstance(child, tk.Entry):
                        preview_entry = child
                
                if all([preview_title, preview_text, preview_button, preview_entry]):
                    self.update_preview_colors(preview_frame, preview_title, preview_text, preview_button, preview_entry)
        
        # 显示主题切换提示
        theme_names = {"light": "亮色", "dark": "暗色", "system": "系统"}
        messagebox.showinfo("主题设置", f"已切换到{theme_names[theme]}主题")

    def copy_console_content(self):
        # 获取当前HTML内容并提取纯文本
        html_content = self.log_text.html
        
        # 创建一个临时的HTML解析器来提取文本
        from html.parser import HTMLParser
        
        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
                
            def handle_data(self, data):
                self.text.append(data)
                
            def get_text(self):
                return ''.join(self.text)
        
        parser = TextExtractor()
        parser.feed(html_content)
        text_content = parser.get_text()
        
        # 复制到剪贴板
        self.root.clipboard_clear()
        self.root.clipboard_append(text_content)
        messagebox.showinfo("复制成功", "控制台内容已复制到剪贴板")

    def run_test(self):
        self.api_result_text.set_html("<p style='font-family:黑体;'>开始测试...</p>")
        result = test_servers()
        # 将结果转换为HTML格式
        html_result = f"<p style='font-family:黑体;'>测试结果:</p><pre style='font-family:黑体;'>{result}</pre>"
        self.api_result_text.set_html(html_result)

    def generate_character(self):
        character_desc = self.character_desc_entry.get()
        if not character_desc:
            messagebox.showwarning("输入错误", "请输入角色描述！")
            return

        config = APIConfig.read_config()
        tester = APITester(config.get('real_server_base_url'), config.get('api_key'), config.get('model'))

        try:
            self.set_html("<p style='font-family:黑体;'>正在生成角色人设...</p>")
            self.generated_profile = tester.generate_character_profile(character_desc)
            # 将生成的人设转换为HTML格式
            html_profile = f"<p style='font-family:黑体;'>角色人设生成成功！</p><pre style='font-family:黑体;'>{self.generated_profile}</pre>"
            self.set_html(html_profile)
        except Exception as e:
            error_msg = handle_api_error(e, "生成人设")
            self.set_html(f"<p style='font-family:黑体;'>生成失败:</p><pre style='font-family:黑体;'>{error_msg}</pre>")

    def import_profile(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")], title="选择人设文件")
        if not file_path:
            return

        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:
            messagebox.showwarning("文件过大", "文件大小超过 10MB，请选择较小的文件！")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.generated_profile = f.read()
            messagebox.showinfo("导入成功", "人设文件已导入！")
            # 将导入的人设转换为HTML格式
            html_profile = f"<p style='font-family:黑体;'>导入的人设内容:</p><pre style='font-family:黑体;'>{self.generated_profile}</pre>"
            self.log_text.set_html(html_profile)
        except Exception as e:
            messagebox.showerror("导入失败", f"导入文件时出错：{e}")

    def export_profile(self):
        if not self.generated_profile:
            messagebox.showwarning("导出失败", "请先生成或导入角色人设！")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")], title="保存人设文件")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.generated_profile)
                messagebox.showinfo("导出成功", f"角色人设已导出到: {file_path}")
            except Exception as e:
                messagebox.showerror("导出失败", f"导出文件时出错：{e}")

    def polish_character(self):
        if not self.generated_profile:
            messagebox.showwarning("润色失败", "请先生成或导入角色人设！")
            return

        polish_desc = self.polish_desc_entry.get()
        if not polish_desc:
            messagebox.showwarning("输入错误", "请输入润色要求！")
            return

        config = APIConfig.read_config()
        tester = APITester(config.get('real_server_base_url'), config.get('api_key'), config.get('model'))

        try:
            self.set_html("<p style='font-family:黑体;'>正在润色角色人设...</p>")
            self.generated_profile = tester.polish_character_profile(self.generated_profile, polish_desc)
            # 将润色后的人设转换为HTML格式
            html_profile = f"<p style='font-family:黑体;'>角色人设润色成功！</p><pre style='font-family:黑体;'>{self.generated_profile}</pre>"
            self.set_html(html_profile)
        except Exception as e:
            error_msg = handle_api_error(e, "润色人设")
            self.set_html(f"<p style='font-family:黑体;'>润色失败:</p><pre style='font-family:黑体;'>{error_msg}</pre>")

    def recognize_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.jpeg *.png")], title="选择图片文件")
        if not file_path:
            return

        config = APIConfig.read_config()
        tester = APITester(config.get('real_server_base_url'), config.get('api_key'), config.get('model'))

        try:
            self.image_result_text.set_html("<p style='font-family:黑体;'>正在识别图片...</p>")
            result = tester.recognize_image(file_path)
            
            # 从响应中提取文本内容
            content = result["choices"][0]["message"]["content"]
            
            # 将图片和识别结果一起显示在HTML中
            with open(file_path, 'rb') as img_file:
                img_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            # 获取当前主题颜色
            if self.current_theme == "system":
                try:
                    import darkdetect
                    system_theme = "dark" if darkdetect.isDark() else "light"
                except ImportError:
                    system_theme = "light"
                colors = self.theme_colors[system_theme]
            else:
                colors = self.theme_colors[self.current_theme]
            
            # 将样式放在style标签中，不在内容中显示CSS代码
            html_result = f"""
            <style>
            body {{ background-color: {colors['console_bg']}; color: {colors['console_fg']}; }}
            </style>
            <h3 style='font-family:黑体;'>图片识别结果:</h3>
            <div style="text-align:center;margin-bottom:10px;">
                <img src="data:image/jpeg;base64,{img_data}" style="max-width:400px;max-height:300px;">
            </div>
            <div style="border:1px solid #ccc;padding:10px;background-color:{colors['highlight_bg']};">
                <p style='font-family:黑体;'>{content}</p>
            </div>
            """
            self.image_result_text.set_html(html_result)
        except Exception as e:
            error_msg = handle_api_error(e, "图片识别")
            self.image_result_text.set_html(f"<p style='font-family:黑体;'>图片识别失败:</p><p style='font-family:黑体;'>{error_msg}</p>")

    def generate_image(self):
        """生成图片"""
        # 获取提示词
        prompt = self.generation_prompt_text.get(1.0, tk.END).strip()
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
            self.generation_image_label.config(text="正在生成图片，请稍候...")
            self.generation_image_label.update()
            
            # 创建API请求
            tester = APITester(url, api_key, model)
            response = tester.generate_image(prompt, size)
            
            if response and response.status_code == 200:
                result = response.json()
                if "images" in result and len(result["images"]) > 0 and "url" in result["images"][0]:
                    image_url = result["images"][0]["url"]
                    
                    # 下载图片
                    image_response = requests.get(image_url)
                    if image_response.status_code == 200:
                        # 将图片数据转换为PIL图像
                        image = Image.open(io.BytesIO(image_response.content))
                        
                        # 保存原始图像用于后续保存
                        self.generated_image = image
                        
                        # 调整图片大小以适应预览区域
                        display_image = self.resize_image(image, 300)
                        photo = ImageTk.PhotoImage(display_image)
                        
                        # 更新预览标签
                        self.generation_image_label.config(image=photo, text="")
                        self.generation_image_label.image = photo  # 保持引用
                        
                        # 启用保存按钮
                        self.save_image_button.config(state="normal")
                    else:
                        self.generation_image_label.config(text=f"下载图片失败: {image_response.status_code}")
                else:
                    self.generation_image_label.config(text="无法解析生成结果，请检查API响应格式。")
            else:
                self.generation_image_label.config(text=f"生成失败: {response.text if response else '无响应'}")
        
        except Exception as e:
            error_msg = handle_api_error(e, "图片生成")
            self.generation_image_label.config(text=f"生成出错: {error_msg}")

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

    def resize_image(self, image, max_size):
        """调整图片大小，保持宽高比"""
        width, height = image.size
        if width > height:
            new_width = max_size
            new_height = int(height * max_size / width)
        else:
            new_height = max_size
            new_width = int(width * max_size / height)
        
        return image.resize((new_width, new_height), Image.LANCZOS)

    def copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("提示", "内容已复制到剪贴板！")

    def setup_theme_page(self):
        """设置主题页面"""
        # 创建主题页面的标题
        page_title = tk.Label(self.theme_frame, text="主题设置", font=("黑体", 16, "bold"))
        page_title.pack(pady=(0, 20))
        
        # 创建主题选择框架
        theme_selection_frame = tk.Frame(self.theme_frame)
        theme_selection_frame.pack(pady=20)
        
        # 主题选择标签
        tk.Label(theme_selection_frame, text="选择主题:", font=("黑体", 12)).pack(side="left", padx=10)
        
        # 主题选择下拉菜单
        self.theme_var = tk.StringVar(value=self.current_theme.capitalize())
        themes = ["Light", "Dark", "System"]
        theme_dropdown = tk.OptionMenu(theme_selection_frame, self.theme_var, *themes, command=self.change_theme)
        theme_dropdown.pack(side="left", padx=10)
        
        # 主题预览框架
        preview_frame = tk.LabelFrame(self.theme_frame, text="主题预览", padx=20, pady=20, font=self.default_font)
        preview_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 预览内容
        preview_title = tk.Label(preview_frame, text="这是标题文本", font=("黑体", 14, "bold"))
        preview_title.pack(pady=10)
        
        preview_text = tk.Label(preview_frame, text="这是正文文本示例，用于展示不同主题下的文本显示效果。", font=self.default_font)
        preview_text.pack(pady=10)
        
        preview_button = tk.Button(preview_frame, text="示例按钮", font=self.default_font)
        preview_button.pack(pady=10)
        
        preview_entry = tk.Entry(preview_frame, font=self.default_font)
        preview_entry.insert(0, "输入框示例")
        preview_entry.pack(pady=10)
        
        # 保存主题设置按钮
        save_button = tk.Button(self.theme_frame, text="保存主题设置", command=self.save_theme_settings, font=self.default_font)
        save_button.pack(pady=20)
        
        # 更新预览框架的颜色
        self.update_preview_colors(preview_frame, preview_title, preview_text, preview_button, preview_entry)

    def update_preview_colors(self, frame, title, text, button, entry):
        """更新预览框架的颜色"""
        theme = self.theme_var.get().lower()
        if theme == "system":
            # 获取系统主题
            theme = self.detect_system_theme()
        
        colors = self.theme_colors.get(theme, self.theme_colors["light"])
        
        frame.config(bg=colors["bg"])
        title.config(bg=colors["bg"], fg=colors["fg"])
        text.config(bg=colors["bg"], fg=colors["fg"])
        button.config(bg=colors["highlight_bg"], fg=colors["fg"])
        entry.config(bg=colors["console_bg"], fg=colors["console_fg"])

    def change_theme(self, theme_name):
        """切换主题"""
        theme = theme_name.lower()
        if theme == "system":
            # 获取系统主题
            actual_theme = self.detect_system_theme()
        else:
            actual_theme = theme
        
        # 应用主题
        self.apply_theme(theme)
        
        # 更新预览
        for widget in self.theme_frame.winfo_children():
            if isinstance(widget, tk.LabelFrame) and widget.cget("text") == "主题预览":
                preview_frame = widget
                preview_title = None
                preview_text = None
                preview_button = None
                preview_entry = None
                
                for child in preview_frame.winfo_children():
                    if isinstance(child, tk.Label) and child.cget("text") == "这是标题文本":
                        preview_title = child
                    elif isinstance(child, tk.Label) and "示例" in child.cget("text"):
                        preview_text = child
                    elif isinstance(child, tk.Button):
                        preview_button = child
                    elif isinstance(child, tk.Entry):
                        preview_entry = child
                
                if all([preview_title, preview_text, preview_button, preview_entry]):
                    self.update_preview_colors(preview_frame, preview_title, preview_text, preview_button, preview_entry)
        
        # 显示主题切换提示
        theme_names = {"light": "亮色", "dark": "暗色", "system": "系统"}
        messagebox.showinfo("主题设置", f"已切换到{theme_names[theme]}主题")

    def save_theme_settings(self):
        """保存主题设置"""
        theme = self.theme_var.get().lower()
        self.current_theme = theme
        
        # 保存到配置文件
        config = APIConfig.read_config()
        config["theme"] = theme
        APIConfig.save_config(config)
        
        messagebox.showinfo("成功", "主题设置已保存！")

    def detect_system_theme(self):
        """检测系统主题"""
        try:
            if platform.system() == "Windows":
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return "light" if value == 1 else "dark"
        except Exception:
            return "light"  # 出错时默认为浅色主题

    def setup_help_page(self):
        """设置帮助页面"""
        # 创建帮助页面的标题
        page_title = tk.Label(self.help_frame, text="帮助与关于", font=("黑体", 16, "bold"))
        page_title.pack(pady=(0, 20))
        
        # 创建帮助内容框架
        help_content_frame = tk.Frame(self.help_frame)
        help_content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 使用HTML查看器显示帮助内容
        help_html = tkhtmlview.HTMLScrolledText(help_content_frame, html=self.get_help_content())
        help_html.pack(fill="both", expand=True)
        
        # 底部按钮框架
        button_frame = tk.Frame(self.help_frame)
        button_frame.pack(pady=20)
        
        # 访问官网按钮
        website_button = tk.Button(
            button_frame, 
            text="项目地址", 
            command=lambda: webbrowser.open("https://github.com/linxiajin08/linxiajinKouri"),
            font=self.default_font
        )
        website_button.pack(side="left", padx=10)
        
        # 检查更新按钮
        update_button = tk.Button(
            button_frame, 
            text="检查更新", 
            command=self.check_for_updates,
            font=self.default_font
        )
        update_button.pack(side="left", padx=10)
        
        # 联系我们按钮
        contact_button = tk.Button(
            button_frame, 
            text="联系我们", 
            command=self.show_qq_group,
            font=("黑体", 10)
        )
        contact_button.pack(side="left", padx=10)

    def show_qq_group(self):
        """显示QQ群号"""
        messagebox.showinfo("联系我们", "欢迎加入QQ交流群：639849597")

    def get_help_content(self):
        """获取帮助页面HTML内容"""
        return """
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <h2 style="color: #333;">Kouri Chat 工具箱 V10.0</h2>
            <p>这是一个功能强大的AI聊天和图像处理工具箱，帮助您轻松创建角色人设、识别图片内容和生成图片。</p>
            
            <h3 style="color: #555;">主要功能</h3>
            <ul>
                <li><b>角色人设创建</b> - 快速生成和润色角色人设，支持多种模型</li>
                <li><b>图片识别</b> - 上传图片并获取AI对图片内容的详细描述</li>
                <li><b>图片生成</b> - 通过文字提示生成各种风格的图片</li>
                <li><b>API配置</b> - 灵活配置不同的API服务，支持多种渠道</li>
                <li><b>主题设置</b> - 自定义界面主题，支持浅色、深色和跟随系统</li>
            </ul>
            
            <h3 style="color: #555;">使用指南</h3>
            <ol>
                <li>首先在"API配置"页面设置您的API密钥和服务地址</li>
                <li>在"角色人设"页面输入简短描述，点击生成获取详细人设</li>
                <li>在"图片功能"页面可以上传图片进行识别或生成新图片</li>
                <li>所有生成的内容都可以复制或保存到本地</li>
            </ol>
            
            <h3 style="color: #555;">常见问题</h3>
            <p><b>问：为什么API测试失败？</b><br>
            答：请检查您的API密钥是否正确，URL地址是否有效，以及网络连接是否正常。</p>
            
            <p><b>问：如何获取API密钥？</b><br>
            答：点击各API配置页面中的"申请密钥"按钮，访问相应服务商网站注册账号并获取API密钥。</p>
            
            <p><b>问：生成的内容质量不高怎么办？</b><br>
            答：尝试使用更详细的描述，或者选择更高级的模型。不同的模型在不同任务上表现各异。</p>
            
            <h3 style="color: #555;">关于我们</h3>
            <p>Kouri Chat 工具箱由Kouri团队开发，致力于为用户提供简单易用的AI工具。</p>
            <p>版本：V10.0</p>
            <p>版权所有 © 2023-2024 Kouri Team</p>
        </body>
        </html>
        """

    def check_for_updates(self):
        """检查更新"""
        current_version = "10.0"
        try:
            latest_version = "10.0"
            
            if latest_version > current_version:
                if messagebox.askyesno("发现新版本", f"发现新版本 V{latest_version}，当前版本 V{current_version}。\n是否前往下载？"):
                    webbrowser.open("https://www.kourichat.com/download")
            else:
                messagebox.showinfo("检查更新", "您已经使用最新版本！")
        except Exception as e:
            messagebox.showerror("检查更新失败", f"无法检查更新: {str(e)}")

    def save_character_config(self):
        """保存人设API配置"""
        config = APIConfig.read_config()
        
        # 获取模型名称
        model = self.character_model_var.get()
        if model == "自定义":
            model = self.character_model_entry.get()
        
        # 保存人设API配置
        config["character_api"] = {
            "url": self.character_url_entry.get(),
            "api_key": self.character_key_entry.get(),
            "model": model
        }
        
        # 更新主配置
        config["real_server_base_url"] = self.character_url_entry.get()
        config["api_key"] = self.character_key_entry.get()
        config["model"] = model
        
        APIConfig.save_config(config)
        messagebox.showinfo("保存成功", "人设API配置已保存！")

    def save_recognition_config(self):
        """保存图片识别API配置"""
        config = APIConfig.read_config()
        
        # 获取模型名称
        model = self.recognition_model_var.get()
        if model == "自定义":
            model = self.recognition_model_entry.get()
        
        # 保存图片识别API配置
        config["recognition_api"] = {
            "url": self.recognition_url_entry.get(),
            "api_key": self.recognition_key_entry.get(),
            "model": model
        }
        
        APIConfig.save_config(config)
        messagebox.showinfo("保存成功", "图片识别API配置已保存！")

    def save_generation_config(self):
        """保存图片生成API配置"""
        config = APIConfig.read_config()
        
        # 获取模型名称
        model = self.generation_model_var.get()
        if model == "自定义":
            model = self.generation_model_entry.get()
        
        # 获取图片尺寸
        size = self.image_size_var.get() if hasattr(self, 'image_size_var') else "1024x1024"
        
        # 保存图片生成API配置
        config["generation_api"] = {
            "url": self.generation_url_entry.get(),
            "api_key": self.generation_key_entry.get(),
            "model": model,
            "generate_size": size
        }
        
        # 更新图片尺寸配置
        config["image_config"] = {"generate_size": size}
        
        APIConfig.save_config(config)
        messagebox.showinfo("保存成功", "图片生成API配置已保存！")

    def save_all_configs(self):
        """保存所有API配置"""
        # 保存各个API配置
        self.save_character_config()
        self.save_recognition_config()
        self.save_generation_config()
        
        messagebox.showinfo("保存成功", "所有API配置已保存！")

    def setup_character_page(self):
        """设置角色人设页面"""
        # 创建角色人设页面的标题
        page_title = tk.Label(self.character_frame, text="角色人设生成", font=("黑体", 16, "bold"))
        page_title.pack(pady=(0, 20))
        
        # 创建输入框架
        input_frame = tk.Frame(self.character_frame)
        input_frame.pack(fill="x", padx=20, pady=10)
        
        # 角色描述标签
        tk.Label(input_frame, text="角色描述:", font=self.default_font).pack(anchor="w")
        
        # 角色描述输入框
        self.character_desc_text = scrolledtext.ScrolledText(
            input_frame, 
            width=60, 
            height=5, 
            font=self.default_font,
            wrap=tk.WORD
        )
        self.character_desc_text.pack(fill="x", pady=(0, 10))
        
        # 示例提示
        example_text = "示例: 一个生活在未来世界的女性科学家，性格坚毅，擅长解决问题。"
        tk.Label(input_frame, text=example_text, font=(self.default_font[0], 9), fg="gray").pack(anchor="w")
        
        # 按钮框架
        button_frame = tk.Frame(self.character_frame)
        button_frame.pack(pady=10)
        
        # 生成按钮
        generate_button = tk.Button(
            button_frame, 
            text="生成人设", 
            command=self.generate_character,
            font=self.default_font
        )
        generate_button.pack(side="left", padx=10)
        
        # 清空按钮
        clear_button = tk.Button(
            button_frame, 
            text="清空", 
            command=self.clear_character_inputs,
            font=self.default_font
        )
        clear_button.pack(side="left", padx=10)
        
        # 结果框架
        result_frame = tk.Frame(self.character_frame)
        result_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 结果标签
        tk.Label(result_frame, text="生成结果:", font=self.default_font).pack(anchor="w")
        
        # 结果文本框
        self.character_result_text = scrolledtext.ScrolledText(
            result_frame, 
            width=60, 
            height=15, 
            font=self.default_font,
            wrap=tk.WORD
        )
        self.character_result_text.pack(fill="both", expand=True, pady=(0, 10))
        
        # 底部按钮框架
        bottom_button_frame = tk.Frame(self.character_frame)
        bottom_button_frame.pack(pady=10)
        
        # 复制按钮
        copy_button = tk.Button(
            bottom_button_frame, 
            text="复制结果", 
            command=lambda: self.copy_to_clipboard(self.character_result_text.get(1.0, tk.END)),
            font=self.default_font
        )
        copy_button.pack(side="left", padx=10)
        
        # 保存按钮
        save_button = tk.Button(
            bottom_button_frame, 
            text="保存到文件", 
            command=self.save_character_to_file,
            font=self.default_font
        )
        save_button.pack(side="left", padx=10)
        
        # 润色框架
        polish_frame = tk.Frame(self.character_frame)
        polish_frame.pack(fill="x", padx=20, pady=10)
        
        # 润色标签
        tk.Label(polish_frame, text="润色要求:", font=self.default_font).pack(anchor="w")
        
        # 润色输入框
        self.polish_desc_text = scrolledtext.ScrolledText(
            polish_frame, 
            width=60, 
            height=3, 
            font=self.default_font,
            wrap=tk.WORD
        )
        self.polish_desc_text.pack(fill="x", pady=(0, 10))
        
        # 示例提示
        polish_example_text = "示例: 增加更多关于角色童年经历的描述，使性格更加立体。"
        tk.Label(polish_frame, text=polish_example_text, font=(self.default_font[0], 9), fg="gray").pack(anchor="w")
        
        # 润色按钮
        polish_button = tk.Button(
            polish_frame, 
            text="润色人设", 
            command=self.polish_character,
            font=self.default_font
        )
        polish_button.pack(pady=10)

    def generate_character(self):
        """生成角色人设"""
        # 获取角色描述
        character_desc = self.character_desc_text.get(1.0, tk.END).strip()
        if not character_desc:
            messagebox.showwarning("提示", "请输入角色描述！")
            return
        
        # 获取API配置
        config = APIConfig.read_config()
        url = config.get("real_server_base_url")
        api_key = config.get("api_key")
        model = config.get("model")
        
        if not url or not api_key or not model:
            messagebox.showwarning("配置错误", "请先在API配置页面设置API！")
            return
        
        try:
            # 显示加载中提示
            self.character_result_text.delete(1.0, tk.END)
            self.character_result_text.insert(tk.END, "正在生成角色人设，请稍候...")
            self.character_result_text.update()
            
            # 创建API请求
            tester = APITester(url, api_key, model)
            result = tester.generate_character_profile(character_desc)
            
            # 显示结果
            self.character_result_text.delete(1.0, tk.END)
            self.character_result_text.insert(tk.END, result)
        
        except Exception as e:
            error_msg = handle_api_error(e, "角色人设生成")
            self.character_result_text.delete(1.0, tk.END)
            self.character_result_text.insert(tk.END, f"生成出错: {error_msg}")

    def polish_character(self):
        """润色角色人设"""
        # 获取当前人设和润色要求
        current_profile = self.character_result_text.get(1.0, tk.END).strip()
        polish_desc = self.polish_desc_text.get(1.0, tk.END).strip()
        
        if not current_profile:
            messagebox.showwarning("提示", "请先生成角色人设！")
            return
        
        if not polish_desc:
            messagebox.showwarning("提示", "请输入润色要求！")
            return
        
        # 获取API配置
        config = APIConfig.read_config()
        url = config.get("real_server_base_url")
        api_key = config.get("api_key")
        model = config.get("model")
        
        if not url or not api_key or not model:
            messagebox.showwarning("配置错误", "请先在API配置页面设置API！")
            return
        
        try:
            # 显示加载中提示
            self.character_result_text.delete(1.0, tk.END)
            self.character_result_text.insert(tk.END, "正在润色角色人设，请稍候...")
            self.character_result_text.update()
            
            # 创建API请求
            tester = APITester(url, api_key, model)
            result = tester.polish_character_profile(current_profile, polish_desc)
            
            # 显示结果
            self.character_result_text.delete(1.0, tk.END)
            self.character_result_text.insert(tk.END, result)
        
        except Exception as e:
            error_msg = handle_api_error(e, "角色人设润色")
            self.character_result_text.delete(1.0, tk.END)
            self.character_result_text.insert(tk.END, f"润色出错: {error_msg}")

    def clear_character_inputs(self):
        """清空角色人设输入和结果"""
        self.character_desc_text.delete(1.0, tk.END)
        self.polish_desc_text.delete(1.0, tk.END)
        self.character_result_text.delete(1.0, tk.END)

    def save_character_to_file(self):
        """保存角色人设到文件"""
        content = self.character_result_text.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "没有可保存的内容！")
            return
        
        # 提取角色名称作为默认文件名
        default_filename = "角色人设"
        try:
            # 尝试从内容中提取角色名称
            lines = content.split('\n')
            for line in lines[:10]:  # 只检查前10行
                if "名称" in line or "姓名" in line:
                    name_match = re.search(r'[：:]\s*(.+?)(?:\s|$)', line)
                    if name_match:
                        default_filename = name_match.group(1)
                        break
        except:
            pass  # 如果提取失败，使用默认文件名
        
        # 打开文件保存对话框
        file_path = filedialog.asksaveasfilename(
            title="保存角色人设",
            defaultextension=".txt",
            initialfile=default_filename,
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("成功", f"角色人设已保存到: {file_path}")
        except Exception as e:
            messagebox.showerror("保存失败", f"保存文件时出错: {str(e)}")

    def setup_api_config_page(self):
        """设置API配置页面"""
        # 创建API配置页面的标题
        page_title = tk.Label(self.api_config_frame, text="API配置", font=("黑体", 16, "bold"))
        page_title.pack(pady=(0, 20))
        
        # 创建选项卡控件
        tab_control = ttk.Notebook(self.api_config_frame)
        
        # 创建三个选项卡
        character_tab = ttk.Frame(tab_control)
        recognition_tab = ttk.Frame(tab_control)
        generation_tab = ttk.Frame(tab_control)
        
        # 添加选项卡到控件
        tab_control.add(character_tab, text="人设API")
        tab_control.add(recognition_tab, text="图片识别API")
        tab_control.add(generation_tab, text="图片生成API")
        
        # 显示选项卡控件
        tab_control.pack(expand=1, fill="both")
        
        # 设置各个选项卡的内容
        self.setup_character_api_config(character_tab)
        self.setup_image_recognition_api_config(recognition_tab)
        self.setup_image_generation_api_config(generation_tab)
        
        # 底部按钮框架
        button_frame = tk.Frame(self.api_config_frame)
        button_frame.pack(pady=20)
        
        # 保存所有配置按钮
        save_all_button = tk.Button(
            button_frame, 
            text="保存所有配置", 
            command=self.save_all_configs,
            font=self.default_font
        )
        save_all_button.pack()

    def setup_character_api_config(self, parent_frame):
        """设置人设API配置"""
        # 人设API配置框架
        character_frame = tk.LabelFrame(parent_frame, text="人设API配置", padx=10, pady=10, font=self.default_font)
        character_frame.pack(fill="x", padx=10, pady=5)
        
        # 读取配置
        config = APIConfig.read_config()
        character_config = config.get("character_api", {})
        
        # 渠道选择
        tk.Label(character_frame, text="选择渠道:", font=self.default_font).grid(row=0, column=0, sticky="w")
        
        # 预设渠道选项
        self.character_channel_var = tk.StringVar()
        character_channels = [
            "硅基流动",
            "DeepSeek官网",
            "KouriChat",
            "自定义"
        ]
        
        # 根据当前配置设置默认选项
        current_url = character_config.get("url", config.get("real_server_base_url", "https://api.siliconflow.cn/"))
        current_model = character_config.get("model", config.get("model", "deepseek-ai/DeepSeek-V3"))
        
        if current_url == "https://api.siliconflow.cn/":
            self.character_channel_var.set(character_channels[0])
        elif current_url == "https://api.deepseek.com":
            self.character_channel_var.set(character_channels[1])
        elif current_url == "https://api.kourichat.com":
            self.character_channel_var.set(character_channels[2])
        else:
            self.character_channel_var.set(character_channels[3])  # 自定义
        
        channel_dropdown = tk.OptionMenu(character_frame, self.character_channel_var, *character_channels, command=self.update_character_channel)
        channel_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        channel_dropdown.config(width=15)
        
        # 申请密钥按钮
        apply_key_button = tk.Button(character_frame, text="申请密钥", command=self.apply_character_key, font=self.default_font)
        apply_key_button.grid(row=0, column=2, padx=5, pady=5)
        
        # URL地址
        tk.Label(character_frame, text="URL地址:", font=self.default_font).grid(row=1, column=0, sticky="w")
        self.character_url_entry = tk.Entry(character_frame, width=50, font=self.default_font)
        self.character_url_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5)
        self.character_url_entry.insert(0, character_config.get("url", config.get("real_server_base_url", "https://api.siliconflow.cn/")))
        
        # API密钥
        tk.Label(character_frame, text="API密钥:", font=self.default_font).grid(row=2, column=0, sticky="w")
        self.character_key_entry = tk.Entry(character_frame, width=50, font=self.default_font)
        self.character_key_entry.grid(row=2, column=1, columnspan=2, padx=5, pady=5)
        self.character_key_entry.insert(0, character_config.get("api_key", config.get("api_key", "")))
        
        # 模型名称
        tk.Label(character_frame, text="模型名称:", font=self.default_font).grid(row=3, column=0, sticky="w")
        
        # 模型选择下拉菜单
        self.character_model_var = tk.StringVar()
        self.character_model_options = {
            "硅基流动": ["deepseek-ai/DeepSeek-V3", "Qwen/Qwen2-72B-Instruct", "自定义"],
            "DeepSeek官网": ["deepseek-chat", "deepseek-coder", "自定义"],
            "KouriChat": ["kourichat-v3", "自定义"],
            "自定义": ["自定义"]
        }
        
        # 根据当前渠道设置模型选项
        current_channel = self.character_channel_var.get()
        model_options = self.character_model_options.get(current_channel, ["自定义"])
        
        # 设置当前模型
        if current_model in model_options:
            self.character_model_var.set(current_model)
        else:
            self.character_model_var.set("自定义")
        
        self.character_model_dropdown = tk.OptionMenu(character_frame, self.character_model_var, *model_options, command=self.update_character_model)
        self.character_model_dropdown.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        self.character_model_dropdown.config(width=15)
        
        # 自定义模型输入框
        self.character_model_entry = tk.Entry(character_frame, width=30, font=self.default_font)
        self.character_model_entry.grid(row=3, column=2, padx=5, pady=5, sticky="w")
        if self.character_model_var.get() == "自定义":
            self.character_model_entry.insert(0, current_model)
        else:
            self.character_model_entry.insert(0, "")
            self.character_model_entry.config(state="disabled")
        
        # 按钮框架
        button_frame = tk.Frame(character_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        # 保存按钮
        save_button = tk.Button(button_frame, text="保存人设API配置", command=self.save_character_config, font=self.default_font)
        save_button.pack(side="left", padx=10)
        
        # 测试按钮
        test_button = tk.Button(button_frame, text="测试人设API", command=self.test_character_api, font=self.default_font)
        test_button.pack(side="left", padx=10)

    def setup_image_recognition_api_config(self, parent_frame):
        """设置图片识别API配置"""
        # 图片识别API配置框架
        recognition_frame = tk.LabelFrame(parent_frame, text="图片识别API配置", padx=10, pady=10, font=self.default_font)
        recognition_frame.pack(fill="x", padx=10, pady=5)
        
        # 读取配置
        config = APIConfig.read_config()
        recognition_config = config.get("recognition_api", {})
        
        # 渠道选择
        tk.Label(recognition_frame, text="选择渠道:", font=self.default_font).grid(row=0, column=0, sticky="w")
        
        # 预设渠道选项
        self.recognition_channel_var = tk.StringVar()
        recognition_channels = [
            "硅基流动",
            "月之暗面",
            "自定义"
        ]
        
        # 根据当前配置设置默认选项
        current_url = recognition_config.get("url", config.get("real_server_base_url", "https://api.siliconflow.cn/"))
        current_model = recognition_config.get("model", config.get("model", "Qwen/Qwen2-VL-72B-Instruct"))
        
        if current_url == "https://api.siliconflow.cn/":
            self.recognition_channel_var.set(recognition_channels[0])
        elif current_url == "https://api.moonshot.cn":
            self.recognition_channel_var.set(recognition_channels[1])
        else:
            self.recognition_channel_var.set(recognition_channels[2])  # 自定义
        
        channel_dropdown = tk.OptionMenu(recognition_frame, self.recognition_channel_var, *recognition_channels, command=self.update_recognition_channel)
        channel_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        channel_dropdown.config(width=15)
        
        # 申请密钥按钮
        apply_key_button = tk.Button(recognition_frame, text="申请密钥", command=self.apply_recognition_key, font=self.default_font)
        apply_key_button.grid(row=0, column=2, padx=5, pady=5)
        
        # URL地址
        tk.Label(recognition_frame, text="URL地址:", font=self.default_font).grid(row=1, column=0, sticky="w")
        self.recognition_url_entry = tk.Entry(recognition_frame, width=50, font=self.default_font)
        self.recognition_url_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5)
        self.recognition_url_entry.insert(0, recognition_config.get("url", config.get("real_server_base_url", "https://api.siliconflow.cn/")))
        
        # API密钥
        tk.Label(recognition_frame, text="API密钥:", font=self.default_font).grid(row=2, column=0, sticky="w")
        self.recognition_key_entry = tk.Entry(recognition_frame, width=50, font=self.default_font)
        self.recognition_key_entry.grid(row=2, column=1, columnspan=2, padx=5, pady=5)
        self.recognition_key_entry.insert(0, recognition_config.get("api_key", config.get("api_key", "")))
        
        # 模型名称
        tk.Label(recognition_frame, text="模型名称:", font=self.default_font).grid(row=3, column=0, sticky="w")
        
        # 模型选择下拉菜单
        self.recognition_model_var = tk.StringVar()
        self.recognition_model_options = {
            "硅基流动": ["Qwen/Qwen2-VL-72B-Instruct", "自定义"],
            "月之暗面": ["moonshot-v1-8k-vision-preview", "自定义"],
            "自定义": ["自定义"]
        }
        
        # 根据当前渠道设置模型选项
        current_channel = self.recognition_channel_var.get()
        model_options = self.recognition_model_options.get(current_channel, ["自定义"])
        
        # 设置当前模型
        if current_model in model_options:
            self.recognition_model_var.set(current_model)
        else:
            self.recognition_model_var.set("自定义")
        
        self.recognition_model_dropdown = tk.OptionMenu(recognition_frame, self.recognition_model_var, *model_options, command=self.update_recognition_model)
        self.recognition_model_dropdown.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        self.recognition_model_dropdown.config(width=15)
        
        # 自定义模型输入框
        self.recognition_model_entry = tk.Entry(recognition_frame, width=30, font=self.default_font)
        self.recognition_model_entry.grid(row=3, column=2, padx=5, pady=5, sticky="w")
        if self.recognition_model_var.get() == "自定义":
            self.recognition_model_entry.insert(0, current_model)
        else:
            self.recognition_model_entry.insert(0, "")
            self.recognition_model_entry.config(state="disabled")
        
        # 按钮框架
        button_frame = tk.Frame(recognition_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        # 保存按钮
        save_button = tk.Button(button_frame, text="保存识别API配置", command=self.save_recognition_config, font=self.default_font)
        save_button.pack(side="left", padx=10)
        
        # 测试按钮
        test_button = tk.Button(button_frame, text="测试识别API", command=self.test_recognition_api, font=self.default_font)
        test_button.pack(side="left", padx=10)

    def setup_image_generation_api_config(self, parent_frame):
        """设置图片生成API配置"""
        # 图片生成API配置框架
        generation_frame = tk.LabelFrame(parent_frame, text="图片生成API配置", padx=10, pady=10, font=self.default_font)
        generation_frame.pack(fill="x", padx=10, pady=5)
        
        # 读取配置
        config = APIConfig.read_config()
        generation_config = config.get("generation_api", {})
        
        # 渠道选择
        tk.Label(generation_frame, text="选择渠道:", font=self.default_font).grid(row=0, column=0, sticky="w")

        # 预设渠道选项
        self.generation_channel_var = tk.StringVar()
        generation_channels = [
            "硅基流动",
            "自定义"
        ]
        
        # 根据当前配置设置默认选项
        current_url = generation_config.get("url", config.get("real_server_base_url", "https://api.siliconflow.cn/"))
        current_model = generation_config.get("model", config.get("model", "Kwai-Kolors/Kolors"))
        
        if current_url == "https://api.siliconflow.cn/":
            self.generation_channel_var.set(generation_channels[0])
        else:
            self.generation_channel_var.set(generation_channels[1])  # 自定义
        
        channel_dropdown = tk.OptionMenu(generation_frame, self.generation_channel_var, *generation_channels, command=self.update_generation_channel)
        channel_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        channel_dropdown.config(width=15)
        
        # 申请密钥按钮
        apply_key_button = tk.Button(generation_frame, text="申请密钥", command=self.apply_generation_key, font=self.default_font)
        apply_key_button.grid(row=0, column=2, padx=5, pady=5)
        
        # URL地址
        tk.Label(generation_frame, text="URL地址:", font=self.default_font).grid(row=1, column=0, sticky="w")
        self.generation_url_entry = tk.Entry(generation_frame, width=50, font=self.default_font)
        self.generation_url_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5)
        self.generation_url_entry.insert(0, generation_config.get("url", config.get("real_server_base_url", "https://api.siliconflow.cn/")))
        
        # API密钥
        tk.Label(generation_frame, text="API密钥:", font=self.default_font).grid(row=2, column=0, sticky="w")
        self.generation_key_entry = tk.Entry(generation_frame, width=50, font=self.default_font)
        self.generation_key_entry.grid(row=2, column=1, columnspan=2, padx=5, pady=5)
        self.generation_key_entry.insert(0, generation_config.get("api_key", config.get("api_key", "")))
        
        # 模型名称
        tk.Label(generation_frame, text="模型名称:", font=self.default_font).grid(row=3, column=0, sticky="w")
        
        # 模型选择下拉菜单
        self.generation_model_var = tk.StringVar()
        self.generation_model_options = {
            "硅基流动": ["Kwai-Kolors/Kolors", "自定义"],
            "自定义": ["自定义"]
        }
        
        # 根据当前渠道设置模型选项
        current_channel = self.generation_channel_var.get()
        model_options = self.generation_model_options.get(current_channel, ["自定义"])
        
        # 设置当前模型
        if current_model in model_options:
            self.generation_model_var.set(current_model)
        else:
            self.generation_model_var.set("自定义")
        
        self.generation_model_dropdown = tk.OptionMenu(generation_frame, self.generation_model_var, *model_options, command=self.update_generation_model)
        self.generation_model_dropdown.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        self.generation_model_dropdown.config(width=15)
        
        # 自定义模型输入框
        self.generation_model_entry = tk.Entry(generation_frame, width=30, font=self.default_font)
        self.generation_model_entry.grid(row=3, column=2, padx=5, pady=5, sticky="w")
        if self.generation_model_var.get() == "自定义":
            self.generation_model_entry.insert(0, current_model)
        else:
            self.generation_model_entry.insert(0, "")
            self.generation_model_entry.config(state="disabled")
        
        # 图片尺寸选择
        tk.Label(generation_frame, text="图片尺寸:", font=self.default_font).grid(row=4, column=0, sticky="w")
        
        # 图片尺寸下拉菜单
        self.image_size_var = tk.StringVar()
        size_options = ["1024x1024", "960x1280", "768x1024", "720x1440", "720x1280"]
        
        # 设置当前尺寸
        current_size = generation_config.get("generate_size", config.get("image_config", {}).get("generate_size", "1024x1024"))
        if current_size in size_options:
            self.image_size_var.set(current_size)
        else:
            self.image_size_var.set("1024x1024")
        
        size_dropdown = ttk.Combobox(generation_frame, textvariable=self.image_size_var, values=size_options, width=15, font=self.default_font)
        size_dropdown.grid(row=4, column=1, padx=5, pady=5, sticky="w")
        
        # 按钮框架
        button_frame = tk.Frame(generation_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        # 保存按钮
        save_button = tk.Button(button_frame, text="保存生成API配置", command=self.save_generation_config, font=self.default_font)
        save_button.pack(side="left", padx=10)
        
        # 测试按钮
        test_button = tk.Button(button_frame, text="测试生成API", command=self.test_generation_api, font=self.default_font)
        test_button.pack(side="left", padx=10)

    def update_character_channel(self, selection):
        """根据选择的渠道更新URL和模型下拉菜单"""
        # 更新URL
        if selection == "硅基流动":
            self.character_url_entry.delete(0, tk.END)
            self.character_url_entry.insert(0, "https://api.siliconflow.cn/")
        elif selection == "DeepSeek官网":
            self.character_url_entry.delete(0, tk.END)
            self.character_url_entry.insert(0, "https://api.deepseek.com")
        elif selection == "KouriChat":
            self.character_url_entry.delete(0, tk.END)
            self.character_url_entry.insert(0, "https://api.kourichat.com")
        
        # 更新模型下拉菜单
        model_options = self.character_model_options.get(selection, ["自定义"])
        
        # 重新创建下拉菜单
        self.character_model_dropdown.destroy()
        self.character_model_dropdown = tk.OptionMenu(
            self.character_model_dropdown.master, 
            self.character_model_var, 
            *model_options,
            command=self.update_character_model
        )
        self.character_model_dropdown.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        self.character_model_dropdown.config(width=15)
        
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
            self.character_model_entry.config(state="normal")
            self.character_model_entry.delete(0, tk.END)
        else:
            self.character_model_entry.delete(0, tk.END)
            self.character_model_entry.config(state="disabled")

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

    def update_generation_channel(self, selection):
        """根据选择的渠道更新URL和模型下拉菜单"""
        # 更新URL
        if selection == "硅基流动":
            self.generation_url_entry.delete(0, tk.END)
            self.generation_url_entry.insert(0, "https://api.siliconflow.cn/")
        
        # 更新模型下拉菜单
        model_options = self.generation_model_options.get(selection, ["自定义"])
        
        # 重新创建下拉菜单
        self.generation_model_dropdown.destroy()
        self.generation_model_dropdown = tk.OptionMenu(
            self.generation_model_dropdown.master, 
            self.generation_model_var, 
            *model_options,
            command=self.update_generation_model
        )
        self.generation_model_dropdown.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        self.generation_model_dropdown.config(width=15)
        
        # 设置默认模型
        if selection == "硅基流动":
            self.generation_model_var.set("Kwai-Kolors/Kolors")
        else:
            self.generation_model_var.set("自定义")
        
        # 更新模型输入框状态
        self.update_generation_model(self.generation_model_var.get())

    def update_generation_model(self, selection):
        """根据选择的模型更新输入框状态"""
        if selection == "自定义":
            self.generation_model_entry.config(state="normal")
            self.generation_model_entry.delete(0, tk.END)
        else:
            self.generation_model_entry.delete(0, tk.END)
            self.generation_model_entry.config(state="disabled")

    def apply_generation_key(self):
        """打开申请密钥的网页"""
        channel = self.generation_channel_var.get()
        if channel == "硅基流动":
            webbrowser.open("https://www.siliconflow.cn/")
        else:
            messagebox.showinfo("提示", "请先选择一个渠道")

    def test_character_api(self):
        """测试人设API连接"""
        # 先保存配置
        self.save_character_config()
        
        url = self.character_url_entry.get()
        api_key = self.character_key_entry.get()
        
        # 获取模型名称
        model = self.character_model_var.get()
        if model == "自定义":
            model = self.character_model_entry.get()
        
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

    def test_recognition_api(self):
        """测试图片识别API连接"""
        # 先保存配置
        self.save_recognition_config()
        
        url = self.recognition_url_entry.get()
        api_key = self.recognition_key_entry.get()
        
        # 获取模型名称
        model = self.recognition_model_var.get()
        if model == "自定义":
            model = self.recognition_model_entry.get()
        
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

    def test_generation_api(self):
        """测试图片生成API连接"""
        # 先保存配置
        self.save_generation_config()
        
        url = self.generation_url_entry.get()
        api_key = self.generation_key_entry.get()
        
        # 获取模型名称
        model = self.generation_model_var.get()
        if model == "自定义":
            model = self.generation_model_entry.get()
        
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

    def update_recognition_channel(self, selection):
        """根据选择的渠道更新URL和模型下拉菜单"""
        # 更新URL
        if selection == "硅基流动":
            self.recognition_url_entry.delete(0, tk.END)
            self.recognition_url_entry.insert(0, "https://api.siliconflow.cn/")
        elif selection == "DeepSeek官网":
            self.recognition_url_entry.delete(0, tk.END)
            self.recognition_url_entry.insert(0, "https://api.deepseek.com")
        elif selection == "KouriChat":
            self.recognition_url_entry.delete(0, tk.END)
            self.recognition_url_entry.insert(0, "https://api.kourichat.com")
        
        # 更新模型下拉菜单
        model_options = self.recognition_model_options.get(selection, ["自定义"])
        
        # 重新创建下拉菜单
        self.recognition_model_dropdown.destroy()
        self.recognition_model_dropdown = tk.OptionMenu(
            self.recognition_model_dropdown.master, 
            self.recognition_model_var, 
            *model_options,
            command=self.update_recognition_model
        )
        self.recognition_model_dropdown.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        self.recognition_model_dropdown.config(width=15)
        
        # 设置默认模型
        if selection == "硅基流动":
            self.recognition_model_var.set("deepseek-ai/DeepSeek-V3")
        elif selection == "DeepSeek官网":
            self.recognition_model_var.set("deepseek-chat")
        elif selection == "KouriChat":
            self.recognition_model_var.set("kourichat-v3")
        else:
            self.recognition_model_var.set("自定义")
        
        # 更新模型输入框状态
        self.update_recognition_model(self.recognition_model_var.get())

    def update_recognition_model(self, selection):
        """根据选择的模型更新输入框状态"""
        if selection == "自定义":
            self.recognition_model_entry.config(state="normal")
            self.recognition_model_entry.delete(0, tk.END)
        else:
            self.recognition_model_entry.delete(0, tk.END)
            self.recognition_model_entry.config(state="disabled")

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

    def setup_image_page(self):
        """设置图片页面"""
        # 创建图片页面的标题
        page_title = tk.Label(self.image_frame, text="图片功能", font=("黑体", 16, "bold"))
        page_title.pack(pady=(0, 20))
        
        # 创建图片识别和生成的按钮框架
        button_frame = tk.Frame(self.image_frame)
        button_frame.pack(pady=20)
        
        # 图片识别按钮
        recognition_button = tk.Button(
            button_frame, 
            text="图片识别", 
            command=self.show_image_recognition, 
            font=("黑体", 12),
            width=15,
            height=2
        )
        recognition_button.pack(side="left", padx=20)
        
        # 图片生成按钮
        generation_button = tk.Button(
            button_frame, 
            text="图片生成", 
            command=self.show_image_generation, 
            font=("黑体", 12),
            width=15,
            height=2
        )
        generation_button.pack(side="left", padx=20)
        
        # 创建图片识别和生成的子框架
        self.image_recognition_frame = tk.Frame(self.image_frame)
        self.image_generation_frame = tk.Frame(self.image_frame)
        
        # 设置图片识别框架内容
        self.setup_image_recognition_frame()
        
        # 设置图片生成框架内容
        self.setup_image_generation_frame()

    def setup_image_recognition_frame(self):
        """设置图片识别框架内容"""
        # 标题
        title = tk.Label(self.image_recognition_frame, text="图片识别", font=("黑体", 14, "bold"))
        title.pack(pady=(0, 10))
        
        # 上传图片按钮
        upload_button = tk.Button(
            self.image_recognition_frame, 
            text="上传图片", 
            command=self.upload_image_for_recognition,
            font=self.default_font
        )
        upload_button.pack(pady=10)
        
        # 图片预览框架
        self.recognition_preview_frame = tk.Frame(self.image_recognition_frame)
        self.recognition_preview_frame.pack(pady=10)
        
        # 图片预览标签
        self.recognition_image_label = tk.Label(self.recognition_preview_frame, text="图片预览区域")
        self.recognition_image_label.pack()
        
        # 识别结果框架
        result_frame = tk.Frame(self.image_recognition_frame)
        result_frame.pack(fill="both", expand=True, pady=10)
        
        # 识别结果标签
        tk.Label(result_frame, text="识别结果:", font=self.default_font).pack(anchor="w")
        
        # 识别结果文本框
        self.recognition_result_text = scrolledtext.ScrolledText(
            result_frame, 
            width=60, 
            height=10, 
            font=self.default_font,
            wrap=tk.WORD
        )
        self.recognition_result_text.pack(fill="both", expand=True)
        
        # 复制结果按钮
        copy_button = tk.Button(
            result_frame, 
            text="复制结果", 
            command=lambda: self.copy_to_clipboard(self.recognition_result_text.get(1.0, tk.END)),
            font=self.default_font
        )
        copy_button.pack(pady=10)

    def setup_image_generation_frame(self):
        """设置图片生成框架内容"""
        # 标题
        title = tk.Label(self.image_generation_frame, text="图片生成", font=("黑体", 14, "bold"))
        title.pack(pady=(0, 10))
        
        # 提示词输入框架
        prompt_frame = tk.Frame(self.image_generation_frame)
        prompt_frame.pack(fill="x", pady=10)
        
        # 提示词标签
        tk.Label(prompt_frame, text="提示词:", font=self.default_font).pack(anchor="w")
        
        # 提示词文本框
        self.generation_prompt_text = scrolledtext.ScrolledText(
            prompt_frame, 
            width=60, 
            height=5, 
            font=self.default_font,
            wrap=tk.WORD
        )
        self.generation_prompt_text.pack(fill="x")
        
        # 图片尺寸选择框架
        size_frame = tk.Frame(self.image_generation_frame)
        size_frame.pack(fill="x", pady=5)
        
        # 图片尺寸标签
        tk.Label(size_frame, text="图片尺寸:", font=self.default_font).pack(side="left", padx=(0, 10))
        
        # 图片尺寸下拉菜单
        # 根据硅基流动API文档支持的尺寸
        self.image_size_var = tk.StringVar(value="1024x1024")
        size_options = ["1024x1024", "960x1280", "768x1024", "720x1440", "720x1280"]
        size_dropdown = ttk.Combobox(size_frame, textvariable=self.image_size_var, values=size_options, width=15, font=self.default_font)
        size_dropdown.pack(side="left")
        
        # 生成按钮
        generate_button = tk.Button(
            self.image_generation_frame, 
            text="生成图片", 
            command=self.generate_image,
            font=self.default_font
        )
        generate_button.pack(pady=10)
        
        # 图片预览框架
        self.generation_preview_frame = tk.Frame(self.image_generation_frame)
        self.generation_preview_frame.pack(pady=10)
        
        # 图片预览标签
        self.generation_image_label = tk.Label(self.generation_preview_frame, text="图片生成区域")
        self.generation_image_label.pack()
        
        # 保存图片按钮
        self.save_image_button = tk.Button(
            self.image_generation_frame, 
            text="保存图片", 
            command=self.save_generated_image,
            font=self.default_font,
            state="disabled"  # 初始状态为禁用
        )
        self.save_image_button.pack(pady=10)

    def show_image_recognition(self):
        """显示图片识别框架"""
        self.image_generation_frame.pack_forget()
        self.image_recognition_frame.pack(fill="both", expand=True)

    def show_image_generation(self):
        """显示图片生成框架"""
        self.image_recognition_frame.pack_forget()
        self.image_generation_frame.pack(fill="both", expand=True)

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
            image = Image.open(file_path)
            # 调整图片大小以适应预览区域
            image = self.resize_image(image, 300)
            photo = ImageTk.PhotoImage(image)
            
            # 更新预览标签
            self.recognition_image_label.config(image=photo)
            self.recognition_image_label.image = photo  # 保持引用
            
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
            self.recognition_result_text.delete(1.0, tk.END)
            self.recognition_result_text.insert(tk.END, "正在识别图片，请稍候...")
            self.recognition_result_text.update()
            
            # 将图片转换为base64编码
            with open(file_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # 创建API请求
            tester = APITester(url, api_key, model)
            response = tester.recognize_image(encoded_image)
            
            # 显示识别结果
            self.recognition_result_text.delete(1.0, tk.END)
            if response and response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    self.recognition_result_text.insert(tk.END, content)
                else:
                    self.recognition_result_text.insert(tk.END, "无法解析识别结果，请检查API响应格式。")
            else:
                self.recognition_result_text.insert(tk.END, f"识别失败: {response.text if response else '无响应'}")
        
        except Exception as e:
            error_msg = handle_api_error(e, "图片识别")
            self.recognition_result_text.delete(1.0, tk.END)
            self.recognition_result_text.insert(tk.END, f"识别出错: {error_msg}")

    def generate_image(self):
        """生成图片"""
        # 获取提示词
        prompt = self.generation_prompt_text.get(1.0, tk.END).strip()
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
            self.generation_image_label.config(text="正在生成图片，请稍候...")
            self.generation_image_label.update()
            
            # 创建API请求
            tester = APITester(url, api_key, model)
            response = tester.generate_image(prompt, size)
            
            if response and response.status_code == 200:
                result = response.json()
                if "data" in result and len(result["data"]) > 0 and "url" in result["data"][0]:
                    image_url = result["data"][0]["url"]
                    
                    # 下载图片
                    image_response = requests.get(image_url)
                    if image_response.status_code == 200:
                        # 将图片数据转换为PIL图像
                        image = Image.open(io.BytesIO(image_response.content))
                        
                        # 保存原始图像用于后续保存
                        self.generated_image = image
                        
                        # 调整图片大小以适应预览区域
                        display_image = self.resize_image(image, 300)
                        photo = ImageTk.PhotoImage(display_image)
                        
                        # 更新预览标签
                        self.generation_image_label.config(image=photo, text="")
                        self.generation_image_label.image = photo  # 保持引用
                        
                        # 启用保存按钮
                        self.save_image_button.config(state="normal")
                    else:
                        self.generation_image_label.config(text=f"下载图片失败: {image_response.status_code}")
                else:
                    self.generation_image_label.config(text="无法解析生成结果，请检查API响应格式。")
            else:
                self.generation_image_label.config(text=f"生成失败: {response.text if response else '无响应'}")
        
        except Exception as e:
            error_msg = handle_api_error(e, "图片生成")
            self.generation_image_label.config(text=f"生成出错: {error_msg}")

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

# 在文件末尾添加或修改主程序入口点
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = KouriChatToolbox(root)
        root.mainloop()
    except Exception as e:
        # 捕获并显示任何异常
        import traceback
        error_message = f"启动错误: {str(e)}\n\n{traceback.format_exc()}"
        print(error_message)  # 打印到控制台
        
        # 尝试显示错误对话框
        try:
            import tkinter.messagebox as msgbox
            msgbox.showerror("启动错误", error_message)
        except:
            pass

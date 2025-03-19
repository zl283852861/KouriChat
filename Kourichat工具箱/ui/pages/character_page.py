import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import os

from widgets.scrollable_text_box import ScrollableTextBox
from api.tester import APITester
from core.error_handler import handle_api_error

class CharacterPage:
    """人设页面类"""
    
    def __init__(self, app):
        self.app = app
        self.setup_character_page()
    
    def setup_character_page(self):
        """设置人设页面内容"""
        # 页面标题
        title_label = ctk.CTkLabel(
            self.app.character_frame, 
            text="角色人设生成", 
            font=self.app.title_font
        )
        title_label.pack(pady=(20, 20))
        
        # 创建左右分栏
        content_frame = ctk.CTkFrame(self.app.character_frame)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 配置网格布局
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # 左侧输入区域
        input_frame = ctk.CTkFrame(content_frame)
        input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # 右侧结果区域
        result_frame = ctk.CTkFrame(content_frame)
        result_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # 设置左侧输入区域
        self.setup_input_area(input_frame)
        
        # 设置右侧结果区域
        self.setup_result_area(result_frame)
    
    def setup_input_area(self, parent_frame):
        """设置输入区域"""
        # 标题
        input_title = ctk.CTkLabel(
            parent_frame, 
            text="输入角色描述", 
            font=ctk.CTkFont(family="Arial Unicode MS", size=14, weight="bold")
        )
        input_title.pack(pady=(10, 5))
        
        # 角色描述输入框
        desc_label = ctk.CTkLabel(
            parent_frame, 
            text="角色简要描述:", 
            font=self.app.default_font
        )
        desc_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        self.character_desc_text = ctk.CTkTextbox(
            parent_frame, 
            height=150, 
            font=self.app.default_font,
            wrap="word"
        )
        self.character_desc_text.pack(fill="x", padx=10, pady=(0, 10))
        
        # 润色要求输入框
        polish_label = ctk.CTkLabel(
            parent_frame, 
            text="润色要求(可选):", 
            font=self.app.default_font
        )
        polish_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        self.polish_desc_text = ctk.CTkTextbox(
            parent_frame, 
            height=100, 
            font=self.app.default_font,
            wrap="word"
        )
        self.polish_desc_text.pack(fill="x", padx=10, pady=(0, 10))
        
        # 按钮区域
        button_frame = ctk.CTkFrame(parent_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # 生成按钮
        generate_button = ctk.CTkButton(
            button_frame, 
            text="生成人设", 
            command=self.generate_profile,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        generate_button.pack(side="left", padx=5, pady=5)
        
        # 润色按钮
        polish_button = ctk.CTkButton(
            button_frame, 
            text="润色人设", 
            command=self.polish_profile,
            font=self.app.default_font,
            fg_color=self.app.button_color,
            hover_color=self.app.button_hover_color
        )
        polish_button.pack(side="left", padx=5, pady=5)
        
        # 清空按钮
        clear_button = ctk.CTkButton(
            button_frame, 
            text="清空", 
            command=self.clear_character_inputs,
            font=self.app.default_font,
            fg_color="gray60",
            hover_color="gray40"
        )
        clear_button.pack(side="right", padx=5, pady=5)
    
    def setup_result_area(self, parent_frame):
        """设置结果区域"""
        # 标题
        result_title = ctk.CTkLabel(
            parent_frame, 
            text="生成结果", 
            font=ctk.CTkFont(family="Arial Unicode MS", size=14, weight="bold")
        )
        result_title.pack(pady=(10, 5))
        
        # 结果显示框
        self.character_result_text = ScrollableTextBox(parent_frame)
        self.character_result_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 按钮区域
        button_frame = ctk.CTkFrame(parent_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # 导入按钮
        import_button = ctk.CTkButton(
            button_frame, 
            text="导入人设", 
            command=self.import_profile,
            font=self.app.default_font,
            fg_color=self.app.purple_color,
            hover_color=self.app.purple_hover_color
        )
        import_button.pack(side="left", padx=5, pady=5)
        
        # 导出按钮
        export_button = ctk.CTkButton(
            button_frame, 
            text="导出人设", 
            command=self.export_profile,
            font=self.app.default_font,
            fg_color=self.app.purple_color,
            hover_color=self.app.purple_hover_color
        )
        export_button.pack(side="left", padx=5, pady=5)
    
    def generate_profile(self):
        """生成角色人设"""
        # 获取角色描述
        character_desc = self.character_desc_text.get("1.0", "end-1c").strip()
        
        if not character_desc:
            messagebox.showwarning("提示", "请输入角色描述！")
            return
        
        # 获取API配置
        config = self.app.config
        character_config = config.get("character_api", {})
        
        url = character_config.get("url", config.get("real_server_base_url", ""))
        api_key = character_config.get("api_key", config.get("api_key", ""))
        model = character_config.get("model", config.get("model", ""))
        
        if not url or not api_key or not model:
            messagebox.showwarning("提示", "请先在API配置页面设置人设API参数！")
            return
        
        # 显示生成中提示
        self.character_result_text.set_text("正在生成角色人设，请稍候...")
        
        # 创建API测试器
        api_tester = APITester(url, api_key, model)
        
        # 在后台线程中生成人设
        def generate_in_thread():
            try:
                # 生成人设
                profile = api_tester.generate_character_profile(character_desc)
                
                # 更新UI
                self.app.after(0, lambda: self.update_profile_result(profile))
                
            except Exception as e:
                error_msg = handle_api_error(e, "人设API")
                self.app.after(0, lambda: self.character_result_text.set_text(error_msg))
        
        # 启动线程
        threading.Thread(target=generate_in_thread, daemon=True).start()
    
    def polish_profile(self):
        """润色角色人设"""
        # 获取润色要求
        polish_desc = self.polish_desc_text.get("1.0", "end-1c").strip()
        
        if not polish_desc:
            messagebox.showwarning("提示", "请输入润色要求！")
            return
        
        # 获取当前人设
        current_profile = self.character_result_text.get_text().strip()
        
        if not current_profile:
            messagebox.showwarning("提示", "请先生成或导入人设！")
            return
        
        # 获取API配置
        config = self.app.config
        character_config = config.get("character_api", {})
        
        url = character_config.get("url", config.get("real_server_base_url", ""))
        api_key = character_config.get("api_key", config.get("api_key", ""))
        model = character_config.get("model", config.get("model", ""))
        
        if not url or not api_key or not model:
            messagebox.showwarning("提示", "请先在API配置页面设置人设API参数！")
            return
        
        # 显示润色中提示
        self.character_result_text.set_text("正在润色角色人设，请稍候...")
        
        # 创建API测试器
        api_tester = APITester(url, api_key, model)
        
        # 在后台线程中润色人设
        def polish_in_thread():
            try:
                # 润色人设
                polished_profile = api_tester.polish_character_profile(current_profile, polish_desc)
                
                # 更新UI
                self.app.after(0, lambda: self.update_profile_result(polished_profile))
                
            except Exception as e:
                error_msg = handle_api_error(e, "人设API")
                self.app.after(0, lambda: self.character_result_text.set_text(error_msg))
        
        # 启动线程
        threading.Thread(target=polish_in_thread, daemon=True).start()
    
    def update_profile_result(self, profile):
        """更新人设结果"""
        self.character_result_text.set_text(profile)
        self.app.generated_profile = profile
        messagebox.showinfo("成功", "角色人设已生成！")
    
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
            self.app.generated_profile = profile_text
            
            messagebox.showinfo("导入成功", "人设已成功导入！")
            
        except Exception as e:
            messagebox.showerror("导入失败", f"读取人设文件时出错: {str(e)}")
    
    def export_profile(self):
        """导出角色人设"""
        # 检查是否有已生成的人设
        profile_text = self.character_result_text.get_text().strip()
        if not profile_text:
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
                f.write(profile_text)
            
            messagebox.showinfo("导出成功", f"人设已保存到: {file_path}")
            
        except Exception as e:
            messagebox.showerror("导出失败", f"保存人设文件时出错: {str(e)}")
    
    def clear_character_inputs(self):
        """清空人设输入框"""
        self.character_desc_text.delete("1.0", "end")
        self.polish_desc_text.delete("1.0", "end")
        self.character_result_text.set_text("")
        self.app.generated_profile = None
        messagebox.showinfo("提示", "已清空所有输入和结果！") 
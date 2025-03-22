import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import os

from widgets.scrollable_text_box import ScrollableTextBox
from api.tester import APITester
from core.error_handler import handle_api_error
from ..theme import Theme

class CharacterPage:
    """人设页面类"""
    
    def __init__(self, app):
        self.app = app
        self.setup_character_page()
    
    def setup_character_page(self):
        """设置人设页面内容"""
        # 创建主容器
        main_container = ctk.CTkFrame(
            self.app.character_frame,
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
            text="角色人设生成", 
            font=Theme.get_font(size=32, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        title_label.pack(expand=True)
        
        # 创建左右分栏
        content_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        content_frame.pack(fill="both", expand=True)
        
        # 配置网格布局 - 调整左右比例为4:5，让右侧结果区域更大
        content_frame.grid_columnconfigure(0, weight=4)
        content_frame.grid_columnconfigure(1, weight=5)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # 左侧输入区域
        input_frame = ctk.CTkFrame(
            content_frame,
            fg_color=Theme.CARD_BG,
            corner_radius=15
        )
        input_frame.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")
        
        # 右侧结果区域
        result_frame = ctk.CTkFrame(
            content_frame,
            fg_color=Theme.CARD_BG,
            corner_radius=15
        )
        result_frame.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="nsew")
        
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
            font=Theme.get_font(size=22, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        input_title.pack(pady=(25, 20))
        
        # 角色描述输入框
        desc_label = ctk.CTkLabel(
            parent_frame, 
            text="角色简要描述:", 
            font=Theme.get_font(size=16),
            text_color=Theme.TEXT_PRIMARY
        )
        desc_label.pack(anchor="w", padx=25, pady=(0, 10))
        
        self.character_desc_text = ScrollableTextBox(
            parent_frame, 
            height=220,
            font=Theme.get_font(size=14),
            fg_color=Theme.BG_SECONDARY,
            text_color=Theme.TEXT_PRIMARY,
            border_color=None
        )
        self.character_desc_text.pack(fill="x", padx=25, pady=(0, 20))
        
        # 润色要求输入框
        polish_label = ctk.CTkLabel(
            parent_frame, 
            text="润色要求 (可选):", 
            font=Theme.get_font(size=16),
            text_color=Theme.TEXT_PRIMARY
        )
        polish_label.pack(anchor="w", padx=25, pady=(0, 10))
        
        self.polish_desc_text = ScrollableTextBox(
            parent_frame, 
            height=160,
            font=Theme.get_font(size=14),
            fg_color=Theme.BG_SECONDARY,
            text_color=Theme.TEXT_PRIMARY,
            border_color=None
        )
        self.polish_desc_text.pack(fill="x", padx=25, pady=(0, 25))
        
        # 按钮区域
        button_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=25, pady=(0, 20))
        
        # 生成按钮
        generate_button = ctk.CTkButton(
            button_frame, 
            text="生成人设", 
            command=self.generate_profile,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8,
            border_spacing=10
        )
        generate_button.pack(side="left", padx=5)
        
        # 润色按钮
        polish_button = ctk.CTkButton(
            button_frame, 
            text="润色人设", 
            command=self.polish_profile,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8,
            border_spacing=10
        )
        polish_button.pack(side="left", padx=5)
        
        # 清空按钮
        clear_button = ctk.CTkButton(
            button_frame, 
            text="清空", 
            command=self.clear_input,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_DANGER,
            hover_color=Theme.BUTTON_DANGER_HOVER,
            height=38,
            width=100,
            corner_radius=8,
            border_spacing=10
        )
        clear_button.pack(side="right", padx=5)
    
    def setup_result_area(self, parent_frame):
        """设置结果区域"""
        # 标题
        result_title = ctk.CTkLabel(
            parent_frame, 
            text="生成结果", 
            font=Theme.get_font(size=22, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        result_title.pack(pady=(25, 20))
        
        # 结果显示框
        self.character_result_text = ScrollableTextBox(
            parent_frame,
            width=500,
            height=500,
            font=Theme.get_font(size=14),
            fg_color=Theme.BG_SECONDARY,
            text_color=Theme.TEXT_PRIMARY,
            border_color=None
        )
        self.character_result_text.pack(fill="both", expand=True, padx=25, pady=(0, 25))
        
        # 按钮区域
        button_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=25, pady=(0, 20))
        
        # 导入按钮
        import_button = ctk.CTkButton(
            button_frame, 
            text="导入人设", 
            command=self.import_profile,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8,
            border_spacing=10
        )
        import_button.pack(side="left", padx=5)
        
        # 导出按钮
        export_button = ctk.CTkButton(
            button_frame, 
            text="导出人设", 
            command=self.export_profile,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=120,
            corner_radius=8,
            border_spacing=10
        )
        export_button.pack(side="left", padx=5)
        
        # 复制按钮
        copy_button = ctk.CTkButton(
            button_frame, 
            text="复制", 
            command=self.copy_result,
            font=Theme.get_font(size=14, weight="bold"),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=38,
            width=100,
            corner_radius=8,
            border_spacing=10
        )
        copy_button.pack(side="right", padx=5)
    
    def generate_profile(self):
        """生成人设"""
        # 获取输入内容
        character_desc = self.character_desc_text.get_text().strip()
        polish_desc = self.polish_desc_text.get_text().strip()
        
        # 检查输入
        if not character_desc:
            messagebox.showwarning("警告", "请输入角色描述！")
            return
        
        # 显示生成中提示
        self.character_result_text.set_text("正在生成人设，请稍候...")
        
        # 在后台线程中生成人设
        def generate_in_thread():
            try:
                # 调用API生成人设
                api_tester = APITester(
                    self.app.config.get("character_api", {}).get("url", ""),
                    self.app.config.get("character_api", {}).get("api_key", ""),
                    self.app.config.get("character_api", {}).get("model", "")
                )
                
                # 准备提示词
                prompt = f"请根据以下描述生成一个角色人设：\n{character_desc}"
                if polish_desc:
                    prompt += f"\n\n润色要求：\n{polish_desc}"
                
                # 调用API
                response = api_tester.generate_character_profile(prompt)
                
                # 更新结果
                self.app.after(0, lambda: self.character_result_text.set_text(response))
                
                # 保存生成的人设
                self.app.generated_profile = response
                
            except Exception as e:
                error_msg = handle_api_error(e, "人设生成")
                self.app.after(0, lambda: self.character_result_text.set_text(
                    f"生成失败！\n\n错误信息：{error_msg}"
                ))
        
        # 启动线程
        threading.Thread(target=generate_in_thread, daemon=True).start()
    
    def polish_profile(self):
        """润色人设"""
        # 检查是否有生成的人设
        if not self.app.generated_profile:
            messagebox.showwarning("警告", "请先生成人设！")
            return
        
        # 获取润色要求
        polish_desc = self.polish_desc_text.get_text().strip()
        if not polish_desc:
            messagebox.showwarning("警告", "请输入润色要求！")
            return
        
        # 显示润色中提示
        self.character_result_text.set_text("正在润色人设，请稍候...")
        
        # 在后台线程中润色人设
        def polish_in_thread():
            try:
                # 调用API润色人设
                api_tester = APITester(
                    self.app.config.get("character_api", {}).get("url", ""),
                    self.app.config.get("character_api", {}).get("api_key", ""),
                    self.app.config.get("character_api", {}).get("model", "")
                )
                
                # 准备提示词
                prompt = f"请根据以下要求润色这个角色人设：\n\n原人设：\n{self.app.generated_profile}\n\n润色要求：\n{polish_desc}"
                
                # 调用API
                response = api_tester.polish_character_profile(prompt)
                
                # 更新结果
                self.app.after(0, lambda: self.character_result_text.set_text(response))
                
                # 更新保存的人设
                self.app.generated_profile = response
                
            except Exception as e:
                error_msg = handle_api_error(e, "人设润色")
                self.app.after(0, lambda: self.character_result_text.set_text(
                    f"润色失败！\n\n错误信息：{error_msg}"
                ))
        
        # 启动线程
        threading.Thread(target=polish_in_thread, daemon=True).start()
    
    def import_profile(self):
        """导入人设"""
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
                content = f.read()
            
            # 更新结果显示
            self.character_result_text.set_text(content)
            
            # 保存导入的人设
            self.app.generated_profile = content
            
            messagebox.showinfo("提示", "人设文件导入成功！")
            
        except Exception as e:
            messagebox.showerror("导入失败", f"读取人设文件时出错: {str(e)}")
    
    def export_profile(self):
        """导出人设"""
        # 检查是否有可导出的内容
        content = self.character_result_text.get_text().strip()
        if not content:
            messagebox.showwarning("警告", "没有可导出的人设内容！")
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
            # 保存文件内容
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            messagebox.showinfo("提示", "人设文件导出成功！")
            
        except Exception as e:
            messagebox.showerror("导出失败", f"保存人设文件时出错: {str(e)}")
    
    def clear_input(self):
        """清空输入框"""
        self.character_desc_text.clear()
        self.polish_desc_text.clear()
        self.character_result_text.clear()
        self.app.generated_profile = None
        messagebox.showinfo("提示", "已清空所有输入和结果！")
    
    def copy_result(self):
        """复制结果文本"""
        # 获取当前结果文本
        result_text = self.character_result_text.get_text().strip()
        
        if not result_text:
            messagebox.showwarning("提示", "没有可复制的结果文本！")
            return
        
        # 使用系统剪贴板复制文本
        try:
            self.app.clipboard_clear()
            self.app.clipboard_append(result_text)
            messagebox.showinfo("提示", "结果文本已复制到剪贴板！")
        except Exception as e:
            messagebox.showerror("复制失败", f"复制结果文本时出错: {str(e)}") 
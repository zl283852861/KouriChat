"""侧边栏模块，提供应用程序的导航功能"""

import os
import sys
import math
import tkinter as tk
import webbrowser
import customtkinter as ctk
from PIL import Image, ImageTk

class Sidebar:
    """侧边栏类"""
    
    def __init__(self, app):
        self.app = app
        
        # 侧边栏宽度 - 统一深色和浅色模式的宽度
        self.width = 240
        
        # 动画参数
        self.animation_duration = 300  # 动画持续时间(毫秒)
        self.animation_steps = 15  # 动画步数
        self.is_animating = False  # 动画状态标记
        
        # 侧边栏颜色
        self.sidebar_colors = {
            "light": "#0078D7",  # Windows蓝色
            "dark": "#1a1a1a"    # 深灰色
        }
        
        # 设置侧边栏
        self.setup_sidebar()
        
        # 创建两层蒙版框架 - 分别用于扩展和收缩动画
        self.expand_mask_frame = tk.Frame(
            self.app,
            background=self.get_sidebar_color()
        )
        self.shrink_mask_frame = tk.Frame(
            self.app,
            background=self.get_sidebar_color()
        )
    
    def get_sidebar_color(self):
        """获取当前主题下的侧边栏颜色"""
        return self.sidebar_colors["dark"] if self.app.current_theme == "dark" else self.sidebar_colors["light"]
    
    def setup_sidebar(self):
        """设置侧边栏"""
        # 创建侧边栏框架 - 修改颜色配置，浅色模式为Windows蓝
        self.sidebar_frame = ctk.CTkFrame(
            self.app, 
            width=self.width, 
            corner_radius=0,
            fg_color=(self.sidebar_colors["light"], self.sidebar_colors["dark"])
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)  # 底部空白区域可扩展
        
        # 添加应用标题 - 更新样式
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="Kouri Chat",
            font=ctk.CTkFont(family="Segoe Script", size=32, weight="bold"),
            text_color=("white", "white")  # 在亮色和暗色模式下都使用白色文字
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(35, 35))
        
        # 添加分割线
        self.separator = ctk.CTkFrame(
            self.sidebar_frame,
            height=2,
            fg_color=("#E0E0E0", "#505050")  # 使用十六进制颜色
        )
        self.separator.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 20))
        
        # 添加侧边栏按钮 - 使用更现代的样式
        self.sidebar_buttons = []
        
        # 人设按钮
        self.character_button = ctk.CTkButton(
            self.sidebar_frame,
            text="人设生成",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=16, weight="bold"),
            command=lambda: self.handle_page_switch(self.app.show_character_page, self.character_button),
            fg_color="transparent",
            hover_color=("#1a90ff", "#424242"),
            text_color=("white", "white"),
            anchor="center",
            height=42,
            corner_radius=10,
            border_width=1,
            border_color=("#66B2FF", "#333333"),  # 使用更深的浅蓝色边框
            border_spacing=8
        )
        self.character_button.grid(row=2, column=0, padx=20, pady=7, sticky="ew")
        self.sidebar_buttons.append(self.character_button)
        
        # API配置按钮
        self.api_config_button = ctk.CTkButton(
            self.sidebar_frame,
            text="API 配置",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=16, weight="bold"),
            command=lambda: self.handle_page_switch(self.app.show_api_config_page, self.api_config_button),
            fg_color="transparent",
            hover_color=("#1a90ff", "#424242"),
            text_color=("white", "white"),
            anchor="center",
            height=42,
            corner_radius=10,
            border_width=1,
            border_color=("#66B2FF", "#333333"),
            border_spacing=8
        )
        self.api_config_button.grid(row=3, column=0, padx=20, pady=7, sticky="ew")
        self.sidebar_buttons.append(self.api_config_button)
        
        # 图片按钮
        self.image_button = ctk.CTkButton(
            self.sidebar_frame,
            text="图片工具",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=16, weight="bold"),
            command=lambda: self.handle_page_switch(self.app.show_image_page, self.image_button),
            fg_color="transparent",
            hover_color=("#1a90ff", "#424242"),
            text_color=("white", "white"),
            anchor="center",
            height=42,
            corner_radius=10,
            border_width=1,
            border_color=("#66B2FF", "#333333"),
            border_spacing=8
        )
        self.image_button.grid(row=4, column=0, padx=20, pady=7, sticky="ew")
        self.sidebar_buttons.append(self.image_button)
        
        # 帮助按钮
        self.help_button = ctk.CTkButton(
            self.sidebar_frame,
            text="帮助中心",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=16, weight="bold"),
            command=lambda: self.handle_page_switch(self.app.show_help_page, self.help_button),
            fg_color="transparent",
            hover_color=("#1a90ff", "#424242"),
            text_color=("white", "white"),
            anchor="center",
            height=42,
            corner_radius=10,
            border_width=1,
            border_color=("#66B2FF", "#333333"),
            border_spacing=8
        )
        self.help_button.grid(row=5, column=0, padx=20, pady=7, sticky="ew")
        self.sidebar_buttons.append(self.help_button)
        
        # 添加底部分割线
        self.bottom_separator = ctk.CTkFrame(
            self.sidebar_frame,
            height=2,
            fg_color=("#E0E0E0", "#505050")  # 使用十六进制颜色
        )
        self.bottom_separator.grid(row=6, column=0, sticky="ew", padx=15, pady=(20, 15))
        
        # 创建主题切换框架 - 美化版本
        self.theme_frame = ctk.CTkFrame(
            self.sidebar_frame,
            fg_color="transparent"
        )
        self.theme_frame.grid(row=7, column=0, padx=20, pady=(10, 10), sticky="ew")
        
        # 主题文本（移除了图标）
        mode_text = "深色模式" if self.app.current_theme == "dark" else "浅色模式"
        
        # 创建主题文本标签 - 使用更优雅的字体和排版
        self.appearance_mode_label = ctk.CTkLabel(
            self.theme_frame,
            text=mode_text,
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=14, weight="bold"),
            text_color=("white", "white"),
            anchor="w"
        )
        self.appearance_mode_label.grid(row=0, column=0, padx=0, pady=5, sticky="w")
        
        # 创建主题切换开关 - 改进样式
        self.app.appearance_mode_switch = ctk.CTkSwitch(
            self.theme_frame,
            text="",
            command=self.app.toggle_theme,
            progress_color=("#66B2FF", "#505050"),
            button_color=("white", "white"),
            button_hover_color=("#e6e6e6", "#d9d9d9"),
            switch_width=46,
            switch_height=24
        )
        self.app.appearance_mode_switch.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="e")
        
        # 配置主题框架列权重，使开关靠右对齐
        self.theme_frame.grid_columnconfigure(0, weight=1)
        
        # 版权信息
        copyright_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="© 2025 Kouri Chat V12.0",
            font=ctk.CTkFont(family="Arial Unicode MS", size=12),
            text_color=("#E0E0E0", "#A0A0A0")  # 使用十六进制颜色
        )
        copyright_label.grid(row=8, column=0, padx=20, pady=(5, 20), sticky="sw")
        
        # 根据当前主题设置开关状态
        if self.app.current_theme == "dark":
            self.app.appearance_mode_switch.select()
        else:
            self.app.appearance_mode_switch.deselect()
    
    def highlight_button(self, active_button):
        """高亮当前选中的侧边栏按钮"""
        for button in self.sidebar_buttons:
            if button == active_button:
                # 使用高亮背景色
                button.configure(
                    fg_color=("#1a90ff", "#424242"),  # 更鲜艳的背景色
                    text_color=("white", "white"),
                    border_color=("#99B2FF", "#666666")  # 高亮时使用更深的蓝色边框
                )
            else:
                button.configure(
                    fg_color="transparent",
                    text_color=("white", "white"),
                    border_color=("#66B2FF", "#333333")  # 恢复默认边框颜色
                )
    
    def handle_page_switch(self, show_page_func, target_button):
        """处理页面切换逻辑"""
        # 如果已经在动画中，不执行新动画
        if self.is_animating:
            return
            
        # 检查是否点击的是当前高亮按钮
        is_current_button = False
        for button in self.sidebar_buttons:
            if button == target_button and button.cget("fg_color") != "transparent":
                is_current_button = True
                break
                
        # 如果点击当前已高亮按钮，不执行动画
        if is_current_button:
            return
            
        # 设置动画状态
        self.is_animating = True
        
        # 保存要执行的函数和按钮
        self.target_page_func = show_page_func
        self.target_button = target_button
        
        # 获取内容区域尺寸和位置
        content_frame = self.app.content_frame
        content_x = content_frame.winfo_x()
        content_y = content_frame.winfo_y()
        content_width = content_frame.winfo_width()
        content_height = content_frame.winfo_height()
        
        # 更新两个蒙版颜色，以确保它们与当前主题匹配
        self.expand_mask_frame.configure(background=self.get_sidebar_color())
        self.shrink_mask_frame.configure(background=self.get_sidebar_color())
        
        # 放置扩展蒙版在内容区域左侧边缘，确保不遮挡侧边栏
        self.expand_mask_frame.place(x=content_x, y=content_y, width=1, height=content_height)
        self.expand_mask_frame.lift()  # 确保蒙版在最上层
        
        # 开始扩展动画，使用缓动效果
        self.animate_mask_expand(0, content_width)
    
    def animate_mask_expand(self, step, max_width):
        """蒙版扩展动画，使用缓出效果"""
        if step >= self.animation_steps:
            # 扩展完成，立即切换页面并准备收缩动画
            self.prepare_page_switch(max_width)
            return
        
        # 使用缓出效果（ease-out）计算当前宽度：开始快，结束慢
        progress = step / self.animation_steps
        # 使用缓出二次方公式: 1 - (1 - t)^2
        eased_progress = 1 - math.pow(1 - progress, 2)
        width = eased_progress * max_width
        
        # 更新蒙版宽度
        self.expand_mask_frame.place_configure(width=int(width))
        
        # 下一步
        step_time = self.animation_duration / (self.animation_steps * 2)  # 分配一半时间给扩展
        self.app.after(int(step_time), lambda: self.animate_mask_expand(step + 1, max_width))
    
    def prepare_page_switch(self, max_width):
        """准备页面切换，设置全屏蒙版并切换页面"""
        # 获取内容区域尺寸和位置
        content_frame = self.app.content_frame
        content_x = content_frame.winfo_x()
        content_y = content_frame.winfo_y()
        content_width = content_frame.winfo_width()
        content_height = content_frame.winfo_height()
        
        # 设置全屏蒙版，覆盖整个内容区域
        self.shrink_mask_frame.place(x=content_x, y=content_y, width=content_width, height=content_height)
        self.shrink_mask_frame.lift()  # 确保蒙版在最上层
        
        # 隐藏扩展蒙版
        self.expand_mask_frame.place_forget()
        
        # 切换页面
        self.switch_page()
        
        # 短暂延迟后开始收缩动画
        self.app.after(30, lambda: self.animate_mask_shrink(0, max_width))
    
    def animate_mask_shrink(self, step, max_width):
        """蒙版收缩动画，使用缓入效果"""
        if step >= self.animation_steps:
            # 收缩完成，移除蒙版
            self.shrink_mask_frame.place_forget()
            self.is_animating = False
            return
        
        # 使用缓入效果（ease-in）计算当前宽度：开始慢，结束快
        progress = step / self.animation_steps
        # 使用缓入二次方公式: t^2
        eased_progress = progress * progress
        
        # 计算当前宽度 - 保持x位置不变，只缩减宽度从右向左
        width = max_width * (1 - eased_progress)
        
        # 更新蒙版宽度，x位置保持在内容区域左侧边缘
        content_x = self.app.content_frame.winfo_x()
        self.shrink_mask_frame.place_configure(x=content_x, width=int(width))
        
        # 下一步
        step_time = self.animation_duration / (self.animation_steps * 2)  # 分配一半时间给收缩
        self.app.after(int(step_time), lambda: self.animate_mask_shrink(step + 1, max_width))
    
    def switch_page(self):
        """切换到目标页面"""
        self.target_page_func() 
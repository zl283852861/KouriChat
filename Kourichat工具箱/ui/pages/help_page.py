"""帮助页面模块，提供应用程序的使用指南和关于信息"""

import tkinter as tk
import webbrowser
import customtkinter as ctk
from ..theme import Theme

class HelpPage:
    """帮助页面类"""
    
    def __init__(self, app):
        self.app = app
        self.setup_help_page()
    
    def setup_help_page(self):
        """设置帮助页面内容"""
        # 创建外层框架
        outer_frame = ctk.CTkFrame(self.app.help_frame, fg_color="transparent")
        outer_frame.pack(fill="both", expand=True)
        
        # 页面标题
        title_label = ctk.CTkLabel(
            outer_frame, 
            text="帮助与关于", 
            font=Theme.get_font(size=28, weight="bold"),
            text_color=Theme.TEXT_PRIMARY,
            anchor="center"
        )
        title_label.pack(pady=(30, 25))
        
        # 创建主内容卡片
        main_card = ctk.CTkFrame(
            outer_frame,
            fg_color=Theme.CARD_BG,
            corner_radius=15
        )
        main_card.pack(fill="both", expand=True, padx=40, pady=(0, 30))
        
        # 创建内容框架
        content_frame = ctk.CTkFrame(main_card, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=25, pady=25)
        content_frame.pack_propagate(False)
        
        # 左侧：使用帮助
        left_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 15))
        
        help_title = ctk.CTkLabel(
            left_frame,
            text="使用帮助",
            font=Theme.get_font(size=22, weight="bold"),
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        )
        help_title.pack(anchor="w", pady=(0, 20))
        
        # 创建左侧滚动区域
        help_scroll = ctk.CTkScrollableFrame(
            left_frame, 
            fg_color=Theme.BG_SECONDARY,
            scrollbar_fg_color=Theme.SCROLLBAR_FG,
            scrollbar_button_color=Theme.SCROLLBAR_BG,
            scrollbar_button_hover_color=Theme.SCROLLBAR_HOVER,
            corner_radius=10
        )
        help_scroll.pack(fill="both", expand=True)
        
        # 添加帮助内容
        self.create_help_sections(help_scroll)
        
        # 右侧：关于软件和联系方式
        right_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        right_frame.pack(side="right", fill="both", expand=True, padx=(15, 0))
        
        # 关于软件
        self.setup_about_section(right_frame)
        
        # 联系方式
        self.setup_contact_section(right_frame)
    
    def setup_about_section(self, parent_frame):
        """设置关于软件部分"""
        about_title = ctk.CTkLabel(
            parent_frame,
            text="关于软件",
            font=Theme.get_font(size=22, weight="bold"),
            text_color=Theme.TEXT_PRIMARY,
            anchor="w"
        )
        about_title.pack(anchor="w", pady=(0, 20))
        
        # 软件信息卡片
        about_card = ctk.CTkFrame(
            parent_frame, 
            fg_color=Theme.BG_SECONDARY,
            corner_radius=10,
            height=160
        )
        about_card.pack(fill="x", pady=(0, 25))
        about_card.pack_propagate(False)
        
        # Logo
        logo_label = ctk.CTkLabel(
            about_card,
            text="Kouri Chat",
            font=Theme.get_font(size=36, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        logo_label.pack(pady=(35, 10))
        
        # 版本号
        version_label = ctk.CTkLabel(
            about_card,
            text="版本 12.0.0",
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_SECONDARY
        )
        version_label.pack(pady=(0, 10))
        
        # 版权信息
        copyright_label = ctk.CTkLabel(
            about_card,
            text="© 2025 KouriChat Team",
            font=Theme.get_font(size=12),
            text_color=Theme.TEXT_TERTIARY
        )
        copyright_label.pack()
    
    def setup_contact_section(self, parent_frame):
        """设置联系我们区域"""
        # 标题
        title_frame = ctk.CTkFrame(parent_frame, fg_color="transparent", height=50)
        title_frame.pack(fill="x", pady=(0, 15))
        title_frame.pack_propagate(False)
        
        contact_title = ctk.CTkLabel(
            title_frame,
            text="联系我们",
            font=Theme.get_font(size=22, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        contact_title.pack(side="left")
        
        # 联系方式容器
        contact_container = ctk.CTkFrame(
            parent_frame,
            fg_color=Theme.BG_SECONDARY,
            corner_radius=15
        )
        contact_container.pack(fill="both", expand=True)
        
        # 联系方式列表
        contact_list = ctk.CTkFrame(contact_container, fg_color="transparent")
        contact_list.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 官方网站
        website_frame = ctk.CTkFrame(contact_list, fg_color="transparent", height=45)
        website_frame.pack(fill="x", pady=(0, 15))
        website_frame.pack_propagate(False)
        
        website_label = ctk.CTkLabel(
            website_frame,
            text="主项目官方网站",
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_PRIMARY,
            width=120,
            anchor="w"
        )
        website_label.pack(side="left")
        
        website_button = ctk.CTkButton(
            website_frame,
            text="kourichat.com",
            command=lambda: webbrowser.open("https://kourichat.com"),
            font=Theme.get_font(size=14),
            fg_color=Theme.BG_TERTIARY,
            hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            height=35,
            corner_radius=8
        )
        website_button.pack(side="right")
        
        # 主项目GitHub
        main_github_frame = ctk.CTkFrame(contact_list, fg_color="transparent", height=45)
        main_github_frame.pack(fill="x", pady=(0, 15))
        main_github_frame.pack_propagate(False)
        
        main_github_label = ctk.CTkLabel(
            main_github_frame,
            text="主项目GitHub",
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_PRIMARY,
            width=120,
            anchor="w"
        )
        main_github_label.pack(side="left")
        
        main_github_button = ctk.CTkButton(
            main_github_frame,
            text="KouriChat/KouriChat",
            command=lambda: webbrowser.open("https://github.com/KouriChat/KouriChat"),
            font=Theme.get_font(size=14),
            fg_color=Theme.BG_TERTIARY,
            hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            height=35,
            corner_radius=8
        )
        main_github_button.pack(side="right")
        
        # QQ群
        qq_frame = ctk.CTkFrame(contact_list, fg_color="transparent", height=45)
        qq_frame.pack(fill="x", pady=(0, 15))
        qq_frame.pack_propagate(False)
        
        qq_label = ctk.CTkLabel(
            qq_frame,
            text="工具箱QQ群",
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_PRIMARY,
            width=120,
            anchor="w"
        )
        qq_label.pack(side="left")
        
        qq_button = ctk.CTkButton(
            qq_frame,
            text="639849597",
            command=lambda: self.copy_to_clipboard("639849597"),
            font=Theme.get_font(size=14),
            fg_color=Theme.BG_TERTIARY,
            hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            height=35,
            corner_radius=8
        )
        qq_button.pack(side="right")
        
        # 工具箱GitHub
        github_frame = ctk.CTkFrame(contact_list, fg_color="transparent", height=45)
        github_frame.pack(fill="x")
        github_frame.pack_propagate(False)
        
        github_label = ctk.CTkLabel(
            github_frame,
            text="工具箱GitHub",
            font=Theme.get_font(size=14),
            text_color=Theme.TEXT_PRIMARY,
            width=120,
            anchor="w"
        )
        github_label.pack(side="left")
        
        github_button = ctk.CTkButton(
            github_frame,
            text="linxiajin08/linxiajinKouri",
            command=lambda: webbrowser.open("https://github.com/linxiajin08/linxiajinKouri"),
            font=Theme.get_font(size=14),
            fg_color=Theme.BG_TERTIARY,
            hover_color=Theme.BUTTON_SECONDARY_HOVER,
            text_color=Theme.TEXT_PRIMARY,
            height=35,
            corner_radius=8
        )
        github_button.pack(side="right")
    
    def create_help_sections(self, parent):
        """创建所有帮助章节"""
        sections = [
            {
                "title": "在「角色人设」页面，您可以：",
                "items": [
                    "输入简要的角色描述，生成详细人设",
                    "对已有人设进行润色，使其更加丰富",
                    "导入导出人设，以便保存和共享"
                ]
            },
            {
                "title": "在「API配置」页面，您可以：",
                "items": [
                    "配置AI服务的API地址和密钥",
                    "设置用于不同功能的模型参数",
                    "测试API连接确保正常工作"
                ]
            },
            {
                "title": "在「图片处理」页面，您可以：",
                "items": [
                    "上传图片并进行智能识别和描述",
                    "通过文本描述生成新的图片",
                    "保存和导出生成的图片结果"
                ]
            },
            {
                "title": "使用技巧",
                "items": [
                    "人设描述越详细，生成的人设越丰富",
                    "适当调整模型参数，获得不同风格的输出",
                    "为获得更好的图片生成效果，请使用详细且有创意的描述"
                ]
            }
        ]
        
        for section in sections:
            self.create_help_section(parent, section["title"], section["items"])
    
    def create_help_section(self, parent, title, items):
        """创建帮助章节"""
        section_frame = ctk.CTkFrame(
            parent, 
            fg_color="transparent",
            corner_radius=8
        )
        section_frame.pack(fill="x", pady=(0, 20), padx=15)
        
        # 章节标题
        title_label = ctk.CTkLabel(
            section_frame,
            text=title,
            font=Theme.get_font(size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY,
            justify="left",
            anchor="w"
        )
        title_label.pack(anchor="w", pady=(0, 12))
        
        # 章节内容
        for i, item in enumerate(items):
            item_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
            item_frame.pack(fill="x", pady=(0, 8))
            
            # 序号
            bullet_label = ctk.CTkLabel(
                item_frame,
                text=f"{i+1}.",
                font=Theme.get_font(size=14),
                text_color=Theme.TEXT_SECONDARY,
                width=25,
                anchor="e"
            )
            bullet_label.pack(side="left")
            
            # 内容
            item_text = ctk.CTkLabel(
                item_frame,
                text=item,
                font=Theme.get_font(size=14),
                text_color=Theme.TEXT_SECONDARY,
                justify="left",
                anchor="w",
                wraplength=350
            )
            item_text.pack(side="left", padx=(8, 0), fill="x", expand=True)
    
    def create_contact_button(self, parent, label, value, action):
        """创建联系方式按钮"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=6)
        
        # 标签
        text_label = ctk.CTkLabel(
            frame,
            text=f"{label}：",
            font=Theme.get_font(size=14, weight="bold"),
            text_color=Theme.TEXT_PRIMARY,
            anchor="w",
            width=100
        )
        text_label.pack(side="left")
        
        # 按钮
        button = ctk.CTkButton(
            frame,
            text=value,
            command=lambda v=value: self.copy_to_clipboard(v) if action == "copy" else webbrowser.open(v),
            font=Theme.get_font(size=14),
            fg_color=Theme.BUTTON_PRIMARY,
            hover_color=Theme.BUTTON_PRIMARY_HOVER,
            height=32,
            corner_radius=6,
            width=260,
            anchor="w"
        )
        button.pack(side="left", padx=(5, 0))
        
        # 提示标签
        hint_text = "点击复制" if action == "copy" else "点击跳转"
        hint_label = ctk.CTkLabel(
            frame,
            text=hint_text,
            font=Theme.get_font(size=12),
            text_color=Theme.TEXT_TERTIARY
        )
        hint_label.pack(side="left", padx=(8, 0))
    
    def copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        self.app.clipboard_clear()
        self.app.clipboard_append(text)
        self.app.update()
        
        # 显示提示窗口
        popup = tk.Toplevel(self.app)
        popup.wm_title("提示")
        popup.geometry("200x80")
        popup.resizable(False, False)
        
        # 居中显示
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (width // 2)
        y = (popup.winfo_screenheight() // 2) - (height // 2)
        popup.geometry(f'+{x}+{y}')
        
        # 设置样式
        popup.configure(bg=Theme.BG_SECONDARY[0])
        popup.attributes("-topmost", True)
        
        # 提示信息
        label = tk.Label(
            popup, 
            text=f"已复制到剪贴板：\n{text}", 
            bg=Theme.BG_SECONDARY[0],
            fg=Theme.TEXT_PRIMARY[0],
            padx=10, 
            pady=10
        )
        label.pack(fill="both", expand=True)
        
        # 2秒后自动关闭
        popup.after(2000, popup.destroy) 
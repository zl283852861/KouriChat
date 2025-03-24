"""
主题管理模块，负责应用程序的主题切换和管理
"""

import customtkinter as ctk

class ThemeManager:
    """主题管理类，控制应用程序的明暗主题切换"""
    
    @staticmethod
    def apply_theme(app_instance, theme_name):
        """
        应用指定的主题到应用程序
        
        Args:
            app_instance: 应用程序实例
            theme_name: 主题名称 (light/dark/system)
        """
        # 应用主题模式
        ctk.set_appearance_mode(theme_name if theme_name != "system" else "system")
        
        # 设置侧边栏颜色
        sidebar_colors = {"light": "#0078D7", "dark": "#1a1a1a"}
        sidebar_color = sidebar_colors.get(theme_name, sidebar_colors["light"])
        
        # 获取侧边栏组件并设置颜色
        if hasattr(app_instance, 'sidebar') and hasattr(app_instance.sidebar, 'sidebar_frame'):
            app_instance.sidebar.sidebar_frame.configure(fg_color=sidebar_color)
        elif hasattr(app_instance, 'sidebar_frame'):
            app_instance.sidebar_frame.configure(fg_color=sidebar_color)
        
        # 更新配置
        app_instance.current_theme = theme_name
        app_instance.config["theme"] = theme_name
        
        # 更新主题开关状态
        if hasattr(app_instance, 'appearance_mode_switch'):
            if theme_name == "dark":
                app_instance.appearance_mode_switch.select()
            else:
                app_instance.appearance_mode_switch.deselect()
                
        # 更新主题标签文本
        if hasattr(app_instance, 'sidebar') and hasattr(app_instance.sidebar, 'appearance_mode_label'):
            text = "深色模式" if theme_name == "dark" else "浅色模式"
            app_instance.sidebar.appearance_mode_label.configure(text=text)
        
        # 强制更新UI
        app_instance.update_idletasks()
        
        # 通知主题动画
        if hasattr(app_instance, 'theme_transition'):
            app_instance.after(100, app_instance.theme_transition.notify_theme_applied)
    
    @staticmethod
    def toggle_theme(app_instance):
        """
        切换应用程序的明暗主题
        
        Args:
            app_instance: 应用程序实例
        """
        # 获取当前主题和目标主题
        current_theme = app_instance.current_theme
        target_theme = "dark" if current_theme != "dark" else "light"
        
        # 如果有主题过渡动画，使用动画切换
        if hasattr(app_instance, 'theme_transition'):
            app_instance.theme_transition.start_transition()
            app_instance.after(200, lambda: ThemeManager.apply_theme(app_instance, target_theme))
        else:
            # 直接应用主题
            theme = "dark" if app_instance.appearance_mode_switch.get() == 1 else "light"
            ThemeManager.apply_theme(app_instance, theme)
        
        # 保存配置
        from core.config import APIConfig
        APIConfig.save_config(app_instance.config)
        
        # 在这里添加对 API 配置页面按钮颜色更新的调用
        if hasattr(app_instance, 'api_config_page'):
            app_instance.api_config_page.update_button_colors() 
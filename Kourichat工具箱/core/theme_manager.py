import customtkinter as ctk

class ThemeManager:
    """主题管理类"""
    
    @staticmethod
    def apply_theme(app_instance, theme_name):
        """应用主题"""
        if theme_name == "light":
            ctk.set_appearance_mode("light")
        elif theme_name == "dark":
            ctk.set_appearance_mode("dark")
        else:  # system
            ctk.set_appearance_mode("system")
        
        # 更新配置
        app_instance.current_theme = theme_name
        app_instance.config["theme"] = theme_name
        
        # 更新主题开关状态
        if hasattr(app_instance, 'appearance_mode_switch'):
            if theme_name == "dark":
                app_instance.appearance_mode_switch.select()
            else:
                app_instance.appearance_mode_switch.deselect()
    
    @staticmethod
    def toggle_theme(app_instance):
        """切换明暗主题"""
        if app_instance.appearance_mode_switch.get() == 1:  # 开关打开，使用暗色主题
            ThemeManager.apply_theme(app_instance, "dark")
        else:  # 开关关闭，使用亮色主题
            ThemeManager.apply_theme(app_instance, "light")
        
        # 保存配置
        from core.config import APIConfig
        APIConfig.save_config(app_instance.config) 
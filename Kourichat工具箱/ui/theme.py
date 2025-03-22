"""主题模块，提供应用程序的颜色和字体统一管理"""

import customtkinter as ctk

class Theme:
    """主题配置类"""
    
    # 主色调
    PRIMARY = ("#0078D7", "#1a90ff")  # (浅色模式, 深色模式)
    PRIMARY_HOVER = ("#1a90ff", "#40a9ff")
    
    # 背景色
    BG_PRIMARY = ("white", "#1a1a1a")
    BG_SECONDARY = ("#f5f5f5", "#2b2b2b")
    BG_TERTIARY = ("#e6e6e6", "#333333")
    
    # 卡片背景
    CARD_BG = ("#ffffff", "#2b2b2b")
    CARD_BG_HOVER = ("#f0f0f0", "#333333")
    
    # 文本颜色
    TEXT_PRIMARY = ("#000000", "#ffffff")
    TEXT_SECONDARY = ("#666666", "#a6a6a6")
    TEXT_TERTIARY = ("#999999", "#808080")
    
    # 边框颜色
    BORDER = ("#e0e0e0", "#404040")
    
    # 输入框
    INPUT_BG = ("#f5f5f5", "#2b2b2b")
    INPUT_BORDER = ("#d9d9d9", "#404040")
    INPUT_BORDER_FOCUS = ("#1a90ff", "#40a9ff")
    
    # 滚动条
    SCROLLBAR_BG = ("#f0f0f0", "#333333")
    SCROLLBAR_FG = ("#c0c0c0", "#4d4d4d")
    SCROLLBAR_HOVER = ("#a6a6a6", "#666666")
    
    # 标签页
    TAB_BG = ("#f0f0f0", "#2b2b2b")
    TAB_SELECTED = ("#0078D7", "#1a90ff")
    TAB_HOVER = ("#e6e6e6", "#333333")
    
    # 按钮
    BUTTON_PRIMARY = ("#0078D7", "#1a90ff")
    BUTTON_PRIMARY_HOVER = ("#1a90ff", "#40a9ff")
    BUTTON_SECONDARY = ("#f5f5f5", "#2b2b2b")
    BUTTON_SECONDARY_HOVER = ("#e6e6e6", "#333333")
    BUTTON_DANGER = ("#ff4d4f", "#ff7875")
    BUTTON_DANGER_HOVER = ("#ff7875", "#ffa39e")
    
    # 字体
    FONT_FAMILY = "Microsoft YaHei UI"
    
    @classmethod
    def get_font(cls, size=14, weight="normal"):
        """获取字体配置"""
        return ctk.CTkFont(family=cls.FONT_FAMILY, size=size, weight=weight) 
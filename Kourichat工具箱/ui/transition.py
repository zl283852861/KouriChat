"""页面过渡动画模块，提供界面切换效果"""

import customtkinter as ctk

class PageTransition:
    """页面过渡管理器，处理UI页面之间的切换效果"""
    
    def __init__(self, app):
        """
        初始化过渡管理器
        
        Args:
            app: 应用程序主实例
        """
        self.app = app
        
        # 当前页面和目标页面
        self.current_frame = None
        self.target_frame = None
        self.target_button = None
        
        # 状态标记
        self.is_animating = False
    
    def transit_to(self, target_frame, target_button):
        """
        切换到目标页面
        
        Args:
            target_frame: 目标页面框架
            target_button: 应该高亮的侧边栏按钮
        """
        # 如果已经在处理中或当前页面就是目标页面，不执行新的切换
        if self.is_animating:
            return
        
        # 获取当前可见页面
        frames = [self.app.character_frame, self.app.api_config_frame, 
                 self.app.image_frame, self.app.help_frame]
        
        self.current_frame = next((frame for frame in frames if frame.winfo_ismapped()), None)
        
        # 如果当前页面就是目标页面，不执行切换
        if self.current_frame == target_frame:
            return
        
        # 记录目标页面和按钮
        self.target_frame = target_frame
        self.target_button = target_button
        
        # 设置状态
        self.is_animating = True
        
        # 执行页面切换
        self.switch_page()
        self.is_animating = False
    
    def switch_page(self):
        """执行页面切换操作"""
        # 隐藏当前页面
        if self.current_frame:
            self.current_frame.pack_forget()
        
        # 显示目标页面
        self.target_frame.pack(fill="both", expand=True)
        
        # 高亮目标按钮
        self.app.highlight_sidebar_button(self.target_button) 
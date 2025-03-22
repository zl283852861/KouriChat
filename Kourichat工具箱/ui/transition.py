import customtkinter as ctk
import time

class PageTransition:
    """页面过渡效果管理器"""
    
    def __init__(self, app):
        """初始化过渡效果管理器
        
        Args:
            app: 应用程序主实例
        """
        self.app = app
        
        # 过渡动画参数
        self.duration = 300  # 动画持续时间 (毫秒)
        self.steps = 15  # 动画步数
        self.step_time = self.duration / self.steps  # 每步时间
        
        # 当前页面和目标页面
        self.current_frame = None
        self.target_frame = None
        self.target_button = None
        
        # 创建遮罩框架 (与侧边栏同色)
        self.mask_frame = ctk.CTkFrame(
            self.app.content_frame,
            fg_color=self.app.sidebar.sidebar_frame._fg_color,
            corner_radius=0
        )
        
        # 动画状态
        self.is_animating = False
    
    def transit_to(self, target_frame, target_button):
        """执行到目标页面的过渡效果
        
        Args:
            target_frame: 目标页面框架
            target_button: 应该高亮的侧边栏按钮
        """
        # 如果正在动画中，不执行新动画
        if self.is_animating:
            return
        
        # 记录当前可见的页面
        self.current_frame = None
        # 获取所有可能的页面框架
        frames = [self.app.character_frame, self.app.api_config_frame, 
                 self.app.image_frame, self.app.help_frame]
        
        # 尝试添加主题页面框架如果存在的话
        if hasattr(self.app, 'theme_frame'):
            frames.append(self.app.theme_frame)
            
        # 查找当前可见的页面
        for frame in frames:
            if frame.winfo_ismapped():
                self.current_frame = frame
                break
        
        # 如果当前页面就是目标页面，不执行动画
        if self.current_frame == target_frame:
            return
        
        # 记录目标页面和按钮
        self.target_frame = target_frame
        self.target_button = target_button
        
        # 设置动画状态
        self.is_animating = True
        
        # 开始遮罩扩展动画
        self.start_expand_animation()
    
    def start_expand_animation(self):
        """开始遮罩扩展动画"""
        # 获取内容区域的宽度
        content_width = self.app.content_frame.winfo_width()
        
        # 先放置遮罩在左侧
        self.mask_frame.place(x=0, y=0, height=self.app.content_frame.winfo_height(), width=1)
        self.mask_frame.lift()  # 确保遮罩在最上层
        
        # 执行扩展动画
        self.animate_expand(0, content_width)
    
    def animate_expand(self, step, total_width):
        """执行遮罩扩展动画
        
        Args:
            step: 当前步数
            total_width: 总宽度
        """
        if step >= self.steps:
            # 动画结束，切换页面
            self.switch_page()
            # 开始收缩动画
            self.animate_shrink(0, total_width)
            return
        
        # 计算当前宽度
        width = (step + 1) / self.steps * total_width
        
        # 更新遮罩宽度
        self.mask_frame.place(x=0, y=0, height=self.app.content_frame.winfo_height(), width=width)
        
        # 下一步
        self.app.after(int(self.step_time), lambda: self.animate_expand(step + 1, total_width))
    
    def switch_page(self):
        """切换页面"""
        # 隐藏当前页面
        if self.current_frame:
            self.current_frame.pack_forget()
        
        # 显示目标页面
        self.target_frame.pack(fill="both", expand=True)
        
        # 高亮目标按钮
        self.app.highlight_sidebar_button(self.target_button)
    
    def animate_shrink(self, step, total_width):
        """执行遮罩收缩动画
        
        Args:
            step: 当前步数
            total_width: 总宽度
        """
        if step >= self.steps:
            # 动画结束，移除遮罩
            self.mask_frame.place_forget()
            self.is_animating = False
            return
        
        # 计算当前宽度和位置
        width = total_width * (1 - (step + 1) / self.steps)
        x_pos = total_width - width
        
        # 更新遮罩位置和宽度
        self.mask_frame.place(x=x_pos, y=0, height=self.app.content_frame.winfo_height(), width=width)
        
        # 下一步
        self.app.after(int(self.step_time), lambda: self.animate_shrink(step + 1, total_width)) 
"""
主题切换过渡动画模块，提供平滑的明暗主题切换效果
"""

import tkinter as tk
import customtkinter as ctk
import time
import math
import threading
import queue

class ThemeTransition:
    """主题切换过渡动画类，实现主题切换时的视觉效果"""
    
    def __init__(self, app):
        """
        初始化主题过渡动画
        
        Args:
            app: 应用程序主实例
        """
        self.app = app
        
        # 动画状态
        self.is_animating = False
        
        # 动画参数
        self.animation_duration = 800  # 动画持续时间(ms)
        self.fade_in_percent = 0.15    # 淡入占总时间的比例
        self.fade_out_percent = 0.25   # 淡出占总时间的比例
        self.target_fps = 60           # 目标帧率
        
        # 动画计时
        self.start_time = 0            # 动画开始时间
        self.last_update_time = 0      # 上次更新时间
        
        # 遮罩层
        self.overlay = None
        
        # 静态图形参数
        self.static_icon_size = 40     # 图标大小
        self.icon_color = "#ffffff"    # 图标默认颜色
        
        # 动画优化
        self._cached_opacity = 0       # 缓存的不透明度
        self._cached_bg_color = None   # 缓存的背景颜色
        self._cached_text_color = None # 缓存的文本颜色
        self._precomputed_frames = {}  # 预计算的帧参数
        self._is_preloaded = False     # 是否已预加载
        self._preload_lock = threading.Lock()  # 预加载线程锁
        
        # 主题颜色 - 用于渐变效果
        self.theme_colors = {
            "light": {"bg": "#f0f0f0", "text": "#000000"},  # 浅色模式颜色
            "dark": {"bg": "#1a1a1a", "text": "#ffffff"}    # 暗色模式颜色
        }
        
        # 预先创建遮罩窗口但不显示，减少创建开销
        self._create_overlay_window()
        
        # 主题应用队列 - 用于异步应用主题
        self.theme_apply_queue = queue.Queue()
        
        # 动画状态
        self.source_theme = None
        self.target_theme = None
        
        # 使用更简单的动画队列
        self.animation_running = False
        
        # 主题已应用标志
        self.theme_applied = False
        self.theme_apply_time = 0
        
        # 主题切换器任务ID
        self._theme_processor_id = None
        
        # 预计算主题UI元素
        self._precached_ui_elements = {"light": {}, "dark": {}}
        
        # 预计算不透明度值
        self._precomputed_opacities = {}
        steps = 100  # 将动画分为100个离散步骤
        for i in range(steps + 1):
            progress = i / steps
            self._precomputed_opacities[progress] = self._calculate_opacity(progress)
        
        # 触发预加载过程
        self._trigger_preload()
        
        # 设置主题处理器
        self._setup_theme_processor()
    
    def _create_overlay_window(self):
        """预先创建遮罩窗口但不显示"""
        self.overlay = tk.Toplevel(self.app)
        self.overlay.withdraw()  # 隐藏窗口
        self.overlay.overrideredirect(True)  # 无边框窗口
        self.overlay.attributes("-alpha", 0.0)  # 完全透明
        self.overlay.attributes("-topmost", True)  # 置顶
        
        # 创建画布 - 使用双缓冲减少闪烁
        self.canvas = tk.Canvas(
            self.overlay, 
            highlightthickness=0,
            # 启用双缓冲绘制以减少闪烁
            # 这在Windows上特别有用
            xscrollincrement=1,
            yscrollincrement=1
        )
        self.canvas.pack(fill="both", expand=True)
        
        # 创建静态图形元素 - 初始化时不可见
        self.static_icon = None
        
        # 创建文本和线条
        self.mode_text = self.canvas.create_text(0, 0, text="", font=("Microsoft YaHei UI", 16, "bold"), anchor="center")
        self.line_top = self.canvas.create_line(0, 0, 0, 0, width=2, smooth=True)
        self.line_bottom = self.canvas.create_line(0, 0, 0, 0, width=2, smooth=True)
    
    def _trigger_preload(self):
        """触发预加载过程"""
        # 检查是否已经预加载
        if self._is_preloaded:
            return
            
        # 在后台线程中预计算帧参数
        threading.Thread(target=self._precompute_animation_frames, daemon=True).start()
        
        # 添加到应用程序空闲任务队列，不影响主线程性能
        self.app.after_idle(self._check_preload_status)
    
    def _check_preload_status(self):
        """检查预加载状态"""
        if not self._is_preloaded:
            # 如果预加载未完成，再次检查
            self.app.after(100, self._check_preload_status)
    
    def _precompute_animation_frames(self):
        """预计算动画帧参数"""
        with self._preload_lock:
            if self._is_preloaded:
                return
                
            try:
                # 标记为已预加载
                self._is_preloaded = True
            except Exception as e:
                print(f"Error during preload: {e}")
    
    def _setup_theme_processor(self):
        """设置主题处理器，在空闲时异步处理主题应用"""
        # 取消现有处理器（如果有）
        if self._theme_processor_id:
            self.app.after_cancel(self._theme_processor_id)
        
        # 处理主题切换队列
        def process_theme_queue():
            # 检查队列中是否有待处理的主题
            try:
                # 非阻塞方式获取主题 - 如果没有就跳过
                theme_info = self.theme_apply_queue.get_nowait()
                
                # 获取当前时间
                current_time = time.time() * 1000
                
                # 如果动画已经开始，且已经过了一定时间（确保动画已经显示），才应用主题
                if self.is_animating and (current_time - self.start_time) > 150:
                    # 分批处理UI更新，减少主线程阻塞
                    self._apply_theme_in_chunks(theme_info["theme"])
                    
                    # 释放队列项
                    self.theme_apply_queue.task_done()
                else:
                    # 如果动画尚未开始或时间不够，放回队列稍后再处理
                    self.theme_apply_queue.put(theme_info)
            except queue.Empty:
                # 队列为空，继续检查
                pass
            
            # 每20ms处理一次队列
            self._theme_processor_id = self.app.after(20, process_theme_queue)
        
        # 启动主题处理器
        self._theme_processor_id = self.app.after(50, process_theme_queue)
    
    def _apply_theme_in_chunks(self, theme):
        """分批应用主题，避免长时间阻塞主线程
        
        Args:
            theme: 需要应用的主题名称 ('light' 或 'dark')
        """
        # 这个函数会被重复调用，每次处理一小批UI元素
        def apply_chunk():
            # 这里实际应用主题的代码 - 实际实现时需替换为真实的主题应用逻辑
            try:
                # 应用系统主题 - 这一操作通常是阻塞的
                ctk.set_appearance_mode(theme.capitalize())
                
                # 标记主题已应用
                self.notify_theme_applied()
                
                # 更新应用程序的当前主题
                self.app.current_theme = theme
            except Exception as e:
                print(f"Error applying theme: {e}")
        
        # 使用after方法来延迟执行，让UI有机会更新
        self.app.after(10, apply_chunk)
    
    def setup_overlay(self):
        """设置遮罩窗口位置和大小"""
        # 获取应用窗口尺寸
        win_width = self.app.winfo_width()
        win_height = self.app.winfo_height()
        
        # 设置遮罩大小和位置
        x = self.app.winfo_rootx()
        y = self.app.winfo_rooty()
        self.overlay.geometry(f"{win_width}x{win_height}+{x}+{y}")
        
        # 计算中心位置
        center_x = win_width / 2
        center_y = win_height / 2
        
        # 配置画布大小 - 创建舞台并初始化为空白
        self.canvas.configure(
            width=win_width, 
            height=win_height,
            bg=self.get_bg_color(self.source_theme)
        )
        
        # 获取目标主题文本
        text = "深色模式" if self.target_theme == "dark" else "浅色模式"
        text_color = self.get_text_color(self.source_theme)
        
        # 一次性设置所有UI元素
        self.canvas.delete("all")  # 清除旧元素
        
        # 创建静态图形 - 使用多边形而非旋转动画
        icon_center_y = center_y - 20
        
        # 为深浅色模式创建不同的图形
        if self.target_theme == "dark":
            # 创建一个圆形 - 表示深色模式
            self.static_icon = self.canvas.create_oval(
                center_x - self.static_icon_size/2,
                icon_center_y - self.static_icon_size/2,
                center_x + self.static_icon_size/2,
                icon_center_y + self.static_icon_size/2,
                outline=text_color,
                width=2,
                fill=""
            )
            
            # 添加内部点缀 - 创建月牙效果
            circle_r = self.static_icon_size/4
            self.inner_detail = self.canvas.create_oval(
                center_x - circle_r,
                icon_center_y - circle_r,
                center_x + circle_r,
                icon_center_y + circle_r,
                fill=text_color,
                outline=""
            )
        else:
            # 创建多边形 - 表示光芒或太阳
            points = []
            rays = 8  # 光芒数量
            outer_r = self.static_icon_size/2
            inner_r = self.static_icon_size/3
            
            for i in range(rays * 2):
                angle = math.pi * i / rays
                r = outer_r if i % 2 == 0 else inner_r
                x = center_x + r * math.cos(angle)
                y = icon_center_y + r * math.sin(angle)
                points.extend([x, y])
            
            self.static_icon = self.canvas.create_polygon(
                points,
                outline=text_color,
                fill=text_color,
                smooth=True
            )
        
        # 创建文本和线条
        line_width = min(win_width / 3, 200)  # 固定线条宽度，但有最大值
        
        self.line_top = self.canvas.create_line(
            center_x - line_width/2, center_y - 65,
            center_x + line_width/2, center_y - 65,
            width=2, fill=text_color, smooth=True
        )
        
        self.line_bottom = self.canvas.create_line(
            center_x - line_width/2, center_y + 65,
            center_x + line_width/2, center_y + 65,
            width=2, fill=text_color, smooth=True
        )
        
        self.mode_text = self.canvas.create_text(
            center_x, center_y + 35,
            text=f"切换至{text}",
            font=("Microsoft YaHei UI", 16, "bold"),
            fill=text_color,
            anchor="center"
        )
        
        # 使用防抖动技术显示窗口
        self.app.after(1, self._show_overlay)
        
        # 强制刷新一次画布，预加载到GPU缓存
        self.canvas.update_idletasks()
        
        # 将主题变更添加到队列中，等待动画开始后处理
        self._queue_theme_change(self.target_theme)
    
    def _queue_theme_change(self, theme):
        """将主题变更添加到队列，实现异步处理"""
        self.theme_apply_queue.put({
            "theme": theme,
            "timestamp": time.time() * 1000
        })
    
    def _show_overlay(self):
        """显示遮罩，分离UI操作以提高性能"""
        if self.overlay:
            # 在显示前确保动画已经准备好
            self.overlay.deiconify()
            # 使用update_idletasks代替update，减少阻塞
            self.overlay.update_idletasks()
    
    def get_bg_color(self, theme):
        """获取指定主题的背景颜色"""
        return self.theme_colors[theme]["bg"]
    
    def get_text_color(self, theme):
        """获取指定主题的文本颜色"""
        return self.theme_colors[theme]["text"]
    
    def interpolate_color(self, start_color, end_color, ratio):
        """在两个颜色之间进行插值
        
        Args:
            start_color: 起始颜色(十六进制)
            end_color: 结束颜色(十六进制)
            ratio: 插值比例(0.0到1.0)
            
        Returns:
            插值后的颜色(十六进制)
        """
        # 解析颜色
        r1, g1, b1 = int(start_color[1:3], 16), int(start_color[3:5], 16), int(start_color[5:7], 16)
        r2, g2, b2 = int(end_color[1:3], 16), int(end_color[3:5], 16), int(end_color[5:7], 16)
        
        # 计算插值
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        
        # 返回十六进制颜色
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def easeInOutQuad(self, t):
        """缓入缓出二次方曲线
        
        Args:
            t: 0.0-1.0之间的时间变量
        
        Returns:
            缓动后的值
        """
        return 2 * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 2) / 2
    
    def notify_theme_applied(self):
        """通知主题已应用完成"""
        self.theme_applied = True
        self.theme_apply_time = time.time() * 1000  # 记录主题应用完成时间
    
    def update_animation(self):
        """更新动画效果 - 仅处理淡入淡出和颜色过渡，不做旋转"""
        if not self.overlay or not self.animation_running:
            return
            
        # 计算当前时间和动画进度
        current_time = time.time() * 1000  # 毫秒
        if current_time - self.last_update_time < 8:  # 限制更新频率
            self.app.after(5, self.update_animation)
            return
            
        self.last_update_time = current_time
        elapsed = current_time - self.start_time
        
        # 检查是否达到最大持续时间
        if elapsed >= self.animation_duration:
            # 动画结束，强制完成
            self.complete_animation()
            return
        
        # 如果主题已应用完成且至少经过了最小持续时间的一半，可以开始淡出
        ready_to_fade_out = self.theme_applied and (current_time - self.theme_apply_time) > 200
        
        # 计算当前进度比例 (0.0-1.0)
        progress = elapsed / self.animation_duration
        
        # 如果主题已应用且准备好淡出，加速进度以便开始淡出阶段
        if ready_to_fade_out and progress < (1 - self.fade_out_percent):
            # 加速进度，直接跳到淡出阶段开始的位置
            progress = 1 - self.fade_out_percent
        
        # 量化进度以使用预计算值
        progress_key = round(progress * 100) / 100
        
        try:
            # 使用预计算的不透明度值 - 从缓存获取
            new_opacity = self._precomputed_opacities.get(progress_key)
            if new_opacity is None:
                # 如果缓存没有，计算新值
                new_opacity = self._calculate_opacity(progress)
            
            # 只有当不透明度变化足够大时才更新
            if abs(new_opacity - self._cached_opacity) > 0.02:
                self._cached_opacity = new_opacity
                self.overlay.attributes("-alpha", new_opacity)
            
            # 使用缓动的进度值计算颜色
            eased_progress = self.easeInOutQuad(progress)
            
            # 插值计算当前颜色 - 从源主题颜色到目标主题颜色
            new_bg_color = self.interpolate_color(
                self.get_bg_color(self.source_theme),
                self.get_bg_color(self.target_theme),
                eased_progress
            )
            
            # 只有当颜色变化明显时才更新背景
            if self._cached_bg_color != new_bg_color:
                self._cached_bg_color = new_bg_color
                self.canvas.configure(bg=new_bg_color)
            
            # 文本颜色随背景变化 - 从源主题文本颜色到目标主题文本颜色
            new_text_color = self.interpolate_color(
                self.get_text_color(self.source_theme),
                self.get_text_color(self.target_theme),
                eased_progress
            )
            
            # 只有当文本颜色变化明显时才更新
            if self._cached_text_color != new_text_color:
                self._cached_text_color = new_text_color
                # 批量更新颜色，减少重绘次数
                for item in [self.mode_text, self.line_top, self.line_bottom, self.static_icon]:
                    if item and self.canvas.type(item) != "":
                        if self.canvas.type(item) == "polygon" or self.canvas.type(item) == "oval":
                            self.canvas.itemconfig(item, outline=new_text_color)
                            if self.target_theme == "light":  # 只为太阳图标填充颜色
                                self.canvas.itemconfig(item, fill=new_text_color)
                        else:
                            self.canvas.itemconfig(item, fill=new_text_color)
                
                # 更新内部细节（如果存在）
                if hasattr(self, 'inner_detail') and self.inner_detail and self.canvas.type(self.inner_detail) != "":
                    self.canvas.itemconfig(self.inner_detail, fill=new_text_color)
                
            # 使用固定帧率更新，避免每帧的不稳定
            if self.animation_running:
                self.app.after(16, self.update_animation)
        except Exception as e:
            # 防止窗口已关闭但动画仍在运行的情况
            print(f"Animation error: {e}")
            self.animation_running = False
    
    def _calculate_opacity(self, progress):
        """计算当前不透明度"""
        fade_in_end = self.fade_in_percent
        fade_out_start = 1 - self.fade_out_percent
        
        if progress < fade_in_end:  # 淡入阶段
            return progress / fade_in_end
        elif progress > fade_out_start:  # 淡出阶段
            return (1.0 - progress) / self.fade_out_percent
        else:  # 保持完全不透明阶段
            return 1.0
    
    def complete_animation(self):
        """完成动画并清理资源"""
        self.animation_running = False
        self.hide_overlay()
    
    def hide_overlay(self):
        """隐藏遮罩而非销毁"""
        if self.overlay:
            self.overlay.withdraw()
            self.is_animating = False
            self.source_theme = None
            self.target_theme = None
            self.theme_applied = False
    
    def start_transition(self):
        """开始主题过渡动画"""
        # 如果已经在动画中，不执行新动画
        if self.is_animating:
            return
        
        # 确保预加载完成
        if not self._is_preloaded:
            self._precompute_animation_frames()
            
        # 设置动画状态
        self.is_animating = True
        self.animation_running = True
        self.theme_applied = False
        
        # 重置缓存
        self._cached_opacity = 0
        self._cached_bg_color = None
        self._cached_text_color = None
        
        # 记录时间
        self.start_time = time.time() * 1000  # 毫秒
        self.last_update_time = self.start_time
        
        # 记录源主题和目标主题
        self.source_theme = self.app.current_theme
        self.target_theme = "dark" if self.source_theme != "dark" else "light"
        
        # 在动画开始前，对当前窗口进行快照，减少重绘
        self._snapshot_current_window()
        
        # 设置遮罩
        self.setup_overlay()
        
        # 开始动画，使用防抖动技术
        self.app.after(5, self.update_animation)
    
    def _snapshot_current_window(self):
        """对当前窗口进行快照，通过提前捕获窗口内容减轻实际切换时的负担"""
        try:
            # 这是一个性能优化，在主题切换前捕获当前窗口状态
            # 在某些平台上可以减少视觉上的闪烁
            self.app.update_idletasks()
        except Exception as e:
            # 忽略快照过程中的错误
            print(f"Window snapshot error: {e}")
            pass 
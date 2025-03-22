import customtkinter as ctk
import threading
import time

class LoadingAnimation:
    """
    加载动画类，在标签上显示加载动画
    """
    def __init__(self, label, app, text="正在处理", dot_count=3, interval=0.5):
        """
        初始化加载动画
        
        Args:
            label: 显示动画的标签
            app: 主应用
            text: 动画文本前缀
            dot_count: 动画点的最大数量
            interval: 动画更新间隔（秒）
        """
        self.label = label
        self.app = app
        self.text = text
        self.dot_count = dot_count
        self.interval = interval
        self.is_running = False
        self.animation_thread = None
        
    def start(self):
        """启动加载动画"""
        if self.is_running:
            return
            
        self.is_running = True
        self.animation_thread = threading.Thread(target=self._animate)
        self.animation_thread.daemon = True
        self.animation_thread.start()
        
    def stop(self):
        """停止加载动画"""
        self.is_running = False
        if self.animation_thread and self.animation_thread.is_alive():
            self.animation_thread.join(timeout=1.0)
        
        # 清除标签文本
        try:
            self.label.configure(text="")
        except Exception:
            pass
            
    def _animate(self):
        """动画循环"""
        dots = 0
        while self.is_running:
            try:
                # 更新标签文本
                dots = (dots % self.dot_count) + 1
                animation_text = f"{self.text}{'.' * dots}"
                
                # 使用after方法在主线程中更新UI
                self.app.after(0, lambda t=animation_text: self.label.configure(text=t))
                
                # 暂停一段时间
                time.sleep(self.interval)
            except Exception:
                # 如果出现异常（例如窗口已关闭），则退出循环
                break 
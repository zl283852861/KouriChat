import customtkinter as ctk
from tkinter import messagebox

class MessageDialog:
    """消息对话框类"""
    
    @staticmethod
    def show_info(title, message):
        """显示信息对话框"""
        messagebox.showinfo(title, message)
    
    @staticmethod
    def show_warning(title, message):
        """显示警告对话框"""
        messagebox.showwarning(title, message)
    
    @staticmethod
    def show_error(title, message):
        """显示错误对话框"""
        messagebox.showerror(title, message)
    
    @staticmethod
    def show_question(title, message):
        """显示问题对话框"""
        return messagebox.askquestion(title, message) == "yes"
    
    @staticmethod
    def show_ok_cancel(title, message):
        """显示确定/取消对话框"""
        return messagebox.askokcancel(title, message)
    
    @staticmethod
    def show_yes_no(title, message):
        """显示是/否对话框"""
        return messagebox.askyesno(title, message)
    
    @staticmethod
    def show_retry_cancel(title, message):
        """显示重试/取消对话框"""
        return messagebox.askretrycancel(title, message) 
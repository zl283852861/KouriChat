import json
import os
from tkinter import messagebox

class APIConfig:
    """API配置管理类，负责读取和保存应用配置"""
    
    CONFIG_FILE = "api_config.json"
    
    @staticmethod
    def read_config():
        """读取配置文件，如果不存在或格式错误则返回默认配置"""
        try:
            if os.path.exists(APIConfig.CONFIG_FILE):
                with open(APIConfig.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return APIConfig.get_default_config()
        except json.JSONDecodeError:
            messagebox.showerror("配置文件错误", "配置格式错误，将使用默认配置。")
            return APIConfig.get_default_config()
    
    @staticmethod
    def save_config(config):
        """保存配置到文件"""
        with open(APIConfig.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
    
    @staticmethod
    def get_default_config():
        """获取默认配置"""
        return {
            "real_server_base_url": "https://api.siliconflow.cn/", 
            "api_key": "", 
            "model": "deepseek-ai/DeepSeek-V3", 
            "messages": [], 
            "image_config": {"generate_size": "512x512"}, 
            "theme": "system"
        } 
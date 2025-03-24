"""API测试模块，提供统一的API测试接口"""

import logging
from api.character_api import CharacterAPI
from api.recognition_api import RecognitionAPI
from api.generation_api import GenerationAPI
import requests

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class APITester:
    """API测试类，整合各类API的测试功能"""
    
    def __init__(self, url, api_key, model, image_config=None):
        """
        初始化API测试器
        
        Args:
            url: API基础URL
            api_key: API密钥
            model: 使用的模型名称
            image_config: 图像生成配置
        """
        self.url = url
        self.api_key = api_key
        self.model = model
        self.image_config = image_config or {"generate_size": "512x512"}
        
        # 初始化各个API处理类
        self.character_api = CharacterAPI(url, api_key, model)
        self.recognition_api = RecognitionAPI(url, api_key, model)
        self.generation_api = GenerationAPI(url, api_key, model)

    def test_standard_api(self):
        """测试标准API连接"""
        return self.character_api.test_connection()
    
    def recognize_image(self, image_path_or_base64):
        """识别图片内容"""
        return self.recognition_api.recognize_image(image_path_or_base64)
    
    def generate_image(self, prompt, size=None):
        """生成图片"""
        size = size or self.image_config.get("generate_size", "512x512")
        return self.generation_api.generate_image(prompt, size)

    def generate_character_profile(self, character_desc):
        """生成角色人设"""
        return self.character_api.generate_profile(character_desc)

    def polish_character_profile(self, profile, polish_desc):
        """润色角色人设"""
        return self.character_api.polish_profile(profile, polish_desc)

    def test_character_api(self):
        """测试人设API连接"""
        try:
            response = self.character_api.test_connection()
            response.raise_for_status()
            return "人设API连接测试成功！"
        except Exception as e:
            logging.error(f"人设API测试失败: {str(e)}")
            raise
        
    def test_recognition_api(self):
        """测试识别API连接"""
        try:
            response = self.recognition_api.test_connection()
            response.raise_for_status()
            return "图片识别API连接测试成功！"
        except Exception as e:
            logging.error(f"识别API测试失败: {str(e)}")
            raise
        
    def test_generation_api(self):
        """测试生成API连接"""
        try:
            # 简单的测试请求
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": self.model,
                "prompt": "测试图像生成API连接"
            }
            
            response = requests.post(
                f"{self.url.rstrip('/')}/v1/images/generations",
                headers=headers,
                json=data,
                timeout=10
            )
            
            response.raise_for_status()
            return "图片生成API连接测试成功！"
        except Exception as e:
            logging.error(f"生成API测试失败: {str(e)}")
            raise 
import requests
import base64
import os
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class RecognitionAPI:
    """图片识别API处理类"""
    
    def __init__(self, base_url, api_key, model):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
    
    def test_connection(self):
        """测试API连接"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that can analyze images."},
                {"role": "user", "content": "Can you analyze images?"}
            ]
        }
        
        response = requests.post(
            f"{self.base_url.rstrip('/')}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=10
        )
        
        return response
    
    def recognize_image(self, image_path_or_base64):
        """识别图片内容"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 处理输入，可以是文件路径或已编码的base64字符串
        if isinstance(image_path_or_base64, str) and (
            os.path.exists(image_path_or_base64) or 
            not image_path_or_base64.startswith("data:")
        ):
            # 是文件路径
            with open(image_path_or_base64, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode('utf-8')
        else:
            # 已经是base64字符串
            base64_image = image_path_or_base64
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that can analyze images."},
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": "请描述这张图片的内容。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ]
        }
        
        response = requests.post(
            f"{self.base_url.rstrip('/')}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30  # 图片识别可能需要更长时间
        )
        
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"] 
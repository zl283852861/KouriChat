import requests
import base64
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class GenerationAPI:
    """图片生成API处理类"""
    
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
            "prompt": "A test image of a blue circle",
            "n": 1,
            "size": "256x256"
        }
        
        response = requests.post(
            f"{self.base_url.rstrip('/')}/v1/images/generations",
            headers=headers,
            json=data,
            timeout=10
        )
        
        return response
    
    def generate_image(self, prompt, size="1024x1024"):
        """生成图片"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": size
        }
        
        response = requests.post(
            f"{self.base_url.rstrip('/')}/v1/images/generations",
            headers=headers,
            json=data,
            timeout=30  # 图片生成可能需要更长时间
        )
        
        response.raise_for_status()
        result = response.json()
        
        # 返回图片URL或base64数据
        if "data" in result and len(result["data"]) > 0:
            if "url" in result["data"][0]:
                return result["data"][0]["url"]
            elif "b64_json" in result["data"][0]:
                return f"data:image/png;base64,{result['data'][0]['b64_json']}"
        
        raise ValueError("API返回的数据格式不正确") 
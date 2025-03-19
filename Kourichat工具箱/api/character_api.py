import requests
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class CharacterAPI:
    """角色人设API处理类"""
    
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
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, are you working?"}
            ]
        }
        
        response = requests.post(
            f"{self.base_url.rstrip('/')}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=10
        )
        
        return response
    
    def generate_profile(self, character_desc):
        """生成角色人设"""
        prompt = f"请根据以下描述生成一个详细的角色人设，要贴合实际，至少1000字，包含以下内容：\n1. 角色名称\n2. 性格特点\n3. 外表特征\n4. 时代背景\n5. 人物经历\n描述：{character_desc}\n请以清晰的格式返回。"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model, 
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = requests.post(
            f"{self.base_url.rstrip('/')}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    def polish_profile(self, profile, polish_desc):
        """润色角色人设"""
        prompt = f"请根据以下要求润色角色人设：\n润色要求：{polish_desc}\n人设内容：{profile}\n请返回润色后的完整人设。修改的内容至少500字"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model, 
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = requests.post(
            f"{self.base_url.rstrip('/')}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"] 
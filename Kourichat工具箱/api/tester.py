import logging
from api.character_api import CharacterAPI
from api.recognition_api import RecognitionAPI
from api.generation_api import GenerationAPI

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class APITester:
    """API测试类"""
    
    def __init__(self, base_url, api_key, model, image_config=None):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.image_config = image_config or {"generate_size": "512x512"}
        
        # 初始化各个API处理类
        self.character_api = CharacterAPI(base_url, api_key, model)
        self.recognition_api = RecognitionAPI(base_url, api_key, model)
        self.generation_api = GenerationAPI(base_url, api_key, model)

    def test_standard_api(self):
        """测试标准API连接"""
        return self.character_api.test_connection()
    
    def recognize_image(self, image_path_or_base64):
        """识别图片内容"""
        return self.recognition_api.recognize_image(image_path_or_base64)
    
    def generate_image(self, prompt, size=None):
        """生成图片"""
        if size is None:
            size = self.image_config.get("generate_size", "512x512")
        return self.generation_api.generate_image(prompt, size)

    def generate_character_profile(self, character_desc):
        """生成角色人设"""
        return self.character_api.generate_profile(character_desc)

    def polish_character_profile(self, profile, polish_desc):
        """润色角色人设"""
        return self.character_api.polish_profile(profile, polish_desc) 
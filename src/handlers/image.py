"""
图像处理模块
负责处理图像相关功能，包括:
- 图像生成请求识别
- 随机图片获取
- API图像生成
- 临时文件管理
"""

import os
import logging
import requests
from datetime import datetime
from typing import Optional
import re
import time

logger = logging.getLogger(__name__)

class ImageHandler:
    def __init__(self, root_dir, api_key, base_url, image_model):
        self.root_dir = root_dir
        self.api_key = api_key
        self.base_url = base_url
        self.image_model = image_model
        self.temp_dir = os.path.join(root_dir, "data", "images", "temp")
        
        # 复用消息模块的AI实例
        self.text_ai = DeepSeekAI(
            api_key=api_key,
            base_url=base_url,
            model="deepseek-chat",
            max_token=2048,
            temperature=0.5
        )
        
        # 多语言提示模板
        self.prompt_templates = {
            'basic': (
                "请将以下图片描述优化为英文提示词，包含：\n"
                "1. 主体细节（至少3个特征）\n"
                "2. 环境背景\n"
                "3. 艺术风格\n"
                "4. 质量参数\n"
                "示例格式：\"A..., ... , ... , digital art, trending on artstation\"\n"
                "原描述：{prompt}"
            ),
            'creative': (
                "你是一位专业插画师，请用英文为以下主题生成详细绘画提示词：\n"
                "- 核心元素：{prompt}\n"
                "- 需包含：构图指导/色彩方案/光影效果\n"
                "- 禁止包含：水印/文字/低质量描述\n"
                "直接返回结果"
            )
        }

        # 质量分级参数配置
        self.quality_profiles = {
            'fast': {'steps': 20, 'width': 768},
            'standard': {'steps': 28, 'width': 1024},
            'premium': {'steps': 40, 'width': 1280}
        }

        # 通用负面提示词库（50+常见词条）
        self.base_negative_prompts = [
            "low quality", "blurry", "ugly", "duplicate", "poorly drawn",
            "disfigured", "deformed", "extra limbs", "mutated hands",
            "poor anatomy", "cloned face", "malformed limbs",
            "missing arms", "missing legs", "extra fingers",
            "fused fingers", "long neck", "unnatural pose",
            "low resolution", "jpeg artifacts", "signature",
            "watermark", "username", "text", "error",
            "cropped", "worst quality", "normal quality",
            "out of frame", "bad proportions", "bad shadow",
            "unrealistic", "cartoonish", "3D render",
            "overexposed", "underexposed", "grainy",
            "low contrast", "bad perspective", "mutation",
            "childish", "beginner", "amateur"
        ]
        
        # 动态负面提示词生成模板
        self.negative_prompt_template = (
            "根据以下图片描述，生成5个英文负面提示词（用逗号分隔），避免出现：\n"
            "- 与描述内容冲突的元素\n"
            "- 重复通用负面词\n"
            "描述内容：{prompt}\n"
            "现有通用负面词：{existing_negatives}"
        )
        # 提示词扩展触发条件
        self.prompt_extend_threshold = 30  # 字符数阈值
        os.makedirs(self.temp_dir, exist_ok=True)

    def is_random_image_request(self, message: str) -> bool:
        """检查消息是否为请求图片的模式"""
        # 基础词组
        basic_patterns = [
            r'来个图',
            r'来张图',
            r'来点图',
            r'想看图',
        ]
        
        # 将消息转换为小写以进行不区分大小写的匹配
        message = message.lower()
        
        # 1. 检查基础模式
        if any(pattern in message for pattern in basic_patterns):
            return True
            
        # 2. 检查更复杂的模式
        complex_patterns = [
            r'来[张个幅]图',
            r'发[张个幅]图',
            r'看[张个幅]图',
        ]
        
        if any(re.search(pattern, message) for pattern in complex_patterns):
            return True
            
        return False

    def get_random_image(self) -> Optional[str]:
        """从API获取随机图片并保存"""
        try:
            if not os.path.exists(self.temp_dir):
                os.makedirs(self.temp_dir)
                
            # 获取图片链接
            response = requests.get('https://t.mwm.moe/pc')
            if response.status_code == 200:
                # 生成唯一文件名
                timestamp = int(time.time())
                image_path = os.path.join(self.temp_dir, f'image_{timestamp}.jpg')
                
                # 保存图片
                with open(image_path, 'wb') as f:
                    f.write(response.content)
                
                return image_path
        except Exception as e:
            logger.error(f"获取图片失败: {str(e)}")
        return None

    def is_image_generation_request(self, text: str) -> bool:
        """判断是否为图像生成请求"""
        # 基础动词
        draw_verbs = ["画", "绘", "生成", "创建", "做"]
        
        # 图像相关词
        image_nouns = ["图", "图片", "画", "照片", "插画", "像"]
        
        # 数量词
        quantity = ["一下", "一个", "一张", "个", "张", "幅"]
        
        # 组合模式
        patterns = [
            r"画.*[猫狗人物花草山水]",
            r"画.*[一个张只条串份副幅]",
            r"帮.*画.*",
            r"给.*画.*",
            r"生成.*图",
            r"创建.*图",
            r"能.*画.*吗",
            r"可以.*画.*吗",
            r"要.*[张个幅].*图",
            r"想要.*图",
            r"做[一个张]*.*图",
            r"画画",
            r"画一画",
        ]
        
        # 1. 检查正则表达式模式
        if any(re.search(pattern, text) for pattern in patterns):
            return True
            
        # 2. 检查动词+名词组合
        for verb in draw_verbs:
            for noun in image_nouns:
                if f"{verb}{noun}" in text:
                    return True
                # 检查带数量词的组合
                for q in quantity:
                    if f"{verb}{q}{noun}" in text:
                        return True
                    if f"{verb}{noun}{q}" in text:
                        return True
        
        # 3. 检查特定短语
        special_phrases = [
            "帮我画", "给我画", "帮画", "给画",
            "能画吗", "可以画吗", "会画吗",
            "想要图", "要图", "需要图",
        ]
        
        if any(phrase in text for phrase in special_phrases):
            return True
        
        return False

    def generate_image(self, prompt: str) -> Optional[str]:
        """调用API生成图片，保存到临时目录并返回路径"""
        try:
            logger.info(f"开始生成图片，提示词: {prompt}")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.image_model,
                "prompt": prompt,
            }
            
            response = requests.post(
                f"{self.base_url}/images/generations",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            if "data" in result and len(result["data"]) > 0:
                img_url = result["data"][0]["url"]
                img_response = requests.get(img_url)
                if img_response.status_code == 200:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    temp_path = os.path.join(self.temp_dir, f"image_{timestamp}.jpg")
                    with open(temp_path, "wb") as f:
                        f.write(img_response.content)
                    logger.info(f"图片已保存到: {temp_path}")
                    return temp_path
            logger.error("API返回的数据中没有图片URL")
            return None
            
        except Exception as e:
            logger.error(f"图像生成失败: {str(e)}")
            return None

    def cleanup_temp_dir(self):
        """清理临时目录中的旧图片"""
        try:
            if os.path.exists(self.temp_dir):
                for file in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            logger.info(f"清理旧临时文件: {file_path}")
                    except Exception as e:
                        logger.error(f"清理文件失败 {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"清理临时目录失败: {str(e)}") 
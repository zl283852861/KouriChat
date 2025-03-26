"""
图像处理模块
负责处理图像相关功能，包括:
- 图像生成请求识别
- 随机图片获取
- API图像生成
- 图像识别
- 临时文件管理
"""

import os
import logging
import requests
import asyncio
import random
from datetime import datetime
from typing import Optional, List, Tuple, Callable, Dict, Any
import re
import time
import enum
import threading
import queue
# 移除直接导入，通过延迟导入方式在需要时导入
# from src.services.ai.llm_service import LLMService

# 添加缺失的ImageType枚举
class ImageType(enum.Enum):
    RANDOM = "random"
    GENERATED = "generated"
    USER_UPLOADED = "user_uploaded"
    ERROR = "error"

# 修改logger获取方式，确保与main模块一致
logger = logging.getLogger('main')

class ImageHandler:
    def __init__(self, root_dir, api_key=None, base_url=None, image_model=None, config=None):
        self.root_dir = root_dir
        self.api_key = api_key
        self.base_url = base_url
        self.image_model = image_model
        self.config = config or {}
        
        # 图像处理基础路径
        self.image_dir = os.path.join(root_dir, "data", "images")
        self.temp_dir = os.path.join(self.image_dir, "temp")
        
        # 随机图片目录
        self.random_image_dir = os.path.join(self.image_dir, "random")
        
        # 生成图片保存目录
        self.generated_image_dir = os.path.join(self.image_dir, "generated")
        
        # 创建目录结构
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.random_image_dir, exist_ok=True)
        os.makedirs(self.generated_image_dir, exist_ok=True)
        
        # 使用任务队列替代处理锁
        self.task_queue = queue.Queue()
        self.is_replying = False
        self.worker_thread = threading.Thread(target=self._process_image_queue, daemon=True)
        self.worker_thread.start()
        
        # 尝试延迟导入LLMService以避免循环导入
        try:
            from src.services.ai.llm_service import LLMService
            self.text_ai = LLMService(
                api_key=api_key,
                base_url=base_url,
                model="deepseek-ai/DeepSeek-V3",  # 修改为默认免费模型
                max_token=2048,
                temperature=0.5,
                max_groups=15
            )
        except (ImportError, Exception) as e:
            logger.warning(f"无法初始化LLMService: {str(e)}")
            self.text_ai = None
        
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
        
        # 图像识别关键字
        self.recognition_keywords = self.config.get('recognition_keywords', ['这是什么', '帮我看看这是什么', '识别这个图片'])
        
        # 随机图片关键字
        self.random_image_keywords = self.config.get('random_image_keywords', ['来张图片', '随机图片', '给我看看', '来个图', '来张图'])
        
        # 图像生成关键字
        self.image_generation_keywords = self.config.get('image_generation_keywords', ['画', '生成图片', '绘制'])
        
        # 图像识别器
        self.image_recognizer = None
        
        logger.info("图像处理器初始化完成")

    async def initialize(self):
        """初始化图像处理器，加载识别模型和生成模型"""
        try:
            # 这里可以加载图像识别和生成模型
            logger.info("初始化图像处理器...")
            
            # TODO: 实现实际的模型加载逻辑
            
            logger.info("图像处理器初始化完成")
            return True
        except Exception as e:
            logger.error(f"初始化图像处理器失败: {str(e)}")
            return False

    def _process_image_queue(self):
        """后台线程处理图片生成/获取队列"""
        while True:
            try:
                # 等待队列中的任务
                task = self.task_queue.get()
                if task is None:
                    continue
                    
                # 如果正在回复，等待回复结束
                while self.is_replying:
                    time.sleep(0.5)
                    
                # 解析任务
                task_type, params, callback = task
                
                result = None
                # 根据任务类型执行不同操作
                if task_type == "random":
                    result = self._get_random_image_impl()
                elif task_type == "generate":
                    prompt = params.get("prompt", "")
                    result = self._generate_image_impl(prompt)
                elif task_type == "recognize":
                    image_path = params.get("image_path", "")
                    result = self._recognize_image_impl(image_path)
                
                # 执行回调
                if callback and result:
                    callback(result)
                    
            except Exception as e:
                logger.error(f"处理图片任务队列时出错: {str(e)}")
            finally:
                # 标记任务完成
                try:
                    self.task_queue.task_done()
                except:
                    pass
                time.sleep(0.1)

    def set_replying_status(self, is_replying: bool):
        """设置当前是否在进行回复"""
        self.is_replying = is_replying
        logger.debug(f"图片处理回复状态已更新: {'正在回复' if is_replying else '回复结束'}")
        
    def _get_random_image_impl(self) -> Optional[str]:
        """实际执行随机图片获取的内部方法"""
        try:
            # 首先尝试从随机图片目录获取
            image_files = [f for f in os.listdir(self.random_image_dir) 
                          if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
            
            if image_files:
                # 随机选择一张图片
                selected_image = random.choice(image_files)
                image_path = os.path.join(self.random_image_dir, selected_image)
                logger.info(f"从本地目录选择随机图片: {image_path}")
                return image_path
            
            # 如果本地目录为空，从API获取
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

    def get_random_image(self, callback: Callable = None) -> Optional[str]:
        """将随机图片获取任务添加到队列"""
        try:
            # 添加到任务队列
            self.task_queue.put(("random", {}, callback))
            logger.info("已添加随机图片获取任务到队列")
            return "图片获取请求已添加到队列，将在消息回复后处理"
        except Exception as e:
            logger.error(f"添加随机图片获取任务失败: {str(e)}")
            return None

    def is_random_image_request(self, message: str) -> bool:
        """检查消息是否为请求图片的模式"""
        # 检查是否包含随机图片关键字
        for keyword in self.random_image_keywords:
            if keyword in message:
                return True
                
        # 基础词组
        basic_patterns = [
            r'来个图',
            r'来张图',
            r'来点图',
            r'想看图',
            r'随机图片',
            r'随机壁纸',
            r'壁纸',
            r'图片',
            r'美图'
        ]
        
        # 使用正则表达式检查
        for pattern in basic_patterns:
            if re.search(pattern, message):
                return True
        
        return False

    def is_image_generation_request(self, text: str) -> bool:
        """检查是否为图像生成请求"""
        # 直接包含图像生成关键字
        for keyword in self.image_generation_keywords:
            if keyword in text:
                return True
        
        # 图像生成常见表达式
        generation_patterns = [
            r'画[一个|].*图',
            r'生成[一张|].*图',
            r'[帮我|请]?画[一下|]',
            r'[帮我|请]?生成[一下|]',
            r'来[一张|].*的?图片',
            r'绘制[一下|]?',
            r'画[一下|]',
            r'(做|搞|整|P)[一张|]图',
            r'AI\s?(绘画|画图|生成)',
            r'图片生成',
            r'(做|画|生成)[一个|]图像'
        ]
        
        # 一些特殊触发词
        special_triggers = [
            "想看", "能画", "能否画", "可以画", "图像", "风格", "照片",
            "写实", "卡通", "动漫", "插画", "海报"
        ]
        
        # 检查生成模式
        for pattern in generation_patterns:
            if re.search(pattern, text):
                return True
                
        # 检查特殊触发词，要求文本至少20个字符，避免误触发
        if len(text) > 20:
            for trigger in special_triggers:
                if trigger in text:
                    # 进一步验证上下文
                    context_validation = any(kw in text for kw in ["图", "绘", "画", "生成", "风格"])
                    if context_validation:
                        return True
        
        return False
        
    def is_image_recognition_request(self, content: str) -> bool:
        """
        检查是否是图像识别请求
        
        Args:
            content: 消息内容
            
        Returns:
            bool: 是否是图像识别请求
        """
        if not content:
            return False
            
        # 检查是否包含图像识别关键字
        for keyword in self.recognition_keywords:
            if keyword in content:
                return True
                
        return False

    def _expand_prompt(self, prompt: str) -> str:
        """扩展简短的提示词"""
        if not prompt or len(prompt) >= self.prompt_extend_threshold:
            return prompt
        
        try:
            # 调用API进行提示词扩展
            template = self.prompt_templates.get('creative')
            expanded_prompt = prompt  # 默认为原始提示词
            
            # TODO: 实现提示词扩展逻辑
            
            return expanded_prompt
        except Exception as e:
            logger.error(f"扩展提示词失败: {str(e)}")
            return prompt

    def _translate_prompt(self, prompt: str) -> str:
        """将中文提示词翻译为英文"""
        try:
            # 检测语言
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in prompt)
            if not has_chinese:
                return prompt
                
            template = self.prompt_templates.get('basic')
            
            # TODO: 实现翻译逻辑
            
            return prompt  # 默认返回原提示词
        except Exception as e:
            logger.error(f"翻译提示词失败: {str(e)}")
            return prompt

    def _generate_dynamic_negatives(self, prompt: str) -> List[str]:
        """根据提示词生成动态负面提示词"""
        try:
            # 基于提示词内容生成相关负面提示词
            template = self.negative_prompt_template.format(
                prompt=prompt,
                existing_negatives=", ".join(self.base_negative_prompts[:10])
            )
            
            # TODO: 实现动态负面提示词生成逻辑
            
            # 假设结果
            custom_negatives = []
            
            return custom_negatives
        except Exception as e:
            logger.error(f"生成动态负面提示词失败: {str(e)}")
            return []

    def _build_final_negatives(self, prompt: str) -> str:
        """构建最终的负面提示词"""
        # 获取动态负面提示词
        custom_negatives = self._generate_dynamic_negatives(prompt)
        
        # 合并基础负面提示词和动态负面提示词
        all_negatives = self.base_negative_prompts + custom_negatives
        
        # 去重并连接
        unique_negatives = list(set(all_negatives))
        return ", ".join(unique_negatives)

    def _optimize_prompt(self, prompt: str) -> Tuple[str, str]:
        """优化提示词，返回(正向提示词, 负向提示词)"""
        try:
            # 1. 扩展简短提示词
            if len(prompt) < self.prompt_extend_threshold:
                prompt = self._expand_prompt(prompt)
                
            # 2. 翻译中文提示词
            prompt = self._translate_prompt(prompt)
            
            # 3. 构建负面提示词
            negative_prompt = self._build_final_negatives(prompt)
            
            return prompt, negative_prompt
            
        except Exception as e:
            logger.error(f"优化提示词失败: {str(e)}")
            return prompt, ", ".join(self.base_negative_prompts[:15])  # 返回默认值

    def _select_quality_profile(self, prompt: str) -> dict:
        """根据提示词选择合适的质量配置"""
        # 这里可以实现基于提示词复杂度的质量选择逻辑
        # 当前版本：简单地返回标准配置
        return self.quality_profiles.get('standard')

    def _generate_image_impl(self, prompt: str) -> Optional[str]:
        """实际执行图像生成的内部方法"""
        if not prompt:
            logger.warning("生成图像失败：提示词为空")
            return None
            
        try:
            # 优化提示词
            optimized_prompt, negative_prompt = self._optimize_prompt(prompt)
            
            # 选择质量配置
            quality_profile = self._select_quality_profile(prompt)
            
            # 生成图片保存路径
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            image_path = os.path.join(self.generated_image_dir, f"generated_{timestamp}.png")
            
            # TODO: 实现实际的API调用逻辑
            
            # 模拟生成图片
            mock_success = False  # 设置为True进行测试
            
            if mock_success:
                logger.info(f"成功生成图片: {image_path}")
                return image_path
            else:
                logger.warning(f"图片生成失败: {prompt[:50]}...")
                return None
                
        except Exception as e:
            logger.error(f"生成图片失败: {str(e)}")
            return None

    def generate_image(self, prompt: str, callback: Callable = None) -> Optional[str]:
        """将图片生成任务添加到队列"""
        try:
            # 添加到任务队列
            self.task_queue.put(("generate", {"prompt": prompt}, callback))
            logger.info(f"已添加图片生成任务到队列: {prompt[:30]}...")
            return "图片生成请求已添加到队列，将在消息回复后处理"
        except Exception as e:
            logger.error(f"添加图片生成任务失败: {str(e)}")
            return None
            
    def _recognize_image_impl(self, image_path: str) -> str:
        """
        实际执行图像识别的内部方法
        
        Args:
            image_path: 图像路径
            
        Returns:
            str: 识别结果
        """
        if not os.path.exists(image_path):
            logger.error(f"图像文件不存在: {image_path}")
            return "图像文件不存在"
        
        try:
            # 调用图像识别器分析图像
            result = "这是一张图片" # 替换为实际的识别结果
            
            # TODO: 实现实际的图像识别逻辑
            
            logger.info(f"图像识别完成: {image_path}")
            return result
            
        except Exception as e:
            logger.error(f"识别图像失败: {str(e)}")
            return f"抱歉，图像识别失败: {str(e)}"
    
    def process_image(self, image_path: str, callback: Callable = None):
        """
        处理图像，包括识别和分析
        
        Args:
            image_path: 图像路径
            callback: 处理完成后的回调函数
            
        Returns:
            bool: 是否成功开始处理
        """
        try:
            # 添加到任务队列
            self.task_queue.put(("recognize", {"image_path": image_path}, callback))
            logger.info(f"已添加图像识别任务到队列: {image_path}")
            return True
        except Exception as e:
            logger.error(f"添加图像识别任务失败: {str(e)}")
            if callback:
                callback(f"图像处理失败: {str(e)}")
            return False

    def cleanup_temp_dir(self):
        """清理临时文件目录"""
        try:
            if os.path.exists(self.temp_dir):
                # 获取当前时间戳
                current_time = time.time()
                
                # 获取目录中的所有文件
                for file_name in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file_name)
                    
                    # 如果是文件（不是目录）
                    if os.path.isfile(file_path):
                        # 获取文件的修改时间
                        file_mod_time = os.path.getmtime(file_path)
                        
                        # 如果文件超过24小时未修改，则删除
                        if current_time - file_mod_time > 24 * 60 * 60:
                            os.remove(file_path)
                            logger.info(f"已清理临时图片文件: {file_path}")
                
                logger.info("临时图片目录清理完成")
        except Exception as e:
            logger.error(f"清理临时图片目录失败: {str(e)}")

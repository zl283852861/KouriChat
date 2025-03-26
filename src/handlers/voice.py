"""
语音处理模块
负责处理语音相关功能，包括:
- 语音请求识别
- TTS语音生成
- STT语音识别
- 语音文件管理
- 清理临时文件
"""

import os
import logging
import requests
import asyncio
import re
import time
from datetime import datetime
from typing import Optional, Dict, Any

# 修改logger获取方式，确保与main模块一致
logger = logging.getLogger('main')

class VoiceHandler:
    def __init__(self, root_dir, tts_api_url=None, config=None):
        self.root_dir = root_dir
        self.tts_api_url = tts_api_url
        self.config = config or {}
        self.voice_dir = os.path.join(root_dir, "data", "voices")
        
        # 确保语音目录存在
        os.makedirs(self.voice_dir, exist_ok=True)
        
        # 语音生成关键字
        self.voice_generation_keywords = self.config.get('voice_generation_keywords', ['生成语音', '转为语音', '语音回复'])
        
        # 语音转文字关键字
        self.voice_recognition_keywords = self.config.get('voice_recognition_keywords', ['语音识别', '转为文字'])
        
        # 语音设置
        self.default_voice = self.config.get('default_voice', 'zh-CN-XiaoxiaoNeural')
        self.voice_rate = self.config.get('voice_rate', '+0%')
        self.voice_pitch = self.config.get('voice_pitch', '+0%')
        
        # TTS和STT引擎
        self.tts_engine = None
        self.stt_engine = None
        
        logger.info("语音处理器初始化完成")

    async def initialize(self):
        """初始化语音处理器，加载TTS和STT引擎"""
        try:
            # 这里可以加载语音合成和识别引擎
            logger.info("初始化语音处理器...")
            
            # TODO: 实现实际的TTS/STT引擎加载逻辑
            
            logger.info("语音处理器初始化完成")
            return True
        except Exception as e:
            logger.error(f"初始化语音处理器失败: {str(e)}")
            return False

    def is_voice_request(self, text: str) -> bool:
        """判断是否为语音请求"""
        voice_keywords = ["语音", "播放", "说话", "读出来"]
        return any(keyword in text for keyword in voice_keywords)

    def is_voice_generation_request(self, content: str) -> bool:
        """
        检查是否是语音生成请求
        
        Args:
            content: 消息内容
            
        Returns:
            bool: 是否是语音生成请求
        """
        if not content:
            return False
            
        # 检查是否包含语音生成关键字
        for keyword in self.voice_generation_keywords:
            if keyword in content:
                return True
                
        return False
    
    def is_voice_recognition_request(self, content: str) -> bool:
        """
        检查是否是语音识别请求
        
        Args:
            content: 消息内容
            
        Returns:
            bool: 是否是语音识别请求
        """
        if not content:
            return False
            
        # 检查是否包含语音识别关键字
        for keyword in self.voice_recognition_keywords:
            if keyword in content:
                return True
                
        return False

    def generate_voice(self, text: str, voice_name: str = None) -> Optional[str]:
        """
        生成语音文件
        
        Args:
            text: 要转换为语音的文本
            voice_name: 语音名称，如果为None则使用默认语音
            
        Returns:
            Optional[str]: 生成的语音文件路径，如果失败则返回None
        """
        if not text:
            logger.warning("无法生成语音：文本为空")
            return None
            
        # 使用指定的语音名称或默认语音
        voice_name = voice_name or self.default_voice
        
        try:
            # 确保语音目录存在
            if not os.path.exists(self.voice_dir):
                os.makedirs(self.voice_dir)
                
            # 生成唯一的文件名
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            voice_path = os.path.join(self.voice_dir, f"voice_{timestamp}.mp3")
            
            # 检查是否设置了TTS API URL
            if self.tts_api_url:
                # 调用TTS API
                response = requests.get(f"{self.tts_api_url}?text={text}", stream=True)
                if response.status_code == 200:
                    with open(voice_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    logger.info(f"成功生成语音: {voice_path}")
                    return voice_path
                else:
                    logger.error(f"语音生成失败: {response.status_code}")
                    return None
            else:
                # 使用TTS引擎
                if self.tts_engine:
                    # TODO: 实现实际的TTS引擎调用逻辑
                    success = False  # 修改为True进行测试
                    
                    if success:
                        logger.info(f"成功生成语音: {voice_path}")
                        return voice_path
                    else:
                        logger.warning(f"语音生成失败: {text[:30]}...")
                        return None
                else:
                    logger.warning("未配置TTS API或TTS引擎")
                    return None
                
        except Exception as e:
            logger.error(f"生成语音失败: {str(e)}")
            return None

    async def recognize_voice(self, voice_path: str) -> Optional[str]:
        """
        将语音文件转换为文本
        
        Args:
            voice_path: 语音文件路径
            
        Returns:
            Optional[str]: 识别的文本，如果失败则返回None
        """
        if not os.path.exists(voice_path):
            logger.error(f"语音文件不存在: {voice_path}")
            return None
            
        if not self.stt_engine:
            logger.warning("语音识别引擎未初始化")
            return None
            
        try:
            # TODO: 实现实际的语音识别逻辑
            # 模拟识别过程，实际应用中这里应该调用STT引擎
            recognized_text = "这是识别出的文本"  # 替换为实际识别结果
            
            logger.info(f"成功识别语音: {voice_path}")
            return recognized_text
            
        except Exception as e:
            logger.error(f"识别语音失败: {str(e)}")
            return None
    
    def clean_tts_text(self, text: str) -> str:
        """
        清理用于TTS的文本，移除不适合语音合成的内容
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""
            
        # 移除URL
        text = re.sub(r'https?://\S+', '网址链接', text)
        
        # 移除表情符号
        text = re.sub(r'[\U00010000-\U0010ffff\u2600-\u26FF\u2700-\u27BF]', '', text)
        
        # 移除多余的空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 限制长度
        max_length = 500  # 大多数TTS引擎的限制
        if len(text) > max_length:
            text = text[:max_length] + "..."
            
        return text

    def cleanup_voice_dir(self):
        """清理语音目录中的旧文件"""
        try:
            if os.path.exists(self.voice_dir):
                # 获取当前时间戳
                current_time = time.time()
                
                for file_name in os.listdir(self.voice_dir):
                    file_path = os.path.join(self.voice_dir, file_name)
                    try:
                        if os.path.isfile(file_path):
                            # 获取文件的修改时间
                            file_mod_time = os.path.getmtime(file_path)
                            
                            # 如果文件超过24小时未修改，则删除
                            if current_time - file_mod_time > 24 * 60 * 60:
                                os.remove(file_path)
                                logger.info(f"清理旧语音文件: {file_path}")
                    except Exception as e:
                        logger.error(f"清理语音文件失败 {file_path}: {str(e)}")
                        
                logger.info("语音目录清理完成")
        except Exception as e:
            logger.error(f"清理语音目录失败: {str(e)}") 
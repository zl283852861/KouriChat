"""
表情包处理模块
负责处理表情包相关功能，包括:
- 表情包请求识别
- 表情包选择
- 表情包截图
- 文件管理
"""

import os
import random
import logging
import re
from datetime import datetime
import pyautogui
import time
from wxauto import WeChat
from typing import Tuple, Optional
from src.config.rag_config import config

# 修改logger获取方式，确保与main模块一致
logger = logging.getLogger('main')

class EmojiHandler:
    def __init__(self, root_dir, wx_instance=None):
        self.root_dir = root_dir
        self.wx = wx_instance  # 使用传入的 WeChat 实例
        self.emoji_dir = os.path.join(root_dir, config.behavior.context.avatar_dir, "emojis")
        self.screenshot_dir = os.path.join(root_dir, 'screenshot')
        
        # 情感分类映射（情感目录名: 关键词列表）
        self.emotion_map = {
            # 情感关键词映射，每个情感类别对应一组关键词
            'happy': ['开心', '高兴', '哈哈', '笑', '嘻嘻', '可爱', '乐', '啊哈', '好', '愉快', '满意', '幸福', '喜悦', '兴奋', '爽', '棒', '感兴趣', '探讨', '一起', '随时', '有意思'],  # 表示快乐和友好的关键词
            'sad': ['难过', '伤心', '哭', '委屈', '泪', '呜呜', '悲', '唉', '失落', '沮丧', '悲伤', '痛苦', '绝望', '伤感'],  # 表示悲伤的关键词
            'angry': ['生气', '怒', '哼', '愤怒', '恼火', '气愤', '暴躁', '火大', '抓狂'],  # 表示愤怒的关键词
            'neutral': ['平静', '冷静', '一般', '普通', '无聊', '随便', '还好', '正常', '一般般']  # 默认中性分类，表示没有明显情感波动的关键词
        }
        
        # 确保目录存在
        os.makedirs(self.emoji_dir, exist_ok=True)
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def is_emoji_request(self, text: str) -> bool:
        """判断是否为表情包请求"""
        emoji_keywords = ["来个表情包", "斗图", "gif", "动图"]
        return any(keyword in text.lower() for keyword in emoji_keywords)

    def detect_emotion(self, text: str) -> str:
        """从文本中检测情感分类"""
        # 初始化情感得分
        emotion_scores = {
            'happy': 0,
            'sad': 0,
            'angry': 0,
            'neutral': 0
        }
        
        # 否定词列表
        negation_words = ['不', '没', '别', '莫', '勿', '非', '无', '未', '休']
        
        # 检查是否包含否定词
        has_negation = any(word in text for word in negation_words)
        
        # 计算每个情感类别的得分
        for emotion, keywords in self.emotion_map.items():
            if emotion == 'neutral':
                continue
                
            # 计算匹配的关键词数量
            matched_keywords = [keyword for keyword in keywords if keyword in text]
            
            # 根据匹配的关键词数量和位置计算得分
            for keyword in matched_keywords:
                # 基础分值
                score = 1.0
                
                # 如果关键词出现在句子末尾，增加权重
                if text.endswith(keyword):
                    score *= 1.5
                    
                # 如果存在否定词，可能需要转换情感
                if has_negation:
                    # 检查否定词是否直接修饰当前关键词
                    for neg_word in negation_words:
                        neg_pos = text.find(neg_word)
                        if neg_pos != -1 and 0 <= text.find(keyword) - neg_pos <= 5:
                            # 如果否定词直接修饰情感词，转换情感
                            if emotion == 'happy':
                                emotion_scores['sad'] += score
                            elif emotion == 'sad':
                                emotion_scores['happy'] += score
                            break
                    else:
                        # 否定词不直接修饰当前关键词
                        emotion_scores[emotion] += score
                else:
                    emotion_scores[emotion] += score
        
        # 如果没有明显情感倾向，返回neutral
        max_score = max(emotion_scores.values())
        if max_score == 0:
            return 'neutral'
            
        # 返回得分最高的情感
        return max(emotion_scores.items(), key=lambda x: x[1])[0]

    def get_emotion_emoji(self, text: str) -> Optional[str]:
        """根据AI回复内容的情感获取对应表情包"""
        try:
            # 检测情感分类
            emotion = self.detect_emotion(text)
            target_dir = os.path.join(self.emoji_dir, emotion)
            
            # 回退机制处理
            if not os.path.exists(target_dir):
                if os.path.exists(self.emoji_dir):
                    logger.warning(f"情感目录 {emotion} 不存在，使用根目录")
                    target_dir = self.emoji_dir
                else:
                    logger.error(f"表情包根目录不存在: {self.emoji_dir}")
                    return None

            # 获取有效表情包文件
            emoji_files = [f for f in os.listdir(target_dir)
                          if f.lower().endswith(('.gif', '.jpg', '.png', '.jpeg'))]
            
            if not emoji_files:
                logger.warning(f"目录中未找到表情包: {target_dir}")
                return None
                
            # 随机选择并返回路径
            selected = random.choice(emoji_files)
            logger.info(f"已选择 {emotion} 表情包: {selected}")
            return os.path.join(target_dir, selected)
        except Exception as e:
            logger.error(f"获取表情包失败: {str(e)}", exc_info=True)
            return None

    def capture_emoji_screenshot(self, username: str) -> str:
        """捕获并保存表情包截图"""
        try:
            # 确保目录存在
            emoji_dir = os.path.join(self.root_dir, "data", "emoji_cache")
            os.makedirs(emoji_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"emoji_{username}_{timestamp}.png"
            filepath = os.path.join(emoji_dir, filename)
            
            # 等待表情加载
            time.sleep(0.5)
            
            # 使用 pyautogui 的安全模式
            pyautogui.FAILSAFE = True
            
            # 获取当前活动窗口
            try:
                wx_chat = WeChat()
                wx_chat.ChatWith(username)  # 确保切换到正确的聊天窗口
                chat_window = pyautogui.getWindowsWithTitle(username)[0]
                
                # 确保窗口被前置和激活
                if not chat_window.isActive:
                    chat_window.activate()
                
                # 获取消息区域的位置（右下角）
                window_width = chat_window.width
                window_height = chat_window.height
                
                # 计算表情区域（消息区域的右侧）
                emoji_width = 150
                emoji_height = 150
                emoji_x = chat_window.left + window_width - emoji_width - 50  # 右边缘偏移50像素
                emoji_y = chat_window.top + window_height - emoji_height - 50  # 下边缘偏移50像素
                
                # 截取表情区域
                screenshot = pyautogui.screenshot(region=(emoji_x, emoji_y, emoji_width, emoji_height))
                screenshot.save(filepath)
                
                logger.info(f"表情包已保存: {filepath}")
                return filepath
            except Exception as e:
                logger.error(f"窗口操作失败: {str(e)}")
                return ""
                
        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            return ""

    def capture_chat_screenshot(self, who: str) -> str:
        """捕获并保存聊天窗口截图"""
        try:
            # 确保截图目录存在
            os.makedirs(self.screenshot_dir, exist_ok=True)
            
            screenshot_path = os.path.join(
                self.screenshot_dir, 
                f'{who}_{datetime.now().strftime("%Y%m%d%H%M%S")}.png'
            )
            
            try:
                # 激活并定位微信聊天窗口
                wx_chat = WeChat()
                wx_chat.ChatWith(who)
                chat_window = pyautogui.getWindowsWithTitle(who)[0]
                
                # 确保窗口被前置和激活
                if not chat_window.isActive:
                    chat_window.activate()
                if not chat_window.isMaximized:
                    chat_window.maximize()
                
                # 获取窗口的坐标和大小
                x, y, width, height = chat_window.left, chat_window.top, chat_window.width, chat_window.height

                time.sleep(1)  # 短暂等待确保窗口已激活

                # 截取指定窗口区域的屏幕
                screenshot = pyautogui.screenshot(region=(x, y, width, height))
                screenshot.save(screenshot_path)
                logger.info(f'已保存截图: {screenshot_path}')
                return screenshot_path
                
            except Exception as e:
                logger.error(f'截取或保存截图失败: {str(e)}')
                return None
                
        except Exception as e:
            logger.error(f'创建截图目录失败: {str(e)}')
            return None

    def cleanup_screenshot_dir(self):
        """清理截图目录"""
        try:
            if os.path.exists(self.screenshot_dir):
                for file in os.listdir(self.screenshot_dir):
                    file_path = os.path.join(self.screenshot_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        logger.error(f"删除截图失败 {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"清理截图目录失败: {str(e)}")
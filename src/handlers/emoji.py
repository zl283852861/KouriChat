"""
表情包处理模块
负责处理表情包相关功能，包括:
- 表情包请求识别
- 表情包选择
- 文件管理
"""

import os
import random
import logging
import re
import yaml
from datetime import datetime
from typing import Tuple, Optional, Callable, Dict, List, Any
import threading
import queue
import time
from src.config.rag_config import config
from src.webui.routes.avatar import AVATARS_DIR

# 基础表情包触发概率配置
EMOJI_TRIGGER_RATE = 0.3  # 基础触发概率30%
TRIGGER_RATE_INCREMENT = 0.15  # 未触发时概率增加量
MAX_TRIGGER_RATE = 0.8  # 最大触发概率

# 获取logger
logger = logging.getLogger('main')

class EmojiHandler:
    def __init__(self, root_dir, wx_instance=None, sentiment_analyzer=None, config=None):
        """
        初始化表情处理器
        
        Args:
            root_dir: 根目录
            wx_instance: WeChat实例的引用
            sentiment_analyzer: 情感分析器实例
            config: 配置信息字典
        """
        self.root_dir = root_dir
        self.wx = wx_instance
        self.sentiment_analyzer = sentiment_analyzer
        self.config = config or {}
        
        # 从配置中读取头像目录
        self.avatar_dir = self._get_avatar_dir_from_config()
        
        # 表情包处理路径
        self.emoji_dir = os.path.join(AVATARS_DIR, self.avatar_dir, "emojis")
        os.makedirs(self.emoji_dir, exist_ok=True)
        
        # 使用任务队列替代处理锁
        self.task_queue = queue.Queue()
        self.is_replying = False
        self.worker_thread = threading.Thread(target=self._process_emoji_queue, daemon=True)
        self.worker_thread.start()
        
        # 情感到目录的映射 (新系统)
        self.emotion_dir_map = {
            'Happy': 'happy',
            'Sad': 'sad',
            'Anger': 'angry',
            'Neutral': 'neutral',
            'Surprise': 'surprise',
            'Fear': 'fear',
            'Depress': 'depress',
            'Dislike': 'dislike'
        }
        
        # 表情包分类目录 (旧系统)
        self.emotions = {
            "happy": ["高兴", "开心", "快乐", "喜悦", "欢乐", "笑", "爽", "哈哈"],
            "sad": ["悲伤", "难过", "伤心", "痛苦", "失落", "哭", "泪"],
            "angry": ["生气", "愤怒", "恼怒", "怒火", "发火", "暴怒", "怒"],
            "surprised": ["惊讶", "惊奇", "震惊", "意外", "惊", "吃惊"],
            "disgusted": ["厌恶", "反感", "恶心", "讨厌", "嫌弃"],
            "fearful": ["害怕", "恐惧", "担心", "惊恐", "怕", "畏惧"],
            "neutral": ["平静", "正常", "普通", "一般", "淡定"],
            "excited": ["兴奋", "激动", "热情", "嗨", "兴高采烈"],
            "love": ["爱", "喜欢", "爱心", "爱情", "暗恋", "温馨"],
            "embarrassed": ["尴尬", "难为情", "害羞", "羞涩", "羞耻"],
            "proud": ["骄傲", "自豪", "得意", "满足"],
            "confused": ["困惑", "疑惑", "迷惑", "不解", "不明白"],
            "bored": ["无聊", "乏味", "枯燥", "无趣"],
            "sleepy": ["困", "困倦", "睡意", "瞌睡", "疲倦"],
            "amused": ["逗乐", "好笑", "幽默", "搞笑", "滑稽"],
            "annoyed": ["烦恼", "烦躁", "不爽", "不满", "嫌烦"]
        }
        
        # 触发概率状态维护 {user_id: current_prob}
        self.trigger_states = {}
        
        # 创建表情目录
        self._create_emotion_directories()
        
        # 表情包关键字
        self.emoji_keywords = ["发表情", "来个表情包", "表情包", "斗图", "发个表情", "发个gif", "发个动图"]
    
    def _get_avatar_dir_from_config(self):
        """从配置文件中读取avatar_dir设置"""
        try:
            # 首先尝试从rag_config中获取
            if hasattr(config, 'behavior') and hasattr(config.behavior, 'context') and hasattr(config.behavior.context, 'avatar_dir'):
                avatar_dir = config.behavior.context.avatar_dir
                logger.info(f"从rag_config中读取到头像目录: {avatar_dir}")
                return avatar_dir
            
            # 尝试从配置文件读取
            config_path = os.path.join('src', 'config', 'config.yaml')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                avatar_dir = config_data.get('categories', {}).get('behavior_settings', {}).get('settings', {}).get('context', {}).get('avatar_dir', {}).get('value', 'MONO')
                logger.info(f"从配置文件中读取到头像目录: {avatar_dir}")
                return avatar_dir
            else:
                logger.warning("配置文件不存在，使用默认值MONO")
                return "MONO"
        except Exception as e:
            logger.error(f"读取配置失败: {str(e)}，使用默认值MONO")
            return "MONO"
    
    def _create_emotion_directories(self):
        """创建情感目录"""
        # 为旧系统情绪创建目录
        for emotion in self.emotions:
            emotion_dir = os.path.join(self.emoji_dir, emotion)
            os.makedirs(emotion_dir, exist_ok=True)
        
        # 为新系统情绪创建目录
        for emotion_dir in self.emotion_dir_map.values():
            dir_path = os.path.join(self.emoji_dir, emotion_dir)
            os.makedirs(dir_path, exist_ok=True)
    
    def is_emoji_request(self, text: str) -> bool:
        """判断是否为表情包请求"""
        if not text:
            return False
            
        # 检查是否包含表情包关键字
        return any(keyword in text.lower() for keyword in self.emoji_keywords)

    def _update_trigger_prob(self, user_id: str, triggered: bool):
        """更新触发概率状态"""
        current_prob = self.trigger_states.get(user_id, EMOJI_TRIGGER_RATE)
        
        if triggered:
            # 触发后重置概率
            new_prob = EMOJI_TRIGGER_RATE
        else:
            # 未触发时增加概率（使用指数衰减）
            new_prob = min(current_prob + TRIGGER_RATE_INCREMENT * (1 - current_prob), MAX_TRIGGER_RATE)
        
        self.trigger_states[user_id] = new_prob
        logger.debug(f"用户 {user_id} 触发概率更新: {current_prob:.2f} -> {new_prob:.2f}")

    def should_send_emoji(self, user_id: str) -> bool:
        """判断是否应该发送表情包"""
        current_prob = self.trigger_states.get(user_id, EMOJI_TRIGGER_RATE)
        if random.random() < current_prob:
            self._update_trigger_prob(user_id, True)
            return True
        self._update_trigger_prob(user_id, False)
        return False

    def _process_emoji_queue(self):
        """后台线程处理表情包任务队列"""
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
                text, user_id, callback = task
                
                # 执行表情包获取
                result = self._get_emotion_emoji_impl(text, user_id)
                if callback and result:
                    callback(result)
                    
            except Exception as e:
                logger.error(f"处理表情包队列时出错: {str(e)}")
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
        logger.debug(f"表情包处理回复状态已更新: {'正在回复' if is_replying else '回复结束'}")
    
    def _detect_emotion_from_text(self, content: str) -> tuple[Optional[str], bool]:
        """
        从消息内容中检测情绪
        
        Args:
            content: 消息内容
            
        Returns:
            tuple: (检测到的情绪类型, 是否是新情绪系统)，如果未检测到则返回(None, False)
        """
        if not content:
            return None, False
        
        # 首先检查新的情绪系统
        # 创建情绪关键词映射
        new_emotion_keywords = {
            'Happy': ['快乐', '开心', '高兴', '愉快', '欢喜', '笑'],
            'Sad': ['悲伤', '难过', '伤心', '哀伤', '痛苦', '哭'],
            'Anger': ['愤怒', '生气', '恼火', '气愤', '怒火', '发怒'],
            'Neutral': ['平静', '中性', '普通', '一般', '淡定'],
            'Surprise': ['惊讶', '吃惊', '震惊', '意外', '惊奇'],
            'Fear': ['恐惧', '害怕', '惊恐', '惧怕', '畏惧'],
            'Depress': ['沮丧', '抑郁', '消沉', '低落', '郁闷'],
            'Dislike': ['厌恶', '讨厌', '反感', '嫌弃', '不喜欢']
        }
        
        # 检查新情绪系统关键词
        max_matches = 0
        detected_new_emotion = None
        
        for emotion, keywords in new_emotion_keywords.items():
            matches = 0
            for keyword in keywords:
                if keyword in content:
                    matches += 1
            
            if matches > max_matches:
                max_matches = matches
                detected_new_emotion = emotion
        
        # 如果找到匹配的新情绪
        if max_matches > 0 and detected_new_emotion:
            emotion_dir = self.emotion_dir_map.get(detected_new_emotion)
            logger.info(f"从消息中检测到新系统情绪: {detected_new_emotion} -> {emotion_dir}")
            return emotion_dir, True
        
        # 如果没有找到新情绪，则使用旧的情绪系统
        max_matches = 0
        detected_old_emotion = None
        
        for emotion, keywords in self.emotions.items():
            matches = 0
            for keyword in keywords:
                if keyword in content:
                    matches += 1
            
            if matches > max_matches:
                max_matches = matches
                detected_old_emotion = emotion
        
        # 如果找到匹配的旧情绪
        if max_matches > 0:
            logger.info(f"从消息中检测到旧系统情绪: {detected_old_emotion}")
            return detected_old_emotion, False
        
        # 没有找到匹配的情绪
        return None, False

    def _get_emotion_emoji_impl(self, text: str, user_id: str) -> Optional[str]:
        """实际执行表情包获取的内部方法"""
        try:
            # 判断是否触发表情包发送
            if not self.should_send_emoji(user_id):
                logger.info(f"未触发表情发送（用户 {user_id}）")
                return None
            
            # 首先尝试使用情感分析器
            if self.sentiment_analyzer:
                try:
                    # 获取情感分析结果
                    result = self.sentiment_analyzer.analyze(text)
                    emotion_type = result.get('sentiment_type', 'Neutral')
                    
                    # 映射到目录
                    target_emotion = self.emotion_dir_map.get(emotion_type, 'neutral')
                    logger.debug(f"情感分析结果: {emotion_type} -> 目录: {target_emotion}")
                except Exception as e:
                    logger.warning(f"情感分析失败，回退到文本匹配: {str(e)}")
                    target_emotion = None
            else:
                target_emotion = None
            
            # 如果情感分析不可用或失败，使用文本关键词匹配
            if not target_emotion:
                detected_emotion, is_new_emotion = self._detect_emotion_from_text(text)
                if detected_emotion:
                    target_emotion = detected_emotion
                else:
                    # 随机选择一个情绪
                    if random.random() < 0.5:  # 50%概率使用新情绪系统
                        target_emotion = random.choice(list(self.emotion_dir_map.values()))
                    else:
                        target_emotion = random.choice(list(self.emotions.keys()))
                    logger.debug(f"随机选择情绪: {target_emotion}")
            
            # 查找对应情绪目录
            target_dir = os.path.join(self.emoji_dir, target_emotion)
            
            # 回退机制处理
            if not os.path.exists(target_dir):
                if os.path.exists(self.emoji_dir):
                    logger.warning(f"情感目录 {target_emotion} 不存在，使用根目录")
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
            logger.info(f"已选择 {target_emotion} 表情包: {selected}")
            return os.path.join(target_dir, selected)
            
        except Exception as e:
            logger.error(f"获取表情包失败: {str(e)}", exc_info=True)
            return None

    def get_emotion_emoji(self, text: str, user_id: str, callback: Callable = None, is_self_emoji: bool = False) -> Optional[str]:
        """将表情包获取任务添加到队列"""
        try:
            # 如果是自己发送的表情包，直接跳过处理
            if is_self_emoji:
                logger.info(f"检测到自己发送的表情包，跳过获取和识别")
                return None
                
            # 添加到任务队列
            self.task_queue.put((text, user_id, callback))
            logger.info(f"已添加表情包获取任务到队列，用户: {user_id}")
            return "表情包请求已添加到队列，将在消息回复后处理"
        except Exception as e:
            logger.error(f"添加表情包获取任务失败: {str(e)}")
            return None
            
    async def initialize(self):
        """初始化表情处理器，加载表情包资源"""
        try:
            # 扫描表情包目录，加载表情包资源
            logger.info("初始化表情处理器...")
            
            # 检查表情包目录
            emoji_count = 0
            
            # 统计旧情绪系统的表情包
            for emotion in self.emotions:
                emotion_dir = os.path.join(self.emoji_dir, emotion)
                if os.path.exists(emotion_dir):
                    # 统计图片数量
                    files = [f for f in os.listdir(emotion_dir) 
                             if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
                    emoji_count += len(files)
            
            # 统计新情绪系统的表情包
            for emotion_dir in self.emotion_dir_map.values():
                dir_path = os.path.join(self.emoji_dir, emotion_dir)
                if os.path.exists(dir_path):
                    # 统计图片数量
                    files = [f for f in os.listdir(dir_path) 
                             if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
                    emoji_count += len(files)
            
            logger.info(f"表情处理器初始化完成，共加载 {emoji_count} 个表情包")
            return True
        except Exception as e:
            logger.error(f"初始化表情处理器失败: {str(e)}")
            return False

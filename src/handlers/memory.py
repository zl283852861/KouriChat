import os
import logging
import random
from typing import List, Optional, Dict  # 添加 Dict 导入
from datetime import datetime
from src.services.ai.llm_service import LLMService
import jieba
import re
from src.handlers.emotion import SentimentResourceLoader, SentimentAnalyzer
import json

logger = logging.getLogger('main')

# 定义需要重点关注的关键词列表
KEYWORDS = [
    "记住了没？", "记好了", "记住", "别忘了", "牢记", "记忆深刻", "不要忘记", "铭记",
    "别忘掉", "记在心里", "时刻记得", "莫失莫忘", "印象深刻", "难以忘怀", "念念不忘", "回忆起来",
    "永远不忘", "留意", "关注", "提醒", "提示", "警示", "注意", "特别注意",
    "记得检查", "请记得", "务必留意", "时刻提醒自己", "定期回顾", "随时注意", "不要忽略", "确认一下",
    "核对", "检查", "温馨提示", "小心"
]


class MemoryHandler:
    def __init__(self, root_dir: str, api_key: str, base_url: str, model: str,
                 max_token: int, temperature: float, max_groups: int, 
                 bot_name: str = None, sentiment_analyzer: SentimentAnalyzer = None):
        # 基础参数
        self.root_dir = root_dir
        self.api_key = api_key
        self.base_url = base_url
        self.max_token = max_token
        self.temperature = temperature
        self.max_groups = max_groups
        self.model = model
        
        # 从config模块获取配置
        from config import config
        self.bot_name = bot_name or config.robot_wx_name
        self.listen_list = config.user.listen_list
        
        # 记忆目录结构
        self.memory_base_dir = os.path.join(root_dir, "data", "memory")
        os.makedirs(self.memory_base_dir, exist_ok=True)
        
        # 初始化每个用户的记忆文件
        for user_id in self.listen_list:
            if user_id:  # 确保用户ID不为空
                self._init_user_files(user_id)

    # 删除不需要的方法
    def _load_config(self):
        """此方法不再需要"""
        pass

    def _get_robot_name_from_config(self):
        """此方法不再需要"""
        pass

    def _get_listen_list_from_config(self):
        """此方法不再需要"""
        pass

    def _get_memory_paths(self, user_id: str) -> tuple:
        """获取用户的所有记忆文件路径"""
        user_dir = self._get_user_memory_dir(user_id)
        return (
            os.path.join(user_dir, "short_memory.txt"),
            os.path.join(user_dir, "long_memory_buffer.txt"),
            os.path.join(user_dir, "important_memory.txt")  # 修改文件名
        )

    def add_short_memory(self, message: str, reply: str, user_id: str):
        """添加短期记忆"""
        # 移除或修改这个检查，因为可能有些用户ID不在listen_list中
        # if not user_id or user_id not in self.listen_list:
        if not user_id:
            logger.error(f"无效的用户ID: {user_id}")
            return
            
        try:
            self._ensure_memory_files(user_id)
            short_memory_path, _, _ = self._get_memory_paths(user_id)
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 写入记忆
            memory_content = (
                f"[{timestamp}] 用户: {message}\n"
                f"[{timestamp}] bot: {reply}\n\n"
            )
            
            try:
                with open(short_memory_path, "a", encoding="utf-8") as f:
                    f.write(memory_content)
                logger.info(f"成功写入短期记忆: {user_id}")
                print(f"控制台日志: 成功写入短期记忆 - 用户ID: {user_id}")
            except Exception as e:
                logger.error(f"写入短期记忆失败: {str(e)}")
                print(f"控制台日志: 写入短期记忆失败 - 用户ID: {user_id}, 错误: {str(e)}")
                return
                
            # 检查关键词并添加重要记忆
            if any(keyword in message for keyword in KEYWORDS):
                self._add_important_memory(message, user_id)
                
        except Exception as e:
            logger.error(f"添加短期记忆失败: {str(e)}")
            print(f"控制台日志: 添加短期记忆失败 - 用户ID: {user_id}, 错误: {str(e)}")

    def _add_important_memory(self, message: str, user_id: str):
        """添加重要记忆"""
        if not user_id:
            raise ValueError("用户ID不能为空")
            
        try:
            _, _, important_memory_path = self._get_memory_paths(user_id)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            memory_content = f"[{timestamp}] 重要记忆: {message}\n"
            
            with open(important_memory_path, "a", encoding="utf-8") as f:
                f.write(memory_content)
            logger.info(f"成功写入重要记忆: {user_id}")
            print(f"控制台日志: 成功写入重要记忆 - 用户ID: {user_id}")
        except Exception as e:
            logger.error(f"写入重要记忆失败: {str(e)}")
            print(f"控制台日志: 写入重要记忆失败 - 用户ID: {user_id}, 错误: {str(e)}")

    def _ensure_memory_files(self, user_id: str):
        """确保用户的记忆文件存在"""
        try:
            # 获取所有记忆文件路径
            short_memory_path, long_memory_buffer_path, important_memory_path = self._get_memory_paths(user_id)
            
            # 确保用户目录存在
            user_dir = os.path.dirname(short_memory_path)
            os.makedirs(user_dir, exist_ok=True)
            
            # 检查并创建所有必要的文件
            for file_path in [short_memory_path, long_memory_buffer_path, important_memory_path]:
                if not os.path.exists(file_path):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        pass  # 创建空文件
                    logger.info(f"创建记忆文件: {file_path}")
            
            return True
        except Exception as e:
            logger.error(f"确保记忆文件存在时出错: {str(e)}")
            return False

    def get_relevant_memories(self, query: str, user_id: Optional[str] = None) -> List[str]:
        """获取相关记忆"""
        # 如果没有提供 user_id，使用 listen_list 中的第一个用户
        if user_id is None and self.listen_list:
            user_id = self.listen_list[0]
            
        if not user_id:
            logger.error("无效的用户ID")
            return []
            
        _, long_memory_buffer_path, important_memory_path = self._get_memory_paths(user_id)  # 修改变量名
        
        important_memories = []  # 修改变量名
        prioritized_memories = []
        
        # 尝试读取重要记忆
        if os.path.exists(important_memory_path):  # 修改变量名
            try:
                with open(important_memory_path, "r", encoding="utf-8") as f:  # 修改变量名
                    important_memories = [line.strip() for line in f if line.strip()]  # 修改变量名
                logger.debug(f"用户 {user_id} 的重要记忆数量: {len(important_memories)}")  # 修改日志文本
            except Exception as e:
                logger.error(f"读取用户 {user_id} 的重要记忆文件失败: {str(e)}")  # 修改错误文本
        
        # 检查长期记忆缓冲区是否存在
        if not os.path.exists(long_memory_buffer_path):
            logger.warning(f"用户 {user_id} 的长期记忆缓冲")

    def _get_user_memory_dir(self, user_id: str) -> str:
        """获取特定用户的记忆目录路径"""
        # 创建层级目录结构: data/memory/{bot_name}/{user_id}/
        bot_memory_dir = os.path.join(self.memory_base_dir, self.bot_name)
        user_memory_dir = os.path.join(bot_memory_dir, user_id)
        
        # 确保目录存在
        try:
            os.makedirs(bot_memory_dir, exist_ok=True)
            os.makedirs(user_memory_dir, exist_ok=True)
            logger.debug(f"确保用户记忆目录存在: {user_memory_dir}")
        except Exception as e:
            logger.error(f"创建用户记忆目录失败 {user_memory_dir}: {str(e)}")
        
        return user_memory_dir

    def _init_user_files(self, user_id: str):
        """初始化用户的记忆文件"""
        try:
            short_memory_path, long_memory_buffer_path, important_memory_path = self._get_memory_paths(user_id)
            
            files_to_check = [short_memory_path, long_memory_buffer_path, important_memory_path]
            for f in files_to_check:
                if not os.path.exists(f):
                    try:
                        with open(f, "w", encoding="utf-8") as _:
                            logger.info(f"为用户 {user_id} 创建文件: {os.path.basename(f)}")
                    except Exception as file_e:
                        logger.error(f"创建记忆文件失败 {f}: {str(file_e)}")
        except Exception as e:
            logger.error(f"初始化用户文件失败 {user_id}: {str(e)}")

    def get_recent_memory(self, user_id: str, max_count: int = 5) -> List[Dict[str, str]]:
        """获取最近的对话记录"""
        try:
            # 使用正确的路径获取方法
            short_memory_path, _, _ = self._get_memory_paths(user_id)
            if not os.path.exists(short_memory_path):
                return []
                
            with open(short_memory_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            history = []
            current_pair = {}
            
            # 从后往前读取，获取最近的对话
            for line in reversed(lines):
                line = line.strip()
                if line.startswith("[") and "] 用户:" in line:
                    current_pair["message"] = line.split("] 用户:", 1)[1].strip()
                    if "reply" in current_pair:
                        history.append(current_pair)
                        current_pair = {}
                        if len(history) >= max_count:
                            break
                elif line.startswith("[") and "] bot:" in line:
                    current_pair["reply"] = line.split("] bot:", 1)[1].strip()
                        
            # 确保顺序是从早到晚
            return list(reversed(history))
                
        except Exception as e:
            logger.error(f"获取记忆失败: {str(e)}")
            return []
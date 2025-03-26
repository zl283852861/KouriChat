"""
消息处理器模块
负责消息的处理策略和响应生成
"""

import logging
import random
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from src.handlers.messages.base_handler import BaseHandler

# 获取logger
logger = logging.getLogger('main')

class MessageProcessor(BaseHandler):
    """消息处理器，负责消息处理策略和响应生成"""
    
    def __init__(self, message_manager=None, config=None):
        """
        初始化消息处理器
        
        Args:
            message_manager: 消息管理器实例的引用
            config: 配置信息字典
        """
        super().__init__(message_manager)
        self.config = config or {}
        
        # 设置响应参数
        self.response_settings = {
            'min_response_time': self.config.get('min_response_time', 1.0),
            'max_response_time': self.config.get('max_response_time', 5.0),
            'typing_speed': self.config.get('typing_speed', 0.1),  # 每字符秒数
            'thinking_time': self.config.get('thinking_time', 1.5),  # 思考时间
            'delay_per_char': self.config.get('delay_per_char', 0.1)  # 每字符添加的延迟
        }
    
    def calculate_response_length_ratio(self, user_message_length: int) -> float:
        """
        计算回复长度与用户消息的比例
        
        Args:
            user_message_length: 用户消息的长度
            
        Returns:
            float: 回复长度比例
        """
        # 基础比例从1.0开始，表示回复长度与用户消息长度相同
        base_ratio = 1.0
        
        # 根据用户消息长度动态调整比例，但保持在接近1.0的范围内
        if user_message_length < 10:  # 非常短的消息
            ratio = base_ratio * 1.5  # 短消息略微长一点
        elif user_message_length < 30:  # 较短的消息
            ratio = base_ratio * 1.3
        elif user_message_length < 50:  # 中等长度
            ratio = base_ratio * 1.2
        elif user_message_length < 100:  # 较长消息
            ratio = base_ratio * 1.1
        else:  # 很长的消息
            ratio = base_ratio * 1.0  # 对于长消息保持1:1比例
        
        # 限制最大比例，确保不会过长
        return min(ratio, 1.5)
    
    def calculate_response_delay(self, message_length: int, is_complex: bool = False) -> float:
        """
        计算响应延迟时间
        
        Args:
            message_length: 消息长度
            is_complex: 是否是复杂消息
            
        Returns:
            float: 延迟时间(秒)
        """
        # 基础延迟
        base_delay = self.response_settings['thinking_time']
        
        # 根据消息长度添加延迟
        length_factor = min(message_length * self.response_settings['delay_per_char'], 3.0)
        
        # 复杂消息添加额外延迟
        complexity_factor = 1.5 if is_complex else 1.0
        
        # 计算总延迟，并添加随机波动
        total_delay = (base_delay + length_factor) * complexity_factor
        randomized_delay = total_delay * random.uniform(0.8, 1.2)
        
        # 确保延迟在合理范围内
        final_delay = max(
            self.response_settings['min_response_time'],
            min(randomized_delay, self.response_settings['max_response_time'])
        )
        
        logger.debug(f"响应延迟计算: 消息长度={message_length}, 复杂度={is_complex}, 延迟={final_delay:.2f}秒")
        return final_delay
    
    def is_complex_message(self, content: str) -> bool:
        """
        判断消息是否复杂
        
        Args:
            content: 消息内容
            
        Returns:
            bool: 是否是复杂消息
        """
        if not content:
            return False
            
        # 检查消息长度
        if len(content) > 100:
            return True
            
        # 检查是否包含复杂格式
        has_code = bool(re.search(r'```[\s\S]*?```', content))
        has_table = ('|' in content and '-' in content and len(re.findall(r'\|', content)) > 3)
        has_math = bool(re.search(r'\$\$.+?\$\$|\$.+?\$', content))
        has_url = bool(re.search(r'https?://\S+', content))
        has_list = bool(re.search(r'^\s*[-*]\s+.+', content, re.MULTILINE))
        
        return has_code or has_table or has_math or has_url or has_list
    
    def is_sensitive_topic(self, content: str) -> bool:
        """
        检查消息是否包含敏感话题
        
        Args:
            content: 消息内容
            
        Returns:
            bool: 是否包含敏感话题
        """
        if not content:
            return False
            
        # 敏感话题关键字
        sensitive_keywords = self.config.get('sensitive_keywords', [
            '政治', '宗教', '色情', '暴力', '黄色', '赌博', '毒品', '自杀', '恐怖', '歧视'
        ])
        
        # 检查是否包含敏感关键字
        for keyword in sensitive_keywords:
            if keyword in content:
                logger.warning(f"检测到敏感话题: {keyword}")
                return True
                
        return False
    
    def is_command_message(self, content: str) -> bool:
        """
        检查消息是否是命令
        
        Args:
            content: 消息内容
            
        Returns:
            bool: 是否是命令
        """
        if not content:
            return False
            
        # 命令前缀列表
        command_prefixes = self.config.get('command_prefixes', ['/', '!', '#'])
        
        # 检查是否以命令前缀开头
        for prefix in command_prefixes:
            if content.startswith(prefix):
                return True
                
        return False
    
    def extract_command(self, content: str) -> Optional[Dict[str, str]]:
        """
        从消息中提取命令和参数
        
        Args:
            content: 消息内容
            
        Returns:
            Optional[Dict[str, str]]: 命令和参数，格式为 {'command': 'cmd', 'params': 'params'}
        """
        if not self.is_command_message(content):
            return None
            
        # 命令前缀列表
        command_prefixes = self.config.get('command_prefixes', ['/', '!', '#'])
        
        # 提取命令和参数
        for prefix in command_prefixes:
            if content.startswith(prefix):
                # 移除前缀
                command_text = content[len(prefix):]
                
                # 分割命令和参数
                parts = command_text.split(None, 1)
                command = parts[0].lower() if parts else ""
                params = parts[1] if len(parts) > 1 else ""
                
                return {
                    'command': command,
                    'params': params,
                    'prefix': prefix,
                    'original': content
                }
                
        return None
    
    def format_bot_response(self, response: str, user_name: str = None, is_group: bool = False) -> str:
        """
        格式化机器人响应
        
        Args:
            response: 原始响应内容
            user_name: 用户名，用于@回复
            is_group: 是否是群聊
            
        Returns:
            str: 格式化后的响应
        """
        if not response:
            return ""
            
        # 清理响应内容
        cleaned_response = self._clean_ai_response(response)
        
        # 群聊中添加@
        if is_group and user_name:
            # 检查是否已经包含@
            if not cleaned_response.startswith(f'@{user_name}'):
                cleaned_response = f'@{user_name} {cleaned_response}'
        
        return cleaned_response
    
    def should_respond(self, content: str, user_id: str, is_group: bool) -> bool:
        """
        判断是否应该回复消息
        
        Args:
            content: 消息内容
            user_id: 用户ID
            is_group: 是否是群聊
            
        Returns:
            bool: 是否应该回复
        """
        if not content:
            return False
            
        # 检查是否是命令
        if self.is_command_message(content):
            return True
            
        # 群聊中必须@才回复
        if is_group:
            # 检查是否@了机器人（这个判断应该在外部完成，这里假设已经判断过）
            return True
            
        # 私聊总是回复
        return True
        
    def get_conversation_memory_context(self, username_or_group_id: str, is_group: bool = False, query: str = None) -> str:
        """
        获取对话记忆上下文
        
        Args:
            username_or_group_id: 用户ID或群ID
            is_group: 是否是群聊
            query: 查询内容，用于获取相关记忆
            
        Returns:
            str: 上下文内容
        """
        if not self.message_manager or not hasattr(self.message_manager, 'memory_manager'):
            return ""
            
        memory_manager = self.message_manager.memory_manager
        return memory_manager.get_conversation_context(username_or_group_id, query)
        
    def is_quiet_time(self) -> bool:
        """
        检查当前是否是安静时间（不打扰时间）
        
        Returns:
            bool: 是否是安静时间
        """
        # 获取安静时间配置
        quiet_time = self.config.get('quiet_time', {})
        start_hour = quiet_time.get('start_hour', 22)
        end_hour = quiet_time.get('end_hour', 8)
        
        # 获取当前时间
        current_hour = datetime.now().hour
        
        # 判断是否在安静时间范围内
        if start_hour < end_hour:
            # 简单情况：如 22:00 - 8:00
            return start_hour <= current_hour or current_hour < end_hour
        else:
            # 跨日情况：如 22:00 - 8:00
            return start_hour <= current_hour and current_hour < 24 or 0 <= current_hour < end_hour 

if __name__ == "__main__":
    import asyncio
    import logging
    
    # 配置基本日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('test')
    
    class MockMessageManager:
        """模拟MessageManager类"""
        def __init__(self):
            pass
            
        def get_module(self, name):
            return None
    
    async def test_message_processor():
        print("开始测试消息处理器...")
        
        # 创建模拟对象
        manager = MockMessageManager()
        processor = MessageProcessor(manager)
        
        # 测试检测命令消息
        test_commands = [
            "#帮助",
            "#设置 参数=值",
            "普通消息，不是命令",
            "/start",
            "!command"
        ]
        
        for cmd in test_commands:
            is_command = processor.is_command_message(cmd)
            print(f"消息: '{cmd}'")
            print(f"是否是命令: {is_command}")
            print("---")
        
        # 测试格式化机器人响应
        test_responses = [
            "普通响应消息",
            "包含特殊字符的响应：@#$%^&*()",
            "多行响应\n第二行\n第三行"
        ]
        
        for resp in test_responses:
            # 私聊格式化
            formatted_private = processor.format_bot_response(resp, user_name="test_user", is_group=False)
            print(f"原始响应: '{resp}'")
            print(f"私聊格式化: '{formatted_private}'")
            
            # 群聊格式化
            formatted_group = processor.format_bot_response(resp, user_name="group_user", is_group=True)
            print(f"群聊格式化: '{formatted_group}'")
            print("---")
        
        # 测试should_respond方法
        test_scenarios = [
            {"content": "#帮助", "user_id": "test_user", "is_group": False},
            {"content": "普通消息", "user_id": "test_user", "is_group": False},
            {"content": "群聊消息", "user_id": "group_user", "is_group": True},
            {"content": "", "user_id": "test_user", "is_group": False}
        ]
        
        for scenario in test_scenarios:
            should_respond = processor.should_respond(**scenario)
            print(f"场景: {scenario}")
            print(f"是否应该响应: {should_respond}")
            print("---")
        
        # 测试清理AI响应
        if hasattr(processor, '_clean_ai_response'):
            test_ai_responses = [
                "普通AI响应",
                "</think>这是思考后的回复",
                "多余的空格和换行      \n\n\n",
                "[思考中]这应该是我的回复"
            ]
            
            for ai_resp in test_ai_responses:
                cleaned = processor._clean_ai_response(ai_resp)
                print(f"原始AI响应: '{ai_resp}'")
                print(f"清理后: '{cleaned}'")
                print("---")
        
        print("消息处理器测试完成")
    
    # 运行测试
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_message_processor()) 
"""
消息预处理模块
负责处理输入消息的格式化、构建LLM提示词等
"""

import re
import logging
from datetime import datetime
from src.handlers.messages.base_handler import BaseHandler

# 获取logger
logger = logging.getLogger('main')

class MessagePreprocessor(BaseHandler):
    """消息预处理器，负责格式化消息和构建提示词"""
    
    def __init__(self, message_manager=None):
        """
        初始化预处理器
        
        Args:
            message_manager: 消息管理器实例的引用
        """
        super().__init__(message_manager)
    
    def format_private_message(self, content, username, context=""):
        """
        格式化私聊消息，添加时间戳和上下文信息
        
        Args:
            content: 原始消息内容
            username: 用户ID
            context: 历史上下文信息
            
        Returns:
            str: 格式化后的消息
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 清理原始内容，确保不包含重复的时间戳
        cleaned_content = self._clean_message_content(content)
        
        # 构建带有时间戳的消息
        if context:
            formatted_message = f"{context}\n\n(以上是历史对话内容，仅供参考，无需进行互动。请专注处理接下来的新内容)\n\n[{current_time}] ta私聊对你说：{cleaned_content}"
        else:
            formatted_message = f"[{current_time}] ta私聊对你说：{cleaned_content}"
        
        return formatted_message
    
    def format_group_message(self, content, group_id, sender_name, context=""):
        """
        格式化群聊消息，添加时间戳、群ID和发送者信息
        
        Args:
            content: 原始消息内容
            group_id: 群聊ID
            sender_name: 发送者昵称
            context: 群聊上下文信息
            
        Returns:
            str: 格式化后的消息
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 清理原始内容，确保不包含重复的时间戳
        cleaned_content = self._clean_message_content(content)
        
        # 构建XML风格的消息结构，便于AI解析
        formatted_message = f"<time>{current_time}</time>\n<group>{group_id}</group>\n<sender>{sender_name}</sender>\n"
        
        if context:
            formatted_message += f"{context}\n"
        
        formatted_message += f"<input>{cleaned_content}</input>"
        
        return formatted_message
    
    def build_context_from_memory(self, memories, is_group=False):
        """
        从记忆中构建上下文信息
        
        Args:
            memories: 记忆列表
            is_group: 是否是群聊记忆
            
        Returns:
            str: 格式化的上下文信息
        """
        if not memories:
            return ""
        
        if is_group:
            # 构建群聊上下文
            context_parts = []
            for msg in memories:
                sender_display = msg.get('sender_name', 'Unknown')
                human_message = self._clean_memory_content(msg.get('human_message', ''))
                assistant_message = self._clean_memory_content(msg.get('assistant_message', ''))
                
                if human_message:
                    context_parts.append(f"{sender_display}: {human_message}")
                    if assistant_message:
                        context_parts.append(f"{self.message_manager.robot_name if self.message_manager else 'AI'}: {assistant_message}")
            
            if context_parts:
                return "<context>" + "\n".join(context_parts) + "</context>"
            return ""
        else:
            # 构建私聊上下文
            context_parts = []
            for idx, mem in enumerate(memories):
                if mem.get('message') and mem.get('reply'):
                    context_parts.append(f"对话{idx+1}:\n用户: {mem['message']}\nAI: {mem['reply']}")
            
            if context_parts:
                return "以下是之前的对话记录：\n\n" + "\n\n".join(context_parts)
            return ""
    
    def extract_quoted_content(self, content):
        """
        提取引用内容
        
        Args:
            content: 原始消息内容
            
        Returns:
            tuple: (清理后的内容, 引用者, 引用内容)
        """
        # 微信引用消息格式通常是: "引用 xxx 的消息"或"回复 xxx 的消息"
        quote_match = re.search(r'(?:引用|回复)\s+([^\s]+)\s+的(?:消息)?[:：]?\s*(.+?)(?=\n|$)', content)
        
        if quote_match:
            quoted_sender = quote_match.group(1)
            quoted_content = quote_match.group(2).strip()
            # 从原始消息中移除引用部分
            cleaned_content = re.sub(r'(?:引用|回复)\s+[^\s]+\s+的(?:消息)?[:：]?\s*.+?(?=\n|$)', '', content).strip()
            return (cleaned_content, quoted_sender, quoted_content)
        
        return (content, None, None)
    
    def detect_at_mention(self, content, robot_name):
        """
        检测@提及
        
        Args:
            content: 消息内容
            robot_name: 机器人名称
            
        Returns:
            tuple: (是否被@, @内容)
        """
        # 改进@机器人检测逻辑
        robot_name_pattern = re.escape(robot_name).replace('\\ ', '[ \u2005\u00A0\u200B\u3000]*')
        at_pattern = re.compile(f"@{robot_name_pattern}[\\s\u2005\u00A0\u200B\u3000]?")
        is_at = bool(at_pattern.search(content))
        
        # 提取原始@部分
        at_match = re.search(f"(@{re.escape(robot_name)}[\\s\u2005\u00A0\u200B\u3000]?)", content)
        at_content = at_match.group(1) if at_match else ''
        
        return (is_at, at_content)
    
    def merge_messages(self, messages):
        """
        合并多条消息
        
        Args:
            messages: 消息列表
            
        Returns:
            str: 合并后的消息
        """
        if not messages:
            return ""
        
        # 对消息按时间排序
        sorted_messages = sorted(messages, key=lambda x: x.get('timestamp', 0))
        
        # 提取每条消息的内容
        contents = []
        first_timestamp = None
        
        for msg in sorted_messages:
            content = msg.get('content', '')
            if not first_timestamp:
                # 提取第一条消息的时间戳
                timestamp_match = re.search(r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(?::\d{2})?', content)
                if timestamp_match:
                    first_timestamp = timestamp_match.group()
            
            # 清理消息内容
            cleaned_content = self._clean_message_content(content)
            if cleaned_content:
                contents.append(cleaned_content)
        
        # 使用 $ 作为句子分隔符合并消息
        merged_content = ' $ '.join(contents)
        
        return merged_content

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
    
    async def test_preprocessor():
        print("开始测试预处理器...")
        
        # 创建模拟对象
        manager = MockMessageManager()
        processor = MessagePreprocessor(manager)
        
        # 测试格式化私聊消息
        test_messages = [
            "你好，这是测试消息",
            "[2023-01-01 12:00:00] 带有时间戳的消息",
            "包含特殊字符的消息：@#$%^&*()"
        ]
        
        for msg in test_messages:
            # 不带上下文
            formatted = processor.format_private_message(msg, "test_user")
            print(f"原始消息: {msg}")
            print(f"格式化后 (无上下文): {formatted}")
            
            # 带上下文
            context = "历史消息1\n历史消息2"
            formatted_with_context = processor.format_private_message(msg, "test_user", context)
            print(f"格式化后 (有上下文): {formatted_with_context[:50]}...")
            print("---")
        
        # 测试preprocess_message方法
        test_message_data = [
            {
                "message_type": "private",
                "content": "私聊消息",
                "chat_id": "user1",
                "sender_name": "用户1",
                "username": "user1"
            },
            {
                "message_type": "group",
                "content": "@机器人 群聊消息",
                "chat_id": "group1",
                "sender_name": "群成员",
                "username": "group_user"
            }
        ]
        
        for data in test_message_data:
            preprocessed = await processor.preprocess_message(data)
            print(f"原始数据: {data}")
            print(f"预处理后: {preprocessed}")
            print("---")
        
        # 测试合并消息（如果实现了）
        if hasattr(processor, 'merge_messages'):
            messages = [
                {"content": "第一条消息", "timestamp": 1},
                {"content": "第二条消息", "timestamp": 2},
                {"content": "第三条消息", "timestamp": 3}
            ]
            merged = await processor.merge_messages(messages)
            print(f"合并后的消息: {merged}")
        
        print("预处理器测试完成")
    
    # 运行测试
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_preprocessor()) 
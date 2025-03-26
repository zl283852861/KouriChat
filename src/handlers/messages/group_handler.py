"""
群聊消息处理模块
负责处理群聊消息，特别是@消息
"""

import logging
import re
import difflib
from datetime import datetime
from src.handlers.messages.base_handler import BaseHandler
import os
from src.handlers.emoji import EmojiHandler
from src.handlers.image import ImageHandler

# 获取logger
logger = logging.getLogger('main')

class GroupMessageHandler(BaseHandler):
    """群聊消息处理器，负责处理群聊消息，特别是@消息"""
    
    def __init__(self, message_manager=None):
        """
        初始化群聊消息处理器
        
        Args:
            message_manager: 消息管理器实例的引用
        """
        super().__init__(message_manager)
        # 存储@消息的时间戳
        self.at_message_timestamps = {}  # 格式: {group_id_timestamp: timestamp}
        
        # 直接初始化emoji和image处理器
        self.emoji_handler = None
        self.image_handler = None
        
        # 在首次使用时延迟初始化处理器
        self._init_handlers()
    
    def _init_handlers(self):
        """延迟初始化表情和图片处理器"""
        try:
            # 获取根目录路径
            if hasattr(self.message_manager, 'wx') and hasattr(self.message_manager.wx, 'root_dir'):
                root_dir = self.message_manager.wx.root_dir
            else:
                # 尝试从当前文件路径获取根目录
                current_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            
            # 获取微信实例
            wx_instance = getattr(self.message_manager, 'wx', None)
            
            # 获取API处理器和情感分析器
            api_handler = None
            sentiment_analyzer = None
            if hasattr(self.message_manager, 'api_handler'):
                api_handler = self.message_manager.api_handler
                # 从api_handler获取情感分析器
                sentiment_analyzer = getattr(api_handler, 'sentiment_analyzer', None)
            
            # 初始化表情处理器，直接传入api_handler而不是sentiment_analyzer
            if self.emoji_handler is None:
                try:
                    # 如果api_handler存在，直接使用它进行初始化
                    if api_handler:
                        self.emoji_handler = EmojiHandler(
                            root_dir=root_dir, 
                            wx_instance=wx_instance,
                            sentiment_analyzer=sentiment_analyzer
                        )
                    else:
                        # 没有api_handler时的简单初始化
                        self.emoji_handler = EmojiHandler(root_dir)
                    
                    logger.info("已初始化表情处理器")
                except Exception as e:
                    logger.error(f"初始化表情处理器失败: {str(e)}")
                    self.emoji_handler = None
            
            # 初始化图片处理器，同样直接传入api_handler
            if self.image_handler is None:
                try:
                    # 如果api_handler存在，使用它进行初始化
                    if api_handler:
                        self.image_handler = ImageHandler(root_dir=root_dir)
                    else:
                        # 没有api_handler时的简单初始化
                        self.image_handler = ImageHandler(root_dir)
                    
                    logger.info("已初始化图片处理器")
                except Exception as e:
                    logger.error(f"初始化图片处理器失败: {str(e)}")
                    self.image_handler = None
                    
        except Exception as e:
            logger.error(f"初始化处理器失败: {str(e)}")
    
    def _update_activity(self, group_id, username):
        """更新用户活跃时间
        
        Args:
            group_id: 群聊ID
            username: 用户名
        """
        # 记录最后活跃时间
        if not hasattr(self, '_last_activity'):
            self._last_activity = {}
            
        if group_id not in self._last_activity:
            self._last_activity[group_id] = {}
            
        self._last_activity[group_id][username] = datetime.now()

    def handle_special_request(self, content, group_id, sender_name, username):
        """
        处理特殊请求
        
        Args:
            content: 消息内容
            group_id: 群ID
            sender_name: 发送者名称
            username: 用户名
            
        Returns:
            tuple: (是否特殊请求, 处理结果)
        """
        # 确保处理器已初始化
        if self.emoji_handler is None or self.image_handler is None:
            self._init_handlers()
            
        # 处理表情包请求
        if self.emoji_handler and self.emoji_handler.is_emoji_request(content):
            logger.info("处理群聊表情包请求")
            return self._handle_emoji_request(content, group_id, username)
            
        # 图像生成请求处理
        if self.image_handler and self.image_handler.is_image_generation_request(content):
            logger.info("处理群聊图像生成请求")
            return self._handle_image_generation_request(content, group_id)
            
        # 添加更多特殊请求处理...
            
        return (False, None)
        
    def _handle_emoji_request(self, content, chat_id, username):
        """处理表情包请求"""
        try:
            if not self.emoji_handler:
                return (False, None)
            
            def callback(emoji_path):
                if emoji_path and os.path.exists(emoji_path) and self.message_manager.wx:
                    self.message_manager.wx.SendFiles(emoji_path, chat_id)
                    
            result = self.emoji_handler.get_emotion_emoji(content, username, callback)
            return (True, result)
                
        except Exception as e:
            logger.error(f"处理表情包请求失败: {str(e)}")
            return (False, None)
            
    def _handle_image_generation_request(self, content, chat_id):
        """处理图像生成请求"""
        try:
            if not self.image_handler:
                return (False, None)
                
            image_path = self.image_handler.generate_image(content)
            if image_path and self.message_manager.wx:
                self.message_manager.wx.SendFiles(image_path, chat_id)
                return (True, image_path)
                
            return (False, None)
        except Exception as e:
            logger.error(f"处理图像生成请求失败: {str(e)}")
            return (False, None)
        
    async def handle_message(self, content, group_id, sender_name, username, is_image_recognition=False, **kwargs):
        """
        处理群聊消息
        
        Args:
            content: 消息内容
            group_id: 群ID
            sender_name: 发送者昵称
            username: 用户ID
            is_image_recognition: 是否是图像识别结果
            **kwargs: 其他参数
            
        Returns:
            dict: 处理结果，包含success字段和result或error字段
        """
        try:
            # 提取引用内容和检测@标记
            is_at = kwargs.get('is_at', False)
            
            # 备用检测：如果传入参数为False，再尝试本地检测
            if not is_at:
                is_at_local, at_content = self._detect_at_mention(content)
                is_at = is_at_local
            
            # 清理消息内容
            actual_content = self._clean_message_content(content)
            logger.info(f"收到群聊消息: {actual_content}")
            
            # 提取引用内容
            actual_content, quoted_sender, quoted_content = self._extract_quoted_content(actual_content)
            
            # 记录最后活跃时间
            self._update_activity(group_id, username)
            
            # 检查是否是特殊请求
            is_special, special_result = self.handle_special_request(actual_content, group_id, sender_name, username)
            if is_special:
                return {"success": True, "result": special_result}

            # 保存所有群聊消息到群聊记忆，不论是否@
            if hasattr(self.message_manager, 'group_chat_memory') and self.message_manager.group_chat_memory:
                timestamp = self.message_manager.group_chat_memory.add_message(
                    group_id, sender_name, actual_content, is_at
                )
                logger.debug(f"消息已保存到群聊记忆: {group_id}, 时间戳: {timestamp}")
                
                # 如果是@消息，记录时间戳
                if is_at:
                    self.at_message_timestamps[f"{group_id}_{timestamp}"] = timestamp
                    
            # 如果是@消息，交给队列管理器处理
            if is_at:
                logger.info(f"检测到@消息: {actual_content}, 发送者: {sender_name}")
                
                if hasattr(self.message_manager, 'queue_manager'):
                    # 构建消息对象
                    message_obj = {
                        'content': actual_content,
                        'group_id': group_id,
                        'sender_name': sender_name,
                        'username': username,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'quoted_sender': quoted_sender,
                        'quoted_content': quoted_content
                    }
                    
                    # 缓存消息并设置处理
                    self.message_manager.queue_manager.cache_group_at_message(message_obj, group_id)
                    return {"success": True, "result": "消息已加入处理队列"}
                else:
                    # 如果没有队列管理器，直接处理
                    result = await self.handle_at_message(
                        actual_content, 
                        group_id, 
                        sender_name, 
                        username, 
                        quoted_sender, 
                        quoted_content
                    )
                    return {"success": True, "result": result}
            
            return {"success": True, "result": None}
            
        except Exception as e:
            logger.error(f"处理群聊消息失败: {str(e)}")
            return {"success": False, "error": str(e), "result": None}
    
    async def process_at_message(self, message_obj):
        """
        处理@消息
        
        Args:
            message_obj: 消息对象
            
        Returns:
            str: 处理结果
        """
        try:
            result = await self.handle_at_message(
                message_obj['content'],
                message_obj['group_id'],
                message_obj['sender_name'],
                message_obj['username'],
                message_obj.get('quoted_sender'),
                message_obj.get('quoted_content'),
                message_obj.get('timestamp')
            )
            return result
        except Exception as e:
            logger.error(f"处理@消息失败: {str(e)}")
            return f"处理消息时发生错误: {str(e)}"
    
    async def handle_at_message(self, content, group_id, sender_name, username, quoted_sender=None, quoted_content=None, timestamp=None):
        """
        公开方法，处理@消息
        
        Args:
            content: 消息内容
            group_id: 群ID
            sender_name: 发送者昵称
            username: 用户ID
            quoted_sender: 引用消息的发送者
            quoted_content: 引用消息的内容
            timestamp: 消息时间戳，如果为None则使用当前时间
            
        Returns:
            str: 处理结果
        """
        try:
            # 记录实际的@消息发送者信息
            logger.info(f"处理@消息 - 群ID: {group_id}, 发送者: {sender_name}, 用户ID: {username}")
            
            # 如果提供了引用内容但没有引用发送者，构建完整的引用信息
            if quoted_content and not quoted_sender:
                quoted_sender = "某人"
                
            # 如果提供了引用信息，添加到当前消息的上下文中
            if quoted_content and quoted_sender:
                logger.info(f"检测到引用消息 - 引用者: {quoted_sender}, 内容: {quoted_content}")
                
                # 将引用内容添加到当前消息的上下文中
                enriched_content = f"(引用消息: {quoted_sender} 说: {quoted_content})\n{content}"
                content = enriched_content
                
                # 如果引用内容为空，尝试从群聊记忆中获取
                if not quoted_content and hasattr(self.message_manager, 'group_chat_memory'):
                    # 获取引用消息的上下文
                    quoted_context = self.message_manager.group_chat_memory.get_message_by_content(group_id, quoted_content)
                    if quoted_context:
                        logger.info(f"找到引用消息的上下文: {quoted_context}")
                        # 将引用内容添加到当前消息的上下文中
                        content = f"(引用消息: {quoted_sender} 说: {quoted_context.get('human_message', '')})\n{content}"
            
            # 获取当前时间
            current_time = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 获取上下文消息
            context_messages = []
            if hasattr(self.message_manager, 'memory_manager'):
                # 使用记忆管理器获取上下文
                try:
                    memory_manager = self.message_manager.get_module('memory_manager')
                    if memory_manager:
                        # 直接使用await调用异步方法
                        memories = await memory_manager.get_relevant_memories(
                            f"群聊 {group_id} 最近的对话 {content}",
                            username,
                            5  # 获取5条相关记忆
                        )
                        
                        # 格式化记忆为上下文
                        context_parts = []
                        for memory in memories:
                            user_msg = memory.get('message', '')
                            ai_msg = memory.get('reply', '')
                            if user_msg:
                                context_parts.append(f"用户: {user_msg}")
                            if ai_msg:
                                robot_name = self.message_manager.robot_name if self.message_manager else 'AI'
                                context_parts.append(f"{robot_name}: {ai_msg}")
                        
                        context = "<context>" + "\n".join(context_parts) + "</context>" if context_parts else ""
                        logger.info(f"从记忆管理器获取了 {len(memories)} 条相关记忆作为上下文")
                    else:
                        context = ""
                except Exception as e:
                    logger.error(f"从记忆管理器获取上下文失败: {str(e)}")
                    context = ""
            elif hasattr(self.message_manager, 'group_chat_memory'):
                # 直接从群聊记忆中获取上下文
                raw_messages = self.message_manager.group_chat_memory.get_context_messages(group_id, current_time)
                
                # 过滤和格式化上下文
                context_parts = []
                for msg in raw_messages:
                    sender_display = msg.get('sender_name', 'Unknown')
                    human_message = self._clean_memory_content(msg.get('human_message', ''))
                    assistant_message = self._clean_memory_content(msg.get('assistant_message', ''))
                    
                    if human_message:
                        context_parts.append(f"{sender_display}: {human_message}")
                        if assistant_message:
                            robot_name = self.message_manager.robot_name if self.message_manager else 'AI'
                            context_parts.append(f"{robot_name}: {assistant_message}")
                
                context = "<context>" + "\n".join(context_parts) + "</context>" if context_parts else ""
            else:
                context = ""
            
            # 格式化消息
            if hasattr(self.message_manager, 'preprocessor'):
                # 使用预处理器格式化消息
                formatted_content = self.message_manager.preprocessor.format_group_message(
                    content, 
                    group_id, 
                    sender_name, 
                    context
                )
            else:
                # 简单格式化
                formatted_content = f"<time>{current_time}</time>\n<group>{group_id}</group>\n<sender>{sender_name}</sender>\n"
                if context:
                    formatted_content += f"{context}\n"
                formatted_content += f"<input>{content}</input>"
            
            # 获取AI回复
            reply = await self.message_manager.get_api_response(formatted_content, username)
            
            # 如果成功获取回复
            if reply:
                # 清理回复内容
                # 如果回复是一个元组(success, message)，提取message部分
                if isinstance(reply, tuple) and len(reply) == 2:
                    reply = reply[1]
                
                reply = self._clean_ai_response(reply)
                
                # 在回复中显式提及发送者，确保回复的是正确的人
                if not reply.startswith(f"@{sender_name}"):
                    reply = f"@{sender_name} {reply}"
                
                # 发送消息
                if not self.message_manager.is_debug:
                    if hasattr(self.message_manager, 'postprocessor'):
                        # 使用后处理器分割和发送消息
                        split_messages = self.message_manager.postprocessor.split_message_for_sending(reply)
                        self.message_manager.postprocessor.send_split_messages(
                            split_messages, 
                            group_id, 
                            sender_name, 
                            True  # 是群聊
                        )
                    else:
                        # 简单发送
                        self._safe_send_msg(reply, group_id)
                
                # 更新群聊记忆
                if hasattr(self.message_manager, 'group_chat_memory'):
                    memory_content = None
                    if hasattr(self.message_manager, 'postprocessor'):
                        split_messages = self.message_manager.postprocessor.split_message_for_sending(reply)
                        if isinstance(split_messages, dict) and split_messages.get('memory_content'):
                            memory_content = split_messages.get('memory_content')
                    
                    if not memory_content:
                        # 如果没有memory_content字段，则使用过滤动作和表情后的回复
                        memory_content = self._filter_action_emotion(reply)
                        
                    # 更新群聊记忆
                    self.message_manager.group_chat_memory.update_assistant_response(
                        group_id, current_time, memory_content
                    )
                
                # 如果有记忆管理器，存储对话记忆
                if hasattr(self.message_manager, 'memory_manager'):
                    try:
                        # 获取memory_manager模块
                        memory_manager = self.message_manager.get_module('memory_manager')
                        if memory_manager:
                            # 使用记忆管理器存储记忆
                            await memory_manager.remember(
                                content,       # 用户消息
                                reply,        # 助手回复
                                f"{username}_群_{group_id}"  # 用户ID_群ID组合作为唯一标识
                            )
                            logger.info(f"异步存储群聊对话记忆 - 用户: {username}, 群: {group_id}")
                    except Exception as memory_e:
                        logger.error(f"存储群聊对话记忆失败: {str(memory_e)}")
                
                return reply
            
            return None
            
        except Exception as e:
            logger.error(f"处理@消息失败: {str(e)}")
            return None

    def _detect_at_mention(self, content):
        """
        检测消息中是否@机器人
        
        Args:
            content: 消息内容
            
        Returns:
            tuple: (是否@机器人, @内容)
        """
        if not self.message_manager or not hasattr(self.message_manager, 'robot_name'):
            return False, ""
            
        robot_name = self.message_manager.robot_name
        
        # 改进@机器人检测逻辑 - 使用更全面的模式匹配
        # 常见的空格字符：普通空格、不间断空格、零宽空格、特殊的微信空格等
        
        # 检查完整的正则模式
        # 允许@后面的名称部分有一些小的变化（比如有些空格字符可能会被替换）
        robot_name_pattern = re.escape(robot_name).replace('\\ ', '[ \u2005\u00A0\u200B\u3000]*')
        at_pattern = re.compile(f"@{robot_name_pattern}[\\s\u2005\u00A0\u200B\u3000]?")
        is_at = bool(at_pattern.search(content))
        
        # 检查完整的模式列表
        if not is_at:
            robot_at_patterns = [
                f"@{robot_name}",  # 基本@模式
                f"@{robot_name} ",  # 普通空格
                f"@{robot_name}\u2005",  # 特殊的微信空格
                f"@{robot_name}\u00A0",  # 不间断空格
                f"@{robot_name}\u200B",  # 零宽空格
                f"@{robot_name}\u3000"   # 全角空格
            ]
            is_at = any(pattern in content for pattern in robot_at_patterns)
            
        # 额外检查@开头的消息
        if not is_at and content.startswith('@'):
            # 提取@后面的第一个词，检查是否接近机器人名称
            at_name_match = re.match(r'@([^ \u2005\u00A0\u200B\u3000]+)', content)
            if at_name_match:
                at_name = at_name_match.group(1)
                # 检查名称相似度（允许一些小的变化）
                similarity_ratio = difflib.SequenceMatcher(None, at_name, robot_name).ratio()
                if similarity_ratio > 0.8:  # 80%相似度作为阈值
                    is_at = True
                    logger.info(f"基于名称相似度检测到@机器人: {at_name} vs {robot_name}, 相似度: {similarity_ratio:.2f}")
        
        # 提取原始@部分
        at_match = re.search(f"(@{re.escape(robot_name)}[\\s\u2005\u00A0\u200B\u3000]?)", content)
        at_content = at_match.group(1) if at_match else ''
        
        return is_at, at_content
    
    def _extract_quoted_content(self, content):
        """
        提取引用内容
        
        Args:
            content: 消息内容
            
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

    def _filter_action_emotion(self, text):
        """
        过滤文本中的动作表情标签
        
        Args:
            text: 输入文本
            
        Returns:
            str: 过滤后的文本
        """
        if not text:
            return ""
            
        # 过滤动作标签 [动作:xxx] 或 (动作:xxx)
        text = re.sub(r'[\[\(]动作:[^\]\)]*[\]\)]', '', text)
        
        # 过滤表情标签 [表情:xxx] 或 (表情:xxx)
        text = re.sub(r'[\[\(]表情:[^\]\)]*[\]\)]', '', text)
        
        return text
    
    def _clean_ai_response(self, response):
        """
        清理AI回复内容，移除不需要的格式标签和前缀
        
        Args:
            response: AI回复内容
            
        Returns:
            str: 清理后的回复内容
        """
        if not response:
            return ""
        
        # 去除可能的前缀内容
        prefixes_to_remove = [
            r"^AI[:：]",
            r"^机器人[:：]",
            r"^助手[:：]",
            r"^回复[:：]",
            r"^Reply[:：]"
        ]
        
        for prefix in prefixes_to_remove:
            response = re.sub(prefix, "", response, flags=re.IGNORECASE)
        
        # 去除XML/HTML标签
        response = re.sub(r'<[^>]+>', '', response)
        
        # 去除前后空白
        response = response.strip()
        
        return response
    
    def _safe_send_msg(self, msg, to_user):
        """安全发送消息，处理可能的异常"""
        try:
            if hasattr(self.message_manager, 'wx') and self.message_manager.wx:
                self.message_manager.wx.SendMsg(msg, to_user)
            else:
                logger.warning(f"无法发送消息，微信实例不可用: {msg[:30]}...")
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
    
    def _clean_memory_content(self, content):
        """清理记忆内容，移除特殊标记和格式"""
        if not content:
            return ""
            
        # 移除特殊标记和格式
        # 移除XML/HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 移除动作和表情标签
        content = self._filter_action_emotion(content)
        
        # 去除前后空白
        content = content.strip()
        
        return content

if __name__ == "__main__":
    import asyncio
    import logging
    from datetime import datetime
    
    # 配置基本日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('test')
    
    class MockWX:
        """模拟微信接口"""
        def __init__(self):
            self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
            
        def SendMsg(self, msg, who=None):
            print(f"发送群聊消息到 {who}: {msg}")
            return True
            
        def SendFiles(self, filepath, who=None):
            print(f"发送文件 {filepath} 到 {who}")
            return True
            
        def __len__(self):
            """实现len方法，防止类型错误"""
            return 1
    
    class MockMemoryManager:
        """模拟内存管理器"""
        def __init__(self):
            pass
            
        async def get_relevant_memories(self, query, user_id, limit=5):
            print(f"获取相关记忆: {query[:30]}...")
            return []
            
        async def remember(self, user_message, ai_message, user_id):
            print(f"记忆对话: 用户ID: {user_id}")
            return True
    
    class MockAPIHandler:
        """模拟API处理器"""
        def __init__(self):
            pass
            
        async def get_response(self, prompt, user_id=None):
            print(f"API请求: {prompt[:50]}...")
            return f"这是对群聊消息的回复: {prompt[:20]}..."
    
    class MockMessageManager:
        """模拟MessageManager类"""
        def __init__(self):
            self.wx = MockWX()
            self.is_debug = False
            self.robot_name = "测试机器人"
            self.api_handler = MockAPIHandler()
            
        def get_module(self, name):
            if name == 'memory_manager':
                return MockMemoryManager()
            elif name == 'api_handler':
                return self.api_handler
            return None
            
        async def get_api_response(self, content, username=None):
            """使用API处理器获取响应"""
            try:
                api_handler = self.get_module('api_handler')
                if api_handler:
                    response = await api_handler.get_response(content, username)
                    return response
                else:
                    logger.warning("未找到API处理器，返回默认响应")
                    return "API处理器不可用，这是默认响应"
            except Exception as e:
                logger.error(f"获取API响应失败: {str(e)}")
                return f"错误: {str(e)}"
    
    async def test_group_handler():
        print("开始测试群聊处理器...")
        
        # 创建模拟对象
        manager = MockMessageManager()
        handler = GroupMessageHandler(manager)
        
        # 测试handle_message方法
        test_messages = [
            "普通群聊消息",
            "@测试机器人 你好",
            "#命令测试"
        ]
        
        for msg in test_messages:
            result = await handler.handle_message(
                content=msg,
                group_id="test_group",
                sender_name="群成员",
                username="group_user"
            )
            print(f"群聊消息: {msg}")
            print(f"处理结果: {result}")
            print("---")
        
        # 测试handle_at_message方法
        at_messages = [
            "你好，机器人",
            "请回答一个问题",
            "群聊中@你"
        ]
        
        for msg in at_messages:
            result = await handler.handle_at_message(
                content=msg,
                group_id="test_group",
                sender_name="群成员",
                username="group_user",
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            print(f"@消息: {msg}")
            print(f"处理结果: {result}")
            print("---")
        
        # 测试特殊请求处理
        if hasattr(handler, 'handle_special_request'):
            special_result = handler.handle_special_request(
                "生成语音：群聊测试", "test_group", "群成员", "group_user"
            )
            print(f"群聊特殊请求处理结果: {special_result}")
        
        print("群聊处理器测试完成")
    
    # 运行测试
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_group_handler()) 
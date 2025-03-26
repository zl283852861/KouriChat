"""
私聊消息处理模块
负责处理一对一聊天消息
"""

import logging
from datetime import datetime
from src.handlers.messages.base_handler import BaseHandler
import asyncio
import os

# 获取logger
logger = logging.getLogger('main')

class PrivateMessageHandler(BaseHandler):
    """私聊消息处理器，负责处理一对一聊天消息"""
    
    def __init__(self, message_manager=None):
        """
        初始化私聊消息处理器
        
        Args:
            message_manager: 消息管理器实例的引用
        """
        super().__init__(message_manager)
        # 最后活跃时间记录
        self._last_message_times = {}
    
    async def handle_message(self, content, chat_id, sender_name, username, is_image_recognition=False, is_self_message=False):
        """
        处理私聊消息
        
        Args:
            content: 消息内容
            chat_id: 聊天ID
            sender_name: 发送者昵称
            username: 用户ID
            is_image_recognition: 是否是图像识别结果
            is_self_message: 是否是自己发送的消息
            
        Returns:
            dict: 处理结果，包含success字段和result或error字段
        """
        try:
            # 验证并修正用户ID
            if not username or username == "System":
                username = chat_id.split('@')[0] if '@' in chat_id else chat_id
                if username == "filehelper":
                    username = "FileHelper"
                sender_name = sender_name or username

            # 清理消息内容
            actual_content = self._clean_message_content(content)
            logger.info(f"收到私聊消息: {actual_content}")
            
            # 记录最后活跃时间
            self._last_message_times[username] = datetime.now()

            # 如果是自己发送的消息，进行特殊处理
            if is_self_message:
                return {"success": True, "result": None}

            # 处理特殊请求
            is_special, special_result = self.handle_special_request(actual_content, chat_id, sender_name, username)
            if is_special:
                return {"success": True, "result": special_result}

            # 对于普通消息，使用标准API请求
            try:
                # 获取对话上下文
                context = ""
                if hasattr(self.message_manager, 'memory_manager') and self.message_manager.get_module('memory_manager'):
                    memory_manager = self.message_manager.get_module('memory_manager')
                    # 检查是否有异步的get_relevant_memories方法
                    if hasattr(memory_manager, 'get_relevant_memories'):
                        try:
                            # 直接使用await调用异步方法
                            memories = await memory_manager.get_relevant_memories(username, actual_content, limit=5)
                            if memories:
                                memory_texts = []
                                for memory in memories:
                                    if 'user_message' in memory and 'ai_message' in memory:
                                        memory_texts.append(f"用户: {memory['user_message']}")
                                        memory_texts.append(f"AI: {memory['ai_message']}")
                                if memory_texts:
                                    context = "<context>\n" + "\n".join(memory_texts) + "\n</context>"
                                    logger.info(f"获取到 {len(memories)} 条相关记忆")
                        except Exception as e:
                            logger.error(f"获取相关记忆失败: {str(e)}")
                    elif hasattr(memory_manager, 'get_conversation_context'):
                        # 使用旧方法获取上下文
                        context = memory_manager.get_conversation_context(username)
                
                # 格式化消息
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if context:
                    formatted_content = f"{context}\n\n(以上是历史对话内容，仅供参考，无需进行互动。请专注处理接下来的新内容)\n\n[{current_time}] ta私聊对你说：{actual_content}"
                else:
                    formatted_content = f"[{current_time}] ta私聊对你说：{actual_content}"
                
                # 获取API响应
                success, response = await self.message_manager.get_api_response(formatted_content, username)
                if not success:
                    logger.error(f"获取API响应失败: {response.get('error', '未知错误')}")
                    return {"success": False, "error": response.get('error', '获取响应失败'), "result": None}
                
                # 存储对话记忆
                try:
                    memory_manager = self.message_manager.get_module('memory_manager')
                    if memory_manager:
                        asyncio.create_task(memory_manager.remember(
                            actual_content,  # 用户消息
                            response,        # 助手回复
                            username         # 用户ID
                        ))
                        logger.info(f"异步存储对话记忆 - 用户: {username}")
                except Exception as memory_e:
                    logger.error(f"存储对话记忆失败: {str(memory_e)}")
                
                return {"success": True, "result": response}
            except Exception as api_e:
                logger.error(f"处理API请求时出错: {str(api_e)}")
                return {"success": False, "error": str(api_e), "result": None}
            
        except Exception as e:
            logger.error(f"处理私聊消息失败: {str(e)}")
            return {"success": False, "error": str(e), "result": None}
            
    async def process_cached_messages(self, username, messages):
        """
        处理缓存的私聊消息
        
        Args:
            username: 用户ID
            messages: 消息列表
            
        Returns:
            str: 处理结果，如果需要回复则返回回复内容，否则返回None
        """
        try:
            if not messages:
                return None
                
            # 按时间排序消息
            messages.sort(key=lambda x: x.get('timestamp', 0))
            
            # 获取最近的对话记录作为上下文
            context = ""
            if hasattr(self.message_manager, 'memory_manager'):
                memory_manager = self.message_manager.get_module('memory_manager')
                if memory_manager:
                    if hasattr(memory_manager, 'get_conversation_context'):
                        context = memory_manager.get_conversation_context(username)
            
            # 合并消息内容
            first_message = messages[0]
            last_message = messages[-1]
            
            # 使用预处理器合并消息
            if hasattr(self.message_manager, 'preprocessor'):
                preprocessor = self.message_manager.get_module('preprocessor')
                if preprocessor:
                    merged_content = await preprocessor.merge_messages(messages)
                    # 格式化合并后的消息
                    formatted_content = await preprocessor.format_private_message(
                        merged_content, 
                        username, 
                        context
                    )
                else:
                    # 简单合并消息
                    contents = [self._clean_message_content(msg.get('content', '')) for msg in messages]
                    merged_content = ' $ '.join([c for c in contents if c])
                    
                    # 格式化消息
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if context:
                        formatted_content = f"{context}\n\n(以上是历史对话内容，仅供参考，无需进行互动。请专注处理接下来的新内容)\n\n[{current_time}] ta私聊对你说：{merged_content}"
                    else:
                        formatted_content = f"[{current_time}] ta私聊对你说：{merged_content}"
            else:
                # 简单合并消息
                contents = [self._clean_message_content(msg.get('content', '')) for msg in messages]
                merged_content = ' $ '.join([c for c in contents if c])
                
                # 格式化消息
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if context:
                    formatted_content = f"{context}\n\n(以上是历史对话内容，仅供参考，无需进行互动。请专注处理接下来的新内容)\n\n[{current_time}] ta私聊对你说：{merged_content}"
                else:
                    formatted_content = f"[{current_time}] ta私聊对你说：{merged_content}"
            
            # 调用消息管理器获取API响应
            success, response = await self.message_manager.get_api_response(formatted_content, username)
            
            # 处理响应并发送
            if success and response and not self.message_manager.is_debug:
                # 处理回复，添加$和￥分隔符，过滤标点符号
                postprocessor = self.message_manager.get_module('postprocessor')
                if postprocessor:
                    # 使用后处理器处理回复
                    split_messages = await postprocessor.split_message_for_sending(response)
                    await postprocessor.send_split_messages(split_messages, last_message['chat_id'])
                else:
                    # 简单发送回复
                    await self._safe_send_msg(response, last_message['chat_id'])
                
                # 如果有记忆处理器，存储对话记忆
                memory_manager = self.message_manager.get_module('memory_manager')
                if memory_manager:
                    try:
                        # 使用memory_manager存储记忆
                        asyncio.create_task(memory_manager.remember(
                            merged_content,  # 用户消息
                            response,        # 助手回复
                            username         # 用户ID
                        ))
                        logger.info(f"异步存储缓存消息对话记忆 - 用户: {username}")
                    except Exception as memory_e:
                        logger.error(f"存储缓存消息对话记忆失败: {str(memory_e)}")
            
            return response if success else None
            
        except Exception as e:
            logger.error(f"处理缓存消息失败: {str(e)}")
            return None
    
    def handle_special_request(self, content, chat_id, sender_name, username):
        """
        处理特殊请求，如语音生成、图片生成等
        
        Args:
            content: 消息内容
            chat_id: 聊天ID
            sender_name: 发送者昵称
            username: 用户ID
            
        Returns:
            tuple: (是否是特殊请求, 处理结果)
        """
        # 语音请求处理
        if hasattr(self.message_manager, 'voice_handler') and \
           self.message_manager.voice_handler and \
           "生成语音" in content:
            logger.info("处理语音请求")
            return self._handle_voice_request(content, chat_id)
        
        # 随机图片请求处理
        if hasattr(self.message_manager, 'image_handler') and \
           self.message_manager.image_handler and \
           self.message_manager.image_handler.is_random_image_request(content):
            logger.info("处理随机图片请求")
            return self._handle_random_image_request(content, chat_id)
            
        # 图像生成请求处理
        if hasattr(self.message_manager, 'image_handler') and \
           self.message_manager.image_handler and \
           self.message_manager.image_handler.is_image_generation_request(content):
            logger.info("处理图像生成请求")
            return self._handle_image_generation_request(content, chat_id)
        
        # 表情包请求处理
        if hasattr(self.message_manager, 'emoji_handler') and \
           self.message_manager.emoji_handler and \
           self.message_manager.emoji_handler.is_emoji_request(content):
            logger.info("处理表情包请求")
            return self._handle_emoji_request(content, chat_id, username)
            
        return (False, None)
    
    def _handle_voice_request(self, content, chat_id):
        """
        处理语音生成请求
        
        Args:
            content: 消息内容
            chat_id: 聊天ID
            
        Returns:
            tuple: (是否处理成功, 处理结果)
        """
        voice_handler = self.message_manager.voice_handler
        wx = self.message_manager.wx
        
        reply = self.message_manager.get_api_response(content, chat_id)
        if "</think>" in reply:
            reply = reply.split("</think>", 1)[1].strip()

        voice_path = voice_handler.generate_voice(reply)
        if voice_path:
            try:
                wx.SendFiles(filepath=voice_path, who=chat_id)
                return (True, reply)
            except Exception as e:
                logger.error(f"发送语音失败: {str(e)}")
                wx.SendMsg(msg=reply, who=chat_id)
                return (True, reply)
        else:
            wx.SendMsg(msg=reply, who=chat_id)
            return (True, reply)
    
    def _handle_random_image_request(self, content, chat_id):
        """
        处理随机图片请求
        
        Args:
            content: 消息内容
            chat_id: 聊天ID
            
        Returns:
            tuple: (是否处理成功, 处理结果)
        """
        image_handler = self.message_manager.image_handler
        wx = self.message_manager.wx
        
        image_path = image_handler.get_random_image()
        if image_path:
            try:
                wx.SendFiles(filepath=image_path, who=chat_id)
                reply = "给主人你找了一张好看的图片哦~"
                wx.SendMsg(msg=reply, who=chat_id)
                return (True, reply)
            except Exception as e:
                logger.error(f"发送图片失败: {str(e)}")
                reply = "抱歉主人，图片发送失败了..."
                wx.SendMsg(msg=reply, who=chat_id)
                return (True, reply)
        return (False, None)
    
    def _handle_image_generation_request(self, content, chat_id):
        """
        处理图像生成请求
        
        Args:
            content: 消息内容
            chat_id: 聊天ID
            
        Returns:
            tuple: (是否处理成功, 处理结果)
        """
        image_handler = self.message_manager.image_handler
        wx = self.message_manager.wx
        
        image_path = image_handler.generate_image(content)
        if image_path:
            try:
                wx.SendFiles(filepath=image_path, who=chat_id)
                reply = "这是按照主人您的要求生成的图片\\(^o^)/~"
                wx.SendMsg(msg=reply, who=chat_id)
                return (True, reply)
            except Exception as e:
                logger.error(f"发送生成图片失败: {str(e)}")
                reply = "抱歉主人，图片生成失败了..."
                wx.SendMsg(msg=reply, who=chat_id)
                return (True, reply)
        return (False, None)
    
    def _handle_emoji_request(self, content, chat_id, username):
        """
        处理表情包请求
        
        Args:
            content: 消息内容
            chat_id: 聊天ID
            username: 用户ID
            
        Returns:
            tuple: (是否处理成功, 处理结果)
        """
        emoji_handler = self.message_manager.emoji_handler
        wx = self.message_manager.wx
        
        def callback(emoji_path):
            try:
                if emoji_path and os.path.exists(emoji_path):
                    logger.info(f"找到表情包: {emoji_path}")
                    # 发送表情包
                    if not self.message_manager.is_debug:
                        wx.SendFiles(filepath=emoji_path, who=chat_id)
            except Exception as e:
                logger.error(f"处理表情包回调时出错: {str(e)}")
        
        result = emoji_handler.get_emotion_emoji(content, username, callback)
        return (True, result)

if __name__ == "__main__":
    import asyncio
    import logging
    from datetime import datetime
    
    # 配置基本日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('test')
    
    class MockMessageManager:
        """模拟MessageManager类"""
        def __init__(self):
            self.wx = None
            self.voice_handler = None
            self.image_handler = None
            self.emoji_handler = None
            self.is_debug = False
            
        def get_module(self, name):
            return None
            
        async def get_api_response(self, content, username=None):
            """模拟API响应"""
            logger.info(f"模拟API调用: {content[:50]}...")
            return True, f"这是对消息 '{content[:20]}...' 的模拟回复"
    
    async def test_private_handler():
        print("开始测试私聊消息处理器...")
        
        # 创建模拟对象
        manager = MockMessageManager()
        handler = PrivateMessageHandler(manager)
        
        # 测试handle_message方法
        test_messages = [
            "你好，这是测试消息",
            "测试特殊字符 @#$%^&*()",
            "#命令测试"
        ]
        
        for msg in test_messages:
            result = await handler.handle_message(
                content=msg,
                chat_id="test_user",
                sender_name="测试用户",
                username="test_user"
            )
            print(f"原始消息: {msg}")
            print(f"处理结果: {result}")
            print("---")
        
        # 测试process_cached_messages方法
        cached_messages = [
            {"content": "第一条消息", "timestamp": 1, "chat_id": "test_user"},
            {"content": "第二条消息", "timestamp": 2, "chat_id": "test_user"},
            {"content": "第三条消息", "timestamp": 3, "chat_id": "test_user"}
        ]
        
        response = await handler.process_cached_messages("test_user", cached_messages)
        print(f"缓存消息处理结果: {response}")
        
        # 测试特殊请求处理（简单模拟）
        special_result = handler.handle_special_request(
            "生成语音：你好，世界", "test_user", "测试用户", "test_user"
        )
        print(f"特殊请求处理结果: {special_result}")
        
        print("私聊消息处理器测试完成")
    
    # 运行测试
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_private_handler()) 
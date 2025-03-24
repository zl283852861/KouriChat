"""
消息处理模块
负责处理聊天消息，包括:
- 消息队列管理
- 消息分发处理
- API响应处理
- 多媒体消息处理
- 对话结束处理
"""

from datetime import datetime
import logging
import threading
import time
from wxauto import WeChat
import random
import os
from src.services.ai.llm_service import LLMService
from src.config import config
import re
import jieba
import asyncio

# 修改logger获取方式，确保与main模块一致
logger = logging.getLogger('main')


class MessageHandler:
    def __init__(self, root_dir, llm: LLMService, robot_name, prompt_content, image_handler, emoji_handler, voice_handler, memory_handler, wx=None, is_debug=False, is_qq=False):
        self.root_dir = root_dir
        self.robot_name = robot_name
        self.prompt_content = prompt_content
        self.debug = is_debug
        # 添加消息缓存相关属性
        self.message_cache = {}  # 用户消息缓存
        self.last_message_time = {}  # 用户最后发送消息的时间
        self.message_timer = {}  # 用户消息处理定时器
        # 使用 DeepSeekAI 替换直接的 OpenAI 客户端
        self.deepseek = llm
        # 消息队列相关
        self.user_queues = {}
        self.queue_lock = threading.Lock()
        self.chat_contexts = {}

        # 微信实例
        self.wx = wx
        self.is_debug = is_debug
        self.is_qq = is_qq

        # 添加 handlers
        self.image_handler = image_handler
        self.emoji_handler = emoji_handler
        self.voice_handler = voice_handler
        self.memory_handler = memory_handler
        
        # 从配置文件获取角色名称
        try:
            # 导入所需的类
            from src.handlers.memories.group_chat_memory import GroupChatMemory
            from src.config import config
            
            # 从 AVATAR_DIR 获取角色名称
            avatar_dir = config.behavior.context.avatar_dir
            if not avatar_dir:
                logger.warning("未找到角色目录配置，使用默认名称")
                avatar_name = "default"
            else:
                # 获取目录的最后一部分作为角色名称
                avatar_name = os.path.basename(avatar_dir)
                
            # 清理角色名称，只保留有效字符
            safe_avatar_name = "".join(c for c in avatar_name if c.isalnum() or c in (' ', '-', '_'))
            if not safe_avatar_name:
                safe_avatar_name = "default"
                
            # 从配置文件中获取监听列表
            try:
                # 尝试通过属性方式访问
                try:
                    listen_list = config.categories.user_settings.settings.listen_list.value
                except AttributeError:
                    # 备选方案：当属性访问失败时，尝试字典方式访问
                    listen_list = config.categories.get("user_settings", {}).get("settings", {}).get("listen_list", {}).get("value", [])
                
                if not listen_list:
                    logger.warning("配置文件中的 listen_list 为空，使用空列表")
                    listen_list = []
                else:
                    logger.info(f"从配置文件读取到监听列表: {listen_list}")
            except Exception as e:
                logger.warning(f"无法从配置文件读取 listen_list: {str(e)}，使用空列表")
                listen_list = []
            
            group_chats = []
            
            # 如果有微信实例，检查每个监听对象是否为群聊
            if wx and listen_list:
                for chat_id in listen_list:
                    try:
                        # 使用微信API检查是否为群聊
                        if wx.GetWeChatWindow(chat_id):
                            is_group = wx.IsGroupChat(chat_id)
                            if is_group:
                                group_chats.append(chat_id)
                                logger.info(f"识别到群聊: {chat_id}")
                    except Exception as e:
                        logger.error(f"检查群聊状态失败: {chat_id}, 错误: {str(e)}")
            
            # 添加群聊记忆处理器
            self.group_chat_memory = GroupChatMemory(
                root_dir=root_dir,
                avatar_name=safe_avatar_name,
                group_chats=group_chats,  # 传入已识别的群聊列表
                api_wrapper=memory_handler.api_wrapper if hasattr(memory_handler, 'api_wrapper') and memory_handler is not None else None
            )
            
        except Exception as e:
            logger.error(f"初始化群聊记忆失败: {str(e)}")
            # 导入 GroupChatMemory 类（确保在这里也能访问到）
            from src.handlers.memories.group_chat_memory import GroupChatMemory
            # 使用默认值初始化
            self.group_chat_memory = GroupChatMemory(
                root_dir=root_dir, 
                avatar_name="default", 
                group_chats=[],
                api_wrapper=memory_handler.api_wrapper if hasattr(memory_handler, 'api_wrapper') else None
            )
        
        # 添加群聊消息处理队列
        self.group_message_queues = {}
        self.group_queue_lock = threading.Lock()
        self.at_message_timestamps = {}  # 存储@消息的时间戳
        
        self.unanswered_counters = {}
        self.unanswered_timers = {}
        self.MAX_MESSAGE_LENGTH = 500

    def get_api_response(self, message: str, user_id: str, group_id: str = None, sender_name: str = None) -> str:
        """获取API回复"""
        try:
            # 使用正确的属性名和方法名
            if not hasattr(self, 'deepseek') or self.deepseek is None:
                logger.error("LLM服务未初始化，无法生成回复")
                return "系统错误：LLM服务未初始化"
            
            # 使用正确的属性名称调用方法
            try:
                # 修改：检查URL末尾是否有斜杠，并记录日志
                if hasattr(self.deepseek.llm, 'url') and self.deepseek.llm.url.endswith('/'):
                    # 尝试在本地临时修复URL
                    fixed_url = self.deepseek.llm.url.rstrip('/')
                    self.deepseek.llm.url = fixed_url
                
                # 调用API获取响应
                response = self.deepseek.llm.handel_prompt(message, user_id)
                
                # 简化API响应日志，只记录响应长度
                if response:
                    response_length = len(response)
                    # 只记录一次响应长度，避免重复日志
                    logger.info(f"API响应: {response_length}字符")
                else:
                    logger.error("收到空响应")
                
                # 增加异常检测，避免将错误信息存入记忆
                if response and (
                    "API调用失败" in response or 
                    "Connection error" in response or
                    "服务暂时不可用" in response or
                    "Error:" in response or
                    "错误:" in response or
                    "认证错误" in response
                ):
                    logger.error(f"API调用返回错误: {response}")
                    
                    # 增加错误类型的分类
                    if "Connection error" in response or "连接错误" in response:
                        logger.error("网络连接错误 - 请检查网络连接和API地址配置")
                        return f"抱歉，我暂时无法连接到API服务器。请检查网络连接和API地址配置。"
                    
                    elif "认证错误" in response or "API密钥" in response:
                        logger.error("API认证错误 - 请检查API密钥是否正确")
                        return f"抱歉，API认证失败。请检查API密钥配置。"
                    
                    elif "模型" in response and ("错误" in response or "不存在" in response):
                        logger.error("模型错误 - 模型名称可能不正确或不可用")
                        return f"抱歉，无法使用指定的AI模型。请检查模型名称配置。"
                    
                    else:
                        return f"抱歉，我暂时无法回应。错误信息：{response}"
                    
                return response
                
            except Exception as api_error:
                error_msg = str(api_error)
                logger.error(f"API调用异常: {error_msg}")
                
                # 增加异常处理的详细分类
                if "Connection" in error_msg or "connect" in error_msg.lower():
                    logger.error(f"网络连接错误 - 请检查网络连接和API地址")
                    return f"API调用失败: 无法连接到服务器。请检查网络连接和API地址配置。"
                
                elif "authenticate" in error_msg.lower() or "authorization" in error_msg.lower() or "auth" in error_msg.lower():
                    logger.error(f"API认证错误 - 请检查API密钥是否正确")
                    return f"API调用失败: 认证错误。请检查API密钥配置。"
                
                elif "not found" in error_msg.lower() or "404" in error_msg:
                    logger.error(f"API资源不存在 - 请检查API地址和路径是否正确")
                    return f"API调用失败: 请求的资源不存在。请检查API地址和路径。"
                
                else:
                    return f"API调用出错：{error_msg}"
                
        except Exception as e:
            logger.error(f"获取API回复失败: {str(e)}")
            # 降级处理：使用简化的提示
            try:
                return f"抱歉，我暂时无法回应，请稍后再试。(错误: {str(e)[:50]}...)"
            except Exception as fallback_error:
                logger.error(f"降级处理也失败: {str(fallback_error)}")
                return f"服务暂时不可用，请稍后重试。"

    def handle_user_message(self, content: str, chat_id: str, sender_name: str,
                            username: str, is_group: bool = False, is_image_recognition: bool = False, 
                            is_self_message: bool = False, is_at: bool = False):
        """统一的消息处理入口"""
        try:
            # 验证并修正用户ID
            if not username or username == "System":
                username = chat_id.split('@')[0] if '@' in chat_id else chat_id
                if username == "filehelper":
                    username = "FileHelper"
                sender_name = sender_name or username

            # 检查是否是群聊消息
            if is_group:
                logger.info(f"处理群聊消息: 群ID={chat_id}, 发送者={sender_name}, 内容={content[:30]}...")
                # 传递is_at参数
                return self._handle_group_message(content, chat_id, sender_name, username, is_at)

            # 处理私聊消息的逻辑保持不变
            actual_content = self._clean_message_content(content)
            logger.info(f"收到私聊消息: {actual_content}")
            
            if not hasattr(self, '_last_message_times'):
                self._last_message_times = {}
            self._last_message_times[username] = datetime.now()

            if is_self_message:
                self._send_self_message(content, chat_id)
                return None

            content_length = len(actual_content)
            
            should_cache = True
            if should_cache:
                return self._cache_message(content, chat_id, sender_name, username, is_group, is_image_recognition)
            
            return self._handle_uncached_message(content, chat_id, sender_name, username, is_group, is_image_recognition)

        except Exception as e:
            logger.error(f"处理消息失败: {str(e)}", exc_info=True)
            return None

    def _handle_group_message(self, content: str, group_id: str, sender_name: str, username: str, is_at: bool = False):
        """处理群聊消息"""
        try:
            # 优先使用传入的is_at参数，如果main.py已经正确检测并传入
            is_at_from_param = is_at
            
            # 检查是否包含引用消息
            quoted_content = None
            quoted_sender = None
            # 微信引用消息格式通常是: "引用 xxx 的消息"或"回复 xxx 的消息"
            quote_match = re.search(r'(?:引用|回复)\s+([^\s]+)\s+的(?:消息)?[:：]?\s*(.+?)(?=\n|$)', content)
            if quote_match and is_at_from_param:
                quoted_sender = quote_match.group(1)
                quoted_content = quote_match.group(2).strip()
                logger.info(f"检测到引用消息 - 引用者: {quoted_sender}, 内容: {quoted_content}")
                # 从原始消息中移除引用部分
                content = re.sub(r'(?:引用|回复)\s+[^\s]+\s+的(?:消息)?[:：]?\s*.+?(?=\n|$)', '', content).strip()
            
            # 备用检测：如果传入参数为False，再尝试本地检测
            if not is_at_from_param:
                # 检查是否@机器人 - 在消息清理前确定
                # 常见的空格字符：普通空格、不间断空格、零宽空格、特殊的微信空格等
                robot_at_patterns = [
                    f"@{self.robot_name} ",  # 普通空格
                    f"@{self.robot_name}\u2005",  # 特殊的微信空格
                    f"@{self.robot_name}\u00A0",  # 不间断空格
                    f"@{self.robot_name}\u200B",  # 零宽空格
                    f"@{self.robot_name}\u3000"   # 全角空格
                ]
                
                # 使用正则表达式进行更精确的匹配
                at_pattern = re.compile(f"@{re.escape(self.robot_name)}[\\s\u2005\u00A0\u200B\u3000]")
                is_at_local = bool(at_pattern.search(content)) or any(pattern in content for pattern in robot_at_patterns)
                
                # 提取原始@部分以供后续处理
                at_match = re.search(f"(@{re.escape(self.robot_name)}[\\s\u2005\u00A0\u200B\u3000])", content)
                at_content = at_match.group(1) if at_match else ''
            else:
                # 直接使用传入的参数
                is_at_local = True
                at_content = ""  # 不需要再提取，因为main.py已经处理过
            
            # 使用传入参数和本地检测的综合结果
            is_at_final = is_at_from_param or is_at_local
            
            # 清理消息内容
            actual_content = self._clean_message_content(content)
            
            # 使用最终的@状态进行日志记录和后续处理
            logger.info(f"收到群聊消息 - 群: {group_id}, 发送者: {sender_name}, 内容: {actual_content}, 是否@: {is_at_final}")
            
            # 保存所有群聊消息到群聊记忆，不论是否@
            timestamp = self.group_chat_memory.add_message(group_id, sender_name, actual_content, is_at_final)
            logger.debug(f"消息已保存到群聊记忆: {group_id}, 时间戳: {timestamp}")
            
            # 如果是@消息，加入处理队列并进行回复
            if is_at_final:
                logger.info(f"检测到@消息: {actual_content}")
                self.at_message_timestamps[f"{group_id}_{timestamp}"] = timestamp
                
                # 如果@被清理掉了，且有原始@内容
                if at_content and at_content not in actual_content:
                    at_stripped_content = actual_content.strip()
                    return self._handle_at_message(at_stripped_content, group_id, sender_name, username, timestamp)
                else:
                    return self._handle_at_message(actual_content, group_id, sender_name, username, timestamp)
            else:
                logger.debug(f"非@消息，仅保存到记忆: {actual_content[:30]}...")
                
            return None
            
        except Exception as e:
            logger.error(f"处理群聊消息失败: {str(e)}", exc_info=True)
            return None

    def _handle_at_message(self, content: str, group_id: str, sender_name: str, username: str, timestamp: str):
        """处理@消息"""
        try:
            # 检查是否包含引用消息
            quoted_content = None
            quoted_sender = None
            quote_match = re.search(r'(?:引用|回复)\s+([^\s]+)\s+的(?:消息)?[:：]?\s*(.+?)(?=\n|$)', content)
            if quote_match:
                quoted_sender = quote_match.group(1)
                quoted_content = quote_match.group(2).strip()
                logger.info(f"检测到引用消息 - 引用者: {quoted_sender}, 内容: {quoted_content}")
                # 从原始消息中移除引用部分
                content = re.sub(r'(?:引用|回复)\s+[^\s]+\s+的(?:消息)?[:：]?\s*.+?(?=\n|$)', '', content).strip()
                
                # 如果引用内容为空，尝试从群聊记忆中获取
                if quoted_content and hasattr(self, 'group_chat_memory'):
                    # 获取引用消息的上下文
                    quoted_context = self.group_chat_memory.get_message_by_content(group_id, quoted_content)
                    if quoted_context:
                        logger.info(f"找到引用消息的上下文: {quoted_context}")
                        # 将引用内容添加到当前消息的上下文中
                        content = f"(引用消息: {quoted_sender} 说: {quoted_content})\n{content}"
            
            # 获取最近的群聊上下文消息，限制数量和时间范围
            context_messages = self.group_chat_memory.get_context_messages(group_id, timestamp)
            
            # 过滤和清理上下文消息
            filtered_context = []
            current_time = datetime.now()
            
            if context_messages:
                for msg in context_messages:
                    if msg["timestamp"] == timestamp:  # 跳过当前消息
                        continue
                        
                    # 检查消息时间（限制在6小时内）
                    try:
                        msg_time = datetime.strptime(msg["timestamp"], "%Y-%m-%d %H:%M:%S")
                        if (current_time - msg_time).total_seconds() > 21600:  # 6小时 = 21600秒
                            continue
                    except (ValueError, TypeError):
                        continue
                    
                    # 清理消息内容
                    human_message = self._clean_memory_content(msg["human_message"])
                    assistant_message = self._clean_memory_content(msg["assistant_message"]) if msg["assistant_message"] else None
                    
                    if human_message:
                        filtered_context.append({
                            "sender_name": msg["sender_name"],
                            "human_message": human_message,
                            "assistant_message": assistant_message
                        })
            
            # 限制上下文消息数量
            filtered_context = filtered_context[-3:]  # 只保留最近3条消息
            
            # 构建上下文字符串
            context = ""
            if filtered_context:
                context_parts = []
                for msg in filtered_context:
                    # 添加发送者消息
                    context_parts.append(f"{msg['sender_name']}: {msg['human_message']}")
                    # 如果有机器人回复，也添加进去
                    if msg["assistant_message"]:
                        context_parts.append(f"{self.robot_name}: {msg['assistant_message']}")
                
                if context_parts:
                    context = "<context>" + "\n".join(context_parts) + "</context>\n\n"
            
            # 构建API请求内容
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            api_content = f"<time>{current_time}</time>\n<group>{group_id}</group>\n<sender>{sender_name}</sender>\n{context}<input>{content}</input>"
            
            # 获取AI回复
            reply = self.get_api_response(api_content, username)
            
            # 如果成功获取回复
            if reply:
                # 清理回复内容
                reply = self._clean_ai_response(reply)
                
                # 更新群聊记忆
                self.group_chat_memory.update_assistant_response(group_id, timestamp, reply)
                
                # 过滤动作和表情
                reply = self._filter_action_emotion(reply)
                
                # 分割消息
                split_messages = self._split_message_for_sending(reply)
                
                # 发送消息
                if not self.is_debug:
                    self._send_split_messages(split_messages, group_id)
                
                return split_messages['parts']
            
            return None
            
        except Exception as e:
            logger.error(f"处理@消息失败: {str(e)}")
            return None

    def _clean_message_content(self, content: str) -> str:
        """清理消息内容，去除时间戳和前缀"""
        # 匹配并去除时间戳和前缀
        patterns = [
            r'^\(?\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\)?\s+ta私聊对你说\s*',
            r'^\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\]\s+ta私聊对你说\s*',
            r'^\(此时时间为\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\)\s+ta(私聊|在群聊里)对你说\s*',
            r'^.*?ta私聊对你说\s*',
            r'^.*?ta在群聊里对你说\s*'  # 添加群聊消息模式
        ]
        
        actual_content = content
        
        # 保存@信息
        at_match = re.search(r'(@[^\s]+)', actual_content)
        at_content = at_match.group(1) if at_match else ''
        
        # 清理时间戳和前缀
        for pattern in patterns:
            if re.search(pattern, actual_content):
                actual_content = re.sub(pattern, '', actual_content)
                break
        
        # 如果有@信息且在清理过程中被移除，重新添加到开头
        if at_content and at_content not in actual_content:
            actual_content = f"{at_content} {actual_content}"
        
        return actual_content.strip()

    def _cache_message(self, content: str, chat_id: str, sender_name: str, username: str, 
                      is_group: bool, is_image_recognition: bool) -> None:
        """缓存消息并设置定时器"""
        current_time = time.time()
        
        # 取消现有定时器
        if username in self.message_timer and self.message_timer[username]:
            self.message_timer[username].cancel()
        
        # 添加到消息缓存
        if username not in self.message_cache:
            self.message_cache[username] = []
        
        # 提取实际内容
        actual_content = self._clean_message_content(content)
        
        self.message_cache[username].append({
            'content': content,
            'chat_id': chat_id,
            'sender_name': sender_name,
            'is_group': is_group,
            'is_image_recognition': is_image_recognition,
            'timestamp': current_time
        })
        
        # 设置新的定时器
        wait_time = self._calculate_wait_time(username, len(self.message_cache[username]))
        timer = threading.Timer(wait_time, self._process_cached_messages, args=[username])
        timer.daemon = True
        timer.start()
        self.message_timer[username] = timer
        
        # 简化日志，只显示缓存内容和等待时间
        logger.info(f"缓存消息: {actual_content} | 等待时间: {wait_time:.1f}秒")
        
        return None

    def _calculate_wait_time(self, username: str, msg_count: int) -> float:
        """计算消息等待时间"""
        base_wait_time = 3.0
        typing_speed = self._estimate_typing_speed(username)
        
        if msg_count == 1:
            wait_time = base_wait_time + 5.0
        else:
            estimated_typing_time = min(4.0, typing_speed * 20)  # 假设用户输入20个字符
            wait_time = base_wait_time + estimated_typing_time
            
        # 简化日志，只在debug级别显示详细计算过程
        logger.debug(f"消息等待时间计算: 基础={base_wait_time}秒, 打字速度={typing_speed:.2f}秒/字, 结果={wait_time:.1f}秒")
        
        return wait_time

    def _process_cached_messages(self, username: str):
        """处理缓存的消息"""
        try:
            if not self.message_cache.get(username):
                return None
            
            messages = self.message_cache[username]
            messages.sort(key=lambda x: x.get('timestamp', 0))
            
            # 获取最近的对话记录作为上下文
            context = self._get_conversation_context(username)
            
            # 合并消息内容
            raw_contents = []
            first_timestamp = None
            
            for msg in messages:
                content = msg['content']
                if not first_timestamp:
                    # 提取第一条消息的时间戳
                    timestamp_match = re.search(r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(?::\d{2})?', content)
                    if timestamp_match:
                        first_timestamp = timestamp_match.group()
                
                # 清理消息内容
                cleaned_content = self._clean_message_content(content)
                if cleaned_content:
                    raw_contents.append(cleaned_content)
            
            # 使用 \ 作为句子分隔符合并消息
            content_text = ' $ '.join(raw_contents)
            
            # 格式化最终消息
            first_timestamp = first_timestamp or datetime.now().strftime('%Y-%m-%d %H:%M')
            merged_content = f"[{first_timestamp}]ta 私聊对你说：{content_text}"
            
            if context:
                merged_content = f"{context}\n\n(以上是历史对话内容，仅供参考，无需进行互动。请专注处理接下来的新内容)\n\n{merged_content}"
            
            # 处理合并后的消息
            last_message = messages[-1]
            result = self._handle_text_message(
                merged_content,
                last_message['chat_id'],
                last_message['sender_name'],
                username,
                last_message['is_group'],
                any(msg.get('is_image_recognition', False) for msg in messages)
            )
            
            # 清理缓存和定时器
            self.message_cache[username] = []
            if username in self.message_timer and self.message_timer[username]:
                self.message_timer[username].cancel()
                self.message_timer[username] = None
            
            return result

        except Exception as e:
            logger.error(f"处理缓存消息失败: {str(e)}", exc_info=True)
            return None
            
    def _get_conversation_context(self, username: str) -> str:
        """获取对话上下文"""
        try:
            # 构建更精确的查询，包含用户ID和当前时间信息，以获取更相关的记忆
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            query = f"与用户 {username} 相关的最近重要对话 {current_time}"
            
            # 获取相关记忆
            recent_history = self.memory_handler.get_relevant_memories(
                query, 
                username,
                top_k=10  # 增加获取的记忆数量，后续会基于质量筛选
            )
            
            if recent_history and len(recent_history) > 0:
                # 根据记忆质量排序和筛选
                # 筛选标准：
                # 1. 尽量选择长度适中的对话（不太短也不太长）
                # 2. 优先选择更复杂的对话（含有特定信息的）
                
                # 简单评分函数
                def memory_quality_score(mem):
                    if not mem.get('message') or not mem.get('reply'):
                        return 0
                    
                    msg_len = len(mem['message'])
                    reply_len = len(mem['reply'])
                    
                    # 太短的对话质量低
                    if msg_len < 5 or reply_len < 10:
                        return 0
                    
                    # 太长的对话也不理想
                    if msg_len > 500 or reply_len > 1000:
                        return 10
                    
                    # 基础分数
                    score = min(100, (msg_len + reply_len) / 10)
                    
                    # 包含特定用户名或对话元素的加分
                    if username.lower() in mem['message'].lower() or username.lower() in mem['reply'].lower():
                        score += 15
                    
                    # 包含问答格式的加分
                    if "?" in mem['message'] or "？" in mem['message']:
                        score += 10
                        
                    return score
                
                # 按质量排序
                sorted_memories = sorted(recent_history, key=memory_quality_score, reverse=True)
                
                # 选取最高质量的记忆（最多5条）
                quality_memories = sorted_memories[:5]
                logger.info(f"从 {len(recent_history)} 条记忆中筛选出 {len(quality_memories)} 条高质量记忆")
                
                # 构建上下文
                context_parts = []
                for idx, hist in enumerate(quality_memories):
                    if hist.get('message') and hist.get('reply'):
                        context_parts.append(f"对话{idx+1}:\n用户: {hist['message']}\nAI: {hist['reply']}")
                
                if context_parts:
                    return "以下是之前的对话记录：\n\n" + "\n\n".join(context_parts)
            
            return ""
            
        except Exception as e:
            logger.error(f"获取记忆历史记录失败: {str(e)}")
            return ""

    def _estimate_typing_speed(self, username: str) -> float:
        """估计用户的打字速度（秒/字符）"""
        # 如果没有足够的历史消息，使用默认值
        if username not in self.message_cache or len(self.message_cache[username]) < 2:
            # 根据用户ID是否存在于last_message_time中返回不同的默认值
            # 如果是新用户，给予更长的等待时间
            if username not in self.last_message_time:
                typing_speed = 0.2  # 新用户默认速度：每字0.2秒
            else:
                typing_speed = 0.15  # 已知用户默认速度：每字0.15秒
            
            logger.info(f"用户打字速度: {typing_speed:.2f}秒/字符")
            return typing_speed
        
        # 获取最近的两条消息
        messages = self.message_cache[username]
        if len(messages) < 2:
            typing_speed = 0.15
            logger.info(f"用户打字速度: {typing_speed:.2f}秒/字符")
            return typing_speed
        
        # 按时间戳排序，确保我们比较的是连续的消息
        recent_msgs = sorted(messages, key=lambda x: x.get('timestamp', 0))[-2:]
        
        # 计算时间差和字符数
        time_diff = recent_msgs[1].get('timestamp', 0) - recent_msgs[0].get('timestamp', 0)
        
        # 获取实际内容（去除时间戳和前缀）
        content = recent_msgs[0].get('content', '')
        
        # 定义系统提示词模式
        time_prefix_pattern = r'^\(?\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\)?\s+ta私聊对你说\s+'
        time_prefix_pattern2 = r'^\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\]\s+ta私聊对你说\s+'
        time_prefix_pattern3 = r'^\(此时时间为\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\)\s+ta(私聊|在群聊里)对你说\s*'
        reminder_pattern = r'\((?:上次的对话内容|以上是历史对话内容)[^)]*\)'
        context_pattern = r'对话\d+:\n用户:.+\nAI:.+'
        system_patterns = [
            # 旧的精确字数限制提示
            r'\n\n请注意：你的回复应当与用户消息的长度相当，控制在约\d+个字符和\d+个句子左右。',
            # 新的提示词变体
            r'\n\n请简短回复，控制在一两句话内。',
            r'\n\n请注意保持自然的回复长度，与用户消息风格协调。',
            r'\n\n请保持简洁明了的回复。',
            # 其他系统提示词
            r'\(以上是历史对话内容，仅供参考，无需进行互动。请专注处理接下来的新内容\)',
            r'请你回应用户的结束语'
        ]
        
        # 先去除基本的时间戳和前缀
        if re.search(time_prefix_pattern, content):
            content = re.sub(time_prefix_pattern, '', content)
        elif re.search(time_prefix_pattern2, content):
            content = re.sub(time_prefix_pattern2, '', content)
        elif re.search(time_prefix_pattern3, content):
            content = re.sub(time_prefix_pattern3, '', content)
        
        # 去除其他系统提示词
        content = re.sub(reminder_pattern, '', content)
        content = re.sub(context_pattern, '', content, flags=re.DOTALL)
        
        for pattern in system_patterns:
            content = re.sub(pattern, '', content)
        
        # 计算过滤后的实际用户内容长度
        filtered_content = content.strip()
        char_count = len(filtered_content)
        
        # 如果时间差或字符数无效，使用默认值
        if time_diff <= 0 or char_count <= 0:
            typing_speed = 0.15
            logger.info(f"用户打字速度: {typing_speed:.2f}秒/字符")
            return typing_speed
        
        # 计算打字速度（秒/字）
        typing_speed = time_diff / char_count
        
        # 应用平滑因子，避免极端值
        # 如果我们有历史记录的打字速度，将其纳入考虑
        if hasattr(self, '_typing_speeds') and username in self._typing_speeds:
            prev_speed = self._typing_speeds[username]
            # 使用加权平均，新速度权重0.4，历史速度权重0.6
            typing_speed = 0.4 * typing_speed + 0.6 * prev_speed
        
        # 存储计算出的打字速度
        if not hasattr(self, '_typing_speeds'):
            self._typing_speeds = {}
        self._typing_speeds[username] = typing_speed
        
        # 限制在合理范围内：0.2秒/字 到 1.2秒/字
        typing_speed = max(0.2, min(1.2, typing_speed))
        
        # 只输出最终的打字速度
        logger.info(f"用户打字速度: {typing_speed:.2f}秒/字符")
        
        return typing_speed

    def _calculate_response_length_ratio(self, user_message_length: int) -> float:
        """计算回复长度与用户消息的比例"""
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

    def _handle_voice_request(self, content, chat_id, sender_name, username, is_group):
        """处理语音请求"""
        logger.info("处理语音请求")
        reply = self.get_api_response(content, chat_id)
        if "</think>" in reply:
            reply = reply.split("</think>", 1)[1].strip()

        voice_path = self.voice_handler.generate_voice(reply)
        if voice_path:
            try:
                self.wx.SendFiles(filepath=voice_path, who=chat_id)
            except Exception as e:
                logger.error(f"发送语音失败: {str(e)}")
                if is_group:
                    reply = f"@{sender_name} {reply}"
                self.wx.SendMsg(msg=reply, who=chat_id)
            finally:
                try:
                    os.remove(voice_path)
                except Exception as e:
                    logger.error(f"删除临时语音文件失败: {str(e)}")
        else:
            if is_group:
                reply = f"@{sender_name} {reply}"
            self.wx.SendMsg(msg=reply, who=chat_id)
        return reply

    def _handle_random_image_request(self, content, chat_id, sender_name, username, is_group):
        """处理随机图片请求"""
        logger.info("处理随机图片请求")
        image_path = self.image_handler.get_random_image()
        if image_path:
            try:
                self.wx.SendFiles(filepath=image_path, who=chat_id)
                reply = "给主人你找了一张好看的图片哦~"
            except Exception as e:
                logger.error(f"发送图片失败: {str(e)}")
                reply = "抱歉主人，图片发送失败了..."
            finally:
                try:
                    if os.path.exists(image_path):
                        os.remove(image_path)
                except Exception as e:
                    logger.error(f"删除临时图片失败: {str(e)}")

            if is_group:
                reply = f"@{sender_name} {reply}"
            self.wx.SendMsg(msg=reply, who=chat_id)
            return reply
        return None

    def _handle_image_generation_request(self, content, chat_id, sender_name, username, is_group):
        """处理图像生成请求"""
        logger.info("处理画图请求")
        image_path = self.image_handler.generate_image(content)
        if image_path:
            try:
                self.wx.SendFiles(filepath=image_path, who=chat_id)
                reply = "这是按照主人您的要求生成的图片\\(^o^)/~"
            except Exception as e:
                logger.error(f"发送生成图片失败: {str(e)}")
                reply = "抱歉主人，图片生成失败了..."
            finally:
                try:
                    if os.path.exists(image_path):
                        os.remove(image_path)
                except Exception as e:
                    logger.error(f"删除临时图片失败: {str(e)}")

            if is_group:
                reply = f"@{sender_name} {reply}"
            self.wx.SendMsg(msg=reply, who=chat_id)
            return reply
        return None

    def _filter_action_emotion(self, text):
        """处理动作描写和颜文字，确保格式一致"""
        # 1. 先移除文本中的引号，避免引号包裹非动作文本
        text = text.replace('"', '').replace('"', '').replace('"', '')
        
        # 2. 保护已经存在的括号内容
        protected_parts = {}
        
        # 匹配所有类型的括号及其内容
        bracket_pattern = r'[\(\[（【][^\(\[（【\)\]）】]*[\)\]）】]'
        brackets = list(re.finditer(bracket_pattern, text))
        
        # 保护已有的括号内容
        for i, match in enumerate(brackets):
            placeholder = f"__PROTECTED_{i}__"
            protected_parts[placeholder] = match.group()
            text = text.replace(match.group(), placeholder)
        
        # 3. 保护颜文字 - 使用更宽松的匹配规则
        if not hasattr(self, '_emoticon_chars_set'):
            self._emoticon_chars_set = set(
                '（()）~～‿⁀∀︿⌒▽△□◇○●ˇ＾∇＿゜◕ω・ノ丿╯╰つ⊂＼／┌┐┘└°△▲▽▼◇◆○●◎■□▢▣▤▥▦▧▨▩♡♥ღ☆★✡⁂✧✦❈❇✴✺✹✸✷✶✵✳✲✱✰✯✮✭✬✫✪✩✧✦✥✤✣✢✡✠✟✞✝✜✛✚✙✘✗✖✕✔✓✒✑✐✏✎✍✌✋✊✉✈✇✆✅✄✃✂✁✀✿✾✽✼✻✺✹✸✷✶✵✴✳✲✱✰✯✮✭✬✫✪✩✨✧✦✥✤✣✢✡✠✟✞✝✜✛✚✙✘✗✖✕✔✓✒✑✐✏✎✍✌✋✊✉✈✇✆✅✄✃✂✁❤♪♫♬♩♭♮♯°○◎●◯◐◑◒◓◔◕◖◗¤☼☀☁☂☃☄★☆☎☏⊙◎☺☻☯☭♠♣♧♡♥❤❥❣♂♀☿❀❁❃❈❉❊❋❖☠☢☣☤☥☦☧☨☩☪☫☬☭☮☯☸☹☺☻☼☽☾☿♀♁♂♃♄♆♇♈♉♊♋♌♍♎♏♐♑♒♓♔♕♖♗♘♙♚♛♜♝♞♟♠♡♢♣♤♥♦♧♨♩♪♫♬♭♮♯♰♱♲♳♴♵♶♷♸♹♺♻♼♽♾♿⚀⚁⚂⚃⚄⚆⚇⚈⚉⚊⚋⚌⚍⚎⚏⚐⚑⚒⚓⚔⚕⚖⚗⚘⚙⚚⚛⚜⚝⚞⚟*^_^')
        
        emoji_patterns = [
            # 括号类型的颜文字
            r'\([\w\W]{1,10}?\)',  # 匹配较短的括号内容
            r'（[\w\W]{1,10}?）',  # 中文括号
            
            # 符号组合类型
            r'[＼\\\/\*\-\+\<\>\^\$\%\!\?\@\#\&\|\{\}\=\;\:\,\.]{2,}',  # 常见符号组合
            
            # 常见表情符号
            r'[◕◑◓◒◐•‿\^▽\◡\⌒\◠\︶\ω\´\`\﹏\＾\∀\°\◆\□\▽\﹃\△\≧\≦\⊙\→\←\↑\↓\○\◇\♡\❤\♥\♪\✿\★\☆]{1,}',
            
            # *号组合
            r'\*[\w\W]{1,5}?\*'  # 星号强调内容
        ]
        
        for pattern in emoji_patterns:
            emojis = list(re.finditer(pattern, text))
            for i, match in enumerate(emojis):
                # 避免处理过长的内容，可能是动作描写而非颜文字
                if len(match.group()) <= 15 and not any(p in match.group() for p in protected_parts.values()):
                    # 检查是否包含足够的表情符号字符
                    chars_count = sum(1 for c in match.group() if c in self._emoticon_chars_set)
                    if chars_count >= 2 or len(match.group()) <= 5:
                        placeholder = f"__EMOJI_{i}__"
                        protected_parts[placeholder] = match.group()
                        text = text.replace(match.group(), placeholder)
        
        # 4. 处理分隔符 - 保留原样
        parts = text.split('$')
        new_parts = []
        
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:  # 跳过空部分
                continue
                
            # 直接添加部分，不添加括号
            new_parts.append(part)
        
        # 5. 特殊处理：同时兼容原来的 \ 分隔符
        if len(new_parts) == 1:  # 如果没有找到 $ 分隔符，尝试处理 \ 分隔符
            parts = text.split('\\')
            if len(parts) > 1:  # 确认有实际分隔
                new_parts = []
                for i, part in enumerate(parts):
                    part = part.strip()
                    if not part:
                        continue
                    # 直接添加部分，不添加括号
                    new_parts.append(part)
        
        # 6. 重新组合文本
        result = " $ ".join(new_parts)
        
        # 7. 恢复所有保护的内容
        for placeholder, content in protected_parts.items():
            result = result.replace(placeholder, content)
            
        return result

    def _handle_file_request(self, file_path, chat_id, sender_name, username, is_group):
        """处理文件请求"""
        logger.info(f"处理文件请求: {file_path}")

        try:

            from handlers.file import FileHandler
            files_handler = FileHandler(self.root_dir)

            target_path = files_handler.move_to_files_dir(file_path)
            logger.info(f"文件已转存至: {target_path}")

            # 获取文件类型
            file_type = files_handler.get_file_type(target_path)
            logger.info(f"文件类型: {file_type}")

            # 读取文件内容
            file_content = files_handler.read_file_content(target_path)
            logger.info(f"成功读取文件内容，长度: {len(file_content)} 字符")

            prompt = f"你收到了一个{file_type}文件，文件内容如下:\n\n{file_content}\n\n请帮我分析这个文件的内容，提取关键信息，根据角色设定，给出你的回答。"

            # 获取 AI 回复
            reply = self.get_api_response(prompt, chat_id)
            if "</think>" in reply:
                think_content, reply = reply.split("</think>", 1)
                logger.info("\n思考过程:")
                logger.info(think_content.strip())
                reply = reply.strip()

            # 在群聊中添加@
            if is_group:
                reply = f"@{sender_name} \n{reply}"
            else:
                reply = f"{reply}"

            # 发送回复
            try:
                # 增强型智能分割器
                delayed_reply = []
                current_sentence = []
                ending_punctuations = {'。', '！', '？', '!', '?', '…', '……'}
                split_symbols = {'$', '|', '￤', '\n', '\\n'}  # 支持多种手动分割符

                for idx, char in enumerate(reply):
                    # 处理手动分割符号（优先级最高）
                    if char in split_symbols:
                        if current_sentence:
                            delayed_reply.append(''.join(current_sentence).strip())
                        current_sentence = []
                        continue

                    current_sentence.append(char)

                    # 处理中文标点和省略号
                    if char in ending_punctuations:
                        # 排除英文符号在短句中的误判（如英文缩写）
                        if char in {'!', '?'} and len(current_sentence) < 4:
                            continue

                        # 处理连续省略号
                        if char == '…' and idx > 0 and reply[idx - 1] == '…':
                            if len(current_sentence) >= 3:  # 至少三个点形成省略号
                                delayed_reply.append(''.join(current_sentence).strip())
                                current_sentence = []
                        else:
                            delayed_reply.append(''.join(current_sentence).strip())
                            current_sentence = []

                # 处理剩余内容
                if current_sentence:
                    delayed_reply.append(''.join(current_sentence).strip())
                delayed_reply = [s for s in delayed_reply if s]  # 过滤空内容

                # 发送分割后的文本回复, 并控制时间间隔
                for part in delayed_reply:
                    self.wx.SendMsg(msg=part, who=chat_id)
                    time.sleep(random.uniform(0.5, 1.5))  # 稍微增加一点随机性

            except Exception as e:
                logger.error(f"发送文件分析结果失败: {str(e)}")
                self.wx.SendMsg(msg="抱歉，文件分析结果发送失败", who=chat_id)
            # 重置计数器（如果大于0）
            if self.unanswered_counters.get(username, 0) > 0:
                self.unanswered_counters[username] = 0
                logger.info(f"用户 {username} 的未回复计数器已重置")

            return reply

        except Exception as e:
            logger.error(f"处理文件失败: {str(e)}", exc_info=True)
            error_msg = f"抱歉，文件处理过程中出现错误: {str(e)}"
            if is_group:
                error_msg = f"@{sender_name} {error_msg}"
            self.wx.SendMsg(msg=error_msg, who=chat_id)
            return None

    def _safe_send_msg(self, msg, who, max_retries=None, char_by_char=False):
        """安全发送消息，带重试机制"""
        if not msg or not who:
            logger.warning("消息或接收人为空，跳过发送")
            return False
            
        # 检查调试模式
        if self.is_debug:
            # 调试模式下直接打印消息而不是发送
            logger.debug(f"[调试模式] 发送消息: {msg[:20]}...")
            return True
            
        # 检查wx对象是否可用
        if self.wx is None:
            logger.warning("WeChat对象为None，无法发送消息")
            return False
        
        # 不再特殊处理消息末尾的反斜杠，因为所有反斜杠都已在分割阶段处理
        processed_msg = msg
            
        # 设置重试次数
        if max_retries is None:
            max_retries = 3
            
        # 尝试发送消息
        for attempt in range(max_retries):
            try:
                if self.is_qq:
                    # QQ消息直接返回，不实际发送
                    return True
                else:
                    # 微信消息发送
                    if char_by_char:
                        # 逐字发送
                        for char in processed_msg:
                            self.wx.SendMsg(char, who)
                            time.sleep(random.uniform(0.1, 0.3))
                    else:
                        # 整条发送
                        self.wx.SendMsg(processed_msg, who)
                return True
            except Exception as e:
                # 只在最后一次重试失败时记录错误
                if attempt == max_retries - 1:
                    logger.error(f"发送消息失败: {str(e)}")
                
                if attempt < max_retries - 1:
                    time.sleep(1)  # 等待一秒后重试
                    
        return False

    def _handle_text_message(self, content, chat_id, sender_name, username, is_group, is_image_recognition=False):
        """处理文本消息"""
        try:
            # 初始化返回值列表
            delayed_reply = []
            
            # 提取用户实际输入的内容（去除历史记忆和系统提示）
            actual_user_input = self._extract_actual_user_input(content)
            
            # 获取记忆 - 简化记忆检索的日志
            memories = []
            if self.memory_handler:
                try:
                    # 获取相关记忆，但限制数量和时间范围
                    current_time = datetime.now()
                    memories = self.memory_handler.get_relevant_memories(
                        content, 
                        username if not is_group else chat_id,
                        top_k=3  # 限制只获取最相关的3条记忆
                    )
                    
                    # 过滤和清理记忆
                    filtered_memories = []
                    for mem in memories:
                        if not mem.get('message') or not mem.get('reply'):
                            continue
                            
                        # 检查记忆时间（如果有）
                        if 'timestamp' in mem:
                            try:
                                mem_time = datetime.strptime(mem['timestamp'], '%Y-%m-%d %H:%M:%S')
                                # 只使用24小时内的记忆
                                if (current_time - mem_time).days > 1:
                                    continue
                            except (ValueError, TypeError):
                                pass
                        
                        # 清理记忆中的系统提示词
                        message = self._clean_memory_content(mem['message'])
                        reply = self._clean_memory_content(mem['reply'])
                        
                        if message and reply:
                            filtered_memories.append({
                                'message': message,
                                'reply': reply,
                                'timestamp': mem.get('timestamp', '')
                            })
                    
                    memories = filtered_memories[:2]  # 最多使用2条过滤后的记忆
                    
                    # 只记录找到记忆的数量，不输出详细内容
                    if memories:
                        logger.info(f"找到并过滤后的有效记忆: {len(memories)}条")
                except Exception as mem_err:
                    logger.error(f"获取记忆失败: {str(mem_err)}")
                    memories = []
            
            # 获取或初始化未回复计数器
            counter = self.unanswered_counters.get(username, 0)
            
            # 定义结束关键词
            end_keywords = [
                "结束", "再见", "拜拜", "下次聊", "先这样", "告辞", "bye", "晚点聊", "回头见",
                "稍后", "改天", "有空聊", "去忙了", "暂停", "待一会儿", "过一会儿", "晚安", "休息",
                "走了", "撤了", "闪了", "不聊了", "断了", "下线", "离开", "停", "歇", "退"
            ]
            
            # 检查消息中是否包含结束关键词
            is_end_of_conversation = any(keyword in actual_user_input for keyword in end_keywords)
            raw_content = content
            
            # 构建API请求内容
            api_content = actual_user_input
            
            # 计算用户实际输入的字符长度，只计算 $ 分隔的实际消息内容
            user_messages = [msg.strip() for msg in actual_user_input.split('$') if msg.strip()]
            user_input_length = sum(len(msg) for msg in user_messages)
            target_length = int(user_input_length * self._calculate_response_length_ratio(user_input_length))
            target_sentences = max(1, min(4, int(target_length / 25)))  # 大约每25个字符一个句子
            
            # 构建系统提示词（使用特殊标记包裹，确保不会出现在最终回复中）
            system_prompts = []
            
            # 添加长度限制提示词
            system_prompts.append(f"<length>请将回复控制在{target_length}字符和{target_sentences}个句子左右</length>")
            
            # 如果检测到结束关键词，添加结束语提示
            if is_end_of_conversation:
                system_prompts.append("<end>请以你的身份回应用户的结束语</end>")
            
            # 添加记忆上下文（如果有）
            if memories:
                memory_context = []
                for i, mem in enumerate(memories, 1):
                    memory_context.append(f"记忆{i}:\n用户: {mem['message']}\nAI: {mem['reply']}")
                
                if memory_context:
                    memory_text = "\n\n".join(memory_context)
                    system_prompts.append(f"<memory>参考以下历史对话：\n\n{memory_text}</memory>")
            
            # 组合所有提示词和用户输入
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            final_prompt = f"<system>{' '.join(system_prompts)}</system>\n\n<time>{current_time}</time>\n\n<input>{api_content}</input>"
            
            # 获取AI回复
            reply = self.get_api_response(final_prompt, username)
            
            # 处理思考过程和清理回复内容
            if "</think>" in reply:
                think_content, reply = reply.split("</think>", 1)
                if not self.is_debug:
                    logger.debug(f"思考过程: {think_content.strip()}")
            
            # 清理AI回复中的所有系统标记和提示词
            reply = self._clean_ai_response(reply)
            
            # 保存原始回复，用于记忆存储
            original_reply = reply
            
            # 过滤括号内的动作和情感描述
            reply = self._filter_action_emotion(reply)
            
            # 立即保存对话记忆
            try:
                if self.memory_handler:
                    try:
                        # 确保保存的记忆内容不包含memory_number相关信息
                        if asyncio.iscoroutinefunction(self.memory_handler.remember):
                            save_result = _run_async(global_remember(username, actual_user_input, original_reply))
                        else:
                            save_result = self.memory_handler.remember(username, actual_user_input, original_reply)
                        
                        if not save_result and hasattr(self.memory_handler, 'add_short_memory'):
                            self.memory_handler.add_short_memory(username, actual_user_input, original_reply)
                    except Exception as e:
                        logger.error(f"保存记忆失败: {str(e)}")
            except Exception as mem_err:
                logger.error(f"保存对话记忆失败: {str(mem_err)}")
            
            # 为回复添加断句标记 (用于微信发送)
            reply_with_breaks = self._add_sentence_breaks(reply)
            
            # 记录带断句标记的完整回复
            logger.info(f"发送回复(带断句): {reply_with_breaks}")
            
            # 添加群聊@
            if is_group:
                # 检查原始消息中是否包含@信息，并提取原始@者的名字
                at_match = re.search(r'@([^\s]+)', content)
                if at_match:
                    original_at_name = at_match.group(1)
                    # 如果找到原始@者，使用原始@者的名字
                    reply_with_breaks = f"@{original_at_name} {reply_with_breaks}"
                else:
                    # 如果没有找到原始@信息，使用发送者名字
                    reply_with_breaks = f"@{sender_name} {reply_with_breaks}"
            
            try:
                # 使用优化后的消息分割方法，只计算实际回复的长度
                split_messages = self._split_message_for_sending(reply_with_breaks)
                delayed_reply.extend(split_messages['parts'])
                
                # 记录实际消息统计（确保这是实际AI回复的统计，不包括历史记忆）
                actual_length = split_messages['total_length']
                actual_sentence_count = split_messages['sentence_count']
                logger.info(f"发送消息: {actual_length}字符, {actual_sentence_count}句")
                
                # 使用优化后的消息发送方法
                if not self.is_debug:
                    self._send_split_messages(split_messages, chat_id)
                
                # 检查是否需要发送表情包
                emoji_path = None
                if self.emoji_handler and hasattr(self.emoji_handler, 'get_emotion_emoji'):
                    try:
                        # 传入实际用户输入和用户ID进行判断
                        emoji_path = self.emoji_handler.get_emotion_emoji(actual_user_input, username)
                    except Exception as e:
                        logger.error(f"获取表情包失败: {str(e)}")
            
                # 发送回复
                if emoji_path:
                    try:
                        self.wx.SendFiles(filepath=emoji_path, who=chat_id)
                        delayed_reply.append(emoji_path)
                    except Exception as e:
                        logger.error(f"发送表情包失败: {str(e)}")
            except Exception as e:
                logger.error(f"发送回复失败: {str(e)}")
                return delayed_reply
            
            # 重置计数器（如果大于0）
            if self.unanswered_counters.get(username, 0) > 0:
                self.unanswered_counters[username] = 0
            
            return delayed_reply
        except Exception as e:
            logger.error(f"处理文本消息失败: {str(e)}", exc_info=True)
            error_msg = f"抱歉，处理消息时出现错误"
            if is_group:
                error_msg = f"@{sender_name} {error_msg}"
            
            if self.wx:
                self.wx.SendMsg(msg=error_msg, who=chat_id)
            
            return [error_msg]
            
    def _clean_ai_response(self, response: str) -> str:
        """清理AI回复中的所有系统标记和提示词"""
        if not response:
            return ""
        
        # 移除所有XML样式的标记
        response = re.sub(r'<[^>]+>', '', response)
        
        # 清理其他系统标记和提示词
        patterns_to_remove = [
            r'\[系统提示\].*?\[/系统提示\]',
            r'\[系统指令\].*?\[/系统指令\]',
            r'记忆\d+:\s*\n用户:.*?\nAI:.*?(?=\n\n|$)',
            r'以下是之前的对话记录：.*?(?=\n\n)',
            r'\(以上是历史对话内容[^)]*\)',
            r'memory_number:.*?(?=\n|$)',
            r'\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(?::\d{2})?\]',
            r'请注意：.*?(?=\n|$)',
            r'请(?:简短|简洁)回复.*?(?=\n|$)',
            r'请.*?控制在.*?(?=\n|$)',
            r'请你回应用户的结束语',
            r'^你：|^对方：|^AI：',
            r'ta(?:私聊|在群聊里)对你说[：:]\s*'
        ]
        
        for pattern in patterns_to_remove:
            response = re.sub(pattern, '', response, flags=re.DOTALL|re.IGNORECASE)
        
        # 移除多余的空白字符
        response = re.sub(r'\s+', ' ', response)
        return response.strip()

    def _add_sentence_breaks(self, text):
        """在句子之间添加断句标记($)用于微信发送"""
        # 定义句子结束标点
        sentence_ends = ['。', '！', '？', '!', '?', '.', '\n']
        
        # 1. 先移除文本中的引号，避免引号包裹非动作文本
        text = text.replace('"', '').replace('"', '').replace('"', '')
        
        # 2. 保护已经存在的括号内容和颜文字
        protected_parts = {}
        
        # 匹配所有类型的括号及其内容
        bracket_pattern = r'[\(\[（【][^\(\[（【\)\]）】]*[\)\]）】]'
        brackets = list(re.finditer(bracket_pattern, text))
        
        # 保护已有的括号内容
        for i, match in enumerate(brackets):
            placeholder = f"__PROTECTED_{i}__"
            protected_parts[placeholder] = match.group()
            text = text.replace(match.group(), placeholder)
        
        # 保护颜文字 - 使用更宽松的匹配规则
        emoji_patterns = [
            r'\([\w\W]{1,10}?\)',  # 匹配较短的括号内容
            r'（[\w\W]{1,10}?）',  # 中文括号
            r'[＼\\\/\*\-\+\<\>\^\$\%\!\?\@\#\&\|\{\}\=\;\:\,\.]{2,}',  # 常见符号组合
            r'[◕◑◓◒◐•‿\^▽\◡\⌒\◠\︶\ω\´\`\﹏\＾\∀\°\◆\□\▽\﹃\△\≧\≦\⊙\→\←\↑\↓\○\◇\♡\❤\♥\♪\✿\★\☆]{1,}',
            r'\*[\w\W]{1,5}?\*'  # 星号强调内容
        ]
        
        for pattern in emoji_patterns:
            emojis = list(re.finditer(pattern, text))
            for i, match in enumerate(emojis):
                if len(match.group()) <= 15 and not any(p in match.group() for p in protected_parts.values()):
                    placeholder = f"__EMOJI_{i}__"
                    protected_parts[placeholder] = match.group()
                    text = text.replace(match.group(), placeholder)
        
        # 3. 分析文本并添加断句标记
        result = []
        current_sentence = ""
        min_sentence_length = 6  # 最小断句长度
        
        sentences = []
        last_pos = 0
        
        # 查找所有潜在的断句点
        for i, char in enumerate(text):
            if char in sentence_ends:
                # 获取完整句子
                full_sentence = text[last_pos:i+1].strip()
                # 检查句子长度和是否包含临时标记
                if len(full_sentence) >= min_sentence_length and not any(p in full_sentence for p in protected_parts.keys()):
                    sentences.append(full_sentence)
                    last_pos = i + 1
                elif any(p in full_sentence for p in protected_parts.keys()):
                    # 如果句子包含临时标记，尝试找到下一个安全的断句点
                    continue
                elif i - last_pos > 15:  
                    # 如果已经积累了超过15个字符，即使没有标准断句点也可以断句
                    sentences.append(full_sentence)
                    last_pos = i + 1
        
        # 添加剩余文本
        if last_pos < len(text):
            remaining = text[last_pos:].strip()
            if remaining:
                sentences.append(remaining)
        
        # 进一步处理句子，考虑中文语境的自然停顿
        final_sentences = []
        for sentence in sentences:
            # 如果句子很长，尝试在逗号等位置进一步断句
            if len(sentence) > 20:
                parts = re.split(r'[，,、；;]', sentence)
                accumulated = ""
                for part in parts:
                    if accumulated and len(accumulated) + len(part) > 20:
                        final_sentences.append(accumulated.strip())
                        accumulated = part
                    else:
                        accumulated += part + ("，" if part != parts[-1] else "")
                if accumulated:
                    final_sentences.append(accumulated.strip())
            else:
                final_sentences.append(sentence)
        
        # 使用$分隔符，并移除分隔符前的逗号
        processed_sentences = []
        for sentence in final_sentences:
            # 移除句子末尾的逗号
            cleaned_sentence = re.sub(r'[，,]+$', '', sentence.strip())
            if cleaned_sentence:
                processed_sentences.append(cleaned_sentence)
        
        text_with_breaks = ' $ '.join(processed_sentences)
        
        # 4. 恢复所有保护的内容
        for placeholder, content in protected_parts.items():
            text_with_breaks = text_with_breaks.replace(placeholder, content)
        
        # 5. 最后再次检查并移除$前的逗号
        text_with_breaks = re.sub(r'[，,。]+\s*\$', ' $', text_with_breaks)
        
        return text_with_breaks

    def _extract_actual_user_input(self, content: str) -> str:
        """
        提取实际的用户输入内容，去除历史对话和时间戳等
        
        Args:
            content: 用户发送的原始消息内容
            
        Returns:
            str: 处理后的用户实际输入内容
        """
        try:
            # 1. 移除时间戳
            time_patterns = [
                r'^\[\d{2}:\d{2}:\d{2}\]',
                r'^\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\]',
                r'^\(此时时间为\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\)',
                r'^\(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\)'
            ]
            
            cleaned_content = content
            for pattern in time_patterns:
                cleaned_content = re.sub(pattern, '', cleaned_content)
            
            # 2. 移除对话标记
            dialog_patterns = [
                r'ta私聊对你说[：:]\s*',
                r'ta在群聊里对你说[：:]\s*',
                r'^你：|^对方：|^AI：'
            ]
            
            for pattern in dialog_patterns:
                cleaned_content = re.sub(pattern, '', cleaned_content)
            
            # 3. 移除历史对话记录
            if "以下是之前的对话记录：" in cleaned_content:
                parts = cleaned_content.split("(以上是历史对话内容")
                if len(parts) > 1:
                    # 获取最后一部分（实际用户输入）
                    cleaned_content = parts[-1].split(")")[-1]
            
            # 4. 移除系统提示和指令
            system_patterns = [
                r'\[系统提示\].*?\[/系统提示\]',
                r'\[系统指令\].*?\[/系统指令\]',
                r'请注意：你的回复应当与用户消息的长度相当，控制在约\d+个字符和\d+个句子左右。',
                r'请简短回复，控制在一两句话内。',
                r'请注意保持自然的回复长度，与用户消息风格协调。',
                r'请保持简洁明了的回复。',
                r'请你回应用户的结束语'
            ]
            
            for pattern in system_patterns:
                cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.DOTALL)
            
            # 5. 移除memory_number相关内容
            cleaned_content = re.sub(r'\s*memory_number:.*?($|\n|\$)', '', cleaned_content, flags=re.DOTALL|re.IGNORECASE)
            
            # 6. 处理多余的空白字符
            cleaned_content = re.sub(r'\s+', ' ', cleaned_content)
            cleaned_content = cleaned_content.strip()
            
            # 7. 记录处理结果
            if cleaned_content != content:
                logger.debug(f"消息清理前: {len(content)}字符")
                logger.debug(f"消息清理后: {len(cleaned_content)}字符")
                logger.debug(f"清理后内容: {cleaned_content}")
            
            return cleaned_content
            
        except Exception as e:
            logger.error(f"提取用户实际输入失败: {str(e)}")
            return content.strip()  # 出错时返回原始内容

    def _check_time_query(self, content: str, username: str) -> tuple:
        """检查是否是时间查询请求"""
        # 时间查询关键词
        time_keywords = [
            "几点了", "现在时间", "当前时间", "现在几点", "时间是", "报时", "几点钟",
            "what time", "current time", "time now", "现在是几点", "告诉我时间",
            "今天日期", "今天几号", "几月几号", "星期几",
            "today's date", "what day", "date today", "几月几日"
        ]
        
        # 更严格的单词匹配，避免将部分词语误判为时间查询
        # 例如"时间"、"几点"这种常见词汇单独判断，要求它们是独立词组
        broad_keywords = ["时间", "几点", "日期"]
        specific_match = any(keyword in content.lower() for keyword in time_keywords)
        
        # 对于宽泛关键词，要求它们是独立词或短语，通过边界检查实现
        broad_match = False
        for keyword in broad_keywords:
            # 检查是否为独立词组，前后有标点、空格或字符串边界
            pattern = r'(^|[\s,，.。!！?？:：;；]){0}($|[\s,，.。!！?？:：;；])'.format(keyword)
            if re.search(pattern, content):
                broad_match = True
                break
        
        # 时间查询条件：匹配特定关键词或独立的宽泛关键词，且不是简单问候语
        is_time_query = (specific_match or broad_match) and not (
                "你好" in content or "早上好" in content or "晚上好" in content or 
                "下午好" in content or "中午好" in content or "嗨" in content)
        
        if is_time_query:
            # 获取当前时间
            now = datetime.now()
            weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            weekday = weekday_names[now.weekday()]
            
            # 格式化时间回复
            time_str = now.strftime("%Y年%m月%d日 %H:%M:%S")
            reply = f"现在是 {time_str}，{weekday}"
            
            logger.info(f"检测到时间查询请求，回复: {reply}")
            return True, reply
            
        return False, None

    # 注释掉_check_memory_query方法
    # def _check_memory_query(self, content: str, username: str, is_group: bool = False, group_id: str = None, sender_name: str = None) -> tuple:
    #     """检查是否是记忆查询请求"""
    #     # 记忆查询关键词
    #     memory_keywords = [
    #         "记得我", "还记得", "记忆中", "之前说过", "上次说", "之前提到", "之前聊过",
    #         "remember me", "remember what", "我们之前", "我之前跟你", "你之前说",
    #         "你记得", "你还记得", "记得什么", "记得多少", "记得我们", "记得我说过",
    #         "记得我告诉过你", "记得我们讨论过", "记得我们聊过", "记得我问过你"
    #     ]
    #     
    #     # 检查是否包含记忆查询关键词
    #     if any(keyword in content.lower() for keyword in memory_keywords):
    #         # 获取相关记忆
    #         memories = self.memory_handler.get_relevant_memories(content, username)
    #         
    #         if memories:
    #             # 构建记忆回复
    #             memory_text = "\n".join([f"- {mem}" for mem in memories[:3]])  # 最多显示3条记忆
    #             reply = f"根据我的记忆，我们之前聊过这些内容：\n{memory_text}"
    #             
    #             if len(memories) > 3:
    #                 reply += f"\n...还有{len(memories)-3}条相关记忆"
    #         else:
    #             reply = "抱歉，我没有找到与此相关的记忆。"
    #         
    #         logger.info(f"检测到记忆查询请求，回复: {reply[:100]}...")
    #         return True, reply
    #         
    #     return False, None

    #以下是onebot QQ方法实现
    def add_to_queue(self, chat_id: str, content: str, sender_name: str,
                     username: str, is_group: bool = False, is_self_message: bool = False):
        """添加消息到队列"""
        with self.queue_lock:
            if chat_id not in self.user_queues:
                self.user_queues[chat_id] = []
            self.user_queues[chat_id].append({
                'content': content,
                'sender_name': sender_name,
                'username': username,
                'is_group': is_group,
                'is_self_message': is_self_message
            })

    def process_messages(self, chat_id: str):
        """处理指定聊天的消息队列"""
        with self.queue_lock:
            if chat_id not in self.user_queues or not self.user_queues[chat_id]:
                return
            message = self.user_queues[chat_id].pop(0)
            
        # 处理消息
        self.handle_user_message(
            message['content'],
            chat_id,
            message['sender_name'],
            message['username'],
            message['is_group'],
            False,  # 不是图像识别
            message['is_self_message']
        )

    def QQ_handle_voice_request(self, content, qqid, sender_name):
        """处理QQ来源的语音请求"""
        logger.info("处理语音请求")
        reply = self.get_api_response(content, qqid)
        if "</think>" in reply:
            reply = reply.split("</think>", 1)[1].strip()

        voice_path = self.voice_handler.generate_voice(reply)
        # 异步保存消息记录
        if voice_path:
            return voice_path
        else:
            return reply

    def QQ_handle_random_image_request(self, content, qqid, sender_name):
        """处理随机图片请求"""
        logger.info("处理随机图片请求")
        image_path = self.image_handler.get_random_image()
        if image_path:

            return image_path
            # 异步保存消息记录
        return None

    def QQ_handle_image_generation_request(self, content, qqid, sender_name):
        """处理图像生成请求"""
        logger.info("处理画图请求")
        try:
            image_path = self.image_handler.generate_image(content)
            if image_path:
                return image_path
            return None
        except:
            return None

    def QQ_handle_text_message(self, content, qqid, sender_name):
        """处理普通文本消息"""
        # 添加正则表达式过滤时间戳
        time_pattern = r'\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\]'
        content = re.sub(time_pattern, '', content)

        # 更通用的模式
        general_pattern = r'\[\d[^\]]*\]|\[\d+\]'
        content = re.sub(general_pattern, '', content)

        logger.info("处理普通文本回复")

        # 定义结束关键词
        end_keywords = [
            "结束", "再见", "拜拜", "下次聊", "先这样", "告辞", "bye", "晚点聊", "回头见",
            "稍后", "改天", "有空聊", "去忙了", "暂停", "待一会儿", "过一会儿", "晚安", "休息",
            "走了", "撤了", "闪了", "不聊了", "断了", "下线", "离开", "停", "歇", "退"
        ]

        # 检查消息中是否包含结束关键词
        is_end_of_conversation = any(keyword in content for keyword in end_keywords)
        
        # 计算用户输入的字符长度，用于动态调整回复长度
        user_input_length = len(content)
        target_length = int(user_input_length * self._calculate_response_length_ratio(user_input_length))
        target_sentences = max(1, min(4, int(target_length / 25)))  # 大约每25个字符一个句子
        
        # 添加长度限制提示词
        length_prompt = f"\n\n请注意：你的回复应当与用户消息的长度相当，控制在约{target_length}个字符和{target_sentences}个句子左右。"
        
        if is_end_of_conversation:
            # 如果检测到结束关键词，在消息末尾添加提示
            content += "\n请以你的身份回应用户的结束语。" + length_prompt
            logger.info(f"检测到对话结束关键词，尝试生成更自然的结束语")
        else:
            # 添加长度限制提示词
            content += length_prompt

        # 获取 API 回复, 需要传入 username
        reply = self.get_api_response(content, qqid)
        if "</think>" in reply:
            think_content, reply = reply.split("</think>", 1)
            logger.info("\n思考过程:")
            logger.info(think_content.strip())
            logger.info(reply.strip())
        else:
            logger.info("\nAI回复:")
            logger.info(reply)

        # 过滤括号内的动作和情感描述
        reply = self._filter_action_emotion(reply)

        try:
            # 使用统一的消息分割方法
            delayed_reply = self._split_message_for_sending(reply)
            
            # 检查回复中是否包含情感关键词并发送表情包
            logger.info("开始检查AI回复的情感关键词")
            emotion_detected = False

            if not hasattr(self.emoji_handler, 'emotion_map'):
                logger.error("emoji_handler 缺少 emotion_map 属性")
                return delayed_reply  # 直接返回分割后的文本，在控制台打印error

            for emotion, keywords in self.emoji_handler.emotion_map.items():
                if not keywords:  # 跳过空的关键词列表
                    continue

                if any(keyword in reply for keyword in keywords):
                    emotion_detected = True
                    logger.info(f"在回复中检测到情感: {emotion}")

                    emoji_path = self.emoji_handler.get_emotion_emoji(reply)
                    if emoji_path:
                        delayed_reply.append(emoji_path)  #在发送消息队列后增加path，由响应器处理
                    else:
                        logger.warning(f"未找到对应情感 {emotion} 的表情包")
                    break

            if not emotion_detected:
                logger.info("未在回复中检测到明显情感")
        except Exception as e:
            logger.error(f"消息处理过程中发生错误: {str(e)}")
            delayed_reply = [reply]  # 出错时使用原始回复
        return delayed_reply

    def _split_message_for_sending(self, reply):
        """将长消息分割为多条发送，并计算实际长度和句数"""
        if not reply:
            return {'parts': [], 'total_length': 0, 'sentence_count': 0}
        
        # 首先清理掉所有可能的历史记忆标记和系统提示
        # 1. 清理历史对话记录部分
        reply = re.sub(r'以下是之前的对话记录：.*?(?=\(以上是历史对话内容)', '', reply, flags=re.DOTALL)
        reply = re.sub(r'\(以上是历史对话内容，[^)]*\)\s*', '', reply)
        # 2. 清理记忆内容部分
        reply = re.sub(r'以下是相关记忆内容：.*?(?=\n\n请结合这些记忆)', '', reply, flags=re.DOTALL)
        # 3. 清理对话标记
        reply = re.sub(r'对话\d+:\s*\n用户:.*?\nAI:.*?(?=\n\n|$)', '', reply, flags=re.DOTALL)
        # 4. 清理系统检索提示
        reply = re.sub(r'检索中\.{3}哔哔！', '', reply)
        # 5. 清理其他系统提示
        reply = re.sub(r'请注意保持自然的回复长度，与用户消息风格协调。', '', reply)
        reply = re.sub(r'请你回应用户的结束语', '', reply)
        # 添加对字数和句子限制提示词的清理
        reply = re.sub(r'请注意：你的回复应当与用户消息的长度相当，控制在约\d+个字符和\d+个句子左右。', '', reply)
        reply = re.sub(r'请简短回复，控制在一两句话内。', '', reply)
        reply = re.sub(r'请保持简洁明了的回复。', '', reply)
        # 6. 清理对方/用户/AI:前缀
        reply = re.sub(r'(^|\n)(?:对方|用户|AI)[:：]', '', reply)
        # 7. 清理时间戳
        reply = re.sub(r'\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(?::\d{2})?\]', '', reply)
        
        # 整理清理后的文本
        reply = reply.strip()
        
        # 1. 先移除文本中的引号，避免引号包裹非动作文本
        reply = reply.replace('"', '').replace('"', '').replace('"', '')
        
        # 2. 保护已经存在的括号内容和颜文字
        protected_parts = {}
        
        # 匹配所有类型的括号及其内容
        bracket_pattern = r'[\(\[（【][^\(\[（【\)\]）】]*[\)\]）】]'
        brackets = list(re.finditer(bracket_pattern, reply))
        
        # 保护已有的括号内容
        for i, match in enumerate(brackets):
            placeholder = f"__PROTECTED_{i}__"
            protected_parts[placeholder] = match.group()
            reply = reply.replace(match.group(), placeholder)
        
        # 保护颜文字 - 使用更宽松的匹配规则
        emoji_patterns = [
            # 常见颜文字组合
            r'\([\w\W]{1,10}?\)',  # 匹配较短的括号内容
            r'（[\w\W]{1,10}?）',  # 中文括号
            r'[＼\\\/\*\-\+\<\>\^\$\%\!\?\@\#\&\|\{\}\=\;\:\,\.]{2,}',  # 常见符号组合
            r'[◕◑◓◒◐•‿\^▽\◡\⌒\◠\︶\ω\´\`\﹏\＾\∀\°\◆\□\▽\﹃\△\≧\≦\⊙\→\←\↑\↓\○\◇\♡\❤\♥\♪\✿\★\☆]{1,}',
            r'\*[\w\W]{1,5}?\*'  # 星号强调内容
        ]
        
        for pattern in emoji_patterns:
            emojis = list(re.finditer(pattern, reply))
            for i, match in enumerate(emojis):
                if len(match.group()) <= 15 and not any(p in match.group() for p in protected_parts.values()):
                    placeholder = f"__EMOJI_{i}__"
                    protected_parts[placeholder] = match.group()
                    reply = reply.replace(match.group(), placeholder)
        
        # 3. 统一处理斜杠/和反斜杠\为$分隔符（排除URL中的斜杠）
        # 处理斜杠/，但避免替换//（URL协议部分）
        reply = re.sub(r'(?<![A-Za-z:])\/(?![\/])', ' $ ', reply)
        
        # 处理反斜杠\，避免替换\\（转义字符）
        reply = re.sub(r'\\(?![\\])', ' $ ', reply)
        
        # 4. 将换行符替换为$分隔符（保留连续的换行符）
        reply = re.sub(r'\n(?!\n)', ' $ ', reply)
        
        # 5. 确保不会有连续的$分隔符出现，并移除多余空格
        reply = re.sub(r'\s*\$\s*\$\s*', ' $ ', reply)
        reply = re.sub(r'\s+\$\s+', ' $ ', reply)
        
        # 6. 恢复所有保护的内容
        for placeholder, content in protected_parts.items():
            reply = reply.replace(placeholder, content)
        
        # 按$分隔符分割
        parts = []
        total_length = 0
        sentence_count = 0
        
        if '$' in reply:
            # 分割消息
            temp_parts = reply.split('$')
            # 处理每个部分
            for i, part in enumerate(temp_parts):
                part = part.strip()
                if not part:  # 跳过空部分
                    continue
                
                # 无论是第几部分，都直接添加，不再添加括号
                parts.append(part)
                
                # 计算长度和句子数
                if i == 0:  # 第一部分通常是主要文本
                    # 检查是否需要进一步按自然句子分割
                    if len(part) > self.MAX_MESSAGE_LENGTH:
                        sub_parts_info = self._split_by_sentences(part)
                        parts = sub_parts_info['parts']  # 替换整个parts
                        total_length = sub_parts_info['total_length']
                        sentence_count = sub_parts_info['sentence_count']
                        break  # 如果第一部分需要分割，就忽略其他部分
                    else:
                        total_length += len(part)
                        # 计算句子数（按句号、感叹号、问号等标点符号）
                        sentence_count += len(re.findall(r'[。！？!?…]+', part)) or 1
                else:
                    total_length += len(part)
                    sentence_count += 1
        else:
            # 如果没有分隔符，按自然句子分割
            split_info = self._split_by_sentences(reply)
            parts = split_info['parts']
            total_length = split_info['total_length']
            sentence_count = split_info['sentence_count']
        
        # 确保至少有一个句子
        if sentence_count == 0 and parts:
            sentence_count = 1
        
        return {'parts': parts, 'total_length': total_length, 'sentence_count': sentence_count}
    
    def _split_by_sentences(self, text):
        """按自然句子分割文本，并返回分割信息"""
        # 只使用句号作为句子结束符
        sentence_ends = ['。']
        
        sentences = []
        total_length = 0
        sentence_count = 0
        current_sentence = ''
        
        i = 0
        while i < len(text):
            char = text[i]
            current_sentence += char
            
            # 检查是否遇到句号
            if char in sentence_ends:
                if current_sentence.strip():
                    # 如果单个句子超过长度限制，需要进一步分割
                    if len(current_sentence) > self.MAX_MESSAGE_LENGTH:
                        # 按固定长度分割，但尽量在标点符号处断开
                        sub_parts_info = self._split_long_sentence(current_sentence)
                        sentences.extend(sub_parts_info['parts'])
                        total_length += sub_parts_info['total_length']
                        sentence_count += sub_parts_info['sentence_count']
                    else:
                        # 移除句尾的句号
                        clean_sentence = current_sentence[:-1].strip()
                        if clean_sentence:
                            sentences.append(clean_sentence)
                            total_length += len(clean_sentence)
                            sentence_count += 1
                current_sentence = ''
            
            i += 1
        
        # 处理最后一个句子
        if current_sentence.strip():
            # 检查最后一个字符是否是句号
            if current_sentence[-1] in sentence_ends:
                current_sentence = current_sentence[:-1]
            
            if len(current_sentence) > self.MAX_MESSAGE_LENGTH:
                sub_parts_info = self._split_long_sentence(current_sentence)
                sentences.extend(sub_parts_info['parts'])
                total_length += sub_parts_info['total_length']
                sentence_count += sub_parts_info['sentence_count']
            else:
                clean_sentence = current_sentence.strip()
                if clean_sentence:
                    sentences.append(clean_sentence)
                    total_length += len(clean_sentence)
                    sentence_count += 1
        
        return {'parts': sentences, 'total_length': total_length, 'sentence_count': sentence_count}
    
    def _split_long_sentence(self, sentence):
        """分割过长的单个句子，并返回分割信息"""
        parts = []
        total_length = 0
        sentence_count = 0
        current_part = ''
        
        # 使用句号、问号、感叹号作为主要断句点
        primary_breaks = ['。', '！', '？','?','!']  # 主要断句点
        
        for char in sentence:
            current_part += char
            current_length = len(current_part)
            
            # 遇到主要断句点时断句
            if char in primary_breaks:
                if current_length >= 5:  # 确保最小句子长度
                    parts.append(current_part.strip())
                    total_length += len(current_part.strip())
                    sentence_count += 1
                    current_part = ''
                continue
            
            # 如果当前部分超过长度限制，强制断句
            if current_length >= self.MAX_MESSAGE_LENGTH:
                parts.append(current_part.strip())
                total_length += len(current_part.strip())
                sentence_count += 1
                current_part = ''
        
        # 处理最后一部分
        if current_part.strip():
            parts.append(current_part.strip())
            total_length += len(current_part.strip())
            sentence_count += 1
        
        return {'parts': parts, 'total_length': total_length, 'sentence_count': sentence_count}

    def _send_split_messages(self, messages, chat_id):
        """发送分割后的消息，支持重试和自然发送节奏"""
        if not messages or not isinstance(messages, dict):
            return False
        
        # 记录已发送的消息，防止重复发送
        sent_messages = set()
        success_count = 0
        
        # 计算自然的发送间隔
        base_interval = 0.5  # 基础间隔时间（秒）
        
        # 检查是否是群聊消息（通过chat_id是否包含群聊标识）
        is_group_chat = False
        sender_name = None
        
        # 从chat_id中提取群聊信息
        if hasattr(self, 'group_chat_memory'):
            is_group_chat = chat_id in self.group_chat_memory.group_chats
            if is_group_chat:
                # 从最近的群聊消息中获取发送者名称
                recent_messages = self.group_chat_memory.get_memory_from_file(chat_id, limit=1)
                if recent_messages:
                    sender_name = recent_messages[0].get('sender_name')
        
        for i, part in enumerate(messages['parts']):
            if part not in sent_messages:
                # 模拟真实用户输入行为
                time.sleep(base_interval)  # 基础间隔
                
                # 如果是群聊消息且有发送者名称，在第一条消息前添加@
                if is_group_chat and sender_name and i == 0:
                    send_content = f"@{sender_name}\u2005{part}"
                else:
                    send_content = part
                
                # 发送消息，支持重试
                success = self._safe_send_msg(send_content, chat_id)
                
                if success:
                    sent_messages.add(part)
                    success_count += 1
                    
                    # 根据消息长度动态调整下一条消息的等待时间
                    wait_time = base_interval + random.uniform(0.3, 0.7) * (len(part) / 50)
                    time.sleep(wait_time)
                else:
                    logger.error(f"发送片段失败: {part[:20]}...")
            else:
                # 不再记录重复内容的日志
                pass
        
        return success_count > 0

    def _send_self_message(self, content: str, chat_id: str):
        """发送主动消息"""
        try:
            # 添加时间戳
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            time_aware_content = f"(此时时间为{current_time}) ta私聊对你说{content}"
            
            # 处理消息
            return self._handle_text_message(
                content=time_aware_content,
                chat_id=chat_id,
                sender_name="System",
                username=chat_id,
                is_group=False,
                is_image_recognition=False
            )
        except Exception as e:
            logger.error(f"发送主动消息失败: {str(e)}")
            return None

    def auto_send_message(self, listen_list, robot_wx_name, get_personality_summary, is_quiet_time, start_countdown):
        """自动发送消息"""
        try:
            # 如果是安静时间，不发送消息
            if is_quiet_time():
                logger.info("当前是安静时间，跳过主动发送")
                return
            
            # 获取当前时间
            current_time = datetime.now()
            
            # 遍历监听列表
            for chat_id in listen_list:
                try:
                    # 检查是否需要发送消息
                    if chat_id not in self.unanswered_counters:
                        self.unanswered_counters[chat_id] = 0
                    
                    # 获取未回复计数
                    unanswered_count = self.unanswered_counters[chat_id]
                    
                    # 如果未回复计数大于0，可能需要主动发送消息
                    if unanswered_count > 0:
                        # 获取上次回复时间
                        last_reply_time = self.ai_last_reply_time.get(chat_id, 0)
                        time_since_last_reply = current_time.timestamp() - last_reply_time
                        
                        # 如果距离上次回复超过30分钟，可以考虑主动发送
                        if time_since_last_reply > 1800:  # 30分钟 = 1800秒
                            # 获取性格摘要
                            personality = get_personality_summary()
                            
                            # 构建提示词
                            prompt = f"根据我的性格特点：{personality}，"
                            prompt += "请生成一条自然的主动问候语或关心语，要简短自然，不要过于刻意。"
                            
                            # 获取API回复
                            reply = self.get_api_response(prompt, chat_id)
                            
                            if reply:
                                # 发送消息
                                self._send_self_message(reply, chat_id)
                                
                                # 重置计数器
                                self.unanswered_counters[chat_id] = 0
                                
                                # 更新最后回复时间
                                self.ai_last_reply_time[chat_id] = current_time.timestamp()
                                
                                logger.info(f"已向 {chat_id} 发送主动消息")
                                
                                # 随机等待5-15秒再处理下一个
                                time.sleep(random.uniform(5, 15))
                
                except Exception as e:
                    logger.error(f"处理聊天 {chat_id} 的主动消息失败: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"自动发送消息失败: {str(e)}")

    def increase_unanswered_counter(self, username):
        """增加未回复计数器"""
        try:
            if username not in self.unanswered_counters:
                self.unanswered_counters[username] = 0
            
            self.unanswered_counters[username] += 1
            logger.info(f"增加用户 {username} 的未回复计数器: {self.unanswered_counters[username]}")
        except Exception as e:
            logger.error(f"增加未回复计数器失败: {str(e)}")

    def _init_performance_metrics(self):
        """初始化性能监控指标"""
        if not hasattr(self, '_performance_metrics'):
            self._performance_metrics = {
                'api_calls': 0,
                'api_errors': 0,
                'api_response_times': [],
                'message_count': 0,
                'avg_message_length': 0,
                'avg_response_length': 0,
                'start_time': time.time()
            }

    def _update_metrics(self, metric_type, value=None):
        """更新性能指标"""
        if not hasattr(self, '_performance_metrics'):
            self._init_performance_metrics()
        
        if metric_type == 'api_call':
            self._performance_metrics['api_calls'] += 1
        elif metric_type == 'api_error':
            self._performance_metrics['api_errors'] += 1
        elif metric_type == 'api_response_time' and value is not None:
            self._performance_metrics['api_response_times'].append(value)
        elif metric_type == 'message':
            self._performance_metrics['message_count'] += 1
        elif metric_type == 'message_length' and value is not None:
            # 更新平均消息长度
            current_avg = self._performance_metrics['avg_message_length']
            count = self._performance_metrics['message_count']
            self._performance_metrics['avg_message_length'] = (current_avg * (count - 1) + value) / count
        elif metric_type == 'response_length' and value is not None:
            # 更新平均回复长度
            current_avg = self._performance_metrics['avg_response_length']
            count = self._performance_metrics['message_count']
            self._performance_metrics['avg_response_length'] = (current_avg * (count - 1) + value) / count

    def get_performance_stats(self):
        """获取性能统计信息"""
        if not hasattr(self, '_performance_metrics'):
            self._init_performance_metrics()
        
        metrics = self._performance_metrics
        runtime = time.time() - metrics['start_time']
        hours = runtime // 3600
        minutes = (runtime % 3600) // 60
        seconds = runtime % 60
        
        # 计算API响应时间统计
        api_times = metrics['api_response_times']
        avg_api_time = sum(api_times) / len(api_times) if api_times else 0
        
        stats = {
            'runtime': f"{int(hours)}小时{int(minutes)}分{int(seconds)}秒",
            'message_count': metrics['message_count'],
            'api_calls': metrics['api_calls'],
            'api_errors': metrics['api_errors'],
            'api_error_rate': f"{(metrics['api_errors'] / metrics['api_calls'] * 100) if metrics['api_calls'] > 0 else 0:.2f}%",
            'avg_api_response_time': f"{avg_api_time:.2f}秒",
            'avg_message_length': f"{metrics['avg_message_length']:.1f}字符",
            'avg_response_length': f"{metrics['avg_response_length']:.1f}字符",
            'messages_per_hour': f"{(metrics['message_count'] / (runtime / 3600)) if runtime > 0 else 0:.1f}"
        }
        
        return stats

    def process_message_for_user(self, user_id, force=False):
        """处理用户消息队列"""
        with self.queue_lock:
            if not hasattr(self, 'message_queues'):
                self.message_queues = {}  # 初始化消息队列字典
                
            if user_id not in self.message_queues:
                if self.is_debug and force:
                    logger.info(f"调试模式：用户 {user_id} 的消息队列为空")
                    # 在调试模式下，为空队列时直接处理输入
                    if force:
                        return self._handle_text_message(
                            "你好，这是测试消息",  # 默认测试消息
                            "debug_chat",
                            "debug_user",
                            user_id,
                            False
                        )
                return
                
            # 获取队列
            message_data = self.message_queues[user_id]
            messages = message_data["messages"]
            
            if not messages:
                # 清除空队列
                del self.message_queues[user_id]
                return
                
            # 提取信息
            chat_id = message_data.get("chat_id")
            sender_name = message_data.get("sender_name", "用户")
            username = message_data.get("username", user_id)
            is_group = message_data.get("is_group", False)
            
            # 合并消息
            combined_message = " ".join(messages)
            
            # 清空队列
            del self.message_queues[user_id]
        
        # 调试模式下特殊处理
        if self.is_debug:
            logger.info(f"\n[调试模式] 正在处理消息: {combined_message}")
        
        # 处理合并后的消息
        reply = self._handle_text_message(
            combined_message,
            chat_id,
            sender_name,
            username,
            is_group
        )
        
        # 调试模式下确保返回值
        if self.is_debug and not reply:
            return ["[调试模式] 没有生成回复"]
        
        return reply

    def handle_message(self, message: str, user_id: str = None, group_id: str = None, is_debug: bool = False):
        """
        处理接收到的消息
        
        Args:
            message: 接收到的消息内容
            user_id: 发送者ID
            group_id: 群组ID（如果有）
            is_debug: 是否为调试模式
        
        Returns:
            响应消息
        """
        try:
            # 检查是否为重要记忆（集成关键记忆检测）
            if hasattr(self, 'memory_handler') and self.memory_handler:
                self.memory_handler.check_important_memory(message, user_id)
            
            # 获取响应
            response = self.get_api_response(message, user_id, group_id)
            
            # 发送响应
            if is_debug:
                # 调试模式下的处理
                print(f"AI响应: {response}")
            else:
                # 实际生产环境下的发送逻辑
                self.send_response(response, user_id, group_id)
                
            return response
        except Exception as e:
            logger.error(f"处理消息失败: {str(e)}")
            return f"处理消息时出错: {str(e)}"

    def send_wx_message(self, response: str, user_id: str, group_id: str = None):
        """发送微信消息"""
        # ... 现有代码保持不变 ...
        
        # 这里可以添加统计或其他处理逻辑
        if hasattr(self, 'memory_handler') and self.memory_handler and hasattr(self.memory_handler, 'short_term_memory'):
            # 仅显示嵌入缓存统计（可选）
            try:
                embedding_model = self.memory_handler.short_term_memory.rag.embedding_model
                if hasattr(embedding_model, 'get_cache_stats'):
                    stats = embedding_model.get_cache_stats()
                    logger.info(f"嵌入缓存统计: 大小={stats['cache_size']}, 命中率={stats['hit_rate_percent']:.1f}%")
            except Exception as e:
                logger.debug(f"获取嵌入缓存统计失败: {str(e)}")

    def _clean_memory_content(self, content: str) -> str:
        """清理记忆内容中的系统提示词和特殊标记"""
        if not content:
            return ""
            
        # 清理系统提示词和标记
        patterns_to_remove = [
            r'\[系统提示\].*?\[/系统提示\]',
            r'\[系统指令\].*?\[/系统指令\]',
            r'请注意：.*?(?=\n|$)',
            r'以下是之前的对话记录：.*?(?=\n\n)',
            r'\(以上是历史对话内容[^)]*\)',
            r'memory_number:.*?(?=\n|$)',
            r'\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(?::\d{2})?\]',
            r'ta(?:私聊|在群聊里)对你说[：:]\s*',
            r'^你：|^对方：|^AI：',
            r'请(?:简短|简洁)回复.*?(?=\n|$)',
            r'请.*?控制在.*?(?=\n|$)',
            r'请你回应用户的结束语'
        ]
        
        cleaned = content
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL|re.IGNORECASE)
        
        # 移除多余的空白字符
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()

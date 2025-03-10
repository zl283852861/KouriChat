"""
消息处理模块
负责处理聊天消息，包括:
- 消息队列管理
- 消息分发处理
- API响应处理
- 多媒体消息处理
- 对话结束处理
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from openai import OpenAI
from wxauto import WeChat
from services.database import Session, ChatMessage
import random
import os
from services.ai.llm_service import LLMService
from handlers.memory import MemoryHandler
from config import config
import re

# 修改logger获取方式，确保与main模块一致
logger = logging.getLogger('main')

class MessageHandler:
    def __init__(self, root_dir, api_key, base_url, model, max_token, temperature, 
                 max_groups, robot_name, prompt_content, image_handler, emoji_handler, voice_handler, memory_handler):
        self.root_dir = root_dir
        self.api_key = api_key
        self.model = model
        self.max_token = max_token
        self.temperature = temperature
        self.max_groups = max_groups
        self.robot_name = robot_name
        self.prompt_content = prompt_content
        
        # 使用 DeepSeekAI 替换直接的 OpenAI 客户端
        self.deepseek = LLMService(
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_token=max_token,
            temperature=temperature,
            max_groups=max_groups
        )
        
        # 消息队列相关
        self.user_queues = {}
        self.queue_lock = threading.Lock()
        self.chat_contexts = {}
        
        # 微信实例
        self.wx = WeChat()

        # 添加 handlers
        self.image_handler = image_handler
        self.emoji_handler = emoji_handler
        self.voice_handler = voice_handler
        self.memory_handler = memory_handler
        self.unanswered_counters = {}
        self.unanswered_timers = {}  # 新增：存储每个用户的计时器

    def save_message(self, sender_id: str, sender_name: str, message: str, reply: str):
        """保存聊天记录到数据库和短期记忆"""
        try:
            session = Session()
            chat_message = ChatMessage(
                sender_id=sender_id,
                sender_name=sender_name,
                message=message,
                reply=reply
            )
            session.add(chat_message)
            session.commit()
            session.close()
            # 新增短期记忆保存
            self.memory_handler.add_short_memory(message, reply)
        except Exception as e:
            logger.error(f"保存消息失败: {str(e)}", exc_info=True)

    def get_api_response(self, message: str, user_id: str) -> str:
        """获取 API 回复（含记忆增强）"""
        avatar_dir = os.path.join(self.root_dir, config.behavior.context.avatar_dir)
        prompt_path = os.path.join(avatar_dir, "avatar.md")
        original_content = ""

        try:
            # 步骤1：读取原始提示内容
            with open(prompt_path, "r", encoding="utf-8") as f:
                original_content = f.read()
                logger.debug(f"原始提示文件大小: {len(original_content)} bytes")

            # 步骤2：获取相关记忆并构造临时提示
            relevant_memories = self.memory_handler.get_relevant_memories(message)
            memory_prompt = "\n# 动态记忆注入\n" + "\n".join(relevant_memories) if relevant_memories else ""
            logger.debug(f"注入记忆条数: {len(relevant_memories)}")

            # 步骤3：写入临时记忆
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(f"{original_content}\n{memory_prompt}")

            # 步骤4：确保文件内容已刷新
            with open(prompt_path, "r", encoding="utf-8") as f:
                full_prompt = f.read()
                logger.debug(f"临时提示内容样例:\n{full_prompt[:200]}...")  # 显示前200字符

            # 调用API
            return self.deepseek.get_response(message, user_id, full_prompt)

        except Exception as e:
            logger.error(f"动态记忆注入失败: {str(e)}")
            return self.deepseek.get_response(message, user_id, original_content)  # 降级处理

        finally:
            # 步骤5：恢复原始内容（无论是否出错）
            try:
                with open(prompt_path, "w", encoding="utf-8") as f:
                    f.write(original_content)
            except Exception as restore_error:
                logger.error(f"恢复提示文件失败: {str(restore_error)}")

    def handle_user_message(self, content: str, chat_id: str, sender_name: str, 
                     username: str, is_group: bool = False, is_image_recognition: bool = False):
        """统一的消息处理入口"""
        try:
            logger.info(f"处理消息 - 发送者: {sender_name}, 聊天ID: {chat_id}, 是否群聊: {is_group}")
            logger.info(f"消息内容: {content}")
            
            # 检查是否为语音请求
            if self.voice_handler.is_voice_request(content):
                return self._handle_voice_request(content, chat_id, sender_name, username, is_group)
                
            # 检查是否为随机图片请求
            elif self.image_handler.is_random_image_request(content):
                return self._handle_random_image_request(content, chat_id, sender_name, username, is_group)
                
            # 检查是否为图像生成请求，但跳过图片识别结果
            elif not is_image_recognition and self.image_handler.is_image_generation_request(content):
                return self._handle_image_generation_request(content, chat_id, sender_name, username, is_group)
                
            # 处理普通文本回复
            else:
                return self._handle_text_message(content, chat_id, sender_name, username, is_group)
                
        except Exception as e:
            logger.error(f"处理消息失败: {str(e)}", exc_info=True)
            return None

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

        # 异步保存消息记录
        threading.Thread(target=self.save_message,
                       args=(username, sender_name, content, reply)).start()
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

            # 异步保存消息记录
            threading.Thread(target=self.save_message,
                           args=(username, sender_name, content, reply)).start()
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

            # 异步保存消息记录
            threading.Thread(target=self.save_message,
                           args=(username, sender_name, content, reply)).start()
            return reply
        return None

    def _handle_text_message(self, content, chat_id, sender_name, username, is_group):
        """处理普通文本消息"""
        # 添加正则表达式过滤时间戳
        time_pattern = r'\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\]'
        content = re.sub(time_pattern, '', content)
        
        # 更通用的模式
        general_pattern = r'\[\d[^\]]*\]|\[\d+\]'
        content = re.sub(general_pattern, '', content)
        
        logger.info("处理普通文本回复")

        # 获取或初始化未回复计数器
        counter = self.unanswered_counters.get(username, 0)

        # 定义结束关键词
        end_keywords = [
            "结束", "再见", "拜拜", "下次聊", "先这样", "告辞", "bye", "晚点聊", "回头见",
            "稍后", "改天", "有空聊", "去忙了", "暂停", "待会儿", "过会儿", "晚安", "休息",
            "走了", "撤了", "闪了", "不聊了", "断了", "下线", "离开", "停", "歇", "退"
        ]

        # 检查消息中是否包含结束关键词
        is_end_of_conversation = any(keyword in content for keyword in end_keywords)
        if is_end_of_conversation:
            # 如果检测到结束关键词，在消息末尾添加提示
            content += "\n请以你的身份回应用户的结束语。"
            logger.info(f"检测到对话结束关键词，尝试生成更自然的结束语")

        # 获取 API 回复, 需要传入 username
        reply = self.get_api_response(content, chat_id)
        if "</think>" in reply:
            think_content, reply = reply.split("</think>", 1)
            logger.info("\n思考过程:")
            logger.info(think_content.strip())
            logger.info(reply.strip())
        else:
            logger.info("\nAI回复:") 
            logger.info(reply) 

        if is_group:
            reply = f"@{sender_name} {reply}"

        try:
            # 增强型智能分割器
            delayed_reply = []
            current_sentence = []
            ending_punctuations = {'。', '！', '？', '!', '?', '…', '……'}
            split_symbols = {'\\', '|', '￤'}  # 支持多种手动分割符

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

            # 检查回复中是否包含情感关键词并发送表情包
            logger.info("开始检查AI回复的情感关键词")
            emotion_detected = False

        
            if not hasattr(self.emoji_handler, 'emotion_map'):
                logger.error("emoji_handler 缺少 emotion_map 属性")
                return reply

            for emotion, keywords in self.emoji_handler.emotion_map.items():
                if not keywords:  # 跳过空的关键词列表
                    continue

                if any(keyword in reply for keyword in keywords):
                    emotion_detected = True
                    logger.info(f"在回复中检测到情感: {emotion}")

                    emoji_path = self.emoji_handler.get_emotion_emoji(reply)
                    if emoji_path:
                        try:
                            self.wx.SendFiles(filepath=emoji_path, who=chat_id)
                            logger.info(f"已发送情感表情包: {emoji_path}")
                        except Exception as e:
                            logger.error(f"发送表情包失败: {str(e)}")
                    else:
                        logger.warning(f"未找到对应情感 {emotion} 的表情包")
                    break

            if not emotion_detected:
                logger.info("未在回复中检测到明显情感")

        except Exception as e:
            logger.error(f"消息处理过程中发生错误: {str(e)}")

        # 异步保存消息记录
        threading.Thread(target=self.save_message,
                         args=(username, sender_name, content, reply)).start()
         # 重置计数器（如果大于0）
        if self.unanswered_counters.get(username, 0) > 0:
            self.unanswered_counters[username] = 0
            logger.info(f"用户 {username} 的未回复计数器已重置")


        return reply

    def increase_unanswered_counter(self, username: str):
        """增加未回复计数器"""
        with self.queue_lock:
            if username in self.unanswered_counters:
                self.unanswered_counters[username] += 1
            else:
                self.unanswered_counters[username] = 1
            logger.info(f"用户 {username} 的未回复计数器增加到 {self.unanswered_counters[username]}")


    def add_to_queue(self, chat_id: str, content: str, sender_name: str,
                    username: str, is_group: bool = False):
        """添加消息到队列（已废弃，保留兼容）"""
        logger.info("直接处理消息，跳过队列")
        return self.handle_user_message(content, chat_id, sender_name, username, is_group)

    def process_messages(self, chat_id: str):
        """处理消息队列中的消息（已废弃，保留兼容）"""
        logger.warning("process_messages方法已废弃，使用handle_message代替")
        pass

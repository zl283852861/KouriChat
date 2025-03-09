import os
import logging
import random
from typing import List
from datetime import datetime
from src.services.ai.llm_service import LLMService
from textblob import TextBlob

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
                 max_token: int, temperature: float, max_groups: int):
        # 保持原有初始化参数
        self.root_dir = root_dir
        self.memory_dir = os.path.join(root_dir, "data", "memory")
        self.short_memory_path = os.path.join(self.memory_dir, "short_memory.txt")
        self.long_memory_buffer_path = os.path.join(self.memory_dir, "long_memory_buffer.txt")
        self.high_priority_memory_path = os.path.join(self.memory_dir, "high_priority_memory.txt") # 新增
        self.api_key = api_key
        self.base_url = base_url
        self.max_token = max_token
        self.temperature = temperature
        self.max_groups = max_groups
        self.model = model

        # 新增记忆层
        self.memory_layers = {
            'working': os.path.join(self.memory_dir, "working_memory.txt")
        }

        # 初始化文件和目录
        os.makedirs(self.memory_dir, exist_ok=True)
        self._init_files()

        # 新增：情感权重
        self.emotion_weights = {
            'neutral': 1,
            'happy': 2,
            'sad': 2,
            'anger': 3,  # 愤怒情绪权重更高
            'surprise': 2,
            'fear': 2,
            'disgust': 2,
        }

        # 新增： 消息重复计数
        self.memory_counts = {}

    def _init_files(self):
        """初始化所有记忆文件"""
        files_to_check = [
            self.short_memory_path,
            self.long_memory_buffer_path,
            self.high_priority_memory_path, # 新增
            *self.memory_layers.values()
        ]
        for f in files_to_check:
            if not os.path.exists(f):
                with open(f, "w", encoding="utf-8") as _:
                    logger.info(f"创建文件: {os.path.basename(f)}")

    def _get_deepseek_client(self):
        """获取LLM客户端（保持原有逻辑）"""
        return LLMService(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            max_token=self.max_token,
            temperature=self.temperature,
            max_groups=self.max_groups
        )

    def add_short_memory(self, message: str, reply: str):
        """添加短期记忆（兼容原有调用）"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            logger.debug(f"开始写入短期记忆文件: {self.short_memory_path}")
            with open(self.short_memory_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] 用户: {message}\n")
                f.write(f"[{timestamp}] bot: {reply}\n\n")
            logger.info(f"成功写入短期记忆: 用户 - {message}, bot - {reply}")
        except Exception as e:
            logger.error(f"写入短期记忆文件失败: {str(e)}", exc_info=True)

        # 检查是否包含关键词, 并获取情感
        emotion = self._detect_emotion(message)
        if any(keyword in message for keyword in KEYWORDS) or emotion != 'neutral':
            self._add_high_priority_memory(message, emotion) # 传入 emotion

        # 增加消息的重复计数 (这里为了简化，直接使用原消息作为 key)
        if message in self.memory_counts:
            self.memory_counts[message] += 1
        else:
            self.memory_counts[message] = 1
        logger.info(f"消息 '{message}' 的重复计数: {self.memory_counts[message]}")

    def _add_high_priority_memory(self, message: str, emotion: str): # 修改
        """添加高优先级记忆"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            high_priority_path = os.path.join(self.memory_dir, "high_priority_memory.txt")
            logger.info(f"开始写入高优先级记忆文件: {high_priority_path}")
            with open(high_priority_path, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] 情感: {emotion}, 消息: {message}\n") # 写入情感
            logger.info(f"成功写入高优先级记忆: {message}")
        except Exception as e:
            logger.error(f"写入高优先级记忆文件失败: {str(e)}", exc_info=True)

    def _detect_emotion(self, text: str) -> str: # 新增
        """情感分析"""
        # 这里只是简单示例, 实际应用中需要更强大的情感分析模型
        analysis = TextBlob(text)
        # 使用 TextBlob 的情感极性 (polarity) 和主观性 (subjectivity)
        polarity = analysis.sentiment.polarity
        subjectivity = analysis.sentiment.subjectivity

        # 根据极性和主观性判断情感
        if polarity > 0.5 and subjectivity > 0.5:
            return 'happy'
        elif polarity > 0 and subjectivity > 0.5:
            return 'happy'
        elif polarity < -0.5 and subjectivity > 0.5:
            return 'anger'  # 强烈的负面情感
        elif polarity < 0 and subjectivity > 0.5:
            return 'sad'
        elif -0.5 <= polarity <= 0.5 and subjectivity > 0.5:
            return 'surprise'
        elif polarity < -0.3 and subjectivity < 0.5:  # 区分 fear 和 disgust
            return 'fear'
        elif polarity < 0 and subjectivity < 0.5:
            return 'disgust'
        else:
            return 'neutral'

    def summarize_memories(self):
        """总结短期记忆到长期记忆（保持原有逻辑）"""
        if not os.path.exists(self.short_memory_path):
            logger.debug("短期记忆文件不存在，跳过总结")
            return

        with open(self.short_memory_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if len(lines) >= 30:  # 15组对话
            max_retries = 3  # 最大重试次数
            retries = 0
            while retries < max_retries:
                try:
                    deepseek = self._get_deepseek_client()
                    # 优化提示，更明确地指示LLM考虑情感和重复
                    prompt = (
                        "请将以下对话记录总结为最重要的几条长期记忆，总结内容应包含地点，事件，人物（如果对话记录中有的话）用中文简要表述。\n"
                        "注意：请特别关注以下几点：\n"
                        "1. 具有强烈情感的消息（如愤怒、高兴）应优先考虑。\n"
                        "2. 被多次提及的消息应优先考虑。\n"
                        "3. 包含关键词（如 '记住'、'别忘了' 等）的消息应优先考虑。\n\n"
                        "对话记录：\n" + "".join(lines[-30:])
                    )
                    summary = deepseek.get_response(
                        message=prompt,
                        user_id="system",
                        system_prompt="总结以下对话："  # 可以保留之前的 system_prompt
                    )
                    logger.debug(f"总结结果:\n{summary}")

                    # 检查是否需要重试
                    retry_sentences = [
                        "好像有些小状况，请再试一次吧～",
                        "信号好像不太稳定呢（皱眉）",
                        "思考被打断了，请再说一次好吗？"
                    ]
                    if summary in retry_sentences:
                        logger.warning(f"收到需要重试的总结结果: {summary}")
                        retries += 1
                        continue

                    # 写入长期记忆缓冲区
                    date = datetime.now().strftime('%Y-%m-%d')
                    try:
                        logger.debug(f"开始写入长期记忆缓冲区文件: {self.long_memory_buffer_path}")
                        with open(self.long_memory_buffer_path, "a", encoding="utf-8") as f:
                            f.write(f"总结日期: {date}\n")
                            f.write(summary + "\n\n")
                        logger.info(f"成功将总结结果写入长期记忆缓冲区: {summary}")
                    except Exception as e:
                        logger.error(f"写入长期记忆缓冲区文件失败: {str(e)}", exc_info=True)

                    # 清空短期记忆
                    try:
                        logger.debug(f"开始清空短期记忆文件: {self.short_memory_path}")
                        open(self.short_memory_path, "w").close()
                        logger.info("记忆总结完成，已写入长期记忆缓冲区，短期记忆已清空")
                    except Exception as e:
                        logger.error(f"清空短期记忆文件失败: {str(e)}", exc_info=True)
                    break  # 成功后退出循环

                except Exception as e:
                    logger.error(f"记忆总结失败: {str(e)}")
                    retries += 1
                    if retries >= max_retries:
                        logger.error("达到最大重试次数，放弃总结")
                        break

    def get_relevant_memories(self, query: str) -> List[str]:
        """获取相关记忆（增加调试日志）"""
        if not os.path.exists(self.long_memory_buffer_path):
            logger.warning("长期记忆缓冲区不存在，尝试创建...")
            try:
                with open(self.long_memory_buffer_path, "w", encoding="utf-8"):
                    logger.info("长期记忆缓冲区文件已创建。")
            except Exception as e:
                logger.error(f"创建长期记忆缓冲区文件失败: {str(e)}")
                return []

        # 调试：打印文件路径
        logger.debug(f"长期记忆缓冲区文件路径: {self.long_memory_buffer_path}")

        max_retries = 3  # 设置最大重试次数
        for retry_count in range(max_retries):
            try:
                with open(self.long_memory_buffer_path, "r", encoding="utf-8") as f:
                    memories = [line.strip() for line in f if line.strip()]

                # 调试：打印文件内容
                logger.debug(f"长期记忆缓冲区条目数: {len(memories)}")

                if not memories:
                    logger.debug("长期记忆缓冲区为空")
                    return []

                deepseek = self._get_deepseek_client()
                response = deepseek.get_response(
                    message="\n".join(memories[-20:]),
                    user_id="retrieval",
                    system_prompt=f"请从以下记忆中找到与'{query}'最相关的条目，按相关性排序返回最多3条:"
                )

                # 调试：打印模型响应
                logger.debug(f"模型返回相关记忆条数: {len(response.splitlines())}")

                # 检查是否需要重试
                retry_sentences = [
                    "好像有些小状况，请再试一次吧～",
                    "信号好像不太稳定呢（皱眉）",
                    "思考被打断了，请再说一次好吗？"
                ]
                if response in retry_sentences:
                    if retry_count < max_retries - 1:
                        logger.warning(f"第 {retry_count + 1} 次重试：收到需要重试的响应: {response}")
                        continue  # 重试
                    else:
                        logger.error(f"达到最大重试次数：最后一次响应为 {response}")
                        return []
                else:
                    # 返回处理后的响应
                    return [line.strip() for line in response.split("\n") if line.strip()]

            except Exception as e:
                logger.error(f"第 {retry_count + 1} 次尝试失败: {str(e)}")
                if retry_count < max_retries - 1:
                    continue
                else:
                    logger.error(f"达到最大重试次数: {str(e)}")
                return []

        return []

    def maintain_memories(self, max_entries=100):
        """记忆文件维护"""
        # 长期记忆轮替
        if os.path.getsize(self.long_memory_buffer_path) > 1024 * 1024:  # 1MB
            try:
                logger.debug(f"开始维护长期记忆缓冲区文件: {self.long_memory_buffer_path}")
                with open(self.long_memory_buffer_path, 'r+', encoding='utf-8') as f:
                    lines = f.readlines()
                    keep_lines = lines[-max_entries * 2:]  # 保留最后N条
                    f.seek(0)
                    f.writelines(keep_lines)
                    f.truncate()
                logger.info("已完成长期记忆维护")
            except Exception as e:
                logger.error(f"长期记忆维护失败: {str(e)}", exc_info=True)

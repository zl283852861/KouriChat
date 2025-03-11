import os
import logging
import random
from typing import List
from datetime import datetime
from src.services.ai.llm_service import LLMService
import jieba

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
        self.api_key = api_key
        self.base_url = base_url
        self.max_token = max_token
        self.temperature = temperature
        self.max_groups = max_groups
        self.model = model


        # 初始化文件和目录
        os.makedirs(self.memory_dir, exist_ok=True)
        self._init_files()

    def _init_files(self):
        """初始化所有记忆文件"""
        files_to_check = [
            self.short_memory_path,
            self.long_memory_buffer_path
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
            # 新增情感标记
            emotion = self._detect_emotion(message)
            logger.debug(f"开始写入短期记忆文件: {self.short_memory_path},emotion:{emotion}")
            with open(self.short_memory_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] 用户: {message}\n")
                f.write(f"[{timestamp}] bot: {reply}\n\n")
            logger.info(f"成功写入短期记忆: 用户 - {message}, bot - {reply}")
        except Exception as e:
            logger.error(f"写入短期记忆文件失败: {str(e)}")

        # 检查是否包含关键词
        if any(keyword in message for keyword in KEYWORDS):
            self._add_high_priority_memory(message)

    def _add_high_priority_memory(self, message: str):
        """添加高优先级记忆"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            high_priority_path = os.path.join(self.memory_dir, "high_priority_memory.txt")
            logger.debug(f"开始写入高优先级记忆文件: {high_priority_path}")
            with open(high_priority_path, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] 高优先级: {message}\n")
            logger.info(f"成功写入高优先级记忆: {message}")
        except Exception as e:
            logger.error(f"写入高优先级记忆文件失败: {str(e)}")

    def _detect_emotion(self, text: str) -> str:
        """基于词典的情感分析"""

        # 加载情感词典
        positive_words = self._load_wordlist('src/handlers/emodata/正面情绪词.txt')
        negative_words = self._load_wordlist('src/handlers/emodata/负面情绪词.txt')
        negation_words = self._load_wordlist('src/handlers/emodata/否定词表.txt')
        degree_words = self._load_wordlist('src/handlers/emodata/程度副词.txt')

        # 修正程度副词
        degree_dict = {}
        for word in degree_words:
            parts = word.strip().split(',')  # 假设格式为 "词语,权重"
            if len(parts) == 2:
                degree_dict[parts[0].strip()] = float(parts[1].strip())

        # 分词
        words = list(jieba.cut(text))

        # 情感计算
        score = 0
        negation_count = 0  # 否定词计数
        for i, word in enumerate(words):
            if word in positive_words:
                # 考虑程度副词
                degree = 1.0
                for j in range(i - 1, max(-1, i - 4), -1):  # 向前查找最多3个词
                    if words[j] in degree_dict:
                        degree *= degree_dict[words[j]]
                        break
                # 考虑否定词
                if negation_count % 2 == 1:
                    degree *= -1.0
                score += degree

            elif word in negative_words:
                degree = 1.0
                for j in range(i - 1, max(-1, i - 4), -1):
                    if words[j] in degree_dict:
                        degree *= degree_dict[words[j]]
                        break

                if negation_count % 2 == 1:
                    degree *= -1.0
                score -= degree

            elif word in negation_words:
                negation_count += 1

        # 情感分类
        if score > 0.5:
            return 'happy'
        elif score < -0.5:
            return 'anger'  # 负面情绪比较强烈
        elif -0.5 <= score <= 0.5:
            return 'neutral'
        else:
            return 'sad'  # 负面情绪

    def _load_wordlist(self, filepath: str) -> List[str]:
        """加载词表文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.error(f"加载词表文件失败: {filepath} - {str(e)}")
            return []

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
                    summary = deepseek.get_response(
                        message="".join(lines[-30:]),
                        user_id="system",
                        system_prompt="请将以下对话记录总结为最重要的几条长期记忆，总结内容应包含地点，事件，人物（如果对话记录中有的话）用中文简要表述："
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
                        logger.error(f"写入长期记忆缓冲区文件失败: {str(e)}")

                    # 清空短期记忆
                    try:
                        logger.debug(f"开始清空短期记忆文件: {self.short_memory_path}")
                        open(self.short_memory_path, "w").close()
                        logger.info("记忆总结完成，已写入长期记忆缓冲区，短期记忆已清空")
                    except Exception as e:
                        logger.error(f"清空短期记忆文件失败: {str(e)}")
                    break  # 成功后退出循环

                except Exception as e:
                    logger.error(f"记忆总结失败: {str(e)}")
                    retries += 1
                    if retries >= max_retries:
                        logger.error("达到最大重试次数，放弃总结")
                        break

    def get_relevant_memories(self, query: str) -> List[str]:
        """获取相关记忆（增加调试日志）"""
        # 检查高优先级记忆文件是否存在
        high_priority_path = os.path.join(self.memory_dir, "high_priority_memory.txt")
        high_priority_memories = []
        
        # 尝试读取高优先级记忆
        if os.path.exists(high_priority_path):
            try:
                with open(high_priority_path, "r", encoding="utf-8") as f:
                    high_priority_memories = [line.strip() for line in f if line.strip()]
                logger.debug(f"高优先级记忆数量: {len(high_priority_memories)}")
            except Exception as e:
                logger.error(f"读取高优先级记忆文件失败: {str(e)}")
        
        # 检查长期记忆缓冲区是否存在
        if not os.path.exists(self.long_memory_buffer_path):
            logger.warning("长期记忆缓冲区不存在，尝试创建...")
            try:
                with open(self.long_memory_buffer_path, "w", encoding="utf-8"):
                    logger.info("长期记忆缓冲区文件已创建。")
            except Exception as e:
                logger.error(f"创建长期记忆缓冲区文件失败: {str(e)}")
                # 如果有高优先级记忆，仍然返回
                if high_priority_memories:
                    # 筛选与查询相关的高优先级记忆
                    relevant_high_priority = self._filter_relevant_memories(high_priority_memories, query)
                    if relevant_high_priority:
                        logger.info(f"返回 {len(relevant_high_priority)} 条高优先级相关记忆")
                        return relevant_high_priority
                return []

        # 调试：打印文件路径
        logger.debug(f"长期记忆缓冲区文件路径: {self.long_memory_buffer_path}")

        max_retries = 3  # 设置最大重试次数
        for retry_count in range(max_retries):
            try:
                # 读取长期记忆
                with open(self.long_memory_buffer_path, "r", encoding="utf-8") as f:
                    long_memories = [line.strip() for line in f if line.strip()]

                # 调试：打印文件内容
                logger.debug(f"长期记忆缓冲区内容数量: {len(long_memories)}")

                # 如果没有任何记忆，但有高优先级记忆，则返回高优先级记忆
                if not long_memories and not high_priority_memories:
                    logger.debug("所有记忆缓冲区为空")
                    return []
                
                # 构建优先级记忆列表
                # 1. 高优先级记忆（权重最高）
                # 2. 长期记忆（权重中等）
                prioritized_memories = []
                
                # 筛选与查询相关的高优先级记忆
                if high_priority_memories:
                    relevant_high_priority = self._filter_relevant_memories(high_priority_memories, query)
                    if relevant_high_priority:
                        prioritized_memories.extend(relevant_high_priority)
                        logger.info(f"添加了 {len(relevant_high_priority)} 条高优先级相关记忆")
                
                # 如果已经有足够的高优先级记忆，可以直接返回
                if len(prioritized_memories) >= 3:
                    logger.info("高优先级记忆足够，直接返回")
                    return prioritized_memories[:3]  # 最多返回3条
                
                # 否则，继续获取长期记忆
                deepseek = self._get_deepseek_client()
                response = deepseek.get_response(
                    message="\n".join(long_memories[-20:]),
                    user_id="retrieval",
                    system_prompt=f"请从以下记忆中找到与'{query}'最相关的条目，按相关性排序返回最多{3 - len(prioritized_memories)}条:"
                )

                # 调试：打印模型响应
                logger.debug(f"模型响应: {response}")

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
                        # 如果有高优先级记忆，仍然返回
                        if prioritized_memories:
                            return prioritized_memories
                        return []
                else:
                    # 处理响应并添加到优先级记忆列表
                    long_memory_results = [line.strip() for line in response.split("\n") if line.strip()]
                    prioritized_memories.extend(long_memory_results)
                    
                    # 返回最终的优先级记忆列表
                    logger.info(f"返回总计 {len(prioritized_memories)} 条优先级记忆")
                    return prioritized_memories

            except Exception as e:
                logger.error(f"第 {retry_count + 1} 次尝试失败: {str(e)}")
                if retry_count < max_retries - 1:
                    continue
                else:
                    logger.error(f"达到最大重试次数: {str(e)}")
                    # 如果有高优先级记忆，仍然返回
                    if prioritized_memories:
                        return prioritized_memories
                    return []

        # 如果所有重试都失败，但有高优先级记忆，仍然返回
        if high_priority_memories:
            relevant_high_priority = self._filter_relevant_memories(high_priority_memories, query)
            if relevant_high_priority:
                return relevant_high_priority[:3]  # 最多返回3条
        return []

    def _filter_relevant_memories(self, memories: List[str], query: str) -> List[str]:
        """根据查询筛选相关记忆"""
        # 简单实现：检查记忆中是否包含查询中的关键词
        # 实际应用中可以使用更复杂的相关性算法
        query_words = set(jieba.cut(query))
        relevant_memories = []
        
        for memory in memories:
            # 去除时间戳和标签
            if '] 高优先级: ' in memory:
                memory_content = memory.split('] 高优先级: ', 1)[1]
            else:
                memory_content = memory
                
            # 计算相关性分数
            memory_words = set(jieba.cut(memory_content))
            common_words = query_words.intersection(memory_words)
            
            # 如果有共同词或者查询词在记忆中，认为相关
            if common_words or any(word in memory_content for word in query_words):
                relevant_memories.append(memory_content)
                
        return relevant_memories[:3]  # 最多返回3条
        
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
                
        # 高优先级记忆维护
        high_priority_path = os.path.join(self.memory_dir, "high_priority_memory.txt")
        if os.path.exists(high_priority_path) and os.path.getsize(high_priority_path) > 512 * 1024:  # 512KB
            try:
                logger.debug(f"开始维护高优先级记忆文件: {high_priority_path}")
                with open(high_priority_path, 'r+', encoding='utf-8') as f:
                    lines = f.readlines()
                    keep_lines = lines[-max_entries:]  # 保留最后N条
                    f.seek(0)
                    f.writelines(keep_lines)
                    f.truncate()
                logger.info("已完成高优先级记忆维护")
            except Exception as e:
                logger.error(f"高优先级记忆维护失败: {str(e)}", exc_info=True)
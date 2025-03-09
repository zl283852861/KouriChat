import os
import logging
import random
from typing import List
from datetime import datetime
from src.services.ai.llm_service import LLMService

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

        # 新增记忆层
        self.memory_layers = {
            'instant': os.path.join(self.memory_dir, "instant_memory.txt"),
            'working': os.path.join(self.memory_dir, "working_memory.txt")
        }

        # 初始化文件和目录
        os.makedirs(self.memory_dir, exist_ok=True)
        self._init_files()

    def _init_files(self):
        """初始化所有记忆文件"""
        files_to_check = [
            self.short_memory_path,
            self.long_memory_buffer_path,
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
            logger.error(f"写入短期记忆文件失败: {str(e)}")

        # 新增情感标记
        emotion = self._detect_emotion(message)
        self._add_instant_memory(f"用户: {message}", emotion)

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
        """简易情感检测"""
        if '!' in text or '💔' in text:
            return 'anger'
        return 'neutral'

    def _add_instant_memory(self, message: str, emotion: str):
        """添加瞬时记忆"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            icon = '❤️🔥' if emotion == 'anger' else '📝'
            entry = f"[{timestamp}] {icon} {message}"
            logger.debug(f"开始写入瞬时记忆文件: {self.memory_layers['instant']}")
            with open(self.memory_layers['instant'], 'a', encoding='utf-8') as f:
                f.write(entry + '\n')
            logger.info(f"成功写入瞬时记忆: {entry}")
        except Exception as e:
            logger.error(f"写入瞬时记忆文件失败: {str(e)}")

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
                logger.debug(f"长期记忆缓冲区内容: {memories}")

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
                logger.error(f"长期记忆维护失败: {str(e)}")

        # 瞬时记忆归档
        instant_path = self.memory_layers['instant']
        if os.path.getsize(instant_path) > 512 * 1024:  # 512KB
            try:
                archive_name = f"instant_memory_{datetime.now().strftime('%Y%m%d')}.bak"
                logger.debug(f"开始归档瞬时记忆文件: {instant_path} 到 {archive_name}")
                os.rename(instant_path, os.path.join(self.memory_dir, archive_name))
                logger.info(f"瞬时记忆已归档: {archive_name}")
            except Exception as e:
                logger.error(f"瞬时记忆归档失败: {str(e)}")


# # 测试模块
# if __name__ == "__main__":
#     # 配置日志格式
#     logging.basicConfig(
#         level=logging.DEBUG,  # 调整为 DEBUG 级别，以便查看调试信息
#         format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
#     )
#
#     # 测试配置
#     test_config = {
#         "root_dir": os.path.dirname(os.path.abspath(".")),  # 测试数据目录，往上一个根目录寻址
#         "api_key": "",  # 测试用的API Key
#         "base_url": "https://api.siliconflow.cn/v1",
#         "model": "deepseek-ai/DeepSeek-V3",
#         "max_token": 512,
#         "temperature": 0.7,
#         "max_groups": 5
#     }
#
#     # 增强的清理函数
#     def clean_test_files():
#         files_to_clean = [
#             os.path.join(test_config["root_dir"], "data", "memory", f)
#             for f in ['short_memory.txt',
#                       'long_memory_buffer.txt',
#                       'instant_memory.txt',
#                       'working_memory.txt',
#                       'high_priority_memory.txt']
#         ]
#
#         for path in files_to_clean:
#             if os.path.exists(path):
#                 try:
#                     if path.endswith('working_memory.txt'):
#                         # 保留工作记忆模板
#                         with open(path, 'w', encoding='utf-8') as f:
#                             f.write("初始工作记忆内容...\n")
#                     else:
#                         os.remove(path)
#                     logger.info(f"清理文件: {os.path.basename(path)}")
#                 except Exception as e:
#                     logger.error(f"清理文件失败: {path} - {str(e)}")
#
#
#     clean_test_files()  # 替换原有的单个清理操作
#
#     # 初始化 MemoryHandler
#     logger.info("初始化 MemoryHandler...")
#     handler = MemoryHandler(**test_config)
#
#     # 测试添加短期记忆
#     logger.info("测试添加短期记忆...")
#     handler.add_short_memory("记住我喜欢吃巧克力蛋糕", "好的，我记住了！")
#     handler.add_short_memory("今天工作好累！", "要注意休息哦~")
#     handler.add_short_memory("我生气了！", "冷静一下~")
#     handler.add_short_memory("今天很开心！", "太好了！")
#     handler.add_short_memory("明天要去旅行，好期待！", "祝您旅途愉快！")
#     handler.add_short_memory("最近在学习编程，感觉有点难", "慢慢来，编程需要耐心和练习。")
#     handler.add_short_memory("我养了一只小猫，它很可爱", "小猫确实很可爱，记得照顾好它哦~")
#     handler.add_short_memory("最近天气变冷了", "记得多穿点衣服，别感冒了。")
#     handler.add_short_memory("我喜欢看电影，尤其是科幻片", "科幻片很有趣，您最近看了什么好片？")
#     handler.add_short_memory("我有点饿了", "要不要吃点东西？记得选择健康的食物。")
#
#     # 测试总结记忆
#     logger.info("测试总结记忆...")
#     handler.summarize_memories()
#
#     # 测试获取相关记忆
#     logger.info("测试获取相关记忆...")
#     relevant_memories = handler.get_relevant_memories("工作")
#     logger.info(f"获取到的相关记忆: {relevant_memories}")
#
#     # 手动验证长期记忆缓冲区文件内容
#     long_memory_buffer_path = os.path.join(test_config["root_dir"], "data", "memory", "long_memory_buffer.txt")
#     with open(long_memory_buffer_path, "r", encoding="utf-8") as f:
#         logger.info("长期记忆缓冲区文件内容:")
#         logger.info(f.read())
#
#     # 测试瞬时记忆
#     logger.info("测试瞬时记忆功能...")
#     handler.add_short_memory("我生气了！", "冷静一下~")
#     handler.add_short_memory("今天很开心！", "太好了！")
#
#     # 打印瞬时记忆文件内容
#     instant_memory_path = os.path.join(test_config["root_dir"], "data", "memory", "instant_memory.txt")
#     with open(instant_memory_path, "r", encoding="utf-8") as f:
#         logger.info("瞬时记忆文件内容:")
#         logger.info(f.read())
#
#     # 添加工作记忆
#     working_memory_path = os.path.join(test_config["root_dir"], "data", "memory", "working_memory.txt")
#     logger.info("测试工作记忆功能...")
#     try:
#         logger.debug(f"开始写入工作记忆文件: {working_memory_path}")
#         with open(working_memory_path, "w", encoding="utf-8") as f:
#             f.write("2025-03-08 19:30:00 - 今日小结：\n")
#             f.write("1. 用户多次表达工作疲劳，建议其注意休息。\n")
#             # 接上段代码
#             f.write("2. 用户喜欢巧克力蛋糕，已经记住这一偏好。\n")
#             f.write("3. 用户在情绪波动时，提醒用户保持冷静。\n")
#             f.write("4. 用户计划去旅行，祝其旅途愉快。\n")
#             f.write("5. 用户在学习编程，鼓励其保持耐心。\n")
#             f.write("6. 用户养了一只小猫，提醒其照顾好宠物。\n")
#             f.write("7. 用户提到天气变冷，建议其注意保暖。\n")
#             f.write("8. 用户喜欢看电影，尤其是科幻片。\n")
#             f.write("9. 用户感到饿了，建议其选择健康食物。\n\n")
#             f.write("关键记忆标签：\n")
#             f.write("- 用户过敏史：无\n")
#             f.write("- 用户喜好：巧克力蛋糕、科幻电影\n")
#             f.write("- 用户宠物：小猫\n")
#             f.write("- 用户近期计划：旅行\n")
#         logger.info("成功写入工作记忆文件")
#     except Exception as e:
#         logger.error(f"写入工作记忆文件失败: {str(e)}")
#
#     # 打印工作记忆文件内容
#     with open(working_memory_path, "r", encoding="utf-8") as f:
#         logger.info("工作记忆文件内容:")
#         logger.info(f.read())
#
#         # 打印高优先级记忆文件内容
#     high_priority_path = os.path.join(test_config["root_dir"], "data", "memory", "high_priority_memory.txt")
#     if os.path.exists(high_priority_path):
#         with open(high_priority_path, "r", encoding="utf-8") as f:
#             logger.info("高优先级记忆文件内容:")
#             logger.info(f.read())

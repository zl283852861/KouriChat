import logging
import random
from typing import List, Optional
from src.services.ai.llm_service import LLMService

logger = logging.getLogger('main')

class SmartMessageGenerator:
    """智能消息生成器
    
    用于根据历史对话内容生成更智能的自动消息，使AI主动发起的对话更加自然连贯。
    """
    
    def __init__(self, memory_handler, llm_service: LLMService):
        """初始化智能消息生成器
        
        Args:
            memory_handler: 记忆处理器实例，用于获取历史对话记忆
            llm_service: LLM服务实例，用于生成智能回复
        """
        self.memory_handler = memory_handler
        self.llm_service = llm_service
        
        # 默认问候语列表，当无法获取上下文时使用
        self.default_greetings = [
            "在干嘛呢？",
            "今天过得怎么样？",
            "有什么新鲜事吗？",
            "最近忙什么呢？",
            "有空聊聊吗？",
            "今天天气不错，你那边呢？",
            "刚刚在想你，你在做什么呢？",
            "突然想起你，最近怎么样？",
            "好久不见，近况如何？",
            "有什么有趣的事情分享吗？"
        ]
        
        # 基于活动的问候模板
        self.activity_templates = {
            "工作": [
                "工作顺利吗？需要放松一下吗？",
                "工作中遇到什么有趣的事情了吗？",
                "工作累了吧？要不要休息一下？",
                "今天的工作进展如何？"
            ],
            "学习": [
                "学习进展如何？有什么我能帮忙的吗？",
                "学习累了吧？要不要休息一下？",
                "今天学到什么新知识了？",
                "学习中遇到什么困难了吗？"
            ],
            "吃饭": [
                "吃了什么好吃的？能分享一下吗？",
                "这顿饭好吃吗？有什么推荐的？",
                "吃饱了吗？有什么美食推荐？",
                "今天的饭菜合胃口吗？"
            ],
            "游戏": [
                "玩什么游戏呢？好玩吗？",
                "游戏进展如何？赢了吗？",
                "这个游戏你玩了多久了？有什么技巧吗？",
                "能教教我怎么玩这个游戏吗？"
            ],
            "看电影": [
                "电影好看吗？能推荐给我吗？",
                "这部电影讲什么的？值得一看吗？",
                "有什么印象深刻的情节吗？",
                "这部电影的演员表现如何？"
            ],
            "睡觉": [
                "睡得好吗？做了什么有趣的梦？",
                "休息得怎么样？精神恢复了吗？",
                "昨晚睡得好吗？",
                "有什么助眠的好方法吗？"
            ]
        }
    
    def generate_smart_message(self, default_content: str, chat_id: str) -> str:
        """生成智能消息
        
        根据历史对话内容，生成更加智能、自然的消息。
        
        Args:
            default_content: 默认消息内容，当无法生成智能消息时返回
            chat_id: 聊天ID，用于检索相关记忆
            
        Returns:
            生成的智能消息
        """
        try:
            # 1. 尝试获取相关记忆
            memories = self.memory_handler.get_relevant_memories(f"与{chat_id}的最近对话")
            
            # 如果没有相关记忆，使用默认问候语
            if not memories or len(memories) == 0:
                logger.info(f"未找到与{chat_id}的相关记忆，使用默认问候语")
                return random.choice(self.default_greetings)
            
            # 2. 分析记忆中的活动信息
            activity = self._extract_activity_from_memories(memories)
            
            # 3. 如果找到了明确的活动，使用相应的模板
            if activity and activity in self.activity_templates:
                message = random.choice(self.activity_templates[activity])
                logger.info(f"根据活动'{activity}'生成消息: {message}")
                return message
            
            # 4. 如果没有明确活动或没有匹配的模板，使用LLM生成个性化消息
            return self._generate_personalized_message(memories, chat_id)
            
        except Exception as e:
            logger.error(f"生成智能消息失败: {str(e)}")
            return default_content
    
    def _extract_activity_from_memories(self, memories: List[str]) -> Optional[str]:
        """从记忆中提取活动信息
        
        分析记忆内容，尝试提取用户正在进行的活动。
        
        Args:
            memories: 记忆列表
            
        Returns:
            提取到的活动，如果没有找到则返回None
        """
        # 活动关键词映射
        activity_keywords = {
            "工作": ["工作", "加班", "开会", "项目", "客户", "文档", "报表", "办公室", "同事"],
            "学习": ["学习", "复习", "考试", "作业", "论文", "课程", "老师", "同学", "笔记", "题目"],
            "吃饭": ["吃饭", "午餐", "晚餐", "早餐", "美食", "餐厅", "菜", "饭", "饿", "点餐"],
            "游戏": ["游戏", "打游戏", "玩游戏", "开黑", "组队", "通关", "赢了", "输了", "段位"],
            "看电影": ["电影", "电视剧", "看剧", "追剧", "影院", "电视", "视频", "演员", "导演"],
            "睡觉": ["睡觉", "睡了", "休息", "困", "累", "床", "睡不着", "失眠", "梦"]
        }
        
        # 遍历所有记忆
        for memory in memories:
            # 遍历所有活动类型
            for activity, keywords in activity_keywords.items():
                # 检查记忆中是否包含该活动的关键词
                if any(keyword in memory for keyword in keywords):
                    logger.debug(f"从记忆'{memory}'中提取到活动: {activity}")
                    return activity
        
        return None
    
    def _generate_personalized_message(self, memories: List[str], chat_id: str) -> str:
        """生成个性化消息
        
        使用LLM根据历史记忆生成个性化的消息。
        
        Args:
            memories: 相关记忆列表
            chat_id: 聊天ID
            
        Returns:
            生成的个性化消息
        """
        try:
            # 构建提示词
            prompt = f"""根据以下与用户的历史对话记忆，生成一条自然、友好的主动问候消息。消息应该基于历史对话中的内容，体现出对用户近况的关心。
            消息应该简短自然（不超过30个字），像朋友之间的日常对话，避免过于正式或机械的表达。
            
            历史记忆：
            {' '.join(memories)}
            
            生成的消息："""
            
            # 调用LLM生成回复
            response = self.llm_service.get_response(
                message=prompt,
                user_id="system",
                system_prompt="你是一个善于社交的AI助手，擅长根据历史对话生成自然、友好的问候消息。"
            )
            
            # 检查响应
            if response and len(response.strip()) > 0:
                logger.info(f"成功生成个性化消息: {response}")
                return response.strip()
            else:
                logger.warning("生成的个性化消息为空，使用默认问候语")
                return random.choice(self.default_greetings)
                
        except Exception as e:
            logger.error(f"生成个性化消息失败: {str(e)}")
            return random.choice(self.default_greetings)
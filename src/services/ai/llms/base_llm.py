from datetime import datetime
from typing import Callable, List, Dict, Optional, Tuple
from logging import Logger
from src.services.ai.llms.llm import online_llm


class BaseLLM(online_llm):
    """
    大模型基类，提供通用的上下文管理和响应生成功能
    """
    def __init__(
        self, 
        logger: Logger,
        model_name: str, 
        url: str, 
        api_key: str, 
        n_ctx: int, 
        temperature: float,
        max_context_messages: int = 10,  # 这里表示最大对话对数量
        system_prompt: Optional[str] = None,
        singleton: bool = True
    ):
        """
        初始化大模型基类
        
        Args:
            logger: 日志记录器
            model_name: 模型名称
            url: API地址
            api_key: API密钥
            n_ctx: 上下文长度
            temperature: 温度参数
            max_context_messages: 上下文对话对最大数量
            system_prompt: 系统提示词
            singleton: 是否为单例模式
        """
        super().__init__(
            model_name,
            url,
            api_key,
            n_ctx,
            temperature,
            singleton
        )
        self.logger = logger
        self.max_context_messages = max_context_messages
        self.context: List[Dict[str, str]] = []
        self._context_handler = None
        
        # 添加系统提示
        if system_prompt:
            self.context.append({"role": "system", "content": system_prompt})
            self.system_prompt = system_prompt
        else:
            self.system_prompt = None
        
        # 2025-03-17 修复适配获取最近时间
        self.user_recent_chat_time = {}
    
    def context_handler(self, func: Callable[[str, str, str], None]):
        """
        装饰器：注册上下文处理函数
        
        Args:
            func: 处理函数，接收用户ID、用户输入和AI回复三个参数
        """
        self._context_handler = func
        return func
    
    def _build_prompt(self, current_prompt: str) -> List[Dict[str, str]]:
        """
        构建完整的提示消息列表
        
        Args:
            current_prompt: 当前用户输入的提示
            
        Returns:
            包含上下文历史和当前提示的消息列表
        """
        messages = self.context.copy()
        messages.append({"role": "user", "content": current_prompt})
        
        # 添加详细日志
        self.logger.info(f"[上下文跟踪] 构建提示，当前上下文消息数: {len(messages)}")
        for idx, msg in enumerate(messages):
            # 限制长度以免日志过长
            content_preview = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            self.logger.info(f"[上下文消息 {idx}] 角色: {msg['role']}, 内容: {content_preview}")
        
        return messages
    
    def _update_context(self, user_prompt: str, assistant_response: str) -> None:
        """
        更新上下文历史
        
        Args:
            user_prompt: 用户输入
            assistant_response: 助手回复
        """
        # 添加新的对话到上下文
        self.context.append({"role": "user", "content": user_prompt})
        self.context.append({"role": "assistant", "content": assistant_response})
        
        # 计算当前对话对数量（不包括system prompt）
        message_count = len(self.context)
        system_offset = 1 if self.system_prompt else 0
        pair_count = (message_count - system_offset) // 2
        
        self.logger.info(f"[上下文管理] 更新后上下文总消息数: {message_count}, 对话对数: {pair_count}, 最大限制: {self.max_context_messages}")
        
        # 如果超出对话对数量限制，移除最早的对话对
        if pair_count > self.max_context_messages:
            # 计算需要移除的对话对数量
            excess_pairs = pair_count - self.max_context_messages
            # 每对包含两条消息
            excess_messages = excess_pairs * 2
            
            self.logger.warning(f"[上下文截断] 超出限制，需要移除 {excess_pairs} 对对话（{excess_messages} 条消息）")
            
            # 保存被移除的消息用于处理
            start_idx = system_offset
            removed_messages = self.context[start_idx:start_idx+excess_messages]
            
            # 记录被移除的消息
            for idx, msg in enumerate(removed_messages):
                content_preview = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
                self.logger.info(f"[移除消息 {idx}] 角色: {msg['role']}, 内容: {content_preview}")
            
            # 更新上下文，保留system prompt
            if self.system_prompt:
                self.context = [self.context[0]] + self.context[start_idx+excess_messages:]
            else:
                self.context = self.context[excess_messages:]
            
            # 如果设置了上下文处理函数，处理被移除的消息
            if self._context_handler and removed_messages:
                # 成对处理被移除的用户输入和AI回复
                for i in range(0, len(removed_messages), 2):
                    if i+1 < len(removed_messages):
                        user_msg = removed_messages[i]["content"]
                        ai_msg = removed_messages[i+1]["content"]
                        try:
                            self._context_handler(user_msg, ai_msg)
                        except Exception as e:
                            self.logger.error(f"上下文处理函数执行失败: {str(e)}")
    
    def handel_prompt(self, prompt: str, user_id: str = None) -> str:
        """
        处理用户输入并生成回复
        
        Args:
            prompt: 用户输入的提示
            user_id: 用户ID，用于关联上下文
            
        Returns:
            模型生成的回复
        """
        try:
            self.logger.info(f"[处理提示] 收到输入: {prompt}")
            
            # 使用用户ID构建上下文键
            context_key = user_id if user_id else "default"
            
            # 如果没有为此用户初始化上下文，则创建
            if not hasattr(self, 'user_contexts'):
                self.user_contexts = {}
            
            # 获取或创建此用户的上下文
            if context_key not in self.user_contexts:
                # 新用户，初始化上下文
                if self.system_prompt:
                    self.user_contexts[context_key] = [{"role": "system", "content": self.system_prompt}]
                else:
                    self.user_contexts[context_key] = []
            
            # 获取当前用户的上下文
            current_context = self.user_contexts[context_key].copy()
            current_context.append({"role": "user", "content": prompt})
            
            # 构建完整提示
            self.logger.info(f"[上下文跟踪] 构建提示，当前上下文消息数: {len(current_context)}")
            for idx, msg in enumerate(current_context):
                content_preview = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                self.logger.info(f"[上下文消息 {idx}] 角色: {msg['role']}, 内容: {content_preview}")
            
            # 这里需要子类实现具体的API调用逻辑
            response = self.generate_response(current_context)
            
            # 更新用户上下文
            self.user_contexts[context_key].append({"role": "user", "content": prompt})
            self.user_contexts[context_key].append({"role": "assistant", "content": response})
            
            # 关键修复点：立即调用上下文管理，确保每次对话后检查并截断上下文
            self.logger.info(f"[上下文管理] 开始管理上下文长度，最大允许对话对数: {self.max_context_messages}")
            self._manage_context_length(context_key)
            
            # 打印更新后的上下文信息
            post_manage_context = self.user_contexts[context_key]
            self.logger.info(f"[上下文管理后] 更新后的上下文消息数: {len(post_manage_context)}")
            
            self.logger.info(f"[API响应] 收到回复: {response}")
            
            self.user_recent_chat_time[user_id] = datetime.now()
            return response
            
        except Exception as e:
            self.logger.error(f"处理提示时出错: {str(e)}")
            return f"处理您的请求时出现错误: {str(e)}"
    
    def _manage_context_length(self, context_key):
        """管理特定用户的上下文长度"""
        if context_key not in self.user_contexts:
            return
        
        context = self.user_contexts[context_key]
        
        # 计算当前对话对数量（不包括system prompt）
        message_count = len(context)
        system_offset = 1 if any(msg["role"] == "system" for msg in context) else 0
        pair_count = (message_count - system_offset) // 2
        
        self.logger.warning(f"[上下文管理详情] 用户 {context_key} 的上下文总消息数: {message_count}, 对话对数: {pair_count}, 最大限制: {self.max_context_messages}")
        
        # 如果超出对话对数量限制，移除最早的对话对
        if pair_count > self.max_context_messages:
            # 计算需要移除的对话对数量
            excess_pairs = pair_count - self.max_context_messages
            # 每对包含两条消息
            excess_messages = excess_pairs * 2
            
            self.logger.warning(f"[上下文截断] 超出限制，需要移除 {excess_pairs} 对对话（{excess_messages} 条消息）")
            
            # 保存被移除的消息用于处理
            start_idx = system_offset
            removed_messages = context[start_idx:start_idx+excess_messages]
            
            # 记录被移除的消息
            for idx, msg in enumerate(removed_messages):
                content_preview = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
                self.logger.warning(f"[移除消息 {idx}] 角色: {msg['role']}, 内容: {content_preview}")
            
            # 更新上下文，保留system prompt
            if system_offset > 0:
                self.user_contexts[context_key] = [context[0]] + context[start_idx+excess_messages:]
            else:
                self.user_contexts[context_key] = context[excess_messages:]
            
            self.logger.warning(f"[上下文截断后] 更新后的上下文消息数: {len(self.user_contexts[context_key])}")
            
            # 如果设置了上下文处理函数，处理被移除的消息
            if self._context_handler and removed_messages:
                # 成对处理被移除的用户输入和AI回复
                for i in range(0, len(removed_messages), 2):
                    if i+1 < len(removed_messages):
                        user_msg = removed_messages[i]["content"]
                        ai_msg = removed_messages[i+1]["content"]
                        try:
                            # 传入用户ID作为参数
                            self._context_handler(context_key, user_msg, ai_msg)
                        except Exception as e:
                            self.logger.error(f"上下文处理函数执行失败: {str(e)}")
    
    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """
        调用API生成回复，需要在子类中实现
        
        Args:
            messages: 完整的消息列表
            
        Returns:
            模型生成的回复
        """
        raise NotImplementedError("子类必须实现_generate_response方法")

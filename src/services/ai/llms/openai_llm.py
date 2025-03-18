from typing import List, Dict
import logging
from openai import OpenAI
from src.services.ai.llms.base_llm import BaseLLM

class OpenAILLM(BaseLLM):
    """
    OpenAI API 大模型调用类
    """
    def __init__(
        self,
        logger: logging.Logger,
        model_name: str,
        url: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        max_context_messages: int = 10,
        n_ctx: int = 1024,
        system_prompt: str = None,
        singleton: bool = True
    ):
        # 调用父类初始化
        super().__init__(
            logger=logger,
            model_name=model_name,
            url=url,
            api_key=api_key,
            n_ctx=n_ctx,
            temperature=temperature,
            max_context_messages=max_context_messages,
            system_prompt=system_prompt,
            singleton=singleton
        )
        
        # OpenAI特有参数
        self.max_tokens = max_tokens
        
        # 初始化客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.url
        )
        
        self.logger.info(f"OpenAI LLM 初始化完成，模型: {self.model_name}")
    
    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """
        调用OpenAI API生成回复
        
        Args:
            messages: 完整的消息列表
            
        Returns:
            模型生成的回复
        """
        try:
            self.logger.debug(f"发送请求到OpenAI API，消息数: {len(messages)}")
            self.logger.info(f"使用模型: {self.model_name}, API URL: {self.url}, 温度: {self.temperature}")
            
            # 调用API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # 检查响应类型
            if isinstance(response, str):
                self.logger.error(f"API返回了字符串而不是对象: {response[:100]}...")
                return f"API响应格式错误，请检查配置。"
            
            # 检查响应内容
            if not hasattr(response, 'choices') or not response.choices or len(response.choices) == 0:
                self.logger.error(f"API返回无效响应: {response}")
                raise ValueError("API返回空响应")
                
            assistant_response = response.choices[0].message.content.strip()
            
            self.logger.debug(f"收到OpenAI API响应，长度: {len(assistant_response)}")
            return assistant_response
            
        except Exception as e:
            error_message = str(e)
            self.logger.error(f"OpenAI API调用失败: {error_message}")
            
            # 增强错误日志
            if "Connection" in error_message:
                self.logger.error(f"连接错误详情 - URL: {self.url}, API密钥前4位: {self.api_key[:4] if len(self.api_key) > 4 else '无效'}")
                self.logger.error(f"请检查网络连接和API配置。确保API URL和API密钥在config.yaml中正确设置。")
                return f"API调用失败: 连接错误。请检查API配置和网络连接。"
            elif "authorization" in error_message.lower() or "authenticate" in error_message.lower():
                self.logger.error(f"认证错误 - 请检查API密钥是否正确设置")
                return f"API调用失败: 认证错误。请检查API密钥设置。"
            elif "timeout" in error_message.lower():
                self.logger.error(f"请求超时 - 服务器响应时间过长")
                return f"API调用失败: 请求超时。请稍后重试。"
            else:
                return f"API调用失败: {error_message}"  # 直接返回错误信息而不是抛出异常

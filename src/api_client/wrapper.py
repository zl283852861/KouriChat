"""
API调用包装器模块 - 提供统一的API调用接口
"""
import os
import logging
import json
import openai
from typing import Any, Dict, List, Optional, Union

# 设置日志
logger = logging.getLogger('main')

class APIWrapper:
    """
    API调用包装器类，提供统一的API调用接口
    """
    
    def __init__(self, api_key: str, base_url: str = None):
        """
        初始化API包装器
        
        Args:
            api_key: API密钥
            base_url: API基础URL，默认为OpenAI官方API
        """
        self.api_key = api_key
        self.base_url = base_url
        
        # 初始化OpenAI客户端
        self._init_client()
        
        # 创建API接口
        self._create_interfaces()
        
    def _init_client(self):
        """初始化OpenAI客户端"""
        try:
            # 设置环境变量
            os.environ["OPENAI_API_KEY"] = self.api_key
            if self.base_url:
                os.environ["OPENAI_API_BASE"] = self.base_url
                
            # 创建客户端
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"成功初始化API客户端，基础URL: {self.base_url or '默认OpenAI'}")
        except Exception as e:
            logger.error(f"初始化API客户端失败: {str(e)}")
            # 创建一个空客户端，避免程序崩溃
            self.client = object()
            
    def _create_interfaces(self):
        """创建API接口"""
        # 嵌入API
        self.embeddings = APIEmbeddings(self)
        
    def handle_api_error(self, error: Exception) -> Dict:
        """
        处理API错误
        
        Args:
            error: 异常对象
            
        Returns:
            Dict: 错误信息字典
        """
        try:
            if hasattr(error, 'json'):
                return error.json()
            elif hasattr(error, 'response') and hasattr(error.response, 'json'):
                return error.response.json()
            else:
                return {"error": str(error)}
        except:
            return {"error": str(error)}

class APIEmbeddings:
    """嵌入API接口"""
    
    def __init__(self, wrapper: APIWrapper):
        """
        初始化嵌入API接口
        
        Args:
            wrapper: API包装器实例
        """
        self.wrapper = wrapper
        
    async def create(self, model: str, input: Union[str, List[str]]) -> Any:
        """
        创建嵌入向量
        
        Args:
            model: 模型名称
            input: 输入文本或文本列表
            
        Returns:
            Any: API响应
        """
        try:
            # 调用OpenAI API
            response = self.wrapper.client.embeddings.create(
                model=model,
                input=input
            )
            return response
        except Exception as e:
            logger.error(f"创建嵌入向量失败: {str(e)}")
            error_info = self.wrapper.handle_api_error(e)
            logger.error(f"API错误详情: {json.dumps(error_info)}")
            raise 
"""
本文件实现了网络大模型调用基类和本地大模型调用基类
"""

import abc


class local_llm_gguf(abc.ABC):
    """
    本地大模型基类
    """
    _instance = None

    def __new__(cls, *args, singleton: bool = True, **kwargs):
        if singleton and cls._instance is None:
            cls._instance = super(local_llm_gguf, cls).__new__(cls)
        elif not singleton:
            cls._instance = super(local_llm_gguf, cls).__new__(cls)
        return cls._instance

    def __init__(self, model_path: str, n_ctx: int, temperature: float, singleton: bool = True):
        # 无论是否已初始化，都更新关键参数
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.temperature = temperature
        
        # 仅在首次初始化时设置model和initialized
        if not hasattr(self, 'initialized'):
            self.model = None
            self.initialized = True

    @abc.abstractmethod
    def handel_prompt(self, prompt: str) -> str:
        """
        处理prompt
        """


class online_llm(abc.ABC):
    """
    网络大模型基类
    """
    _instance = None
    _last_model_name = None

    def __new__(cls, model_name: str, url: str, api_key: str, n_ctx: int, temperature: float, singleton: bool = True, **kwargs):
        # 如果是单例模式并且已存在实例，但模型名称变更了，则强制重新创建实例
        if singleton and cls._instance is not None and cls._last_model_name != model_name:
            cls._instance = None
            
        if singleton and cls._instance is None:
            cls._instance = super(online_llm, cls).__new__(cls)
            cls._last_model_name = model_name
        elif not singleton:
            cls._instance = super(online_llm, cls).__new__(cls)
            cls._last_model_name = model_name
        return cls._instance

    def __init__(self, model_name: str, url: str, api_key: str, n_ctx: int, temperature: float, singleton: bool = True):
        # 无论是否已初始化，都更新关键参数
        self.model_name = model_name
        # 处理URL末尾斜杠
        if url and url.endswith('/'):
            self.url = url.rstrip('/')
        else:
            self.url = url
        self.api_key = api_key
        self.n_ctx = n_ctx
        self.temperature = temperature
        
        # 仅在首次初始化时设置initialized标志
        if not hasattr(self, 'initialized'):
            self.initialized = True

    @abc.abstractmethod
    def handel_prompt(self, prompt: str) -> str:
        """
        处理prompt
        """

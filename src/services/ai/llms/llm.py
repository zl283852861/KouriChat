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
        if not hasattr(self, 'initialized'):
            self.model_path = model_path
            self.n_ctx = n_ctx
            self.temperature = temperature
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

    def __new__(cls, *args, singleton: bool = True, **kwargs):
        if singleton and cls._instance is None:
            cls._instance = super(online_llm, cls).__new__(cls)
        elif not singleton:
            cls._instance = super(online_llm, cls).__new__(cls)
        return cls._instance

    def __init__(self, model_name: str, url: str, api_key: str, n_ctx: int, temperature: float, singleton: bool = True):
        if not hasattr(self, 'initialized'):
            self.model_name = model_name
            self.url = url
            self.api_key = api_key
            self.n_ctx = n_ctx
            self.temperature = temperature
            self.initialized = True

    @abc.abstractmethod
    def handel_prompt(self, prompt: str) -> str:
        """
        处理prompt
        """

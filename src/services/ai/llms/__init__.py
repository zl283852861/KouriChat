# 使用相对导入，避免循环依赖
# 这里不主动导入任何模块，而是在实际使用时再导入

__all__ = ['BaseLLM', 'OpenAILLM']

# 这里不做实际导入，以避免循环引用
# from .base_llm import BaseLLM
# from .openai_llm import OpenAILLM 
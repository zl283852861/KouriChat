# 标记为Python包
# 导出类列表
__all__ = [
    'LLMService', 'ImageRecognitionService'
]

# 避免循环导入，将实际导入移动到这里
# 实际导入会在使用时进行，而不是初始化时
# from .ai.llm_service import LLMService
# from .ai.image_recognition_service import ImageRecognitionService
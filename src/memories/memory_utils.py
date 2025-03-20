"""
记忆工具模块 - 提供记忆操作相关的工具函数
"""
import os
import re
import logging
import functools
import asyncio
from typing import Dict, List, Any, Callable, Tuple, Union, Optional

# 设置日志
logger = logging.getLogger('main')

# 嵌入模型常量
EMBEDDING_MODEL = "text-embedding-3-small"  # 默认嵌入模型
EMBEDDING_FALLBACK_MODEL = "text-embedding-ada-002"  # 备用嵌入模型
LOCAL_EMBEDDING_MODEL_PATH = "paraphrase-multilingual-MiniLM-L12-v2"  # 本地嵌入模型路径

# 缓存装饰器
def memory_cache(func):
    """
    记忆结果缓存装饰器
    
    仅缓存异步函数的结果，避免重复计算
    
    Args:
        func: 要缓存的函数
    
    Returns:
        包装后的函数
    """
    cache = {}
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # 生成缓存键
        key = str(args) + str(kwargs)
        
        # 检查缓存
        if key in cache:
            # 判断缓存是否过期（默认10分钟）
            import time
            current_time = time.time()
            cached_time = cache[key]['time']
            
            # 10分钟内的缓存有效
            if current_time - cached_time < 600:
                return cache[key]['result']
        
        # 执行原函数
        result = await func(*args, **kwargs)
        
        # 缓存结果
        import time
        cache[key] = {
            'result': result,
            'time': time.time()
        }
        
        # 限制缓存大小
        if len(cache) > 100:
            # 删除最旧的缓存
            oldest_key = min(cache, key=lambda k: cache[k]['time'])
            del cache[oldest_key]
            
        return result
    
    return wrapper

def clean_memory_content(memory_key: str, memory_value: str) -> Tuple[str, str]:
    """
    清理记忆内容，去除敏感信息和冗余信息
    
    Args:
        memory_key: 记忆键
        memory_value: 记忆值
        
    Returns:
        Tuple[str, str]: 清理后的记忆键和值
    """
    # 清理记忆键
    clean_key = memory_key.strip()
    
    # 去除可能的敏感信息（如密码、API密钥等）
    sensitive_patterns = [
        r'password[s]?\s*[:=]?\s*\S+',
        r'api[-_]?key[s]?\s*[:=]?\s*\S+',
        r'token[s]?\s*[:=]?\s*\S+',
        r'secret[s]?\s*[:=]?\s*\S+',
        r'access[-_]?key[s]?\s*[:=]?\s*\S+',
    ]
    
    clean_value = memory_value
    for pattern in sensitive_patterns:
        clean_value = re.sub(pattern, '[REDACTED]', clean_value, flags=re.IGNORECASE)
    
    # 去除可能的命令注入
    command_patterns = [
        r'rm\s+-rf',
        r'sudo\s+',
        r'chmod\s+',
        r'chown\s+',
        r'wget\s+',
        r'curl\s+',
    ]
    
    for pattern in command_patterns:
        clean_value = re.sub(pattern, '[FILTERED]', clean_value, flags=re.IGNORECASE)
    
    # 限制长度
    if len(clean_value) > 1000:
        clean_value = clean_value[:1000] + "..."
    
    return clean_key, clean_value

def get_importance_keywords() -> List[str]:
    """
    获取重要性关键词列表
    
    Returns:
        List[str]: 关键词列表
    """
    # 这些关键词表示内容可能需要被长期记忆
    return [
        # 人物信息
        "我叫", "我的名字", "我是", "我姓", 
        "名字是", "我的全名", "我的英文名",
        
        # 联系方式
        "电话", "手机号", "邮箱", "地址",
        "微信号", "QQ号", "联系方式",
        
        # 重要日期
        "生日", "纪念日", "周年", "结婚",
        "出生", "毕业", "入职", "就职",
        
        # 喜好
        "喜欢", "讨厌", "爱好", "兴趣",
        "最爱", "最讨厌", "偏好", "特别喜欢",
        
        # 家庭关系
        "父母", "父亲", "母亲", "爸爸", "妈妈",
        "兄弟", "姐妹", "家人", "亲人", "孩子",
        "儿子", "女儿", "老婆", "丈夫", "太太",
        
        # 工作学习
        "工作", "公司", "职位", "职业",
        "学校", "专业", "学习", "研究",
        
        # 重要事件
        "计划", "准备", "打算", "即将",
        "想要", "梦想", "目标", "愿望",
        
        # 情感状态
        "难过", "开心", "伤心", "生气",
        "焦虑", "压力", "烦恼", "困扰",
        
        # 健康状况
        "生病", "不舒服", "头疼", "感冒",
        "医院", "吃药", "治疗", "检查"
    ]

def get_memory_path(root_dir: str) -> str:
    """
    获取记忆文件路径
    
    Args:
        root_dir: 根目录路径
        
    Returns:
        str: 记忆文件路径
    """
    memory_base_dir = os.path.join(root_dir, "data", "memory")
    os.makedirs(memory_base_dir, exist_ok=True)
    memory_path = os.path.join(memory_base_dir, "rag-memory.json")
    return memory_path 

def clean_dialog_memory(sender_text: str, receiver_text: str) -> Tuple[str, str]:
    """
    清理对话记忆文本，过滤掉时间戳和其他固定模式文本
    
    Args:
        sender_text: 发送者文本
        receiver_text: 接收者文本
        
    Returns:
        Tuple[str, str]: 清理后的发送者文本和接收者文本
    """
    # 清理发送者文本
    if sender_text:
        # 去除时间戳 [xxxx-xx-xx xx:xx]
        sender_text = re.sub(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?\]', '', sender_text)
        # 去除"ta 私聊对你说："等固定模式
        sender_text = re.sub(r'ta 私聊对你说：', '', sender_text)
        # 去除"你好对你说："等变种模式
        sender_text = re.sub(r'[\w\s]+对你说：', '', sender_text)
        # 去除角色名称前缀，如"主人："
        sender_text = re.sub(r'^(主人|用户|您|我)：\s*', '', sender_text)
        # 去除所有换行符，包括\n\n
        sender_text = re.sub(r'\n+', ' ', sender_text)
        # 去除"请注意：你的回复应当..."等提示信息（更精确的模式）
        sender_text = re.sub(r'请注意：你的回复应当与用户消息的长度相当，控制在约\d+个字符和\d+个句子左右。', '', sender_text)
        # 去除新的提示语变体
        sender_text = re.sub(r'请简短回复，控制在一两句话内。', '', sender_text)
        sender_text = re.sub(r'请注意保持自然的回复长度，与用户消息风格协调。', '', sender_text)
        sender_text = re.sub(r'请保持简洁明了的回复。', '', sender_text)
        # 去除各种系统提示和指令
        sender_text = re.sub(r'(?:请|)(?:注意|记住|考虑|保持)[:：]?\s*.*?(?:回复|角色|表现|风格|语气|姿态|限制).*?。', '', sender_text)
        sender_text = re.sub(r'(?:记得|别忘了|注意|请)(?:保持|扮演).*?(?:角色|人设|立场).*?。', '', sender_text)
        sender_text = re.sub(r'(?:以下|接下来|现在)(?:是|为).*?(?:内容|消息|对话|聊天记录).*?[:：]', '', sender_text)
        # 去除其他常见噪音
        sender_text = re.sub(r'\[MASK\]|\[CLS\]|\[SEP\]|\[PAD\]|\[UNK\]', '', sender_text)
        sender_text = re.sub(r'<(?:s|p|div|span|img|br|hr).*?>', '', sender_text)
        sender_text = re.sub(r'<\/(?:s|p|div|span)>', '', sender_text)
        # 去除对方ID标记
        sender_text = re.sub(r'\(ID[:：]\w+\)', '', sender_text)
        # 去除方括号内容
        sender_text = re.sub(r'\[.*?\]', '', sender_text)
        # 清理多余空白
        sender_text = sender_text.strip()
    
    # 清理接收者文本
    if receiver_text:
        # 替换反斜杠和换行符为空格
        receiver_text = receiver_text.replace('\\', ' ').replace('\n', ' ')
        # 去除角色名称前缀，如"人工智能："
        receiver_text = re.sub(r'^(人工智能|AI|助手|我)[:：]\s*', '', receiver_text)
        # 去除"你："等变种模式
        receiver_text = re.sub(r'^你[:：]\s*', '', receiver_text)
        # 替换连续的空格为单个空格
        receiver_text = re.sub(r'\s+', ' ', receiver_text)
        # 去除各种标点符号过多的情况
        receiver_text = re.sub(r'([.。!！?？~～…,，;；])(\1{2,})', r'\1', receiver_text)
        # 去除方括号内的表情或动作描述
        receiver_text = re.sub(r'\[(?:笑|笑脸|微笑|开心|哭|伤心|思考|疑惑|困惑|惊讶|害羞|点头|摇头).*?\]', '', receiver_text)
        # 去除markdown格式
        receiver_text = re.sub(r'\*\*(.*?)\*\*', r'\1', receiver_text)  # 去除加粗
        receiver_text = re.sub(r'\*(.*?)\*', r'\1', receiver_text)  # 去除斜体
        receiver_text = re.sub(r'```.*?```', '', receiver_text, flags=re.DOTALL)  # 去除代码块
        # 去除其他常见噪音
        receiver_text = re.sub(r'\[MASK\]|\[CLS\]|\[SEP\]|\[PAD\]|\[UNK\]', '', receiver_text)
        receiver_text = re.sub(r'<(?:s|p|div|span|img|br|hr).*?>', '', receiver_text)
        receiver_text = re.sub(r'<\/(?:s|p|div|span)>', '', receiver_text)
        # 清理多余空白
        receiver_text = receiver_text.strip()
    
    return sender_text, receiver_text 
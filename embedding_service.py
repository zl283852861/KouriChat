from openai import OpenAI
import logging
import os
from src.config.rag_config import EMBEDDING_MODEL, EMBEDDING_FALLBACK_MODEL, OPENAI_API_KEY, OPENAI_API_BASE
from logger_config import retry_with_exponential_backoff

# 获取logger
logger = logging.getLogger(__name__)

# 创建OpenAI客户端
client = None

def init_client():
    """初始化OpenAI客户端"""
    global client
    api_key = os.getenv("OPENAI_API_KEY") or OPENAI_API_KEY
    api_base = os.getenv("OPENAI_API_BASE") or OPENAI_API_BASE
    
    if not api_key:
        logger.error("未设置OpenAI API密钥")
        raise ValueError("OpenAI API密钥未设置")
    
    if api_base:
        client = OpenAI(api_key=api_key, base_url=api_base)
        logger.info(f"使用自定义API基础URL: {api_base}")
    else:
        client = OpenAI(api_key=api_key)
    
    logger.info("OpenAI API客户端已初始化")

@retry_with_exponential_backoff
def get_embedding(text, model=EMBEDDING_MODEL):
    """
    获取文本的嵌入向量
    
    参数:
        text (str): 需要嵌入的文本
        model (str): 使用的嵌入模型名称
        
    返回:
        list: 嵌入向量
    """
    global client
    if client is None:
        init_client()
        
    try:
        response = client.embeddings.create(
            input=text,
            model=model
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"嵌入失败: {str(e)}")
        if model != EMBEDDING_FALLBACK_MODEL:
            logger.info(f"尝试使用备用模型 {EMBEDDING_FALLBACK_MODEL}")
            return get_embedding(text, EMBEDDING_FALLBACK_MODEL)
        else:
            raise 

def get_batch_embeddings(texts, model=EMBEDDING_MODEL, batch_size=100):
    """
    批量获取文本的嵌入向量
    
    参数:
        texts (list): 需要嵌入的文本列表
        model (str): 使用的嵌入模型名称
        batch_size (int): 批处理大小
        
    返回:
        list: 嵌入向量列表
    """
    global client
    if client is None:
        init_client()
        
    all_embeddings = []
    
    # 分批处理
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        logger.info(f"处理批次 {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
        
        try:
            response = client.embeddings.create(
                input=batch_texts,
                model=model
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
        except Exception as e:
            logger.error(f"批量嵌入失败: {str(e)}")
            # 如果批量处理失败，尝试单个处理
            for text in batch_texts:
                embedding = get_embedding(text, model)
                all_embeddings.append(embedding)
    
    return all_embeddings

def setup_openai_api():
    """设置OpenAI API配置"""
    global client
    init_client()
    logger.info("OpenAI API配置已设置") 
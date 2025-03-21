"""
记忆格式迁移模块 - 提供记忆格式迁移功能
"""
import sys
import os
import json
import re
import logging
from datetime import datetime
from pathlib import Path

# 设置日志
logger = logging.getLogger(__name__)

def clean_memory_text(text: str) -> str:
    """
    清理记忆文本，过滤掉时间戳和其他固定模式文本
    """
    if not text:
        return ""
        
    # 去除时间戳 [xxxx-xx-xx xx:xx]
    text = re.sub(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\]', '', text)
    # 去除"ta 私聊对你说："等固定模式
    text = re.sub(r'ta 私聊对你说：', '', text)
    # 去除"你好对你说："等变种模式
    text = re.sub(r'[\w\s]+对你说：', '', text)
    # 去除所有换行符
    text = re.sub(r'\n+', ' ', text)
    # 去除"请注意：你的回复应当..."等提示信息
    text = re.sub(r'请注意：你的回复应当与用户消息的长度相当，控制在约\d+个字符和\d+个句子左右。', '', text)
    # 更通用的提示语过滤
    text = re.sub(r'请注意：.*?控制在.*?。', '', text)
    # 去除可能的对话标识
    text = re.sub(r'对方\(ID:.*?\):', '', text)
    text = re.sub(r'你:', '', text)
    # 替换反斜杠
    text = text.replace('\\', ' ')
    # 清理多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def migrate_memory_format():
    """
    迁移记忆格式，将旧格式转换为新格式
    """
    # 确保在项目根目录下运行
    root_dir = Path.cwd()
    memory_dir = root_dir / "data" / "memory"
    
    # 记忆文件路径
    memory_path = memory_dir / "rag-memory.json"
    backup_path = memory_dir / f"rag-memory-backup-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    
    if not memory_path.exists():
        logger.error(f"记忆文件不存在: {memory_path}")
        return False
        
    # 创建备份
    try:
        memory_dir.mkdir(parents=True, exist_ok=True)
        with open(memory_path, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(old_data, f, ensure_ascii=False, indent=2)
        logger.info(f"已创建记忆备份: {backup_path}")
    except Exception as e:
        logger.error(f"创建备份失败: {e}")
        return False
    
    # 转换格式
    try:
        new_data = {}
        
        # 检查是否已经是新格式
        first_chat = next(iter(old_data.values()), None)
        if first_chat and isinstance(first_chat, list) and len(first_chat) > 0:
            first_entry = first_chat[0]
            if isinstance(first_entry, dict) and "sender_text" in first_entry and "receiver_text" in first_entry:
                logger.info("记忆文件已经是新格式，无需转换")
                return True
        
        # 开始转换
        logger.info("开始转换记忆格式...")
        for chat_id, memories in old_data.items():
            new_data[chat_id] = []
            
            # 判断memories的类型
            if isinstance(memories, dict):
                # 旧格式: {timestamp: {sender: xxx, receiver: xxx}}
                for timestamp, memory in memories.items():
                    if isinstance(memory, dict) and "sender" in memory and "receiver" in memory:
                        sender_text = clean_memory_text(memory.get("sender", ""))
                        receiver_text = clean_memory_text(memory.get("receiver", ""))
                        
                        if sender_text and receiver_text:  # 确保不是空对话
                            new_data[chat_id].append({
                                "sender_text": sender_text,
                                "receiver_text": receiver_text,
                                "timestamp": timestamp,
                                "importance": memory.get("importance", 0.5)
                            })
            elif isinstance(memories, list):
                # 另一种旧格式: [{sender: xxx, receiver: xxx}]
                for memory in memories:
                    if isinstance(memory, dict):
                        sender_text = clean_memory_text(memory.get("sender", ""))
                        receiver_text = clean_memory_text(memory.get("receiver", ""))
                        
                        if sender_text and receiver_text:  # 确保不是空对话
                            new_data[chat_id].append({
                                "sender_text": sender_text,
                                "receiver_text": receiver_text,
                                "timestamp": memory.get("timestamp", datetime.now().isoformat()),
                                "importance": memory.get("importance", 0.5)
                            })
        
        # 保存新格式数据
        with open(memory_path, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"记忆格式转换完成，共处理 {len(new_data)} 个会话")
        return True
    except Exception as e:
        logger.error(f"转换格式失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # 尝试恢复备份
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            with open(memory_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            logger.info("已从备份恢复原始记忆文件")
        except Exception as restore_error:
            logger.error(f"恢复备份失败: {restore_error}")
            
        return False 
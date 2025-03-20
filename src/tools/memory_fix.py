"""
记忆修复模块 - 提供记忆修复功能
"""
import os
import sys
import logging
import json
from pathlib import Path
import time

# 设置日志
logger = logging.getLogger(__name__)

def fix_memory_format():
    """
    修复记忆文件格式
    
    Returns:
        bool: 修复成功返回True，否则返回False
    """
    logger.info("开始修复记忆文件...")
    
    # 获取项目根目录和记忆文件路径
    root_dir = Path.cwd()
    memory_path = root_dir / "data" / "memory" / "rag-memory.json"
    
    if not memory_path.exists():
        logger.error(f"记忆文件不存在: {memory_path}")
        return False
    
    # 尝试修复记忆文件
    try:
        # 读取记忆文件
        with open(memory_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                logger.error("记忆文件格式错误，无法解析JSON")
                return False
        
        # 判断是否需要修复
        need_fix = False
        fixed_data = {}
        
        for chat_id, conversations in data.items():
            fixed_data[chat_id] = []
            
            for entry in conversations:
                if not isinstance(entry, dict):
                    logger.error(f"会话 {chat_id} 中有无效条目: {entry}")
                    continue
                
                # 检查必要字段
                if "sender_text" not in entry or "receiver_text" not in entry:
                    need_fix = True
                    # 尝试从旧格式转换
                    if "sender" in entry and "receiver" in entry:
                        fixed_entry = {
                            "sender_text": entry["sender"],
                            "receiver_text": entry["receiver"],
                            "timestamp": entry.get("timestamp", ""),
                            "importance": entry.get("importance", 0.5)
                        }
                        fixed_data[chat_id].append(fixed_entry)
                else:
                    fixed_data[chat_id].append(entry)
        
        # 如果需要修复，保存修复后的数据
        if need_fix:
            # 创建备份
            backup_path = memory_path.with_name(f"{memory_path.stem}-backup-{int(time.time())}.json")
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"已创建备份文件: {backup_path}")
            
            # 保存修复后的数据
            with open(memory_path, 'w', encoding='utf-8') as f:
                json.dump(fixed_data, f, ensure_ascii=False, indent=2)
            logger.info("记忆文件修复成功")
            return True
        else:
            logger.info("记忆文件格式正确，无需修复")
            return False
            
    except Exception as e:
        logger.error(f"修复过程中出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False 
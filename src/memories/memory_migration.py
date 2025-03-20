"""
记忆格式迁移脚本 - 将旧格式记忆转换为新格式
[已弃用] 请使用 src.tools.memory_migration 模块
"""
import os
import json
import logging
import re
import warnings
from datetime import datetime
from typing import Dict, Any, List

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 发出弃用警告
warnings.warn(
    "src.memories.memory_migration 模块已弃用，请使用 src.tools.memory_migration",
    DeprecationWarning,
    stacklevel=2
)

# 从新模块导入功能，保持向后兼容
try:
    from src.tools.memory_migration import migrate_memory_format, clean_memory_text
except ImportError:
    # 保留原始实现作为备份
    def clean_memory_text(text: str) -> str:
        """
        清理记忆文本，过滤掉时间戳和其他固定模式文本
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
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
        # 清理多余空白
        text = text.strip()
        # 替换反斜杠
        text = text.replace('\\', ' ')
        # 替换连续的空格为单个空格
        text = re.sub(r'\s+', ' ', text)
        return text

    # 保留原始功能实现为备份
    def migrate_memory_format():
        logger.warning("使用已弃用的记忆迁移模块，建议更新代码使用 src.tools.memory_migration")
        # 记忆文件路径
        memory_path = os.path.join(os.getcwd(), "data", "memory", "rag-memory.json")
        backup_path = os.path.join(os.getcwd(), "data", "memory", f"rag-memory-backup-{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
        
        if not os.path.exists(memory_path):
            logger.warning(f"记忆文件不存在: {memory_path}")
            return False
        
        # 备份原始文件
        try:
            with open(memory_path, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(original_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"原始记忆文件已备份到: {backup_path}")
        except Exception as e:
            logger.error(f"备份记忆文件失败: {str(e)}")
            return False
        
        # 提取和转换记忆数据
        try:
            # 初始化新格式数据，保留embeddings数据
            new_format_data = {}
            
            # 保留embeddings数据，确保向量索引正常工作
            if "embeddings" in original_data:
                logger.info("保留embeddings数据...")
                new_format_data["embeddings"] = original_data["embeddings"]
            
            # 提取所有以conversation开头的键值对
            for key, value in original_data.items():
                if key.startswith("conversation"):
                    # 检查并清理会话数据中的文本
                    cleaned_entries = []
                    for entry in value:
                        # 深度复制条目以避免修改原始数据
                        cleaned_entry = entry.copy()
                        if "sender_text" in cleaned_entry:
                            cleaned_entry["sender_text"] = clean_memory_text(cleaned_entry["sender_text"])
                        if "receiver_text" in cleaned_entry:
                            cleaned_entry["receiver_text"] = clean_memory_text(cleaned_entry["receiver_text"])
                        cleaned_entries.append(cleaned_entry)
                    
                    new_format_data[key] = cleaned_entries
                    logger.info(f"保留并清理原有会话数据: {key}")
            
            # 检查是否有旧格式的记忆数据
            if "memories" in original_data:
                logger.info("检测到旧格式memories字段，开始转换...")
                memories = original_data["memories"]
                
                # 计算下一个会话索引
                next_index = 0
                for key in new_format_data.keys():
                    if key.startswith("conversation"):
                        try:
                            index = int(key.replace("conversation", ""))
                            next_index = max(next_index, index + 1)
                        except:
                            pass
                
                # 将旧格式记忆转换为新格式
                memory_entries = []
                for memory_key, memory_value in memories.items():
                    # 清理文本
                    cleaned_key = clean_memory_text(memory_key)
                    cleaned_value = clean_memory_text(memory_value)
                    
                    if cleaned_key and cleaned_value:
                        memory_entry = {
                            "bot_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "sender_id": "未知用户",
                            "sender_text": cleaned_key,
                            "receiver_id": "AI助手",
                            "receiver_text": cleaned_value,
                            "emotion": "None",
                            "is_initiative": False
                        }
                        memory_entries.append(memory_entry)
                
                if memory_entries:
                    conversation_key = f"conversation{next_index}"
                    new_format_data[conversation_key] = memory_entries
                    logger.info(f"已将 {len(memory_entries)} 条旧格式记忆转换为新格式，索引: {conversation_key}")
            
            # 保存新格式数据
            with open(memory_path, 'w', encoding='utf-8') as f:
                json.dump(new_format_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"记忆迁移完成，保存到: {memory_path}")
            logger.info(f"总共保留 {len([k for k in new_format_data.keys() if k.startswith('conversation')])} 个会话")
            if "embeddings" in new_format_data:
                logger.info("已保留向量嵌入数据，确保检索功能正常")
            
            return True
        except Exception as e:
            logger.error(f"迁移记忆格式失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # 尝试恢复备份
            try:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                
                with open(memory_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"已从备份恢复记忆文件")
            except Exception as restore_err:
                logger.error(f"恢复备份失败: {str(restore_err)}")
            
            return False

if __name__ == "__main__":
    print("开始迁移记忆格式...")
    result = migrate_memory_format()
    if result:
        print("记忆格式迁移成功！")
    else:
        print("记忆格式迁移失败，请查看日志获取详细信息。") 
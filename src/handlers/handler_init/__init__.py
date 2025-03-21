"""
记忆系统包初始化文件 - 重定向到新的记忆模块
"""
import os
import logging
import warnings
from typing import Optional, Dict, List, Any, Tuple

# 从新模块导入所需函数和类
from src.handlers.memory_manager import (
    init_memory, remember, retrieve, is_important,
    get_memory_processor, get_memory_stats,
    clear_memories, save_memories, init_rag_from_config, get_rag,
    get_relevant_memories
)

# 设置日志
logger = logging.getLogger('main')

# 输出警告信息
warnings.warn(
    "从src.memories导入已弃用，请直接从src.handlers.memory_manager导入所需功能",
    DeprecationWarning, stacklevel=2
)

# 兼容性导出 - 保持旧API可用
setup_memory = init_memory
get_memory_handler = get_memory_processor
setup_rag = init_rag_from_config

# 导出所有重要函数，保持原始API兼容
__all__ = [
    'init_memory', 'remember', 'retrieve', 'is_important',
    'get_memory_processor', 'get_memory_stats',
    'clear_memories', 'save_memories', 'init_rag_from_config', 'get_rag',
    'get_relevant_memories',
    # 兼容性别名
    'setup_memory', 'get_memory_handler', 'setup_rag'
] 
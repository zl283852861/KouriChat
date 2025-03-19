"""
错误处理模块
提供错误处理、记录和报告功能
"""

import logging
import traceback
from typing import Optional, Dict, Any, List

logger = logging.getLogger('main')

class ErrorHandler:
    """错误处理器类，负责处理、记录和报告错误"""
    
    def __init__(self):
        self.error_count = 0
        self.error_history = []
        
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> str:
        """
        处理错误并返回用户友好的错误消息
        
        Args:
            error: 捕获的异常
            context: 错误发生时的上下文信息
            
        Returns:
            用户友好的错误消息
        """
        self.error_count += 1
        error_type = type(error).__name__
        error_msg = str(error)
        
        # 记录详细错误信息
        logger.error(f"错误类型: {error_type}, 错误信息: {error_msg}")
        if context:
            logger.error(f"错误上下文: {context}")
        logger.error(traceback.format_exc())
        
        # 保存错误历史
        self.error_history.append({
            'type': error_type,
            'message': error_msg,
            'context': context,
            'traceback': traceback.format_exc()
        })
        
        # 限制历史记录长度
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]
        
        # 返回友好的错误消息
        return f"发生了一个错误: {error_msg}"
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        return {
            'total_errors': self.error_count,
            'recent_errors': len(self.error_history)
        }
    
    def clear_error_history(self) -> None:
        """清除错误历史记录"""
        self.error_history = [] 
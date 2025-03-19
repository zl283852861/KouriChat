"""
Web消息处理模块
处理与Web接口相关的消息交互
"""

import logging
import json
from typing import Dict, Any, Optional, List

logger = logging.getLogger('main')

class WebMessageHandler:
    """Web消息处理器，负责处理来自Web界面的消息"""
    
    def __init__(self, message_handler=None):
        self.message_handler = message_handler
        self.connected_clients = set()
        self.message_history = []
        
    def handle_web_message(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """
        处理来自Web客户端的消息
        
        Args:
            message: 消息内容
            client_id: 客户端ID
            
        Returns:
            响应消息
        """
        logger.info(f"收到Web消息: {message}")
        
        # 记录客户端连接
        self.connected_clients.add(client_id)
        
        # 处理不同类型的消息
        message_type = message.get('type', '')
        
        if message_type == 'chat':
            return self._handle_chat_message(message, client_id)
        elif message_type == 'command':
            return self._handle_command_message(message, client_id)
        else:
            logger.warning(f"未知消息类型: {message_type}")
            return {'status': 'error', 'message': '未知消息类型'}
    
    def _handle_chat_message(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """处理聊天类型的消息"""
        content = message.get('content', '')
        
        if not content:
            return {'status': 'error', 'message': '消息内容不能为空'}
        
        # 记录消息历史
        self.message_history.append({
            'client_id': client_id,
            'content': content,
            'timestamp': message.get('timestamp', '')
        })
        
        # 如果存在消息处理器，则传递消息
        if self.message_handler:
            try:
                response = self.message_handler.handle_user_message(
                    content=content,
                    chat_id=f"web_{client_id}",
                    sender_name="web_user",
                    username=client_id,
                    is_group=False
                )
                return {'status': 'success', 'message': response}
            except Exception as e:
                logger.error(f"处理Web聊天消息失败: {str(e)}")
                return {'status': 'error', 'message': f'处理消息失败: {str(e)}'}
        else:
            return {'status': 'error', 'message': '消息处理器未初始化'}
    
    def _handle_command_message(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """处理命令类型的消息"""
        command = message.get('command', '')
        
        if command == 'get_history':
            return {
                'status': 'success',
                'history': self.message_history[-50:]  # 返回最近50条消息
            }
        elif command == 'clear_history':
            self.message_history = []
            return {'status': 'success', 'message': '历史记录已清除'}
        else:
            return {'status': 'error', 'message': f'未知命令: {command}'}
    
    def broadcast_message(self, message: str) -> None:
        """广播消息到所有连接的客户端"""
        # 实际实现需要与WebServer集成
        logger.info(f"广播消息: {message} 到 {len(self.connected_clients)} 个客户端")
    
    def disconnect_client(self, client_id: str) -> None:
        """断开客户端连接"""
        if client_id in self.connected_clients:
            self.connected_clients.remove(client_id)
            logger.info(f"客户端断开连接: {client_id}") 
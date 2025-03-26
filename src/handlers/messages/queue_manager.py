"""
消息队列管理模块
负责管理消息队列、缓存和定时处理
"""

import threading
import time
import logging
from datetime import datetime
from src.handlers.messages.base_handler import BaseHandler

# 获取logger
logger = logging.getLogger('main')

class QueueManager(BaseHandler):
    """消息队列管理器，负责消息缓存和队列管理"""
    
    def __init__(self, message_manager=None):
        """
        初始化队列管理器
        
        Args:
            message_manager: 消息管理器实例的引用
        """
        super().__init__(message_manager)
        # 消息缓存和队列
        self.message_cache = {}  # 用户消息缓存 {username: [message_objects]}
        self.message_timer = {}  # 用户消息处理定时器 {username: timer}
        self.last_message_time = {}  # 用户最后发送消息的时间 {username: timestamp}
        
        # 群聊@消息缓存
        self.group_at_cache = {}  # 群聊@消息缓存 {group_id: [message_objects]}
        self.group_at_timer = {}  # 群聊@消息定时器 {group_id: timer}
        
        # 全局消息队列
        self.global_message_queue = []  # 全局消息队列
        self.global_message_queue_lock = threading.Lock()  # 全局消息队列锁
        self.is_processing_queue = False  # 是否正在处理队列
        self.queue_process_timer = None  # 队列处理定时器
        
        # 打字速度记录
        self._typing_speeds = {}  # 用户打字速度记录 {username: speed}
        
        # 启动定时清理任务
        self._start_cleanup_timer()
    
    def _start_cleanup_timer(self):
        """启动定时清理定时器"""
        cleanup_timer = threading.Timer(30.0, self.cleanup_message_queues)
        cleanup_timer.daemon = True
        cleanup_timer.start()
    
    def cache_message(self, message_obj, username):
        """
        缓存用户消息并设置处理定时器
        
        Args:
            message_obj: 消息对象，包含消息内容和元数据
            username: 用户ID
            
        Returns:
            bool: 是否成功缓存
        """
        current_time = time.time()
        
        # 取消现有定时器
        if username in self.message_timer and self.message_timer[username]:
            self.message_timer[username].cancel()
        
        # 添加到消息缓存
        if username not in self.message_cache:
            self.message_cache[username] = []
        
        # 记录时间并添加消息
        self.last_message_time[username] = current_time
        self.message_cache[username].append(message_obj)
        
        # 计算等待时间并设置新的定时器
        wait_time = self._calculate_wait_time(username, len(self.message_cache[username]))
        timer = threading.Timer(wait_time, self._process_cached_messages, args=[username])
        timer.daemon = True
        timer.start()
        self.message_timer[username] = timer
        
        # 记录日志
        logger.info(f"缓存消息: {message_obj.get('content', '')[:30]}... | 等待时间: {wait_time:.1f}秒")
        
        return True
    
    def cache_group_at_message(self, message_obj, group_id):
        """
        缓存群聊@消息并添加到全局处理队列
        
        Args:
            message_obj: 消息对象，包含群ID、发送者等信息
            group_id: 群聊ID
            
        Returns:
            bool: 是否成功缓存
        """
        current_time = time.time()
        
        # 添加时间戳
        message_obj['added_time'] = current_time
        
        # 将消息添加到全局处理队列
        with self.global_message_queue_lock:
            self.global_message_queue.append(message_obj)
            
            # 如果没有正在处理的队列，启动处理
            if not self.is_processing_queue:
                # 设置处理状态
                self.is_processing_queue = True
                # 设置延迟处理定时器，等待一小段时间收集更多可能的消息
                if self.queue_process_timer:
                    self.queue_process_timer.cancel()
                
                self.queue_process_timer = threading.Timer(2.0, self._process_global_message_queue)
                self.queue_process_timer.daemon = True
                self.queue_process_timer.start()
        
        # 同时保持群聊缓存机制作为备份
        if group_id not in self.group_at_cache:
            self.group_at_cache[group_id] = []
        
        # 添加到群聊@消息缓存
        self.group_at_cache[group_id].append(message_obj)
        
        logger.info(f"缓存群聊@消息: 群: {group_id}, 发送者: {message_obj.get('sender_name', '')}, 已添加到全局队列")
        return True
    
    def _calculate_wait_time(self, username, msg_count):
        """
        计算消息等待时间
        
        Args:
            username: 用户ID
            msg_count: 当前缓存的消息数量
            
        Returns:
            float: 等待时间(秒)
        """
        base_wait_time = 3.0
        typing_speed = self._estimate_typing_speed(username)
        
        if msg_count == 1:
            wait_time = base_wait_time + 5.0
        else:
            estimated_typing_time = min(4.0, typing_speed * 20)  # 假设用户输入20个字符
            wait_time = base_wait_time + estimated_typing_time
            
        logger.debug(f"消息等待时间计算: 基础={base_wait_time}秒, 打字速度={typing_speed:.2f}秒/字, 结果={wait_time:.1f}秒")
        
        return wait_time
    
    def _estimate_typing_speed(self, username):
        """
        估计用户的打字速度(秒/字符)
        
        Args:
            username: 用户ID
            
        Returns:
            float: 打字速度(秒/字符)
        """
        # 如果没有足够的历史消息，使用默认值
        if username not in self.message_cache or len(self.message_cache[username]) < 2:
            # 根据用户ID是否存在于last_message_time中返回不同的默认值
            # 如果是新用户，给予更长的等待时间
            if username not in self.last_message_time:
                typing_speed = 0.2  # 新用户默认速度：每字0.2秒
            else:
                typing_speed = 0.15  # 已知用户默认速度：每字0.15秒
            
            logger.info(f"用户打字速度: {typing_speed:.2f}秒/字符")
            return typing_speed
        
        # 获取最近的两条消息
        messages = self.message_cache[username]
        if len(messages) < 2:
            typing_speed = 0.15
            logger.info(f"用户打字速度: {typing_speed:.2f}秒/字符")
            return typing_speed
        
        # 按时间戳排序，确保我们比较的是连续的消息
        recent_msgs = sorted(messages, key=lambda x: x.get('timestamp', 0))[-2:]
        
        # 计算时间差和字符数
        time_diff = recent_msgs[1].get('timestamp', 0) - recent_msgs[0].get('timestamp', 0)
        
        # 获取实际内容（去除时间戳和前缀）
        content = recent_msgs[0].get('content', '')
        cleaned_content = self._clean_message_content(content)
        char_count = len(cleaned_content)
        
        # 如果时间差或字符数无效，使用默认值
        if time_diff <= 0 or char_count <= 0:
            typing_speed = 0.15
            logger.info(f"用户打字速度: {typing_speed:.2f}秒/字符")
            return typing_speed
        
        # 计算打字速度（秒/字）
        typing_speed = time_diff / char_count
        
        # 应用平滑因子，避免极端值
        # 如果我们有历史记录的打字速度，将其纳入考虑
        if username in self._typing_speeds:
            prev_speed = self._typing_speeds[username]
            # 使用加权平均，新速度权重0.4，历史速度权重0.6
            typing_speed = 0.4 * typing_speed + 0.6 * prev_speed
        
        # 存储计算出的打字速度
        self._typing_speeds[username] = typing_speed
        
        # 限制在合理范围内：0.2秒/字 到 1.2秒/字
        typing_speed = max(0.2, min(1.2, typing_speed))
        
        logger.info(f"用户打字速度: {typing_speed:.2f}秒/字符")
        return typing_speed
    
    def _process_cached_messages(self, username):
        """
        处理用户缓存的消息
        
        Args:
            username: 用户ID
            
        Returns:
            bool: 是否成功处理
        """
        try:
            if not self.message_cache.get(username):
                return False
            
            # 获取消息
            messages = self.message_cache[username]
            messages.sort(key=lambda x: x.get('timestamp', 0))
            
            # 传给消息管理器处理
            if self.message_manager:
                self.message_manager.process_cached_user_messages(username, messages)
            
            # 清理缓存和定时器
            self.message_cache[username] = []
            if username in self.message_timer and self.message_timer[username]:
                self.message_timer[username].cancel()
                self.message_timer[username] = None
            
            return True
        except Exception as e:
            logger.error(f"处理缓存消息失败: {str(e)}")
            return False
    
    def _process_global_message_queue(self):
        """处理全局消息队列，按顺序处理所有群聊的消息"""
        try:
            # 获取队列中的所有消息
            with self.global_message_queue_lock:
                if not self.global_message_queue:
                    self.is_processing_queue = False
                    return
                
                current_message = self.global_message_queue.pop(0)
            
            # 处理当前消息
            group_id = current_message['group_id']
            logger.info(f"从全局队列处理消息: 群ID: {group_id}, 发送者: {current_message['sender_name']}")
            
            # 调用消息处理方法
            if self.message_manager:
                self.message_manager.process_group_at_message(current_message)
            
            # 处理完成后，检查队列中是否还有消息
            with self.global_message_queue_lock:
                if self.global_message_queue:
                    # 如果还有消息，设置定时器处理下一条
                    # 使用较短的延迟，但仍然保持一定间隔，避免消息发送过快
                    self.queue_process_timer = threading.Timer(1.0, self._process_global_message_queue)
                    self.queue_process_timer.daemon = True
                    self.queue_process_timer.start()
                else:
                    # 如果没有更多消息，重置处理状态
                    self.is_processing_queue = False
        
        except Exception as e:
            logger.error(f"处理全局消息队列失败: {str(e)}")
            # 重置处理状态，防止队列处理卡死
            with self.global_message_queue_lock:
                self.is_processing_queue = False
    
    def cleanup_message_queues(self):
        """清理过期的消息队列和缓存"""
        try:
            current_time = time.time()
            
            # 清理用户消息缓存
            for username, messages in list(self.message_cache.items()):
                # 移除超过5分钟的消息
                self.message_cache[username] = [
                    msg for msg in messages 
                    if msg.get('timestamp', current_time) > current_time - 300
                ]
                
                # 如果没有消息，清理相关记录
                if not self.message_cache[username]:
                    if username in self.message_timer and self.message_timer[username]:
                        self.message_timer[username].cancel()
                    self.message_timer.pop(username, None)
                    self.message_cache.pop(username, None)
            
            # 清理群聊@消息缓存
            for group_id, messages in list(self.group_at_cache.items()):
                # 移除超过5分钟的消息
                self.group_at_cache[group_id] = [
                    msg for msg in messages 
                    if msg.get('added_time', current_time) > current_time - 300
                ]
                
                # 如果没有消息，清理相关记录
                if not self.group_at_cache[group_id]:
                    if group_id in self.group_at_timer and self.group_at_timer[group_id]:
                        self.group_at_timer[group_id].cancel()
                    self.group_at_timer.pop(group_id, None)
                    self.group_at_cache.pop(group_id, None)
            
            # 清理全局队列中的过期消息
            with self.global_message_queue_lock:
                # 移除超过5分钟的消息
                self.global_message_queue = [
                    msg for msg in self.global_message_queue 
                    if msg.get('added_time', current_time) > current_time - 300
                ]
            
            # 重新设置清理定时器，每10分钟执行一次
            cleanup_timer = threading.Timer(600.0, self.cleanup_message_queues)
            cleanup_timer.daemon = True
            cleanup_timer.start()
            
            logger.info("已完成消息队列清理操作")
        except Exception as e:
            logger.error(f"清理消息队列失败: {str(e)}")
            # 即使出错也要重新设置定时器
            cleanup_timer = threading.Timer(600.0, self.cleanup_message_queues)
            cleanup_timer.daemon = True
            cleanup_timer.start()

if __name__ == "__main__":
    import logging
    import time
    import threading
    from unittest.mock import MagicMock
    
    # 配置基本日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('test')
    
    class MockMessageManager:
        """模拟MessageManager类"""
        def __init__(self):
            self.process_cached_user_messages = MagicMock(return_value="模拟处理结果")
            self.process_group_at_message = MagicMock(return_value="模拟群聊处理结果")
            
        def get_module(self, name):
            return None
    
    def test_queue_manager():
        print("开始测试队列管理器...")
        
        # 创建模拟对象
        manager = MockMessageManager()
        queue_manager = QueueManager(manager)
        
        # 测试添加私聊消息到缓存
        users = ["用户1", "用户2", "用户3"]
        
        for i, user in enumerate(users):
            for j in range(3):  # 每个用户添加3条消息
                message = {
                    "content": f"测试消息 {j+1} 来自 {user}",
                    "timestamp": time.time(),
                    "chat_id": user
                }
                success = queue_manager.cache_message(message, user)
                print(f"缓存来自 {user} 的消息 {j+1}: {'成功' if success else '失败'}")
                
                # 如果是第一个用户的最后一条消息，不等待定时器，直接执行处理
                if i == 0 and j == 2:
                    print(f"\n手动触发处理 {user} 的消息")
                    queue_manager._process_cached_messages(user)
                else:
                    # 短暂等待，避免消息被立即处理
                    time.sleep(0.1)
        
        # 等待一小段时间，让部分定时任务执行
        print("\n等待其他定时器处理消息...")
        time.sleep(3)
        
        # 打印消息缓存状态
        print("\n消息缓存状态:")
        for user, messages in queue_manager.message_cache.items():
            print(f"用户 {user}: {len(messages)} 条缓存消息")
        
        # 测试群聊消息缓存
        groups = ["群组1", "群组2"]
        
        for group in groups:
            for j in range(2):  # 每个群组添加2条消息
                message = {
                    "content": f"测试群聊消息 {j+1} 来自 {group}",
                    "group_id": group,
                    "sender_name": f"群成员{j+1}",
                    "username": f"user{j+1}"
                }
                success = queue_manager.cache_group_at_message(message, group)
                print(f"缓存来自 {group} 的群聊消息 {j+1}: {'成功' if success else '失败'}")
        
        # 测试全局消息队列处理
        print("\n全局消息队列状态:")
        print(f"队列长度: {len(queue_manager.global_message_queue)}")
        print(f"正在处理: {queue_manager.is_processing_queue}")
        
        # 如果有未处理的消息，手动触发处理
        if queue_manager.global_message_queue and not queue_manager.is_processing_queue:
            print("手动触发全局队列处理")
            queue_manager._process_global_message_queue()
        
        # 等待一小段时间，让处理完成
        time.sleep(1)
        
        # 测试清理功能
        print("\n测试消息队列清理:")
        queue_manager.cleanup_message_queues()
        
        # 显示清理后的状态
        print("\n清理后的消息缓存状态:")
        for user, messages in queue_manager.message_cache.items():
            print(f"用户 {user}: {len(messages)} 条缓存消息")
        
        print(f"全局队列长度: {len(queue_manager.global_message_queue)}")
        
        # 计算等待时间
        wait_time = queue_manager._calculate_wait_time("测试用户", 3)
        print(f"\n计算的等待时间(3条消息): {wait_time:.2f}秒")
        
        print("队列管理器测试完成")
    
    # 运行测试
    test_queue_manager() 
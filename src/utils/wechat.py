"""
微信接口模块
提供与微信交互的接口，包括消息发送、接收和文件操作
"""

import os
import logging
import time
import queue
import traceback
import wxauto
import pythoncom  # 添加pythoncom导入
import random
from typing import Dict, List, Any, Optional, Tuple, Union

logger = logging.getLogger('main')

class WeChat:
    """微信接口类，提供与微信交互的方法"""
    
    def __init__(self):
        """初始化WeChat类"""
        try:
            pythoncom.CoInitialize()  # 初始化COM环境
            self.wx = wxauto.WeChat()
            logger.info("微信接口初始化完成")
            
            # 检查API兼容性
            self._check_api_compatibility()
            
            # 设置图标信息
            self.A_MyIcon = self.IconInfo()
            self.A_MyIcon.Name = self.wx.GetSelfName() if hasattr(self.wx, 'GetSelfName') else "未知机器人"
            
            # 跟踪已添加的监听聊天
            self._listen_chats = set()
            
            # 监听窗口相关
            self._listen_windows = {}  # 存储监听窗口的引用
            self._window_handles = {}  # 存储窗口句柄
            self._current_chat = None  # 当前活动的聊天
            self._last_window_check = 0  # 上次检查窗口的时间
            self._window_check_interval = 5  # 窗口检查间隔（秒）
            
            # 消息缓存
            self._last_messages = {}  # 存储每个聊天的最后一条消息
            
            # 重连相关
            self._reconnect_attempts = 0
            self._max_reconnect_attempts = 3
            self._reconnect_delay = 10  # 重连等待时间（秒）
            self._last_reconnect_time = 0
            self._check_interval = 600  # 窗口检查间隔（秒）
            
            logger.info("微信接口初始化完成")
        except Exception as e:
            logger.error(f"微信接口初始化失败: {str(e)}")
            self.wx = None
            self.A_MyIcon = self.IconInfo()
            # 出错时也尝试释放COM
            try:
                pythoncom.CoUninitialize()
            except:
                pass
    
    def _check_api_compatibility(self):
        """检查wxauto API兼容性，记录可用的方法"""
        required_methods = [
            "GetMsgs", "GetAllMessage", "GetLastMessage",
            "SendFiles", "ChatWith", "SendMsg"
        ]
        
        compatibility_report = []
        for method in required_methods:
            if hasattr(self.wx, method):
                compatibility_report.append(f"{method}: 可用")
            else:
                compatibility_report.append(f"{method}: 不可用")
        
        # 记录兼容性报告
        logger.info("WeChat API兼容性检查结果:")
        for report in compatibility_report:
            logger.info(f"  - {report}")
    
    class IconInfo:
        """图标信息类，提供名称等属性"""
        def __init__(self):
            self.Name = "默认机器人"  # 默认名称
    
    def _get_chat_window(self, who: str) -> Optional[Any]:
        """
        获取聊天窗口对象
        
        Args:
            who: 聊天对象名称
            
        Returns:
            Optional[Any]: 聊天窗口对象或None
        """
        try:
            current_time = time.time()
            
            # 如果已经有缓存的窗口且距离上次检查时间不超过间隔，直接返回
            if who in self._listen_windows:
                if current_time - self._last_window_check < self._window_check_interval:
                    return self._listen_windows[who]
            
            # 更新检查时间
            self._last_window_check = current_time
            
            # 如果当前聊天已经是目标聊天，直接获取窗口而不进行切换
            if self._current_chat != who:
                # 切换到指定聊天
                if not self.ChatWith(who):
                    return None
            
            # 获取当前活动的聊天窗口
            windows = wxauto.GetWindowsWithTitle(who)
            if not windows:
                logger.error(f"找不到聊天窗口: {who}")
                return None
            
            # 缓存并返回窗口对象
            window = windows[0]
            self._listen_windows[who] = window
            self._window_handles[who] = window.handle
            return window
            
        except Exception as e:
            logger.error(f"获取聊天窗口失败 {who}: {str(e)}")
            return None
    
    def _ensure_window_active(self, who: str) -> bool:
        """
        确保聊天窗口处于活动状态
        
        Args:
            who: 聊天对象名称
            
        Returns:
            bool: 是否成功激活窗口
        """
        try:
            # 如果当前聊天已经是目标聊天，无需切换
            if self._current_chat == who:
                return True
                
            # 直接使用ChatWith切换到目标聊天，而不是先调用_get_chat_window
            if not self.ChatWith(who):
                logger.error(f"无法切换到聊天 {who}")
                return False
            
            # 获取当前活动的聊天窗口
            windows = wxauto.GetWindowsWithTitle(who)
            if not windows:
                logger.error(f"找不到聊天窗口: {who}")
                return False
            
            # 缓存并使用窗口对象
            window = windows[0]
            self._listen_windows[who] = window
            self._window_handles[who] = window.handle
            
            # 如果窗口未激活，则激活它
            if not window.isActive:
                window.activate()
                time.sleep(0.2)  # 减少等待时间
            
            self._current_chat = who
            return True
        except Exception as e:
            logger.error(f"激活窗口失败 {who}: {str(e)}")
            return False
    
    def ChatWith(self, who: str) -> bool:
        """
        切换到指定聊天
        
        Args:
            who: 聊天对象名称
            
        Returns:
            bool: 是否成功
        """
        try:
            if not self.wx:
                logger.error("微信接口未初始化")
                return False
            
            # 如果当前聊天已经是目标聊天，无需切换
            if self._current_chat == who:
                return True
            
            # 如果没有缓存的窗口，使用wxauto切换
            result = self.wx.ChatWith(who)
            if result:
                self._current_chat = who
                logger.info(f"切换到聊天: {who}")
            
            return result
        except Exception as e:
            logger.error(f"切换聊天失败 {who}: {str(e)}")
            return False
    
    def SendMsg(self, msg: str, who: str = None) -> bool:
        """
        发送文本消息
        
        Args:
            msg: 消息内容
            who: 接收者，如果为None则使用当前聊天
            
        Returns:
            bool: 是否成功
        """
        try:
            if not self.wx:
                logger.error("微信接口未初始化")
                return False
            
            if who:
                # 确保窗口处于活动状态
                if not self._ensure_window_active(who):
                    logger.error(f"无法切换到聊天 {who}")
                    return False
            
            # 发送消息
            self.wx.SendMsg(msg)
            logger.info(f"发送消息到 {who if who else '当前聊天'}: {msg[:30]}...")
            return True
        except Exception as e:
            logger.error(f"发送消息失败 {msg[:20]}: {str(e)}")
            return False
    
    def SendFiles(self, file_path: str, who: str = None) -> bool:
        """
        发送文件
        
        Args:
            file_path: 文件路径
            who: 接收者，如果为None则使用当前聊天
            
        Returns:
            bool: 是否成功
        """
        try:
            if not self.wx:
                logger.error("微信接口未初始化")
                return False
            
            if who:
                # 确保窗口处于活动状态
                if not self._ensure_window_active(who):
                    logger.error(f"无法切换到聊天 {who}")
                    return False
            
            # 发送文件
            self.wx.SendFiles(file_path)
            logger.info(f"发送文件到 {who if who else '当前聊天'}: {file_path}")
            return True
        except Exception as e:
            logger.error(f"发送文件失败 {file_path}: {str(e)}")
            return False
    
    def AddListenChat(self, who: str, savepic: bool = False, savefile: bool = False) -> bool:
        """
        添加监听的聊天
        
        Args:
            who: 聊天对象名称
            savepic: 是否保存图片
            savefile: 是否保存文件
            
        Returns:
            bool: 是否成功
        """
        try:
            if not self.wx:
                logger.error("微信接口未初始化")
                return False
            
            # 如果已经在监听，直接返回成功
            if who in self._listen_chats:
                logger.info(f"聊天 {who} 已在监听列表中")
                return True
            
            # 获取并激活聊天窗口
            if not self._ensure_window_active(who):
                logger.error(f"无法切换到聊天 {who}，监听添加失败")
                return False
            
            # 获取当前聊天内容作为基准
            try:
                current_content = self.wx.GetAllMessage()
                if who not in self._last_messages:
                    self._last_messages[who] = current_content
            except Exception as e:
                logger.warning(f"获取初始消息失败，将在下次检查时更新: {str(e)}")
            
            # 添加到监听列表
            self._listen_chats.add(who)
            logger.info(f"成功添加聊天监听: {who}")
            return True
            
        except Exception as e:
            logger.error(f"添加监听失败 {who}: {str(e)}")
            return False
    
    def RemoveListenChat(self, who: str) -> bool:
        """
        移除聊天监听
        
        Args:
            who: 聊天对象名称
            
        Returns:
            bool: 是否成功
        """
        try:
            if who in self._listen_chats:
                self._listen_chats.remove(who)
            if who in self._listen_windows:
                del self._listen_windows[who]
            if who in self._window_handles:
                del self._window_handles[who]
            if self._current_chat == who:
                self._current_chat = None
            logger.info(f"移除聊天监听: {who}")
            return True
        except Exception as e:
            logger.error(f"移除监听失败 {who}: {str(e)}")
            return False
    
    def IsListening(self, who: str) -> bool:
        """
        检查是否已添加监听
        
        Args:
            who: 聊天对象名称
            
        Returns:
            bool: 是否已添加监听
        """
        return who in self._listen_chats
    
    def GetSessionList(self) -> List[str]:
        """
        获取会话列表
        
        Returns:
            List[str]: 会话列表
        """
        try:
            if not self.wx:
                logger.error("微信接口未初始化")
                return []
            
            # 调用wxauto获取会话列表
            sessions = self.wx.GetSessionList()
            return sessions
        except Exception as e:
            logger.error(f"获取会话列表失败: {str(e)}")
            return []
    
    def GetListenMessageQuiet(self) -> Dict:
        """
        静默获取监听消息，出错时不打印错误信息或使用更低级别日志
        
        Returns:
            Dict: 消息字典
        """
        try:
            # 使用GetAllMessage方法（已确认可用）
            if hasattr(self.wx, "GetAllMessage"):
                msgs = self.wx.GetAllMessage()
                if msgs:
                    logger.debug(f"静默模式(GetAllMessage)获取到 {len(msgs)} 条消息")
                    return msgs
            
            # 不再尝试使用GetMsgs和GetLastMessage，因为它们不可用
            return {}
        except Exception as e:
            logger.debug(f"静默获取消息失败: {str(e)}")
            return {}

    def GetListenMessage(self) -> Dict:
        """
        获取监听消息
        
        Returns:
            Dict: 消息字典
        """
        try:
            if not self.wx:
                logger.error("微信接口未初始化")
                return {}
            
            # 只使用GetAllMessage方法（已确认可用）
            if hasattr(self.wx, "GetAllMessage"):
                msgs = self.wx.GetAllMessage()
                if msgs:
                    logger.debug(f"获取到 {len(msgs)} 条消息")
                    return msgs
            
            # 如果GetAllMessage失败，返回空字典
            logger.debug("GetAllMessage方法未返回消息")
            return {}
        except Exception as e:
            logger.error(f"获取消息失败: {str(e)}")
            return {}
    
    def _compare_messages(self, msg1, msg2) -> bool:
        """
        比较两条消息是否相同
        
        Args:
            msg1: 第一条消息
            msg2: 第二条消息
            
        Returns:
            bool: 是否相同
        """
        try:
            # 如果两个对象是同一个，直接返回True
            if msg1 is msg2:
                return True
                
            # 如果是简单的字符串或者基本类型，直接比较
            if isinstance(msg1, (str, int, float, bool)) and isinstance(msg2, (str, int, float, bool)):
                return msg1 == msg2
                
            # 如果是简单的字典或列表，转为JSON字符串比较
            if isinstance(msg1, (dict, list)) and isinstance(msg2, (dict, list)):
                import json
                try:
                    return json.dumps(msg1, sort_keys=True) == json.dumps(msg2, sort_keys=True)
                except:
                    pass
            
            # 如果是对象，尝试比较关键属性
            if hasattr(msg1, 'content') and hasattr(msg2, 'content'):
                if msg1.content != msg2.content:
                    return False
            
            if hasattr(msg1, 'sender') and hasattr(msg2, 'sender'):
                if msg1.sender != msg2.sender:
                    return False
                    
            if hasattr(msg1, 'time') and hasattr(msg2, 'time'):
                if msg1.time != msg2.time:
                    return False
            
            # 尝试使用__eq__方法
            try:
                return msg1 == msg2
            except:
                # 如果上述比较都无法完成，返回False
                return False
                
        except Exception as e:
            logger.error(f"比较消息时出错: {str(e)}")
            return False
    
    def GetInfo(self) -> Dict[str, Any]:
        """
        获取微信信息
        
        Returns:
            Dict[str, Any]: 微信信息
        """
        try:
            if not self.wx:
                return {"name": self.A_MyIcon.Name, "status": "offline"}
            
            return {
                "name": self.A_MyIcon.Name,
                "status": "online",
                "current_chat": self._current_chat,
                "listening_chats": list(self._listen_chats)
            }
        except Exception as e:
            logger.error(f"获取微信信息失败: {str(e)}")
            return {"name": "未知", "status": "error"}

    def initialize_listening(self, listen_list: list) -> bool:
        """
        初始化微信监听，包含重试机制
        
        Args:
            listen_list: 需要监听的聊天列表
            
        Returns:
            bool: 是否成功初始化
        """
        try:
            # 检查微信是否初始化成功
            if not self.wx:
                logger.error("微信接口未初始化")
                return False
                
            # 尝试获取会话列表
            try:
                session_list = self.wx.GetSessionList()
                if not session_list:
                    logger.error("未检测到微信会话列表，请确保微信已登录")
                    return False
                logger.info(f"获取到 {len(session_list)} 个会话")
            except Exception as e:
                logger.error(f"获取会话列表失败: {str(e)}")
                return False
            
            # 备份当前监听状态以便恢复
            old_listen_chats = self._listen_chats.copy()
            
            # 初始化过程要始终重置监听状态
            self._listen_windows.clear()
            self._window_handles.clear()
            self._listen_chats.clear()
            self._last_messages.clear()
            self._current_chat = None
            
            # 记录有效添加计数
            added_count = 0
            skip_count = 0
            error_count = 0
            
            # 循环添加监听对象
            for chat_name in listen_list:
                try:
                    # 检查聊天名称是否在会话列表中
                    chat_exists = False
                    for session in session_list:
                        if isinstance(session, str):
                            if session == chat_name:
                                chat_exists = True
                                break
                        elif hasattr(session, 'name'):
                            if session.name == chat_name:
                                chat_exists = True
                                break
                    
                    if not chat_exists:
                        logger.warning(f"会话列表中找不到聊天: {chat_name}，尝试直接切换")
                        
                    # 尝试切换到该聊天
                    if not self.ChatWith(chat_name):
                        logger.error(f"找不到会话 {chat_name}，跳过监听设置")
                        error_count += 1
                        continue
                    
                    # 短暂暂停确保切换成功
                    time.sleep(0.5)  
                    
                    # 添加监听
                    result = self.AddListenChat(chat_name, savepic=True, savefile=True)
                    if result:
                        added_count += 1
                        logger.info(f"成功添加监听 [{added_count}]: {chat_name}")
                    else:
                        error_count += 1
                        logger.error(f"添加监听失败: {chat_name}")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"处理聊天 {chat_name} 时出错: {str(e)}")
                    continue
            
            # 显示初始化结果统计
            logger.info(f"监听初始化结果: 成功={added_count}, 跳过={skip_count}, 失败={error_count}")
            
            # 只有在成功添加至少一个监听时才算成功
            if added_count > 0:
                # 更新相关时间戳
                self._last_window_check = time.time()
                self._last_reconnect_time = time.time()
                return True
            else:
                # 恢复原有监听
                self._listen_chats = old_listen_chats
                logger.warning("未能添加任何监听，恢复原有监听状态")
                return False
            
        except Exception as e:
            logger.error(f"初始化微信监听失败: {str(e)}")
            return False

    def check_and_reconnect(self) -> bool:
        """
        检查微信连接状态并在必要时重连
        
        Returns:
            bool: 是否成功连接
        """
        try:
            current_time = time.time()
            
            # 检查是否需要重置重连计数
            if current_time - self._last_reconnect_time > 300:  # 5分钟无错误
                if self._reconnect_attempts > 0:
                    logger.info(f"重置重连尝试计数，之前值为: {self._reconnect_attempts}")
                self._reconnect_attempts = 0
            
            # 检查重连次数
            if self._reconnect_attempts >= self._max_reconnect_attempts:
                logger.error(f"达到最大重连次数({self._max_reconnect_attempts})，等待{self._reconnect_delay}秒后重试...")
                time.sleep(self._reconnect_delay)
                self._reconnect_attempts = 0
                self._last_reconnect_time = current_time
                return False
            
            # 记录重连尝试
            self._reconnect_attempts += 1
            logger.info(f"尝试第 {self._reconnect_attempts}/{self._max_reconnect_attempts} 次重连")
            
            # 尝试重新初始化
            try:
                old_wx = self.wx  # 保存旧的wx对象以便比较
                self.wx = wxauto.WeChat()
                session_list = self.wx.GetSessionList()
                
                if not session_list:
                    logger.error("重连后无法获取会话列表")
                    self._last_reconnect_time = current_time
                    return False
                    
                # 检查是否与之前的微信实例相同
                if old_wx and hasattr(old_wx, 'GetSelfName') and hasattr(self.wx, 'GetSelfName'):
                    old_name = old_wx.GetSelfName()
                    new_name = self.wx.GetSelfName()
                    if old_name == new_name:
                        logger.info(f"重连成功，微信用户相同: {new_name}")
                    else:
                        logger.warning(f"微信用户可能已更改: 从 {old_name} 到 {new_name}")
                
            except Exception as e:
                logger.error(f"创建WeChat实例失败: {str(e)}")
                self._last_reconnect_time = current_time
                return False
            
            # 只重新添加长时间未响应的监听
            listen_problem_chats = []
            for chat in self._listen_chats.copy():
                # 检查聊天是否在会话列表中
                if chat not in session_list:
                    logger.warning(f"无法找到会话 {chat}，可能已被删除")
                    continue
                    
                # 检查最近是否收到过该聊天的消息
                chat_active = chat in self._last_messages and (
                    current_time - self._last_window_check < 300)  # 5分钟内有活动
                
                if not chat_active:
                    listen_problem_chats.append(chat)
            
            # 如果有问题聊天，重新添加它们的监听
            if listen_problem_chats:
                logger.info(f"重新添加 {len(listen_problem_chats)} 个聊天的监听")
                
                for chat in listen_problem_chats:
                    try:
                        logger.info(f"尝试重新添加监听: {chat}")
                        # 保存当前聊天以便后续恢复
                        current_chat = self._current_chat
                        
                        if self.ChatWith(chat):
                            if chat in self._last_messages:
                                del self._last_messages[chat]  # 清除旧消息缓存
                                
                            self.AddListenChat(chat, savepic=True, savefile=True)
                            logger.info(f"成功重新添加 {chat} 的监听")
                            
                            # 恢复之前的聊天（如果有）
                            if current_chat and current_chat != chat:
                                self.ChatWith(current_chat)
                        else:
                            logger.error(f"无法切换到聊天 {chat}")
                    except Exception as e:
                        logger.error(f"重新添加监听失败 {chat}: {str(e)}")
            else:
                logger.info("所有聊天监听状态正常，无需重新添加")
            
            # 重置重连计数和时间
            self._reconnect_attempts = 0
            self._last_reconnect_time = current_time
            logger.info("微信监听恢复正常")
            return True
            
        except Exception as e:
            logger.error(f"重连过程中发生错误: {str(e)}")
            self._last_reconnect_time = time.time()
            return False

    def needs_reconnect(self) -> bool:
        """
        检查是否需要重新连接
        
        Returns:
            bool: 是否需要重连
        """
        current_time = time.time()
        
        # 避免频繁检查，只有在_check_interval秒后才检查
        if current_time - self._last_reconnect_time < 60:  # 至少间隔1分钟
            return False
            
        # 只有在以下情况才需要重连：
        # 1. wx对象为None
        # 2. 长时间未检查 (超过_check_interval秒)
        # 3. 无法获取会话列表
        try:
            if not self.wx:
                return True
                
            # 长时间未检查才进行深度检查
            if current_time - self._last_window_check > self._check_interval:
                # 尝试获取会话列表，如果失败则需要重连
                session_list = self.wx.GetSessionList()
                if not session_list:
                    logger.warning("无法获取会话列表，可能需要重连")
                    return True
                    
                # 更新检查时间
                self._last_window_check = current_time
                return False
                
            # 正常情况下不需要重连
            return False
        except Exception as e:
            logger.error(f"检查连接状态时出错: {str(e)}")
            return True

    def InitAllListenings(self, chat_list):
        """
        一次性初始化所有需要监听的聊天
        
        Args:
            chat_list (list): 需要监听的聊天列表
            
        Returns:
            bool: 是否所有聊天都成功添加了监听
        """
        try:
            # 清除所有现有监听，确保只监听指定的列表
            current_listening = list(self._listen_chats)
            for old_chat in current_listening:
                if old_chat not in chat_list:
                    self.RemoveListenChat(old_chat)
                    logger.info(f"移除了不在监听列表中的聊天: {old_chat}")
            
            # 构建监听列表集合，用于快速查找
            chat_set = set(chat_list)
            
            success_count = 0
            for chat_name in chat_list:
                try:
                    # 检查会话是否存在
                    if not self.ChatWith(chat_name):
                        logger.error(f"找不到会话 {chat_name}")
                        continue
                    
                    # 添加到监听列表 - 确保这是一个有效的监听对象
                    if chat_name not in self._listen_chats:
                        # 尝试添加监听
                        self.AddListenChat(who=chat_name, savepic=True, savefile=True)
                        logger.info(f"成功添加监听: {chat_name}")
                        success_count += 1
                        time.sleep(0.5)  # 添加短暂延迟，避免操作过快
                    else:
                        logger.info(f"聊天 {chat_name} 已在监听列表中")
                        success_count += 1
                    
                except Exception as e:
                    logger.error(f"添加监听失败 {chat_name}: {str(e)}")
                    continue
            
            # 添加GetWeChatWindow方法，避免为不在监听列表中的用户创建新窗口
            if not hasattr(self, 'GetWeChatWindow'):
                def GetWeChatWindow(who: str) -> bool:
                    """
                    检查指定聊天是否应该被监听，防止监听不在列表中的用户
                    
                    Args:
                        who: 聊天对象名称
                        
                    Returns:
                        bool: 是否应该被监听
                    """
                    # 只有在监听列表中的聊天才会返回True
                    if who in chat_set or who in self._listen_chats:
                        # 存在于监听列表，尝试正常获取窗口
                        try:
                            return self._get_chat_window(who) is not None
                        except:
                            return False
                    else:
                        # 不在监听列表中，不获取窗口
                        logger.info(f"忽略不在监听列表中的聊天: {who}")
                        return False
                
                # 将方法添加到实例
                self.GetWeChatWindow = GetWeChatWindow
                logger.info("已添加防止监听非列表用户的保护方法")
            
            # 检查监听列表是否为空
            if not self._listen_chats:
                logger.warning("初始化后监听列表为空，可能存在问题")
                return False
                
            # 记录监听列表完整内容
            logger.info(f"当前监听的聊天列表: {list(self._listen_chats)}")
            
            # 如果所有聊天都成功添加了监听，返回True
            return success_count == len(chat_list)
            
        except Exception as e:
            logger.error(f"初始化所有监听失败: {str(e)}")
            return False 
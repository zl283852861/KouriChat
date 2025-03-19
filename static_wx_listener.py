#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
静态微信监听测试工具
初始化后不再切换窗口，避免干扰用户操作
"""

import os
import sys
import time
import logging
import threading
import pythoncom
import traceback
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("static_wx_listener.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 尝试导入wxauto前初始化COM
try:
    # 初始化COM环境
    logger.info("正在初始化COM环境...")
    pythoncom.CoInitialize()
    logger.info("COM环境初始化成功")
    
    # 然后导入wxauto
    import wxauto
    from wxauto import WeChat
    logger.info("成功导入wxauto模块")
except ImportError:
    logger.error("无法导入wxauto模块，请确保它已正确安装")
    print("错误: 无法导入wxauto模块，请确保它已正确安装")
    print("可以使用: pip install wxauto")
    pythoncom.CoUninitialize()  # 确保释放COM
    sys.exit(1)
except Exception as e:
    logger.error(f"初始化过程出错: {str(e)}")
    print(f"初始化错误: {str(e)}")
    try:
        pythoncom.CoUninitialize()  # 尝试释放COM
    except:
        pass
    sys.exit(1)

# 全局变量
stop_event = threading.Event()
wx_instance = None

class EnhancedWeChat(WeChat):
    """增强版WeChat类，添加静态监听功能"""
    
    def InitAllListenings(self, chat_names):
        """初始化所有监听，返回是否全部成功"""
        try:
            # 标记是否所有聊天都已添加
            all_chats_added = True
            
            # 添加每个聊天的监听
            for chat_name in chat_names:
                try:
                    if not self.ChatWith(chat_name):
                        logger.error(f"无法切换到聊天 '{chat_name}'")
                        all_chats_added = False
                        continue
                        
                    logger.info(f"成功切换到聊天 '{chat_name}'")
                    
                    # 添加监听
                    self.AddListenChat(who=chat_name, savepic=True, savefile=True)
                    logger.info(f"成功添加对 '{chat_name}' 的监听")
                    
                    # 短暂等待，避免微信响应不及时
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"添加监听失败 {chat_name}: {str(e)}")
                    all_chats_added = False
            
            # 如果有多个聊天，默认选择第一个作为主窗口
            if chat_names and all_chats_added:
                main_chat = chat_names[0]
                self.ChatWith(main_chat)
                logger.info(f"所有监听已初始化，选择 '{main_chat}' 作为主窗口")
                
            return all_chats_added
            
        except Exception as e:
            logger.error(f"初始化所有监听失败: {str(e)}")
            return False
    
    def GetListenMessageQuiet(self):
        """获取监听消息，安静模式，尽量减少窗口切换"""
        try:
            # 尝试直接获取消息而不切换窗口
            return self.GetListenMessage()
        except Exception as e:
            logger.error(f"安静获取消息失败: {str(e)}")
            return []

def create_wechat_instance():
    """创建微信实例并初始化COM环境"""
    try:
        # 每个线程都需要初始化COM
        pythoncom.CoInitialize()
        logger.info("线程COM环境初始化成功")
        
        # 创建微信实例
        wx = EnhancedWeChat()
        logger.info("成功创建WeChat实例")
        
        # 测试获取会话列表
        sessions = wx.GetSessionList()
        if sessions:
            logger.info(f"成功获取会话列表，找到 {len(sessions)} 个会话")
            logger.info(f"前5个会话: {sessions[:5] if len(sessions) > 5 else sessions}")
        else:
            logger.warning("获取到空的会话列表，请确保微信已登录")
            
        return wx
    except Exception as e:
        logger.error(f"创建微信实例失败: {str(e)}")
        return None

def static_listen(chat_names, duration=0):
    """
    静态监听模式，初始化后不再切换窗口
    
    Args:
        chat_names: 聊天名称列表
        duration: 监听持续时间(秒)，0表示一直监听直到用户中断
    """
    global wx_instance
    
    if wx_instance is None:
        logger.error("微信实例不存在，无法进行监听")
        return
    
    try:
        # 初始化所有监听
        success = wx_instance.InitAllListenings(chat_names)
        if not success:
            logger.warning("部分聊天未能成功添加监听，但将继续运行")
        
        # 主窗口默认选择第一个聊天
        main_chat = chat_names[0] if chat_names else None
        if not main_chat:
            logger.error("没有有效的聊天名称，无法继续")
            return
            
        logger.info(f"静态监听模式已启动，使用 '{main_chat}' 作为主窗口")
        
        # 初次确保窗口被激活
        wx_instance.ChatWith(main_chat)
        logger.info("窗口已激活，开始接收消息...")
        print(f"正在静态监听 {', '.join(chat_names)}")
        print("此模式下不会频繁切换窗口，减少对用户操作的干扰")
        print("按Ctrl+C可随时终止程序")
        
        # 设置时间相关变量
        message_count = 0
        start_time = time.time()
        check_interval = 1  # 每1秒检查一次
        window_check_interval = 300  # 每5分钟检查一次窗口
        last_window_check = time.time()
        
        # 主循环
        while not stop_event.is_set():
            # 检查是否达到指定时长
            if duration > 0 and time.time() - start_time > duration:
                logger.info(f"已达到指定监听时长 {duration} 秒，结束监听")
                break
                
            try:
                # 定期检查窗口状态，确保监听正常
                current_time = time.time()
                if current_time - last_window_check > window_check_interval:
                    logger.info(f"定期检查: 激活窗口 '{main_chat}'")
                    wx_instance.ChatWith(main_chat)
                    last_window_check = current_time
                
                # 获取消息
                msgs = wx_instance.GetListenMessageQuiet()
                
                if msgs:
                    message_count += len(msgs)
                    logger.info(f"收到 {len(msgs)} 条新消息 (总计: {message_count})")
                    
                    # 显示消息详情
                    for i, msg in enumerate(msgs):
                        try:
                            who = getattr(msg, 'who', '[未知聊天]')
                            sender = getattr(msg, 'sender', '[未知]')
                            content = getattr(msg, 'content', None) or getattr(msg, 'text', '[无内容]')
                            
                            # 记录消息详情
                            logger.info(f"消息 {i+1}: 来源={who}, 发送者={sender}, 内容={content[:100]}" + 
                                       ("..." if content and len(content) > 100 else ""))
                            
                            # 在控制台实时显示
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] {who} - {sender}: {content[:100]}" + 
                                  ("..." if content and len(content) > 100 else ""))
                        except Exception as e:
                            logger.error(f"解析消息失败: {str(e)}")
                
            except Exception as e:
                logger.error(f"监听过程出错: {str(e)}")
                
                # 如果遇到错误，尝试重新激活窗口
                try:
                    time.sleep(2)  # 等待一段时间
                    logger.info(f"尝试重新激活窗口 '{main_chat}'")
                    wx_instance.ChatWith(main_chat)
                    last_window_check = time.time()
                except Exception as e2:
                    logger.error(f"重新激活窗口失败: {str(e2)}")
            
            # 短暂等待，减少CPU占用
            time.sleep(check_interval)
        
        # 监听结束
        if message_count > 0:
            logger.info(f"监听结束！共收到 {message_count} 条消息")
            print(f"监听结束！共收到 {message_count} 条消息")
        else:
            logger.warning("未收到任何消息，可能是微信监听功能未正常工作或没有消息发送")
            print("未收到任何消息，请查看日志了解详情")
            
    except Exception as e:
        logger.error(f"静态监听出错: {str(e)}\n{traceback.format_exc()}")

def cleanup():
    """清理资源"""
    try:
        pythoncom.CoUninitialize()
        logger.info("COM环境已释放")
    except:
        pass

def main():
    """主函数"""
    global wx_instance
    
    print("=" * 50)
    print(" 静态微信监听测试工具 ")
    print("=" * 50)
    print("\n此工具将使用静态监听模式，初始化后不再切换窗口")
    print("这样可以避免干扰用户在电脑上的正常操作")
    print("请确保微信已登录并显示在屏幕上\n")
    
    try:
        # 创建微信实例
        wx_instance = create_wechat_instance()
        if not wx_instance:
            print("无法创建微信实例，测试终止")
            return 1
        
        # 获取聊天名称
        print("\n请输入要监听的聊天名称(多个聊天用逗号分隔):")
        chat_input = input("> ").strip()
        
        chat_names = [name.strip() for name in chat_input.split(',') if name.strip()]
        if not chat_names:
            print("未提供聊天名称，测试终止")
            return 1
        
        # 获取监听时长
        print("\n请输入监听时长(秒)，0表示一直监听直到手动中断:")
        try:
            duration = int(input("> ").strip() or "0")
        except:
            duration = 0
            print("输入无效，将一直监听直到手动中断")
            
        # 开始静态监听
        static_listen(chat_names, duration)
        
        print("\n监听结束，详情请查看 static_wx_listener.log 文件")
        
    except KeyboardInterrupt:
        print("\n用户中断监听")
    except Exception as e:
        logger.error(f"程序出错: {str(e)}\n{traceback.format_exc()}")
        print(f"程序出错: {str(e)}")
        return 1
    finally:
        # 清理资源
        stop_event.set()
        cleanup()
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
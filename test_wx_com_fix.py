import os
import sys
import time
import logging
import pythoncom
from typing import List, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('wx_test.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

try:
    import wxauto
    from wxauto import WeChat as WxAutoWeChat
except ImportError:
    logger.error("无法导入wxauto模块，请确保已安装: pip install wxauto")
    sys.exit(1)

class WeChat:
    def __init__(self):
        """初始化WeChat实例"""
        self.wx = None
        try:
            self.wx = WxAutoWeChat()
            if not self.wx:
                raise Exception("无法创建WeChat实例")
            logger.info("WeChat实例创建成功")
        except Exception as e:
            logger.error(f"初始化WeChat失败: {str(e)}")
            raise

    def ChatWith(self, who: str) -> bool:
        """切换到指定聊天窗口"""
        try:
            return bool(self.wx.ChatWith(who))
        except Exception as e:
            logger.error(f"切换到聊天 {who} 失败: {str(e)}")
            return False

    def GetSessionList(self) -> List[str]:
        """获取会话列表"""
        try:
            return self.wx.GetSessionList()
        except Exception as e:
            logger.error(f"获取会话列表失败: {str(e)}")
            return []

    def AddListenChat(self, who: str, savepic: bool = True, savefile: bool = True) -> bool:
        """添加聊天监听"""
        try:
            self.wx.AddListenChat(who=who, savepic=savepic, savefile=savefile)
            return True
        except Exception as e:
            logger.error(f"添加监听失败 {who}: {str(e)}")
            return False

    def GetListenMessageQuiet(self) -> List[Any]:
        """静默获取监听消息"""
        try:
            # 尝试直接获取所有消息
            msgs = self.wx.GetAllMessage()
            if msgs:
                logger.info(f"静默模式成功获取到 {len(msgs)} 条消息")
                return msgs
                
            # 如果GetAllMessage失败，尝试GetMsgs
            msgs = self.wx.GetMsgs()
            if msgs:
                logger.info(f"静默模式(GetMsgs)获取到 {len(msgs)} 条消息")
                return msgs
                
            # 如果GetMsgs也失败，尝试GetLastMessage
            msg = self.wx.GetLastMessage()
            if msg:
                logger.info("静默模式获取到最后一条消息")
                return [msg]
                
            return []
            
        except Exception as e:
            logger.warning(f"静默获取消息失败: {str(e)}")
            return []

    def GetListenMessage(self) -> List[Any]:
        """获取监听消息"""
        try:
            # 首先尝试静默获取消息
            msgs = self.GetListenMessageQuiet()
            if msgs:
                return msgs
                
            # 如果静默获取失败，尝试常规方法
            msgs = self.wx.GetAllMessage()
            if msgs:
                return msgs
                
            # 如果还是失败，尝试其他方法
            msgs = self.wx.GetMsgs()
            if msgs:
                return msgs
                
            # 最后尝试获取最后一条消息
            msg = self.wx.GetLastMessage()
            if msg:
                return [msg]
                
            return []
            
        except Exception as e:
            logger.error(f"获取监听消息失败: {str(e)}")
            return []

def test_chat_monitoring(chat_name: str, duration: int = 300):
    """
    测试聊天监听功能
    
    Args:
        chat_name: 要监听的聊天名称
        duration: 监听持续时间（秒），默认5分钟
    """
    try:
        # 初始化COM环境
        pythoncom.CoInitialize()
        logger.info("COM环境初始化成功")
        
        # 创建WeChat实例
        wx = WeChat()
        
        # 检查会话列表
        sessions = wx.GetSessionList()
        if not sessions:
            logger.error("未检测到任何会话")
            return
        logger.info(f"检测到 {len(sessions)} 个会话")
        
        # 检查目标聊天是否存在
        if chat_name not in sessions:
            logger.error(f"找不到聊天: {chat_name}")
            return
        
        # 切换到目标聊天并添加监听
        if not wx.ChatWith(chat_name):
            logger.error(f"无法切换到聊天: {chat_name}")
            return
        
        if not wx.AddListenChat(chat_name):
            logger.error(f"无法添加监听: {chat_name}")
            return
        
        logger.info(f"成功添加监听: {chat_name}")
        logger.info("进入静态监听模式...")
        
        # 记录开始时间
        start_time = time.time()
        msg_count = 0
        
        # 监听消息
        while time.time() - start_time < duration:
            try:
                # 使用静默模式获取消息
                msgs = wx.GetListenMessageQuiet()
                
                if msgs:
                    msg_count += len(msgs)
                    for msg in msgs:
                        who = getattr(msg, 'who', None)
                        sender = getattr(msg, 'sender', None)
                        content = getattr(msg, 'content', None) or getattr(msg, 'text', None)
                        msgtype = getattr(msg, 'type', 'unknown')
                        
                        logger.info(f"收到消息 - 来源: {who}, 发送者: {sender}, 类型: {msgtype}")
                        logger.info(f"消息内容: {content[:100]}" + ("..." if content and len(content) > 100 else ""))
                
                # 每5分钟检查一次窗口状态
                elapsed = time.time() - start_time
                if elapsed % 300 < 1:  # 接近5分钟的整数倍时
                    logger.info(f"定期检查: 重新激活窗口 '{chat_name}'")
                    wx.ChatWith(chat_name)
                
                time.sleep(1)  # 避免过于频繁的检查
                
            except Exception as e:
                logger.error(f"监听过程出错: {str(e)}")
                time.sleep(5)  # 出错后等待一段时间再继续
        
        logger.info(f"监听结束，共收到 {msg_count} 条消息")
        
    except Exception as e:
        logger.error(f"测试过程出错: {str(e)}")
    finally:
        try:
            pythoncom.CoUninitialize()
            logger.info("COM环境已释放")
        except:
            pass

def main():
    """主函数"""
    try:
        # 获取用户输入
        chat_name = input("请输入要监听的聊天名称: ").strip()
        if not chat_name:
            logger.error("聊天名称不能为空")
            return
            
        duration = input("请输入监听时间（秒，默认300）: ").strip()
        try:
            duration = int(duration) if duration else 300
        except ValueError:
            logger.error("无效的时间输入，使用默认值300秒")
            duration = 300
            
        # 开始测试
        logger.info(f"开始测试 - 聊天: {chat_name}, 持续时间: {duration}秒")
        test_chat_monitoring(chat_name, duration)
        
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")
    finally:
        input("按回车键退出...")

if __name__ == "__main__":
    main() 
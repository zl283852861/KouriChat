import win32gui
import win32con
import win32api
import time


def click_wechat_buttons():
    # 获取微信登录窗口
    hwnd = win32gui.FindWindow(None, "微信")
    if hwnd == 0:
        print("找不到微信登录窗口")
        return
    
    # 获取窗口位置和大小
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top
    # 激活窗口
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.1)
    
    # 点击"确定"按钮（位置需要根据实际调整）
    confirm_x = width // 2
    confirm_y = height // 2+20
    win32api.SetCursorPos((left + confirm_x, top + confirm_y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    
    time.sleep(0.5)  # 等待确定按钮响应
    
    # 点击"登录"按钮
    login_x = width // 2
    login_y = height - 90
    win32api.SetCursorPos((left + login_x, top + login_y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

if __name__ == "__main__":
    click_wechat_buttons()
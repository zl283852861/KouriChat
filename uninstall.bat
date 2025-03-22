@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 设置标题
title KouriChat 卸载程序

:: 获取脚本所在目录
cd /d "%~dp0"

:: 获取脚本所在目录
cd /d "%~dp0"

:: 检查管理员权限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 请以管理员权限运行此脚本！
    echo 按任意键退出...
    pause >nul
    exit /b 1
)

:: 检查Python环境
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo Python未安装或未添加到环境变量！
    echo 请确保已正确安装Python并添加到环境变量。
    echo 按任意键退出...
    pause >nul
    exit /b 1
)

:: 显示欢迎信息
echo ====================================
echo        KouriChat 卸载程序
echo ====================================
echo.

:: 结束所有KouriChat相关进程
echo [处理] 正在结束KouriChat相关进程...
taskkill /f /im "kourichat*.exe" >nul 2>&1
taskkill /f /im "python.exe" /fi "WINDOWTITLE eq KouriChat*" >nul 2>&1

:: 询问是否完全删除KouriChat
echo 警告：这将删除整个KouriChat目录及其所有文件！
set /p DELETE_ALL="是否完全删除KouriChat？(Y/N): "
if /i "%DELETE_ALL%"=="Y" (
    echo [处理] 正在删除整个KouriChat目录...
    cd ..
    rmdir /s /q "%~dp0"
) else (
    :: 询问是否保留用户数据
    set /p KEEP_DATA="是否保留用户数据？(Y/N): "
    if /i "%KEEP_DATA%"=="Y" (
        python run.py --uninstall --keep-data
    ) else (
        python run.py --uninstall
    )
)

:: 删除虚拟环境
if exist .venv (
    echo [处理] 正在删除虚拟环境...
    rmdir /s /q .venv
)

:: 删除快捷方式
echo [处理] 正在删除快捷方式...
del /f /q "%USERPROFILE%\Desktop\KouriChat.lnk" 2>nul
del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\KouriChat.lnk" 2>nul

:: 清理注册表
echo [处理] 正在清理注册表...
reg delete "HKCU\Software\KouriChat" /f >nul 2>&1
reg delete "HKLM\Software\KouriChat" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\KouriChat" /f >nul 2>&1

:: 清理环境变量
echo [处理] 正在清理环境变量...
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path ^| findstr /i "path"') do (
    set "USER_PATH=%%b"
)
setx PATH "%USER_PATH:KouriChat;=%" >nul 2>&1

echo.
echo [完成] 卸载完成！
echo 按任意键退出...
pause >nul
exit /b 0
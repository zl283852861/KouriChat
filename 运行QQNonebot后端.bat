@echo off
setlocal enabledelayedexpansion

:: 设置代码页为 GBK
chcp 936 >nul
title My Dream Moments 启动器

cls
echo ====================================
echo        My Dream Moments 启动器
echo ====================================
echo.
echo ╔══════════════════════════════════╗
echo ║      My Dream Moments - AI Chat   ║
echo ║      Created with Heart by umaru  ║
echo ╚══════════════════════════════════╝
echo.

:: 设置临时python环境
set "python_home=%cd%\Python310"
if not exist "!python_home!" (
    rem 解压Python文件
    echo 安装python环境，请在弹出的窗口中点击开始
    start /wait Python310.exe
    echo Done
    rem 构建PIP
    Python310\python -m ensurepip
    copy Python310\Scripts\pip3.10.exe Python310\Scripts\pip.exe
)
rem 构建临时环境变量
set "path=!python_home!;!python_home!\Scripts;!path!"
echo 当前PATH: "!path!"
rem 构建完成
python --version
if errorlevel 1 (
    echo Python临时环境安装错误
    pause
    exit /b 1
)

:: 设置虚拟环境目录
set VENV_DIR=.venv

:: 检查虚拟环境是否存在
if not exist %VENV_DIR% (
    echo 正在创建虚拟环境...
    python -m venv %VENV_DIR%
    if errorlevel 1 (
        echo 创建虚拟环境失败
        pause
        exit /b 1
    )
)

:: 激活虚拟环境
call %VENV_DIR%\Scripts\activate.bat

:: 安装依赖
if exist requirements.txt (
    echo 正在安装依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 安装依赖失败
        pause
        exit /b 1
    )
)

:: 运行程序
echo 正在启动程序...
python oneBotMain.py

:: 如果发生异常退出则暂停显示错误信息
if errorlevel 1 (
    echo 程序运行出错
    pause
)

:: 退出虚拟环境
deactivate
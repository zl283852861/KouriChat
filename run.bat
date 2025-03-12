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

:: 检查是否存在 Python310 环境标记文件
set "python_installed_flag=%USERPROFILE%\.python310_installed"
set "python_home="

:: 首先检查当前目录
if exist "Python310" (
    set "python_home=%cd%\Python310"
    goto :python_found
)

:: 检查已知的 Python310 标记文件
if exist "%python_installed_flag%" (
    set /p python_home=<"%python_installed_flag%"
    if exist "!python_home!" goto :python_found
)

:: 如果没有找到 Python310，则安装
echo 未找到 Python310 环境，开始安装...
start /wait Python310.exe
set "python_home=%cd%\Python310"
echo !python_home!>"%python_installed_flag%"

:python_found
echo 使用 Python 环境: !python_home!

:: 构建临时环境变量
set "path=!python_home!;!python_home!\Scripts;!path!"

:: 验证 Python 安装
python --version >nul 2>&1
if errorlevel 1 (
    echo Python环境异常，请检查安装
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
python run_config_web.py

:: 如果发生异常退出则暂停显示错误信息
if errorlevel 1 (
    echo 程序运行出错
    pause
)

:: 退出虚拟环境
deactivate
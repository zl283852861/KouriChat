@echo off
setlocal enabledelayedexpansion

:: 检查 Python 是否已安装
python --version >nul 2>&1
if errorlevel 1 (
    echo Python未安装，请先安装Python
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

:: 如果程序异常退出，暂停显示错误信息
if errorlevel 1 (
    echo 程序运行出错
    pause
)

:: 退出虚拟环境
deactivate

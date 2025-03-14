@echo off
setlocal enabledelayedexpansion

:: 设置控制台编码为 GBK
chcp 936 >nul
title My Dream Moments 启动器

cls
echo ====================================
echo        My Dream Moments 启动器
echo ====================================
echo.
echo ╔═══════════════════════════════════╗
echo ║      My Dream Moments - AI Chat   ║
echo ║      Created with Heart by umaru  ║
echo ╚═══════════════════════════════════╝
echo.

:: 检查 Python 是否已安装
python --version >nul 2>&1
if errorlevel 1 (
    echo Python未安装，请先安装Python
    pause
    exit /b 1
)

:: 检查 Python 版本
for /f "tokens=2" %%I in ('python -V 2^>^&1') do set PYTHON_VERSION=%%I
for /f "tokens=2 delims=." %%I in ("!PYTHON_VERSION!") do set MINOR_VERSION=%%I
if !MINOR_VERSION! GEQ 13 (
    echo 不支持 Python 3.13 及以上版本
    echo 当前Python版本: !PYTHON_VERSION!
    echo 请使用 Python 3.12 或更早版本
    pause
    exit /b 1
)

:: 设置虚拟环境目录
set VENV_DIR=.venv

:: 创建虚拟环境（如果不存在）
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

:: 安装依赖（三重镜像源机制）
if exist requirements.txt (
    echo 正在使用清华镜像源安装依赖...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    
    :: 如果清华源失败，尝试阿里云镜像
    if errorlevel 1 (
        echo ═══════════════════════════════
        echo 正在尝试阿里云镜像源安装...
        pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
        
        :: 如果阿里云失败，尝试腾讯云镜像
        if errorlevel 1 (
            echo ═══════════════════════════════
            echo 正在尝试腾讯云镜像源安装...
            pip install -r requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple
            
            :: 最终失败处理
            if errorlevel 1 (
                echo ═══════════════════════════════
                echo 所有镜像源尝试失败，请检查：
                echo 1. 网络连接是否正常
                echo 2. 手动安装命令：pip install -r requirements.txt
                echo 3. 是否存在特殊依赖包
                echo 4. 尝试临时关闭防火墙/代理
                pause
                exit /b 1
            )
        )
    )
)

:: 运行程序
echo 正在启动程序...
python run_config_web.py

:: 异常退出处理
if errorlevel 1 (
    echo 程序异常退出
    pause
)

:: 退出虚拟环境
deactivate

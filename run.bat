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
set "python_home=%~dp0Python310"

:: 如果没有找到 Python310，则安装
if not exist "%python_home%\python.exe" (
    echo 未找到 Python 3.10 环境，开始安装...
    if exist "Python310.exe" (
        echo 正在安装 Python 3.10...
        start /wait Python310.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 TargetDir="%python_home%"
        echo !python_home!>"%python_installed_flag%"
    ) else (
        echo 错误：未找到 Python310.exe 安装程序
        pause
        exit /b 1
    )
)

:python_found
echo 使用 Python 环境: !python_home!

:: 设置 Python 环境变量
set "PYTHON_HOME=!python_home!"
set "PYTHONPATH=!python_home!\Lib;!python_home!\DLLs;!python_home!\Lib\site-packages"
set "PATH=!python_home!;!python_home!\Scripts;%PATH%"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

:: 修复/重新安装 pip
echo 正在修复 pip 安装...
powershell -Command "(New-Object Net.WebClient).DownloadFile('https://mirrors.aliyun.com/pypi/get-pip.py', 'get-pip.py')"
"!python_home!\python.exe" get-pip.py --force-reinstall --no-warn-script-location
del /f /q get-pip.py

:: 配置 pip 使用清华源
if not exist "%APPDATA%\pip" mkdir "%APPDATA%\pip"
(
echo [global]
echo index-url = https://pypi.tuna.tsinghua.edu.cn/simple
echo [install]
echo trusted-host = mirrors.aliyun.com
) > "%APPDATA%\pip\pip.ini"

:: 清理并重建 Python 环境
echo 正在清理 Python 环境...
if exist "!python_home!\Lib\site-packages" rd /s /q "!python_home!\Lib\site-packages"
if exist "!python_home!\Scripts" rd /s /q "!python_home!\Scripts"

:: 清理 Python 缓存文件
if exist "%~dp0*.pyc" del /f /q "%~dp0*.pyc"
if exist "%~dp0__pycache__" rd /s /q "%~dp0__pycache__"

:: 验证 Python 安装（使用完整路径）
"!python_home!\python.exe" --version >nul 2>&1
if errorlevel 1 (
    echo Python环境异常，请检查安装
    echo 当前 Python 路径: !python_home!
    echo 尝试运行: "!python_home!\python.exe" --version
    pause
    exit /b 1
)

:: 确保 PATH 中包含 Python 和 pip
set "PATH=!python_home!;!python_home!\Scripts;%PATH%"

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
set VENV_DIR=%python_home%\.venv

:: 检查虚拟环境是否存在
if not exist %VENV_DIR% (
    echo 正在创建虚拟环境...
    python -m venv %VENV_DIR%
    if errorlevel 1 (
        echo 创建虚拟环境失败
        pause
        exit /b 1
    )
    set "FRESH_ENV=1"
)

:: 激活虚拟环境
call %VENV_DIR%\Scripts\activate.bat

:: 确保 pip 已安装
echo 正在检查 pip...
python -m ensurepip --upgrade
if errorlevel 1 (
    echo pip 安装失败
    pause
    exit /b 1
)

:: 检查依赖是否需要更新
set "NEEDS_UPDATE=0"
if exist requirements.txt (
    if not exist "%req_hash_file%" set "NEEDS_UPDATE=1"
    if exist "%req_hash_file%" (
        for /f "usebackq" %%a in (`certutil -hashfile requirements.txt SHA256 ^| find /v "hash"`) do (
            set "current_hash=%%a"
        )
        set /p stored_hash=<"%req_hash_file%"
        if not "!current_hash!"=="!stored_hash!" set "NEEDS_UPDATE=1"
    )
    
    if "!NEEDS_UPDATE!"=="1" (
        echo 正在安装/更新依赖...
        python -m pip install --upgrade pip
        python -m pip install --no-cache-dir -r requirements.txt
        if errorlevel 1 (
            echo 安装依赖失败
            pause
            exit /b 1
        )
        echo !current_hash!>"%req_hash_file%"
    ) else (
        echo 依赖已是最新版本，跳过安装...
    )
)

:: 运行程序
echo 正在启动程序...
cd /d "%~dp0"
python run_config_web.py

:: 如果发生异常退出则暂停显示错误信息
if errorlevel 1 (
    echo 程序运行出错
    pause
)

:: 退出虚拟环境
deactivate
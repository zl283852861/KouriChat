@echo off
setlocal enabledelayedexpansion

:: 设置代码页为 UTF-8
chcp 65001 >nul
title My Dream Moments 启动器

cls
echo ====================================
echo       My Dream Moments 启动器
echo ====================================
echo.
echo +--------------------------------+
echo ^|   My Dream Moments - AI Chat   ^|
echo ^|   Created with Heart by umaru  ^|
echo +--------------------------------+
echo.

:: 设置 Python 环境变量
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

:: 确保 pip 已安装
echo cheking pip ...
python -m ensurepip --upgrade >nul 2>&1
if errorlevel 1 (
    echo pip 安装失败喵
    pause
    exit /b 1
)

:: 检查依赖是否需要更新
@echo off
setlocal enabledelayedexpansion

:: 设置代码页为 UTF-8
chcp 65001 >nul
title My Dream Moments 启动器

:: ... 前面的代码保持不变 ...

:: 检查依赖是否需要更新
set "NEEDS_UPDATE=0"
set "req_hash_file=%TEMP%\requirements_hash.txt"
if exist requirements.txt (
    if not exist "%req_hash_file%" set "NEEDS_UPDATE=1"
    if exist "%req_hash_file%" (
        for /f "usebackq" %%a in (`certutil -hashfile requirements.txt SHA256 ^| find /v "hash"`) do (
            set "current_hash=%%a"
        )
        set /p stored_hash=<"%req_hash_file%" 2>nul
        if not "!current_hash!"=="!stored_hash!" set "NEEDS_UPDATE=1"
    )
    
    if "!NEEDS_UPDATE!"=="1" (
        echo 正在安装/更新依赖喵...
        python -m pip install --upgrade pip >nul 2>&1

        :: 定义镜像源列表
        set "mirrors[0]=https://pypi.tuna.tsinghua.edu.cn/simple"
        set "mirrors[1]=https://mirrors.aliyun.com/pypi/simple/"
        set "mirrors[2]=https://pypi.mirrors.ustc.edu.cn/simple/"
        set "mirrors[3]=https://mirrors.cloud.tencent.com/pypi/simple"
        set "mirrors[4]=https://pypi.org/simple"

        set success=0
        set mirror_count=5

        :: 尝试每个镜像源
        for /L %%i in (0,1,4) do (
            if !success!==0 (
                echo 尝试使用镜像源: !mirrors[%%i]!
                python -m pip install --no-cache-dir -i !mirrors[%%i]! -r requirements.txt
                if !errorlevel!==0 (
                    set success=1
                    echo 依赖安装成功喵~
                    echo !current_hash!>"%req_hash_file%"
                ) else (
                    echo 当前镜像源安装失败，尝试下一个...
                )
            )
        )

        :: 检查是否所有镜像源都失败
        if !success!==0 (
            echo 所有镜像源都安装失败了喵...
            echo 请检查网络连接或手动安装依赖喵
            pause
            exit /b 1
        )
    ) else (
        echo 依赖已是最新版本，跳过安装喵...
    )
)


:: 运行程序
echo 正在启动程序喵...
cd /d "%~dp0"
python run_config_web.py

:: 如果发生异常退出则暂停显示错误信息
if errorlevel 1 (
    echo 程序运行出错喵
    pause
)
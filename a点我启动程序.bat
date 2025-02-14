@echo off
chcp 936
title My Dream Moments 启动器

cls
echo ====================================
echo        My Dream Moments 启动器
echo ====================================
echo.
echo ╔══════════════════════════════════════════════╗
echo ║          My Dream Moments - AI Chat          ║
echo ║            Created with Heart by umaru       ║
echo ╚══════════════════════════════════════════════╝
echo.

REM 创建桌面快捷方式
set "SCRIPT_PATH=%~f0"
set "DESKTOP_PATH=%USERPROFILE%\Desktop"
set "SHORTCUT_PATH=%DESKTOP_PATH%\My Dream Moments.lnk"

dir "%SHORTCUT_PATH%" >nul 2>nul
if errorlevel 1 (
    choice /c yn /m "是否要在桌面创建快捷方式"
    if errorlevel 2 goto SKIP_SHORTCUT
    if errorlevel 1 (
        echo 正在创建桌面快捷方式...
        powershell "$WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut('%SHORTCUT_PATH%'); $SC.TargetPath = '%SCRIPT_PATH%'; $SC.WorkingDirectory = '%~dp0'; $SC.Save()"
        echo 快捷方式创建完成！
        echo.
    )
)
:SKIP_SHORTCUT

where python >nul 2>nul
if errorlevel 1 (
    echo 错误：系统中未找到Python！
    echo 请确保已安装Python并添加到系统环境变量中。
    pause
    exit
)

echo 正在检查必要的Python模块...
python -c "import pyautogui" 2>nul
if errorlevel 1 (
    echo 正在安装 pyautogui 模块...
    pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host mirrors.aliyun.com pyautogui -i http://mirrors.aliyun.com/pypi/simple/
)

python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo 正在安装 streamlit 模块...
    pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host mirrors.aliyun.com streamlit -i http://mirrors.aliyun.com/pypi/simple/
)

python -c "import sqlalchemy" 2>nul
if errorlevel 1 (
    echo 正在安装 sqlalchemy 模块...
    pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host mirrors.aliyun.com sqlalchemy -i http://mirrors.aliyun.com/pypi/simple/
)

echo 模块检查完成！
echo.

echo 正在启动配置界面...
start http://localhost:8501/
start /b python run_config_web.py
if errorlevel 1 (
    echo 配置界面启动失败！
    echo 请确保run_config_web.py文件存在。
    pause
    exit
)

echo 正在等待配置界面启动...
timeout /t 5 /nobreak >nul

:check_config
echo.
echo 是否已完成配置修改？(Y/N)
set /p CONFIG_DONE=": "
if /i "%CONFIG_DONE%"=="Y" (
    taskkill /f /im python.exe >nul 2>nul
    echo.
    echo 配置完成，正在启动机器人...
    python run.py
    if errorlevel 1 (
        echo 机器人启动失败！
        echo 请确保run.py文件存在。
        pause
        exit
    )
) else if /i "%CONFIG_DONE%"=="N" (
    goto check_config
) else (
    echo 无效的输入，请输入 Y 或 N
    goto check_config
)

pause
:: 运行程序
echo 正在启动机器人喵...
cd /d "%~dp0"
python run_config_web.py

:: 如果发生异常退出则暂停显示错误信息
if errorlevel 1 (
    echo 程序运行出错喵
    pause
)
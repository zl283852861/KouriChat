@echo off
echo ========================================
echo  guyuejj
echo 启动脚本
echo ========================================
echo.

chcp 65001 > nul
cd /d "%~dp0"

echo ========================================
echo 微信机器人自动配置和启动程序
echo ========================================

REM 获取当前脚本所在的目录（含尾部反斜杠），确保路径不会写死
set "BASE_DIR=%~dp0"
echo [信息] 当前工作目录: %BASE_DIR%
echo.

REM 检查Python是否安装
echo [步骤 1/6] 检查Python环境...
python --version > nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python！
    echo [提示] 请安装Python 3.8或更高版本
    pause
    exit /b 1
)

REM 检查pip版本
echo [信息] 检查pip版本...
for /f "tokens=2" %%I in ('pip --version') do set PIP_VERSION=%%I
echo [信息] 当前pip版本: %PIP_VERSION%
pip list --outdated | find "pip" > nul
if not errorlevel 1 (
    echo [警告] 发现pip有新版本可用
    echo [提示] 建议运行以下命令升级pip:
    echo        python -m pip install --upgrade pip
)

REM 检查长路径支持
echo [信息] 检查长路径支持...
reg query "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v "LongPathsEnabled" | find "0x1" > nul
if errorlevel 1 (
    echo [警告] Windows长路径支持未启用
    echo [提示] 建议启用长路径支持，可以：
    echo        1. 以管理员身份运行PowerShell
    echo        2. 执行: Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1
    echo        3. 重启计算机
)

echo [步骤 1/5] 检查必要文件...
set "MISSING_FILES="
set "CHECK_FILES=database.py bot.py config.py"

echo [检查] 检查程序文件...
for %%F in (%CHECK_FILES%) do (
    if not exist "%BASE_DIR%%%F" (
        echo [错误] 未找到 %%F 文件！
        set "MISSING_FILES=1"
    ) else (
        echo [成功] 找到 %%F 文件
    )
)

if defined MISSING_FILES (
    echo.
    echo [错误] 缺少必要文件！
    echo [提示] 请确保以下文件都在当前目录下：
    echo        - database.py  （数据库模型定义）
    echo        - config.py    （配置文件）
    echo        - bot.py       （主程序）
    pause
    exit /b 1
)

echo [检查] 检查必要目录和文件...
if not exist "%BASE_DIR%prompts" (
    echo [信息] 创建 prompts 目录...
    mkdir "%BASE_DIR%prompts"
)

echo [检查] 检查markdown文件...
if not exist "%BASE_DIR%prompts\ATRI.md" (
    echo [信息] 创建 ATRI.md 文件...
    echo # ATRI > "%BASE_DIR%prompts\ATRI.md"
    echo [成功] ATRI.md 创建完成
)

if not exist "%BASE_DIR%SponsorList.md" (
    echo [信息] 创建 SponsorList.md 文件...
    echo # Sponsor List > "%BASE_DIR%SponsorList.md"
    echo [成功] SponsorList.md 创建完成
)

echo [成功] 所有必要文件检查完成！
echo.

echo [步骤 2/5] 检查微信...
echo [提示] 请确保：
echo        1. 微信已经正常登录
echo        2. 微信窗口处于打开状态
echo        3. 联系人列表已完全加载
echo.
echo [注意] 常见问题：
echo        - 如果出现"Find Control Timeout"，说明找不到微信窗口或联系人
echo        - 如果出现"LookupError"，说明无法找到指定的联系人
echo        - 如果出现"FileNotFoundError"，说明缺少必要的配置或资源文件
echo.
echo 按任意键继续...
pause > nul

echo [步骤 3/5] 检查虚拟环境...
if not exist "%BASE_DIR%venv\Scripts\activate.bat" (
    echo [操作] 未检测到虚拟环境，正在创建...
    python -m venv venv
    if errorlevel 1 (
         echo [错误] 虚拟环境创建失败！
         echo [错误] 请检查Python是否正确安装并配置到环境变量中！
         echo [提示] 解决方法：
         echo        1. 确保已安装Python 3.8或更高版本
         echo        2. 检查系统环境变量中是否包含Python路径
         echo        3. 尝试重新安装Python
         pause
         exit /b 1
    )
    echo [成功] 虚拟环境创建完成！
) else (
    echo [信息] 检测到已存在的虚拟环境，跳过创建步骤...
)
echo.

echo [步骤 4/6] 激活虚拟环境并安装依赖...
call "%BASE_DIR%venv\Scripts\activate.bat"
echo [成功] 虚拟环境已激活！

echo [信息] 正在通过阿里云镜像源安装依赖...
REM 设置临时pip配置以允许长路径
set PIP_MAX_PATH_LENGTH=260

REM 添加错误处理的pip安装命令
echo [安装] 正在安装基础依赖...
(pip install sqlalchemy -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com) || (
    echo [错误] 安装失败！可能原因：
    echo        1. 路径过长导致安装失败
    echo        2. 网络连接问题
    echo [建议] 尝试以下解决方案：
    echo        1. 将项目移动到更短的路径下
    echo        2. 启用Windows长路径支持
    echo        3. 检查网络连接
    pause
    exit /b 1
)

pip install wxauto -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
pip install openai -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
pip install requests -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
pip install python-dateutil -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
pip install typing -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
pip install regex -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

echo [安装] SQLAlchemy相关依赖...
pip install sqlalchemy-utils -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
pip install alembic -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

REM 恢复默认pip配置
set PIP_MAX_PATH_LENGTH=

echo [信息] 检查依赖安装状态...
python -c "import datetime, sqlalchemy, sqlalchemy.ext.declarative, sqlalchemy.orm, wxauto, openai, requests, typing, re" 2>nul
if errorlevel 1 (
    echo [错误] 部分依赖安装失败！
    echo [提示] 可能的原因：
    echo        1. 网络连接不稳定
    echo        2. 镜像源暂时不可用
    echo        3. Python版本不兼容
    echo [建议] 解决方法：
    echo        1. 检查网络连接
    echo        2. 尝试重新运行此脚本
    echo        3. 手动执行pip安装命令
    pause
    exit /b 1
)

REM 创建数据库目录（如果不存在）
if not exist "%BASE_DIR%data" (
    echo [信息] 创建数据目录...
    mkdir "%BASE_DIR%data"
)

echo [成功] 所有依赖包安装完成！
echo.

echo [步骤 5/5] 启动程序...
echo [信息] 正在启动 bot.py
echo [提示] 常见错误及解决方法：
echo        1. "Find Control Timeout"：
echo           - 确保微信窗口已打开且正常显示
echo           - 确保联系人列表已完全加载
echo           - 检查要查找的联系人是否存在
echo        2. "ModuleNotFoundError"：
echo           - 检查是否有遗漏的依赖包
echo           - 尝试重新运行此脚本
echo        3. "FileNotFoundError"：
echo           - 检查配置文件和资源文件是否存在
echo           - 确保文件路径正确
echo ========================================
"%BASE_DIR%venv\Scripts\python.exe" bot.py
echo ========================================
if errorlevel 1 (
    echo [错误] 程序异常退出！
    echo [提示] 请查看上方错误信息，常见问题：
    echo        1. 配置文件错误或缺失
    echo        2. 微信窗口未正确打开
    echo        3. 依赖包安装不完整
    echo        4. 权限不足
    echo [建议] 如果问题持续：
    echo        1. 检查所有配置文件
    echo        2. 重新启动微信和程序
    echo        3. 以管理员身份运行
)

echo.
echo ========================================
echo guyuejj
echo ========================================
pause
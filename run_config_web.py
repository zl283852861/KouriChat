"""
配置管理Web界面启动文件
提供Web配置界面功能，包括:
- 初始化Python路径
- 禁用字节码缓存
- 清理缓存文件
- 启动Web服务器
- 动态修改配置
"""
import os
import sys
import re
import logging
from flask import Flask, render_template, jsonify, request, send_from_directory, redirect, url_for, session
import importlib
import json
from colorama import init, Fore, Style
from werkzeug.utils import secure_filename
from typing import Dict, Any, List
import psutil
import subprocess
import threading
from src.autoupdate.updater import Updater
import requests
import time
from queue import Queue
import datetime
from logging.config import dictConfig
import shutil
import signal
import atexit
import socket
import webbrowser
import hashlib
import secrets
from datetime import timedelta

# 在文件开头添加全局变量声明
bot_process = None
bot_start_time = None
bot_logs = Queue(maxsize=1000)

# 配置日志
dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'level': 'DEBUG'
        }
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['console']
    },
    'loggers': {
        'werkzeug': {
            'level': 'ERROR',  # 将 Werkzeug 的日志级别设置为 ERROR
            'handlers': ['console'],
            'propagate': False
        }
    }
})

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 初始化colorama
init()

# 添加项目根目录到Python路径
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT_DIR)

# 禁用Python的字节码缓存
sys.dont_write_bytecode = True

app = Flask(__name__, 
    template_folder=os.path.join(ROOT_DIR, 'src/webui/templates'),
    static_folder=os.path.join(ROOT_DIR, 'src/webui/static'))

# 添加配置
app.config['UPLOAD_FOLDER'] = os.path.join(ROOT_DIR, 'src/webui/background_image')

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 生成密钥用于session加密
app.secret_key = secrets.token_hex(16)

def print_status(message: str, status: str = "info", emoji: str = ""):
    """打印带颜色和表情的状态消息"""
    colors = {
        "success": Fore.GREEN,
        "info": Fore.BLUE,
        "warning": Fore.YELLOW,
        "error": Fore.RED
    }
    color = colors.get(status, Fore.WHITE)
    print(f"{color}{emoji} {message}{Style.RESET_ALL}")


def get_available_avatars() -> List[str]:
    """获取可用的人设目录列表"""
    avatar_base_dir = os.path.join(ROOT_DIR, "data/avatars")
    if not os.path.exists(avatar_base_dir):
        return []
    
    # 获取所有包含 avatar.md 和 emojis 目录的有效人设目录
    avatars = []
    for item in os.listdir(avatar_base_dir):
        avatar_dir = os.path.join(avatar_base_dir, item)
        if os.path.isdir(avatar_dir):
            if os.path.exists(os.path.join(avatar_dir, "avatar.md")) and \
               os.path.exists(os.path.join(avatar_dir, "emojis")):
                avatars.append(f"data/avatars/{item}")
    
    return avatars

def parse_config_groups() -> Dict[str, Dict[str, Any]]:
    """解析配置文件，将配置项按组分类"""
    from src.config import config

    config_groups = {
        "基础配置": {},
        "图像识别API配置": {},
        "图像生成配置": {},
        "时间配置": {},
        "语音配置": {},
        "Prompt配置": {},
    }

    # 基础配置
    config_groups["基础配置"].update(
        {
            "LISTEN_LIST": {
                "value": config.user.listen_list,
                "description": "用户列表(请配置要和bot说话的账号的昵称或者群名，不要写备注！)",
            },
            "MODEL": {"value": config.llm.model, "description": "AI模型选择"},
            "DEEPSEEK_BASE_URL": {
                "value": config.llm.base_url,
                "description": "硅基流动API注册地址",
            },
            "DEEPSEEK_API_KEY": {
                "value": config.llm.api_key,
                "description": "DeepSeek API密钥",
            },
            "MAX_TOKEN": {
                "value": config.llm.max_tokens,
                "description": "回复最大token数",
                "type": "number",
            },
            "TEMPERATURE": {
                "value": float(config.llm.temperature),  # 确保是浮点数
                "type": "number",
                "description": "温度参数",
                "min": 0.0,
                "max": 1.7
            },
        }
    )

    # 图像识别API配置
    config_groups["图像识别API配置"].update(
        {
            "MOONSHOT_API_KEY": {
                "value": config.media.image_recognition.api_key,
                "description": "Moonshot API密钥（用于图片和表情包识别）",
            },
            "MOONSHOT_BASE_URL": {
                "value": config.media.image_recognition.base_url,
                "description": "Moonshot API基础URL",
            },
            "MOONSHOT_TEMPERATURE": {
                "value": config.media.image_recognition.temperature,
                "description": "Moonshot温度参数",
            },
        }
    )

    # 图像生成配置
    config_groups["图像生成配置"].update(
        {
            "IMAGE_MODEL": {
                "value": config.media.image_generation.model,
                "description": "图像生成模型",
            },
            "TEMP_IMAGE_DIR": {
                "value": config.media.image_generation.temp_dir,
                "description": "临时图片目录",
            },
        }
    )

    # 时间配置
    config_groups["时间配置"].update(
        {
            "AUTO_MESSAGE": {
                "value": config.behavior.auto_message.content,
                "description": "自动消息内容",
            },
            "MIN_COUNTDOWN_HOURS": {
                "value": config.behavior.auto_message.min_hours,
                "description": "最小倒计时时间（小时）",
            },
            "MAX_COUNTDOWN_HOURS": {
                "value": config.behavior.auto_message.max_hours,
                "description": "最大倒计时时间（小时）",
            },
            "QUIET_TIME_START": {
                "value": config.behavior.quiet_time.start,
                "description": "安静时间开始",
            },
            "QUIET_TIME_END": {
                "value": config.behavior.quiet_time.end,
                "description": "安静时间结束",
            },
        }
    )

    # 语音配置
    config_groups["语音配置"].update(
        {
            "TTS_API_URL": {
                "value": config.media.text_to_speech.tts_api_url,
                "description": "语音服务API地址",
            },
            "VOICE_DIR": {
                "value": config.media.text_to_speech.voice_dir,
                "description": "语音文件目录",
            },
        }
    )

    # Prompt配置
    available_avatars = get_available_avatars()
    config_groups["Prompt配置"].update(
        {
            "MAX_GROUPS": {
                "value": config.behavior.context.max_groups,
                "description": "最大的上下文轮数",
            },
            "AVATAR_DIR": {
                "value": config.behavior.context.avatar_dir,
                "description": "人设目录（自动包含 avatar.md 和 emojis 目录）",
                "options": available_avatars,
                "type": "select"
            }
        }
    )

    return config_groups


def save_config(new_config: Dict[str, Any]) -> bool:
    """保存新的配置到文件"""
    try:
        from src.config import (
            UserSettings,
            LLMSettings,
            ImageRecognitionSettings,
            ImageGenerationSettings,
            TextToSpeechSettings,
            MediaSettings,
            AutoMessageSettings,
            QuietTimeSettings,
            ContextSettings,
            BehaviorSettings,
            config
        )

        # 添加调试日志，查看接收到的所有参数
        logger.debug("接收到的所有配置参数:")
        for key, value in new_config.items():
            logger.debug(f"{key}: {value} (类型: {type(value)})")

        # 特别关注温度参数
        temperature = new_config.get("TEMPERATURE")
        logger.debug(f"温度参数: {temperature} (类型: {type(temperature)})")

        # 构建所有新的配置对象
        user_settings = UserSettings(
            listen_list=new_config.get("LISTEN_LIST", [])
        )

        llm_settings = LLMSettings(
            api_key=new_config.get("DEEPSEEK_API_KEY", ""),
            base_url=new_config.get("DEEPSEEK_BASE_URL", ""),
            model=new_config.get("MODEL", ""),
            max_tokens=int(new_config.get("MAX_TOKEN", 2000)),
            temperature=float(new_config.get("TEMPERATURE", 1.1))  # 改回 TEMPERATURE
        )

        # 记录转换后的温度值
        logger.debug(f"LLM设置中的温度值: {llm_settings.temperature}")

        media_settings = MediaSettings(
            image_recognition=ImageRecognitionSettings(
                api_key=new_config.get("MOONSHOT_API_KEY", ""),
                base_url=new_config.get("MOONSHOT_BASE_URL", ""),
                temperature=float(new_config.get("MOONSHOT_TEMPERATURE", 1.1)),
            ),
            image_generation=ImageGenerationSettings(
                model=new_config.get("IMAGE_MODEL", ""),
                temp_dir=new_config.get("TEMP_IMAGE_DIR", ""),
            ),
            text_to_speech=TextToSpeechSettings(
                tts_api_url=new_config.get("TTS_API_URL", ""),
                voice_dir=new_config.get("VOICE_DIR", ""),
            )
        )

        behavior_settings = BehaviorSettings(
            auto_message=AutoMessageSettings(
                content=new_config.get("AUTO_MESSAGE", ""),
                min_hours=float(new_config.get("MIN_COUNTDOWN_HOURS", 1)),
                max_hours=float(new_config.get("MAX_COUNTDOWN_HOURS", 3)),
            ),
            quiet_time=QuietTimeSettings(
                start=new_config.get("QUIET_TIME_START", ""),
                end=new_config.get("QUIET_TIME_END", ""),
            ),
            context=ContextSettings(
                max_groups=int(new_config.get("MAX_GROUPS", 15)),
                avatar_dir=new_config.get("AVATAR_DIR", ""),
            ),
        )

        # 构建JSON结构
        config_data = {
            "categories": {
                "user_settings": {
                    "title": "用户设置",
                    "settings": {
                        "listen_list": {
                            "value": user_settings.listen_list,
                            "type": "array",
                            "description": "要监听的用户列表（请使用微信昵称，不要使用备注名）",
                        }
                    },
                },
                "llm_settings": {
                    "title": "大语言模型配置",
                    "settings": {
                        "api_key": {
                            "value": llm_settings.api_key,
                            "type": "string",
                            "description": "DeepSeek API密钥",
                            "is_secret": True,
                        },
                        "base_url": {
                            "value": llm_settings.base_url,
                            "type": "string",
                            "description": "DeepSeek API基础URL",
                        },
                        "model": {
                            "value": llm_settings.model,
                            "type": "string",
                            "description": "使用的AI模型名称",
                            "options": [
                                "deepseek-ai/DeepSeek-V3",
                                "Pro/deepseek-ai/DeepSeek-V3",
                                "Pro/deepseek-ai/DeepSeek-R1",
                            ],
                        },
                        "max_tokens": {
                            "value": llm_settings.max_tokens,
                            "type": "number",
                            "description": "回复最大token数量",
                        },
                        "temperature": {
                            "value": float(llm_settings.temperature),
                            "type": "number",
                            "description": "AI回复的温度值",
                            "min": 0.0,
                            "max": 1.7
                        },
                    },
                },
                "media_settings": {
                    "title": "媒体设置",
                    "settings": {
                        "image_recognition": {
                            "api_key": {
                                "value": media_settings.image_recognition.api_key,
                                "type": "string",
                                "description": "Moonshot AI API密钥（用于图片和表情包识别）",
                                "is_secret": True,
                            },
                            "base_url": {
                                "value": media_settings.image_recognition.base_url,
                                "type": "string",
                                "description": "Moonshot API基础URL",
                            },
                            "temperature": {
                                "value": media_settings.image_recognition.temperature,
                                "type": "number",
                                "description": "Moonshot AI的温度值",
                                "min": 0,
                                "max": 2,
                            },
                        },
                        "image_generation": {
                            "model": {
                                "value": media_settings.image_generation.model,
                                "type": "string",
                                "description": "图像生成模型",
                            },
                            "temp_dir": {
                                "value": media_settings.image_generation.temp_dir,
                                "type": "string",
                                "description": "临时图片存储目录",
                            },
                        },
                        "text_to_speech": {
                            "tts_api_url": {
                                "value": media_settings.text_to_speech.tts_api_url,
                                "type": "string",
                                "description": "TTS服务API地址",
                            },
                            "voice_dir": {
                                "value": media_settings.text_to_speech.voice_dir,
                                "type": "string",
                                "description": "语音文件存储目录",
                            },
                        }
                    },
                },
                "behavior_settings": {
                    "title": "行为设置",
                    "settings": {
                        "auto_message": {
                            "content": {
                                "value": behavior_settings.auto_message.content,
                                "type": "string",
                                "description": "自动消息内容",
                            },
                            "countdown": {
                                "min_hours": {
                                    "value": behavior_settings.auto_message.min_hours,
                                    "type": "number",
                                    "description": "最小倒计时时间（小时）",
                                },
                                "max_hours": {
                                    "value": behavior_settings.auto_message.max_hours,
                                    "type": "number",
                                    "description": "最大倒计时时间（小时）",
                                },
                            },
                        },
                        "quiet_time": {
                            "start": {
                                "value": behavior_settings.quiet_time.start,
                                "type": "string",
                                "description": "安静时间开始",
                            },
                            "end": {
                                "value": behavior_settings.quiet_time.end,
                                "type": "string",
                                "description": "安静时间结束",
                            },
                        },
                        "context": {
                            "max_groups": {
                                "value": behavior_settings.context.max_groups,
                                "type": "number",
                                "description": "最大上下文轮数",
                            },
                            "avatar_dir": {
                                "value": behavior_settings.context.avatar_dir,
                                "type": "string",
                                "description": "人设目录（自动包含 avatar.md 和 emojis 目录）",
                            },
                        },
                    },
                },
            }
        }

        # 在保存前记录最终的温度配置
        final_temp = config_data["categories"]["llm_settings"]["settings"]["temperature"]["value"]
        logger.debug(f"最终保存到JSON的温度值: {final_temp} (类型: {type(final_temp)})")

        # 使用 Config 类的方法保存配置
        if not config.save_config(config_data):
            logger.error("保存配置失败")
            return False

        # 重新加载配置模块
        importlib.reload(sys.modules["src.config"])
        
        logger.debug("配置已成功保存和重新加载")
        return True
        
    except Exception as e:
        logger.error(f"保存配置失败: {str(e)}")
        return False


@app.route('/')
def index():
    """重定向到控制台"""
    return redirect(url_for('dashboard'))

@app.route('/save', methods=['POST'])
def save():
    """保存配置"""
    try:
        new_config = request.json
        # 添加调试日志
        logger.debug(f"接收到的配置数据: {new_config}")
        logger.debug(f"MIN_COUNTDOWN_HOURS type: {type(new_config.get('MIN_COUNTDOWN_HOURS'))}")
        logger.debug(f"MIN_COUNTDOWN_HOURS value: {new_config.get('MIN_COUNTDOWN_HOURS')}")
        
        if save_config(new_config):
            return jsonify({"status": "success", "message": "配置已保存"})
        return jsonify({"status": "error", "message": "保存失败"})
    except Exception as e:
        logger.error(f"保存失败: {str(e)}")
        return jsonify({"status": "error", "message": f"保存失败: {str(e)}"})

# 添加上传处理路由
@app.route('/upload_background', methods=['POST'])
def upload_background():
    if 'background' not in request.files:
        return jsonify({"status": "error", "message": "没有选择文件"})
    
    file = request.files['background']
    if file.filename == '':
        return jsonify({"status": "error", "message": "没有选择文件"})
    
    if file:
        filename = secure_filename(file.filename)
        # 清理旧的背景图片
        for old_file in os.listdir(app.config['UPLOAD_FOLDER']):
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], old_file))
        # 保存新图片
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({
            "status": "success", 
            "message": "背景图片已更新",
            "path": f"/background_image/{filename}"
        })

# 添加背景图片目录的路由
@app.route('/background_image/<filename>')
def background_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# 添加获取背景图片路由
@app.route('/get_background')
def get_background():
    """获取当前背景图片"""
    try:
        # 获取背景图片目录中的第一个文件
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        if files:
            # 返回找到的第一个图片
            return jsonify({
                "status": "success",
                "path": f"/background_image/{files[0]}"
            })
        return jsonify({
            "status": "success",
            "path": None
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

# 添加新的路由
@app.route('/dashboard')
def dashboard():
    """仪表盘页面"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template(
        'dashboard.html', 
        is_local=is_local_network(),
        active_page='dashboard'
    )

@app.route('/system_info')
def system_info():
    """获取系统信息"""
    try:
        # 创建静态变量存储上次的值
        if not hasattr(system_info, 'last_bytes'):
            system_info.last_bytes = {
                'sent': 0,
                'recv': 0,
                'time': time.time()
            }

        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()
        
        # 计算网络速度
        current_time = time.time()
        time_delta = current_time - system_info.last_bytes['time']
        
        # 计算每秒的字节数
        upload_speed = (net.bytes_sent - system_info.last_bytes['sent']) / time_delta
        download_speed = (net.bytes_recv - system_info.last_bytes['recv']) / time_delta
        
        # 更新上次的值
        system_info.last_bytes = {
            'sent': net.bytes_sent,
            'recv': net.bytes_recv,
            'time': current_time
        }
        
        # 转换为 KB/s
        upload_speed = upload_speed / 1024
        download_speed = download_speed / 1024
        
        return jsonify({
            'cpu': cpu_percent,
            'memory': {
                'total': round(memory.total / (1024**3), 2),
                'used': round(memory.used / (1024**3), 2),
                'percent': memory.percent
            },
            'disk': {
                'total': round(disk.total / (1024**3), 2),
                'used': round(disk.used / (1024**3), 2),
                'percent': disk.percent
            },
            'network': {
                'upload': round(upload_speed, 2),
                'download': round(download_speed, 2)
            }
        })
    except Exception as e:
        logger.error(f"获取系统信息失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/check_update')
def check_update():
    """检查更新"""
    try:
        updater = Updater()
        result = updater.check_for_updates()
        
        return jsonify({
            'status': 'success',
            'has_update': result.get('has_update', False),
            'console_output': result['output'],
            'update_info': result if result.get('has_update') else None,
            'wait_input': result.get('has_update', False)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'has_update': False,
            'console_output': f'检查更新失败: {str(e)}'
        })

@app.route('/confirm_update', methods=['POST'])
def confirm_update():
    """确认是否更新"""
    try:
        choice = request.json.get('choice', '').lower()
        if choice in ('y', 'yes'):
            updater = Updater()
            result = updater.update()
            
            return jsonify({
                'status': 'success' if result['success'] else 'error',
                'console_output': result['output']
            })
        else:
            return jsonify({
                'status': 'success',
                'console_output': '用户取消更新'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'console_output': f'更新失败: {str(e)}'
        })

@app.route('/start_bot')
def start_bot():
    """启动机器人"""
    global bot_process, bot_start_time
    try:
        if bot_process and bot_process.poll() is None:
            return jsonify({
                'status': 'error',
                'message': '机器人已在运行中'
            })
        
        # 清空之前的日志
        while not bot_logs.empty():
            bot_logs.get()
        
        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # 创建新的进程组
        if sys.platform.startswith('win'):
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            DETACHED_PROCESS = 0x00000008
            creationflags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
        else:
            creationflags = 0
        
        # 启动进程
        bot_process = subprocess.Popen(
            [sys.executable, 'run.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            env=env,
            encoding='utf-8',
            errors='replace',
            creationflags=creationflags if sys.platform.startswith('win') else 0,
            preexec_fn=os.setsid if not sys.platform.startswith('win') else None
        )
        
        # 记录启动时间
        bot_start_time = datetime.datetime.now()
        
        # 启动日志读取线程
        def read_output():
            try:
                while bot_process and bot_process.poll() is None:
                    line = bot_process.stdout.readline()
                    if line:
                        try:
                            # 尝试解码并清理日志内容
                            line = line.strip()
                            if isinstance(line, bytes):
                                line = line.decode('utf-8', errors='replace')
                            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
                            bot_logs.put(f"[{timestamp}] {line}")
                        except Exception as e:
                            logger.error(f"日志处理错误: {str(e)}")
                            continue
            except Exception as e:
                logger.error(f"读取日志失败: {str(e)}")
                bot_logs.put(f"[ERROR] 读取日志失败: {str(e)}")
        
        thread = threading.Thread(target=read_output, daemon=True)
        thread.start()
        
        return jsonify({
            'status': 'success',
            'message': '机器人启动成功'
        })
    except Exception as e:
        logger.error(f"启动机器人失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/get_bot_logs')
def get_bot_logs():
    """获取机器人日志"""
    logs = []
    while not bot_logs.empty():
        logs.append(bot_logs.get())
    
    # 获取运行时间
    uptime = '0分钟'
    if bot_start_time and bot_process and bot_process.poll() is None:
        delta = datetime.datetime.now() - bot_start_time
        total_seconds = int(delta.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            uptime = f"{hours}小时{minutes}分钟{seconds}秒"
        elif minutes > 0:
            uptime = f"{minutes}分钟{seconds}秒"
        else:
            uptime = f"{seconds}秒"
    
    return jsonify({
        'status': 'success',
        'logs': logs,
        'uptime': uptime,
        'is_running': bot_process is not None and bot_process.poll() is None
    })

@app.route('/stop_bot')
def stop_bot():
    """停止机器人"""
    global bot_process
    try:
        if bot_process:
            # 首先尝试正常终止进程
            bot_process.terminate()
            
            # 等待进程结束
            try:
                bot_process.wait(timeout=5)  # 等待最多5秒
            except subprocess.TimeoutExpired:
                # 如果超时，强制结束进程
                bot_process.kill()
                bot_process.wait()
            
            # 确保所有子进程都被终止
            if sys.platform.startswith('win'):
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(bot_process.pid)], 
                             capture_output=True)
            else:
                import signal
                os.killpg(os.getpgid(bot_process.pid), signal.SIGTERM)
            
            # 清理进程对象
            bot_process = None
            
            # 添加日志记录
            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            bot_logs.put(f"[{timestamp}] 正在关闭监听线程...")
            bot_logs.put(f"[{timestamp}] 正在关闭系统...")
            bot_logs.put(f"[{timestamp}] 系统已退出")
            
            return jsonify({
                'status': 'success',
                'message': '机器人已停止'
            })
            
        return jsonify({
            'status': 'error',
            'message': '机器人未在运行'
        })
    except Exception as e:
        logger.error(f"停止机器人失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/config')
def config():
    """配置页面"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    config_groups = parse_config_groups()  # 获取配置组
    return render_template(
        'config.html', 
        config_groups=config_groups,  # 传递配置组
        is_local=is_local_network(),  # 传递本地网络状态
        active_page='config'  # 传递当前页面标识
    )

# 添加获取用户信息的路由
@app.route('/user_info')
def get_user_info():
    """获取用户账户信息"""
    try:
        from src.config import config
        api_key = config.llm.api_key
        base_url = config.llm.base_url.rstrip('/')
        
        # 确保使用正确的API端点
        if 'siliconflow.cn' in base_url:
            api_url = f"{base_url}/user/info"
        else:
            return jsonify({
                'status': 'error',
                'message': '当前API不支持查询用户信息'
            })
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') is True and data.get('data'):  # 修改判断条件
                user_data = data['data']
                return jsonify({
                    'status': 'success',
                    'data': {
                        'balance': user_data.get('balance', '0'),
                        'total_balance': user_data.get('totalBalance', '0'),
                        'charge_balance': user_data.get('chargeBalance', '0'),
                        'name': user_data.get('name', 'Unknown'),
                        'email': user_data.get('email', 'Unknown'),
                        'status': user_data.get('status', 'Unknown')
                    }
                })
            
        return jsonify({
            'status': 'error',
            'message': f"API返回错误: {response.text}"
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f"获取用户信息失败: {str(e)}"
        })

# 在 app 初始化后添加
@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件服务"""
    return send_from_directory(app.static_folder, filename)

@app.route('/execute_command', methods=['POST'])
def execute_command():
    """执行控制台命令"""
    try:
        command = request.json.get('command', '').strip()
        global bot_process, bot_start_time
        
        # 处理内置命令
        if command.lower() == 'help':
            return jsonify({
                'status': 'success',
                'output': '''可用命令:
help - 显示帮助信息
clear - 清空日志
status - 显示系统状态
version - 显示版本信息
memory - 显示内存使用情况
start - 启动机器人
stop - 停止机器人
restart - 重启机器人

支持所有CMD命令，例如:
dir - 显示目录内容
cd - 切换目录
echo - 显示消息
type - 显示文件内容
等...'''
            })
            
        elif command.lower() == 'clear':
            # 清空日志队列
            while not bot_logs.empty():
                bot_logs.get()
            return jsonify({
                'status': 'success',
                'output': '',  # 返回空输出，让前端清空日志
                'clear': True  # 添加标记，告诉前端需要清空日志
            })
            
        elif command.lower() == 'status':
            if bot_process and bot_process.poll() is None:
                uptime = '0分钟'
                if bot_start_time:
                    delta = datetime.datetime.now() - bot_start_time
                    total_seconds = int(delta.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    if hours > 0:
                        uptime = f"{hours}小时{minutes}分钟{seconds}秒"
                    elif minutes > 0:
                        uptime = f"{minutes}分钟{seconds}秒"
                    else:
                        uptime = f"{seconds}秒"
                return jsonify({
                    'status': 'success',
                    'output': f'机器人状态: 运行中\n运行时间: {uptime}'
                })
            else:
                return jsonify({
                    'status': 'success',
                    'output': '机器人状态: 已停止'
                })
            
        elif command.lower() == 'version':
            return jsonify({
                'status': 'success',
                'output': 'My Dream Moments v1.3.1'
            })
            
        elif command.lower() == 'memory':
            memory = psutil.virtual_memory()
            return jsonify({
                'status': 'success',
                'output': f'内存使用: {memory.percent}% ({memory.used/1024/1024/1024:.1f}GB/{memory.total/1024/1024/1024:.1f}GB)'
            })
            
        elif command.lower() == 'start':
            if bot_process and bot_process.poll() is None:
                return jsonify({
                    'status': 'error',
                    'error': '机器人已在运行中'
                })
            
            # 清空之前的日志
            while not bot_logs.empty():
                bot_logs.get()
            
            # 设置环境变量
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # 创建新的进程组
            if sys.platform.startswith('win'):
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                DETACHED_PROCESS = 0x00000008
                creationflags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
            else:
                creationflags = 0
            
            # 启动进程
            bot_process = subprocess.Popen(
                [sys.executable, 'run.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                env=env,
                encoding='utf-8',
                errors='replace',
                creationflags=creationflags if sys.platform.startswith('win') else 0,
                preexec_fn=os.setsid if not sys.platform.startswith('win') else None
            )
            
            # 记录启动时间
            bot_start_time = datetime.datetime.now()
            
            return jsonify({
                'status': 'success',
                'output': '机器人启动成功'
            })
            
        elif command.lower() == 'stop':
            if bot_process and bot_process.poll() is None:
                try:
                    # 首先尝试正常终止进程
                    bot_process.terminate()
                    
                    # 等待进程结束
                    try:
                        bot_process.wait(timeout=5)  # 等待最多5秒
                    except subprocess.TimeoutExpired:
                        # 如果超时，强制结束进程
                        bot_process.kill()
                        bot_process.wait()
                    
                    # 确保所有子进程都被终止
                    if sys.platform.startswith('win'):
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(bot_process.pid)], 
                                     capture_output=True)
                    else:
                        import signal
                        os.killpg(os.getpgid(bot_process.pid), signal.SIGTERM)
                    
                    # 清理进程对象
                    bot_process = None
                    bot_start_time = None
                    
                    return jsonify({
                        'status': 'success',
                        'output': '机器人已停止'
                    })
                except Exception as e:
                    return jsonify({
                        'status': 'error',
                        'error': f'停止失败: {str(e)}'
                    })
            else:
                return jsonify({
                    'status': 'error',
                    'error': '机器人未在运行'
                })
            
        elif command.lower() == 'restart':
            # 先停止
            if bot_process and bot_process.poll() is None:
                try:
                    bot_process.terminate()
                    try:
                        bot_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        bot_process.kill()
                        bot_process.wait()
                    
                    if sys.platform.startswith('win'):
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(bot_process.pid)], 
                                     capture_output=True)
                    else:
                        import signal
                        os.killpg(os.getpgid(bot_process.pid), signal.SIGTERM)
                except Exception as e:
                    return jsonify({
                        'status': 'error',
                        'error': f'重启失败: {str(e)}'
                    })
            
            time.sleep(2)  # 等待进程完全停止
            
            # 然后重新启动
            try:
                # 清空日志
                while not bot_logs.empty():
                    bot_logs.get()
                
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                
                if sys.platform.startswith('win'):
                    CREATE_NEW_PROCESS_GROUP = 0x00000200
                    DETACHED_PROCESS = 0x00000008
                    creationflags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
                else:
                    creationflags = 0
                
                bot_process = subprocess.Popen(
                    [sys.executable, 'run.py'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                    env=env,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=creationflags if sys.platform.startswith('win') else 0,
                    preexec_fn=os.setsid if not sys.platform.startswith('win') else None
                )
                
                bot_start_time = datetime.datetime.now()
                
                return jsonify({
                    'status': 'success',
                    'output': '机器人已重启'
                })
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'error': f'重启失败: {str(e)}'
                })
            
        # 执行CMD命令
        else:
            try:
                # 使用subprocess执行命令并捕获输出
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding='utf-8',
                    errors='replace'
                )
                
                # 获取命令输出
                stdout, stderr = process.communicate(timeout=30)
                
                # 如果有错误输出
                if stderr:
                    return jsonify({
                        'status': 'error',
                        'error': stderr
                    })
                    
                # 返回命令执行结果
                return jsonify({
                    'status': 'success',
                    'output': stdout or '命令执行成功，无输出'
                })
                
            except subprocess.TimeoutExpired:
                process.kill()
                return jsonify({
                    'status': 'error',
                    'error': '命令执行超时'
                })
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'error': f'执行命令失败: {str(e)}'
                })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': f'执行命令失败: {str(e)}'
        })

@app.route('/check_dependencies')
def check_dependencies():
    """检查Python和pip环境"""
    try:
        # 检查Python版本
        python_version = sys.version.split()[0]
        
        # 检查pip是否安装
        pip_path = shutil.which('pip')
        has_pip = pip_path is not None
        
        # 检查requirements.txt是否存在
        requirements_path = os.path.join(ROOT_DIR, 'requirements.txt')
        has_requirements = os.path.exists(requirements_path)
        
        # 如果requirements.txt存在，检查是否所有依赖都已安装
        dependencies_status = "unknown"
        missing_deps = []
        if has_requirements and has_pip:
            try:
                # 获取已安装的包列表
                process = subprocess.Popen(
                    [sys.executable, '-m', 'pip', 'list'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                stdout, stderr = process.communicate()
                # 解析pip list的输出，只获取包名
                installed_packages = {
                    line.split()[0].lower() 
                    for line in stdout.split('\n')[2:] 
                    if line.strip()
                }
                
                logger.debug(f"已安装的包: {installed_packages}")
                
                # 读取requirements.txt，只获取包名
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    required_packages = set()
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # 只取包名，忽略版本信息
                            pkg = line.split('=')[0].split('>')[0].split('<')[0].split('~')[0]
                            pkg = pkg.strip().lower()
                            required_packages.add(pkg)
                
                logger.debug(f"需要的包: {required_packages}")
                
                # 检查缺失的依赖
                missing_deps = [
                    pkg for pkg in required_packages 
                    if pkg not in installed_packages and not (
                        pkg == 'wxauto' and 'wxauto-py' in installed_packages
                    )
                ]
                
                logger.debug(f"缺失的包: {missing_deps}")
                
                # 根据是否有缺失依赖设置状态
                dependencies_status = "complete" if not missing_deps else "incomplete"
                    
            except Exception as e:
                logger.error(f"检查依赖时出错: {str(e)}")
                dependencies_status = "error"
        else:
            dependencies_status = "complete" if not has_requirements else "incomplete"
        
        return jsonify({
            'status': 'success',
            'python_version': python_version,
            'has_pip': has_pip,
            'has_requirements': has_requirements,
            'dependencies_status': dependencies_status,
            'missing_dependencies': missing_deps
        })
    except Exception as e:
        logger.error(f"依赖检查失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/favicon.ico')
def favicon():
    """提供网站图标"""
    return send_from_directory(
        os.path.join(app.root_path, 'src/webui/static'),
        'mom.ico',
        mimetype='image/vnd.microsoft.icon'
    )

def cleanup_processes():
    """清理所有相关进程"""
    try:
        # 清理机器人进程
        global bot_process
        if bot_process:
            try:
                # 获取进程组
                parent = psutil.Process(bot_process.pid)
                children = parent.children(recursive=True)
                
                # 终止子进程
                for child in children:
                    try:
                        child.terminate()
                    except:
                        child.kill()
                
                # 终止主进程
                bot_process.terminate()
                
                # 等待进程结束
                gone, alive = psutil.wait_procs(children + [parent], timeout=3)
                
                # 强制结束仍在运行的进程
                for p in alive:
                    try:
                        p.kill()
                    except:
                        pass
                
                bot_process = None
                
            except Exception as e:
                logger.error(f"清理机器人进程失败: {str(e)}")
        
        # 清理当前进程的所有子进程
        current_process = psutil.Process()
        children = current_process.children(recursive=True)
        for child in children:
            try:
                child.terminate()
            except:
                try:
                    child.kill()
                except:
                    pass
        
        # 等待所有子进程结束
        gone, alive = psutil.wait_procs(children, timeout=3)
        for p in alive:
            try:
                p.kill()
            except:
                pass
                
    except Exception as e:
        logger.error(f"清理进程失败: {str(e)}")

def signal_handler(signum, frame):
    """信号处理函数"""
    logger.info(f"收到信号: {signum}")
    cleanup_processes()
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Windows平台特殊处理
if sys.platform.startswith('win'):
    try:
        signal.signal(signal.SIGBREAK, signal_handler)
    except:
        pass

# 注册退出处理
atexit.register(cleanup_processes)

def open_browser(port):
    """在新线程中打开浏览器"""
    def _open_browser():
        # 等待服务器启动
        time.sleep(1.5)
        # 优先使用 localhost
        url = f"http://localhost:{port}"
        webbrowser.open(url)
    
    # 创建新线程来打开浏览器
    threading.Thread(target=_open_browser, daemon=True).start()

def main():
    """主函数"""
    from src.config import config
    
    # 设置系统编码为 UTF-8 (不清除控制台输出)
    if sys.platform.startswith('win'):
        os.system("@chcp 65001 >nul")  # 使用 >nul 来隐藏输出而不清屏
    
    print("\n" + "="*50)
    print_status("配置管理系统启动中...", "info", "🚀")
    print("-"*50)
    
    # 检查必要目录
    print_status("检查系统目录...", "info", "📁")
    if not os.path.exists(os.path.join(ROOT_DIR, 'src/webui/templates')):
        print_status("错误：模板目录不存在！", "error", "❌")
        return
    print_status("系统目录检查完成", "success", "✅")
    
    # 检查配置文件
    print_status("检查配置文件...", "info", "⚙️")
    if not os.path.exists(config.config_path):
        print_status("错误：配置文件不存在！", "error", "❌")
        return
    print_status("配置文件检查完成", "success", "✅")
    
    # 清理缓存
    print_status("清理系统缓存...", "info", "🧹")
    cleanup_count = 0
    for root, dirs, files in os.walk(ROOT_DIR):
        if '__pycache__' in dirs:
            cleanup_count += 1
    if cleanup_count > 0:
        print_status(f"已清理 {cleanup_count} 个缓存目录", "success", "🗑️")
    else:
        print_status("没有需要清理的缓存", "info", "✨")
    
    # 修改启动 Web 服务器的部分
    cli = sys.modules['flask.cli']
    cli.show_server_banner = lambda *x: None  # 禁用 Flask 启动横幅
    
    host = '0.0.0.0'
    port = 8501
    
    print_status("正在启动Web服务...", "info", "🌐")
    print("-"*50)
    print_status("配置管理系统已就绪！", "success", "✨")
    
    # 获取本机所有IP地址
    def get_ip_addresses():
        ip_list = []
        try:
            # 获取主机名
            hostname = socket.gethostname()
            # 获取本机IP地址列表
            addresses = socket.getaddrinfo(hostname, None)
            
            for addr in addresses:
                ip = addr[4][0]
                # 只获取IPv4地址且不是回环地址
                if '.' in ip and ip != '127.0.0.1':
                    ip_list.append(ip)
        except:
            pass
        return ip_list

    # 显示所有可用的访问地址
    ip_addresses = get_ip_addresses()
    print_status("可通过以下地址访问:", "info", "🔗")
    print(f"  Local:   http://localhost:{port}")
    print(f"  Local:   http://127.0.0.1:{port}")
    for ip in ip_addresses:
        print(f"  Network: http://{ip}:{port}")
    print("="*50 + "\n")
    
    # 启动浏览器
    open_browser(port)
    
    app.run(
        host=host, 
        port=port, 
        debug=True,
        use_reloader=False  # 禁用重载器以避免创建多余的进程
    )

@app.route('/install_dependencies', methods=['POST'])
def install_dependencies():
    """安装依赖"""
    try:
        output = []
        
        # 安装依赖
        output.append("正在安装依赖...")
        requirements_path = os.path.join(ROOT_DIR, 'requirements.txt')
        
        if not os.path.exists(requirements_path):
            return jsonify({
                'status': 'error',
                'message': '找不到requirements.txt文件'
            })
            
        process = subprocess.Popen(
            [sys.executable, '-m', 'pip', 'install', '-r', requirements_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = process.communicate()
        output.append(stdout if stdout else stderr)
        
        if process.returncode == 0:
            return jsonify({
                'status': 'success',
                'output': '\n'.join(output)
            })
        else:
            return jsonify({
                'status': 'error',
                'output': '\n'.join(output),
                'message': '安装依赖失败'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

def hash_password(password: str) -> str:
    # 对密码进行哈希处理
    return hashlib.sha256(password.encode()).hexdigest()

def is_local_network() -> bool:
    # 检查是否是本地网络访问
    client_ip = request.remote_addr
    return (
        client_ip == '127.0.0.1' or 
        client_ip.startswith('192.168.') or 
        client_ip.startswith('10.') or 
        client_ip.startswith('172.16.')
    )

@app.before_request
def check_auth():
    # 请求前验证登录状态
    # 排除不需要验证的路由
    public_routes = ['login', 'static', 'init_password']
    if request.endpoint in public_routes:
        return
        
    # 检查是否需要初始化密码
    from src.config import config
    if not config.auth.admin_password:
        return redirect(url_for('init_password'))
        
    # 如果是本地网络访问，自动登录
    if is_local_network():
        session['logged_in'] = True
        return
        
    if not session.get('logged_in'):
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # 处理登录请求
    from src.config import config
    
    # 首先检查是否需要初始化密码
    if not config.auth.admin_password:
        return redirect(url_for('init_password'))
    
    if request.method == 'GET':
        # 如果已经登录，直接跳转到仪表盘
        if session.get('logged_in'):
            return redirect(url_for('dashboard'))
            
        # 如果是本地网络访问，自动登录并重定向到仪表盘
        if is_local_network():
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
            
        return render_template('login.html')
    
    # POST请求处理
    data = request.get_json()
    password = data.get('password')
    remember_me = data.get('remember_me', False)
    
    # 正常登录验证
    stored_hash = config.auth.admin_password
    if hash_password(password) == stored_hash:
        session.clear()  # 清除旧会话
        session['logged_in'] = True
        if remember_me:
            session.permanent = True
            app.permanent_session_lifetime = timedelta(days=30)
        return jsonify({'status': 'success'})
    
    return jsonify({
        'status': 'error',
        'message': '密码错误'
    })

@app.route('/init_password', methods=['GET', 'POST'])
def init_password():
    # 初始化管理员密码页面
    from src.config import config
    
    if request.method == 'GET':
        # 如果已经设置了密码，重定向到登录页面
        if config.auth.admin_password:
            return redirect(url_for('login'))
        return render_template('init_password.html')
        
    # POST请求处理
    try:
        data = request.get_json()
        if not data or 'password' not in data:
            return jsonify({
                'status': 'error',
                'message': '无效的请求数据'
            })
            
        password = data.get('password')
        
        # 再次检查是否已经设置了密码
        if config.auth.admin_password:
            return jsonify({
                'status': 'error',
                'message': '密码已经设置'
            })
        
        # 保存新密码的哈希值
        hashed_password = hash_password(password)
        if config.update_password(hashed_password):
            # 重新加载配置
            importlib.reload(sys.modules['src.config'])
            from src.config import config
            
            # 验证密码是否正确保存
            if not config.auth.admin_password:
                return jsonify({
                    'status': 'error',
                    'message': '密码保存失败'
                })
            
            # 设置登录状态
            session.clear()
            session['logged_in'] = True
            return jsonify({'status': 'success'})
        
        return jsonify({
            'status': 'error',
            'message': '保存密码失败'
        })
        
    except Exception as e:
        logger.error(f"初始化密码失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/logout')
def logout():
    # 退出登录
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        print_status("正在关闭服务...", "warning", "🛑")
        cleanup_processes()
        print_status("配置管理系统已停止", "info", "👋")
        print("\n")
    except Exception as e:
        print_status(f"系统错误: {str(e)}", "error", "💥")
        cleanup_processes()

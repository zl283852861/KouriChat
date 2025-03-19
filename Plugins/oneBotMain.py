# 目前默认回复所有好友的消息

import logging
import shutil
import threading
import nonebot
import json
import sys
import time
import os
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter
from nonebot.plugin import _plugins

src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.append(src_path)

from src.config.rag_config import config, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL, MAX_TOKEN, TEMPERATURE, MAX_GROUPS
from colorama import init, Style
from src.handlers.emoji import EmojiHandler
from src.handlers.image import ImageHandler
from src.handlers.message import MessageHandler
from src.handlers.voice import VoiceHandler
from src.services.ai.llm_service import LLMService
from src.services.ai.image_recognition_service import ImageRecognitionService
from src.handlers.memory import MemoryHandler
from src.utils.logger import LoggerConfig
from src.utils.console import print_status
from colorama import init, Style
from src.AutoTasker.autoTasker import AutoTasker
from src.utils.api_wrapper import APIWrapper
from src.handlers.memory import init_memory

from src.utils.console import print_status
# 获取项目根目录
root_dir = os.path.dirname(os.path.abspath(__file__))



# 检查并初始化配置文件
config_path = os.path.join(root_dir, 'src', 'config', 'config.json')
config_template_path = os.path.join(root_dir, 'src', 'config', 'config.json.template')

if not os.path.exists(config_path) and os.path.exists(config_template_path):
    logger = logging.getLogger('main')
    logger.info("配置文件不存在，正在从模板创建...")
    shutil.copy2(config_template_path, config_path)
    logger.info(f"已从模板创建配置文件: {config_path}")

# 读取提示文件
avatar_dir = os.path.join(root_dir, config.behavior.context.avatar_dir)
prompt_path = os.path.join(avatar_dir, "avatar.md")
with open(prompt_path, "r", encoding="utf-8") as file:
    prompt_content = file.read()

# 创建全局实例
emoji_handler = EmojiHandler(root_dir)
image_handler = ImageHandler(
    root_dir=root_dir,
    api_key=config.llm.api_key,
    base_url=config.llm.base_url,
    image_model=config.media.image_generation.model
)
voice_handler = VoiceHandler(
    root_dir=root_dir,
    tts_api_url=config.media.text_to_speech.tts_api_url
)

# 创建LLMService实例
with open(prompt_path, "r", encoding="utf-8") as f:
    deepseek = LLMService(
        sys_prompt=f.read(),
        api_key=config.llm.api_key,
        base_url=config.llm.base_url,
        model=config.llm.model,
        max_token=config.llm.max_tokens,
        temperature=config.llm.temperature,
        max_groups=config.behavior.context.max_groups,
    )

# 创建API包装器
api_wrapper = APIWrapper(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL
)

# 初始化记忆系统
memory_handler = init_memory(root_dir, api_wrapper)

moonshot_ai = ImageRecognitionService(
    api_key=config.media.image_recognition.api_key,
    base_url=config.media.image_recognition.base_url,
    temperature=config.media.image_recognition.temperature,
    model=config.media.image_recognition.model
)

message_handler = MessageHandler(
    root_dir=root_dir,
    llm=deepseek,  # 传递LLMService实例
    robot_name="KOURIQQ",  # QQ侧，使用固定机器人名称
    prompt_content=prompt_content,
    image_handler=image_handler,
    emoji_handler=emoji_handler,
    voice_handler=voice_handler,
    memory_handler=memory_handler,
    is_qq=True
)

if __name__ == '__main__':
    
    # 程序开始时间
    startTime = time.time_ns()

    # 插件目录加载进环境变量
    sys.path.append("../")
    sys.path.append("./src/Plugins/Basic_plugins")  # 底层插件
    sys.path.append("./src/Plugins/ChatPlugin")  # chat插件

    # 初始化nonebot
    nonebot.init()
    app = nonebot.get_asgi()

    # 连接驱动
    driver = nonebot.get_driver()
    driver.register_adapter(ONEBOT_V11Adapter)

    configDict = driver.config.dict()
    if "save_log_level" not in configDict.keys():
        save_log_level = "ERROR"
    else:
        save_log_level = configDict["save_log_level"]
    if not os.path.isdir("Log"):
        os.makedirs("Log")
    logger.add(f"onebotLog/KouriChat.log", level=save_log_level, rotation="1 days", retention="14 days")

    # 根据初始化配置选择插件目录配置文件进行初始化
    # 默认配置文件路径为./plugin.dev.json
    # 根据在.env中的环境设置，进行更新
    if "environment" not in configDict.keys():
        plugin_dir = "plugin.dev.json"
    else:
        environment = configDict["environment"]
        plugin_dir = "plugin." + environment + ".json"

    with open(plugin_dir, encoding="utf-8") as plg_dir:
        plugins = json.load(plg_dir)
        plugins = plugins["Plugin"]["Dir"]
        for plugin in plugins:
            time1 = time.time_ns()
            nonebot.load_plugin(plugin)
            time2 = time.time_ns()
            plugin_time = (time2 - time1) / 1000000000
            plugin_time = round(plugin_time, 3)
            print_status(f"插件{plugin}加载用时{plugin_time}s", "success", "CHECK")

    # 插件加载完毕后，加载meta.json
    metaDir = "oneBotConfig"
    for plugin_name, plugin in _plugins.items():
        metaPath = os.path.join(metaDir, plugin_name, "Metadata.json")
        # meta不存在，不进行初始化
        if plugin.metadata is None:
            # 不进行初始化
            print_status(f"插件{plugin_name}不存在metaData，不写入配置文件。","info","FILE")
            continue
        # 插件配置
        plugin_extra = plugin.metadata.extra
        jsonDict = {
            "extra": plugin_extra,
            "WARNING": "请勿更改下划线开头的变量数值！",
            "_extra": plugin_extra
        }
        if not os.path.isfile(metaPath):
            if not os.path.isdir(os.path.join(metaDir,plugin_name)):
                try :
                    os.makedirs(os.path.join(metaDir, plugin_name))
                    print_status(f"创建目录: {metaPath}", "info", "FILE")
                except OSError as e:
                    print_status(f"新建目录失败: {str(e)}", "error", "ERROR")
            with open(file=metaPath, mode="w", encoding="utf-8") as metaFile:
                metaFile.write(json.dumps(jsonDict, ensure_ascii=False, indent=4))
        else:
            # 实现效果：
            # 若插件extra未更新，则以json文件为标准
            # 若插件extra更新，则以插件为准，并覆盖更新json文件所有字段
            with open(file=metaPath, mode="a+", encoding="utf-8") as metaFile:
                metaFile.seek(0)
                info = metaFile.read()
                info = json.loads(info)
                configInitFlag = False
                updateFlag = False
                if "extra" not in info or "_extra" not in info:
                    configInitFlag = True
                else:
                    config_extra = info["extra"]
                    origin_extra = info["_extra"]
                    # 比对插件的extra，与文件创建时的原始extra
                    if origin_extra != plugin_extra:
                        updateFlag = True
                    else:
                        plugin.metadata.extra = info["extra"]
                # 信息恢复
                if configInitFlag or updateFlag:
                    infoMsg = f"插件{plugin_name}配置文件异常，正在恢复。" if configInitFlag else f"插件{plugin_name}配置已更新，重新写入配置文件。"
                    print_status(infoMsg, "info", "FILE")
                    # 根据插件信息进行恢复
                    info["extra"] = plugin.metadata.extra
                    info["_extra"] = plugin.metadata.extra
                    # 清空文件并重新写入
                    metaFile.seek(0)
                    metaFile.truncate()
                    metaFile.write(json.dumps(jsonDict, ensure_ascii=False, indent=4))
    plugin_number = len(_plugins.values())
    print_status(f"启动nonebot服务成功，共加载插件{plugin_number}个", "success", "CHECK")
    print_status("开始启动Kouri核心服务", "info", "CHECK")
    # 获取项目根目录

    # 检查并初始化配置文件
    config_path = os.path.join(root_dir, 'src', 'config', 'config.json')
    config_template_path = os.path.join(root_dir, 'src', 'config', 'config.json.template')

    if not os.path.exists(config_path) and os.path.exists(config_template_path):
        logger = logging.getLogger('main')
        logger.info("配置文件不存在，正在从模板创建...")
        shutil.copy2(config_template_path, config_path)
        logger.info(f"已从模板创建配置文件: {config_path}")

    # 配置日志
    # 清除所有现有日志处理器
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logger_config = LoggerConfig(root_dir)
    logger = logger_config.setup_logger('main')
    # 初始化colorama
    init()

    def memory_maintenance():
        while True:
            try:
                memory_handler.summarize_memories()
                time.sleep(3600)  # 每小时检查一次
            except Exception as e:
                logger.error(f"记忆维护失败: {str(e)}")
    print_status("启动记忆维护线程...", "info", "BRAIN")
    memory_thread = threading.Thread(target=memory_maintenance)

    print("-" * 50)
    print_status("系统初始化完成", "success", "STAR_2")
    print("=" * 50)
    
    nonebot.run(app="__mp_main__:app")




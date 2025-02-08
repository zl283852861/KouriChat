# 用户列表(请配置要和bot说话的账号的昵称或者群名，不要写备注！)
# 例如：LISTEN_LIST = ['用户1','用户2','群名']
LISTEN_LIST = ['hllqkb']
# 机器人的微信名称，如'亚托莉'
ROBOT_WX_NAME = '亚托莉'
# DeepSeek API 配置

DEEPSEEK_API_KEY = 'sk-bmvnslydzysacqzxgfidgznvwljbntalnusqghggqumszvrs'
# 硅基流动API注册地址，免费15元额度 https://cloud.siliconflow.cn/i/aQXU6eC5
DEEPSEEK_BASE_URL = 'https://api.siliconflow.cn/v1/'
# 如果要使用官方的API
# DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
# 硅基流动API的V3模型(deepseek-ai/DeepSeek-V3)，推荐充值才能使用的那个pro，模型名字是(Pro/deepseek-ai/DeepSeek-V3),还有r1 pro 名字(deepseek-ai/DeepSeek-R1)
# 要切换模型请把括号里的内容复制到MODEL里
MODEL = 'Pro/deepseek-ai/DeepSeek-V3'
# 官方API的V3模型
# MODEL = 'deepseek-chat'
# 回复最大token
MAX_TOKEN = 2000
#温度

TEMPERATURE = 1.3
#图像生成(默认使用 deepseek-ai/Janus-Pro-7B 模型)
IMAGE_MODEL = 'deepseek-ai/Janus-Pro-7B'
TEMP_IMAGE_DIR = 'temp_images'
#最大的上下文轮数
MAX_GROUPS = 15
#prompt文件名
PROMPT_NAME = 'ATRI.md'
#表情包存放目录
EMOJI_DIR = 'emojis'

#语音配置
TTS_API_URL = 'http://127.0.0.1:5000/tts'
VOICE_DIR = 'voices'  # 语音文件临时存储目录

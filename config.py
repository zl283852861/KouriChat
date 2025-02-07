# 用户列表(请配置要和bot说话的账号的昵称，不要写备注！)
# 例如：LISTEN_LIST = ['用户1','用户2']
LISTEN_LIST = ['要和bot说话的账号的昵称，不要写备注！']
# DeepSeek API 配置
DEEPSEEK_API_KEY = 'sk-'
# 硅基流动API注册地址，免费15元额度 https://cloud.siliconflow.cn/i/aQXU6eC5
DEEPSEEK_BASE_URL = 'https://api.siliconflow.cn/v1/'
# 如果要使用官方的API
# DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
# 硅基流动API的V3模型，推荐充值杀那个pro，注意看模型名字哦
MODEL = 'deepseek-ai/DeepSeek-V3'
# 官方API的V3模型
# MODEL = 'deepseek-chat'
# 回复最大token
MAX_TOKEN = 2000
#温度
TEMPERATURE = 1.3
#图像生成
IMAGE_MODEL = 'stabilityai/stable-diffusion-3-medium'
IMAGE_SIZE = '960x1280'
BATCH_SIZE = '1'
GUIDANCE_SCALE = '3'
NUM_INFERENCE_STEPS = '4'
PROMPT_ENHANCEMENT = 'True'
TEMP_IMAGE_DIR = 'temp_images'
#最大的上下文轮数
MAX_GROUPS = 15
#prompt文件名
PROMPT_NAME = 'ATRI.md'

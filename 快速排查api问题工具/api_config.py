import json
# 实际 AI 对话服务器的配置 --修改为json格式（其实我觉得可用读取config.json里的配置？）
try:
    # 读取 json 文件
    with open('api_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 将 json 中的配置信息提取为 Python 变量
    real_server_base_url = config.get('real_server_base_url')
    api_key = config.get('api_key')
    model = config.get('model')
    messages = config.get('messages')
# 这一行是为了以防有小呆呆非要在json配置，然后写错了json或者误删引号、逗号等过于逆天的操作。（呐其实也可不要。）
except FileNotFoundError:
    print("配置文件 api_config.json 未找到，请检查文件路径。")
except json.JSONDecodeError:
    print("配置文件 api_config.json 格式错误，请检查 JSON 格式。")

#呜呜呜，前端大佬看到这句话请把它写成webui的格式好吗？

#好的~
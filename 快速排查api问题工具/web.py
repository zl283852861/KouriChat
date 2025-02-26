from flask import Flask, render_template, request, jsonify, Response
import subprocess
import json
import threading
import sys


app = Flask(__name__)

class StreamLogger:
    def __init__(self):
        self._buffer = []
        self._lock = threading.Lock()

    def write(self, msg):
        with self._lock:
            self._buffer.append(msg)
        return len(msg)

    def flush(self):
        pass

    def get_output(self):
        with self._lock:
            output = ''.join(self._buffer)
            self._buffer.clear()
            return output

# 读取配置文件
def read_config():
    try:
        with open('api_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"real_server_base_url": "", "api_key": "", "model": "", "messages": []}

# 保存配置文件
def save_config(config):
    with open('api_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

# 首页路由，渲染HTML模板
@app.route('/')
def index():
    config = read_config()
    return render_template('index.html', config=config)

# 保存配置信息的路由
@app.route('/save_config', methods=['POST'])
def save_config_route():
    data = request.get_json()
    save_config(data)
    return jsonify({"status": "success"})

# 运行诊断测试的路由
@app.route('/run_diagnostic_test')
def run_diagnostic_test():
    def generate():
        try:
            # 执行 api_main.py 脚本，并捕获标准输出和标准错误输出
            process = subprocess.Popen(['python', 'api_main.py'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
            for line in process.stdout:
                # 将输出逐行发送给前端
                yield line
                # 刷新缓冲区，确保实时输出
                sys.stdout.flush()
            process.wait()
        except Exception as e:
            # 处理异常情况，将错误信息发送给前端
            yield f"Error: {str(e)}\n"

    # 返回一个流式响应，内容类型为文本
    return Response(generate(), mimetype='text/plain')

if __name__ == '__main__':
    # 启动Flask应用
    app.run(host='0.0.0.0', port=5000, debug=True)
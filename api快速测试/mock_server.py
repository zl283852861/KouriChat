"""
API模拟测试(支持本地和局域网):
负责模拟DeepSeek API的标准请求，包括
- 请求模拟
- 动态响应
- 异常测试
- 延时响应
"""

from flask import Flask, request, jsonify
import argparse
import time
from threading import Lock

app = Flask(__name__)
response_lock = Lock()

# 全局配置存储
config = {
    "default_response": {"content": "这是默认测试响应"},
    "enable_test_endpoints": False
}

@app.route('/v1/chat/completions', methods=['POST'])
def api_handler():
    """模拟DeepSeek标准API端点"""
    with response_lock:
        current_response = config['default_response'].copy()
    
    # 记录请求日志
    print("\n[请求日志]")
    print(f"Headers: {dict(request.headers)}")
    print(f"Body: {request.json}")

    # 构造响应
    return jsonify({
        "choices": [{
            "message": {
                "content": current_response['content']
            }
        }]
    })

@app.route('/control/set_response', methods=['POST'])
def set_custom_response():
    """动态修改响应内容"""
    if not request.is_json:
        return jsonify({"error": "需要JSON格式"}), 400
    
    new_response = request.json
    with response_lock:
        config['default_response'].update(new_response)
    
    print(f"\n[配置更新] 新响应内容: {new_response}")
    return jsonify({"status": "success", "new_response": new_response})

# 以下为测试专用端点（需通过--enable-test启用）
@app.route('/test/500', methods=['GET', 'POST'])
def mock_500_error():
    """模拟服务器错误"""
    return jsonify({
        "error": "测试用服务器错误",
        "detail": "这是模拟的500错误响应"
    }), 500

@app.route('/test/timeout/<int:delay>', methods=['GET'])
def mock_timeout(delay):
    """模拟延时响应"""
    time.sleep(delay)
    return jsonify({
        "status": f"延时 {delay} 秒响应",
        "data": "请求最终成功"
    })

if __name__ == '__main__':
    # 命令行参数配置
    parser = argparse.ArgumentParser(
        description='DeepSeek API模拟服务',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--port', type=int, default=5000,
                       help='服务监听端口')
    parser.add_argument('--enable-test', action='store_true',
                       help='启用测试端点(/test/*)')
    args = parser.parse_args()

    # 根据参数配置功能
    config['enable_test_endpoints'] = args.enable_test

    # 启动提示信息
    print(f"\n服务启动配置：")
    print(f"监听端口: {args.port}")
    print(f"测试端点: {'已启用' if args.enable_test else '已禁用'}")
    print(f"控制接口: POST /control/set_response")
    print(f"标准端点: POST /v1/chat/completions")
    
    # 启动服务（设置debug=False生产环境）
    app.run(host='0.0.0.0', port=args.port, debug=False)
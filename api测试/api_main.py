from mock_server import DeepSeekAPIMockServer
from api_request import APITester
import api_config
import threading
import time
import requests

def start_mock_server():
    """启动 DeepSeek API 模拟服务器"""
    server = DeepSeekAPIMockServer()
    server.run()

def test_servers():
    """测试模拟服务器和实际 AI 对话服务器"""
    # 等待模拟服务器启动
    time.sleep(2)
    # 创建 APITester 实例，使用模拟服务器的配置
    mock_tester = APITester(api_config.mock_server_base_url, api_config.api_key, api_config.model)

    try:
        print("正在向模拟服务器发送请求...")
        mock_tester.test_standard_api()
        print("模拟服务器响应正常。")
    except requests.exceptions.ConnectionError as e:
        print(f"向模拟服务器发送请求时出现连接错误: {e}。可能是服务器未启动、地址或端口错误，或者网络有问题。请检查服务器是否正常运行，确认地址和端口无误，检查网络连接。")
        return
    except requests.exceptions.Timeout as e:
        print(f"向模拟服务器发送请求时超时: {e}。可能是服务器响应慢或者网络延迟高。请稍后重试，或者检查网络环境。")
        return
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        if status_code == 400:
            print(f"向模拟服务器发送请求时收到 400 错误（错误请求）: {e}。可能是请求参数格式不正确。请检查请求数据。")
        elif status_code == 401:
            print(f"向模拟服务器发送请求时收到 401 错误（未授权）: {e}。可能是 API 密钥无效。请检查 API 密钥。")
        elif status_code == 404:
            print(f"向模拟服务器发送请求时收到 404 错误（未找到）: {e}。可能是请求的接口地址不存在。请检查接口地址。")
        elif status_code == 500:
            print(f"向模拟服务器发送请求时收到 500 错误（服务器内部错误）: {e}。可能是服务器出现问题。请联系服务器管理员。")
        else:
            print(f"向模拟服务器发送请求时收到 HTTP 错误: {e}。请根据状态码排查问题。")
        return
    except Exception as e:
        print(f"向模拟服务器发送请求时出现未知错误: {e}。请检查代码逻辑或联系技术支持。")
        return

    # 创建 APITester 实例，使用实际 AI 对话服务器的配置
    real_tester = APITester(api_config.real_server_base_url, api_config.api_key, api_config.model)

    try:
        print("正在向实际 AI 对话服务器发送请求...")
        real_tester.test_standard_api()
        print("实际 AI 对话服务器响应正常。")
    except requests.exceptions.ConnectionError as e:
        print(f"向实际 AI 对话服务器发送请求时出现连接错误: {e}。可能是服务器未启动、地址或端口错误，或者网络有问题。请检查服务器是否正常运行，确认地址和端口无误，检查网络连接。")
    except requests.exceptions.Timeout as e:
        print(f"向实际 AI 对话服务器发送请求时超时: {e}。可能是服务器响应慢或者网络延迟高。请稍后重试，或者检查网络环境。")
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        if status_code == 400:
            print(f"向实际 AI 对话服务器发送请求时收到 400 错误（错误请求）: {e}。可能是请求参数格式不正确。请检查请求数据。")
        elif status_code == 401:
            print(f"向实际 AI 对话服务器发送请求时收到 401 错误（未授权）: {e}。可能是 API 密钥无效。请检查 API 密钥。")
        elif status_code == 404:
            print(f"向实际 AI 对话服务器发送请求时收到 404 错误（未找到）: {e}。可能是请求的接口地址不存在。请检查接口地址。")
        elif status_code == 500:
            print(f"向实际 AI 对话服务器发送请求时收到 500 错误（服务器内部错误）: {e}。可能是服务器出现问题。请联系服务器管理员。")
        else:
            print(f"向实际 AI 对话服务器发送请求时收到 HTTP 错误: {e}。请根据状态码排查问题。")
    except Exception as e:
        print(f"向实际 AI 对话服务器发送请求时出现未知错误: {e}。请检查代码逻辑或联系技术支持。")

if __name__ == "__main__":
    # 启动模拟服务器线程
    mock_server_thread = threading.Thread(target=start_mock_server)
    mock_server_thread.daemon = True
    mock_server_thread.start()

    # 开始测试服务器
    test_servers()

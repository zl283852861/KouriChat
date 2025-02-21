import requests

# 服务地址和端口，这里替换为实际的服务器地址
base_url = 'http://your-server-address:port'
# 替换为实际的 API 密钥
api_key = 'your-api-key'

# 1. 向标准 API 端点发送请求
def test_standard_api():
    """
    测试标准 API 端点 /v1/chat/completions
    """
    url = f'{base_url}/v1/chat/completions'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    data = {
        "prompt": "这是一个测试请求"
    }
    response = requests.post(url, headers=headers, json=data)
    print("标准 API 端点响应:")
    print(response.json())

# 2. 动态修改响应内容
def test_set_custom_response():
    """
    测试动态修改响应内容的接口 /control/set_response
    """
    url = f'{base_url}/control/set_response'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    new_response = {
        "content": "这是自定义的测试响应"
    }
    response = requests.post(url, headers=headers, json=new_response)
    print("动态修改响应内容的接口响应:")
    print(response.json())

# 3. 模拟服务器错误
def test_mock_500_error():
    """
    测试模拟服务器错误的接口 /test/500
    """
    url = f'{base_url}/test/500'
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    response = requests.get(url, headers=headers)
    print("模拟服务器错误的接口响应:")
    print(response.status_code)
    print(response.json())

# 4. 模拟延时响应
def test_mock_timeout():
    """
    测试模拟延时响应的接口 /test/timeout/<delay>
    """
    delay = 5  # 延时 5 秒
    url = f'{base_url}/test/timeout/{delay}'
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    response = requests.get(url, headers=headers)
    print("模拟延时响应的接口响应:")
    print(response.json())

if __name__ == "__main__":
    # 测试标准 API 端点
    test_standard_api()

    # 动态修改响应内容
    test_set_custom_response()

    # 再次测试标准 API 端点，验证响应内容是否已修改
    test_standard_api()

    # 模拟服务器错误
    test_mock_500_error()

    # 模拟延时响应
    test_mock_timeout()

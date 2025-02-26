import requests

class APITester:
    def __init__(self, base_url, api_key, model, messages=None):  # 添加messages参数
        """
        初始化 API 测试类
        :param messages: 对话消息列表
        """
        self.messages = messages or [{"role": "user", "content": "测试消息"}]
        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    def test_standard_api(self):
        """测试标准 API 端点 /v1/chat/completions"""
        url = f'{self.base_url}/v1/chat/completions'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        data = {
            "model": self.model,
            "messages": self.messages  # 替换原来的prompt字段
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # 新增状态码检查
        return response  # 新增返回响应对象

if __name__ == "__main__":
    # 服务地址和端口，这里替换为实际的服务器地址
    base_url = 'http://your-server-address:port'
    # 替换为实际的 API 密钥
    api_key = 'your-api-key'
    # 选择要使用的模型
    model = "your-model-name"

    tester = APITester(base_url, api_key, model)

    # 测试标准 API 端点
    tester.test_standard_api()

    # 动态修改响应内容
    tester.test_set_custom_response()

    # 再次测试标准 API 端点，验证响应内容是否已修改
    tester.test_standard_api()

from web_config import app

if __name__ == '__main__':
    print("配置管理页面已启动，请访问: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000) 
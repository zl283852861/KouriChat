# v2.0 HTTP API 文档

## 目录
- [认证说明](#认证说明)
- [基础接口](#基础接口)
- [消息接口](#消息接口)
- [配置管理](#配置管理)
- [系统管理](#系统管理)
- [资源管理](#资源管理)
- [机器人管理](#机器人管理)
- [任务管理](#任务管理)
- [微信相关](#微信相关)

## 认证说明
除了白名单接口外，所有接口都需要在请求头中携带 `Authorization` Token，或者使用会话（Session）认证。

白名单接口：
- `/`
- `/is_first`
- `/login`
- `/init_password`

## 基础接口

### 服务器状态检查
- **URL**: `/`
- **方法**: `GET`
- **描述**: 检查服务器运行状态
- **响应**: 
  ```json
  {
    "status": "ok",
    "message": "Chat server is running"
  }
  ```

### 首次启动检查
- **URL**: `/is_first`
- **方法**: `GET`
- **描述**: 判断是否是第一次启动
- **响应**:
  - 成功: `{"status":"ok","message":"not first"}`
  - 首次: `{"status":"error","message":"first"}`

### 登录
- **URL**: `/login`
- **方法**: `POST`
- **请求体**:
  ```json
  {
    "password": "登录密码",
    "remember_me": true/false
  }
  ```
- **响应**:
  - 成功: `{"status":"success","message":"登录成功","token":"xxx"}`
  - 失败: `{"status":"error","message":"密码错误"}`

### 初始化密码
- **URL**: `/init_password`
- **方法**: `POST`
- **请求体**:
  ```json
  {
    "password": "设置的密码"
  }
  ```
- **响应**:
  - 成功: `{"status":"success"}`
  - 失败: `{"status":"error","message":"错误信息"}`

### 登出
- **URL**: `/logout`
- **方法**: `GET`
- **响应**:
  - 成功: 重定向到登录页面
  - 失败: 错误信息

## 消息接口

### 发送文本消息
- **URL**: `/message/text`
- **方法**: `POST`
- **Content-Type**: `application/json`
- **请求体**:
  ```json
  {
    "sender_id": 123,
    "sender": "发送者名称",
    "chat_type": "group",
    "character": 0,
    "message_type": "text",
    "message_send_time": "YYYY-MM-DD HH:mm:ss"
  }
  ```
- **响应**:
  - 成功: `{"status":"ok","message":"消息接收成功","received_content":"xxx"}`

### 发送图片消息
- **URL**: `/message/image`
- **方法**: `POST`
- **Content-Type**: `multipart/form-data`
- **表单字段**:
  - image: 图片文件
  - sender_id: 发送者ID
  - sender: 发送者名称
  - chat_type: 聊天类型
  - character: 角色ID
  - message_type: "image"
  - message_send_time: 发送时间
- **响应**:
  - 成功: `{"status":"ok","message":"图片上传成功","image_path":"xxx"}`

### 发送语音消息
- **URL**: `/message/voice`
- **方法**: `POST`
- **Content-Type**: `multipart/form-data`
- **表单字段**:
  - voice: 语音文件
  - sender_id: 发送者ID
  - sender: 发送者名称
  - chat_type: 聊天类型
  - character: 角色ID
  - message_type: "voice"
  - message_send_time: 发送时间
- **响应**:
  - 成功: `{"status":"ok","message":"语音上传成功","voice_path":"xxx"}`

## 配置管理

### 获取配置
- **URL**: `/config`
- **方法**: `GET`
- **描述**: 获取当前配置
- **响应**:
  - 成功: `{"status":"success","message":"获取配置成功","configs":{...}}`

### 保存配置
- **URL**: `/save`
- **方法**: `POST`
- **请求体**:
  ```json
  {
    "config_key": "LISTEN_LIST",
    "config_value": [...],
    "is_update_all": false
  }
  ```
- **响应**:
  - 成功: `{"status":"success","message":"保存配置成功"}`
  - 失败: `{"status":"error","message":"保存配置失败"}`

### 获取所有配置
- **URL**: `/get_all_configs`
- **方法**: `GET`
- **描述**: 获取所有配置分组
- **响应**:
  - 成功: `{"status":"success","message":"获取配置成功","configs":{...}}`

### 获取模型配置
- **URL**: `/get_model_configs`
- **方法**: `GET`
- **描述**: 获取AI模型相关配置
- **响应**:
  - 成功: `{"status":"success","message":"获取模型配置成功","data":{...}}`

### 快速设置保存
- **URL**: `/save_quick_setup`
- **方法**: `POST`
- **描述**: 保存快速设置配置
- **请求体**:
  ```json
  {
    "api_provider": "kourichat",
    "api_key": "your_api_key",
    "model": "kourichat-v3",
    "listen_users": ["用户1", "用户2"]
  }
  ```
- **响应**:
  - 成功: `{"status":"success","message":"保存成功"}`

## 系统管理

### 获取系统信息
- **URL**: `/system_info`
- **方法**: `GET`
- **描述**: 获取系统资源使用情况
- **响应**:
  ```json
  {
    "status": "success",
    "message": "获取系统信息成功",
    "data": {
      "cpu_percent": 0,
      "memory": {
        "total": 0,
        "used": 0,
        "percent": 0
      },
      "disk": {
        "total": 0,
        "used": 0,
        "percent": 0
      },
      "network": {
        "upload": 0,
        "download": 0
      }
    }
  }
  ```

### 检查更新
- **URL**: `/check_update`
- **方法**: `GET`
- **描述**: 检查软件更新
- **响应**:
  - 有更新: `{"status":"success","message":"发现新版本","version":"1.2.3","description":"更新说明"}`
  - 无更新: `{"status":"info","message":"当前已是最新版本"}`

### 确认更新
- **URL**: `/confirm_update`
- **方法**: `POST`
- **描述**: 确认并执行更新
- **响应**:
  - 成功: `{"status":"success","message":"开始更新"}`

### 检查依赖
- **URL**: `/check_dependencies`
- **方法**: `GET`
- **描述**: 检查系统依赖项
- **响应**:
  - 成功: `{"status":"success","message":"依赖检查完成","missing":[]}`
  - 有缺失: `{"status":"warning","message":"发现缺失依赖","missing":["依赖1","依赖2"]}`

### 安装依赖
- **URL**: `/install_dependencies`
- **方法**: `POST`
- **描述**: 安装缺失的依赖项
- **请求体**:
  ```json
  {
    "dependencies": ["依赖1", "依赖2"]
  }
  ```
- **响应**:
  - 成功: `{"status":"success","message":"依赖安装完成"}`

## 资源管理

### 上传背景图片
- **URL**: `/upload_background`
- **方法**: `POST`
- **Content-Type**: `multipart/form-data`
- **表单字段**:
  - background: 图片文件
- **响应**:
  - 成功: `{"status":"success","message":"背景图片更新成功，请重新加载"}`

### 获取背景图片
- **URL**: `/get_background`
- **方法**: `GET`
- **描述**: 获取当前背景图片路径
- **响应**:
  - 成功: `{"status":"success","message":"获取背景图片成功","data":"background_image/background.png"}`

### 获取可用头像
- **URL**: `/get_available_avatars`
- **方法**: `GET`
- **描述**: 获取系统中可用的角色头像列表
- **响应**:
  - 成功: `{"status":"success","message":"获取可用头像成功","avatars":[...]}`

### 加载头像内容
- **URL**: `/load_avatar_content`
- **方法**: `GET`
- **描述**: 获取指定头像的配置内容
- **查询参数**:
  - avatar: 头像目录名
- **响应**:
  - 成功: `{"status":"success","message":"加载头像内容成功","content":"..."}`

### 加载表情包
- **URL**: `/load_avatar_emojis`
- **方法**: `GET`
- **描述**: 获取角色的表情包列表
- **查询参数**:
  - avatar: 头像目录名
- **响应**:
  - 成功: `{"status":"success","message":"加载表情包成功","emojis":[...]}`

### 删除表情包
- **URL**: `/delete_avatar_emojis`
- **方法**: `POST`
- **描述**: 删除角色的表情包
- **请求体**:
  ```json
  {
    "avatar": "头像目录名",
    "emoji_file": "表情包文件名"
  }
  ```
- **响应**:
  - 成功: `{"status":"success","message":"删除表情包成功"}`

### 上传表情包压缩包
- **URL**: `/upload_avatarEmoji_zip`
- **方法**: `POST`
- **Content-Type**: `multipart/form-data`
- **表单字段**:
  - zip_file: 表情包压缩文件
  - avatar: 头像目录名
- **响应**:
  - 成功: `{"status":"success","message":"表情包上传成功"}`

## 机器人管理

### 启动机器人
- **URL**: `/start_bot`
- **方法**: `GET`
- **描述**: 启动聊天机器人服务
- **响应**:
  - 成功: `{"status":"success","message":"机器人已启动"}`
  - 已在运行: `{"status":"info","message":"机器人已在运行中"}`

### 停止机器人
- **URL**: `/stop_bot`
- **方法**: `GET`
- **描述**: 停止聊天机器人服务
- **响应**:
  - 成功: `{"status":"success","message":"机器人已停止"}`
  - 未在运行: `{"status":"info","message":"机器人未在运行"}`

### 获取机器人日志
- **URL**: `/get_bot_logs`
- **方法**: `GET`
- **描述**: 获取机器人运行日志
- **响应**:
  - 成功: `{"status":"success","message":"获取日志成功","logs":[...]}`

### 执行命令
- **URL**: `/execute_command`
- **方法**: `POST`
- **描述**: 在机器人环境中执行命令
- **请求体**:
  ```json
  {
    "command": "命令内容"
  }
  ```
- **响应**:
  - 成功: `{"status":"success","message":"命令执行成功","output":"命令输出"}`

## 任务管理

### 获取任务
- **URL**: `/get_tasks`
- **方法**: `GET`
- **描述**: 获取定时任务列表
- **响应**:
  - 成功: `{"status":"success","message":"获取任务成功","tasks":[...]}`

## 微信相关

### 点击微信按钮
- **URL**: `/click_wechat_buttons`
- **方法**: `POST`
- **描述**: 自动点击微信登录界面的按钮
- **响应**:
  - 成功: `{"status":"success","message":"操作成功"}`

## 系统配置信息

### 服务端口说明
- **配置中心 Web 服务端口**: 8502
  - 用于提供配置中心 Web 界面和相关 API
- **语音服务 API 端口**: 5000
  - 用于文本转语音服务
- **Ollama API 端口**: 11434
  - 用于本地 AI 模型服务 
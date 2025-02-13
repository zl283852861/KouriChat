![ATRI.jpg](data%2Fimages%2Fimg%2FATRI.jpg)

有问题可加群：715616260 

- 一键整合包夸克网盘：https://pan.quark.cn/s/f37d765e1404 提取码：zXpP 推荐转存，项目更新直接下载最新的代码zip。我也能有收益，感谢您的支持！
- 部署项目推荐使用Windows服务器，[雨云优惠通道注册送首月五折券](https://www.rainyun.com/MzE0MTU=_) 
- 获取 DeepSeek API Key，[获取 API Key（15元免费额度）](https://cloud.siliconflow.cn/i/aQXU6eC5)

---

## 简介

简体中文 · [English](./README_EN.md) 

- 已经更换了安全的微信自动化方案，即<code>wxauto</code>，封号可能性几乎没有，稳定性拉满
- My Dream Moments 是一个基于大型语言模型（LLM）的情感陪伴程序，能够接入微信，提供更真实的情感交互体验。内置了 Atri-My dear moments 的 prompt，并且解决了传统人机对话程序一问一答的死板效果，提供沉浸式角色扮演和多轮对话支持。项目名字来源是运行在该程序上的第一个智能体的原作名称+项目价值观混合而来。
- 推荐使用DeepSeek V3 模型。<br>
- [赞助者名单](SponsorList.md)
- [里程碑](MileStone.md)
- [致谢](Thanks.md)<br>
  ![demo.png](data%2Fimages%2Fimg%2Fdemo.png)

---

## 声明

- 本项目仅用于交流学习，LLM发言不代表作者本人立场。prompt所模仿角色版权归属原作者。任何未经许可进行的限制级行为均由使用者个人承担。

---

## 已实现的功能

- [x] 对接微信，沉浸式角色扮演
- [x] 聊天分段响应，消除人机感
- [x] 多轮对话
- [x] 多用户支持
- [x] 由 DeepSeek R1 利用游戏文本生成的 Prompt
- [x] 无需联网的时间感知
- [x] WebUI，方便不理解代码的用户配置项目
- [x] 图像生成
- [x] 异步请求
- [x] 实现群聊
- [x] 表情包
- [x] Ai图片识别，调用kimi
- [x] 实现R1对话
- [x] 实现主动发消息

---

## 待实现功能，期待您的加入

- [ ] 定时任务与智能定时任务
- [ ] 利用 8B 小模型实时生成记忆并定期整理，实现持久记忆
- [ ] 负载均衡
- [ ] 语音功能，暂时发送wav语言文件
- [ ] 完善WebUi
- [ ] 数学公式或者代码实现远程渲染

---


## 如何运行项目

### 1. 前期准备

1. **备用手机/安卓模拟器**  
   - 微信电脑端登录必须有一个移动设备同时登录，因此不能使用您的主要设备。

2. **微信小号**  
   - 可以登录微信电脑版即可。

3. **DeepSeek API Key**  
   - 推荐使用：[获取 API Key（15元免费额度）](https://cloud.siliconflow.cn/i/aQXU6eC5)

---

### 2. 部署项目

1. **克隆本仓库**  

   ```bash
   git clone https://github.com/umaru-233/My-Dream-Moments.git
   ```

2. **安装pip** 

   ```bash
   python -m ensurepip
   ```

3. **安装依赖**  

   ```bash
   pip install -r requirements.txt
   ```

4. **配置<code>src/config/settings.py</code>**  
   修改<code>LISTEN_LIST</code>、<code>DEEPSEEK_BASE_URL</code>和<code>DEEPSEEK_API_KEY</code>。

按需调整<code>MAX_TOKEN</code>、<code>TEMPERATURE</code>和<code>MODEL</code>。如何配置请阅读<code>config.py</code>里的注释。

5. **运行<code>run.py</code>，如果报错请尝试使用Python 3.11版本。**

   ```bash
   python run.py
   ```

6. FAQ:没什么问题是重启解决不了的，如果重启解决不了，请重启


### 3. 如何使用

- **使用微信小号登录微信电脑版**

- **项目运行后，控制台提示**

  ```bash
  初始化成功，获取到已登录窗口：<您的微信昵称>
  开始运行BOT...
  ```

  即可开始监听并调用模型自动回复消息。

## 如果您想修改prompt

- 修改avatars/ATRI/ATRI.md的内容
- 注意：请不要修改与反斜线 <code> \ </code>相关的 prompt，因为它们被用于分段回复消息。

结构说明：

```python
My-Dream-Moments-WeChat-wxauto/
├── src/
│   ├── __init__.py
│   ├── main.py                # 主程序入口
│   ├── config/               
│   │   ├── __init__.py
│   │   └── settings.py        # 配置文件
│   ├── handlers/
│   │   ├── __init__.py 
│   │   ├── message_handler.py # 消息处理
│   │   ├── file_handler.py    # 文件处理
│   │   └── event_handler.py   # 事件处理
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   └── openai_service.py  # OpenAI服务
│   │   ├── wechat_service.py      # 微信服务
│   │   └── db_service.py          # 数据库服务
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py          # 日志工具
│   │   └── helper.py          # 辅助工具
│   ├── webui/                 # Web界面
│   │   ├── __init__.py
│   │   ├── app.py            # Flask应用
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── api.py
│   │   ├── static/
│   │   │   ├── css/
│   │   │   ├── js/
│   │   │   └── images/
│   │   └── templates/
│   │       └── index.html
│   ├── autoupdate/           # 自动更新
│   │   ├── __init__.py
│   │   └── updater.py
│   └── wxauto文件/            # 微信自动化核心文件
│       └── wxauto.py
├── logs/                     # 日志目录
│   ├── error.log
│   └── info.log
├── data/                     # 数据目录
│   ├── database/
│   │   └── mydream.db
│   ├── images/              # 图片存储
│   └── cache/               # 缓存文件
├── requirements.txt          # 项目依赖
├── run.py                    # 运行脚本
├── run_config_web.py         # Web配置运行脚本
├── test.py                   # 测试文件
├── README.md                 # 中文文档
├── README_EN.md             # 英文文档
└── LICENSE                  # 开源许可证
```



## 赞助

此项目欢迎赞助。您的支持对我非常重要！

- 赞助用户如需远程部署或定制 prompt，请联系我。
- E-Mail: yangchenglin2004@foxmail.com 
- Bilibili: [umaru今天吃什么](https://space.bilibili.com/209397245)
- 感谢您的支持与使用！!<br>
  ![qrcode.jpg](data%2Fimages%2Fimg%2Fqrcode.jpg)

## 请给我Star，这对我很重要TvT

- [![Star History Chart](https://api.star-history.com/svg?repos=umaru-233/My-Dream-Moments&type=Timeline)](https://star-history.com/?spm=a2c6h.12873639.article-detail.8.7b9d359dJmTgdE#umaru-233/My-Dream-Moments&Timeline)

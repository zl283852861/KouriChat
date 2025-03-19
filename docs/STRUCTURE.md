# KouriChat 项目结构

本文档描述了KouriChat项目的目录结构，方便开发者理解项目组织。

## 主要目录结构

```
KouriChat/
├── data/                   # 数据存储目录
│   ├── avatars/            # 头像数据
│   ├── base/               # 基础数据
│   ├── images/             # 图片数据
│   ├── memory/             # 记忆数据
│   └── voices/             # 语音数据
├── docs/                   # 文档目录
│   ├── KouriChat_v2.0_API_Documentation.md # API文档
│   ├── LICENSE             # 许可证
│   ├── README.md           # 中文README
│   ├── README_EN.md        # 英文README
│   ├── STRUCTURE.md        # 项目结构文档（本文件）
│   └── Thanks.md           # 致谢文档
├── logs/                   # 日志目录
│   └── automation/         # 自动化日志
├── scripts/                # 脚本目录
│   ├── query_generator.py  # 查询生成器
│   ├── query_optimizer.py  # 查询优化器
│   ├── run.bat             # Windows启动批处理
│   ├── run_config_web.py   # 配置Web界面
│   ├── test.py             # 测试脚本
│   └── 运行QQNonebot后端.bat  # QQ机器人启动脚本
├── screenshot/             # 截图目录
├── src/                    # 源代码目录
│   ├── api_client/         # API客户端
│   ├── AutoTasker/         # 自动任务管理
│   ├── autoupdate/         # 自动更新
│   ├── config/             # 配置文件
│   ├── handlers/           # 消息处理器
│   ├── memories/           # 记忆管理
│   ├── Plugins/            # 插件系统
│   ├── services/           # 服务接口
│   ├── utils/              # 工具函数
│   ├── Wechat_Login_Clicker/ # 微信登录辅助
│   ├── webui/              # Web界面
│   ├── avatar_manager.py   # 头像管理器
│   ├── main.py             # 主程序入口
│   └── __init__.py         # 包初始化
├── tests/                  # 测试目录
├── tools/                  # 工具目录
│   ├── embedding_service.py # 嵌入服务
│   ├── logger_config.py     # 日志配置
│   └── oneBotMain.py        # OneBot主程序
├── .env                    # 环境变量
├── .env.kouri              # Kouri环境变量
├── .gitattributes          # Git属性
├── .gitignore              # Git忽略文件
├── requirements.txt        # 依赖清单
├── run.py                  # 主启动脚本
└── version.json            # 版本信息
```

## 目录说明

### data/
存储运行时数据，包括用户数据、图片、语音等内容。

### docs/
项目文档，包括API文档、许可证和项目说明等。

### logs/
日志文件目录，用于存储程序运行日志。

### scripts/
各种脚本文件，包括启动脚本、配置脚本和测试脚本等。

### src/
项目源代码目录，包含所有核心功能实现。

### tests/
测试代码目录，用于单元测试和集成测试。

### tools/
辅助工具目录，包含各种独立功能的工具程序。

## 使用说明

- 运行 `run.py` 启动主程序
- 运行 `run.py --debug` 在调试模式下启动
- 使用 `scripts/run.bat` 在Windows环境下快速启动
- 配置文件位于 `src/config/` 目录 
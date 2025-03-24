# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 添加需要包含的数据文件
added_files = [
    # ('assets', 'assets'),  # 如果存在，取消注释
    # ('ui/images', 'ui/images'),  # 如果存在，取消注释
    ('ui', 'ui'),  # 包含整个ui文件夹
    ('core', 'core'),  # 包含核心模块
    ('widgets', 'widgets'),  # 包含自定义组件
    ('api', 'api'),  # 包含API相关模块
]

# 排除不需要打包的文件
excluded_files = [
    'config.json',
    'api_config.json',
    '*.pyc',
    '__pycache__',
    '*.log'
]

# 创建运行时钩子文件 - 使用显式编码
with open('runtime_hook.py', 'w', encoding='utf-8') as f:
    f.write("""# -*- coding: utf-8 -*-
import os
import sys

# 确保当前目录在路径中
if getattr(sys, 'frozen', False):
    # 运行在打包环境中
    bundle_dir = sys._MEIPASS
    # 将bundle_dir添加到sys.path
    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)
""")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,  # 添加数据文件
    hiddenimports=[
        'customtkinter',
        'customtkinter.windows',
        'customtkinter.windows.widgets',
        'customtkinter.windows.widgets.appearance_mode',
        'customtkinter.windows.widgets.scaling',
        'customtkinter.windows.widgets.core_rendering',
        'customtkinter.windows.widgets.theme',
        'PIL',
        'requests',
        'json',
        'threading',
        'webbrowser',
        'os',
        'sys',
        'tkinter',
        'traceback',
        'ui.theme_transition',  # 明确添加 theme_transition 模块
        'ui.transition',        # 添加相关的 transition 模块
        'ui.theme',             # 添加主题模块
        'core.theme_manager',   # 添加主题管理器
        'math',                 # theme_transition.py 使用了 math 模块
        'queue'                 # theme_transition.py 使用了 queue 模块
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],  # 添加运行时钩子
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 排除不需要的文件
for file in excluded_files:
    a.datas = [x for x in a.datas if not x[0].endswith(file)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Kourichat工具箱',
    debug=False,  # 关闭调试模式
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 关闭控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

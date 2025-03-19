import os

# 定义目录结构
directories = [
    "core",
    "api",
    "widgets",
    "themes",
    "assets",
    "assets/images"
]

# 创建目录
for directory in directories:
    os.makedirs(directory, exist_ok=True)
    # 在每个目录中创建一个空的__init__.py文件
    with open(f"{directory}/__init__.py", "w") as f:
        pass

print("项目目录结构已创建完成！") 
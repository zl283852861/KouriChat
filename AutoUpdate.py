import os
import requests
import zipfile
import shutil
import json

# 需要跳过的文件和文件夹（不会被更新）
SKIP_FILES = [
    "AutoUpdate.py",#更新脚本
    "chat_history.db",#聊天记录
    os.path.join("prompts", "ATRI.md"),#角色文件夹
    "custom_config.py",#自定义配置文件
    os.path.join("custom_folder", "custom_file.txt")#自定义文件夹
]

def check_and_update():
    print("开始检查更新...")
    
    # 定义临时目录(要先定义，不然会报错)
    temp_dir = "temp_update"
    
    try:
        # GitHub API endpoint
        api_url = "https://api.github.com/repos/umaru-233/My-Dream-Moments/releases/latest"
        
        # 获取最新release信息
        response = requests.get(api_url)
        response.raise_for_status()  # 如果状态码不是200，将引发异常
        
        release_data = response.json()
        
        # 获取zip下载链接
        zip_url = release_data['zipball_url']
        
        # 创建临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)  # 如果目录已存在，先删除
        os.makedirs(temp_dir)
            
        # 下载zip文件
        print("下载更新文件...")
        zip_path = os.path.join(temp_dir, "update.zip")
        response = requests.get(zip_url)
        with open(zip_path, 'wb') as f:
            f.write(response.content)
            
        # 解压文件
        print("解压文件...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        # 获取解压后的目录名（通常是仓库名-分支名）
        extracted_dir = None
        for item in os.listdir(temp_dir):
            if os.path.isdir(os.path.join(temp_dir, item)) and item.startswith("umaru-233-My-Dream-Moments"):
                extracted_dir = item
                break
                
        if not extracted_dir:
            print("无法找到解压后的目录")
            return
            
        # 复制新文件，跳过指定文件
        print("更新文件...")
        src_dir = os.path.join(temp_dir, extracted_dir)
        for root, dirs, files in os.walk(src_dir):
            # 计算目标路径
            relative_path = os.path.relpath(root, src_dir)
            target_dir = relative_path if relative_path != "." else ""
            
            # 创建目标目录
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir)
                
            # 复制文件
            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(target_dir, file) if target_dir else file
                
                # 检查是否在跳过列表中
                skip = False
                for skip_path in SKIP_FILES:
                    if dst_file == skip_path:
                        print(f"跳过文件: {dst_file}")
                        skip = True
                        break
                
                if skip:
                    continue
                    
                shutil.copy2(src_file, dst_file)
                
        # 清理临时文件
        print("清理临时文件...")
        shutil.rmtree(temp_dir)
        
        print("更新完成！")
        
    except requests.exceptions.RequestException as e:
        print(f"网络请求错误: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {str(e)}")
    except Exception as e:
        print(f"更新过程中出现错误: {str(e)}")
    finally:
        # 确保清理临时目录
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"清理临时文件时出现错误: {str(e)}")

if __name__ == "__main__":
    check_and_update() 

"""
记忆文件测试脚本 - 检查当前记忆文件格式
"""
import os
import json
import sys
from datetime import datetime

def get_memory_path(root_dir):
    """获取记忆文件路径"""
    memory_dir = os.path.join(root_dir, "data", "memory")
    return os.path.join(memory_dir, "memory.json")

def read_memory_file(memory_path):
    """读取记忆文件"""
    try:
        if not os.path.exists(memory_path):
            print(f"记忆文件不存在: {memory_path}")
            return None
            
        with open(memory_path, 'r', encoding='utf-8') as f:
            memory_data = json.load(f)
            
        return memory_data
    except Exception as e:
        print(f"读取记忆文件失败: {str(e)}")
        return None

def show_memory_format(memory_data):
    """展示记忆格式"""
    if not memory_data:
        print("没有记忆数据")
        return
        
    memories = memory_data.get("memories", {})
    print(f"共找到 {len(memories)} 条记忆")
    
    # 打印前5条记忆的格式
    count = 0
    for key, value in memories.items():
        print("\n===== 记忆项 =====")
        print(f"键: {key}")
        print(f"值: {value}")
        
        count += 1
        if count >= 5:
            break
            
    # 打印embeddings数量
    embeddings = memory_data.get("embeddings", {})
    print(f"\n嵌入向量数量: {len(embeddings)}")

def write_test_memory():
    """写入测试记忆（使用新格式）"""
    # 获取项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(script_dir))
    memory_path = get_memory_path(root_dir)
    
    # 读取现有记忆
    memory_data = read_memory_file(memory_path)
    if not memory_data:
        memory_data = {"memories": {}, "embeddings": {}}
    
    # 获取当前时间
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 创建新格式的测试记忆
    test_memory = f"[{current_time}]对方：这是一条测试消息 ||| 你：这是一条测试回复，使用新的格式存储"
    
    # 添加到记忆数据
    memory_data["memories"][test_memory] = test_memory
    
    # 保存记忆数据
    try:
        with open(memory_path, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)
            
        print(f"成功写入测试记忆到: {memory_path}")
    except Exception as e:
        print(f"写入测试记忆失败: {str(e)}")

def main():
    """主函数"""
    # 获取项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(script_dir))
    
    print(f"项目根目录: {root_dir}")
    
    # 获取记忆文件路径
    memory_path = get_memory_path(root_dir)
    print(f"记忆文件路径: {memory_path}")
    
    # 读取记忆文件
    memory_data = read_memory_file(memory_path)
    
    # 展示记忆格式
    show_memory_format(memory_data)
    
    # 如果命令行参数包含 --write，则写入测试记忆
    if len(sys.argv) > 1 and sys.argv[1] == "--write":
        write_test_memory()

if __name__ == "__main__":
    main() 
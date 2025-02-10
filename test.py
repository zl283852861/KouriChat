import os
import shutil

def cleanup_wxauto_files():
    """
    清理当前目录下的wxauto文件夹中的文件和子文件夹
    """
    try:
        # 当前目录下的wxauto文件夹路径
        wxauto_dir = os.path.join(os.getcwd(), "wxauto文件")
        print(f"正在检查目录: {wxauto_dir}")
        if not os.path.exists(wxauto_dir):
            print("wxauto文件夹不存在，无需清理")
            return
            
        files = os.listdir(wxauto_dir)
        if not files:
            print("wxauto文件夹为空，无需清理")
            return
            
        deleted_count = 0
        for file in files:
            try:
                file_path = os.path.join(wxauto_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    # print(f"已删除文件: {file_path}")
                    deleted_count += 1
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    # print(f"已删除文件夹: {file_path}")
                    deleted_count += 1
            except Exception as e:
                # print(f"删除失败 {file_path}: {str(e)}")
                continue
                
        print(f"清理完成，共删除 {deleted_count} 个文件/文件夹")
    except Exception as e:
        print(f"清理wxauto文件夹时发生错误: {str(e)}")

def main():
    cleanup_wxauto_files()

if __name__ == "__main__":
    main()
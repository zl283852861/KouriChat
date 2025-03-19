"""
文件处理模块
负责文件的读取、保存和管理
"""

import os
import logging
import shutil
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

logger = logging.getLogger('main')

class FileHandler:
    """文件处理器，负责各种文件操作"""
    
    def __init__(self):
        self.temp_files = []
        
    def read_file(self, file_path: str) -> Optional[str]:
        """读取文件内容"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            logger.error(f"读取文件失败: {str(e)}")
            return None
            
    def write_file(self, file_path: str, content: str) -> bool:
        """写入文件内容"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"写入文件失败: {str(e)}")
            return False
            
    def append_file(self, file_path: str, content: str) -> bool:
        """追加文件内容"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"追加文件失败: {str(e)}")
            return False
            
    def delete_file(self, file_path: str) -> bool:
        """删除文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
            return False
            
    def copy_file(self, source_path: str, target_path: str) -> bool:
        """复制文件"""
        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            shutil.copy2(source_path, target_path)
            return True
        except Exception as e:
            logger.error(f"复制文件失败: {str(e)}")
            return False
            
    def create_temp_file(self, content: str, prefix: str = "temp_", suffix: str = ".txt") -> Optional[str]:
        """创建临时文件"""
        try:
            import tempfile
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, prefix=prefix, suffix=suffix, mode='w', encoding='utf-8')
            temp_file.write(content)
            temp_file.close()
            
            self.temp_files.append(temp_file.name)
            return temp_file.name
        except Exception as e:
            logger.error(f"创建临时文件失败: {str(e)}")
            return None
            
    def cleanup_temp_files(self) -> None:
        """清理临时文件"""
        for file_path in self.temp_files[:]:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.temp_files.remove(file_path)
            except Exception as e:
                logger.error(f"清理临时文件失败: {str(e)}")
                
    def __del__(self):
        """析构函数，确保临时文件被清理"""
        self.cleanup_temp_files()
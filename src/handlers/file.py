import os
import shutil
from typing import Optional, List, Dict, Union
from pathlib import Path

from docx import Document
import pandas as pd
from io import StringIO

class FileHandler:
    """文件处理器类
    
    负责处理文件的移动、类型识别和内容读取等操作。
    该类提供了统一的文件操作接口，支持多种文件格式的处理。
    """
    
    # 文件类型映射
    FILE_TYPES: Dict[str, str] = {
        '.txt': 'text',
        '.doc': 'word',
        '.docx': 'word',
        '.xls': 'excel',
        '.xlsx': 'excel',
        '.xlsm': 'excel',
        '.ppt': 'powerpoint', # 暂未支持
        '.pptx': 'powerpoint',
        '.pdf': 'pdf', # 暂未支持
    }
    
    def __init__(self, root_dir: Optional[str] = None):
        """初始化FileHandler
        
        Args:
            root_dir: 项目根目录路径，如果不提供则自动获取
        """
        if root_dir is None:
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.root_dir = current_dir
        else:
            self.root_dir = root_dir
            
        self.files_dir = os.path.join(self.root_dir, "files")
        os.makedirs(self.files_dir, exist_ok=True)
    
    def move_to_files_dir(self, file_path: str) -> str:
        """将文件移动到项目的files目录下
        
        Args:
            file_path: 源文件路径
            
        Returns:
            str: 移动后的目标文件路径
            
        Raises:
            FileNotFoundError: 源文件不存在
            OSError: 文件移动失败
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"源文件不存在: {file_path}")
        
        try:
            file_name = os.path.basename(file_path)
            target_path = os.path.join(self.files_dir, file_name)
            
            # 如果目标文件已存在，添加数字后缀
            counter = 1
            while os.path.exists(target_path):
                name, ext = os.path.splitext(file_name)
                target_path = os.path.join(self.files_dir, f"{name}_{counter}{ext}")
                counter += 1
            
            shutil.move(file_path, target_path)
            return target_path
        except Exception as e:
            raise OSError(f"文件移动失败: {str(e)}")
    
    def get_file_type(self, file_path: str) -> Optional[str]:
        """获取文件类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[str]: 文件类型，如果类型未知则返回None
        """
        file_extension = os.path.splitext(file_path)[1].lower()
        return self.FILE_TYPES.get(file_extension)
    
    def read_file_content(self, file_path: str) -> str:
        """读取文件内容
        
        支持txt、word和excel格式的文件读取
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件内容
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不支持的文件类型
            Exception: 文件读取失败
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        file_type = self.get_file_type(file_path)
        if file_type is None:
            raise ValueError(f"不支持的文件类型: {file_path}")
        
        try:
            if file_type == 'text':
                return self._read_text_file(file_path)
            elif file_type == 'word':
                return self._read_word_file(file_path)
            elif file_type == 'excel':
                return self._read_excel_file(file_path)
            else:
                raise ValueError(f"暂不支持读取该类型文件: {file_type}")
        except Exception as e:
            raise Exception(f"文件读取失败: {str(e)}")
    
    def _read_text_file(self, file_path: str) -> str:
        """读取文本文件内容"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，使用二进制模式读取
        with open(file_path, "rb") as f:
            return str(f.read())
    
    def _read_word_file(self, file_path: str) -> str:
        """读取Word文档内容"""
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    
    def _read_excel_file(self, file_path: str) -> str:
        """读取Excel文件内容"""
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        
        if not sheet_names:
            return "Excel文件中没有工作表"
        
        all_data = []
        for sheet in sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet)
            all_data.append(f"工作表: {sheet}\n{df.to_csv(index=False)}")
        
        return "\n\n".join(all_data)
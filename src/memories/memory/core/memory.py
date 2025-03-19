import os
import json
import logging
from functools import wraps
from typing import List, Dict, Any, Callable, Optional, Tuple

logger = logging.getLogger('main')

class Memory:
    """
    记忆管理类，用于存储和检索键值对记忆
    实现了单例模式，支持钩子函数用于记忆变更通知
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None or not kwargs.get('singleton', True):
            cls._instance = super(Memory, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_path: str = '../config/memory.json', singleton: bool = True):
        # 避免重复初始化单例
        if hasattr(self, 'initialized') and self.initialized and singleton:
            return
            
        # 使用 super().__setattr__ 直接设置所有属性，避免触发 __getattr__
        super().__setattr__('config_path', config_path)
        super().__setattr__('settings', {})
        super().__setattr__('_memory_hooks', [])
        super().__setattr__('_in_hook', False)  # 钩子执行状态标志
        super().__setattr__('initialized', True)
        super().__setattr__('logger', logger)
        
        # 加载配置
        self.load_config()
        self.logger.debug(f"记忆系统初始化完成，配置路径: {config_path}")

    def load_config(self) -> None:
        """加载记忆配置文件"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as file:
                    loaded_data = json.load(file)
                    if loaded_data is not None:
                        self.settings = loaded_data
                    else:
                        self.settings = {}
                        self.logger.warning(f"配置文件 {self.config_path} 为空或格式错误，已初始化为空字典")
            else:
                # 确保目录存在
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                # 创建空配置文件
                with open(self.config_path, 'w', encoding='utf-8') as file:
                    json.dump({}, file)
                self.settings = {}
                self.logger.info(f"配置文件 {self.config_path} 不存在，已创建空配置文件")
        except Exception as e:
            self.logger.error(f"加载记忆配置失败: {str(e)}")
            self.settings = {}  # 出错时使用空字典作为回退

    def save_config(self) -> bool:
        """保存记忆配置到文件，返回是否成功"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as file:
                json.dump(self.settings, file, indent=4, ensure_ascii=False)
            self.logger.debug(f"记忆配置已保存到 {self.config_path}")
            return True
        except Exception as e:
            self.logger.error(f"保存记忆配置失败: {str(e)}")
            return False

    def save(self) -> bool:
        """save方法，作为save_config的别名，用于兼容性"""
        return self.save_config()

    def __getattr__(self, key: str) -> Any:
        """通过属性访问方式获取记忆内容"""
        # 避免递归：直接访问 self.settings，而不是通过 self.__getattr__
        if key in super().__getattribute__('settings'):
            return super().__getattribute__('settings')[key]
        raise AttributeError(f"'Memory' object has no attribute '{key}'")

    def __setattr__(self, key: str, value: Any) -> None:
        """通过属性设置方式存储记忆内容"""
        # 处理内部属性
        if key in ['config_path', 'settings', 'initialized', '_memory_hooks', '_in_hook', 'logger']:
            super().__setattr__(key, value)
        # 外部属性通过 set 方法处理
        else:
            self.set(key, value)

    def __setitem__(self, key: str, value: Any) -> None:
        """通过字典方式设置记忆内容"""
        self.set(key, value)

    def __getitem__(self, key: str) -> Any:
        """通过字典方式获取记忆内容"""
        return self.settings.get(key)

    def set(self, key: str, value: Any) -> None:
        """设置记忆内容，并触发相关钩子函数"""
        if not isinstance(key, str):
            key = str(key)
            
        # 更新记忆内容
        self.settings[key] = value

        # 触发记忆钩子（带防重复触发保护）
        if not self._in_hook:
            self._in_hook = True
            try:
                for hook in self._memory_hooks:
                    try:
                        hook(key, value)
                    except Exception as e:
                        self.logger.error(f"执行记忆钩子函数时出错: {str(e)}")
            finally:
                self._in_hook = False

    def get(self, key: str, default: Any = None) -> Any:
        """获取记忆内容，提供默认值"""
        return self.settings.get(key, default)

    def get_key_value_pairs(self) -> List[str]:
        """获取所有键值对，格式为 key:value 的字符串列表"""
        return [f"{key}:{value}" for key, value in self.settings.items()]

    def get_all_items(self) -> Dict[str, Any]:
        """获取所有记忆项目的字典副本"""
        return self.settings.copy()

    def add_memory_hook(self, func: Callable[[str, Any], None]) -> Callable:
        """
        添加记忆钩子函数，当记忆内容变更时触发
        
        Args:
            func: 钩子函数，接收 key 和 value 两个参数
            
        Returns:
            包装后的钩子函数
        """
        @wraps(func)
        def wrapper(key, value):
            return func(key, value)

        self._memory_hooks.append(wrapper)
        return wrapper

    def remove_memory_hook(self, func: Callable) -> bool:
        """
        移除记忆钩子函数
        
        Args:
            func: 要移除的钩子函数
            
        Returns:
            是否成功移除
        """
        if func in self._memory_hooks:
            self._memory_hooks.remove(func)
            return True
        return False

    def clear(self) -> None:
        """清空所有记忆内容"""
        self.settings = {}
        self.logger.info("已清空所有记忆内容")
        self.save_config()


if __name__ == '__main__':
    # 测试代码
    memory = Memory(config_path="memory_test.json")
    memory["hello"] = "world"
    print(memory.settings)
    assert memory["hello"] == "world"
    
    # 测试钩子函数
    @memory.add_memory_hook
    def test_hook(key, value):
        print(f"Hook called with {key}={value}")
    
    memory["test"] = "hook"

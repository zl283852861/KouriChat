"""
记忆模块测试文件
"""
import os
import sys
import asyncio
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test')

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入记忆管理器
from src.handlers.memory_manager import (
    init_memory, remember, retrieve, is_important,
    get_memory_processor, get_memory_stats,
    clear_memories, save_memories, init_rag_from_config, get_rag
)

async def test_memory_basic():
    """测试基本记忆功能"""
    logger.info("=== 测试基本记忆功能 ===")
    
    # 获取当前目录
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # 初始化记忆
    memory_processor = init_memory(root_dir)
    
    if not memory_processor:
        logger.error("初始化记忆处理器失败")
        return False
    
    logger.info("记忆处理器初始化成功")
    
    # 清空记忆
    clear_memories()
    logger.info("清空记忆成功")
    
    # 记住对话
    user_message = "我的生日是5月1日"
    assistant_response = "好的，我记住了你的生日是5月1日"
    
    result = await remember(user_message, assistant_response)
    logger.info(f"记忆结果: {result}")
    
    # 检索记忆
    query = "我的生日"
    memories = await retrieve(query)
    logger.info(f"检索结果: {memories}")
    
    # 判断重要性
    importance = await is_important("请记住我的电话号码是13800138000")
    logger.info(f"重要性判断结果: {importance}")
    
    # 保存记忆
    save_memories()
    logger.info("保存记忆成功")
    
    # 获取记忆统计
    stats = get_memory_stats()
    logger.info(f"记忆统计: {stats}")
    
    return True

async def test_rag():
    """测试RAG功能"""
    logger.info("=== 测试RAG功能 ===")
    
    # 获取当前目录
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    config_path = os.path.join(root_dir, "src", "config", "config.yaml")
    
    # 初始化RAG
    rag = init_rag_from_config(config_path)
    
    if not rag:
        logger.warning("初始化RAG失败，跳过RAG测试")
        return False
    
    logger.info("RAG初始化成功")
    
    # 查询RAG
    query = "测试查询"
    results = await rag.query(query, 3)
    
    if results:
        logger.info(f"查询结果数量: {len(results)}")
        logger.info(f"第一条结果: {results[0]}")
    else:
        logger.info("没有找到查询结果")
    
    return True

async def main():
    """主函数"""
    logger.info("开始测试记忆模块")
    
    # 测试基本记忆功能
    basic_result = await test_memory_basic()
    
    # 测试RAG功能
    rag_result = await test_rag()
    
    logger.info("测试完成")
    logger.info(f"基本记忆功能测试结果: {'成功' if basic_result else '失败'}")
    logger.info(f"RAG功能测试结果: {'成功' if rag_result else '失败'}")

if __name__ == "__main__":
    asyncio.run(main()) 
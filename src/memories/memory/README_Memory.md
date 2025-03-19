# 记忆系统优化

本项目对RAG记忆系统进行了全面优化，提高了记忆检索与存储的效率和稳定性。

## 主要优化内容

### 1. 记忆核心类优化 (Memory)

- 增强了单例模式实现，避免重复初始化
- 添加了完整的类型注解，提高代码可读性和IDE支持
- 改进了配置加载和保存逻辑，增加错误处理
- 优化钩子函数机制，添加移除钩子的功能
- 添加更完善的日志系统

### 2. 记忆处理器优化 (MemoryHandler)

- 重构类初始化逻辑，采用模块化方法
- 将大型方法拆分为更小更专注的函数
- 增强错误处理和容错能力
- 优化检索逻辑，提高相关记忆的获取速度
- 改进记忆清理流程，去除冗余信息
- 添加定期去重机制，确保记忆质量

### 3. 性能优化

- 使用异步检索，减少记忆查询响应时间
- 添加超时控制，避免长时间阻塞
- 实现更高效的混合嵌入模型，结合在线API和本地模型
- 优化了记忆清理算法，提高压缩率

### 4. 稳定性增强

- 全面提升错误处理机制
- 增加组件状态检查，防止空引用错误
- 添加日志记录，便于问题排查
- 实现备用机制，在主要组件失败时提供回退方案

## 系统架构

记忆系统由以下主要组件构成：

1. **核心记忆类** (Memory)：提供基础的键值对存储和检索功能
2. **短期记忆** (ShortTermMemory)：存储近期对话，可快速检索
3. **长期记忆** (LongTermMemory)：存储重要信息，定期从短期记忆中提取
4. **关键记忆** (KeyMemory)：存储特别重要的信息，优先级最高
5. **RAG检索系统**：基于语义相似度进行记忆检索

## 使用方法

记忆处理器在main.py中初始化：

```python
memory_handler = MemoryHandler(
    root_dir=root_dir,
    api_key=config.llm.api_key,
    base_url=config.llm.base_url,
    model=config.llm.model,
    max_token=config.llm.max_tokens,
    temperature=config.llm.temperature,
    max_groups=config.behavior.context.max_groups,
    bot_name=ROBOT_WX_NAME,
    llm=deepseek
)
```

记忆检索示例：

```python
memories = memory_handler.get_relevant_memories("你喜欢什么颜色？", user_id="user123")
```

添加记忆示例：

```python
memory_handler.add_short_memory("你喜欢什么颜色？", "我喜欢蓝色", user_id="user123")
```

检查重要记忆：

```python
is_important = memory_handler.check_important_memory("记住我喜欢红色", user_id="user123")
# 添加命令处理部分，包含download_model命令
@bot.command("download_model", "下载本地备用嵌入模型")
def download_model_cmd():
    try:
        # 优先检查ShortTermMemory实例
        from src.memories.short_term_memory import ShortTermMemory
        stm = ShortTermMemory.get_instance()
        if hasattr(stm, 'command_download_model'):
            return stm.command_download_model()
        
        # 检查是否有RAG嵌入模型实例
        from src.memories.memory.core.rag import RAG
        rag_instance = RAG()
        if rag_instance.embedding_model and hasattr(rag_instance.embedding_model, 'download_model_web_cmd'):
            return rag_instance.embedding_model.download_model_web_cmd()
        
        # 如果没有直接实例或不是混合模型，尝试创建一个新的模型并下载
        from src.memories.memory.core.rag import HybridEmbeddingModel, OnlineEmbeddingModel
        
        # 从配置获取信息
        from src.config import config
        
        api_key = config.rag.api_key or config.llm.api_key
        base_url = config.rag.base_url or config.llm.base_url
        embedding_model_name = config.rag.embedding_model or "text-embedding-3-large"
        local_model_path = config.rag.local_embedding_model_path or "paraphrase-multilingual-MiniLM-L12-v2"
        
        # 创建临时模型实例
        api_model = OnlineEmbeddingModel(
            api_key=api_key,
            base_url=base_url,
            model_name=embedding_model_name
        )
        
        hybrid_model = HybridEmbeddingModel(
            api_model=api_model,
            local_model_path=local_model_path,
            auto_download=True
        )
        
        return "本地备用模型下载任务已完成"
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"下载模型出错: {str(e)}\n详细错误: {error_details}" 
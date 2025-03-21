# 添加命令处理部分，包含download_model命令
from src.config.rag_config import config
from src.handlers.memories.core.rag import HybridEmbeddingModel, OnlineEmbeddingModel, LocalEmbeddingModel

@bot.command("initialize_local_model", "初始化本地嵌入模型")
def download_model_cmd():
    """
    初始化本地嵌入模型，用于RAG记忆系统
    """
    try:
        local_model_path = config.rag.local_embedding_model_path or "paraphrase-multilingual-MiniLM-L12-v2"
        
        # 直接初始化本地模型
        try:
            local_model = LocalEmbeddingModel(local_model_path)
            # 测试嵌入功能
            test_embedding = local_model.embed(["测试嵌入功能"])
            embedding_dim = len(test_embedding[0])
            
            # 更新配置，启用本地模型
            from src.run_config_web import update_config_value
            import json
            
            config_data = {}
            with open("src/config/config.yaml", "r", encoding="utf-8") as f:
                import yaml
                config_data = yaml.safe_load(f)
            
            # 更新本地模型启用状态
            update_config_value(config_data, "LOCAL_MODEL_ENABLED", True)
            
            # 保存配置
            with open("src/config/config.yaml", "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, allow_unicode=True)
            
            return f"本地模型初始化成功！模型维度: {embedding_dim}\n模型路径: {local_model_path}\n系统已自动更新配置，启用本地模型。"
        except Exception as e:
            return f"本地模型初始化失败: {str(e)}\n请检查模型路径是否正确，可能需要先下载模型文件。"
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"初始化模型出错: {str(e)}\n详细错误: {error_details}" 
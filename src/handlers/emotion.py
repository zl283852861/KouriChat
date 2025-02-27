"""
感情处理模块
负责处理感情相关功能，包括:
- 文本正负向识别
- 文本感情七维构建
- 文本感情强烈程度评分
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import pandas as pd
import jieba
import math
import numpy as np
from collections import Counter
from src.services.ai.embedding import EmbeddingModelAI
from tenacity import retry, stop_after_attempt, wait_exponential, wait_fixed, retry_if_exception_type

# 标点符号常量
PUNCTUATION = {'，', '。', '！', '？', '；', '：', '、', ',', '.', '!', '?', ';', ':'}

def load_word_list(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        print(f"未找到词表文件: {file_path}")
        return set()

# 加载词表
BASE_DIR = Path(__file__).parent
NEGATIVE_WORDS = load_word_list(BASE_DIR/'emodata/否定词表.txt')
DEGREE_ADVERBS = load_word_list(BASE_DIR/'emodata/程度副词.txt')
POSITIVE_WORDS = load_word_list(BASE_DIR/'emodata/正面情绪词.txt')
NEGATIVE_WORDS_EXT = load_word_list(BASE_DIR/'emodata/负面情绪词.txt')

# 情感分类映射
CATEGORY_MAPPING = {
    'PA': ('joy', 'positive'), 'PE': ('joy', 'positive'),
    'PD': ('like', 'positive'), 'PH': ('like', 'positive'),
    'PG': ('like', 'positive'), 'PB': ('like', 'positive'),
    'PK': ('like', 'positive'), 'PC': ('surprise', 'positive'),
    'NA': ('anger', 'negative'), 'NB': ('anger', 'negative'),
    'NJ': ('depress', 'negative'), 'NH': ('depress', 'negative'),
    'PF': ('depress', 'negative'), 'NI': ('fear', 'negative'),
    'NC': ('fear', 'negative'), 'NG': ('fear', 'negative'),
    'NE': ('dislike', 'negative'), 'ND': ('dislike', 'negative'),
    'NK': ('dislike', 'negative'), 'NL': ('dislike', 'negative'),
}
class SentimentAnalyzer:
    def __init__(self, hybrid_mode=True):
        self._hybrid_mode = hybrid_mode
        self.emotion_dict = {}
        self.embedding_model = None
        self._init_components()
        
    def _init_components(self):
        """初始化组件并处理失败情况"""
        # 加载情感词典
        self._load_emotion_dictionary()
        
        # 尝试初始化嵌入模型
        if self._hybrid_mode:
            try:
                # 维度参数（1024是支持的选项之一）
                self.embedding_model = EmbeddingModelAI(dimension=1024)
                if not self.embedding_model.available:
                    print("混合模式不可用，自动切换到规则模式")
                    self._hybrid_mode = False
            except Exception as e:
                print(f"混合模式初始化失败: {str(e)}，切换到规则模式")
                self._hybrid_mode = False

    def analyze(self, text):
        """自动回退的核心分析方法"""
        emotion_result = self._analyze_emotion(text)
        
        if self._hybrid_mode and self.embedding_model:
            try:
                embedding = self.embedding_model.get_embeddings(text)
                if embedding is not None:
                    emotion_result = self._enhance_with_embedding(emotion_result, embedding)
                else:
                    print("获取嵌入失败，使用规则模式结果")
            except Exception as e:
                print(f"嵌入处理异常: {str(e)}，使用规则模式结果")
                self._hybrid_mode = False

        # 综合评分计算
        intensity = emotion_result['emotion_info']['intensity']
        base_score = emotion_result['emotion_info']['base_score']
        adjusted_score = base_score * (1 + math.exp(2 * intensity - 1))
        final_score = max(min(adjusted_score, 5), -5)
        
        return {
            **emotion_result,
            'sentiment_score': round(final_score, 2),
            'mode': 'hybrid' if self._hybrid_mode else 'rule'
        }
# 情感分类映射
CATEGORY_MAPPING = {
    'PA': ('joy', 'positive'), 'PE': ('joy', 'positive'),
    'PD': ('like', 'positive'), 'PH': ('like', 'positive'),
    'PG': ('like', 'positive'), 'PB': ('like', 'positive'),
    'PK': ('like', 'positive'), 'PC': ('surprise', 'positive'),
    'NA': ('anger', 'negative'), 'NB': ('anger', 'negative'),
    'NJ': ('depress', 'negative'), 'NH': ('depress', 'negative'),
    'PF': ('depress', 'negative'), 'NI': ('fear', 'negative'),
    'NC': ('fear', 'negative'), 'NG': ('fear', 'negative'),
    'NE': ('dislike', 'negative'), 'ND': ('dislike', 'negative'),
    'NK': ('dislike', 'negative'), 'NL': ('dislike', 'negative'),
}
class SentimentAnalyzer:
    def __init__(self, hybrid_mode=False):
        self.hybrid_mode = hybrid_mode
        self.emotion_dict = {}
        self._load_emotion_dictionary()
        self.embedding_model = EmbeddingModelAI() if hybrid_mode else None

    def analyze(self, text):
        """核心分析方法"""
        emotion_result = self._analyze_emotion(text)
        
        if self.hybrid_mode:
            try:
                embedding = self.embedding_model.get_embeddings(text)
                if embedding:
                    emotion_result = self._enhance_with_embedding(emotion_result, embedding)
            except Exception as e:
                print(f"嵌入模型异常: {str(e)}")

        # 综合评分计算
        intensity = emotion_result['emotion_info']['intensity']
        base_score = emotion_result['emotion_info']['base_score']
        adjusted_score = base_score * (1 + math.exp(2 * intensity - 1))  # 增强指数项
        final_score = max(min(adjusted_score, 5), -5)
        
        return {
            **emotion_result,
            'sentiment_score': round(final_score, 2),
            'mode': 'hybrid' if self.hybrid_mode else 'rule'
        }

    def _enhance_with_embedding(self, result, embedding):
        """增强模式处理"""
        vector_norm = np.linalg.norm(embedding)
        # 增强嵌入影响：使用sigmoid函数调整强度
        intensity_boost = 2 / (1 + math.exp(-vector_norm/50))  # 系数调整
        result['emotion_info']['intensity'] = min(
            result['emotion_info']['intensity'] * intensity_boost, 3.0
        )
        result['embedding'] = embedding[:3]
        return result

    def _load_emotion_dictionary(self):
        """加载情感词典"""
        try:
            df = pd.read_csv(
                r'src\handlers\emodata\大连理工大学中文情感词汇本体.csv',
                usecols=['词语', '情感分类'],
                encoding='utf-8'
            )
            valid_records = df[df['情感分类'].isin(CATEGORY_MAPPING)]
            self.emotion_dict = {
                row['词语']: CATEGORY_MAPPING[row['情感分类']]
                for _, row in valid_records.iterrows()
            }
            print(f'情感词典加载完成，共{len(self.emotion_dict)}条记录')
        except FileNotFoundError:
            print("未找到情感词典文件，请检查路径。")
    def _analyze_emotion(self, text):
        """核心情感分析方法"""
        words = jieba.lcut(text)
        word_counts = Counter(words)
        
        # 初始化参数
        counters = {t: 0 for t in ['positive', 'negative', 'anger', 'dislike', 
                                 'fear', 'depress', 'surprise', 'like', 'joy']}
        current_weight = 1.0
        negation_scope = False
        adverb_weight = 1.0

        for i, word in enumerate(words):
            # 标点符号处理
            if word in PUNCTUATION:
                negation_scope = False
                adverb_weight = 1.0
                continue
                
            # 位置权重（句子开头和结尾增强）
            position_weight = 1.2 - 0.5 * (i / len(words))
            
            # 程度副词处理
            if word in DEGREE_ADVERBS:
                adverb_weight = self._get_adverb_weight(word)
                continue
                
            # 否定词处理
            if word in NEGATIVE_WORDS:
                negation_scope = True
                counters['negative'] += 1.5 * position_weight
                counters['dislike'] += 1.0 * position_weight
                continue

            # 情感词处理
            emotion_type, polarity = self._get_word_sentiment(word)
            if emotion_type:
                # 应用权重和否定反转
                final_weight = adverb_weight * position_weight
                if negation_scope:
                    polarity = 'negative' if polarity == 'positive' else 'positive'
                    emotion_type = self._reverse_emotion(emotion_type)
                
                # 更新计数器
                counters[polarity] += final_weight
                counters[emotion_type] += final_weight
                adverb_weight = 1.0  # 重置副词权重

        return self._finalize_result(counters, len(words))
    def _finalize_result(self, counters, text_length):
        """结果处理"""
        # 情感极性计算
        positive = counters['positive']
        negative = counters['negative']
        
        # 线性归一化得分
        total = positive + negative
        if total == 0:
            polarity = '中立'
            base_score = 0
        else:
            base_score = (positive - negative) / total * 5
            polarity = '正面' if base_score > 0 else '负面'
        
        # 主情感类型
        emotions = [(k, v) for k, v in counters.items() if k not in ['positive', 'negative']]
        main_emotion, max_val = max(emotions, key=lambda x: x[1], default=(None, 0))
        
        # 强度计算（线性）
        intensity = min(max_val / (text_length * 0.5), 1)  # 按文本长度归一化

        return {
            'sentiment_type': main_emotion.capitalize() if max_val > 0 else 'None',
            'polarity': polarity,
            'emotion_info': {
                'length': text_length,
                'positive': positive,
                'negative': negative,
                'intensity': round(intensity, 2),
                'base_score': base_score, 
                **counters
            }
        }

    # 辅助方法
    def _get_adverb_weight(self, adverb):
        """细粒度程度副词权重"""
        weights = {
            '极其': 3.0, '超': 2.8, '最': 2.5,
            '非常': 2.0, '特别': 2.0, '十分': 2.0,
            '较为': 1.5, '比较': 1.5, '有点': 0.7,
            '稍微': 0.6, '略微': 0.5
        }
        return weights.get(adverb, 1.0)

    def _reverse_emotion(self, emotion):
        """情感类型反转逻辑"""
        reversal_map = {
            'joy': 'depress',
            'like': 'dislike',
            'surprise': 'fear',
            'anger': 'like',
            'dislike': 'like',
            'fear': 'surprise',
            'depress': 'joy'
        }
        return reversal_map.get(emotion, emotion)

    def _get_word_sentiment(self, word):
        """获取词语情感属性"""
        if word in self.emotion_dict:
            return self.emotion_dict[word]
        if word in POSITIVE_WORDS:
            return ('joy', 'positive')
        if word in NEGATIVE_WORDS_EXT:
            return ('depress', 'negative')
        return (None, None)
    

# 实例化分析器
analyzer = SentimentAnalyzer(hybrid_mode=True)

# 分析文本
result = analyzer.analyze("我喜欢你")
print(result)
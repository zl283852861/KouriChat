"""
消息后处理模块
负责处理AI响应、处理输入消息的格式化、消息分割、发送等操作
"""

import re
import logging
import time
import random
import threading
from datetime import datetime
from src.handlers.messages.base_handler import BaseHandler

try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False

# 获取logger
logger = logging.getLogger('main')

class MessagePostprocessor(BaseHandler):
    """消息后处理器，负责处理AI响应和发送消息"""
    
    def __init__(self, message_manager=None):
        """
        初始化后处理器
        
        Args:
            message_manager: 消息管理器实例的引用
        """
        super().__init__(message_manager)
        # 添加发送消息锁，确保消息发送的顺序性
        self.send_message_lock = threading.Lock()
    
    def process_for_sending_and_memory(self, content):
        """
        处理AI回复，添加$和￥分隔符，过滤标点符号
        返回处理后的分段消息和存储到记忆的内容
        
        Args:
            content: 原始AI响应
            
        Returns:
            dict: 包含处理后的消息部分和记忆内容
        """
        if not content:
            return {"parts": [], "memory_content": "", "total_length": 0, "sentence_count": 0}
        
        # 首先处理分隔符周围的标点符号，无论使用哪种分句方法
        # 此方法中同时也会处理连续分隔符为单个分隔符
        cleaned_content = self._clean_delimiter_punctuation(content)
        
        # 优先使用jieba分句，如果可用
        if JIEBA_AVAILABLE:
            # 预处理：清理所有@用户名（包括其后的空格和周围的标点符号）
            # 1. 查找所有@开头的用户名及其后的特殊空格
            cleaned_content = re.sub(r'@\S+[\u2005\u0020\u3000]?', '', cleaned_content)
            
            # 2. 处理可能残留的@符号
            cleaned_content = re.sub(r'@\S+', '', cleaned_content)
            
            # 3. 清理可能残留的特殊空格
            cleaned_content = re.sub(r'[\u2005\u3000]+', ' ', cleaned_content)
            
            # 4. 删除可能因清理造成的多余空格
            cleaned_content = re.sub(r'\s+', ' ', cleaned_content).strip()
            
            # 使用jieba智能分句
            parts = self._split_message_nlp(cleaned_content, max_length=30)
            
            # 添加记忆内容标记
            memory_parts = parts.copy()
            if memory_parts:
                # 最后一部分添加￥作为结束标记
                memory_parts[-1] = memory_parts[-1] + "￥"
            
            # 为记忆内容添加$分隔符 - 直接连接，不添加空格
            memory_content = "$".join(memory_parts)
            
            return {
                "parts": parts,
                "memory_content": memory_content,
                "total_length": sum(len(part) for part in parts),
                "sentence_count": len(parts)
            }
        
        # 如果jieba不可用，使用原有逻辑
        # 然后按照单个$分割
        dollar_parts = re.split(r'\$', cleaned_content)
        
        # 如果没有找到$分隔符，或者只有一部分，则使用句子分割逻辑
        if len(dollar_parts) <= 1:
            # 检查是否包含表情符号或特殊字符
            has_emoji = bool(re.search(r'[\U00010000-\U0010ffff\u2600-\u26FF\u2700-\u27BF]', content))
            
            # 对于包含表情符号的内容，使用不同的处理策略
            if has_emoji:
                # 直接使用句子作为分割单位，不再使用标点符号分割
                # 可能包含表情符号的句子，按照换行符或者句号分割
                sentences = re.split(r'([。！？\.\!\?\n])', content)
                
                # 重组句子
                complete_sentences = []
                for i in range(0, len(sentences)-1, 2):
                    if i+1 < len(sentences):
                        # 将句子和标点符号重新组合
                        sentence = sentences[i] + sentences[i+1]
                        complete_sentences.append(sentence)
                
                # 处理最后一个可能没有标点的片段
                if len(sentences) % 2 == 1 and sentences[-1].strip():
                    complete_sentences.append(sentences[-1])
                    
                # 如果没有成功分割，则将整个内容作为一句话处理
                if not complete_sentences:
                    complete_sentences = [content]
                    
                # 直接将每个句子作为一部分，不进行标点过滤
                processed_parts = []
                memory_parts = []
                
                for i, sentence in enumerate(complete_sentences):
                    clean_sentence = sentence.strip()
                    if clean_sentence:
                        # 恢复特殊标记为连续的$
                        clean_sentence = clean_sentence.replace('###MULTI_DOLLAR###', '$$')
                        
                        # 添加到处理结果
                        processed_parts.append(clean_sentence)
                        
                        # 为记忆内容准备，最后一句添加￥
                        if i == len(complete_sentences) - 1:
                            memory_parts.append(clean_sentence + "￥")
                        else:
                            memory_parts.append(clean_sentence)
                
                # 为记忆内容添加$分隔符 - 不使用空格
                memory_content = "$".join(memory_parts)
                
                return {
                    "parts": processed_parts,
                    "memory_content": memory_content,
                    "total_length": sum(len(part) for part in processed_parts),
                    "sentence_count": len(processed_parts)
                }
            
            # 没有表情符号的情况，使用句子分割逻辑
            sentences = re.split(r'([。！？\.\!\?])', content)
            
            # 重组句子
            complete_sentences = []
            for i in range(0, len(sentences)-1, 2):
                if i+1 < len(sentences):
                    # 将句子和标点符号重新组合
                    sentence = sentences[i] + sentences[i+1]
                    complete_sentences.append(sentence)
            
            # 处理最后一个可能没有标点的片段
            if len(sentences) % 2 == 1 and sentences[-1].strip():
                complete_sentences.append(sentences[-1])
            
            # 如果没有分离出句子，则视为一个完整句子
            if not complete_sentences and content.strip():
                complete_sentences = [content]
            
            # 处理每个句子，添加分隔符，过滤标点
            processed_parts = []
            memory_parts = []
            
            # 将每个句子作为单独的部分处理
            for i, sentence in enumerate(complete_sentences):
                is_last = i == len(complete_sentences) - 1
                # 过滤标点符号
                filtered_sentence = self._filter_punctuation(sentence, is_last)
                
                # 如果句子不为空，添加到处理结果中
                if filtered_sentence.strip():
                    # 恢复特殊标记为连续的$
                    filtered_sentence = filtered_sentence.replace('###MULTI_DOLLAR###', '$$')
                    
                    # 处理记忆内容，给最后一句添加￥
                    memory_sentence = filtered_sentence
                    if is_last:
                        memory_sentence = memory_sentence + "￥"
                    
                    processed_parts.append(filtered_sentence)
                    memory_parts.append(memory_sentence)
            
            # 为记忆内容添加$分隔符 - 不使用空格
            memory_content = "$".join(memory_parts)
            
            return {
                "parts": processed_parts,
                "memory_content": memory_content,
                "total_length": sum(len(part) for part in processed_parts),
                "sentence_count": len(processed_parts)
            }
        
        # 处理$分隔的部分
        processed_parts = []
        memory_parts = []
        
        for i, part in enumerate(dollar_parts):
            # 清理和准备部分，进行标点过滤
            clean_part = part.strip()
            if clean_part:
                # 对非空部分应用标点过滤
                is_last = (i == len(dollar_parts) - 1)
                is_first = (i == 0)
                
                # 过滤标点符号
                filtered_part = self._filter_punctuation(clean_part, is_last)
                
                # 使用基础处理器的方法清理部分的标点符号（开头和结尾）
                filtered_part = self._clean_part_punctuation(filtered_part, is_first, is_last)
                
                if filtered_part.strip():
                    processed_parts.append(filtered_part)
                    
                    # 为记忆内容准备，最后一部分添加￥
                    if i == len(dollar_parts) - 1:
                        memory_parts.append(filtered_part + "￥")
                    else:
                        memory_parts.append(filtered_part)
        
        # 为记忆内容添加$分隔符 - 直接连接，不添加空格
        memory_content = "$".join(memory_parts)
        
        return {
            "parts": processed_parts,
            "memory_content": memory_content,
            "total_length": sum(len(part) for part in processed_parts),
            "sentence_count": len(processed_parts)
        }
    
    def split_message_for_sending(self, text):
        """
        将消息分割成适合发送的多个部分
        
        Args:
            text: 原始消息
            
        Returns:
            dict: 分割后的消息信息
        """
        if not text:
            return {'parts': [], 'total_length': 0, 'sentence_count': 0}
        
        # 使用处理函数
        processed = self.process_for_sending_and_memory(text)
        
        # 添加日志
        logger.info(f"消息分割: 原文 \"{text[:100]}...\"")
        logger.info(f"消息分割: 分成了 {len(processed['parts'])} 个部分")
        
        for i, part in enumerate(processed['parts']):
            logger.info(f"消息分割部分 {i+1}: \"{part}\" (长度: {len(part)}字符)")
        
        if 'memory_content' in processed:
            # 显示处理后的记忆内容和长度
            mem_content = processed['memory_content']
            logger.info(f"记忆内容: \"{mem_content[:100]}...\" (总长度: {len(mem_content)}字符)")
        
        return {
            'parts': processed['parts'],
            'total_length': processed['total_length'],
            'sentence_count': processed['sentence_count'],
            'memory_content': processed['memory_content']
        }
    
    def send_split_messages(self, messages, chat_id, sender_name=None, is_group_chat=False):
        """
        发送分割后的消息
        
        Args:
            messages: 分割后的消息对象
            chat_id: 聊天ID
            sender_name: 发送者名称(仅用于群聊)
            is_group_chat: 是否是群聊
            
        Returns:
            bool: 是否发送成功
        """
        if not messages or not isinstance(messages, dict):
            return False
        
        # 使用锁确保消息发送的原子性
        with self.send_message_lock:
            # 记录已发送的消息，防止重复发送
            sent_messages = set()
            
            # 计算自然的发送间隔
            base_interval = 0.5  # 基础间隔时间（秒）
            
            # 检查消息内容是否已经包含@标记，避免重复@
            first_part = messages['parts'][0] if messages['parts'] else ""
            already_has_at = bool(re.search(r'^@[^\s]+', first_part))
            
            for i, part in enumerate(messages['parts']):
                if part not in sent_messages and part.strip():
                    # 处理消息中的$分隔符
                    processed_part = part
                    
                    # 移除消息开头的$符号
                    if processed_part.startswith('$'):
                        processed_part = processed_part[1:].strip()
                    
                    # 模拟真实用户输入行为
                    time.sleep(base_interval)  # 基础间隔
                    
                    # 只有在第一条消息、是群聊、有发送者名称且消息不已经包含@时才添加@
                    # 使用微信特殊的U+2005空格（四分之一空格）
                    if i == 0 and is_group_chat and sender_name and not already_has_at:
                        send_content = f"@{sender_name}\u2005{processed_part}"
                    else:
                        send_content = processed_part
                    
                    # 发送消息
                    logger.info(f"发送消息片段 {i+1}/{len(messages['parts'])}: {send_content[:20]}...")
                    
                    self._safe_send_msg(send_content, chat_id)
                    sent_messages.add(part)
                    
                    # 根据消息长度动态调整下一条消息的等待时间
                    wait_time = base_interval + random.uniform(0.3, 0.7) * (len(processed_part) / 50)
                    time.sleep(wait_time)
        
        return True 

    def _split_message_nlp(self, text, max_length=30):
        """
        使用jieba进行智能分句，适合微信聊天风格
        如果jieba库不可用，则回退到原始的分割方法
        
        Args:
            text: 原始文本
            max_length: 单条消息最大长度
            
        Returns:
            list: 分割后的消息段落列表
        """
        if not text:
            return []
            
        # 如果jieba不可用，回退到原始分割方法
        if not JIEBA_AVAILABLE:
            # 先检查是否有手动的$分隔符
            if '$' in text:
                return [part.strip() for part in text.split('$') if part.strip()]
            # 没有分隔符时，检查是否有\分隔符（兼容性处理）
            elif '\\' in text:
                return [part.strip() for part in text.split('\\') if part.strip()]
            # 没有分隔符时，尝试按句号、问号、感叹号分割
            else:
                # 使用正则表达式按句号、问号、感叹号分割
                segments = re.split(r'([。！？!?])', text)
                result = []
                temp = ""
                for i in range(0, len(segments), 2):
                    if i < len(segments):
                        # 当前片段
                        current = segments[i]
                        # 如果下一个是标点，加上标点
                        if i+1 < len(segments):
                            current += segments[i+1]
                        
                        # 如果添加当前片段会超过最大长度且temp不为空，先添加temp到结果
                        if len(temp) + len(current) > max_length and temp:
                            result.append(temp.strip())
                            temp = current
                        else:
                            temp += current
                
                # 添加最后的片段
                if temp:
                    result.append(temp.strip())
                    
                return result
        
        # 使用jieba进行分词
        try:
            # 先使用正则表达式分割句子
            sentence_pattern = r'([^。！？!?\n]+[。！？!?\n]+)'
            sentences = re.findall(sentence_pattern, text)
            
            # 处理可能剩余的文本（没有标点符号结尾的）
            remaining_text = re.sub(sentence_pattern, '', text).strip()
            if remaining_text:
                sentences.append(remaining_text)
            
            # 如果没有成功分割句子，则直接返回原始文本
            if not sentences:
                return [text]
                
            # 处理各个句子，尝试合并短句
            segments = []
            current_segment = ""
            
            # 处理括号保护
            bracket_stack = []  # 用于跟踪未闭合的括号
            bracket_pairs = {'(': ')', '（': '）', '[': ']', '【': '】', '{': '}', '<': '>'}
            
            # 模拟闭合括号的检查函数
            def is_bracket_closed():
                return len(bracket_stack) == 0
            
            for sentence in sentences:
                # 检查句子中的括号平衡
                for char in sentence:
                    if char in bracket_pairs:
                        bracket_stack.append(char)
                    elif char in bracket_pairs.values() and bracket_stack:
                        # 检查是否匹配最近的开括号
                        open_bracket = bracket_stack[-1]
                        if char == bracket_pairs.get(open_bracket):
                            bracket_stack.pop()
                
                # 如果句子太长，可能需要二次拆分
                if len(sentence) > max_length:
                    # 使用jieba进行分词，找到自然的拆分点
                    words = list(jieba.cut(sentence))
                    sub_temp = ""
                    for word in words:
                        if len(sub_temp) + len(word) <= max_length:
                            sub_temp += word
                        else:
                            if sub_temp:
                                segments.append(sub_temp.strip())
                            sub_temp = word
                    if sub_temp:
                        segments.append(sub_temp.strip())
                else:
                    # 尝试将当前句子添加到现有段落
                    if len(current_segment) + len(sentence) <= max_length:
                        current_segment += sentence
                    else:
                        # 如果添加会超过长度限制，并且括号已闭合，则分段
                        if current_segment and is_bracket_closed():
                            segments.append(current_segment.strip())
                            current_segment = sentence
                        else:
                            # 括号未闭合，继续累加
                            current_segment += sentence
            
            # 添加最后一个段落
            if current_segment:
                segments.append(current_segment.strip())
                
            # 清理段落末尾的多余标点
            for i in range(len(segments)):
                # 移除末尾的逗号、分号
                segments[i] = re.sub(r'[,，;；]$', '', segments[i])
                
            return segments
            
        except Exception as e:
            logger.warning(f"使用jieba分词处理失败: {str(e)}")
            # 失败时回退到基本分割
            return self._split_message_basic(text, max_length)
        
    def _split_message_basic(self, text, max_length=30):
        """
        基本的消息分割方法，用于jieba不可用时的回退方案
        
        Args:
            text: 原始文本
            max_length: 单条消息最大长度
            
        Returns:
            list: 分割后的消息段落列表
        """
        if not text:
            return []
            
        # 先检查是否有手动的$分隔符
        if '$' in text:
            return [part.strip() for part in text.split('$') if part.strip()]
            
        # 没有分隔符时，检查是否有\分隔符（兼容性处理）
        elif '\\' in text:
            return [part.strip() for part in text.split('\\') if part.strip()]
            
        # 没有分隔符时，尝试按句号、问号、感叹号分割
        else:
            # 使用正则表达式按句号、问号、感叹号分割
            pattern = r'([。！？!?])'
            segments = re.split(pattern, text)
            
            result = []
            temp = ""
            
            for i in range(0, len(segments), 2):
                if i < len(segments):
                    # 当前片段
                    current = segments[i]
                    # 如果下一个是标点，加上标点
                    if i+1 < len(segments):
                        current += segments[i+1]
                    
                    # 如果添加当前片段会超过最大长度且temp不为空，先添加temp到结果
                    if len(temp) + len(current) > max_length and temp:
                        result.append(temp.strip())
                        temp = current
                    else:
                        temp += current
            
            # 添加最后的片段
            if temp:
                result.append(temp.strip())
                
            return result

if __name__ == "__main__":
    # 测试代码
    import asyncio
    
    # 配置基本日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    class MockMessageManager:
        def __init__(self):
            pass
            
        def get_module(self, name):
            return None
    
    async def test_postprocessor():
        print("开始测试消息后处理器...")
        
        # 创建模拟对象
        manager = MockMessageManager()
        processor = MessagePostprocessor(manager)
        
        # 测试NLP分句功能
        test_texts = [
            "群里在讨论API的问题，好像是因为API爆了，大家在考虑用v3来解决。你怎么突然关心起这个来了？",
            "今天天气真好！你觉得呢？我们要不要出去走走？",
            "这是一段很长的文本，主要用于测试NLP分句功能。我们期望它能够根据语义和句法结构自动分割成多个句子。测试中包含逗号、句号等多种标点符号。括号内的内容(比如这一部分)应该被保护，不会被随意切分。",
            "我有以下几点建议：第一，多使用自然语言处理；第二，优化用户体验；第三，提高系统响应速度。"
        ]
        
        print("\n测试NLP分句功能:")
        for text in test_texts:
            print(f"原始文本: '{text}'")
            result = processor.split_message_for_sending(text)
            parts = result['parts']
            print("分句结果:")
            for i, seg in enumerate(parts):
                print(f"  段落{i+1}: '{seg}'")
            print("---")
        
        # 测试传统分句功能 (使用$分隔符)
        test_with_delimiter = "第一部分$第二部分$带有标点符号的第三部分，测试一下。"
        print(f"\n测试带分隔符的文本: '{test_with_delimiter}'")
        result = processor.split_message_for_sending(test_with_delimiter)
        parts = result['parts']
        print("分句结果:")
        for i, seg in enumerate(parts):
            print(f"  段落{i+1}: '{seg}'")
        
        # 测试带有标点符号周围的分隔符
        test_with_punctuation = "第一部分，$，第二部分$，带有标点符号的，$，第三部分，测试一下。"
        print(f"\n测试带有标点符号周围的分隔符: '{test_with_punctuation}'")
        result = processor.split_message_for_sending(test_with_punctuation)
        parts = result['parts']
        print("分句结果:")
        for i, seg in enumerate(parts):
            print(f"  段落{i+1}: '{seg}'")
        
        # 测试带有连续分隔符和￥结束符
        test_with_consecutive = "第一部分$$第二部分$第三部分￥带有标点。"
        print(f"\n测试带有连续分隔符和￥结束符: '{test_with_consecutive}'")
        result = processor.split_message_for_sending(test_with_consecutive)
        parts = result['parts']
        print("分句结果:")
        for i, seg in enumerate(parts):
            print(f"  段落{i+1}: '{seg}'")
        memory = result['memory_content']
        print(f"记忆内容: '{memory}'")
        
        # 测试处理@用户名
        test_with_at = [
            "@用户名\u2005后面是微信特殊空格",
            "内容中带有@用户名\u2005和特殊空格$第二部分也有@某人",
            "@用户甲\u2005@用户乙\u2005多个连续用户名",
            "含有标点符号的@用户名，和逗号$后面部分"
        ]
        
        print("\n测试处理@用户名:")
        for text in test_with_at:
            print(f"原始文本: '{text}'")
            result = processor.split_message_for_sending(text)
            parts = result['parts']
            print("处理结果:")
            for i, seg in enumerate(parts):
                print(f"  段落{i+1}: '{seg}'")
            print("---")
        
        print("\n消息后处理器测试完成")
    
    # 运行测试
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_postprocessor()) 
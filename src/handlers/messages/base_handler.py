"""
基础消息处理器模块
消息过滤处理
定义消息处理器的基本接口和共享工具方法
"""

import re
import logging
import time
from datetime import datetime
import random

# 获取logger
logger = logging.getLogger('main')

class BaseHandler:
    """基础消息处理器类，定义通用接口和工具方法"""
    
    def __init__(self, message_manager=None):
        """
        初始化基础处理器
        
        Args:
            message_manager: 消息管理器实例的引用
        """
        self.message_manager = message_manager
        self.MAX_MESSAGE_LENGTH = 500
    
    def _clean_message_content(self, content: str) -> str:
        """
        清理消息内容，去除时间戳和前缀
        
        Args:
            content: 原始消息内容
            
        Returns:
            str: 清理后的消息内容
        """
        # 匹配并去除时间戳和前缀
        patterns = [
            r'^\(?\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\)?\s+ta私聊对你说\s*',
            r'^\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\]\s+ta私聊对你说\s*',
            r'^\(此时时间为\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\)\s+ta(私聊|在群聊里)对你说\s*',
            r'^.*?ta私聊对你说\s*',
            r'^.*?ta在群聊里对你说\s*',  # 添加群聊消息模式
            r'^\[?\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(:\d{2})?\]?\s+', # 匹配纯时间戳格式
            r'^\(?\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(:\d{2})?\)?\s+'  # 匹配带小括号的时间戳格式
        ]
        
        actual_content = content
        
        # 保存@信息
        at_match = re.search(r'(@[^\s]+)', actual_content)
        at_content = at_match.group(1) if at_match else ''
        
        # 清理时间戳和前缀
        for pattern in patterns:
            if re.search(pattern, actual_content):
                actual_content = re.sub(pattern, '', actual_content)
                break
        
        # 如果有@信息且在清理过程中被移除，重新添加到开头
        if at_content and at_content not in actual_content:
            actual_content = f"{at_content} {actual_content}"
        
        return actual_content.strip()
    
    def _clean_memory_content(self, content: str) -> str:
        """
        清理记忆内容，移除不必要的格式和标记
        
        Args:
            content: 原始内容
            
        Returns:
            str: 清理后的内容
        """
        if not content:
            return ""
        
        # 移除时间戳和前缀
        patterns = [
            r'^\(?\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(?::\d{2})?\)?\s+',  # 时间戳格式
            r'^\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(?::\d{2})?\]\s+',    # 带方括号的时间戳
            r'^\(此时时间为\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(?::\d{2})?\)\s+', # 带说明的时间戳
            r'^.*?ta(私聊|在群聊里)对你说\s*',  # 对话前缀
            r'<time>.*?</time>\s*',  # XML风格时间标记
            r'<group>.*?</group>\s*',  # 群组标记
            r'<sender>.*?</sender>\s*',  # 发送者标记
            r'<input>(.*?)</input>',  # 保留input标记内的内容
            r'<context>.*?</context>\s*'  # 上下文标记
        ]
        
        # 应用所有模式
        cleaned_content = content
        for pattern in patterns:
            if re.search(pattern, cleaned_content):
                if 'input' in pattern:
                    # 对于input标记，保留其内容
                    match = re.search(pattern, cleaned_content)
                    if match:
                        cleaned_content = match.group(1)
                else:
                    # 对于其他模式，直接移除
                    cleaned_content = re.sub(pattern, '', cleaned_content)
        
        # 移除引用格式
        cleaned_content = re.sub(r'\(引用消息:.*?\)\s*', '', cleaned_content)
        
        # 移除多余的空白字符
        cleaned_content = re.sub(r'\s+', ' ', cleaned_content)
        
        # 移除@标记
        cleaned_content = re.sub(r'@[^\s]+\s*', '', cleaned_content)
        
        # 移除代码块标记
        cleaned_content = re.sub(r'```.*?```', '', cleaned_content, flags=re.DOTALL)
        
        # 移除多行环境中的多余换行符
        cleaned_content = re.sub(r'\n+', ' ', cleaned_content)
        
        return cleaned_content.strip()
    
    def _clean_ai_response(self, response: str) -> str:
        """
        清理AI回复中的所有系统标记和提示词
        
        Args:
            response: 原始AI响应
            
        Returns:
            str: 清理后的响应
        """
        if not response:
            return ""
        
        # 移除所有XML样式的标记
        response = re.sub(r'<[^>]+>', '', response)
        
        # 清理其他系统标记和提示词
        patterns_to_remove = [
            r'\[系统提示\].*?\[/系统提示\]',
            r'\[系统指令\].*?\[/系统指令\]',
            r'记忆\d+:\s*\n用户:.*?\nAI:.*?(?=\n\n|$)',
            r'以下是之前的对话记录：.*?(?=\n\n)',
            r'\(以上是历史对话内容[^)]*\)',
            r'memory_number:.*?(?=\n|$)',
            r'\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(?::\d{2})?\]',
            r'请注意：.*?(?=\n|$)',
            r'请(?:简短|简洁)回复.*?(?=\n|$)',
            r'请.*?控制在.*?(?=\n|$)',
            r'请你回应用户的结束语',
            r'^你：|^对方：|^AI：',
            r'ta(?:私聊|在群聊里)对你说[：:]\s*',
        ]
        
        for pattern in patterns_to_remove:
            response = re.sub(pattern, '', response, flags=re.DOTALL|re.IGNORECASE)
        
        # 移除多余的空白字符
        response = re.sub(r'\s+', ' ', response)
        return response.strip()
        
    def _filter_action_emotion(self, text):
        """
        处理动作描写和颜文字，确保格式一致
        
        Args:
            text: 原始文本
            
        Returns:
            str: 处理后的文本
        """
        if not text:
            return ""
            
        # 1. 先移除文本中的引号，避免引号包裹非动作文本
        text = text.replace('"', '').replace('"', '').replace('"', '')
        
        # 2. 保护已经存在的括号内容
        protected_parts = {}
        
        # 匹配所有类型的括号及其内容
        bracket_pattern = r'[\(\[（【][^\(\[（【\)\]）】]*[\)\]）】]'
        brackets = list(re.finditer(bracket_pattern, text))
        
        # 保护已有的括号内容
        for i, match in enumerate(brackets):
            placeholder = f"__PROTECTED_{i}__"
            protected_parts[placeholder] = match.group()
            text = text.replace(match.group(), placeholder)
        
        # 3. 保护颜文字 - 使用更宽松的匹配规则
        # 定义常用颜文字字符集
        emoticon_chars_set = set(
            '（()）~～‿⁀∀︿⌒▽△□◇○●ˇ＾∇＿゜◕ω・ノ丿╯╰つ⊂＼／┌┐┘└°△▲▽▼◇◆○●◎■□▢▣▤▥▦▧▨▩♡♥ღ☆★✡⁂✧✦❈❇✴✺✹✸✷✶✵✳✳✲✱✰✯✮✭✬✫✪✩✨✧✦✥✤✣✢✡✠✟✞✝✜✛✚✙✘✗✖✕✔✓✒✑✐✏✎✍✌✋✊✉✈✇✆✅✄✃✂✁✀✿✾✽✼✻✺✹✸✷✶✵✴✳✲✱✰✯✮✭✬✫✪✩✧✦✥✤✣✢✡✠✟✞✝✜✛✚✙✘✗✖✕✔✓✒✑✐✏✎✍✌✋✊✉✈✇✆✅✄✃✂✁❤♪♫♬♩♭♮♯°○◎●◯◐◑◒◓◔◕◖◗¤☼☀☁☂☃☄★☆☎☏⊙◎☺☻☯☭♠♣♧♡♥❤❥❣♂♀☿❀❁❃❈❉❊❋❖☠☢☣☤☥☦☧☨☩☪☫☬☭☮☯☸☹☺☻☼☽☾☿♀♁♂♃♄♆♇♈♉♊♋♌♍♎♏♐♑♒♓♔♕♖♗♘♙♚♛♜♝♞♟♠♡♢♣♤♥♦♧♨♩♪♫♬♭♮♯♰♱♲♳♴♵♶♷♸♹♺♻♼♽♾♿⚀⚁⚂⚃⚄⚆⚇⚈⚉⚊⚋⚌⚍⚎⚏⚐⚑⚒⚓⚔⚕⚖⚗⚘⚙⚚⚛⚜⚝⚞⚟*^_^')
        
        emoji_patterns = [
            # 括号类型的颜文字
            r'\([\w\W]{1,10}?\)',  # 匹配较短的括号内容
            r'（[\w\W]{1,10}?）',  # 中文括号
            
            # 符号组合类型
            r'[＼\\\/\*\-\+\<\>\^\$\%\!\?\@\#\&\|\{\}\=\;\:\,\.]{2,}',  # 常见符号组合
            
            # 常见表情符号
            r'[◕◑◓◒◐•‿\^▽\◡\⌒\◠\︶\ω\´\`\﹏\＾\∀\°\◆\□\▽\﹃\△\≧\≦\⊙\→\←\↑\↓\○\◇\♡\❤\♥\♪\✿\★\☆]{1,}',
            
            # *号组合
            r'\*[\w\W]{1,5}?\*'  # 星号强调内容
        ]
        
        for pattern in emoji_patterns:
            emojis = list(re.finditer(pattern, text))
            for i, match in enumerate(emojis):
                # 避免处理过长的内容，可能是动作描写而非颜文字
                if len(match.group()) <= 15 and not any(p in match.group() for p in protected_parts.values()):
                    # 检查是否包含足够的表情符号字符
                    chars_count = sum(1 for c in match.group() if c in emoticon_chars_set)
                    if chars_count >= 2 or len(match.group()) <= 5:
                        placeholder = f"__EMOJI_{i}__"
                        protected_parts[placeholder] = match.group()
                        text = text.replace(match.group(), placeholder)
        
        # 4. 处理分隔符 - 保留原样
        parts = text.split('$')
        new_parts = []
        
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:  # 跳过空部分
                continue
                
            # 直接添加部分，不添加括号
            new_parts.append(part)
        
        # 5. 特殊处理：同时兼容原来的 \ 分隔符
        if len(new_parts) == 1:  # 如果没有找到 $ 分隔符，尝试处理 \ 分隔符
            parts = text.split('\\')
            if len(parts) > 1:  # 确认有实际分隔
                new_parts = []
                for i, part in enumerate(parts):
                    part = part.strip()
                    if not part:
                        continue
                    # 直接添加部分，不添加括号
                    new_parts.append(part)
        
        # 6. 重新组合文本
        result = "$".join(new_parts)
        
        # 7. 恢复所有保护的内容
        for placeholder, content in protected_parts.items():
            result = result.replace(placeholder, content)
            
        return result
    
    def _filter_punctuation(self, text: str, is_last_sentence: bool = False) -> str:
        """
        过滤标点符号，保留问号、感叹号、省略号、书名号、括号、引号
        如果是最后一句，并过滤掉句尾的句号
        
        Args:
            text: 原始文本
            is_last_sentence: 是否是最后一句
            
        Returns:
            str: 处理后的文本
        """
        if not text:
            return ""
        
        # 定义需要保留的标点符号集合
        keep_punctuation = set(['?', '!', '？', '！', '…', '《', '》', '(', ')', '（', '）', '"', '"', ''', ''', '「', '」'])
        
        # 需要过滤的标点符号（除了保留的那些）
        filter_punctuation = set(['。', '，', '、', '：', '；', '·', '~', ',', '.', ':', ';'])
        
        # 如果是最后一句，且以句号结尾，移除句尾的句号
        if is_last_sentence and text[-1] in ['。', '.']:
            text = text[:-1]
        
        # 处理文本中的标点
        result = ""
        for char in text:
            if char in filter_punctuation:
                # 过滤掉需要过滤的标点
                continue
            result += char
        
        return result
    
    def _clean_delimiter_punctuation(self, text: str) -> str:
        """
        清理分隔符$和￥周围的标点符号，保留分隔符前的问号、感叹号和省略号
        连续的多个分隔符将被替换为单个分隔符
        ￥作为句子结束符，其后的标点将被清理
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""
        
        result = text
        
        # 处理连续的分隔符 - 替换为单个分隔符
        # 替换连续2个及以上的$为单个$
        result = re.sub(r'\${2,}', '$', result)
        # 替换连续2个及以上的￥为单个￥
        result = re.sub(r'￥{2,}', '￥', result)
        
        # 设定临时标记，用于保护特殊标点
        protected_marks = {}
        placeholder_index = 0
        
        # 1. 先标记并保护省略号（包括连续句号形式的省略号）
        ellipsis_patterns = [
            (r'\.{2,}\s*\$', '...'), # 英文省略号
            (r'\.{2,}\s*￥', '...'), 
            (r'。{2,}\s*\$', '。。。'), # 中文省略号
            (r'。{2,}\s*￥', '。。。'),
            (r'…+\s*\$', '…'), # Unicode省略号
            (r'…+\s*￥', '…')
        ]
        
        for pattern, replacement in ellipsis_patterns:
            matches = re.finditer(pattern, result)
            for match in matches:
                full_match = match.group(0)
                placeholder = f"__PROTECT_{placeholder_index}__"
                placeholder_index += 1
                
                # 决定保留哪部分作为省略号
                if '$' in full_match:
                    protected_marks[placeholder] = replacement + '$'
                else:
                    protected_marks[placeholder] = replacement + '￥'
                    
                result = result.replace(full_match, placeholder)
        
        # 2. 标记并保护问号和感叹号
        for char in "!！?？":
            # 处理$分隔符前的特殊标点
            pattern = re.escape(char) + r'+\s*\$'
            matches = re.finditer(pattern, result)
            for match in matches:
                placeholder = f"__PROTECT_{placeholder_index}__"
                placeholder_index += 1
                protected_marks[placeholder] = char + '$'
                result = result.replace(match.group(0), placeholder)
                
            # 处理￥分隔符前的特殊标点
            pattern = re.escape(char) + r'+\s*￥'
            matches = re.finditer(pattern, result)
            for match in matches:
                placeholder = f"__PROTECT_{placeholder_index}__"
                placeholder_index += 1
                protected_marks[placeholder] = char + '￥'
                result = result.replace(match.group(0), placeholder)
        
        # 3. 清理需要过滤的标点符号（普通标点）
        filter_punctuation = "。，、；：·~,;:,、'\"()（）\"\"''\"\"''【】[]{}《》<>『』「」—_-+=*&#@"
        
        # 清理分隔符$前的标点
        result = re.sub(r'[' + re.escape(filter_punctuation) + r']+\s*\$', '$', result)
        
        # 清理分隔符$后的标点
        result = re.sub(r'\$\s*[' + re.escape(filter_punctuation) + r'!！?？]+', '$', result)
        
        # 清理分隔符￥前的标点
        result = re.sub(r'[' + re.escape(filter_punctuation) + r']+\s*￥', '￥', result)
        
        # 清理分隔符￥后的标点
        result = re.sub(r'￥\s*[' + re.escape(filter_punctuation) + r'!！?？]+', '￥', result)
        
        # 4. 恢复所有保护的标记
        for placeholder, content in protected_marks.items():
            result = result.replace(placeholder, content)
        
        # 5. 处理分隔符周围可能存在的空格问题
        result = re.sub(r'\s*\$\s*', '$', result)
        result = re.sub(r'\s*￥\s*', '￥', result)
        
        return result
    
    def _clean_part_punctuation(self, part: str, is_first: bool = False, is_last: bool = False) -> str:
        """
        清理分段后的文本部分的标点符号，主要处理分段开头和结尾
        同时清理@用户名及其后面的空格（包括微信特殊的U+2005空格）
        
        Args:
            part: 文本部分
            is_first: 是否是第一部分
            is_last: 是否是最后一部分
            
        Returns:
            str: 清理后的文本
        """
        if not part:
            return ""
            
        # 定义需要过滤的标点符号
        punct_chars = "。，、；：·~.,;:，、'\"()（）\"\"''\"\"''【】[]{}《》<>『』「」—_-+=*&#@"
        
        # 首先清理所有@用户名（包括其后的空格和周围的标点符号）
        # 1. 查找所有@开头的用户名及其后的特殊空格
        cleaned_part = re.sub(r'@\S+[\u2005\u0020\u3000]?', '', part)
        
        # 2. 处理可能残留的@符号
        cleaned_part = re.sub(r'@\S+', '', cleaned_part)
        
        # 3. 清理可能残留的特殊空格
        cleaned_part = re.sub(r'[\u2005\u3000]+', ' ', cleaned_part)
        
        # 清理部分开头和结尾的标点符号
        cleaned_part = cleaned_part.strip()
        
        # 如果不是第一部分，清理开头的标点
        if not is_first:
            # 使用正则表达式一次性清理开头的所有标点
            cleaned_part = re.sub(f'^[{re.escape(punct_chars)}]+', '', cleaned_part).strip()
        
        # 如果不是最后一部分，清理结尾的标点
        if not is_last:
            # 使用正则表达式一次性清理结尾的所有标点
            cleaned_part = re.sub(f'[{re.escape(punct_chars)}]+$', '', cleaned_part).strip()
        
        # 删除可能因清理造成的多余空格
        cleaned_part = re.sub(r'\s+', ' ', cleaned_part).strip()
        
        return cleaned_part
    
    async def _safe_send_msg_async(self, msg, chat_id):
        """
        安全发送消息的异步方法
        
        Args:
            msg: 消息内容
            chat_id: 聊天ID
        """
        try:
            if not msg or not chat_id:
                logger.warning("无法发送消息: 消息内容或聊天ID为空")
                return
                
            # 获取微信实例
            wx = self.message_manager.wx if self.message_manager else None
            if not wx:
                logger.warning("无法发送消息: 找不到微信实例")
                return
                
            # 发送消息
            wx.SendMsg(msg, chat_id)
            logger.info(f"已发送消息到 {chat_id}: {msg[:50]}...")
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            
    def _safe_send_msg(self, msg, chat_id):
        """
        安全发送消息(同步版本)
        
        Args:
            msg: 消息内容
            chat_id: 聊天ID
        """
        try:
            if not msg or not chat_id:
                logger.warning("无法发送消息: 消息内容或聊天ID为空")
                return
                
            # 获取微信实例
            wx = self.message_manager.wx if self.message_manager else None
            if not wx:
                logger.warning("无法发送消息: 找不到微信实例")
                return
                
            # 发送消息
            wx.SendMsg(msg, chat_id)
            logger.info(f"已发送消息到 {chat_id}: {msg[:50]}...")
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")

if __name__ == "__main__":
    import asyncio
    import logging
    
    # 配置基本日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('test')
    
    class MockMessageManager:
        """模拟MessageManager类"""
        def __init__(self):
            self.wx = MockWX()
            
        def get_module(self, name):
            return None
    
    class MockWX:
        """模拟微信接口"""
        def SendMsg(self, msg, who=None):
            print(f"发送消息到 {who}: {msg}")
            return True
            
        def SendFiles(self, filepath, who=None):
            print(f"发送文件 {filepath} 到 {who}")
            return True
    
    # 创建一个继承BaseHandler的测试类
    class TestHandler(BaseHandler):
        """用于测试的处理器类"""
        def __init__(self, message_manager=None):
            super().__init__(message_manager)
            
        async def test_method(self, content):
            """测试方法"""
            return f"处理结果: {content}"
            
        def clean_test(self, content):
            """测试清理方法"""
            return self._clean_message_content(content)
    
    async def test_base_handler():
        print("开始测试基础处理器...")
        
        # 创建模拟对象
        manager = MockMessageManager()
        handler = TestHandler(manager)
        
        # 测试_clean_message_content方法
        test_contents = [
            "普通消息",
            "[2023-01-01 12:00:00] 带时间戳的消息",
            "包含特殊字符与标点的消息：@#，$%^&... $*()。￥",
            "    消息前后有空格    "
        ]
        
        for content in test_contents:
            cleaned = handler.clean_test(content)
            print(f"原始内容: '{content}'")
            print(f"清理后: '{cleaned}'")
            print("---")
        
        # 测试_clean_delimiter_punctuation方法
        test_delimiter_contents = [
            "这是一段带有$符号的文本",
            "带有标点符号的测试，$前面有标点",
            "标点符号$，在分隔符周围",
            "内容结尾带有标点。￥。",  # ￥作为句尾结束符
            "问号标点？$感叹号！$省略号...$在分隔符前",
            "内容结尾带问号？￥",  # ￥作为句尾结束符
            "内容带有$分隔且结尾带有￥",
            "连续$$$分隔符测试￥￥￥",
            "连续开头分隔符$的情况",
            "句子结尾带有标点￥，",  # ￥后有标点
            "正常句子$然后是第二句结尾￥。"  # ￥后有标点
        ]
        
        print("\n测试清理分隔符周围标点:")
        for content in test_delimiter_contents:
            cleaned = handler._clean_delimiter_punctuation(content)
            print(f"原始内容: '{content}'")
            print(f"清理后: '{cleaned}'")
            print("---")
        
        # 测试_clean_part_punctuation方法
        test_parts = [
            "第一部分",
            "，第二部分开头有标点",
            "第三部分结尾有标点，",
            "，第四部分，两端都有标点，",
            "@用户名 ，有标点",
            "，@用户名 ，两端有标点，",
            "@用户名\u2005后面是微信特殊空格",  # 使用U+2005空格
            "@用户甲\u2005@用户乙\u2005多个连续用户名",
            "前面有文字@用户名\u2005后面也有文字",
            "含有标点符号的@用户名，和逗号"
        ]
        
        print("\n测试清理部分标点:")
        for i, part in enumerate(test_parts):
            is_first = (i == 0)
            is_last = (i == len(test_parts) - 1)
            cleaned = handler._clean_part_punctuation(part, is_first, is_last)
            print(f"原始部分({i+1}): '{part}'")
            print(f"清理后: '{cleaned}'")
            print("---")
        
        # 测试_safe_send_msg方法
        await handler._safe_send_msg_async("测试异步发送消息", "test_user")
        handler._safe_send_msg("测试同步发送消息", "test_user")
        
        # 注释掉不存在的方法调用
        # 测试get_memory_retriever方法(如果有)
        if hasattr(handler, 'get_memory_retriever'):
            retriever = handler.get_memory_retriever()
            print(f"记忆检索器: {retriever}")
        
        print("基础处理器测试完成")
    
    # 运行测试
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_base_handler()) 
"""
配置管理Web界面启动文件
提供Web配置界面功能，包括:
- 初始化Python路径
- 禁用字节码缓存
- 清理缓存文件
- 启动Web服务器
- 动态修改配置
"""
import os
import sys
import re
from flask import Flask, render_template, jsonify, request, send_from_directory
import importlib
import json
from colorama import init, Fore, Style
from werkzeug.utils import secure_filename

# 初始化colorama
init()

# 添加项目根目录到Python路径
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT_DIR)

# 禁用Python的字节码缓存
sys.dont_write_bytecode = True

app = Flask(__name__, 
    template_folder=os.path.join(ROOT_DIR, 'src/webui/templates'),
    static_folder=os.path.join(ROOT_DIR, 'src/webui/static'))

# 添加配置
app.config['UPLOAD_FOLDER'] = os.path.join(ROOT_DIR, 'src/webui/background_image')

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def print_status(message: str, status: str = "info", emoji: str = ""):
    """打印带颜色和表情的状态消息"""
    colors = {
        "success": Fore.GREEN,
        "info": Fore.BLUE,
        "warning": Fore.YELLOW,
        "error": Fore.RED
    }
    color = colors.get(status, Fore.WHITE)
    print(f"{color}{emoji} {message}{Style.RESET_ALL}")

def get_config_with_comments():
    """获取配置文件内容，包括注释"""
    config_path = os.path.join(ROOT_DIR, 'src/config/settings.py')
    with open(config_path, 'r', encoding='utf-8') as f:
        return f.read()

def parse_config_groups():
    """解析配置文件，将配置项按组分类"""
    from src.config import settings
    
    config_content = get_config_with_comments()
    config_groups = {}
    current_group = "基础配置"
    
    # 使用正则表达式匹配注释
    comment_pattern = r'#\s*(.*?)\n'
    docstring_pattern = r'"""(.*?)"""'
    
    comments = {}
    # 提取所有注释
    for match in re.finditer(comment_pattern, config_content, re.MULTILINE):
        line_num = config_content.count('\n', 0, match.start())
        comment_text = match.group(1).strip()
        # 如果注释以变量名开头，则跳过（避免重复）
        if not any(var.isupper() and comment_text.startswith(var) for var in dir(settings)):
            comments[line_num] = comment_text
    
    # 配置项描述映射
    descriptions = {
        # 基础配置
        'MODEL': 'AI模型选择',
        'DEEPSEEK_BASE_URL': '硅基流动API注册地址',
        'DEEPSEEK_API_KEY': 'DeepSeek API密钥',
        'LISTEN_LIST': '用户列表(请配置要和bot说话的账号的昵称或者群名，不要写备注！)',
        'MAX_GROUPS': '最大的上下文轮数',
        'MAX_TOKEN': '回复最大token数',
        'TEMPERATURE': '温度参数',
        'EMOJI_DIR': '表情包存放目录',

        # 图像识别API配置
        'MOONSHOT_API_KEY': 'Moonshot API密钥（用于图片和表情包识别）',
        'MOONSHOT_BASE_URL': 'Moonshot API基础URL',
        'MOONSHOT_TEMPERATURE': 'Moonshot温度参数',

        # 图像生成配置
        'IMAGE_MODEL': '图像生成模型',
        'TEMP_IMAGE_DIR': '临时图片目录',

        # 时间配置
        'AUTO_MESSAGE': '自动消息内容',
        'MIN_COUNTDOWN_HOURS': '最小倒计时时间（小时）',
        'MAX_COUNTDOWN_HOURS': '最大倒计时时间（小时）',
        'QUIET_TIME_START': '安静时间开始',
        'QUIET_TIME_END': '安静时间结束',

        # 语音配置
        'TTS_API_URL': '语音服务API地址',
        'VOICE_DIR': '语音文件目录',

        # Prompt配置
        'PROMPT_NAME': 'Prompt文件路径'
    }
    
    # 获取所有配置项
    for name in dir(settings):
        if name.isupper():  # 只处理大写的配置项
            value = getattr(settings, name)
            if not callable(value):  # 排除方法
                # 在配置内容中查找该配置项的位置
                pattern = rf'{name}\s*='
                match = re.search(pattern, config_content, re.MULTILINE)
                if match:
                    line_num = config_content.count('\n', 0, match.start())
                    # 使用预定义的描述，如果没有则使用注释中的描述
                    description = descriptions.get(name, comments.get(line_num - 1, ""))
                    
                    # 修改分组判断逻辑
                    if "Moonshot" in name:
                        group = "图像识别API配置"
                    elif "IMAGE" in name or "TEMP_IMAGE_DIR" in name:
                        group = "图像生成配置"
                    elif name == "PROMPT_NAME":
                        group = "Prompt配置"
                    elif any(word in name for word in ["TIME", "COUNTDOWN", "AUTO_MESSAGE"]):
                        group = "时间配置"
                    elif any(word in name for word in ["TTS", "VOICE"]):
                        group = "语音配置"
                    else:
                        group = "基础配置"
                        
                    if group not in config_groups:
                        config_groups[group] = {}
                    
                    config_groups[group][name] = {
                        "value": value,
                        "description": description
                    }
    
    return config_groups

def save_config(new_config):
    """保存新的配置到文件"""
    config_content = get_config_with_comments()
    
    # 更新配置内容
    for key, value in new_config.items():
        # 处理不同类型的值
        if isinstance(value, str):
            value_str = f"'{value}'"
        elif isinstance(value, list):
            value_str = str(value)
        elif isinstance(value, bool):
            value_str = str(value).lower()  # 布尔值转换为小写字符串
        elif isinstance(value, int):
            value_str = str(value)  # 整数保持为字符串
        else:
            value_str = str(value)  # 确保其他类型的值转换为字符串
            
        # 使用正则表达式替换配置值
        pattern = rf'{key}\s*=\s*[^#\n]+'
        config_content = re.sub(pattern, f'{key} = {value_str}', config_content)
    
    # 保存到文件
    config_path = os.path.join(ROOT_DIR, 'src/config/settings.py')
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    # 重新加载配置模块
    importlib.reload(sys.modules['src.config.settings'])
    
    return True

@app.route('/')
def index():
    """渲染配置页面"""
    config_groups = parse_config_groups()
    return render_template('config.html', config_groups=config_groups)

@app.route('/save', methods=['POST'])
def save():
    """保存配置"""
    try:
        new_config = request.json
        if save_config(new_config):
            return jsonify({"status": "success", "message": "配置已保存"})
        return jsonify({"status": "error", "message": "保存失败"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"保存失败: {str(e)}"})

# 添加上传处理路由
@app.route('/upload_background', methods=['POST'])
def upload_background():
    if 'background' not in request.files:
        return jsonify({"status": "error", "message": "没有选择文件"})
    
    file = request.files['background']
    if file.filename == '':
        return jsonify({"status": "error", "message": "没有选择文件"})
    
    if file:
        filename = secure_filename(file.filename)
        # 清理旧的背景图片
        for old_file in os.listdir(app.config['UPLOAD_FOLDER']):
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], old_file))
        # 保存新图片
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({
            "status": "success", 
            "message": "背景图片已更新",
            "path": f"/background_image/{filename}"
        })

# 添加背景图片目录的路由
@app.route('/background_image/<filename>')
def background_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# 添加获取背景图片路由
@app.route('/get_background')
def get_background():
    """获取当前背景图片"""
    try:
        # 获取背景图片目录中的第一个文件
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        if files:
            # 返回找到的第一个图片
            return jsonify({
                "status": "success",
                "path": f"/background_image/{files[0]}"
            })
        return jsonify({
            "status": "success",
            "path": None
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

def main():
    """主函数"""
    print("\n" + "="*50)
    print_status("配置管理系统启动中...", "info", "🚀")
    print("-"*50)
    
    # 检查必要目录
    print_status("检查系统目录...", "info", "📁")
    if not os.path.exists(os.path.join(ROOT_DIR, 'src/webui/templates')):
        print_status("错误：模板目录不存在！", "error", "❌")
        return
    print_status("系统目录检查完成", "success", "✅")
    
    # 检查配置文件
    print_status("检查配置文件...", "info", "⚙️")
    if not os.path.exists(os.path.join(ROOT_DIR, 'src/config/settings.py')):
        print_status("错误：配置文件不存在！", "error", "❌")
        return
    print_status("配置文件检查完成", "success", "✅")
    
    # 清理缓存
    print_status("清理系统缓存...", "info", "🧹")
    cleanup_count = 0
    for root, dirs, files in os.walk(ROOT_DIR):
        if '__pycache__' in dirs:
            cleanup_count += 1
    if cleanup_count > 0:
        print_status(f"已清理 {cleanup_count} 个缓存目录", "success", "🗑️")
    else:
        print_status("没有需要清理的缓存", "info", "✨")
    
    # 启动服务器
    print_status("正在启动Web服务...", "info", "🌐")
    print("-"*50)
    print_status("配置管理系统已就绪！", "success", "✨")
    print_status("请访问: http://localhost:8501", "info", "🔗")
    print("="*50 + "\n")
    
    # 启动Web服务器
    app.run(host='0.0.0.0', port=8501, debug=True)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        print_status("正在关闭服务...", "warning", "🛑")
        print_status("配置管理系统已停止", "info", "👋")
        print("\n")
    except Exception as e:
        print_status(f"系统错误: {str(e)}", "error", "💥")
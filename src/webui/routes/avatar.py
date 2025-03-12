import os
import shutil
from flask import Blueprint, jsonify, request
from pathlib import Path
import json
import re

avatar_bp = Blueprint('avatar', __name__)

AVATARS_DIR = Path('data/avatars')

def parse_md_content(content):
    """解析markdown内容为字典格式"""
    sections = {
        '任务': 'task',
        '角色': 'role',
        '外表': 'appearance',
        '经历': 'experience',
        '性格': 'personality',
        '经典台词': 'classic_lines',
        '喜好': 'preferences',
        '备注': 'notes'
    }
    
    result = {v: '' for v in sections.values()}
    current_section = None
    current_content = []
    
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('#'):
            # 更加灵活地处理标题格式
            section_name = line.lstrip('#').strip()
            if current_section and current_content:
                result[sections.get(current_section, 'notes')] = '\\n'.join(current_content)
                current_content = []
            
            current_section = section_name
            continue
            
        if current_section:
            current_content.append(line)
    
    # 处理最后一个部分
    if current_section and current_content:
        result[sections.get(current_section, 'notes')] = '\\n'.join(current_content)
    
    return result

@avatar_bp.route('/get_available_avatars')
def get_available_avatars():
    """获取所有可用的人设列表"""
    try:
        if not AVATARS_DIR.exists():
            return jsonify({'status': 'success', 'avatars': []})
            
        avatars = [d.name for d in AVATARS_DIR.iterdir() if d.is_dir()]
        return jsonify({'status': 'success', 'avatars': avatars})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@avatar_bp.route('/load_avatar_content')
def load_avatar_content():
    """加载指定人设的内容"""
    avatar = request.args.get('avatar')
    if not avatar:
        return jsonify({'status': 'error', 'message': '未指定人设名称'})
        
    try:
        avatar_dir = AVATARS_DIR / avatar
        avatar_file = avatar_dir / 'avatar.md'
        
        if not avatar_file.exists():
            return jsonify({'status': 'error', 'message': '人设文件不存在'})
            
        with open(avatar_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        parsed_content = parse_md_content(content)
        return jsonify({
            'status': 'success',
            'content': parsed_content,
            'raw_content': content
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@avatar_bp.route('/create_avatar', methods=['POST'])
def create_avatar():
    """创建新的人设"""
    try:
        data = request.get_json()
        avatar_name = data.get('avatar_name')
        
        if not avatar_name:
            return jsonify({'status': 'error', 'message': '未提供人设名称'})
            
        # 创建人设目录
        avatar_dir = AVATARS_DIR / avatar_name
        if avatar_dir.exists():
            return jsonify({'status': 'error', 'message': '该人设已存在'})
            
        # 创建目录结构
        avatar_dir.mkdir(parents=True)
        (avatar_dir / 'emojis').mkdir()
        
        # 创建avatar.md文件
        avatar_file = avatar_dir / 'avatar.md'
        template = """# 任务
请在此处描述角色的任务和目标

# 角色
请在此处描述角色的基本信息

# 外表
请在此处描述角色的外表特征

# 经历
请在此处描述角色的经历和背景故事

# 性格
请在此处描述角色的性格特点

# 经典台词
请在此处列出角色的经典台词

# 喜好
请在此处描述角色的喜好

# 备注
其他需要补充的信息
"""
        with open(avatar_file, 'w', encoding='utf-8') as f:
            f.write(template)
        
        # 更新当前使用的角色
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src', 'config', 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            current_config = json.load(f)
        
        if 'categories' not in current_config:
            current_config['categories'] = {}
        if 'behavior_settings' not in current_config['categories']:
            current_config['categories']['behavior_settings'] = {
                "title": "行为设置",
                "settings": {}
            }
        if 'context' not in current_config['categories']['behavior_settings']['settings']:
            current_config['categories']['behavior_settings']['settings']['context'] = {
                "avatar_dir": {
                    "value": f"data/avatars/{avatar_name}",
                    "type": "string",
                    "description": "人设目录（自动包含 avatar.md 和 emojis 目录）"
                }
            }
        else:
            current_config['categories']['behavior_settings']['settings']['context']['avatar_dir']['value'] = f"data/avatars/{avatar_name}"
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(current_config, f, ensure_ascii=False, indent=4)
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@avatar_bp.route('/delete_avatar', methods=['POST'])
def delete_avatar():
    """删除人设"""
    try:
        data = request.get_json()
        avatar_name = data.get('avatar_name')
        
        if not avatar_name:
            return jsonify({'status': 'error', 'message': '未提供人设名称'})
            
        avatar_dir = AVATARS_DIR / avatar_name
        if not avatar_dir.exists():
            return jsonify({'status': 'error', 'message': '人设不存在'})
            
        # 删除整个人设目录
        shutil.rmtree(avatar_dir)
        return jsonify({'status': 'success', 'message': '人设已删除'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@avatar_bp.route('/save_avatar', methods=['POST'])
def save_avatar():
    """保存人设设定"""
    data = request.get_json()
    avatar_name = data.get('avatar')
    
    if not avatar_name:
        return jsonify({'status': 'error', 'message': '未提供人设名称'})
    
    try:
        avatar_dir = AVATARS_DIR / avatar_name
        avatar_file = avatar_dir / 'avatar.md'
        
        if not avatar_dir.exists():
            return jsonify({'status': 'error', 'message': '人设目录不存在'})
        
        # 获取前端传递的数据
        task = data.get('task', '')
        role = data.get('role', '')
        appearance = data.get('appearance', '')
        experience = data.get('experience', '')
        personality = data.get('personality', '')
        classic_lines = data.get('classic_lines', '')
        preferences = data.get('preferences', '')
        notes = data.get('notes', '')
        
        # 构建新的 markdown 内容
        content = ""

        # Helper function to append content with proper escaping
        def append_section(title, text):
            nonlocal content
            content += f"# {title}\\n"
            # Escape any heading-like sequence at the beginning of a line
            escaped_text = re.sub(r'(^|\n)(#+)', r'\1\\\2', text)
            content += escaped_text + "\\n\\n"

        append_section('任务', task)
        append_section('角色', role)
        append_section('外表', appearance)
        append_section('经历', experience)
        append_section('性格', personality)
        append_section('经典台词', classic_lines)
        append_section('喜好', preferences)
        append_section('备注', notes)
        
        # 保存文件
        with open(avatar_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 更新当前使用的角色
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src', 'config', 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            current_config = json.load(f)
        
        if 'categories' not in current_config:
            current_config['categories'] = {}
        if 'behavior_settings' not in current_config['categories']:
            current_config['categories']['behavior_settings'] = {
                "title": "行为设置",
                "settings": {}
            }
        if 'context' not in current_config['categories']['behavior_settings']['settings']:
            current_config['categories']['behavior_settings']['settings']['context'] = {
                "avatar_dir": {
                    "value": f"data/avatars/{avatar_name}",
                    "type": "string",
                    "description": "人设目录（自动包含 avatar.md 和 emojis 目录）"
                }
            }
        else:
            current_config['categories']['behavior_settings']['settings']['context']['avatar_dir']['value'] = f"data/avatars/{avatar_name}"
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(current_config, f, ensure_ascii=False, indent=4)
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@avatar_bp.route('/save_avatar_raw', methods=['POST'])
def save_avatar_raw():
    """保存原始Markdown内容"""
    try:
        data = request.get_json()
        avatar_name = data.get('avatar')
        content = data.get('content')
        
        if not avatar_name:
            return jsonify({'status': 'error', 'message': '未提供人设名称'})
        
        if content is None:
            return jsonify({'status': 'error', 'message': '未提供内容'})
        
        avatar_dir = AVATARS_DIR / avatar_name
        avatar_file = avatar_dir / 'avatar.md'
        
        if not avatar_dir.exists():
            return jsonify({'status': 'error', 'message': '人设目录不存在'})
        
        # 保存原始内容
        with open(avatar_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 更新当前使用的角色
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src', 'config', 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            current_config = json.load(f)
        
        if 'categories' not in current_config:
            current_config['categories'] = {}
        if 'behavior_settings' not in current_config['categories']:
            current_config['categories']['behavior_settings'] = {
                "title": "行为设置",
                "settings": {}
            }
        if 'context' not in current_config['categories']['behavior_settings']['settings']:
            current_config['categories']['behavior_settings']['settings']['context'] = {
                "avatar_dir": {
                    "value": f"data/avatars/{avatar_name}",
                    "type": "string",
                    "description": "人设目录（自动包含 avatar.md 和 emojis 目录）"
                }
            }
        else:
            current_config['categories']['behavior_settings']['settings']['context']['avatar_dir']['value'] = f"data/avatars/{avatar_name}"
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(current_config, f, ensure_ascii=False, indent=4)
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

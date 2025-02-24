import os
import json
from flask import Blueprint, request, jsonify, render_template
from src.config import config

avatar_manager = Blueprint('avatar_manager', __name__)

@avatar_manager.route('/load_avatar', methods=['GET'])
def load_avatar():
    """加载 avatar.md 内容"""
    avatar_path = os.path.join(config.behavior.context.avatar_dir, 'avatar.md')
    if not os.path.exists(avatar_path):
        return jsonify({'status': 'error', 'message': '文件不存在'})

    with open(avatar_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 将内容分割成不同区域
    sections = {}
    for section in ['任务', '角色', '外表', '经历', '性格']:
        start = content.find(section)
        end = content.find('\n#', start + 1) if start != -1 else -1
        sections[section] = content[start:end].strip() if start != -1 else ''

    return jsonify({'status': 'success', 'content': sections})

@avatar_manager.route('/save_avatar', methods=['POST'])
def save_avatar():
    """保存 avatar.md 内容"""
    data = request.json
    avatar_path = os.path.join(config.behavior.context.avatar_dir, 'avatar.md')

    if not os.path.exists(avatar_path):
        return jsonify({'status': 'error', 'message': '文件不存在'})

    # 重新构建内容
    content = ""
    for section in ['任务', '角色', '外表', '经历', '性格']:
        content += f"# {section}\n{data.get(section.lower(), '')}\n\n"

    with open(avatar_path, 'w', encoding='utf-8') as f:
        f.write(content.strip())

    return jsonify({'status': 'success', 'message': '保存成功'})

@avatar_manager.route('/edit_avatar', methods=['GET'])
def edit_avatar():
    """角色设定页面"""
    return render_template('edit_avatar.html')
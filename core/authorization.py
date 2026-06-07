import json
import os
import time
from pathlib import Path
from astrbot.api import logger

def get_astrbot_plugin_data_path():
    data_path = None
    try:
        from astrbot.core.utils.astrbot_path import get_astrbot_data_path
        data_path = get_astrbot_data_path()
    except Exception as e:
        logger.error(f"获取 AstrBot 数据目录失败: {e}")
    
    if data_path:
        return Path(data_path)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    return Path(parent_dir)

def get_auth_file():
    data_path = get_astrbot_plugin_data_path() / "plugin_data" / "auth"
    data_path.mkdir(parents=True, exist_ok=True)
    return str(data_path / "auth.json")

def load_auth_data() -> dict:
    auth_file = get_auth_file()
    try:
        if os.path.exists(auth_file):
            with open(auth_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"加载授权数据失败: {e}")
    return {"groups": {}}

def save_auth_data(data: dict):
    auth_file = get_auth_file()
    try:
        with open(auth_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存授权数据失败: {e}")

def is_group_authorized(group_id: str) -> bool:
    data = load_auth_data()
    if group_id not in data.get("groups", {}):
        return False
    expire = data["groups"][group_id].get("expire", 0)
    return expire > time.time()

def get_group_auth_info(group_id: str) -> dict:
    data = load_auth_data()
    return data.get("groups", {}).get(group_id, {})

def get_remaining_time(group_id: str) -> int:
    data = load_auth_data()
    if group_id not in data.get("groups", {}):
        return 0
    expire = data["groups"][group_id].get("expire", 0)
    remaining = expire - time.time()
    return max(0, int(remaining))

def format_time(seconds: int) -> str:
    if seconds <= 0:
        return "已过期"
    
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分钟")
    
    return "".join(parts) if parts else "1分钟内"

import json
import os
import time
from typing import Dict, Any


class DataManager:
    """数据管理核心类"""

    def __init__(self, plugin_dir: str, plugin_settings: Dict = None):
        self.plugin_dir = plugin_dir
        self.plugin_settings = plugin_settings or {}
        self.global_config = self._load_global_config()
        self._sync_settings_to_config()
        self.groups_data = self._load_all_groups_data()
        self._schedule_cleanup()

    def _sync_settings_to_config(self):
        """将插件设置同步到全局配置"""
        settings_mapping = {
            'enable_group_settings': 'enable_group_settings',
            'enable_global_settings': 'enable_global_settings',
            'owner_ids': 'owner_ids',
            'admin_roles': 'admin_roles',
            'auto_approve': 'auto_approve',
            'approval_max_attempts': 'approval_max_attempts',
            'approval_kick_on_fail': 'approval_kick_on_fail',
            'anti_spam_enabled': 'anti_spam_enabled',
            'spam_threshold': 'spam_threshold',
            'spam_time_window': 'spam_time_window',
            'default_mute_duration': 'default_mute_duration',
            'default_mute_reason': 'default_mute_reason',
            'default_kick_reason': 'default_kick_reason',
            'kick_recall_messages': 'kick_recall_messages',
            'kick_recall_count': 'kick_recall_count',
            'max_recall_count': 'max_recall_count',
            'allow_self_recall': 'allow_self_recall',
            'welcome_enabled': 'welcome_enabled',
            'welcome_messages': 'welcome_messages',
            'auto_reply_enabled': 'auto_reply_enabled',
            'auto_reply_cooldown': 'auto_reply_cooldown',
            'auto_reply_ignore_admin': 'auto_reply_ignore_admin',
            'sign_enabled': 'sign_enabled',
            'sign_bonus_points': 'sign_bonus_points',
            'sign_continuous_bonus': 'sign_continuous_bonus',
            'allow_self_reply': 'allow_self_reply',
            'auto_clean_expired': 'auto_clean_expired',
            'command_aliases': 'command_aliases',
            'custom_admins': 'custom_admins'
        }

        for setting_key, config_key in settings_mapping.items():
            if setting_key in self.plugin_settings:
                self.global_config[config_key] = self.plugin_settings[setting_key]

        self._save_global_config()

    def update_settings(self, settings: Dict):
        """更新插件设置并同步到配置文件"""
        self.plugin_settings = settings
        self._sync_settings_to_config()

    def _get_group_file_path(self, filename: str) -> str:
        """获取数据文件路径"""
        return os.path.join(self.plugin_dir, filename)

    def _load_global_config(self) -> Dict:
        """加载全局配置"""
        path = self._get_group_file_path('global_config.json')
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                from astrbot.api import logger
                logger.error(f"加载全局配置失败: {e}")
                return self._get_default_global_config()
        return self._get_default_global_config()

    def _get_default_global_config(self) -> Dict:
        """获取默认全局配置"""
        return {
            'version': '3.1.0',
            'owner_ids': [],
            'enable_group_settings': False,
            'enable_global_settings': True,
            'admin_roles': ['群主', '管理员'],
            'auto_approve': False,
            'approval_max_attempts': 3,
            'approval_kick_on_fail': False,
            'anti_spam_enabled': True,
            'spam_threshold': 5,
            'spam_time_window': 60,
            'default_mute_duration': 30,
            'default_mute_reason': '违规发言',
            'default_kick_reason': '违规发言',
            'kick_recall_messages': True,
            'kick_recall_count': 10,
            'max_recall_count': 10,
            'allow_self_recall': False,
            'welcome_enabled': True,
            'welcome_messages': [],
            'welcome_random': False,
            'auto_reply_enabled': False,
            'auto_reply_cooldown': 5,
            'auto_reply_ignore_admin': True,
            'sign_enabled': True,
            'sign_bonus_points': 10,
            'sign_continuous_bonus': 5,
            'allow_self_reply': False,
            'auto_clean_expired': True,
            'custom_admins': [],
            'command_aliases': {
                '审核': ['审批'],
                '黑名单': ['黑名', '拉黑', '封禁'],
                '禁言': ['静音', '闭嘴'],
                '解封': ['解禁'],
                '踢出': ['踢人', '移除'],
                '撤回': ['删除', '收回'],
                '欢迎': ['欢迎语'],
                '回复': ['私信'],
                '自动回复': ['自动'],
                '定时消息': ['定时'],
                '签到': ['打卡'],
                '排行榜': ['排行', '排名'],
                '统计': ['数据'],
                '设置': ['配置'],
                '全局设置': ['全局配置'],
                '群管帮助': ['帮助', '帮助菜单']
            }
        }

    def _save_global_config(self) -> bool:
        """保存全局配置"""
        path = self._get_group_file_path('global_config.json')
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.global_config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            from astrbot.api import logger
            logger.error(f"保存全局配置失败: {e}")
            return False

    def get_global_config(self) -> Dict:
        """获取全局配置"""
        return self.global_config.copy()

    def set_global_config(self, key: str, value: Any) -> bool:
        """设置全局配置"""
        if key in self.global_config:
            self.global_config[key] = value
            return self._save_global_config()
        return False

    def reset_global_config(self) -> bool:
        """重置全局配置为默认值"""
        self.global_config = self._get_default_global_config()
        return self._save_global_config()

    def is_group_settings_enabled(self) -> bool:
        """检查是否启用分群设置"""
        return self.global_config.get('enable_group_settings', False)

    def get_effective_config(self, group_id: str) -> Dict:
        """获取群的有效配置"""
        if not self.is_group_settings_enabled():
            return self.get_global_config()
        
        group_config = self._get_group_data(group_id, 'config', {})
        global_config = self.get_global_config()
        
        merged_config = global_config.copy()
        merged_config.update(group_config)
        
        return merged_config

    def _load_all_groups_data(self) -> Dict:
        """加载所有群的数据"""
        groups_data = {}

        file_mapping = {
            'config.json': 'config',
            'blacklist.json': 'blacklist',
            'auto_replies.json': 'auto_replies',
            'scheduled.json': 'scheduled_messages',
            'user_stats.json': 'user_stats',
            'muted_users.json': 'muted_users',
            'invitations.json': 'invitations',
            'verification.json': 'verification',
            'kick_logs.json': 'kick_logs',
            'recall_logs.json': 'recall_logs',
            'reply_logs.json': 'reply_logs',
            'reply_templates.json': 'reply_templates',
            'user_titles.json': 'user_titles'
        }

        for filename, key in file_mapping.items():
            path = self._get_group_file_path(filename)
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, dict) and key not in ['config']:
                            groups_data[key] = data
                        else:
                            groups_data[key] = {'default': data} if key in ['config'] else data
                except Exception as e:
                    from astrbot.api import logger
                    logger.error(f"加载 {filename} 失败: {e}")
                    groups_data[key] = {}
            else:
                groups_data[key] = {}

        return groups_data

    def _get_default_data(self, data_type: str, default_value: Any):
        """获取默认数据结构"""
        if data_type == 'config':
            return {
                'welcome_enabled': False,
                'welcome_messages': [
                    "欢迎 {user_name} 加入本群！",
                    "请遵守群规，文明发言~"
                ],
                'auto_approve': False,
                'anti_spam_enabled': False,
                'spam_threshold': 5,
                'spam_time_window': 60,
                'admin_roles': ['群主', '管理员'],
                'sign_enabled': False,
                'auto_reply_enabled': False,
                'default_mute_duration': 30,
                'default_mute_reason': '违规发言',
                'default_kick_reason': '违规发言',
                'allow_self_recall': False,
                'max_recall_count': 10,
                'welcome_random': False,
                'allow_self_reply': True
            }
        elif data_type == 'blacklist':
            return {'users': [], 'words': []}
        elif data_type == 'auto_replies':
            return {}
        elif data_type == 'scheduled_messages':
            return []
        elif data_type == 'user_stats':
            return {}
        elif data_type == 'muted_users':
            return []
        elif data_type == 'invitations':
            return {}
        elif data_type == 'verification':
            return {
                'enabled': True,
                'mode': 'manual',
                'questions': [
                    {'question': '本群是做什么的？', 'answer': '交流学习'},
                    {'question': '请输入暗号', 'answer': '666'}
                ],
                'keywords': ['学习', '交流', '技术'],
                'invite_codes': ['VIP2024', 'ADMIN', 'TEST'],
                'auto_approve_condition': {
                    'min_age_days': 0,
                    'must_have_avatar': False
                }
            }
        elif data_type == 'kick_logs':
            return []
        elif data_type == 'recall_logs':
            return []
        elif data_type == 'reply_logs':
            return []
        elif data_type == 'reply_templates':
            return {}
        elif data_type == 'user_titles':
            return {}
        return default_value

    def _get_group_data(self, group_id: str, data_type: str, default_value: Any):
        """获取指定群的数据"""
        if group_id is None or group_id == '':
            group_id = 'default'

        if data_type not in self.groups_data:
            self.groups_data[data_type] = {}
        if group_id not in self.groups_data[data_type]:
            self.groups_data[data_type][group_id] = self._get_default_data(data_type, default_value)
        return self.groups_data[data_type][group_id]

    def _set_group_data(self, data_type: str, data: Any, group_id: str):
        """设置指定群的数据"""
        if group_id is None or group_id == '':
            group_id = 'default'

        if data_type not in self.groups_data:
            self.groups_data[data_type] = {}
        self.groups_data[data_type][group_id] = data

    def _save_group_data(self, data_type: str):
        """保存分群数据"""
        filename_mapping = {
            'config': 'config.json',
            'blacklist': 'blacklist.json',
            'auto_replies': 'auto_replies.json',
            'scheduled_messages': 'scheduled.json',
            'user_stats': 'user_stats.json',
            'muted_users': 'muted_users.json',
            'invitations': 'invitations.json',
            'verification': 'verification.json',
            'kick_logs': 'kick_logs.json',
            'recall_logs': 'recall_logs.json',
            'reply_logs': 'reply_logs.json',
            'reply_templates': 'reply_templates.json',
            'user_titles': 'user_titles.json'
        }

        filename = filename_mapping.get(data_type, f'{data_type}.json')
        path = self._get_group_file_path(filename)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.groups_data.get(data_type, {}), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            from astrbot.api import logger
            logger.error(f"保存 {filename} 失败: {e}")
            return False

    def _save_group_config(self, group_id: str, key: str, value: Any):
        """保存群配置"""
        config = self._get_group_data(group_id, 'config', {})
        config[key] = value
        self._set_group_data('config', config, group_id)
        self._save_group_data('config')

    def _cleanup_all_expired_bans(self):
        """清理所有群的过期封禁"""
        groups_to_check = ['default'] if not self.is_group_settings_enabled() else self.groups_data.get('blacklist', {}).keys()

        for group_id in groups_to_check:
            blacklist = self.groups_data.get('blacklist', {}).get(group_id, {'users': [], 'words': []})
            current_time = time.time()
            expired_users = []
            for user in blacklist.get('users', []):
                if user.get('expire_time') and not user.get('permanent'):
                    try:
                        expire_timestamp = time.mktime(time.strptime(user['expire_time'], "%Y-%m-%d %H:%M:%S"))
                        if current_time > expire_timestamp:
                            expired_users.append(user['qq'])
                    except Exception:
                        pass
            if expired_users:
                blacklist['users'] = [u for u in blacklist['users'] if u['qq'] not in expired_users]
                if group_id not in self.groups_data['blacklist']:
                    self.groups_data['blacklist'][group_id] = blacklist
                from astrbot.api import logger
                logger.info(f"群 {group_id} 已自动清理 {len(expired_users)} 个过期封禁")
        self._save_group_data('blacklist')

    def _cleanup_all_expired_mutes(self):
        """清理所有群的过期禁言"""
        groups_to_check = ['default'] if not self.is_group_settings_enabled() else self.groups_data.get('muted_users', {}).keys()

        for group_id in groups_to_check:
            muted_users = self.groups_data.get('muted_users', {}).get(group_id, [])
            current_time = time.time()
            cleaned = [
                u for u in muted_users
                if u.get('expire_time') is None or
                time.mktime(time.strptime(u['expire_time'], "%Y-%m-%d %H:%M:%S")) > current_time
            ]
            if group_id not in self.groups_data['muted_users']:
                self.groups_data['muted_users'][group_id] = cleaned
            else:
                self.groups_data['muted_users'][group_id] = cleaned
        self._save_group_data('muted_users')

    def _save_recall_log(self, group_id: str, operator: str, target_user: str, reason: str):
        """保存撤回日志"""
        if not self.is_group_settings_enabled():
            group_id = 'default'

        recall_logs = self._get_group_data(group_id, 'recall_logs', [])
        recall_logs.insert(0, {
            'operator': operator,
            'target_user': target_user,
            'reason': reason,
            'time': time.strftime("%Y-%m-%d %H:%M:%S")
        })
        if len(recall_logs) > 100:
            recall_logs = recall_logs[:100]
        self._save_group_data('recall_logs')

    def _schedule_cleanup(self):
        """执行清理过期数据"""
        if self.global_config.get('auto_clean_expired', True):
            self._cleanup_all_expired_bans()
            self._cleanup_all_expired_mutes()

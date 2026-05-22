from astrbot.api.event import AstrMessageEvent
from .data_manager import DataManager


class Utils:
    """工具类"""

    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager

    def _get_group_id(self, event: AstrMessageEvent) -> str:
        """从事件获取群ID"""
        try:
            return str(event.get_group_id())
        except Exception:
            return 'default'

    def _get_user_id(self, event: AstrMessageEvent) -> str:
        """从事件获取用户ID"""
        try:
            return str(event.get_sender_id())
        except Exception:
            return "unknown"

    def _is_owner(self, event: AstrMessageEvent) -> bool:
        """检查是否是机器人主人（不受权限限制）"""
        try:
            # 获取全局配置中的主人ID列表
            global_config = self.data_manager.get_global_config()
            owner_ids = global_config.get('owner_ids', [])
            
            if not isinstance(owner_ids, list):
                owner_ids = []
            
            user_id = self._get_user_id(event)
            return user_id in owner_ids
        except Exception:
            return False

    def _is_admin(self, event: AstrMessageEvent) -> bool:
        """检查是否是管理员（主人或群管理员/群主）"""
        # 机器人主人不受任何权限限制
        if self._is_owner(event):
            return True
        
        # 检查是否是群管理员或群主
        try:
            group_id = self._get_group_id(event)
            config = self.data_manager._get_group_data(group_id, 'config', {})
            sender_role = event.get_sender_role()
            return sender_role in config.get('admin_roles', ['群主', '管理员'])
        except Exception:
            return False

    def _is_group_admin(self, event: AstrMessageEvent) -> bool:
        """仅检查是否是群管理员/群主（不包括主人）"""
        try:
            group_id = self._get_group_id(event)
            config = self.data_manager._get_group_data(group_id, 'config', {})
            sender_role = event.get_sender_role()
            return sender_role in config.get('admin_roles', ['群主', '管理员'])
        except Exception:
            return False

    def _is_group_custom_admin(self, event: AstrMessageEvent) -> bool:
        """检查是否是分群自定义管理员"""
        try:
            group_id = self._get_group_id(event)
            user_id = self._get_user_id(event)
            config = self.data_manager._get_group_data(group_id, 'config', {})
            custom_admins = config.get('custom_admins', [])
            return user_id in custom_admins
        except Exception:
            return False

    def _is_owner_by_id(self, user_id: str) -> bool:
        """根据用户ID检查是否是机器人主人"""
        try:
            global_config = self.data_manager.get_global_config()
            owner_ids = global_config.get('owner_ids', [])
            
            if not isinstance(owner_ids, list):
                owner_ids = []
            
            return user_id in owner_ids
        except Exception:
            return False

    def _has_group_permission(self, event: AstrMessageEvent) -> bool:
        """检查是否有群管理权限（主人、群管理员、分群自定义管理员）"""
        if self._is_owner(event):
            return True
        if self._is_group_admin(event):
            return True
        if self._is_group_custom_admin(event):
            return True
        return False

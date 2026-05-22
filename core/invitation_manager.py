from typing import Dict, List
from .data_manager import DataManager


class InvitationManager:
    """邀请关系管理类"""

    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager

    def _record_invitation(self, group_id: str, inviter_id: str, invited_id: str):
        """记录邀请关系"""
        invitations = self.data_manager._get_group_data(group_id, 'invitations', {})
        if inviter_id not in invitations:
            invitations[inviter_id] = []
        if invited_id not in invitations[inviter_id]:
            invitations[inviter_id].append(invited_id)
        self.data_manager._save_group_data('invitations')

    def _get_invited_users(self, group_id: str, user_id: str) -> List[str]:
        """获取用户邀请的所有成员"""
        invitations = self.data_manager._get_group_data(group_id, 'invitations', {})
        return invitations.get(user_id, [])

    def _get_inviter_of(self, group_id: str, user_id: str) -> str | None:
        """获取邀请人"""
        invitations = self.data_manager._get_group_data(group_id, 'invitations', {})
        for inviter, invited_list in invitations.items():
            if user_id in invited_list:
                return inviter
        return None

    def _remove_user_from_invitations(self, group_id: str, user_id: str):
        """从邀请关系中移除用户"""
        invitations = self.data_manager._get_group_data(group_id, 'invitations', {})
        for inviter in invitations:
            if user_id in invitations[inviter]:
                invitations[inviter].remove(user_id)
        self.data_manager._save_group_data('invitations')

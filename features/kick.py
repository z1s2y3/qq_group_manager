from astrbot.api.event import AstrMessageEvent, filter
from typing import Dict, List, Optional
import time

from ..core.data_manager import DataManager
from ..core.utils import Utils
from ..core.invitation_manager import InvitationManager


class KickFeature:
    """踢出管理功能"""

    def __init__(self, data_manager: DataManager, utils: Utils, invitation_manager: InvitationManager, context=None, message_history=None):
        self.data_manager = data_manager
        self.utils = utils
        self.invitation_manager = invitation_manager
        self.context = context
        self.message_history = message_history or {}

    async def _kick_member(self, group_id: int, user_id: int, reject_add_request: bool = False) -> bool:
        """执行实际的踢出操作"""
        try:
            if self.context:
                await self.context.call_api(
                    "set_group_kick",
                    group_id=group_id,
                    user_id=user_id,
                    reject_add_request=reject_add_request
                )
                return True
            return False
        except Exception as e:
            from astrbot.api import logger
            logger.error(f"踢出失败: {e}")
            return False

    async def _recall_message(self, message_id: int) -> bool:
        """执行实际的消息撤回操作"""
        try:
            if self.context:
                await self.context.call_api("delete_msg", message_id=message_id)
                return True
            return False
        except Exception as e:
            from astrbot.api import logger
            logger.error(f"撤回消息失败: {e}")
            return False

    def _get_user_messages(self, group_id: str, user_id: str) -> list:
        """获取指定用户的所有消息"""
        if group_id not in self.message_history:
            return []
        # 获取该用户的所有消息，不限于类型
        return [msg for msg in self.message_history[group_id] if msg['user_id'] == user_id]

    async def _recall_all_user_messages(self, group_id: str, user_id: str) -> int:
        """撤回指定用户的所有消息（不限于转发、名片等）"""
        messages = self._get_user_messages(group_id, user_id)
        success_count = 0
        for msg in messages:
            if await self._recall_message(msg['message_id']):
                success_count += 1
        return success_count

    @filter.command("踢出")
    async def command(self, event: AstrMessageEvent):
        # 检查授权（主人、白名单群自动通过）
        if not self.utils._is_group_authorized(event):
            yield event.plain_result("❌ 本群尚未授权，请联系机器人主人进行 SCUM 授权")
            return
        
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        config = self.data_manager.get_effective_config(group_id)
        kick_logs = self.data_manager._get_group_data(group_id, 'kick_logs', [])
        operator_id = self.utils._get_user_id(event)
        operator_name = event.get_sender_name() or '管理员'
        at_user = config.get('kick_at_user', False)

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("""📋 踢出命令使用方法:
/踢出 <QQ> - 踢出用户
/踢出 <QQ> <理由> - 踢出用户并指定理由
/踢出 连带 <QQ> - 踢出用户及其邀请的所有成员
/查看踢出记录 - 查看踢出记录""")
            return

        # 连带踢出
        if args[1] == '连带':
            if len(args) < 3:
                yield event.plain_result("❌ 使用方法: /踢出 连带 <QQ>")
                return

            user_id = args[2]
            if not user_id.isdigit():
                yield event.plain_result("❌ 请输入有效的QQ号")
                return

            # 先撤回用户的所有消息
            recalled_count = await self._recall_all_user_messages(group_id, user_id)

            invited_users = self.invitation_manager._get_invited_users(group_id, user_id)

            success = await self._kick_member(int(group_id), int(user_id), False)

            kicked_count = 1
            for invited in invited_users:
                if invited != user_id:
                    await self._kick_member(int(group_id), int(invited), False)
                    kicked_count += 1

            kick_logs.insert(0, {
                'qq': user_id,
                'operator_id': operator_id,
                'operator_name': operator_name,
                'action': 'chain_kick',
                'reason': '连带踢出',
                'time': time.strftime("%Y-%m-%d %H:%M:%S")
            })
            if len(kick_logs) > 100:
                kick_logs = kick_logs[:100]
            self.data_manager._save_group_data('kick_logs')

            recall_msg = f"，已撤回{recalled_count}条消息" if recalled_count > 0 else ""
            at_prefix = f"[CQ:at,qq={user_id}] " if at_user else ""
            if kicked_count > 1:
                yield event.plain_result(f"{at_prefix}👢 已踢出 {user_id} 及其邀请的 {kicked_count - 1} 名成员{recall_msg}")
            else:
                yield event.plain_result(f"{at_prefix}👢 已踢出 {user_id}{recall_msg}")
            return

        # 普通踢出
        user_id = args[1]
        if not user_id.isdigit():
            yield event.plain_result("❌ 请输入有效的QQ号")
            return

        reason = ' '.join(args[2:]) if len(args) > 2 else config.get('default_kick_reason', '违规发言')

        # 先撤回用户的所有消息
        recalled_count = await self._recall_all_user_messages(group_id, user_id)

        success = await self._kick_member(int(group_id), int(user_id), False)

        kick_logs.insert(0, {
            'qq': user_id,
            'operator_id': operator_id,
            'operator_name': operator_name,
            'action': 'kick',
            'reason': reason,
            'time': time.strftime("%Y-%m-%d %H:%M:%S")
        })
        if len(kick_logs) > 100:
            kick_logs = kick_logs[:100]
        self.data_manager._save_group_data('kick_logs')

        recall_msg = f"，已撤回{recalled_count}条消息" if recalled_count > 0 else ""
        at_prefix = f"[CQ:at,qq={user_id}] " if at_user else ""
        if success:
            yield event.plain_result(f"{at_prefix}👢 已踢出 {user_id}，理由: {reason}{recall_msg}")
        else:
            yield event.plain_result(f"{at_prefix}⚠️ 记录已更新{recall_msg}，但踢出API调用失败")

    @filter.command("查看踢出记录")
    async def show_kick_log_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        kick_logs = self.data_manager._get_group_data(group_id, 'kick_logs', [])

        if not kick_logs:
            yield event.plain_result("📋 暂无踢出记录")
            return

        log_lines = []
        for i, log in enumerate(kick_logs, 1):
            action_str = "连带踢出" if log['action'] == 'chain_kick' else "踢出"
            operator_info = f" (操作者: {log.get('operator_name', '未知')} [{log.get('operator_id', '')}])"
            log_lines.append(f"{i}. 时间: {log['time']}\n   被踢: {log['qq']}\n   操作: {action_str}\n   理由: {log['reason']}{operator_info}")

        result = f"📋 踢出记录 (共{len(kick_logs)}条):\n"
        result += '\n' + '\n'.join(log_lines)
        yield event.plain_result(result)

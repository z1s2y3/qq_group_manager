from astrbot.api.event import AstrMessageEvent, filter
from typing import Dict, List
import time

from ..core.data_manager import DataManager
from ..core.utils import Utils


class BlacklistFeature:
    """黑名单管理功能"""

    def __init__(self, data_manager: DataManager, utils: Utils, context=None):
        self.data_manager = data_manager
        self.utils = utils
        self.context = context

    async def _kick_member(self, group_id: int, user_id: int) -> bool:
        """执行实际的踢出操作"""
        try:
            if self.context:
                await self.context.call_api(
                    "set_group_kick",
                    group_id=group_id,
                    user_id=user_id,
                    reject_add_request=True
                )
                return True
            return False
        except Exception as e:
            from astrbot.api import logger
            logger.error(f"踢出失败: {e}")
            return False

    def is_user_blacklisted(self, group_id: int, user_id: str) -> bool:
        """检查用户是否在黑名单中"""
        blacklist = self.data_manager._get_group_data(group_id, 'blacklist', {'users': []})
        return any(u['qq'] == user_id for u in blacklist['users'])

    @filter.command("黑名单")
    async def command(self, event: AstrMessageEvent):
        # 检查授权（主人、白名单群自动通过）
        if not self.utils._is_group_authorized(event):
            yield event.plain_result("❌ 本群尚未授权，请联系机器人主人进行 SCUM 授权")
            return
        
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        blacklist = self.data_manager._get_group_data(group_id, 'blacklist', {'users': []})

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("""📋 黑名单命令:
/拉黑 <QQ> [理由] - 拉黑用户
/删黑 <QQ> - 移除黑名单
/清空黑名单 - 清空黑名单
/查看黑名单 - 查看列表""")
            return

    @filter.command("拉黑")
    async def blacklist_command(self, event: AstrMessageEvent):
        """拉黑用户"""
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        blacklist = self.data_manager._get_group_data(group_id, 'blacklist', {'users': []})
        config = self.data_manager.get_effective_config(group_id)
        at_user = config.get('blacklist_at_user', False)

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("📋 使用方法:\n/拉黑 <QQ> - 拉黑用户\n/拉黑 <QQ> <理由> - 拉黑用户并指定理由")
            return

        user_id = args[1]
        reason = ' '.join(args[2:]) if len(args) > 2 else "违规发言"

        existing = next((u for u in blacklist['users'] if u['qq'] == user_id), None)
        if not existing:
            user_entry = {
                'qq': user_id,
                'reason': reason,
                'time': time.strftime("%Y-%m-%d %H:%M:%S"),
                'added_by': event.get_sender_name() or 'admin'
            }
            blacklist['users'].append(user_entry)
            self.data_manager._save_group_data('blacklist')

        success = await self._kick_member(int(group_id), int(user_id))

        at_prefix = f"[CQ:at,qq={user_id}] " if at_user else ""
        if success:
            yield event.plain_result(f"{at_prefix}🚫 已将 {user_id} 拉黑并踢出，理由: {reason}")
        else:
            yield event.plain_result(f"{at_prefix}⚠️ 已将 {user_id} 加入黑名单，但踢出失败")

    @filter.command("删黑")
    async def remove_blacklist_command(self, event: AstrMessageEvent):
        """删除黑名单用户"""
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        blacklist = self.data_manager._get_group_data(group_id, 'blacklist', {'users': []})
        config = self.data_manager.get_effective_config(group_id)
        at_user = config.get('blacklist_at_user', False)

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("📋 使用方法:\n/删黑 <QQ> - 从黑名单移除用户")
            return

        user_id = args[1]
        original_count = len(blacklist['users'])
        blacklist['users'] = [u for u in blacklist['users'] if u['qq'] != user_id]

        if len(blacklist['users']) < original_count:
            self.data_manager._save_group_data('blacklist')
            at_prefix = f"[CQ:at,qq={user_id}] " if at_user else ""
            yield event.plain_result(f"{at_prefix}✅ 已将 {user_id} 从黑名单移除")
        else:
            yield event.plain_result(f"⚠️ {user_id} 不在黑名单中")

    @filter.command("清空黑名单")
    async def clear_blacklist_command(self, event: AstrMessageEvent):
        """清空黑名单"""
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        blacklist = self.data_manager._get_group_data(group_id, 'blacklist', {'users': []})

        if not blacklist['users']:
            yield event.plain_result("⚠️ 黑名单已经是空的")
            return

        blacklist['users'] = []
        self.data_manager._save_group_data('blacklist')
        yield event.plain_result("🗑️ 已清空黑名单")

    @filter.command("查看黑名单")
    async def list_blacklist_command(self, event: AstrMessageEvent):
        """查看黑名单列表"""
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        blacklist = self.data_manager._get_group_data(group_id, 'blacklist', {'users': []})

        if not blacklist['users']:
            yield event.plain_result("📋 黑名单: 无")
            return

        user_lines = []
        for i, u in enumerate(blacklist['users'], 1):
            user_lines.append(f"{i}. {u['qq']} | {u['reason']} | {u['time']}")

        result = f"📋 黑名单 ({len(blacklist['users'])}人):\n"
        result += '\n'.join(user_lines)
        yield event.plain_result(result)

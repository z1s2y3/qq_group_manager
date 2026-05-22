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

    def _get_user_messages(self, group_id: str, user_id: str, count: int = 100) -> list:
        """获取指定用户的所有消息"""
        if group_id not in self.message_history:
            return []
        return [msg for msg in self.message_history[group_id] if msg['user_id'] == user_id][-count:]

    async def _recall_user_messages(self, group_id: str, user_id: str) -> int:
        """撤回指定用户的所有消息"""
        messages = self._get_user_messages(group_id, user_id, 100)
        success_count = 0
        for msg in messages:
            if await self._recall_message(msg['message_id']):
                success_count += 1
        return success_count

    @filter.command("踢出")
    async def command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        config = self.data_manager._get_group_data(group_id, 'config', {})
        kick_logs = self.data_manager._get_group_data(group_id, 'kick_logs', [])
        recall_logs = self.data_manager._get_group_data(group_id, 'recall_logs', [])

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("""📋 踢出命令使用方法:
👢 基本操作:
/踢出 <QQ> [理由] - 踢出用户(可重新加入)
/踢出 连带 <QQ> [理由] - 踢出用户及其邀请的所有成员

🚫 拉黑踢出:
/拉黑踢出 <QQ> [理由] - 拉黑并踢出(不可重新加入)

📖 其他命令:
/踢出记录 [页码] - 查看踢出记录
/踢出搜索 <关键词> - 搜索踢出记录""")
            return

        action = args[1].lower()

        # 连带踢出
        if action == '连带':
            if len(args) < 3:
                yield event.plain_result("❌ 使用方法: /踢出 连带 <QQ> [理由]")
                return

            user_id = args[2]
            
            if not user_id.isdigit():
                yield event.plain_result("❌ 请输入有效的QQ号")
                return

            reason = ' '.join(args[3:]) if len(args) > 3 else config.get('default_kick_reason', '违规发言')

            # 先撤回用户消息
            recalled_count = await self._recall_user_messages(group_id, user_id)
            if recalled_count > 0:
                recall_logs.insert(0, {
                    'operator': self.utils._get_user_id(event),
                    'target_user': user_id,
                    'reason': f'连带踢出撤回{recalled_count}条消息',
                    'time': time.strftime("%Y-%m-%d %H:%M:%S")
                })
                self.data_manager._save_group_data('recall_logs')

            invited_users = self.invitation_manager._get_invited_users(group_id, user_id)

            success = await self._kick_member(int(group_id), int(user_id), False)

            kicked_count = 1
            for invited in invited_users:
                if invited != user_id:
                    await self._kick_member(int(group_id), int(invited), False)
                    kicked_count += 1

            kick_logs.insert(0, {
                'qq': user_id,
                'action': 'chain_kick',
                'reason': reason,
                'time': time.strftime("%Y-%m-%d %H:%M:%S")
            })
            if len(kick_logs) > 100:
                kick_logs = kick_logs[:100]
            self.data_manager._save_group_data('kick_logs')

            recall_msg = f"，已撤回{recalled_count}条消息" if recalled_count > 0 else ""
            if kicked_count > 1:
                yield event.plain_result(f"👢 已踢出 {user_id} 及其邀请的 {kicked_count - 1} 名成员，理由: {reason}{recall_msg}")
            else:
                yield event.plain_result(f"👢 已踢出 {user_id}，理由: {reason}{recall_msg}")
            return

        # 普通踢出
        user_id = args[1]
        
        if not user_id.isdigit():
            yield event.plain_result("❌ 请输入有效的QQ号")
            return

        reason = ' '.join(args[2:]) if len(args) > 2 else config.get('default_kick_reason', '违规发言')

        # 先撤回用户消息
        recalled_count = await self._recall_user_messages(group_id, user_id)
        if recalled_count > 0:
            recall_logs.insert(0, {
                'operator': self.utils._get_user_id(event),
                'target_user': user_id,
                'reason': f'踢出撤回{recalled_count}条消息',
                'time': time.strftime("%Y-%m-%d %H:%M:%S")
            })
            self.data_manager._save_group_data('recall_logs')

        success = await self._kick_member(int(group_id), int(user_id), False)

        kick_logs.insert(0, {
            'qq': user_id,
            'action': 'kick',
            'reason': reason,
            'time': time.strftime("%Y-%m-%d %H:%M:%S")
        })
        if len(kick_logs) > 100:
            kick_logs = kick_logs[:100]
        self.data_manager._save_group_data('kick_logs')

        recall_msg = f"，已撤回{recalled_count}条消息" if recalled_count > 0 else ""
        if success:
            yield event.plain_result(f"👢 已踢出 {user_id}，理由: {reason}{recall_msg}")
        else:
            yield event.plain_result(f"⚠️ 本地记录已更新{recall_msg}，但踢出API调用失败")

    @filter.command("拉黑踢出")
    async def black_kick_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        config = self.data_manager._get_group_data(group_id, 'config', {})
        blacklist = self.data_manager._get_group_data(group_id, 'blacklist', {'users': [], 'words': []})
        kick_logs = self.data_manager._get_group_data(group_id, 'kick_logs', [])
        recall_logs = self.data_manager._get_group_data(group_id, 'recall_logs', [])

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("📋 使用方法:\n/拉黑踢出 <QQ> [理由]")
            return

        user_id = args[1]
        
        if not user_id.isdigit():
            yield event.plain_result("❌ 请输入有效的QQ号")
            return

        reason = ' '.join(args[2:]) if len(args) > 2 else config.get('default_kick_reason', '违规发言')

        existing = next((u for u in blacklist['users'] if u['qq'] == user_id), None)
        if existing:
            yield event.plain_result(f"⚠️ {user_id} 已在黑名单中")
            return

        # 先撤回用户消息
        recalled_count = await self._recall_user_messages(group_id, user_id)
        if recalled_count > 0:
            recall_logs.insert(0, {
                'operator': self.utils._get_user_id(event),
                'target_user': user_id,
                'reason': f'拉黑踢出撤回{recalled_count}条消息',
                'time': time.strftime("%Y-%m-%d %H:%M:%S")
            })
            self.data_manager._save_group_data('recall_logs')

        user_entry = {
            'qq': user_id,
            'reason': reason,
            'time': time.strftime("%Y-%m-%d %H:%M:%S"),
            'added_by': event.get_sender_name() or 'admin',
            'expire_time': None,
            'permanent': True
        }
        blacklist['users'].append(user_entry)
        self.data_manager._save_group_data('blacklist')

        success = await self._kick_member(int(group_id), int(user_id), True)

        kick_logs.insert(0, {
            'qq': user_id,
            'action': 'black_kick',
            'reason': reason,
            'time': time.strftime("%Y-%m-%d %H:%M:%S")
        })
        if len(kick_logs) > 100:
            kick_logs = kick_logs[:100]
        self.data_manager._save_group_data('kick_logs')

        recall_msg = f"，已撤回{recalled_count}条消息" if recalled_count > 0 else ""
        if success:
            yield event.plain_result(f"🚫 已拉黑并踢出 {user_id}，理由: {reason}{recall_msg}")
        else:
            yield event.plain_result(f"⚠️ 拉黑记录已保存{recall_msg}，但踢出API调用失败")

    @filter.command("踢出记录")
    async def kick_log_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        kick_logs = self.data_manager._get_group_data(group_id, 'kick_logs', [])

        args = event.message_str.strip().split()
        page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1

        if not kick_logs:
            yield event.plain_result("📋 暂无踢出记录")
            return

        page_size = 10
        total_pages = max(1, (len(kick_logs) + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_logs = kick_logs[start_idx:end_idx]

        log_lines = []
        for i, log in enumerate(page_logs, start=start_idx + 1):
            action_str = "拉黑踢出" if log['action'] == 'black_kick' else ("连带踢出" if log['action'] == 'chain_kick' else "踢出")
            log_lines.append(f"{i}. {log['time']} | {log['qq']} | {action_str} | {log['reason'][:15]}...")

        result = f"📋 踢出记录 (第{page}/{total_pages}页, 共{len(kick_logs)}条):\n"
        result += '\n'.join(log_lines) if log_lines else "无"
        yield event.plain_result(result)

    @filter.command("踢出搜索")
    async def kick_search_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        kick_logs = self.data_manager._get_group_data(group_id, 'kick_logs', [])

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("📋 使用方法:\n/踢出搜索 <关键词>")
            return

        keyword = ' '.join(args[1:]).lower()

        results = []
        for log in kick_logs:
            if keyword in log['qq'].lower() or keyword in log['reason'].lower():
                action_str = "拉黑踢出" if log['action'] == 'black_kick' else ("连带踢出" if log['action'] == 'chain_kick' else "踢出")
                results.append(f"{log['time']} | {log['qq']} | {action_str} | {log['reason']}")

        if results:
            yield event.plain_result(f"🔍 搜索结果 ({len(results)}条):\n" + '\n'.join(results[:10]))
        else:
            yield event.plain_result("⚠️ 未找到匹配记录")
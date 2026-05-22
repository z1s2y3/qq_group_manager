from astrbot.api.event import AstrMessageEvent, filter
from typing import Dict, List, Optional
import time

from ..core.data_manager import DataManager
from ..core.utils import Utils


class MuteFeature:
    """禁言管理功能"""

    def __init__(self, data_manager: DataManager, utils: Utils, context=None):
        self.data_manager = data_manager
        self.utils = utils
        self.context = context

    async def _set_group_mute(self, group_id: int, user_id: int, duration: int = 0) -> bool:
        """执行实际的禁言操作"""
        try:
            if self.context:
                await self.context.call_api(
                    "set_group_ban",
                    group_id=group_id,
                    user_id=user_id,
                    duration=duration
                )
                return True
            return False
        except Exception as e:
            from astrbot.api import logger
            logger.error(f"禁言失败: {e}")
            return False

    async def _unset_group_mute(self, group_id: int, user_id: int) -> bool:
        """执行实际的解除禁言操作"""
        try:
            if self.context:
                await self.context.call_api(
                    "set_group_ban",
                    group_id=group_id,
                    user_id=user_id,
                    duration=0
                )
                return True
            return False
        except Exception as e:
            from astrbot.api import logger
            logger.error(f"解除禁言失败: {e}")
            return False

    async def _set_group_whole_ban(self, group_id: int, enable: bool) -> bool:
        """执行全体禁言操作"""
        try:
            if self.context:
                await self.context.call_api(
                    "set_group_whole_ban",
                    group_id=group_id,
                    enable=enable
                )
                return True
            return False
        except Exception as e:
            from astrbot.api import logger
            logger.error(f"全体禁言操作失败: {e}")
            return False

    @filter.command("禁言")
    async def command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        config = self.data_manager._get_group_data(group_id, 'config', {})
        muted_users = self.data_manager._get_group_data(group_id, 'muted_users', [])

        args = event.message_str.strip().split()
        if len(args) < 2:
            default_duration = config.get('default_mute_duration', 30)
            yield event.plain_result(f"""📋 本群禁言命令使用方法:
👤 单个禁言:
/禁言 <QQ> - 使用默认时间禁言(当前默认: {default_duration}分钟)
/禁言 <QQ> <时长> [理由] - 禁言用户(时长: 30s/30m/2h/7d)
/禁言 list [页码] - 查看禁言列表(分页)
/禁言 info <QQ> - 查看禁言详情
/禁言 search <关键词> - 搜索禁言用户

⏰ 快捷禁言:
/禁言 60s <QQ> - 快速禁言60秒
/禁言 10m <QQ> - 快速禁言10分钟
/禁言 1h <QQ> - 快速禁言1小时
/禁言 24h <QQ> - 快速禁言24小时

🔧 其他命令:
/永久禁言 <QQ> [理由] - 永久禁言用户
/解禁 <QQ> [理由] - 解除单个用户禁言
/解除禁言 - 解除所有用户禁言
/全体禁言 - 切换全体禁言状态
/设置默认禁言时间 <分钟> - 设置默认禁言时长""")
            return

        action = args[1].lower()

        if action == 'list':
            if not muted_users:
                yield event.plain_result("✅ 当前本群没有被禁言的用户")
                return

            page = int(args[2]) if len(args) > 2 and args[2].isdigit() else 1
            page_size = 10
            total_pages = max(1, (len(muted_users) + page_size - 1) // page_size)
            page = max(1, min(page, total_pages))

            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_users = muted_users[start_idx:end_idx]

            user_lines = []
            for i, u in enumerate(page_users, start=start_idx + 1):
                expire_str = "永久" if u.get('permanent') else (u.get('expire_time')[:16] if u.get('expire_time') else "未知")
                user_lines.append(f"{i}. {u['qq']} | {u.get('reason', '无')[:15]}... | {expire_str}")

            result = f"🔇 本群禁言列表 (第{page}/{total_pages}页, 共{len(muted_users)}人):\n"
            result += '\n'.join(user_lines) if user_lines else "无"
            yield event.plain_result(result)
            return

        if action == 'info':
            if len(args) < 3:
                yield event.plain_result("❌ 请指定要查看的QQ")
                return
            user_id = args[2]
            user_entry = next((u for u in muted_users if u['qq'] == user_id), None)

            if user_entry:
                expire_str = "永久禁言" if user_entry.get('permanent') else f"将于 {user_entry['expire_time']} 到期"
                info = f"""📋 本群禁言详情:
QQ: {user_entry['qq']}
原因: {user_entry.get('reason', '无')}
开始时间: {user_entry.get('time', '未知')}
执行者: {user_entry.get('added_by', 'admin')}
类型: {expire_str}"""
                yield event.plain_result(info)
            else:
                yield event.plain_result(f"⚠️ {user_id} 不在本群禁言列表中")
            return

        if action == 'search':
            if len(args) < 3:
                yield event.plain_result("❌ 请指定搜索关键词")
                return
            keyword = ' '.join(args[2:]).lower()

            results = []
            for u in muted_users:
                if keyword in u['qq'].lower() or keyword in u.get('reason', '').lower():
                    expire_str = "永久" if u.get('permanent') else (u.get('expire_time')[:10] if u.get('expire_time') else "未知")
                    results.append(f"{u['qq']} | {u.get('reason', '无')[:20]}... | {expire_str}")

            if results:
                yield event.plain_result(f"🔍 本群搜索结果 ({len(results)}条):\n" + '\n'.join(results[:10]))
            else:
                yield event.plain_result("⚠️ 未找到匹配的禁言用户")
            return

        if action in ['60s', '10m', '1h', '24h']:
            if len(args) < 3:
                yield event.plain_result(f"❌ 使用方法: /禁言 {action} <QQ> [理由]")
                return

            user_id = args[2]
            reason = ' '.join(args[3:]) if len(args) > 3 else '无'

            expire_time = None

            if action == '60s':
                expire_time = time.time() + 60
            elif action == '10m':
                expire_time = time.time() + 10 * 60
            elif action == '1h':
                expire_time = time.time() + 3600
            elif action == '24h':
                expire_time = time.time() + 24 * 3600
            duration_str = action

            existing = next((u for u in muted_users if u['qq'] == user_id), None)
            if existing:
                yield event.plain_result(f"⚠️ {user_id} 已在本群禁言列表中")
                return

            expire_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire_time)) if expire_time else None

            mute_entry = {
                'qq': user_id,
                'reason': reason,
                'time': time.strftime("%Y-%m-%d %H:%M:%S"),
                'added_by': event.get_sender_name() or 'admin',
                'expire_time': expire_time_str,
                'permanent': False
            }
            muted_users.append(mute_entry)
            self.data_manager._save_group_data('muted_users')

            duration_seconds = int((expire_time - time.time()) if expire_time else 30 * 60)
            if await self._set_group_mute(int(group_id), int(user_id), duration_seconds):
                yield event.plain_result(f"🔇 已在本群禁言 {user_id} {duration_str}，理由: {reason}")
            else:
                yield event.plain_result(f"⚠️ 本地禁言记录已更新，但API调用失败")
            return

        user_id = args[1]
        if len(args) >= 3:
            duration = args[2]
            reason = ' '.join(args[3:]) if len(args) > 3 else config.get('default_mute_reason', '违规发言')
        else:
            duration = str(config.get('default_mute_duration', 30)) + 'm'
            reason = config.get('default_mute_reason', '违规发言')

        expire_time = None
        permanent = False

        try:
            if duration.lower() == 'perm' or duration.lower() == '永久':
                permanent = True
            elif duration.endswith('s'):
                expire_time = time.time() + int(duration[:-1])
            elif duration.endswith('m'):
                expire_time = time.time() + int(duration[:-1]) * 60
            elif duration.endswith('h'):
                expire_time = time.time() + int(duration[:-1]) * 3600
            elif duration.endswith('d'):
                expire_time = time.time() + int(duration[:-1]) * 86400
            else:
                expire_time = time.time() + int(duration) * 60
        except ValueError:
            yield event.plain_result("❌ 时长格式错误，请使用: 30s/30m/2h/7d/perm")
            return

        existing = next((u for u in muted_users if u['qq'] == user_id), None)
        if existing:
            yield event.plain_result(f"⚠️ {user_id} 已在本群禁言列表中")
            return

        expire_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire_time)) if expire_time else None

        mute_entry = {
            'qq': user_id,
            'reason': reason,
            'time': time.strftime("%Y-%m-%d %H:%M:%S"),
            'added_by': event.get_sender_name() or 'admin',
            'expire_time': expire_time_str,
            'permanent': permanent
        }
        muted_users.append(mute_entry)
        self.data_manager._save_group_data('muted_users')

        duration_str = "永久" if permanent else duration
        if await self._set_group_mute(int(group_id), int(user_id), 0 if permanent else int((expire_time - time.time()) if expire_time else 30 * 60)):
            yield event.plain_result(f"🔇 已在本群禁言 {user_id} {duration_str}，理由: {reason}")
        else:
            yield event.plain_result(f"⚠️ 本地禁言记录已更新，但API调用失败")

    @filter.command("永久禁言")
    async def permanent_mute_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        muted_users = self.data_manager._get_group_data(group_id, 'muted_users', [])

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("📋 使用方法:\n/永久禁言 <QQ> [理由]")
            return

        user_id = args[1]
        reason = ' '.join(args[2:]) if len(args) > 2 else '无'

        existing = next((u for u in muted_users if u['qq'] == user_id), None)
        if existing:
            if existing.get('permanent'):
                yield event.plain_result(f"⚠️ {user_id} 已是永久禁言状态")
            else:
                existing['permanent'] = True
                existing['expire_time'] = None
                existing['reason'] = reason
                self.data_manager._save_group_data('muted_users')
                if await self._set_group_mute(int(group_id), int(user_id), 0):
                    yield event.plain_result(f"🔇 已将 {user_id} 改为永久禁言，理由: {reason}")
                else:
                    yield event.plain_result(f"⚠️ 本地记录已更新，但API调用失败")
            return

        mute_entry = {
            'qq': user_id,
            'reason': reason,
            'time': time.strftime("%Y-%m-%d %H:%M:%S"),
            'added_by': event.get_sender_name() or 'admin',
            'expire_time': None,
            'permanent': True
        }
        muted_users.append(mute_entry)
        self.data_manager._save_group_data('muted_users')

        if await self._set_group_mute(int(group_id), int(user_id), 0):
            yield event.plain_result(f"🔇 已在本群永久禁言 {user_id}，理由: {reason}")
        else:
            yield event.plain_result(f"⚠️ 本地禁言记录已更新，但API调用失败")

    @filter.command("解禁")
    async def unmute_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        muted_users = self.data_manager._get_group_data(group_id, 'muted_users', [])

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("📋 使用方法:\n/解禁 <QQ> [理由]")
            return

        user_id = args[1]
        reason = ' '.join(args[2:]) if len(args) > 2 else '无'

        original_count = len(muted_users)
        updated_muted_users = [u for u in muted_users if u['qq'] != user_id]
        self.data_manager._set_group_data('muted_users', updated_muted_users, group_id)

        if len(updated_muted_users) < original_count:
            self.data_manager._save_group_data('muted_users')
            if await self._unset_group_mute(int(group_id), int(user_id)):
                yield event.plain_result(f"✅ 已在本群解禁 {user_id}，理由: {reason}")
            else:
                yield event.plain_result(f"⚠️ 本地记录已更新，但API调用失败")
        else:
            yield event.plain_result(f"⚠️ {user_id} 不在本群禁言列表中")

    @filter.command("解除禁言")
    async def unmute_all_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        muted_users = self.data_manager._get_group_data(group_id, 'muted_users', [])

        count = len(muted_users)
        for user in muted_users:
            await self._unset_group_mute(int(group_id), int(user['qq']))
        self.data_manager._set_group_data('muted_users', [], group_id)
        self.data_manager._save_group_data('muted_users')
        yield event.plain_result(f"✅ 已解除本群所有 {count} 人的禁言")

    @filter.command("全体禁言")
    async def global_mute_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)

        global_muted_data = self.data_manager.groups_data.get('global_muted', {})
        current_status = global_muted_data.get(group_id, False)
        
        if current_status:
            global_muted_data[group_id] = False
            self.data_manager.groups_data['global_muted'] = global_muted_data
            if await self._set_group_whole_ban(int(group_id), False):
                yield event.plain_result("✅ 已关闭本群全体禁言")
            else:
                yield event.plain_result("⚠️ 本地状态已更新，但API调用失败")
        else:
            global_muted_data[group_id] = True
            self.data_manager.groups_data['global_muted'] = global_muted_data
            if await self._set_group_whole_ban(int(group_id), True):
                yield event.plain_result("🔇 已开启本群全体禁言")
            else:
                yield event.plain_result("⚠️ 本地状态已更新，但API调用失败")

    @filter.command("设置默认禁言时间")
    async def set_default_mute_duration_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        config = self.data_manager._get_group_data(group_id, 'config', {})

        args = event.message_str.strip().split()
        if len(args) < 2:
            current = config.get('default_mute_duration', 30)
            yield event.plain_result(f"📋 使用方法:\n/设置默认禁言时间 <分钟>\n当前默认禁言时间: {current}分钟")
            return

        try:
            minutes = int(args[1])
            if minutes < 1 or minutes > 43200:
                yield event.plain_result("❌ 禁言时间必须在1-43200分钟之间(最多30天)")
                return
            
            config['default_mute_duration'] = minutes
            self.data_manager._save_group_data('config')
            yield event.plain_result(f"✅ 默认禁言时间已设置为: {minutes}分钟")
        except ValueError:
            yield event.plain_result("❌ 请输入有效的数字")
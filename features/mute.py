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

    def _parse_duration(self, duration_str: str) -> tuple:
        """解析时长，返回(秒数, 显示字符串)"""
        duration_str = duration_str.lower().strip()
        
        try:
            if duration_str.endswith('s'):
                seconds = int(duration_str[:-1])
                return seconds, f"{seconds}秒"
            elif duration_str.endswith('m'):
                seconds = int(duration_str[:-1]) * 60
                return seconds, f"{int(duration_str[:-1])}分钟"
            elif duration_str.endswith('h'):
                seconds = int(duration_str[:-1]) * 3600
                return seconds, f"{int(duration_str[:-1])}小时"
            elif duration_str.endswith('d'):
                seconds = int(duration_str[:-1]) * 86400
                return seconds, f"{int(duration_str[:-1])}天"
            else:
                # 纯数字默认是分钟
                seconds = int(duration_str) * 60
                return seconds, f"{duration_str}分钟"
        except ValueError:
            return None, None

    @filter.command("禁言")
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
        muted_users = self.data_manager._get_group_data(group_id, 'muted_users', [])
        at_user = config.get('mute_at_user', False)

        args = event.message_str.strip().split()
        if len(args) < 2:
            default_duration = config.get('default_mute_duration', 30)
            yield event.plain_result(f"""📋 禁言命令使用方法:
👤 单个禁言:
/禁言 <QQ> - 使用默认时间禁言(当前默认: {default_duration}分钟)
/禁言 <QQ> <时长> [理由] - 禁言用户(时长: 1s/1m/1h/1d)

🔧 其他命令:
/设置默认禁言时间 <分钟> - 设置默认禁言时长""")
            return

        # 检查是否是纯数字QQ
        user_id = args[1]
        if not user_id.isdigit():
            yield event.plain_result("❌ 请输入有效的QQ号")
            return

        # 获取时长和理由
        if len(args) >= 3:
            duration = args[2]
            reason = ' '.join(args[3:]) if len(args) > 3 else config.get('default_mute_reason', '违规发言')
        else:
            duration = str(config.get('default_mute_duration', 30))
            reason = config.get('default_mute_reason', '违规发言')

        # 解析时长
        duration_seconds, duration_display = self._parse_duration(duration)
        if duration_seconds is None:
            yield event.plain_result("❌ 时长格式错误，请使用: 1s/1m/1h/1d")
            return

        # 检查是否已在禁言列表
        existing = next((u for u in muted_users if u['qq'] == user_id), None)
        if existing:
            yield event.plain_result(f"⚠️ {user_id} 已在禁言列表中")
            return

        expire_time = time.time() + duration_seconds
        expire_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire_time))

        mute_entry = {
            'qq': user_id,
            'reason': reason,
            'time': time.strftime("%Y-%m-%d %H:%M:%S"),
            'added_by': event.get_sender_name() or '管理员',
            'operator_id': self.utils._get_user_id(event),
            'expire_time': expire_time_str,
            'permanent': False
        }
        muted_users.append(mute_entry)
        self.data_manager._save_group_data('muted_users')

        at_prefix = f"[CQ:at,qq={user_id}] " if at_user else ""
        if await self._set_group_mute(int(group_id), int(user_id), duration_seconds):
            yield event.plain_result(f"{at_prefix}🔇 已禁言 {user_id} {duration_display}，理由: {reason}")
        else:
            yield event.plain_result(f"{at_prefix}⚠️ 本地记录已更新，但API调用失败")

    @filter.command("解禁")
    async def unmute_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        muted_users = self.data_manager._get_group_data(group_id, 'muted_users', [])
        config = self.data_manager.get_effective_config(group_id)
        at_user = config.get('mute_at_user', False)

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("📋 使用方法:\n/解禁 <QQ>")
            return

        user_id = args[1]
        original_count = len(muted_users)
        updated_muted_users = [u for u in muted_users if u['qq'] != user_id]
        self.data_manager._set_group_data('muted_users', updated_muted_users, group_id)

        at_prefix = f"[CQ:at,qq={user_id}] " if at_user else ""
        if len(updated_muted_users) < original_count:
            self.data_manager._save_group_data('muted_users')
            if await self._unset_group_mute(int(group_id), int(user_id)):
                yield event.plain_result(f"{at_prefix}✅ 已解禁 {user_id}")
            else:
                yield event.plain_result(f"{at_prefix}⚠️ 本地记录已更新，但API调用失败")
        else:
            yield event.plain_result(f"⚠️ {user_id} 不在禁言列表中")

    @filter.command("查看禁言列表")
    async def list_muted_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        muted_users = self.data_manager._get_group_data(group_id, 'muted_users', [])

        if not muted_users:
            yield event.plain_result("📋 当前没有被禁言的用户")
            return

        user_lines = []
        for i, u in enumerate(muted_users, 1):
            expire_str = "永久" if u.get('permanent') else u.get('expire_time', '未知')
            operator_info = f" (操作者: {u.get('added_by', '未知')} [{u.get('operator_id', '')}])"
            user_lines.append(f"{i}. 时间: {u['time']}\n   QQ: {u['qq']}\n   理由: {u.get('reason', '无')}\n   到期: {expire_str}{operator_info}")

        result = f"📋 禁言列表 (共{len(muted_users)}人):\n"
        result += '\n' + '\n'.join(user_lines)
        yield event.plain_result(result)

    @filter.command("清空禁言列表")
    async def clear_muted_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        muted_users = self.data_manager._get_group_data(group_id, 'muted_users', [])

        if not muted_users:
            yield event.plain_result("📋 禁言列表已经是空的")
            return

        count = len(muted_users)
        for user in muted_users:
            await self._unset_group_mute(int(group_id), int(user['qq']))

        self.data_manager._set_group_data('muted_users', [], group_id)
        self.data_manager._save_group_data('muted_users')
        yield event.plain_result(f"✅ 已清空禁言列表，解禁 {count} 人")

    @filter.command("全体禁言")
    async def global_mute_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)

        if await self._set_group_whole_ban(int(group_id), True):
            yield event.plain_result("🔇 已开启全体禁言")
        else:
            yield event.plain_result("⚠️ API调用失败")

    @filter.command("全体解禁")
    async def global_unmute_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)

        if await self._set_group_whole_ban(int(group_id), False):
            yield event.plain_result("✅ 已关闭全体禁言")
        else:
            yield event.plain_result("⚠️ API调用失败")

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

    @filter.command("定时禁言")
    async def scheduled_mute_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        config = self.data_manager._get_group_data(group_id, 'config', {})

        args = event.message_str.strip().split()
        if len(args) < 3:
            current_start = config.get('scheduled_mute_start', '')
            current_end = config.get('scheduled_mute_end', '')
            enabled = config.get('scheduled_mute_enabled', False)
            status = "开启" if enabled else "关闭"
            
            yield event.plain_result(f"""📋 定时全体禁言命令:

当前状态: {status}
开始时间: {current_start or '未设置'}
结束时间: {current_end or '未设置'}

使用方法:
/定时禁言 <开始时间> <结束时间> - 设置时间段(如: /定时禁言 20:00 06:00)
/定时禁言 on - 开启定时禁言
/定时禁言 off - 关闭定时禁言""")
            return

        if args[1] == 'on':
            config['scheduled_mute_enabled'] = True
            self.data_manager._save_group_data('config')
            yield event.plain_result("✅ 已开启定时全体禁言")
        elif args[1] == 'off':
            config['scheduled_mute_enabled'] = False
            self.data_manager._save_group_data('config')
            yield event.plain_result("✅ 已关闭定时全体禁言")
        else:
            start_time = args[1]
            end_time = args[2]
            
            # 简单验证时间格式
            if len(start_time) != 5 or start_time[2] != ':' or len(end_time) != 5 or end_time[2] != ':':
                yield event.plain_result("❌ 时间格式错误，请使用 HH:MM 格式")
                return
            
            config['scheduled_mute_start'] = start_time
            config['scheduled_mute_end'] = end_time
            config['scheduled_mute_enabled'] = True
            self.data_manager._save_group_data('config')
            yield event.plain_result(f"✅ 定时全体禁言已设置: {start_time} - {end_time}")

    @filter.command("添加关键词禁言")
    async def add_keyword_mute(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        keywords = self.data_manager._get_group_data(group_id, 'mute_keywords', [])

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result(f"""📋 关键词禁言命令:

当前关键词: {', '.join(keywords) if keywords else '无'}

使用方法:
/添加关键词禁言 <关键词> - 添加关键词
/删除关键词禁言 <关键词> - 删除关键词
/清空关键词禁言 - 清空所有关键词""")
            return

        keyword = ' '.join(args[1:])
        
        if keyword in keywords:
            yield event.plain_result(f"❌ 关键词 '{keyword}' 已存在")
            return
        
        keywords.append(keyword)
        self.data_manager._set_group_data('mute_keywords', keywords, group_id)
        self.data_manager._save_group_data('mute_keywords')
        yield event.plain_result(f"✅ 已添加关键词禁言: {keyword}")

    @filter.command("删除关键词禁言")
    async def remove_keyword_mute(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        keywords = self.data_manager._get_group_data(group_id, 'mute_keywords', [])

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("📋 使用方法:\n/删除关键词禁言 <关键词>")
            return

        keyword = ' '.join(args[1:])
        
        if keyword not in keywords:
            yield event.plain_result(f"❌ 关键词 '{keyword}' 不存在")
            return
        
        keywords.remove(keyword)
        self.data_manager._set_group_data('mute_keywords', keywords, group_id)
        self.data_manager._save_group_data('mute_keywords')
        yield event.plain_result(f"✅ 已删除关键词禁言: {keyword}")

    @filter.command("清空关键词禁言")
    async def clear_keyword_mute(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        
        self.data_manager._set_group_data('mute_keywords', [], group_id)
        self.data_manager._save_group_data('mute_keywords')
        yield event.plain_result("✅ 已清空所有关键词禁言")

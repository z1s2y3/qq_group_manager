from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api import logger
from typing import Dict, List, Optional
import time
import random
import os

from ..core.data_manager import DataManager
from ..core.utils import Utils


class OtherFeatures:
    """其他功能模块"""

    def __init__(self, data_manager: DataManager, utils: Utils, context=None, message_history=None):
        self.data_manager = data_manager
        self.utils = utils
        self.context = context
        self.message_history = message_history or {}
        self.auto_reply_cooldowns = {}

    @filter.command("群管菜单")
    async def help_menu(self, event: AstrMessageEvent, *args):
        if args and args[0]:
            await self._show_category_help(args[0], event)
            return
        
        yield event.plain_result("""📋 QQ群管菜单

审核系统|欢迎系统
撤回系统|踢出系统
禁言系统|定时消息
分群设置|统计系统
黑名单系统

💡 直接输入分类名查看详情，如: 审核系统""")

    @filter.command("审核系统")
    async def help_approval(self, event: AstrMessageEvent):
        await self._show_category_help("审核系统", event)

    @filter.command("欢迎系统")
    async def help_welcome(self, event: AstrMessageEvent):
        await self._show_category_help("欢迎系统", event)

    @filter.command("撤回系统")
    async def help_recall(self, event: AstrMessageEvent):
        await self._show_category_help("撤回系统", event)

    @filter.command("踢出系统")
    async def help_kick(self, event: AstrMessageEvent):
        await self._show_category_help("踢出系统", event)

    @filter.command("禁言系统")
    async def help_mute(self, event: AstrMessageEvent):
        await self._show_category_help("禁言系统", event)

    @filter.command("定时消息")
    async def help_schedule(self, event: AstrMessageEvent):
        await self._show_category_help("定时消息", event)

    @filter.command("分群设置")
    async def help_settings(self, event: AstrMessageEvent):
        await self._show_category_help("分群设置", event)

    @filter.command("统计系统")
    async def help_stats(self, event: AstrMessageEvent):
        await self._show_category_help("统计系统", event)

    @filter.command("黑名单系统")
    async def help_blacklist(self, event: AstrMessageEvent):
        await self._show_category_help("黑名单系统", event)

    async def _show_category_help(self, category: str, event: AstrMessageEvent):
        help_texts = {
            '审核系统': """📝 审核系统

/入群审核                    - 查看审核状态
/入群审核 同意 <QQ> [理由]   - 通过申请
/入群审核 拒绝 <QQ> [理由]   - 拒绝申请
/入群审核 math               - 数学验证模式
/入群审核 id                 - 随机数字验证模式
/审核自定义次数 <次数>        - 设置验证次数上限""",
            '欢迎系统': """📢 欢迎系统

/设置欢迎语 <内容>           - 设置欢迎语
/欢迎 on/off                 - 开关欢迎功能
/欢迎测试                     - 测试欢迎消息""",
            '撤回系统': """🗑️ 撤回系统

/撤回 <数量>                 - 撤回消息
/撤回 用户 <QQ> <数量>       - 撤回用户消息
/撤回 <消息ID>               - 撤回指定消息""",
            '踢出系统': """👢 踢出系统

/踢出 <QQ> [理由]            - 踢出用户
/踢出 @用户 [理由]           - @方式踢出
/连带踢出 <QQ>               - 踢出及其邀请人
/拉黑踢出 <QQ> [理由]        - 踢出并拉黑""",
            '禁言系统': """🔇 禁言系统

/禁言 <QQ> [时长] [理由]     - 禁言用户
/禁言 list [页码]            - 查看禁言列表
/禁言 info <QQ>              - 查看禁言详情
/解禁 <QQ>                   - 解除禁言
/解禁 all                    - 解除所有禁言
/全体禁言 on/off             - 全体禁言开关
/永久禁言 <QQ> [理由]        - 永久禁言""",
            '定时消息': """⏰ 定时消息

/定时消息 add <时间> <内容>   - 添加定时消息
/定时消息 list               - 查看定时消息
/定时消息 del <ID>           - 删除定时消息""",
            '分群设置': """⚙️ 分群设置

/设置                       - 查看本群设置
/设置 admin add <QQ>         - 添加分群管理员
/设置 admin remove <QQ>      - 移除分群管理员
/设置 admin list             - 查看分群管理员""",
            '统计系统': """📊 统计系统

/统计                       - 查看统计信息
/排行榜                     - 查看积分排行榜
/签到                       - 每日签到
/我的信息                   - 查看个人信息""",
            '黑名单系统': """🚫 黑名单系统

/黑名单 add <QQ> [原因]      - 添加用户黑名单
/黑名单 remove <QQ>          - 移除用户黑名单
/黑名单 list [页码]          - 查看黑名单
/关键词 add <关键词>          - 添加关键词黑名单
/关键词 remove <关键词>       - 移除关键词
/关键词 list                 - 查看关键词列表"""
        }
        
        help_text = help_texts.get(category)
        if help_text:
            yield event.plain_result(help_text)
        else:
            yield event.plain_result(f"❌ 未知分类: {category}\n\n可用分类: 审核系统 | 欢迎系统 | 撤回系统 | 踢出系统 | 禁言系统 | 定时消息 | 分群设置 | 统计系统 | 黑名单系统")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def message_listener(self, event: AstrMessageEvent):
        """监听所有消息 - 自动回复、黑名单检测"""
        group_id = self.utils._get_group_id(event)
        user_id = self.utils._get_user_id(event)
        
        if not group_id:
            return
        
        if group_id not in self.message_history:
            self.message_history[group_id] = []
        
        msg_info = {
            'message_id': event.get_message_id(),
            'user_id': user_id,
            'user_name': event.get_sender_name() or 'unknown',
            'content': event.message_str or '',
            'timestamp': time.time()
        }
        self.message_history[group_id].append(msg_info)
        if len(self.message_history[group_id]) > 100:
            self.message_history[group_id] = self.message_history[group_id][-100:]
        
        config = self.data_manager.get_effective_config(group_id)
        
        if self.utils._is_admin(event):
            await self._handle_auto_reply(event, group_id, user_id, config)
            return
        
        blacklist = self.data_manager._get_group_data(group_id, 'blacklist', {'users': [], 'words': []})
        
        if config.get('anti_spam_enabled', False):
            for user in blacklist['users']:
                if user['qq'] == user_id:
                    try:
                        if self.context:
                            await self.context.call_api("delete_msg", message_id=event.get_message_id())
                    except:
                        pass
                    yield event.plain_result(f"🚫 黑名单用户，已自动撤回消息")
                    return
            
            message_text = event.message_str or ""
            for word_entry in blacklist['words']:
                word = word_entry.get('word', word_entry) if isinstance(word_entry, dict) else word_entry
                if word in message_text:
                    try:
                        if self.context:
                            await self.context.call_api("delete_msg", message_id=event.get_message_id())
                    except:
                        pass
                    yield event.plain_result(f"⚠️ 消息包含敏感内容，已自动撤回")
                    return
        
        await self._handle_auto_reply(event, group_id, user_id, config)

    async def _handle_auto_reply(self, event: AstrMessageEvent, group_id: str, user_id: str, config: Dict):
        """处理自动回复"""
        if not config.get('auto_reply_enabled', False):
            return
        
        ignore_admin = config.get('auto_reply_ignore_admin', True)
        if ignore_admin and self.utils._is_admin(event):
            return
        
        cooldown = config.get('auto_reply_cooldown', 5)
        now = time.time()
        
        if group_id not in self.auto_reply_cooldowns:
            self.auto_reply_cooldowns[group_id] = {}
        
        last_time = self.auto_reply_cooldowns[group_id].get(user_id, 0)
        if now - last_time < cooldown:
            return
        
        message_text = event.message_str or ""
        auto_replies = self.data_manager._get_group_data(group_id, 'auto_replies', {})
        
        if not auto_replies:
            return
        
        sorted_replies = sorted(auto_replies.items(), key=lambda x: x[1].get('priority', 1), reverse=True)
        
        for trigger, data in sorted_replies:
            replies = data['replies']
            if trigger in message_text:
                reply = random.choice(replies)
                reply = self._replace_variables(reply, event)
                yield event.plain_result(reply)
                self.auto_reply_cooldowns[group_id][user_id] = now
                return

    def _replace_variables(self, text: str, event: AstrMessageEvent) -> str:
        """替换变量"""
        user_name = event.get_sender_name() or '用户'
        group_name = getattr(event, 'group_name', '本群')
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        text = text.replace('{user}', user_name)
        text = text.replace('{group}', group_name)
        text = text.replace('{time}', current_time)
        return text

    def _get_recent_messages(self, group_id: str, count: int = 10) -> list:
        """获取最近消息"""
        if group_id not in self.message_history:
            return []
        return self.message_history[group_id][-count:]

    @filter.command("撤回")
    async def recall_message(self, event: AstrMessageEvent, *args):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._getGroup_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        if not args:
            yield event.plain_result("""📖 撤回命令帮助

/撤回 <数量>                 - 撤回最近N条消息
/撤回 用户 <QQ> <数量>       - 撤回指定用户的消息
/撤回 <消息ID>               - 撤回指定消息""")
            return
        
        try:
            if args[0] == "用户" and len(args) >= 3:
                target_qq = args[1]
                count = int(args[2])
                await self._recall_user_messages(group_id, target_qq, count, event)
            elif args[0].isdigit():
                count = min(int(args[0]), 10)
                await self._recall_recent_messages(group_id, count, event)
            else:
                message_id = int(args[0])
                await self._recall_single_message(group_id, message_id, event)
        except ValueError:
            yield event.plain_result("❌ 参数错误")

    async def _recall_recent_messages(self, group_id: str, count: int, event: AstrMessageEvent):
        """撤回最近的消息"""
        messages = self._get_recent_messages(group_id, count)
        if not messages:
            yield event.plain_result("❌ 无可撤回的消息")
            return
        
        success = 0
        for msg in messages:
            if await self._recall_message_by_id(msg['message_id']):
                success += 1
        
        yield event.plain_result(f"✅ 已撤回 {success} 条消息")

    async def _recall_user_messages(self, group_id: str, user_id: str, count: int, event: AstrMessageEvent):
        """撤回指定用户的消息"""
        messages = self._get_recent_messages(group_id, 50)
        user_messages = [m for m in messages if m['user_id'] == user_id][:count]
        
        if not user_messages:
            yield event.plain_result(f"❌ 未找到用户 {user_id} 的消息")
            return
        
        success = 0
        for msg in user_messages:
            if await self._recall_message_by_id(msg['message_id']):
                success += 1
        
        yield event.plain_result(f"✅ 已撤回用户 {user_id} 的 {success} 条消息")

    async def _recall_single_message(self, group_id: str, message_id: int, event: AstrMessageEvent):
        """撤回单条消息"""
        if await self._recall_message_by_id(message_id):
            yield event.plain_result("✅ 消息已撤回")
        else:
            yield event.plain_result("❌ 撤回失败")

    async def _recall_message_by_id(self, message_id: int) -> bool:
        """执行撤回"""
        try:
            if self.context:
                await self.context.call_api("delete_msg", message_id=message_id)
                return True
        except Exception as e:
            logger.error(f"撤回消息失败: {e}")
        return False

    @filter.command("欢迎")
    async def welcome_control(self, event: AstrMessageEvent, *args):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._getGroupId(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        if not args or args[0] not in ['on', 'off']:
            yield event.plain_result("📖 欢迎命令\n\n/欢迎 on  - 开启欢迎\n/欢迎 off - 关闭欢迎")
            return
        
        enabled = args[0] == 'on'
        self.data_manager._save_group_config(group_id, 'welcome_enabled', enabled)
        yield event.plain_result(f"✅ 欢迎功能已{'开启' if enabled else '关闭'}")

    @filter.command("设置欢迎语")
    async def set_welcome(self, event: AstrMessageEvent, *args):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._getGroupId(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        if not args:
            current = self.data_manager._get_group_data(group_id, 'config', {}).get('welcome_message', '')
            yield event.plain_result(f"📝 当前欢迎语:\n{current or '未设置'}\n\n/设置欢迎语 <内容>")
            return
        
        welcome_msg = ' '.join(args)
        self.data_manager._save_group_config(group_id, 'welcome_message', welcome_msg)
        yield event.plain_result(f"✅ 欢迎语已设置:\n欢迎 {{user}}进入{{group}}, {welcome_msg}")

    @filter.command("签到")
    async def sign_in(self, event: AstrMessageEvent):
        user_id = self.utils._get_user_id(event)
        group_id = self.utils._getGroupId(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        config = self.data_manager.get_effective_config(group_id)
        if not config.get('sign_enabled', True):
            yield event.plain_result("❌ 签到功能已关闭")
            return
        
        sign_data = self.data_manager._get_group_data(group_id, 'sign_data', {})
        today = time.strftime("%Y-%m-%d")
        
        if user_id in sign_data and sign_data[user_id].get('date') == today:
            yield event.plain_result(f"❌ 今日已签到！\n签到时间: {sign_data[user_id]['time']}")
            return
        
        base_points = config.get('sign_bonus_points', 10)
        sign_data[user_id] = {
            'date': today,
            'time': time.strftime("%H:%M:%S"),
            'points': base_points,
            'continuous_days': sign_data.get(user_id, {}).get('continuous_days', 0) + 1 if sign_data.get(user_id, {}).get('date') == time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400)) else 1
        }
        
        self.data_manager._set_group_data('sign_data', sign_data, group_id)
        
        days = sign_data[user_id]['continuous_days']
        bonus = config.get('sign_continuous_bonus', 2) * (days - 1)
        total = base_points + bonus
        
        yield event.plain_result(f"""✅ 签到成功！

👤 用户: {event.get_sender_name()}
📅 日期: {today}
💰 获得积分: {total}
🔥 连续签到: {days} 天""")

    @filter.command("排行榜")
    async def leaderboard(self, event: AstrMessageEvent, *args):
        group_id = self.utils._getGroupId(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        sign_data = self.data_manager._get_group_data(group_id, 'sign_data', {})
        
        if not sign_data:
            yield event.plain_result("❌ 暂无签到数据")
            return
        
        sorted_users = sorted(sign_data.items(), key=lambda x: x[1].get('points', 0), reverse=True)[:10]
        
        result = "🏆 签到排行榜\n\n"
        for i, (qq, data) in enumerate(sorted_users, 1):
            result += f"{i}. QQ{qq} - {data.get('points', 0)}积分 ({data.get('continuous_days', 0)}天连续)\n"
        
        yield event.plain_result(result)

    @filter.command("我的信息")
    async def my_info(self, event: AstrMessageEvent):
        user_id = self.utils._get_user_id(event)
        group_id = self.utils._getGroupId(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        sign_data = self.data_manager._get_group_data(group_id, 'sign_data', {})
        user_data = sign_data.get(user_id, {})
        
        yield event.plain_result(f"""👤 个人信息

QQ: {user_id}
昵称: {event.get_sender_name()}
积分: {user_data.get('points', 0)}
连续签到: {user_data.get('continuous_days', 0)} 天
最后签到: {user_data.get('date', '未签到')}""")

    @filter.command("统计")
    async def statistics(self, event: AstrMessageEvent):
        group_id = self.utils._getGroupId(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        sign_data = self.data_manager._get_group_data(group_id, 'sign_data', {})
        kick_logs = self.data_manager._get_group_data(group_id, 'kick_logs', [])
        muted_users = self.data_manager._get_group_data(group_id, 'muted_users', [])
        
        yield event.plain_result(f"""📊 群统计概览

👥 签到人数: {len(sign_data)}
👢 踢出记录: {len(kick_logs)}
🔇 禁言中: {len(muted_users)}""")

    @filter.command("设置")
    async def group_settings(self, event: AstrMessageEvent, *args):
        group_id = self.utils._getGroupId(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        config = self.data_manager.get_effective_config(group_id)
        
        if not args:
            yield event.plain_result(f"""⚙️ 群设置

欢迎功能: {'开启' if config.get('welcome_enabled', True) else '关闭'}
自动回复: {'开启' if config.get('auto_reply_enabled', False) else '关闭'}
反垃圾: {'开启' if config.get('anti_spam_enabled', True) else '关闭'}
签到: {'开启' if config.get('sign_enabled', True) else '关闭'}

子命令:
/设置 admin add <QQ>   - 添加分群管理员
/设置 admin remove <QQ> - 移除分群管理员
/设置 admin list       - 查看分群管理员""")
            return
        
        if args[0] == 'admin':
            if len(args) < 2:
                yield event.plain_result("📖 /设置 admin add/remove/list <QQ>")
                return
            
            action = args[1]
            custom_admins = config.get('custom_admins', [])
            
            if action == 'list':
                if not custom_admins:
                    yield event.plain_result("❌ 无分群管理员")
                    return
                yield event.plain_result(f"👥 分群管理员:\n" + "\n".join([f"- QQ{qq}" for qq in custom_admins]))
                return
            
            if not self.utils._is_group_admin(event):
                yield event.plain_result("❌ 仅群管理员可管理")
                return
            
            if len(args) < 3:
                yield event.plain_result(f"📖 /设置 admin {action} <QQ>")
                return
            
            target_qq = args[2]
            
            if action == 'add':
                if target_qq in custom_admins:
                    yield event.plain_result("❌ 该用户已是分群管理员")
                    return
                custom_admins.append(target_qq)
                self.data_manager._save_group_config(group_id, 'custom_admins', custom_admins)
                yield event.plain_result(f"✅ 已添加分群管理员: {target_qq}")
            elif action == 'remove':
                if target_qq not in custom_admins:
                    yield event.plain_result("❌ 该用户不是分群管理员")
                    return
                custom_admins.remove(target_qq)
                self.data_manager._save_group_config(group_id, 'custom_admins', custom_admins)
                yield event.plain_result(f"✅ 已移除分群管理员: {target_qq}")
            else:
                yield event.plain_result("❌ 未知操作")

    @filter.command("名片")
    async def card_management(self, event: AstrMessageEvent, *args):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._getGroupId(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        if not args:
            yield event.plain_result("📖 名片命令\n\n/名片 set <QQ> <昵称> - 设置群名片\n/名片 get <QQ>        - 查看群名片")
            return
        
        if args[0] == 'set' and len(args) >= 3:
            target_qq = args[1]
            card_name = args[2]
            
            try:
                if self.context:
                    await self.context.call_api("set_group_card", group_id=int(group_id), user_id=int(target_qq), card=card_name)
                    yield event.plain_result(f"✅ 已设置 QQ{target_qq} 的名片为: {card_name}")
            except Exception as e:
                yield event.plain_result(f"❌ 设置失败: {e}")
        elif args[0] == 'get' and len(args) >= 2:
            yield event.plain_result("📖 获取名片功能开发中")
        else:
            yield event.plain_result("❌ 参数错误")

    @filter.command("回复")
    async def private_reply(self, event: AstrMessageEvent, *args):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        if not args:
            yield event.plain_result("📖 回复命令\n\n/回复 <QQ> <消息> - 发送私聊消息")
            return
        
        if len(args) < 2:
            yield event.plain_result("❌ 参数不足")
            return
        
        target_qq = args[0]
        message = ' '.join(args[1:])
        
        try:
            if self.context:
                await self.context.call_api("send_private_msg", user_id=int(target_qq), message=message)
                yield event.plain_result(f"✅ 消息已发送给 QQ{target_qq}")
        except Exception as e:
            yield event.plain_result(f"❌ 发送失败: {e}")

    @filter.command("自动回复")
    async def auto_reply_management(self, event: AstrMessageEvent, *args):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._getGroupId(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        if not args:
            auto_replies = self.data_manager._get_group_data(group_id, 'auto_replies', {})
            config = self.data_manager.get_effective_config(group_id)
            
            status = f"""🤖 自动回复

状态: {'开启' if config.get('auto_reply_enabled', False) else '关闭'}
冷却: {config.get('auto_reply_cooldown', 5)}秒
规则数: {len(auto_replies)}

子命令:
/自动回复 on/off          - 开关自动回复
/自动回复 add <词> <回复>  - 添加规则
/自动回复 del <词>         - 删除规则
/自动回复 list             - 查看规则列表"""
            yield event.plain_result(status)
            return
        
        sub_cmd = args[0]
        
        if sub_cmd == 'on':
            self.data_manager._save_group_config(group_id, 'auto_reply_enabled', True)
            yield event.plain_result("✅ 自动回复已开启")
        elif sub_cmd == 'off':
            self.data_manager._save_group_config(group_id, 'auto_reply_enabled', False)
            yield event.plain_result("✅ 自动回复已关闭")
        elif sub_cmd == 'list':
            auto_replies = self.data_manager._get_group_data(group_id, 'auto_replies', {})
            if not auto_replies:
                yield event.plain_result("❌ 暂无自动回复规则")
                return
            result = "📝 自动回复规则:\n\n"
            for trigger, data in auto_replies.items():
                replies = data.get('replies', [])
                priority = data.get('priority', 1)
                result += f"[{priority}] {trigger} -> {replies[0] if replies else ''}\n"
            yield event.plain_result(result)
        elif sub_cmd == 'add' and len(args) >= 3:
            trigger = args[1]
            reply = ' '.join(args[2:])
            
            auto_replies = self.data_manager._get_group_data(group_id, 'auto_replies', {})
            
            if trigger in auto_replies:
                replies = auto_replies[trigger]['replies']
                if reply not in replies:
                    replies.append(reply)
                auto_replies[trigger]['replies'] = replies
            else:
                auto_replies[trigger] = {
                    'replies': [reply],
                    'priority': 1,
                    'exact_match': False
                }
            
            self.data_manager._set_group_data('auto_replies', auto_replies, group_id)
            yield event.plain_result(f"✅ 已添加: {trigger} -> {reply}")
        elif sub_cmd == 'del' and len(args) >= 2:
            trigger = args[1]
            auto_replies = self.data_manager._get_group_data(group_id, 'auto_replies', {})
            
            if trigger in auto_replies:
                del auto_replies[trigger]
                self.data_manager._set_group_data('auto_replies', auto_replies, group_id)
                yield event.plain_result(f"✅ 已删除: {trigger}")
            else:
                yield event.plain_result(f"❌ 不存在: {trigger}")
        else:
            yield event.plain_result("❌ 参数错误")

    @filter.command("定时消息")
    async def schedule_management(self, event: AstrMessageEvent, *args):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._getGroupId(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        if not args:
            yield event.plain_result("📖 定时消息\n\n/定时消息 add <HH:MM> <内容> - 添加\n/定时消息 list                - 查看\n/定时消息 del <ID>           - 删除")
            return
        
        sub_cmd = args[0]
        
        if sub_cmd == 'list':
            schedule_list = self.data_manager._get_group_data(group_id, 'schedule_list', [])
            if not schedule_list:
                yield event.plain_result("❌ 暂无定时消息")
                return
            result = "⏰ 定时消息列表:\n\n"
            for i, item in enumerate(schedule_list, 1):
                result += f"{i}. [{item.get('time', '')}] {item.get('content', '')}\n"
            yield event.plain_result(result)
        elif sub_cmd == 'add' and len(args) >= 3:
            time_str = args[1]
            content = ' '.join(args[2:])
            
            schedule_list = self.data_manager._get_group_data(group_id, 'schedule_list', [])
            schedule_list.append({'time': time_str, 'content': content, 'enabled': True})
            self.data_manager._set_group_data('schedule_list', schedule_list, group_id)
            yield event.plain_result(f"✅ 已添加定时消息: [{time_str}] {content}")
        elif sub_cmd == 'del' and len(args) >= 2:
            try:
                idx = int(args[1]) - 1
                schedule_list = self.data_manager._get_group_data(group_id, 'schedule_list', [])
                if 0 <= idx < len(schedule_list):
                    deleted = schedule_list.pop(idx)
                    self.data_manager._set_group_data('schedule_list', schedule_list, group_id)
                    yield event.plain_result(f"✅ 已删除: [{deleted.get('time', '')}] {deleted.get('content', '')}")
                else:
                    yield event.plain_result("❌ 索引错误")
            except ValueError:
                yield event.plain_result("❌ 无效的索引")
        else:
            yield event.plain_result("❌ 参数错误")

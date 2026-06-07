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

    def __init__(self, data_manager: DataManager, utils: Utils, context=None, message_history=None, self_messages=None):
        self.data_manager = data_manager
        self.utils = utils
        self.context = context
        self.message_history = message_history or {}
        self.self_messages = self_messages or {}  # 机器人发送的消息记录（从主文件传入）
        
    def record_self_message(self, group_id: str, message_id: int):
        """记录机器人发送的消息"""
        if group_id not in self.self_messages:
            self.self_messages[group_id] = []
        self.self_messages[group_id].append((message_id, time.time()))

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

    @filter.command("自动回复")
    async def help_auto_reply(self, event: AstrMessageEvent):
        await self._show_category_help("自动回复", event)

    @filter.command("主人专属")
    async def help_owner(self, event: AstrMessageEvent):
        await self._show_category_help("主人专属", event)

    async def _show_category_help(self, category: str, event: AstrMessageEvent):
        help_texts = {
            '审核系统': """📝 审核系统
├─ /入群审核 math - 数学验证
├─ /入群审核 id - 随机ID验证
├─ /入群审核 同意/拒绝 <QQ> - 手动审核
├─ /入群审核 设置 - 查看设置
└─ /审核自定义次数 <次数> - 设置验证次数""",
            '欢迎系统': """📢 欢迎系统
├─ /欢迎 on - 开启欢迎
├─ /欢迎 off - 关闭欢迎
└─ /添加欢迎语 <内容> - 设置欢迎语""",
            '撤回系统': """🗑️ 撤回系统
├─ /撤回 <数量> - 撤回最近N条消息
├─ /撤回 用户 <QQ> <数量> - 撤回指定用户N条消息
├─ /撤回 用户 <QQ> - 撤回指定用户所有消息
├─ /撤回 <消息ID> - 撤回指定消息
├─ /开启撤回自身 - 开启机器人自动撤回自己的消息
├─ /关闭撤回自身 - 关闭机器人自动撤回自己的消息
└─ /设置撤回时间 <秒数> - 设置机器人消息自动撤回时间""",
            '自动回复': """🤖 自动回复
├─ /自动回复 on - 开启自动回复
├─ /自动回复 off - 关闭自动回复
├─ /添加/模糊 问 答 - 添加模糊匹配回复
├─ /添加/精准 问 答 - 添加精准匹配回复
├─ /添加用户回复 <QQ> <内容> - 特定用户发言时自动回复
├─ /添加用户回复 <QQ> @ <内容> - 回复时@该用户
├─ /查看用户回复列表 - 查看用户回复规则
├─ /删除用户回复 <QQ> - 删除用户回复规则
├─ /查看回复列表 - 查看所有回复规则
└─ /设置回复冷却时间 <秒> - 设置关键词回复冷却""",
            '踢出系统': """👢 踢出系统
├─ /踢出 <QQ> - 踢出用户
├─ /踢出 <QQ> <理由> - 踢出用户并指定理由
├─ /踢出 连带 <QQ> - 踢出用户及其邀请的所有成员
└─ /查看踢出记录 - 查看踢出记录""",
            '禁言系统': """🔇 禁言系统
├─ /禁言 <QQ> - 使用默认时间禁言
├─ /禁言 <QQ> <时长> [理由] - 禁言用户(1s/1m/1h/1d)
├─ /解禁 <QQ> - 解除禁言
├─ /查看禁言列表 - 查看禁言列表
├─ /清空禁言列表 - 清空禁言列表并全部解禁
├─ /全体禁言 - 开启全体禁言
├─ /全体解禁 - 关闭全体禁言
├─ /定时禁言 <开始> <结束> - 设置时间段全体禁言
├─ /添加关键词禁言 <词> - 添加禁言关键词
├─ /删除关键词禁言 <词> - 删除禁言关键词
└─ /设置默认禁言时间 <分钟> - 设置默认禁言时间""",
            '定时消息': """⏰ 定时消息
├─ /定时消息 add <时间> <内容> - 添加定时消息
├─ /定时消息 addall <时间> <内容> - 添加@全体定时消息
├─ /定时消息 list - 查看列表
└─ /定时消息 del <序号> - 删除""",
            '分群设置': """⚙️ 分群设置
├─ /设置 admin add <QQ> - 添加分群管理员
├─ /设置 admin remove <QQ> - 移除分群管理员
├─ /设置 admin list - 查看管理员列表
├─ /设置 - 查看本群所有配置
└─ /克隆全局配置 - 将全局配置克隆到当前群""",

            '主人专属': """👑 主人专属（仅机器人主人可用）
├─ /添加主人 <QQ> - 添加机器人主人
├─ /移除主人 <QQ> - 移除机器人主人
├─ /查看主人 - 查看主人列表
├─ /查看全局配置 - 查看所有全局配置
├─ /修改全局配置 <配置名> <值> - 修改全局配置
├─ /重置全局配置 confirm - 重置全局配置为默认值
├─ /添加群白名单 <群号> - 添加群到白名单（不受功能限制）
├─ /移除群白名单 <群号> - 从白名单移除群
├─ /查看群白名单 - 查看白名单列表
├─ /添加过滤群 <群号> - 添加群到过滤列表（不自动回复）
├─ /移除过滤群 <群号> - 从过滤列表移除群
└─ /查看过滤群 - 查看过滤群列表""",
            '统计系统': """📊 统计系统
├─ /签到 - 每日签到获得积分
├─ /排行榜 - 查看积分排行榜
├─ /我的信息 - 查看个人签到数据
└─ /统计 - 查看群统计概览""",
            '黑名单系统': """🚫 黑名单系统
├─ /拉黑 <QQ> [理由] - 拉黑用户
├─ /删黑 <QQ> - 移除黑名单
├─ /清空黑名单 - 清空黑名单
└─ /查看黑名单 - 查看列表"""
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
        # 不限制消息历史条数，以便踢出时可以撤回所有发言
        
        config = self.data_manager.get_effective_config(group_id)
        
        if self.utils._is_admin(event):
            await self._handle_auto_reply(event, group_id, user_id, config)
            return
        
        blacklist = self.data_manager._get_group_data(group_id, 'blacklist', {'users': []})
        
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
        
        await self._handle_auto_reply(event, group_id, user_id, config)

    async def _handle_auto_reply(self, event: AstrMessageEvent, group_id: str, user_id: str, config: Dict):
        """处理自动回复"""
        # 检查群是否在过滤列表中
        if self.data_manager.is_group_filtered(group_id):
            return
        
        if not config.get('auto_reply_enabled', False):
            return
        
        message_text = event.message_str or ""
        
        # 首先检查针对特定用户的回复规则（不受冷却时间限制）
        user_replies = self.data_manager._get_group_data(group_id, 'user_replies', [])
        for item in user_replies:
            target_user = item.get('user_id', '')
            reply = item.get('reply', '')
            at_user = item.get('at_user', False)
            
            if target_user == user_id:
                # 三种回复形式
                if at_user and reply:
                    # 形式3：@用户 + 消息
                    reply = f"[CQ:at,qq={user_id}] {reply}"
                elif at_user and not reply:
                    # 形式1：只@用户
                    reply = f"[CQ:at,qq={user_id}]"
                else:
                    # 形式2：只回复消息
                    reply = self._replace_variables(reply, event)
                
                yield event.plain_result(reply)
                return
        
        # 然后检查普通自动回复规则（关键词回复，受冷却时间限制）
        if not hasattr(self, 'auto_reply_cooldowns'):
            self.auto_reply_cooldowns = {}
        
        cooldown = config.get('auto_reply_cooldown', 5)
        now = time.time()
        
        if group_id not in self.auto_reply_cooldowns:
            self.auto_reply_cooldowns[group_id] = {}
        
        last_time = self.auto_reply_cooldowns[group_id].get(user_id, 0)
        if now - last_time < cooldown:
            return
        
        auto_replies = self.data_manager._get_group_data(group_id, 'auto_replies', [])
        
        if not auto_replies:
            return
        
        auto_reply_at_user = config.get('auto_reply_at_user', False)
        at_prefix = f"[CQ:at,qq={user_id}] " if auto_reply_at_user else ""
        
        # 先检查精准匹配，再检查模糊匹配
        for item in auto_replies:
            trigger = item.get('trigger', '')
            reply = item.get('reply', '')
            match_type = item.get('match_type', 'fuzzy')
            
            if match_type == 'exact' and message_text == trigger:
                reply = self._replace_variables(reply, event)
                yield event.plain_result(f"{at_prefix}{reply}")
                self.auto_reply_cooldowns[group_id][user_id] = now
                return
        
        for item in auto_replies:
            trigger = item.get('trigger', '')
            reply = item.get('reply', '')
            match_type = item.get('match_type', 'fuzzy')
            
            if match_type == 'fuzzy' and trigger in message_text:
                reply = self._replace_variables(reply, event)
                yield event.plain_result(f"{at_prefix}{reply}")
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
        if not self.utils._is_group_authorized(event):
            yield event.plain_result("❌ 本群尚未授权，请联系机器人主人进行 SCUM 授权")
            return
        
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        if not args:
            yield event.plain_result("""📖 撤回命令帮助

/撤回 <数量>                 - 撤回最近N条消息
/撤回 用户 <QQ> <数量>       - 撤回指定用户的N条消息
/撤回 用户 <QQ>              - 撤回指定用户的所有消息
/撤回 <消息ID>               - 撤回指定消息""")
            return
        
        try:
            if args[0] == "用户":
                if len(args) >= 2:
                    target_qq = args[1]
                    if len(args) >= 3:
                        # /撤回 用户 <QQ> <数量>
                        count = int(args[2])
                        await self._recall_user_messages(group_id, target_qq, count, event)
                    else:
                        # /撤回 用户 <QQ> - 撤回所有消息
                        await self._recall_user_messages(group_id, target_qq, None, event)
            elif args[0].isdigit():
                count = int(args[0])
                await self._recall_recent_messages(group_id, count, event)
            else:
                message_id = int(args[0])
                await self._recall_single_message(group_id, message_id, event)
        except ValueError:
            yield event.plain_result("❌ 参数错误")

    async def _recall_recent_messages(self, group_id: str, count: int, event: AstrMessageEvent):
        """撤回最近的消息"""
        # 获取所有消息，取最近的count条
        all_messages = self.message_history.get(group_id, [])
        messages = all_messages[-count:] if count > 0 else all_messages
        
        if not messages:
            yield event.plain_result("❌ 无可撤回的消息")
            return
        
        success = 0
        for msg in messages:
            if await self._recall_message_by_id(msg['message_id']):
                success += 1
        
        yield event.plain_result(f"✅ 已撤回 {success} 条消息")

    async def _recall_user_messages(self, group_id: str, user_id: str, count: int | None, event: AstrMessageEvent):
        """撤回指定用户的消息"""
        # 获取所有消息
        all_messages = self.message_history.get(group_id, [])
        user_messages = [m for m in all_messages if m['user_id'] == user_id]
        
        # 如果指定了数量，只取前count条
        if count is not None:
            user_messages = user_messages[-count:]
        
        if not user_messages:
            yield event.plain_result(f"❌ 未找到用户 {user_id} 的消息")
            return
        
        success = 0
        for msg in user_messages:
            if await self._recall_message_by_id(msg['message_id']):
                success += 1
        
        if count is None:
            yield event.plain_result(f"✅ 已撤回用户 {user_id} 的全部 {success} 条消息")
        else:
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
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        if not args or args[0] not in ['on', 'off']:
            yield event.plain_result("📖 欢迎命令\n\n/欢迎 on  - 开启欢迎\n/欢迎 off - 关闭欢迎")
            return
        
        enabled = args[0] == 'on'
        self.data_manager._save_group_config(group_id, 'welcome_enabled', enabled)
        yield event.plain_result(f"✅ 欢迎功能已{'开启' if enabled else '关闭'}")

    @filter.command("添加欢迎语")
    async def add_welcome(self, event: AstrMessageEvent, *args):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        if not args:
            current = self.data_manager._get_group_data(group_id, 'config', {}).get('welcome_message', '')
            yield event.plain_result(f"📝 当前欢迎语:\n{current or '未设置'}\n\n/添加欢迎语 <内容>")
            return
        
        welcome_msg = ' '.join(args)
        self.data_manager._save_group_config(group_id, 'welcome_message', welcome_msg)
        yield event.plain_result(f"✅ 欢迎语已设置:\n@用户 加入群 {welcome_msg}")

    @filter.command("签到")
    async def sign_in(self, event: AstrMessageEvent):
        user_id = self.utils._get_user_id(event)
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        config = self.data_manager.get_effective_config(group_id)
        if not config.get('sign_enabled', True):
            yield event.plain_result("❌ 签到功能已关闭")
            return
        
        sign_data = self.data_manager._get_group_data(group_id, 'sign_data', {})
        today = time.strftime("%Y-%m-%d")
        now = time.time()
        
        if user_id in sign_data and sign_data[user_id].get('date') == today:
            at_prefix = f"[CQ:at,qq={user_id}] " if config.get('sign_at_user', False) else ""
            yield event.plain_result(f"{at_prefix}❌ 今日已签到！\n签到时间: {sign_data[user_id]['time']}")
            return
        
        base_points = config.get('sign_bonus_points', 10)
        last_date = sign_data.get(user_id, {}).get('date')
        yesterday = time.strftime("%Y-%m-%d", time.localtime(now - 86400))
        continuous_days = sign_data.get(user_id, {}).get('continuous_days', 0) + 1 if last_date == yesterday else 1
        total_points = sign_data.get(user_id, {}).get('total_points', 0) + base_points
        
        sign_data[user_id] = {
            'date': today,
            'time': time.strftime("%H:%M:%S"),
            'points': base_points,
            'total_points': total_points,
            'continuous_days': continuous_days,
            'sign_count': sign_data.get(user_id, {}).get('sign_count', 0) + 1,
            'nickname': event.get_sender_name()
        }
        
        self.data_manager._set_group_data('sign_data', sign_data, group_id)
        
        bonus = config.get('sign_continuous_bonus', 2) * (continuous_days - 1)
        earned = base_points + bonus
        
        # 计算排名
        sorted_users = sorted(sign_data.items(), key=lambda x: x[1].get('total_points', 0), reverse=True)
        rank = next((i for i, (qq, _) in enumerate(sorted_users, 1) if qq == user_id), len(sorted_users))
        
        at_prefix = f"[CQ:at,qq={user_id}] " if config.get('sign_at_user', False) else ""
        yield event.plain_result(f"{at_prefix}✅ 签到成功！\n\n👤 用户: {event.get_sender_name()}\n📅 日期: {today}\n⏰ 时间: {sign_data[user_id]['time']}\n💰 获得积分: +{earned}\n🎯 累计积分: {total_points}\n🔥 连续签到: {continuous_days} 天\n📊 累计签到: {sign_data[user_id]['sign_count']} 次\n🏅 当前排名: 第{rank}名")

    @filter.command("排行榜")
    async def leaderboard(self, event: AstrMessageEvent, *args):
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        sign_data = self.data_manager._get_group_data(group_id, 'sign_data', {})
        
        if not sign_data:
            yield event.plain_result("❌ 暂无签到数据")
            return
        
        sorted_users = sorted(sign_data.items(), key=lambda x: x[1].get('total_points', 0), reverse=True)[:15]
        
        result = "🏆 积分排行榜\n\n"
        medals = ['🥇', '🥈', '🥉']
        for i, (qq, data) in enumerate(sorted_users, 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            nickname = data.get('nickname', f'QQ{qq}')
            result += f"{medal} {nickname} - {data.get('total_points', 0)}积分\n"
            result += f"   连续:{data.get('continuous_days', 0)}天 | 累计:{data.get('sign_count', 0)}次\n"
        
        yield event.plain_result(result)

    @filter.command("我的信息")
    async def my_info(self, event: AstrMessageEvent):
        user_id = self.utils._get_user_id(event)
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        sign_data = self.data_manager._get_group_data(group_id, 'sign_data', {})
        user_data = sign_data.get(user_id, {})
        
        # 计算排名
        sorted_users = sorted(sign_data.items(), key=lambda x: x[1].get('total_points', 0), reverse=True)
        rank = next((i for i, (qq, _) in enumerate(sorted_users, 1) if qq == user_id), len(sorted_users))
        
        # 今日签到状态
        today = time.strftime("%Y-%m-%d")
        today_sign = "✅" if user_data.get('date') == today else "❌"
        
        yield event.plain_result(f"""👤 个人信息

📱 QQ: {user_id}
🎭 昵称: {event.get_sender_name()}
💰 累计积分: {user_data.get('total_points', 0)}
📅 最后签到: {user_data.get('date', '从未签到')}
⏰ 签到时间: {user_data.get('time', '-')}
🔥 连续签到: {user_data.get('continuous_days', 0)} 天
📊 累计签到: {user_data.get('sign_count', 0)} 次
🏅 当前排名: 第{rank}名 (共{len(sign_data)}人)
📌 今日签到: {today_sign}""")

    @filter.command("统计")
    async def statistics(self, event: AstrMessageEvent):
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        sign_data = self.data_manager._get_group_data(group_id, 'sign_data', {})
        kick_logs = self.data_manager._get_group_data(group_id, 'kick_logs', [])
        muted_users = self.data_manager._get_group_data(group_id, 'muted_users', [])
        blacklist = self.data_manager._get_group_data(group_id, 'blacklist', {'users': []})
        
        # 计算今日签到人数
        today = time.strftime("%Y-%m-%d")
        today_sign_count = sum(1 for data in sign_data.values() if data.get('date') == today)
        
        # 计算总积分
        total_points = sum(data.get('total_points', 0) for data in sign_data.values())
        
        # 连续签到最多
        max_continuous = max((data.get('continuous_days', 0) for data in sign_data.values()), default=0)
        
        # 签到最多的人
        sign_count_user = max(sign_data.items(), key=lambda x: x[1].get('sign_count', 0), default=None)
        
        yield event.plain_result(f"""📊 群统计概览

━━━━━━━━━━━━━━━━━━━
👥 签到统计
━━━━━━━━━━━━━━━━━━━
📅 今日签到: {today_sign_count} 人
👥 累计签到: {len(sign_data)} 人
💰 总积分: {total_points}
🔥 最高连续: {max_continuous} 天
📈 签到最多: {sign_count_user[0] if sign_count_user else '-'} ({sign_count_user[1].get('sign_count', 0)}次)

━━━━━━━━━━━━━━━━━━━
🔧 管理统计
━━━━━━━━━━━━━━━━━━━
👢 踢出记录: {len(kick_logs)} 条
🔇 禁言中: {len(muted_users)} 人
🚫 黑名单: {len(blacklist.get('users', []))} 人""")

    @filter.command("设置")
    async def group_settings(self, event: AstrMessageEvent, *args):
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        config = self.data_manager.get_effective_config(group_id)
        
        if not args:
            # 获取各种配置数据
            auto_replies = self.data_manager._get_group_data(group_id, 'auto_replies', [])
            blacklist = self.data_manager._get_group_data(group_id, 'blacklist', {'users': []})
            mute_keywords = self.data_manager._get_group_data(group_id, 'mute_keywords', [])
            schedule_list = self.data_manager._get_group_data(group_id, 'schedule_list', [])
            custom_admins = config.get('custom_admins', [])
            approval_mode = config.get('approval_mode', 'math')
            
            # 构建配置信息
            config_info = f"""⚙️ 群设置 [{group_id}]

━━━━━━━━━━━━━━━━━━━
🔧 功能开关
━━━━━━━━━━━━━━━━━━━
欢迎功能: {'✅开启' if config.get('welcome_enabled', True) else '❌关闭'}
自动回复: {'✅开启' if config.get('auto_reply_enabled', False) else '❌关闭'}
反垃圾: {'✅开启' if config.get('anti_spam_enabled', True) else '❌关闭'}
签到: {'✅开启' if config.get('sign_enabled', True) else '❌关闭'}
撤回自身: {'✅开启' if config.get('self_recall_enabled', False) else '❌关闭'}

━━━━━━━━━━━━━━━━━━━
📝 审核设置
━━━━━━━━━━━━━━━━━━━
审核方式: {'数学验证' if approval_mode == 'math' else '随机验证'}
验证次数: {config.get('max_attempts', 3)}次

━━━━━━━━━━━━━━━━━━━
🔇 禁言设置
━━━━━━━━━━━━━━━━━━━
默认禁言时间: {config.get('default_mute_duration', 30)}分钟
定时禁言: {'✅开启' if config.get('scheduled_mute_enabled', False) else '❌关闭'}
{config.get('scheduled_mute_start', '')} - {config.get('scheduled_mute_end', '')}
关键词禁言: {len(mute_keywords)}个

━━━━━━━━━━━━━━━━━━━
💬 自动回复
━━━━━━━━━━━━━━━━━━━
规则数: {len(auto_replies)}条
冷却时间: {config.get('auto_reply_cooldown', 5)}秒

━━━━━━━━━━━━━━━━━━━
🚫 黑名单
━━━━━━━━━━━━━━━━━━━
黑名单用户: {len(blacklist.get('users', []))}人

━━━━━━━━━━━━━━━━━━━
⏰ 定时消息
━━━━━━━━━━━━━━━━━━━
定时消息: {len(schedule_list)}条

━━━━━━━━━━━━━━━━━━━
👥 分群管理员
━━━━━━━━━━━━━━━━━━━
管理员数: {len(custom_admins)}人
"""
            yield event.plain_result(config_info)
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
        
        group_id = self.utils._get_group_id(event)
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

    @filter.command("自动回复 on")
    async def auto_reply_on(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        self.data_manager._save_group_config(group_id, 'auto_reply_enabled', True)
        yield event.plain_result("✅ 自动回复已开启")

    @filter.command("自动回复 off")
    async def auto_reply_off(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        self.data_manager._save_group_config(group_id, 'auto_reply_enabled', False)
        yield event.plain_result("✅ 自动回复已关闭")

    @filter.command("添加/模糊")
    async def add_fuzzy_reply(self, event: AstrMessageEvent, *args):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        if len(args) < 2:
            yield event.plain_result("📖 使用方法:\n/添加/模糊 问 答")
            return
        
        trigger = args[0]
        reply = ' '.join(args[1:])
        
        auto_replies = self.data_manager._get_group_data(group_id, 'auto_replies', [])
        auto_replies.append({
            'trigger': trigger,
            'reply': reply,
            'match_type': 'fuzzy'
        })
        
        self.data_manager._set_group_data('auto_replies', auto_replies, group_id)
        yield event.plain_result(f"✅ 已添加模糊回复:\n问: {trigger}\n答: {reply}")

    @filter.command("添加/精准")
    async def add_exact_reply(self, event: AstrMessageEvent, *args):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        if len(args) < 2:
            yield event.plain_result("📖 使用方法:\n/添加/精准 问 答")
            return
        
        trigger = args[0]
        reply = ' '.join(args[1:])
        
        auto_replies = self.data_manager._get_group_data(group_id, 'auto_replies', [])
        auto_replies.append({
            'trigger': trigger,
            'reply': reply,
            'match_type': 'exact'
        })
        
        self.data_manager._set_group_data('auto_replies', auto_replies, group_id)
        yield event.plain_result(f"✅ 已添加精准回复:\n问: {trigger}\n答: {reply}")

    @filter.command("添加用户回复")
    async def add_user_reply(self, event: AstrMessageEvent, *args):
        """添加针对特定用户的自动回复"""
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        if len(args) < 2:
            yield event.plain_result("""📖 使用方法:
/添加用户回复 <QQ> <消息> - 用户发言时回复消息
/添加用户回复 <QQ> @ - 用户发言时只@该用户
/添加用户回复 <QQ> @ <消息> - 用户发言时@并回复消息""")
            return
        
        target_qq = args[0]
        at_user = False
        reply_content = ''
        
        # 只输入了QQ和@符号，没有消息内容
        if len(args) == 2 and args[1] == '@':
            at_user = True
            reply_content = ''
        # 输入了QQ、@和消息内容
        elif len(args) >= 3 and args[1] == '@':
            at_user = True
            reply_content = ' '.join(args[2:])
        else:
            # 只输入了QQ和消息内容
            at_user = False
            reply_content = ' '.join(args[1:])
        
        if not target_qq.isdigit():
            yield event.plain_result("❌ QQ号必须是数字")
            return
        
        user_replies = self.data_manager._get_group_data(group_id, 'user_replies', [])
        
        # 检查是否已存在该用户的回复规则
        existing = next((item for item in user_replies if item['user_id'] == target_qq), None)
        if existing:
            existing['reply'] = reply_content
            existing['at_user'] = at_user
        else:
            user_replies.append({
                'user_id': target_qq,
                'reply': reply_content,
                'at_user': at_user
            })
        
        self.data_manager._set_group_data('user_replies', user_replies, group_id)
        self.data_manager._save_group_data('user_replies')
        
        # 显示不同的回复形式
        if at_user and reply_content:
            result = f"✅ 已添加用户回复规则（@用户+消息）\n用户: {target_qq}\n回复: [CQ:at,qq={target_qq}] {reply_content}"
        elif at_user and not reply_content:
            result = f"✅ 已添加用户回复规则（只@用户）\n用户: {target_qq}\n回复: [CQ:at,qq={target_qq}]"
        else:
            result = f"✅ 已添加用户回复规则（消息）\n用户: {target_qq}\n回复: {reply_content}"
        
        yield event.plain_result(result)

    @filter.command("删除用户回复")
    async def remove_user_reply(self, event: AstrMessageEvent, *args):
        """删除针对特定用户的自动回复"""
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        if len(args) < 1:
            yield event.plain_result("📖 使用方法:\n/删除用户回复 <QQ>")
            return
        
        target_qq = args[0]
        
        user_replies = self.data_manager._get_group_data(group_id, 'user_replies', [])
        original_count = len(user_replies)
        user_replies = [item for item in user_replies if item['user_id'] != target_qq]
        
        if len(user_replies) < original_count:
            self.data_manager._set_group_data('user_replies', user_replies, group_id)
            self.data_manager._save_group_data('user_replies')
            yield event.plain_result(f"✅ 已删除用户 {target_qq} 的回复规则")
        else:
            yield event.plain_result(f"❌ 用户 {target_qq} 没有回复规则")

    @filter.command("查看用户回复列表")
    async def view_user_reply_list(self, event: AstrMessageEvent):
        """查看所有针对特定用户的回复规则"""
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        user_replies = self.data_manager._get_group_data(group_id, 'user_replies', [])
        
        if not user_replies:
            yield event.plain_result("❌ 暂无用户回复规则")
            return
        
        result = "👤 用户回复规则:\n\n"
        for i, item in enumerate(user_replies, 1):
            user_id = item.get('user_id', '')
            reply = item.get('reply', '')
            at_user = item.get('at_user', False)
            
            # 显示不同的回复形式
            if at_user and reply:
                reply_type = "[@+消息]"
                reply_display = f"[CQ:at,qq={user_id}] {reply}"
            elif at_user and not reply:
                reply_type = "[@用户]"
                reply_display = f"[CQ:at,qq={user_id}]"
            else:
                reply_type = "[消息]"
                reply_display = reply
            
            result += f"{i}. {user_id} {reply_type} -> {reply_display}\n"
        
        yield event.plain_result(result)

    @filter.command("查看回复列表")
    async def view_reply_list(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        auto_replies = self.data_manager._get_group_data(group_id, 'auto_replies', [])
        
        if not auto_replies:
            yield event.plain_result("❌ 暂无自动回复规则")
            return
        
        result = "📝 自动回复规则:\n\n"
        for i, item in enumerate(auto_replies, 1):
            trigger = item.get('trigger', '')
            reply = item.get('reply', '')
            match_type = item.get('match_type', 'fuzzy')
            type_str = "精准" if match_type == 'exact' else "模糊"
            result += f"{i}. [{type_str}] {trigger} -> {reply}\n"
        
        yield event.plain_result(result)

    @filter.command("设置回复冷却时间")
    async def set_reply_cooldown(self, event: AstrMessageEvent, *args):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        if len(args) < 1:
            config = self.data_manager.get_effective_config(group_id)
            current = config.get('auto_reply_cooldown', 5)
            yield event.plain_result(f"📖 使用方法:\n/设置回复冷却时间 <秒数>\n当前冷却时间: {current}秒\n注意: 仅关键词回复受冷却限制")
            return
        
        try:
            seconds = int(args[0])
            if seconds < 0:
                yield event.plain_result("❌ 冷却时间不能为负数")
                return
            
            self.data_manager._save_group_config(group_id, 'auto_reply_cooldown', seconds)
            yield event.plain_result(f"✅ 回复冷却时间已设置为: {seconds}秒")
        except ValueError:
            yield event.plain_result("❌ 请输入有效的数字")

    @filter.command("定时消息")
    async def schedule_management(self, event: AstrMessageEvent, *args):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        if not args:
            yield event.plain_result("📖 定时消息\n\n/定时消息 add <HH:MM> <内容> - 添加定时消息\n/定时消息 addall <HH:MM> <内容> - 添加@全体定时消息\n/定时消息 list - 查看列表\n/定时消息 del <ID> - 删除")
            return
        
        sub_cmd = args[0]
        
        if sub_cmd == 'list':
            schedule_list = self.data_manager._get_group_data(group_id, 'schedule_list', [])
            if not schedule_list:
                yield event.plain_result("❌ 暂无定时消息")
                return
            result = "⏰ 定时消息列表:\n\n"
            for i, item in enumerate(schedule_list, 1):
                at_all = " @全体" if item.get('at_all', False) else ""
                result += f"{i}. [{item.get('time', '')}]{at_all} {item.get('content', '')}\n"
            yield event.plain_result(result)
        elif sub_cmd == 'add' and len(args) >= 3:
            time_str = args[1]
            content = ' '.join(args[2:])
            
            schedule_list = self.data_manager._get_group_data(group_id, 'schedule_list', [])
            schedule_list.append({'time': time_str, 'content': content, 'enabled': True, 'at_all': False})
            self.data_manager._set_group_data('schedule_list', schedule_list, group_id)
            yield event.plain_result(f"✅ 已添加定时消息: [{time_str}] {content}")
        elif sub_cmd == 'addall' and len(args) >= 3:
            time_str = args[1]
            content = ' '.join(args[2:])
            
            schedule_list = self.data_manager._get_group_data(group_id, 'schedule_list', [])
            schedule_list.append({'time': time_str, 'content': content, 'enabled': True, 'at_all': True})
            self.data_manager._set_group_data('schedule_list', schedule_list, group_id)
            yield event.plain_result(f"✅ 已添加定时消息(@全体): [{time_str}] {content}")
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

    @filter.command("开启撤回自身")
    async def enable_self_recall(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        self.data_manager._save_group_config(group_id, 'self_recall_enabled', True)
        yield event.plain_result("✅ 已开启机器人自动撤回自身消息功能")

    @filter.command("关闭撤回自身")
    async def disable_self_recall(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        self.data_manager._save_group_config(group_id, 'self_recall_enabled', False)
        yield event.plain_result("✅ 已关闭机器人自动撤回自身消息功能")

    @filter.command("设置撤回时间")
    async def set_self_recall_time(self, event: AstrMessageEvent, *args):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        if len(args) < 1:
            config = self.data_manager.get_effective_config(group_id)
            current = config.get('self_recall_time', 10)
            yield event.plain_result(f"📖 使用方法:\n/设置撤回时间 <秒数>\n当前撤回时间: {current}秒")
            return
        
        try:
            seconds = int(args[0])
            if seconds < 1:
                yield event.plain_result("❌ 撤回时间至少为1秒")
                return
            
            self.data_manager._save_group_config(group_id, 'self_recall_time', seconds)
            yield event.plain_result(f"✅ 机器人自动撤回时间已设置为: {seconds}秒")
        except ValueError:
            yield event.plain_result("❌ 请输入有效的数字")

    @filter.command("添加主人")
    async def add_owner(self, event: AstrMessageEvent, *args):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 仅机器人主人可使用此命令")
            return
        
        if len(args) < 1:
            yield event.plain_result("📖 使用方法:\n/添加主人 <QQ>")
            return
        
        user_id = args[0]
        global_config = self.data_manager.get_global_config()
        owner_ids = global_config.get('owner_ids', [])
        
        if user_id in owner_ids:
            yield event.plain_result("❌ 该用户已是机器人主人")
            return
        
        owner_ids.append(user_id)
        self.data_manager.set_global_config('owner_ids', owner_ids)
        yield event.plain_result(f"✅ 已添加机器人主人: {user_id}")

    @filter.command("移除主人")
    async def remove_owner(self, event: AstrMessageEvent, *args):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 仅机器人主人可使用此命令")
            return
        
        if len(args) < 1:
            yield event.plain_result("📖 使用方法:\n/移除主人 <QQ>")
            return
        
        user_id = args[0]
        global_config = self.data_manager.get_global_config()
        owner_ids = global_config.get('owner_ids', [])
        
        if user_id not in owner_ids:
            yield event.plain_result("❌ 该用户不是机器人主人")
            return
        
        if len(owner_ids) <= 1:
            yield event.plain_result("❌ 至少需要保留一个机器人主人")
            return
        
        owner_ids.remove(user_id)
        self.data_manager.set_global_config('owner_ids', owner_ids)
        yield event.plain_result(f"✅ 已移除机器人主人: {user_id}")

    @filter.command("查看主人")
    async def list_owners(self, event: AstrMessageEvent):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 仅机器人主人可使用此命令")
            return
        
        global_config = self.data_manager.get_global_config()
        owner_ids = global_config.get('owner_ids', [])
        
        if not owner_ids:
            yield event.plain_result("❌ 还没有设置机器人主人")
            return
        
        result = "👑 机器人主人列表:\n\n"
        for i, owner in enumerate(owner_ids, 1):
            result += f"{i}. {owner}\n"
        
        yield event.plain_result(result)

    @filter.command("查看全局配置")
    async def view_global_config(self, event: AstrMessageEvent):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 仅机器人主人可使用此命令")
            return
        
        global_config = self.data_manager.get_global_config()
        
        result = "⚙️ 全局配置:\n\n"
        for key, value in global_config.items():
            if key != 'command_aliases':  # 不显示命令别名
                result += f"{key}: {value}\n"
        
        yield event.plain_result(result)

    @filter.command("修改全局配置")
    async def set_global_config(self, event: AstrMessageEvent, *args):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 仅机器人主人可使用此命令")
            return
        
        if len(args) < 2:
            yield event.plain_result("📖 使用方法:\n/修改全局配置 <配置名> <值>")
            return
        
        key = args[0]
        value_str = ' '.join(args[1:])
        
        # 尝试转换类型
        try:
            if value_str.lower() == 'true':
                value = True
            elif value_str.lower() == 'false':
                value = False
            elif value_str.isdigit():
                value = int(value_str)
            elif '.' in value_str and value_str.replace('.', '').isdigit():
                value = float(value_str)
            else:
                value = value_str
        except:
            value = value_str
        
        success = self.data_manager.set_global_config(key, value)
        if success:
            yield event.plain_result(f"✅ 已设置全局配置: {key} = {value}")
        else:
            yield event.plain_result(f"❌ 设置失败，配置 {key} 不存在")

    @filter.command("重置全局配置")
    async def reset_global_config(self, event: AstrMessageEvent, *args):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 仅机器人主人可使用此命令")
            return
        
        if len(args) < 1 or args[0] != 'confirm':
            yield event.plain_result("⚠️ 此操作将重置所有全局配置为默认值！\n请使用: /重置全局配置 confirm")
            return
        
        self.data_manager.reset_global_config()
        yield event.plain_result("✅ 已重置全局配置为默认值")

    @filter.command("克隆全局配置")
    async def clone_global_config(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 无权限")
            return
        
        group_id = self.utils._get_group_id(event)
        if not group_id:
            yield event.plain_result("❌ 非群聊环境")
            return
        
        global_config = self.data_manager.get_global_config()
        
        # 克隆全局配置到当前群（排除主人ID列表）
        exclude_keys = ['owner_ids', 'version']
        for key, value in global_config.items():
            if key not in exclude_keys:
                self.data_manager._save_group_config(group_id, key, value)
        
        yield event.plain_result("✅ 已将全局配置克隆到当前群")

    # ===== 群白名单管理（仅主人可用）=====
    
    @filter.command("添加群白名单")
    async def add_group_whitelist(self, event: AstrMessageEvent, *args):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 仅机器人主人可使用此命令")
            return
        
        if len(args) < 1:
            whitelist = self.data_manager.get_group_whitelist()
            yield event.plain_result(f"""📖 使用方法:
/添加群白名单 <群号>
当前白名单群: {', '.join(whitelist) or '无'}""")
            return
        
        group_id = args[0]
        success = self.data_manager.add_to_group_whitelist(group_id)
        if success:
            yield event.plain_result(f"✅ 已将群 {group_id} 添加到白名单")
        else:
            yield event.plain_result(f"❌ 群 {group_id} 已在白名单中")

    @filter.command("移除群白名单")
    async def remove_group_whitelist(self, event: AstrMessageEvent, *args):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 仅机器人主人可使用此命令")
            return
        
        if len(args) < 1:
            whitelist = self.data_manager.get_group_whitelist()
            yield event.plain_result(f"""📖 使用方法:
/移除群白名单 <群号>
当前白名单群: {', '.join(whitelist) or '无'}""")
            return
        
        group_id = args[0]
        success = self.data_manager.remove_from_group_whitelist(group_id)
        if success:
            yield event.plain_result(f"✅ 已将群 {group_id} 从白名单移除")
        else:
            yield event.plain_result(f"❌ 群 {group_id} 不在白名单中")

    @filter.command("查看群白名单")
    async def view_group_whitelist(self, event: AstrMessageEvent):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 仅机器人主人可使用此命令")
            return
        
        whitelist = self.data_manager.get_group_whitelist()
        if not whitelist:
            yield event.plain_result("❌ 群白名单为空")
            return
        
        result = "📋 群白名单列表:\n\n"
        for i, group in enumerate(whitelist, 1):
            result += f"{i}. {group}\n"
        
        yield event.plain_result(result)

    # ===== 过滤群管理（仅主人可用）=====
    
    @filter.command("添加过滤群")
    async def add_filter_group(self, event: AstrMessageEvent, *args):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 仅机器人主人可使用此命令")
            return
        
        if len(args) < 1:
            filtered = self.data_manager.get_filtered_groups()
            yield event.plain_result(f"""📖 使用方法:
/添加过滤群 <群号>
当前过滤群: {', '.join(filtered) or '无'}""")
            return
        
        group_id = args[0]
        success = self.data_manager.add_to_filtered_groups(group_id)
        if success:
            yield event.plain_result(f"✅ 已将群 {group_id} 添加到过滤列表")
        else:
            yield event.plain_result(f"❌ 群 {group_id} 已在过滤列表中")

    @filter.command("移除过滤群")
    async def remove_filter_group(self, event: AstrMessageEvent, *args):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 仅机器人主人可使用此命令")
            return
        
        if len(args) < 1:
            filtered = self.data_manager.get_filtered_groups()
            yield event.plain_result(f"""📖 使用方法:
/移除过滤群 <群号>
当前过滤群: {', '.join(filtered) or '无'}""")
            return
        
        group_id = args[0]
        success = self.data_manager.remove_from_filtered_groups(group_id)
        if success:
            yield event.plain_result(f"✅ 已将群 {group_id} 从过滤列表移除")
        else:
            yield event.plain_result(f"❌ 群 {group_id} 不在过滤列表中")

    @filter.command("查看过滤群")
    async def view_filter_groups(self, event: AstrMessageEvent):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 仅机器人主人可使用此命令")
            return
        
        filtered = self.data_manager.get_filtered_groups()
        if not filtered:
            yield event.plain_result("❌ 过滤群列表为空")
            return
        
        result = "📋 过滤群列表:\n\n"
        for i, group in enumerate(filtered, 1):
            result += f"{i}. {group}\n"
        
        yield event.plain_result(result)
    
    # ===== 授权检查 =====
    
    @filter.command("查看授权")
    async def check_authorization(self, event: AstrMessageEvent, *args):
        """查看当前群的授权状态"""
        group_id = self.utils._get_group_id(event)
        if group_id == 'default':
            yield event.plain_result("❌ 非群聊环境")
            return
        
        # 导入授权模块
        try:
            from ..core import authorization
        except:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from core import authorization
        
        is_authorized = authorization.is_group_authorized(group_id)
        remaining = authorization.get_remaining_time(group_id)
        auth_info = authorization.get_group_auth_info(group_id)
        
        if not is_authorized:
            yield event.plain_result(f"❌ 群 {group_id} 尚未授权或授权已过期")
            return
        
        time_str = authorization.format_time(remaining)
        result = f"✅ 群 {group_id} 授权状态\n\n"
        result += f"授权状态: 有效\n"
        result += f"剩余时间: {time_str}\n"
        if auth_info:
            if 'activated_at' in auth_info:
                activated_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(auth_info['activated_at']))
                result += f"激活时间: {activated_time}\n"
        
        yield event.plain_result(result)
    
    @filter.command("群管菜单")
    async def help_menu(self, event: AstrMessageEvent, *args):
        """群管菜单，检查授权后显示"""
        # 检查授权（主人、白名单群自动通过，否则检查 astrbot_plugin_joker 授权）
        if not self.utils._is_group_authorized(event):
            yield event.plain_result("❌ 本群尚未授权，无法使用群管功能\n\n💡 请联系机器人主人进行 SCUM 授权")
            return
        
        # 继续正常的菜单显示
        if args and args[0]:
            await self._show_category_help(args[0], event)
            return
        
        menu_text = "📋 QQ群管菜单\n\n审核系统|欢迎系统\n撤回系统|踢出系统\n禁言系统|定时消息\n分群设置|统计系统\n黑名单系统|自动回复"
        
        if self.utils._is_owner(event):
            menu_text += "\n主人专属"
        
        menu_text += "\n\n💡 直接输入分类名查看详情，如: 审核系统"
        yield event.plain_result(menu_text)

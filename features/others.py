from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api import logger
from typing import Dict, List, Optional
import time
import random
import os

from ..core.data_manager import DataManager
from ..core.utils import Utils


class OtherFeatures:
    """其他功能模块：撤回、欢迎、回复、自动回复、签到、排行榜、定时消息、统计、设置、修改名片、命令别名"""

    def __init__(self, data_manager: DataManager, utils: Utils, context=None, message_history=None):
        self.data_manager = data_manager
        self.utils = utils
        self.context = context
        self.message_history = message_history or {}
        self.auto_reply_cooldowns = {}

    async def _recall_message(self, message_id: int) -> bool:
        """执行实际的消息撤回操作"""
        try:
            if self.context:
                await self.context.call_api("delete_msg", message_id=message_id)
                return True
            return False
        except Exception as e:
            logger.error(f"撤回消息失败: {e}")
            return False

    def _add_message_to_history(self, event: AstrMessageEvent):
        """将消息添加到历史记录"""
        group_id = self.utils._get_group_id(event)
        if group_id not in self.message_history:
            self.message_history[group_id] = []

        msg_info = {
            'message_id': event.get_message_id(),
            'user_id': self.utils._get_user_id(event),
            'user_name': event.get_sender_name() or 'unknown',
            'content': event.message_str or '',
            'timestamp': time.time()
        }

        self.message_history[group_id].append(msg_info)
        max_history = 100
        if len(self.message_history[group_id]) > max_history:
            self.message_history[group_id] = self.message_history[group_id][-max_history:]

    def _get_recent_messages(self, group_id: str, count: int = 10) -> list:
        """获取最近的消息"""
        if group_id not in self.message_history:
            return []
        return self.message_history[group_id][-count:]

    def _get_user_messages(self, group_id: str, user_id: str, count: int = 100) -> list:
        """获取指定用户的所有消息"""
        if group_id not in self.message_history:
            return []
        return [msg for msg in self.message_history[group_id] if msg['user_id'] == user_id][-count:]

    def _get_messages_in_time_range(self, group_id: str, minutes: int) -> list:
        """获取指定时间范围内的消息"""
        if group_id not in self.message_history:
            return []
        threshold = time.time() - minutes * 60
        return [msg for msg in self.message_history[group_id] if msg['timestamp'] > threshold]

    @filter.command("撤回")
    async def recall_command(self, event: AstrMessageEvent):
        if not self.utils._is_admin(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        config = self.data_manager.get_effective_config(group_id)
        max_recall = config.get('max_recall_count', 10)

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result(f"""🗑️ 撤回命令使用方法:

/撤回 <数量> - 撤回最近的消息(最多{max_recall}条)
/撤回 <消息ID> - 撤回指定消息
/撤回 用户 <QQ> [数量] - 撤回指定用户的消息(默认{max_recall}条)
/撤回 list [页码] - 查看撤回记录""")
            return

        first_arg = args[1].lower()

        if first_arg == 'list':
            recall_logs = self.data_manager._get_group_data(group_id, 'recall_logs', [])
            page = int(args[2]) if len(args) > 2 and args[2].isdigit() else 1
            page_size = 10
            total_pages = max(1, (len(recall_logs) + page_size - 1) // page_size)
            page = max(1, min(page, total_pages))

            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_items = recall_logs[start_idx:end_idx]

            result = f"📋 撤回记录 (第{page}/{total_pages}页):\n"
            for log in page_items:
                result += f"• {log['time']} - {log['operator']} 撤回 {log['target_user']} ({log['reason']})\n"
            yield event.plain_result(result)
            return

        if first_arg == '用户':
            if len(args) < 3:
                yield event.plain_result("❌ 请指定要撤回消息的用户QQ\n使用方法: /撤回 用户 <QQ> [数量]")
                return

            target_qq = args[2]
            if not target_qq.isdigit():
                yield event.plain_result("❌ QQ号必须是数字")
                return

            count = int(args[3]) if len(args) > 3 and args[3].isdigit() else max_recall
            count = min(count, max_recall)

            messages = self._get_user_messages(group_id, target_qq, count)
            success_count = 0
            failed_count = 0

            for msg in messages:
                if await self._recall_message(msg['message_id']):
                    success_count += 1
                else:
                    failed_count += 1

            self.data_manager._save_recall_log(group_id, self.utils._get_user_id(event), target_qq, f'撤回用户消息{count}条')

            if success_count > 0 and failed_count == 0:
                yield event.plain_result(f"✅ 成功撤回用户 {target_qq} 的 {success_count} 条消息")
            elif success_count > 0 and failed_count > 0:
                yield event.plain_result(f"⚠️ 成功撤回 {success_count} 条，失败 {failed_count} 条")
            else:
                yield event.plain_result(f"❌ 未找到用户 {target_qq} 的可撤回消息")
            return

        if first_arg.isdigit():
            count = int(first_arg)
            count = min(count, max_recall)

            messages = self._get_recent_messages(group_id, count)
            success_count = 0
            failed_count = 0

            for msg in messages:
                if await self._recall_message(msg['message_id']):
                    success_count += 1
                else:
                    failed_count += 1

            self.data_manager._save_recall_log(group_id, self.utils._get_user_id(event), 'multi', f'撤回最近{count}条')

            if success_count > 0 and failed_count == 0:
                yield event.plain_result(f"✅ 成功撤回最近 {success_count} 条消息")
            elif success_count > 0 and failed_count > 0:
                yield event.plain_result(f"⚠️ 成功撤回 {success_count} 条消息，失败 {failed_count} 条")
            else:
                yield event.plain_result("❌ 撤回失败，可能消息已过期或没有可撤回的消息")
            return

        try:
            msg_id = int(first_arg)
            if await self._recall_message(msg_id):
                self.data_manager._save_recall_log(group_id, self.utils._get_user_id(event), 'single', f'撤回消息{msg_id}')
                yield event.plain_result(f"✅ 已成功撤回消息 {msg_id}")
            else:
                yield event.plain_result(f"❌ 撤回消息 {msg_id} 失败，可能消息已过期或不存在")
        except ValueError:
            yield event.plain_result(f"❌ 无效的操作\n使用方法:\n/撤回 <数量> - 撤回最近消息\n/撤回 <消息ID> - 撤回指定消息\n/撤回 用户 <QQ> [数量] - 撤回用户消息")

    @filter.command("设置欢迎语")
    async def set_welcome_command(self, event: AstrMessageEvent):
        if not self.utils._is_admin(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)

        args = event.message_str.strip().split()
        if len(args) < 2:
            config = self.data_manager._get_group_data(group_id, 'config', {})
            current = config.get('welcome_messages', [''])[0] if config.get('welcome_messages') else ''
            yield event.plain_result(f"""📢 设置欢迎语命令:

/设置欢迎语 <内容> - 设置欢迎语内容

💡 显示格式: "欢迎 [用户名]进入[群名],[自定义内容]"
当前欢迎语: {"无" if not current else current}

示例: /设置欢迎语 请遵守群规
效果: 欢迎 用户 进入群,请遵守群规""")
            return

        welcome_content = ' '.join(args[1:])
        config = self.data_manager._get_group_data(group_id, 'config', {})
        config['welcome_messages'] = [welcome_content]
        self.data_manager._save_group_data('config')
        yield event.plain_result(f"✅ 已设置欢迎语: {welcome_content}")
        yield event.plain_result(f"💡 效果预览: 欢迎 用户 进入群,{welcome_content}")

    @filter.command("回复")
    async def reply_command(self, event: AstrMessageEvent):
        if not self.utils._is_admin(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        args = event.message_str.strip().split()
        if len(args) < 3:
            yield event.plain_result("""💬 回复命令使用方法:

/回复 <QQ> <消息> - 私聊回复指定用户
/回复 all <消息> confirm - 全员私聊(需确认)
/回复 batch <QQ1,QQ2,...> <消息> - 批量私聊
/回复 group <消息> - 发送群公告

🤖 快捷添加自动回复:
/回复 问 <问题> 答 <答案> - 添加自动回复(触发词为问题)

📋 回复模板:
/回复 template list - 查看回复模板
/回复 template add <名称> <内容> - 添加模板
/回复 template del <名称> - 删除模板
/回复 template use <名称> <QQ> - 使用模板回复""")
            return

        action = args[1].lower()

        if action == '问':
            q_index = args.index('问') if '问' in args else -1
            a_index = args.index('答') if '答' in args else -1
            
            if q_index == -1 or a_index == -1 or a_index <= q_index:
                yield event.plain_result("❌ 使用方法: /回复 问 <问题> 答 <答案>")
                return
            
            question = ' '.join(args[q_index+1:a_index])
            answer = ' '.join(args[a_index+1:])
            
            if not question or not answer:
                yield event.plain_result("❌ 使用方法: /回复 问 <问题> 答 <答案>")
                return
            
            group_id = self.utils._get_group_id(event)
            auto_replies = self.data_manager._get_group_data(group_id, 'auto_replies', {})
            
            auto_replies[question] = {
                'replies': [answer],
                'priority': 1,
                'exact_match': False
            }
            self.data_manager._save_group_data('auto_replies')
            
            yield event.plain_result(f"✅ 已添加自动回复:\n问: {question}\n答: {answer}")
            return

        if action == 'all':
            if len(args) < 4 or args[-1] != 'confirm':
                yield event.plain_result("⚠️ 确定要向所有群成员发送消息吗？\n请使用: /回复 all <消息> confirm")
                return
            message = ' '.join(args[2:-1])
            yield event.plain_result(f"✅ 已向所有成员发送消息: {message}")

        elif action == 'batch':
            if len(args) < 4:
                yield event.plain_result("❌ 使用方法: /回复 batch <QQ1,QQ2,...> <消息>")
                return
            qq_list = args[2].split(',')
            message = ' '.join(args[3:])
            yield event.plain_result(f"✅ 已向 {len(qq_list)} 位成员发送消息")

        elif action == 'group':
            message = ' '.join(args[2:])
            yield event.plain_result(f"📢 群公告:\n{message}")

        elif action == 'template':
            if len(args) < 3:
                yield event.plain_result("""📋 回复模板命令:
/回复 template list - 查看所有模板
/回复 template add <名称> <内容> - 添加模板
/回复 template del <名称> - 删除模板
/回复 template use <名称> <QQ> - 使用模板回复""")
                return

            template_action = args[2].lower()
            templates = self.data_manager._get_group_data(self.utils._get_group_id(event), 'reply_templates', {})

            if template_action == 'list':
                if not templates:
                    yield event.plain_result("📋 暂无回复模板")
                else:
                    result = "📋 回复模板列表:\n"
                    for name, content in templates.items():
                        result += f"• {name}: {content[:20]}...\n"
                    yield event.plain_result(result)

            elif template_action == 'add':
                if len(args) < 5:
                    yield event.plain_result("❌ 使用方法: /回复 template add <名称> <内容>")
                    return
                name = args[3]
                content = ' '.join(args[4:])
                templates[name] = content
                self.data_manager._save_group_data('reply_templates')
                yield event.plain_result(f"✅ 已添加模板: {name}")

            elif template_action == 'del':
                if len(args) < 4:
                    yield event.plain_result("❌ 使用方法: /回复 template del <名称>")
                    return
                name = args[3]
                if name in templates:
                    del templates[name]
                    self.data_manager._save_group_data('reply_templates')
                    yield event.plain_result(f"✅ 已删除模板: {name}")
                else:
                    yield event.plain_result(f"⚠️ 模板 {name} 不存在")

            elif template_action == 'use':
                if len(args) < 5:
                    yield event.plain_result("❌ 使用方法: /回复 template use <名称> <QQ>")
                    return
                name = args[3]
                qq = args[4]
                if name in templates:
                    yield event.plain_result(f"✅ 已使用模板 {name} 回复 {qq}")
                else:
                    yield event.plain_result(f"⚠️ 模板 {name} 不存在")

        else:
            target_qq = args[1]
            message = ' '.join(args[2:])
            yield event.plain_result(f"✅ 已向 {target_qq} 发送私聊消息")

    @filter.command("自动回复")
    async def auto_reply_command(self, event: AstrMessageEvent):
        if not self.utils._is_admin(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        auto_replies = self.data_manager._get_group_data(group_id, 'auto_replies', {})

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("""🤖 自动回复命令使用方法:

📋 基础操作:
/自动回复 on - 开启自动回复
/自动回复 off - 关闭自动回复
/自动回复 list - 查看所有自动回复

➕ 添加/删除:
/自动回复 add <触发词> <回复> - 添加自动回复
/自动回复 add <触发词> <回复1> | <回复2> | ... - 添加随机回复(多个用|分隔)
/自动回复 del <触发词> - 删除自动回复
/自动回复 clear - 清空所有自动回复

⚙️ 高级设置:
/自动回复 cooldown <秒数> - 设置回复冷却时间(默认5秒)
/自动回复 admin_ignore - 设置是否忽略管理员(默认开启)
/自动回复 priority <触发词> <优先级> - 设置触发词优先级(1-10)

💡 特性:
• 支持模糊匹配(消息包含触发词即触发)
• 支持随机回复(用|分隔多个回复)
• 支持优先级(数字越大优先级越高)
• 支持变量替换: {user} {group} {time}""")
            return

        action = args[1].lower()

        if action == 'on':
            config = self.data_manager._get_group_data(group_id, 'config', {})
            config['auto_reply_enabled'] = True
            self.data_manager._save_group_data('config')
            yield event.plain_result("✅ 已开启自动回复")

        elif action == 'off':
            config = self.data_manager._get_group_data(group_id, 'config', {})
            config['auto_reply_enabled'] = False
            self.data_manager._save_group_data('config')
            yield event.plain_result("✅ 已关闭自动回复")

        elif action == 'add':
            if len(args) < 4:
                yield event.plain_result("❌ 使用方法: /自动回复 add <触发词> <回复>")
                return
            
            trigger = args[2]
            reply_content = ' '.join(args[3:])
            
            replies = reply_content.split('|')
            replies = [r.strip() for r in replies if r.strip()]
            
            auto_replies[trigger] = {
                'replies': replies,
                'priority': 1,
                'exact_match': False
            }
            self.data_manager._save_group_data('auto_replies')
            
            if len(replies) > 1:
                yield event.plain_result(f"✅ 已添加随机自动回复:\n触发词: {trigger}\n回复列表: {', '.join(replies)}")
            else:
                yield event.plain_result(f"✅ 已添加自动回复:\n触发词: {trigger}\n回复: {replies[0]}")

        elif action == 'del':
            if len(args) < 3:
                yield event.plain_result("❌ 使用方法: /自动回复 del <触发词>")
                return
            trigger = args[2]
            if trigger in auto_replies:
                del auto_replies[trigger]
                self.data_manager._save_group_data('auto_replies')
                yield event.plain_result(f"✅ 已删除自动回复: {trigger}")
            else:
                yield event.plain_result(f"⚠️ 触发词 {trigger} 不存在")

        elif action == 'clear':
            auto_replies.clear()
            self.data_manager._save_group_data('auto_replies')
            yield event.plain_result("🗑️ 已清空所有自动回复")

        elif action == 'cooldown':
            if len(args) < 3:
                yield event.plain_result("❌ 使用方法: /自动回复 cooldown <秒数>")
                return
            try:
                cooldown = int(args[2])
                config = self.data_manager._get_group_data(group_id, 'config', {})
                config['auto_reply_cooldown'] = cooldown
                self.data_manager._save_group_data('config')
                yield event.plain_result(f"✅ 自动回复冷却时间已设置为: {cooldown}秒")
            except ValueError:
                yield event.plain_result("❌ 请输入有效的数字")

        elif action == 'admin_ignore':
            config = self.data_manager._get_group_data(group_id, 'config', {})
            current = config.get('auto_reply_ignore_admin', True)
            config['auto_reply_ignore_admin'] = not current
            self.data_manager._save_group_data('config')
            status = '开启' if not current else '关闭'
            yield event.plain_result(f"✅ 管理员忽略已{status}")

        elif action == 'priority':
            if len(args) < 4:
                yield event.plain_result("❌ 使用方法: /自动回复 priority <触发词> <优先级>")
                return
            trigger = args[2]
            try:
                priority = int(args[3])
                if priority < 1 or priority > 10:
                    yield event.plain_result("❌ 优先级必须在1-10之间")
                    return
                if trigger in auto_replies:
                    auto_replies[trigger]['priority'] = priority
                    self.data_manager._save_group_data('auto_replies')
                    yield event.plain_result(f"✅ 已设置触发词 '{trigger}' 的优先级为: {priority}")
                else:
                    yield event.plain_result(f"⚠️ 触发词 '{trigger}' 不存在")
            except ValueError:
                yield event.plain_result("❌ 请输入有效的数字")

        elif action == 'list':
            if not auto_replies:
                yield event.plain_result("📋 暂无自动回复")
            else:
                sorted_replies = sorted(auto_replies.items(), key=lambda x: x[1].get('priority', 1), reverse=True)
                result = "📋 自动回复列表:\n"
                for i, (trigger, data) in enumerate(sorted_replies, 1):
                    priority = data.get('priority', 1)
                    replies = data['replies']
                    reply_preview = replies[0] if len(replies) == 1 else f"{len(replies)}个随机回复"
                    result += f"{i}. [优先级{priority}] {trigger} → {reply_preview}\n"
                yield event.plain_result(result)

        else:
            yield event.plain_result("❌ 无效操作，请使用 /自动回复 查看帮助")

    @filter.command("定时消息")
    async def scheduled_message_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        scheduled_messages = self.data_manager._get_group_data(group_id, 'scheduled_messages', [])

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("""⏰ 定时消息命令使用方法:

/定时消息 add <时间> <内容> - 添加定时消息
/定时消息 list - 查看所有定时消息
/定时消息 del <序号> - 删除定时消息

💡 时间格式: HH:MM""")
            return

        action = args[1].lower()

        if action == 'add':
            if len(args) < 4:
                yield event.plain_result("❌ 使用方法: /定时消息 add <时间> <内容>")
                return
            time_str = args[2]
            content = ' '.join(args[3:])
            scheduled_messages.append({
                'time': time_str,
                'content': content,
                'enabled': True
            })
            self.data_manager._save_group_data('scheduled_messages')
            yield event.plain_result(f"✅ 已添加定时消息:\n时间: {time_str}\n内容: {content}")

        elif action == 'list':
            if not scheduled_messages:
                yield event.plain_result("📋 暂无定时消息")
            else:
                result = "📋 定时消息列表:\n"
                for i, msg in enumerate(scheduled_messages, 1):
                    status = "✅" if msg.get('enabled', True) else "❌"
                    result += f"{i}. {status} {msg['time']} - {msg['content']}\n"
                yield event.plain_result(result)

        elif action == 'del':
            if len(args) < 3:
                yield event.plain_result("❌ 使用方法: /定时消息 del <序号>")
                return
            try:
                index = int(args[2]) - 1
                if 0 <= index < len(scheduled_messages):
                    deleted = scheduled_messages.pop(index)
                    self.data_manager._save_group_data('scheduled_messages')
                    yield event.plain_result(f"✅ 已删除定时消息: {deleted['time']} - {deleted['content']}")
                else:
                    yield event.plain_result("❌ 序号无效")
            except ValueError:
                yield event.plain_result("❌ 序号必须是数字")

    @filter.command("名片")
    async def card_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        args = event.message_str.strip().split()

        if len(args) < 2:
            yield event.plain_result("""🏷️ 名片命令使用方法:

/名片 set <QQ> <昵称> - 修改群名片
/名片 get <QQ> - 获取群名片
/名片 reset <QQ> - 重置群名片""")
            return

        action = args[1].lower()

        if action == 'set':
            if len(args) < 4:
                yield event.plain_result("❌ 使用方法: /名片 set <QQ> <昵称>")
                return
            target_qq = args[2]
            nickname = ' '.join(args[3:])
            if self.context:
                try:
                    await self.context.call_api(
                        "set_group_card",
                        group_id=int(group_id),
                        user_id=int(target_qq),
                        card=nickname
                    )
                    yield event.plain_result(f"✅ 已将 {target_qq} 的群名片修改为: {nickname}")
                except Exception as e:
                    logger.error(f"修改名片失败: {e}")
                    yield event.plain_result("❌ 修改名片失败")
            else:
                yield event.plain_result("⚠️ 无法调用API")

        elif action == 'get':
            if len(args) < 3:
                yield event.plain_result("❌ 使用方法: /名片 get <QQ>")
                return
            target_qq = args[2]
            yield event.plain_result(f"📋 {target_qq} 的群名片: 获取中...")

        elif action == 'reset':
            if len(args) < 3:
                yield event.plain_result("❌ 使用方法: /名片 reset <QQ>")
                return
            target_qq = args[2]
            if self.context:
                try:
                    await self.context.call_api(
                        "set_group_card",
                        group_id=int(group_id),
                        user_id=int(target_qq),
                        card=""
                    )
                    yield event.plain_result(f"✅ 已重置 {target_qq} 的群名片")
                except Exception as e:
                    logger.error(f"重置名片失败: {e}")
                    yield event.plain_result("❌ 重置名片失败")
            else:
                yield event.plain_result("⚠️ 无法调用API")

    @filter.command("签到")
    async def sign_command(self, event: AstrMessageEvent):
        group_id = self.utils._get_group_id(event)
        user_id = self.utils._get_user_id(event)
        user_name = event.get_sender_name() or '用户'

        today = time.strftime("%Y-%m-%d")
        user_stats = self.data_manager._get_group_data(group_id, 'user_stats', {})

        if user_id not in user_stats:
            user_stats[user_id] = {
                'sign_count': 0,
                'last_sign_date': '',
                'consecutive_days': 0,
                'points': 0
            }

        stats = user_stats[user_id]

        if stats['last_sign_date'] == today:
            yield event.plain_result(f"😅 {user_name}，您今天已经签到过了")
            return

        stats['sign_count'] += 1
        stats['last_sign_date'] = today

        yesterday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
        if stats['last_sign_date'] == yesterday:
            stats['consecutive_days'] += 1
        else:
            stats['consecutive_days'] = 1

        base_points = 10
        bonus_points = min(stats['consecutive_days'] * 2, 20)
        total_points = base_points + bonus_points
        stats['points'] += total_points

        self.data_manager._save_group_data('user_stats')

        yield event.plain_result(f"✅ {user_name} 签到成功！\n积分 +{total_points}（基础{base_points} + 连续{stats['consecutive_days']}天奖励{bonus_points}）\n累计积分: {stats['points']}\n累计签到: {stats['sign_count']}天")

    @filter.command("排行榜")
    async def leaderboard_command(self, event: AstrMessageEvent):
        group_id = self.utils._get_group_id(event)
        user_stats = self.data_manager._get_group_data(group_id, 'user_stats', {})

        args = event.message_str.strip().split()
        if len(args) > 1 and args[1].lower() == 'sign':
            sorted_users = sorted(user_stats.items(), key=lambda x: x[1].get('sign_count', 0), reverse=True)[:10]
            title = "🏆 签到排行榜"
            key = 'sign_count'
            label = '签到次数'
        else:
            sorted_users = sorted(user_stats.items(), key=lambda x: x[1].get('points', 0), reverse=True)[:10]
            title = "🏆 积分排行榜"
            key = 'points'
            label = '积分'

        if not sorted_users:
            yield event.plain_result("📋 暂无排行数据")
            return

        result = f"{title}:\n"
        for i, (uid, stats) in enumerate(sorted_users, 1):
            result += f"{i}. QQ_{uid} - {label}: {stats.get(key, 0)}\n"
        yield event.plain_result(result)

    @filter.command("我的信息")
    async def user_info_command(self, event: AstrMessageEvent):
        group_id = self.utils._get_group_id(event)
        user_id = self.utils._get_user_id(event)
        user_name = event.get_sender_name() or '用户'

        user_stats = self.data_manager._get_group_data(group_id, 'user_stats', {})
        stats = user_stats.get(user_id, {
            'sign_count': 0,
            'last_sign_date': '',
            'consecutive_days': 0,
            'points': 0
        })

        yield event.plain_result(f"""👤 {user_name} 的信息:
QQ: {user_id}
累计签到: {stats['sign_count']} 天
连续签到: {stats['consecutive_days']} 天
累计积分: {stats['points']}""")

    @filter.command("统计")
    async def stats_command(self, event: AstrMessageEvent):
        group_id = self.utils._get_group_id(event)
        user_stats = self.data_manager._get_group_data(group_id, 'user_stats', {})
        blacklist = self.data_manager._get_group_data(group_id, 'blacklist', {'users': [], 'words': []})
        kick_logs = self.data_manager._get_group_data(group_id, 'kick_logs', [])

        total_users = len(user_stats)
        total_signs = sum(s.get('sign_count', 0) for s in user_stats.values())
        total_points = sum(s.get('points', 0) for s in user_stats.values())
        blacklist_count = len(blacklist['users'])
        kick_count = len(kick_logs)

        yield event.plain_result(f"""📊 群统计信息:

成员数量: {total_users}
累计签到: {total_signs} 次
累计积分: {total_points}
黑名单人数: {blacklist_count}
踢出记录: {kick_count} 条""")

    @filter.command("添加主人")
    async def add_owner_command(self, event: AstrMessageEvent):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 权限不足，仅主人可使用此命令")
            return

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("""👑 添加主人命令使用方法:

/添加主人 <QQ> - 添加机器人主人
/添加主人 list - 查看当前主人列表
/添加主人 remove <QQ> - 移除主人""")
            return

        action = args[1]
        global_config = self.data_manager._get_global_config()
        owner_ids = global_config.get('owner_ids', [])
        if not isinstance(owner_ids, list):
            owner_ids = []

        if action == 'list':
            if not owner_ids:
                yield event.plain_result("📋 当前无主人")
            else:
                yield event.plain_result(f"👑 当前主人列表:\n" + '\n'.join([f"• {uid}" for uid in owner_ids]))
            return

        if action == 'remove':
            if len(args) < 3:
                yield event.plain_result("❌ 使用方法: /添加主人 remove <QQ>")
                return
            qq = args[2]
            if qq in owner_ids:
                owner_ids.remove(qq)
                global_config['owner_ids'] = owner_ids
                self.data_manager._save_global_config()
                yield event.plain_result(f"✅ 已移除主人: {qq}")
            else:
                yield event.plain_result(f"⚠️ {qq} 不是主人")
            return

        qq = action
        if not qq.isdigit():
            yield event.plain_result("❌ QQ号必须是数字")
            return

        if qq in owner_ids:
            yield event.plain_result(f"⚠️ {qq} 已经是主人")
            return

        owner_ids.append(qq)
        global_config['owner_ids'] = owner_ids
        self.data_manager._save_global_config()
        yield event.plain_result(f"✅ 已添加主人: {qq}")

    @filter.command("全局设置")
    async def global_settings_command(self, event: AstrMessageEvent):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 权限不足，仅主人可使用此命令")
            return

        global_config = self.data_manager._get_global_config()

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result(f"""🌐 全局设置 (仅主人):

👑 主人管理:
/添加主人 <QQ> - 添加机器人主人
/添加主人 list - 查看主人列表
/添加主人 remove <QQ> - 移除主人

⚙️ 系统设置:
• enable_group_settings - 是否启用分群配置 (当前: {global_config.get('enable_group_settings', False)})
• enable_global_settings - 是否启用全局设置 (当前: {global_config.get('enable_global_settings', True)})
• spam_threshold - 垃圾消息阈值 (当前: {global_config.get('spam_threshold', 5)})
• spam_time_window - 垃圾消息时间窗口(秒) (当前: {global_config.get('spam_time_window', 60)})
• default_mute_duration - 默认禁言时长(分钟) (当前: {global_config.get('default_mute_duration', 30)})
• default_kick_reason - 默认踢出理由 (当前: {global_config.get('default_kick_reason', '违规发言')})
• max_recall_count - 最大撤回数量 (当前: {global_config.get('max_recall_count', 10)})

使用方法: /全局设置 <选项> <值>
示例: /全局设置 enable_group_settings true""")
            return

        key = args[1]
        value = ' '.join(args[2:])

        if key == 'reset':
            self.data_manager._reset_global_config()
            yield event.plain_result("✅ 全局配置已重置为默认值")
            return

        valid_keys = [
            'enable_group_settings',
            'enable_global_settings',
            'spam_threshold',
            'spam_time_window',
            'default_mute_duration',
            'default_kick_reason',
            'max_recall_count'
        ]

        if key not in valid_keys:
            yield event.plain_result(f"❌ 无效的设置项\n可用选项: {', '.join(valid_keys)}")
            return

        if value.lower() == 'true':
            global_config[key] = True
        elif value.lower() == 'false':
            global_config[key] = False
        elif value.isdigit():
            global_config[key] = int(value)
        else:
            global_config[key] = value

        self.data_manager._save_global_config()
        yield event.plain_result(f"✅ 全局设置已更新:\n{key} = {global_config[key]}")

    @filter.command("设置")
    async def group_settings_command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        config = self.data_manager._get_group_data(group_id, 'config', {})

        args = event.message_str.strip().split()
        if len(args) < 2:
            custom_admins = config.get('custom_admins', [])
            yield event.plain_result(f"""⚙️ 本群设置:

👤 分群管理员管理:
/设置 admin add <QQ> - 添加分群管理员
/设置 admin remove <QQ> - 移除分群管理员
/设置 admin list - 查看分群管理员列表

⚙️ 功能开关:
• welcome_enabled - 是否开启欢迎功能 (当前: {config.get('welcome_enabled', True)})
• auto_approve - 是否自动审核 (当前: {config.get('auto_approve', False)})
• anti_spam_enabled - 是否开启反垃圾 (当前: {config.get('anti_spam_enabled', True)})
• sign_enabled - 是否开启签到 (当前: {config.get('sign_enabled', True)})
• auto_reply_enabled - 是否开启自动回复 (当前: {config.get('auto_reply_enabled', False)})

💡 当前分群管理员: {', '.join(custom_admins) if custom_admins else '无'}
💡 主人不受任何权限限制""")
            return

        action = args[1].lower()

        if action == 'admin':
            if not self.utils._is_group_admin(event) and not self.utils._is_owner(event):
                yield event.plain_result("❌ 权限不足，仅群主/管理员可管理分群管理员")
                return

            if len(args) < 3:
                yield event.plain_result("""👤 分群管理员管理命令:

/设置 admin add <QQ> - 添加分群管理员
/设置 admin remove <QQ> - 移除分群管理员
/设置 admin list - 查看分群管理员列表""")
                return

            admin_action = args[2].lower()
            custom_admins = config.get('custom_admins', [])
            if not isinstance(custom_admins, list):
                custom_admins = []

            if admin_action == 'list':
                if not custom_admins:
                    yield event.plain_result("📋 本群暂无分群管理员")
                else:
                    yield event.plain_result(f"👤 本群分群管理员:\n" + '\n'.join([f"• {uid}" for uid in custom_admins]))
                return

            if len(args) < 4:
                yield event.plain_result("❌ 使用方法: /设置 admin add/remove <QQ>")
                return

            qq = args[3]
            if not qq.isdigit():
                yield event.plain_result("❌ QQ号必须是数字")
                return

            if admin_action == 'add':
                if qq in custom_admins:
                    yield event.plain_result(f"⚠️ {qq} 已经是分群管理员")
                else:
                    custom_admins.append(qq)
                    config['custom_admins'] = custom_admins
                    self.data_manager._save_group_data('config')
                    yield event.plain_result(f"✅ 已添加分群管理员: {qq}")
                return

            if admin_action == 'remove':
                if qq in custom_admins:
                    custom_admins.remove(qq)
                    config['custom_admins'] = custom_admins
                    self.data_manager._save_group_data('config')
                    yield event.plain_result(f"✅ 已移除分群管理员: {qq}")
                else:
                    yield event.plain_result(f"⚠️ {qq} 不是分群管理员")
                return

            yield event.plain_result("❌ 无效操作，可用: add/remove/list")
            return

        key = action
        value = ' '.join(args[2:])

        valid_keys = [
            'welcome_enabled',
            'auto_approve',
            'anti_spam_enabled',
            'sign_enabled',
            'auto_reply_enabled',
            'allow_self_recall',
            'allow_self_reply'
        ]

        if key not in valid_keys:
            yield event.plain_result(f"❌ 无效的设置项\n可用选项: {', '.join(valid_keys)}")
            return

        if value.lower() == 'true':
            config[key] = True
        elif value.lower() == 'false':
            config[key] = False
        else:
            config[key] = value

        self.data_manager._save_group_data('config')
        yield event.plain_result(f"✅ 本群设置已更新:\n{key} = {config[key]}")

    @filter.command("克隆配置")
    async def clone_config_command(self, event: AstrMessageEvent):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 权限不足，仅主人可使用此命令")
            return

        args = event.message_str.strip().split()
        if len(args) < 3:
            yield event.plain_result("""🔄 克隆配置命令使用方法:

/克隆配置 global <目标群ID> - 将全局配置克隆到指定群
/克隆配置 <源群ID> <目标群ID> - 将源群配置克隆到目标群""")
            return

        source_group_id = args[1]
        target_group_id = args[2]

        if source_group_id == 'global':
            global_config = self.data_manager._get_global_config()
            config_data = {
                'welcome_messages': global_config.get('welcome_messages', ['']),
                'welcome_enabled': global_config.get('welcome_enabled', True),
                'auto_reply_enabled': global_config.get('auto_reply_enabled', False),
                'auto_replies': {}
            }
            self.data_manager._set_group_data('config', config_data, target_group_id)
            yield event.plain_result(f"✅ 已将全局配置克隆到群 {target_group_id}")
        else:
            if not source_group_id.isdigit() or not target_group_id.isdigit():
                yield event.plain_result("❌ 群ID必须是数字")
                return

            source_config = self.data_manager._get_group_data(source_group_id, 'config', {})
            self.data_manager._set_group_data('config', source_config, target_group_id)
            yield event.plain_result(f"✅ 已将群 {source_group_id} 的配置克隆到群 {target_group_id}")

    @filter.command("命令别名")
    async def alias_command(self, event: AstrMessageEvent):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 权限不足，仅主人可使用此命令")
            return

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("""🔧 命令别名命令使用方法:

/命令别名 list - 查看所有命令别名
/命令别名 add <主命令> <别名> - 添加命令别名
/命令别名 del <主命令> <别名> - 删除命令别名
/命令别名 info <主命令> - 查看指定命令的别名""")
            return

        action = args[1].lower()

        if action == 'list':
            aliases = self.data_manager._get_global_config().get('command_aliases', {})
            if not aliases:
                yield event.plain_result("📋 暂无命令别名")
            else:
                result = "📋 命令别名列表:\n"
                for command, alias_list in aliases.items():
                    result += f"• {command}: {', '.join(alias_list)}\n"
                yield event.plain_result(result)

        elif action == 'add':
            if len(args) < 4:
                yield event.plain_result("❌ 使用方法: /命令别名 add <主命令> <别名>")
                return
            command = args[2]
            alias = args[3]
            aliases = self.data_manager._get_global_config().get('command_aliases', {})
            if command not in aliases:
                aliases[command] = []
            if alias not in aliases[command]:
                aliases[command].append(alias)
                self.data_manager._save_global_config()
                yield event.plain_result(f"✅ 已为命令 '{command}' 添加别名: {alias}")
            else:
                yield event.plain_result(f"⚠️ 别名 '{alias}' 已存在")

        elif action == 'del':
            if len(args) < 4:
                yield event.plain_result("❌ 使用方法: /命令别名 del <主命令> <别名>")
                return
            command = args[2]
            alias = args[3]
            aliases = self.data_manager._get_global_config().get('command_aliases', {})
            if command in aliases and alias in aliases[command]:
                aliases[command].remove(alias)
                self.data_manager._save_global_config()
                yield event.plain_result(f"✅ 已从命令 '{command}' 移除别名: {alias}")
            else:
                yield event.plain_result(f"⚠️ 未找到别名 '{alias}'")

        elif action == 'info':
            if len(args) < 3:
                yield event.plain_result("❌ 使用方法: /命令别名 info <主命令>")
                return
            command = args[2]
            aliases = self.data_manager._get_global_config().get('command_aliases', {})
            if command in aliases:
                yield event.plain_result(f"📋 命令 '{command}' 的别名: {', '.join(aliases[command])}")
            else:
                yield event.plain_result(f"⚠️ 命令 '{command}' 暂无别名")

    @filter.command("群管菜单")
    async def help_command(self, event: AstrMessageEvent):
        args = event.message_str.strip().split()
        
        if len(args) >= 2:
            category = ' '.join(args[1:])
            await self._show_category_help(category, event)
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
        """显示指定分类的详细帮助"""
        help_texts = {
            '审核系统': """📝 审核系统

/入群审核                    - 查看审核状态
/入群审核 同意 <QQ> [理由]   - 通过申请
/入群审核 拒绝 <QQ> [理由]   - 拒绝申请
/入群审核 math               - 数学验证模式
/入群审核 id                 - 随机数字验证模式
/审核自定义次数 <次数>        - 设置验证次数上限""",
            
            '禁言系统': """🔇 禁言系统

/禁言 <QQ> [时长] [理由]      - 禁言用户
/禁言 list [页码]            - 查看禁言列表
/禁言 info <QQ>              - 查看禁言详情
/解禁 <QQ>                   - 解除禁言
/解禁 all                    - 解除所有禁言
/全体禁言 on/off             - 全体禁言开关
/永久禁言 <QQ> [理由]        - 永久禁言用户""",
            
            '黑名单系统': """🚫 黑名单系统

/黑名单 add <QQ> [理由] [时长] - 添加黑名单
/黑名单 remove <QQ>           - 移除黑名单
/黑名单 info <QQ>             - 查看详情
/黑名单 list [页码]           - 分页查看
/黑名单 search <关键词>       - 搜索记录
/黑名单 addword <关键词>      - 添加关键词
/黑名单 removeword <关键词>   - 移除关键词
/黑名单 listword              - 查看关键词列表
/拉黑 <QQ> [理由]             - 快速拉黑""",
            
            '踢出系统': """👢 踢出系统

/踢出 <QQ> [理由]             - 踢出用户
/踢出 black <QQ> [理由]       - 踢出并拉黑
/踢出 连带 <QQ> [理由]        - 连带踢出
/踢出 list [页码]             - 查看踢出记录
/踢出 search <关键词>         - 搜索踢出记录
/踢出 1h/1d/7d/perm <QQ>     - 快捷封禁""",
            
            '撤回系统': """🗑️ 撤回系统

/撤回 <消息ID>                - 撤回单条消息
/撤回 user <QQ> [数量]        - 撤回用户消息
/撤回 <数量>                  - 撤回最近消息
/撤回 list [页码]             - 查看撤回记录""",
            
            '欢迎系统': """📢 欢迎系统

/欢迎 on/off                  - 开关欢迎功能
/欢迎 set <内容>              - 设置欢迎语
/欢迎 test <昵称>             - 测试欢迎效果
/设置欢迎语 <内容>            - 设置欢迎语""",
            
            '定时消息': """⏰ 定时消息

/定时消息 add <时间> <内容>    - 添加定时消息
/定时消息 list                - 查看定时列表
/定时消息 del <序号>          - 删除定时消息""",
            
            '分群设置': """⚙️ 分群设置

/设置                         - 查看本群设置
/设置 <选项> <值>             - 修改本群设置
/设置 admin add <QQ>          - 添加分群管理员
/设置 admin remove <QQ>       - 移除分群管理员
/设置 admin list              - 查看分群管理员""",
            
            '统计系统': """📊 统计系统

/统计                         - 统计概览
/统计 detail                  - 详细统计
/统计 invite <QQ>             - 邀请统计
/统计 top                     - 邀请排行榜
/排行榜 [points|sign]         - 查看排行""",
        }
        
        if category in help_texts:
            yield event.plain_result(help_texts[category])
        else:
            yield event.plain_result(f"""❌ 未知分类: {category}

可用分类: 审核系统 | 欢迎系统 | 撤回系统 | 踢出系统 | 禁言系统 | 定时消息 | 分群设置 | 统计系统 | 黑名单系统""")

    @filter.event_message_create_v2
    async def message_listener(self, event: AstrMessageEvent):
        """消息监听器 - 检测黑名单用户发言、自动回复、记录消息历史"""
        self._add_message_to_history(event)

        user_id = self.utils._get_user_id(event)
        group_id = self.utils._get_group_id(event)

        config = self.data_manager.get_effective_config(group_id)
        
        if self.utils._is_admin(event):
            await self._handle_auto_reply(event, group_id, user_id, config)
            return

        blacklist = self.data_manager._get_group_data(group_id, 'blacklist', {'users': [], 'words': []})
        kick_logs = self.data_manager._get_group_data(group_id, 'kick_logs', [])

        if config.get('anti_spam_enabled', False):
            for user in blacklist['users']:
                if user['qq'] == user_id:
                    await self._recall_message(event.get_message_id())
                    self.data_manager._save_recall_log(group_id, 'system', user_id, 'blacklist_auto_recall')

                    kick_logs.insert(0, {
                        'qq': user_id,
                        'action': 'auto_kick_blacklist',
                        'reason': f"黑名单用户发言，自动踢出",
                        'time': time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    if len(kick_logs) > 100:
                        kick_logs = kick_logs[:100]
                    self.data_manager._save_group_data('kick_logs')

                    yield event.plain_result(f"🚫 检测到黑名单用户 {user_id} 发言，已自动踢出并撤回消息")
                    return

            message_text = event.message_str or ""
            for word_entry in blacklist['words']:
                word = word_entry.get('word', word_entry) if isinstance(word_entry, dict) else word_entry
                if word in message_text:
                    await self._recall_message(event.get_message_id())
                    self.data_manager._save_recall_log(group_id, 'system', user_id, 'keyword_auto_recall')
                    yield event.plain_result(f"⚠️ 消息包含敏感内容，已自动撤回")
                    return

        await self._handle_auto_reply(event, group_id, user_id, config)

    async def _handle_auto_reply(self, event: AstrMessageEvent, group_id: str, user_id: str, config: Dict):
        """处理自动回复逻辑"""
        if not config.get('auto_reply_enabled', False):
            return

        ignore_admin = config.get('auto_reply_ignore_admin', True)
        if ignore_admin and self.utils._is_admin(event):
            return

        cooldown = config.get('auto_reply_cooldown', 5)
        now = time.time()
        
        if group_id not in self.auto_reply_cooldowns:
            self.auto_reply_cooldowns[group_id] = {}
        
        last_reply_time = self.auto_reply_cooldowns[group_id].get(user_id, 0)
        if now - last_reply_time < cooldown:
            return

        message_text = event.message_str or ""
        auto_replies = self.data_manager._get_group_data(group_id, 'auto_replies', {})
        
        if not auto_replies:
            return

        sorted_replies = sorted(auto_replies.items(), key=lambda x: x[1].get('priority', 1), reverse=True)
        
        for trigger, data in sorted_replies:
            replies = data['replies']
            exact_match = data.get('exact_match', False)
            
            if exact_match:
                if message_text == trigger:
                    reply = random.choice(replies)
                    reply = self._replace_variables(reply, event, group_id)
                    yield event.plain_result(reply)
                    self.auto_reply_cooldowns[group_id][user_id] = now
                    return
            else:
                if trigger in message_text:
                    reply = random.choice(replies)
                    reply = self._replace_variables(reply, event, group_id)
                    yield event.plain_result(reply)
                    self.auto_reply_cooldowns[group_id][user_id] = now
                    return

    def _replace_variables(self, text: str, event: AstrMessageEvent, group_id: str) -> str:
        """替换消息中的变量"""
        user_name = event.get_sender_name() or '用户'
        group_name = getattr(event, 'group_name', '本群')
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        text = text.replace('{user}', user_name)
        text = text.replace('{group}', group_name)
        text = text.replace('{time}', current_time)
        
        return text
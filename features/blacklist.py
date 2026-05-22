from astrbot.api.event import AstrMessageEvent, filter
from typing import Dict, List, Optional
import time
import json
import os

from ..core.data_manager import DataManager
from ..core.utils import Utils
from ..core.invitation_manager import InvitationManager


class BlacklistFeature:
    """黑名单管理功能"""

    def __init__(self, data_manager: DataManager, utils: Utils, invitation_manager: InvitationManager, context=None):
        self.data_manager = data_manager
        self.utils = utils
        self.invitation_manager = invitation_manager
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

    @filter.command("黑名单")
    async def command(self, event: AstrMessageEvent):
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        blacklist = self.data_manager._get_group_data(group_id, 'blacklist', {'users': [], 'words': []})

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("""📋 群黑名单命令使用方法:

👤 用户黑名单:
/黑名单 add <QQ> [理由] [时长] - 添加用户 (时长: 30m, 2h, 7d, 不填为永久)
/黑名单 remove <QQ> - 移除用户
/黑名单 info <QQ> - 查看用户详情
/黑名单 list [页码] - 查看用户列表(分页)
/黑名单 search <关键词> - 搜索黑名单
/黑名单 clear confirm - 清空所有用户

🔤 关键词黑名单:
/黑名单 addword <关键词> [理由] - 添加关键词
/黑名单 removeword <关键词> - 移除关键词
/黑名单 listword - 查看关键词

💾 数据管理:
/黑名单 export - 导出本群黑名单
/黑名单 import - 导入本群黑名单""")
            return

        action = args[1].lower()

        if action == 'add':
            if len(args) < 3:
                yield event.plain_result("❌ 请指定要加入黑名单的QQ")
                return
            user_id = args[2]
            reason = args[3] if len(args) > 3 else "违规发言"
            duration = args[4] if len(args) > 4 else None

            expire_time = None
            if duration:
                try:
                    if duration.endswith('m'):
                        expire_time = time.time() + int(duration[:-1]) * 60
                    elif duration.endswith('h'):
                        expire_time = time.time() + int(duration[:-1]) * 3600
                    elif duration.endswith('d'):
                        expire_time = time.time() + int(duration[:-1]) * 86400
                    else:
                        yield event.plain_result("❌ 时长格式错误，请使用 30m, 2h, 7d")
                        return
                except ValueError:
                    yield event.plain_result("❌ 时长数字格式错误")
                    return

            existing = next((u for u in blacklist['users'] if u['qq'] == user_id), None)
            if existing:
                expire_str = "永久封禁" if existing['permanent'] else f"将于 {existing['expire_time']} 到期"
                yield event.plain_result(f"⚠️ {user_id} 已在本群黑名单中\n原因: {existing['reason']}\n类型: {expire_str}")
                return

            user_entry = {
                'qq': user_id,
                'reason': reason,
                'time': time.strftime("%Y-%m-%d %H:%M:%S"),
                'added_by': event.get_sender_name() or 'admin',
                'expire_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire_time)) if expire_time else None,
                'permanent': expire_time is None
            }
            blacklist['users'].append(user_entry)
            self.data_manager._save_group_data('blacklist')

            expire_str = f"将于 {user_entry['expire_time']} 到期" if expire_time else "永久封禁"
            yield event.plain_result(f"✅ 已将 {user_id} 加入本群黑名单\n原因: {reason}\n类型: {expire_str}")

        elif action == 'remove':
            if len(args) < 3:
                yield event.plain_result("❌ 请指定要移出黑名单的QQ")
                return
            user_id = args[2]
            original_count = len(blacklist['users'])
            blacklist['users'] = [u for u in blacklist['users'] if u['qq'] != user_id]

            if len(blacklist['users']) < original_count:
                self.data_manager._save_group_data('blacklist')
                yield event.plain_result(f"✅ 已将 {user_id} 移出本群黑名单")
            else:
                yield event.plain_result(f"⚠️ {user_id} 不在本群黑名单中")

        elif action == 'info':
            if len(args) < 3:
                yield event.plain_result("❌ 请指定要查看的QQ")
                return
            user_id = args[2]
            user_entry = next((u for u in blacklist['users'] if u['qq'] == user_id), None)

            if user_entry:
                expire_str = "永久封禁" if user_entry['permanent'] else f"将于 {user_entry['expire_time']} 到期"
                inviter = self.invitation_manager._get_inviter_of(group_id, user_id)
                info = f"""📋 本群黑名单用户详情:
QQ: {user_entry['qq']}
原因: {user_entry['reason']}
添加时间: {user_entry['time']}
添加人: {user_entry['added_by']}
类型: {expire_str}"""
                if inviter:
                    info += f"\n邀请人: {inviter}"
                yield event.plain_result(info)
            else:
                yield event.plain_result(f"⚠️ {user_id} 不在本群黑名单中")

        elif action == 'list':
            if not blacklist['users']:
                yield event.plain_result("📋 本群黑名单用户: 无")
                return

            page = int(args[2]) if len(args) > 2 and args[2].isdigit() else 1
            page_size = 10
            total_pages = max(1, (len(blacklist['users']) + page_size - 1) // page_size)
            page = max(1, min(page, total_pages))

            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_users = blacklist['users'][start_idx:end_idx]

            user_lines = []
            for i, u in enumerate(page_users, start=start_idx + 1):
                expire_str = "永久" if u['permanent'] else (u['expire_time'][:10] if u['expire_time'] else "未知")
                user_lines.append(f"{i}. {u['qq']} | {u['reason'][:15]}... | {expire_str}")

            result = f"📋 本群黑名单用户 (第{page}/{total_pages}页, 共{len(blacklist['users'])}人):\n"
            result += '\n'.join(user_lines) if user_lines else "无"
            yield event.plain_result(result)

        elif action == 'search':
            if len(args) < 3:
                yield event.plain_result("❌ 请指定搜索关键词")
                return
            keyword = ' '.join(args[2:]).lower()

            user_results = []
            for u in blacklist['users']:
                if keyword in u['qq'].lower() or keyword in u['reason'].lower():
                    expire_str = "永久" if u['permanent'] else (u['expire_time'][:10] if u['expire_time'] else "未知")
                    user_results.append(f"用户: {u['qq']} | 原因: {u['reason'][:20]}... | {expire_str}")

            word_results = []
            for w in blacklist['words']:
                word_text = w.get('word', w) if isinstance(w, dict) else w
                reason = w.get('reason', '无') if isinstance(w, dict) else '无'
                if keyword in word_text.lower() or keyword in reason.lower():
                    word_results.append(f"关键词: {word_text} | 原因: {reason}")

            if user_results or word_results:
                result = "🔍 本群搜索结果:\n"
                if user_results:
                    result += f"\n👤 用户 ({len(user_results)}条):\n" + '\n'.join(user_results[:10])
                if word_results:
                    result += f"\n🔤 关键词 ({len(word_results)}条):\n" + '\n'.join(word_results[:10])
                yield event.plain_result(result)
            else:
                yield event.plain_result("⚠️ 未找到匹配的结果")

        elif action == 'addword':
            if len(args) < 3:
                yield event.plain_result("❌ 请指定要添加的关键词")
                return

            if len(args) > 3 and args[-1] not in ['m', 'h', 'd']:
                word = ' '.join(args[2:-1])
                reason = args[-1]
            else:
                word = ' '.join(args[2:])
                reason = "垃圾广告"

            existing = next((w for w in blacklist['words'] if (w.get('word', w) if isinstance(w, dict) else w) == word), None)
            if existing:
                yield event.plain_result(f"⚠️ 关键词 '{word}' 已存在")
                return

            word_entry = {
                'word': word,
                'reason': reason,
                'time': time.strftime("%Y-%m-%d %H:%M:%S"),
                'added_by': event.get_sender_name() or 'admin'
            }
            blacklist['words'].append(word_entry)
            self.data_manager._save_group_data('blacklist')
            yield event.plain_result(f"✅ 已添加本群关键词: {word}\n原因: {reason}")

        elif action == 'removeword':
            if len(args) < 3:
                yield event.plain_result("❌ 请指定要移除的关键词")
                return
            word = ' '.join(args[2:])
            original_count = len(blacklist['words'])
            blacklist['words'] = [w for w in blacklist['words'] if (w.get('word', w) if isinstance(w, dict) else w) != word]

            if len(blacklist['words']) < original_count:
                self.data_manager._save_group_data('blacklist')
                yield event.plain_result(f"✅ 已移除本群关键词: {word}")
            else:
                yield event.plain_result(f"⚠️ 关键词 '{word}' 不存在")

        elif action == 'listword':
            if not blacklist['words']:
                yield event.plain_result("📋 本群黑名单关键词: 无")
                return

            words = []
            for i, w in enumerate(blacklist['words'], 1):
                word_text = w.get('word', w) if isinstance(w, dict) else w
                reason = w.get('reason', '无') if isinstance(w, dict) else '无'
                words.append(f"{i}. {word_text} | {reason}")

            yield event.plain_result(f"📋 本群黑名单关键词 ({len(blacklist['words'])}个):\n" + '\n'.join(words))

        elif action == 'clear':
            if len(args) < 3 or args[2] != 'confirm':
                yield event.plain_result("⚠️ 确定要清空本群所有黑名单吗？\n此操作不可恢复！\n请使用: /黑名单 clear confirm")
                return

            blacklist['users'] = []
            blacklist['words'] = []
            self.data_manager._save_group_data('blacklist')
            yield event.plain_result("🗑️ 已清空本群所有黑名单数据")

        elif action == 'export':
            if not blacklist['users'] and not blacklist['words']:
                yield event.plain_result("⚠️ 本群黑名单为空，无需导出")
                return

            export_data = json.dumps(blacklist, ensure_ascii=False, indent=2)
            export_path = os.path.join(self.data_manager.plugin_dir, f'blacklist_{group_id}_export.json')

            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(export_data)

            yield event.plain_result(f"✅ 本群黑名单已导出!\n路径: blacklist_{group_id}_export.json\n用户: {len(blacklist['users'])}人\n关键词: {len(blacklist['words'])}个")

        elif action == 'import':
            import_path = os.path.join(self.data_manager.plugin_dir, f'blacklist_{group_id}_import.json')

            if not os.path.exists(import_path):
                import_path = os.path.join(self.data_manager.plugin_dir, 'blacklist_import.json')
                if not os.path.exists(import_path):
                    yield event.plain_result(f"⚠️ 未找到导入文件: blacklist_{group_id}_import.json 或 blacklist_import.json\n请先将文件放入插件目录")
                    return

            try:
                with open(import_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)

                if 'users' in import_data:
                    blacklist['users'] = import_data['users']
                if 'words' in import_data:
                    blacklist['words'] = import_data['words']

                self.data_manager._save_group_data('blacklist')
                yield event.plain_result(f"✅ 成功导入本群黑名单!\n用户: {len(blacklist['users'])}人\n关键词: {len(blacklist['words'])}个")
            except Exception as e:
                yield event.plain_result(f"❌ 导入失败: {str(e)}")

        else:
            yield event.plain_result("❌ 无效操作，请查看帮助")

    @filter.command("拉黑")
    async def simple_blacklist_command(self, event: AstrMessageEvent):
        """简单的拉黑指令"""
        if not self.utils._has_group_permission(event):
            yield event.plain_result("❌ 权限不足，仅管理员可使用此命令")
            return

        group_id = self.utils._get_group_id(event)
        config = self.data_manager._get_group_data(group_id, 'config', {})
        blacklist = self.data_manager._get_group_data(group_id, 'blacklist', {'users': [], 'words': []})
        kick_logs = self.data_manager._get_group_data(group_id, 'kick_logs', [])

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("📋 使用方法:\n/拉黑 <QQ> - 拉黑用户(默认理由)\n/拉黑 <QQ> <理由> - 拉黑用户并指定理由")
            return

        user_id = args[1]
        reason = ' '.join(args[2:]) if len(args) > 2 else config.get('default_kick_reason', '违规发言')

        existing = next((u for u in blacklist['users'] if u['qq'] == user_id), None)
        if not existing:
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

        # 保存踢出日志
        kick_logs.insert(0, {
            'qq': user_id,
            'action': 'perm_kick',
            'reason': reason,
            'time': time.strftime("%Y-%m-%d %H:%M:%S")
        })
        if len(kick_logs) > 100:
            kick_logs = kick_logs[:100]
        self.data_manager._save_group_data('kick_logs')

        # 执行实际踢出
        success = await self._kick_member(int(group_id), int(user_id))
        
        # 撤回该用户的所有消息并踢出
        self.data_manager._save_recall_log(group_id, 'admin', user_id, 'recall_all_user')
        
        if success:
            yield event.plain_result(f"🚫 已将 {user_id} 拉黑并踢出群聊，理由: {reason}\n已撤回该用户发送的所有消息")
        else:
            yield event.plain_result(f"⚠️ 已将 {user_id} 加入黑名单，但踢出API调用失败")
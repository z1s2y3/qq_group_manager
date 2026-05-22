from astrbot.api.event import AstrMessageEvent, filter
from typing import Dict, List, Optional
import time
import random
import hashlib


class ApprovalFeature:
    """审核系统功能"""

    def __init__(self, data_manager, utils, invitation_manager, context=None):
        self.data_manager = data_manager
        self.utils = utils
        self.invitation_manager = invitation_manager
        self.context = context
        self.pending_verification = {}
        self.verification_attempts = {}

    @filter.command("入群审核")
    async def command(self, event: AstrMessageEvent):
        group_id = self.utils._get_group_id(event)
        verification = self.data_manager._get_group_data(group_id, 'verification', {})

        args = event.message_str.strip().split()
        if len(args) < 2:
            mode_name = self._get_mode_name(verification.get('mode', 'math'))
            config = self.data_manager._get_group_data(group_id, 'config', {})
            max_attempts = verification.get('max_attempts', config.get('approval_max_attempts', 3))
            kick_on_fail = config.get('approval_kick_on_fail', False)
            yield event.plain_result(f"""📋 入群审核系统:

👤 成员验证:
直接发送验证码或数学题答案即可完成验证
💡 管理员/主人邀请的成员可免验证直接入群

🔧 管理员操作:
/入群审核 同意 <QQ> [理由]   - 通过申请
/入群审核 拒绝 <QQ> [理由]   - 拒绝申请
/入群审核 设置               - 设置审核模式
/入群审核 math               - 数学验证模式
/入群审核 id                 - 随机数字验证模式

👑 主人专属:
/审核自定义次数 <次数>        - 设置验证次数上限(默认3次)

当前审核模式: {mode_name} | 验证次数上限: {max_attempts}次 | 验证失败踢出: {'开启' if kick_on_fail else '关闭'}""")
            return

        action = args[1]

        if action == '同意':
            if not self.utils._is_admin(event):
                yield event.plain_result("❌ 权限不足")
                return
            if len(args) < 3:
                yield event.plain_result("❌ 使用方法: /入群审核 同意 <QQ> [理由]")
                return
            user_id = args[2]
            reason = ' '.join(args[3:]) if len(args) > 3 else '审核通过'
            await self._approve_user(group_id, user_id, reason, event)

        elif action == '拒绝':
            if not self.utils._is_admin(event):
                yield event.plain_result("❌ 权限不足")
                return
            if len(args) < 3:
                yield event.plain_result("❌ 使用方法: /入群审核 拒绝 <QQ> [理由]")
                return
            user_id = args[2]
            reason = ' '.join(args[3:]) if len(args) > 3 else '审核未通过'
            await self._reject_user(group_id, user_id, reason)

        elif action == '设置':
            if not self.utils._is_admin(event):
                yield event.plain_result("❌ 权限不足")
                return

            await self._show_settings(group_id, verification)

        elif action.lower() in ['math', 'id']:
            if not self.utils._is_admin(event):
                yield event.plain_result("❌ 权限不足")
                return

            await self._set_mode(group_id, verification, action.lower())

        else:
            await self._handle_member_verification(group_id, event, args[1])

    @filter.command("审核自定义次数")
    async def set_attempts_command(self, event: AstrMessageEvent):
        if not self.utils._is_owner(event):
            yield event.plain_result("❌ 权限不足，仅主人可使用此命令")
            return

        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("📋 使用方法: /审核自定义次数 <次数>\n例如: /审核自定义次数 5")
            return

        try:
            attempts = int(args[1])
            if attempts < 1 or attempts > 10:
                yield event.plain_result("❌ 次数必须在 1-10 之间")
                return

            group_id = self.utils._get_group_id(event)
            verification = self.data_manager._get_group_data(group_id, 'verification', {})
            verification['max_attempts'] = attempts
            self.data_manager._save_group_data('verification')
            yield event.plain_result(f"✅ 验证次数上限已设置为: {attempts}次")
        except ValueError:
            yield event.plain_result("❌ 次数必须是数字")



    @filter.event_message_create_v2
    async def message_listener(self, event: AstrMessageEvent):
        """消息监听器 - 检测新成员并发送验证请求"""
        group_id = self.utils._get_group_id(event)
        user_id = self.utils._get_user_id(event)
        verification = self.data_manager._get_group_data(group_id, 'verification', {})

        mode = verification.get('mode', 'math')
        if mode not in ['math', 'id']:
            return

        if user_id not in self.pending_verification.get(group_id, {}):
            inviter = self.invitation_manager._get_inviter_of(group_id, user_id)
            
            if inviter and self._is_admin_or_owner(group_id, inviter):
                user_name = getattr(event, 'user_name', f"QQ_{user_id}")
                group_name = getattr(event, 'group_name', "本群")
                yield event.plain_result(f"🎉 欢迎 {user_name} 加入{group_name}！（由管理员/主人邀请，免验证）")
                welcome_msg = self._generate_welcome_message(group_id, user_name, user_id, group_name, 150)
                if welcome_msg:
                    yield event.plain_result(f"🎊 {welcome_msg}")
                return
            
            await self._generate_new_verification(group_id, event)

    def _is_admin_or_owner(self, group_id: str, user_id: str) -> bool:
        """检查用户是否为管理员或主人"""
        if self.utils._is_owner_by_id(user_id):
            return True
        
        if self.context:
            try:
                member_info = self.context.call_api(
                    "get_group_member_info",
                    group_id=int(group_id),
                    user_id=int(user_id)
                )
                if member_info and member_info.get('role') in ['admin', 'owner']:
                    return True
            except Exception:
                pass
        
        return False

    async def _generate_new_verification(self, group_id: str, event: AstrMessageEvent):
        """生成新的验证题目"""
        user_id = self.utils._get_user_id(event)
        verification = self.data_manager._get_group_data(group_id, 'verification', {})
        mode = verification.get('mode', 'math')

        if group_id not in self.pending_verification:
            self.pending_verification[group_id] = {}
        if group_id not in self.verification_attempts:
            self.verification_attempts[group_id] = {}

        if mode == 'math':
            num1 = random.randint(1, 100)
            num2 = random.randint(1, 100)
            operator = random.choice(['+', '-', '*', '/'])

            if operator == '+':
                answer = num1 + num2
                question = f"{num1} + {num2}"
            elif operator == '-':
                if num1 < num2:
                    num1, num2 = num2, num1
                answer = num1 - num2
                question = f"{num1} - {num2}"
            elif operator == '*':
                num1 = random.randint(1, 20)
                num2 = random.randint(1, 10)
                answer = num1 * num2
                question = f"{num1} × {num2}"
            else:
                num2 = random.randint(1, 10)
                answer = num1 // num2
                num1 = answer * num2
                question = f"{num1} ÷ {num2}"

            self.pending_verification[group_id][user_id] = {
                'type': 'math',
                'question': question,
                'answer': answer,
                'timestamp': time.time()
            }

            max_attempts = verification.get('max_attempts', 3)
            self.verification_attempts[group_id][user_id] = 0

            yield event.plain_result(f"""🔢 请完成数学验证以完成入群审核:

{question} = ?

💡 请直接发送答案数字，您有 {max_attempts} 次机会""")

        elif mode == 'id':
            digits = random.choice([4, 5])
            random_id = random.randint(10**(digits-1), 10**digits - 1)
            self.pending_verification[group_id][user_id] = {
                'type': 'id',
                'question': random_id,
                'answer': random_id,
                'timestamp': time.time()
            }

            max_attempts = verification.get('max_attempts', 3)
            self.verification_attempts[group_id][user_id] = 0

            yield event.plain_result(f"""🔑 请输入验证码完成入群审核:

验证码: {random_id}

💡 请直接发送验证码数字，您有 {max_attempts} 次机会""")

    async def _handle_member_verification(self, group_id: str, event: AstrMessageEvent, code: str):
        """处理成员验证"""
        user_id = self.utils._get_user_id(event)
        verification = self.data_manager._get_group_data(group_id, 'verification', {})
        max_attempts = verification.get('max_attempts', 3)

        if group_id not in self.pending_verification or user_id not in self.pending_verification[group_id]:
            await self._generate_new_verification(group_id, event)
            return

        pending = self.pending_verification[group_id][user_id]
        attempts = self.verification_attempts[group_id].get(user_id, 0)

        try:
            user_answer = int(code.strip())

            if user_answer == pending['answer']:
                await self._verification_success(group_id, user_id, event)
            else:
                attempts += 1
                self.verification_attempts[group_id][user_id] = attempts

                if attempts >= max_attempts:
                    await self._verification_failed(group_id, user_id, event)
                else:
                    remaining = max_attempts - attempts
                    yield event.plain_result(f"""❌ 验证失败！

正确答案: {pending['answer']}
您还剩 {remaining} 次机会

🔢 请重新回答: {pending['question']} = ?""")

        except ValueError:
            attempts += 1
            self.verification_attempts[group_id][user_id] = attempts

            if attempts >= max_attempts:
                await self._verification_failed(group_id, user_id, event)
            else:
                remaining = max_attempts - attempts
                yield event.plain_result(f"""❌ 格式错误！请输入数字答案

您还剩 {remaining} 次机会

🔢 请重新回答: {pending['question']} = ?""")

    async def _verification_success(self, group_id: str, user_id: str, event: AstrMessageEvent):
        """验证成功"""
        if group_id in self.pending_verification and user_id in self.pending_verification[group_id]:
            del self.pending_verification[group_id][user_id]
        if group_id in self.verification_attempts and user_id in self.verification_attempts[group_id]:
            del self.verification_attempts[group_id][user_id]

        yield event.plain_result("✅ 验证通过！欢迎加入本群！🎉")

        user_name = getattr(event, 'user_name', f"QQ_{user_id}")
        group_name = getattr(event, 'group_name', "本群")
        
        welcome_msg = self._generate_welcome_message(group_id, user_name, user_id, group_name, 150)
        if welcome_msg:
            yield event.plain_result(f"🎊 {welcome_msg}")

    async def _verification_failed(self, group_id: str, user_id: str, event: AstrMessageEvent):
        """验证失败 - 超出次数限制"""
        if group_id in self.pending_verification and user_id in self.pending_verification[group_id]:
            del self.pending_verification[group_id][user_id]
        if group_id in self.verification_attempts and user_id in self.verification_attempts[group_id]:
            del self.verification_attempts[group_id][user_id]

        config = self.data_manager._get_group_data(group_id, 'config', {})
        kick_on_fail = config.get('approval_kick_on_fail', False)

        if kick_on_fail:
            yield event.plain_result(f"❌ 验证失败次数过多，已被移出群聊！")

            if self.context:
                try:
                    await self.context.call_api(
                        "set_group_kick",
                        group_id=int(group_id),
                        user_id=int(user_id),
                        reject_add_request=True
                    )
                except Exception as e:
                    from astrbot.api import logger
                    logger.error(f"踢出用户失败: {e}")
        else:
            yield event.plain_result(f"❌ 验证失败次数过多，请联系管理员！")

    async def _approve_user(self, group_id: str, user_id: str, reason: str, event: AstrMessageEvent):
        """批准用户入群"""
        inviter = self.invitation_manager._get_inviter_of(group_id, user_id)
        result = f"✅ 已同意 {user_id} 入群"
        if reason and reason != '审核通过':
            result += f" ({reason})"
        if inviter:
            result += f" | 邀请人: {inviter}"
        yield event.plain_result(result)

        user_name = getattr(event, 'user_name', f"QQ_{user_id}")
        group_name = getattr(event, 'group_name', "本群")
        welcome_msg = self._generate_welcome_message(group_id, user_name, user_id, group_name, 150)
        if welcome_msg:
            yield event.plain_result(f"🎊 {welcome_msg}")

    async def _reject_user(self, group_id: str, user_id: str, reason: str):
        """拒绝用户入群"""
        result = f"❌ 已拒绝 {user_id} 入群"
        if reason and reason != '审核未通过':
            result += f" ({reason})"
        yield event.plain_result(result)

    async def _show_settings(self, group_id: str, verification: Dict):
        """显示设置菜单"""
        current_mode = verification.get('mode', 'math')
        mode_name = self._get_mode_name(current_mode)
        max_attempts = verification.get('max_attempts', 3)

        result = f"""⚙️ 审核设置:

当前模式: {mode_name}
验证次数上限: {max_attempts}次

📋 可用模式:
1. math - 数学验证(加减乘除)
2. id   - 随机数字验证(4-5位)

💡 使用:
/入群审核 math          - 切换到数学验证
/入群审核 id            - 切换到随机数字验证
/审核自定义次数 <次数>   - 设置验证次数上限(仅主人)"""

        yield event.plain_result(result)

    async def _set_mode(self, group_id: str, verification: Dict, mode: str):
        """设置审核模式"""
        valid_modes = ['math', 'id']

        if mode in valid_modes:
            verification['mode'] = mode
            self.data_manager._save_group_data('verification')
            yield event.plain_result(f"✅ 审核模式已设置为: {self._get_mode_name(mode)}")
        else:
            yield event.plain_result("❌ 无效模式，可用: math/id")

    def _get_mode_name(self, mode: str) -> str:
        """获取模式中文名"""
        mode_names = {
            'math': '数学验证',
            'id': '随机数字验证',
            'manual': '手动审核',
            'auto': '自动审核'
        }
        return mode_names.get(mode, mode)

    def _generate_welcome_message(self, group_id: str, user_name: str, user_id: str, group_name: str, member_count: int):
        """生成欢迎消息 - 格式: 欢迎 [用户名]进入[群名],[自定义内容]"""
        config = self.data_manager._get_group_data(group_id, 'config', {})
        if not config.get('welcome_enabled', True):
            return None

        welcome_contents = config.get('welcome_messages', [])
        if not welcome_contents or not welcome_contents[0]:
            return f"欢迎 {user_name}进入{group_name},"

        content = welcome_contents[0]
        content = content.replace('{group_name}', group_name)
        content = content.replace('{member_count}', str(member_count))
        content = content.replace('{current_time}', time.strftime("%Y-%m-%d %H:%M:%S"))

        return f"欢迎 {user_name}进入{group_name},{content}"

"""
QQ群管插件 v3.1 - 分群模式
使用 AstrBot 框架开发
"""

import os
import asyncio
import time
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger

from .core import DataManager, InvitationManager, Utils
from .features import (
    ApprovalFeature,
    BlacklistFeature,
    KickFeature,
    MuteFeature,
    OtherFeatures
)


class GroupManagerPlugin(Star):
    """QQ群管插件主类"""

    def __init__(self, context: Context):
        super().__init__(context)
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.context = context
        
        # 获取插件设置
        plugin_settings = {}
        try:
            plugin_settings = context.get_settings() if hasattr(context, 'get_settings') else {}
        except Exception as e:
            logger.warning(f"获取插件设置失败: {e}")
        
        # 共享消息历史记录（用于撤回功能）
        self.message_history = {}
        self.self_messages = {}  # 机器人发送的消息记录
        
        # 初始化核心模块
        self.data_manager = DataManager(self.plugin_dir, plugin_settings)
        self.utils = Utils(self.data_manager)
        self.invitation_manager = InvitationManager(self.data_manager)
        
        # 初始化功能模块
        self.approval_feature = ApprovalFeature(self.data_manager, self.utils, self.invitation_manager, context)
        self.blacklist_feature = BlacklistFeature(self.data_manager, self.utils, context)
        self.kick_feature = KickFeature(self.data_manager, self.utils, self.invitation_manager, context, self.message_history)
        self.mute_feature = MuteFeature(self.data_manager, self.utils, context)
        self.other_features = OtherFeatures(self.data_manager, self.utils, context, self.message_history, self.self_messages)
        
        # 启动定时任务
        self.self_recall_task = asyncio.create_task(self.check_self_messages())
        self.scheduled_task = asyncio.create_task(self.run_scheduled_tasks())
        
        logger.info("QQ群管插件初始化完成（分群模式 v4.0）")

    async def check_self_messages(self):
        """检查并自动撤回机器人消息"""
        logger.info("机器人自动撤回任务已启动")
        while True:
            try:
                await asyncio.sleep(1)  # 每秒检查一次
                current_time = time.time()
                
                # 检查每个群的消息
                for group_id, messages in list(self.self_messages.items()):
                    if not messages:
                        continue
                    
                    config = self.data_manager.get_effective_config(group_id)
                    # 检查是否开启撤回自身功能
                    if not config.get('self_recall_enabled', False):
                        continue
                    
                    recall_time = config.get('self_recall_time', 10)  # 默认10秒
                    
                    # 检查每条消息是否过期
                    remaining_messages = []
                    for msg_id, send_time in messages:
                        if current_time - send_time >= recall_time:
                            # 撤回消息
                            try:
                                if self.context:
                                    await self.context.call_api(
                                        "delete_msg",
                                        message_id=msg_id
                                    )
                                    logger.debug(f"已自动撤回群 {group_id} 的机器人消息 (ID: {msg_id})")
                            except Exception as e:
                                logger.debug(f"撤回消息失败: {e}")
                        else:
                            remaining_messages.append((msg_id, send_time))
                    
                    # 更新消息列表
                    if remaining_messages:
                        self.self_messages[group_id] = remaining_messages
                    else:
                        if group_id in self.self_messages:
                            del self.self_messages[group_id]
                            
            except Exception as e:
                logger.error(f"自动撤回检查任务出错: {e}")

    async def run_scheduled_tasks(self):
        """执行定时任务（定时消息、定时禁言）"""
        logger.info("定时任务执行器已启动")
        last_minute = -1
        
        while True:
            try:
                await asyncio.sleep(1)
                now = time.localtime()
                current_minute = now.tm_min
                current_hour = now.tm_hour
                current_time_str = f"{current_hour:02d}:{current_minute:02d}"
                
                # 每分钟检查一次
                if current_minute == last_minute:
                    continue
                last_minute = current_minute
                
                # 检查所有群的定时任务
                groups = self.data_manager._list_groups()
                
                for group_id in groups:
                    # 检查群是否授权
                    try:
                        from .core import authorization
                        if not authorization.is_group_authorized(group_id):
                            continue
                    except Exception:
                        continue
                    
                    # 检查群是否在过滤列表中
                    if self.data_manager.is_group_filtered(group_id):
                        continue
                    
                    config = self.data_manager.get_effective_config(group_id)
                    
                    # 处理定时消息
                    schedule_list = self.data_manager._get_group_data(group_id, 'schedule_list', [])
                    for item in schedule_list:
                        if item.get('enabled', True) and item.get('time') == current_time_str:
                            try:
                                content = item.get('content', '')
                                if item.get('at_all', False):
                                    # @全体成员
                                    message = f"[CQ:at,qq=all]\n{content}"
                                else:
                                    message = content
                                
                                if self.context:
                                    await self.context.call_api(
                                        "send_group_msg",
                                        group_id=int(group_id),
                                        message=message
                                    )
                                    logger.info(f"定时消息已发送到群 {group_id}: {content[:30]}...")
                            except Exception as e:
                                logger.error(f"发送定时消息失败: {e}")
                    
                    # 处理定时禁言
                    if config.get('scheduled_mute_enabled', False):
                        start_time = config.get('scheduled_mute_start', '')
                        end_time = config.get('scheduled_mute_end', '')
                        
                        if start_time == current_time_str:
                            # 开启全体禁言
                            try:
                                if self.context:
                                    await self.context.call_api(
                                        "set_group_whole_ban",
                                        group_id=int(group_id),
                                        enable=True
                                    )
                                    logger.info(f"定时禁言已开启: {group_id}")
                            except Exception as e:
                                logger.error(f"开启定时禁言失败: {e}")
                        
                        if end_time == current_time_str:
                            # 关闭全体禁言
                            try:
                                if self.context:
                                    await self.context.call_api(
                                        "set_group_whole_ban",
                                        group_id=int(group_id),
                                        enable=False
                                    )
                                    logger.info(f"定时禁言已关闭: {group_id}")
                            except Exception as e:
                                logger.error(f"关闭定时禁言失败: {e}")
                                
            except Exception as e:
                logger.error(f"定时任务执行器出错: {e}")

    @filter.on_group_member_increase
    async def on_member_join(self, event: AstrMessageEvent):
        """新成员加入群聊时触发欢迎"""
        try:
            group_id = str(event.get_group_id())
            
            # 检查群是否在过滤列表中
            if self.data_manager.is_group_filtered(group_id):
                return
            
            config = self.data_manager.get_effective_config(group_id)
            
            # 检查欢迎功能是否开启
            if not config.get('welcome_enabled', True):
                return
            
            # 获取用户信息
            user_id = str(event.get_user_id())
            user_name = event.get_sender_name() or user_id
            
            # 获取欢迎语，默认为"欢迎进群"
            welcome_msg = config.get('welcome_message', '欢迎进群')
            
            # 构建欢迎消息，格式：@用户 加入群 欢迎语
            # 使用 AstrBot 的 @提及格式
            mention = f"[CQ:at,qq={user_id}]"
            message = f"{mention} 加入群 {welcome_msg}"
            
            # 发送欢迎消息
            await event.reply(message)
            
            # 记录机器人发送的消息
            # 注意：这里我们无法直接获取到消息ID，因为 AstrBot 的 reply 通常不会返回消息ID
            # 但我们可以添加一个小技巧：在发送消息后，如果我们能捕获到消息ID的话
            logger.info(f"群 {group_id} 欢迎新成员 {user_id}")
            
        except Exception as e:
            logger.error(f"发送欢迎消息失败: {e}")

    async def terminate(self):
        """插件卸载时的清理工作"""
        if hasattr(self, 'self_recall_task'):
            self.self_recall_task.cancel()
        if hasattr(self, 'scheduled_task'):
            self.scheduled_task.cancel()
        logger.info("QQ群管插件已卸载")

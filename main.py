"""
QQ群管插件 v3.1 - 分群模式
使用 AstrBot 框架开发
"""

import os
from astrbot.api.event import filter
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
        
        # 初始化核心模块
        self.data_manager = DataManager(self.plugin_dir, plugin_settings)
        self.utils = Utils(self.data_manager)
        self.invitation_manager = InvitationManager(self.data_manager)
        
        # 初始化功能模块
        self.approval_feature = ApprovalFeature(self.data_manager, self.utils, self.invitation_manager, context)
        self.blacklist_feature = BlacklistFeature(self.data_manager, self.utils, self.invitation_manager, context)
        self.kick_feature = KickFeature(self.data_manager, self.utils, self.invitation_manager, context, self.message_history)
        self.mute_feature = MuteFeature(self.data_manager, self.utils, context)
        self.other_features = OtherFeatures(self.data_manager, self.utils, context, self.message_history)
        
        logger.info("QQ群管插件初始化完成（分群模式 v3.1）")

    async def terminate(self):
        """插件卸载时的清理工作"""
        logger.info("QQ群管插件已卸载")
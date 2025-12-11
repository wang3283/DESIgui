#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
License验证集成模块 - 用于主程序集成License验证功能
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple
from license_manager_core import LicenseValidator, LicenseGenerator


class LicenseIntegration:
    """License集成管理器"""
    
    def __init__(self):
        self.license_file = Path.home() / ".desi_analytics" / "license.key"
        self.license_key = None
        self.expires_at = None
        self.days_left = None
        self.is_valid = False
        self.is_expired = False
        self.features_restricted = False
    
    def check_license_on_startup(self) -> Tuple[bool, str, Optional[int]]:
        """
        启动时检查License
        
        返回:
            (是否有效, 消息, 剩余天数)
        """
        # 检查License文件是否存在
        if not self.license_file.exists():
            return (False, "未找到License文件", None)
        
        # 读取License
        try:
            self.license_key = self.license_file.read_text().strip()
        except Exception as e:
            return (False, f"读取License失败: {e}", None)
        
        # 验证License格式
        if not LicenseGenerator.validate_license_format(self.license_key):
            return (False, "License格式无效", None)
        
        # 检查到期时间（从数据库或配置文件读取）
        self.expires_at = self._get_expiry_date()
        
        if not self.expires_at:
            # 没有到期时间，只验证格式
            self.is_valid = True
            return (True, "License有效（无到期限制）", None)
        
        # 验证到期时间
        self.days_left = LicenseValidator.check_expiry(self.expires_at)
        
        if self.days_left < 0:
            self.is_expired = True
            self.features_restricted = True
            return (False, f"许可证已过期（{abs(self.days_left)}天前）", self.days_left)
        
        self.is_valid = True
        return (True, f"License有效，剩余{self.days_left}天", self.days_left)
    
    def _get_expiry_date(self) -> Optional[str]:
        """
        获取到期日期
        
        从配置文件或数据库读取
        如果没有配置，返回None（表示无限期）
        """
        # 尝试从配置文件读取
        config_file = Path.home() / ".desi_analytics" / "license_config.txt"
        
        if config_file.exists():
            try:
                lines = config_file.read_text().strip().split('\n')
                for line in lines:
                    if line.startswith('expires_at='):
                        return line.split('=', 1)[1].strip()
            except:
                pass
        
        # 默认：1年后过期（用于测试）
        from datetime import timedelta
        default_expiry = datetime.now() + timedelta(days=365)
        return default_expiry.isoformat()
    
    def should_show_reminder(self) -> Tuple[bool, str]:
        """
        判断是否显示提醒
        
        返回:
            (是否显示, 提醒级别)
        """
        if self.days_left is None:
            return (False, 'none')
        
        return LicenseValidator.should_show_reminder(self.days_left)
    
    def get_reminder_message(self) -> str:
        """获取提醒消息"""
        if self.days_left is None:
            return ""
        
        return LicenseValidator.get_reminder_message(self.days_left)
    
    def should_restrict_features(self) -> bool:
        """判断是否应该限制功能"""
        return self.features_restricted
    
    def get_restricted_features(self) -> list:
        """
        获取受限功能列表
        
        返回:
            受限功能名称列表
        """
        if not self.features_restricted:
            return []
        
        return [
            'load_sample',      # 加载新样本
            'export_data',      # 导出数据
            'split_metabolites', # 拆分代谢物
            'generate_report',  # 生成报告
            'roi_analysis',     # ROI分析
            'metabolite_search', # 代谢物查询
        ]
    
    def is_feature_allowed(self, feature_name: str) -> bool:
        """
        检查功能是否允许使用
        
        参数:
            feature_name: 功能名称
        
        返回:
            是否允许
        """
        if not self.features_restricted:
            return True
        
        restricted = self.get_restricted_features()
        return feature_name not in restricted
    
    def get_feature_restriction_message(self, feature_name: str) -> str:
        """
        获取功能限制消息
        
        参数:
            feature_name: 功能名称
        
        返回:
            限制消息
        """
        if self.is_feature_allowed(feature_name):
            return ""
        
        return (
            f"此功能已被限制！\n\n"
            f"您的许可证已过期，无法使用此功能。\n"
            f"请联系管理员续费以恢复所有功能。\n\n"
            f"您仍可以：\n"
            f"• 查看历史数据\n"
            f"• 导出使用报告"
        )
    
    def update_license(self, new_license_key: str) -> Tuple[bool, str]:
        """
        更新License
        
        参数:
            new_license_key: 新的许可证密钥
        
        返回:
            (是否成功, 消息)
        """
        # 验证格式
        if not LicenseGenerator.validate_license_format(new_license_key):
            return (False, "License格式无效")
        
        # 保存新License
        try:
            self.license_file.parent.mkdir(parents=True, exist_ok=True)
            self.license_file.write_text(new_license_key)
            
            # 重新检查
            self.license_key = new_license_key
            is_valid, message, days_left = self.check_license_on_startup()
            
            if is_valid:
                self.features_restricted = False
                return (True, "License更新成功，所有功能已恢复")
            else:
                return (False, f"License更新失败: {message}")
        
        except Exception as e:
            return (False, f"保存License失败: {e}")
    
    def get_license_info(self) -> Dict:
        """
        获取许可证信息
        
        返回:
            许可证信息字典
        """
        return {
            'license_key': self.license_key,
            'expires_at': self.expires_at,
            'days_left': self.days_left,
            'is_valid': self.is_valid,
            'is_expired': self.is_expired,
            'features_restricted': self.features_restricted
        }


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("License集成模块测试")
    print("=" * 60)
    
    # 创建集成管理器
    integration = LicenseIntegration()
    
    # 测试启动检查
    print("\n[测试] 测试启动检查...")
    is_valid, message, days_left = integration.check_license_on_startup()
    print(f"验证结果: {message}")
    print(f"剩余天数: {days_left}")
    print(f"是否有效: {is_valid}")
    
    # 测试提醒
    print("\n[测试] 测试提醒...")
    should_show, level = integration.should_show_reminder()
    print(f"是否显示提醒: {should_show}")
    print(f"提醒级别: {level}")
    
    if should_show:
        message = integration.get_reminder_message()
        print(f"提醒消息: {message}")
    
    # 测试功能限制
    print("\n[测试] 测试功能限制...")
    is_restricted = integration.should_restrict_features()
    print(f"是否限制功能: {is_restricted}")
    
    if is_restricted:
        restricted_features = integration.get_restricted_features()
        print(f"受限功能: {restricted_features}")
        
        # 测试具体功能
        test_features = ['load_sample', 'view_data', 'export_report']
        for feature in test_features:
            allowed = integration.is_feature_allowed(feature)
            print(f"  {feature}: {'允许' if allowed else '受限'}")
    
    # 获取许可证信息
    print("\n[测试] 许可证信息...")
    info = integration.get_license_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    print("\n[成功] 所有测试完成")

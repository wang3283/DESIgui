#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
License验证属性测试

测试License验证和到期管理功能的正确性
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from license_manager_core import LicenseGenerator, LicenseValidator
from license_integration import LicenseIntegration


class TestLicenseValidationProperties:
    """License验证属性测试"""
    
    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=50)
    def test_property_13_expiry_reminder_trigger(self, days_left):
        """
        **Feature: commercial-billing-system, Property 13: 到期提醒触发性**
        **Validates: Requirements 5.2, 5.3**
        
        对于任意剩余天数在30天以内的License，系统应该显示相应级别的续费提醒
        """
        # 测试不同天数的提醒级别
        should_show, level = LicenseValidator.should_show_reminder(days_left)
        
        if days_left <= 7:
            assert should_show, f"剩余{days_left}天应该显示提醒"
            assert level == 'urgent', f"剩余{days_left}天应该是紧急提醒"
        elif days_left <= 30:
            assert should_show, f"剩余{days_left}天应该显示提醒"
            assert level == 'warning', f"剩余{days_left}天应该是警告提醒"
        elif days_left <= 60:
            assert should_show, f"剩余{days_left}天应该显示提醒"
            assert level == 'info', f"剩余{days_left}天应该是信息提醒"
        else:
            assert not should_show, f"剩余{days_left}天不应该显示提醒"
            assert level == 'none', f"剩余{days_left}天提醒级别应该是none"
    
    @given(st.integers(min_value=-100, max_value=-1))
    @settings(max_examples=30)
    def test_property_13_expired_reminder(self, days_left):
        """
        **Feature: commercial-billing-system, Property 13: 到期提醒触发性（已过期）**
        **Validates: Requirements 5.2, 5.3**
        
        对于任意已过期的License，系统应该显示过期提醒
        """
        should_show, level = LicenseValidator.should_show_reminder(days_left)
        
        assert should_show, f"已过期{abs(days_left)}天应该显示提醒"
        assert level == 'expired', f"已过期应该是expired级别"
    
    @given(st.integers(min_value=-100, max_value=-1))
    @settings(max_examples=50)
    def test_property_14_expired_license_restriction(self, days_left):
        """
        **Feature: commercial-billing-system, Property 14: 过期License功能限制**
        **Validates: Requirements 5.4**
        
        对于任意已过期的License，系统应该限制核心功能
        """
        # 直接测试功能限制逻辑
        should_restrict = LicenseValidator.should_restrict_features(days_left)
        
        # 已过期应该限制功能
        assert should_restrict, f"已过期{abs(days_left)}天应该限制功能"
        
        # 创建集成管理器测试受限功能
        integration = LicenseIntegration()
        integration.features_restricted = True
        integration.days_left = days_left
        
        # 验证受限功能列表
        restricted = integration.get_restricted_features()
        assert len(restricted) > 0, "应该有受限功能"
        
        # 验证核心功能被限制
        assert not integration.is_feature_allowed('load_sample'), "加载样本应该被限制"
        assert not integration.is_feature_allowed('export_data'), "导出数据应该被限制"
        assert not integration.is_feature_allowed('split_metabolites'), "拆分代谢物应该被限制"
        
        # 验证限制消息
        message = integration.get_feature_restriction_message('load_sample')
        assert len(message) > 0, "应该有限制消息"
        assert "过期" in message or "限制" in message, "消息应该说明原因"
    
    @given(st.integers(min_value=1, max_value=365))
    @settings(max_examples=50)
    def test_property_15_license_update_effectiveness(self, new_days):
        """
        **Feature: commercial-billing-system, Property 15: License更新生效性**
        **Validates: Requirements 5.5**
        
        对于任意有效的新License密钥，系统应该验证并更新，立即恢复所有功能
        """
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 创建集成管理器
            integration = LicenseIntegration()
            integration.license_file = Path(temp_dir) / "license.key"
            integration.license_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 生成新License
            new_license = LicenseGenerator.generate_license_key()
            
            # 更新License
            success, message = integration.update_license(new_license)
            
            # 验证更新成功
            assert success, f"License更新应该成功: {message}"
            
            # 验证License文件已更新
            assert integration.license_file.exists(), "License文件应该存在"
            saved_license = integration.license_file.read_text().strip()
            assert saved_license == new_license, "保存的License应该与新License一致"
            
            # 验证功能恢复
            assert not integration.features_restricted, "功能限制应该被解除"
            assert integration.is_feature_allowed('load_sample'), "加载样本应该被允许"
            assert integration.is_feature_allowed('export_data'), "导出数据应该被允许"
        
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_invalid_license_format_rejection(self):
        """测试无效License格式被拒绝"""
        invalid_licenses = [
            "INVALID-LICENSE",
            "DESI-12345678",
            "DESI-12345678-87654321",  # 缺少校验位
            "DESI-12345678-87654321-XXXX",  # 错误的校验位
            "",
            "   ",
        ]
        
        for invalid in invalid_licenses:
            is_valid = LicenseGenerator.validate_license_format(invalid)
            assert not is_valid, f"应该识别为无效: {invalid}"
    
    def test_valid_license_format_acceptance(self):
        """测试有效License格式被接受"""
        # 生成多个License并验证
        for _ in range(20):
            license_key = LicenseGenerator.generate_license_key()
            is_valid = LicenseGenerator.validate_license_format(license_key)
            assert is_valid, f"生成的License应该有效: {license_key}"
    
    def test_expiry_reminder_message_content(self):
        """测试到期提醒消息内容"""
        test_cases = [
            (365, False, ""),
            (30, True, "30天"),
            (7, True, "7天"),
            (-1, True, "过期"),
        ]
        
        for days, should_have_message, expected_keyword in test_cases:
            message = LicenseValidator.get_reminder_message(days, "测试客户")
            
            if should_have_message:
                assert len(message) > 0, f"剩余{days}天应该有提醒消息"
                if expected_keyword:
                    assert expected_keyword in message, f"消息应该包含'{expected_keyword}'"
            else:
                assert len(message) == 0, f"剩余{days}天不应该有提醒消息"
    
    def test_feature_restriction_message(self):
        """测试功能限制消息"""
        integration = LicenseIntegration()
        integration.features_restricted = True
        
        restricted_features = ['load_sample', 'export_data', 'split_metabolites']
        
        for feature in restricted_features:
            message = integration.get_feature_restriction_message(feature)
            assert len(message) > 0, f"{feature}应该有限制消息"
            assert "过期" in message or "限制" in message, "消息应该说明原因"
    
    def test_license_info_completeness(self):
        """测试License信息完整性"""
        integration = LicenseIntegration()
        integration.check_license_on_startup()
        
        info = integration.get_license_info()
        
        # 验证必要字段存在
        required_fields = [
            'license_key', 'expires_at', 'days_left',
            'is_valid', 'is_expired', 'features_restricted'
        ]
        
        for field in required_fields:
            assert field in info, f"License信息应该包含{field}字段"


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])

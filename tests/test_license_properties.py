#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
License模块属性测试
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from hypothesis import given, strategies as st, settings
from license_manager_core import LicenseGenerator, LicenseValidator


class TestLicenseProperties:
    """License属性测试"""
    
    @given(st.integers(min_value=1, max_value=1000))
    @settings(max_examples=100)
    def test_license_uniqueness_property(self, n):
        """
        **Feature: commercial-billing-system, Property 1: License唯一性**
        **验证: 需求 1.3**
        
        对于任意数量的License生成操作，所有生成的License应该是唯一的
        """
        licenses = set()
        for _ in range(n):
            license_key = LicenseGenerator.generate_license_key()
            licenses.add(license_key)
        
        # 验证唯一性
        assert len(licenses) == n, f"生成{n}个License，但只有{len(licenses)}个唯一"
    
    @given(st.integers(min_value=1, max_value=1000))
    @settings(max_examples=100)
    def test_customer_id_uniqueness_property(self, n):
        """
        **Feature: commercial-billing-system, Property 2: 客户ID唯一性**
        **验证: 需求 1.3**
        
        对于任意数量的客户ID生成操作，所有生成的客户ID应该是唯一的
        """
        customer_ids = set()
        for _ in range(n):
            customer_id = LicenseGenerator.generate_customer_id()
            customer_ids.add(customer_id)
        
        # 验证唯一性
        assert len(customer_ids) == n, f"生成{n}个客户ID，但只有{len(customer_ids)}个唯一"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=10))
    def test_generated_license_format_valid_property(self, _):
        """
        **Feature: commercial-billing-system, Property 12: License验证正确性**
        **验证: 需求 5.1**
        
        对于任意生成的License，格式验证应该通过
        """
        license_key = LicenseGenerator.generate_license_key()
        
        # 验证格式
        is_valid = LicenseGenerator.validate_license_format(license_key)
        assert is_valid, f"生成的License格式无效: {license_key}"
    
    @given(
        st.text(min_size=1, max_size=50),  # name
        st.emails(),  # email
        st.text(max_size=50),  # company
        st.integers(min_value=1, max_value=3650)  # expires_days
    )
    @settings(max_examples=100)
    def test_create_customer_data_completeness_property(self, name, email, company, expires_days):
        """
        **Feature: commercial-billing-system, Property 12: License验证正确性**
        **验证: 需求 5.1**
        
        对于任意客户信息，创建的客户数据应该包含所有必要字段且License有效
        """
        customer_data = LicenseGenerator.create_customer_data(
            name=name,
            email=email,
            company=company,
            expires_days=expires_days
        )
        
        # 验证必要字段存在
        required_fields = ['customer_id', 'name', 'email', 'license_key', 
                          'created_at', 'expires_at', 'status']
        for field in required_fields:
            assert field in customer_data, f"缺少字段: {field}"
        
        # 验证License格式
        assert LicenseGenerator.validate_license_format(customer_data['license_key']), \
            "生成的License格式无效"
        
        # 验证客户ID格式
        assert customer_data['customer_id'].startswith('CUST-'), "客户ID格式错误"
    
    @given(st.integers(min_value=-100, max_value=1000))
    @settings(max_examples=100)
    def test_expiry_reminder_logic_property(self, days_left):
        """
        **Feature: commercial-billing-system, Property 13: 到期提醒触发性**
        **验证: 需求 5.2, 5.3**
        
        对于任意剩余天数，到期提醒逻辑应该正确判断是否显示和级别
        """
        show, level = LicenseValidator.should_show_reminder(days_left)
        
        # 验证逻辑正确性
        if days_left < 0:
            assert show and level == 'expired', f"过期应显示expired: {days_left}天"
        elif days_left <= 7:
            assert show and level == 'urgent', f"7天内应显示urgent: {days_left}天"
        elif days_left <= 30:
            assert show and level == 'warning', f"30天内应显示warning: {days_left}天"
        elif days_left <= 60:
            assert show and level == 'info', f"60天内应显示info: {days_left}天"
        else:
            assert not show and level == 'none', f"60天以上不应显示: {days_left}天"
    
    @given(st.integers(min_value=-100, max_value=1000))
    @settings(max_examples=100)
    def test_feature_restriction_property(self, days_left):
        """
        **Feature: commercial-billing-system, Property 14: 过期License功能限制**
        **验证: 需求 5.4**
        
        对于任意剩余天数，只有过期后才应该限制功能
        """
        should_restrict = LicenseValidator.should_restrict_features(days_left)
        
        if days_left < 0:
            assert should_restrict, f"过期应限制功能: {days_left}天"
        else:
            assert not should_restrict, f"未过期不应限制功能: {days_left}天"
    
    @given(
        st.text(min_size=1, max_size=50),
        st.emails(),
        st.integers(min_value=1, max_value=365)
    )
    @settings(max_examples=50)
    def test_license_validation_with_expiry_property(self, name, email, expires_days):
        """
        **Feature: commercial-billing-system, Property 15: License更新生效性**
        **验证: 需求 5.5**
        
        对于任意有效的客户数据，License验证应该返回正确的结果
        """
        customer_data = LicenseGenerator.create_customer_data(
            name=name,
            email=email,
            expires_days=expires_days
        )
        
        # 验证License
        result = LicenseValidator.validate(
            customer_data['license_key'],
            customer_data['expires_at']
        )
        
        # 应该验证通过
        assert result['valid'], f"有效License验证失败: {result['message']}"
        assert result['format_valid'], "格式验证应该通过"
        assert not result['expired'], "不应该过期"
        assert result['days_left'] is not None, "应该有剩余天数"
        assert result['days_left'] >= expires_days - 1, "剩余天数计算错误"  # 允许1天误差
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_invalid_license_format_detection_property(self, invalid_license):
        """
        **Feature: commercial-billing-system, Property 12: License验证正确性**
        **验证: 需求 5.1**
        
        对于任意非标准格式的字符串，格式验证应该返回False（除非碰巧符合格式）
        """
        # 如果不是DESI-开头，肯定无效
        if not invalid_license.startswith('DESI-'):
            is_valid = LicenseGenerator.validate_license_format(invalid_license)
            assert not is_valid, f"应该识别为无效: {invalid_license}"


# 运行测试
if __name__ == "__main__":
    import pytest
    
    print("=" * 60)
    print("运行License模块属性测试")
    print("=" * 60)
    
    pytest.main([__file__, "-v", "--tb=short"])

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计费逻辑属性测试 - 使用Hypothesis进行Property-Based Testing

测试属性:
- 属性6: 按样本数计费正确性
- 属性7: 按操作次数计费正确性
- 属性8: 固定订阅计费正确性
- 属性21: 混合模式计费正确性
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from invoice_generator import InvoiceGenerator, InvoiceConfig


class TestBillingProperties:
    """计费逻辑属性测试"""
    
    @given(
        unique_samples=st.integers(min_value=0, max_value=10000),
        unit_price=st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_property_6_per_sample_billing_correctness(self, unique_samples, unit_price):
        """
        **Feature: commercial-billing-system, Property 6: 按样本数计费正确性**
        **Validates: Requirements 3.2**
        
        对于任意客户和任意单价，使用"按样本数"模式计算的总金额应该等于唯一样本数乘以单价
        """
        # 创建配置
        config = InvoiceConfig(
            customer_id='TEST',
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 31),
            billing_mode='per_sample',
            unit_price=unit_price,
            tax_rate=0.0  # 不含税，便于验证
        )
        
        # 使用数据
        usage_data = {
            'unique_samples': unique_samples,
            'total_operations': 0,
            'total_samples': unique_samples
        }
        
        # 计算金额
        generator = InvoiceGenerator()
        subtotal, tax_amount, total_amount = generator.calculate_amount(config, usage_data)
        
        # 验证: 总金额 = 唯一样本数 × 单价
        expected_amount = unique_samples * unit_price
        
        # 使用相对误差进行浮点数比较
        if expected_amount > 0:
            relative_error = abs(total_amount - expected_amount) / expected_amount
            assert relative_error < 0.0001, f"计算错误: {total_amount} != {expected_amount}"
        else:
            assert abs(total_amount - expected_amount) < 0.01
    
    @given(
        total_operations=st.integers(min_value=0, max_value=10000),
        unit_price=st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_property_7_per_operation_billing_correctness(self, total_operations, unit_price):
        """
        **Feature: commercial-billing-system, Property 7: 按操作次数计费正确性**
        **Validates: Requirements 3.3**
        
        对于任意客户和任意单价，使用"按操作次数"模式计算的总金额应该等于总操作次数乘以单价
        """
        # 创建配置
        config = InvoiceConfig(
            customer_id='TEST',
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 31),
            billing_mode='per_operation',
            unit_price=unit_price,
            tax_rate=0.0
        )
        
        # 使用数据
        usage_data = {
            'unique_samples': 0,
            'total_operations': total_operations,
            'total_samples': 0
        }
        
        # 计算金额
        generator = InvoiceGenerator()
        subtotal, tax_amount, total_amount = generator.calculate_amount(config, usage_data)
        
        # 验证: 总金额 = 总操作次数 × 单价
        expected_amount = total_operations * unit_price
        
        if expected_amount > 0:
            relative_error = abs(total_amount - expected_amount) / expected_amount
            assert relative_error < 0.0001, f"计算错误: {total_amount} != {expected_amount}"
        else:
            assert abs(total_amount - expected_amount) < 0.01
    
    @given(
        subscription_fee=st.floats(min_value=0.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        unique_samples=st.integers(min_value=0, max_value=10000),
        total_operations=st.integers(min_value=0, max_value=10000)
    )
    @settings(max_examples=100)
    def test_property_8_subscription_billing_correctness(self, subscription_fee, unique_samples, total_operations):
        """
        **Feature: commercial-billing-system, Property 8: 固定订阅计费正确性**
        **Validates: Requirements 3.4**
        
        对于任意使用"固定订阅"模式的客户，账单金额应该等于订阅费，与使用量无关
        """
        # 创建配置
        config = InvoiceConfig(
            customer_id='TEST',
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 31),
            billing_mode='subscription',
            subscription_fee=subscription_fee,
            tax_rate=0.0
        )
        
        # 使用数据 - 不同的使用量
        usage_data = {
            'unique_samples': unique_samples,
            'total_operations': total_operations,
            'total_samples': unique_samples
        }
        
        # 计算金额
        generator = InvoiceGenerator()
        subtotal, tax_amount, total_amount = generator.calculate_amount(config, usage_data)
        
        # 验证: 总金额 = 订阅费（与使用量无关）
        expected_amount = subscription_fee
        
        if expected_amount > 0:
            relative_error = abs(total_amount - expected_amount) / expected_amount
            assert relative_error < 0.0001, f"计算错误: {total_amount} != {expected_amount}"
        else:
            assert abs(total_amount - expected_amount) < 0.01
    
    @given(
        subscription_fee=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
        base_quota=st.integers(min_value=0, max_value=1000),
        unique_samples=st.integers(min_value=0, max_value=2000),
        overage_price=st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_property_21_hybrid_billing_correctness(self, subscription_fee, base_quota, unique_samples, overage_price):
        """
        **Feature: commercial-billing-system, Property 21: 混合模式计费正确性**
        **Validates: Requirements 7.5**
        
        对于任意使用量，"混合模式"计费应该正确计算基础订阅费加上超额使用费
        """
        # 创建配置
        config = InvoiceConfig(
            customer_id='TEST',
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 31),
            billing_mode='hybrid',
            subscription_fee=subscription_fee,
            base_quota=base_quota,
            overage_price=overage_price,
            tax_rate=0.0
        )
        
        # 使用数据
        usage_data = {
            'unique_samples': unique_samples,
            'total_operations': 0,
            'total_samples': unique_samples
        }
        
        # 计算金额
        generator = InvoiceGenerator()
        subtotal, tax_amount, total_amount = generator.calculate_amount(config, usage_data)
        
        # 验证: 总金额 = 基础订阅费 + max(0, 使用量 - 配额) × 超额单价
        overage = max(0, unique_samples - base_quota)
        expected_amount = subscription_fee + (overage * overage_price)
        
        if expected_amount > 0:
            relative_error = abs(total_amount - expected_amount) / expected_amount
            assert relative_error < 0.0001, f"计算错误: {total_amount} != {expected_amount}, overage={overage}"
        else:
            assert abs(total_amount - expected_amount) < 0.01
    
    @given(
        unique_samples=st.integers(min_value=1, max_value=1000),
        unit_price=st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
        tax_rate=st.floats(min_value=0.0, max_value=0.3, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50)
    def test_property_6_with_tax(self, unique_samples, unit_price, tax_rate):
        """
        测试按样本数计费（含税）
        验证税费计算的正确性
        """
        config = InvoiceConfig(
            customer_id='TEST',
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 31),
            billing_mode='per_sample',
            unit_price=unit_price,
            tax_rate=tax_rate
        )
        
        usage_data = {
            'unique_samples': unique_samples,
            'total_operations': 0,
            'total_samples': unique_samples
        }
        
        generator = InvoiceGenerator()
        subtotal, tax_amount, total_amount = generator.calculate_amount(config, usage_data)
        
        # 验证小计
        expected_subtotal = unique_samples * unit_price
        assert abs(subtotal - expected_subtotal) < 0.01
        
        # 验证税额
        expected_tax = expected_subtotal * tax_rate
        assert abs(tax_amount - expected_tax) < 0.01
        
        # 验证总额
        expected_total = expected_subtotal + expected_tax
        if expected_total > 0:
            relative_error = abs(total_amount - expected_total) / expected_total
            assert relative_error < 0.0001
        else:
            assert abs(total_amount - expected_total) < 0.01
    
    def test_edge_case_zero_usage(self):
        """边界测试: 零使用量"""
        config = InvoiceConfig(
            customer_id='TEST',
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 31),
            billing_mode='per_sample',
            unit_price=10.0,
            tax_rate=0.06
        )
        
        usage_data = {
            'unique_samples': 0,
            'total_operations': 0,
            'total_samples': 0
        }
        
        generator = InvoiceGenerator()
        subtotal, tax_amount, total_amount = generator.calculate_amount(config, usage_data)
        
        assert subtotal == 0.0
        assert tax_amount == 0.0
        assert total_amount == 0.0
    
    def test_edge_case_hybrid_no_overage(self):
        """边界测试: 混合模式无超额"""
        config = InvoiceConfig(
            customer_id='TEST',
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 31),
            billing_mode='hybrid',
            subscription_fee=500.0,
            base_quota=100,
            overage_price=8.0,
            tax_rate=0.0
        )
        
        # 使用量等于配额
        usage_data = {
            'unique_samples': 100,
            'total_operations': 0,
            'total_samples': 100
        }
        
        generator = InvoiceGenerator()
        subtotal, tax_amount, total_amount = generator.calculate_amount(config, usage_data)
        
        # 应该只收取基础订阅费
        assert subtotal == 500.0
        assert total_amount == 500.0
    
    def test_edge_case_hybrid_exact_overage(self):
        """边界测试: 混合模式刚好超额1个"""
        config = InvoiceConfig(
            customer_id='TEST',
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 31),
            billing_mode='hybrid',
            subscription_fee=500.0,
            base_quota=100,
            overage_price=8.0,
            tax_rate=0.0
        )
        
        # 使用量超出配额1个
        usage_data = {
            'unique_samples': 101,
            'total_operations': 0,
            'total_samples': 101
        }
        
        generator = InvoiceGenerator()
        subtotal, tax_amount, total_amount = generator.calculate_amount(config, usage_data)
        
        # 应该收取基础订阅费 + 1个超额费用
        expected = 500.0 + 8.0
        assert abs(subtotal - expected) < 0.01
        assert abs(total_amount - expected) < 0.01


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

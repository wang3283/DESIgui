#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客户管理的属性测试

测试客户管理功能的正确性属性
"""

import os
import tempfile
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timedelta
from contextlib import contextmanager

from database_manager import DatabaseManager
from license_manager_core import LicenseGenerator


@contextmanager
def temp_db_context():
    """创建临时数据库上下文管理器"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    db = DatabaseManager(db_path=path, mode='admin')
    
    try:
        yield db
    finally:
        db.close()
        if os.path.exists(path):
            os.unlink(path)


# 属性 3: 数据库更新一致性
@given(
    name=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',))),
    email=st.emails(),
    company=st.text(min_size=0, max_size=100, alphabet=st.characters(blacklist_categories=('Cs',))),
    new_name=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',))),
    new_email=st.emails()
)
@settings(max_examples=50, deadline=None)
def test_property_3_database_update_consistency(name, email, company, new_name, new_email):
    """
    **Feature: commercial-billing-system, Property 3: 数据库更新一致性**
    **验证: 需求 1.5**
    
    对于任意有效的客户信息修改，数据库中的记录应该被正确更新，
    且修改前后的customer_id保持不变
    """
    with temp_db_context() as temp_db:
        # 创建客户
        license_gen = LicenseGenerator()
        customer_id = license_gen.generate_customer_id()
        license_key = license_gen.generate_license_key()
        
        customer_data = {
            'customer_id': customer_id,
            'name': name,
            'email': email,
            'company': company if company else None,
            'license_key': license_key,
            'billing_mode': 'per_sample',
            'unit_price': 10.0,
            'subscription_fee': 0.0,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d'),
            'status': 'active',
            'notes': None
        }
        
        temp_db.create_customer(customer_data)
        
        # 获取原始客户数据
        original_customer = temp_db.get_customer(customer_id)
        assert original_customer is not None
        assert original_customer['customer_id'] == customer_id
        assert original_customer['name'] == name
        assert original_customer['email'] == email
        
        # 更新客户信息
        update_data = {
            'name': new_name,
            'email': new_email,
            'unit_price': 20.0
        }
        
        result = temp_db.update_customer(customer_id, update_data)
        assert result is True
        
        # 验证更新后的数据
        updated_customer = temp_db.get_customer(customer_id)
        assert updated_customer is not None
        
        # 属性验证：customer_id保持不变
        assert updated_customer['customer_id'] == customer_id
        assert updated_customer['customer_id'] == original_customer['customer_id']
        
        # 属性验证：更新的字段已改变
        assert updated_customer['name'] == new_name
        assert updated_customer['email'] == new_email
        assert updated_customer['unit_price'] == 20.0
        
        # 属性验证：未更新的字段保持不变
        assert updated_customer['license_key'] == original_customer['license_key']
        assert updated_customer['billing_mode'] == original_customer['billing_mode']
        assert updated_customer['company'] == original_customer['company']


@given(
    customers=st.lists(
        st.tuples(
            st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',))),
            st.emails(),
            st.text(min_size=0, max_size=100, alphabet=st.characters(blacklist_categories=('Cs',)))
        ),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=30, deadline=None)
def test_property_3_multiple_updates_consistency(customers):
    """
    **Feature: commercial-billing-system, Property 3: 数据库更新一致性（多客户）**
    **验证: 需求 1.5**
    
    对于任意数量的客户，每个客户的更新操作应该独立且一致，
    不影响其他客户的数据
    """
    with temp_db_context() as temp_db:
        license_gen = LicenseGenerator()
        customer_ids = []
        
        # 创建多个客户
        for name, email, company in customers:
            customer_id = license_gen.generate_customer_id()
            license_key = license_gen.generate_license_key()
            
            customer_data = {
                'customer_id': customer_id,
                'name': name,
                'email': email,
                'company': company if company else None,
                'license_key': license_key,
                'billing_mode': 'per_sample',
                'unit_price': 10.0,
                'subscription_fee': 0.0,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d'),
                'status': 'active',
                'notes': None
            }
            
            temp_db.create_customer(customer_data)
            customer_ids.append(customer_id)
        
        # 更新第一个客户
        if customer_ids:
            first_customer_id = customer_ids[0]
            update_data = {
                'name': 'Updated Name',
                'unit_price': 99.99
            }
            
            temp_db.update_customer(first_customer_id, update_data)
            
            # 验证第一个客户已更新
            updated_customer = temp_db.get_customer(first_customer_id)
            assert updated_customer['name'] == 'Updated Name'
            assert updated_customer['unit_price'] == 99.99
            
            # 验证其他客户未受影响
            for customer_id in customer_ids[1:]:
                other_customer = temp_db.get_customer(customer_id)
                assert other_customer['name'] != 'Updated Name'
                assert other_customer['unit_price'] == 10.0


@given(
    name=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',))),
    email=st.emails()
)
@settings(max_examples=30, deadline=None)
def test_property_3_delete_consistency(name, email):
    """
    **Feature: commercial-billing-system, Property 3: 数据库删除一致性**
    **验证: 需求 1.5**
    
    删除客户后，该客户的所有相关数据应该被完全删除
    """
    with temp_db_context() as temp_db:
        # 创建客户
        license_gen = LicenseGenerator()
        customer_id = license_gen.generate_customer_id()
        license_key = license_gen.generate_license_key()
        
        customer_data = {
            'customer_id': customer_id,
            'name': name,
            'email': email,
            'company': None,
            'license_key': license_key,
            'billing_mode': 'per_sample',
            'unit_price': 10.0,
            'subscription_fee': 0.0,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d'),
            'status': 'active',
            'notes': None
        }
        
        temp_db.create_customer(customer_data)
        
        # 添加一些使用记录
        usage_data = {
            'customer_id': customer_id,
            'license_key': license_key,
            'machine_id': 'test-machine',
            'report_date': datetime.now().isoformat(),
            'period_start': datetime.now().isoformat(),
            'period_end': datetime.now().isoformat(),
            'total_samples_loaded': 10,
            'total_exports': 5,
            'total_splits': 3,
            'unique_samples': 8,
            'imported_at': datetime.now().isoformat(),
            'report_file': 'test.enc'
        }
        temp_db.add_usage_record(usage_data)
        
        # 验证客户存在
        assert temp_db.get_customer(customer_id) is not None
        
        # 删除客户
        result = temp_db.delete_customer(customer_id)
        assert result is True
        
        # 验证客户已删除
        assert temp_db.get_customer(customer_id) is None
        
        # 验证使用记录也被删除
        usage_records = temp_db.fetchall(
            "SELECT * FROM usage_records WHERE customer_id = ?",
            (customer_id,)
        )
        assert len(usage_records) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

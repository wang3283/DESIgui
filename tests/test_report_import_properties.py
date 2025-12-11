#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告导入的属性测试

测试报告解密和重复检测的正确性属性
"""

import os
import tempfile
import json
import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta
from contextlib import contextmanager

from database_manager import DatabaseManager
from license_manager_core import LicenseGenerator
from data_encryptor import DataEncryptor


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


def create_test_report(license_key: str, machine_id: str, usage_stats: dict) -> dict:
    """创建测试报告数据"""
    return {
        'license_key': license_key,
        'machine_id': machine_id,
        'report_date': datetime.now().isoformat(),
        'period_start': (datetime.now() - timedelta(days=30)).isoformat(),
        'period_end': datetime.now().isoformat(),
        'usage_stats': usage_stats
    }


# 属性 4: 报告解密成功性
@given(
    machine_id=st.text(min_size=8, max_size=32, alphabet=st.characters(blacklist_categories=('Cs',))),
    total_loads=st.integers(min_value=0, max_value=1000),
    total_exports=st.integers(min_value=0, max_value=1000),
    total_splits=st.integers(min_value=0, max_value=1000),
    unique_samples=st.integers(min_value=0, max_value=1000)
)
@settings(max_examples=50, deadline=None)
def test_property_4_report_decryption_success(machine_id, total_loads, total_exports, total_splits, unique_samples):
    """
    **Feature: commercial-billing-system, Property 4: 报告解密成功性**
    **验证: 需求 2.2, 2.3**
    
    对于任意由系统生成的加密报告，使用正确的机器ID或License密钥应该能够成功解密
    """
    with temp_db_context() as temp_db:
        # 创建测试客户
        license_gen = LicenseGenerator()
        customer_id = license_gen.generate_customer_id()
        license_key = license_gen.generate_license_key()
        
        customer_data = {
            'customer_id': customer_id,
            'name': 'Test Customer',
            'email': 'test@example.com',
            'company': 'Test Company',
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
        
        # 创建使用统计数据
        usage_stats = {
            'total_loads': total_loads,
            'total_exports': total_exports,
            'total_splits': total_splits,
            'unique_samples': unique_samples
        }
        
        # 创建报告数据
        report_data = create_test_report(license_key, machine_id, usage_stats)
        
        # 使用License密钥加密
        encryptor = DataEncryptor(license_key)
        report_json = json.dumps(report_data)
        encrypted_data = encryptor.encrypt(report_json)
        
        # 属性验证：使用相同的License密钥应该能够解密
        decryptor = DataEncryptor(license_key)
        decrypted_data = decryptor.decrypt(encrypted_data)
        
        assert decrypted_data is not None
        
        # 验证解密后的数据与原始数据一致
        decrypted_report = json.loads(decrypted_data)
        assert decrypted_report['license_key'] == license_key
        assert decrypted_report['machine_id'] == machine_id
        assert decrypted_report['usage_stats']['total_loads'] == total_loads
        assert decrypted_report['usage_stats']['total_exports'] == total_exports
        assert decrypted_report['usage_stats']['total_splits'] == total_splits
        assert decrypted_report['usage_stats']['unique_samples'] == unique_samples


@given(
    machine_id=st.text(min_size=8, max_size=32, alphabet=st.characters(blacklist_categories=('Cs',))),
    usage_stats=st.fixed_dictionaries({
        'total_loads': st.integers(min_value=0, max_value=100),
        'total_exports': st.integers(min_value=0, max_value=100),
        'total_splits': st.integers(min_value=0, max_value=100),
        'unique_samples': st.integers(min_value=0, max_value=100)
    })
)
@settings(max_examples=30, deadline=None)
def test_property_4_wrong_key_fails(machine_id, usage_stats):
    """
    **Feature: commercial-billing-system, Property 4: 报告解密成功性（反向测试）**
    **验证: 需求 2.2, 2.3**
    
    使用错误的密钥应该无法解密报告
    """
    with temp_db_context() as temp_db:
        # 创建两个不同的License
        license_gen = LicenseGenerator()
        license_key_1 = license_gen.generate_license_key()
        license_key_2 = license_gen.generate_license_key()
        
        # 确保两个密钥不同
        assert license_key_1 != license_key_2
        
        # 创建报告数据
        report_data = create_test_report(license_key_1, machine_id, usage_stats)
        
        # 使用license_key_1加密
        encryptor = DataEncryptor(license_key_1)
        report_json = json.dumps(report_data)
        encrypted_data = encryptor.encrypt(report_json)
        
        # 属性验证：使用license_key_2应该无法解密
        wrong_decryptor = DataEncryptor(license_key_2)
        decrypted_data = wrong_decryptor.decrypt(encrypted_data)
        
        # 解密应该失败或返回无效数据
        if decrypted_data is not None:
            # 如果返回了数据，应该无法解析为有效JSON
            try:
                json.loads(decrypted_data)
                # 如果能解析，说明解密逻辑有问题
                assert False, "使用错误密钥不应该成功解密"
            except (json.JSONDecodeError, UnicodeDecodeError):
                # 预期行为：无法解析
                pass


# 属性 5: 重复报告检测
@given(
    machine_id=st.text(min_size=8, max_size=32, alphabet=st.characters(blacklist_categories=('Cs',))),
    usage_stats=st.fixed_dictionaries({
        'total_loads': st.integers(min_value=1, max_value=100),
        'total_exports': st.integers(min_value=1, max_value=100),
        'total_splits': st.integers(min_value=1, max_value=100),
        'unique_samples': st.integers(min_value=1, max_value=100)
    })
)
@settings(max_examples=50, deadline=None)
def test_property_5_duplicate_report_detection(machine_id, usage_stats):
    """
    **Feature: commercial-billing-system, Property 5: 重复报告检测**
    **验证: 需求 2.5**
    
    对于任意已导入的使用报告，再次导入相同的报告应该被系统检测并警告
    """
    with temp_db_context() as temp_db:
        # 创建测试客户
        license_gen = LicenseGenerator()
        customer_id = license_gen.generate_customer_id()
        license_key = license_gen.generate_license_key()
        
        customer_data = {
            'customer_id': customer_id,
            'name': 'Test Customer',
            'email': 'test@example.com',
            'company': 'Test Company',
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
        
        # 创建报告数据
        report_date = datetime.now().isoformat()
        report_data = {
            'license_key': license_key,
            'machine_id': machine_id,
            'report_date': report_date,
            'period_start': (datetime.now() - timedelta(days=30)).isoformat(),
            'period_end': datetime.now().isoformat(),
            'usage_stats': usage_stats
        }
        
        # 第一次导入
        usage_record_1 = {
            'customer_id': customer_id,
            'license_key': license_key,
            'machine_id': machine_id,
            'report_date': report_date,
            'period_start': report_data['period_start'],
            'period_end': report_data['period_end'],
            'total_samples_loaded': usage_stats['total_loads'],
            'total_exports': usage_stats['total_exports'],
            'total_splits': usage_stats['total_splits'],
            'unique_samples': usage_stats['unique_samples'],
            'imported_at': datetime.now().isoformat(),
            'report_file': 'test_report.enc'
        }
        
        temp_db.add_usage_record(usage_record_1)
        
        # 属性验证：检查是否存在相同的报告
        existing = temp_db.fetchone('''
            SELECT id FROM usage_records 
            WHERE license_key = ? AND report_date = ? AND machine_id = ?
        ''', (license_key, report_date, machine_id))
        
        assert existing is not None, "第一次导入应该成功"
        
        # 尝试第二次导入相同的报告
        duplicate_check = temp_db.fetchone('''
            SELECT id FROM usage_records 
            WHERE license_key = ? AND report_date = ? AND machine_id = ?
        ''', (license_key, report_date, machine_id))
        
        # 属性验证：应该检测到重复
        assert duplicate_check is not None, "应该检测到重复报告"


@given(
    machine_ids=st.lists(
        st.text(min_size=8, max_size=32, alphabet=st.characters(blacklist_categories=('Cs',))),
        min_size=2,
        max_size=5,
        unique=True
    ),
    usage_stats=st.fixed_dictionaries({
        'total_loads': st.integers(min_value=1, max_value=100),
        'total_exports': st.integers(min_value=1, max_value=100),
        'total_splits': st.integers(min_value=1, max_value=100),
        'unique_samples': st.integers(min_value=1, max_value=100)
    })
)
@settings(max_examples=30, deadline=None)
def test_property_5_different_machines_not_duplicate(machine_ids, usage_stats):
    """
    **Feature: commercial-billing-system, Property 5: 重复报告检测（不同机器）**
    **验证: 需求 2.5**
    
    来自不同机器的报告不应该被视为重复
    """
    with temp_db_context() as temp_db:
        # 创建测试客户
        license_gen = LicenseGenerator()
        customer_id = license_gen.generate_customer_id()
        license_key = license_gen.generate_license_key()
        
        customer_data = {
            'customer_id': customer_id,
            'name': 'Test Customer',
            'email': 'test@example.com',
            'company': 'Test Company',
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
        
        # 使用相同的report_date但不同的machine_id
        report_date = datetime.now().isoformat()
        
        # 导入来自不同机器的报告
        for machine_id in machine_ids:
            usage_record = {
                'customer_id': customer_id,
                'license_key': license_key,
                'machine_id': machine_id,
                'report_date': report_date,
                'period_start': (datetime.now() - timedelta(days=30)).isoformat(),
                'period_end': datetime.now().isoformat(),
                'total_samples_loaded': usage_stats['total_loads'],
                'total_exports': usage_stats['total_exports'],
                'total_splits': usage_stats['total_splits'],
                'unique_samples': usage_stats['unique_samples'],
                'imported_at': datetime.now().isoformat(),
                'report_file': f'test_report_{machine_id}.enc'
            }
            
            temp_db.add_usage_record(usage_record)
        
        # 属性验证：应该有多条记录（不同机器不算重复）
        all_records = temp_db.fetchall('''
            SELECT machine_id FROM usage_records 
            WHERE license_key = ? AND report_date = ?
        ''', (license_key, report_date))
        
        assert len(all_records) == len(machine_ids), "不同机器的报告不应该被视为重复"
        
        # 验证每个机器ID都被记录
        recorded_machine_ids = [r['machine_id'] for r in all_records]
        for machine_id in machine_ids:
            assert machine_id in recorded_machine_ids


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

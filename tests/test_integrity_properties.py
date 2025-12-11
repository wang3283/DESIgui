#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整性验证系统的属性测试
使用Hypothesis进行基于属性的测试
"""

import pytest
import sqlite3
import tempfile
import os
import hashlib
from datetime import datetime
from hypothesis import given, strategies as st, settings
from hypothesis import assume

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrity_verifier import IntegrityVerifier, IntegrityCheckResult


# 测试策略
record_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=48),
    min_size=5,
    max_size=20
)

sample_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=48),
    min_size=3,
    max_size=30
)

action_type_strategy = st.sampled_from([
    'load_sample', 'export_data', 'split_metabolites'
])


def create_test_database():
    """创建测试数据库"""
    test_db = tempfile.mktemp(suffix='.db')
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE usage_records (
            id INTEGER PRIMARY KEY,
            record_id TEXT UNIQUE,
            timestamp TEXT,
            action_type TEXT,
            sample_name TEXT,
            sample_hash TEXT,
            checksum TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    
    return test_db


def insert_record(db_path: str, record_data: dict, checksum: str):
    """插入记录到数据库"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO usage_records 
            (record_id, timestamp, action_type, sample_name, sample_hash, checksum)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            record_data['record_id'],
            record_data['timestamp'],
            record_data['action_type'],
            record_data['sample_name'],
            record_data['sample_hash'],
            checksum
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        # 重复的record_id，跳过
        pass
    finally:
        conn.close()


# ==================== 属性测试 ====================

@given(
    st.lists(
        st.tuples(record_id_strategy, sample_name_strategy, action_type_strategy),
        min_size=1,
        max_size=50,
        unique_by=lambda x: x[0]  # 确保record_id唯一
    )
)
@settings(max_examples=50, deadline=None)
def test_property_17_integrity_verification_completeness(records_data):
    """
    **Feature: commercial-billing-system, Property 17: 完整性验证全面性**
    对于任意导入的使用报告，系统应该验证所有记录的完整性，检测任何篡改
    **验证: 需求 6.2**
    """
    # 创建测试数据库
    test_db = create_test_database()
    
    try:
        machine_id = "test_machine_12345"
        secret_seed = b"TEST_SECRET_KEY"
        verifier = IntegrityVerifier(test_db, machine_id, secret_seed)
        
        # 插入所有记录（使用正确的校验和）
        for record_id, sample_name, action_type in records_data:
            record_data = {
                'record_id': record_id,
                'timestamp': datetime.now().isoformat(),
                'action_type': action_type,
                'sample_name': sample_name,
                'sample_hash': hashlib.md5(sample_name.encode()).hexdigest()
            }
            
            # 计算正确的校验和
            checksum = verifier.calculate_checksum(record_data)
            insert_record(test_db, record_data, checksum)
        
        # 执行完整性验证
        result = verifier.verify_all_records(mark_suspicious=False)
        
        # 属性验证：所有记录都应该被验证
        assert result.total_records == len(set(r[0] for r in records_data))
        
        # 属性验证：所有记录都应该是有效的（因为使用了正确的校验和）
        assert result.valid_records == result.total_records
        assert result.invalid_records == 0
        assert result.integrity_ok is True
        assert len(result.suspicious_records) == 0
        
    finally:
        os.unlink(test_db)


@given(
    st.lists(
        st.tuples(record_id_strategy, sample_name_strategy, action_type_strategy),
        min_size=2,
        max_size=20,
        unique_by=lambda x: x[0]
    ),
    st.integers(min_value=0, max_value=10)  # 篡改记录的数量
)
@settings(max_examples=50, deadline=None)
def test_property_17_tampering_detection(records_data, tamper_count):
    """
    **Feature: commercial-billing-system, Property 17: 篡改检测准确性**
    对于任意包含篡改记录的数据集，系统应该准确检测出所有篡改
    **验证: 需求 6.2, 6.3**
    """
    assume(tamper_count <= len(records_data))
    
    test_db = create_test_database()
    
    try:
        machine_id = "test_machine_12345"
        secret_seed = b"TEST_SECRET_KEY"
        verifier = IntegrityVerifier(test_db, machine_id, secret_seed)
        
        # 插入记录
        tampered_indices = set(range(tamper_count))
        
        for idx, (record_id, sample_name, action_type) in enumerate(records_data):
            record_data = {
                'record_id': record_id,
                'timestamp': datetime.now().isoformat(),
                'action_type': action_type,
                'sample_name': sample_name,
                'sample_hash': hashlib.md5(sample_name.encode()).hexdigest()
            }
            
            if idx in tampered_indices:
                # 使用伪造的校验和（篡改）
                checksum = "0" * 64
            else:
                # 使用正确的校验和
                checksum = verifier.calculate_checksum(record_data)
            
            insert_record(test_db, record_data, checksum)
        
        # 执行完整性验证
        result = verifier.verify_all_records(mark_suspicious=True)
        
        # 属性验证：检测到的无效记录数应该等于篡改数
        assert result.invalid_records == tamper_count
        assert result.valid_records == result.total_records - tamper_count
        
        # 属性验证：完整性状态应该正确
        if tamper_count > 0:
            assert result.integrity_ok is False
            assert len(result.suspicious_records) == tamper_count
        else:
            assert result.integrity_ok is True
            assert len(result.suspicious_records) == 0
        
    finally:
        os.unlink(test_db)


@given(
    st.lists(
        st.tuples(record_id_strategy, sample_name_strategy, action_type_strategy),
        min_size=1,
        max_size=30,
        unique_by=lambda x: x[0]
    )
)
@settings(max_examples=50, deadline=None)
def test_property_16_checksum_existence(records_data):
    """
    **Feature: commercial-billing-system, Property 16: 校验和存在性**
    对于任意使用记录，系统应该计算并存储基于机器ID的校验和
    **验证: 需求 6.1**
    """
    test_db = create_test_database()
    
    try:
        machine_id = "test_machine_12345"
        secret_seed = b"TEST_SECRET_KEY"
        verifier = IntegrityVerifier(test_db, machine_id, secret_seed)
        
        # 插入记录
        for record_id, sample_name, action_type in records_data:
            record_data = {
                'record_id': record_id,
                'timestamp': datetime.now().isoformat(),
                'action_type': action_type,
                'sample_name': sample_name,
                'sample_hash': hashlib.md5(sample_name.encode()).hexdigest()
            }
            
            # 计算校验和
            checksum = verifier.calculate_checksum(record_data)
            
            # 属性验证：校验和应该存在且非空
            assert checksum is not None
            assert len(checksum) > 0
            assert len(checksum) == 64  # SHA256哈希长度
            
            # 属性验证：校验和应该是十六进制字符串
            assert all(c in '0123456789abcdef' for c in checksum)
            
            insert_record(test_db, record_data, checksum)
        
        # 验证数据库中的所有记录都有校验和
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM usage_records WHERE checksum IS NULL OR checksum = ''")
        null_count = cursor.fetchone()[0]
        conn.close()
        
        # 属性验证：没有记录的校验和为空
        assert null_count == 0
        
    finally:
        os.unlink(test_db)


@given(
    st.tuples(record_id_strategy, sample_name_strategy, action_type_strategy),
    st.text(min_size=10, max_size=50)  # 不同的机器ID
)
@settings(max_examples=50, deadline=None)
def test_checksum_machine_id_dependency(record_data, machine_id):
    """
    **Feature: commercial-billing-system, 校验和机器ID依赖性**
    对于相同的记录数据，不同的机器ID应该产生不同的校验和
    **验证: 需求 6.1**
    """
    record_id, sample_name, action_type = record_data
    
    record_dict = {
        'record_id': record_id,
        'timestamp': datetime.now().isoformat(),
        'action_type': action_type,
        'sample_name': sample_name,
        'sample_hash': hashlib.md5(sample_name.encode()).hexdigest()
    }
    
    secret_seed = b"TEST_SECRET_KEY"
    
    # 使用第一个机器ID计算校验和
    verifier1 = IntegrityVerifier(":memory:", machine_id, secret_seed)
    checksum1 = verifier1.calculate_checksum(record_dict)
    
    # 使用不同的机器ID计算校验和
    different_machine_id = machine_id + "_different"
    verifier2 = IntegrityVerifier(":memory:", different_machine_id, secret_seed)
    checksum2 = verifier2.calculate_checksum(record_dict)
    
    # 属性验证：不同机器ID应该产生不同的校验和
    assert checksum1 != checksum2


@given(
    st.lists(
        st.tuples(record_id_strategy, sample_name_strategy, action_type_strategy),
        min_size=5,
        max_size=20,
        unique_by=lambda x: x[0]
    )
)
@settings(max_examples=50, deadline=None)
def test_integrity_report_generation(records_data):
    """
    **Feature: commercial-billing-system, 完整性报告生成**
    对于任意数据集，系统应该能够生成完整的完整性报告
    **验证: 需求 6.5**
    """
    test_db = create_test_database()
    
    try:
        machine_id = "test_machine_12345"
        secret_seed = b"TEST_SECRET_KEY"
        verifier = IntegrityVerifier(test_db, machine_id, secret_seed)
        
        # 插入记录
        for record_id, sample_name, action_type in records_data:
            record_data = {
                'record_id': record_id,
                'timestamp': datetime.now().isoformat(),
                'action_type': action_type,
                'sample_name': sample_name,
                'sample_hash': hashlib.md5(sample_name.encode()).hexdigest()
            }
            checksum = verifier.calculate_checksum(record_data)
            insert_record(test_db, record_data, checksum)
        
        # 生成报告
        report = verifier.generate_integrity_report()
        
        # 属性验证：报告应该包含所有必要字段
        assert 'report_generated' in report
        assert 'machine_id' in report
        assert 'current_check' in report
        assert 'suspicious_records' in report
        assert 'check_history' in report
        assert 'summary' in report
        
        # 属性验证：摘要应该包含正确的统计信息
        summary = report['summary']
        assert 'total_records' in summary
        assert 'valid_records' in summary
        assert 'invalid_records' in summary
        assert 'integrity_rate' in summary
        
        # 属性验证：完整性率应该在0-100之间
        assert 0 <= summary['integrity_rate'] <= 100
        
        # 属性验证：统计数字应该一致
        assert summary['total_records'] == summary['valid_records'] + summary['invalid_records']
        
    finally:
        os.unlink(test_db)


@given(
    st.lists(
        st.tuples(record_id_strategy, sample_name_strategy, action_type_strategy),
        min_size=1,
        max_size=15,
        unique_by=lambda x: x[0]
    )
)
@settings(max_examples=50, deadline=None)
def test_suspicious_record_marking(records_data):
    """
    **Feature: commercial-billing-system, 可疑记录标记功能**
    对于检测到的篡改记录，系统应该能够正确标记并提供清除功能
    **验证: 需求 6.3**
    """
    test_db = create_test_database()
    
    try:
        machine_id = "test_machine_12345"
        secret_seed = b"TEST_SECRET_KEY"
        verifier = IntegrityVerifier(test_db, machine_id, secret_seed)
        
        # 插入一些有效记录和一些篡改记录
        tampered_ids = []
        
        for idx, (record_id, sample_name, action_type) in enumerate(records_data):
            record_data = {
                'record_id': record_id,
                'timestamp': datetime.now().isoformat(),
                'action_type': action_type,
                'sample_name': sample_name,
                'sample_hash': hashlib.md5(sample_name.encode()).hexdigest()
            }
            
            if idx % 3 == 0:  # 每3条记录篡改1条
                checksum = "0" * 64
                tampered_ids.append(record_id)
            else:
                checksum = verifier.calculate_checksum(record_data)
            
            insert_record(test_db, record_data, checksum)
        
        # 执行验证并标记
        result = verifier.verify_all_records(mark_suspicious=True)
        
        # 属性验证：可疑记录应该被正确标记
        suspicious = verifier.get_suspicious_records()
        assert len(suspicious) == len(tampered_ids)
        
        # 属性验证：清除标记功能应该工作
        if tampered_ids:
            first_tampered = tampered_ids[0]
            cleared = verifier.clear_suspicious_flag(first_tampered)
            assert cleared is True
            
            # 再次获取可疑记录，应该少一条
            suspicious_after = verifier.get_suspicious_records()
            assert len(suspicious_after) == len(tampered_ids) - 1
        
    finally:
        os.unlink(test_db)


@given(
    st.lists(
        st.tuples(record_id_strategy, sample_name_strategy, action_type_strategy),
        min_size=1,
        max_size=20,
        unique_by=lambda x: x[0]
    )
)
@settings(max_examples=50, deadline=None)
def test_overall_checksum_consistency(records_data):
    """
    **Feature: commercial-billing-system, 整体校验和一致性**
    对于相同的记录集，多次计算的整体校验和应该一致
    **验证: 需求 6.1**
    """
    test_db = create_test_database()
    
    try:
        machine_id = "test_machine_12345"
        secret_seed = b"TEST_SECRET_KEY"
        verifier = IntegrityVerifier(test_db, machine_id, secret_seed)
        
        # 插入记录
        for record_id, sample_name, action_type in records_data:
            record_data = {
                'record_id': record_id,
                'timestamp': datetime.now().isoformat(),
                'action_type': action_type,
                'sample_name': sample_name,
                'sample_hash': hashlib.md5(sample_name.encode()).hexdigest()
            }
            checksum = verifier.calculate_checksum(record_data)
            insert_record(test_db, record_data, checksum)
        
        # 第一次验证
        result1 = verifier.verify_all_records(mark_suspicious=False)
        checksum1 = result1.overall_checksum
        
        # 第二次验证（不修改数据）
        result2 = verifier.verify_all_records(mark_suspicious=False)
        checksum2 = result2.overall_checksum
        
        # 属性验证：整体校验和应该一致
        assert checksum1 == checksum2
        
    finally:
        os.unlink(test_db)


# ==================== 单元测试 ====================

def test_empty_database():
    """测试空数据库的完整性验证"""
    test_db = create_test_database()
    
    try:
        verifier = IntegrityVerifier(test_db, "test_machine", b"SECRET")
        result = verifier.verify_all_records()
        
        assert result.total_records == 0
        assert result.valid_records == 0
        assert result.invalid_records == 0
        assert result.integrity_ok is True
        
    finally:
        os.unlink(test_db)


def test_report_export():
    """测试报告导出功能"""
    test_db = create_test_database()
    report_file = tempfile.mktemp(suffix='.json')
    
    try:
        verifier = IntegrityVerifier(test_db, "test_machine", b"SECRET")
        
        # 插入一条测试记录
        record_data = {
            'record_id': 'TEST-001',
            'timestamp': datetime.now().isoformat(),
            'action_type': 'load_sample',
            'sample_name': 'test_sample',
            'sample_hash': hashlib.md5(b'test_sample').hexdigest()
        }
        checksum = verifier.calculate_checksum(record_data)
        insert_record(test_db, record_data, checksum)
        
        # 生成并导出报告
        report = verifier.generate_integrity_report(report_file)
        
        assert os.path.exists(report_file)
        assert report['summary']['total_records'] == 1
        
    finally:
        os.unlink(test_db)
        if os.path.exists(report_file):
            os.unlink(report_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据加密模块属性测试
使用Property-Based Testing验证加密解密的正确性
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from hypothesis import given, strategies as st, settings
from data_encryptor import DataEncryptor, MultiKeyDecryptor


class TestDataEncryptorProperties:
    """数据加密器属性测试"""
    
    @given(st.text(min_size=1, max_size=1000))
    @settings(max_examples=100)
    def test_encryption_roundtrip_property(self, original_data):
        """
        **Feature: commercial-billing-system, Property 11: 报告导出加密性（Round-trip）**
        **验证: 需求 4.4, 6.4**
        
        对于任意字符串数据，加密后再解密应该得到原始数据
        """
        encryptor = DataEncryptor(machine_id="test-machine-123")
        
        # 加密
        encrypted = encryptor.encrypt(original_data)
        
        # 解密
        decrypted = encryptor.decrypt(encrypted)
        
        # 验证round-trip
        assert decrypted == original_data, f"Round-trip失败: {original_data[:50]}"
    
    @given(st.dictionaries(
        st.text(min_size=1, max_size=50),
        st.one_of(
            st.text(max_size=100),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans()
        ),
        min_size=1,
        max_size=20
    ))
    @settings(max_examples=100)
    def test_integrity_verification_property(self, test_data):
        """
        **Feature: commercial-billing-system, Property 11: 报告导出加密性**
        **验证: 需求 4.4, 6.4**
        
        对于任意数据字典，加密后解密应该保持数据完整性
        """
        encryptor = DataEncryptor(machine_id="test-machine-456")
        
        # 加密并添加完整性校验
        encrypted = encryptor.encrypt_with_integrity(test_data)
        
        # 解密并验证完整性
        decrypted = encryptor.decrypt_and_verify(encrypted)
        
        # 验证数据一致性
        assert decrypted == test_data, f"完整性验证失败"
    
    @given(
        st.text(min_size=10, max_size=50),  # machine_id
        st.dictionaries(
            st.text(min_size=1, max_size=30),
            st.integers(min_value=0, max_value=10000),
            min_size=1,
            max_size=10
        )  # data
    )
    @settings(max_examples=100)
    def test_different_machine_ids_property(self, machine_id, test_data):
        """
        **Feature: commercial-billing-system, Property 11: 报告导出加密性**
        **验证: 需求 2.2, 6.4**
        
        对于任意机器ID和数据，使用该机器ID加密的数据应该能被相同机器ID解密
        """
        encryptor = DataEncryptor(machine_id=machine_id)
        
        # 加密
        encrypted = encryptor.encrypt_with_integrity(test_data)
        
        # 使用相同机器ID解密
        decrypted = encryptor.decrypt_and_verify(encrypted)
        
        assert decrypted == test_data, f"机器ID {machine_id[:10]}... 解密失败"
    
    @given(
        st.lists(st.text(min_size=10, max_size=30), min_size=2, max_size=10, unique=True),
        st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.text(max_size=50),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=50)
    def test_multi_key_decryption_property(self, machine_ids, test_data):
        """
        **Feature: commercial-billing-system, Property 4: 报告解密成功性**
        **验证: 需求 2.2, 2.3**
        
        对于任意机器ID列表，使用其中任一ID加密的数据应该能被多密钥解密器解密
        """
        # 使用第一个机器ID加密
        encryptor = DataEncryptor(machine_id=machine_ids[0])
        encrypted = encryptor.encrypt_with_integrity(test_data)
        
        # 使用多密钥解密器（包含所有机器ID）
        multi_decryptor = MultiKeyDecryptor(known_machine_ids=machine_ids)
        decrypted = multi_decryptor.decrypt(encrypted)
        
        assert decrypted == test_data, "多密钥解密失败"
    
    @given(st.dictionaries(
        st.text(min_size=1, max_size=30),
        st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
        min_size=1,
        max_size=10
    ))
    @settings(max_examples=100)
    def test_checksum_consistency_property(self, test_data):
        """
        **Feature: commercial-billing-system, Property 16: 校验和存在性**
        **验证: 需求 6.1**
        
        对于任意数据，多次计算校验和应该得到相同结果
        """
        encryptor = DataEncryptor(machine_id="test-machine")
        
        # 多次计算校验和
        checksum1 = encryptor.calculate_checksum(test_data)
        checksum2 = encryptor.calculate_checksum(test_data)
        checksum3 = encryptor.calculate_checksum(test_data)
        
        # 验证一致性
        assert checksum1 == checksum2 == checksum3, "校验和不一致"
    
    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.integers(),
            min_size=1,
            max_size=5
        ),
        st.text(min_size=1, max_size=10)  # 修改的key
    )
    @settings(max_examples=50)
    def test_checksum_detects_tampering_property(self, test_data, tamper_key):
        """
        **Feature: commercial-billing-system, Property 17: 完整性验证全面性**
        **验证: 需求 6.2**
        
        对于任意数据，修改数据后校验和应该不同（检测篡改）
        """
        encryptor = DataEncryptor(machine_id="test-machine")
        
        # 计算原始校验和
        original_checksum = encryptor.calculate_checksum(test_data)
        
        # 篡改数据
        tampered_data = test_data.copy()
        if tamper_key in tampered_data:
            # 修改现有key的值
            if isinstance(tampered_data[tamper_key], int):
                tampered_data[tamper_key] += 1
            else:
                tampered_data[tamper_key] = "tampered"
        else:
            # 添加新key
            tampered_data[tamper_key] = "new_value"
        
        # 计算篡改后的校验和
        tampered_checksum = encryptor.calculate_checksum(tampered_data)
        
        # 验证校验和不同
        assert original_checksum != tampered_checksum, "校验和未检测到篡改"


# 运行测试
if __name__ == "__main__":
    import pytest
    
    print("=" * 60)
    print("运行加密模块属性测试")
    print("=" * 60)
    
    # 运行pytest
    pytest.main([__file__, "-v", "--tb=short"])

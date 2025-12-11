#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据加密解密模块
支持多种解密策略和完整性验证
"""

import base64
import hashlib
import json
from typing import Optional, List, Dict, Any

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    print("[警告] 未安装cryptography库，使用基础加密")


class DataEncryptor:
    """数据加密解密器"""
    
    SECRET_SEED = b"DESI_METABOLOMICS_2025_SECRET_KEY"
    
    def __init__(self, machine_id: str = None, license_key: str = None):
        """
        初始化加密器
        
        参数:
            machine_id: 机器ID（用于生成加密密钥）
            license_key: 许可证密钥（备用加密方式）
        """
        self.machine_id = machine_id
        self.license_key = license_key
        self.ciphers = []
        
        # 初始化多个加密器
        if HAS_CRYPTO:
            if machine_id:
                self.ciphers.append(('machine_id', self._create_cipher(machine_id)))
            if license_key:
                self.ciphers.append(('license', self._create_cipher(license_key)))
    
    def _create_cipher(self, seed: str) -> Optional[Fernet]:
        """创建Fernet加密器"""
        if not HAS_CRYPTO:
            return None
        
        try:
            # 使用种子生成加密密钥
            salt = seed[:16].encode() if len(seed) >= 16 else (seed * 16)[:16].encode()
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.SECRET_SEED))
            return Fernet(key)
        except Exception as e:
            print(f"[警告] 创建加密器失败: {e}")
            return None
    
    def encrypt(self, data: str) -> str:
        """
        加密数据
        
        参数:
            data: 要加密的字符串
        
        返回:
            加密后的字符串
        """
        if self.ciphers and self.ciphers[0][1]:
            # 使用第一个可用的加密器
            cipher = self.ciphers[0][1]
            try:
                return cipher.encrypt(data.encode()).decode()
            except Exception as e:
                print(f"[警告] Fernet加密失败: {e}")
        
        # 回退到base64编码
        return base64.b64encode(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> Optional[str]:
        """
        解密数据（尝试多种方法）
        
        参数:
            encrypted_data: 加密的字符串
        
        返回:
            解密后的字符串，失败返回None
        """
        # 方法1: 尝试所有已配置的加密器
        for name, cipher in self.ciphers:
            if cipher:
                try:
                    decrypted = cipher.decrypt(encrypted_data.encode()).decode()
                    return decrypted
                except Exception:
                    continue
        
        # 方法2: 尝试base64解码
        try:
            decoded = base64.b64decode(encrypted_data.encode()).decode()
            return decoded
        except Exception:
            pass
        
        return None
    
    def try_decrypt_with_keys(self, encrypted_data: str, 
                             machine_ids: List[str] = None,
                             license_keys: List[str] = None) -> Optional[str]:
        """
        尝试使用多个密钥解密
        
        参数:
            encrypted_data: 加密的数据
            machine_ids: 机器ID列表
            license_keys: 许可证密钥列表
        
        返回:
            解密后的数据，失败返回None
        """
        # 尝试机器ID
        if machine_ids:
            for mid in machine_ids:
                cipher = self._create_cipher(mid)
                if cipher:
                    try:
                        return cipher.decrypt(encrypted_data.encode()).decode()
                    except:
                        continue
        
        # 尝试许可证密钥
        if license_keys:
            for lic in license_keys:
                cipher = self._create_cipher(lic)
                if cipher:
                    try:
                        return cipher.decrypt(encrypted_data.encode()).decode()
                    except:
                        continue
        
        # 尝试base64
        try:
            return base64.b64decode(encrypted_data.encode()).decode()
        except:
            return None
    
    def calculate_checksum(self, data: Dict[str, Any]) -> str:
        """
        计算数据校验和
        
        参数:
            data: 要计算校验和的数据字典
        
        返回:
            SHA256校验和
        """
        # 将数据转为JSON并排序
        data_str = json.dumps(data, sort_keys=True)
        
        # 添加机器ID和密钥种子
        combined = f"{data_str}|{self.machine_id or ''}|{self.SECRET_SEED.decode()}"
        
        # 计算SHA256
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def verify_checksum(self, data: Dict[str, Any], expected_checksum: str) -> bool:
        """
        验证校验和
        
        参数:
            data: 数据字典
            expected_checksum: 期望的校验和
        
        返回:
            是否匹配
        """
        actual_checksum = self.calculate_checksum(data)
        return actual_checksum == expected_checksum
    
    def encrypt_with_integrity(self, data: Dict[str, Any]) -> str:
        """
        加密数据并添加完整性校验
        
        参数:
            data: 要加密的数据字典
        
        返回:
            加密后的字符串
        """
        # 计算校验和
        checksum = self.calculate_checksum(data)
        
        # 添加校验和到数据
        data_with_checksum = {
            'data': data,
            'checksum': checksum
        }
        
        # 加密
        json_str = json.dumps(data_with_checksum, ensure_ascii=False)
        return self.encrypt(json_str)
    
    def decrypt_and_verify(self, encrypted_data: str) -> Optional[Dict[str, Any]]:
        """
        解密数据并验证完整性
        
        参数:
            encrypted_data: 加密的数据
        
        返回:
            解密后的数据字典，验证失败返回None
        """
        # 解密
        decrypted = self.decrypt(encrypted_data)
        if not decrypted:
            return None
        
        try:
            # 解析JSON
            data_with_checksum = json.loads(decrypted)
            
            # 提取数据和校验和
            data = data_with_checksum.get('data')
            expected_checksum = data_with_checksum.get('checksum')
            
            if not data or not expected_checksum:
                return None
            
            # 验证校验和
            if self.verify_checksum(data, expected_checksum):
                return data
            else:
                print("[警告] 校验和验证失败，数据可能被篡改")
                return None
        
        except json.JSONDecodeError:
            print("[警告] JSON解析失败")
            return None


class MultiKeyDecryptor:
    """多密钥解密器 - 用于管理员导入报告"""
    
    def __init__(self, known_machine_ids: List[str] = None, 
                 known_license_keys: List[str] = None):
        """
        初始化多密钥解密器
        
        参数:
            known_machine_ids: 已知的机器ID列表
            known_license_keys: 已知的许可证密钥列表
        """
        self.known_machine_ids = known_machine_ids or []
        self.known_license_keys = known_license_keys or []
    
    def decrypt(self, encrypted_data: str) -> Optional[Dict[str, Any]]:
        """
        尝试使用所有已知密钥解密
        
        参数:
            encrypted_data: 加密的数据
        
        返回:
            解密后的数据，失败返回None
        """
        # 尝试所有机器ID
        for machine_id in self.known_machine_ids:
            encryptor = DataEncryptor(machine_id=machine_id)
            result = encryptor.decrypt_and_verify(encrypted_data)
            if result:
                return result
        
        # 尝试所有许可证密钥
        for license_key in self.known_license_keys:
            encryptor = DataEncryptor(license_key=license_key)
            result = encryptor.decrypt_and_verify(encrypted_data)
            if result:
                return result
        
        # 尝试base64解码
        try:
            decoded = base64.b64decode(encrypted_data.encode()).decode()
            data = json.loads(decoded)
            return data.get('data') if isinstance(data, dict) and 'data' in data else data
        except:
            pass
        
        return None
    
    def add_known_key(self, key: str, key_type: str = 'machine_id'):
        """
        添加已知密钥
        
        参数:
            key: 密钥值
            key_type: 'machine_id' 或 'license'
        """
        if key_type == 'machine_id':
            if key not in self.known_machine_ids:
                self.known_machine_ids.append(key)
        elif key_type == 'license':
            if key not in self.known_license_keys:
                self.known_license_keys.append(key)


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("数据加密解密模块测试")
    print("=" * 60)
    
    # 测试基本加密解密
    print("\n[NOTE] 测试基本加密解密...")
    encryptor = DataEncryptor(machine_id="test-machine-123")
    
    original_data = "这是测试数据"
    encrypted = encryptor.encrypt(original_data)
    print(f"原始数据: {original_data}")
    print(f"加密后: {encrypted[:50]}...")
    
    decrypted = encryptor.decrypt(encrypted)
    print(f"解密后: {decrypted}")
    assert decrypted == original_data, "解密失败"
    print("[成功] 基本加密解密测试通过")
    
    # 测试完整性验证
    print("\n[NOTE] 测试完整性验证...")
    test_data = {
        'name': '测试',
        'value': 123,
        'list': [1, 2, 3]
    }
    
    encrypted_with_integrity = encryptor.encrypt_with_integrity(test_data)
    print(f"加密数据: {encrypted_with_integrity[:50]}...")
    
    decrypted_data = encryptor.decrypt_and_verify(encrypted_with_integrity)
    print(f"解密数据: {decrypted_data}")
    assert decrypted_data == test_data, "完整性验证失败"
    print("[成功] 完整性验证测试通过")
    
    # 测试多密钥解密
    print("\n[NOTE] 测试多密钥解密...")
    encryptor1 = DataEncryptor(machine_id="machine-001")
    encrypted1 = encryptor1.encrypt_with_integrity({'test': 'data1'})
    
    encryptor2 = DataEncryptor(machine_id="machine-002")
    encrypted2 = encryptor2.encrypt_with_integrity({'test': 'data2'})
    
    # 使用多密钥解密器
    multi_decryptor = MultiKeyDecryptor(
        known_machine_ids=["machine-001", "machine-002", "machine-003"]
    )
    
    result1 = multi_decryptor.decrypt(encrypted1)
    result2 = multi_decryptor.decrypt(encrypted2)
    
    print(f"解密结果1: {result1}")
    print(f"解密结果2: {result2}")
    assert result1 == {'test': 'data1'}, "多密钥解密1失败"
    assert result2 == {'test': 'data2'}, "多密钥解密2失败"
    print("[成功] 多密钥解密测试通过")
    
    print("\n[成功] 所有测试通过")

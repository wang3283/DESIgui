#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
License生成和验证核心模块
"""

import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional


class LicenseGenerator:
    """License生成器"""
    
    @staticmethod
    def generate_customer_id() -> str:
        """
        生成唯一的客户ID
        
        返回:
            格式: CUST-XXXXXXXX (8位十六进制)
        """
        return f"CUST-{uuid.uuid4().hex[:8].upper()}"
    
    @staticmethod
    def generate_license_key() -> str:
        """
        生成唯一的许可证密钥
        
        返回:
            格式: DESI-XXXXXXXX-YYYYYYYY (两组8位十六进制)
        """
        part1 = uuid.uuid4().hex[:8].upper()
        part2 = uuid.uuid4().hex[:8].upper()
        
        # 计算校验位
        checksum = LicenseGenerator._calculate_checksum(f"{part1}{part2}")
        
        return f"DESI-{part1}-{part2}-{checksum}"
    
    @staticmethod
    def _calculate_checksum(data: str) -> str:
        """
        计算校验位
        
        参数:
            data: 要计算校验位的数据
        
        返回:
            4位十六进制校验位
        """
        hash_obj = hashlib.md5(data.encode())
        return hash_obj.hexdigest()[:4].upper()
    
    @staticmethod
    def validate_license_format(license_key: str) -> bool:
        """
        验证License格式
        
        参数:
            license_key: 许可证密钥
        
        返回:
            是否格式正确
        """
        if not license_key:
            return False
        
        parts = license_key.split('-')
        
        # 检查格式: DESI-XXXXXXXX-YYYYYYYY-CCCC
        if len(parts) != 4:
            return False
        
        if parts[0] != 'DESI':
            return False
        
        if len(parts[1]) != 8 or len(parts[2]) != 8:
            return False
        
        if len(parts[3]) != 4:
            return False
        
        # 验证校验位
        expected_checksum = LicenseGenerator._calculate_checksum(f"{parts[1]}{parts[2]}")
        return parts[3] == expected_checksum
    
    @staticmethod
    def create_customer_data(name: str, email: str, company: str = "",
                           expires_days: int = 365) -> Dict:
        """
        创建完整的客户数据
        
        参数:
            name: 客户名称
            email: 邮箱
            company: 公司名称
            expires_days: 有效期天数
        
        返回:
            客户数据字典
        """
        customer_id = LicenseGenerator.generate_customer_id()
        license_key = LicenseGenerator.generate_license_key()
        created_at = datetime.now()
        expires_at = created_at + timedelta(days=expires_days)
        
        return {
            'customer_id': customer_id,
            'name': name,
            'email': email,
            'company': company,
            'license_key': license_key,
            'created_at': created_at.isoformat(),
            'expires_at': expires_at.isoformat(),
            'status': 'active'
        }


class LicenseValidator:
    """License验证器"""
    
    @staticmethod
    def validate(license_key: str, expires_at: str = None) -> Dict:
        """
        验证License
        
        参数:
            license_key: 许可证密钥
            expires_at: 到期时间（ISO格式字符串）
        
        返回:
            验证结果字典
        """
        result = {
            'valid': False,
            'format_valid': False,
            'expired': False,
            'days_left': None,
            'message': ''
        }
        
        # 验证格式
        if not LicenseGenerator.validate_license_format(license_key):
            result['message'] = 'License格式无效'
            return result
        
        result['format_valid'] = True
        
        # 验证到期时间
        if expires_at:
            try:
                expires_dt = datetime.fromisoformat(expires_at)
                now = datetime.now()
                
                if expires_dt < now:
                    result['expired'] = True
                    result['message'] = '许可证已过期'
                    return result
                
                # 计算剩余天数
                days_left = (expires_dt - now).days
                result['days_left'] = days_left
                result['valid'] = True
                result['message'] = f'License有效，剩余{days_left}天'
                
            except ValueError:
                result['message'] = '到期时间格式错误'
                return result
        else:
            # 没有到期时间，只验证格式
            result['valid'] = True
            result['message'] = 'License格式有效'
        
        return result
    
    @staticmethod
    def check_expiry(expires_at: str) -> int:
        """
        检查到期时间
        
        参数:
            expires_at: 到期时间（ISO格式字符串）
        
        返回:
            剩余天数，已过期返回负数
        """
        try:
            expires_dt = datetime.fromisoformat(expires_at)
            now = datetime.now()
            return (expires_dt - now).days
        except ValueError:
            return -999  # 格式错误
    
    @staticmethod
    def should_show_reminder(days_left: int) -> Tuple[bool, str]:
        """
        判断是否显示提醒
        
        参数:
            days_left: 剩余天数
        
        返回:
            (是否显示, 提醒级别)
            提醒级别: 'expired', 'urgent', 'warning', 'info', 'none'
        """
        if days_left < 0:
            return (True, 'expired')
        elif days_left <= 7:
            return (True, 'urgent')
        elif days_left <= 30:
            return (True, 'warning')
        elif days_left <= 60:
            return (True, 'info')
        else:
            return (False, 'none')
    
    @staticmethod
    def get_reminder_message(days_left: int, customer_name: str = "客户") -> str:
        """
        获取提醒消息
        
        参数:
            days_left: 剩余天数
            customer_name: 客户名称
        
        返回:
            提醒消息
        """
        show, level = LicenseValidator.should_show_reminder(days_left)
        
        if not show:
            return ""
        
        if level == 'expired':
            return f"[警告] {customer_name}的许可证已过期！请联系管理员续费。"
        elif level == 'urgent':
            return f"[紧急] {customer_name}的License将在{days_left}天后过期！请尽快续费。"
        elif level == 'warning':
            return f"[提醒] {customer_name}的License将在{days_left}天后过期，请及时续费。"
        elif level == 'info':
            return f"[信息] {customer_name}的License将在{days_left}天后过期。"
        
        return ""
    
    @staticmethod
    def should_restrict_features(days_left: int) -> bool:
        """
        判断是否应该限制功能
        
        参数:
            days_left: 剩余天数
        
        返回:
            是否限制功能
        """
        return days_left < 0  # 只有过期后才限制


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("License生成和验证模块测试")
    print("=" * 60)
    
    # 测试License生成
    print("\n[NOTE] 测试License生成...")
    license_key = LicenseGenerator.generate_license_key()
    print(f"生成的License: {license_key}")
    
    # 验证格式
    is_valid = LicenseGenerator.validate_license_format(license_key)
    print(f"格式验证: {'[成功] 通过' if is_valid else '[错误] 失败'}")
    assert is_valid, "License格式验证失败"
    
    # 测试客户ID生成
    print("\n[NOTE] 测试客户ID生成...")
    customer_id = LicenseGenerator.generate_customer_id()
    print(f"生成的客户ID: {customer_id}")
    assert customer_id.startswith('CUST-'), "客户ID格式错误"
    
    # 测试唯一性
    print("\n[NOTE] 测试唯一性...")
    licenses = set()
    customer_ids = set()
    for _ in range(100):
        licenses.add(LicenseGenerator.generate_license_key())
        customer_ids.add(LicenseGenerator.generate_customer_id())
    
    print(f"生成100个License，唯一数量: {len(licenses)}")
    print(f"生成100个客户ID，唯一数量: {len(customer_ids)}")
    assert len(licenses) == 100, "License不唯一"
    assert len(customer_ids) == 100, "客户ID不唯一"
    
    # 测试创建客户数据
    print("\n[NOTE] 测试创建客户数据...")
    customer_data = LicenseGenerator.create_customer_data(
        name="测试客户",
        email="test@example.com",
        company="测试公司"
    )
    print(f"客户ID: {customer_data['customer_id']}")
    print(f"License: {customer_data['license_key']}")
    print(f"到期时间: {customer_data['expires_at'][:10]}")
    
    # 测试License验证
    print("\n[NOTE] 测试License验证...")
    result = LicenseValidator.validate(
        customer_data['license_key'],
        customer_data['expires_at']
    )
    print(f"验证结果: {result['message']}")
    print(f"剩余天数: {result['days_left']}")
    assert result['valid'], "License验证失败"
    
    # 测试到期提醒
    print("\n[NOTE] 测试到期提醒...")
    test_cases = [
        (365, False, 'none'),
        (60, True, 'info'),
        (30, True, 'warning'),
        (7, True, 'urgent'),
        (-1, True, 'expired')
    ]
    
    for days, should_show, expected_level in test_cases:
        show, level = LicenseValidator.should_show_reminder(days)
        message = LicenseValidator.get_reminder_message(days, "测试客户")
        print(f"剩余{days}天: 显示={show}, 级别={level}, 消息={message[:30] if message else '无'}")
        assert show == should_show, f"提醒判断错误: {days}天"
        assert level == expected_level, f"提醒级别错误: {days}天"
    
    # 测试功能限制
    print("\n[NOTE] 测试功能限制...")
    assert not LicenseValidator.should_restrict_features(1), "不应限制功能"
    assert LicenseValidator.should_restrict_features(-1), "应该限制功能"
    print("[成功] 功能限制逻辑正确")
    
    # 测试无效License
    print("\n[NOTE] 测试无效License...")
    invalid_licenses = [
        "INVALID-LICENSE",
        "DESI-12345678",
        "DESI-12345678-87654321",  # 缺少校验位
        "DESI-12345678-87654321-XXXX",  # 错误的校验位
    ]
    
    for invalid in invalid_licenses:
        is_valid = LicenseGenerator.validate_license_format(invalid)
        print(f"{invalid}: {'[错误] 无效' if not is_valid else '[警告] 意外有效'}")
        assert not is_valid, f"应该识别为无效: {invalid}"
    
    print("\n[成功] 所有测试通过")

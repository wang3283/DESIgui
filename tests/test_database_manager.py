#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理器单元测试
"""

import unittest
import os
import tempfile
from datetime import datetime
from pathlib import Path
import sys

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from database_manager import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    """数据库管理器测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时数据库文件
        self.temp_dir = tempfile.mkdtemp()
        self.admin_db_path = os.path.join(self.temp_dir, "test_admin.db")
        self.client_db_path = os.path.join(self.temp_dir, "test_client.db")
        
        self.admin_db = DatabaseManager(self.admin_db_path, mode='admin')
        self.client_db = DatabaseManager(self.client_db_path, mode='client')
    
    def tearDown(self):
        """测试后清理"""
        self.admin_db.close()
        self.client_db.close()
        
        # 删除临时文件
        try:
            os.remove(self.admin_db_path)
            os.remove(self.client_db_path)
            os.rmdir(self.temp_dir)
        except:
            pass
    
    # ==================== Schema测试 ====================
    
    def test_admin_schema_creation(self):
        """测试管理员Schema创建"""
        # 验证所有表都存在
        tables = ['customers', 'usage_records', 'invoices', 'email_logs', 'backup_records']
        
        for table in tables:
            result = self.admin_db.fetchone(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            self.assertIsNotNone(result, f"表 {table} 应该存在")
    
    def test_client_schema_creation(self):
        """测试客户端Schema创建"""
        # 验证所有表都存在
        tables = ['usage_records', 'usage_stats', 'license_info']
        
        for table in tables:
            result = self.client_db.fetchone(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            self.assertIsNotNone(result, f"表 {table} 应该存在")
    
    # ==================== CRUD操作测试 ====================
    
    def test_create_customer(self):
        """测试创建客户"""
        customer_data = {
            'customer_id': 'CUST-TEST001',
            'name': '测试客户',
            'email': 'test@example.com',
            'company': '测试公司',
            'license_key': 'DESI-TEST-1234',
            'created_at': datetime.now().isoformat(),
            'expires_at': datetime.now().isoformat()
        }
        
        customer_id = self.admin_db.create_customer(customer_data)
        self.assertEqual(customer_id, 'CUST-TEST001')
        
        # 验证客户已创建
        customer = self.admin_db.get_customer('CUST-TEST001')
        self.assertIsNotNone(customer)
        self.assertEqual(customer['name'], '测试客户')
    
    def test_update_customer(self):
        """测试更新客户"""
        # 先创建客户
        customer_data = {
            'customer_id': 'CUST-TEST002',
            'name': '原始名称',
            'email': 'test@example.com',
            'license_key': 'DESI-TEST-5678',
            'created_at': datetime.now().isoformat(),
            'expires_at': datetime.now().isoformat()
        }
        self.admin_db.create_customer(customer_data)
        
        # 更新客户
        success = self.admin_db.update_customer('CUST-TEST002', {
            'name': '新名称',
            'company': '新公司'
        })
        self.assertTrue(success)
        
        # 验证更新
        customer = self.admin_db.get_customer('CUST-TEST002')
        self.assertEqual(customer['name'], '新名称')
        self.assertEqual(customer['company'], '新公司')
        # customer_id应该保持不变
        self.assertEqual(customer['customer_id'], 'CUST-TEST002')
    
    def test_list_customers(self):
        """测试列出客户"""
        # 创建多个客户
        for i in range(3):
            customer_data = {
                'customer_id': f'CUST-TEST{i:03d}',
                'name': f'客户{i}',
                'email': f'test{i}@example.com',
                'license_key': f'DESI-TEST-{i:04d}',
                'created_at': datetime.now().isoformat(),
                'expires_at': datetime.now().isoformat()
            }
            self.admin_db.create_customer(customer_data)
        
        # 列出所有客户
        customers = self.admin_db.list_customers()
        self.assertEqual(len(customers), 3)
    
    # ==================== 事务测试 ====================
    
    def test_transaction_commit(self):
        """测试事务提交"""
        with self.admin_db.transaction() as conn:
            conn.execute('''
                INSERT INTO customers 
                (customer_id, name, email, license_key, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('CUST-TX001', '事务测试', 'tx@example.com', 'DESI-TX-001',
                  datetime.now().isoformat(), datetime.now().isoformat()))
        
        # 验证数据已提交
        customer = self.admin_db.get_customer('CUST-TX001')
        self.assertIsNotNone(customer)
    
    def test_transaction_rollback(self):
        """测试事务回滚"""
        try:
            with self.admin_db.transaction() as conn:
                conn.execute('''
                    INSERT INTO customers 
                    (customer_id, name, email, license_key, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', ('CUST-TX002', '回滚测试', 'rb@example.com', 'DESI-TX-002',
                      datetime.now().isoformat(), datetime.now().isoformat()))
                
                # 故意引发错误
                raise Exception("测试回滚")
        except Exception:
            pass
        
        # 验证数据已回滚
        customer = self.admin_db.get_customer('CUST-TX002')
        self.assertIsNone(customer)
    
    # ==================== 客户端功能测试 ====================
    
    def test_save_and_get_license(self):
        """测试保存和获取License"""
        license_data = {
            'license_key': 'DESI-CLIENT-1234',
            'activated_at': datetime.now().isoformat(),
            'expires_at': datetime.now().isoformat(),
            'last_validated': datetime.now().isoformat()
        }
        
        self.client_db.save_license_info(license_data)
        
        # 获取License
        saved_license = self.client_db.get_license_info()
        self.assertIsNotNone(saved_license)
        self.assertEqual(saved_license['license_key'], 'DESI-CLIENT-1234')
    
    def test_record_usage(self):
        """测试记录使用"""
        import hashlib
        
        record_data = {
            'record_id': 'REC-001',
            'timestamp': datetime.now().isoformat(),
            'action_type': 'load_sample',
            'sample_name': 'test_sample',
            'sample_hash': hashlib.md5('test_sample'.encode()).hexdigest(),
            'checksum': 'test_checksum'
        }
        
        record_id = self.client_db.record_usage(record_data)
        self.assertEqual(record_id, 'REC-001')
    
    def test_update_daily_stats(self):
        """测试更新每日统计"""
        import hashlib
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 先记录一些使用数据
        for i in range(3):
            record_data = {
                'record_id': f'REC-STAT-{i}',
                'timestamp': datetime.now().isoformat(),
                'action_type': 'load_sample' if i < 2 else 'export_data',
                'sample_name': f'test_sample_{i}',
                'sample_hash': hashlib.md5(f'test_sample_{i}'.encode()).hexdigest(),
                'checksum': f'checksum_{i}'
            }
            self.client_db.record_usage(record_data)
        
        # 更新统计
        self.client_db.update_daily_stats(today, 'load_sample')
        self.client_db.update_daily_stats(today, 'export_data')
        
        # 验证统计
        stats = self.client_db.get_usage_stats(days=1)
        self.assertGreater(stats['total_records'], 0)
    
    # ==================== 错误处理测试 ====================
    
    def test_mode_restriction_admin(self):
        """测试模式限制（管理员）"""
        # 客户端模式不能调用管理员方法
        with self.assertRaises(ValueError):
            self.client_db.create_customer({})
    
    def test_mode_restriction_client(self):
        """测试模式限制（客户端）"""
        # 管理员模式不能调用客户端方法
        with self.assertRaises(ValueError):
            self.admin_db.record_usage({})


if __name__ == '__main__':
    unittest.main()

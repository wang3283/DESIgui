#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DESI软件License管理系统 - 简单方案

功能：
1. License生成和验证
2. 使用报告收集和解密
3. 账单生成
4. 客户管理

使用方式：
- 你（管理员）运行此脚本管理客户
- 客户软件自动记录使用量
- 定期收集客户的使用报告文件进行计费
"""

import os
import json
import uuid
import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import base64

# 加密相关
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class LicenseManager:
    """License管理器 - 管理员使用"""
    
    SECRET_SEED = b"DESI_METABOLOMICS_2025_SECRET_KEY"
    
    def __init__(self, db_path: str = "license_manager.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化管理数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 客户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT UNIQUE,
                name TEXT,
                email TEXT,
                company TEXT,
                license_key TEXT UNIQUE,
                created_at TEXT,
                expires_at TEXT,
                status TEXT DEFAULT 'active',
                notes TEXT
            )
        ''')
        
        # 使用记录表（从客户报告导入）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT,
                license_key TEXT,
                machine_id TEXT,
                report_date TEXT,
                period_start TEXT,
                period_end TEXT,
                total_samples_loaded INTEGER,
                total_exports INTEGER,
                total_splits INTEGER,
                unique_samples INTEGER,
                imported_at TEXT,
                report_file TEXT
            )
        ''')
        
        # 账单表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id TEXT UNIQUE,
                customer_id TEXT,
                period_start TEXT,
                period_end TEXT,
                total_samples INTEGER,
                unit_price REAL,
                total_amount REAL,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                paid_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_customer(self, name: str, email: str, company: str = "",
                       expires_days: int = 365) -> Dict:
        """
        创建新客户并生成License
        
        返回:
            包含customer_id和license_key的字典
        """
        customer_id = f"CUST-{uuid.uuid4().hex[:8].upper()}"
        license_key = f"DESI-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"
        
        created_at = datetime.now().isoformat()
        expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO customers 
            (customer_id, name, email, company, license_key, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (customer_id, name, email, company, license_key, created_at, expires_at))
        
        conn.commit()
        conn.close()
        
        return {
            'customer_id': customer_id,
            'name': name,
            'email': email,
            'license_key': license_key,
            'expires_at': expires_at
        }
    
    def list_customers(self) -> List[Dict]:
        """列出所有客户"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT customer_id, name, email, company, license_key, 
                   created_at, expires_at, status
            FROM customers
            ORDER BY created_at DESC
        ''')
        
        customers = []
        for row in cursor.fetchall():
            customers.append({
                'customer_id': row[0],
                'name': row[1],
                'email': row[2],
                'company': row[3],
                'license_key': row[4],
                'created_at': row[5],
                'expires_at': row[6],
                'status': row[7]
            })
        
        conn.close()
        return customers
    
    def _get_cipher(self, machine_id: str):
        """根据机器ID获取解密器"""
        if not HAS_CRYPTO:
            return None
        
        salt = machine_id[:16].encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.SECRET_SEED))
        return Fernet(key)
    
    def import_usage_report(self, report_file: str, machine_id: str = None) -> Dict:
        """
        导入客户的使用报告文件
        
        参数:
            report_file: 客户导出的.enc报告文件
            machine_id: 客户机器ID（可选，用于解密）
        
        返回:
            导入结果
        """
        try:
            with open(report_file, 'r') as f:
                encrypted_data = f.read()
            
            report_data = None
            
            # 方式1：尝试Fernet解密（需要机器ID）
            if HAS_CRYPTO and machine_id:
                try:
                    cipher = self._get_cipher(machine_id)
                    decrypted = cipher.decrypt(encrypted_data.encode()).decode()
                    report_data = json.loads(decrypted)
                except:
                    pass
            
            # 方式2：尝试常见机器ID解密
            if not report_data and HAS_CRYPTO:
                # 从数据库获取已知的机器ID尝试解密
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT DISTINCT machine_id FROM usage_records WHERE machine_id IS NOT NULL')
                known_machines = [row[0] for row in cursor.fetchall()]
                conn.close()
                
                for mid in known_machines:
                    try:
                        cipher = self._get_cipher(mid)
                        decrypted = cipher.decrypt(encrypted_data.encode()).decode()
                        report_data = json.loads(decrypted)
                        break
                    except:
                        continue
            
            # 方式3：尝试base64解码（无加密时的备用）
            if not report_data:
                try:
                    decoded = base64.b64decode(encrypted_data.encode()).decode()
                    report_data = json.loads(decoded)
                except:
                    pass
            
            if not report_data:
                return {'success': False, 'error': '无法解密报告文件，请提供机器ID'}
            
            # 提取数据
            license_key = report_data.get('license_key', '')
            machine_id = report_data.get('machine_id', '')
            stats = report_data.get('usage_stats', {})
            
            # 查找客户
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT customer_id FROM customers WHERE license_key = ?',
                          (license_key,))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return {'success': False, 'error': f'未找到License: {license_key}'}
            
            customer_id = row[0]
            
            # 插入使用记录
            cursor.execute('''
                INSERT INTO usage_records
                (customer_id, license_key, machine_id, report_date,
                 total_samples_loaded, total_exports, total_splits,
                 unique_samples, imported_at, report_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                customer_id,
                license_key,
                machine_id,
                report_data.get('report_generated', ''),
                stats.get('total_loads', 0),
                stats.get('total_exports', 0),
                stats.get('total_splits', 0),
                stats.get('unique_samples', 0),
                datetime.now().isoformat(),
                report_file
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'customer_id': customer_id,
                'license_key': license_key,
                'unique_samples': stats.get('unique_samples', 0),
                'total_loads': stats.get('total_loads', 0)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_customer_usage(self, customer_id: str) -> Dict:
        """获取客户使用统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                SUM(total_samples_loaded) as total_loads,
                SUM(total_exports) as total_exports,
                SUM(total_splits) as total_splits,
                SUM(unique_samples) as unique_samples,
                COUNT(*) as report_count,
                MAX(report_date) as last_report
            FROM usage_records
            WHERE customer_id = ?
        ''', (customer_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            'customer_id': customer_id,
            'total_loads': row[0] or 0,
            'total_exports': row[1] or 0,
            'total_splits': row[2] or 0,
            'unique_samples': row[3] or 0,
            'report_count': row[4] or 0,
            'last_report': row[5]
        }
    
    def generate_invoice(self, customer_id: str, unit_price: float = 10.0,
                        period_days: int = 30) -> Dict:
        """
        生成账单
        
        参数:
            customer_id: 客户ID
            unit_price: 每个样本的单价
            period_days: 计费周期（天）
        """
        usage = self.get_customer_usage(customer_id)
        
        invoice_id = f"INV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        total_samples = usage['unique_samples']
        total_amount = total_samples * unit_price
        
        period_end = datetime.now()
        period_start = period_end - timedelta(days=period_days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO invoices
            (invoice_id, customer_id, period_start, period_end,
             total_samples, unit_price, total_amount, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            invoice_id,
            customer_id,
            period_start.isoformat(),
            period_end.isoformat(),
            total_samples,
            unit_price,
            total_amount,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # 获取客户信息
        customers = self.list_customers()
        customer = next((c for c in customers if c['customer_id'] == customer_id), {})
        
        return {
            'invoice_id': invoice_id,
            'customer_id': customer_id,
            'customer_name': customer.get('name', ''),
            'period': f"{period_start.strftime('%Y-%m-%d')} ~ {period_end.strftime('%Y-%m-%d')}",
            'total_samples': total_samples,
            'unit_price': unit_price,
            'total_amount': total_amount
        }
    
    def export_invoice_text(self, invoice_id: str) -> str:
        """导出账单文本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT i.*, c.name, c.email, c.company
            FROM invoices i
            JOIN customers c ON i.customer_id = c.customer_id
            WHERE i.invoice_id = ?
        ''', (invoice_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return "账单未找到"
        
        text = f"""
╔══════════════════════════════════════════════════════════════╗
║                    DESI软件使用账单                           ║
╠══════════════════════════════════════════════════════════════╣
║  账单编号: {row[1]:<48} ║
║  客户名称: {row[11]:<48} ║
║  公司:     {row[13] or 'N/A':<48} ║
║  邮箱:     {row[12]:<48} ║
╠══════════════════════════════════════════════════════════════╣
║  计费周期: {row[3][:10]} ~ {row[4][:10]:<35} ║
║  处理样本数: {row[5]:<46} ║
║  单价:     ¥{row[6]:.2f}/样本{' '*38} ║
╠══════════════════════════════════════════════════════════════╣
║  应付金额: ¥{row[7]:.2f}{' '*46} ║
╠══════════════════════════════════════════════════════════════╣
║  账单日期: {row[9][:10]:<48} ║
║  状态:     {row[8]:<48} ║
╚══════════════════════════════════════════════════════════════╝
"""
        return text


def main():
    """命令行管理工具"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DESI License管理工具')
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 创建客户
    create_parser = subparsers.add_parser('create', help='创建新客户')
    create_parser.add_argument('--name', required=True, help='客户名称')
    create_parser.add_argument('--email', required=True, help='邮箱')
    create_parser.add_argument('--company', default='', help='公司')
    
    # 列出客户
    subparsers.add_parser('list', help='列出所有客户')
    
    # 导入报告
    import_parser = subparsers.add_parser('import', help='导入使用报告')
    import_parser.add_argument('file', help='报告文件路径')
    import_parser.add_argument('--machine-id', help='客户机器ID（用于解密）')
    
    # 查看使用量
    usage_parser = subparsers.add_parser('usage', help='查看客户使用量')
    usage_parser.add_argument('customer_id', help='客户ID')
    
    # 生成账单
    invoice_parser = subparsers.add_parser('invoice', help='生成账单')
    invoice_parser.add_argument('customer_id', help='客户ID')
    invoice_parser.add_argument('--price', type=float, default=10.0, help='单价')
    
    args = parser.parse_args()
    
    manager = LicenseManager()
    
    if args.command == 'create':
        result = manager.create_customer(args.name, args.email, args.company)
        print("\n[成功] 客户创建成功！")
        print(f"   客户ID: {result['customer_id']}")
        print(f"   License: {result['license_key']}")
        print(f"   有效期至: {result['expires_at'][:10]}")
        print("\n请将License发送给客户。")
    
    elif args.command == 'list':
        customers = manager.list_customers()
        print(f"\n共 {len(customers)} 个客户:\n")
        for c in customers:
            print(f"  [{c['customer_id']}] {c['name']}")
            print(f"      License: {c['license_key']}")
            print(f"      状态: {c['status']}, 到期: {c['expires_at'][:10]}")
            print()
    
    elif args.command == 'import':
        result = manager.import_usage_report(args.file, args.machine_id)
        if result['success']:
            print(f"\n[成功] 导入成功！")
            print(f"   客户: {result['customer_id']}")
            print(f"   唯一样本数: {result['unique_samples']}")
        else:
            print(f"\n[错误] 导入失败: {result['error']}")
    
    elif args.command == 'usage':
        usage = manager.get_customer_usage(args.customer_id)
        print(f"\n客户 {args.customer_id} 使用统计:")
        print(f"   样本加载: {usage['total_loads']} 次")
        print(f"   数据导出: {usage['total_exports']} 次")
        print(f"   代谢物拆分: {usage['total_splits']} 次")
        print(f"   唯一样本数: {usage['unique_samples']}")
        print(f"   报告数: {usage['report_count']}")
    
    elif args.command == 'invoice':
        invoice = manager.generate_invoice(args.customer_id, args.price)
        print(manager.export_invoice_text(invoice['invoice_id']))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

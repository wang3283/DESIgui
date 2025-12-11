#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理器 - 统一的数据库访问层
支持管理员和客户端两种模式
"""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
import json


class DatabaseManager:
    """统一的数据库管理器"""
    
    # 数据库版本
    DB_VERSION = 1
    
    def __init__(self, db_path: str, mode: str = 'admin'):
        """
        初始化数据库管理器
        
        参数:
            db_path: 数据库文件路径
            mode: 'admin' 或 'client'
        """
        self.db_path = db_path
        self.mode = mode
        self._local = threading.local()
        
        # 确保数据库目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_database()
        
        # 检查并执行迁移
        self._migrate_if_needed()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取线程本地的数据库连接（连接池）"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            # 启用外键约束
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        return self._local.connection
    
    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    
    def _init_database(self):
        """初始化数据库Schema"""
        if self.mode == 'admin':
            self._init_admin_schema()
        else:
            self._init_client_schema()
    
    def _init_admin_schema(self):
        """初始化管理员数据库Schema"""
        with self.transaction() as conn:
            cursor = conn.cursor()
            
            # 版本表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS db_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            ''')
            
            # 客户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    company TEXT,
                    license_key TEXT UNIQUE NOT NULL,
                    billing_mode TEXT DEFAULT 'per_sample',
                    unit_price REAL DEFAULT 10.0,
                    subscription_fee REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    notes TEXT
                )
            ''')
            
            # 使用记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT NOT NULL,
                    license_key TEXT NOT NULL,
                    machine_id TEXT,
                    report_date TEXT NOT NULL,
                    period_start TEXT,
                    period_end TEXT,
                    total_samples_loaded INTEGER DEFAULT 0,
                    total_exports INTEGER DEFAULT 0,
                    total_splits INTEGER DEFAULT 0,
                    unique_samples INTEGER DEFAULT 0,
                    imported_at TEXT NOT NULL,
                    report_file TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                )
            ''')
            
            # 账单表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id TEXT UNIQUE NOT NULL,
                    customer_id TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    billing_mode TEXT NOT NULL,
                    total_samples INTEGER DEFAULT 0,
                    total_operations INTEGER DEFAULT 0,
                    unit_price REAL DEFAULT 0.0,
                    subscription_fee REAL DEFAULT 0.0,
                    subtotal REAL DEFAULT 0.0,
                    tax_rate REAL DEFAULT 0.0,
                    tax_amount REAL DEFAULT 0.0,
                    total_amount REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    sent_at TEXT,
                    paid_at TEXT,
                    notes TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                )
            ''')
            
            # 邮件日志表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT,
                    email_type TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    sent_at TEXT NOT NULL,
                    status TEXT DEFAULT 'sent',
                    error_message TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                )
            ''')
            
            # 备份记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backup_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_file TEXT NOT NULL,
                    backup_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    file_size INTEGER,
                    checksum TEXT
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_customers_license 
                ON customers(license_key)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_usage_customer 
                ON usage_records(customer_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_invoices_customer 
                ON invoices(customer_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_email_customer 
                ON email_logs(customer_id)
            ''')
    
    def _init_client_schema(self):
        """初始化客户端数据库Schema"""
        with self.transaction() as conn:
            cursor = conn.cursor()
            
            # 版本表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS db_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            ''')
            
            # 使用记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    sample_name TEXT NOT NULL,
                    sample_hash TEXT NOT NULL,
                    details_encrypted TEXT,
                    reported INTEGER DEFAULT 0,
                    report_time TEXT,
                    checksum TEXT NOT NULL
                )
            ''')
            
            # 统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    samples_loaded INTEGER DEFAULT 0,
                    samples_exported INTEGER DEFAULT 0,
                    samples_split INTEGER DEFAULT 0,
                    total_operations INTEGER DEFAULT 0
                )
            ''')
            
            # 许可证信息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS license_info (
                    id INTEGER PRIMARY KEY,
                    license_key TEXT NOT NULL,
                    activated_at TEXT NOT NULL,
                    expires_at TEXT,
                    last_validated TEXT
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_usage_timestamp 
                ON usage_records(timestamp)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_usage_sample_hash 
                ON usage_records(sample_hash)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_stats_date 
                ON usage_stats(date)
            ''')

    
    def _migrate_if_needed(self):
        """检查并执行数据库迁移"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 获取当前版本
        cursor.execute("SELECT version FROM db_version ORDER BY version DESC LIMIT 1")
        row = cursor.fetchone()
        current_version = row[0] if row else 0
        
        # 如果需要迁移
        if current_version < self.DB_VERSION:
            print(f"[信息] 数据库迁移: v{current_version} -> v{self.DB_VERSION}")
            self._perform_migration(current_version, self.DB_VERSION)
            
            # 更新版本
            with self.transaction() as conn:
                conn.execute(
                    "INSERT INTO db_version (version, applied_at) VALUES (?, ?)",
                    (self.DB_VERSION, datetime.now().isoformat())
                )
            print("[成功] 数据库迁移完成")
    
    def _perform_migration(self, from_version: int, to_version: int):
        """执行数据库迁移"""
        # 这里可以添加具体的迁移逻辑
        # 例如：添加新列、修改表结构等
        pass
    
    # ==================== CRUD操作 ====================
    
    def execute(self, query: str, params: Tuple = ()) -> sqlite3.Cursor:
        """执行SQL查询"""
        conn = self._get_connection()
        return conn.execute(query, params)
    
    def fetchone(self, query: str, params: Tuple = ()) -> Optional[sqlite3.Row]:
        """查询单条记录"""
        cursor = self.execute(query, params)
        return cursor.fetchone()
    
    def fetchall(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """查询多条记录"""
        cursor = self.execute(query, params)
        return cursor.fetchall()
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """插入记录"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        with self.transaction() as conn:
            cursor = conn.execute(query, tuple(data.values()))
            return cursor.lastrowid
    
    def update(self, table: str, data: Dict[str, Any], where: str, where_params: Tuple = ()) -> int:
        """更新记录"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        
        with self.transaction() as conn:
            cursor = conn.execute(query, tuple(data.values()) + where_params)
            return cursor.rowcount
    
    def delete(self, table: str, where: str, where_params: Tuple = ()) -> int:
        """删除记录"""
        query = f"DELETE FROM {table} WHERE {where}"
        
        with self.transaction() as conn:
            cursor = conn.execute(query, where_params)
            return cursor.rowcount
    
    # ==================== 管理员专用方法 ====================
    
    def create_customer(self, customer_data: Dict[str, Any]) -> str:
        """创建客户（管理员）"""
        if self.mode != 'admin':
            raise ValueError("此操作仅限管理员模式")
        
        customer_id = self.insert('customers', customer_data)
        return customer_data['customer_id']
    
    def get_customer(self, customer_id: str) -> Optional[Dict]:
        """获取客户信息（管理员）"""
        if self.mode != 'admin':
            raise ValueError("此操作仅限管理员模式")
        
        row = self.fetchone(
            "SELECT * FROM customers WHERE customer_id = ?",
            (customer_id,)
        )
        return dict(row) if row else None
    
    def list_customers(self, status: str = None) -> List[Dict]:
        """列出所有客户（管理员）"""
        if self.mode != 'admin':
            raise ValueError("此操作仅限管理员模式")
        
        if status:
            query = "SELECT * FROM customers WHERE status = ? ORDER BY created_at DESC"
            rows = self.fetchall(query, (status,))
        else:
            query = "SELECT * FROM customers ORDER BY created_at DESC"
            rows = self.fetchall(query)
        
        return [dict(row) for row in rows]
    
    def get_all_customers(self) -> List[Dict]:
        """获取所有客户（管理员）- list_customers的别名"""
        return self.list_customers()
    
    def update_customer(self, customer_id: str, data: Dict[str, Any]) -> bool:
        """更新客户信息（管理员）"""
        if self.mode != 'admin':
            raise ValueError("此操作仅限管理员模式")
        
        count = self.update('customers', data, "customer_id = ?", (customer_id,))
        return count > 0
    
    def delete_customer(self, customer_id: str) -> bool:
        """删除客户及其相关数据（管理员）"""
        if self.mode != 'admin':
            raise ValueError("此操作仅限管理员模式")
        
        with self.transaction():
            # 删除相关的使用记录
            self.execute("DELETE FROM usage_records WHERE customer_id = ?", (customer_id,))
            # 删除相关的账单
            self.execute("DELETE FROM invoices WHERE customer_id = ?", (customer_id,))
            # 删除相关的邮件日志
            self.execute("DELETE FROM email_logs WHERE customer_id = ?", (customer_id,))
            # 删除客户
            cursor = self.execute("DELETE FROM customers WHERE customer_id = ?", (customer_id,))
            return cursor.rowcount > 0
    
    def add_usage_record(self, record_data: Dict[str, Any]) -> int:
        """添加使用记录"""
        return self.insert('usage_records', record_data)
    
    def get_customer_usage(self, customer_id: str) -> Dict:
        """获取客户使用统计（管理员）"""
        if self.mode != 'admin':
            raise ValueError("此操作仅限管理员模式")
        
        row = self.fetchone('''
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
        
        if row:
            return {
                'customer_id': customer_id,
                'total_loads': row['total_loads'] or 0,
                'total_exports': row['total_exports'] or 0,
                'total_splits': row['total_splits'] or 0,
                'unique_samples': row['unique_samples'] or 0,
                'report_count': row['report_count'] or 0,
                'last_report': row['last_report']
            }
        return {}
    
    def create_invoice(self, invoice_data: Dict[str, Any]) -> str:
        """创建账单（管理员）"""
        if self.mode != 'admin':
            raise ValueError("此操作仅限管理员模式")
        
        self.insert('invoices', invoice_data)
        return invoice_data['invoice_id']
    
    def get_invoice(self, invoice_id: str) -> Optional[Dict]:
        """获取账单（管理员）"""
        if self.mode != 'admin':
            raise ValueError("此操作仅限管理员模式")
        
        row = self.fetchone(
            "SELECT * FROM invoices WHERE invoice_id = ?",
            (invoice_id,)
        )
        return dict(row) if row else None
    
    def list_invoices(self, customer_id: str = None) -> List[Dict]:
        """列出账单（管理员）"""
        if self.mode != 'admin':
            raise ValueError("此操作仅限管理员模式")
        
        if customer_id:
            query = "SELECT * FROM invoices WHERE customer_id = ? ORDER BY created_at DESC"
            rows = self.fetchall(query, (customer_id,))
        else:
            query = "SELECT * FROM invoices ORDER BY created_at DESC"
            rows = self.fetchall(query)
        
        return [dict(row) for row in rows]
    
    def log_email(self, email_data: Dict[str, Any]) -> int:
        """记录邮件日志（管理员）"""
        if self.mode != 'admin':
            raise ValueError("此操作仅限管理员模式")
        
        return self.insert('email_logs', email_data)
    
    def create_backup_record(self, backup_data: Dict[str, Any]) -> int:
        """创建备份记录（管理员）"""
        if self.mode != 'admin':
            raise ValueError("此操作仅限管理员模式")
        
        return self.insert('backup_records', backup_data)
    
    # ==================== 客户端专用方法 ====================
    
    def record_usage(self, record_data: Dict[str, Any]) -> str:
        """记录使用情况（客户端）"""
        if self.mode != 'client':
            raise ValueError("此操作仅限客户端模式")
        
        self.insert('usage_records', record_data)
        return record_data['record_id']
    
    def get_usage_stats(self, days: int = 30) -> Dict:
        """获取使用统计（客户端）"""
        if self.mode != 'client':
            raise ValueError("此操作仅限客户端模式")
        
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # 总体统计
        row = self.fetchone('''
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT sample_hash) as unique_samples,
                SUM(CASE WHEN action_type = 'load_sample' THEN 1 ELSE 0 END) as loads,
                SUM(CASE WHEN action_type = 'export_data' THEN 1 ELSE 0 END) as exports,
                SUM(CASE WHEN action_type = 'split_metabolites' THEN 1 ELSE 0 END) as splits
            FROM usage_records
            WHERE timestamp >= ?
        ''', (start_date,))
        
        # 每日统计
        daily_rows = self.fetchall('''
            SELECT date, samples_loaded, samples_exported, samples_split, total_operations
            FROM usage_stats
            WHERE date >= ?
            ORDER BY date DESC
        ''', (start_date,))
        
        return {
            'period_days': days,
            'total_records': row['total_records'] or 0,
            'unique_samples': row['unique_samples'] or 0,
            'total_loads': row['loads'] or 0,
            'total_exports': row['exports'] or 0,
            'total_splits': row['splits'] or 0,
            'daily_stats': [dict(r) for r in daily_rows]
        }
    
    def update_daily_stats(self, date: str, action_type: str):
        """更新每日统计（客户端）"""
        if self.mode != 'client':
            raise ValueError("此操作仅限客户端模式")
        
        with self.transaction() as conn:
            # 插入或更新
            conn.execute('''
                INSERT INTO usage_stats (date, total_operations)
                VALUES (?, 1)
                ON CONFLICT(date) DO UPDATE SET
                total_operations = total_operations + 1
            ''', (date,))
            
            # 根据操作类型更新
            if action_type == 'load_sample':
                conn.execute('''
                    UPDATE usage_stats SET samples_loaded = samples_loaded + 1
                    WHERE date = ?
                ''', (date,))
            elif action_type == 'export_data':
                conn.execute('''
                    UPDATE usage_stats SET samples_exported = samples_exported + 1
                    WHERE date = ?
                ''', (date,))
            elif action_type == 'split_metabolites':
                conn.execute('''
                    UPDATE usage_stats SET samples_split = samples_split + 1
                    WHERE date = ?
                ''', (date,))
    
    def save_license_info(self, license_data: Dict[str, Any]):
        """保存许可证信息（客户端）"""
        if self.mode != 'client':
            raise ValueError("此操作仅限客户端模式")
        
        with self.transaction() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO license_info 
                (id, license_key, activated_at, expires_at, last_validated)
                VALUES (1, ?, ?, ?, ?)
            ''', (
                license_data['license_key'],
                license_data['activated_at'],
                license_data.get('expires_at'),
                license_data.get('last_validated')
            ))
    
    def get_license_info(self) -> Optional[Dict]:
        """获取许可证信息（客户端）"""
        if self.mode != 'client':
            raise ValueError("此操作仅限客户端模式")
        
        row = self.fetchone("SELECT * FROM license_info WHERE id = 1")
        return dict(row) if row else None
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("数据库管理器测试")
    print("=" * 60)
    
    # 测试管理员模式
    print("\n[测试] 测试管理员模式...")
    admin_db = DatabaseManager("test_admin.db", mode='admin')
    
    # 创建测试客户
    customer_data = {
        'customer_id': 'CUST-TEST001',
        'name': '测试客户',
        'email': 'test@example.com',
        'company': '测试公司',
        'license_key': 'DESI-TEST-1234',
        'created_at': datetime.now().isoformat(),
        'expires_at': datetime.now().isoformat()
    }
    admin_db.create_customer(customer_data)
    print("[成功] 创建客户成功")
    
    # 查询客户
    customer = admin_db.get_customer('CUST-TEST001')
    print(f"[成功] 查询客户: {customer['name']}")
    
    # 测试客户端模式
    print("\n[测试] 测试客户端模式...")
    client_db = DatabaseManager("test_client.db", mode='client')
    
    # 保存License
    client_db.save_license_info({
        'license_key': 'DESI-TEST-1234',
        'activated_at': datetime.now().isoformat()
    })
    print("[成功] 保存License成功")
    
    # 获取License
    license_info = client_db.get_license_info()
    print(f"[成功] 获取License: {license_info['license_key']}")
    
    print("\n[成功] 所有测试通过")
    
    # 清理
    admin_db.close()
    client_db.close()

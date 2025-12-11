#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DESI软件使用量追踪系统
用于商业化计费：记录客户处理的样本数量

功能：
1. 本地加密存储使用记录（防篡改）
2. 云端上报使用数据
3. License验证
4. 离线缓存队列（联网后自动上报）
"""

import os
import sys
import json
import time
import uuid
import hashlib
import sqlite3
import platform
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
import base64

# 加密相关
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    print("[警告] 未安装cryptography库，使用基础加密")

# 网络请求
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("[警告] 未安装requests库，云端上报功能不可用")


class UsageTracker:
    """使用量追踪器"""
    
    # 云端服务器配置（需要替换为你的实际服务器）
    SERVER_URL = "https://your-server.com/api/usage"
    
    # 加密密钥种子（实际部署时应该更复杂）
    SECRET_SEED = b"DESI_METABOLOMICS_2025_SECRET_KEY"
    
    def __init__(self, license_key: str = None, data_dir: str = None, silent: bool = True):
        """
        初始化追踪器（优化版 - 快速启动）
        
        参数:
            license_key: 客户的许可证密钥
            data_dir: 数据存储目录
            silent: 静默模式（不显示任何提示）
        """
        self.silent = silent
        self.license_key = license_key or self._get_or_create_license()
        self.machine_id = self._get_machine_id()
        
        # 数据目录
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            # 默认存储在用户目录的隐藏文件夹
            self.data_dir = Path.home() / ".desi_analytics"
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据库文件
        self.db_path = self.data_dir / "usage_data.db"
        self.config_path = self.data_dir / "config.enc"
        
        # 初始化加密器（延迟加载）
        self._cipher = None
        
        # 初始化数据库（带自动修复）
        self._init_database_with_repair()
        
        # 上报队列（离线时缓存）
        self.pending_reports = []
        self._batch_buffer = []  # 批量插入缓冲区
        self._batch_size = 10  # 批量大小
        self._last_flush_time = time.time()
        
        # 后台上报线程（延迟启动）
        self._reporter_thread = None
        self._start_background_reporter()
        
        if not self.silent:
            print(f"[信息] 使用量追踪器已初始化")
            print(f"   License: {self.license_key[:8]}...{self.license_key[-4:]}")
            print(f"   Machine: {self.machine_id[:8]}...")
    
    def _get_machine_id(self) -> str:
        """获取机器唯一标识"""
        # 组合多个硬件信息生成唯一ID
        info_parts = [
            platform.node(),  # 主机名
            platform.machine(),  # 架构
            platform.processor(),  # 处理器
        ]
        
        # 尝试获取MAC地址
        try:
            import uuid as uuid_lib
            mac = uuid_lib.getnode()
            info_parts.append(str(mac))
        except:
            pass
        
        # 生成哈希
        combined = "|".join(info_parts)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _get_or_create_license(self) -> str:
        """获取或创建许可证密钥"""
        license_file = Path.home() / ".desi_analytics" / "license.key"
        
        if license_file.exists():
            try:
                return license_file.read_text().strip()
            except:
                pass
        
        # 生成新的License（实际应该从服务器获取）
        new_license = f"DESI-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"
        
        license_file.parent.mkdir(parents=True, exist_ok=True)
        license_file.write_text(new_license)
        
        return new_license
    
    @property
    def cipher(self):
        """延迟加载加密器（优化启动时间）"""
        if self._cipher is None:
            self._cipher = self._init_cipher()
        return self._cipher
    
    def _init_cipher(self):
        """初始化加密器"""
        if not HAS_CRYPTO:
            return None
        
        # 使用机器ID和密钥种子生成加密密钥
        salt = self.machine_id[:16].encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.SECRET_SEED))
        return Fernet(key)
    
    def _encrypt(self, data: str) -> str:
        """加密数据"""
        if self.cipher:
            return self.cipher.encrypt(data.encode()).decode()
        else:
            # 简单的base64编码（不安全，仅作备用）
            return base64.b64encode(data.encode()).decode()
    
    def _decrypt(self, data: str) -> str:
        """解密数据"""
        if self.cipher:
            return self.cipher.decrypt(data.encode()).decode()
        else:
            return base64.b64decode(data.encode()).decode()
    
    def _init_database_with_repair(self):
        """初始化SQLite数据库（带自动修复功能）"""
        try:
            # 尝试连接数据库
            conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            cursor = conn.cursor()
            
            # 检查数据库完整性
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            if result[0] != 'ok':
                if not self.silent:
                    print("[警告] 数据库损坏，尝试修复...")
                self._repair_database()
                conn.close()
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
            
            # 使用记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id TEXT UNIQUE,
                    timestamp TEXT,
                    action_type TEXT,
                    sample_name TEXT,
                    sample_hash TEXT,
                    details_encrypted TEXT,
                    reported INTEGER DEFAULT 0,
                    report_time TEXT,
                    checksum TEXT
                )
            ''')
            
            # 统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE,
                    samples_loaded INTEGER DEFAULT 0,
                    samples_exported INTEGER DEFAULT 0,
                    samples_split INTEGER DEFAULT 0,
                    total_operations INTEGER DEFAULT 0
                )
            ''')
            
            # 验证表（防篡改）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS integrity_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    check_time TEXT,
                    total_records INTEGER,
                    checksum TEXT
                )
            ''')
            
            # 创建索引（优化查询性能）
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON usage_records(timestamp)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_sample_hash 
                ON usage_records(sample_hash)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_date 
                ON usage_stats(date)
            ''')
            
            conn.commit()
            conn.close()
            
        except sqlite3.DatabaseError as e:
            if not self.silent:
                print(f"[错误] 数据库错误: {e}")
                print("[信息] 创建新数据库...")
            self._repair_database()
    
    def _repair_database(self):
        """修复损坏的数据库"""
        try:
            # 备份旧数据库
            if self.db_path.exists():
                backup_path = self.db_path.with_suffix('.db.backup')
                import shutil
                shutil.copy2(self.db_path, backup_path)
                if not self.silent:
                    print(f"[信息] 已备份到: {backup_path}")
            
            # 删除损坏的数据库
            if self.db_path.exists():
                self.db_path.unlink()
            
            if not self.silent:
                print("[成功] 数据库已重建")
        
        except Exception as e:
            if not self.silent:
                print(f"[错误] 修复失败: {e}")
    
    def _calculate_checksum(self, data: Dict) -> str:
        """计算数据校验和"""
        # 将数据转为JSON并计算哈希
        data_str = json.dumps(data, sort_keys=True)
        combined = f"{data_str}|{self.machine_id}|{self.SECRET_SEED.decode()}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def record_usage(self, action_type: str, sample_name: str, 
                     details: Dict = None) -> str:
        """
        记录使用情况（优化版 - 批量插入）
        
        参数:
            action_type: 操作类型 (load_sample, export_data, split_metabolites, etc.)
            sample_name: 样本名称
            details: 额外详情
        
        返回:
            记录ID
        """
        record_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # 样本名称哈希（用于去重统计）
        sample_hash = hashlib.md5(sample_name.encode()).hexdigest()
        
        # 详情加密（延迟加载cipher）
        details = details or {}
        details['machine_id'] = self.machine_id
        details['license_key'] = self.license_key
        details['app_version'] = '2.4'
        details['os'] = platform.system()
        
        details_encrypted = self._encrypt(json.dumps(details))
        
        # 计算校验和
        checksum_data = {
            'record_id': record_id,
            'timestamp': timestamp,
            'action_type': action_type,
            'sample_name': sample_name,
            'sample_hash': sample_hash
        }
        checksum = self._calculate_checksum(checksum_data)
        
        # 添加到批量缓冲区
        self._batch_buffer.append({
            'record_id': record_id,
            'timestamp': timestamp,
            'action_type': action_type,
            'sample_name': sample_name,
            'sample_hash': sample_hash,
            'details_encrypted': details_encrypted,
            'checksum': checksum
        })
        
        # 添加到上报队列
        self.pending_reports.append({
            'record_id': record_id,
            'timestamp': timestamp,
            'action_type': action_type,
            'sample_hash': sample_hash,
            'checksum': checksum
        })
        
        # 检查是否需要刷新缓冲区
        current_time = time.time()
        if (len(self._batch_buffer) >= self._batch_size or 
            current_time - self._last_flush_time > 60):  # 1分钟强制刷新
            self._flush_batch()
        
        return record_id
    
    def _flush_batch(self):
        """刷新批量缓冲区到数据库"""
        if not self._batch_buffer:
            return
        
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            cursor = conn.cursor()
            
            # 批量插入记录
            cursor.executemany('''
                INSERT INTO usage_records 
                (record_id, timestamp, action_type, sample_name, sample_hash, 
                 details_encrypted, checksum)
                VALUES (:record_id, :timestamp, :action_type, :sample_name, 
                        :sample_hash, :details_encrypted, :checksum)
            ''', self._batch_buffer)
            
            # 更新每日统计
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 统计各类操作数量
            load_count = sum(1 for r in self._batch_buffer if r['action_type'] == 'load_sample')
            export_count = sum(1 for r in self._batch_buffer if r['action_type'] == 'export_data')
            split_count = sum(1 for r in self._batch_buffer if r['action_type'] == 'split_metabolites')
            total_count = len(self._batch_buffer)
            
            # 更新统计表
            cursor.execute('''
                INSERT INTO usage_stats (date, total_operations, samples_loaded, 
                                        samples_exported, samples_split)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                total_operations = total_operations + ?,
                samples_loaded = samples_loaded + ?,
                samples_exported = samples_exported + ?,
                samples_split = samples_split + ?
            ''', (today, total_count, load_count, export_count, split_count,
                  total_count, load_count, export_count, split_count))
            
            conn.commit()
            conn.close()
            
            # 清空缓冲区
            self._batch_buffer = []
            self._last_flush_time = time.time()
            
        except Exception as e:
            if not self.silent:
                print(f"[警告] 批量插入失败: {e}")
    
    def __del__(self):
        """析构函数 - 确保缓冲区被刷新"""
        try:
            self._flush_batch()
        except:
            pass
    
    def get_usage_stats(self, days: int = 30) -> Dict:
        """
        获取使用统计
        
        参数:
            days: 统计天数
        
        返回:
            统计数据字典
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # 总体统计
        cursor.execute('''
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT sample_hash) as unique_samples,
                SUM(CASE WHEN action_type = 'load_sample' THEN 1 ELSE 0 END) as loads,
                SUM(CASE WHEN action_type = 'export_data' THEN 1 ELSE 0 END) as exports,
                SUM(CASE WHEN action_type = 'split_metabolites' THEN 1 ELSE 0 END) as splits
            FROM usage_records
            WHERE timestamp >= ?
        ''', (start_date,))
        
        row = cursor.fetchone()
        
        # 每日统计
        cursor.execute('''
            SELECT date, samples_loaded, samples_exported, samples_split, total_operations
            FROM usage_stats
            WHERE date >= ?
            ORDER BY date DESC
        ''', (start_date,))
        
        daily_stats = []
        for row2 in cursor.fetchall():
            daily_stats.append({
                'date': row2[0],
                'samples_loaded': row2[1],
                'samples_exported': row2[2],
                'samples_split': row2[3],
                'total_operations': row2[4]
            })
        
        conn.close()
        
        return {
            'period_days': days,
            'total_records': row[0],
            'unique_samples': row[1],
            'total_loads': row[2],
            'total_exports': row[3],
            'total_splits': row[4],
            'daily_stats': daily_stats,
            'license_key': self.license_key,
            'machine_id': self.machine_id[:16] + '...'
        }
    
    def _start_background_reporter(self):
        """启动后台上报线程（延迟启动，优化性能）"""
        def reporter_thread():
            # 延迟30秒启动，避免影响应用启动
            time.sleep(30)
            
            while True:
                try:
                    # 先刷新批量缓冲区
                    self._flush_batch()
                    
                    # 然后尝试上报
                    self._report_pending()
                except Exception as e:
                    if not self.silent:
                        print(f"[警告] 后台上报错误: {e}")
                
                time.sleep(300)  # 每5分钟尝试上报
        
        if self._reporter_thread is None:
            self._reporter_thread = threading.Thread(target=reporter_thread, daemon=True)
            self._reporter_thread.start()
    
    def _report_pending(self):
        """上报待处理的记录"""
        if not HAS_REQUESTS or not self.pending_reports:
            return
        
        try:
            # 准备上报数据
            report_data = {
                'license_key': self.license_key,
                'machine_id': self.machine_id,
                'records': self.pending_reports[:100],  # 每次最多100条
                'timestamp': datetime.now().isoformat()
            }
            
            # 计算签名
            signature = self._calculate_checksum(report_data)
            report_data['signature'] = signature
            
            # 发送到服务器
            response = requests.post(
                self.SERVER_URL,
                json=report_data,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                # 标记为已上报
                reported_ids = [r['record_id'] for r in self.pending_reports[:100]]
                self._mark_as_reported(reported_ids)
                self.pending_reports = self.pending_reports[100:]
                print(f"[成功] 已上报 {len(reported_ids)} 条使用记录")
            else:
                print(f"[警告] 上报失败: {response.status_code}")
        
        except Exception as e:
            # 网络错误，保留在队列中稍后重试
            pass
    
    def _mark_as_reported(self, record_ids: List[str]):
        """标记记录为已上报"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        report_time = datetime.now().isoformat()
        
        for record_id in record_ids:
            cursor.execute('''
                UPDATE usage_records 
                SET reported = 1, report_time = ?
                WHERE record_id = ?
            ''', (report_time, record_id))
        
        conn.commit()
        conn.close()
    
    def verify_integrity(self) -> Dict:
        """
        验证数据完整性（检测篡改）
        
        返回:
            验证结果
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 获取所有记录
        cursor.execute('''
            SELECT record_id, timestamp, action_type, sample_name, sample_hash, checksum
            FROM usage_records
        ''')
        
        total_records = 0
        valid_records = 0
        invalid_records = []
        
        for row in cursor.fetchall():
            total_records += 1
            
            # 重新计算校验和
            checksum_data = {
                'record_id': row[0],
                'timestamp': row[1],
                'action_type': row[2],
                'sample_name': row[3],
                'sample_hash': row[4]
            }
            expected_checksum = self._calculate_checksum(checksum_data)
            
            if expected_checksum == row[5]:
                valid_records += 1
            else:
                invalid_records.append(row[0])
        
        conn.close()
        
        return {
            'total_records': total_records,
            'valid_records': valid_records,
            'invalid_records': len(invalid_records),
            'integrity_ok': len(invalid_records) == 0,
            'tampered_ids': invalid_records[:10]  # 只返回前10个
        }
    
    def export_usage_report(self, output_file: str, days: int = 30):
        """
        导出使用报告（兼容License Manager导入格式）
        
        参数:
            output_file: 输出文件路径
            days: 统计天数
        """
        stats = self.get_usage_stats(days)
        integrity = self.verify_integrity()
        
        # 计算报告日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 构建兼容License Manager的报告格式
        report = {
            # 必需字段（License Manager导入需要）
            'license_key': self.license_key,
            'machine_id': self.machine_id,
            'report_date': end_date.strftime('%Y-%m-%d'),
            'period_start': start_date.strftime('%Y-%m-%d'),
            'period_end': end_date.strftime('%Y-%m-%d'),
            
            # 使用统计（License Manager期望的格式）
            'usage_stats': {
                'total_loads': stats['total_loads'],
                'total_exports': stats['total_exports'],
                'total_splits': stats['total_splits'],
                'unique_samples': stats['unique_samples'],
                'total_records': stats['total_records'],
                'period_days': days
            },
            
            # 额外信息
            'report_generated': datetime.now().isoformat(),
            'integrity_check': integrity,
            'daily_stats': stats.get('daily_stats', [])
        }
        
        # 使用许可证密钥加密（而不是机器ID）
        # 这样管理员可以用许可证密钥解密
        report_json = json.dumps(report, indent=2, ensure_ascii=False)
        
        # 创建使用许可证密钥的加密器
        if HAS_CRYPTO:
            try:
                salt = self.license_key[:16].encode() if len(self.license_key) >= 16 else (self.license_key * 16)[:16].encode()
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(self.SECRET_SEED))
                cipher = Fernet(key)
                encrypted_report = cipher.encrypt(report_json.encode()).decode()
            except Exception as e:
                if not self.silent:
                    print(f"[警告] 加密失败，使用base64: {e}")
                encrypted_report = base64.b64encode(report_json.encode()).decode()
        else:
            # 回退到base64
            encrypted_report = base64.b64encode(report_json.encode()).decode()
        
        # 保存
        with open(output_file, 'w') as f:
            f.write(encrypted_report)
        
        if not self.silent:
            print(f"[成功] 使用报告已导出: {output_file}")
            print(f"  报告期间: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
            print(f"  样本加载: {stats['total_loads']}")
            print(f"  数据导出: {stats['total_exports']}")
            print(f"  代谢物拆分: {stats['total_splits']}")
            print(f"  唯一样本: {stats['unique_samples']}")
            print(f"  [信息] 报告使用许可证密钥加密，管理员可导入")
        
        return report


# 全局追踪器实例
_tracker_instance = None

def get_tracker(silent: bool = True) -> UsageTracker:
    """获取全局追踪器实例（默认静默模式）"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = UsageTracker(silent=silent)
    return _tracker_instance

def record_sample_load(sample_name: str, n_scans: int = 0, n_mz: int = 0):
    """记录样本加载"""
    tracker = get_tracker()
    tracker.record_usage('load_sample', sample_name, {
        'n_scans': n_scans,
        'n_mz': n_mz
    })

def record_data_export(sample_name: str, export_type: str, n_items: int = 0):
    """记录数据导出"""
    tracker = get_tracker()
    tracker.record_usage('export_data', sample_name, {
        'export_type': export_type,
        'n_items': n_items
    })

def record_metabolite_split(sample_name: str, n_metabolites: int = 0):
    """记录代谢物拆分"""
    tracker = get_tracker()
    tracker.record_usage('split_metabolites', sample_name, {
        'n_metabolites': n_metabolites
    })


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("DESI 使用量追踪系统测试（重构版）")
    print("=" * 60)
    
    # 测试1: 静默模式
    print("\n[TEST 1] 静默模式初始化...")
    tracker = UsageTracker(silent=True)
    print("[成功] 静默模式初始化完成（无输出）")
    
    # 测试2: 批量插入性能
    print("\n[TEST 2] 批量插入性能测试...")
    import time
    start_time = time.time()
    
    for i in range(20):
        tracker.record_usage('load_sample', f'test_sample_{i:03d}', 
                           {'n_scans': 10000, 'n_mz': 1500})
    
    # 强制刷新
    tracker._flush_batch()
    
    elapsed = time.time() - start_time
    print(f"[成功] 20条记录插入耗时: {elapsed:.3f}秒")
    
    # 测试3: 获取统计
    print("\n[TEST 3] 使用统计:")
    stats = tracker.get_usage_stats(30)
    print(f"   总记录数: {stats['total_records']}")
    print(f"   唯一样本数: {stats['unique_samples']}")
    print(f"   加载次数: {stats['total_loads']}")
    print(f"   导出次数: {stats['total_exports']}")
    print(f"   拆分次数: {stats['total_splits']}")
    
    # 测试4: 验证完整性
    print("\n[TEST 4] 完整性验证:")
    integrity = tracker.verify_integrity()
    print(f"   总记录: {integrity['total_records']}")
    print(f"   有效记录: {integrity['valid_records']}")
    print(f"   完整性: {'[成功] 通过' if integrity['integrity_ok'] else '[错误] 发现篡改'}")
    
    # 测试5: 数据库修复
    print("\n[TEST 5] 数据库自动修复功能已集成")
    print("   [信息] 如果数据库损坏，系统会自动备份并重建")
    
    print("\n[成功] 所有测试完成")

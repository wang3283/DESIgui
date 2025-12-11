#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整性验证系统
用于检测使用记录的篡改和数据完整性
"""

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict


@dataclass
class IntegrityCheckResult:
    """完整性检查结果"""
    total_records: int
    valid_records: int
    invalid_records: int
    suspicious_records: List[str]
    integrity_ok: bool
    check_time: str
    overall_checksum: str


@dataclass
class SuspiciousRecord:
    """可疑记录"""
    record_id: str
    timestamp: str
    action_type: str
    sample_name: str
    expected_checksum: str
    actual_checksum: str
    reason: str


class IntegrityVerifier:
    """完整性验证器"""
    
    def __init__(self, db_path: str, machine_id: str, secret_seed: bytes):
        """
        初始化完整性验证器
        
        参数:
            db_path: 数据库路径
            machine_id: 机器ID
            secret_seed: 密钥种子
        """
        self.db_path = db_path
        self.machine_id = machine_id
        self.secret_seed = secret_seed
    
    def calculate_checksum(self, data: Dict[str, Any]) -> str:
        """
        计算数据校验和（增强版）
        
        参数:
            data: 要计算校验和的数据
        
        返回:
            校验和字符串
        """
        # 将数据转为JSON并排序键（确保一致性）
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        
        # 组合机器ID和密钥种子
        combined = f"{data_str}|{self.machine_id}|{self.secret_seed.decode()}"
        
        # 使用SHA256计算哈希
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

    
    def verify_record(self, record: Dict[str, Any]) -> Tuple[bool, str]:
        """
        验证单条记录的完整性
        
        参数:
            record: 记录数据
        
        返回:
            (是否有效, 原因)
        """
        # 提取用于计算校验和的字段
        checksum_data = {
            'record_id': record.get('record_id'),
            'timestamp': record.get('timestamp'),
            'action_type': record.get('action_type'),
            'sample_name': record.get('sample_name'),
            'sample_hash': record.get('sample_hash')
        }
        
        # 计算期望的校验和
        expected_checksum = self.calculate_checksum(checksum_data)
        actual_checksum = record.get('checksum', '')
        
        # 比较校验和
        if expected_checksum == actual_checksum:
            return True, "Valid"
        else:
            return False, f"Checksum mismatch: expected {expected_checksum[:8]}..., got {actual_checksum[:8]}..."
    
    def verify_all_records(self, mark_suspicious: bool = True) -> IntegrityCheckResult:
        """
        批量验证所有记录的完整性
        
        参数:
            mark_suspicious: 是否标记可疑记录
        
        返回:
            完整性检查结果
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取所有记录
        cursor.execute('''
            SELECT record_id, timestamp, action_type, sample_name, 
                   sample_hash, checksum
            FROM usage_records
            ORDER BY timestamp
        ''')
        
        records = cursor.fetchall()
        total_records = len(records)
        valid_records = 0
        suspicious_records = []
        
        # 验证每条记录
        for record in records:
            record_dict = dict(record)
            is_valid, reason = self.verify_record(record_dict)
            
            if is_valid:
                valid_records += 1
            else:
                suspicious_records.append(record_dict['record_id'])
                
                # 标记可疑记录
                if mark_suspicious:
                    self._mark_record_suspicious(
                        conn, 
                        record_dict['record_id'],
                        reason
                    )
        
        # 计算整体校验和
        overall_checksum = self._calculate_overall_checksum(records)
        
        # 保存完整性检查记录
        check_time = datetime.now().isoformat()
        self._save_integrity_check(
            conn,
            total_records,
            valid_records,
            overall_checksum,
            check_time
        )
        
        conn.commit()
        conn.close()
        
        return IntegrityCheckResult(
            total_records=total_records,
            valid_records=valid_records,
            invalid_records=len(suspicious_records),
            suspicious_records=suspicious_records,
            integrity_ok=len(suspicious_records) == 0,
            check_time=check_time,
            overall_checksum=overall_checksum
        )
    
    def _mark_record_suspicious(self, conn: sqlite3.Connection, 
                                record_id: str, reason: str):
        """标记记录为可疑"""
        # 确保suspicious_flag列存在
        cursor = conn.cursor()
        
        # 检查列是否存在
        cursor.execute("PRAGMA table_info(usage_records)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'suspicious_flag' not in columns:
            cursor.execute('''
                ALTER TABLE usage_records 
                ADD COLUMN suspicious_flag INTEGER DEFAULT 0
            ''')
        
        if 'suspicious_reason' not in columns:
            cursor.execute('''
                ALTER TABLE usage_records 
                ADD COLUMN suspicious_reason TEXT
            ''')
        
        # 标记记录
        cursor.execute('''
            UPDATE usage_records 
            SET suspicious_flag = 1, suspicious_reason = ?
            WHERE record_id = ?
        ''', (reason, record_id))
    
    def _calculate_overall_checksum(self, records: List[sqlite3.Row]) -> str:
        """计算所有记录的整体校验和"""
        if not records:
            return hashlib.sha256(b"empty").hexdigest()
        
        # 将所有记录的校验和组合
        combined_checksums = "|".join([
            record['checksum'] for record in records
        ])
        
        return hashlib.sha256(combined_checksums.encode()).hexdigest()
    
    def _save_integrity_check(self, conn: sqlite3.Connection,
                              total_records: int, valid_records: int,
                              checksum: str, check_time: str):
        """保存完整性检查记录"""
        cursor = conn.cursor()
        
        # 确保表存在
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS integrity_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_time TEXT NOT NULL,
                total_records INTEGER NOT NULL,
                valid_records INTEGER NOT NULL,
                invalid_records INTEGER NOT NULL,
                overall_checksum TEXT NOT NULL
            )
        ''')
        
        invalid_records = total_records - valid_records
        
        cursor.execute('''
            INSERT INTO integrity_checks 
            (check_time, total_records, valid_records, invalid_records, overall_checksum)
            VALUES (?, ?, ?, ?, ?)
        ''', (check_time, total_records, valid_records, invalid_records, checksum))
    
    def get_suspicious_records(self) -> List[SuspiciousRecord]:
        """获取所有可疑记录"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 检查列是否存在
        cursor.execute("PRAGMA table_info(usage_records)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'suspicious_flag' not in columns:
            conn.close()
            return []
        
        # 查询可疑记录
        cursor.execute('''
            SELECT record_id, timestamp, action_type, sample_name, 
                   checksum, suspicious_reason
            FROM usage_records
            WHERE suspicious_flag = 1
            ORDER BY timestamp DESC
        ''')
        
        suspicious_records = []
        for row in cursor.fetchall():
            record_dict = dict(row)
            
            # 重新计算期望的校验和
            checksum_data = {
                'record_id': record_dict['record_id'],
                'timestamp': record_dict['timestamp'],
                'action_type': record_dict['action_type'],
                'sample_name': record_dict['sample_name'],
                'sample_hash': ''  # 需要从数据库获取
            }
            expected_checksum = self.calculate_checksum(checksum_data)
            
            suspicious_records.append(SuspiciousRecord(
                record_id=record_dict['record_id'],
                timestamp=record_dict['timestamp'],
                action_type=record_dict['action_type'],
                sample_name=record_dict['sample_name'],
                expected_checksum=expected_checksum,
                actual_checksum=record_dict['checksum'],
                reason=record_dict.get('suspicious_reason', 'Unknown')
            ))
        
        conn.close()
        return suspicious_records
    
    def clear_suspicious_flag(self, record_id: str) -> bool:
        """清除记录的可疑标记（管理员确认后）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE usage_records 
            SET suspicious_flag = 0, suspicious_reason = NULL
            WHERE record_id = ?
        ''', (record_id,))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected > 0
    
    def generate_integrity_report(self, output_file: str = None) -> Dict:
        """
        生成完整性报告
        
        参数:
            output_file: 输出文件路径（可选）
        
        返回:
            报告数据
        """
        # 执行完整性检查
        check_result = self.verify_all_records(mark_suspicious=False)
        
        # 获取可疑记录详情
        suspicious_records = self.get_suspicious_records()
        
        # 获取历史检查记录
        history = self._get_check_history(limit=10)
        
        # 生成报告
        report = {
            'report_generated': datetime.now().isoformat(),
            'machine_id': self.machine_id[:16] + '...',
            'current_check': asdict(check_result),
            'suspicious_records': [asdict(sr) for sr in suspicious_records],
            'check_history': history,
            'summary': {
                'total_records': check_result.total_records,
                'valid_records': check_result.valid_records,
                'invalid_records': check_result.invalid_records,
                'integrity_rate': (
                    check_result.valid_records / check_result.total_records * 100
                    if check_result.total_records > 0 else 100.0
                )
            }
        }
        
        # 保存到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report
    
    def _get_check_history(self, limit: int = 10) -> List[Dict]:
        """获取历史检查记录"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='integrity_checks'
        ''')
        
        if not cursor.fetchone():
            conn.close()
            return []
        
        cursor.execute('''
            SELECT check_time, total_records, valid_records, 
                   invalid_records, overall_checksum
            FROM integrity_checks
            ORDER BY check_time DESC
            LIMIT ?
        ''', (limit,))
        
        history = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return history


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("完整性验证系统测试")
    print("=" * 60)
    
    # 创建测试数据库
    import tempfile
    import os
    
    test_db = tempfile.mktemp(suffix='.db')
    
    # 初始化数据库
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
    
    # 创建验证器
    machine_id = "test_machine_12345"
    secret_seed = b"TEST_SECRET_KEY"
    verifier = IntegrityVerifier(test_db, machine_id, secret_seed)
    
    # 插入测试记录
    print("\n[TEST 1] 插入有效记录...")
    for i in range(5):
        record_data = {
            'record_id': f'REC-{i:03d}',
            'timestamp': datetime.now().isoformat(),
            'action_type': 'load_sample',
            'sample_name': f'sample_{i}',
            'sample_hash': hashlib.md5(f'sample_{i}'.encode()).hexdigest()
        }
        checksum = verifier.calculate_checksum(record_data)
        
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
    
    # 插入篡改记录
    print("[TEST 2] 插入篡改记录...")
    tampered_data = {
        'record_id': 'REC-TAMPERED',
        'timestamp': datetime.now().isoformat(),
        'action_type': 'load_sample',
        'sample_name': 'tampered_sample',
        'sample_hash': hashlib.md5(b'tampered_sample').hexdigest()
    }
    fake_checksum = "0" * 64  # 伪造的校验和
    
    cursor.execute('''
        INSERT INTO usage_records 
        (record_id, timestamp, action_type, sample_name, sample_hash, checksum)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        tampered_data['record_id'],
        tampered_data['timestamp'],
        tampered_data['action_type'],
        tampered_data['sample_name'],
        tampered_data['sample_hash'],
        fake_checksum
    ))
    
    conn.commit()
    conn.close()
    
    # 测试完整性验证
    print("\n[TEST 3] 批量验证完整性...")
    result = verifier.verify_all_records(mark_suspicious=True)
    
    print(f"   总记录数: {result.total_records}")
    print(f"   有效记录: {result.valid_records}")
    print(f"   无效记录: {result.invalid_records}")
    print(f"   完整性: {'[成功] 通过' if result.integrity_ok else '[警告] 发现篡改'}")
    
    if result.suspicious_records:
        print(f"   可疑记录: {result.suspicious_records}")
    
    # 测试生成报告
    print("\n[TEST 4] 生成完整性报告...")
    report_file = tempfile.mktemp(suffix='.json')
    report = verifier.generate_integrity_report(report_file)
    
    print(f"   报告已保存: {report_file}")
    print(f"   完整性率: {report['summary']['integrity_rate']:.2f}%")
    
    # 测试获取可疑记录
    print("\n[TEST 5] 获取可疑记录...")
    suspicious = verifier.get_suspicious_records()
    print(f"   可疑记录数: {len(suspicious)}")
    
    for sr in suspicious:
        print(f"   - {sr.record_id}: {sr.reason}")
    
    # 清理
    os.unlink(test_db)
    os.unlink(report_file)
    
    print("\n[成功] 所有测试完成")

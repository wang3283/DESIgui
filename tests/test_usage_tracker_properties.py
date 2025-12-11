#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用追踪属性测试 - 使用Hypothesis进行Property-Based Testing

测试属性:
- 属性10: 使用记录自动性
- 属性16: 校验和存在性
"""

import pytest
from hypothesis import given, strategies as st, settings
import sys
import os
import tempfile
import shutil
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from usage_tracker import UsageTracker


class TestUsageTrackerProperties:
    """使用追踪属性测试"""
    
    def setup_method(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """每个测试后清理临时目录"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @given(
        action_type=st.sampled_from(['load_sample', 'export_data', 'split_metabolites']),
        sample_name=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=('Cs',))),
        n_operations=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=50)
    def test_property_10_usage_record_automaticity(self, action_type, sample_name, n_operations):
        """
        **Feature: commercial-billing-system, Property 10: 使用记录自动性**
        **Validates: Requirements 4.2**
        
        对于任意用户操作（加载样本、导出数据、拆分代谢物），系统应该自动创建对应的使用记录
        """
        # 创建追踪器
        tracker = UsageTracker(data_dir=self.temp_dir, silent=True)
        
        # 记录多次操作
        record_ids = []
        for i in range(n_operations):
            record_id = tracker.record_usage(action_type, f"{sample_name}_{i}")
            record_ids.append(record_id)
        
        # 强制刷新缓冲区
        tracker._flush_batch()
        
        # 验证: 所有操作都应该被记录
        stats = tracker.get_usage_stats(1)
        
        # 检查记录数量
        assert stats['total_records'] >= n_operations, \
            f"记录数量不足: {stats['total_records']} < {n_operations}"
        
        # 检查操作类型统计
        if action_type == 'load_sample':
            assert stats['total_loads'] >= n_operations
        elif action_type == 'export_data':
            assert stats['total_exports'] >= n_operations
        elif action_type == 'split_metabolites':
            assert stats['total_splits'] >= n_operations
    
    @given(
        sample_name=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=('Cs',))),
        n_records=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=50)
    def test_property_16_checksum_existence(self, sample_name, n_records):
        """
        **Feature: commercial-billing-system, Property 16: 校验和存在性**
        **Validates: Requirements 6.1**
        
        对于任意使用记录，系统应该计算并存储基于机器ID的校验和
        """
        # 创建追踪器
        tracker = UsageTracker(data_dir=self.temp_dir, silent=True)
        
        # 记录多次操作
        for i in range(n_records):
            tracker.record_usage('load_sample', f"{sample_name}_{i}", 
                               {'test_data': f'value_{i}'})
        
        # 强制刷新
        tracker._flush_batch()
        
        # 验证完整性
        integrity = tracker.verify_integrity()
        
        # 验证: 所有记录都应该有校验和
        assert integrity['total_records'] >= n_records, \
            f"记录数量不足: {integrity['total_records']} < {n_records}"
        
        # 验证: 所有记录的校验和都应该有效
        assert integrity['valid_records'] == integrity['total_records'], \
            f"存在无效校验和: {integrity['invalid_records']} 条记录"
        
        # 验证: 完整性检查应该通过
        assert integrity['integrity_ok'], "完整性检查失败"
    
    @given(
        sample_names=st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',))),
            min_size=1,
            max_size=20,
            unique=True  # 确保列表中的元素唯一
        )
    )
    @settings(max_examples=30)
    def test_unique_sample_counting(self, sample_names):
        """
        测试唯一样本统计
        验证系统能正确统计唯一样本数（去重）
        """
        # 使用新的临时目录确保干净的环境
        import tempfile
        temp_dir2 = tempfile.mkdtemp()
        
        try:
            tracker = UsageTracker(data_dir=temp_dir2, silent=True)
            
            # 记录样本（每个样本记录两次，测试去重）
            for sample_name in sample_names:
                tracker.record_usage('load_sample', sample_name)
                tracker.record_usage('load_sample', sample_name)  # 重复记录
            
            tracker._flush_batch()
            
            # 获取统计
            stats = tracker.get_usage_stats(1)
            
            # 验证: 唯一样本数应该等于去重后的数量
            expected_unique = len(sample_names)
            assert stats['unique_samples'] == expected_unique, \
                f"唯一样本统计错误: {stats['unique_samples']} != {expected_unique}"
        finally:
            import shutil
            if os.path.exists(temp_dir2):
                shutil.rmtree(temp_dir2)
    
    def test_batch_insert_performance(self):
        """
        测试批量插入性能
        验证批量插入比单条插入更快
        """
        import time
        
        # 测试批量插入
        tracker_batch = UsageTracker(data_dir=self.temp_dir, silent=True)
        tracker_batch._batch_size = 10
        
        start = time.time()
        for i in range(50):
            tracker_batch.record_usage('load_sample', f'sample_{i}')
        tracker_batch._flush_batch()
        batch_time = time.time() - start
        
        # 验证记录数
        stats = tracker_batch.get_usage_stats(1)
        assert stats['total_records'] == 50
        
        # 批量插入应该很快（< 1秒）
        assert batch_time < 1.0, f"批量插入太慢: {batch_time:.3f}秒"
    
    def test_database_repair_functionality(self):
        """
        测试数据库自动修复功能
        验证损坏的数据库能被自动修复
        """
        # 创建追踪器
        tracker1 = UsageTracker(data_dir=self.temp_dir, silent=True)
        tracker1.record_usage('load_sample', 'test_sample')
        tracker1._flush_batch()
        del tracker1  # 确保连接关闭
        
        # 模拟数据库损坏（写入无效数据）
        db_path = Path(self.temp_dir) / "usage_data.db"
        import time
        time.sleep(0.1)  # 等待文件系统同步
        
        with open(db_path, 'wb') as f:
            f.write(b'CORRUPTED DATA')
        
        # 重新初始化应该触发修复
        tracker2 = UsageTracker(data_dir=self.temp_dir, silent=True)
        
        # 验证: 新数据库应该可以正常工作（能记录数据）
        try:
            tracker2.record_usage('load_sample', 'new_sample')
            tracker2._flush_batch()
            # 如果能执行到这里，说明修复成功
            repair_success = True
        except Exception as e:
            repair_success = False
        
        assert repair_success, "修复后的数据库应该可以记录数据"
        
        # 验证备份文件存在
        backup_path = db_path.with_suffix('.db.backup')
        assert backup_path.exists(), "应该创建备份文件"
    
    def test_silent_mode(self):
        """
        测试静默模式
        验证静默模式不输出任何信息
        """
        import io
        import sys
        
        # 捕获标准输出
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            tracker = UsageTracker(data_dir=self.temp_dir, silent=True)
            tracker.record_usage('load_sample', 'test')
            tracker._flush_batch()
            
            output = sys.stdout.getvalue()
            
            # 验证: 静默模式不应该有输出（除了警告）
            # 允许有WARNING，但不应该有INFO或SUCCESS
            assert '[INFO]' not in output, "静默模式不应该输出INFO"
            assert '[SUCCESS]' not in output, "静默模式不应该输出SUCCESS"
        
        finally:
            sys.stdout = old_stdout
    
    @given(
        n_operations=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=20)
    def test_checksum_tampering_detection(self, n_operations):
        """
        测试校验和篡改检测
        验证系统能检测到数据被篡改
        """
        # 使用新的临时目录
        import tempfile
        temp_dir2 = tempfile.mkdtemp()
        
        try:
            tracker = UsageTracker(data_dir=temp_dir2, silent=True)
            
            # 记录操作
            for i in range(n_operations):
                tracker.record_usage('load_sample', f'sample_{i}')
            tracker._flush_batch()
            
            # 验证初始完整性
            integrity1 = tracker.verify_integrity()
            assert integrity1['integrity_ok'], \
                f"初始数据应该完整: valid={integrity1['valid_records']}, invalid={integrity1['invalid_records']}"
            
            # 篡改数据库（修改一条记录的checksum）
            import sqlite3
            conn = sqlite3.connect(str(Path(temp_dir2) / "usage_data.db"))
            cursor = conn.cursor()
            cursor.execute("UPDATE usage_records SET checksum = 'TAMPERED' WHERE id = 1")
            conn.commit()
            conn.close()
            
            # 重新验证完整性
            integrity2 = tracker.verify_integrity()
            
            # 验证: 应该检测到篡改
            assert not integrity2['integrity_ok'], "应该检测到数据被篡改"
            assert integrity2['invalid_records'] >= 1, "应该有至少1条无效记录"
        finally:
            import shutil
            if os.path.exists(temp_dir2):
                shutil.rmtree(temp_dir2)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

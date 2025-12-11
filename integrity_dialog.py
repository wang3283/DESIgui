#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整性验证对话框
用于管理员查看和处理数据完整性问题
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QTextEdit, QGroupBox,
    QProgressBar, QMessageBox, QHeaderView, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor
from datetime import datetime
from typing import Dict, List
import json


class IntegrityCheckThread(QThread):
    """完整性检查线程"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    
    def __init__(self, verifier):
        super().__init__()
        self.verifier = verifier
    
    def run(self):
        """执行完整性检查"""
        try:
            self.progress.emit(10, "正在读取数据库...")
            
            self.progress.emit(30, "正在验证记录...")
            result = self.verifier.verify_all_records(mark_suspicious=True)
            
            self.progress.emit(70, "正在生成报告...")
            report = self.verifier.generate_integrity_report()
            
            self.progress.emit(100, "完成")
            self.finished.emit(report)
            
        except Exception as e:
            self.finished.emit({'error': str(e)})


class IntegrityDialog(QDialog):
    """完整性验证对话框"""
    
    def __init__(self, verifier, parent=None):
        super().__init__(parent)
        self.verifier = verifier
        self.current_report = None
        
        self.setWindowTitle("数据完整性验证")
        self.setMinimumSize(900, 700)
        
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("数据完整性验证系统")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        # 摘要面板
        summary_group = self._create_summary_panel()
        layout.addWidget(summary_group)
        
        # 可疑记录表格
        suspicious_group = self._create_suspicious_panel()
        layout.addWidget(suspicious_group)
        
        # 历史记录
        history_group = self._create_history_panel()
        layout.addWidget(history_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.check_btn = QPushButton("执行完整性检查")
        self.check_btn.clicked.connect(self.run_integrity_check)
        button_layout.addWidget(self.check_btn)
        
        self.export_btn = QPushButton("导出报告")
        self.export_btn.clicked.connect(self.export_report)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_data)
        button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # 初始加载数据
        self.refresh_data()
    
    def _create_summary_panel(self) -> QGroupBox:
        """创建摘要面板"""
        group = QGroupBox("完整性摘要")
        layout = QHBoxLayout(group)
        
        self.total_label = QLabel("总记录数: -")
        self.valid_label = QLabel("有效记录: -")
        self.invalid_label = QLabel("无效记录: -")
        self.rate_label = QLabel("完整性率: -")
        
        layout.addWidget(self.total_label)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.valid_label)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.invalid_label)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.rate_label)
        layout.addStretch()
        
        return group
    
    def _create_suspicious_panel(self) -> QGroupBox:
        """创建可疑记录面板"""
        group = QGroupBox("可疑记录")
        layout = QVBoxLayout(group)
        
        # 表格
        self.suspicious_table = QTableWidget()
        self.suspicious_table.setColumnCount(5)
        self.suspicious_table.setHorizontalHeaderLabels([
            "记录ID", "时间", "操作类型", "样本名称", "原因"
        ])
        
        header = self.suspicious_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        
        self.suspicious_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.suspicious_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.suspicious_table)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        clear_btn = QPushButton("清除标记")
        clear_btn.clicked.connect(self.clear_suspicious_flag)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return group
    
    def _create_history_panel(self) -> QGroupBox:
        """创建历史记录面板"""
        group = QGroupBox("检查历史")
        layout = QVBoxLayout(group)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "检查时间", "总记录", "有效记录", "无效记录", "整体校验和"
        ])
        
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        
        self.history_table.setMaximumHeight(150)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.history_table)
        
        return group
    
    def run_integrity_check(self):
        """执行完整性检查"""
        # 禁用按钮
        self.check_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建并启动检查线程
        self.check_thread = IntegrityCheckThread(self.verifier)
        self.check_thread.progress.connect(self.update_progress)
        self.check_thread.finished.connect(self.check_finished)
        self.check_thread.start()
    
    def update_progress(self, value: int, message: str):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.statusBar().showMessage(message) if hasattr(self, 'statusBar') else None
    
    def check_finished(self, report: Dict):
        """检查完成"""
        self.check_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if 'error' in report:
            QMessageBox.critical(
                self,
                "错误",
                f"完整性检查失败:\n{report['error']}"
            )
            return
        
        self.current_report = report
        self.export_btn.setEnabled(True)
        
        # 更新显示
        self.refresh_data()
        
        # 显示结果
        summary = report.get('summary', {})
        integrity_rate = summary.get('integrity_rate', 0)
        
        if integrity_rate == 100.0:
            QMessageBox.information(
                self,
                "完整性检查",
                f"[成功] 所有记录完整性验证通过!\n\n"
                f"总记录数: {summary.get('total_records', 0)}\n"
                f"有效记录: {summary.get('valid_records', 0)}\n"
                f"完整性率: {integrity_rate:.2f}%"
            )
        else:
            QMessageBox.warning(
                self,
                "完整性检查",
                f"[警告] 发现可疑记录!\n\n"
                f"总记录数: {summary.get('total_records', 0)}\n"
                f"有效记录: {summary.get('valid_records', 0)}\n"
                f"无效记录: {summary.get('invalid_records', 0)}\n"
                f"完整性率: {integrity_rate:.2f}%\n\n"
                f"请检查可疑记录列表。"
            )
    
    def refresh_data(self):
        """刷新数据显示"""
        try:
            # 获取最新报告（如果没有则生成）
            if not self.current_report:
                self.current_report = self.verifier.generate_integrity_report()
            
            # 更新摘要
            summary = self.current_report.get('summary', {})
            self.total_label.setText(f"总记录数: {summary.get('total_records', 0)}")
            self.valid_label.setText(f"有效记录: {summary.get('valid_records', 0)}")
            self.invalid_label.setText(f"无效记录: {summary.get('invalid_records', 0)}")
            
            rate = summary.get('integrity_rate', 0)
            rate_text = f"完整性率: {rate:.2f}%"
            self.rate_label.setText(rate_text)
            
            # 根据完整性率设置颜色
            if rate == 100.0:
                self.rate_label.setStyleSheet("color: green; font-weight: bold;")
            elif rate >= 95.0:
                self.rate_label.setStyleSheet("color: orange; font-weight: bold;")
            else:
                self.rate_label.setStyleSheet("color: red; font-weight: bold;")
            
            # 更新可疑记录表格
            self._update_suspicious_table()
            
            # 更新历史记录表格
            self._update_history_table()
            
        except Exception as e:
            QMessageBox.warning(self, "警告", f"刷新数据失败: {e}")
    
    def _update_suspicious_table(self):
        """更新可疑记录表格"""
        suspicious_records = self.current_report.get('suspicious_records', [])
        
        self.suspicious_table.setRowCount(len(suspicious_records))
        
        for row, record in enumerate(suspicious_records):
            self.suspicious_table.setItem(row, 0, QTableWidgetItem(record.get('record_id', '')))
            self.suspicious_table.setItem(row, 1, QTableWidgetItem(record.get('timestamp', '')))
            self.suspicious_table.setItem(row, 2, QTableWidgetItem(record.get('action_type', '')))
            self.suspicious_table.setItem(row, 3, QTableWidgetItem(record.get('sample_name', '')))
            self.suspicious_table.setItem(row, 4, QTableWidgetItem(record.get('reason', '')))
            
            # 设置行背景色
            for col in range(5):
                item = self.suspicious_table.item(row, col)
                if item:
                    item.setBackground(QColor(255, 200, 200))
    
    def _update_history_table(self):
        """更新历史记录表格"""
        history = self.current_report.get('check_history', [])
        
        self.history_table.setRowCount(len(history))
        
        for row, check in enumerate(history):
            self.history_table.setItem(row, 0, QTableWidgetItem(check.get('check_time', '')))
            self.history_table.setItem(row, 1, QTableWidgetItem(str(check.get('total_records', 0))))
            self.history_table.setItem(row, 2, QTableWidgetItem(str(check.get('valid_records', 0))))
            self.history_table.setItem(row, 3, QTableWidgetItem(str(check.get('invalid_records', 0))))
            
            checksum = check.get('overall_checksum', '')
            self.history_table.setItem(row, 4, QTableWidgetItem(checksum[:16] + '...'))
    
    def clear_suspicious_flag(self):
        """清除可疑标记"""
        selected_rows = self.suspicious_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先选择要清除标记的记录")
            return
        
        reply = QMessageBox.question(
            self,
            "确认",
            f"确定要清除 {len(selected_rows)} 条记录的可疑标记吗?\n\n"
            "这将表示您已确认这些记录是有效的。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            cleared_count = 0
            
            for index in selected_rows:
                row = index.row()
                record_id = self.suspicious_table.item(row, 0).text()
                
                if self.verifier.clear_suspicious_flag(record_id):
                    cleared_count += 1
            
            QMessageBox.information(
                self,
                "完成",
                f"已清除 {cleared_count} 条记录的可疑标记"
            )
            
            # 刷新显示
            self.current_report = None
            self.refresh_data()
    
    def export_report(self):
        """导出报告"""
        if not self.current_report:
            QMessageBox.information(self, "提示", "请先执行完整性检查")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出完整性报告",
            f"integrity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON文件 (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.current_report, f, indent=2, ensure_ascii=False)
                
                QMessageBox.information(
                    self,
                    "成功",
                    f"报告已导出到:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "错误",
                    f"导出失败:\n{e}"
                )


# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    import tempfile
    import sqlite3
    import hashlib
    from integrity_verifier import IntegrityVerifier
    
    app = QApplication(sys.argv)
    
    # 创建测试数据库
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
    
    # 创建验证器
    machine_id = "test_machine_12345"
    secret_seed = b"TEST_SECRET_KEY"
    verifier = IntegrityVerifier(test_db, machine_id, secret_seed)
    
    # 插入测试数据
    for i in range(10):
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
    
    conn.commit()
    conn.close()
    
    # 显示对话框
    dialog = IntegrityDialog(verifier)
    dialog.exec_()
    
    # 清理
    import os
    os.unlink(test_db)

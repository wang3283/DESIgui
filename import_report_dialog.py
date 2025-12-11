#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用报告导入对话框

支持拖拽导入、多种解密方法、进度显示和重复检测
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QFileDialog, QMessageBox, QGroupBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QDragEnterEvent, QDropEvent

from database_manager import DatabaseManager
from data_encryptor import DataEncryptor, MultiKeyDecryptor
import json


class ImportWorker(QThread):
    """导入工作线程"""
    
    progress = pyqtSignal(int, str)  # 进度百分比, 状态消息
    finished = pyqtSignal(dict)  # 导入结果
    error = pyqtSignal(str)  # 错误消息
    
    def __init__(self, file_path: str, db_manager: DatabaseManager):
        super().__init__()
        self.file_path = file_path
        self.db_manager = db_manager
    
    def run(self):
        """执行导入"""
        try:
            self.progress.emit(10, "正在读取文件...")
            
            # 读取加密文件
            with open(self.file_path, 'rb') as f:
                encrypted_data = f.read()
            
            self.progress.emit(20, "正在尝试解密...")
            
            # 尝试解密
            decrypted_data = self._try_decrypt(encrypted_data)
            
            if not decrypted_data:
                self.error.emit("无法解密文件。请确认文件格式正确或提供正确的解密密钥。")
                return
            
            self.progress.emit(40, "解密成功，正在解析数据...")
            
            # 解析JSON数据
            try:
                report_data = json.loads(decrypted_data)
            except json.JSONDecodeError as e:
                self.error.emit(f"数据格式错误: {str(e)}")
                return
            
            self.progress.emit(60, "正在验证数据...")
            
            # 验证数据格式
            if not self._validate_report(report_data):
                self.error.emit("报告数据格式不完整或无效")
                return
            
            self.progress.emit(70, "正在检查重复...")
            
            # 检查重复
            is_duplicate = self._check_duplicate(report_data)
            
            self.progress.emit(80, "正在保存到数据库...")
            
            # 保存到数据库
            result = self._save_to_database(report_data, is_duplicate)
            
            self.progress.emit(100, "导入完成")
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(f"导入失败: {str(e)}")
    
    def _try_decrypt(self, encrypted_data: bytes) -> Optional[str]:
        """尝试多种方法解密"""
        # 将bytes转为string
        if isinstance(encrypted_data, bytes):
            encrypted_str = encrypted_data.decode('utf-8')
        else:
            encrypted_str = encrypted_data
        
        # 获取所有已知的机器ID和许可证密钥
        customers = self.db_manager.list_customers()
        
        # 方法1: 尝试使用所有客户的许可证密钥解密
        for customer in customers:
            license_key = customer['license_key']
            try:
                # 使用DataEncryptor解密
                encryptor = DataEncryptor(license_key=license_key)
                decrypted = encryptor.decrypt(encrypted_str)
                
                if decrypted:
                    # 验证是否为有效JSON
                    try:
                        json.loads(decrypted)
                        return decrypted
                    except:
                        continue
            except:
                continue
        
        # 方法2: 尝试使用机器ID解密（如果有的话）
        # 从usage_records表中获取已知的machine_id
        try:
            machine_ids = self.db_manager.fetchall('''
                SELECT DISTINCT machine_id FROM usage_records
                WHERE machine_id IS NOT NULL
            ''')
            
            for row in machine_ids:
                machine_id = row['machine_id']
                try:
                    encryptor = DataEncryptor(machine_id=machine_id)
                    decrypted = encryptor.decrypt(encrypted_str)
                    
                    if decrypted:
                        try:
                            json.loads(decrypted)
                            return decrypted
                        except:
                            continue
                except:
                    continue
        except:
            pass
        
        # 方法3: 尝试base64解码（向后兼容）
        try:
            import base64
            decoded = base64.b64decode(encrypted_str.encode()).decode('utf-8')
            # 验证是否为有效JSON
            json.loads(decoded)
            return decoded
        except:
            pass
        
        return None
    
    def _validate_report(self, report_data: Dict) -> bool:
        """验证报告数据格式"""
        required_fields = ['license_key', 'machine_id', 'report_date', 'usage_stats']
        
        for field in required_fields:
            if field not in report_data:
                return False
        
        # 验证usage_stats
        usage_stats = report_data.get('usage_stats', {})
        if not isinstance(usage_stats, dict):
            return False
        
        return True
    
    def _check_duplicate(self, report_data: Dict) -> bool:
        """检查是否为重复报告"""
        license_key = report_data['license_key']
        report_date = report_data['report_date']
        machine_id = report_data['machine_id']
        
        # 查询数据库
        existing = self.db_manager.fetchone('''
            SELECT id FROM usage_records 
            WHERE license_key = ? AND report_date = ? AND machine_id = ?
        ''', (license_key, report_date, machine_id))
        
        return existing is not None
    
    def _save_to_database(self, report_data: Dict, is_duplicate: bool) -> Dict:
        """保存到数据库"""
        license_key = report_data['license_key']
        machine_id = report_data['machine_id']
        usage_stats = report_data['usage_stats']
        
        # 查找客户
        customer = self.db_manager.fetchone(
            "SELECT customer_id, name FROM customers WHERE license_key = ?",
            (license_key,)
        )
        
        if not customer:
            return {
                'success': False,
                'error': f"未找到许可证密钥对应的客户: {license_key}",
                'is_duplicate': is_duplicate
            }
        
        customer_id = customer['customer_id']
        customer_name = customer['name']
        
        # 如果是重复报告，返回提示但包含完整信息
        if is_duplicate:
            return {
                'success': False,
                'error': "重复的报告，已跳过",
                'is_duplicate': True,
                'customer_id': customer_id,
                'customer_name': customer_name,
                'license_key': license_key,
                'machine_id': machine_id,
                'report_date': report_data['report_date'],
                'usage_stats': usage_stats
            }
        
        # 构建使用记录
        usage_record = {
            'customer_id': customer_id,
            'license_key': license_key,
            'machine_id': machine_id,
            'report_date': report_data['report_date'],
            'period_start': report_data.get('period_start'),
            'period_end': report_data.get('period_end'),
            'total_samples_loaded': usage_stats.get('total_loads', 0),
            'total_exports': usage_stats.get('total_exports', 0),
            'total_splits': usage_stats.get('total_splits', 0),
            'unique_samples': usage_stats.get('unique_samples', 0),
            'imported_at': datetime.now().isoformat(),
            'report_file': Path(self.file_path).name
        }
        
        # 保存到数据库
        self.db_manager.add_usage_record(usage_record)
        
        return {
            'success': True,
            'customer_id': customer_id,
            'customer_name': customer_name,
            'machine_id': machine_id,
            'usage_stats': usage_stats,
            'is_duplicate': False
        }


class ImportReportDialog(QDialog):
    """导入使用报告对话框"""
    
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.worker = None
        self.init_ui()
        
        # 启用拖拽
        self.setAcceptDrops(True)
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("导入使用报告")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("导入客户使用报告")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # 说明
        info_label = QLabel(
            "支持拖拽.enc文件到此窗口，或点击按钮选择文件。\n"
            "系统将自动尝试解密并识别客户。"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 拖拽区域
        drop_zone = QGroupBox("拖拽文件到此处")
        drop_zone.setMinimumHeight(100)
        drop_zone.setAlignment(Qt.AlignCenter)
        drop_zone.setStyleSheet("""
            QGroupBox {
                border: 2px dashed #999;
                border-radius: 5px;
                margin-top: 10px;
                font-size: 12pt;
                color: #666;
            }
        """)
        drop_zone_layout = QVBoxLayout(drop_zone)
        drop_label = QLabel("将.enc文件拖拽到此处\n或点击下方按钮选择文件")
        drop_label.setAlignment(Qt.AlignCenter)
        drop_label.setStyleSheet("border: none; color: #666;")
        drop_zone_layout.addWidget(drop_label)
        layout.addWidget(drop_zone)
        
        # 选择文件按钮
        select_btn = QPushButton("选择文件...")
        select_btn.clicked.connect(self.select_file)
        layout.addWidget(select_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)
        
        # 结果显示
        result_group = QGroupBox("导入结果")
        result_layout = QVBoxLayout(result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(150)
        result_layout.addWidget(self.result_text)
        layout.addWidget(result_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """拖拽放下事件"""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        
        # 过滤.enc文件
        enc_files = [f for f in files if f.endswith('.enc')]
        
        if enc_files:
            self.import_file(enc_files[0])
        else:
            QMessageBox.warning(self, "警告", "请拖拽.enc格式的使用报告文件")
    
    def select_file(self):
        """选择文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择使用报告文件",
            "",
            "加密报告文件 (*.enc);;所有文件 (*.*)"
        )
        
        if file_path:
            self.import_file(file_path)
    
    def import_file(self, file_path: str):
        """导入文件"""
        # 显示进度
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setVisible(True)
        self.status_label.setText("正在导入...")
        self.result_text.clear()
        
        # 禁用按钮
        self.close_btn.setEnabled(False)
        
        # 创建工作线程
        self.worker = ImportWorker(file_path, self.db_manager)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def on_progress(self, value: int, message: str):
        """进度更新"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def on_finished(self, result: Dict):
        """导入完成"""
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        self.close_btn.setEnabled(True)
        
        if result['success']:
            # 成功
            summary = f"[成功] 导入成功\n\n"
            summary += f"客户: {result['customer_name']} ({result['customer_id']})\n"
            summary += f"机器ID: {result['machine_id']}\n\n"
            summary += "使用统计:\n"
            stats = result['usage_stats']
            summary += f"  - 样本加载: {stats.get('total_loads', 0)}\n"
            summary += f"  - 数据导出: {stats.get('total_exports', 0)}\n"
            summary += f"  - 代谢物拆分: {stats.get('total_splits', 0)}\n"
            summary += f"  - 唯一样本数: {stats.get('unique_samples', 0)}\n"
            
            self.result_text.setPlainText(summary)
            
            # 通知父窗口刷新
            if self.parent():
                self.parent().refresh_data()
        else:
            # 失败
            error_msg = f"[错误] 导入失败\n\n"
            error_msg += f"原因: {result.get('error', '未知错误')}\n"
            
            if result.get('is_duplicate'):
                error_msg += "\n[信息] 这是一个重复的报告\n"
                error_msg += f"客户: {result.get('customer_name', 'N/A')}\n"
                error_msg += f"报告日期: {result.get('report_date', 'N/A')}\n"
                error_msg += f"机器ID: {result.get('machine_id', 'N/A')}\n\n"
                
                # 显示使用统计供参考
                if 'usage_stats' in result:
                    stats = result['usage_stats']
                    error_msg += "报告内容:\n"
                    error_msg += f"  - 样本加载: {stats.get('total_loads', 0)}\n"
                    error_msg += f"  - 数据导出: {stats.get('total_exports', 0)}\n"
                    error_msg += f"  - 代谢物拆分: {stats.get('total_splits', 0)}\n"
                    error_msg += f"  - 唯一样本数: {stats.get('unique_samples', 0)}\n\n"
                
                error_msg += "[提示] 如需重新导入，请先在数据库中删除旧记录：\n"
                error_msg += f"  1. 在许可证管理器中选择客户 '{result.get('customer_name', '')}'\n"
                error_msg += f"  2. 查看使用记录，找到日期为 {result.get('report_date', '')} 的记录\n"
                error_msg += f"  3. 删除该记录后重新导入\n"
            
            self.result_text.setPlainText(error_msg)
    
    def on_error(self, error_message: str):
        """导入错误"""
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        self.close_btn.setEnabled(True)
        
        error_text = f"[错误] 导入失败\n\n{error_message}"
        self.result_text.setPlainText(error_text)
        
        QMessageBox.critical(self, "导入失败", error_message)


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 测试对话框
    db = DatabaseManager("test_admin.db", mode='admin')
    dialog = ImportReportDialog(db)
    dialog.exec_()
    
    db.close()

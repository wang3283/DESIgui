#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
License验证对话框 - 用于客户端License验证和管理
"""

from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QGroupBox, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from license_manager_core import LicenseValidator


class LicenseReminderDialog(QDialog):
    """许可证到期提醒对话框"""
    
    def __init__(self, days_left: int, license_key: str, parent=None):
        super().__init__(parent)
        self.days_left = days_left
        self.license_key = license_key
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("许可证到期提醒")
        self.setModal(True)
        self.resize(500, 300)
        
        layout = QVBoxLayout(self)
        
        # 根据剩余天数显示不同级别的提醒
        _, level = LicenseValidator.should_show_reminder(self.days_left)
        
        # 标题
        title_label = QLabel()
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        if level == 'expired':
            title_label.setText("[警告] 许可证已过期")
            title_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
        elif level == 'urgent':
            title_label.setText("[紧急] 许可证即将过期")
            title_label.setStyleSheet("color: #f57c00; font-weight: bold;")
        elif level == 'warning':
            title_label.setText("[提醒] 许可证到期提醒")
            title_label.setStyleSheet("color: #fbc02d; font-weight: bold;")
        else:
            title_label.setText("ℹ️ 许可证到期提醒")
            title_label.setStyleSheet("color: #1976d2;")
        
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        layout.addSpacing(10)
        
        # 信息组
        info_group = QGroupBox("许可证信息")
        info_layout = QVBoxLayout()
        
        # 许可证密钥
        license_layout = QHBoxLayout()
        license_layout.addWidget(QLabel("许可证密钥:"))
        license_value = QLabel(self.license_key)
        license_value.setStyleSheet("font-family: monospace;")
        license_layout.addWidget(license_value)
        license_layout.addStretch()
        info_layout.addLayout(license_layout)
        
        # 剩余天数
        days_layout = QHBoxLayout()
        days_layout.addWidget(QLabel("剩余天数:"))
        days_value = QLabel(f"{self.days_left} 天" if self.days_left >= 0 else "已过期")
        days_value_font = QFont()
        days_value_font.setPointSize(12)
        days_value_font.setBold(True)
        days_value.setFont(days_value_font)
        
        if self.days_left < 0:
            days_value.setStyleSheet("color: #d32f2f;")
        elif self.days_left <= 7:
            days_value.setStyleSheet("color: #f57c00;")
        elif self.days_left <= 30:
            days_value.setStyleSheet("color: #fbc02d;")
        
        days_layout.addWidget(days_value)
        days_layout.addStretch()
        info_layout.addLayout(days_layout)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        layout.addSpacing(10)
        
        # 提醒消息
        message_text = QTextEdit()
        message_text.setReadOnly(True)
        message_text.setMaximumHeight(100)
        
        if level == 'expired':
            message = (
                "您的许可证已过期！\n\n"
                "核心功能已被限制，您只能：\n"
                "• 查看历史数据\n"
                "• 导出使用报告\n\n"
                "请联系管理员续费以恢复所有功能。"
            )
        elif level == 'urgent':
            message = (
                f"您的License将在 {self.days_left} 天后过期！\n\n"
                "请尽快联系管理员续费，避免功能受限。"
            )
        elif level == 'warning':
            message = (
                f"您的License将在 {self.days_left} 天后过期。\n\n"
                "建议您提前联系管理员续费。"
            )
        else:
            message = (
                f"您的License将在 {self.days_left} 天后过期。\n\n"
                "请注意及时续费。"
            )
        
        message_text.setText(message)
        layout.addWidget(message_text)
        
        layout.addSpacing(10)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        if level == 'expired':
            update_btn = QPushButton("更新License")
            update_btn.clicked.connect(self.update_license)
            button_layout.addWidget(update_btn)
        
        button_layout.addStretch()
        
        if level == 'expired':
            close_btn = QPushButton("继续使用（受限）")
        else:
            close_btn = QPushButton("我知道了")
        
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def update_license(self):
        """更新License"""
        dialog = LicenseUpdateDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.accept()


class LicenseUpdateDialog(QDialog):
    """License更新对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("更新License")
        self.setModal(True)
        self.resize(500, 250)
        
        layout = QVBoxLayout(self)
        
        # 说明
        info_label = QLabel(
            "请输入新的许可证密钥。\n"
            "如果您还没有新的License，请联系管理员。"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addSpacing(10)
        
        # License输入
        input_group = QGroupBox("新许可证密钥")
        input_layout = QVBoxLayout()
        
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("DESI-XXXXXXXX-YYYYYYYY-CCCC")
        self.license_input.setFont(QFont("Courier", 10))
        input_layout.addWidget(self.license_input)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        layout.addSpacing(10)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        validate_btn = QPushButton("验证并更新")
        validate_btn.clicked.connect(self.validate_and_update)
        button_layout.addWidget(validate_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def validate_and_update(self):
        """验证并更新License"""
        new_license = self.license_input.text().strip()
        
        if not new_license:
            QMessageBox.warning(self, "警告", "请输入许可证密钥")
            return
        
        # 验证格式
        from license_manager_core import LicenseGenerator
        if not LicenseGenerator.validate_license_format(new_license):
            QMessageBox.critical(
                self, "错误",
                "License格式无效！\n\n"
                "正确格式: DESI-XXXXXXXX-YYYYYYYY-CCCC"
            )
            return
        
        # 保存新License
        try:
            from pathlib import Path
            license_file = Path.home() / ".desi_analytics" / "license.key"
            license_file.parent.mkdir(parents=True, exist_ok=True)
            license_file.write_text(new_license)
            
            QMessageBox.information(
                self, "成功",
                "License已更新！\n\n"
                "新License将在下次启动时生效。\n"
                "建议您重启软件以立即应用新License。"
            )
            
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(
                self, "错误",
                f"保存License失败:\n{str(e)}"
            )


class LicenseValidationDialog(QDialog):
    """License验证对话框（首次启动或验证失败时显示）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("License验证")
        self.setModal(True)
        self.resize(500, 300)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("欢迎使用DESI空间代谢组学分析系统")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        layout.addSpacing(10)
        
        # 说明
        info_label = QLabel(
            "本软件需要有效的License才能使用。\n"
            "请输入您的许可证密钥，或联系管理员获取。"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addSpacing(10)
        
        # License输入
        input_group = QGroupBox("许可证密钥")
        input_layout = QVBoxLayout()
        
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("DESI-XXXXXXXX-YYYYYYYY-CCCC")
        self.license_input.setFont(QFont("Courier", 10))
        input_layout.addWidget(self.license_input)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        layout.addSpacing(10)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        validate_btn = QPushButton("验证")
        validate_btn.clicked.connect(self.validate_license)
        button_layout.addWidget(validate_btn)
        
        exit_btn = QPushButton("退出")
        exit_btn.clicked.connect(self.reject)
        button_layout.addWidget(exit_btn)
        
        layout.addLayout(button_layout)
    
    def validate_license(self):
        """验证License"""
        license_key = self.license_input.text().strip()
        
        if not license_key:
            QMessageBox.warning(self, "警告", "请输入许可证密钥")
            return
        
        # 验证格式
        from license_manager_core import LicenseGenerator
        if not LicenseGenerator.validate_license_format(license_key):
            QMessageBox.critical(
                self, "错误",
                "License格式无效！\n\n"
                "正确格式: DESI-XXXXXXXX-YYYYYYYY-CCCC\n\n"
                "请检查您的许可证密钥是否正确。"
            )
            return
        
        # 保存License
        try:
            from pathlib import Path
            license_file = Path.home() / ".desi_analytics" / "license.key"
            license_file.parent.mkdir(parents=True, exist_ok=True)
            license_file.write_text(license_key)
            
            QMessageBox.information(
                self, "成功",
                "License验证成功！\n\n"
                "您现在可以使用软件的所有功能。"
            )
            
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(
                self, "错误",
                f"保存License失败:\n{str(e)}"
            )


# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 测试到期提醒对话框
    print("[测试] 测试许可证到期提醒对话框")
    
    # 测试不同级别的提醒
    test_cases = [
        (365, "正常状态"),
        (30, "30天提醒"),
        (7, "7天紧急提醒"),
        (-1, "已过期")
    ]
    
    for days, desc in test_cases:
        print(f"\n测试: {desc} (剩余{days}天)")
        dialog = LicenseReminderDialog(days, "DESI-12345678-87654321-ABCD")
        dialog.exec_()
    
    print("\n[成功] 所有测试完成")

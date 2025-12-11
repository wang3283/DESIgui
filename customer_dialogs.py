#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客户管理对话框

包含创建客户、编辑客户等对话框
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QDoubleSpinBox,
    QDateEdit, QTextEdit, QPushButton, QMessageBox,
    QDialogButtonBox
)
from PyQt5.QtCore import QDate, Qt

from database_manager import DatabaseManager
from license_manager_core import LicenseGenerator


class CreateCustomerDialog(QDialog):
    """创建客户对话框"""
    
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.license_generator = LicenseGenerator()
        self.customer_data = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("创建新客户")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # 表单布局
        form_layout = QFormLayout()
        
        # 基本信息
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入客户姓名")
        form_layout.addRow("姓名 *:", self.name_input)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@company.com")
        form_layout.addRow("邮箱 *:", self.email_input)
        
        self.company_input = QLineEdit()
        self.company_input.setPlaceholderText("公司名称（可选）")
        form_layout.addRow("公司:", self.company_input)
        
        # 许可证信息
        license_label = QLabel("许可证密钥将自动生成")
        license_label.setStyleSheet("color: gray; font-style: italic;")
        form_layout.addRow("License:", license_label)
        
        # 计费模式
        self.billing_mode_combo = QComboBox()
        self.billing_mode_combo.addItems([
            "按样本数计费",
            "按操作次数计费",
            "固定订阅制",
            "混合模式"
        ])
        self.billing_mode_combo.currentTextChanged.connect(self.on_billing_mode_changed)
        form_layout.addRow("计费模式 *:", self.billing_mode_combo)
        
        # 单价
        self.unit_price_spin = QDoubleSpinBox()
        self.unit_price_spin.setRange(0.01, 10000.0)
        self.unit_price_spin.setValue(10.0)
        self.unit_price_spin.setDecimals(2)
        self.unit_price_spin.setSuffix(" 元")
        form_layout.addRow("单价:", self.unit_price_spin)
        
        # 订阅费
        self.subscription_fee_spin = QDoubleSpinBox()
        self.subscription_fee_spin.setRange(0.0, 100000.0)
        self.subscription_fee_spin.setValue(0.0)
        self.subscription_fee_spin.setDecimals(2)
        self.subscription_fee_spin.setSuffix(" 元/月")
        self.subscription_fee_spin.setEnabled(False)
        form_layout.addRow("订阅费:", self.subscription_fee_spin)
        
        # 到期日期
        self.expires_date = QDateEdit()
        self.expires_date.setCalendarPopup(True)
        self.expires_date.setDate(QDate.currentDate().addYears(1))
        self.expires_date.setDisplayFormat("yyyy-MM-dd")
        form_layout.addRow("到期日期 *:", self.expires_date)
        
        # 备注
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("备注信息（可选）")
        self.notes_input.setMaximumHeight(80)
        form_layout.addRow("备注:", self.notes_input)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def on_billing_mode_changed(self, mode: str):
        """计费模式变化时更新UI"""
        if mode == "固定订阅制":
            self.unit_price_spin.setEnabled(False)
            self.subscription_fee_spin.setEnabled(True)
        elif mode == "混合模式":
            self.unit_price_spin.setEnabled(True)
            self.subscription_fee_spin.setEnabled(True)
        else:
            self.unit_price_spin.setEnabled(True)
            self.subscription_fee_spin.setEnabled(False)
    
    def validate_and_accept(self):
        """验证输入并接受"""
        # 验证必填字段
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "验证错误", "请输入客户姓名")
            self.name_input.setFocus()
            return
        
        email = self.email_input.text().strip()
        if not email:
            QMessageBox.warning(self, "验证错误", "请输入客户邮箱")
            self.email_input.setFocus()
            return
        
        # 简单的邮箱格式验证
        if '@' not in email or '.' not in email:
            QMessageBox.warning(self, "验证错误", "请输入有效的邮箱地址")
            self.email_input.setFocus()
            return
        
        # 生成License和客户ID
        license_key = self.license_generator.generate_license_key()
        customer_id = self.license_generator.generate_customer_id()
        
        # 获取计费模式
        billing_mode_map = {
            "按样本数计费": "per_sample",
            "按操作次数计费": "per_operation",
            "固定订阅制": "subscription",
            "混合模式": "hybrid"
        }
        billing_mode = billing_mode_map[self.billing_mode_combo.currentText()]
        
        # 构建客户数据
        self.customer_data = {
            'customer_id': customer_id,
            'name': name,
            'email': email,
            'company': self.company_input.text().strip() or None,
            'license_key': license_key,
            'billing_mode': billing_mode,
            'unit_price': self.unit_price_spin.value(),
            'subscription_fee': self.subscription_fee_spin.value(),
            'created_at': datetime.now().isoformat(),
            'expires_at': self.expires_date.date().toString("yyyy-MM-dd"),
            'status': 'active',
            'notes': self.notes_input.toPlainText().strip() or None
        }
        
        # 保存到数据库
        try:
            self.db_manager.create_customer(self.customer_data)
            QMessageBox.information(
                self,
                "成功",
                f"客户创建成功！\n\n"
                f"客户ID: {customer_id}\n"
                f"许可证密钥: {license_key}\n\n"
                f"请将许可证密钥发送给客户。"
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建客户失败: {str(e)}")
    
    def get_customer_data(self) -> Optional[Dict]:
        """获取客户数据"""
        return self.customer_data


class EditCustomerDialog(QDialog):
    """编辑客户对话框"""
    
    def __init__(self, db_manager: DatabaseManager, customer_id: str, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.customer_id = customer_id
        self.customer_data = None
        self.init_ui()
        self.load_customer_data()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("编辑客户信息")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # 表单布局
        form_layout = QFormLayout()
        
        # 客户ID（只读）
        self.customer_id_label = QLabel()
        self.customer_id_label.setStyleSheet("color: gray;")
        form_layout.addRow("客户ID:", self.customer_id_label)
        
        # 许可证密钥（只读）
        self.license_key_label = QLabel()
        self.license_key_label.setStyleSheet("color: gray;")
        self.license_key_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form_layout.addRow("License:", self.license_key_label)
        
        # 基本信息
        self.name_input = QLineEdit()
        form_layout.addRow("姓名 *:", self.name_input)
        
        self.email_input = QLineEdit()
        form_layout.addRow("邮箱 *:", self.email_input)
        
        self.company_input = QLineEdit()
        form_layout.addRow("公司:", self.company_input)
        
        # 计费模式
        self.billing_mode_combo = QComboBox()
        self.billing_mode_combo.addItems([
            "按样本数计费",
            "按操作次数计费",
            "固定订阅制",
            "混合模式"
        ])
        self.billing_mode_combo.currentTextChanged.connect(self.on_billing_mode_changed)
        form_layout.addRow("计费模式 *:", self.billing_mode_combo)
        
        # 单价
        self.unit_price_spin = QDoubleSpinBox()
        self.unit_price_spin.setRange(0.01, 10000.0)
        self.unit_price_spin.setDecimals(2)
        self.unit_price_spin.setSuffix(" 元")
        form_layout.addRow("单价:", self.unit_price_spin)
        
        # 订阅费
        self.subscription_fee_spin = QDoubleSpinBox()
        self.subscription_fee_spin.setRange(0.0, 100000.0)
        self.subscription_fee_spin.setDecimals(2)
        self.subscription_fee_spin.setSuffix(" 元/月")
        form_layout.addRow("订阅费:", self.subscription_fee_spin)
        
        # 状态
        self.status_combo = QComboBox()
        self.status_combo.addItems(["活跃", "已过期", "已暂停"])
        form_layout.addRow("状态 *:", self.status_combo)
        
        # 到期日期
        self.expires_date = QDateEdit()
        self.expires_date.setCalendarPopup(True)
        self.expires_date.setDisplayFormat("yyyy-MM-dd")
        form_layout.addRow("到期日期 *:", self.expires_date)
        
        # 备注
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        form_layout.addRow("备注:", self.notes_input)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def on_billing_mode_changed(self, mode: str):
        """计费模式变化时更新UI"""
        if mode == "固定订阅制":
            self.unit_price_spin.setEnabled(False)
            self.subscription_fee_spin.setEnabled(True)
        elif mode == "混合模式":
            self.unit_price_spin.setEnabled(True)
            self.subscription_fee_spin.setEnabled(True)
        else:
            self.unit_price_spin.setEnabled(True)
            self.subscription_fee_spin.setEnabled(False)
    
    def load_customer_data(self):
        """加载客户数据"""
        customer = self.db_manager.get_customer(self.customer_id)
        if not customer:
            QMessageBox.critical(self, "错误", "无法加载客户数据")
            self.reject()
            return
        
        # 填充表单
        self.customer_id_label.setText(customer['customer_id'])
        self.license_key_label.setText(customer['license_key'])
        self.name_input.setText(customer['name'])
        self.email_input.setText(customer['email'])
        self.company_input.setText(customer['company'] or '')
        
        # 计费模式
        billing_mode_map = {
            'per_sample': "按样本数计费",
            'per_operation': "按操作次数计费",
            'subscription': "固定订阅制",
            'hybrid': "混合模式"
        }
        self.billing_mode_combo.setCurrentText(
            billing_mode_map.get(customer['billing_mode'], "按样本数计费")
        )
        
        self.unit_price_spin.setValue(customer['unit_price'])
        self.subscription_fee_spin.setValue(customer['subscription_fee'])
        
        # 状态
        status_map = {
            'active': "活跃",
            'expired': "已过期",
            'suspended': "已暂停"
        }
        self.status_combo.setCurrentText(
            status_map.get(customer['status'], "活跃")
        )
        
        # 到期日期
        expires_date = QDate.fromString(customer['expires_at'], "yyyy-MM-dd")
        self.expires_date.setDate(expires_date)
        
        self.notes_input.setPlainText(customer['notes'] or '')
    
    def validate_and_accept(self):
        """验证输入并接受"""
        # 验证必填字段
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "验证错误", "请输入客户姓名")
            return
        
        email = self.email_input.text().strip()
        if not email or '@' not in email:
            QMessageBox.warning(self, "验证错误", "请输入有效的邮箱地址")
            return
        
        # 获取计费模式
        billing_mode_map = {
            "按样本数计费": "per_sample",
            "按操作次数计费": "per_operation",
            "固定订阅制": "subscription",
            "混合模式": "hybrid"
        }
        billing_mode = billing_mode_map[self.billing_mode_combo.currentText()]
        
        # 获取状态
        status_map = {
            "活跃": "active",
            "已过期": "expired",
            "已暂停": "suspended"
        }
        status = status_map[self.status_combo.currentText()]
        
        # 构建更新数据
        update_data = {
            'name': name,
            'email': email,
            'company': self.company_input.text().strip() or None,
            'billing_mode': billing_mode,
            'unit_price': self.unit_price_spin.value(),
            'subscription_fee': self.subscription_fee_spin.value(),
            'status': status,
            'expires_at': self.expires_date.date().toString("yyyy-MM-dd"),
            'notes': self.notes_input.toPlainText().strip() or None
        }
        
        # 更新数据库
        try:
            self.db_manager.update_customer(self.customer_id, update_data)
            QMessageBox.information(self, "成功", "客户信息已更新")
            self.customer_data = update_data
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"更新客户失败: {str(e)}")
    
    def get_customer_data(self) -> Optional[Dict]:
        """获取更新后的客户数据"""
        return self.customer_data

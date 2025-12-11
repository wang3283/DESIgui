#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账单生成对话框 - 提供账单配置和生成功能
"""

from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QComboBox, QDoubleSpinBox, QDateEdit, QTextEdit,
    QGroupBox, QMessageBox, QFileDialog, QSpinBox
)
from PyQt5.QtCore import Qt, QDate

from invoice_generator import InvoiceGenerator, InvoiceConfig, InvoiceData


class GenerateInvoiceDialog(QDialog):
    """生成账单对话框"""
    
    def __init__(self, db_manager, customer_id: str, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.customer_id = customer_id
        self.customer = None
        self.invoice_generator = InvoiceGenerator(db_manager)
        self.generated_invoice = None
        
        self.setWindowTitle("生成账单")
        self.setModal(True)
        self.resize(600, 700)
        
        self.init_ui()
        self.load_customer_info()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 客户信息组
        customer_group = QGroupBox("客户信息")
        customer_layout = QFormLayout()
        
        self.customer_name_label = QLabel("-")
        self.customer_email_label = QLabel("-")
        self.customer_company_label = QLabel("-")
        
        customer_layout.addRow("客户名称:", self.customer_name_label)
        customer_layout.addRow("邮箱:", self.customer_email_label)
        customer_layout.addRow("公司:", self.customer_company_label)
        
        customer_group.setLayout(customer_layout)
        layout.addWidget(customer_group)
        
        # 计费周期组
        period_group = QGroupBox("计费周期")
        period_layout = QFormLayout()
        
        self.period_start_edit = QDateEdit()
        self.period_start_edit.setCalendarPopup(True)
        self.period_start_edit.setDate(QDate.currentDate().addMonths(-1))
        period_layout.addRow("开始日期:", self.period_start_edit)
        
        self.period_end_edit = QDateEdit()
        self.period_end_edit.setCalendarPopup(True)
        self.period_end_edit.setDate(QDate.currentDate())
        period_layout.addRow("结束日期:", self.period_end_edit)
        
        period_group.setLayout(period_layout)
        layout.addWidget(period_group)
        
        # 计费模式组
        billing_group = QGroupBox("计费配置")
        billing_layout = QFormLayout()
        
        self.billing_mode_combo = QComboBox()
        self.billing_mode_combo.addItems([
            "按样本数计费",
            "按操作次数计费",
            "固定订阅",
            "混合模式"
        ])
        self.billing_mode_combo.currentIndexChanged.connect(self.on_billing_mode_changed)
        billing_layout.addRow("计费模式:", self.billing_mode_combo)
        
        # 单价
        self.unit_price_spin = QDoubleSpinBox()
        self.unit_price_spin.setRange(0.01, 10000.0)
        self.unit_price_spin.setValue(10.0)
        self.unit_price_spin.setPrefix("¥ ")
        self.unit_price_spin.setDecimals(2)
        billing_layout.addRow("单价:", self.unit_price_spin)
        
        # 订阅费
        self.subscription_fee_spin = QDoubleSpinBox()
        self.subscription_fee_spin.setRange(0.0, 100000.0)
        self.subscription_fee_spin.setValue(0.0)
        self.subscription_fee_spin.setPrefix("¥ ")
        self.subscription_fee_spin.setDecimals(2)
        self.subscription_fee_spin.setEnabled(False)
        billing_layout.addRow("订阅费:", self.subscription_fee_spin)
        
        # 混合模式参数
        self.base_quota_spin = QSpinBox()
        self.base_quota_spin.setRange(0, 100000)
        self.base_quota_spin.setValue(50)
        self.base_quota_spin.setEnabled(False)
        billing_layout.addRow("基础配额:", self.base_quota_spin)
        
        self.overage_price_spin = QDoubleSpinBox()
        self.overage_price_spin.setRange(0.01, 10000.0)
        self.overage_price_spin.setValue(8.0)
        self.overage_price_spin.setPrefix("¥ ")
        self.overage_price_spin.setDecimals(2)
        self.overage_price_spin.setEnabled(False)
        billing_layout.addRow("超额单价:", self.overage_price_spin)
        
        # 税率
        self.tax_rate_spin = QDoubleSpinBox()
        self.tax_rate_spin.setRange(0.0, 1.0)
        self.tax_rate_spin.setValue(0.06)
        self.tax_rate_spin.setSingleStep(0.01)
        self.tax_rate_spin.setDecimals(2)
        self.tax_rate_spin.setSuffix(" %")
        billing_layout.addRow("税率:", self.tax_rate_spin)
        
        billing_group.setLayout(billing_layout)
        layout.addWidget(billing_group)
        
        # 备注
        notes_group = QGroupBox("备注")
        notes_layout = QVBoxLayout()
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("输入账单备注（可选）...")
        self.notes_edit.setMaximumHeight(80)
        notes_layout.addWidget(self.notes_edit)
        
        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)
        
        # 预览区域
        preview_group = QGroupBox("账单预览")
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel("点击预览按钮查看账单详情")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("padding: 10px; background-color: #f5f5f5;")
        preview_layout.addWidget(self.preview_label)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("预览")
        self.preview_btn.clicked.connect(self.preview_invoice)
        button_layout.addWidget(self.preview_btn)
        
        self.generate_btn = QPushButton("生成账单")
        self.generate_btn.clicked.connect(self.generate_invoice)
        button_layout.addWidget(self.generate_btn)
        
        self.export_text_btn = QPushButton("导出文本")
        self.export_text_btn.clicked.connect(self.export_text)
        self.export_text_btn.setEnabled(False)
        button_layout.addWidget(self.export_text_btn)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def load_customer_info(self):
        """加载客户信息"""
        self.customer = self.db_manager.get_customer(self.customer_id)
        if self.customer:
            self.customer_name_label.setText(self.customer['name'])
            self.customer_email_label.setText(self.customer['email'])
            self.customer_company_label.setText(self.customer.get('company', '-'))
            
            # 加载客户的默认计费配置
            billing_mode = self.customer.get('billing_mode', 'per_sample')
            mode_map = {
                'per_sample': 0,
                'per_operation': 1,
                'subscription': 2,
                'hybrid': 3
            }
            self.billing_mode_combo.setCurrentIndex(mode_map.get(billing_mode, 0))
            
            self.unit_price_spin.setValue(self.customer.get('unit_price', 10.0))
            self.subscription_fee_spin.setValue(self.customer.get('subscription_fee', 0.0))
    
    def on_billing_mode_changed(self, index):
        """计费模式变化"""
        if index == 0:  # 按样本数
            self.unit_price_spin.setEnabled(True)
            self.subscription_fee_spin.setEnabled(False)
            self.base_quota_spin.setEnabled(False)
            self.overage_price_spin.setEnabled(False)
        elif index == 1:  # 按操作次数
            self.unit_price_spin.setEnabled(True)
            self.subscription_fee_spin.setEnabled(False)
            self.base_quota_spin.setEnabled(False)
            self.overage_price_spin.setEnabled(False)
        elif index == 2:  # 固定订阅
            self.unit_price_spin.setEnabled(False)
            self.subscription_fee_spin.setEnabled(True)
            self.base_quota_spin.setEnabled(False)
            self.overage_price_spin.setEnabled(False)
        elif index == 3:  # 混合模式
            self.unit_price_spin.setEnabled(False)
            self.subscription_fee_spin.setEnabled(True)
            self.base_quota_spin.setEnabled(True)
            self.overage_price_spin.setEnabled(True)
    
    def get_billing_mode_key(self) -> str:
        """获取计费模式键"""
        mode_map = {
            0: 'per_sample',
            1: 'per_operation',
            2: 'subscription',
            3: 'hybrid'
        }
        return mode_map[self.billing_mode_combo.currentIndex()]
    
    def create_config(self) -> InvoiceConfig:
        """创建账单配置"""
        period_start = self.period_start_edit.date().toPyDate()
        period_end = self.period_end_edit.date().toPyDate()
        
        config = InvoiceConfig(
            customer_id=self.customer_id,
            period_start=datetime.combine(period_start, datetime.min.time()),
            period_end=datetime.combine(period_end, datetime.max.time()),
            billing_mode=self.get_billing_mode_key(),
            unit_price=self.unit_price_spin.value(),
            subscription_fee=self.subscription_fee_spin.value(),
            tax_rate=self.tax_rate_spin.value() / 100.0,
            notes=self.notes_edit.toPlainText(),
            base_quota=self.base_quota_spin.value(),
            overage_price=self.overage_price_spin.value()
        )
        
        return config
    
    def preview_invoice(self):
        """预览账单"""
        try:
            config = self.create_config()
            
            # 获取使用数据
            usage_data = self.invoice_generator.get_usage_data(
                config.customer_id,
                config.period_start,
                config.period_end
            )
            
            # 计算金额
            subtotal, tax_amount, total_amount = self.invoice_generator.calculate_amount(
                config, usage_data
            )
            
            # 显示预览
            preview_text = f"""
<b>计费周期:</b> {config.period_start.strftime('%Y-%m-%d')} 至 {config.period_end.strftime('%Y-%m-%d')}<br>
<br>
<b>使用统计:</b><br>
• 总样本数: {usage_data['total_samples']}<br>
• 唯一样本数: {usage_data['unique_samples']}<br>
• 总操作次数: {usage_data['total_operations']}<br>
<br>
<b>计费详情:</b><br>
• 计费模式: {self.billing_mode_combo.currentText()}<br>
"""
            
            if config.billing_mode == 'per_sample':
                preview_text += f"• 唯一样本数: {usage_data['unique_samples']}<br>"
                preview_text += f"• 单价: ¥{config.unit_price:.2f}<br>"
            elif config.billing_mode == 'per_operation':
                preview_text += f"• 总操作次数: {usage_data['total_operations']}<br>"
                preview_text += f"• 单价: ¥{config.unit_price:.2f}<br>"
            elif config.billing_mode == 'subscription':
                preview_text += f"• 订阅费: ¥{config.subscription_fee:.2f}<br>"
            elif config.billing_mode == 'hybrid':
                preview_text += f"• 基础订阅费: ¥{config.subscription_fee:.2f}<br>"
                preview_text += f"• 基础配额: {config.base_quota} 样本<br>"
                overage = max(0, usage_data['unique_samples'] - config.base_quota)
                preview_text += f"• 超额使用: {overage} 样本<br>"
                preview_text += f"• 超额单价: ¥{config.overage_price:.2f}<br>"
            
            preview_text += f"<br>"
            preview_text += f"• 小计: ¥{subtotal:.2f}<br>"
            if config.tax_rate > 0:
                preview_text += f"• 税率: {config.tax_rate * 100:.1f}%<br>"
                preview_text += f"• 税额: ¥{tax_amount:.2f}<br>"
            preview_text += f"<br>"
            preview_text += f"<b>总计: ¥{total_amount:.2f}</b>"
            
            self.preview_label.setText(preview_text)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"预览失败: {str(e)}")
    
    def generate_invoice(self):
        """生成账单"""
        try:
            config = self.create_config()
            
            # 验证日期
            if config.period_start >= config.period_end:
                QMessageBox.warning(self, "警告", "结束日期必须晚于开始日期")
                return
            
            # 生成账单
            self.generated_invoice = self.invoice_generator.create_invoice(config)
            
            # 启用导出按钮
            self.export_text_btn.setEnabled(True)
            
            QMessageBox.information(
                self,
                "成功",
                f"账单生成成功！\n\n"
                f"账单编号: {self.generated_invoice.invoice_id}\n"
                f"总金额: ¥{self.generated_invoice.total_amount:.2f}\n\n"
                f"您可以导出账单或关闭对话框。"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成账单失败: {str(e)}")
    
    def export_text(self):
        """导出为文本"""
        if not self.generated_invoice:
            QMessageBox.warning(self, "警告", "请先生成账单")
            return
        
        # 选择保存位置
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "保存账单",
            f"Invoice_{self.generated_invoice.invoice_id}.txt",
            "文本文件 (*.txt)"
        )
        
        if filename:
            try:
                text_content = self.invoice_generator.export_to_text(self.generated_invoice)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                
                QMessageBox.information(self, "成功", f"账单已导出到:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")


# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    from database_manager import DatabaseManager
    
    app = QApplication(sys.argv)
    
    # 创建测试数据库
    db = DatabaseManager("test_invoice.db", mode='admin')
    
    # 创建测试客户
    customer_data = {
        'customer_id': 'CUST-TEST001',
        'name': '测试客户',
        'email': 'test@example.com',
        'company': '测试公司',
        'license_key': 'DESI-TEST-1234',
        'billing_mode': 'per_sample',
        'unit_price': 10.0,
        'created_at': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(days=365)).isoformat()
    }
    
    try:
        db.create_customer(customer_data)
    except:
        pass  # 客户可能已存在
    
    # 显示对话框
    dialog = GenerateInvoiceDialog(db, 'CUST-TEST001')
    dialog.exec_()
    
    db.close()

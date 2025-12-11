#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
License Manager GUI - 商业化计费系统管理员工具

主窗口框架，提供客户管理、报告导入、账单生成等功能
"""

import sys
from datetime import datetime
from typing import Dict, List, Optional
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTableWidget, QTableWidgetItem, QLabel, QPushButton,
    QToolBar, QStatusBar, QMenuBar, QMenu, QAction, QMessageBox,
    QHeaderView, QLineEdit, QComboBox, QDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon

from database_manager import DatabaseManager
from license_manager_core import LicenseGenerator, LicenseValidator
from customer_dialogs import CreateCustomerDialog, EditCustomerDialog
from import_report_dialog import ImportReportDialog
from invoice_dialog import GenerateInvoiceDialog
from usage_stats_dialog import UsageStatsDialog
from integrity_dialog import IntegrityDialog
from integrity_verifier import IntegrityVerifier


class CustomerListWidget(QWidget):
    """客户列表组件"""
    
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.db_manager = None
        self.main_window = main_window
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 搜索和筛选栏
        filter_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索客户名称、邮箱或公司...")
        self.search_input.textChanged.connect(self.filter_customers)
        filter_layout.addWidget(self.search_input)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部状态", "活跃", "已过期", "已暂停"])
        self.status_filter.currentTextChanged.connect(self.filter_customers)
        filter_layout.addWidget(self.status_filter)
        
        layout.addLayout(filter_layout)
        
        # 客户表格
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "客户ID", "姓名", "公司", "邮箱", "License状态", "到期日期", "计费模式"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.table)
    
    def set_database_manager(self, db_manager: DatabaseManager):
        """设置数据库管理器"""
        self.db_manager = db_manager
        self.load_customers()
    
    def load_customers(self):
        """加载所有客户"""
        if not self.db_manager:
            return
        
        customers = self.db_manager.get_all_customers()
        self.table.setRowCount(len(customers))
        
        for row, customer in enumerate(customers):
            self.table.setItem(row, 0, QTableWidgetItem(customer.get('customer_id', '')))
            self.table.setItem(row, 1, QTableWidgetItem(customer.get('name', '')))
            self.table.setItem(row, 2, QTableWidgetItem(customer.get('company') or ''))
            self.table.setItem(row, 3, QTableWidgetItem(customer.get('email', '')))
            self.table.setItem(row, 4, QTableWidgetItem(customer.get('status', '')))
            self.table.setItem(row, 5, QTableWidgetItem(customer.get('expires_at', '')))
            self.table.setItem(row, 6, QTableWidgetItem(customer.get('billing_mode', 'per_sample')))
    
    def filter_customers(self):
        """筛选客户"""
        search_text = self.search_input.text().lower()
        status_filter = self.status_filter.currentText()
        
        for row in range(self.table.rowCount()):
            show_row = True
            
            # 搜索筛选
            if search_text:
                name = self.table.item(row, 1).text().lower()
                company = self.table.item(row, 2).text().lower()
                email = self.table.item(row, 3).text().lower()
                if search_text not in name and search_text not in company and search_text not in email:
                    show_row = False
            
            # 状态筛选
            if status_filter != "全部状态":
                status_map = {"活跃": "active", "已过期": "expired", "已暂停": "suspended"}
                status = self.table.item(row, 4).text()
                if status != status_map.get(status_filter, status_filter):
                    show_row = False
            
            self.table.setRowHidden(row, not show_row)
    
    def on_selection_changed(self):
        """选择变化时触发"""
        selected_items = self.table.selectedItems()
        if selected_items and self.main_window:
            customer_id = self.table.item(selected_items[0].row(), 0).text()
            self.main_window.on_customer_selected(customer_id)
    
    def get_selected_customer_id(self) -> Optional[str]:
        """获取选中的客户ID"""
        selected_items = self.table.selectedItems()
        if selected_items:
            return self.table.item(selected_items[0].row(), 0).text()
        return None


class CustomerDetailPanel(QWidget):
    """客户详情面板"""
    
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.db_manager = None
        self.main_window = main_window
        self.current_customer_id = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("客户详情")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 详情标签
        self.detail_labels = {}
        fields = [
            ("customer_id", "客户ID"),
            ("name", "姓名"),
            ("email", "邮箱"),
            ("company", "公司"),
            ("license_key", "许可证密钥"),
            ("billing_mode", "计费模式"),
            ("unit_price", "单价"),
            ("subscription_fee", "订阅费"),
            ("status", "状态"),
            ("created_at", "创建时间"),
            ("expires_at", "到期时间"),
            ("notes", "备注")
        ]
        
        for field_name, field_label in fields:
            label = QLabel(f"{field_label}: ")
            value_label = QLabel("-")
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            
            field_layout = QHBoxLayout()
            field_layout.addWidget(label)
            field_layout.addWidget(value_label, 1)
            layout.addLayout(field_layout)
            
            self.detail_labels[field_name] = value_label
        
        layout.addStretch()
    
    def set_database_manager(self, db_manager: DatabaseManager):
        """设置数据库管理器"""
        self.db_manager = db_manager
    
    def show_customer(self, customer_id: str):
        """显示客户详情"""
        if not self.db_manager:
            return
        
        self.current_customer_id = customer_id
        customer = self.db_manager.get_customer(customer_id)
        
        if customer:
            for field_name, label in self.detail_labels.items():
                value = customer.get(field_name, '-')
                if value is None:
                    value = '-'
                label.setText(str(value))
        else:
            self.clear()
    
    def clear(self):
        """清空详情"""
        self.current_customer_id = None
        for label in self.detail_labels.values():
            label.setText('-')


class LicenseManagerGUI(QMainWindow):
    """License Manager主窗口"""
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager("license_manager.db", mode='admin')
        self.license_generator = LicenseGenerator()
        self.license_validator = LicenseValidator()
        self.init_ui()
        self.setup_connections()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("DESI商业化计费系统 - License Manager")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_tool_bar()
        
        # 创建中央部件
        self.create_central_widget()
        
        # 创建状态栏
        self.create_status_bar()
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        import_action = QAction("导入使用报告(&I)", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self.import_report)
        file_menu.addAction(import_action)
        
        export_action = QAction("导出数据(&E)", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")
        
        new_customer_action = QAction("新建客户(&N)", self)
        new_customer_action.setShortcut("Ctrl+N")
        new_customer_action.triggered.connect(self.create_customer)
        edit_menu.addAction(new_customer_action)
        
        edit_customer_action = QAction("编辑客户(&E)", self)
        edit_customer_action.triggered.connect(self.edit_customer)
        edit_menu.addAction(edit_customer_action)
        
        delete_customer_action = QAction("删除客户(&D)", self)
        delete_customer_action.triggered.connect(self.delete_customer)
        edit_menu.addAction(delete_customer_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")
        
        generate_invoice_action = QAction("生成账单(&G)", self)
        generate_invoice_action.setShortcut("Ctrl+G")
        generate_invoice_action.triggered.connect(self.generate_invoice)
        tools_menu.addAction(generate_invoice_action)
        
        tools_menu.addSeparator()
        
        usage_stats_action = QAction("使用统计(&U)", self)
        usage_stats_action.setShortcut("Ctrl+U")
        usage_stats_action.triggered.connect(self.show_usage_stats)
        tools_menu.addAction(usage_stats_action)
        
        integrity_action = QAction("完整性验证(&I)", self)
        integrity_action.setShortcut("Ctrl+I")
        integrity_action.triggered.connect(self.show_integrity_check)
        tools_menu.addAction(integrity_action)
        
        tools_menu.addSeparator()
        
        backup_action = QAction("备份数据库(&B)", self)
        backup_action.triggered.connect(self.backup_database)
        tools_menu.addAction(backup_action)
        
        restore_action = QAction("恢复数据库(&R)", self)
        restore_action.triggered.connect(self.restore_database)
        tools_menu.addAction(restore_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_tool_bar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # 新建客户按钮
        new_customer_btn = QPushButton("新建客户")
        new_customer_btn.clicked.connect(self.create_customer)
        toolbar.addWidget(new_customer_btn)
        
        toolbar.addSeparator()
        
        # 导入报告按钮
        import_btn = QPushButton("导入报告")
        import_btn.clicked.connect(self.import_report)
        toolbar.addWidget(import_btn)
        
        # 生成账单按钮
        invoice_btn = QPushButton("生成账单")
        invoice_btn.clicked.connect(self.generate_invoice)
        toolbar.addWidget(invoice_btn)
        
        toolbar.addSeparator()
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)
    
    def create_central_widget(self):
        """创建中央部件 - 四面板布局"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # 创建分割器
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：客户列表
        self.customer_list = CustomerListWidget(main_splitter, main_window=self)
        self.customer_list.set_database_manager(self.db_manager)
        main_splitter.addWidget(self.customer_list)
        
        # 右侧：垂直分割器
        right_splitter = QSplitter(Qt.Vertical)
        
        # 客户详情面板
        self.detail_panel = CustomerDetailPanel(right_splitter, main_window=self)
        self.detail_panel.set_database_manager(self.db_manager)
        right_splitter.addWidget(self.detail_panel)
        
        # 图表面板（占位）
        chart_panel = QWidget()
        chart_layout = QVBoxLayout(chart_panel)
        chart_label = QLabel("使用量图表")
        chart_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        chart_layout.addWidget(chart_label)
        chart_layout.addWidget(QLabel("（图表功能将在后续任务中实现）"))
        chart_layout.addStretch()
        right_splitter.addWidget(chart_panel)
        
        # 账单面板（占位）
        invoice_panel = QWidget()
        invoice_layout = QVBoxLayout(invoice_panel)
        invoice_label = QLabel("账单列表")
        invoice_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        invoice_layout.addWidget(invoice_label)
        invoice_layout.addWidget(QLabel("（账单功能将在后续任务中实现）"))
        invoice_layout.addStretch()
        right_splitter.addWidget(invoice_panel)
        
        main_splitter.addWidget(right_splitter)
        
        # 设置分割器比例
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(main_splitter)
    
    def create_status_bar(self):
        """创建状态栏"""
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        
        # 添加客户数量标签
        self.customer_count_label = QLabel("客户数: 0")
        self.statusBar.addPermanentWidget(self.customer_count_label)
        
        # 定时更新状态
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # 每5秒更新一次
    
    def setup_connections(self):
        """设置信号连接"""
        pass
    
    def on_customer_selected(self, customer_id: str):
        """客户选择变化"""
        self.detail_panel.show_customer(customer_id)
    
    def create_customer(self):
        """创建新客户"""
        dialog = CreateCustomerDialog(self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_data()
            self.statusBar.showMessage("客户创建成功", 3000)
    
    def edit_customer(self):
        """编辑客户"""
        customer_id = self.customer_list.get_selected_customer_id()
        if not customer_id:
            QMessageBox.warning(self, "警告", "请先选择一个客户")
            return
        
        dialog = EditCustomerDialog(self.db_manager, customer_id, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_data()
            self.statusBar.showMessage("客户信息已更新", 3000)
    
    def delete_customer(self):
        """删除客户"""
        customer_id = self.customer_list.get_selected_customer_id()
        if not customer_id:
            QMessageBox.warning(self, "警告", "请先选择一个客户")
            return
        
        # 获取客户信息
        customer = self.db_manager.get_customer(customer_id)
        if not customer:
            QMessageBox.warning(self, "警告", "无法找到客户信息")
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除客户 {customer['name']} ({customer_id}) 吗？\n\n"
            f"此操作将删除该客户的所有相关数据，且无法恢复！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.delete_customer(customer_id)
                self.refresh_data()
                self.detail_panel.clear()
                self.statusBar.showMessage("客户已删除", 3000)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除客户失败: {str(e)}")
    
    def import_report(self):
        """导入使用报告"""
        dialog = ImportReportDialog(self.db_manager, self)
        dialog.exec_()
    
    def export_data(self):
        """导出数据"""
        QMessageBox.information(self, "提示", "导出数据功能将在后续任务中实现")
    
    def generate_invoice(self):
        """生成账单"""
        customer_id = self.customer_list.get_selected_customer_id()
        if not customer_id:
            QMessageBox.warning(self, "警告", "请先选择一个客户")
            return
        
        dialog = GenerateInvoiceDialog(self.db_manager, customer_id, self)
        dialog.exec_()
    
    def show_usage_stats(self):
        """显示使用统计"""
        dialog = UsageStatsDialog(parent=self)
        dialog.exec_()
    
    def show_integrity_check(self):
        """显示完整性验证"""
        # 获取当前选中的客户
        customer_id = self.customer_list.get_selected_customer_id()
        
        if not customer_id:
            QMessageBox.information(
                self,
                "提示",
                "请先选择一个客户以验证其使用报告的完整性"
            )
            return
        
        customer = self.db_manager.get_customer(customer_id)
        
        if not customer:
            QMessageBox.warning(self, "错误", "无法获取客户信息")
            return
        
        # 创建完整性验证器（使用客户的机器ID和License）
        # 注意：这里需要从使用报告中获取机器ID
        # 简化版本：使用客户的License作为标识
        try:
            # 这里应该从导入的使用报告中获取机器ID
            # 暂时使用一个占位符
            machine_id = customer.get('license_key', 'unknown')[:32]
            secret_seed = b"DESI_METABOLOMICS_2025_SECRET_KEY"
            
            # 创建临时数据库路径（实际应该使用客户的使用记录）
            import tempfile
            temp_db = tempfile.mktemp(suffix='.db')
            
            # 这里应该从管理员数据库中提取客户的使用记录到临时数据库
            # 简化版本：直接使用管理员数据库
            verifier = IntegrityVerifier(
                str(self.db_manager.db_path),
                machine_id,
                secret_seed
            )
            
            dialog = IntegrityDialog(verifier, parent=self)
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "错误",
                f"无法启动完整性验证:\n{e}"
            )
    
    def backup_database(self):
        """备份数据库"""
        QMessageBox.information(self, "提示", "备份功能将在阶段10中实现")
    
    def restore_database(self):
        """恢复数据库"""
        QMessageBox.information(self, "提示", "恢复功能将在阶段10中实现")
    
    def refresh_data(self):
        """刷新数据"""
        self.customer_list.load_customers()
        self.update_status()
        self.statusBar.showMessage("数据已刷新", 3000)
    
    def update_status(self):
        """更新状态栏"""
        if self.db_manager:
            customers = self.db_manager.get_all_customers()
            self.customer_count_label.setText(f"客户数: {len(customers)}")
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            "DESI商业化计费系统 - License Manager\n\n"
            "版本: 1.0.0\n"
            "用于管理客户License、使用报告和账单生成\n\n"
            "© 2024 DESI团队"
        )
    
    def closeEvent(self, event):
        """关闭事件"""
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出License Manager吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion风格
    
    window = LicenseManagerGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
License续费提醒对话框
用于离线模式下的续费流程
"""

from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QClipboard

from license_manager_core import LicenseValidator


class LicenseRenewalDialog(QDialog):
    """License续费提醒对话框"""
    
    def __init__(self, days_left: int, license_key: str, 
                 customer_info: dict = None, parent=None):
        super().__init__(parent)
        self.days_left = days_left
        self.license_key = license_key
        self.customer_info = customer_info or {}
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("License续费提醒")
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # 根据剩余天数显示不同级别的提醒
        _, level = LicenseValidator.should_show_reminder(self.days_left)
        
        # 标题
        title_label = QLabel()
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        if level == 'expired':
            title_label.setText("[警告] 许可证已过期 - 需要续费")
            title_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
        elif level == 'urgent':
            title_label.setText("[紧急] 许可证即将过期 - 请尽快续费")
            title_label.setStyleSheet("color: #f57c00; font-weight: bold;")
        elif level == 'warning':
            title_label.setText("[提醒] 许可证到期提醒 - 建议续费")
            title_label.setStyleSheet("color: #fbc02d; font-weight: bold;")
        else:
            title_label.setText("ℹ️ 许可证到期提醒")
            title_label.setStyleSheet("color: #1976d2;")
        
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        layout.addSpacing(10)
        
        # 许可证信息组
        info_group = QGroupBox("当前许可证信息")
        info_layout = QVBoxLayout()
        
        # 许可证密钥
        license_layout = QHBoxLayout()
        license_layout.addWidget(QLabel("许可证密钥:"))
        license_value = QLabel(self.license_key)
        license_value.setStyleSheet("font-family: monospace; font-weight: bold;")
        license_layout.addWidget(license_value)
        license_layout.addStretch()
        info_layout.addLayout(license_layout)
        
        # 剩余天数
        days_layout = QHBoxLayout()
        days_layout.addWidget(QLabel("剩余天数:"))
        days_value = QLabel(f"{self.days_left} 天" if self.days_left >= 0 else "已过期")
        days_value_font = QFont()
        days_value_font.setPointSize(14)
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
        
        # 续费说明
        renewal_group = QGroupBox("如何续费")
        renewal_layout = QVBoxLayout()
        
        instructions = QLabel(
            "请按照以下步骤联系管理员续费：\n\n"
            "1. 复制下方的续费申请信息\n"
            "2. 通过邮件发送给管理员\n"
            "3. 等待管理员处理并发送新的配置文件\n"
            "4. 将配置文件放到指定位置后重启软件"
        )
        instructions.setWordWrap(True)
        renewal_layout.addWidget(instructions)
        
        renewal_group.setLayout(renewal_layout)
        layout.addWidget(renewal_group)
        
        layout.addSpacing(10)
        
        # 续费申请信息（可复制）
        request_group = QGroupBox("续费申请信息（点击下方按钮复制）")
        request_layout = QVBoxLayout()
        
        self.request_text = QTextEdit()
        self.request_text.setReadOnly(True)
        self.request_text.setMaximumHeight(150)
        self.request_text.setStyleSheet("font-family: monospace;")
        
        # 生成续费申请内容
        request_content = self._generate_renewal_request()
        self.request_text.setText(request_content)
        
        request_layout.addWidget(self.request_text)
        
        # 复制按钮
        copy_btn = QPushButton("📋 复制续费申请信息")
        copy_btn.clicked.connect(self.copy_request_to_clipboard)
        request_layout.addWidget(copy_btn)
        
        request_group.setLayout(request_layout)
        layout.addWidget(request_group)
        
        layout.addSpacing(10)
        
        # 联系方式
        contact_group = QGroupBox("管理员联系方式")
        contact_layout = QVBoxLayout()
        
        contact_info = QLabel(
            "邮箱: license@your-company.com\n"
            "电话: 400-XXX-XXXX\n"
            "工作时间: 周一至周五 9:00-18:00"
        )
        contact_info.setStyleSheet("font-size: 12px;")
        contact_layout.addWidget(contact_info)
        
        contact_group.setLayout(contact_layout)
        layout.addWidget(contact_group)
        
        layout.addSpacing(10)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        if level == 'expired':
            close_btn = QPushButton("我知道了（功能受限）")
        else:
            close_btn = QPushButton("我知道了")
        
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _generate_renewal_request(self) -> str:
        """
        生成续费申请内容
        
        返回:
            续费申请文本
        """
        # 获取系统信息
        import platform
        
        content = f"""
=================================================
DESI软件 License续费申请
=================================================

申请时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

【许可证信息】
许可证密钥: {self.license_key}
剩余天数: {self.days_left} 天
状态: {'已过期' if self.days_left < 0 else '即将过期'}

【客户信息】
客户ID: {self.customer_info.get('customer_id', '未知')}
客户名称: {self.customer_info.get('name', '未知')}
公司: {self.customer_info.get('company', '未知')}
邮箱: {self.customer_info.get('email', '未知')}

【系统信息】
操作系统: {platform.system()} {platform.release()}
机器名称: {platform.node()}
软件版本: 2.4

【续费需求】
请帮助续费此License，延长使用期限。

【联系方式】
邮箱: {self.customer_info.get('email', '请填写您的邮箱')}
电话: {self.customer_info.get('phone', '请填写您的电话')}

=================================================
请将此信息发送至: license@your-company.com
=================================================
"""
        return content.strip()
    
    def copy_request_to_clipboard(self):
        """复制续费申请到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.request_text.toPlainText())
        
        QMessageBox.information(
            self,
            "复制成功",
            "续费申请信息已复制到剪贴板！\n\n"
            "请粘贴到邮件中发送给管理员。"
        )


class QuickRenewalGuideDialog(QDialog):
    """快速续费指南对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("License续费指南")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("📖 License续费完整指南")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        layout.addSpacing(20)
        
        # 指南内容
        guide_text = QTextEdit()
        guide_text.setReadOnly(True)
        
        guide_content = """
<h2>续费流程（3个步骤）</h2>

<h3>步骤1: 发送续费申请</h3>
<ol>
<li>点击"续费提醒"对话框中的"复制续费申请信息"按钮</li>
<li>打开邮件客户端，新建邮件</li>
<li>收件人: <b>license@your-company.com</b></li>
<li>主题: <b>License续费申请 - [您的公司名称]</b></li>
<li>粘贴续费申请信息到邮件正文</li>
<li>发送邮件</li>
</ol>

<h3>步骤2: 等待管理员处理</h3>
<ul>
<li>管理员会在1-2个工作日内处理您的续费申请</li>
<li>处理完成后，会通过邮件发送新的配置文件</li>
<li>配置文件名称: <b>license_config.txt</b></li>
</ul>

<h3>步骤3: 更新License配置</h3>
<ol>
<li>下载管理员发送的 <b>license_config.txt</b> 文件</li>
<li>将文件放到以下位置：
    <ul>
    <li>Windows: <code>C:\\Users\\用户名\\.desi_analytics\\license_config.txt</code></li>
    <li>macOS/Linux: <code>~/.desi_analytics/license_config.txt</code></li>
    </ul>
</li>
<li>重启DESI软件</li>
<li>验证License已更新（帮助 → 许可证信息）</li>
</ol>

<h2>常见问题</h2>

<h3>Q: 续费需要多长时间？</h3>
<p>A: 通常1-2个工作日内完成。紧急情况可电话联系。</p>

<h3>Q: 续费期间可以继续使用吗？</h3>
<p>A: 如果许可证已过期，部分功能会受限。建议提前30天续费。</p>

<h3>Q: 配置文件放错位置怎么办？</h3>
<p>A: 软件无法识别，需要重新放到正确位置并重启。</p>

<h3>Q: 如何确认续费成功？</h3>
<p>A: 打开软件 → 帮助 → 许可证信息，查看到期时间是否已更新。</p>

<h2>联系方式</h2>
<p>
<b>邮箱:</b> license@your-company.com<br>
<b>电话:</b> 400-XXX-XXXX<br>
<b>工作时间:</b> 周一至周五 9:00-18:00
</p>
"""
        
        guide_text.setHtml(guide_content)
        layout.addWidget(guide_text)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 测试续费提醒对话框
    print("[测试] 测试License续费提醒对话框")
    
    customer_info = {
        'customer_id': 'CUST-6FA90D6C',
        'name': '张三',
        'company': '测试公司',
        'email': 'zhangsan@test.com',
        'phone': '138-0000-0000'
    }
    
    # 测试不同状态
    test_cases = [
        (30, "30天提醒"),
        (7, "7天紧急提醒"),
        (-1, "已过期")
    ]
    
    for days, desc in test_cases:
        print(f"\n测试: {desc} (剩余{days}天)")
        dialog = LicenseRenewalDialog(
            days_left=days,
            license_key="DESI-F6F9C4FD-C06344B1-4561",
            customer_info=customer_info
        )
        dialog.exec_()
    
    # 测试续费指南
    print("\n测试: 续费指南")
    guide_dialog = QuickRenewalGuideDialog()
    guide_dialog.exec_()
    
    print("\n[成功] 所有测试完成")

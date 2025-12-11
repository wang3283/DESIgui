#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主程序License验证集成补丁

使用方法：
在 main_gui_ultimate.py 的 MainWindow.__init__() 开头添加：

    # License验证（商业化计费）
    from license_integration import LicenseIntegration
    from license_validation_dialog import (
        LicenseValidationDialog, LicenseReminderDialog, LicenseUpdateDialog
    )
    
    self.license_integration = LicenseIntegration()
    
    # 启动时检查License
    is_valid, message, days_left = self.license_integration.check_license_on_startup()
    
    if not is_valid:
        # License无效或不存在
        if days_left is not None and days_left < 0:
            # 已过期，显示提醒
            dialog = LicenseReminderDialog(days_left, self.license_integration.license_key, self)
            dialog.exec_()
        else:
            # 首次使用或格式错误
            dialog = LicenseValidationDialog(self)
            if dialog.exec_() != QDialog.Accepted:
                # 用户取消，退出程序
                sys.exit(0)
            
            # 重新检查
            is_valid, message, days_left = self.license_integration.check_license_on_startup()
    
    # 显示到期提醒（如果需要）
    should_show, level = self.license_integration.should_show_reminder()
    if should_show and level != 'expired':
        dialog = LicenseReminderDialog(days_left, self.license_integration.license_key, self)
        dialog.exec_()

在需要限制功能的地方添加检查：

    def load_sample(self):
        # 检查License
        if not self.license_integration.is_feature_allowed('load_sample'):
            QMessageBox.warning(
                self, "功能受限",
                self.license_integration.get_feature_restriction_message('load_sample')
            )
            return
        
        # 原有的加载逻辑
        ...

在菜单栏添加License管理菜单：

    # 在 create_menu_bar() 的 tools_menu 中添加
    tools_menu.addSeparator()
    
    license_info_action = QAction('许可证信息', self)
    license_info_action.triggered.connect(self.show_license_info)
    tools_menu.addAction(license_info_action)
    
    update_license_action = QAction('更新License', self)
    update_license_action.triggered.connect(self.update_license)
    tools_menu.addAction(update_license_action)

添加License管理方法：

    def show_license_info(self):
        \"\"\"显示许可证信息\"\"\"
        info = self.license_integration.get_license_info()
        
        message = f"许可证信息\\n\\n"
        message += f"许可证密钥: {info['license_key']}\\n"
        
        if info['expires_at']:
            message += f"到期时间: {info['expires_at'][:10]}\\n"
            if info['days_left'] is not None:
                if info['days_left'] >= 0:
                    message += f"剩余天数: {info['days_left']} 天\\n"
                else:
                    message += f"已过期: {abs(info['days_left'])} 天\\n"
        else:
            message += f"到期时间: 无限期\\n"
        
        message += f"\\n状态: {'有效' if info['is_valid'] else '无效'}\\n"
        
        if info['features_restricted']:
            message += f"\\n[警告] 功能已受限\\n"
            message += f"请联系管理员续费"
        
        QMessageBox.information(self, "许可证信息", message)
    
    def update_license(self):
        \"\"\"更新License\"\"\"
        dialog = LicenseUpdateDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # 重新检查License
            is_valid, message, days_left = self.license_integration.check_license_on_startup()
            
            if is_valid:
                QMessageBox.information(
                    self, "成功",
                    "License已更新！\\n\\n"
                    "所有功能已恢复。"
                )
            else:
                QMessageBox.warning(
                    self, "警告",
                    f"License验证失败:\\n{message}"
                )
"""

# 这是一个示例集成代码，展示如何在主程序中集成License验证

def integrate_license_to_main_window():
    """
    集成License验证到主窗口的示例代码
    
    这个函数展示了完整的集成流程
    """
    
    # 1. 在 __init__() 开头添加License验证
    init_code = '''
    # License验证（商业化计费）
    from license_integration import LicenseIntegration
    from license_validation_dialog import (
        LicenseValidationDialog, LicenseReminderDialog, LicenseUpdateDialog
    )
    from PyQt5.QtWidgets import QDialog
    
    self.license_integration = LicenseIntegration()
    
    # 启动时检查License
    is_valid, message, days_left = self.license_integration.check_license_on_startup()
    
    if not is_valid:
        # License无效或不存在
        if days_left is not None and days_left < 0:
            # 已过期，显示提醒
            dialog = LicenseReminderDialog(days_left, self.license_integration.license_key, self)
            dialog.exec_()
        else:
            # 首次使用或格式错误
            dialog = LicenseValidationDialog(self)
            if dialog.exec_() != QDialog.Accepted:
                # 用户取消，退出程序
                import sys
                sys.exit(0)
            
            # 重新检查
            is_valid, message, days_left = self.license_integration.check_license_on_startup()
    
    # 显示到期提醒（如果需要）
    should_show, level = self.license_integration.should_show_reminder()
    if should_show and level != 'expired':
        dialog = LicenseReminderDialog(days_left, self.license_integration.license_key, self)
        dialog.exec_()
    '''
    
    # 2. 添加功能限制检查的示例
    feature_check_code = '''
    def load_sample_with_license_check(self):
        """加载样本（带License检查）"""
        # 检查License
        if not self.license_integration.is_feature_allowed('load_sample'):
            QMessageBox.warning(
                self, "功能受限",
                self.license_integration.get_feature_restriction_message('load_sample')
            )
            return
        
        # 原有的加载逻辑
        self.load_sample()
    '''
    
    # 3. 添加License管理菜单的示例
    menu_code = '''
    # 在 create_menu_bar() 的 tools_menu 中添加
    tools_menu.addSeparator()
    
    license_info_action = QAction('📋 许可证信息', self)
    license_info_action.triggered.connect(self.show_license_info)
    tools_menu.addAction(license_info_action)
    
    update_license_action = QAction('🔄 更新License', self)
    update_license_action.triggered.connect(self.update_license)
    tools_menu.addAction(update_license_action)
    '''
    
    # 4. 添加License管理方法的示例
    methods_code = '''
    def show_license_info(self):
        """显示许可证信息"""
        info = self.license_integration.get_license_info()
        
        message = "许可证信息\\n\\n"
        message += f"许可证密钥: {info['license_key']}\\n"
        
        if info['expires_at']:
            message += f"到期时间: {info['expires_at'][:10]}\\n"
            if info['days_left'] is not None:
                if info['days_left'] >= 0:
                    message += f"剩余天数: {info['days_left']} 天\\n"
                else:
                    message += f"已过期: {abs(info['days_left'])} 天\\n"
        else:
            message += "到期时间: 无限期\\n"
        
        message += f"\\n状态: {'有效' if info['is_valid'] else '无效'}\\n"
        
        if info['features_restricted']:
            message += "\\n[警告] 功能已受限\\n"
            message += "请联系管理员续费"
        
        QMessageBox.information(self, "许可证信息", message)
    
    def update_license(self):
        """更新License"""
        dialog = LicenseUpdateDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # 重新检查License
            is_valid, message, days_left = self.license_integration.check_license_on_startup()
            
            if is_valid:
                QMessageBox.information(
                    self, "成功",
                    "License已更新！\\n\\n"
                    "所有功能已恢复。"
                )
                
                # 刷新界面状态
                self.refresh_ui_state()
            else:
                QMessageBox.warning(
                    self, "警告",
                    f"License验证失败:\\n{message}"
                )
    
    def refresh_ui_state(self):
        """刷新UI状态（根据License状态启用/禁用功能）"""
        is_restricted = self.license_integration.should_restrict_features()
        
        # 更新菜单项状态
        # 这里可以根据需要启用/禁用特定菜单项
        pass
    '''
    
    return {
        'init_code': init_code,
        'feature_check_code': feature_check_code,
        'menu_code': menu_code,
        'methods_code': methods_code
    }


if __name__ == "__main__":
    print("=" * 70)
    print("License验证集成补丁")
    print("=" * 70)
    print()
    print("这个文件包含了将License验证集成到主程序的示例代码。")
    print()
    print("集成步骤：")
    print("1. 在 MainWindow.__init__() 开头添加License验证代码")
    print("2. 在需要限制的功能中添加License检查")
    print("3. 在菜单栏添加License管理选项")
    print("4. 添加许可证信息显示和更新方法")
    print()
    print("详细代码请查看文件内容。")
    print("=" * 70)
    
    # 生成集成代码
    codes = integrate_license_to_main_window()
    
    print("\n[信息] 集成代码已生成")
    print(f"  - 初始化代码: {len(codes['init_code'])} 字符")
    print(f"  - 功能检查代码: {len(codes['feature_check_code'])} 字符")
    print(f"  - 菜单代码: {len(codes['menu_code'])} 字符")
    print(f"  - 方法代码: {len(codes['methods_code'])} 字符")

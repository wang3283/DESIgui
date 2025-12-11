#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据过滤配置对话框
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton,
    QLineEdit, QFileDialog, QTextEdit, QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from pathlib import Path

from data_filter_config import DataFilterConfig


class DataFilterDialog(QDialog):
    """数据过滤配置对话框"""
    
    # 配置改变信号
    config_changed = pyqtSignal(object)
    
    def __init__(self, parent=None, config: DataFilterConfig = None):
        super().__init__(parent)
        
        self.config = config if config else DataFilterConfig()
        
        self.setWindowTitle('数据过滤设置 - 减少处理量')
        self.setGeometry(200, 200, 600, 650)
        
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 启用过滤
        self.enable_checkbox = QCheckBox('启用数据过滤（减少内存和计算时间）')
        self.enable_checkbox.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.enable_checkbox.stateChanged.connect(self.on_enable_changed)
        layout.addWidget(self.enable_checkbox)
        
        layout.addSpacing(10)
        
        # ===== Top N 高强度峰 =====
        top_n_group = QGroupBox('1. 选择最高强度的离子峰')
        top_n_layout = QVBoxLayout()
        
        self.use_top_n_checkbox = QCheckBox('启用Top N过滤')
        top_n_layout.addWidget(self.use_top_n_checkbox)
        
        top_n_input_layout = QHBoxLayout()
        top_n_input_layout.addWidget(QLabel('最高强度峰数量:'))
        self.top_n_spinbox = QSpinBox()
        self.top_n_spinbox.setRange(10, 10000)
        self.top_n_spinbox.setValue(1000)
        self.top_n_spinbox.setSingleStep(100)
        top_n_input_layout.addWidget(self.top_n_spinbox)
        top_n_input_layout.addWidget(QLabel('个'))
        top_n_input_layout.addStretch()
        top_n_layout.addLayout(top_n_input_layout)
        
        info_label = QLabel(
            '[提示] 只保留总强度最高的N个离子，减少数据量\n'
            '   推荐: 1000-2000 (日常分析), 500 (快速预览)'
        )
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        top_n_layout.addWidget(info_label)
        
        top_n_group.setLayout(top_n_layout)
        layout.addWidget(top_n_group)
        
        # ===== m/z 范围过滤 =====
        mz_range_group = QGroupBox('2. m/z 范围过滤')
        mz_range_layout = QVBoxLayout()
        
        self.use_mz_range_checkbox = QCheckBox('启用m/z范围过滤')
        mz_range_layout.addWidget(self.use_mz_range_checkbox)
        
        # Start m/z
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel('Start:'))
        self.mz_start_spinbox = QDoubleSpinBox()
        self.mz_start_spinbox.setRange(0, 5000)
        self.mz_start_spinbox.setValue(50)
        self.mz_start_spinbox.setDecimals(1)
        start_layout.addWidget(self.mz_start_spinbox)
        start_layout.addWidget(QLabel('m/z'))
        start_layout.addStretch()
        mz_range_layout.addLayout(start_layout)
        
        # Stop m/z
        stop_layout = QHBoxLayout()
        stop_layout.addWidget(QLabel('Stop:'))
        self.mz_stop_spinbox = QDoubleSpinBox()
        self.mz_stop_spinbox.setRange(0, 5000)
        self.mz_stop_spinbox.setValue(1200)
        self.mz_stop_spinbox.setDecimals(1)
        stop_layout.addWidget(self.mz_stop_spinbox)
        stop_layout.addWidget(QLabel('m/z'))
        stop_layout.addStretch()
        mz_range_layout.addLayout(stop_layout)
        
        info_label2 = QLabel(
            '[提示] 只保留指定m/z范围内的数据\n'
            '   示例: 50-1200 (常用范围)'
        )
        info_label2.setStyleSheet("color: #666; font-size: 11px;")
        mz_range_layout.addWidget(info_label2)
        
        mz_range_group.setLayout(mz_range_layout)
        layout.addWidget(mz_range_group)
        
        # ===== 目标 m/z 列表 =====
        target_group = QGroupBox('3. 目标 m/z 列表（可选）')
        target_layout = QVBoxLayout()
        
        self.import_file_checkbox = QCheckBox('从文件导入目标m/z列表')
        self.import_file_checkbox.stateChanged.connect(self.on_import_checkbox_changed)
        target_layout.addWidget(self.import_file_checkbox)
        
        # 文件选择
        file_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText('选择包含目标m/z的文本文件 (每行一个m/z值)')
        self.file_path_edit.setReadOnly(True)
        file_layout.addWidget(self.file_path_edit)
        
        browse_btn = QPushButton('浏览...')
        browse_btn.clicked.connect(self.browse_target_file)
        file_layout.addWidget(browse_btn)
        target_layout.addLayout(file_layout)
        
        # 目标m/z显示
        self.target_masses_display = QTextEdit()
        self.target_masses_display.setMaximumHeight(80)
        self.target_masses_display.setPlaceholderText(
            '加载的目标m/z将显示在这里...\n'
            '或手动输入，每行一个m/z值'
        )
        target_layout.addWidget(self.target_masses_display)
        
        # m/z window
        window_layout = QHBoxLayout()
        window_layout.addWidget(QLabel('M/z window:'))
        self.mz_window_spinbox = QDoubleSpinBox()
        self.mz_window_spinbox.setRange(0.001, 1.0)
        self.mz_window_spinbox.setValue(0.02)
        self.mz_window_spinbox.setDecimals(3)
        self.mz_window_spinbox.setSingleStep(0.01)
        window_layout.addWidget(self.mz_window_spinbox)
        window_layout.addWidget(QLabel('Da'))
        window_layout.addStretch()
        target_layout.addLayout(window_layout)
        
        info_label3 = QLabel(
            '[提示] 只保留与目标m/z匹配的离子\n'
            '   文件格式: 每行一个m/z值，如:\n'
            '   283.2634\n'
            '   554.2615'
        )
        info_label3.setStyleSheet("color: #666; font-size: 11px;")
        target_layout.addWidget(info_label3)
        
        target_group.setLayout(target_layout)
        layout.addWidget(target_group)
        
        # ===== 高级设置 =====
        advanced_group = QGroupBox('高级设置')
        advanced_layout = QVBoxLayout()
        
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel('MS Resolution:'))
        self.ms_resolution_spinbox = QSpinBox()
        self.ms_resolution_spinbox.setRange(1000, 1000000)
        self.ms_resolution_spinbox.setValue(20000)
        self.ms_resolution_spinbox.setSingleStep(1000)
        resolution_layout.addWidget(self.ms_resolution_spinbox)
        resolution_layout.addStretch()
        advanced_layout.addLayout(resolution_layout)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        # ===== 按钮 =====
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_config)
        layout.addWidget(button_box)
        
        # 初始状态
        self.on_enable_changed()
    
    def on_enable_changed(self):
        """启用状态改变"""
        enabled = self.enable_checkbox.isChecked()
        
        # 启用/禁用所有控件
        for widget in self.findChildren(QGroupBox):
            widget.setEnabled(enabled)
    
    def on_import_checkbox_changed(self):
        """导入文件复选框状态改变"""
        enabled = self.import_file_checkbox.isChecked()
        self.file_path_edit.setEnabled(enabled)
        self.target_masses_display.setEnabled(enabled)
        self.mz_window_spinbox.setEnabled(enabled)
    
    def browse_target_file(self):
        """浏览目标m/z文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            '选择目标m/z文件',
            '',
            'Text Files (*.txt);;All Files (*)'
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            
            # 加载并显示m/z
            try:
                masses = []
                with open(file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            try:
                                mz = float(line)
                                masses.append(mz)
                            except ValueError:
                                continue
                
                # 显示前20个
                display_text = '\n'.join([f"{mz:.4f}" for mz in masses[:20]])
                if len(masses) > 20:
                    display_text += f"\n\n... 共 {len(masses)} 个m/z"
                
                self.target_masses_display.setPlainText(display_text)
                
            except Exception as e:
                self.target_masses_display.setPlainText(f"[错误] 读取失败: {e}")
    
    def load_config(self):
        """加载配置到UI"""
        self.enable_checkbox.setChecked(self.config.enabled)
        
        self.use_top_n_checkbox.setChecked(self.config.use_top_n)
        self.top_n_spinbox.setValue(self.config.top_n_peaks)
        
        self.use_mz_range_checkbox.setChecked(self.config.use_mz_range)
        self.mz_start_spinbox.setValue(self.config.mz_start)
        self.mz_stop_spinbox.setValue(self.config.mz_stop)
        
        self.import_file_checkbox.setChecked(self.config.import_from_file)
        self.mz_window_spinbox.setValue(self.config.mz_window)
        self.ms_resolution_spinbox.setValue(self.config.ms_resolution)
        
        if self.config.target_mass_file:
            self.file_path_edit.setText(str(self.config.target_mass_file))
        
        if self.config.target_masses:
            display_text = '\n'.join([f"{mz:.4f}" for mz in self.config.target_masses[:20]])
            if len(self.config.target_masses) > 20:
                display_text += f"\n\n... 共 {len(self.config.target_masses)} 个m/z"
            self.target_masses_display.setPlainText(display_text)
    
    def save_config(self):
        """从UI保存配置"""
        self.config.enabled = self.enable_checkbox.isChecked()
        
        self.config.use_top_n = self.use_top_n_checkbox.isChecked()
        self.config.top_n_peaks = self.top_n_spinbox.value()
        
        self.config.use_mz_range = self.use_mz_range_checkbox.isChecked()
        self.config.mz_start = self.mz_start_spinbox.value()
        self.config.mz_stop = self.mz_stop_spinbox.value()
        
        self.config.import_from_file = self.import_file_checkbox.isChecked()
        self.config.mz_window = self.mz_window_spinbox.value()
        self.config.ms_resolution = self.ms_resolution_spinbox.value()
        
        # 从文本框读取目标m/z
        if self.import_file_checkbox.isChecked():
            file_path = self.file_path_edit.text()
            if file_path:
                self.config.load_target_masses_from_file(Path(file_path))
            else:
                # 从文本框手动读取
                text = self.target_masses_display.toPlainText()
                masses = []
                for line in text.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('...'):
                        try:
                            mz = float(line)
                            masses.append(mz)
                        except ValueError:
                            continue
                self.config.target_masses = masses
    
    def apply_config(self):
        """应用配置"""
        self.save_config()
        self.config_changed.emit(self.config)
        print(f"[成功] 数据过滤配置已应用: {self.config.get_filter_description()}")
    
    def accept(self):
        """确定"""
        self.save_config()
        self.config_changed.emit(self.config)
        super().accept()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lock Mass配置对话框

提供Lock Mass参数配置界面
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QLineEdit, QCheckBox, QPushButton,
                             QDoubleSpinBox, QSpinBox, QTableWidget, QTableWidgetItem,
                             QTabWidget, QWidget, QTextEdit, QSplitter, QMessageBox,
                             QFileDialog, QHeaderView)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np

from mass_calibration_manager import LockMassConfig, MassCalibrationManager


class CalibrationPlot(FigureCanvasQTAgg):
    """校准历史绘图"""
    
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(8, 4))
        super().__init__(self.fig)
        self.setParent(parent)
        
        # 创建子图
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212)
        
        self.fig.tight_layout(pad=2.0)
    
    def update_plot(self, calibration_history):
        """更新绘图"""
        self.ax1.clear()
        self.ax2.clear()
        
        if not calibration_history:
            self.ax1.text(0.5, 0.5, '暂无校准数据', 
                         ha='center', va='center', transform=self.ax1.transAxes)
            self.draw()
            return
        
        # 提取数据
        times = list(range(len(calibration_history)))
        errors_ppm = [rec['error_ppm'] for rec in calibration_history]
        corrections = [rec['correction'] for rec in calibration_history]
        
        # 绘制误差曲线
        self.ax1.plot(times, errors_ppm, 'o-', color='#2196F3', markersize=4)
        self.ax1.axhline(y=0, color='red', linestyle='--', alpha=0.5, linewidth=1)
        self.ax1.set_ylabel('质量误差 (ppm)', fontsize=10)
        self.ax1.set_title('Lock Mass质量误差趋势', fontsize=11, fontweight='bold')
        self.ax1.grid(True, alpha=0.3)
        
        # 绘制校正值曲线
        self.ax2.plot(times, corrections, 's-', color='#4CAF50', markersize=4)
        self.ax2.axhline(y=0, color='red', linestyle='--', alpha=0.5, linewidth=1)
        self.ax2.set_xlabel('校准次数', fontsize=10)
        self.ax2.set_ylabel('校正值 (Da)', fontsize=10)
        self.ax2.set_title('质量校正值变化', fontsize=11, fontweight='bold')
        self.ax2.grid(True, alpha=0.3)
        
        self.fig.tight_layout(pad=2.0)
        self.draw()


class LockMassDialog(QDialog):
    """Lock Mass配置对话框"""
    
    config_changed = pyqtSignal(LockMassConfig)
    
    def __init__(self, parent=None, config=None, manager=None):
        super().__init__(parent)
        
        self.config = config or LockMassConfig()
        self.manager = manager or MassCalibrationManager(self.config)
        
        self.setWindowTitle('Lock Mass 质量校准设置')
        self.setMinimumSize(900, 700)
        
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel('[TARGET] Lock Mass 质量校准配置')
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Tab切换
        tabs = QTabWidget()
        
        # Tab 1: 基本设置
        settings_tab = self.create_settings_tab()
        tabs.addTab(settings_tab, '[SETTINGS] 基本设置')
        
        # Tab 2: 校准历史
        history_tab = self.create_history_tab()
        tabs.addTab(history_tab, '[STATS] 校准历史')
        
        # Tab 3: 使用说明
        help_tab = self.create_help_tab()
        tabs.addTab(help_tab, '📖 使用说明')
        
        layout.addWidget(tabs)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton('[SAVE] 保存配置')
        save_btn.clicked.connect(self.save_config_to_file)
        button_layout.addWidget(save_btn)
        
        load_btn = QPushButton('📂 加载配置')
        load_btn.clicked.connect(self.load_config_from_file)
        button_layout.addWidget(load_btn)
        
        apply_btn = QPushButton('[成功] 应用')
        apply_btn.clicked.connect(self.apply_config)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 20px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(apply_btn)
        
        close_btn = QPushButton('关闭')
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def create_settings_tab(self):
        """创建设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Lock Mass参数组
        lock_mass_group = QGroupBox('Lock Mass 参数')
        lock_mass_layout = QVBoxLayout()
        
        # 启用/禁用
        self.enable_check = QCheckBox('启用 Lock Mass 校准')
        self.enable_check.setStyleSheet('font-weight: bold; font-size: 12px;')
        lock_mass_layout.addWidget(self.enable_check)
        
        # Lock mass m/z
        mz_layout = QHBoxLayout()
        mz_layout.addWidget(QLabel('Lock Mass m/z:'))
        self.lock_mass_input = QDoubleSpinBox()
        self.lock_mass_input.setRange(50, 2000)
        self.lock_mass_input.setDecimals(4)
        self.lock_mass_input.setValue(554.2615)
        self.lock_mass_input.setSuffix(' m/z')
        self.lock_mass_input.setMinimumWidth(150)
        mz_layout.addWidget(self.lock_mass_input)
        mz_layout.addWidget(QLabel('(参考离子的理论m/z值)'))
        mz_layout.addStretch()
        lock_mass_layout.addLayout(mz_layout)
        
        # Lock mass tolerance
        tol_layout = QHBoxLayout()
        tol_layout.addWidget(QLabel('Lock Mass 容差:'))
        self.tolerance_input = QDoubleSpinBox()
        self.tolerance_input.setRange(0.01, 5.0)
        self.tolerance_input.setDecimals(2)
        self.tolerance_input.setValue(0.25)
        self.tolerance_input.setSuffix(' amu')
        self.tolerance_input.setMinimumWidth(150)
        tol_layout.addWidget(self.tolerance_input)
        tol_layout.addWidget(QLabel('(搜索Lock Mass峰的m/z范围)'))
        tol_layout.addStretch()
        lock_mass_layout.addLayout(tol_layout)
        
        # Max signal intensity
        max_int_layout = QHBoxLayout()
        max_int_layout.addWidget(QLabel('最大信号强度:'))
        self.max_intensity_input = QSpinBox()
        self.max_intensity_input.setRange(0, 1000000)
        self.max_intensity_input.setValue(500)
        self.max_intensity_input.setSuffix(' counts')
        self.max_intensity_input.setSpecialValueText('无限制')
        self.max_intensity_input.setMinimumWidth(150)
        max_int_layout.addWidget(self.max_intensity_input)
        max_int_layout.addWidget(QLabel('(0表示无限制，避免饱和干扰)'))
        max_int_layout.addStretch()
        lock_mass_layout.addLayout(max_int_layout)
        
        # Use internal lock mass
        self.internal_check = QCheckBox('使用内标 Lock Mass')
        lock_mass_layout.addWidget(self.internal_check)
        
        lock_mass_group.setLayout(lock_mass_layout)
        layout.addWidget(lock_mass_group)
        
        # 采样参数组
        sampling_group = QGroupBox('[TIMER] 采样参数')
        sampling_layout = QVBoxLayout()
        
        # Sample frequency
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel('采样频率:'))
        self.frequency_input = QSpinBox()
        self.frequency_input.setRange(1, 60)
        self.frequency_input.setValue(1)
        self.frequency_input.setSuffix(' 分钟')
        self.frequency_input.setMinimumWidth(150)
        freq_layout.addWidget(self.frequency_input)
        freq_layout.addWidget(QLabel('(每隔多久进行一次校准)'))
        freq_layout.addStretch()
        sampling_layout.addLayout(freq_layout)
        
        # Sample duration
        dur_layout = QHBoxLayout()
        dur_layout.addWidget(QLabel('采样持续时间:'))
        self.duration_input = QSpinBox()
        self.duration_input.setRange(1, 300)
        self.duration_input.setValue(10)
        self.duration_input.setSuffix(' 秒')
        self.duration_input.setMinimumWidth(150)
        dur_layout.addWidget(self.duration_input)
        dur_layout.addWidget(QLabel('(每次采样的时长)'))
        dur_layout.addStretch()
        sampling_layout.addLayout(dur_layout)
        
        sampling_group.setLayout(sampling_layout)
        layout.addWidget(sampling_group)
        
        # 离子合并参数组
        merge_group = QGroupBox('🔗 离子合并参数')
        merge_layout = QVBoxLayout()
        
        merge_tol_layout = QHBoxLayout()
        merge_tol_layout.addWidget(QLabel('合并容差:'))
        self.merge_tolerance_input = QDoubleSpinBox()
        self.merge_tolerance_input.setRange(1, 100)
        self.merge_tolerance_input.setDecimals(1)
        self.merge_tolerance_input.setValue(10)
        self.merge_tolerance_input.setSuffix(' ppm')
        self.merge_tolerance_input.setMinimumWidth(150)
        merge_tol_layout.addWidget(self.merge_tolerance_input)
        merge_tol_layout.addWidget(QLabel('(容差范围内的m/z识别为同一离子)'))
        merge_tol_layout.addStretch()
        merge_layout.addLayout(merge_tol_layout)
        
        # 示例
        example_label = QLabel(
            '[提示] 示例: 设置为10 ppm时，对于m/z=500的离子\n'
            '   m/z在499.995~500.005范围内的峰会被识别为同一离子\n'
            '   它们的强度会被累加，m/z取强度加权平均值'
        )
        example_label.setStyleSheet('color: #666; padding: 10px; background-color: #f5f5f5; border-radius: 4px;')
        merge_layout.addWidget(example_label)
        
        merge_group.setLayout(merge_layout)
        layout.addWidget(merge_group)
        
        layout.addStretch()
        
        return widget
    
    def create_history_tab(self):
        """创建历史标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 统计信息
        stats_group = QGroupBox('[TREND] 校准统计')
        stats_layout = QVBoxLayout()
        
        self.stats_text = QLabel('暂无校准数据')
        self.stats_text.setStyleSheet('padding: 10px; background-color: #f5f5f5; border-radius: 4px;')
        stats_layout.addWidget(self.stats_text)
        
        # 刷新按钮
        refresh_btn = QPushButton('🔄 刷新')
        refresh_btn.clicked.connect(self.update_history)
        stats_layout.addWidget(refresh_btn)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # 校准历史图表
        plot_group = QGroupBox('[STATS] 校准趋势')
        plot_layout = QVBoxLayout()
        
        self.calibration_plot = CalibrationPlot()
        plot_layout.addWidget(self.calibration_plot)
        
        # 导出按钮
        export_btn = QPushButton('[SEND] 导出历史数据')
        export_btn.clicked.connect(self.export_history)
        plot_layout.addWidget(export_btn)
        
        plot_group.setLayout(plot_layout)
        layout.addWidget(plot_group)
        
        return widget
    
    def create_help_tab(self):
        """创建帮助标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h2>[TARGET] Lock Mass 质量校准功能说明</h2>
        
        <h3>📋 功能概述</h3>
        <p>Lock Mass（质量锁定）是质谱仪器中用于实时校正质量漂移的重要功能。通过定期监测一个已知m/z的参考离子，
        系统可以自动检测和补偿仪器的质量漂移，确保长时间测量的准确性和一致性。</p>
        
        <h3>[SETTINGS] 参数说明</h3>
        
        <h4>Lock Mass 参数：</h4>
        <ul>
            <li><b>Lock Mass m/z</b>: 参考离子的理论m/z值（如554.2615）</li>
            <li><b>Lock Mass 容差</b>: 搜索参考离子时的m/z容差范围（amu）</li>
            <li><b>最大信号强度</b>: 参考峰的强度上限，避免饱和信号干扰（0=无限制）</li>
            <li><b>使用内标</b>: 是否使用内标物质作为Lock Mass</li>
        </ul>
        
        <h4>采样参数：</h4>
        <ul>
            <li><b>采样频率</b>: 每隔多久进行一次Lock Mass采样和校准（分钟）</li>
            <li><b>采样持续时间</b>: 每次采样的时长（秒）</li>
        </ul>
        
        <h4>离子合并参数：</h4>
        <ul>
            <li><b>合并容差</b>: m/z在此容差范围内的离子会被识别为同一个（ppm）</li>
        </ul>
        
        <h3>🔬 工作原理</h3>
        <ol>
            <li><b>采样</b>: 按设定频率采集质谱数据</li>
            <li><b>识别</b>: 在数据中搜索Lock Mass峰（理论值±容差范围）</li>
            <li><b>计算</b>: 计算实测值与理论值的偏差（校正值）</li>
            <li><b>校正</b>: 将校正值应用到所有离子的m/z</li>
            <li><b>合并</b>: 将容差范围内的m/z合并为同一离子</li>
        </ol>
        
        <h3>[提示] 使用建议</h3>
        <ul>
            <li>选择在整个质量范围内稳定存在的离子作为Lock Mass</li>
            <li>Lock Mass峰应具有足够的强度，但不应过强（避免饱和）</li>
            <li>采样频率根据仪器漂移速度调整（典型值：1-5分钟）</li>
            <li>离子合并容差通常设置为5-20 ppm</li>
            <li>定期查看校准历史，监测仪器稳定性</li>
        </ul>
        
        <h3>[STATS] 校准历史</h3>
        <p>系统会记录每次校准的结果，包括：</p>
        <ul>
            <li>校准时间</li>
            <li>测量的Lock Mass m/z值</li>
            <li>计算的校正值</li>
            <li>质量误差（ppm）</li>
            <li>Lock Mass峰强度</li>
        </ul>
        
        <p>您可以在"校准历史"标签页查看趋势图和统计信息，并导出数据进行分析。</p>
        
        <h3>[警告] 注意事项</h3>
        <ul>
            <li>确保Lock Mass离子在整个实验过程中持续存在</li>
            <li>避免选择可能与样本离子重叠的m/z作为Lock Mass</li>
            <li>如果Lock Mass峰未找到，系统会跳过该次校准</li>
            <li>校准历史可以帮助评估仪器性能和数据质量</li>
        </ul>
        
        <hr>
        <p style="color: #666; font-size: 11px;">
        更新时间: 2025-10-27 | 版本: 1.0
        </p>
        """)
        layout.addWidget(help_text)
        
        return widget
    
    def load_config(self):
        """从配置对象加载到界面"""
        self.enable_check.setChecked(self.config.enabled)
        self.lock_mass_input.setValue(self.config.lock_mass_mz)
        self.tolerance_input.setValue(self.config.tolerance_amu)
        self.max_intensity_input.setValue(self.config.max_signal_intensity)
        self.internal_check.setChecked(self.config.use_internal)
        self.frequency_input.setValue(self.config.sample_frequency_min)
        self.duration_input.setValue(self.config.sample_duration_sec)
        self.merge_tolerance_input.setValue(self.config.merge_tolerance_ppm)
        
        self.update_history()
    
    def apply_config(self):
        """应用配置"""
        # 从界面读取到配置对象
        self.config.enabled = self.enable_check.isChecked()
        self.config.lock_mass_mz = self.lock_mass_input.value()
        self.config.tolerance_amu = self.tolerance_input.value()
        self.config.max_signal_intensity = self.max_intensity_input.value()
        self.config.use_internal = self.internal_check.isChecked()
        self.config.sample_frequency_min = self.frequency_input.value()
        self.config.sample_duration_sec = self.duration_input.value()
        self.config.merge_tolerance_ppm = self.merge_tolerance_input.value()
        
        # 发送信号
        self.config_changed.emit(self.config)
        
        QMessageBox.information(self, '成功', '[成功] Lock Mass配置已应用！')
    
    def update_history(self):
        """更新历史显示"""
        stats = self.manager.get_calibration_stats()
        
        if stats['total_calibrations'] == 0:
            self.stats_text.setText('暂无校准数据')
        else:
            text = f"""
            <b>总校准次数:</b> {stats['total_calibrations']}<br>
            <b>当前校正值:</b> {stats['current_correction']:.4f} Da<br>
            <b>平均误差:</b> {stats['mean_error_ppm']:.2f} ppm<br>
            <b>误差标准差:</b> {stats['std_error_ppm']:.2f} ppm<br>
            <b>最大误差:</b> {stats['max_error_ppm']:.2f} ppm
            """
            self.stats_text.setText(text)
        
        self.calibration_plot.update_plot(self.manager.correction_history)
    
    def export_history(self):
        """导出校准历史"""
        if not self.manager.correction_history:
            QMessageBox.warning(self, '警告', '暂无校准历史可导出')
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, '导出校准历史', '',
            'Excel文件 (*.xlsx);;CSV文件 (*.csv)'
        )
        
        if filename:
            try:
                self.manager.export_calibration_history(filename)
                QMessageBox.information(self, '成功', f'[成功] 校准历史已导出到:\n{filename}')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导出失败:\n{e}')
    
    def save_config_to_file(self):
        """保存配置到文件"""
        filename, _ = QFileDialog.getSaveFileName(
            self, '保存Lock Mass配置', 'lock_mass_config.json',
            'JSON文件 (*.json)'
        )
        
        if filename:
            try:
                # 先应用当前界面的设置
                self.apply_config()
                self.config.save(filename)
                QMessageBox.information(self, '成功', f'[成功] 配置已保存到:\n{filename}')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'保存失败:\n{e}')
    
    def load_config_from_file(self):
        """从文件加载配置"""
        filename, _ = QFileDialog.getOpenFileName(
            self, '加载Lock Mass配置', '',
            'JSON文件 (*.json)'
        )
        
        if filename:
            try:
                self.config.load(filename)
                self.load_config()
                QMessageBox.information(self, '成功', f'[成功] 配置已从文件加载:\n{filename}')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'加载失败:\n{e}')


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # 创建测试数据
    config = LockMassConfig()
    manager = MassCalibrationManager(config)
    
    # 添加一些测试历史数据
    import datetime
    for i in range(10):
        manager.correction_history.append({
            'time': datetime.datetime.now() - datetime.timedelta(minutes=i*5),
            'measured_mz': 554.2615 + np.random.randn() * 0.002,
            'theoretical_mz': 554.2615,
            'correction': np.random.randn() * 0.002,
            'intensity': 5000 + np.random.randn() * 500,
            'error_ppm': np.random.randn() * 3.6
        })
    
    dialog = LockMassDialog(config=config, manager=manager)
    dialog.show()
    
    sys.exit(app.exec_())


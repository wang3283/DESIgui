#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DESI空间代谢组学分析系统 - 终极完整版
所有功能完全实现，无"开发中"提示
"""

import sys
import os
import numpy as np
from datetime import datetime
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Polygon
from matplotlib.path import Path as MPLPath

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QListWidget, QTableWidget, QTableWidgetItem, QListWidgetItem,
    QPushButton, QLabel, QDoubleSpinBox, QFileDialog, QMessageBox,
    QHeaderView, QDialog, QDialogButtonBox, QComboBox, QSpinBox,
    QCheckBox, QGroupBox, QLineEdit, QAction, QToolBar, QStatusBar,
    QMenu, QTextEdit, QProgressBar, QRadioButton, QProgressDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QIcon, QFont
from pathlib import Path

from data_loader import DataLoader
from sample_comparison_dialog import SampleComparisonDialog
from mass_calibration_manager import LockMassConfig, MassCalibrationManager
from lock_mass_dialog import LockMassDialog
from report_generator import ReportGenerator

# 使用量追踪（商业化计费）- 延迟加载，不影响启动速度
USAGE_TRACKING_ENABLED = True


class MetaboliteSearchDialog(QDialog):
    """代谢物查询对话框（增强版：支持缓存数据库）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle('代谢物数据库查询')
        self.setGeometry(200, 200, 900, 700)
        
        # 使用新的在线注释器（支持缓存数据库）
        try:
            from online_metabolite_annotator import OnlineMetaboliteAnnotator
            self.annotator = OnlineMetaboliteAnnotator(use_cache_db=True)
            self.use_enhanced = True
            print("[成功] 使用增强版代谢物查询（支持缓存数据库）")
        except Exception as e:
            print(f"[错误] 代谢物注释初始化失败: {e}")
            print("[警告] 代谢物查询功能将不可用")
            self.annotator = None
            self.use_enhanced = False
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 输入区域
        input_group = QGroupBox('查询参数')
        input_layout = QHBoxLayout()
        
        input_layout.addWidget(QLabel('m/z:'))
        self.mz_input = QDoubleSpinBox()
        self.mz_input.setRange(0, 2000)
        self.mz_input.setDecimals(4)
        self.mz_input.setValue(100.0)
        input_layout.addWidget(self.mz_input)
        
        input_layout.addWidget(QLabel('容差(ppm):'))
        self.tolerance_input = QSpinBox()
        self.tolerance_input.setRange(1, 100)
        self.tolerance_input.setValue(10)
        input_layout.addWidget(self.tolerance_input)
        
        input_layout.addWidget(QLabel('离子模式:'))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(['positive', 'negative'])
        input_layout.addWidget(self.mode_combo)
        
        search_btn = QPushButton('查询')
        search_btn.clicked.connect(self.search)
        input_layout.addWidget(search_btn)
        
        input_layout.addStretch()
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # 结果表格
        self.result_table = QTableWidget()
        if self.use_enhanced:
            self.result_table.setColumnCount(8)
            self.result_table.setHorizontalHeaderLabels([
                '代谢物名称', '分子式', 'HMDB ID', '理论m/z', '测量m/z', 
                '误差(ppm)', '误差(Da)', '数据源'
            ])
        else:
            self.result_table.setColumnCount(6)
            self.result_table.setHorizontalHeaderLabels([
                '代谢物名称', '分子式', '理论m/z', '测量m/z', '误差(ppm)', '误差(Da)'
            ])
        
        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        layout.addWidget(self.result_table)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        export_btn = QPushButton('导出结果')
        export_btn.clicked.connect(self.export_results)
        button_layout.addWidget(export_btn)
        
        if self.use_enhanced:
            stats_btn = QPushButton('查看缓存统计')
            stats_btn.clicked.connect(self.show_cache_stats)
            button_layout.addWidget(stats_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton('关闭')
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def set_mz(self, mz):
        """设置m/z值"""
        self.mz_input.setValue(mz)
        self.search()
    
    def search(self):
        """执行查询（增强版：支持缓存数据库）"""
        mz = self.mz_input.value()
        tolerance = self.tolerance_input.value()
        mode = self.mode_combo.currentText()
        
        # 使用增强版注释器或基础数据库
        if self.use_enhanced:
            results = self.annotator.annotate_mz(mz, tolerance, mode)
            print(f"\n[SEARCH] 查询 m/z={mz:.4f} (±{tolerance}ppm, {mode})")
            print(f"   找到 {len(results)} 个匹配")
        else:
            results = self.db.search(mz, tolerance, mode)
        
        self.result_table.setRowCount(len(results))
        
        if not results:
            QMessageBox.information(self, '查询结果', 
                f'未找到匹配的代谢物\n\n'
                f'm/z: {mz:.4f}\n'
                f'容差: ±{tolerance} ppm\n'
                f'离子模式: {mode}')
            return
        
        for i, result in enumerate(results):
            self.result_table.setItem(i, 0, QTableWidgetItem(result['name']))
            self.result_table.setItem(i, 1, QTableWidgetItem(result['formula']))
            
            if self.use_enhanced:
                self.result_table.setItem(i, 2, QTableWidgetItem(result.get('hmdb_id', '')))
                self.result_table.setItem(i, 3, QTableWidgetItem(f"{result['theoretical_mz']:.4f}"))
                self.result_table.setItem(i, 4, QTableWidgetItem(f"{mz:.4f}"))
                self.result_table.setItem(i, 5, QTableWidgetItem(f"{result['error_ppm']:.2f}"))
                self.result_table.setItem(i, 6, QTableWidgetItem(f"{result['error_da']:.4f}"))
                self.result_table.setItem(i, 7, QTableWidgetItem(result.get('source', 'Unknown')))
            else:
                self.result_table.setItem(i, 2, QTableWidgetItem(f"{result['theoretical_mz']:.4f}"))
                self.result_table.setItem(i, 3, QTableWidgetItem(f"{mz:.4f}"))
                self.result_table.setItem(i, 4, QTableWidgetItem(f"{result['error_ppm']:.2f}"))
                self.result_table.setItem(i, 5, QTableWidgetItem(f"{result['error_da']:.4f}"))
        
        # 显示查询结果统计
        if self.use_enhanced:
            QMessageBox.information(self, '查询完成', 
                f'[成功] 找到 {len(results)} 个匹配的代谢物\n\n'
                f'm/z: {mz:.4f}\n'
                f'容差: ±{tolerance} ppm\n'
                f'离子模式: {mode}\n\n'
                f'结果已显示在表格中')
    
    def export_results(self):
        """导出查询结果"""
        if self.result_table.rowCount() == 0:
            QMessageBox.warning(self, '警告', '没有查询结果可导出')
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, '导出查询结果', '', 
            'Excel文件 (*.xlsx);;CSV文件 (*.csv)'
        )
        
        if filename:
            try:
                import pandas as pd
                
                data = []
                for row in range(self.result_table.rowCount()):
                    row_data = {}
                    for col in range(self.result_table.columnCount()):
                        header = self.result_table.horizontalHeaderItem(col).text()
                        item = self.result_table.item(row, col)
                        row_data[header] = item.text() if item else ''
                    data.append(row_data)
                
                df = pd.DataFrame(data)
                
                if filename.endswith('.xlsx'):
                    df.to_excel(filename, index=False, engine='openpyxl')
                else:
                    df.to_csv(filename, index=False, encoding='utf-8-sig')
                
                QMessageBox.information(self, '成功', f'查询结果已导出到:\n{filename}')
                print(f"[成功] 导出查询结果: {len(data)} 条记录")
            except Exception as e:
                QMessageBox.warning(self, '错误', f'导出失败: {e}')
    
    def show_cache_stats(self):
        """显示缓存统计信息"""
        if not self.use_enhanced or not hasattr(self.annotator, 'cache_db'):
            return
        
        try:
            stats = self.annotator.cache_db.get_stats()
            
            msg = f"[统计] 代谢物缓存数据库统计\n\n"
            msg += f"缓存记录总数:   {stats['total_cached_annotations']}\n"
            msg += f"总查询次数:     {stats['total_queries']}\n"
            msg += f"缓存命中次数:   {stats['cache_hits']}\n"
            msg += f"缓存未命中次数: {stats['cache_misses']}\n"
            msg += f"命中率:         {stats['hit_rate']:.1f}%\n"
            msg += f"最后更新时间:   {stats['last_updated']}\n"
            
            QMessageBox.information(self, '缓存统计', msg)
        except Exception as e:
            QMessageBox.warning(self, '错误', f'获取统计信息失败: {e}')


class MultiIonComparisonDialog(QDialog):
    """多离子对比对话框"""
    
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        
        self.setWindowTitle('多离子对比')
        self.setGeometry(100, 100, 1200, 900)
        
        self.data = data
        self.selected_mzs = []
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 选择区域
        select_group = QGroupBox('选择离子（2-4个）')
        select_layout = QHBoxLayout()
        
        self.mz_list = QListWidget()
        self.mz_list.setSelectionMode(QListWidget.MultiSelection)
        
        if self.data:
            mz_bins = self.data['mz_bins']
            mean_intensity = np.mean(self.data['intensity_matrix'], axis=0)
            sorted_indices = np.argsort(mean_intensity)[::-1]
            
            # 显示前50个高强度离子
            for i in range(min(50, len(sorted_indices))):
                idx = sorted_indices[i]
                item = QListWidgetItem(f"m/z {mz_bins[idx]:.4f} (强度: {mean_intensity[idx]:.1f})")
                item.setData(Qt.UserRole, mz_bins[idx])
                self.mz_list.addItem(item)
        
        select_layout.addWidget(self.mz_list)
        
        select_group.setLayout(select_layout)
        layout.addWidget(select_group)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        compare_btn = QPushButton('对比选中的离子')
        compare_btn.clicked.connect(self.compare_ions)
        btn_layout.addWidget(compare_btn)
        
        close_btn = QPushButton('关闭')
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        # 图形区域
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
    
    def compare_ions(self):
        """对比离子"""
        selected_items = self.mz_list.selectedItems()
        
        if len(selected_items) < 2:
            QMessageBox.warning(self, '警告', '请至少选择2个离子')
            return
        
        if len(selected_items) > 4:
            QMessageBox.warning(self, '警告', '最多选择4个离子')
            return
        
        # 获取选中的m/z值
        selected_mzs = [item.data(Qt.UserRole) for item in selected_items]
        
        # 绘制对比图
        self.figure.clear()
        
        n_ions = len(selected_mzs)
        rows = 2 if n_ions > 2 else 1
        cols = 2 if n_ions > 1 else 1
        
        coords = self.data['coords']
        x_unique = np.unique(coords[:, 0])
        y_unique = np.unique(coords[:, 1])
        
        for i, mz in enumerate(selected_mzs):
            ax = self.figure.add_subplot(rows, cols, i+1)
            
            # 找到最接近的m/z
            mz_bins = self.data['mz_bins']
            mz_index = np.argmin(np.abs(mz_bins - mz))
            actual_mz = mz_bins[mz_index]
            
            intensities = self.data['intensity_matrix'][:, mz_index]
            
            # 创建网格
            grid = np.zeros((len(y_unique), len(x_unique)))
            
            for j, (x, y) in enumerate(coords):
                xi = np.where(x_unique == x)[0][0]
                yi = np.where(y_unique == y)[0][0]
                grid[yi, xi] = intensities[j]
            
            # 显示
            im = ax.imshow(
                grid, cmap='hot', aspect='auto',
                extent=[x_unique.min(), x_unique.max(), 
                       y_unique.min(), y_unique.max()],
                origin='lower'
            )
            
            ax.set_xlabel('X (mm)')
            ax.set_ylabel('Y (mm)')
            ax.set_title(f'm/z {actual_mz:.4f}')
            
            self.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        
        self.figure.tight_layout()
        self.canvas.draw()


class IonTable(QTableWidget):
    """离子信息表"""
    
    ion_selected = pyqtSignal(float)  # m/z值
    
    def __init__(self):
        super().__init__()
        
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(['m/z', '平均强度', '最大强度', 'CV(%)'])
        
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        
        self.itemDoubleClicked.connect(self.on_double_click)
        
        # 右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        self.current_data = None
    
    def on_double_click(self, item):
        """双击事件"""
        row = item.row()
        mz = float(self.item(row, 0).text())
        self.ion_selected.emit(mz)
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu()
        
        search_action = QAction('代谢物查询', self)
        search_action.triggered.connect(self.search_metabolite)
        menu.addAction(search_action)
        
        export_action = QAction('导出数据', self)
        export_action.triggered.connect(self.export_data)
        menu.addAction(export_action)
        
        menu.exec_(self.mapToGlobal(position))
    
    def search_metabolite(self):
        """代谢物查询"""
        current_row = self.currentRow()
        if current_row >= 0:
            mz = float(self.item(current_row, 0).text())
            dialog = MetaboliteSearchDialog(self)
            dialog.set_mz(mz)
            dialog.exec_()
    
    def export_data(self):
        """导出所有离子数据（优化版本，支持数量限制和进度显示）"""
        print(f"\n[SEARCH] 调试导出: hasattr(self, 'all_ion_stats') = {hasattr(self, 'all_ion_stats')}")

        if hasattr(self, 'all_ion_stats'):
            print(f"   all_ion_stats内容: {list(self.all_ion_stats.keys()) if self.all_ion_stats else 'None'}")
            if self.all_ion_stats and 'sorted_indices' in self.all_ion_stats:
                print(f"   sorted_indices长度: {len(self.all_ion_stats['sorted_indices'])}")
            else:
                print("all_ion_stats结构不完整")
        else:
            print("[错误] all_ion_stats不存在！")

        # 创建导出选项对话框
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QRadioButton, QButtonGroup
        
        dialog = QDialog(self)
        dialog.setWindowTitle('导出选项')
        dialog.setMinimumWidth(400)
        layout = QVBoxLayout(dialog)
        
        # 导出数量选择
        layout.addWidget(QLabel('<b>1. 导出数量：</b>'))
        
        count_group = QButtonGroup(dialog)
        
        export_all_radio = QRadioButton('导出全部离子')
        count_group.addButton(export_all_radio, 1)
        layout.addWidget(export_all_radio)
        
        export_top_radio = QRadioButton('导出Top N高强度离子：')
        count_group.addButton(export_top_radio, 2)
        export_top_radio.setChecked(True)
        
        top_n_layout = QHBoxLayout()
        top_n_layout.addWidget(export_top_radio)
        top_n_spinbox = QSpinBox()
        top_n_spinbox.setRange(10, 10000)
        top_n_spinbox.setValue(500)
        top_n_spinbox.setSuffix(' 个')
        top_n_layout.addWidget(top_n_spinbox)
        top_n_layout.addStretch()
        layout.addLayout(top_n_layout)
        
        # 估算时间提示
        if hasattr(self, 'all_ion_stats'):
            total = len(self.all_ion_stats['sorted_indices'])
            time_estimate_label = QLabel(
                f'<font color="#666">提示: 全部导出约{total}个离子，'
                f'Top 500约节省{int((1-500/total)*100)}%时间</font>'
            )
            layout.addWidget(time_estimate_label)
        
        layout.addSpacing(10)
        
        # 导出格式选择
        layout.addWidget(QLabel('<b>2. 导出格式：</b>'))
        
        format_group = QButtonGroup(dialog)
        
        format_stats_radio = QRadioButton('统计信息（m/z、平均强度、最大强度、CV%等）')
        format_group.addButton(format_stats_radio, 1)
        format_stats_radio.setChecked(True)
        layout.addWidget(format_stats_radio)
        
        format_spatial_radio = QRadioButton('二维空间信息（每个离子在所有扫描点的强度分布）')
        format_group.addButton(format_spatial_radio, 2)
        layout.addWidget(format_spatial_radio)
        
        layout.addSpacing(10)

        # 代谢物注释选择（仅在统计信息格式时显示）
        annot_label = QLabel('<b>3. 代谢物注释：</b>')
        layout.addWidget(annot_label)

        annot_group = QButtonGroup(dialog)

        annot_yes_radio = QRadioButton('包含代谢物注释（需要额外时间）')
        annot_group.addButton(annot_yes_radio, 1)
        annot_yes_radio.setChecked(True)
        layout.addWidget(annot_yes_radio)

        annot_no_radio = QRadioButton('不包含注释（仅m/z和强度，速度快）')
        annot_group.addButton(annot_no_radio, 2)
        layout.addWidget(annot_no_radio)

        # 动态显示/隐藏代谢物注释选项
        def update_annotation_visibility():
            is_stats_format = format_stats_radio.isChecked()
            annot_label.setVisible(is_stats_format)
            annot_yes_radio.setVisible(is_stats_format)
            annot_no_radio.setVisible(is_stats_format)

        # 连接信号
        format_stats_radio.toggled.connect(update_annotation_visibility)
        format_spatial_radio.toggled.connect(update_annotation_visibility)

        # 初始状态
        update_annotation_visibility()
        
        layout.addSpacing(10)
        
        # 按钮
        from PyQt5.QtWidgets import QDialogButtonBox
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # 显示对话框
        if dialog.exec_() != QDialog.Accepted:
            return
        
        # 获取用户选择
        export_all = export_all_radio.isChecked()
        max_export = None if export_all else top_n_spinbox.value()
        export_format = 'stats' if format_stats_radio.isChecked() else 'spatial'
        # 只有在统计信息格式时才考虑代谢物注释
        include_annotation = export_format == 'stats' and annot_yes_radio.isChecked()
        
        # 选择导出文件
        filename, _ = QFileDialog.getSaveFileName(
            self, '导出离子数据', '', 
            'Excel文件 (*.xlsx);;CSV文件 (*.csv)'
        )
        
        if filename:
            try:
                import pandas as pd
                from online_metabolite_annotator import OnlineMetaboliteAnnotator
                import time
                
                # 创建多阶段进度对话框
                from PyQt5.QtWidgets import QProgressDialog
                overall_progress = QProgressDialog("准备导出数据...", None, 0, 100, self)
                overall_progress.setWindowTitle('导出进度')
                overall_progress.setWindowModality(Qt.WindowModal)
                overall_progress.setMinimumDuration(0)
                overall_progress.setValue(0)
                QApplication.processEvents()
                
                start_time = time.time()
                
                # 根据导出格式选择不同的导出方式
                if export_format == 'spatial':
                    # 导出二维空间信息
                    self._export_spatial_data(filename, max_export, overall_progress)
                    overall_progress.close()
                    
                    elapsed = time.time() - start_time
                    QMessageBox.information(
                        self, '导出成功', 
                        f'[成功] 二维空间信息已导出！\n\n'
                        f'文件: {filename}\n'
                        f'耗时: {elapsed:.1f} 秒'
                    )
                    return
                
                # 使用保存的完整统计数据，而不是表格中显示的
                if hasattr(self, 'all_ion_stats'):
                    stats = self.all_ion_stats
                    sorted_indices = stats['sorted_indices']
                    
                    # 应用数量限制
                    if max_export and max_export < len(sorted_indices):
                        sorted_indices = sorted_indices[:max_export]
                        print(f"[统计] 限制导出数量: Top {max_export} (原始: {len(stats['sorted_indices'])})")
                    
                    total_ions = len(sorted_indices)
                    
                    # 阶段1: 收集数据 (0-10%)
                    overall_progress.setLabelText(f'阶段 1/3: 收集离子数据 ({total_ions}个)...')
                    overall_progress.setValue(5)
                    QApplication.processEvents()
                    
                    # 判断离子模式（根据样本名称或让用户选择）
                    ion_mode = self._detect_ion_mode()
                    
                    data = []
                    mz_list = []
                    
                    # 收集m/z值
                    for idx in sorted_indices:
                        mz = float(f"{stats['mz_bins'][idx]:.4f}")
                        mz_list.append(mz)
                        data.append({
                            'm/z': f"{stats['mz_bins'][idx]:.4f}",
                            '平均强度': f"{stats['mean_intensity'][idx]:.1f}",
                            '最大强度': f"{stats['max_intensity'][idx]:.1f}",
                            'CV(%)': f"{stats['cv'][idx]:.2f}"
                        })
                    
                    overall_progress.setValue(10)
                    QApplication.processEvents()
                    
                    # 阶段2: 代谢物注释 (10-80%)
                    if include_annotation:
                        overall_progress.setLabelText(f'阶段 2/3: 代谢物注释 ({total_ions}个离子)...')
                        overall_progress.setValue(10)
                        QApplication.processEvents()
                        
                        print(f"\n[SEARCH] 开始代谢物注释 ({total_ions} 个离子)...")
                        
                        try:
                            # 批量注释
                            annotator = OnlineMetaboliteAnnotator()
                            
                            def update_progress(current, total):
                                # 注释阶段占10-80%的进度
                                progress_percent = 10 + int((current / total) * 70)
                                overall_progress.setValue(progress_percent)
                                overall_progress.setLabelText(
                                    f'阶段 2/3: 代谢物注释\n'
                                    f'进度: {current}/{total} ({current/total*100:.1f}%)\n'
                                    f'预计剩余时间: {int((total-current) * 0.02)}秒'
                                )
                                QApplication.processEvents()
                            
                            annotations = annotator.batch_annotate(
                                mz_list, 
                                tolerance_ppm=10, 
                                ion_mode=ion_mode,
                                progress_callback=update_progress
                            )
                            
                            # 添加注释信息到数据
                            for i, (idx, row_data) in enumerate(zip(sorted_indices, data)):
                                mz = mz_list[i]
                                matches = annotations.get(mz, [])
                                
                                if matches:
                                    best_match = annotator.get_best_match(matches, max_error_ppm=5)
                                    if best_match:
                                        row_data['代谢物名称'] = best_match['name']
                                        row_data['分子式'] = best_match['formula']
                                        row_data['HMDB ID'] = best_match.get('hmdb_id', '')
                                        row_data['分子量'] = f"{best_match.get('molecular_weight', ''):.4f}" if best_match.get('molecular_weight') else ''
                                        row_data['CAS号'] = best_match.get('cas_number', '')
                                        row_data['KEGG ID'] = best_match.get('kegg_id', '')
                                        row_data['分类-界'] = best_match.get('kingdom', '')
                                        row_data['分类-超类'] = best_match.get('super_class', '')
                                        row_data['分类-类'] = best_match.get('class', '')
                                        row_data['分类-亚类'] = best_match.get('sub_class', '')
                                        row_data['理论m/z'] = f"{best_match['theoretical_mz']:.4f}"
                                        row_data['误差(ppm)'] = f"{best_match['error_ppm']:.2f}"
                                        row_data['数据源'] = best_match['source']
                                    else:
                                        # 误差过大，列出可能的匹配
                                        row_data['代谢物名称'] = annotator.format_annotation(matches)
                                        row_data['分子式'] = ''
                                        row_data['HMDB ID'] = ''
                                        row_data['分子量'] = ''
                                        row_data['CAS号'] = ''
                                        row_data['KEGG ID'] = ''
                                        row_data['分类-界'] = ''
                                        row_data['分类-超类'] = ''
                                        row_data['分类-类'] = ''
                                        row_data['分类-亚类'] = ''
                                        row_data['理论m/z'] = ''
                                        row_data['误差(ppm)'] = ''
                                        row_data['数据源'] = '低置信度'
                                else:
                                    row_data['代谢物名称'] = '未匹配'
                                    row_data['分子式'] = ''
                                    row_data['HMDB ID'] = ''
                                    row_data['分子量'] = ''
                                    row_data['CAS号'] = ''
                                    row_data['KEGG ID'] = ''
                                    row_data['分类-界'] = ''
                                    row_data['分类-超类'] = ''
                                    row_data['分类-类'] = ''
                                    row_data['分类-亚类'] = ''
                                    row_data['理论m/z'] = ''
                                    row_data['误差(ppm)'] = ''
                                    row_data['数据源'] = ''
                            
                            print(f"[成功] 代谢物注释完成")
                            
                            # 打印注释统计信息
                            annotator.print_stats()
                            
                            overall_progress.setValue(80)
                        
                        except Exception as e:
                            print(f"[错误] 代谢物注释失败: {e}")
                            import traceback
                            traceback.print_exc()
                            overall_progress.setValue(80)
                    else:
                        # 跳过注释，直接到80%
                        overall_progress.setValue(80)
                    
                    # 阶段3: 写入Excel (80-100%)
                    overall_progress.setLabelText(f'阶段 3/3: 写入Excel文件...')
                    overall_progress.setValue(85)
                    QApplication.processEvents()
                    
                    df = pd.DataFrame(data)
                else:
                    # 回退到只导出表格显示的数据
                    overall_progress.setValue(10)
                    data = []
                    for row in range(self.rowCount()):
                        data.append({
                            'm/z': self.item(row, 0).text(),
                            '平均强度': self.item(row, 1).text(),
                            '最大强度': self.item(row, 2).text(),
                            'CV(%)': self.item(row, 3).text()
                        })
                    df = pd.DataFrame(data)
                    total_ions = len(data)
                    overall_progress.setValue(85)
                
                # 写入文件
                overall_progress.setLabelText(f'写入文件中... ({total_ions} 行数据)')
                overall_progress.setValue(90)
                QApplication.processEvents()
                
                if filename.endswith('.xlsx'):
                    # 使用xlsxwriter引擎（更快）
                    try:
                        df.to_excel(filename, index=False, engine='xlsxwriter')
                    except:
                        # 如果xlsxwriter不可用，回退到openpyxl
                        df.to_excel(filename, index=False, engine='openpyxl')
                else:
                    df.to_csv(filename, index=False, encoding='utf-8-sig')
                
                overall_progress.setValue(95)
                QApplication.processEvents()
                
                # 计算总耗时
                elapsed_time = time.time() - start_time
                
                overall_progress.setLabelText('导出完成！')
                overall_progress.setValue(100)
                QApplication.processEvents()
                
                # 关闭进度对话框
                overall_progress.close()
                
                # 显示完成信息
                msg = f'[成功] 导出完成！\n\n'
                msg += f'导出离子数: {total_ions} 个\n'
                if max_export:
                    msg += f'(限制为Top {max_export}高强度离子)\n'
                msg += f'文件路径: {filename}\n'
                msg += f'耗时: {elapsed_time:.1f}秒\n'
                if include_annotation:
                    msg += '\n[成功] 已包含代谢物注释信息'
                else:
                    msg += '\n[统计] 仅包含m/z和强度信息'
                
                QMessageBox.information(self, '导出成功', msg)
                print(f"\n[成功] 导出完成:")
                print(f"   离子数: {total_ions}")
                print(f"   文件: {filename}")
                print(f"   耗时: {elapsed_time:.1f}秒")
                print(f"   包含注释: {'是' if include_annotation else '否'}")
                
                # 记录使用量
                try:
                    from usage_tracker import record_data_export
                    sample_name = self.current_data.get('sample_name', 'unknown') if hasattr(self, 'current_data') and self.current_data else 'unknown'
                    record_data_export(sample_name, export_format, total_ions)
                except:
                    pass
                
            except Exception as e:
                # 确保关闭进度对话框
                if 'overall_progress' in locals():
                    overall_progress.close()
                
                import traceback
                print(f"[错误] 导出错误:\n{traceback.format_exc()}")
                QMessageBox.warning(self, '错误', f'导出失败: {e}')
    
    def _export_spatial_data(self, filename, max_export, progress):
        """
        导出二维空间信息（每个离子在所有扫描点的强度分布）
        
        参数:
            filename: 导出文件路径
            max_export: 最大导出离子数（None表示全部）
            progress: 进度对话框
        """
        try:
            import pandas as pd
            import time
            
            if not self.current_data:
                QMessageBox.warning(self, '警告', '没有可导出的数据')
                return
            
            # 获取数据
            coords = self.current_data.get('coords')
            intensity_matrix = self.current_data.get('intensity_matrix')
            mz_bins = self.current_data.get('mz_bins')
            
            if coords is None or intensity_matrix is None or mz_bins is None:
                QMessageBox.warning(self, '警告', '数据不完整')
                return
            
            n_scans = len(coords)
            n_mz = len(mz_bins)
            
            # 阶段1: 选择要导出的离子 (0-10%)
            progress.setLabelText(f'阶段 1/4: 选择离子 ({n_mz}个 m/z bins)...')
            progress.setValue(5)
            QApplication.processEvents()
            
            # 获取Top N高强度离子的索引
            if hasattr(self, 'all_ion_stats'):
                sorted_indices = self.all_ion_stats['sorted_indices']
                
                # 应用数量限制
                if max_export and max_export < len(sorted_indices):
                    sorted_indices = sorted_indices[:max_export]
                    print(f"[统计] 限制导出离子数: Top {max_export} (原始: {len(self.all_ion_stats['sorted_indices'])})")
            else:
                # 如果没有统计信息，按总强度排序
                total_intensity = intensity_matrix.sum(axis=0)
                sorted_indices = total_intensity.argsort()[::-1]
                if max_export and max_export < len(sorted_indices):
                    sorted_indices = sorted_indices[:max_export]
            
            selected_mz_bins = mz_bins[sorted_indices]
            selected_intensity = intensity_matrix[:, sorted_indices]
            
            total_ions = len(selected_mz_bins)
            total_points = n_scans * total_ions
            
            progress.setValue(10)
            QApplication.processEvents()
            
            # 阶段2: 准备导出数据 (10-30%)
            progress.setLabelText(f'阶段 2/4: 准备数据 ({n_scans} 扫描 × {total_ions} 离子 = {total_points:,} 数据点)...')
            progress.setValue(15)
            QApplication.processEvents()
            
            # 创建基础数据列
            export_data = {
                'Scan_Index': list(range(n_scans)),
                'X_mm': coords[:, 0].tolist(),
                'Y_mm': coords[:, 1].tolist()
            }
            
            progress.setValue(20)
            QApplication.processEvents()
            
            # 阶段3: 添加离子强度数据 (30-70%) - 向量化操作
            progress.setLabelText(f'阶段 3/4: 添加离子强度数据 ({total_ions}个离子)...')
            
            for i, (idx, mz) in enumerate(zip(range(total_ions), selected_mz_bins)):
                export_data[f'mz_{mz:.4f}'] = selected_intensity[:, idx].tolist()
                
                # 每10%更新一次进度
                if i % max(1, total_ions // 10) == 0:
                    pct = 30 + int(40 * (i / total_ions))
                    progress.setValue(pct)
                    progress.setLabelText(
                        f'阶段 3/4: 添加离子强度数据\n'
                        f'进度: {i}/{total_ions} ({i/total_ions*100:.1f}%)'
                    )
                    QApplication.processEvents()
            
            progress.setValue(70)
            QApplication.processEvents()
            
            # 阶段4: 创建DataFrame并写入文件 (70-100%)
            progress.setLabelText(f'阶段 4/4: 创建数据表...')
            progress.setValue(75)
            QApplication.processEvents()
            
            df = pd.DataFrame(export_data)
            
            progress.setLabelText(f'阶段 4/4: 写入Excel文件 ({len(df)} 行 × {len(df.columns)} 列)...')
            progress.setValue(85)
            QApplication.processEvents()
            
            # 写入Excel文件
            if filename.endswith('.xlsx'):
                # 尝试使用xlsxwriter引擎（更快）
                try:
                    with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                        df.to_excel(writer, sheet_name='Ion_Spatial_Data', index=False)
                        
                        # 添加数据信息sheet
                        info_data = {
                            '参数': ['扫描点数', 'm/z bins数', '总数据点数', '导出时间'],
                            '值': [
                                n_scans,
                                total_ions,
                                total_points,
                                time.strftime('%Y-%m-%d %H:%M:%S')
                            ]
                        }
                        info_df = pd.DataFrame(info_data)
                        info_df.to_excel(writer, sheet_name='Data_Info', index=False)
                except ImportError:
                    # 如果xlsxwriter不可用，回退到openpyxl
                    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name='Ion_Spatial_Data', index=False)
                        
                        info_data = {
                            '参数': ['扫描点数', 'm/z bins数', '总数据点数', '导出时间'],
                            '值': [
                                n_scans,
                                total_ions,
                                total_points,
                                time.strftime('%Y-%m-%d %H:%M:%S')
                            ]
                        }
                        info_df = pd.DataFrame(info_data)
                        info_df.to_excel(writer, sheet_name='Data_Info', index=False)
            else:
                # CSV格式
                df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            progress.setValue(100)
            QApplication.processEvents()
            
            print(f"\n[成功] 二维空间信息导出完成")
            print(f"   文件: {filename}")
            print(f"   扫描点数: {n_scans}")
            print(f"   离子数: {total_ions}")
            print(f"   总数据点: {total_points:,}")
            
        except Exception as e:
            print(f"[错误] 二维空间信息导出失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _detect_ion_mode(self):
        """检测离子模式（从样本名称）"""
        if hasattr(self, 'current_data') and self.current_data:
            sample_name = self.current_data.get('sample_name', '').upper()
            if 'NEG' in sample_name or 'NEGATIVE' in sample_name:
                return 'negative'
            elif 'POS' in sample_name or 'POSITIVE' in sample_name:
                return 'positive'
        
        # 默认或询问用户
        reply = QMessageBox.question(
            self, '离子模式',
            '请选择离子模式：\n\n'
            '• Yes = 正离子模式 [M+H]+\n'
            '• No = 负离子模式 [M-H]-',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        return 'positive' if reply == QMessageBox.Yes else 'negative'
    
    def update_table(self, data):
        """更新表格"""
        self.current_data = data
        
        mz_bins = data['mz_bins']
        intensity_matrix = data['intensity_matrix']
        
        # 计算统计信息（所有离子）
        mean_intensity = np.mean(intensity_matrix, axis=0)
        max_intensity = np.max(intensity_matrix, axis=0)
        std_intensity = np.std(intensity_matrix, axis=0)
        cv = np.zeros_like(mean_intensity)
        mask = mean_intensity > 0
        cv[mask] = (std_intensity[mask] / mean_intensity[mask] * 100)
        
        # 按平均强度排序
        sorted_indices = np.argsort(mean_intensity)[::-1]
        
        # 保存所有离子的完整统计数据（用于导出）
        self.all_ion_stats = {
            'mz_bins': mz_bins,
            'mean_intensity': mean_intensity,
            'max_intensity': max_intensity,
            'cv': cv,
            'sorted_indices': sorted_indices
        }
        
        # 只显示前100个高强度离子（节省界面空间）
        top_n = min(100, len(sorted_indices))
        
        self.setRowCount(top_n)
        
        for i in range(top_n):
            idx = sorted_indices[i]
            
            self.setItem(i, 0, QTableWidgetItem(f"{mz_bins[idx]:.4f}"))
            self.setItem(i, 1, QTableWidgetItem(f"{mean_intensity[idx]:.1f}"))
            self.setItem(i, 2, QTableWidgetItem(f"{max_intensity[idx]:.1f}"))
            self.setItem(i, 3, QTableWidgetItem(f"{cv[idx]:.2f}"))


class ImagingCanvas(FigureCanvas):
    """成像图画布 - 支持ROI交互"""
    
    def __init__(self):
        self.fig = Figure(figsize=(8, 6))
        super().__init__(self.fig)
        
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel('X (mm)')
        self.ax.set_ylabel('Y (mm)')
        
        self.current_data = None
        self.current_mz_index = 0
        self.colormap = 'hot'
        
        self.roi_patches = []
        self.roi_mode = None  # 'rectangle' or 'polygon'
        self.roi_start = None
        self.roi_points = []
        self.temp_patch = None
        self.roi_callback = None
        
        # 连接鼠标事件
        self.mpl_connect('button_press_event', self.on_mouse_press)
        self.mpl_connect('button_release_event', self.on_mouse_release)
        self.mpl_connect('motion_notify_event', self.on_mouse_move)
    
    def start_roi_selection(self, roi_type, callback):
        """开始ROI选择"""
        self.roi_mode = roi_type
        self.roi_callback = callback
        self.roi_start = None
        self.roi_points = []
        
        if roi_type == 'rectangle':
            print("[MOUSE]  矩形ROI模式：按住鼠标左键拖拽选择区域")
        elif roi_type == 'polygon':
            print("[MOUSE]  多边形ROI模式：左键点击添加顶点，右键或双击完成")
    
    def stop_roi_selection(self):
        """停止ROI选择"""
        self.roi_mode = None
        self.roi_start = None
        self.roi_points = []
        if self.temp_patch:
            self.temp_patch.remove()
            self.temp_patch = None
            self.draw()
    
    def on_mouse_press(self, event):
        """鼠标按下"""
        if not self.roi_mode or event.inaxes != self.ax:
            return
        
        if self.roi_mode == 'rectangle':
            self.roi_start = (event.xdata, event.ydata)
        
        elif self.roi_mode == 'polygon':
            if event.button == 1:  # 左键
                self.roi_points.append([event.xdata, event.ydata])
                self.ax.plot(event.xdata, event.ydata, 'yo', markersize=8)
                
                if len(self.roi_points) > 1:
                    points = np.array(self.roi_points)
                    self.ax.plot(points[:, 0], points[:, 1], 'y--', linewidth=2)
                
                self.draw()
            
            elif event.button == 3:  # 右键完成
                self.finish_polygon_roi()
    
    def on_mouse_release(self, event):
        """鼠标释放"""
        if not self.roi_mode or event.inaxes != self.ax:
            return
        
        if self.roi_mode == 'rectangle' and self.roi_start:
            # [TARGET] 像素坐标系统：event.xdata是像素坐标
            x1, y1 = self.roi_start
            x2, y2 = event.xdata, event.ydata
            
            roi = ROI(
                name=f"矩形ROI_{len(self.roi_patches)+1}",
                roi_type='rectangle',
                coords=[x1, y1, x2, y2]
            )
            
            # 打印ROI坐标（像素）
            print(f"\n[编辑]  创建ROI: {roi.name}")
            print(f"   像素坐标: X[{min(x1,x2):.1f}, {max(x1,x2):.1f}] Y[{min(y1,y2):.1f}, {max(y1,y2):.1f}]")
            print(f"   大小: {abs(x2-x1):.1f} × {abs(y2-y1):.1f} 像素")
            
            if self.roi_callback:
                self.roi_callback(roi)
            
            self.add_roi_patch(roi)
            self.stop_roi_selection()
    
    def on_mouse_move(self, event):
        """鼠标移动"""
        if not self.roi_mode or event.inaxes != self.ax:
            return
        
        if self.roi_mode == 'rectangle' and self.roi_start:
            # 绘制临时矩形
            if self.temp_patch:
                self.temp_patch.remove()
            
            x1, y1 = self.roi_start
            x2, y2 = event.xdata, event.ydata
            
            self.temp_patch = Rectangle(
                (min(x1, x2), min(y1, y2)),
                abs(x2 - x1), abs(y2 - y1),
                fill=False, edgecolor='yellow', linewidth=2, linestyle='--'
            )
            self.ax.add_patch(self.temp_patch)
            self.draw()
    
    def finish_polygon_roi(self):
        """完成多边形ROI"""
        if len(self.roi_points) >= 3:
            roi = ROI(
                name=f"多边形ROI_{len(self.roi_patches)+1}",
                roi_type='polygon',
                coords=self.roi_points
            )
            
            if self.roi_callback:
                self.roi_callback(roi)
            
            self.add_roi_patch(roi)
        
        self.stop_roi_selection()
    
    def update_display(self, data, mz_target=None):
        """更新显示"""
        self.current_data = data
        
        if mz_target is not None:
            # 找到最接近的m/z
            mz_bins = data['mz_bins']
            self.current_mz_index = np.argmin(np.abs(mz_bins - mz_target))
        
        mz = data['mz_bins'][self.current_mz_index]
        intensities = data['intensity_matrix'][:, self.current_mz_index]
        coords = data['coords']
        
        # 创建网格
        x_unique = np.unique(coords[:, 0])
        y_unique = np.unique(coords[:, 1])
        
        grid = np.zeros((len(y_unique), len(x_unique)))
        
        for i, (x, y) in enumerate(coords):
            xi = np.where(x_unique == x)[0][0]
            yi = np.where(y_unique == y)[0][0]
            grid[yi, xi] = intensities[i]
        
        # 绘制
        self.ax.clear()
        
        # [TARGET] 最终方案：全部使用像素坐标
        # 原因：
        # 1. extent在PyQt5中有渲染bug
        # 2. scatter数据太稀疏，看起来不连续
        # 3. 像素坐标简单可靠，imshow工作完美
        # 4. 物理坐标信息在ROI分析结果中显示
        
        im = self.ax.imshow(
            grid, cmap=self.colormap, aspect='auto',
            origin='lower',
            interpolation='nearest'
        )
        
        # 保存坐标映射信息（用于像素↔物理转换）
        self.x_unique = x_unique
        self.y_unique = y_unique
        self.coords = coords  # 保存原始物理坐标
        
        print(f"\n[TARGET] 像素坐标系统:")
        print(f"   图像尺寸: {grid.shape[1]} × {grid.shape[0]} 像素")
        print(f"   对应物理范围: X[{x_unique.min():.1f}, {x_unique.max():.1f}] Y[{y_unique.min():.1f}, {y_unique.max():.1f}] mm")
        print(f"   [成功] 使用像素坐标，简单可靠，ROI结果会显示物理坐标")
        
        self.ax.set_xlabel('X (pixels)')
        self.ax.set_ylabel('Y (pixels)')
        self.ax.set_title(f'm/z {mz:.4f}')
        
        # 重新绘制ROI
        for patch in self.roi_patches:
            self.ax.add_patch(patch)
        
        # [HOT] 终极方案：第一次创建colorbar，后续只更新
        if not hasattr(self, 'colorbar') or self.colorbar is None:
            # 第一次：创建colorbar
            self.colorbar = self.fig.colorbar(im, ax=self.ax, label='Intensity')
            # 固定布局
            self.fig.subplots_adjust(left=0.1, right=0.85, top=0.95, bottom=0.1)
            print("首次创建colorbar")
        else:
            # 后续：只更新colorbar，不重新创建
            self.colorbar.update_normal(im)
            print("更新colorbar（不重新创建）")
        
        self.draw()
    
    def add_roi_patch(self, roi):
        """添加ROI显示"""
        patch = roi.get_patch()
        if patch:
            self.roi_patches.append(patch)
            self.ax.add_patch(patch)
            self.draw()
    
    def clear_roi_patches(self):
        """清除所有ROI"""
        for patch in self.roi_patches:
            try:
                patch.remove()
            except Exception:
                pass  # 忽略已经移除的patch
        self.roi_patches = []
        if self.current_data:
            self.update_display(self.current_data)


class SpectrumCanvas(FigureCanvas):
    """光谱图画布"""
    
    peak_clicked = pyqtSignal(float)
    
    def __init__(self):
        self.fig = Figure(figsize=(8, 4))
        super().__init__(self.fig)
        
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel('m/z')
        self.ax.set_ylabel('Relative Intensity (%)')
        
        self.current_data = None
        self.show_annotations = True
        
        # 记录默认坐标轴范围
        self.default_xlim = None
        self.default_ylim = None
        self.custom_xlim = None
        self.custom_ylim = None
        
        # 连接点击事件
        self.mpl_connect('button_press_event', self.on_click)
    
    def update_display(self, data):
        """更新显示"""
        self.current_data = data
        
        mz_bins = data['mz_bins']
        intensity_matrix = data['intensity_matrix']
        
        # 改进的平均谱计算：只使用高强度扫描（排除背景区域）
        # 计算每个扫描的TIC (Total Ion Current)
        tic = np.sum(intensity_matrix, axis=1)
        
        # 选择TIC > 中位数的扫描（即有信号的区域）
        tic_median = np.median(tic)
        high_intensity_mask = tic > tic_median
        high_intensity_scans = intensity_matrix[high_intensity_mask, :]
        
        if high_intensity_scans.shape[0] > 0:
            # 计算高强度扫描的平均
            avg_spectrum = np.mean(high_intensity_scans, axis=0)
            print(f"[统计] 平均质谱：使用 {high_intensity_scans.shape[0]}/{intensity_matrix.shape[0]} 个高强度扫描")
        else:
            # 后备方案：使用所有扫描
            avg_spectrum = np.mean(intensity_matrix, axis=0)
            print(f"[统计] 平均质谱：使用所有 {intensity_matrix.shape[0]} 个扫描")
        
        # 不归一化，使用绝对强度值（类似专业软件）
        max_intensity = avg_spectrum.max()
        print(f"   最大强度: {max_intensity:.2f}")
        
        # 绘制质谱图 - 使用柱状图（vlines）而不是连续线条
        self.ax.clear()
        
        # 过滤掉m/z < 50的区域
        mask = mz_bins >= 50
        mz_filtered = mz_bins[mask]
        spectrum_filtered = avg_spectrum[mask]
        
        # 使用vlines绘制柱状图，类似专业软件
        self.ax.vlines(mz_filtered, 0, spectrum_filtered, colors='black', linewidth=0.5)
        
        # 找到峰并标注
        if self.show_annotations:
            self.annotate_peaks(mz_bins, avg_spectrum)
        
        self.ax.set_xlabel('M/z', fontsize=10)
        self.ax.set_ylabel('Intensity', fontsize=10)
        self.ax.set_title(f'Average Mass Spectrum - {data["sample_name"]}')
        
        # 设置默认坐标轴范围
        self.default_xlim = (mz_filtered.min(), mz_filtered.max())
        if max_intensity > 0:
            self.default_ylim = (0, max_intensity * 1.1)
        else:
            self.default_ylim = (0, 1)
        
        # 应用坐标轴范围（自定义或默认）
        if self.custom_xlim:
            self.ax.set_xlim(self.custom_xlim)
        else:
            self.ax.set_xlim(self.default_xlim)
        
        if self.custom_ylim:
            self.ax.set_ylim(self.custom_ylim)
        else:
            self.ax.set_ylim(self.default_ylim)
        
        # 使用科学计数法显示y轴（如果强度值很大）
        self.ax.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))
        
        self.ax.grid(True, alpha=0.3)
        
        self.fig.tight_layout()
        self.draw()
    
    def set_axis_range(self, xlim=None, ylim=None):
        """设置坐标轴范围"""
        if xlim:
            self.custom_xlim = xlim
            self.ax.set_xlim(xlim)
        if ylim:
            self.custom_ylim = ylim
            self.ax.set_ylim(ylim)
        self.draw()
    
    def reset_axis_range(self):
        """重置坐标轴范围到默认值"""
        self.custom_xlim = None
        self.custom_ylim = None
        if self.default_xlim:
            self.ax.set_xlim(self.default_xlim)
        if self.default_ylim:
            self.ax.set_ylim(self.default_ylim)
        self.draw()
    
    def annotate_peaks(self, mz_bins, spectrum, n_peaks=10):
        """标注峰"""
        # 检测峰
        peaks = []
        for i in range(1, len(spectrum) - 1):
            if (spectrum[i] > spectrum[i-1] and 
                spectrum[i] > spectrum[i+1] and 
                spectrum[i] > 5):  # 阈值5%
                peaks.append((mz_bins[i], spectrum[i]))
        
        # 按强度排序
        peaks.sort(key=lambda x: x[1], reverse=True)
        
        # 标注前N个峰
        for mz, intensity in peaks[:n_peaks]:
            self.ax.plot(mz, intensity, 'ro', markersize=5)
            self.ax.annotate(
                f'{mz:.1f}',
                xy=(mz, intensity),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=8,
                color='red'
            )
    
    def on_click(self, event):
        """点击事件"""
        if event.inaxes == self.ax and event.xdata:
            mz = event.xdata
            self.peak_clicked.emit(mz)


class ROIDialog(QDialog):
    """ROI管理对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle('ROI分析')
        self.setGeometry(200, 200, 700, 500)
        
        self.roi_analyzer = ROIAnalyzer()
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # ROI列表
        self.roi_list = QListWidget()
        layout.addWidget(QLabel('当前ROI:'))
        layout.addWidget(self.roi_list)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        rect_btn = QPushButton('添加矩形ROI')
        rect_btn.clicked.connect(lambda: self.parent().start_roi_selection('rectangle'))
        btn_layout.addWidget(rect_btn)
        
        poly_btn = QPushButton('添加多边形ROI')
        poly_btn.clicked.connect(lambda: self.parent().start_roi_selection('polygon'))
        btn_layout.addWidget(poly_btn)
        
        clear_btn = QPushButton('清除所有ROI')
        clear_btn.clicked.connect(self.clear_rois)
        btn_layout.addWidget(clear_btn)
        
        layout.addLayout(btn_layout)
        
        # 分析按钮
        analyze_btn = QPushButton('分析ROI')
        analyze_btn.clicked.connect(self.analyze_rois)
        layout.addWidget(analyze_btn)
        
        # 导出按钮
        export_btn = QPushButton('导出ROI数据')
        export_btn.clicked.connect(self.export_roi_data)
        layout.addWidget(export_btn)
        
        # 结果显示
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(QLabel('分析结果:'))
        layout.addWidget(self.result_text)
        
        # 关闭按钮
        close_btn = QPushButton('关闭')
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
    
    def add_roi(self, roi):
        """添加ROI"""
        self.roi_analyzer.add_roi(roi)
        self.roi_list.addItem(roi.name)
    
    def clear_rois(self):
        """清除ROI"""
        self.roi_analyzer.clear_rois()
        self.roi_list.clear()
        self.parent().imaging_canvas.clear_roi_patches()
        self.result_text.clear()
    
    def analyze_rois(self):
        """分析ROI"""
        if not self.parent().current_data:
            QMessageBox.warning(self, '警告', '请先加载样本数据')
            return
        
        if len(self.roi_analyzer.rois) == 0:
            QMessageBox.warning(self, '警告', '请先创建ROI')
            return
        
        # 获取当前m/z索引
        mz_index = self.parent().imaging_canvas.current_mz_index
        mz = self.parent().current_data['mz_bins'][mz_index]
        
        # [配置] 关键：将物理坐标转换成像素坐标进行ROI匹配
        coords_physical = self.parent().current_data['coords']
        x_min, x_max = coords_physical[:, 0].min(), coords_physical[:, 0].max()
        y_min, y_max = coords_physical[:, 1].min(), coords_physical[:, 1].max()
        
        # 获取坐标映射
        if hasattr(self.parent().imaging_canvas, 'x_unique') and hasattr(self.parent().imaging_canvas, 'y_unique'):
            x_unique = self.parent().imaging_canvas.x_unique
            y_unique = self.parent().imaging_canvas.y_unique
            
            # 将每个物理坐标转换成像素索引
            coords_pixels = np.zeros_like(coords_physical)
            for i, (x_phys, y_phys) in enumerate(coords_physical):
                coords_pixels[i, 0] = np.where(x_unique == x_phys)[0][0]
                coords_pixels[i, 1] = np.where(y_unique == y_phys)[0][0]
            
            # 创建临时data用于ROI分析（使用像素坐标）
            data_pixel = self.parent().current_data.copy()
            data_pixel['coords'] = coords_pixels
            
            print(f"\n[SEARCH] ROI分析坐标转换:")
            print(f"   物理坐标范围: X[{x_min:.1f}, {x_max:.1f}] Y[{y_min:.1f}, {y_max:.1f}] mm")
            print(f"   像素坐标范围: X[0, {len(x_unique)-1}] Y[0, {len(y_unique)-1}]")
            
            # 分析（使用像素坐标data）
            results = self.roi_analyzer.compare_rois(data_pixel, mz_index)
        else:
            # 降级：直接使用原始坐标
            results = self.roi_analyzer.compare_rois(self.parent().current_data, mz_index)
        
        # 显示结果
        text = f"m/z {mz:.4f} 的ROI分析结果:\n"
        text += f"数据坐标范围: X[{x_min:.1f}, {x_max:.1f}] Y[{y_min:.1f}, {y_max:.1f}]\n\n"
        
        if not results:
            text += "[警告] 所有ROI都没有数据点！\n\n"
            text += "可能原因：\n"
            text += "1. ROI绘制在数据点稀疏或空白的区域\n"
            text += "2. 请在信号强度高的区域（黄色/红色区域）绘制ROI\n"
            text += "3. 尝试在图像左下角或信号集中区域绘制ROI\n"
        else:
            has_empty_roi = False
            for result in results:
                if result['n_points'] == 0:
                    text += f"[警告] {result['name']}: 无数据点（ROI可能在空白区域）\n\n"
                    has_empty_roi = True
                else:
                    text += f"[成功] {result['name']}:\n"
                    text += f"   点数: {result['n_points']}\n"
                    text += f"   平均强度: {result['mean']:.1f}\n"
                    text += f"   中位数: {result['median']:.1f}\n"
                    text += f"   标准差: {result['std']:.1f}\n"
                    text += f"   最小值: {result['min']:.1f}\n"
                    text += f"   最大值: {result['max']:.1f}\n"
                    text += f"   CV: {result['cv']:.2f}%\n\n"
            
            if has_empty_roi:
                text += "\n[提示] 提示: 有些ROI没有数据点，请在成像图的\n"
                text += "   高信号区域（黄色/橙色/红色区域）绘制ROI\n"
        
        self.result_text.setText(text)
    
    def export_roi_data(self):
        """导出ROI数据"""
        if not self.parent().current_data:
            QMessageBox.warning(self, '警告', '请先加载样本数据')
            return
        
        if len(self.roi_analyzer.rois) == 0:
            QMessageBox.warning(self, '警告', '请先创建ROI')
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, '保存ROI数据', '', 
            'Excel文件 (*.xlsx);;CSV文件 (*.csv)'
        )
        
        if filename:
            try:
                self.roi_analyzer.export_roi_data(
                    self.parent().current_data,
                    self.parent().current_data['mz_bins'],
                    filename
                )
                QMessageBox.information(self, '成功', f'ROI数据已导出到:\n{filename}')
            except Exception as e:
                QMessageBox.warning(self, '错误', f'导出失败: {e}')


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # License验证（商业化计费）
        from license_integration import LicenseIntegration
        from license_validation_dialog import (
            LicenseValidationDialog, LicenseReminderDialog
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
        
        pid = os.getpid()
        self.setWindowTitle(f'DESI空间代谢组学分析系统 V2 (终极完整版) [PID: {pid}]')
        self.setGeometry(50, 50, 1600, 1000)
        
        self.loader = DataLoader()
        self.current_data = None
        self.report_generator = ReportGenerator()
        self.roi_dialog = None
        self.workspace_path = Path('/Volumes/US100 256G/mouse DESI data')  # 默认工作目录
        
        # Lock Mass质量校准管理器
        self.lock_mass_config = LockMassConfig()
        self.lock_mass_manager = MassCalibrationManager(self.lock_mass_config)
        
        # 校准数据管理
        self.original_data = None  # 保存原始数据备份
        self.data_is_calibrated = False  # 当前数据是否已校准
        
        # 数据过滤配置
        from data_filter_config import DataFilterConfig
        from data_filter import DataFilter
        self.data_filter_config = DataFilterConfig()
        self.data_filter = DataFilter(self.data_filter_config)
        
        self.init_ui()
        self.create_menu_bar()
        self.create_toolbar()
        
        print("="*70)
        print("[SPARKLE] DESI终极完整版启动成功")
        print("="*70)
        print("所有功能完全实现:")
        print("[成功] Waters Imaging数据加载")
        print("[成功] 离子信息表（100行）")
        print("[成功] 空间成像图")
        print("[成功] 平均质谱图+峰标注")
        print("[成功] 代谢物查询")
        print("[成功] 多离子对比 [SPARKLE]完整实现[SPARKLE]")
        print("[成功] ROI交互式选择 [SPARKLE]完整实现[SPARKLE]")
        print("[成功] ROI分析和导出 [SPARKLE]完整实现[SPARKLE]")
        print("[成功] PDF/Excel报告生成")
        print("="*70)
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        open_action = QAction('打开工作目录', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_workspace)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        export_image_action = QAction('导出成像图', self)
        export_image_action.setShortcut('Ctrl+E')
        export_image_action.triggered.connect(self.export_image)
        file_menu.addAction(export_image_action)
        
        export_spectrum_action = QAction('导出光谱图', self)
        export_spectrum_action.triggered.connect(self.export_spectrum)
        file_menu.addAction(export_spectrum_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 分析菜单
        analysis_menu = menubar.addMenu('分析')
        
        metabolite_action = QAction('代谢物查询', self)
        metabolite_action.setShortcut('Ctrl+M')
        metabolite_action.triggered.connect(self.show_metabolite_search)
        analysis_menu.addAction(metabolite_action)
        
        comparison_action = QAction('多离子对比', self)
        comparison_action.setShortcut('Ctrl+C')
        comparison_action.triggered.connect(self.show_comparison)
        analysis_menu.addAction(comparison_action)
        
        # ROI菜单
        roi_menu = menubar.addMenu('ROI')
        
        roi_manage_action = QAction('ROI管理', self)
        roi_manage_action.triggered.connect(self.show_roi_dialog)
        roi_menu.addAction(roi_manage_action)
        
        roi_menu.addSeparator()
        
        roi_rect_action = QAction('矩形选择', self)
        roi_rect_action.triggered.connect(lambda: self.start_roi_selection('rectangle'))
        roi_menu.addAction(roi_rect_action)
        
        roi_poly_action = QAction('多边形选择', self)
        roi_poly_action.triggered.connect(lambda: self.start_roi_selection('polygon'))
        roi_menu.addAction(roi_poly_action)
        
        # 报告菜单
        report_menu = menubar.addMenu('报告')
        
        pdf_report_action = QAction('生成PDF报告', self)
        pdf_report_action.setShortcut('Ctrl+P')
        pdf_report_action.triggered.connect(self.generate_pdf_report)
        report_menu.addAction(pdf_report_action)
        
        excel_report_action = QAction('生成Excel报告', self)
        excel_report_action.triggered.connect(self.generate_excel_report)
        report_menu.addAction(excel_report_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        lock_mass_action = QAction('Lock Mass 质量校准设置', self)
        lock_mass_action.setShortcut('Ctrl+L')
        lock_mass_action.triggered.connect(self.show_lock_mass_dialog)
        tools_menu.addAction(lock_mass_action)
        
        data_filter_action = QAction('数据过滤设置（减少处理量）', self)
        data_filter_action.setShortcut('Ctrl+F')
        data_filter_action.triggered.connect(self.show_data_filter_dialog)
        tools_menu.addAction(data_filter_action)
        
        tools_menu.addSeparator()
        
        # 代谢物拆分功能
        split_current_action = QAction('[信息] 拆分当前样本代谢物', self)
        split_current_action.setToolTip('将当前样本的每个代谢物拆分为单独的CSV文件')
        split_current_action.triggered.connect(self.split_current_sample_metabolites)
        tools_menu.addAction(split_current_action)
        
        split_batch_action = QAction('[信息] 批量拆分代谢物（从Excel）', self)
        split_batch_action.setToolTip('从已导出的Excel文件批量拆分代谢物数据')
        split_batch_action.triggered.connect(self.batch_split_metabolites_from_excel)
        tools_menu.addAction(split_batch_action)
        
        tools_menu.addSeparator()
        
        # 使用统计
        usage_stats_action = QAction('查看使用统计', self)
        usage_stats_action.setToolTip('查看软件使用统计信息（样本处理数量等）')
        usage_stats_action.triggered.connect(self.show_usage_stats)
        tools_menu.addAction(usage_stats_action)
        
        tools_menu.addSeparator()
        
        # 许可证管理
        license_info_action = QAction('许可证信息', self)
        license_info_action.setToolTip('查看当前许可证信息和到期时间')
        license_info_action.triggered.connect(self.show_license_info)
        tools_menu.addAction(license_info_action)
        
        update_license_action = QAction('更新许可证', self)
        update_license_action.setToolTip('更新许可证密钥')
        update_license_action.triggered.connect(self.update_license)
        tools_menu.addAction(update_license_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        self.peak_annotation_action = QAction('显示峰标注', self, checkable=True)
        self.peak_annotation_action.setChecked(True)
        self.peak_annotation_action.triggered.connect(self.toggle_peak_annotation)
        view_menu.addAction(self.peak_annotation_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar('主工具栏')
        self.addToolBar(toolbar)
        
        # 色彩方案选择
        toolbar.addWidget(QLabel('色彩方案: '))
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(['hot', 'viridis', 'plasma', 'inferno', 
                                      'magma', 'jet', 'rainbow', 'coolwarm'])
        self.colormap_combo.currentTextChanged.connect(self.change_colormap)
        toolbar.addWidget(self.colormap_combo)
        
        toolbar.addSeparator()
        
        # 刷新按钮
        refresh_btn = QPushButton('刷新')
        refresh_btn.clicked.connect(self.refresh_display)
        toolbar.addWidget(refresh_btn)
        
        # Lock Mass校准工具
        toolbar.addSeparator()
        toolbar.addWidget(QLabel('Lock Mass: '))
        
        # 应用校准按钮
        calibrate_btn = QPushButton('应用校准')
        calibrate_btn.setToolTip('对当前样本应用Lock Mass质量校准')
        calibrate_btn.clicked.connect(self.apply_lock_mass_calibration)
        toolbar.addWidget(calibrate_btn)
        
        # 导出校准数据按钮
        export_calib_btn = QPushButton('导出校准数据')
        export_calib_btn.setToolTip('导出Lock Mass校准后的数据到Excel')
        export_calib_btn.clicked.connect(self.export_calibrated_data)
        toolbar.addWidget(export_calib_btn)
        
        # 切换显示按钮
        toggle_btn = QPushButton('切换原始/校准')
        toggle_btn.setToolTip('在原始数据和校准数据之间切换显示')
        toggle_btn.clicked.connect(self.toggle_calibration)
        toolbar.addWidget(toggle_btn)
    
    def init_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # 控制栏
        control_layout = QHBoxLayout()
        
        open_btn = QPushButton('打开工作目录')
        open_btn.clicked.connect(self.open_workspace)
        control_layout.addWidget(open_btn)
        
        control_layout.addWidget(QLabel('m/z:'))
        self.mz_input = QDoubleSpinBox()
        self.mz_input.setRange(0, 2000)
        self.mz_input.setValue(50.0)
        self.mz_input.setDecimals(4)
        self.mz_input.valueChanged.connect(self.manual_mz_change)
        control_layout.addWidget(self.mz_input)
        
        update_btn = QPushButton('更新成像图')
        update_btn.clicked.connect(self.update_imaging)
        control_layout.addWidget(update_btn)
        
        # 多样本比对按钮
        compare_btn = QPushButton('多样本比对')
        compare_btn.clicked.connect(self.open_sample_comparison)
        control_layout.addWidget(compare_btn)
        
        control_layout.addStretch()
        
        main_layout.addLayout(control_layout)
        
        # 主分割器
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧
        left_splitter = QSplitter(Qt.Vertical)
        
        # 样本列表
        sample_widget = QWidget()
        sample_layout = QVBoxLayout(sample_widget)
        sample_layout.addWidget(QLabel('样本列表'))
        self.sample_list = QListWidget()
        self.sample_list.itemDoubleClicked.connect(self.load_sample)
        sample_layout.addWidget(self.sample_list)
        left_splitter.addWidget(sample_widget)
        
        # 离子信息表
        ion_widget = QWidget()
        ion_layout = QVBoxLayout(ion_widget)
        ion_info_label = QLabel('离子信息表 (显示前100个，导出全部)')
        ion_info_label.setToolTip('表格显示前100个高强度离子\n点击下方按钮可导出所有离子')
        ion_layout.addWidget(ion_info_label)
        self.ion_table = IonTable()
        self.ion_table.ion_selected.connect(self.on_ion_selected)
        ion_layout.addWidget(self.ion_table)
        
        # 离子表操作按钮
        ion_button_layout = QHBoxLayout()
        ion_button_layout.addStretch()
        
        export_ion_btn = QPushButton('导出离子数据')
        export_ion_btn.setToolTip('导出所有离子数据，可选择包含代谢物注释')
        export_ion_btn.clicked.connect(self.ion_table.export_data)
        export_ion_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        ion_button_layout.addWidget(export_ion_btn)
        
        search_ion_btn = QPushButton('代谢物查询')
        search_ion_btn.setToolTip('搜索指定m/z的代谢物信息')
        search_ion_btn.clicked.connect(self.open_metabolite_search)
        search_ion_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        ion_button_layout.addWidget(search_ion_btn)
        ion_button_layout.addStretch()
        
        ion_layout.addLayout(ion_button_layout)
        left_splitter.addWidget(ion_widget)
        
        left_splitter.setSizes([200, 600])
        
        # 右侧
        right_splitter = QSplitter(Qt.Vertical)
        
        # 成像图（带工具栏）
        imaging_widget = QWidget()
        imaging_layout = QVBoxLayout(imaging_widget)
        imaging_layout.setContentsMargins(0, 0, 0, 0)
        
        imaging_label = QLabel('空间成像图 (支持ROI交互)')
        font = QFont()
        font.setBold(True)
        imaging_label.setFont(font)
        imaging_layout.addWidget(imaging_label)
        
        self.imaging_canvas = ImagingCanvas()
        self.imaging_toolbar = NavigationToolbar(self.imaging_canvas, self)
        
        imaging_layout.addWidget(self.imaging_toolbar)
        imaging_layout.addWidget(self.imaging_canvas)
        
        right_splitter.addWidget(imaging_widget)
        
        # 光谱图（带工具栏）
        spectrum_widget = QWidget()
        spectrum_layout = QVBoxLayout(spectrum_widget)
        spectrum_layout.setContentsMargins(0, 0, 0, 0)
        
        spectrum_label = QLabel('平均质谱图')
        spectrum_label.setFont(font)
        spectrum_layout.addWidget(spectrum_label)
        
        # 坐标轴范围控制
        axis_control_widget = QWidget()
        axis_control_layout = QHBoxLayout(axis_control_widget)
        axis_control_layout.setContentsMargins(5, 5, 5, 5)
        
        # X轴范围
        axis_control_layout.addWidget(QLabel('X轴:'))
        self.x_min_input = QLineEdit()
        self.x_min_input.setPlaceholderText('最小')
        self.x_min_input.setMaximumWidth(80)
        axis_control_layout.addWidget(self.x_min_input)
        
        axis_control_layout.addWidget(QLabel('-'))
        
        self.x_max_input = QLineEdit()
        self.x_max_input.setPlaceholderText('最大')
        self.x_max_input.setMaximumWidth(80)
        axis_control_layout.addWidget(self.x_max_input)
        
        axis_control_layout.addWidget(QLabel('Y轴:'))
        
        # Y轴范围
        self.y_min_input = QLineEdit()
        self.y_min_input.setPlaceholderText('最小')
        self.y_min_input.setMaximumWidth(80)
        axis_control_layout.addWidget(self.y_min_input)
        
        axis_control_layout.addWidget(QLabel('-'))
        
        self.y_max_input = QLineEdit()
        self.y_max_input.setPlaceholderText('最大')
        self.y_max_input.setMaximumWidth(80)
        axis_control_layout.addWidget(self.y_max_input)
        
        # 应用按钮
        apply_axis_btn = QPushButton('应用范围')
        apply_axis_btn.clicked.connect(self.apply_axis_range)
        axis_control_layout.addWidget(apply_axis_btn)
        
        # 重置按钮
        reset_axis_btn = QPushButton('重置')
        reset_axis_btn.clicked.connect(self.reset_axis_range)
        axis_control_layout.addWidget(reset_axis_btn)
        
        axis_control_layout.addStretch()
        
        spectrum_layout.addWidget(axis_control_widget)
        
        self.spectrum_canvas = SpectrumCanvas()
        self.spectrum_canvas.peak_clicked.connect(self.on_peak_clicked)
        self.spectrum_toolbar = NavigationToolbar(self.spectrum_canvas, self)
        
        spectrum_layout.addWidget(self.spectrum_toolbar)
        spectrum_layout.addWidget(self.spectrum_canvas)
        
        right_splitter.addWidget(spectrum_widget)
        
        right_splitter.setSizes([600, 300])
        
        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([500, 1100])
        
        main_layout.addWidget(main_splitter)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage('[成功] 就绪 - 所有功能完全实现，无"开发中"提示')
    
    def open_workspace(self):
        """打开工作目录"""
        workspace = QFileDialog.getExistingDirectory(
            self, '选择工作目录',
            '/Volumes/US100 256G/mouse DESI data'
        )
        
        if not workspace:
            return
        
        # 保存工作目录路径
        self.workspace_path = Path(workspace)
        
        self.status_bar.showMessage('[SEARCH] 正在扫描样本...')
        QApplication.processEvents()
        
        samples = self.loader.find_samples(workspace)
        
        self.sample_list.clear()
        for sample in samples:
            self.sample_list.addItem(sample.name)
        
        self.status_bar.showMessage(f'[成功] 找到 {len(samples)} 个有效样本')
    
    def load_sample(self, item):
        """加载样本（集成Lock Mass自动校准）"""
        sample_name = item.text()
        workspace = Path('/Volumes/US100 256G/mouse DESI data')
        sample_path = workspace / sample_name
        
        self.status_bar.showMessage(f'[RECEIVE] 正在加载样本: {sample_name}...')
        QApplication.processEvents()
        
        print(f"\n{'='*70}")
        print(f"[RECEIVE] 加载样本: {sample_name}")
        print(f"{'='*70}")
        
        data = self.loader.load(sample_path)
        
        if data is None:
            QMessageBox.warning(self, '错误', f'无法加载样本: {sample_name}')
            self.status_bar.showMessage('[错误] 加载失败')
            return
        
        # 应用数据过滤（如果启用）
        if self.data_filter_config.enabled:
            data = self.data_filter.filter_data(data)
        
        # 保存原始数据备份
        self.original_data = data.copy()
        
        # 检查是否需要自动应用Lock Mass校准
        if self.lock_mass_config.enabled:
            print("[配置] Lock Mass已启用，自动应用校准...")
            self.current_data = data  # 临时赋值，以便apply_lock_mass_calibration使用
            self.apply_lock_mass_calibration(silent=True)
        else:
            self.current_data = data
            self.data_is_calibrated = False
        
        # 更新所有视图
        self.ion_table.update_table(self.current_data)
        self.imaging_canvas.update_display(self.current_data, self.mz_input.value())
        self.spectrum_canvas.update_display(self.current_data)
        
        # 更新状态栏
        self.update_calibration_status()
        
        # 记录使用量
        try:
            from usage_tracker import record_sample_load
            record_sample_load(
                sample_name,
                n_scans=self.current_data.get('n_scans', 0),
                n_mz=len(self.current_data.get('mz_bins', []))
            )
        except Exception as e:
            pass  # 静默失败，不影响主功能
        
        print(f"[成功] 加载完成")
    
    def on_ion_selected(self, mz):
        """离子选择事件"""
        self.mz_input.setValue(mz)
        self.update_imaging()
    
    def open_metabolite_search(self):
        """打开代谢物查询对话框"""
        dialog = MetaboliteSearchDialog(self)
        # 如果有选中的离子，设置其m/z值
        current_row = self.ion_table.currentRow()
        if current_row >= 0:
            mz = float(self.ion_table.item(current_row, 0).text())
            dialog.set_mz(mz)
        dialog.exec_()
    
    def on_peak_clicked(self, mz):
        """峰点击事件"""
        self.mz_input.setValue(mz)
        self.update_imaging()
    
    def apply_axis_range(self):
        """应用坐标轴范围"""
        try:
            xlim = None
            ylim = None
            
            # 解析X轴范围
            x_min_text = self.x_min_input.text().strip()
            x_max_text = self.x_max_input.text().strip()
            if x_min_text and x_max_text:
                x_min = float(x_min_text)
                x_max = float(x_max_text)
                if x_min < x_max:
                    xlim = (x_min, x_max)
                else:
                    QMessageBox.warning(self, '输入错误', 'X轴最小值必须小于最大值')
                    return
            
            # 解析Y轴范围
            y_min_text = self.y_min_input.text().strip()
            y_max_text = self.y_max_input.text().strip()
            if y_min_text and y_max_text:
                y_min = float(y_min_text)
                y_max = float(y_max_text)
                if y_min < y_max:
                    ylim = (y_min, y_max)
                else:
                    QMessageBox.warning(self, '输入错误', 'Y轴最小值必须小于最大值')
                    return
            
            # 应用范围
            if xlim or ylim:
                self.spectrum_canvas.set_axis_range(xlim, ylim)
                print(f"[成功] 应用坐标轴范围: X={xlim}, Y={ylim}")
            else:
                QMessageBox.information(self, '提示', '请输入要设置的坐标轴范围')
        
        except ValueError:
            QMessageBox.warning(self, '输入错误', '请输入有效的数值')
    
    def reset_axis_range(self):
        """重置坐标轴范围"""
        self.spectrum_canvas.reset_axis_range()
        self.x_min_input.clear()
        self.x_max_input.clear()
        self.y_min_input.clear()
        self.y_max_input.clear()
        print("[成功] 重置坐标轴范围到默认值")
    
    def manual_mz_change(self):
        """手动更改m/z"""
        pass
    
    def update_imaging(self):
        """更新成像图"""
        if not self.current_data:
            QMessageBox.warning(self, '警告', '请先加载样本')
            return
        
        mz = self.mz_input.value()
        self.imaging_canvas.update_display(self.current_data, mz)
        self.status_bar.showMessage(f'[成功] 已更新成像图: m/z {mz:.4f}')
    
    def change_colormap(self, colormap):
        """更改色彩方案"""
        self.imaging_canvas.colormap = colormap
        if self.current_data:
            self.update_imaging()
    
    def refresh_display(self):
        """刷新显示"""
        if self.current_data:
            self.update_imaging()
            self.spectrum_canvas.update_display(self.current_data)
    
    def toggle_peak_annotation(self):
        """切换峰标注"""
        self.spectrum_canvas.show_annotations = self.peak_annotation_action.isChecked()
        if self.current_data:
            self.spectrum_canvas.update_display(self.current_data)
    
    def show_metabolite_search(self):
        """显示代谢物查询"""
        dialog = MetaboliteSearchDialog(self)
        if self.current_data:
            mz = self.mz_input.value()
            dialog.set_mz(mz)
        dialog.exec_()
    
    def show_lock_mass_dialog(self):
        """显示Lock Mass配置对话框"""
        dialog = LockMassDialog(self, self.lock_mass_config, self.lock_mass_manager)
        dialog.config_changed.connect(self.on_lock_mass_config_changed)
        dialog.exec_()
    
    def on_lock_mass_config_changed(self, new_config):
        """Lock Mass配置改变时"""
        self.lock_mass_config = new_config
        self.lock_mass_manager.config = new_config
        print(f"[成功] Lock Mass配置已更新:")
        print(f"   启用: {new_config.enabled}")
        print(f"   Lock Mass m/z: {new_config.lock_mass_mz:.4f}")
        print(f"   容差: {new_config.tolerance_amu:.2f} amu")
        print(f"   合并容差: {new_config.merge_tolerance_ppm:.1f} ppm")
    
    def show_data_filter_dialog(self):
        """显示数据过滤配置对话框"""
        from data_filter_dialog import DataFilterDialog
        dialog = DataFilterDialog(self, self.data_filter_config)
        dialog.config_changed.connect(self.on_data_filter_config_changed)
        dialog.exec_()
    
    def on_data_filter_config_changed(self, new_config):
        """数据过滤配置改变时"""
        from data_filter import DataFilter
        self.data_filter_config = new_config
        self.data_filter = DataFilter(self.data_filter_config)
        print(f"[成功] 数据过滤配置已更新:")
        print(f"   启用: {new_config.enabled}")
        print(f"   过滤条件: {new_config.get_filter_description()}")
    
    def show_comparison(self):
        """显示多离子对比"""
        if not self.current_data:
            QMessageBox.warning(self, '警告', '请先加载样本')
            return
        
        dialog = MultiIonComparisonDialog(self, self.current_data)
        dialog.exec_()
    
    def show_roi_dialog(self):
        """显示ROI对话框"""
        if not self.current_data:
            QMessageBox.warning(self, '警告', '请先加载样本')
            return
        
        if not self.roi_dialog:
            self.roi_dialog = ROIDialog(self)
        
        self.roi_dialog.show()
    
    def open_sample_comparison(self):
        """打开多样本比对对话框"""
        # 检查是否有样本
        if self.sample_list.count() == 0:
            QMessageBox.warning(self, '警告', '请先打开工作目录并扫描样本')
            return
        
        # 创建并显示对话框，传递loader、workspace和lock_mass_manager
        dialog = SampleComparisonDialog(
            self, 
            self.loader, 
            self.workspace_path,
            lock_mass_manager=self.lock_mass_manager  # 传递Lock Mass管理器
        )
        dialog.exec_()
    
    def start_roi_selection(self, roi_type):
        """开始ROI选择"""
        if not self.current_data:
            QMessageBox.warning(self, '警告', '请先加载样本')
            return
        
        # 确保ROI对话框打开
        if not self.roi_dialog:
            self.roi_dialog = ROIDialog(self)
        self.roi_dialog.show()
        
        # 开始ROI选择
        self.imaging_canvas.start_roi_selection(roi_type, self.on_roi_created)
        
        if roi_type == 'rectangle':
            self.status_bar.showMessage('[MOUSE]  按住鼠标左键拖拽选择矩形区域')
        elif roi_type == 'polygon':
            self.status_bar.showMessage('[MOUSE]  左键点击添加顶点，右键或双击完成多边形')
    
    def on_roi_created(self, roi):
        """ROI创建完成"""
        print(f"[成功] 创建ROI: {roi.name}")
        
        if self.roi_dialog:
            self.roi_dialog.add_roi(roi)
        
        self.imaging_canvas.add_roi_patch(roi)
        self.status_bar.showMessage(f'[成功] 已创建 {roi.name}')
    
    def generate_pdf_report(self):
        """生成PDF报告"""
        if not self.current_data:
            QMessageBox.warning(self, '警告', '请先加载样本')
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, '保存PDF报告', '', 'PDF文件 (*.pdf)'
        )
        
        if filename:
            self.status_bar.showMessage('[文件] 正在生成PDF报告...')
            QApplication.processEvents()
            
            try:
                self.report_generator.generate_summary_report(self.current_data, filename)
                QMessageBox.information(self, '成功', f'PDF报告已生成:\n{filename}')
                self.status_bar.showMessage(f'[成功] PDF报告已生成')
            except Exception as e:
                QMessageBox.warning(self, '错误', f'报告生成失败: {e}')
                self.status_bar.showMessage('[错误] 报告生成失败')
    
    def generate_excel_report(self):
        """生成Excel报告"""
        if not self.current_data:
            QMessageBox.warning(self, '警告', '请先加载样本')
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, '保存Excel报告', '', 'Excel文件 (*.xlsx)'
        )
        
        if filename:
            self.status_bar.showMessage('[统计] 正在生成Excel报告...')
            QApplication.processEvents()
            
            try:
                self.report_generator.generate_excel_report(self.current_data, filename)
                QMessageBox.information(self, '成功', f'Excel报告已生成:\n{filename}')
                self.status_bar.showMessage(f'[成功] Excel报告已生成')
            except Exception as e:
                QMessageBox.warning(self, '错误', f'报告生成失败: {e}')
                self.status_bar.showMessage('[错误] 报告生成失败')
    
    def export_image(self):
        """导出成像图"""
        if not self.current_data:
            QMessageBox.warning(self, '警告', '请先加载样本')
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, '保存成像图', '', 
            'PNG文件 (*.png);;PDF文件 (*.pdf);;所有文件 (*)'
        )
        
        if filename:
            self.imaging_canvas.fig.savefig(filename, dpi=300, bbox_inches='tight')
            QMessageBox.information(self, '成功', f'成像图已保存到:\n{filename}')
    
    def export_spectrum(self):
        """导出光谱图"""
        if not self.current_data:
            QMessageBox.warning(self, '警告', '请先加载样本')
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, '保存光谱图', '', 
            'PNG文件 (*.png);;PDF文件 (*.pdf);;所有文件 (*)'
        )
        
        if filename:
            self.spectrum_canvas.fig.savefig(filename, dpi=300, bbox_inches='tight')
            QMessageBox.information(self, '成功', f'光谱图已保存到:\n{filename}')
    
    def apply_lock_mass_calibration(self, silent=False):
        """应用Lock Mass校准到当前样本"""
        if not self.current_data:
            if not silent:
                QMessageBox.warning(self, '警告', '请先加载样本')
            return
        
        if not self.original_data:
            self.original_data = self.current_data.copy()
        
        try:
            from calibrated_data_handler import CalibratedDataHandler
            from PyQt5.QtWidgets import QProgressDialog
            
            # 创建处理器
            handler = CalibratedDataHandler(self.lock_mass_manager)
            
            # 显示进度（非静默模式）
            if not silent:
                progress = QProgressDialog("正在应用Lock Mass校准...", None, 0, 0, self)
                progress.setWindowModality(Qt.WindowModal)
                progress.show()
                QApplication.processEvents()
            
            # 应用校准
            calibrated_data = handler.process_sample(self.original_data)
            
            if not silent:
                progress.close()
            
            # 检查是否校准成功
            if calibrated_data.get('calibration_info', {}).get('calibrated'):
                self.current_data = calibrated_data
                self.data_is_calibrated = True
                
                calib_info = calibrated_data['calibration_info']
                
                if not silent:
                    QMessageBox.information(self, '校准成功', 
                        f"[成功] Lock Mass校准已应用！\n\n"
                        f"Lock Mass m/z: {calib_info['lock_mass_mz']:.4f}\n"
                        f"校正值: {calib_info['correction_da']:+.6f} Da\n"
                        f"离子数量: {len(self.original_data['mz_bins'])} → "
                        f"{len(calibrated_data['mz_bins'])}")
                
                # 更新所有显示
                self.ion_table.update_table(self.current_data)
                self.imaging_canvas.update_display(self.current_data, self.mz_input.value())
                self.spectrum_canvas.update_display(self.current_data)
            else:
                self.data_is_calibrated = False
                reason = calibrated_data.get('calibration_info', {}).get('reason', 'Unknown')
                if not silent:
                    QMessageBox.warning(self, '校准失败', 
                        f"[警告] Lock Mass校准未成功\n\n原因: {reason}\n\n使用原始数据")
                else:
                    print(f"[警告] Lock Mass校准未成功: {reason}")
            
            self.update_calibration_status()
            
        except Exception as e:
            QMessageBox.critical(self, '错误', f'校准失败:\n{e}')
            import traceback
            traceback.print_exc()
    
    def export_calibrated_data(self):
        """导出校准后的数据（优化版 - 带导出选项和详细进度）"""
        if not self.current_data:
            QMessageBox.warning(self, '警告', '请先加载样本')
            return
        
        if not self.data_is_calibrated:
            reply = QMessageBox.question(self, '确认',
                '当前数据未校准，是否要导出原始数据？',
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        
        try:
            from calibrated_data_handler import CalibratedDataHandler
            
            handler = CalibratedDataHandler(self.lock_mass_manager)
            
            # 获取数据信息
            n_scans = len(self.current_data.get('coords', []))
            n_mz = len(self.current_data.get('mz_bins', []))
            total_points = n_scans * n_mz
            
            # 显示导出选项对话框
            from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, 
                                        QRadioButton, QSpinBox, QLabel, QPushButton, QCheckBox)
            
            options_dialog = QDialog(self)
            options_dialog.setWindowTitle('校准数据导出选项')
            options_dialog.setMinimumWidth(500)
            
            layout = QVBoxLayout()
            
            # 数据信息
            info_label = QLabel(f"[统计] 当前数据: {n_scans:,} 扫描点 × {n_mz:,} m/z bins\n"
                               f"[趋势] 总数据点: {total_points:,}")
            info_label.setStyleSheet("color: blue; font-weight: bold; padding: 10px;")
            layout.addWidget(info_label)
            
            # 扫描点选项
            scan_group = QGroupBox("[1] 扫描点选项")
            scan_layout = QVBoxLayout()
            
            scan_all_radio = QRadioButton(f"导出全部扫描点 ({n_scans:,} 个)")
            scan_all_radio.setChecked(True)
            scan_layout.addWidget(scan_all_radio)
            
            scan_sample_layout = QHBoxLayout()
            scan_sample_radio = QRadioButton("扫描点采样（每N点取1个）：")
            scan_sample_spin = QSpinBox()
            scan_sample_spin.setRange(2, 100)
            scan_sample_spin.setValue(10)
            scan_sample_spin.setSuffix(' 点取1')
            scan_sample_layout.addWidget(scan_sample_radio)
            scan_sample_layout.addWidget(scan_sample_spin)
            scan_sample_layout.addStretch()
            scan_layout.addLayout(scan_sample_layout)
            
            scan_group.setLayout(scan_layout)
            layout.addWidget(scan_group)
            
            # m/z选项
            mz_group = QGroupBox("[2] m/z bins选项")
            mz_layout = QVBoxLayout()
            
            mz_all_radio = QRadioButton(f"导出全部m/z ({n_mz:,} 个)")
            mz_all_radio.setChecked(True)
            mz_layout.addWidget(mz_all_radio)
            
            mz_top_layout = QHBoxLayout()
            mz_top_radio = QRadioButton("导出Top N高强度m/z：")
            mz_top_spin = QSpinBox()
            mz_top_spin.setRange(100, min(n_mz, 2000))
            mz_top_spin.setValue(min(500, n_mz))
            mz_top_spin.setSuffix(' 个')
            mz_top_layout.addWidget(mz_top_radio)
            mz_top_layout.addWidget(mz_top_spin)
            mz_top_layout.addStretch()
            mz_layout.addLayout(mz_top_layout)
            
            mz_group.setLayout(mz_layout)
            layout.addWidget(mz_group)
            
            # 性能提示
            hint_label = QLabel()
            hint_label.setWordWrap(True)
            hint_label.setStyleSheet("background-color: #ffffcc; padding: 10px; border-radius: 5px;")
            layout.addWidget(hint_label)
            
            def update_hint():
                """更新性能提示"""
                est_scans = n_scans
                est_mz = n_mz
                
                if scan_sample_radio.isChecked():
                    est_scans = n_scans // scan_sample_spin.value()
                
                if mz_top_radio.isChecked():
                    est_mz = mz_top_spin.value()
                
                est_points = est_scans * est_mz
                reduction = 100 * (1 - est_points / total_points)
                
                # 估算时间（基于实测数据）
                # 全量约150-250秒，向量化优化后约30-50秒
                # 进一步过滤可降至5-15秒
                if est_points > 10_000_000:  # >1000万
                    est_time = "30-60秒"
                    color = "orange"
                elif est_points > 1_000_000:  # >100万
                    est_time = "10-30秒"
                    color = "green"
                else:
                    est_time = "5-15秒"
                    color = "darkgreen"
                
                hint_text = (f"[提示] 预计导出: {est_scans:,} 扫描 × {est_mz:,} m/z = {est_points:,} 数据点\n"
                            f"[DECLINE] 数据量减少: {reduction:.1f}%\n"
                            f"[时间]  预计耗时: {est_time}")
                
                hint_label.setText(hint_text)
                hint_label.setStyleSheet(f"background-color: {color}; color: white; "
                                        f"padding: 10px; border-radius: 5px; font-weight: bold;")
            
            # 连接信号
            scan_all_radio.toggled.connect(update_hint)
            scan_sample_radio.toggled.connect(update_hint)
            scan_sample_spin.valueChanged.connect(update_hint)
            mz_all_radio.toggled.connect(update_hint)
            mz_top_radio.toggled.connect(update_hint)
            mz_top_spin.valueChanged.connect(update_hint)
            
            update_hint()
            
            # 按钮
            button_layout = QHBoxLayout()
            ok_button = QPushButton('开始导出')
            ok_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px; font-weight: bold;")
            cancel_button = QPushButton('取消')
            
            ok_button.clicked.connect(options_dialog.accept)
            cancel_button.clicked.connect(options_dialog.reject)
            
            button_layout.addStretch()
            button_layout.addWidget(cancel_button)
            button_layout.addWidget(ok_button)
            layout.addLayout(button_layout)
            
            options_dialog.setLayout(layout)
            
            # 显示对话框
            if options_dialog.exec_() != QDialog.Accepted:
                return
            
            # 获取用户选择
            max_scans = None
            if scan_sample_radio.isChecked():
                max_scans = n_scans // scan_sample_spin.value()
            
            max_mz = None
            if mz_top_radio.isChecked():
                max_mz = mz_top_spin.value()
            
            # 选择输出目录
            output_dir = QFileDialog.getExistingDirectory(
                self, '选择导出目录', str(self.workspace_path)
            )
            
            if not output_dir:
                return
            
            # 详细进度条
            from PyQt5.QtWidgets import QProgressDialog
            progress = QProgressDialog("准备导出...", "取消", 0, 100, self)
            progress.setWindowTitle("导出校准数据")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            progress.show()
            QApplication.processEvents()
            
            # 进度回调函数
            def progress_callback(stage, pct, message):
                """进度回调"""
                stage_names = ['', '数据过滤', '数据处理', 'DataFrame', 'Excel写入', '完成']
                progress.setLabelText(f"阶段 {stage}/5: {stage_names[stage]}\n{message}")
                progress.setValue(pct)
                QApplication.processEvents()
                
                # 检查取消
                if progress.wasCanceled():
                    raise Exception("用户取消导出")
            
            # 导出数据
            import time
            start_time = time.time()
            
            excel_file = handler.export_calibrated_data(
                self.current_data, 
                Path(output_dir),
                progress_callback=progress_callback,
                max_scans=max_scans,
                max_mz=max_mz
            )
            
            # 如果有原始数据，生成对比报告
            report_file = None
            if self.data_is_calibrated and self.original_data:
                progress.setLabelText("生成校准对比报告...")
                progress.setValue(95)
                QApplication.processEvents()
                
                report_file = handler.generate_comparison_report(
                    self.original_data, self.current_data, Path(output_dir)
                )
            
            progress.setValue(100)
            progress.close()
            
            elapsed = time.time() - start_time
            
            # 成功消息
            msg = f"[成功] 数据已导出！\n\n"
            msg += f"[文件] Excel文件: {Path(excel_file).name}\n"
            msg += f"[文件] 目录: {output_dir}\n"
            msg += f"[时间]  耗时: {elapsed:.1f} 秒\n"
            
            if max_scans or max_mz:
                msg += f"\n[TARGET] 过滤选项:\n"
                if max_scans:
                    msg += f"   - 扫描点采样: {n_scans:,} → {max_scans:,}\n"
                if max_mz:
                    msg += f"   - m/z Top N: {n_mz:,} → {max_mz:,}\n"
            
            if report_file:
                msg += f"\n[统计] 对比报告: {Path(report_file).name}"
            
            QMessageBox.information(self, '导出成功', msg)
            
            # 询问是否打开文件
            reply = QMessageBox.question(self, '打开文件',
                '是否打开导出的Excel文件？',
                QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                import subprocess
                subprocess.run(['open', str(excel_file)])
                
        except Exception as e:
            if progress:
                progress.close()
            if "用户取消" not in str(e):
                QMessageBox.critical(self, '错误', f'导出失败:\n{e}')
                import traceback
                traceback.print_exc()
    
    def update_calibration_status(self):
        """更新校准状态显示"""
        if not self.current_data:
            return
        
        sample_name = self.current_data.get('sample_name', '未知样本')
        n_scans = self.current_data.get('n_scans', 0)
        n_bins = len(self.current_data.get('mz_bins', []))
        
        if self.data_is_calibrated:
            calib_info = self.current_data.get('calibration_info', {})
            correction = calib_info.get('correction_da', 0)
            status_text = f"[成功] {sample_name} (已校准 {correction:+.6f} Da) | {n_scans} 扫描 | {n_bins} m/z bins"
        else:
            status_text = f"⚪ {sample_name} (未校准) | {n_scans} 扫描 | {n_bins} m/z bins"
        
        self.status_bar.showMessage(status_text)
    
    def toggle_calibration(self):
        """切换显示校准/原始数据"""
        if not self.original_data:
            QMessageBox.warning(self, '警告', '没有可切换的数据')
            return
        
        if self.data_is_calibrated:
            # 切换到原始数据
            self.current_data = self.original_data.copy()
            self.data_is_calibrated = False
            
            # 更新所有显示
            self.ion_table.update_table(self.current_data)
            self.imaging_canvas.update_display(self.current_data, self.mz_input.value())
            self.spectrum_canvas.update_display(self.current_data)
            
            self.update_calibration_status()
            QMessageBox.information(self, '已切换', '现在显示原始数据')
        else:
            # 尝试应用校准
            self.apply_lock_mass_calibration()
    
    def split_current_sample_metabolites(self):
        """拆分当前样本的代谢物数据"""
        if not self.current_data:
            QMessageBox.warning(self, '警告', '请先加载样本数据')
            return
        
        # 显示选项对话框
        dialog = QDialog(self)
        dialog.setWindowTitle('拆分代谢物数据')
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        
        # 样本信息
        sample_name = self.current_data.get('sample_name', '未知样本')
        n_mz = len(self.current_data.get('mz_bins', []))
        n_scans = len(self.current_data.get('coords', []))
        
        info_label = QLabel(f"<b>当前样本:</b> {sample_name}<br>"
                           f"<b>代谢物数量:</b> {n_mz}<br>"
                           f"<b>扫描点数:</b> {n_scans}")
        info_label.setStyleSheet("padding: 10px; background-color: #e3f2fd; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # m/z数量选项
        mz_group = QGroupBox("导出数量")
        mz_layout = QVBoxLayout()
        
        mz_all_radio = QRadioButton(f"导出全部 ({n_mz} 个代谢物)")
        mz_all_radio.setChecked(True)
        mz_layout.addWidget(mz_all_radio)
        
        mz_top_layout = QHBoxLayout()
        mz_top_radio = QRadioButton("导出Top N高强度:")
        mz_top_spin = QSpinBox()
        mz_top_spin.setRange(10, min(n_mz, 2000))
        mz_top_spin.setValue(min(500, n_mz))
        mz_top_spin.setSuffix(' 个')
        mz_top_layout.addWidget(mz_top_radio)
        mz_top_layout.addWidget(mz_top_spin)
        mz_top_layout.addStretch()
        mz_layout.addLayout(mz_top_layout)
        
        mz_group.setLayout(mz_layout)
        layout.addWidget(mz_group)
        
        # 处理选项
        options_group = QGroupBox("处理选项")
        options_layout = QVBoxLayout()
        
        process_spin_layout = QHBoxLayout()
        process_spin_layout.addWidget(QLabel("并行进程数:"))
        process_spin = QSpinBox()
        process_spin.setRange(1, 8)
        process_spin.setValue(4)
        process_spin_layout.addWidget(process_spin)
        process_spin_layout.addStretch()
        options_layout.addLayout(process_spin_layout)
        
        archive_check = QCheckBox("创建ZIP压缩包")
        archive_check.setChecked(True)
        options_layout.addWidget(archive_check)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_btn = QPushButton('开始拆分')
        ok_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px; font-weight: bold;")
        cancel_btn = QPushButton('取消')
        
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(ok_btn)
        layout.addLayout(button_layout)
        
        if dialog.exec_() != QDialog.Accepted:
            return
        
        # 获取选项
        max_mz = None if mz_all_radio.isChecked() else mz_top_spin.value()
        n_processes = process_spin.value()
        create_archive = archive_check.isChecked()
        
        # 选择输出目录
        output_dir = QFileDialog.getExistingDirectory(
            self, '选择输出目录', str(self.workspace_path) if self.workspace_path else ''
        )
        
        if not output_dir:
            return
        
        # 执行拆分
        try:
            from metabolite_splitter import MetaboliteSplitter
            import multiprocessing
            
            # macOS需要设置启动方法
            try:
                multiprocessing.set_start_method('spawn', force=True)
            except RuntimeError:
                pass
            
            splitter = MetaboliteSplitter(n_processes=n_processes, batch_size=50)
            
            # 进度对话框
            from PyQt5.QtWidgets import QProgressDialog
            progress = QProgressDialog("准备拆分...", "取消", 0, 100, self)
            progress.setWindowTitle("拆分代谢物数据")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()
            
            def progress_callback(current, total, message):
                progress.setValue(current)
                progress.setLabelText(message)
                QApplication.processEvents()
                if progress.wasCanceled():
                    raise Exception("用户取消")
            
            result = splitter.split_from_data(
                self.current_data,
                output_dir,
                sample_name,
                progress_callback=progress_callback,
                create_archive=create_archive,
                max_mz=max_mz
            )
            
            progress.close()
            
            if result['success']:
                msg = f"[成功] 拆分完成！\n\n"
                msg += f"样本: {result['sample_name']}\n"
                msg += f"成功: {result['success_count']}/{result['metabolites_count']} 个代谢物\n"
                msg += f"输出目录: {result['output_dir']}\n"
                msg += f"耗时: {result['time']:.1f} 秒\n"
                if result['zip_file']:
                    msg += f"\n压缩包: {Path(result['zip_file']).name}"
                
                QMessageBox.information(self, '拆分完成', msg)
                
                # 记录使用量
                try:
                    from usage_tracker import record_metabolite_split
                    record_metabolite_split(sample_name, result['success_count'])
                except:
                    pass
                
                # 询问是否打开目录
                reply = QMessageBox.question(self, '打开目录', '是否打开输出目录？',
                    QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    import subprocess
                    subprocess.run(['open', result['output_dir']])
            else:
                QMessageBox.warning(self, '拆分失败', f"错误: {result.get('error', '未知错误')}")
        
        except Exception as e:
            if 'progress' in locals():
                progress.close()
            if "用户取消" not in str(e):
                QMessageBox.critical(self, '错误', f'拆分失败:\n{e}')
                import traceback
                traceback.print_exc()
    
    def batch_split_metabolites_from_excel(self):
        """从Excel文件批量拆分代谢物数据"""
        # 选择Excel文件
        files, _ = QFileDialog.getOpenFileNames(
            self, '选择Excel文件（二维空间格式）',
            str(self.workspace_path) if self.workspace_path else '',
            'Excel文件 (*.xlsx);;所有文件 (*.*)'
        )
        
        if not files:
            return
        
        # 显示选项对话框
        dialog = QDialog(self)
        dialog.setWindowTitle('批量拆分代谢物数据')
        dialog.setMinimumWidth(600)
        
        layout = QVBoxLayout(dialog)
        
        # 文件列表
        files_group = QGroupBox(f"已选择 {len(files)} 个文件")
        files_layout = QVBoxLayout()
        
        files_list = QListWidget()
        for f in files:
            files_list.addItem(Path(f).name)
        files_list.setMaximumHeight(150)
        files_layout.addWidget(files_list)
        
        files_group.setLayout(files_layout)
        layout.addWidget(files_group)
        
        # 处理选项
        options_group = QGroupBox("处理选项")
        options_layout = QVBoxLayout()
        
        process_spin_layout = QHBoxLayout()
        process_spin_layout.addWidget(QLabel("并行进程数:"))
        process_spin = QSpinBox()
        process_spin.setRange(1, 8)
        process_spin.setValue(4)
        process_spin_layout.addWidget(process_spin)
        process_spin_layout.addStretch()
        options_layout.addLayout(process_spin_layout)
        
        archive_check = QCheckBox("为每个样本创建ZIP压缩包")
        archive_check.setChecked(True)
        options_layout.addWidget(archive_check)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_btn = QPushButton('开始批量拆分')
        ok_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px; font-weight: bold;")
        cancel_btn = QPushButton('取消')
        
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(ok_btn)
        layout.addLayout(button_layout)
        
        if dialog.exec_() != QDialog.Accepted:
            return
        
        # 获取选项
        n_processes = process_spin.value()
        create_archives = archive_check.isChecked()
        
        # 选择输出目录
        output_dir = QFileDialog.getExistingDirectory(
            self, '选择输出目录', str(Path(files[0]).parent)
        )
        
        if not output_dir:
            return
        
        # 执行批量拆分
        try:
            from metabolite_splitter import MetaboliteSplitter
            import multiprocessing
            
            try:
                multiprocessing.set_start_method('spawn', force=True)
            except RuntimeError:
                pass
            
            splitter = MetaboliteSplitter(n_processes=n_processes, batch_size=50)
            
            # 进度对话框
            from PyQt5.QtWidgets import QProgressDialog
            progress = QProgressDialog("准备批量拆分...", "取消", 0, 100, self)
            progress.setWindowTitle("批量拆分代谢物数据")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()
            
            results = []
            total_files = len(files)
            
            for i, excel_file in enumerate(files):
                file_name = Path(excel_file).name
                
                def file_progress(current, total, message):
                    # 计算总进度
                    file_progress_pct = current / total if total > 0 else 0
                    overall_pct = int((i + file_progress_pct) / total_files * 100)
                    progress.setValue(overall_pct)
                    progress.setLabelText(f"文件 {i+1}/{total_files}: {file_name}\n{message}")
                    QApplication.processEvents()
                    if progress.wasCanceled():
                        raise Exception("用户取消")
                
                result = splitter.split_from_excel(
                    excel_file, output_dir,
                    progress_callback=file_progress,
                    create_archive=create_archives
                )
                results.append(result)
            
            progress.close()
            
            # 显示结果
            success_count = sum(1 for r in results if r['success'])
            total_metabolites = sum(r['success_count'] for r in results)
            
            msg = f"[成功] 批量拆分完成！\n\n"
            msg += f"处理文件: {success_count}/{total_files} 成功\n"
            msg += f"总代谢物: {total_metabolites} 个\n"
            msg += f"输出目录: {output_dir}\n\n"
            msg += "详细结果:\n"
            for r in results:
                status = "[成功]" if r['success'] else "[错误]"
                msg += f"  {status} {r['sample_name']}: {r['success_count']} 个\n"
            
            QMessageBox.information(self, '批量拆分完成', msg)
            
            # 询问是否打开目录
            reply = QMessageBox.question(self, '打开目录', '是否打开输出目录？',
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                import subprocess
                subprocess.run(['open', output_dir])
        
        except Exception as e:
            if 'progress' in locals():
                progress.close()
            if "用户取消" not in str(e):
                QMessageBox.critical(self, '错误', f'批量拆分失败:\n{e}')
                import traceback
                traceback.print_exc()
    
    def show_usage_stats(self):
        """显示使用统计"""
        try:
            from usage_tracker import get_tracker
            
            tracker = get_tracker()
            stats = tracker.get_usage_stats(30)
            integrity = tracker.verify_integrity()
            
            # 创建统计对话框
            dialog = QDialog(self)
            dialog.setWindowTitle('[统计] 使用统计')
            dialog.setMinimumWidth(500)
            
            layout = QVBoxLayout(dialog)
            
            # 许可证信息
            license_group = QGroupBox("许可证信息")
            license_layout = QVBoxLayout()
            license_label = QLabel(f"<b>License:</b> {stats['license_key']}<br>"
                                   f"<b>机器ID:</b> {stats['machine_id']}")
            license_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            license_layout.addWidget(license_label)
            license_group.setLayout(license_layout)
            layout.addWidget(license_group)
            
            # 使用统计
            stats_group = QGroupBox(f"最近 {stats['period_days']} 天使用统计")
            stats_layout = QVBoxLayout()
            
            stats_text = f"""
            <table>
            <tr><td><b>总操作次数:</b></td><td>{stats['total_records']}</td></tr>
            <tr><td><b>唯一样本数:</b></td><td>{stats['unique_samples']}</td></tr>
            <tr><td><b>样本加载次数:</b></td><td>{stats['total_loads']}</td></tr>
            <tr><td><b>数据导出次数:</b></td><td>{stats['total_exports']}</td></tr>
            <tr><td><b>代谢物拆分次数:</b></td><td>{stats['total_splits']}</td></tr>
            </table>
            """
            stats_label = QLabel(stats_text)
            stats_layout.addWidget(stats_label)
            stats_group.setLayout(stats_layout)
            layout.addWidget(stats_group)
            
            # 数据完整性
            integrity_group = QGroupBox("数据完整性验证")
            integrity_layout = QVBoxLayout()
            
            if integrity['integrity_ok']:
                integrity_text = f"<font color='green'>[成功] 数据完整性验证通过</font><br>"
            else:
                integrity_text = f"<font color='red'>[警告] 发现 {integrity['invalid_records']} 条异常记录</font><br>"
            
            integrity_text += f"总记录数: {integrity['total_records']}<br>"
            integrity_text += f"有效记录: {integrity['valid_records']}"
            
            integrity_label = QLabel(integrity_text)
            integrity_layout.addWidget(integrity_label)
            integrity_group.setLayout(integrity_layout)
            layout.addWidget(integrity_group)
            
            # 每日统计
            if stats['daily_stats']:
                daily_group = QGroupBox("每日统计（最近7天）")
                daily_layout = QVBoxLayout()
                
                daily_text = "<table border='1' cellpadding='5'>"
                daily_text += "<tr><th>日期</th><th>加载</th><th>导出</th><th>拆分</th><th>总计</th></tr>"
                
                for day in stats['daily_stats'][:7]:
                    daily_text += f"<tr><td>{day['date']}</td>"
                    daily_text += f"<td>{day['samples_loaded']}</td>"
                    daily_text += f"<td>{day['samples_exported']}</td>"
                    daily_text += f"<td>{day['samples_split']}</td>"
                    daily_text += f"<td>{day['total_operations']}</td></tr>"
                
                daily_text += "</table>"
                
                daily_label = QLabel(daily_text)
                daily_layout.addWidget(daily_label)
                daily_group.setLayout(daily_layout)
                layout.addWidget(daily_group)
            
            # 按钮
            button_layout = QHBoxLayout()
            
            export_btn = QPushButton('导出报告')
            export_btn.clicked.connect(lambda: self._export_usage_report(tracker))
            button_layout.addWidget(export_btn)
            
            button_layout.addStretch()
            
            close_btn = QPushButton('关闭')
            close_btn.clicked.connect(dialog.close)
            button_layout.addWidget(close_btn)
            
            layout.addLayout(button_layout)
            
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.warning(self, '错误', f'无法获取使用统计:\n{e}')
            import traceback
            traceback.print_exc()
    
    def _export_usage_report(self, tracker):
        """导出使用报告"""
        default_name = f'usage_report_{datetime.now().strftime("%Y%m%d")}.enc'
        filename, _ = QFileDialog.getSaveFileName(
            self, '导出使用报告', 
            default_name,
            '加密报告 (*.enc);;所有文件 (*.*)'
        )
        
        if filename:
            try:
                tracker.export_usage_report(filename, days=30)
                QMessageBox.information(self, '成功', f'使用报告已导出:\n{filename}')
            except Exception as e:
                QMessageBox.warning(self, '错误', f'导出失败:\n{e}')
    
    def show_about(self):
        """显示关于"""
        about_text = """
        <h2>DESI空间代谢组学分析系统 V2</h2>
        <p><b>版本:</b> 2.5 终极完整版</p>
        <p><b>特点:</b> 所有功能完全实现，无"开发中"提示</p>
        <p><b>功能:</b></p>
        <ul>
            <li>[成功] Waters Imaging数据加载</li>
            <li>[成功] 离子信息表（100行）</li>
            <li>[成功] 代谢物数据库查询</li>
            <li>[成功] 多离子对比（2-4个离子）</li>
            <li>[成功] ROI交互式选择（矩形/多边形）</li>
            <li>[成功] ROI分析和导出</li>
            <li>[成功] PDF/Excel报告生成</li>
            <li>[成功] Lock Mass质量校准</li>
            <li>[成功] 代谢物数据拆分（单样本/批量）</li>
        </ul>
        <p><b>开发日期:</b> 2025-10-26</p>
        """
        
        QMessageBox.about(self, '关于', about_text)
    def show_license_info(self):
        """显示许可证信息"""
        info = self.license_integration.get_license_info()
        
        message = "<h3>许可证信息</h3>"
        message += "<table>"
        message += f"<tr><td><b>许可证密钥:</b></td><td style='font-family:monospace'>{info['license_key']}</td></tr>"
        
        if info['expires_at']:
            message += f"<tr><td><b>到期时间:</b></td><td>{info['expires_at'][:10]}</td></tr>"
            if info['days_left'] is not None:
                if info['days_left'] >= 0:
                    color = 'green' if info['days_left'] > 30 else ('orange' if info['days_left'] > 7 else 'red')
                    message += f"<tr><td><b>剩余天数:</b></td><td><font color='{color}'>{info['days_left']} 天</font></td></tr>"
                else:
                    message += f"<tr><td><b>已过期:</b></td><td><font color='red'>{abs(info['days_left'])} 天</font></td></tr>"
        else:
            message += "<tr><td><b>到期时间:</b></td><td>无限期</td></tr>"
        
        status_color = 'green' if info['is_valid'] else 'red'
        status_text = '有效' if info['is_valid'] else '无效'
        message += f"<tr><td><b>状态:</b></td><td><font color='{status_color}'>{status_text}</font></td></tr>"
        message += "</table>"
        
        if info['features_restricted']:
            message += "<br><font color='red'><b>[警告] 功能已受限</b></font><br>"
            message += "请联系管理员续费以恢复所有功能。"
        
        QMessageBox.information(self, "许可证信息", message)
    
    def update_license(self):
        """更新许可证"""
        from license_validation_dialog import LicenseUpdateDialog
        
        dialog = LicenseUpdateDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # 重新检查License
            is_valid, message, days_left = self.license_integration.check_license_on_startup()
            
            if is_valid:
                QMessageBox.information(
                    self, "成功",
                    "License已更新！\n\n"
                    "所有功能已恢复。\n"
                    "建议重启软件以确保所有功能正常。"
                )
            else:
                QMessageBox.warning(
                    self, "警告",
                    f"License验证失败:\n{message}"
                )


def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()


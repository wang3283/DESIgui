#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多样本对比功能
实现不同样本之间的质谱成像对比（如：高浓度 vs 低浓度）
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                            QLabel, QListWidget, QPushButton, QDoubleSpinBox,
                            QComboBox, QCheckBox, QSplitter, QWidget,
                            QAbstractItemView, QMessageBox, QLineEdit, QFileDialog)
from PyQt5.QtCore import Qt
from pathlib import Path
import pandas as pd

# ROI tools removed during cleanup


class SampleComparisonCanvas(FigureCanvas):
    """多样本对比画布"""
    
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(12, 8), facecolor='white')
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.samples_data = []  # [(sample_name, data), ...]
        self.current_mz = None
        self.colormap = 'hot'
        self.layout_mode = 'horizontal'  # horizontal or vertical
        
        # ROI相关 - 每个样本独立的ROI
        self.sample_rois = {}  # {sample_name: [roi1, roi2, ...]}
        self.roi_patches = {}  # {sample_name: [patch1, patch2, ...]}
        self.roi_mode = None  # 'rectangle' or None
        self.roi_start = None
        self.current_roi_patch = None
        self.roi_counters = {}  # {sample_name: counter}
        self.current_sample = None  # 当前选择的样本用于绘制ROI
        self.sample_axes = {}  # {sample_name: ax}
        
        # 连接鼠标事件
        self.mpl_connect('button_press_event', self.on_mouse_press)
        self.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.mpl_connect('button_release_event', self.on_mouse_release)
        
        # ROI更新回调
        self.roi_updated_callback = None
    
    def get_short_name(self, sample_name):
        """提取样本的简短名称"""
        if 'sample' in sample_name.lower():
            parts = sample_name.split('_')
            sample_num = next((p for p in parts if 'sample' in p.lower()), '')
            mode = next((p for p in parts if p in ['POS', 'NEG']), '')
            if sample_num and mode:
                return f"{sample_num}_{mode}"
        return sample_name[:30] + '...' if len(sample_name) > 30 else sample_name
    
    def update_comparison(self, samples_data, mz_target, layout_mode='horizontal', colormap='hot', normalize=False):
        """
        更新多样本对比显示
        
        Parameters:
        -----------
        samples_data : list
            [(sample_name, data), ...] 样本数据列表
        mz_target : float
            目标m/z值
        layout_mode : str
            布局模式：'horizontal'（横向）或 'vertical'（纵向）
        colormap : str
            色彩方案
        normalize : bool
            是否使用归一化显示（所有样本使用相同的颜色范围）
        """
        self.samples_data = samples_data
        self.current_mz = mz_target
        self.layout_mode = layout_mode
        self.colormap = colormap
        
        self.fig.clear()
        self.sample_axes = {}  # 重置样本axes映射
        
        # 初始化每个样本的ROI列表和计数器
        for sample_name, _ in samples_data:
            if sample_name not in self.sample_rois:
                self.sample_rois[sample_name] = []
                self.roi_counters[sample_name] = 0
                self.roi_patches[sample_name] = []
        
        if not samples_data or len(samples_data) == 0:
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, '请选择要对比的样本',
                   ha='center', va='center', fontsize=14)
            ax.axis('off')
            self.draw()
            return
        
        n_samples = len(samples_data)
        
        # 确定布局
        if layout_mode == 'horizontal':
            nrows, ncols = 1, n_samples
            figsize = (4 * n_samples, 4)
        else:  # vertical
            nrows, ncols = n_samples, 1
            figsize = (6, 4 * n_samples)
        
        # 如果需要归一化，先计算全局强度范围
        global_vmin, global_vmax = None, None
        if normalize:
            print("\n" + "="*60)
            print("🎨 归一化模式：计算全局颜色范围...")
            sample_maxs = []
            
            for sample_name, data in samples_data:
                mz_bins = data['mz_bins']
                mz_index = np.argmin(np.abs(mz_bins - mz_target))
                intensity_map = data['intensity_matrix'][:, mz_index]
                
                # 计算每个样本的统计信息
                sample_min = np.min(intensity_map)  # 包含零值
                sample_max = np.max(intensity_map)
                nonzero_count = np.count_nonzero(intensity_map)
                total_count = len(intensity_map)
                
                print(f"  [{self.get_short_name(sample_name)}] 强度范围: [{sample_min:.2f}, {sample_max:.2f}] "
                      f"({nonzero_count}/{total_count}个非零点)")
                sample_maxs.append(sample_max)
            
            if sample_maxs:
                # 质谱强度不会是负数，vmin设为0是合理的
                global_vmin = 0
                global_vmax = max(sample_maxs)
                print(f"  [成功] 全局颜色范围: [0, {global_vmax:.2f}]")
                print(f"  [STATS] 所有样本将使用此颜色范围，便于直接比较")
                print(f"  [提示] vmin=0确保背景（零值）正确显示为最低颜色")
            else:
                print("  [警告] 未找到有效数据，将使用独立范围")
            print("="*60)
        
        # 为每个样本创建子图
        for idx, (sample_name, data) in enumerate(samples_data):
            ax = self.fig.add_subplot(nrows, ncols, idx + 1)
            self.sample_axes[sample_name] = ax  # 记录样本对应的axes
            
            # 查找最接近的m/z
            mz_bins = data['mz_bins']
            mz_index = np.argmin(np.abs(mz_bins - mz_target))
            actual_mz = mz_bins[mz_index]
            
            # 提取离子分布
            intensity_map = data['intensity_matrix'][:, mz_index]
            coords = data['coords']
            
            print(f"\n{'='*60}")
            print(f"[SEARCH] [{sample_name}] 图像重建调试:")
            print(f"   coords类型: {type(coords)}")
            print(f"   coords形状: {coords.shape if isinstance(coords, np.ndarray) else 'N/A'}")
            print(f"   intensity_map形状: {intensity_map.shape}")
            
            # 重建2D图像 - 使用与主GUI完全相同的方法
            try:
                # 获取唯一的x和y坐标
                x_unique = np.unique(coords[:, 0])
                y_unique = np.unique(coords[:, 1])
                
                print(f"   X: {len(x_unique)}个唯一值, 范围={x_unique.min():.1f}~{x_unique.max():.1f}")
                print(f"   Y: {len(y_unique)}个唯一值, 范围={y_unique.min():.1f}~{y_unique.max():.1f}")
                
                # 创建网格
                img = np.zeros((len(y_unique), len(x_unique)))
                
                # 创建像素坐标数组（用于ROI分析）
                pixel_coords = np.zeros((len(coords), 2))
                
                # 填充图像 - 与main_gui_ultimate.py完全相同的方法
                for i, (x, y) in enumerate(coords):
                    xi = np.where(x_unique == x)[0][0]
                    yi = np.where(y_unique == y)[0][0]
                    img[yi, xi] = intensity_map[i]
                    # 存储像素坐标（用于ROI分析）
                    pixel_coords[i] = [xi, yi]
                
                # 更新data中的coords为像素坐标
                data['coords'] = pixel_coords
                data['x_unique'] = x_unique
                data['y_unique'] = y_unique
                
                print(f"  [成功] 正确重建图像: {img.shape}, 非零像素: {np.count_nonzero(img)}/{img.size}")
                print(f"  [STATS] 像素坐标范围: X[0, {len(x_unique)-1}] Y[0, {len(y_unique)-1}]")
                    
            except Exception as e:
                print(f"  [警告] 重建图像失败: {e}")
                import traceback
                traceback.print_exc()
                # 使用简单reshape作为后备方案
                side_length = int(np.sqrt(len(intensity_map)))
                if side_length > 0 and side_length * side_length <= len(intensity_map):
                    img = intensity_map[:side_length**2].reshape(side_length, side_length)
                    print(f"  使用reshape后备方案: {img.shape}")
                else:
                    img = np.zeros((10, 10))
                    print(f"  使用空白图像")
            
            # 显示图像 - 使用像素坐标（与主GUI一致）
            # 如果启用归一化，使用全局vmin/vmax；否则自动范围
            imshow_kwargs = {
                'cmap': self.colormap,
                'aspect': 'auto',
                'origin': 'lower'
            }
            if normalize and global_vmin is not None and global_vmax is not None:
                imshow_kwargs['vmin'] = global_vmin
                imshow_kwargs['vmax'] = global_vmax
            
            im = ax.imshow(img, **imshow_kwargs)
            
            # 设置标题（包含样本名称和实际m/z）
            short_name = self.get_short_name(sample_name)
            ax.set_title(f'{short_name}\nm/z {actual_mz:.4f}', fontsize=10, fontweight='bold')
            
            # 添加色标
            cbar = self.fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label('Intensity', fontsize=8)
            
            # 设置坐标轴标签（物理坐标范围作为参考）
            ax.set_xlabel(f'X Position (像素, {x_unique.min():.1f}~{x_unique.max():.1f} mm)', fontsize=8)
            ax.set_ylabel(f'Y Position (像素, {y_unique.min():.1f}~{y_unique.max():.1f} mm)', fontsize=8)
        
        self.fig.tight_layout()
        
        # 重绘已存在的ROI
        self.redraw_rois()
        
        self.draw()
    
    def start_roi_selection(self, roi_type):
        """开始ROI选择 - 直接模式"""
        self.roi_mode = roi_type
        self.current_sample = None  # 将在鼠标点击时自动检测
        print(f"[MOUSE]  {roi_type}模式：在任意样本图上拖拽选择区域")
    
    def clear_rois(self, sample_name=None):
        """清除ROI
        
        Parameters:
        -----------
        sample_name : str or None
            如果指定样本名，只清除该样本的ROI；如果为None，清除所有样本的ROI
        """
        if sample_name:
            # 清除指定样本的ROI
            if sample_name in self.sample_rois:
                self.sample_rois[sample_name] = []
                self.roi_patches[sample_name] = []
                print(f"[成功] 已清除 [{sample_name}] 的所有ROI")
        else:
            # 清除所有样本的ROI
            self.sample_rois = {}
            self.roi_patches = {}
            self.roi_counters = {}
            print("[成功] 已清除所有样本的ROI")
        
        self.roi_mode = None
        
        # 重新绘制图形
        if self.samples_data:
            for ax in self.fig.axes:
                # 移除ROI patches
                for patch in list(ax.patches):
                    patch.remove()
            self.redraw_rois()
            self.draw()
    
    def redraw_rois(self):
        """在每个子图上绘制该样本的ROI"""
        if not self.sample_rois:
            return
        
        # 清除旧的patches
        for sample_name in self.roi_patches:
            self.roi_patches[sample_name] = []
        
        # 为每个样本绘制其自己的ROI
        for sample_name, rois in self.sample_rois.items():
            if sample_name not in self.sample_axes:
                continue
            
            ax = self.sample_axes[sample_name]
            
            for roi in rois:
                if roi.roi_type == 'rectangle':
                    x1, y1, x2, y2 = roi.coords
                    width = x2 - x1
                    height = y2 - y1
                    
                    rect = Rectangle(
                        (x1, y1), width, height,
                        fill=False, edgecolor='yellow', linewidth=2,
                        linestyle='--'
                    )
                    ax.add_patch(rect)
                    self.roi_patches[sample_name].append(rect)
                    
                    # 添加标签
                    ax.text(x1, y1, roi.name, 
                           color='yellow', fontsize=8,
                           bbox=dict(boxstyle='round,pad=0.3', 
                                   facecolor='black', alpha=0.7))
    
    def on_mouse_press(self, event):
        """鼠标按下事件 - 自动检测在哪个样本上"""
        if not self.roi_mode or not event.inaxes:
            return
        
        # 自动检测点击在哪个样本的axes上
        clicked_sample = None
        for sample_name, ax in self.sample_axes.items():
            if event.inaxes == ax:
                clicked_sample = sample_name
                break
        
        if not clicked_sample:
            print("[警告]  请在样本图上点击")
            return
        
        # 设置当前操作的样本
        self.current_sample = clicked_sample
        self.roi_start = (event.xdata, event.ydata)
        
        # 提取简短名称用于显示
        short_name = self.get_short_name(clicked_sample)
        print(f"📍 [{short_name}] ROI起点: ({event.xdata:.1f}, {event.ydata:.1f})")
    
    def on_mouse_move(self, event):
        """鼠标移动事件"""
        if not self.roi_mode or not self.roi_start or not event.inaxes:
            return
        
        # 移除临时ROI patch
        if self.current_roi_patch:
            self.current_roi_patch.remove()
        
        # 绘制临时ROI矩形
        x1, y1 = self.roi_start
        x2, y2 = event.xdata, event.ydata
        width = x2 - x1
        height = y2 - y1
        
        self.current_roi_patch = Rectangle(
            (x1, y1), width, height,
            fill=False, edgecolor='yellow', linewidth=2,
            linestyle='--', alpha=0.7
        )
        event.inaxes.add_patch(self.current_roi_patch)
        self.draw()
    
    def on_mouse_release(self, event):
        """鼠标释放事件"""
        if not self.roi_mode or not self.roi_start or not event.inaxes or not self.current_sample:
            return
        
        # 检查是否在当前样本的axes上释放
        if event.inaxes != self.sample_axes.get(self.current_sample):
            self.roi_start = None
            if self.current_roi_patch:
                self.current_roi_patch.remove()
                self.current_roi_patch = None
            self.draw()
            return
        
        # 移除临时patch
        if self.current_roi_patch:
            self.current_roi_patch.remove()
            self.current_roi_patch = None
        
        x1, y1 = self.roi_start
        x2, y2 = event.xdata, event.ydata
        
        # 创建ROI（为当前样本）
        if self.current_sample not in self.roi_counters:
            self.roi_counters[self.current_sample] = 0
        
        self.roi_counters[self.current_sample] += 1
        
        # 使用简短名称作为ROI名称的一部分
        short_name = self.get_short_name(self.current_sample)
        roi_name = f"{short_name}_ROI_{self.roi_counters[self.current_sample]}"
        
        roi = ROI(
            name=roi_name,
            roi_type=self.roi_mode,
            coords=(x1, y1, x2, y2)
        )
        
        # 添加到该样本的ROI列表
        if self.current_sample not in self.sample_rois:
            self.sample_rois[self.current_sample] = []
        self.sample_rois[self.current_sample].append(roi)
        
        print(f"\n[EDIT]  [{short_name}] 创建ROI: {roi_name}")
        print(f"   坐标: X[{x1:.1f}, {x2:.1f}] Y[{y1:.1f}, {y2:.1f}]")
        
        # 重绘ROI
        self.redraw_rois()
        self.draw()
        
        # 重置ROI模式（继续绘制）
        self.roi_start = None
        # 不重置roi_mode，允许连续绘制
        
        print(f"[成功] [{short_name}] 创建ROI: {roi_name}")
        
        # 调用回调通知Dialog更新统计
        if self.roi_updated_callback:
            self.roi_updated_callback()


class SampleComparisonDialog(QDialog):
    """多样本对比对话框"""
    
    def __init__(self, parent=None, loader=None, workspace=None, lock_mass_manager=None):
        super().__init__(parent)
        
        self.loader = loader
        self.workspace = workspace
        self.lock_mass_manager = lock_mass_manager  # Lock Mass管理器
        self.selected_samples = []
        self.loaded_data = {}  # {sample_path: data}
        
        self.setWindowTitle('多样本质谱成像对比')
        self.setGeometry(100, 100, 1400, 900)
        
        self.init_ui()
        
        # 如果提供了workspace，加载样本列表
        if self.workspace and self.loader:
            self.load_sample_list()
    
    def init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        
        # 左侧：控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 样本选择
        sample_group = QGroupBox('样本选择')
        sample_layout = QVBoxLayout()
        
        sample_layout.addWidget(QLabel('可用样本：'))
        self.sample_list = QListWidget()
        self.sample_list.setSelectionMode(QAbstractItemView.MultiSelection)
        sample_layout.addWidget(self.sample_list)
        
        load_btn = QPushButton('[RECEIVE] 加载选中样本')
        load_btn.clicked.connect(self.load_selected_samples)
        sample_layout.addWidget(load_btn)
        
        sample_layout.addWidget(QLabel('已加载样本：'))
        self.loaded_list = QListWidget()
        sample_layout.addWidget(self.loaded_list)
        
        sample_group.setLayout(sample_layout)
        left_layout.addWidget(sample_group)
        
        # m/z选择
        mz_group = QGroupBox('m/z选择')
        mz_layout = QVBoxLayout()
        
        mz_layout.addWidget(QLabel('目标m/z:'))
        self.mz_input = QDoubleSpinBox()
        self.mz_input.setRange(0, 2000)
        self.mz_input.setDecimals(4)
        self.mz_input.setValue(255.2327)
        mz_layout.addWidget(self.mz_input)
        
        mz_group.setLayout(mz_layout)
        left_layout.addWidget(mz_group)
        
        # 显示选项
        display_group = QGroupBox('显示选项')
        display_layout = QVBoxLayout()
        
        display_layout.addWidget(QLabel('布局模式:'))
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(['横向排列', '纵向排列'])
        display_layout.addWidget(self.layout_combo)
        
        display_layout.addWidget(QLabel('色彩方案:'))
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(['hot', 'viridis', 'plasma', 'inferno', 
                                      'magma', 'jet', 'rainbow', 'coolwarm'])
        display_layout.addWidget(self.colormap_combo)
        
        self.normalize_check = QCheckBox('归一化显示')
        self.normalize_check.setChecked(False)
        display_layout.addWidget(self.normalize_check)
        
        display_group.setLayout(display_layout)
        left_layout.addWidget(display_group)
        
        # ROI控制 - 直接在图上操作
        roi_group = QGroupBox('[TARGET] ROI管理（直接在图上操作）')
        roi_layout = QVBoxLayout()
        
        # 使用说明
        instruction_label = QLabel('[提示] 直接在任意样本图上拖动绘制ROI')
        instruction_label.setWordWrap(True)
        instruction_label.setStyleSheet('QLabel { color: #666; font-style: italic; }')
        roi_layout.addWidget(instruction_label)
        
        # ROI操作按钮
        rect_roi_btn = QPushButton('📐 添加ROI（点击后在图上拖动）')
        rect_roi_btn.clicked.connect(self.start_roi_direct_mode)
        rect_roi_btn.setStyleSheet('QPushButton { font-size: 12px; padding: 8px; }')
        roi_layout.addWidget(rect_roi_btn)
        
        # ROI统计信息
        roi_layout.addWidget(QLabel('━━━━━━━━━━━'))
        self.roi_stats_label = QLabel('所有样本的ROI: 0个')
        roi_layout.addWidget(self.roi_stats_label)
        
        # 全局操作
        roi_layout.addWidget(QLabel('━━━━━━━━━━━'))
        analyze_roi_btn = QPushButton('[STATS] 跨样本ROI分析')
        analyze_roi_btn.clicked.connect(self.analyze_rois)
        roi_layout.addWidget(analyze_roi_btn)
        
        export_roi_btn = QPushButton('[SAVE] 导出ROI数据')
        export_roi_btn.clicked.connect(self.export_roi_data)
        roi_layout.addWidget(export_roi_btn)
        
        clear_all_btn = QPushButton('[DELETE] 清除所有ROI')
        clear_all_btn.clicked.connect(self.clear_all_rois)
        roi_layout.addWidget(clear_all_btn)
        
        roi_group.setLayout(roi_layout)
        left_layout.addWidget(roi_group)
        
        # 对比按钮
        compare_btn = QPushButton('[SEARCH] 生成对比图')
        compare_btn.clicked.connect(self.generate_comparison)
        compare_btn.setStyleSheet('QPushButton { font-size: 14px; padding: 10px; }')
        left_layout.addWidget(compare_btn)
        
        # 导出按钮
        export_btn = QPushButton('[SAVE] 导出对比图')
        export_btn.clicked.connect(self.export_comparison)
        left_layout.addWidget(export_btn)
        
        left_layout.addStretch()
        
        layout.addWidget(left_panel, 1)
        
        # 右侧：对比显示区域
        self.comparison_canvas = SampleComparisonCanvas(self)
        self.comparison_canvas.roi_updated_callback = self.on_canvas_roi_updated
        layout.addWidget(self.comparison_canvas, 3)
    
    def load_sample_list(self):
        """加载样本列表"""
        try:
            samples = self.loader.find_samples(self.workspace)
            
            self.sample_list.clear()
            for sample in samples:
                self.sample_list.addItem(sample.name)
            
            print(f"找到 {len(samples)} 个可用样本")
        except Exception as e:
            print(f"加载样本列表失败: {e}")
    
    def load_selected_samples(self):
        """加载选中的样本"""
        selected_items = self.sample_list.selectedItems()
        
        if len(selected_items) == 0:
            QMessageBox.warning(self, '警告', '请至少选择一个样本')
            return
        
        if len(selected_items) > 6:
            QMessageBox.warning(self, '警告', '最多只能同时对比6个样本')
            return
        
        # 加载数据
        for item in selected_items:
            sample_name = item.text()
            
            # 如果已经加载过，跳过
            if sample_name in self.loaded_data:
                continue
            
            try:
                # 查找样本路径
                samples = self.loader.find_samples(self.workspace)
                sample_path = None
                for s in samples:
                    if s.name == sample_name:
                        sample_path = s
                        break
                
                if sample_path:
                    print(f"正在加载样本: {sample_name}...")
                    data = self.loader.load(sample_path)
                    
                    if data:
                        # 应用Lock Mass校准（如果启用）
                        if self.lock_mass_manager and self.lock_mass_manager.config.enabled:
                            try:
                                from calibrated_data_handler import CalibratedDataHandler
                                handler = CalibratedDataHandler(self.lock_mass_manager)
                                calibrated_data = handler.process_sample(data)
                                
                                if calibrated_data.get('calibration_info', {}).get('calibrated'):
                                    data = calibrated_data
                                    print(f"  [成功] Lock Mass校准已应用")
                                else:
                                    print(f"  [警告] Lock Mass校准失败，使用原始数据")
                            except Exception as e:
                                print(f"  [警告] 校准出错: {e}，使用原始数据")
                        
                        self.loaded_data[sample_name] = data
                        self.loaded_list.addItem(f"[成功] {sample_name}")
                        print(f"  加载成功: {data['n_scans']} 扫描, {len(data['mz_bins'])} m/z bins")
                    else:
                        print(f"  加载失败")
                
            except Exception as e:
                print(f"加载 {sample_name} 失败: {e}")
                QMessageBox.warning(self, '错误', f'加载样本失败：{str(e)}')
        
        print(f"已加载 {len(self.loaded_data)} 个样本")
    
    def generate_comparison(self):
        """生成对比图"""
        if len(self.loaded_data) == 0:
            QMessageBox.warning(self, '警告', '请先加载样本数据')
            return
        
        # 获取参数
        mz_target = self.mz_input.value()
        layout_mode = 'horizontal' if self.layout_combo.currentText() == '横向排列' else 'vertical'
        colormap = self.colormap_combo.currentText()
        normalize = self.normalize_check.isChecked()  # 获取归一化状态
        
        # 准备样本数据
        samples_data = [(name, data) for name, data in self.loaded_data.items()]
        
        # 更新显示
        self.comparison_canvas.update_comparison(samples_data, mz_target, layout_mode, colormap, normalize)
        
        # 更新ROI统计
        self.update_roi_stats()
        
        print(f"生成对比图: {len(samples_data)} 个样本, m/z={mz_target:.4f}")
    
    def update_roi_stats(self):
        """更新ROI统计信息"""
        total_rois = sum(len(rois) for rois in self.comparison_canvas.sample_rois.values())
        self.roi_stats_label.setText(f'所有样本的ROI: {total_rois}个')
    
    def on_canvas_roi_updated(self):
        """Canvas中ROI更新时的回调"""
        self.update_roi_stats()
    
    def start_roi_direct_mode(self):
        """启动直接ROI绘制模式"""
        if len(self.loaded_data) == 0:
            QMessageBox.warning(self, '警告', '请先生成对比图')
            return
        
        # 启动ROI选择模式
        self.comparison_canvas.start_roi_selection('rectangle')
        
        # 显示提示信息
        QMessageBox.information(
            self, '提示',
            '[成功] ROI绘制模式已启动！\n\n'
            '📍 请直接在任意样本图上拖动鼠标绘制ROI\n'
            '[TARGET] 系统会自动识别您在哪个样本上操作\n'
            '[RECYCLE]  可以连续绘制多个ROI\n\n'
            '控制台会显示详细信息'
        )
        
        print("\n[提示] ROI绘制模式已启动")
        print("   直接在任意样本图上拖动鼠标即可绘制ROI")
        print("   ROI会自动添加到对应的样本")
    
    def clear_all_rois(self):
        """清除所有样本的ROI"""
        reply = QMessageBox.question(
            self, '确认',
            '确定要清除所有样本的ROI吗？',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.comparison_canvas.clear_rois(None)  # None表示清除所有
            self.update_roi_stats()
    
    def analyze_rois(self):
        """分析每个样本的ROI数据"""
        try:
            print("[SEARCH] 开始ROI分析...")
            
            if len(self.loaded_data) == 0:
                QMessageBox.warning(self, '警告', '请先生成对比图')
                return
            
            # 检查是否有任何ROI
            total_rois = sum(len(rois) for rois in self.comparison_canvas.sample_rois.values())
            print(f"[STATS] 总ROI数: {total_rois}")
            
            if total_rois == 0:
                QMessageBox.warning(self, '警告', '请先为样本添加ROI')
                return
            
            # 创建ROI分析器
            analyzer = ROIAnalyzer()
            mz_target = self.mz_input.value()
            
            results_text = f"[STATS] ROI分析结果 (m/z {mz_target:.4f}):\n\n"
            
            # 为每个样本分析其ROI
            for sample_name, rois in self.comparison_canvas.sample_rois.items():
                if not rois:
                    continue
                
                print(f"[FOLDER] 分析样本: {sample_name}, ROI数: {len(rois)}")
                
                results_text += f"{'='*60}\n"
                results_text += f"[FOLDER] 样本: {sample_name}\n"
                results_text += f"{'='*60}\n\n"
                
                # 获取样本数据
                if sample_name not in self.loaded_data:
                    print(f"[警告]  样本数据未加载: {sample_name}")
                    continue
                
                data = self.loaded_data[sample_name]
                mz_bins = data['mz_bins']
                mz_index = np.argmin(np.abs(mz_bins - mz_target))
                actual_mz = mz_bins[mz_index]
                coords = data['coords']
                intensity_map = data['intensity_matrix'][:, mz_index]
                
                # 获取物理坐标映射（用于显示）
                x_unique_coords = data.get('x_unique', None)
                y_unique_coords = data.get('y_unique', None)
                
                # 分析该样本的每个ROI
                for roi in rois:
                    print(f"  [TARGET] 分析ROI: {roi.name}")
                    results_text += f"[TARGET] {roi.name}:\n"
                    results_text += f"  🔬 实际m/z: {actual_mz:.4f}\n"
                    
                    try:
                        # ROI坐标（像素坐标系）
                        x1, y1, x2, y2 = roi.coords
                        roi_width = abs(x2 - x1)
                        roi_height = abs(y2 - y1)
                        roi_area = roi_width * roi_height
                        
                        # 转换为物理坐标（用于显示）
                        if x_unique_coords is not None and y_unique_coords is not None:
                            try:
                                x1_phys = x_unique_coords[int(min(x1, x2))]
                                x2_phys = x_unique_coords[min(int(max(x1, x2)), len(x_unique_coords)-1)]
                                y1_phys = y_unique_coords[int(min(y1, y2))]
                                y2_phys = y_unique_coords[min(int(max(y1, y2)), len(y_unique_coords)-1)]
                                physical_info = f"  📍 物理坐标: X[{x1_phys:.1f}, {x2_phys:.1f}] Y[{y1_phys:.1f}, {y2_phys:.1f}] mm\n"
                            except:
                                physical_info = ""
                        else:
                            physical_info = ""
                        
                        # 使用ROIAnalyzer分析ROI区域
                        # 正确的方法签名：analyze_roi(roi, data, mz_index)
                        stats = analyzer.analyze_roi(roi, data, mz_index)
                        
                        if stats and stats['n_points'] > 0:
                            # 计算信号密度（总信号/面积）
                            signal_density = stats['sum'] / roi_area if roi_area > 0 else 0
                            
                            results_text += f"  📍 数据点数: {stats['n_points']}\n"
                            results_text += f"  📏 ROI尺寸（像素）: {roi_width:.1f} × {roi_height:.1f} = {roi_area:.1f} 像素²\n"
                            results_text += physical_info
                            results_text += f"  [TREND] 平均强度: {stats['mean']:.2f}\n"
                            results_text += f"  [STATS] 中位数强度: {stats['median']:.2f}\n"
                            results_text += f"  [UP]  最大强度: {stats['max']:.2f}\n"
                            results_text += f"  [DOWN]  最小强度: {stats['min']:.2f}\n"
                            results_text += f"  📐 标准差: {stats['std']:.2f}\n"
                            results_text += f"  ∑  总强度: {stats['sum']:.2f}\n"
                            results_text += f"  [TARGET] 信号密度: {signal_density:.2f} (强度/像素²)\n"
                        else:
                            results_text += f"  📏 ROI尺寸（像素）: {roi_width:.1f} × {roi_height:.1f} = {roi_area:.1f} 像素²\n"
                            results_text += physical_info
                            results_text += f"  [警告]  ROI区域内无数据点\n"
                    except Exception as roi_error:
                        print(f"[错误] ROI分析错误 ({roi.name}): {roi_error}")
                        import traceback
                        traceback.print_exc()
                        results_text += f"  [错误] 分析错误: {str(roi_error)}\n"
                    
                    results_text += "\n"
                
                results_text += "\n"
            
            print("[成功] ROI分析完成，准备显示结果...")
            
            # 显示完整结果对话框
            from PyQt5.QtWidgets import QTextEdit, QVBoxLayout, QPushButton
            
            print("[NOTE] 创建结果对话框...")
            
            # 创建自定义对话框
            dialog = QDialog(self)
            dialog.setWindowTitle('ROI分析结果')
            dialog.setMinimumSize(750, 550)
            
            layout = QVBoxLayout(dialog)
            
            # 添加文本显示
            text_edit = QTextEdit()
            text_edit.setPlainText(results_text)
            text_edit.setReadOnly(True)
            layout.addWidget(text_edit)
            
            # 添加关闭按钮
            close_btn = QPushButton('关闭')
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)
            
            print("[LAUNCH] 显示对话框...")
            dialog.exec_()
            print("[成功] 对话框已关闭")
            
        except Exception as e:
            print(f"[错误] analyze_rois 严重错误: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, '错误', f'ROI分析错误：{str(e)}\n\n请查看控制台获取详细信息。')
    
    def export_roi_data(self):
        """导出每个样本的ROI数据"""
        try:
            # 检查是否有任何ROI
            total_rois = sum(len(rois) for rois in self.comparison_canvas.sample_rois.values())
            if total_rois == 0:
                QMessageBox.warning(self, '警告', '请先为样本添加ROI')
                return
            
            print("[FOLDER] 准备导出ROI数据...")
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                '导出ROI数据',
                f'roi_per_sample_mz_{self.mz_input.value():.4f}.xlsx',
                'Excel Files (*.xlsx);;CSV Files (*.csv)'
            )
            
            print(f"选择的文件名: {filename}")
        except Exception as e:
            print(f"[错误] 文件对话框错误: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, '错误', f'文件对话框错误：{str(e)}')
            return
        
        if filename:
            try:
                print(f"[STATS] 开始导出ROI数据到: {filename}")
                
                # 创建ROI分析器
                analyzer = ROIAnalyzer()
                mz_target = self.mz_input.value()
                
                # 创建数据表
                data_list = []
                
                # 为每个样本导出其ROI数据
                for sample_name, rois in self.comparison_canvas.sample_rois.items():
                    if not rois or sample_name not in self.loaded_data:
                        continue
                    
                    print(f"  [FOLDER] 导出样本: {sample_name}, ROI数: {len(rois)}")
                    
                    data = self.loaded_data[sample_name]
                    mz_bins = data['mz_bins']
                    mz_index = np.argmin(np.abs(mz_bins - mz_target))
                    actual_mz = mz_bins[mz_index]
                    coords = data['coords']
                    intensity_map = data['intensity_matrix'][:, mz_index]
                    
                    # 获取物理坐标映射（用于导出）
                    x_unique_coords = data.get('x_unique', None)
                    y_unique_coords = data.get('y_unique', None)
                    
                    for roi in rois:
                        # 计算ROI面积（像素坐标系）
                        x1, y1, x2, y2 = roi.coords
                        roi_width = abs(x2 - x1)
                        roi_height = abs(y2 - y1)
                        roi_area = roi_width * roi_height
                        
                        # 使用ROIAnalyzer分析ROI区域
                        # 正确的方法签名：analyze_roi(roi, data, mz_index)
                        stats = analyzer.analyze_roi(roi, data, mz_index)
                        
                        # 计算物理坐标（如果可用）
                        if x_unique_coords is not None and y_unique_coords is not None:
                            try:
                                x1_phys = x_unique_coords[int(min(x1, x2))]
                                x2_phys = x_unique_coords[min(int(max(x1, x2)), len(x_unique_coords)-1)]
                                y1_phys = y_unique_coords[int(min(y1, y2))]
                                y2_phys = y_unique_coords[min(int(max(y1, y2)), len(y_unique_coords)-1)]
                            except:
                                x1_phys = x2_phys = y1_phys = y2_phys = 0
                        else:
                            x1_phys = x2_phys = y1_phys = y2_phys = 0
                        
                        row_data = {
                            'Sample': sample_name,
                            'ROI': roi.name,
                            'm/z_target': mz_target,
                            'm/z_actual': actual_mz,
                            'X_min_pixel': min(roi.coords[0], roi.coords[2]),
                            'X_max_pixel': max(roi.coords[0], roi.coords[2]),
                            'Y_min_pixel': min(roi.coords[1], roi.coords[3]),
                            'Y_max_pixel': max(roi.coords[1], roi.coords[3]),
                            'X_min_mm': x1_phys,
                            'X_max_mm': x2_phys,
                            'Y_min_mm': y1_phys,
                            'Y_max_mm': y2_phys,
                            'ROI_width_pixel': roi_width,
                            'ROI_height_pixel': roi_height,
                            'ROI_area_pixel2': roi_area,
                        }
                        
                        # 添加统计数据
                        if stats and stats['n_points'] > 0:
                            # 计算信号密度（总信号/面积）
                            signal_density = stats['sum'] / roi_area if roi_area > 0 else 0
                            
                            row_data.update({
                                'num_points': stats['n_points'],
                                'mean_intensity': stats['mean'],
                                'median_intensity': stats['median'],
                                'max_intensity': stats['max'],
                                'min_intensity': stats['min'],
                                'std_intensity': stats['std'],
                                'total_intensity': stats['sum'],
                                'signal_density': signal_density,
                            })
                        else:
                            row_data.update({
                                'num_points': 0,
                                'mean_intensity': 0,
                                'median_intensity': 0,
                                'max_intensity': 0,
                                'min_intensity': 0,
                                'std_intensity': 0,
                                'total_intensity': 0,
                                'signal_density': 0,
                            })
                        
                        data_list.append(row_data)
                
                print(f"📋 创建DataFrame，总行数: {len(data_list)}")
                df = pd.DataFrame(data_list)
                
                print(f"[SAVE] 写入文件: {filename}")
                if filename.endswith('.csv'):
                    df.to_csv(filename, index=False)
                else:
                    df.to_excel(filename, index=False, engine='openpyxl')
                
                num_samples = len([s for s in self.comparison_canvas.sample_rois if self.comparison_canvas.sample_rois[s]])
                print(f"[成功] ROI数据已导出: {filename} ({num_samples} 样本, {total_rois} ROIs)")
                
                QMessageBox.information(self, '成功', 
                    f'ROI数据已导出到：\n{filename}\n\n'
                    f'包含 {num_samples} 个样本的 {total_rois} 个ROI的定量数据')
                    
            except Exception as e:
                print(f"[错误] 导出失败: {e}")
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, '错误', f'导出失败：{str(e)}\n\n请查看控制台获取详细信息。')
    
    def export_comparison(self):
        """导出对比图"""
        if len(self.loaded_data) == 0:
            QMessageBox.warning(self, '警告', '请先生成对比图')
            return
        
        from PyQt5.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            '保存对比图',
            f'sample_comparison_mz_{self.mz_input.value():.4f}.png',
            'PNG Files (*.png);;PDF Files (*.pdf);;All Files (*)'
        )
        
        if filename:
            try:
                self.comparison_canvas.fig.savefig(filename, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, '成功', f'对比图已保存到：\n{filename}')
                print(f"对比图已导出: {filename}")
            except Exception as e:
                QMessageBox.warning(self, '错误', f'导出失败：{str(e)}')


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    from data_loader import DataLoader
    from pathlib import Path
    
    app = QApplication(sys.argv)
    
    workspace = Path("/Volumes/US100 256G/mouse DESI data")
    loader = DataLoader()
    
    dialog = SampleComparisonDialog(loader=loader, workspace=workspace)
    dialog.show()
    
    sys.exit(app.exec_())
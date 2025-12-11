#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用统计GUI界面
为客户端提供图形化的使用报告展示
"""

import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QGroupBox, QFileDialog, QMessageBox, QWidget, QSplitter
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from usage_tracker import UsageTracker

# matplotlib相关导入
try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    
    # 配置中文字体支持
    import platform
    if platform.system() == 'Darwin':  # macOS
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC', 'PingFang SC']
    elif platform.system() == 'Windows':
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
    else:  # Linux
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'Droid Sans Fallback']
    
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("[警告] 未安装matplotlib，图表功能不可用")


class UsageChartWidget(QWidget):
    """使用量图表组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        if HAS_MATPLOTLIB:
            # 创建matplotlib图表
            self.figure = Figure(figsize=(8, 4))
            self.canvas = FigureCanvas(self.figure)
            layout.addWidget(self.canvas)
        else:
            # 降级显示
            label = QLabel("图表功能需要安装matplotlib库\n请运行: pip install matplotlib")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
    
    def plot_usage_trend(self, daily_stats: List[Dict]):
        """绘制使用趋势图"""
        if not HAS_MATPLOTLIB or not daily_stats:
            return
        
        self.figure.clear()
        
        # 提取数据
        dates = [stat['date'] for stat in daily_stats]
        loads = [stat['samples_loaded'] for stat in daily_stats]
        exports = [stat['samples_exported'] for stat in daily_stats]
        splits = [stat['samples_split'] for stat in daily_stats]
        
        # 创建子图
        ax = self.figure.add_subplot(111)
        
        # 绘制折线图
        ax.plot(dates, loads, marker='o', label='样本加载', linewidth=2)
        ax.plot(dates, exports, marker='s', label='数据导出', linewidth=2)
        ax.plot(dates, splits, marker='^', label='代谢物拆分', linewidth=2)
        
        # 设置标签和标题
        ax.set_xlabel('日期')
        ax.set_ylabel('操作次数')
        ax.set_title('使用量趋势图')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 旋转x轴标签
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def plot_operation_distribution(self, stats: Dict):
        """绘制操作分布饼图"""
        if not HAS_MATPLOTLIB:
            return
        
        self.figure.clear()
        
        # 提取数据
        labels = ['样本加载', '数据导出', '代谢物拆分']
        sizes = [
            stats.get('total_loads', 0),
            stats.get('total_exports', 0),
            stats.get('total_splits', 0)
        ]
        
        # 过滤零值
        filtered_data = [(label, size) for label, size in zip(labels, sizes) if size > 0]
        if not filtered_data:
            return
        
        labels, sizes = zip(*filtered_data)
        
        # 创建饼图
        ax = self.figure.add_subplot(111)
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.set_title('操作类型分布')
        
        self.figure.tight_layout()
        self.canvas.draw()


class UsageStatsDialog(QDialog):
    """使用统计对话框"""
    
    def __init__(self, tracker: UsageTracker = None, parent=None):
        super().__init__(parent)
        self.tracker = tracker or UsageTracker(silent=True)
        self.current_stats = None
        self.init_ui()
        self.load_stats()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("使用统计")
        self.setGeometry(100, 100, 1000, 700)
        
        layout = QVBoxLayout(self)
        
        # 顶部控制栏
        control_layout = QHBoxLayout()
        
        # 时间范围选择
        control_layout.addWidget(QLabel("统计周期:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["最近7天", "最近30天", "最近90天", "全部"])
        self.period_combo.setCurrentIndex(1)  # 默认30天
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        control_layout.addWidget(self.period_combo)
        
        control_layout.addStretch()
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_stats)
        control_layout.addWidget(refresh_btn)
        
        # 导出报告按钮
        export_btn = QPushButton("导出报告")
        export_btn.clicked.connect(self.export_report)
        control_layout.addWidget(export_btn)
        
        layout.addLayout(control_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 统计摘要面板
        summary_group = self.create_summary_panel()
        splitter.addWidget(summary_group)
        
        # 图表面板
        chart_group = self.create_chart_panel()
        splitter.addWidget(chart_group)
        
        # 详细数据表格
        table_group = self.create_table_panel()
        splitter.addWidget(table_group)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 2)
        
        layout.addWidget(splitter)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def create_summary_panel(self) -> QGroupBox:
        """创建统计摘要面板"""
        group = QGroupBox("统计摘要")
        layout = QHBoxLayout(group)
        
        # 创建统计标签
        self.summary_labels = {}
        
        stats_items = [
            ("total_records", "总记录数", "0"),
            ("unique_samples", "唯一样本数", "0"),
            ("total_loads", "加载次数", "0"),
            ("total_exports", "导出次数", "0"),
            ("total_splits", "拆分次数", "0")
        ]
        
        for key, label_text, default_value in stats_items:
            item_layout = QVBoxLayout()
            
            # 数值标签
            value_label = QLabel(default_value)
            value_label.setAlignment(Qt.AlignCenter)
            font = QFont()
            font.setPointSize(18)
            font.setBold(True)
            value_label.setFont(font)
            
            # 描述标签
            desc_label = QLabel(label_text)
            desc_label.setAlignment(Qt.AlignCenter)
            
            item_layout.addWidget(value_label)
            item_layout.addWidget(desc_label)
            
            layout.addLayout(item_layout)
            self.summary_labels[key] = value_label
        
        return group
    
    def create_chart_panel(self) -> QGroupBox:
        """创建图表面板"""
        group = QGroupBox("使用趋势")
        layout = QVBoxLayout(group)
        
        # 图表类型选择
        chart_control = QHBoxLayout()
        chart_control.addWidget(QLabel("图表类型:"))
        
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["趋势图", "分布图"])
        self.chart_type_combo.currentTextChanged.connect(self.on_chart_type_changed)
        chart_control.addWidget(self.chart_type_combo)
        chart_control.addStretch()
        
        layout.addLayout(chart_control)
        
        # 图表组件
        self.chart_widget = UsageChartWidget()
        layout.addWidget(self.chart_widget)
        
        return group
    
    def create_table_panel(self) -> QGroupBox:
        """创建详细数据表格面板"""
        group = QGroupBox("每日详情")
        layout = QVBoxLayout(group)
        
        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "日期", "样本加载", "数据导出", "代谢物拆分", "总操作数"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        
        layout.addWidget(self.table)
        
        return group
    
    def get_period_days(self) -> int:
        """获取选择的统计周期天数"""
        period_text = self.period_combo.currentText()
        period_map = {
            "最近7天": 7,
            "最近30天": 30,
            "最近90天": 90,
            "全部": 365 * 10  # 10年
        }
        return period_map.get(period_text, 30)
    
    def load_stats(self):
        """加载统计数据"""
        try:
            days = self.get_period_days()
            self.current_stats = self.tracker.get_usage_stats(days)
            self.update_ui()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载统计数据失败: {str(e)}")
    
    def update_ui(self):
        """更新UI显示"""
        if not self.current_stats:
            return
        
        # 更新摘要标签
        self.summary_labels['total_records'].setText(str(self.current_stats['total_records']))
        self.summary_labels['unique_samples'].setText(str(self.current_stats['unique_samples']))
        self.summary_labels['total_loads'].setText(str(self.current_stats['total_loads']))
        self.summary_labels['total_exports'].setText(str(self.current_stats['total_exports']))
        self.summary_labels['total_splits'].setText(str(self.current_stats['total_splits']))
        
        # 更新表格
        self.update_table()
        
        # 更新图表
        self.update_chart()
    
    def update_table(self):
        """更新详细数据表格"""
        if not self.current_stats:
            return
        
        daily_stats = self.current_stats.get('daily_stats', [])
        self.table.setRowCount(len(daily_stats))
        
        for row, stat in enumerate(daily_stats):
            self.table.setItem(row, 0, QTableWidgetItem(stat['date']))
            self.table.setItem(row, 1, QTableWidgetItem(str(stat['samples_loaded'])))
            self.table.setItem(row, 2, QTableWidgetItem(str(stat['samples_exported'])))
            self.table.setItem(row, 3, QTableWidgetItem(str(stat['samples_split'])))
            self.table.setItem(row, 4, QTableWidgetItem(str(stat['total_operations'])))
    
    def update_chart(self):
        """更新图表"""
        if not self.current_stats:
            return
        
        chart_type = self.chart_type_combo.currentText()
        
        if chart_type == "趋势图":
            daily_stats = self.current_stats.get('daily_stats', [])
            # 反转列表，使日期从旧到新
            daily_stats_reversed = list(reversed(daily_stats))
            self.chart_widget.plot_usage_trend(daily_stats_reversed)
        elif chart_type == "分布图":
            self.chart_widget.plot_operation_distribution(self.current_stats)
    
    def on_period_changed(self, text: str):
        """统计周期变化"""
        self.load_stats()
    
    def on_chart_type_changed(self, text: str):
        """图表类型变化"""
        self.update_chart()
    
    def export_report(self):
        """导出使用报告"""
        try:
            # 选择保存位置
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出使用报告",
                f"usage_report_{datetime.now().strftime('%Y%m%d')}.enc",
                "加密报告文件 (*.enc)"
            )
            
            if not file_path:
                return
            
            # 导出报告
            days = self.get_period_days()
            self.tracker.export_usage_report(file_path, days)
            
            QMessageBox.information(
                self,
                "成功",
                f"使用报告已导出到:\n{file_path}\n\n"
                f"请将此文件发送给管理员进行计费。"
            )
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出报告失败: {str(e)}")


# 测试代码
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 创建测试数据
    tracker = UsageTracker(silent=True)
    
    # 添加一些测试记录
    for i in range(20):
        tracker.record_usage('load_sample', f'test_sample_{i}', {'n_scans': 1000})
        if i % 2 == 0:
            tracker.record_usage('export_data', f'test_sample_{i}', {'export_type': 'csv'})
        if i % 3 == 0:
            tracker.record_usage('split_metabolites', f'test_sample_{i}', {'n_metabolites': 50})
    
    # 刷新缓冲区
    tracker._flush_batch()
    
    # 显示对话框
    dialog = UsageStatsDialog(tracker)
    dialog.exec_()

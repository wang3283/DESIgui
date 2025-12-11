"""
DESI报告生成器
生成PDF和Excel格式的分析报告
"""

import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


class ReportGenerator:
    """DESI数据分析报告生成器"""

    def __init__(self):
        """初始化报告生成器"""
        self.version = "2.0"
        print("[FILE] 报告生成器初始化完成")

    def generate_summary_report(self, data, filename):
        """
        生成PDF摘要报告

        Args:
            data: DESI数据字典
            filename: 输出PDF文件名
        """
        if not data:
            raise ValueError("数据为空，无法生成报告")

        print(f"[FILE] 生成PDF摘要报告: {filename}")

        # 这里可以实现PDF报告生成
        # 目前提供占位符实现

        # 创建简单的文本报告作为占位符
        report_content = self._generate_text_report(data)

        # 保存为文本文件（临时解决方案）
        text_filename = filename.replace('.pdf', '.txt')
        with open(text_filename, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"[成功] PDF报告已保存为文本格式: {text_filename}")
        print("   注意: 完整的PDF报告功能待实现")

    def generate_excel_report(self, data, filename):
        """
        生成Excel详细报告

        Args:
            data: DESI数据字典
            filename: 输出Excel文件名
        """
        if not data:
            raise ValueError("数据为空，无法生成报告")

        print(f"[STATS] 生成Excel详细报告: {filename}")

        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # 样本信息表
                sample_info = self._create_sample_info_sheet(data)
                sample_info.to_excel(writer, sheet_name='样本信息', index=False)

                # 离子统计表
                ion_stats = self._create_ion_stats_sheet(data)
                ion_stats.to_excel(writer, sheet_name='离子统计', index=False)

                # 前50高强度离子
                top_ions = self._create_top_ions_sheet(data)
                top_ions.to_excel(writer, sheet_name='高强度离子', index=False)

            print(f"[成功] Excel报告已生成: {filename}")

        except Exception as e:
            raise Exception(f"生成Excel报告失败: {str(e)}")

    def generate_comparison_report(self, data_list, labels, output_file):
        """
        生成多样本对比报告

        Args:
            data_list: 数据字典列表
            labels: 样本标签列表
            output_file: 输出文件名
        """
        print(f"[STATS] 生成多样本对比报告: {output_file}")
        print("   注意: 多样本对比报告功能待实现")

        # 创建简单的比较摘要
        comparison_content = self._generate_comparison_text_report(data_list, labels)

        text_filename = output_file.replace('.pdf', '.txt')
        with open(text_filename, 'w', encoding='utf-8') as f:
            f.write(comparison_content)

        print(f"[成功] 对比报告已保存为文本格式: {text_filename}")

    def _generate_text_report(self, data):
        """生成文本格式的报告内容"""
        content = []
        content.append("=" * 60)
        content.append("DESI质谱成像分析报告")
        content.append("=" * 60)
        content.append("")

        # 样本信息
        content.append("📋 样本信息:")
        content.append(f"   文件: {data.get('filename', 'Unknown')}")
        content.append(f"   扫描点数: {data.get('scan_count', 0)}")
        content.append(f"   m/z范围: {data.get('mz_range', 'Unknown')}")
        content.append(f"   离子数: {data.get('ion_count', 0)}")
        content.append("")

        # 统计信息
        content.append("[STATS] 统计信息:")
        if 'mz_bins' in data:
            content.append(f"   m/z值数量: {len(data['mz_bins'])}")
        if 'intensity_matrix' in data:
            content.append(f"   强度矩阵形状: {data['intensity_matrix'].shape}")
        content.append("")

        content.append("[FILE] 注意: 这是简化的文本报告，完整的PDF报告功能正在开发中")
        content.append("=" * 60)

        return "\n".join(content)

    def _generate_comparison_text_report(self, data_list, labels):
        """生成多样本比较的文本报告"""
        content = []
        content.append("=" * 60)
        content.append("DESI多样本对比分析报告")
        content.append("=" * 60)
        content.append("")

        for i, (data, label) in enumerate(zip(data_list, labels)):
            content.append(f"🔬 样本 {i+1}: {label}")
            content.append(f"   扫描点数: {data.get('scan_count', 0)}")
            content.append(f"   离子数: {data.get('ion_count', 0)}")
            content.append("")

        content.append("[FILE] 注意: 这是简化的文本报告，完整的PDF对比报告功能正在开发中")
        content.append("=" * 60)

        return "\n".join(content)

    def _create_sample_info_sheet(self, data):
        """创建样本信息表"""
        info_data = {
            '项目': ['文件名', '扫描点数', '离子数', 'm/z范围'],
            '值': [
                data.get('filename', 'Unknown'),
                data.get('scan_count', 0),
                data.get('ion_count', 0),
                str(data.get('mz_range', 'Unknown'))
            ]
        }
        return pd.DataFrame(info_data)

    def _create_ion_stats_sheet(self, data):
        """创建离子统计表"""
        if 'mz_bins' not in data or 'mean_intensity' not in data:
            # 如果没有统计数据，创建空表
            return pd.DataFrame({'m/z': [], '平均强度': [], '最大强度': [], '变异系数': []})

        stats_data = {
            'm/z': data['mz_bins'][:100],  # 只显示前100个
            '平均强度': data['mean_intensity'][:100],
            '最大强度': data['max_intensity'][:100] if 'max_intensity' in data else [0] * 100,
            '变异系数': data['cv'][:100] if 'cv' in data else [0] * 100
        }
        return pd.DataFrame(stats_data)

    def _create_top_ions_sheet(self, data):
        """创建高强度离子表"""
        if 'mz_bins' not in data or 'mean_intensity' not in data:
            return pd.DataFrame({'排名': [], 'm/z': [], '强度': []})

        # 按强度排序
        intensities = data['mean_intensity']
        mz_values = data['mz_bins']

        # 获取排序索引
        sorted_indices = sorted(range(len(intensities)),
                               key=lambda i: intensities[i],
                               reverse=True)

        top_indices = sorted_indices[:50]  # 前50个

        top_data = {
            '排名': range(1, len(top_indices) + 1),
            'm/z': [mz_values[i] for i in top_indices],
            '强度': [intensities[i] for i in top_indices]
        }

        return pd.DataFrame(top_data)

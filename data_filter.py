#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据过滤器
根据配置过滤和预处理数据，减少处理量
"""

import numpy as np
from typing import Dict, Tuple
from data_filter_config import DataFilterConfig


class DataFilter:
    """数据过滤器"""
    
    def __init__(self, config: DataFilterConfig):
        """
        初始化
        
        参数:
            config: 数据过滤配置
        """
        self.config = config
    
    def filter_data(self, data: Dict) -> Dict:
        """
        过滤数据
        
        参数:
            data: 原始数据字典，包含：
                - 'mz_bins': m/z数组
                - 'intensity_matrix': 强度矩阵
                - 其他元数据
        
        返回:
            过滤后的数据字典
        """
        if not self.config.should_filter():
            print("[信息] 数据过滤未启用")
            return data
        
        print(f"\n[CONFIG] 应用数据过滤: {self.config.get_filter_description()}")
        
        mz_bins = data['mz_bins'].copy()
        intensity_matrix = data['intensity_matrix'].copy()
        
        # 记录原始数据量
        original_mz_count = len(mz_bins)
        print(f"   原始m/z数量: {original_mz_count}")
        
        # 1. m/z范围过滤
        if self.config.use_mz_range:
            mz_bins, intensity_matrix = self._filter_by_mz_range(
                mz_bins, intensity_matrix
            )
            print(f"   m/z范围过滤后: {len(mz_bins)} 个m/z")
        
        # 2. 目标m/z列表过滤
        if self.config.import_from_file and self.config.target_masses:
            mz_bins, intensity_matrix = self._filter_by_target_masses(
                mz_bins, intensity_matrix
            )
            print(f"   目标m/z过滤后: {len(mz_bins)} 个m/z")
        
        # 3. Top N高强度峰过滤
        if self.config.use_top_n:
            mz_bins, intensity_matrix = self._filter_by_top_n(
                mz_bins, intensity_matrix
            )
            print(f"   Top N过滤后: {len(mz_bins)} 个m/z")
        
        # 创建过滤后的数据副本
        filtered_data = data.copy()
        filtered_data['mz_bins'] = mz_bins
        filtered_data['intensity_matrix'] = intensity_matrix
        filtered_data['n_bins'] = len(mz_bins)
        
        # 添加过滤信息
        filtered_data['filter_info'] = {
            'filtered': True,
            'original_mz_count': original_mz_count,
            'filtered_mz_count': len(mz_bins),
            'reduction_ratio': 1 - len(mz_bins) / original_mz_count,
            'filter_description': self.config.get_filter_description()
        }
        
        reduction_percent = (1 - len(mz_bins) / original_mz_count) * 100
        print(f"   [成功] 数据量减少: {reduction_percent:.1f}% "
              f"({original_mz_count} → {len(mz_bins)})")
        
        return filtered_data
    
    def _filter_by_mz_range(
        self, 
        mz_bins: np.ndarray, 
        intensity_matrix: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        按m/z范围过滤
        
        参数:
            mz_bins: m/z数组
            intensity_matrix: 强度矩阵
        
        返回:
            (过滤后的mz_bins, 过滤后的intensity_matrix)
        """
        mask = (mz_bins >= self.config.mz_start) & (mz_bins <= self.config.mz_stop)
        
        filtered_mz = mz_bins[mask]
        filtered_intensity = intensity_matrix[:, mask]
        
        return filtered_mz, filtered_intensity
    
    def _filter_by_target_masses(
        self, 
        mz_bins: np.ndarray, 
        intensity_matrix: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        按目标m/z列表过滤
        
        参数:
            mz_bins: m/z数组
            intensity_matrix: 强度矩阵
        
        返回:
            (过滤后的mz_bins, 过滤后的intensity_matrix)
        """
        # 为每个目标m/z找到最接近的m/z bin
        selected_indices = []
        
        for target_mz in self.config.target_masses:
            # 在窗口范围内查找
            diffs = np.abs(mz_bins - target_mz)
            
            if diffs.min() <= self.config.mz_window:
                closest_idx = np.argmin(diffs)
                if closest_idx not in selected_indices:
                    selected_indices.append(closest_idx)
        
        selected_indices = sorted(selected_indices)
        
        filtered_mz = mz_bins[selected_indices]
        filtered_intensity = intensity_matrix[:, selected_indices]
        
        return filtered_mz, filtered_intensity
    
    def _filter_by_top_n(
        self, 
        mz_bins: np.ndarray, 
        intensity_matrix: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        选择Top N最高强度的峰
        
        参数:
            mz_bins: m/z数组
            intensity_matrix: 强度矩阵
        
        返回:
            (过滤后的mz_bins, 过滤后的intensity_matrix)
        """
        # 计算每个m/z的总强度
        total_intensities = np.sum(intensity_matrix, axis=0)
        
        # 如果m/z数量已经小于等于top_n，不需要过滤
        if len(mz_bins) <= self.config.top_n_peaks:
            return mz_bins, intensity_matrix
        
        # 找到Top N的索引
        top_indices = np.argsort(total_intensities)[-self.config.top_n_peaks:]
        top_indices = np.sort(top_indices)  # 保持m/z顺序
        
        filtered_mz = mz_bins[top_indices]
        filtered_intensity = intensity_matrix[:, top_indices]
        
        return filtered_mz, filtered_intensity


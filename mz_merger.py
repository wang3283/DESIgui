#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
m/z偏差合并算法
将偏差范围内的m/z识别为同一物质
"""

import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
import logging

logger = logging.getLogger(__name__)


class MzMerger:
    """m/z合并器"""
    
    def __init__(self, tolerance_ppm=10, tolerance_da=None, 
                 merge_method='weighted_mean'):
        """
        初始化m/z合并器
        
        Parameters:
        -----------
        tolerance_ppm : float
            ppm容差（默认10 ppm）
        tolerance_da : float, optional
            绝对容差（Da），如果指定则优先使用
        merge_method : str
            合并方法: 'mean', 'weighted_mean', 'median'
        """
        self.tolerance_ppm = tolerance_ppm
        self.tolerance_da = tolerance_da
        self.merge_method = merge_method
        
        # 合并历史
        self.merge_groups = []
    
    def calculate_tolerance(self, mz):
        """
        计算给定m/z的容差
        
        Parameters:
        -----------
        mz : float
            m/z值
        
        Returns:
        --------
        float
            容差（Da）
        """
        if self.tolerance_da is not None:
            return self.tolerance_da
        else:
            return mz * self.tolerance_ppm / 1e6
    
    def merge_mz_values(self, mz_values, intensities=None):
        """
        合并相近的m/z值
        
        Parameters:
        -----------
        mz_values : array
            m/z值数组
        intensities : array, optional
            对应的强度数组（用于加权平均）
        
        Returns:
        --------
        dict
            合并结果:
            {
                'merged_mz': array,        # 合并后的m/z值
                'merged_intensity': array, # 合并后的强度
                'group_ids': array,        # 每个原始m/z所属的组ID
                'group_sizes': array,      # 每个组的大小
                'merge_info': list         # 详细的合并信息
            }
        """
        mz_values = np.array(mz_values)
        n = len(mz_values)
        
        if intensities is not None:
            intensities = np.array(intensities)
        else:
            intensities = np.ones(n)
        
        # 排序
        sort_idx = np.argsort(mz_values)
        sorted_mz = mz_values[sort_idx]
        sorted_intensity = intensities[sort_idx]
        
        # 分组：使用滑动窗口法
        groups = []
        current_group = [0]
        current_group_mz = [sorted_mz[0]]
        
        for i in range(1, n):
            # 计算与当前组的距离
            group_center = np.mean(current_group_mz)
            tolerance = self.calculate_tolerance(group_center)
            
            if abs(sorted_mz[i] - group_center) <= tolerance:
                # 属于当前组
                current_group.append(i)
                current_group_mz.append(sorted_mz[i])
            else:
                # 开始新组
                groups.append(current_group)
                current_group = [i]
                current_group_mz = [sorted_mz[i]]
        
        # 添加最后一组
        groups.append(current_group)
        
        logger.info(f"将 {n} 个m/z值合并为 {len(groups)} 组")
        
        # 合并每个组
        merged_mz = []
        merged_intensity = []
        group_ids = np.zeros(n, dtype=int)
        group_sizes = []
        merge_info = []
        
        for group_id, group_indices in enumerate(groups):
            group_mz = sorted_mz[group_indices]
            group_intensity = sorted_intensity[group_indices]
            
            # 根据方法计算代表性m/z
            if self.merge_method == 'mean':
                representative_mz = np.mean(group_mz)
            elif self.merge_method == 'weighted_mean':
                representative_mz = np.average(group_mz, weights=group_intensity)
            elif self.merge_method == 'median':
                representative_mz = np.median(group_mz)
            else:
                representative_mz = np.mean(group_mz)
            
            # 合并强度（求和）
            representative_intensity = np.sum(group_intensity)
            
            merged_mz.append(representative_mz)
            merged_intensity.append(representative_intensity)
            group_sizes.append(len(group_indices))
            
            # 记录组ID
            for idx in group_indices:
                original_idx = sort_idx[idx]
                group_ids[original_idx] = group_id
            
            # 详细信息
            info = {
                'group_id': group_id,
                'n_members': len(group_indices),
                'representative_mz': float(representative_mz),
                'mz_range': [float(np.min(group_mz)), float(np.max(group_mz))],
                'mz_std': float(np.std(group_mz)),
                'total_intensity': float(representative_intensity),
                'member_mz': [float(mz) for mz in group_mz]
            }
            merge_info.append(info)
        
        self.merge_groups = merge_info
        
        return {
            'merged_mz': np.array(merged_mz),
            'merged_intensity': np.array(merged_intensity),
            'group_ids': group_ids,
            'group_sizes': np.array(group_sizes),
            'merge_info': merge_info,
            'n_original': n,
            'n_merged': len(merged_mz),
            'reduction_rate': (n - len(merged_mz)) / n * 100
        }
    
    def merge_dataset_ions(self, data, intensity_threshold=0):
        """
        合并数据集中的离子
        
        Parameters:
        -----------
        data : dict
            包含以下键的数据字典：
            - 'mz_bins': m/z bins数组
            - 'intensity_matrix': 强度矩阵 (n_scans × n_bins)
        intensity_threshold : float
            强度阈值，低于此值的离子将被忽略
        
        Returns:
        --------
        dict
            合并后的数据字典，包含：
            - 'mz_bins': 合并后的m/z bins
            - 'intensity_matrix': 合并后的强度矩阵
            - 'merge_info': 合并信息
        """
        mz_bins = np.array(data['mz_bins'])
        intensity_matrix = np.array(data['intensity_matrix'])
        n_scans, n_bins = intensity_matrix.shape
        
        # 计算每个m/z的总强度
        total_intensity = np.sum(intensity_matrix, axis=0)
        
        # 过滤低强度离子
        valid_mask = total_intensity > intensity_threshold
        valid_mz = mz_bins[valid_mask]
        valid_intensity_matrix = intensity_matrix[:, valid_mask]
        valid_total_intensity = total_intensity[valid_mask]
        
        logger.info(f"过滤后保留 {len(valid_mz)}/{len(mz_bins)} 个离子")
        
        # 合并m/z值
        merge_result = self.merge_mz_values(valid_mz, valid_total_intensity)
        
        # 重建强度矩阵
        n_merged = len(merge_result['merged_mz'])
        merged_intensity_matrix = np.zeros((n_scans, n_merged))
        
        for scan_idx in range(n_scans):
            scan_intensity = valid_intensity_matrix[scan_idx, :]
            
            # 按组合并强度
            for group_id in range(n_merged):
                group_mask = merge_result['group_ids'] == group_id
                merged_intensity_matrix[scan_idx, group_id] = np.sum(scan_intensity[group_mask])
        
        merged_data = {
            'sample_name': data.get('sample_name', 'Unknown'),
            'mz_bins': merge_result['merged_mz'],
            'intensity_matrix': merged_intensity_matrix,
            'coords': data.get('coords', None),
            'n_scans': n_scans,
            'n_bins': n_merged,
            'merge_info': merge_result['merge_info'],
            'merge_statistics': {
                'n_original': merge_result['n_original'],
                'n_merged': merge_result['n_merged'],
                'reduction_rate': merge_result['reduction_rate']
            }
        }
        
        logger.info(f"离子合并完成: {merge_result['n_original']} → {merge_result['n_merged']} "
                   f"(减少 {merge_result['reduction_rate']:.1f}%)")
        
        return merged_data
    
    def get_merge_statistics(self):
        """
        获取合并统计信息
        
        Returns:
        --------
        dict
            统计信息
        """
        if len(self.merge_groups) == 0:
            return {
                'n_groups': 0,
                'mean_group_size': 0,
                'max_group_size': 0
            }
        
        group_sizes = [g['n_members'] for g in self.merge_groups]
        multi_member_groups = [g for g in self.merge_groups if g['n_members'] > 1]
        
        return {
            'n_groups': len(self.merge_groups),
            'n_multi_member_groups': len(multi_member_groups),
            'mean_group_size': float(np.mean(group_sizes)),
            'max_group_size': int(np.max(group_sizes)),
            'min_mz': float(min(g['representative_mz'] for g in self.merge_groups)),
            'max_mz': float(max(g['representative_mz'] for g in self.merge_groups)),
            'largest_groups': sorted(multi_member_groups, 
                                   key=lambda x: x['n_members'], 
                                   reverse=True)[:10]
        }


if __name__ == '__main__':
    # 测试m/z合并器
    print("="*80)
    print("m/z合并器测试")
    print("="*80)
    
    # 创建模拟数据：包含一些相近的m/z值
    np.random.seed(42)
    
    # 生成3组相近的m/z值
    group1_center = 500.0000
    group2_center = 600.0000
    group3_center = 700.0000
    
    group1_mz = group1_center + np.random.uniform(-0.005, 0.005, 5)  # ±5 mDa
    group2_mz = group2_center + np.random.uniform(-0.003, 0.003, 3)  # ±3 mDa
    group3_mz = group3_center + np.random.uniform(-0.008, 0.008, 7)  # ±8 mDa
    
    # 添加一些独立的m/z值
    isolated_mz = np.array([450.0, 550.0, 650.0, 750.0, 800.0])
    
    # 合并所有m/z值
    all_mz = np.concatenate([group1_mz, group2_mz, group3_mz, isolated_mz])
    all_intensity = np.random.uniform(100, 1000, len(all_mz))
    
    print(f"\n创建模拟数据:")
    print(f"  总m/z数: {len(all_mz)}")
    print(f"  组1: {len(group1_mz)} 个m/z around {group1_center}")
    print(f"  组2: {len(group2_mz)} 个m/z around {group2_center}")
    print(f"  组3: {len(group3_mz)} 个m/z around {group3_center}")
    print(f"  独立: {len(isolated_mz)} 个m/z")
    
    # 创建合并器
    merger = MzMerger(tolerance_ppm=20, merge_method='weighted_mean')
    
    print(f"\nm/z合并器配置:")
    print(f"  容差: {merger.tolerance_ppm} ppm")
    print(f"  合并方法: {merger.merge_method}")
    
    # 执行合并
    print(f"\n执行m/z合并...")
    result = merger.merge_mz_values(all_mz, all_intensity)
    
    print(f"\n合并结果:")
    print(f"  原始m/z数: {result['n_original']}")
    print(f"  合并后m/z数: {result['n_merged']}")
    print(f"  减少率: {result['reduction_rate']:.1f}%")
    
    # 获取统计信息
    stats = merger.get_merge_statistics()
    
    print(f"\n合并统计:")
    print(f"  总组数: {stats['n_groups']}")
    print(f"  多成员组数: {stats['n_multi_member_groups']}")
    print(f"  平均组大小: {stats['mean_group_size']:.2f}")
    print(f"  最大组大小: {stats['max_group_size']}")
    
    print(f"\n最大的组:")
    for i, group in enumerate(stats['largest_groups'][:5]):
        print(f"  组{i+1}: {group['n_members']} 个成员, "
              f"代表m/z={group['representative_mz']:.4f}, "
              f"范围=[{group['mz_range'][0]:.4f}, {group['mz_range'][1]:.4f}], "
              f"std={group['mz_std']:.4f}")
    
    print(f"\n示例：500.0100 和 500.0000 的合并")
    test_mz = np.array([500.0100, 500.0000])
    test_intensity = np.array([1000, 800])
    test_result = merger.merge_mz_values(test_mz, test_intensity)
    print(f"  原始: {test_mz}")
    print(f"  合并后: {test_result['merged_mz']}")
    print(f"  强度: {test_intensity} → {test_result['merged_intensity']}")
    
    print(f"\n[成功] m/z合并器测试完成！")


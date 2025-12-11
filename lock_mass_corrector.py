#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lock Mass校正系统
用于质谱数据的m/z和信号强度校正
"""

import numpy as np
from scipy.interpolate import interp1d
from scipy.signal import find_peaks
import logging

logger = logging.getLogger(__name__)


class LockMassCorrector:
    """Lock Mass校正器"""
    
    # Lock Mass标准值
    LOCK_MASS_POSITIVE = 556.2771  # 正离子模式
    LOCK_MASS_NEGATIVE = 554.2615  # 负离子模式
    
    def __init__(self, ion_mode='positive', tolerance_amu=0.25, 
                 min_intensity=500, sample_frequency_min=1):
        """
        初始化Lock Mass校正器
        
        Parameters:
        -----------
        ion_mode : str
            离子模式 'positive' 或 'negative'
        tolerance_amu : float
            Lock Mass容差（amu）
        min_intensity : float
            最小信号强度阈值
        sample_frequency_min : float
            采样频率（分钟）
        """
        self.ion_mode = ion_mode
        self.tolerance_amu = tolerance_amu
        self.min_intensity = min_intensity
        self.sample_frequency_min = sample_frequency_min
        
        # 选择Lock Mass标准值
        if ion_mode == 'positive':
            self.lock_mass_standard = self.LOCK_MASS_POSITIVE
        elif ion_mode == 'negative':
            self.lock_mass_standard = self.LOCK_MASS_NEGATIVE
        else:
            raise ValueError(f"Unsupported ion mode: {ion_mode}")
        
        # 校正历史记录
        self.correction_history = []
    
    def detect_lock_mass(self, mz_bins, intensity, scan_time=None):
        """
        检测Lock Mass峰
        
        Parameters:
        -----------
        mz_bins : array
            m/z值数组
        intensity : array
            强度数组
        scan_time : float, optional
            扫描时间（分钟）
        
        Returns:
        --------
        dict or None
            检测到的Lock Mass信息：
            {
                'mz_measured': float,  # 测量的m/z
                'intensity': float,     # 信号强度
                'mz_error': float,      # m/z偏差
                'scan_time': float      # 扫描时间
            }
        """
        # 确保输入是numpy数组
        mz_bins = np.array(mz_bins)
        intensity = np.array(intensity)
        
        # 查找Lock Mass附近的m/z范围
        mz_min = self.lock_mass_standard - self.tolerance_amu
        mz_max = self.lock_mass_standard + self.tolerance_amu
        
        # 找到m/z范围内的索引
        mask = (mz_bins >= mz_min) & (mz_bins <= mz_max)
        
        if not np.any(mask):
            logger.warning(f"未在范围 {mz_min:.4f}-{mz_max:.4f} 内找到Lock Mass")
            return None
        
        # 提取范围内的数据
        mz_region = mz_bins[mask]
        intensity_region = intensity[mask]
        
        # 检查强度是否满足阈值
        if np.max(intensity_region) < self.min_intensity:
            logger.warning(f"Lock Mass强度 {np.max(intensity_region):.1f} 低于阈值 {self.min_intensity}")
            return None
        
        # 找到最高峰
        max_idx = np.argmax(intensity_region)
        mz_measured = mz_region[max_idx]
        intensity_measured = intensity_region[max_idx]
        
        # 计算m/z偏差
        mz_error = mz_measured - self.lock_mass_standard
        
        lock_mass_info = {
            'mz_measured': float(mz_measured),
            'intensity': float(intensity_measured),
            'mz_error': float(mz_error),
            'mz_error_ppm': float(mz_error / self.lock_mass_standard * 1e6),
            'scan_time': scan_time
        }
        
        logger.info(f"检测到Lock Mass: m/z={mz_measured:.4f}, "
                   f"偏差={mz_error:.4f} amu ({lock_mass_info['mz_error_ppm']:.2f} ppm)")
        
        return lock_mass_info
    
    def correct_spectrum(self, mz_bins, intensity, correction_factor_mz=None,
                        correction_factor_intensity=None):
        """
        校正单个质谱
        
        Parameters:
        -----------
        mz_bins : array
            原始m/z值数组
        intensity : array
            原始强度数组
        correction_factor_mz : float, optional
            m/z校正因子（偏差）
        correction_factor_intensity : float, optional
            强度校正因子（比例）
        
        Returns:
        --------
        tuple : (corrected_mz, corrected_intensity)
            校正后的m/z和强度
        """
        mz_bins = np.array(mz_bins)
        intensity = np.array(intensity)
        
        # 校正m/z
        if correction_factor_mz is not None:
            corrected_mz = mz_bins - correction_factor_mz
        else:
            corrected_mz = mz_bins.copy()
        
        # 校正强度
        if correction_factor_intensity is not None:
            corrected_intensity = intensity * correction_factor_intensity
        else:
            corrected_intensity = intensity.copy()
        
        return corrected_mz, corrected_intensity
    
    def correct_dataset(self, data, scan_times=None):
        """
        校正整个数据集
        
        Parameters:
        -----------
        data : dict
            包含以下键的数据字典：
            - 'mz_bins': m/z bins数组
            - 'intensity_matrix': 强度矩阵 (n_scans × n_bins)
            - 'coords': 坐标数组 (可选)
        scan_times : array, optional
            每个扫描的时间（分钟）
        
        Returns:
        --------
        dict
            校正后的数据字典，结构与输入相同，额外包含：
            - 'lock_mass_corrections': 校正历史列表
        """
        mz_bins = np.array(data['mz_bins'])
        intensity_matrix = np.array(data['intensity_matrix'])
        n_scans, n_bins = intensity_matrix.shape
        
        # 如果没有提供扫描时间，生成默认时间
        if scan_times is None:
            # 假设每个扫描间隔相等
            total_time = n_scans  # 假设每个扫描1个时间单位
            scan_times = np.linspace(0, total_time, n_scans)
        else:
            scan_times = np.array(scan_times)
        
        # 确定需要校正的扫描索引（按sample_frequency采样）
        sample_interval = int(self.sample_frequency_min * 60)  # 转换为扫描数
        if sample_interval < 1:
            sample_interval = 1
        
        correction_scan_indices = list(range(0, n_scans, sample_interval))
        
        logger.info(f"将在 {len(correction_scan_indices)} 个扫描点进行Lock Mass校正")
        
        # 检测所有校正点的Lock Mass
        lock_mass_detections = []
        for scan_idx in correction_scan_indices:
            spectrum = intensity_matrix[scan_idx, :]
            scan_time = scan_times[scan_idx]
            
            lock_mass_info = self.detect_lock_mass(mz_bins, spectrum, scan_time)
            if lock_mass_info is not None:
                lock_mass_info['scan_idx'] = scan_idx
                lock_mass_detections.append(lock_mass_info)
        
        logger.info(f"成功检测到 {len(lock_mass_detections)} 个Lock Mass峰")
        
        if len(lock_mass_detections) == 0:
            logger.warning("未检测到任何Lock Mass，将返回原始数据")
            return {
                **data,
                'lock_mass_corrections': [],
                'corrected': False
            }
        
        # 创建校正因子插值函数
        if len(lock_mass_detections) == 1:
            # 只有一个检测点，使用常数校正
            mz_correction = lock_mass_detections[0]['mz_error']
            mz_correction_func = lambda t: mz_correction
            intensity_correction_func = lambda t: 1.0  # 暂不校正强度
        else:
            # 多个检测点，使用线性插值
            detection_times = [d['scan_time'] for d in lock_mass_detections]
            mz_errors = [d['mz_error'] for d in lock_mass_detections]
            
            mz_correction_func = interp1d(
                detection_times, mz_errors,
                kind='linear', fill_value='extrapolate'
            )
            intensity_correction_func = lambda t: 1.0  # 暂不校正强度
        
        # 应用校正到所有扫描
        corrected_mz_bins = mz_bins.copy()
        corrected_intensity_matrix = intensity_matrix.copy()
        
        for scan_idx in range(n_scans):
            scan_time = scan_times[scan_idx]
            mz_correction = float(mz_correction_func(scan_time))
            
            # 校正m/z（对于所有扫描使用相同的m/z bins校正）
            if scan_idx == 0:
                corrected_mz_bins = mz_bins - mz_correction
            
            # 不需要校正每个扫描的强度，因为强度本身不受m/z漂移影响
        
        # 记录校正历史
        self.correction_history = lock_mass_detections
        
        corrected_data = {
            'sample_name': data.get('sample_name', 'Unknown'),
            'mz_bins': corrected_mz_bins,
            'intensity_matrix': corrected_intensity_matrix,
            'coords': data.get('coords', None),
            'n_scans': data.get('n_scans', n_scans),
            'n_bins': data.get('n_bins', n_bins),
            'lock_mass_corrections': lock_mass_detections,
            'corrected': True,
            'correction_params': {
                'ion_mode': self.ion_mode,
                'lock_mass_standard': self.lock_mass_standard,
                'tolerance_amu': self.tolerance_amu,
                'min_intensity': self.min_intensity,
                'sample_frequency_min': self.sample_frequency_min
            }
        }
        
        logger.info(f"数据集校正完成，平均m/z偏差: {np.mean(mz_errors):.4f} amu")
        
        return corrected_data
    
    def get_correction_summary(self):
        """
        获取校正总结
        
        Returns:
        --------
        dict
            校正统计信息
        """
        if len(self.correction_history) == 0:
            return {
                'n_corrections': 0,
                'mean_mz_error': 0.0,
                'std_mz_error': 0.0,
                'mean_mz_error_ppm': 0.0,
                'std_mz_error_ppm': 0.0
            }
        
        mz_errors = [c['mz_error'] for c in self.correction_history]
        mz_errors_ppm = [c['mz_error_ppm'] for c in self.correction_history]
        
        return {
            'n_corrections': len(self.correction_history),
            'mean_mz_error': float(np.mean(mz_errors)),
            'std_mz_error': float(np.std(mz_errors)),
            'mean_mz_error_ppm': float(np.mean(mz_errors_ppm)),
            'std_mz_error_ppm': float(np.std(mz_errors_ppm)),
            'min_mz_error': float(np.min(mz_errors)),
            'max_mz_error': float(np.max(mz_errors))
        }


if __name__ == '__main__':
    # 测试Lock Mass校正器
    print("="*80)
    print("Lock Mass校正器测试")
    print("="*80)
    
    # 创建模拟数据
    np.random.seed(42)
    n_scans = 1000
    n_bins = 1500
    
    # 模拟m/z bins（包含Lock Mass）
    mz_bins = np.linspace(50, 1200, n_bins)
    
    # 找到Lock Mass对应的索引
    lock_mass_idx = np.argmin(np.abs(mz_bins - 554.2615))
    
    print(f"\n创建模拟数据:")
    print(f"  扫描数: {n_scans}")
    print(f"  m/z bins: {n_bins}")
    print(f"  Lock Mass索引: {lock_mass_idx}")
    print(f"  Lock Mass m/z: {mz_bins[lock_mass_idx]:.4f}")
    
    # 模拟强度矩阵
    intensity_matrix = np.random.exponential(100, (n_scans, n_bins))
    
    # 在Lock Mass位置添加强信号
    intensity_matrix[:, lock_mass_idx] = np.random.uniform(800, 1200, n_scans)
    
    # 模拟m/z漂移
    time_points = np.linspace(0, 60, n_scans)  # 60分钟
    mz_drift = 0.1 * np.sin(2 * np.pi * time_points / 30)  # 周期性漂移
    
    # 创建数据字典
    data = {
        'sample_name': 'Test Sample',
        'mz_bins': mz_bins + mz_drift[0],  # 添加初始漂移
        'intensity_matrix': intensity_matrix,
        'n_scans': n_scans,
        'n_bins': n_bins
    }
    
    # 创建校正器
    corrector = LockMassCorrector(
        ion_mode='negative',
        tolerance_amu=0.25,
        min_intensity=500,
        sample_frequency_min=1
    )
    
    print(f"\nLock Mass校正器配置:")
    print(f"  离子模式: {corrector.ion_mode}")
    print(f"  Lock Mass标准: {corrector.lock_mass_standard:.4f} m/z")
    print(f"  容差: {corrector.tolerance_amu} amu")
    print(f"  最小强度: {corrector.min_intensity} counts")
    print(f"  采样频率: {corrector.sample_frequency_min} min")
    
    # 执行校正
    print(f"\n执行Lock Mass校正...")
    corrected_data = corrector.correct_dataset(data, scan_times=time_points)
    
    # 获取校正总结
    summary = corrector.get_correction_summary()
    
    print(f"\n校正总结:")
    print(f"  检测到的Lock Mass数: {summary['n_corrections']}")
    print(f"  平均m/z偏差: {summary['mean_mz_error']:.4f} ± {summary['std_mz_error']:.4f} amu")
    print(f"  平均m/z偏差: {summary['mean_mz_error_ppm']:.2f} ± {summary['std_mz_error_ppm']:.2f} ppm")
    print(f"  m/z偏差范围: [{summary['min_mz_error']:.4f}, {summary['max_mz_error']:.4f}] amu")
    
    print(f"\n校正结果:")
    print(f"  原始m/z范围: [{data['mz_bins'][0]:.4f}, {data['mz_bins'][-1]:.4f}]")
    print(f"  校正后m/z范围: [{corrected_data['mz_bins'][0]:.4f}, {corrected_data['mz_bins'][-1]:.4f}]")
    print(f"  数据已校正: {corrected_data['corrected']}")
    
    print(f"\n[成功] Lock Mass校正器测试完成！")


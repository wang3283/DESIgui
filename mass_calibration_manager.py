#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
质量校准管理器 - Lock Mass功能实现

功能：
1. Lock Mass参数管理
2. 质量漂移校准
3. 离子合并（m/z容差范围内）
4. 定期采样和校准
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import json


class LockMassConfig:
    """Lock Mass配置类"""
    
    def __init__(self):
        # Lock Mass参数
        self.enabled = False
        self.lock_mass_mz = 554.2615  # 参考离子的m/z值
        self.tolerance_amu = 0.25  # 容差(amu)
        self.max_signal_intensity = 500  # 最大信号强度阈值
        self.use_internal = True  # 使用内标
        
        # 采样参数
        self.sample_frequency_min = 1  # 采样频率(分钟)
        self.sample_duration_sec = 10  # 采样持续时间(秒)
        
        # 离子合并参数
        self.merge_tolerance_ppm = 10  # m/z合并容差(ppm)
        
        # 校准历史
        self.calibration_history = []
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'enabled': self.enabled,
            'lock_mass_mz': self.lock_mass_mz,
            'tolerance_amu': self.tolerance_amu,
            'max_signal_intensity': self.max_signal_intensity,
            'use_internal': self.use_internal,
            'sample_frequency_min': self.sample_frequency_min,
            'sample_duration_sec': self.sample_duration_sec,
            'merge_tolerance_ppm': self.merge_tolerance_ppm
        }
    
    def from_dict(self, data: Dict):
        """从字典加载"""
        self.enabled = data.get('enabled', False)
        self.lock_mass_mz = data.get('lock_mass_mz', 554.2615)
        self.tolerance_amu = data.get('tolerance_amu', 0.25)
        self.max_signal_intensity = data.get('max_signal_intensity', 500)
        self.use_internal = data.get('use_internal', True)
        self.sample_frequency_min = data.get('sample_frequency_min', 1)
        self.sample_duration_sec = data.get('sample_duration_sec', 10)
        self.merge_tolerance_ppm = data.get('merge_tolerance_ppm', 10)
    
    def save(self, filepath: str):
        """保存配置"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def load(self, filepath: str):
        """加载配置"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.from_dict(data)


class MassCalibrationManager:
    """质量校准管理器"""
    
    def __init__(self, config: Optional[LockMassConfig] = None):
        self.config = config or LockMassConfig()
        self.last_calibration_time = None
        self.current_correction = 0.0  # 当前的质量校正值(Da)
        self.correction_history = []  # 校正历史
    
    def should_calibrate(self, current_time: datetime) -> bool:
        """判断是否需要进行校准"""
        if not self.config.enabled:
            return False
        
        if self.last_calibration_time is None:
            return True
        
        time_diff = (current_time - self.last_calibration_time).total_seconds()
        return time_diff >= self.config.sample_frequency_min * 60
    
    def find_lock_mass_peak(self, mz_array: np.ndarray, 
                           intensity_array: np.ndarray) -> Optional[Tuple[float, float]]:
        """
        在数据中找到Lock Mass峰
        
        参数:
            mz_array: m/z数组
            intensity_array: 强度数组
        
        返回:
            (measured_mz, intensity) 或 None
        """
        # 计算搜索范围
        target_mz = self.config.lock_mass_mz
        tolerance = self.config.tolerance_amu
        
        # 找到范围内的峰
        mask = np.abs(mz_array - target_mz) <= tolerance
        
        if not np.any(mask):
            return None
        
        # 找到最强的峰
        intensities_in_range = intensity_array[mask]
        mz_in_range = mz_array[mask]
        
        max_idx = np.argmax(intensities_in_range)
        measured_mz = mz_in_range[max_idx]
        intensity = intensities_in_range[max_idx]
        
        # 检查强度阈值（仅当设置了最大强度限制时）
        # 注意：设置为0表示不限制最大强度
        if self.config.max_signal_intensity > 0:
            if intensity > self.config.max_signal_intensity:
                print(f"[警告] Lock Mass峰强度({intensity:.1f})超过最大限制({self.config.max_signal_intensity})")
                return None  # 信号过强，可能是干扰或饱和
        
        return measured_mz, intensity
    
    def calculate_correction(self, measured_mz: float) -> float:
        """
        计算质量校正值
        
        参数:
            measured_mz: 实际测量的m/z值
        
        返回:
            校正值(Da) = 理论值 - 测量值
        """
        theoretical_mz = self.config.lock_mass_mz
        correction = theoretical_mz - measured_mz
        return correction
    
    def calibrate(self, mz_array: np.ndarray, 
                  intensity_array: np.ndarray,
                  current_time: Optional[datetime] = None) -> Optional[float]:
        """
        执行校准
        
        参数:
            mz_array: m/z数组
            intensity_array: 强度数组
            current_time: 当前时间
        
        返回:
            校正值(Da) 或 None
        """
        if current_time is None:
            current_time = datetime.now()
        
        # 查找Lock Mass峰
        result = self.find_lock_mass_peak(mz_array, intensity_array)
        
        if result is None:
            print(f"[警告] 未找到Lock Mass峰 (m/z {self.config.lock_mass_mz:.4f})")
            return None
        
        measured_mz, intensity = result
        
        # 计算校正值
        correction = self.calculate_correction(measured_mz)
        
        # 更新状态
        self.current_correction = correction
        self.last_calibration_time = current_time
        
        # 记录历史
        calibration_record = {
            'time': current_time,
            'measured_mz': measured_mz,
            'theoretical_mz': self.config.lock_mass_mz,
            'correction': correction,
            'intensity': intensity,
            'error_ppm': (measured_mz - self.config.lock_mass_mz) / self.config.lock_mass_mz * 1e6
        }
        
        self.correction_history.append(calibration_record)
        self.config.calibration_history.append(calibration_record)
        
        print(f"[成功] Lock Mass校准完成:")
        print(f"   理论m/z: {self.config.lock_mass_mz:.4f}")
        print(f"   测量m/z: {measured_mz:.4f}")
        print(f"   校正值: {correction:.4f} Da ({calibration_record['error_ppm']:.2f} ppm)")
        print(f"   强度: {intensity:.1f}")
        
        return correction
    
    def apply_correction(self, mz_array: np.ndarray) -> np.ndarray:
        """
        应用校正到m/z数组
        
        参数:
            mz_array: 原始m/z数组
        
        返回:
            校正后的m/z数组
        """
        if not self.config.enabled or self.current_correction == 0:
            return mz_array.copy()
        
        return mz_array + self.current_correction
    
    def merge_ions(self, mz_array: np.ndarray, 
                   intensity_array: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        合并容差范围内的离子
        
        将m/z在容差范围内的离子识别为同一个，合并其强度
        
        参数:
            mz_array: m/z数组
            intensity_array: 强度数组
        
        返回:
            (merged_mz_array, merged_intensity_array)
        """
        if len(mz_array) == 0:
            return np.array([]), np.array([])
        
        # 排序
        sort_idx = np.argsort(mz_array)
        sorted_mz = mz_array[sort_idx]
        sorted_intensity = intensity_array[sort_idx]
        
        # 计算容差(ppm转换为Da)
        tolerance_ppm = self.config.merge_tolerance_ppm
        
        merged_mz = []
        merged_intensity = []
        
        i = 0
        while i < len(sorted_mz):
            current_mz = sorted_mz[i]
            current_intensity = sorted_intensity[i]
            
            # 计算当前m/z的容差范围
            tolerance_da = current_mz * tolerance_ppm / 1e6
            
            # 找到所有在容差范围内的离子
            group_mz = [current_mz]
            group_intensity = [current_intensity]
            
            j = i + 1
            while j < len(sorted_mz):
                if sorted_mz[j] - current_mz <= tolerance_da:
                    group_mz.append(sorted_mz[j])
                    group_intensity.append(sorted_intensity[j])
                    j += 1
                else:
                    break
            
            # 合并：使用强度加权平均m/z
            total_intensity = sum(group_intensity)
            if total_intensity > 0:
                weighted_mz = sum(m * i for m, i in zip(group_mz, group_intensity)) / total_intensity
            else:
                weighted_mz = np.mean(group_mz)
            
            merged_mz.append(weighted_mz)
            merged_intensity.append(total_intensity)
            
            i = j
        
        return np.array(merged_mz), np.array(merged_intensity)
    
    def get_calibration_stats(self) -> Dict:
        """获取校准统计信息"""
        if not self.correction_history:
            return {
                'total_calibrations': 0,
                'current_correction': self.current_correction,
                'last_calibration': None
            }
        
        errors_ppm = [rec['error_ppm'] for rec in self.correction_history]
        
        return {
            'total_calibrations': len(self.correction_history),
            'current_correction': self.current_correction,
            'last_calibration': self.correction_history[-1],
            'mean_error_ppm': np.mean(errors_ppm),
            'std_error_ppm': np.std(errors_ppm),
            'max_error_ppm': np.max(np.abs(errors_ppm))
        }
    
    def export_calibration_history(self, filepath: str):
        """导出校准历史"""
        if not self.correction_history:
            print("[警告] 无校准历史可导出")
            return
        
        df = pd.DataFrame(self.correction_history)
        
        if filepath.endswith('.csv'):
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
        elif filepath.endswith('.xlsx'):
            df.to_excel(filepath, index=False)
        else:
            filepath += '.csv'
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        print(f"[成功] 校准历史已导出: {filepath}")
        print(f"   记录数: {len(df)}")


def test_mass_calibration():
    """测试质量校准功能"""
    print("=" * 60)
    print("质量校准功能测试")
    print("=" * 60)
    
    # 创建配置
    config = LockMassConfig()
    config.enabled = True
    config.lock_mass_mz = 554.2615
    config.tolerance_amu = 0.5  # 增大容差确保能找到
    config.max_signal_intensity = 0  # 0表示不限制强度
    config.merge_tolerance_ppm = 10
    
    # 创建管理器
    manager = MassCalibrationManager(config)
    
    # 模拟数据：包含Lock Mass峰和其他离子
    np.random.seed(42)
    
    # Lock Mass峰（有一些漂移）
    lock_mass_measured = 554.2635  # 实际测量值（有+0.002 Da的漂移）
    
    # 构造测试数据
    mz_data = np.array([
        200.0512, 200.0525,  # 应该合并
        300.1234,
        lock_mass_measured,  # Lock Mass
        600.2341, 600.2358,  # 应该合并
        750.3456
    ])
    
    intensity_data = np.array([
        1000, 800,  # 200的两个峰
        1500,
        5000,  # Lock Mass（高强度）
        2000, 1800,  # 600的两个峰
        1200
    ])
    
    print("\n[1] 原始数据:")
    for mz, intensity in zip(mz_data, intensity_data):
        print(f"   m/z {mz:.4f}: {intensity:.0f}")
    
    # 执行校准
    print("\n[2] 执行Lock Mass校准:")
    correction = manager.calibrate(mz_data, intensity_data)
    
    if correction:
        # 应用校正
        print("\n[3] 应用校正:")
        corrected_mz = manager.apply_correction(mz_data)
        
        print("   原始 m/z → 校正后 m/z:")
        for orig, corr in zip(mz_data, corrected_mz):
            print(f"   {orig:.4f} → {corr:.4f} (Δ{corr-orig:+.4f})")
        
        # 离子合并
        print("\n[4] 离子合并 (容差: ±10 ppm):")
        merged_mz, merged_intensity = manager.merge_ions(corrected_mz, intensity_data)
        
        print(f"   原始离子数: {len(mz_data)}")
        print(f"   合并后离子数: {len(merged_mz)}")
        print("\n   合并结果:")
        for mz, intensity in zip(merged_mz, merged_intensity):
            print(f"   m/z {mz:.4f}: {intensity:.0f}")
    
    # 统计信息
    print("\n[5] 校准统计:")
    stats = manager.get_calibration_stats()
    for key, value in stats.items():
        if key != 'last_calibration':
            print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_mass_calibration()


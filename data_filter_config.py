#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据过滤配置
用于减少数据处理量，提高性能
"""

from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path


@dataclass
class DataFilterConfig:
    """数据过滤配置"""
    
    # 是否启用过滤
    enabled: bool = False
    
    # 选择最高强度的N个峰
    top_n_peaks: int = 1000
    use_top_n: bool = True
    
    # m/z范围过滤
    mz_start: float = 50.0
    mz_stop: float = 1200.0
    use_mz_range: bool = True
    
    # m/z窗口大小
    mz_window: float = 0.02
    
    # 质谱分辨率
    ms_resolution: int = 20000
    
    # 从文件导入目标m/z列表
    import_from_file: bool = False
    target_mass_file: Optional[Path] = None
    target_masses: List[float] = None
    
    def __post_init__(self):
        if self.target_masses is None:
            self.target_masses = []
    
    def should_filter(self) -> bool:
        """是否需要过滤数据"""
        return self.enabled and (self.use_top_n or self.use_mz_range or self.import_from_file)
    
    def get_filter_description(self) -> str:
        """获取过滤描述"""
        if not self.enabled:
            return "未启用数据过滤"
        
        desc_parts = []
        
        if self.use_top_n:
            desc_parts.append(f"Top {self.top_n_peaks} 高强度峰")
        
        if self.use_mz_range:
            desc_parts.append(f"m/z {self.mz_start:.1f}-{self.mz_stop:.1f}")
        
        if self.import_from_file and self.target_masses:
            desc_parts.append(f"{len(self.target_masses)} 个目标m/z")
        
        return " + ".join(desc_parts) if desc_parts else "未配置过滤条件"
    
    def load_target_masses_from_file(self, file_path: Path) -> bool:
        """从文件加载目标m/z列表"""
        try:
            self.target_mass_file = file_path
            self.target_masses = []
            
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            mz = float(line)
                            self.target_masses.append(mz)
                        except ValueError:
                            continue
            
            print(f"[成功] 从文件加载了 {len(self.target_masses)} 个目标m/z")
            return True
            
        except Exception as e:
            print(f"[错误] 加载目标m/z文件失败: {e}")
            return False


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简洁的数据加载器 - 只做一件事：加载imaging数据
"""

import numpy as np
from pathlib import Path


class DataLoader:
    """最简单的数据加载器"""

    def scan_samples(self, workspace_path):
        """扫描工作目录中的所有样本"""
        workspace = Path(workspace_path)
        samples = []

        # 查找所有.raw文件夹
        for item in workspace.iterdir():
            if item.is_dir() and item.suffix.lower() == '.raw':
                imaging_folder = item / "imaging"
                has_data = False

                if imaging_folder.exists():
                    txt_files = list(imaging_folder.glob("*.txt"))
                    if txt_files:
                        has_data = True

                samples.append({
                    'name': item.name,
                    'path': item,
                    'has_imaging': has_data
                })

        return samples

    def load(self, raw_folder):
        """加载imaging数据"""
        raw_path = Path(raw_folder)
        imaging_folder = raw_path / "imaging"
        
        if not imaging_folder.exists():
            return None
        
        # 找到txt文件
        txt_files = list(imaging_folder.glob("*.txt"))
        if not txt_files:
            return None
        
        txt_file = txt_files[0]
        print(f"📂 加载: {txt_file.name}")
        
        # 读取所有行
        with open(txt_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 文件格式（0-based索引）：
        # 第1行（索引0）：空行
        # 第2行（索引1）：0  0.0000 0.0000...（标题行）
        # 第3行（索引2）：   1  2  3  4  5...（列索引号）← 错误的！
        # 第4行（索引3）：255.2327 283.2635...（真实m/z值）← 正确的！
        # 第5行（索引4）开始：数据行
        
        # 读取第4行（索引3）作为m/z值
        mz_line = lines[3].strip().split('\t')
        # 第1列是空或标识，所以也跳过第1列
        mz_bins = np.array([float(x) for x in mz_line[1:] if x])
        
        print(f"   [成功] m/z范围: {mz_bins.min():.4f} ~ {mz_bins.max():.4f}")
        print(f"   前5个m/z: {mz_bins[:5]}")
        
        # 从第5行（索引4）开始是数据
        data_lines = lines[4:]
        
        scan_ids = []
        coords = []
        intensities = []
        
        print(f"   读取 {len(data_lines)} 行数据...")
        
        for line in data_lines:
            parts = line.strip().split('\t')
            if len(parts) < 4:
                continue
            
            try:
                # 数据行格式：scan_id  x  y  intensity1  intensity2  ...
                # 第1列：scan_id
                # 第2列：x坐标
                # 第3列：y坐标
                # 第4列开始：强度值
                scan_id = int(float(parts[0]))
                x = float(parts[1])
                y = float(parts[2])
                # 从第4列（索引3）开始读取强度值
                intensity_values = [float(parts[i]) if i < len(parts) else 0.0 
                                   for i in range(3, 3 + len(mz_bins))]
                
                scan_ids.append(scan_id)
                coords.append([x, y])
                intensities.append(intensity_values)
            except Exception as e:
                continue
        
        # 转换为numpy数组
        scan_ids = np.array(scan_ids)
        coords = np.array(coords)
        intensities = np.array(intensities)
        
        print(f"[成功] 加载完成: {len(scan_ids)}扫描 × {len(mz_bins)} m/z")
        
        return {
            'sample_name': raw_path.stem,
            'raw_path': raw_path,
            'mz_bins': mz_bins,
            'scan_ids': scan_ids,
            'coords': coords,
            'intensity_matrix': intensities,
            'n_scans': len(scan_ids),
            'n_bins': len(mz_bins)
        }
    
    def find_samples(self, workspace):
        """查找所有有imaging数据的样本"""
        workspace_path = Path(workspace)
        samples = []
        
        for raw_folder in workspace_path.glob("*.raw"):
            if (raw_folder / "imaging").exists():
                samples.append(raw_folder)
        
        return sorted(samples)


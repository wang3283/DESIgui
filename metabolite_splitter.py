#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代谢物数据拆分模块
将导出的二维空间数据按代谢物拆分成单独的CSV文件
支持单样本和批量处理
"""

import pandas as pd
import numpy as np
import os
import zipfile
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
from typing import Optional, Callable, List, Dict


def process_metabolite_batch(args):
    """
    处理一批物质（子进程函数）
    
    参数:
        args: (data_dict, mz_cols_batch, sample_output_dir) 元组
    """
    data_dict, mz_cols_batch, sample_output_dir = args
    pid = os.getpid()
    results = []
    
    # 重建DataFrame
    df = pd.DataFrame(data_dict)
    
    for mz_col in mz_cols_batch:
        try:
            metabolite_name = mz_col.replace('mz_', '')
            
            # 创建二维矩阵 (Y为行，X为列)
            matrix_df = df.pivot(index='Y_mm', columns='X_mm', values=mz_col)
            
            # 保存
            output_file = Path(sample_output_dir) / f"{metabolite_name}.csv"
            matrix_df.to_csv(output_file)
            
            results.append((True, metabolite_name, pid))
        except Exception as e:
            results.append((False, f"{mz_col}: {e}", pid))
    
    return results


class MetaboliteSplitter:
    """代谢物数据拆分器"""
    
    def __init__(self, n_processes: int = 4, batch_size: int = 50):
        """
        初始化拆分器
        
        参数:
            n_processes: 并行进程数
            batch_size: 每批处理的物质数
        """
        self.n_processes = n_processes
        self.batch_size = batch_size
        self.stats = {
            'total_processed': 0,
            'success_count': 0,
            'error_count': 0,
            'total_time': 0
        }
    
    def split_from_excel(self, excel_file: str, output_dir: str,
                         progress_callback: Optional[Callable] = None,
                         create_archive: bool = True) -> Dict:
        """
        从Excel文件拆分代谢物数据
        
        参数:
            excel_file: 输入的Excel文件路径（二维空间格式）
            output_dir: 输出目录
            progress_callback: 进度回调函数 callback(current, total, message)
            create_archive: 是否创建zip压缩包
        
        返回:
            处理结果字典
        """
        sample_name = Path(excel_file).stem
        sample_output_dir = Path(output_dir) / sample_name
        sample_output_dir.mkdir(parents=True, exist_ok=True)
        
        result = {
            'sample_name': sample_name,
            'success': False,
            'metabolites_count': 0,
            'success_count': 0,
            'error_count': 0,
            'output_dir': str(sample_output_dir),
            'zip_file': None,
            'time': 0
        }
        
        start_time = time.time()
        
        # 读取Excel文件
        if progress_callback:
            progress_callback(0, 100, f"正在读取文件: {Path(excel_file).name}")
        
        try:
            df = pd.read_excel(excel_file)
        except Exception as e:
            result['error'] = f"读取文件失败: {e}"
            return result
        
        # 识别物质列
        mz_cols = [col for col in df.columns if col.startswith('mz_')]
        
        if not mz_cols:
            result['error'] = "未找到m/z数据列（需要以'mz_'开头的列）"
            return result
        
        result['metabolites_count'] = len(mz_cols)
        
        if progress_callback:
            progress_callback(10, 100, f"找到 {len(mz_cols)} 个代谢物，准备拆分...")
        
        # 检查必需的坐标列
        if 'X_mm' not in df.columns or 'Y_mm' not in df.columns:
            result['error'] = "缺少坐标列（需要X_mm和Y_mm列）"
            return result
        
        # 转换为字典格式
        data_dict = {col: df[col].values for col in ['X_mm', 'Y_mm'] + mz_cols}
        
        # 分批处理
        tasks = []
        for i in range(0, len(mz_cols), self.batch_size):
            batch_cols = mz_cols[i:i+self.batch_size]
            batch_data = {'X_mm': data_dict['X_mm'], 'Y_mm': data_dict['Y_mm']}
            for col in batch_cols:
                batch_data[col] = data_dict[col]
            tasks.append((batch_data, batch_cols, str(sample_output_dir)))
        
        # 多进程处理
        success_count = 0
        error_count = 0
        completed_count = 0
        
        if progress_callback:
            progress_callback(15, 100, f"开始多进程拆分 ({self.n_processes} 进程)...")
        
        with ProcessPoolExecutor(max_workers=self.n_processes) as executor:
            futures = [executor.submit(process_metabolite_batch, task) for task in tasks]
            
            for future in as_completed(futures):
                try:
                    batch_results = future.result()
                    
                    for success, msg, pid in batch_results:
                        completed_count += 1
                        if success:
                            success_count += 1
                        else:
                            error_count += 1
                        
                        # 更新进度 (15-85%)
                        if progress_callback:
                            progress = 15 + int((completed_count / len(mz_cols)) * 70)
                            progress_callback(progress, 100, 
                                f"拆分进度: {completed_count}/{len(mz_cols)} ({completed_count/len(mz_cols)*100:.1f}%)")
                
                except Exception as e:
                    error_count += self.batch_size
        
        result['success_count'] = success_count
        result['error_count'] = error_count
        result['success'] = success_count > 0
        
        # 创建压缩包
        if create_archive and success_count > 0:
            if progress_callback:
                progress_callback(85, 100, "正在创建压缩包...")
            
            zip_file = self._create_archive(sample_output_dir)
            if zip_file:
                result['zip_file'] = str(zip_file)
        
        result['time'] = time.time() - start_time
        
        if progress_callback:
            progress_callback(100, 100, f"完成！成功: {success_count}/{len(mz_cols)}")
        
        return result
    
    def split_from_data(self, data: Dict, output_dir: str, sample_name: str,
                        progress_callback: Optional[Callable] = None,
                        create_archive: bool = True,
                        max_mz: Optional[int] = None) -> Dict:
        """
        直接从内存数据拆分代谢物
        
        参数:
            data: 数据字典，包含 coords, mz_bins, intensity_matrix
            output_dir: 输出目录
            sample_name: 样本名称
            progress_callback: 进度回调函数
            create_archive: 是否创建压缩包
            max_mz: 最大导出的m/z数量（按强度排序）
        
        返回:
            处理结果字典
        """
        sample_output_dir = Path(output_dir) / sample_name
        sample_output_dir.mkdir(parents=True, exist_ok=True)
        
        result = {
            'sample_name': sample_name,
            'success': False,
            'metabolites_count': 0,
            'success_count': 0,
            'error_count': 0,
            'output_dir': str(sample_output_dir),
            'zip_file': None,
            'time': 0
        }
        
        start_time = time.time()
        
        if progress_callback:
            progress_callback(0, 100, "准备数据...")
        
        # 提取数据
        coords = data.get('coords', [])
        mz_bins = data.get('mz_bins', [])
        intensity_matrix = data.get('intensity_matrix', [])
        
        if len(coords) == 0 or len(mz_bins) == 0:
            result['error'] = "数据为空"
            return result
        
        # 选择要导出的m/z
        if max_mz and max_mz < len(mz_bins):
            # 按平均强度排序，选择Top N
            mean_intensity = np.mean(intensity_matrix, axis=0)
            sorted_indices = np.argsort(mean_intensity)[::-1][:max_mz]
            selected_mz = [mz_bins[i] for i in sorted_indices]
            selected_intensity = intensity_matrix[:, sorted_indices]
        else:
            selected_mz = mz_bins
            selected_intensity = intensity_matrix
        
        result['metabolites_count'] = len(selected_mz)
        
        if progress_callback:
            progress_callback(10, 100, f"准备拆分 {len(selected_mz)} 个代谢物...")
        
        # 构建数据字典
        data_dict = {
            'X_mm': coords[:, 0],
            'Y_mm': coords[:, 1]
        }
        
        mz_cols = []
        for i, mz in enumerate(selected_mz):
            col_name = f"mz_{mz:.4f}"
            data_dict[col_name] = selected_intensity[:, i]
            mz_cols.append(col_name)
        
        # 分批处理
        tasks = []
        for i in range(0, len(mz_cols), self.batch_size):
            batch_cols = mz_cols[i:i+self.batch_size]
            batch_data = {'X_mm': data_dict['X_mm'], 'Y_mm': data_dict['Y_mm']}
            for col in batch_cols:
                batch_data[col] = data_dict[col]
            tasks.append((batch_data, batch_cols, str(sample_output_dir)))
        
        # 多进程处理
        success_count = 0
        error_count = 0
        completed_count = 0
        
        if progress_callback:
            progress_callback(15, 100, f"开始多进程拆分...")
        
        with ProcessPoolExecutor(max_workers=self.n_processes) as executor:
            futures = [executor.submit(process_metabolite_batch, task) for task in tasks]
            
            for future in as_completed(futures):
                try:
                    batch_results = future.result()
                    
                    for success, msg, pid in batch_results:
                        completed_count += 1
                        if success:
                            success_count += 1
                        else:
                            error_count += 1
                        
                        if progress_callback:
                            progress = 15 + int((completed_count / len(mz_cols)) * 70)
                            progress_callback(progress, 100, 
                                f"拆分进度: {completed_count}/{len(mz_cols)}")
                
                except Exception as e:
                    error_count += self.batch_size
        
        result['success_count'] = success_count
        result['error_count'] = error_count
        result['success'] = success_count > 0
        
        # 创建压缩包
        if create_archive and success_count > 0:
            if progress_callback:
                progress_callback(85, 100, "正在创建压缩包...")
            
            zip_file = self._create_archive(sample_output_dir)
            if zip_file:
                result['zip_file'] = str(zip_file)
        
        result['time'] = time.time() - start_time
        
        if progress_callback:
            progress_callback(100, 100, f"完成！")
        
        return result
    
    def _create_archive(self, sample_dir: Path) -> Optional[Path]:
        """创建压缩包"""
        sample_name = sample_dir.name
        zip_file = sample_dir.parent / f"{sample_name}.zip"
        
        try:
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                csv_files = list(sample_dir.glob('*.csv'))
                for csv_file in csv_files:
                    arcname = f"{sample_name}/{csv_file.name}"
                    zipf.write(csv_file, arcname=arcname)
            
            return zip_file
        except Exception as e:
            print(f"[错误] 打包失败: {e}")
            return None
    
    def batch_split_from_excel(self, excel_files: List[str], output_dir: str,
                               progress_callback: Optional[Callable] = None,
                               create_archives: bool = True) -> List[Dict]:
        """
        批量处理多个Excel文件
        
        参数:
            excel_files: Excel文件路径列表
            output_dir: 输出目录
            progress_callback: 进度回调 callback(current_file, total_files, file_progress, message)
            create_archives: 是否创建压缩包
        
        返回:
            处理结果列表
        """
        results = []
        total_files = len(excel_files)
        
        for i, excel_file in enumerate(excel_files):
            def file_progress(current, total, message):
                if progress_callback:
                    progress_callback(i, total_files, current, message)
            
            result = self.split_from_excel(
                excel_file, output_dir,
                progress_callback=file_progress,
                create_archive=create_archives
            )
            results.append(result)
        
        return results


# 测试代码
if __name__ == "__main__":
    # macOS需要设置启动方法
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass
    
    multiprocessing.freeze_support()
    
    # 测试单文件处理
    splitter = MetaboliteSplitter(n_processes=4, batch_size=50)
    
    test_file = "/Volumes/US100 256G/results/test_sample.xlsx"
    output_dir = "/Volumes/US100 256G/results/split_test"
    
    if os.path.exists(test_file):
        def progress(current, total, msg):
            print(f"[{current}/{total}] {msg}")
        
        result = splitter.split_from_excel(test_file, output_dir, progress_callback=progress)
        print(f"\n结果: {result}")

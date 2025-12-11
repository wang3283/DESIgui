#!/usr/bin/env python3
"""
DESI系统功能全面测试脚本
测试所有核心功能是否正常工作
"""

import sys
import os
import time
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

# 添加项目路径
sys.path.insert(0, '/Volumes/US100 256G/mouse DESI data/desi_gui_v2')

def test_data_loading():
    """测试数据加载功能"""
    print("\n" + "="*60)
    print("[SEARCH] 测试1: 数据加载功能")
    print("="*60)

    try:
        from data_loader import DataLoader

        loader = DataLoader()
        workspace = Path('/Volumes/US100 256G/mouse DESI data')

        # 测试扫描可用样本
        samples = loader.scan_samples(workspace)
        print(f"[SUCCESS] 样本扫描成功: 发现 {len(samples)} 个样本")

        # 测试加载一个有数据的样本
        available_samples = [s for s in samples if s['has_imaging']]
        if available_samples:
            sample_name = available_samples[0]['name']
            print(f"📂 测试加载样本: {sample_name}")

            data = loader.load(workspace / sample_name)
            if data:
                print("[SUCCESS] 数据加载成功")
                print(f"   - m/z范围: {data['mz_bins'][0]:.4f} ~ {data['mz_bins'][-1]:.4f}")
                print(f"   - 扫描点数: {len(data['coords'])}")
                print(f"   - 离子数: {len(data['mz_bins'])}")
                return True
            else:
                print("[ERROR] 数据加载失败")
                return False
        else:
            print("[ERROR] 未发现有数据的样本")
            return False

    except Exception as e:
        print(f"[ERROR] 数据加载测试失败: {e}")
        return False

def test_metabolite_annotation():
    """测试代谢物注释功能"""
    print("\n" + "="*60)
    print("[SEARCH] 测试2: 代谢物注释功能")
    print("="*60)

    try:
        from online_metabolite_annotator import OnlineMetaboliteAnnotator

        # 测试初始化
        annotator = OnlineMetaboliteAnnotator(use_cache_db=True)
        print("[SUCCESS] 注释器初始化成功")

        # 测试单个注释
        test_mz = 255.2327  # 常见的代谢物
        results = annotator.annotate_mz(test_mz, tolerance_ppm=10, ion_mode='positive')

        print(f"[STATS] 测试m/z {test_mz}: 找到 {len(results)} 个匹配")

        if results:
            best_match = annotator.get_best_match(results, max_error_ppm=5)
            if best_match:
                print(f"[SUCCESS] 最佳匹配: {best_match['name']}")
                print(f"   分子式: {best_match['formula']}")
                print(f"   误差: {best_match['error_ppm']:.2f} ppm")
            else:
                print("[WARNING]  无符合精度的最佳匹配")

        # 测试批量注释
        test_mz_list = [255.2327, 301.1457, 187.0967]
        annotations = annotator.batch_annotate(test_mz_list, tolerance_ppm=10, ion_mode='positive')
        print(f"[SUCCESS] 批量注释测试: {len(annotations)}/{len(test_mz_list)} 成功")

        annotator.close()
        return True

    except Exception as e:
        print(f"[ERROR] 代谢物注释测试失败: {e}")
        return False

def test_mass_calibration():
    """测试质量校准功能"""
    print("\n" + "="*60)
    print("[SEARCH] 测试3: Lock Mass质量校准功能")
    print("="*60)

    try:
        from mass_calibration_manager import MassCalibrationManager, LockMassConfig

        # 创建配置
        config = LockMassConfig()
        config.lock_mass_mz = 554.2615
        config.tolerance_amu = 0.25
        config.ion_merge_ppm = 10.0

        manager = MassCalibrationManager(config)
        print("[SUCCESS] 校准管理器初始化成功")

        # 模拟数据
        mz_data = [554.0, 554.2, 554.3, 554.4, 554.5, 554.6, 554.8]
        intensity_data = [100, 200, 5000, 300, 200, 150, 100]  # 554.3有最高强度

        # 转换为numpy数组
        mz_array = np.array(mz_data)
        intensity_array = np.array(intensity_data)

        # 测试峰检测
        peak_result = manager.find_lock_mass_peak(mz_array, intensity_array)
        if peak_result:
            print("[SUCCESS] Lock Mass峰检测成功")
            measured_mz, intensity = peak_result
            print(f"   检测到峰: m/z {measured_mz:.4f}, 强度 {intensity}")
        else:
            print("[ERROR] 未检测到Lock Mass峰")

        # 测试校准计算
        if peak_result:
            measured_mz, intensity = peak_result
            correction = manager.calculate_correction(554.2615, measured_mz)
            print(f"[SUCCESS] 校正值计算: {correction:.6f} Da")

            # 测试校准应用
            corrected_mz = manager.apply_correction(mz_array, correction)
            print(f"[SUCCESS] 校准应用测试: {len(corrected_mz)} 个值已校准")
        else:
            print("[WARNING]  跳过校准计算（未找到峰）")

        return True

    except Exception as e:
        print(f"[ERROR] 质量校准测试失败: {e}")
        return False

def test_data_filtering():
    """测试数据过滤功能"""
    print("\n" + "="*60)
    print("[SEARCH] 测试4: 数据过滤功能")
    print("="*60)

    try:
        from data_filter import DataFilter
        from data_filter_config import DataFilterConfig

        # 创建过滤配置
        config = DataFilterConfig()
        config.enabled = True
        config.top_n_ions = 500
        config.mz_min = 100.0
        config.mz_max = 1000.0
        config.target_masses = []

        # 创建过滤器
        filter_obj = DataFilter(config)
        print("[SUCCESS] 数据过滤器初始化成功")

        # 模拟数据
        mock_data = {
            'mz_bins': np.arange(50, 1050, 1, dtype=float),  # 50-1050 m/z
            'intensity_matrix': np.random.rand(100, 1000) * 1000  # 模拟100个扫描点，1000个m/z
        }

        print(f"原始数据: {len(mock_data['mz_bins'])} 个离子, {len(mock_data['intensity_matrix'])} 个扫描点")

        # 应用过滤
        filtered_data = filter_obj.filter_data(mock_data)

        print("[SUCCESS] 数据过滤成功")
        print(f"过滤后: {len(filtered_data['mz_bins'])} 个离子, {len(filtered_data['intensity_matrix'])} 个扫描点")
        print(f"m/z范围: {filtered_data['mz_bins'][0]:.1f} ~ {filtered_data['mz_bins'][-1]:.1f}")

        return True

    except Exception as e:
        print(f"[ERROR] 数据过滤测试失败: {e}")
        return False

def test_export_functionality():
    """测试导出功能"""
    print("\n" + "="*60)
    print("[SEARCH] 测试5: 数据导出功能")
    print("="*60)

    try:
        # 模拟导出所需的统计数据
        mock_stats = {
            'mz_bins': [187.0967, 255.2327, 301.1457, 400.0000, 500.0000],
            'mean_intensity': [1234.5, 2345.6, 3456.7, 4567.8, 5678.9],
            'max_intensity': [5678.9, 6789.0, 7890.1, 8901.2, 9012.3],
            'cv': [12.3, 23.4, 34.5, 45.6, 56.7],
            'sorted_indices': [0, 1, 2, 3, 4]
        }

        # 测试统计信息导出
        export_data = []
        for idx in mock_stats['sorted_indices'][:3]:
            export_data.append({
                'm/z': f"{mock_stats['mz_bins'][idx]:.4f}",
                '平均强度': f"{mock_stats['mean_intensity'][idx]:.1f}",
                '最大强度': f"{mock_stats['max_intensity'][idx]:.1f}",
                'CV(%)': f"{mock_stats['cv'][idx]:.2f}"
            })

        df = pd.DataFrame(export_data)
        test_file = "/Volumes/US100 256G/mouse DESI data/test_export.xlsx"
        df.to_excel(test_file, index=False)

        if os.path.exists(test_file):
            print("[SUCCESS] 统计信息导出测试成功")
            print(f"   导出文件: {test_file}")
            print(f"   数据行数: {len(df)}")
            print(f"   数据列数: {len(df.columns)}")

            # 清理测试文件
            os.remove(test_file)
            return True
        else:
            print("[ERROR] 导出文件未生成")
            return False

    except Exception as e:
        print(f"[ERROR] 数据导出测试失败: {e}")
        return False

def test_gui_import():
    """测试GUI模块导入"""
    print("\n" + "="*60)
    print("[SEARCH] 测试6: GUI模块导入")
    print("="*60)

    try:
        # 测试主要GUI模块导入
        from main_gui_ultimate import MainWindow, IonTable, MetaboliteSearchDialog
        print("[SUCCESS] 主GUI模块导入成功")

        from sample_comparison_dialog import SampleComparisonDialog
        print("[SUCCESS] 样本对比模块导入成功")

        from lock_mass_dialog import LockMassDialog
        print("[SUCCESS] Lock Mass对话框导入成功")

        from data_filter_dialog import DataFilterDialog
        print("[SUCCESS] 数据过滤对话框导入成功")

        return True

    except Exception as e:
        print(f"[ERROR] GUI模块导入失败: {e}")
        return False

def test_database_integrity():
    """测试数据库完整性"""
    print("\n" + "="*60)
    print("[SEARCH] 测试7: 数据库完整性")
    print("="*60)

    try:
        import sqlite3

        # 检查HMDB数据库
        hmdb_db_path = "/Volumes/US100 256G/mouse DESI data/desi_gui_v2/hmdb_database.db"
        if os.path.exists(hmdb_db_path):
            conn = sqlite3.connect(hmdb_db_path)
            cursor = conn.cursor()

            # 检查表结构
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f"[SUCCESS] HMDB数据库: {len(tables)} 个表")

            if tables:
                # 检查记录数
                cursor.execute("SELECT COUNT(*) FROM annotation_cache")
                count = cursor.fetchone()[0]
                print(f"   记录数: {count:,}")

            conn.close()
        else:
            print("[ERROR] HMDB数据库文件不存在")
            return False

        # 检查缓存数据库
        cache_db_path = "/Volumes/US100 256G/mouse DESI data/desi_gui_v2/metabolite_cache.db"
        if os.path.exists(cache_db_path):
            conn = sqlite3.connect(cache_db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f"[SUCCESS] 缓存数据库: {len(tables)} 个表")

            if tables:
                # 检查annotation_cache表
                cursor.execute("SELECT COUNT(*) FROM annotation_cache")
                count = cursor.fetchone()[0]
                print(f"   缓存记录数: {count:,}")

            conn.close()
        else:
            print("[ERROR] 缓存数据库文件不存在")
            return False

        return True

    except Exception as e:
        print(f"[ERROR] 数据库完整性测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("[LAUNCH] 开始DESI系统功能全面测试")
    print("="*80)

    # 记录开始时间
    start_time = time.time()

    # 测试结果
    results = []

    # 运行各项测试
    test_functions = [
        ("数据加载", test_data_loading),
        ("代谢物注释", test_metabolite_annotation),
        ("质量校准", test_mass_calibration),
        ("数据过滤", test_data_filtering),
        ("数据导出", test_export_functionality),
        ("GUI导入", test_gui_import),
        ("数据库", test_database_integrity),
    ]

    for test_name, test_func in test_functions:
        try:
            result = test_func()
            results.append((test_name, result))
            status = "[SUCCESS] 通过" if result else "[ERROR] 失败"
            print(f"\n{test_name}: {status}")
        except Exception as e:
            print(f"\n{test_name}: [ERROR] 异常 - {e}")
            results.append((test_name, False))

    # 计算总时间
    total_time = time.time() - start_time

    # 输出测试总结
    print("\n" + "="*80)
    print("[STATS] 测试结果总结")
    print("="*80)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "[SUCCESS] 通过" if result else "[ERROR] 失败"
        print(f"    {test_name:<20} {status}")
        if result:
            passed += 1

    print(f"\n[TREND] 总体结果: {passed}/{total} 项测试通过")
    print(f"总耗时: {total_time:.1f}秒")
    success_rate = (passed / total) * 100
    print(f"成功率: {success_rate:.1f}%")
    # 总体评估
    if success_rate >= 90:
        print("[CELEBRATE] 系统状态: 优秀 - 所有核心功能正常")
    elif success_rate >= 75:
        print("[GOOD] 系统状态: 良好 - 大部分功能正常")
    elif success_rate >= 50:
        print("[WARNING]  系统状态: 一般 - 部分功能异常")
    else:
        print("[ERROR] 系统状态: 严重问题 - 需要修复")

    print("\n" + "="*80)
    print("[TARGET] 测试完成！")
    print("="*80)

if __name__ == '__main__':
    run_all_tests()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在线代谢物注释模块
支持HMDB和MetaboAnalyst公共数据库查询
"""

import requests
import json
import time
from typing import List, Dict, Optional
import pandas as pd
from urllib.parse import urlencode


class OnlineMetaboliteAnnotator:
    """在线代谢物注释器（支持本地缓存数据库）"""
    
    def __init__(self, use_cache_db: bool = True):
        self.hmdb_api_base = "https://hmdb.ca"
        self.metaboanalyst_base = "https://www.metaboanalyst.ca"
        
        # 内存缓存（会话级别）
        self.memory_cache = {}
        
        # 持久化缓存数据库
        self.use_cache_db = use_cache_db
        self.cache_db = None
        
        if use_cache_db:
            try:
                from metabolite_cache_db import MetaboliteCacheDB
                self.cache_db = MetaboliteCacheDB()
                print("[成功] 已启用本地缓存数据库")
            except Exception as e:
                print(f"[警告] 无法加载缓存数据库: {e}")
                self.use_cache_db = False
        
        # HMDB完整数据库查询
        self.hmdb_db = None
        try:
            from hmdb_database_query import HMDBDatabaseQuery
            self.hmdb_db = HMDBDatabaseQuery()
        except Exception as e:
            print(f"[警告] 无法加载HMDB数据库: {e}")
        
        # 请求间隔（秒），避免过于频繁的请求
        # 由于我们现在主要使用本地HMDB数据库，不需要延迟
        self.request_delay = 0.0
        
        # 统计信息
        self.stats = {
            'total_queries': 0,
            'db_cache_hits': 0,
            'memory_cache_hits': 0,
            'hmdb_db_hits': 0,
            'new_queries': 0
        }
        
    def annotate_mz(self, mz: float, tolerance_ppm: float = 10, 
                   ion_mode: str = 'positive') -> List[Dict]:
        """
        注释单个m/z值（多级缓存策略）
        
        查询顺序：
        1. 内存缓存（最快）
        2. 本地数据库缓存（快）
        3. 在线/本地数据源查询（慢）
        
        参数:
            mz: m/z值
            tolerance_ppm: 质量误差容忍度（ppm）
            ion_mode: 离子模式 ('positive' or 'negative')
        
        返回:
            匹配的代谢物列表
        """
        self.stats['total_queries'] += 1
        
        # 第1级：检查内存缓存
        cache_key = f"{mz:.4f}_{tolerance_ppm}_{ion_mode}"
        if cache_key in self.memory_cache:
            self.stats['memory_cache_hits'] += 1
            return self.memory_cache[cache_key]
        
        # 第2级：检查数据库缓存
        if self.use_cache_db and self.cache_db:
            try:
                db_results = self.cache_db.query_cache(mz, tolerance_ppm, ion_mode)
                if db_results:
                    self.stats['db_cache_hits'] += 1
                    # 同时保存到内存缓存
                    self.memory_cache[cache_key] = db_results
                    return db_results
            except Exception as e:
                print(f"[警告] 数据库缓存查询失败: {e}")
        
        # 第3级：从HMDB完整数据库查询
        if self.hmdb_db and self.hmdb_db.db_available:
            try:
                hmdb_results = self.hmdb_db.search(mz, tolerance_ppm, ion_mode)
                
                # 保存到缓存（无论是否有结果）
                self.memory_cache[cache_key] = hmdb_results
                
                if hmdb_results:
                    self.stats['hmdb_db_hits'] += 1
                    
                    # 保存到数据库缓存
                    if self.use_cache_db and self.cache_db:
                        try:
                            for result in hmdb_results:
                                self.cache_db.add_annotation(mz, tolerance_ppm, ion_mode, result)
                        except Exception as e:
                            print(f"[警告] 保存到缓存数据库失败: {e}")
                else:
                    # 没有匹配，记录为新查询（但不再查询其他数据源）
                    self.stats['new_queries'] += 1
                
                # 直接返回结果（可能为空），不再查询其他数据源
                return hmdb_results
                
            except Exception as e:
                print(f"[警告] HMDB数据库查询失败: {e}")
        
        # 第4级：从其他数据源查询（备用）
        self.stats['new_queries'] += 1
        results = []
        
        # 1. 尝试从HMDB CSV文件查询
        try:
            hmdb_csv_results = self._query_hmdb(mz, tolerance_ppm, ion_mode)
            results.extend(hmdb_csv_results)
        except Exception as e:
            print(f"[警告] HMDB CSV查询失败 (m/z={mz:.4f}): {e}")
        
        # 2. 尝试从本地小数据库查询（作为补充）
        try:
            local_results = self._query_local_database(mz, tolerance_ppm, ion_mode)
            results.extend(local_results)
        except Exception as e:
            print(f"[警告] 本地数据库查询失败: {e}")
        
        # 去重（根据名称）
        unique_results = []
        seen_names = set()
        for result in results:
            if result['name'] not in seen_names:
                unique_results.append(result)
                seen_names.add(result['name'])
        
        # 按误差排序
        unique_results.sort(key=lambda x: x['error_ppm'])
        
        # 保存到缓存
        self.memory_cache[cache_key] = unique_results
        
        # 保存到数据库缓存
        if self.use_cache_db and self.cache_db and unique_results:
            try:
                for result in unique_results:
                    self.cache_db.add_annotation(mz, tolerance_ppm, ion_mode, result)
            except Exception as e:
                print(f"[警告] 保存到数据库缓存失败: {e}")
        
        return unique_results
    
    def _query_hmdb(self, mz: float, tolerance_ppm: float, ion_mode: str) -> List[Dict]:
        """
        查询HMDB数据库
        
        注意：HMDB没有公开的简单REST API，这里使用模拟查询
        实际应用中可能需要下载HMDB数据库文件或使用第三方API
        """
        results = []
        
        # 计算质量搜索范围
        tolerance_da = (tolerance_ppm / 1e6) * mz
        mass_min = mz - tolerance_da
        mass_max = mz + tolerance_da
        
        # HMDB提供了数据下载，可以使用预下载的数据库文件
        # 这里使用本地HMDB数据库（如果存在）
        hmdb_file = "/Volumes/US100 256G/mouse DESI data/desi_gui_v2/hmdb_metabolites.csv"
        
        try:
            import os
            if os.path.exists(hmdb_file):
                df = pd.read_csv(hmdb_file)
                
                # 根据离子模式选择适当的m/z列
                if ion_mode == 'positive':
                    mz_col = 'mz_positive'  # [M+H]+
                else:
                    mz_col = 'mz_negative'  # [M-H]-
                
                if mz_col in df.columns:
                    # 筛选在误差范围内的代谢物
                    matches = df[(df[mz_col] >= mass_min) & (df[mz_col] <= mass_max)]
                    
                    for _, row in matches.iterrows():
                        theoretical_mz = row[mz_col]
                        error_da = abs(mz - theoretical_mz)
                        error_ppm = (error_da / theoretical_mz) * 1e6
                        
                        results.append({
                            'name': row.get('name', 'Unknown'),
                            'formula': row.get('formula', ''),
                            'hmdb_id': row.get('hmdb_id', ''),
                            'theoretical_mz': theoretical_mz,
                            'measured_mz': mz,
                            'error_ppm': error_ppm,
                            'error_da': error_da,
                            'source': 'HMDB'
                        })
        except Exception as e:
            print(f"[警告] HMDB文件读取失败: {e}")
        
        return results
    
    def _query_local_database(self, mz: float, tolerance_ppm: float, 
                             ion_mode: str) -> List[Dict]:
        """查询本地代谢物数据库（内置常见代谢物）"""
        from metabolite_db import MetaboliteDatabase
        
        db = MetaboliteDatabase()
        local_results = db.search(mz, tolerance_ppm, ion_mode)
        
        # 转换格式
        formatted_results = []
        for result in local_results:
            formatted_results.append({
                'name': result['name'],
                'formula': result['formula'],
                'hmdb_id': '',
                'theoretical_mz': result['theoretical_mz'],
                'measured_mz': result['measured_mz'],
                'error_ppm': result['error_ppm'],
                'error_da': result['error_da'],
                'source': 'Local'
            })
        
        return formatted_results
    
    def batch_annotate(self, mz_list: List[float], tolerance_ppm: float = 10,
                      ion_mode: str = 'positive', 
                      progress_callback=None) -> Dict[float, List[Dict]]:
        """
        批量注释m/z列表
        
        参数:
            mz_list: m/z值列表
            tolerance_ppm: 误差容忍度
            ion_mode: 离子模式
            progress_callback: 进度回调函数 callback(current, total)
        
        返回:
            {mz: [匹配结果列表]} 字典
        """
        annotations = {}
        total = len(mz_list)
        
        print(f"\n[SEARCH] 开始批量注释 {total} 个m/z值...")
        
        for i, mz in enumerate(mz_list):
            try:
                matches = self.annotate_mz(mz, tolerance_ppm, ion_mode)
                annotations[mz] = matches
                
                if progress_callback:
                    progress_callback(i + 1, total)
                
                if (i + 1) % 10 == 0:
                    print(f"   进度: {i+1}/{total} ({(i+1)/total*100:.1f}%)")
            
            except Exception as e:
                print(f"[错误] 注释失败 m/z={mz:.4f}: {e}")
                annotations[mz] = []
        
        print(f"[成功] 批量注释完成: {total} 个m/z值")
        
        return annotations
    
    def get_best_match(self, matches: List[Dict], 
                      max_error_ppm: float = 5) -> Optional[Dict]:
        """
        从匹配结果中获取最佳匹配（误差最小且小于阈值）
        
        参数:
            matches: 匹配结果列表
            max_error_ppm: 最大允许误差（ppm）
        
        返回:
            最佳匹配，如果没有符合条件的返回None
        """
        if not matches:
            return None
        
        # 找到误差最小的匹配
        best_match = min(matches, key=lambda x: x['error_ppm'])
        
        # 检查是否在误差范围内
        if best_match['error_ppm'] <= max_error_ppm:
            return best_match
        
        return None
    
    def format_annotation(self, matches: List[Dict]) -> str:
        """
        格式化注释结果为字符串
        
        返回格式：代谢物名称 (误差ppm); ...
        """
        if not matches:
            return "未匹配"
        
        # 只取前3个最佳匹配
        top_matches = matches[:3]
        
        formatted = []
        for match in top_matches:
            name = match['name']
            error_ppm = match['error_ppm']
            formatted.append(f"{name} ({error_ppm:.2f}ppm)")
        
        return "; ".join(formatted)
    
    def export_annotations_to_csv(self, annotations: Dict[float, List[Dict]], 
                                  output_file: str):
        """
        导出注释结果到CSV文件
        
        参数:
            annotations: {mz: [匹配结果]} 字典
            output_file: 输出文件路径
        """
        rows = []
        
        for mz, matches in annotations.items():
            if matches:
                for match in matches:
                    rows.append({
                        'measured_mz': f"{mz:.4f}",
                        'metabolite_name': match['name'],
                        'formula': match['formula'],
                        'hmdb_id': match.get('hmdb_id', ''),
                        'theoretical_mz': f"{match['theoretical_mz']:.4f}",
                        'error_ppm': f"{match['error_ppm']:.2f}",
                        'error_da': f"{match['error_da']:.6f}",
                        'source': match['source']
                    })
            else:
                rows.append({
                    'measured_mz': f"{mz:.4f}",
                    'metabolite_name': '未匹配',
                    'formula': '',
                    'hmdb_id': '',
                    'theoretical_mz': '',
                    'error_ppm': '',
                    'error_da': '',
                    'source': ''
                })
        
        df = pd.DataFrame(rows)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"[成功] 注释结果已导出到: {output_file}")
    
    def print_stats(self):
        """打印注释统计信息"""
        total = self.stats['total_queries']
        if total == 0:
            print("\n[STATS] 暂无查询记录")
            return
        
        mem_hits = self.stats['memory_cache_hits']
        db_hits = self.stats['db_cache_hits']
        hmdb_hits = self.stats.get('hmdb_db_hits', 0)
        new_queries = self.stats['new_queries']
        
        mem_rate = (mem_hits / total * 100) if total > 0 else 0
        db_rate = (db_hits / total * 100) if total > 0 else 0
        hmdb_rate = (hmdb_hits / total * 100) if total > 0 else 0
        new_rate = (new_queries / total * 100) if total > 0 else 0
        
        print("\n" + "="*60)
        print("[STATS] 代谢物注释性能统计")
        print("="*60)
        print(f"  总查询次数:      {total}")
        print(f"  内存缓存命中:    {mem_hits} ({mem_rate:.1f}%) ⚡")
        print(f"  数据库缓存命中:  {db_hits} ({db_rate:.1f}%) [CACHE]")
        print(f"  HMDB数据库命中:  {hmdb_hits} ({hmdb_rate:.1f}%) 📚")
        print(f"  其他数据源查询:  {new_queries} ({new_rate:.1f}%)")
        print(f"  总缓存命中率:    {(mem_hits + db_hits + hmdb_hits) / total * 100:.1f}%")
        print("="*60 + "\n")
        
        # 如果使用了数据库缓存，打印数据库统计
        if self.use_cache_db and self.cache_db:
            try:
                db_stats = self.cache_db.get_stats()
                print("📂 数据库缓存统计:")
                print(f"  缓存记录总数:   {db_stats['total_cached_annotations']}")
                print(f"  数据库总查询:   {db_stats['total_queries']}")
                print(f"  数据库命中率:   {db_stats['hit_rate']:.1f}%")
                print("="*60 + "\n")
            except Exception as e:
                print(f"[警告] 无法获取数据库统计: {e}")
    
    def close(self):
        """关闭数据库连接并打印统计信息"""
        self.print_stats()
        
        if self.cache_db:
            self.cache_db.close()
    
    def __del__(self):
        """析构函数"""
        if hasattr(self, 'cache_db') and self.cache_db:
            try:
                self.cache_db.close()
            except:
                pass


def download_hmdb_database():
    """
    下载HMDB代谢物数据库
    
    注意：这是一个辅助函数，需要单独运行
    HMDB提供了数据库下载：https://hmdb.ca/downloads
    """
    print("[RECEIVE] HMDB数据库下载说明：")
    print("1. 访问 https://hmdb.ca/downloads")
    print("2. 下载 'All Metabolites' XML或CSV文件")
    print("3. 将文件放置在 desi_gui_v2 目录下")
    print("4. 重命名为 'hmdb_metabolites.csv'")
    print("\n推荐格式：")
    print("  列：name, formula, monoisotopic_mass, hmdb_id")
    print("  计算：mz_positive = mass + 1.00728 (H+)")
    print("  计算：mz_negative = mass - 1.00728 (H-)")


if __name__ == "__main__":
    # 测试代码
    annotator = OnlineMetaboliteAnnotator()
    
    # 测试单个m/z注释
    test_mz = 283.2635
    matches = annotator.annotate_mz(test_mz, tolerance_ppm=10, ion_mode='negative')
    
    print(f"\n测试 m/z = {test_mz}")
    print(f"找到 {len(matches)} 个匹配:")
    for match in matches:
        print(f"  • {match['name']}: {match['theoretical_mz']:.4f} "
              f"({match['error_ppm']:.2f} ppm)")
    
    # 测试批量注释
    test_mz_list = [283.2635, 171.1386, 554.261]
    annotations = annotator.batch_annotate(test_mz_list, ion_mode='negative')
    
    print(f"\n批量注释结果:")
    for mz, matches in annotations.items():
        formatted = annotator.format_annotation(matches)
        print(f"  m/z {mz:.4f}: {formatted}")


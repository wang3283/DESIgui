#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HMDB数据库查询模块

用于从hmdb_database.db快速查询代谢物信息
"""

import sqlite3
from pathlib import Path
from typing import List, Dict


class HMDBDatabaseQuery:
    """HMDB数据库查询类"""
    
    def __init__(self, db_path: str = None):
        """
        初始化HMDB数据库查询
        
        参数:
            db_path: HMDB数据库路径，默认为hmdb_database.db
        """
        if db_path is None:
            db_path = Path(__file__).parent / "hmdb_database.db"
        
        self.db_path = str(db_path)
        
        # 检查数据库是否存在
        if not Path(self.db_path).exists():
            print(f"[警告] HMDB数据库不存在: {self.db_path}")
            print(f"   将使用备用查询方法")
            self.db_available = False
        else:
            self.db_available = True
            print(f"[成功] HMDB数据库已加载: {self.db_path}")
    
    def search(self, mz: float, tolerance_ppm: float = 10, 
              ion_mode: str = 'positive') -> List[Dict]:
        """
        在HMDB数据库中搜索代谢物
        
        参数:
            mz: 待查询的m/z值
            tolerance_ppm: 质量误差容忍度（ppm）
            ion_mode: 离子模式 ('positive' or 'negative')
        
        返回:
            匹配的代谢物列表
        """
        if not self.db_available:
            return []
        
        # 计算质量搜索范围
        tolerance_da = (tolerance_ppm / 1e6) * mz
        mz_min = mz - tolerance_da
        mz_max = mz + tolerance_da
        
        results = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
            cursor = conn.cursor()
            
            # 查询匹配的代谢物
            # 根据theoretical_mz和ion_mode查询
            query = '''
                SELECT 
                    mz,
                    tolerance_ppm,
                    ion_mode,
                    metabolite_name,
                    formula,
                    hmdb_id,
                    molecular_weight,
                    cas_number,
                    kegg_id,
                    kingdom,
                    super_class,
                    class,
                    sub_class,
                    theoretical_mz,
                    error_ppm
                FROM annotation_cache
                WHERE theoretical_mz >= ? AND theoretical_mz <= ?
                AND ion_mode = ?
                ORDER BY ABS(theoretical_mz - ?) ASC
                LIMIT 50
            '''
            
            cursor.execute(query, (mz_min, mz_max, ion_mode, mz))
            
            for row in cursor.fetchall():
                theoretical_mz = row['theoretical_mz']
                error_da = theoretical_mz - mz
                calculated_error_ppm = (error_da / mz) * 1e6
                
                results.append({
                    'name': row['metabolite_name'],
                    'formula': row['formula'],
                    'hmdb_id': row['hmdb_id'] or '',
                    'molecular_weight': row['molecular_weight'],
                    'cas_number': row['cas_number'] or '',
                    'kegg_id': row['kegg_id'] or '',
                    'kingdom': row['kingdom'] or '',
                    'super_class': row['super_class'] or '',
                    'class': row['class'] or '',
                    'sub_class': row['sub_class'] or '',
                    'theoretical_mz': theoretical_mz,
                    'measured_mz': mz,
                    'error_ppm': abs(calculated_error_ppm),
                    'error_da': abs(error_da),
                    'source': 'HMDB'
                })
            
            conn.close()
            
        except Exception as e:
            print(f"[警告] HMDB数据库查询失败: {e}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def get_stats(self) -> Dict:
        """获取数据库统计信息"""
        if not self.db_available:
            return {'available': False}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取总记录数
            cursor.execute('SELECT COUNT(*) FROM annotation_cache')
            total = cursor.fetchone()[0]
            
            # 获取正离子模式记录数
            cursor.execute("SELECT COUNT(*) FROM annotation_cache WHERE ion_mode = 'positive'")
            positive = cursor.fetchone()[0]
            
            # 获取负离子模式记录数
            cursor.execute("SELECT COUNT(*) FROM annotation_cache WHERE ion_mode = 'negative'")
            negative = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'available': True,
                'total_metabolites': total,
                'positive_mode': positive,
                'negative_mode': negative
            }
            
        except Exception as e:
            print(f"[警告] 获取数据库统计失败: {e}")
            return {'available': False}


if __name__ == '__main__':
    """测试HMDB数据库查询"""
    import time
    
    print("="*70)
    print("🧪 测试HMDB数据库查询")
    print("="*70)
    
    hmdb = HMDBDatabaseQuery()
    
    # 获取统计信息
    stats = hmdb.get_stats()
    if stats['available']:
        print(f"\n[STATS] 数据库统计:")
        print(f"   总代谢物数: {stats['total_metabolites']:,}")
        print(f"   正离子模式: {stats['positive_mode']:,}")
        print(f"   负离子模式: {stats['negative_mode']:,}")
    
    # 测试查询
    test_mz_list = [255.2327, 301.1457, 369.3516]
    
    print(f"\n[SEARCH] 测试查询 ({len(test_mz_list)} 个m/z):")
    print("-"*70)
    
    total_start = time.time()
    
    for mz in test_mz_list:
        start = time.time()
        results = hmdb.search(mz, tolerance_ppm=10, ion_mode='positive')
        elapsed = time.time() - start
        
        print(f"\nm/z {mz:.4f}:")
        print(f"  耗时: {elapsed:.4f} 秒")
        print(f"  结果: {len(results)} 个匹配")
        
        if results:
            best = results[0]
            print(f"  最佳匹配: {best['name']}")
            print(f"  分子式: {best['formula']}")
            print(f"  误差: {best['error_ppm']:.2f} ppm")
            print(f"  HMDB ID: {best['hmdb_id']}")
    
    total_elapsed = time.time() - total_start
    
    print("\n" + "="*70)
    print(f"总耗时: {total_elapsed:.4f} 秒")
    print(f"平均每个: {total_elapsed/len(test_mz_list):.4f} 秒")
    print("="*70)


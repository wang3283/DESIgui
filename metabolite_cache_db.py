#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代谢物注释缓存数据库
持久化保存注释结果，避免重复查询
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class MetaboliteCacheDB:
    """代谢物注释缓存数据库"""
    
    def __init__(self, db_path: str = None):
        """
        初始化缓存数据库
        
        参数:
            db_path: 数据库文件路径，默认为 metabolite_cache.db
        """
        if db_path is None:
            db_path = Path(__file__).parent / "metabolite_cache.db"
        
        self.db_path = str(db_path)
        self.conn = None
        self.cursor = None
        
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # 创建注释缓存表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS annotation_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mz REAL NOT NULL,
                tolerance_ppm REAL NOT NULL,
                ion_mode TEXT NOT NULL,
                metabolite_name TEXT,
                formula TEXT,
                hmdb_id TEXT,
                molecular_weight REAL,
                cas_number TEXT,
                kegg_id TEXT,
                kingdom TEXT,
                super_class TEXT,
                class TEXT,
                sub_class TEXT,
                theoretical_mz REAL,
                error_ppm REAL,
                error_da REAL,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(mz, tolerance_ppm, ion_mode, metabolite_name)
            )
        ''')
        
        # 创建索引以提高查询速度
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_mz_mode 
            ON annotation_cache(mz, ion_mode)
        ''')
        
        # 创建统计信息表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_queries INTEGER DEFAULT 0,
                cache_hits INTEGER DEFAULT 0,
                cache_misses INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 初始化统计信息
        self.cursor.execute('SELECT COUNT(*) FROM cache_stats')
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute('''
                INSERT INTO cache_stats (total_queries, cache_hits, cache_misses)
                VALUES (0, 0, 0)
            ''')
        
        self.conn.commit()
        
        print(f"[成功] 代谢物缓存数据库已初始化: {self.db_path}")
    
    def query_cache(self, mz: float, tolerance_ppm: float, 
                   ion_mode: str) -> List[Dict]:
        """
        从缓存查询注释结果
        
        参数:
            mz: m/z值
            tolerance_ppm: 误差容忍度
            ion_mode: 离子模式
        
        返回:
            匹配的代谢物列表
        """
        # 计算搜索范围
        mz_min = mz * (1 - tolerance_ppm / 1e6)
        mz_max = mz * (1 + tolerance_ppm / 1e6)
        
        self.cursor.execute('''
            SELECT metabolite_name, formula, hmdb_id, molecular_weight,
                   cas_number, kegg_id, kingdom, super_class, class, sub_class,
                   theoretical_mz, error_ppm, error_da, source
            FROM annotation_cache
            WHERE ion_mode = ?
              AND theoretical_mz >= ?
              AND theoretical_mz <= ?
            ORDER BY error_ppm
        ''', (ion_mode, mz_min, mz_max))
        
        results = []
        for row in self.cursor.fetchall():
            # 重新计算当前m/z的误差
            theoretical_mz = row[10]
            error_da = abs(mz - theoretical_mz)
            error_ppm = (error_da / theoretical_mz) * 1e6
            
            if error_ppm <= tolerance_ppm:
                results.append({
                    'name': row[0],
                    'formula': row[1],
                    'hmdb_id': row[2],
                    'molecular_weight': row[3],
                    'cas_number': row[4],
                    'kegg_id': row[5],
                    'kingdom': row[6],
                    'super_class': row[7],
                    'class': row[8],
                    'sub_class': row[9],
                    'theoretical_mz': row[10],
                    'measured_mz': mz,
                    'error_ppm': error_ppm,
                    'error_da': error_da,
                    'source': row[13] + ' (cached)'
                })
        
        # 更新统计信息
        if results:
            self._update_stats(cache_hit=True)
        else:
            self._update_stats(cache_hit=False)
        
        return results
    
    def add_annotation(self, mz: float, tolerance_ppm: float, 
                      ion_mode: str, annotation: Dict):
        """
        添加注释结果到缓存
        
        参数:
            mz: m/z值
            tolerance_ppm: 误差容忍度
            ion_mode: 离子模式
            annotation: 注释结果字典
        """
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO annotation_cache
                (mz, tolerance_ppm, ion_mode, metabolite_name, formula,
                 hmdb_id, molecular_weight, cas_number, kegg_id,
                 kingdom, super_class, class, sub_class,
                 theoretical_mz, error_ppm, error_da, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                mz,
                tolerance_ppm,
                ion_mode,
                annotation.get('name', ''),
                annotation.get('formula', ''),
                annotation.get('hmdb_id', ''),
                annotation.get('molecular_weight', 0),
                annotation.get('cas_number', ''),
                annotation.get('kegg_id', ''),
                annotation.get('kingdom', ''),
                annotation.get('super_class', ''),
                annotation.get('class', ''),
                annotation.get('sub_class', ''),
                annotation.get('theoretical_mz', 0),
                annotation.get('error_ppm', 0),
                annotation.get('error_da', 0),
                annotation.get('source', 'Unknown')
            ))
            
            self.conn.commit()
        except sqlite3.IntegrityError:
            # 如果已存在相同记录，忽略
            pass
    
    def batch_add_annotations(self, annotations: List[tuple]):
        """
        批量添加注释结果
        
        参数:
            annotations: [(mz, tolerance_ppm, ion_mode, annotation_dict), ...]
        """
        for mz, tolerance_ppm, ion_mode, annotation in annotations:
            self.add_annotation(mz, tolerance_ppm, ion_mode, annotation)
    
    def _update_stats(self, cache_hit: bool = True):
        """更新统计信息"""
        if cache_hit:
            self.cursor.execute('''
                UPDATE cache_stats
                SET total_queries = total_queries + 1,
                    cache_hits = cache_hits + 1,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = 1
            ''')
        else:
            self.cursor.execute('''
                UPDATE cache_stats
                SET total_queries = total_queries + 1,
                    cache_misses = cache_misses + 1,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = 1
            ''')
        self.conn.commit()
    
    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        self.cursor.execute('''
            SELECT total_queries, cache_hits, cache_misses, last_updated
            FROM cache_stats
            WHERE id = 1
        ''')
        
        row = self.cursor.fetchone()
        if row:
            total, hits, misses, updated = row
            hit_rate = (hits / total * 100) if total > 0 else 0
            
            return {
                'total_queries': total,
                'cache_hits': hits,
                'cache_misses': misses,
                'hit_rate': hit_rate,
                'last_updated': updated,
                'total_cached_annotations': self._get_total_annotations()
            }
        
        return {}
    
    def _get_total_annotations(self) -> int:
        """获取缓存中的总注释数"""
        self.cursor.execute('SELECT COUNT(*) FROM annotation_cache')
        return self.cursor.fetchone()[0]
    
    def export_cache_to_csv(self, output_file: str):
        """导出缓存数据为CSV文件"""
        import pandas as pd
        
        self.cursor.execute('''
            SELECT mz, ion_mode, metabolite_name, formula, hmdb_id,
                   theoretical_mz, error_ppm, source, created_at
            FROM annotation_cache
            ORDER BY ion_mode, mz
        ''')
        
        rows = self.cursor.fetchall()
        columns = ['mz', 'ion_mode', 'metabolite_name', 'formula', 'hmdb_id',
                  'theoretical_mz', 'error_ppm', 'source', 'created_at']
        
        df = pd.DataFrame(rows, columns=columns)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"[成功] 缓存数据已导出到: {output_file}")
        print(f"   总记录数: {len(df)}")
    
    def import_cache_from_csv(self, csv_file: str):
        """从CSV文件导入缓存数据"""
        import pandas as pd
        
        df = pd.read_csv(csv_file)
        
        count = 0
        for _, row in df.iterrows():
            try:
                self.cursor.execute('''
                    INSERT OR REPLACE INTO annotation_cache
                    (mz, tolerance_ppm, ion_mode, metabolite_name, formula,
                     hmdb_id, theoretical_mz, error_ppm, error_da, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['mz'],
                    10.0,  # 默认容忍度
                    row['ion_mode'],
                    row['metabolite_name'],
                    row['formula'],
                    row['hmdb_id'],
                    row['theoretical_mz'],
                    row['error_ppm'],
                    0.0,  # error_da可从其他列计算
                    row['source']
                ))
                count += 1
            except Exception as e:
                print(f"[警告] 导入失败 (行{count}): {e}")
        
        self.conn.commit()
        print(f"[成功] 已从CSV导入 {count} 条记录")
    
    def clear_old_cache(self, days: int = 365):
        """清除过期的缓存数据"""
        self.cursor.execute('''
            DELETE FROM annotation_cache
            WHERE created_at < datetime('now', '-' || ? || ' days')
        ''', (days,))
        
        deleted = self.cursor.rowcount
        self.conn.commit()
        
        print(f"[成功] 已清除 {deleted} 条超过{days}天的缓存记录")
    
    def search_metabolite(self, name_pattern: str) -> List[Dict]:
        """
        按名称搜索代谢物
        
        参数:
            name_pattern: 名称模式（支持SQL LIKE语法）
        
        返回:
            匹配的代谢物列表
        """
        self.cursor.execute('''
            SELECT DISTINCT metabolite_name, formula, hmdb_id
            FROM annotation_cache
            WHERE metabolite_name LIKE ?
            ORDER BY metabolite_name
        ''', (f'%{name_pattern}%',))
        
        results = []
        for row in self.cursor.fetchall():
            results.append({
                'name': row[0],
                'formula': row[1],
                'hmdb_id': row[2]
            })
        
        return results
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            print("[成功] 数据库连接已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


def print_cache_stats():
    """打印缓存统计信息"""
    with MetaboliteCacheDB() as db:
        stats = db.get_stats()
        
        print("\n" + "="*60)
        print("[STATS] 代谢物注释缓存统计")
        print("="*60)
        print(f"  总查询次数:     {stats['total_queries']}")
        print(f"  缓存命中:       {stats['cache_hits']}")
        print(f"  缓存未命中:     {stats['cache_misses']}")
        print(f"  命中率:         {stats['hit_rate']:.1f}%")
        print(f"  缓存记录总数:   {stats['total_cached_annotations']}")
        print(f"  最后更新:       {stats['last_updated']}")
        print("="*60 + "\n")


if __name__ == "__main__":
    # 测试代码
    print("🧪 测试代谢物缓存数据库...")
    
    with MetaboliteCacheDB() as db:
        # 测试添加注释
        test_annotation = {
            'name': 'Oleic acid',
            'formula': 'C18H34O2',
            'hmdb_id': 'HMDB0000207',
            'theoretical_mz': 283.2640,
            'error_ppm': 1.23,
            'error_da': 0.0005,
            'source': 'Local'
        }
        
        db.add_annotation(283.2635, 10.0, 'negative', test_annotation)
        print("[成功] 添加测试注释")
        
        # 测试查询
        results = db.query_cache(283.2635, 10.0, 'negative')
        print(f"[成功] 查询结果: 找到 {len(results)} 个匹配")
        
        for result in results:
            print(f"   • {result['name']}: {result['theoretical_mz']:.4f} "
                  f"({result['error_ppm']:.2f} ppm)")
        
        # 打印统计信息
        stats = db.get_stats()
        print(f"\n[STATS] 缓存统计:")
        print(f"   总记录数: {stats['total_cached_annotations']}")
        print(f"   查询次数: {stats['total_queries']}")
        print(f"   命中率: {stats['hit_rate']:.1f}%")


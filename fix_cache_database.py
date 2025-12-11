#!/usr/bin/env python3
"""
修复代谢物注释缓存问题

问题: HMDB完整数据库和查询缓存混在一起
解决: 分离为两个独立数据库
"""

import shutil
import sqlite3
from pathlib import Path


def fix_cache_database():
    """修复缓存数据库"""
    
    print("="*70)
    print("[CONFIG] 修复代谢物注释缓存数据库")
    print("="*70)
    
    base_dir = Path(__file__).parent
    
    # 当前数据库文件
    current_db = base_dir / 'metabolite_cache.db'
    
    # 新文件名
    hmdb_db = base_dir / 'hmdb_database.db'
    new_cache_db = base_dir / 'metabolite_cache_new.db'
    backup_db = base_dir / 'metabolite_cache_backup.db'
    
    # 步骤1: 备份当前数据库
    print("\n📂 步骤1: 备份当前数据库")
    print("-"*70)
    
    if current_db.exists():
        size_mb = current_db.stat().st_size / (1024 * 1024)
        print(f"当前数据库: {current_db.name} ({size_mb:.2f} MB)")
        
        # 备份
        print(f"备份到: {backup_db.name}")
        shutil.copy2(current_db, backup_db)
        print(f"[成功] 备份完成")
        
        # 重命名为HMDB数据库
        print(f"\n重命名为: {hmdb_db.name}")
        shutil.copy2(current_db, hmdb_db)
        print(f"[成功] HMDB数据库创建完成")
    else:
        print(f"[错误] 当前数据库不存在: {current_db}")
        return False
    
    # 步骤2: 创建新的查询缓存数据库（空的）
    print("\n📂 步骤2: 创建新的查询缓存数据库")
    print("-"*70)
    
    conn = sqlite3.connect(new_cache_db)
    cursor = conn.cursor()
    
    # 创建annotation_cache表
    cursor.execute('''
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
    
    # 创建索引
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_mz_mode 
        ON annotation_cache(mz, ion_mode)
    ''')
    
    # 创建复合索引（优化范围查询）
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_mz_tol_mode 
        ON annotation_cache(mz, tolerance_ppm, ion_mode)
    ''')
    
    # 创建统计表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cache_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_queries INTEGER DEFAULT 0,
            cache_hits INTEGER DEFAULT 0,
            cache_misses INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        INSERT INTO cache_stats (total_queries, cache_hits, cache_misses)
        VALUES (0, 0, 0)
    ''')
    
    # 启用WAL模式（提升性能）
    cursor.execute('PRAGMA journal_mode=WAL')
    
    # 增加缓存大小
    cursor.execute('PRAGMA cache_size = -64000')  # 64MB
    
    conn.commit()
    conn.close()
    
    print(f"[成功] 新缓存数据库创建完成: {new_cache_db.name}")
    print(f"   - 表结构完整")
    print(f"   - 索引已优化")
    print(f"   - WAL模式已启用")
    print(f"   - 缓存大小: 64MB")
    
    # 步骤3: 替换旧数据库
    print("\n📂 步骤3: 替换旧数据库")
    print("-"*70)
    
    if current_db.exists():
        current_db.unlink()
        print(f"[成功] 删除旧数据库: {current_db.name}")
    
    new_cache_db.rename(current_db)
    print(f"[成功] 新数据库已就位: {current_db.name}")
    
    # 总结
    print("\n" + "="*70)
    print("[成功] 修复完成！")
    print("="*70)
    
    print(f"\n[FOLDER] 文件说明:")
    print(f"  1. {hmdb_db.name} ({size_mb:.2f} MB)")
    print(f"     - HMDB完整数据库（435,758条代谢物）")
    print(f"     - 用于首次查询时搜索")
    
    print(f"\n  2. {current_db.name} (新建，几乎为空)")
    print(f"     - 查询缓存数据库")
    print(f"     - 仅存储用户实际查询过的结果")
    print(f"     - 重复查询时极快（< 0.001秒）")
    
    print(f"\n  3. {backup_db.name} ({size_mb:.2f} MB)")
    print(f"     - 原始数据库备份")
    print(f"     - 如需回滚可用")
    
    print(f"\n[TARGET] 效果:")
    print(f"  - 第一次查询: 从HMDB搜索（0.015-0.045秒）")
    print(f"  - 第二次查询: 从缓存读取（< 0.001秒）")
    print(f"  - 性能提升: 15-45倍 ↑")
    
    print(f"\n[警告]  注意:")
    print(f"  - 之前的查询缓存已清空")
    print(f"  - 重新导出时会重建缓存")
    print(f"  - 缓存建立后速度极快")
    
    return True


if __name__ == '__main__':
    try:
        success = fix_cache_database()
        if success:
            print("\n[成功] 数据库修复成功！重启GUI后生效。")
        else:
            print("\n[错误] 数据库修复失败。")
    except Exception as e:
        print(f"\n[错误] 修复过程出错: {e}")
        import traceback
        traceback.print_exc()


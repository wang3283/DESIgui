#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HMDB数据库下载和处理工具
自动下载、解析并导入完整的HMDB代谢物数据库
"""

import os
import sys
import requests
import zipfile
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
from tqdm import tqdm
import time


class HMDBDownloader:
    """HMDB数据库下载器"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.download_dir = self.base_dir / "hmdb_downloads"
        self.download_dir.mkdir(exist_ok=True)
        
        # HMDB下载链接
        self.hmdb_urls = {
            'metabolites_xml': 'https://hmdb.ca/system/downloads/current/hmdb_metabolites.zip',
            'proteins_xml': 'https://hmdb.ca/system/downloads/current/hmdb_proteins.zip',
        }
        
        # 文件路径
        self.xml_file = None
        self.csv_file = self.base_dir / "hmdb_metabolites.csv"
        
        print("=" * 70)
        print("🔬 HMDB数据库下载和处理工具")
        print("=" * 70)
        print(f"\n📂 工作目录: {self.base_dir}")
        print(f"[RECEIVE] 下载目录: {self.download_dir}")
        print()
    
    def download_file(self, url: str, filename: str) -> Path:
        """下载文件（带进度条）"""
        filepath = self.download_dir / filename
        
        # 如果文件已存在，询问是否重新下载
        if filepath.exists():
            print(f"\n[FOLDER] 文件已存在: {filename}")
            size_mb = filepath.stat().st_size / 1024 / 1024
            print(f"   大小: {size_mb:.1f} MB")
            
            response = input("   是否重新下载? (y/N): ").strip().lower()
            if response != 'y':
                print("   [成功] 使用现有文件")
                return filepath
            print("   🔄 重新下载...")
        
        print(f"\n[RECEIVE] 下载: {filename}")
        print(f"   URL: {url}")
        
        try:
            # 发送请求
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            
            # 下载进度条
            with open(filepath, 'wb') as f, tqdm(
                desc=f"   下载进度",
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
            
            size_mb = filepath.stat().st_size / 1024 / 1024
            print(f"   [成功] 下载完成: {size_mb:.1f} MB")
            return filepath
            
        except Exception as e:
            print(f"   [错误] 下载失败: {e}")
            if filepath.exists():
                filepath.unlink()
            raise
    
    def extract_zip(self, zip_path: Path) -> Path:
        """解压ZIP文件"""
        print(f"\n[信息] 解压: {zip_path.name}")
        
        extract_dir = zip_path.parent / zip_path.stem
        extract_dir.mkdir(exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 获取文件列表
                files = zip_ref.namelist()
                print(f"   包含 {len(files)} 个文件")
                
                # 解压
                for file in tqdm(files, desc="   解压进度"):
                    zip_ref.extract(file, extract_dir)
                
                # 查找XML文件
                xml_files = list(extract_dir.glob("**/*.xml"))
                if xml_files:
                    xml_file = xml_files[0]
                    size_mb = xml_file.stat().st_size / 1024 / 1024
                    print(f"   [成功] 解压完成")
                    print(f"   [FILE] XML文件: {xml_file.name} ({size_mb:.1f} MB)")
                    return xml_file
                else:
                    raise FileNotFoundError("未找到XML文件")
                    
        except Exception as e:
            print(f"   [错误] 解压失败: {e}")
            raise
    
    def parse_xml_to_csv(self, xml_path: Path, max_records: int = None) -> Path:
        """解析XML并转换为CSV"""
        print(f"\n🔄 解析XML文件...")
        print(f"   文件: {xml_path.name}")
        
        try:
            # 解析XML
            print("   📖 读取XML...")
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # XML命名空间
            ns = {'hmdb': 'http://www.hmdb.ca'}
            
            # 获取所有代谢物
            metabolites = root.findall('.//hmdb:metabolite', ns)
            total_count = len(metabolites)
            
            if max_records:
                metabolites = metabolites[:max_records]
                print(f"   [警告] 限制处理数量: {max_records}/{total_count}")
            else:
                print(f"   [STATS] 找到 {total_count} 个代谢物")
            
            # 解析数据
            print("   [SEARCH] 解析代谢物信息...")
            data = []
            H_MASS = 1.00728  # H+质量
            
            for metabolite in tqdm(metabolites, desc="   解析进度"):
                try:
                    # 基本信息
                    name = metabolite.findtext('hmdb:name', default='Unknown', namespaces=ns)
                    hmdb_id = metabolite.findtext('hmdb:accession', default='', namespaces=ns)
                    formula = metabolite.findtext('hmdb:chemical_formula', default='', namespaces=ns)
                    
                    # CAS号
                    cas_number = metabolite.findtext('hmdb:cas_registry_number', default='', namespaces=ns)
                    
                    # KEGG ID
                    kegg_id = metabolite.findtext('hmdb:kegg_id', default='', namespaces=ns)
                    
                    # 物质分类信息
                    taxonomy = metabolite.find('hmdb:taxonomy', namespaces=ns)
                    kingdom = ''
                    super_class = ''
                    main_class = ''
                    sub_class = ''
                    
                    if taxonomy is not None:
                        kingdom = taxonomy.findtext('hmdb:kingdom', default='', namespaces=ns)
                        super_class = taxonomy.findtext('hmdb:super_class', default='', namespaces=ns)
                        main_class = taxonomy.findtext('hmdb:class', default='', namespaces=ns)
                        sub_class = taxonomy.findtext('hmdb:sub_class', default='', namespaces=ns)
                    
                    # 获取单一同位素质量
                    mass_text = metabolite.findtext('hmdb:monisotopic_molecular_weight', 
                                                    default=None, namespaces=ns)
                    
                    if not mass_text:
                        # 尝试其他质量字段
                        mass_text = metabolite.findtext('hmdb:average_molecular_weight',
                                                       default=None, namespaces=ns)
                    
                    if mass_text:
                        try:
                            neutral_mass = float(mass_text)
                            
                            # 计算离子化后的m/z
                            mz_positive = neutral_mass + H_MASS  # [M+H]+
                            mz_negative = neutral_mass - H_MASS  # [M-H]-
                            
                            data.append({
                                'name': name,
                                'hmdb_id': hmdb_id,
                                'formula': formula,
                                'molecular_weight': neutral_mass,
                                'cas_number': cas_number,
                                'kegg_id': kegg_id,
                                'kingdom': kingdom,
                                'super_class': super_class,
                                'class': main_class,
                                'sub_class': sub_class,
                                'mz_positive': mz_positive,
                                'mz_negative': mz_negative
                            })
                        except ValueError:
                            continue
                
                except Exception as e:
                    # 跳过有问题的条目
                    continue
            
            # 创建DataFrame
            print(f"\n   [成功] 成功解析 {len(data)} 个代谢物")
            df = pd.DataFrame(data)
            
            # 保存为CSV
            print(f"   [SAVE] 保存为CSV: {self.csv_file.name}")
            df.to_csv(self.csv_file, index=False)
            
            size_mb = self.csv_file.stat().st_size / 1024 / 1024
            print(f"   [成功] CSV文件已保存 ({size_mb:.1f} MB)")
            
            return self.csv_file
            
        except Exception as e:
            print(f"   [错误] 解析失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def import_to_cache_db(self, csv_path: Path):
        """导入到缓存数据库"""
        print(f"\n[SAVE] 导入到缓存数据库...")
        
        try:
            from metabolite_cache_db import MetaboliteCacheDB
            
            # 读取CSV
            print("   📖 读取CSV...")
            df = pd.read_csv(csv_path)
            total = len(df)
            print(f"   [STATS] 共 {total} 条记录")
            
            # 连接数据库
            print("   🔌 连接数据库...")
            cache_db = MetaboliteCacheDB()
            
            # 批量导入
            print("   [RECEIVE] 批量导入中...")
            
            # 分两次导入：正离子和负离子
            tolerance_ppm = 10
            
            # 正离子模式
            print("\n   🔹 导入正离子模式 [M+H]+:")
            for idx, row in tqdm(df.iterrows(), total=total, desc="      进度"):
                try:
                    annotation = {
                        'name': row['name'],
                        'formula': row['formula'],
                        'hmdb_id': row['hmdb_id'],
                        'molecular_weight': row['molecular_weight'],
                        'cas_number': row.get('cas_number', ''),
                        'kegg_id': row.get('kegg_id', ''),
                        'kingdom': row.get('kingdom', ''),
                        'super_class': row.get('super_class', ''),
                        'class': row.get('class', ''),
                        'sub_class': row.get('sub_class', ''),
                        'theoretical_mz': row['mz_positive'],
                        'measured_mz': row['mz_positive'],
                        'error_ppm': 0.0,
                        'error_da': 0.0,
                        'source': 'HMDB'
                    }
                    cache_db.add_annotation(
                        mz=row['mz_positive'],
                        tolerance_ppm=tolerance_ppm,
                        ion_mode='positive',
                        annotation=annotation
                    )
                except Exception as e:
                    continue
            
            # 负离子模式
            print("\n   🔸 导入负离子模式 [M-H]-:")
            for idx, row in tqdm(df.iterrows(), total=total, desc="      进度"):
                try:
                    annotation = {
                        'name': row['name'],
                        'formula': row['formula'],
                        'hmdb_id': row['hmdb_id'],
                        'molecular_weight': row['molecular_weight'],
                        'cas_number': row.get('cas_number', ''),
                        'kegg_id': row.get('kegg_id', ''),
                        'kingdom': row.get('kingdom', ''),
                        'super_class': row.get('super_class', ''),
                        'class': row.get('class', ''),
                        'sub_class': row.get('sub_class', ''),
                        'theoretical_mz': row['mz_negative'],
                        'measured_mz': row['mz_negative'],
                        'error_ppm': 0.0,
                        'error_da': 0.0,
                        'source': 'HMDB'
                    }
                    cache_db.add_annotation(
                        mz=row['mz_negative'],
                        tolerance_ppm=tolerance_ppm,
                        ion_mode='negative',
                        annotation=annotation
                    )
                except Exception as e:
                    continue
            
            # 显示统计
            stats = cache_db.get_stats()
            print(f"\n   [成功] 导入完成！")
            print(f"\n   [STATS] 数据库统计:")
            print(f"      缓存记录总数: {stats['total_cached_annotations']}")
            
            cache_db.close()
            
        except Exception as e:
            print(f"   [错误] 导入失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def run(self, skip_download=False, max_records=None):
        """运行完整流程"""
        try:
            print("\n" + "━" * 70)
            print("[LAUNCH] 开始下载和处理HMDB数据库")
            print("━" * 70)
            
            if not skip_download:
                # 1. 下载
                print("\n[RECEIVE] 步骤1/4: 下载HMDB数据库")
                print("   [TIMER]  预计时间: 5-15分钟（取决于网络速度）")
                
                zip_path = self.download_file(
                    self.hmdb_urls['metabolites_xml'],
                    'hmdb_metabolites.zip'
                )
                
                # 2. 解压
                print("\n[信息] 步骤2/4: 解压文件")
                print("   [TIMER]  预计时间: 2-5分钟")
                
                self.xml_file = self.extract_zip(zip_path)
            else:
                # 查找已有的XML文件
                xml_files = list(self.download_dir.glob("**/*.xml"))
                if xml_files:
                    self.xml_file = xml_files[0]
                    print(f"\n[成功] 使用现有XML文件: {self.xml_file}")
                else:
                    raise FileNotFoundError("未找到XML文件，请先下载")
            
            # 3. 解析
            print("\n🔄 步骤3/4: 解析XML并转换为CSV")
            print("   [TIMER]  预计时间: 5-10分钟")
            
            csv_path = self.parse_xml_to_csv(self.xml_file, max_records)
            
            # 4. 导入数据库
            print("\n[SAVE] 步骤4/4: 导入到缓存数据库")
            print("   [TIMER]  预计时间: 10-20分钟")
            
            self.import_to_cache_db(csv_path)
            
            # 完成
            print("\n" + "=" * 70)
            print("[CELEBRATE] HMDB数据库下载和导入完成！")
            print("=" * 70)
            
            # 统计信息
            df = pd.read_csv(csv_path)
            print(f"\n[STATS] 数据库统计:")
            print(f"   代谢物总数: {len(df):,}")
            print(f"   CSV文件: {csv_path}")
            print(f"   缓存数据库: {self.base_dir / 'metabolite_cache.db'}")
            
            print(f"\n[成功] 现在可以在GUI中使用完整的HMDB数据库了！")
            print(f"\n🧪 测试方法:")
            print(f"   1. 运行: python3 test_mz_187.py")
            print(f"   2. 在GUI中：右键离子表 → 代谢物查询")
            print(f"   3. 导出时选择：包含代谢物注释")
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n[警告] 用户中断")
            return False
        except Exception as e:
            print(f"\n\n[错误] 处理失败: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='HMDB数据库下载和处理工具')
    parser.add_argument('--skip-download', action='store_true',
                       help='跳过下载步骤（使用已有文件）')
    parser.add_argument('--max-records', type=int, default=None,
                       help='限制处理的记录数量（用于测试）')
    
    args = parser.parse_args()
    
    # 运行
    downloader = HMDBDownloader()
    success = downloader.run(
        skip_download=args.skip_download,
        max_records=args.max_records
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()


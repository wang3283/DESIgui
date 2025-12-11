#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一语言和清理emoji的脚本
"""

import re
from pathlib import Path

# 定义替换规则
REPLACEMENTS = {
    # 英文标签替换为中文
    r'\[SUCCESS\]': '[成功]',
    r'\[ERROR\]': '[错误]',
    r'\[INFO\]': '[信息]',
    r'\[WARNING\]': '[警告]',
    r'\[TEST\]': '[测试]',
    r'\[TIP\]': '[提示]',
    
    # emoji替换
    r'[成功]': '[成功]',
    r'[成功]': '[成功]',
    r'[失败]': '[失败]',
    r'[错误]': '[错误]',
    r'[警告]': '[警告]',
    r'': '',
    r'': '',
    r'': '',
    r'': '',
    r'': '',
    r'[紧急]': '[紧急]',
    r'[提醒]': '[提醒]',
    
    # License统一为"许可证"
    r'许可证密钥': '许可证密钥',
    r'许可证信息': '许可证信息',
    r'许可证已过期': '许可证已过期',
    r'许可证即将过期': '许可证即将过期',
    r'许可证到期': '许可证到期',
    r'当前许可证': '当前许可证',
}

# 需要处理的文件（排除测试文件和文档）
INCLUDE_PATTERNS = [
    '**/*dialog*.py',
    '**/*gui*.py',
    '**/usage_tracker.py',
    '**/database_manager.py',
    '**/quarterly_billing_workflow.py',
]

EXCLUDE_PATTERNS = [
    'tests/**',
    '**/__pycache__/**',
    '.pytest_cache/**',
    '.hypothesis/**',
]

def should_process_file(file_path: Path) -> bool:
    """判断是否应该处理该文件"""
    # 排除测试文件
    if 'test_' in file_path.name or file_path.name.startswith('test'):
        return False
    
    # 排除文档
    if file_path.suffix == '.md':
        return False
    
    # 只处理Python文件
    if file_path.suffix != '.py':
        return False
    
    return True

def fix_file(file_path: Path, dry_run=True):
    """修复单个文件"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # 应用所有替换规则
        for pattern, replacement in REPLACEMENTS.items():
            content = re.sub(pattern, replacement, content)
        
        # 检查是否有变化
        if content != original_content:
            if dry_run:
                print(f"[预览] {file_path}")
                # 显示差异
                lines_before = original_content.split('\n')
                lines_after = content.split('\n')
                for i, (before, after) in enumerate(zip(lines_before, lines_after), 1):
                    if before != after:
                        print(f"  行 {i}:")
                        print(f"    - {before[:80]}")
                        print(f"    + {after[:80]}")
            else:
                file_path.write_text(content, encoding='utf-8')
                print(f"[已修复] {file_path}")
            
            return True
        
        return False
    
    except Exception as e:
        print(f"[错误] 处理文件失败 {file_path}: {e}")
        return False

def main():
    """主函数"""
    import sys
    
    dry_run = '--apply' not in sys.argv
    
    if dry_run:
        print("=" * 70)
        print("预览模式 - 不会修改文件")
        print("使用 --apply 参数来实际应用修改")
        print("=" * 70)
    else:
        print("=" * 70)
        print("应用模式 - 将修改文件")
        print("=" * 70)
    
    # 获取所有Python文件
    root = Path('.')
    python_files = []
    
    for pattern in ['*.py', '**/*.py']:
        python_files.extend(root.glob(pattern))
    
    # 过滤文件
    files_to_process = [f for f in python_files if should_process_file(f)]
    
    print(f"\n找到 {len(files_to_process)} 个文件需要处理\n")
    
    # 处理文件
    modified_count = 0
    for file_path in sorted(files_to_process):
        if fix_file(file_path, dry_run):
            modified_count += 1
    
    print("\n" + "=" * 70)
    if dry_run:
        print(f"预览完成: {modified_count} 个文件需要修改")
        print("使用 'python fix_language_consistency.py --apply' 来应用修改")
    else:
        print(f"修复完成: {modified_count} 个文件已修改")
    print("=" * 70)

if __name__ == '__main__':
    main()

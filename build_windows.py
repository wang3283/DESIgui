#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows打包脚本 - 使用PyInstaller
"""

import os
import sys
import subprocess
from pathlib import Path

def build_main_gui():
    """打包主程序"""
    print("=" * 60)
    print("打包 DESI主程序 (main_gui_ultimate.exe)")
    print("=" * 60)
    
    # 根据操作系统选择分隔符
    separator = ';' if sys.platform == 'win32' else ':'
    
    cmd = [
        'pyinstaller',
        '--name=DESI空间代谢组学分析系统',
        '--windowed',  # 不显示控制台
        '--onefile',   # 单文件
        '--clean',
        '--noconfirm',
        # 添加数据文件（自动适配分隔符）
        f'--add-data=hmdb_database.db{separator}.',
        f'--add-data=metabolite_cache.db{separator}.',
        # 隐藏导入
        '--hidden-import=PyQt5',
        '--hidden-import=matplotlib',
        '--hidden-import=numpy',
        '--hidden-import=pandas',
        '--hidden-import=cryptography',
        '--hidden-import=openpyxl',
        '--hidden-import=xlsxwriter',
        # 主文件
        'main_gui_ultimate.py'
    ]
    
    subprocess.run(cmd)
    print("\n[成功] 主程序打包完成: dist/DESI空间代谢组学分析系统.exe")

def build_license_manager():
    """打包许可证管理器"""
    print("\n" + "=" * 60)
    print("打包 许可证管理器 (license_manager_gui.exe)")
    print("=" * 60)
    
    cmd = [
        'pyinstaller',
        '--name=许可证管理器',
        '--windowed',
        '--onefile',
        '--clean',
        '--noconfirm',
        '--hidden-import=PyQt5',
        '--hidden-import=cryptography',
        '--hidden-import=pandas',
        'license_manager_gui.py'
    ]
    
    subprocess.run(cmd)
    print("\n[成功] 许可证管理器打包完成: dist/许可证管理器.exe")

def main():
    """主函数"""
    print("DESI商业化计费系统 - Windows打包工具\n")
    
    # 检查PyInstaller
    try:
        import PyInstaller
        print(f"[成功] PyInstaller版本: {PyInstaller.__version__}")
    except ImportError:
        print("[错误] 未安装PyInstaller")
        print("请运行: pip install pyinstaller")
        sys.exit(1)
    
    # 选择打包目标
    print("\n请选择打包目标:")
    print("1. 主程序 (main_gui_ultimate.exe)")
    print("2. 许可证管理器 (license_manager_gui.exe)")
    print("3. 全部打包")
    
    choice = input("\n请输入选项 (1/2/3): ").strip()
    
    if choice == '1':
        build_main_gui()
    elif choice == '2':
        build_license_manager()
    elif choice == '3':
        build_main_gui()
        build_license_manager()
    else:
        print("[错误] 无效选项")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("[成功] 打包完成！")
    print("=" * 60)
    print("\n可执行文件位置: dist/")
    print("\n使用说明:")
    print("1. 将 dist/ 目录下的 .exe 文件复制到目标Windows电脑")
    print("2. 双击运行即可，无需安装Python")
    print("3. 首次运行可能需要几秒钟启动时间")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cx_Freeze打包配置
"""

import sys
from cx_Freeze import setup, Executable

# 依赖包
build_exe_options = {
    "packages": [
        "PyQt5",
        "matplotlib",
        "numpy",
        "pandas",
        "cryptography",
        "openpyxl",
        "xlsxwriter",
        "sqlite3",
    ],
    "include_files": [
        ("hmdb_database.db", "hmdb_database.db"),
        ("metabolite_cache.db", "metabolite_cache.db"),
    ],
    "excludes": ["tkinter"],
}

# 主程序
main_gui_exe = Executable(
    "main_gui_ultimate.py",
    base="Win32GUI" if sys.platform == "win32" else None,
    target_name="DESI空间代谢组学分析系统.exe",
    icon=None,
)

# 许可证管理器
license_manager_exe = Executable(
    "license_manager_gui.py",
    base="Win32GUI" if sys.platform == "win32" else None,
    target_name="许可证管理器.exe",
    icon=None,
)

setup(
    name="DESI商业化计费系统",
    version="1.0.0",
    description="DESI空间代谢组学分析系统",
    options={"build_exe": build_exe_options},
    executables=[main_gui_exe, license_manager_exe],
)

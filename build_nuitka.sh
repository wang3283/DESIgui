#!/bin/bash
# Nuitka打包脚本（性能最优）

echo "使用Nuitka打包DESI系统..."

# 检查Nuitka
if ! command -v nuitka3 &> /dev/null; then
    echo "[错误] 未安装Nuitka"
    echo "请运行: pip install nuitka"
    exit 1
fi

# 打包主程序
echo "打包主程序..."
nuitka3 \
    --standalone \
    --onefile \
    --windows-disable-console \
    --enable-plugin=pyqt5 \
    --include-data-file=hmdb_database.db=hmdb_database.db \
    --include-data-file=metabolite_cache.db=metabolite_cache.db \
    --output-filename=DESI空间代谢组学分析系统.exe \
    main_gui_ultimate.py

# 打包许可证管理器
echo "打包许可证管理器..."
nuitka3 \
    --standalone \
    --onefile \
    --windows-disable-console \
    --enable-plugin=pyqt5 \
    --output-filename=许可证管理器.exe \
    license_manager_gui.py

echo "[成功] 打包完成！"

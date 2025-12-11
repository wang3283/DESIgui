#!/bin/bash

echo "=================================================="
echo "🚀 DESI终极完整版启动脚本"
echo "=================================================="
echo ""

cd "$(dirname "$0")"

echo "📁 工作目录: $(pwd)"
echo ""

# 检查Python
echo "🔍 检查Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未找到，请安装Python 3.8+"
    exit 1
fi

echo "✅ Python3 可用"
echo ""

# 清理旧进程
echo "🔧 清理旧进程..."
pkill -9 -f "python.*main_gui_ultimate" 2>/dev/null
sleep 1
echo "✅ 完成"
echo ""

# 启动GUI
echo "🚀 启动DESI分析系统..."
python3 main_gui_ultimate.py

echo ""
echo "✅ 程序已退出"

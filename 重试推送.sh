#!/bin/bash
# 重试推送到GitHub

cd "/Volumes/US100 256G/mouse DESI data/desi_gui_v2"

echo "=========================================="
echo "重试推送到GitHub"
echo "=========================================="
echo ""

echo "当前目录: $(pwd)"
echo ""

echo "检查Git状态..."
git status --short | head -5
echo ""

echo "尝试推送到GitHub..."
echo "请稍候（可能需要1-2分钟）..."
echo ""

git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ 推送成功！"
    echo "=========================================="
    echo ""
    echo "GitHub仓库: https://github.com/wang3283/DESIgui.git"
    echo ""
    echo "在Windows上克隆:"
    echo "  git clone https://github.com/wang3283/DESIgui.git"
    echo "  cd DESIgui"
    echo "  pip install -r requirements.txt"
    echo "  python build_windows.py"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "❌ 推送失败"
    echo "=========================================="
    echo ""
    echo "可能的原因:"
    echo "1. 网络连接问题"
    echo "2. 需要GitHub认证"
    echo "3. 远程仓库已有内容"
    echo ""
    echo "解决方案:"
    echo ""
    echo "1. 检查网络连接后重试"
    echo "   bash 重试推送.sh"
    echo ""
    echo "2. 使用SSH代替HTTPS"
    echo "   git remote set-url origin git@github.com:wang3283/DESIgui.git"
    echo "   git push -u origin main"
    echo ""
    echo "3. 强制推送（会覆盖远程）"
    echo "   git push -u origin main --force"
    echo ""
    echo "详细信息请查看: Git推送状态报告.txt"
    echo ""
fi

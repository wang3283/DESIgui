#!/bin/bash
# Git设置和推送脚本

echo "=========================================="
echo "DESI系统 - Git设置和推送到GitHub"
echo "=========================================="

# 初始化Git仓库
echo ""
echo "[1/6] 初始化Git仓库..."
git init

# 添加远程仓库
echo ""
echo "[2/6] 添加远程仓库..."
git remote add origin https://github.com/wang3283/DESIgui.git

# 检查远程仓库
echo ""
echo "[3/6] 检查远程仓库..."
git remote -v

# 添加所有文件
echo ""
echo "[4/6] 添加文件到Git..."
git add .

# 提交
echo ""
echo "[5/6] 提交更改..."
git commit -m "Initial commit: DESI空间代谢组学分析系统

主要功能:
- 数据加载与可视化
- 代谢物注释（HMDB数据库）
- 质量校准（Lock Mass）
- 商业化计费系统
- 许可证管理
- Windows打包支持

技术栈:
- Python 3.7+
- PyQt5
- matplotlib
- numpy/pandas
- SQLite数据库

已完成:
✅ 导航栏语言统一
✅ Windows打包脚本
✅ 完整文档
✅ 跨平台数据库兼容
"

# 推送到GitHub
echo ""
echo "[6/6] 推送到GitHub..."
echo "注意: 如果远程仓库已存在内容，可能需要先pull或使用 --force"
echo ""
read -p "是否继续推送? (y/n): " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    # 尝试正常推送
    git push -u origin main || git push -u origin master || {
        echo ""
        echo "正常推送失败，尝试强制推送..."
        read -p "是否强制推送（会覆盖远程内容）? (y/n): " force_confirm
        if [ "$force_confirm" = "y" ] || [ "$force_confirm" = "Y" ]; then
            git push -u origin main --force || git push -u origin master --force
        fi
    }
else
    echo "取消推送"
fi

echo ""
echo "=========================================="
echo "完成！"
echo "=========================================="
echo ""
echo "GitHub仓库: https://github.com/wang3283/DESIgui.git"
echo ""
echo "在Windows上克隆:"
echo "  git clone https://github.com/wang3283/DESIgui.git"
echo ""

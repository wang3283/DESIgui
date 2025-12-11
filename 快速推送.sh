#!/bin/bash
# 快速推送到GitHub

echo "DESI系统 - 快速推送到GitHub"
echo "======================================"
echo ""

# 检查是否已初始化
if [ ! -d ".git" ]; then
    echo "[1] 初始化Git仓库..."
    git init
    echo ""
fi

# 检查远程仓库
if ! git remote | grep -q "origin"; then
    echo "[2] 添加远程仓库..."
    git remote add origin https://github.com/wang3283/DESIgui.git
    echo ""
else
    echo "[2] 远程仓库已存在"
    git remote -v
    echo ""
fi

# 添加文件
echo "[3] 添加文件..."
git add .
echo ""

# 提交
echo "[4] 提交更改..."
git commit -m "Update: DESI系统完整代码

- 导航栏语言统一
- Windows打包支持
- 完整文档
- 数据库文件
" || echo "没有新的更改需要提交"
echo ""

# 推送
echo "[5] 推送到GitHub..."
echo "尝试推送到 main 分支..."
git push -u origin main 2>/dev/null || {
    echo "main分支推送失败，尝试 master 分支..."
    git push -u origin master 2>/dev/null || {
        echo ""
        echo "⚠️  推送失败！可能的原因:"
        echo "1. 远程仓库已有内容（需要先pull）"
        echo "2. 认证失败（需要配置GitHub token）"
        echo "3. 文件太大（需要使用Git LFS）"
        echo ""
        echo "建议操作:"
        echo "  git pull origin main --rebase"
        echo "  git push -u origin main"
        echo ""
        echo "或强制推送（会覆盖远程）:"
        echo "  git push -u origin main --force"
    }
}

echo ""
echo "======================================"
echo "完成！"
echo "GitHub: https://github.com/wang3283/DESIgui.git"
echo "======================================"

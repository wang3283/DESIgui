@echo off
chcp 65001 >nul
echo ==========================================
echo DESI系统 - 推送到GitHub
echo ==========================================
echo.

REM 检查Git是否安装
git --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未安装Git
    echo 请从 https://git-scm.com/download/win 下载安装
    pause
    exit /b 1
)

REM 初始化Git仓库
if not exist ".git" (
    echo [1] 初始化Git仓库...
    git init
    echo.
) else (
    echo [1] Git仓库已存在
    echo.
)

REM 添加远程仓库
git remote | findstr "origin" >nul
if errorlevel 1 (
    echo [2] 添加远程仓库...
    git remote add origin https://github.com/wang3283/DESIgui.git
    echo.
) else (
    echo [2] 远程仓库已存在
    git remote -v
    echo.
)

REM 添加文件
echo [3] 添加文件...
git add .
echo.

REM 提交
echo [4] 提交更改...
git commit -m "Update: DESI系统完整代码"
echo.

REM 推送
echo [5] 推送到GitHub...
echo 尝试推送到 main 分支...
git push -u origin main 2>nul
if errorlevel 1 (
    echo main分支推送失败，尝试 master 分支...
    git push -u origin master 2>nul
    if errorlevel 1 (
        echo.
        echo [警告] 推送失败！
        echo.
        echo 可能的原因:
        echo 1. 远程仓库已有内容
        echo 2. 需要认证
        echo 3. 文件太大
        echo.
        echo 建议操作:
        echo   git pull origin main --rebase
        echo   git push -u origin main
        echo.
        pause
        exit /b 1
    )
)

echo.
echo ==========================================
echo [成功] 推送完成！
echo ==========================================
echo.
echo GitHub仓库: https://github.com/wang3283/DESIgui.git
echo.
pause

@echo off
chcp 65001 >nul
echo ===============================================
echo DESI系统 - 自动安装依赖
echo ===============================================
echo.

echo [1/3] 检查 Python 环境...
python --version
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.7+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo.

echo [2/3] 升级 pip...
python -m pip install --upgrade pip
echo.

echo [3/3] 安装依赖库...
pip install -r requirements.txt
echo.

if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

echo ===============================================
echo [成功] 所有依赖已安装完成！
echo ===============================================
echo.
echo 下一步: 运行 打包程序.bat 开始打包
echo.
pause

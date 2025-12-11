@echo off
chcp 65001 >nul
echo ===============================================
echo DESI系统 - 一键打包
echo ===============================================
echo.

echo 请选择打包选项:
echo 1. 打包主程序 (DESI空间代谢组学分析系统.exe)
echo 2. 打包许可证管理器 (许可证管理器.exe)
echo 3. 全部打包 (推荐)
echo.

set /p choice="请输入选项 (1/2/3): "

if "%choice%"=="1" goto build_main
if "%choice%"=="2" goto build_license
if "%choice%"=="3" goto build_all
echo [错误] 无效选项
pause
exit /b 1

:build_main
echo.
echo ===============================================
echo 正在打包主程序...
echo ===============================================
python build_windows.py
goto end

:build_license
echo.
echo ===============================================
echo 正在打包许可证管理器...
echo ===============================================
python build_windows.py
goto end

:build_all
echo.
echo ===============================================
echo 正在打包所有程序...
echo ===============================================
python build_windows.py
goto end

:end
echo.
echo ===============================================
echo [成功] 打包完成！
echo ===============================================
echo.
echo 生成的文件位置: dist\
echo   - DESI空间代谢组学分析系统.exe
echo   - 许可证管理器.exe
echo.
echo 可以将这些 .exe 文件分发给用户使用
echo.
pause

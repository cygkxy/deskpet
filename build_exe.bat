@echo off
chcp 65001 >nul
echo ============================================
echo   DeepSeek 余额桌宠 - 打包工具
echo ============================================
echo.

REM 安装依赖
echo [1/3] 安装依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 依赖安装失败！
    pause
    exit /b 1
)
echo 依赖安装完成！
echo.

REM 清理旧的打包文件
echo [2/3] 清理旧构建...
if exist "dist\DeepSeek余额桌宠.exe" del "dist\DeepSeek余额桌宠.exe"
if exist "build" rmdir /s /q build
if exist "DeepSeek余额桌宠.spec" del "DeepSeek余额桌宠.spec"
echo 清理完成！
echo.

REM 打包
echo [3/3] 正在打包为 EXE...
pyinstaller --onefile --windowed ^
    --name "DeepSeek余额桌宠" ^
    --add-data "icon;icon" ^
    --icon "icon\app_icon.ico" ^
    --clean ^
    --noconfirm ^
    deskpet.py

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo  打包成功！
    echo  输出文件: dist\DeepSeek余额桌宠.exe
    echo ============================================
    echo.
    echo 提示：首次运行请在右键菜单中设置 API Key
    echo.
) else (
    echo.
    echo 打包失败，请检查错误信息！
)

pause

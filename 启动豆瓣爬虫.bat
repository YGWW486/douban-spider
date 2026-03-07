@echo off

rem 豆瓣电影Top250爬虫启动器
rem 此脚本用于启动爬虫图形界面

echo 正在启动豆瓣电影Top250爬虫图形界面...

rem 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python环境，请先安装Python
    echo 您可以从 https://www.python.org/downloads/ 下载安装
    pause
    exit /b 1
)

rem 确保依赖已安装
pip install -r requirements.txt pandas matplotlib seaborn json >nul 2>&1
if %errorlevel% neq 0 (
    echo 警告: 安装依赖包时发生错误，但将继续启动程序
)

rem 启动GUI应用
python gui_app.py

rem 检查程序是否正常退出
if %errorlevel% neq 0 (
    echo 程序异常退出，错误代码: %errorlevel%
    pause
)
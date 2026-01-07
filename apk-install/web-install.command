#!/bin/bash

cd "$(dirname "$0")"

# APK 安装工具启动脚本

echo "正在启动 APK 安装工具..."

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 运行数据库迁移
echo "运行数据库迁移..."
python manage.py migrate

# 启动服务器（后台运行）
echo "启动开发服务器..."
echo "访问地址: http://127.0.0.1:8000"
python manage.py runserver &

# 等待服务器启动
echo "等待服务器启动..."
sleep 3

# 根据操作系统启动默认浏览器并打开服务地址
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open http://127.0.0.1:8000/ &
elif command -v open >/dev/null 2>&1; then
    open http://127.0.0.1:8000/ &
elif command -v start >/dev/null 2>&1; then
    start http://127.0.0.1:8000/ &
else
    echo "请手动在浏览器中打开: http://127.0.0.1:8000/"
fi

# 等待服务器进程（保持脚本运行）
wait



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

# 启动服务器
echo "启动开发服务器..."
echo "访问地址: http://127.0.0.1:8000"
python manage.py runserver


#!/bin/bash
# 启动Django后端服务器

cd backend

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

# 运行迁移
echo "运行数据库迁移..."
python manage.py migrate

# 启动服务器
echo "启动Django服务器..."
python manage.py runserver

#!/bin/bash
# 启动React前端服务器

cd frontend

# 检查node_modules
if [ ! -d "node_modules" ]; then
    echo "安装依赖..."
    npm install
fi

# 启动开发服务器
echo "启动React开发服务器..."
npm start

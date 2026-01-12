#!/bin/bash
# 同时启动Django后端和React前端服务器

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 清理函数
cleanup() {
    echo -e "\n${YELLOW}正在关闭服务...${NC}"
    if [ ! -z "$BACKEND_PID" ] && ps -p $BACKEND_PID > /dev/null 2>&1; then
        kill $BACKEND_PID 2>/dev/null
        wait $BACKEND_PID 2>/dev/null
        echo -e "${GREEN}后端服务已关闭${NC}"
    fi
    if [ ! -z "$FRONTEND_PID" ] && ps -p $FRONTEND_PID > /dev/null 2>&1; then
        kill $FRONTEND_PID 2>/dev/null
        wait $FRONTEND_PID 2>/dev/null
        echo -e "${GREEN}前端服务已关闭${NC}"
    fi
    # 停止tail进程
    if [ ! -z "$TAIL_PID" ] && ps -p $TAIL_PID > /dev/null 2>&1; then
        kill $TAIL_PID 2>/dev/null
    fi
    exit 0
}

# 捕获退出信号
trap cleanup SIGINT SIGTERM

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  小学数学练习题生成器 - 启动脚本${NC}"
echo -e "${BLUE}========================================${NC}\n"

# ========== 后端设置 ==========
echo -e "${YELLOW}[1/4] 设置后端环境...${NC}"
cd backend

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
if [ ! -f "venv/.deps_installed" ]; then
    echo -e "${YELLOW}安装Python依赖...${NC}"
    pip install -r requirements.txt
    touch venv/.deps_installed
fi

# 运行迁移
echo -e "${YELLOW}运行数据库迁移...${NC}"
python manage.py migrate > /dev/null 2>&1

# 启动后端服务器（后台运行）
echo -e "${GREEN}启动Django后端服务器 (http://localhost:8000)...${NC}"
# 清空旧的日志文件
> ../backend.log
python manage.py runserver >> ../backend.log 2>&1 &
BACKEND_PID=$!

# 等待后端启动
sleep 3
if ps -p $BACKEND_PID > /dev/null; then
    echo -e "${GREEN}✓ 后端服务已启动 (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}✗ 后端服务启动失败，请查看 backend.log${NC}"
    exit 1
fi

cd ..

# ========== 前端设置 ==========
echo -e "\n${YELLOW}[2/4] 设置前端环境...${NC}"
cd frontend

# 检查node_modules
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}安装Node.js依赖...${NC}"
    npm install
fi

# 启动前端服务器（后台运行）
echo -e "${GREEN}启动React前端服务器 (http://localhost:3000)...${NC}"
# 清空旧的日志文件
> ../frontend.log
npm start >> ../frontend.log 2>&1 &
FRONTEND_PID=$!

# 等待前端启动
sleep 5
if ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${GREEN}✓ 前端服务已启动 (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED}✗ 前端服务启动失败，请查看 frontend.log${NC}"
    cleanup
    exit 1
fi

cd ..

# ========== 显示信息 ==========
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✓ 所有服务已启动成功！${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}后端服务:${NC} http://localhost:8000"
echo -e "${GREEN}前端应用:${NC} http://localhost:3000"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}日志文件:${NC}"
echo -e "  - 后端: backend.log"
echo -e "  - 前端: frontend.log"
echo -e "\n${YELLOW}按 Ctrl+C 停止所有服务${NC}\n"

# ========== 实时显示日志 ==========
# 使用 tail 实时显示日志
tail -f backend.log frontend.log 2>/dev/null &
TAIL_PID=$!

# 等待进程结束
wait $BACKEND_PID $FRONTEND_PID 2>/dev/null

# 清理
cleanup

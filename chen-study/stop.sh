#!/bin/bash
# 停止所有运行中的服务

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}正在查找并停止服务...${NC}"

# 查找并停止Django进程
DJANGO_PIDS=$(ps aux | grep "manage.py runserver" | grep -v grep | awk '{print $2}')
if [ ! -z "$DJANGO_PIDS" ]; then
    for pid in $DJANGO_PIDS; do
        kill $pid 2>/dev/null
        echo -e "${GREEN}已停止Django进程 (PID: $pid)${NC}"
    done
else
    echo -e "${YELLOW}未找到运行中的Django进程${NC}"
fi

# 查找并停止React进程
REACT_PIDS=$(ps aux | grep "react-scripts start" | grep -v grep | awk '{print $2}')
if [ ! -z "$REACT_PIDS" ]; then
    for pid in $REACT_PIDS; do
        kill $pid 2>/dev/null
        echo -e "${GREEN}已停止React进程 (PID: $pid)${NC}"
    done
else
    echo -e "${YELLOW}未找到运行中的React进程${NC}"
fi

# 查找并停止Node进程（可能还有子进程）
NODE_PIDS=$(ps aux | grep "node.*react-scripts" | grep -v grep | awk '{print $2}')
if [ ! -z "$NODE_PIDS" ]; then
    for pid in $NODE_PIDS; do
        kill $pid 2>/dev/null
        echo -e "${GREEN}已停止Node进程 (PID: $pid)${NC}"
    done
fi

echo -e "${GREEN}所有服务已停止${NC}"

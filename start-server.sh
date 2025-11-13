#!/bin/bash

# 基金收益预估器代理服务器启动脚本
# 端口: 9988

echo "🚀 启动基金收益预估器代理服务器..."
echo "📡 端口: 9988"
echo "🌐 访问地址: http://localhost:9988"
echo ""

# 检查Node.js是否安装
if ! command -v node &> /dev/null; then
    echo "❌ 错误: 未找到Node.js"
    echo "请先安装Node.js: https://nodejs.org/"
    exit 1
fi

# 检查端口是否被占用
if lsof -Pi :9988 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  警告: 端口9988已被占用"
    echo "正在尝试关闭占用该端口的进程..."
    
    # 获取占用端口的进程ID
    PID=$(lsof -ti:9988)
    if [ ! -z "$PID" ]; then
        echo "🔄 关闭进程 $PID..."
        kill -9 $PID
        sleep 2
    fi
fi

# 启动服务器
echo "🎯 启动代理服务器..."
node proxy-server.js

#!/bin/bash

echo "============================================"
echo "  SimPy-OpenLayers 生产线仿真可视化系统"
echo "============================================"
echo ""

# 检查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3"
    echo "请先安装 Python 3.8 或更高版本"
    exit 1
fi

echo "✅ Python 版本: $(python3 --version)"
echo ""

# 检查并安装依赖
echo "📦 检查依赖..."
if ! python3 -c "import simpy" 2>/dev/null; then
    echo "⚙️  正在安装依赖包..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        exit 1
    fi
else
    echo "✅ 依赖已安装"
fi

echo ""
echo "🚀 启动服务器..."
echo ""
echo "访问地址: http://localhost:8000"
echo "按 Ctrl+C 停止服务器"
echo ""
echo "============================================"
echo ""

# 启动服务器
cd backend
python3 server.py

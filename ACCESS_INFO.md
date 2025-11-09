# 🚀 项目访问信息

## ✅ 服务器状态

项目已成功启动并运行！

## 📍 访问地址

### 内网访问（本机）
- **地址**: http://localhost:8000
- **地址**: http://127.0.0.1:8000

### 外网访问（远程访问）
- **地址**: http://185.189.48.12:8000

## 🔧 API端点

- **主页**: http://185.189.48.12:8000/
- **仿真状态**: http://185.189.48.12:8000/api/simulation/status
- **车间布局**: http://185.189.48.12:8000/api/workshop-layout
- **启动仿真**: POST http://185.189.48.12:8000/api/simulation/start
- **停止仿真**: POST http://185.189.48.12:8000/api/simulation/stop
- **WebSocket**: ws://185.189.48.12:8000/ws

## 📊 系统信息

- **服务器IP**: 185.189.48.12
- **服务端口**: 8000
- **Python版本**: 3.12.3
- **进程状态**: ✅ 运行中
- **进程ID**: 69825

## 🎮 使用说明

1. 在浏览器中打开: http://185.189.48.12:8000
2. 设置仿真时长（默认100秒）
3. 点击"开始仿真"按钮
4. 观察车间生产线的实时可视化
5. 查看统计数据和事件日志
6. 点击"停止"可随时终止仿真

## 🛠️ 管理命令

### 查看服务器进程
```bash
ps aux | grep "python3 server.py"
```

### 停止服务器
```bash
pkill -f "python3 server.py"
```

### 重启服务器
```bash
cd /root/project/Simpy-OpenLayers-test/backend
python3 server.py &
```

### 查看端口监听
```bash
ss -tlnp | grep 8000
```

## 🔍 测试API

```bash
# 测试主页
curl http://localhost:8000

# 测试仿真状态
curl http://localhost:8000/api/simulation/status

# 测试车间布局
curl http://localhost:8000/api/workshop-layout

# 启动仿真
curl -X POST http://localhost:8000/api/simulation/start?duration=100

# 停止仿真
curl -X POST http://localhost:8000/api/simulation/stop
```

## 📝 项目特点

- ✨ 基于SimPy的离散事件仿真
- 🗺️ 使用OpenLayers的地理可视化
- 🔄 WebSocket实时数据推送
- 📊 9个工位的生产线模拟
- 🎯 包含并列工序和公用缓存区
- 📈 实时统计和利用率监控

## 🔒 防火墙说明

如果无法从外网访问，可能需要配置防火墙规则：

```bash
# UFW防火墙
sudo ufw allow 8000/tcp

# iptables防火墙
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
```

---

**创建时间**: 2025-11-09  
**服务状态**: 🟢 正常运行


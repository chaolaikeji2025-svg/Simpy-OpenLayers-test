"""
FastAPI + WebSocket服务器
提供仿真控制API和实时数据推送
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import json
from typing import List, Dict
import threading
import os
from simulation import ProductionLineSimulation

app = FastAPI(title="SimPy-OpenLayers Production Simulation")

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting: {e}")

manager = ConnectionManager()

# 全局仿真实例
current_simulation = None
simulation_running = False


@app.get("/")
async def read_root():
    """返回前端页面"""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/app.js")
async def get_app_js():
    """返回前端JavaScript"""
    return FileResponse(os.path.join(FRONTEND_DIR, "app.js"))


@app.get("/api/workshop-layout")
async def get_workshop_layout():
    """获取车间布局数据（GeoJSON格式）"""
    layout = {
        "type": "FeatureCollection",
        "features": [
            # 车间边界
            {
                "type": "Feature",
                "properties": {
                    "type": "boundary",
                    "name": "车间边界"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0, 0],
                        [70, 0],
                        [70, 40],
                        [0, 40],
                        [0, 0]
                    ]]
                }
            },
            # 工位1
            {
                "type": "Feature",
                "properties": {
                    "type": "workstation",
                    "id": 0,
                    "name": "工位1 - 粗加工",
                    "status": "idle"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [10, 20]
                }
            },
            # 工位2
            {
                "type": "Feature",
                "properties": {
                    "type": "workstation",
                    "id": 1,
                    "name": "工位2 - 精加工",
                    "status": "idle"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [30, 20]
                }
            },
            # 工位3
            {
                "type": "Feature",
                "properties": {
                    "type": "workstation",
                    "id": 2,
                    "name": "工位3 - 质检",
                    "status": "idle"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [50, 20]
                }
            },
            # 缓冲区1
            {
                "type": "Feature",
                "properties": {
                    "type": "buffer",
                    "id": 0,
                    "name": "缓冲区1",
                    "capacity": 5,
                    "level": 0
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [20, 20]
                }
            },
            # 缓冲区2
            {
                "type": "Feature",
                "properties": {
                    "type": "buffer",
                    "id": 1,
                    "name": "缓冲区2",
                    "capacity": 5,
                    "level": 0
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [40, 20]
                }
            },
            # 物料输入区
            {
                "type": "Feature",
                "properties": {
                    "type": "input_zone",
                    "name": "原料区"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0, 15],
                        [5, 15],
                        [5, 25],
                        [0, 25],
                        [0, 15]
                    ]]
                }
            },
            # 成品输出区
            {
                "type": "Feature",
                "properties": {
                    "type": "output_zone",
                    "name": "成品区"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [60, 15],
                        [70, 15],
                        [70, 25],
                        [60, 25],
                        [60, 15]
                    ]]
                }
            },
            # 产线路径
            {
                "type": "Feature",
                "properties": {
                    "type": "path",
                    "name": "生产线路径"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [5, 20],
                        [10, 20],
                        [20, 20],
                        [30, 20],
                        [40, 20],
                        [50, 20],
                        [60, 20]
                    ]
                }
            }
        ]
    }
    return layout


@app.get("/api/simulation/status")
async def get_simulation_status():
    """获取仿真状态"""
    global current_simulation, simulation_running

    if current_simulation is None:
        return {
            "running": False,
            "statistics": None
        }

    return {
        "running": simulation_running,
        "statistics": current_simulation.get_statistics()
    }


@app.post("/api/simulation/start")
async def start_simulation(duration: float = 100):
    """启动仿真"""
    global current_simulation, simulation_running

    if simulation_running:
        return {"error": "Simulation already running"}

    simulation_running = True

    # 创建事件回调函数
    async def event_callback(event):
        await manager.broadcast(event)
        # 控制事件推送速度（放慢以便观察）
        await asyncio.sleep(0.1)

    # 在新线程中运行仿真
    def run_simulation():
        global simulation_running, current_simulation

        def sync_callback(event):
            # 创建新的事件循环来处理异步回调
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(event_callback(event))
            loop.close()

        current_simulation = ProductionLineSimulation(callback=sync_callback)
        stats = current_simulation.run(until=duration)

        simulation_running = False

        # 发送仿真完成消息
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(manager.broadcast({
            "type": "simulation_completed",
            "data": stats
        }))
        loop.close()

    thread = threading.Thread(target=run_simulation, daemon=True)
    thread.start()

    return {"status": "Simulation started", "duration": duration}


@app.post("/api/simulation/stop")
async def stop_simulation():
    """停止仿真"""
    global simulation_running
    simulation_running = False
    return {"status": "Simulation stopped"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接端点"""
    await manager.connect(websocket)
    try:
        while True:
            # 保持连接
            data = await websocket.receive_text()
            # 可以处理客户端发来的消息
            print(f"Received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("WebSocket disconnected")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

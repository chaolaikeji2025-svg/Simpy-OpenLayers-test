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
import contextlib
from typing import List, Dict
import threading
import os
from simulation import ProductionLineSimulation


# Dedicated event loop for callbacks running in a background thread
callback_loop: asyncio.AbstractEventLoop = None


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the startup and shutdown of the background event loop."""
    global callback_loop
    callback_loop = asyncio.new_event_loop()
    thread = threading.Thread(target=callback_loop.run_forever, daemon=True)
    thread.start()
    yield
    callback_loop.call_soon_threadsafe(callback_loop.stop)


app = FastAPI(title="SimPy-OpenLayers Production Simulation", lifespan=lifespan)

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
    """获取车间布局数据（GeoJSON格式）- 9个工位，包含并列工序和公用缓存区"""
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
                        [120, 0],
                        [120, 40],
                        [0, 40],
                        [0, 0]
                    ]]
                }
            },
            # === 工位定义 ===
            # 工位1 - 预处理
            {
                "type": "Feature",
                "properties": {
                    "type": "workstation",
                    "id": 0,
                    "name": "工位1-预处理",
                    "status": "idle"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [10, 20]
                }
            },
            # 工位2 - 粗加工A（并列）
            {
                "type": "Feature",
                "properties": {
                    "type": "workstation",
                    "id": 1,
                    "name": "工位2-粗加工A",
                    "status": "idle"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [30, 30]
                }
            },
            # 工位3 - 粗加工B（并列）
            {
                "type": "Feature",
                "properties": {
                    "type": "workstation",
                    "id": 2,
                    "name": "工位3-粗加工B",
                    "status": "idle"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [30, 10]
                }
            },
            # 工位4 - 精加工A（并列）
            {
                "type": "Feature",
                "properties": {
                    "type": "workstation",
                    "id": 3,
                    "name": "工位4-精加工A",
                    "status": "idle"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [50, 30]
                }
            },
            # 工位5 - 精加工B（并列）
            {
                "type": "Feature",
                "properties": {
                    "type": "workstation",
                    "id": 4,
                    "name": "工位5-精加工B",
                    "status": "idle"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [50, 10]
                }
            },
            # 工位6 - 组装
            {
                "type": "Feature",
                "properties": {
                    "type": "workstation",
                    "id": 5,
                    "name": "工位6-组装",
                    "status": "idle"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [70, 20]
                }
            },
            # 工位7 - 质检A（并列）
            {
                "type": "Feature",
                "properties": {
                    "type": "workstation",
                    "id": 6,
                    "name": "工位7-质检A",
                    "status": "idle"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [90, 30]
                }
            },
            # 工位8 - 质检B（并列）
            {
                "type": "Feature",
                "properties": {
                    "type": "workstation",
                    "id": 7,
                    "name": "工位8-质检B",
                    "status": "idle"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [90, 10]
                }
            },
            # 工位9 - 包装
            {
                "type": "Feature",
                "properties": {
                    "type": "workstation",
                    "id": 8,
                    "name": "工位9-包装",
                    "status": "idle"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [105, 20]
                }
            },
            # === 缓冲区定义 ===
            # 公用缓存区1（工位1后，工位2和3共享）
            {
                "type": "Feature",
                "properties": {
                    "type": "buffer",
                    "id": 0,
                    "name": "公用缓存区1",
                    "capacity": 5,
                    "level": 0
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [20, 20]
                }
            },
            # 公用缓存区2（工位2和3后，工位4和5共享）
            {
                "type": "Feature",
                "properties": {
                    "type": "buffer",
                    "id": 1,
                    "name": "公用缓存区2",
                    "capacity": 5,
                    "level": 0
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [40, 20]
                }
            },
            # 公用缓存区3（工位4和5后，工位6前）
            {
                "type": "Feature",
                "properties": {
                    "type": "buffer",
                    "id": 2,
                    "name": "公用缓存区3",
                    "capacity": 5,
                    "level": 0
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [60, 20]
                }
            },
            # 缓存区4（工位6后，工位7和8共享）
            {
                "type": "Feature",
                "properties": {
                    "type": "buffer",
                    "id": 3,
                    "name": "缓存区4",
                    "capacity": 5,
                    "level": 0
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [80, 20]
                }
            },
            # 缓存区5（工位7和8后，工位9前）
            {
                "type": "Feature",
                "properties": {
                    "type": "buffer",
                    "id": 4,
                    "name": "缓存区5",
                    "capacity": 5,
                    "level": 0
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [97.5, 20]
                }
            },
            # === 区域定义 ===
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
                        [110, 15],
                        [120, 15],
                        [120, 25],
                        [110, 25],
                        [110, 15]
                    ]]
                }
            },
            # === 产线路径（显示工艺流程）===
            # 主路径
            {
                "type": "Feature",
                "properties": {
                    "type": "path",
                    "name": "主生产线路径"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [5, 20],    # 原料区出口
                        [10, 20],   # 工位1
                        [20, 20],   # 公用缓存区1
                        [40, 20],   # 公用缓存区2
                        [60, 20],   # 公用缓存区3
                        [70, 20],   # 工位6
                        [80, 20],   # 缓存区4
                        [97.5, 20], # 缓存区5
                        [105, 20],  # 工位9
                        [115, 20]   # 成品区
                    ]
                }
            },
            # 并列路径 - 粗加工A
            {
                "type": "Feature",
                "properties": {
                    "type": "path",
                    "name": "粗加工A路径"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [20, 20],   # 公用缓存区1
                        [30, 30],   # 工位2
                        [40, 20]    # 公用缓存区2
                    ]
                }
            },
            # 并列路径 - 粗加工B
            {
                "type": "Feature",
                "properties": {
                    "type": "path",
                    "name": "粗加工B路径"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [20, 20],   # 公用缓存区1
                        [30, 10],   # 工位3
                        [40, 20]    # 公用缓存区2
                    ]
                }
            },
            # 并列路径 - 精加工A
            {
                "type": "Feature",
                "properties": {
                    "type": "path",
                    "name": "精加工A路径"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [40, 20],   # 公用缓存区2
                        [50, 30],   # 工位4
                        [60, 20]    # 公用缓存区3
                    ]
                }
            },
            # 并列路径 - 精加工B
            {
                "type": "Feature",
                "properties": {
                    "type": "path",
                    "name": "精加工B路径"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [40, 20],   # 公用缓存区2
                        [50, 10],   # 工位5
                        [60, 20]    # 公用缓存区3
                    ]
                }
            },
            # 并列路径 - 质检A
            {
                "type": "Feature",
                "properties": {
                    "type": "path",
                    "name": "质检A路径"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [80, 20],   # 缓存区4
                        [90, 30],   # 工位7
                        [97.5, 20]  # 缓存区5
                    ]
                }
            },
            # 并列路径 - 质检B
            {
                "type": "Feature",
                "properties": {
                    "type": "path",
                    "name": "质检B路径"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [80, 20],   # 缓存区4
                        [90, 10],   # 工位8
                        [97.5, 20]  # 缓存区5
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
            """Thread-safe callback to run the async event_callback in the dedicated loop."""
            asyncio.run_coroutine_threadsafe(event_callback(event), callback_loop)

        current_simulation = ProductionLineSimulation(callback=sync_callback)
        try:
            stats = current_simulation.run(until=duration)
        finally:
            simulation_running = False
            message_type = "simulation_completed"
            if current_simulation.stopped_early:
                message_type = "simulation_stopped"

            # Schedule the final broadcast in the callback loop
            asyncio.run_coroutine_threadsafe(
                manager.broadcast({
                    "type": message_type,
                    "data": stats
                }),
                callback_loop
            )

    thread = threading.Thread(target=run_simulation, daemon=True)
    thread.start()

    return {"status": "Simulation started", "duration": duration}


@app.post("/api/simulation/stop")
async def stop_simulation():
    """停止仿真"""
    global simulation_running, current_simulation

    if not simulation_running or current_simulation is None:
        return {"status": "Simulation is not running"}

    current_simulation.request_stop()
    return {"status": "Stop requested"}


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

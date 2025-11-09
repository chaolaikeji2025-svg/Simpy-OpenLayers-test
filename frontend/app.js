/**
 * SimPy-OpenLayers 前端应用
 * 使用OpenLayers可视化SimPy仿真过程
 */

// 全局变量
let map;
let vectorSource;
let partsLayer;
let workshopLayer;
let ws;
let partFeatures = {};  // 存储物料要素

// 初始化地图
function initMap() {
    // 创建车间布局图层源
    const workshopSource = new ol.source.Vector();

    // 创建车间布局图层
    workshopLayer = new ol.layer.Vector({
        source: workshopSource,
        style: function(feature) {
            const type = feature.get('type');

            switch(type) {
                case 'boundary':
                    return new ol.style.Style({
                        stroke: new ol.style.Stroke({
                            color: '#333',
                            width: 2
                        }),
                        fill: new ol.style.Fill({
                            color: 'rgba(255, 255, 255, 0.1)'
                        })
                    });

                case 'workstation':
                    const status = feature.get('status') || 'idle';
                    return new ol.style.Style({
                        image: new ol.style.Circle({
                            radius: 12,
                            fill: new ol.style.Fill({
                                color: status === 'busy' ? '#52c41a' : '#d9d9d9'
                            }),
                            stroke: new ol.style.Stroke({
                                color: '#fff',
                                width: 2
                            })
                        }),
                        text: new ol.style.Text({
                            text: feature.get('name'),
                            offsetY: -20,
                            font: '12px sans-serif',
                            fill: new ol.style.Fill({ color: '#333' }),
                            stroke: new ol.style.Stroke({
                                color: '#fff',
                                width: 3
                            })
                        })
                    });

                case 'buffer':
                    return new ol.style.Style({
                        image: new ol.style.RegularShape({
                            fill: new ol.style.Fill({ color: '#faad14' }),
                            stroke: new ol.style.Stroke({
                                color: '#fff',
                                width: 2
                            }),
                            points: 4,
                            radius: 10,
                            angle: Math.PI / 4
                        }),
                        text: new ol.style.Text({
                            text: `${feature.get('level') || 0}/${feature.get('capacity')}`,
                            offsetY: -18,
                            font: '10px sans-serif',
                            fill: new ol.style.Fill({ color: '#333' }),
                            stroke: new ol.style.Stroke({
                                color: '#fff',
                                width: 2
                            })
                        })
                    });

                case 'input_zone':
                    return new ol.style.Style({
                        fill: new ol.style.Fill({
                            color: 'rgba(24, 144, 255, 0.1)'
                        }),
                        stroke: new ol.style.Stroke({
                            color: '#1890ff',
                            width: 1,
                            lineDash: [5, 5]
                        }),
                        text: new ol.style.Text({
                            text: feature.get('name'),
                            font: '11px sans-serif',
                            fill: new ol.style.Fill({ color: '#1890ff' })
                        })
                    });

                case 'output_zone':
                    return new ol.style.Style({
                        fill: new ol.style.Fill({
                            color: 'rgba(82, 196, 26, 0.1)'
                        }),
                        stroke: new ol.style.Stroke({
                            color: '#52c41a',
                            width: 1,
                            lineDash: [5, 5]
                        }),
                        text: new ol.style.Text({
                            text: feature.get('name'),
                            font: '11px sans-serif',
                            fill: new ol.style.Fill({ color: '#52c41a' })
                        })
                    });

                case 'path':
                    return new ol.style.Style({
                        stroke: new ol.style.Stroke({
                            color: '#bfbfbf',
                            width: 3,
                            lineDash: [10, 5]
                        })
                    });

                default:
                    return null;
            }
        }
    });

    // 创建物料图层源
    vectorSource = new ol.source.Vector();

    // 创建物料图层
    partsLayer = new ol.layer.Vector({
        source: vectorSource,
        style: function(feature) {
            const status = feature.get('status');
            let color = '#1890ff';

            if (status === 'processing') {
                color = '#52c41a';
            } else if (status === 'finished') {
                color = '#722ed1';
            }

            return new ol.style.Style({
                image: new ol.style.Circle({
                    radius: 6,
                    fill: new ol.style.Fill({ color: color }),
                    stroke: new ol.style.Stroke({
                        color: '#fff',
                        width: 2
                    })
                }),
                text: new ol.style.Text({
                    text: feature.get('part_id'),
                    offsetY: -15,
                    font: '10px sans-serif',
                    fill: new ol.style.Fill({ color: '#333' }),
                    stroke: new ol.style.Stroke({
                        color: '#fff',
                        width: 2
                    })
                })
            });
        }
    });

    // 创建视图
    const view = new ol.View({
        center: [35, 20],  // 车间中心
        zoom: 2,
        projection: new ol.proj.Projection({
            code: 'WORKSHOP',
            units: 'meters',
            extent: [0, 0, 70, 40]
        })
    });

    // 创建地图
    map = new ol.Map({
        target: 'map',
        layers: [workshopLayer, partsLayer],
        view: view,
        controls: ol.control.defaults.defaults().extend([
            new ol.control.ScaleLine()
        ])
    });

    // 加载车间布局
    loadWorkshopLayout();
}

// 加载车间布局
async function loadWorkshopLayout() {
    try {
        const response = await fetch('/api/workshop-layout');
        const geojson = await response.json();

        const features = new ol.format.GeoJSON().readFeatures(geojson);
        workshopLayer.getSource().addFeatures(features);

        // 自适应缩放
        const extent = workshopLayer.getSource().getExtent();
        map.getView().fit(extent, {
            padding: [50, 50, 50, 50],
            duration: 1000
        });

    } catch (error) {
        console.error('Failed to load workshop layout:', error);
    }
}

// WebSocket连接
function connectWebSocket() {
    const wsUrl = `ws://${window.location.hostname}:8000/ws`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
        addLog('system', '已连接到仿真服务器');
    };

    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleSimulationEvent(message);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        addLog('error', 'WebSocket连接错误');
    };

    ws.onclose = () => {
        console.log('WebSocket closed');
        addLog('system', '与服务器断开连接');
    };
}

// 处理仿真事件
function handleSimulationEvent(event) {
    const { type, data, timestamp } = event;

    // 记录日志
    addLog(type, JSON.stringify(data), timestamp);

    switch(type) {
        case 'part_arrived':
            createPartFeature(data);
            break;

        case 'part_queue':
        case 'part_waiting_buffer':
        case 'part_in_buffer':
            updatePartPosition(data);
            break;

        case 'part_processing':
            updatePartPosition(data);
            updateWorkstationStatus(data.workstation_id, 'busy');
            break;

        case 'part_completed_station':
            updatePartPosition(data);
            updateWorkstationStatus(data.workstation_id, 'idle');
            break;

        case 'part_finished':
            updatePartPosition(data);
            setTimeout(() => removePartFeature(data.part_id), 2000);
            break;

        case 'simulation_completed':
            handleSimulationCompleted(data);
            break;
    }

    // 更新统计信息
    updateStatistics();
}

// 创建物料要素
function createPartFeature(data) {
    const { part_id, position } = data;

    const feature = new ol.Feature({
        geometry: new ol.geom.Point(position),
        part_id: part_id,
        status: 'arrived'
    });

    vectorSource.addFeature(feature);
    partFeatures[part_id] = feature;
}

// 更新物料位置
function updatePartPosition(data) {
    const { part_id, position, status } = data;
    const feature = partFeatures[part_id];

    if (feature) {
        const geometry = feature.getGeometry();
        const currentPos = geometry.getCoordinates();

        // 平滑动画移动
        animateMove(feature, currentPos, position, 500);

        feature.set('status', status);
    }
}

// 平滑移动动画
function animateMove(feature, start, end, duration) {
    const startTime = Date.now();

    function animate() {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // 缓动函数
        const easeProgress = progress < 0.5
            ? 2 * progress * progress
            : 1 - Math.pow(-2 * progress + 2, 2) / 2;

        const x = start[0] + (end[0] - start[0]) * easeProgress;
        const y = start[1] + (end[1] - start[1]) * easeProgress;

        feature.getGeometry().setCoordinates([x, y]);

        if (progress < 1) {
            requestAnimationFrame(animate);
        }
    }

    animate();
}

// 移除物料要素
function removePartFeature(partId) {
    const feature = partFeatures[partId];
    if (feature) {
        vectorSource.removeFeature(feature);
        delete partFeatures[partId];
    }
}

// 更新工位状态
function updateWorkstationStatus(workstationId, status) {
    const features = workshopLayer.getSource().getFeatures();
    const workstation = features.find(f =>
        f.get('type') === 'workstation' && f.get('id') === workstationId
    );

    if (workstation) {
        workstation.set('status', status);
        workstation.changed();
    }
}

// 更新统计信息
async function updateStatistics() {
    try {
        const response = await fetch('/api/simulation/status');
        const data = await response.json();

        if (data.statistics) {
            const stats = data.statistics;

            document.getElementById('produced').innerHTML =
                `${stats.parts_produced}<span class="stat-unit">件</span>`;
            document.getElementById('inSystem').innerHTML =
                `${stats.parts_in_system}<span class="stat-unit">件</span>`;
            document.getElementById('throughput').innerHTML =
                `${stats.throughput.toFixed(3)}<span class="stat-unit">件/秒</span>`;
            document.getElementById('cycleTime').innerHTML =
                `${stats.avg_cycle_time.toFixed(2)}<span class="stat-unit">秒</span>`;

            // 更新工位利用率
            updateWorkstationUtilization(stats.workstation_utilization);
        }
    } catch (error) {
        console.error('Failed to update statistics:', error);
    }
}

// 更新工位利用率显示
function updateWorkstationUtilization(utilization) {
    const container = document.getElementById('workstationStats');
    container.innerHTML = '';

    const workstationNames = ['工位1 - 粗加工', '工位2 - 精加工', '工位3 - 质检'];

    utilization.forEach((util, index) => {
        const div = document.createElement('div');
        div.className = 'workstation-status';
        div.innerHTML = `
            <div class="workstation-name">${workstationNames[index]}</div>
            <div class="workstation-util">利用率: ${(util * 100).toFixed(1)}%</div>
            <div class="utilization-bar">
                <div class="utilization-fill" style="width: ${util * 100}%"></div>
            </div>
        `;
        container.appendChild(div);
    });
}

// 添加日志
function addLog(type, message, timestamp) {
    const logContainer = document.getElementById('logContainer');
    const entry = document.createElement('div');
    entry.className = 'log-entry';

    const time = timestamp ? timestamp.toFixed(2) : new Date().toLocaleTimeString();

    entry.innerHTML = `
        <span class="log-time">[${time}]</span>
        <span class="log-type">${type}</span>
        <span>${message}</span>
    `;

    logContainer.insertBefore(entry, logContainer.firstChild);

    // 限制日志数量
    while (logContainer.children.length > 100) {
        logContainer.removeChild(logContainer.lastChild);
    }
}

// 处理仿真完成
function handleSimulationCompleted(stats) {
    document.getElementById('statusText').textContent = '仿真完成';
    document.getElementById('statusIndicator').className = 'status-indicator status-stopped';
    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;

    addLog('system', `仿真完成! 共生产 ${stats.parts_produced} 件产品`);
}

// 开始仿真
async function startSimulation() {
    const duration = parseFloat(document.getElementById('duration').value);

    // 清空物料
    vectorSource.clear();
    partFeatures = {};

    // 重置工位状态
    const features = workshopLayer.getSource().getFeatures();
    features.forEach(f => {
        if (f.get('type') === 'workstation') {
            f.set('status', 'idle');
            f.changed();
        }
    });

    document.getElementById('statusText').textContent = '仿真运行中...';
    document.getElementById('statusIndicator').className = 'status-indicator status-running';
    document.getElementById('startBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;
    document.getElementById('logContainer').innerHTML = '';

    try {
        const response = await fetch(`/api/simulation/start?duration=${duration}`, {
            method: 'POST'
        });
        const data = await response.json();
        addLog('system', `启动仿真，时长: ${duration}秒`);
    } catch (error) {
        console.error('Failed to start simulation:', error);
        addLog('error', '启动仿真失败');
    }
}

// 停止仿真
async function stopSimulation() {
    try {
        const response = await fetch('/api/simulation/stop', { method: 'POST' });
        const data = await response.json();

        document.getElementById('statusText').textContent = '已停止';
        document.getElementById('statusIndicator').className = 'status-indicator status-stopped';
        document.getElementById('startBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;

        addLog('system', '仿真已停止');
    } catch (error) {
        console.error('Failed to stop simulation:', error);
    }
}

// 页面加载完成后初始化
window.addEventListener('DOMContentLoaded', () => {
    initMap();
    connectWebSocket();

    // 绑定按钮事件
    document.getElementById('startBtn').addEventListener('click', startSimulation);
    document.getElementById('stopBtn').addEventListener('click', stopSimulation);

    // 定期更新统计信息
    setInterval(updateStatistics, 1000);
});

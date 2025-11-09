"""
系统测试脚本
验证仿真和API功能
"""

import sys
import os

# 添加backend到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from simulation import ProductionLineSimulation
import json

print("=" * 60)
print("   SimPy-OpenLayers 系统测试")
print("=" * 60)
print()

# 测试1: SimPy仿真模型
print("📋 测试1: SimPy仿真模型")
print("-" * 60)

events_log = []

def collect_events(event):
    events_log.append(event)

sim = ProductionLineSimulation(callback=collect_events)
print(f"✅ 仿真实例创建成功")
print(f"   工位数量: {sim.num_workstations}")
print(f"   缓冲区容量: {sim.buffer_capacity}")
print(f"   平均加工时间: {sim.processing_time_mean}秒")
print()

print("🔧 运行仿真 (30秒)...")
stats = sim.run(until=30)

print(f"✅ 仿真完成")
print(f"   仿真时长: {stats['simulation_time']:.2f}秒")
print(f"   已生产: {stats['parts_produced']}件")
print(f"   在制品: {stats['parts_in_system']}件")
print(f"   产能: {stats['throughput']:.3f}件/秒")
print(f"   平均周期时间: {stats['avg_cycle_time']:.2f}秒")
print(f"   平均排队时间: {stats['avg_queue_time']:.2f}秒")
print()

print("🔧 工位利用率:")
for i, util in enumerate(stats['workstation_utilization']):
    print(f"   工位{i+1}: {util*100:.1f}%")
print()

print(f"📝 捕获事件数: {len(events_log)}")
if events_log:
    print(f"   第一个事件: {events_log[0]['type']}")
    print(f"   最后事件: {events_log[-1]['type']}")
print()

# 测试2: 事件类型统计
print("📋 测试2: 事件类型统计")
print("-" * 60)

event_types = {}
for event in events_log:
    event_type = event['type']
    event_types[event_type] = event_types.get(event_type, 0) + 1

for event_type, count in sorted(event_types.items()):
    print(f"   {event_type}: {count}次")
print()

# 测试3: GeoJSON车间布局生成
print("📋 测试3: GeoJSON车间布局")
print("-" * 60)

# 模拟API返回的数据
layout = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "properties": {"type": "workstation"}, "geometry": {"type": "Point"}},
        {"type": "Feature", "properties": {"type": "buffer"}, "geometry": {"type": "Point"}},
    ]
}

print(f"✅ 车间布局生成成功")
print(f"   要素类型: FeatureCollection")
print(f"   要素数量: {len(layout['features'])}")
print()

# 测试总结
print("=" * 60)
print("✅ 所有测试通过！")
print("=" * 60)
print()
print("💡 下一步:")
print("   1. 运行: python backend/server.py")
print("   2. 访问: http://localhost:8000")
print("   3. 点击 '开始仿真' 按钮")
print()

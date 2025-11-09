"""
生产线仿真模型 - 基于SimPy
模拟一个3工位串行生产线，包含缓冲区、设备、物料流转
"""

import simpy
import random
import json
from typing import List, Dict, Any
from datetime import datetime


class ProductionLineSimulation:
    """生产线仿真类"""

    def __init__(self, callback=None):
        """
        初始化仿真环境
        :param callback: 回调函数，用于推送仿真事件
        """
        self.env = simpy.Environment()
        self.callback = callback
        self.event_log = []

        # 仿真参数
        self.num_workstations = 3
        self.buffer_capacity = 5
        self.processing_time_mean = 5.0  # 平均加工时间（秒）
        self.processing_time_std = 1.0   # 加工时间标准差
        self.arrival_interval = 4.0       # 物料到达间隔（秒）

        # 统计数据
        self.stats = {
            'produced': 0,
            'in_system': 0,
            'workstation_busy': [0, 0, 0],
            'workstation_idle': [0, 0, 0],
            'buffer_level': [0, 0],
            'queue_time': [],
            'cycle_time': []
        }

        # 创建资源（设备）
        self.workstations = [
            simpy.Resource(self.env, capacity=1)
            for _ in range(self.num_workstations)
        ]

        # 创建缓冲区（工位之间的存储区）
        self.buffers = [
            simpy.Container(self.env, capacity=self.buffer_capacity, init=0)
            for _ in range(self.num_workstations - 1)
        ]

        # 工位地图坐标（车间平面坐标，米）
        self.workstation_positions = [
            (10, 20),   # 工位1
            (30, 20),   # 工位2
            (50, 20)    # 工位3
        ]

        self.buffer_positions = [
            (20, 20),   # 缓冲区1（工位1和2之间）
            (40, 20)    # 缓冲区2（工位2和3之间）
        ]

        self.part_counter = 0

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """记录并推送事件"""
        event = {
            'timestamp': self.env.now,
            'real_time': datetime.now().isoformat(),
            'type': event_type,
            'data': data
        }
        self.event_log.append(event)

        if self.callback:
            self.callback(event)

    def part_generator(self):
        """物料生成器"""
        while True:
            # 等待到达间隔
            yield self.env.timeout(random.expovariate(1.0 / self.arrival_interval))

            # 创建新物料
            self.part_counter += 1
            part_id = f"PART-{self.part_counter:04d}"

            self.stats['in_system'] += 1

            # 记录物料到达事件
            self.log_event('part_arrived', {
                'part_id': part_id,
                'position': [5, 20],  # 起始位置
                'status': 'arrived'
            })

            # 启动物料流程
            self.env.process(self.part_process(part_id))

    def part_process(self, part_id: str):
        """物料加工流程"""
        arrival_time = self.env.now

        for i in range(self.num_workstations):
            # 如果不是第一个工位，需要从缓冲区取料
            if i > 0:
                # 记录在缓冲区等待
                self.log_event('part_waiting_buffer', {
                    'part_id': part_id,
                    'buffer_id': i - 1,
                    'position': list(self.buffer_positions[i - 1]),
                    'status': 'waiting'
                })

                # 从缓冲区取料
                yield self.buffers[i - 1].get(1)
                self.stats['buffer_level'][i - 1] = self.buffers[i - 1].level

            # 请求工位资源
            queue_start = self.env.now

            self.log_event('part_queue', {
                'part_id': part_id,
                'workstation_id': i,
                'position': list(self.workstation_positions[i]),
                'status': 'queuing'
            })

            with self.workstations[i].request() as req:
                yield req

                queue_time = self.env.now - queue_start
                self.stats['queue_time'].append(queue_time)

                # 记录开始加工
                processing_time = random.gauss(
                    self.processing_time_mean,
                    self.processing_time_std
                )
                processing_time = max(1.0, processing_time)  # 确保至少1秒

                self.log_event('part_processing', {
                    'part_id': part_id,
                    'workstation_id': i,
                    'position': list(self.workstation_positions[i]),
                    'status': 'processing',
                    'duration': processing_time
                })

                # 更新工位忙碌状态
                self.stats['workstation_busy'][i] += processing_time

                # 加工过程
                yield self.env.timeout(processing_time)

                # 记录完成加工
                self.log_event('part_completed_station', {
                    'part_id': part_id,
                    'workstation_id': i,
                    'position': list(self.workstation_positions[i]),
                    'status': 'completed'
                })

            # 如果不是最后一个工位，放入下一个缓冲区
            if i < self.num_workstations - 1:
                yield self.buffers[i].put(1)
                self.stats['buffer_level'][i] = self.buffers[i].level

                self.log_event('part_in_buffer', {
                    'part_id': part_id,
                    'buffer_id': i,
                    'position': list(self.buffer_positions[i]),
                    'status': 'in_buffer',
                    'buffer_level': self.buffers[i].level
                })

        # 所有工位完成
        cycle_time = self.env.now - arrival_time
        self.stats['cycle_time'].append(cycle_time)
        self.stats['produced'] += 1
        self.stats['in_system'] -= 1

        self.log_event('part_finished', {
            'part_id': part_id,
            'position': [60, 20],  # 成品区
            'status': 'finished',
            'cycle_time': cycle_time
        })

    def run(self, until: float = 100):
        """运行仿真"""
        # 启动物料生成器
        self.env.process(self.part_generator())

        # 运行仿真
        self.env.run(until=until)

        # 计算最终统计数据
        return self.get_statistics()

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计数据"""
        total_time = self.env.now

        return {
            'simulation_time': total_time,
            'parts_produced': self.stats['produced'],
            'parts_in_system': self.stats['in_system'],
            'throughput': self.stats['produced'] / total_time if total_time > 0 else 0,
            'avg_cycle_time': sum(self.stats['cycle_time']) / len(self.stats['cycle_time']) if self.stats['cycle_time'] else 0,
            'avg_queue_time': sum(self.stats['queue_time']) / len(self.stats['queue_time']) if self.stats['queue_time'] else 0,
            'workstation_utilization': [
                self.stats['workstation_busy'][i] / total_time if total_time > 0 else 0
                for i in range(self.num_workstations)
            ],
            'buffer_levels': self.stats['buffer_level']
        }


if __name__ == '__main__':
    # 测试仿真
    def print_event(event):
        print(f"[{event['timestamp']:.2f}s] {event['type']}: {event['data']}")

    sim = ProductionLineSimulation(callback=print_event)
    stats = sim.run(until=50)

    print("\n=== 仿真统计 ===")
    print(json.dumps(stats, indent=2))

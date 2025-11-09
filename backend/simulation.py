"""
生产线仿真模型 - 基于SimPy
模拟一个3工位串行生产线，包含缓冲区、设备、物料流转
"""

import simpy
import simpy.core
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

        # 停止控制
        self.stop_requested = False
        self.stop_event = None
        self.stopped_early = False
        self._pre_run_stop_requested = False
        self._aborted_parts = set()

        # 仿真参数
        self.num_workstations = 9
        self.buffer_capacity = 5
        self.processing_time_mean = 5.0  # 平均加工时间（秒）
        self.processing_time_std = 1.0   # 加工时间标准差
        self.arrival_interval = 6.0       # 物料到达间隔（秒）

        # 统计数据
        self.stats = {
            'produced': 0,
            'in_system': 0,
            'workstation_busy': [0] * 9,
            'workstation_idle': [0] * 9,
            'buffer_level': [0] * 5,
            'queue_time': [],
            'cycle_time': []
        }

        # 创建资源（设备）
        self.workstations = [
            simpy.Resource(self.env, capacity=1)
            for _ in range(self.num_workstations)
        ]

        # 创建缓冲区（包含公用缓存区）
        # 缓存区0: 公用缓存区1（工位1后，工位2和3共享）
        # 缓存区1: 公用缓存区2（工位2和3后，工位4和5共享）
        # 缓存区2: 公用缓存区3（工位4和5后，工位6前）
        # 缓存区3: 缓存区4（工位6后，工位7和8共享）
        # 缓存区4: 缓存区5（工位7和8后，工位9前）
        self.buffers = [
            simpy.Container(self.env, capacity=self.buffer_capacity, init=0)
            for _ in range(5)
        ]

        # 工位地图坐标（车间平面坐标，米）
        self.workstation_positions = [
            (10, 20),   # 工位1 - 预处理
            (30, 30),   # 工位2 - 粗加工A（上方）
            (30, 10),   # 工位3 - 粗加工B（下方）
            (50, 30),   # 工位4 - 精加工A（上方）
            (50, 10),   # 工位5 - 精加工B（下方）
            (70, 20),   # 工位6 - 组装
            (90, 30),   # 工位7 - 质检A（上方）
            (90, 10),   # 工位8 - 质检B（下方）
            (105, 20)   # 工位9 - 包装
        ]

        self.buffer_positions = [
            (20, 20),   # 公用缓存区1（工位1后）
            (40, 20),   # 公用缓存区2（工位2和3后）
            (60, 20),   # 公用缓存区3（工位4和5后）
            (80, 20),   # 缓存区4（工位6后）
            (97.5, 20)  # 缓存区5（工位7和8后）
        ]

        # 定义工艺路线（支持并列工序）
        # 每个物料会随机选择并列工序中的一条路线
        self.process_routes = {
            'stage1': [0],           # 工位1 - 预处理
            'stage2': [1, 2],        # 工位2或3 - 粗加工（并列）
            'stage3': [3, 4],        # 工位4或5 - 精加工（并列）
            'stage4': [5],           # 工位6 - 组装
            'stage5': [6, 7],        # 工位7或8 - 质检（并列）
            'stage6': [8]            # 工位9 - 包装
        }

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
            if self.stop_requested:
                break
            # 等待到达间隔
            yield self.env.timeout(random.expovariate(1.0 / self.arrival_interval))

            if self.stop_requested:
                break

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
        """物料加工流程 - 支持并列工序和公用缓存区"""
        arrival_time = self.env.now

        # 定义工艺路线和对应的缓冲区映射
        # (stage, buffer_before, buffer_after)
        process_stages = [
            ('stage1', None, 0),      # 工位1 → 公用缓存区1
            ('stage2', 0, 1),          # 公用缓存区1 → 工位2或3 → 公用缓存区2
            ('stage3', 1, 2),          # 公用缓存区2 → 工位4或5 → 公用缓存区3
            ('stage4', 2, 3),          # 公用缓存区3 → 工位6 → 缓存区4
            ('stage5', 3, 4),          # 缓存区4 → 工位7或8 → 缓存区5
            ('stage6', 4, None)        # 缓存区5 → 工位9 → 完成
        ]

        for stage_name, buffer_before, buffer_after in process_stages:
            if self.stop_requested:
                self._handle_part_abort(part_id)
                return
            # 如果需要从缓冲区取料
            if buffer_before is not None:
                # 记录在缓冲区等待
                self.log_event('part_waiting_buffer', {
                    'part_id': part_id,
                    'buffer_id': buffer_before,
                    'position': list(self.buffer_positions[buffer_before]),
                    'status': 'waiting'
                })

                # 从缓冲区取料
                yield self.buffers[buffer_before].get(1)
                if self.stop_requested:
                    self._handle_part_abort(part_id)
                    return
                self.stats['buffer_level'][buffer_before] = self.buffers[buffer_before].level

            # 从该阶段的可选工位中随机选择一个
            available_workstations = self.process_routes[stage_name]
            workstation_id = random.choice(available_workstations)

            # 请求工位资源
            queue_start = self.env.now

            self.log_event('part_queue', {
                'part_id': part_id,
                'workstation_id': workstation_id,
                'position': list(self.workstation_positions[workstation_id]),
                'status': 'queuing'
            })

            with self.workstations[workstation_id].request() as req:
                yield req

                if self.stop_requested:
                    self._handle_part_abort(part_id)
                    return

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
                    'workstation_id': workstation_id,
                    'position': list(self.workstation_positions[workstation_id]),
                    'status': 'processing',
                    'duration': processing_time
                })

                # 更新工位忙碌状态
                self.stats['workstation_busy'][workstation_id] += processing_time

                # 加工过程
                yield self.env.timeout(processing_time)

                if self.stop_requested:
                    self._handle_part_abort(part_id)
                    return

                # 记录完成加工
                self.log_event('part_completed_station', {
                    'part_id': part_id,
                    'workstation_id': workstation_id,
                    'position': list(self.workstation_positions[workstation_id]),
                    'status': 'completed'
                })

            # 如果需要放入缓冲区
            if buffer_after is not None:
                yield self.buffers[buffer_after].put(1)
                if self.stop_requested:
                    self._handle_part_abort(part_id)
                    return
                self.stats['buffer_level'][buffer_after] = self.buffers[buffer_after].level

                self.log_event('part_in_buffer', {
                    'part_id': part_id,
                    'buffer_id': buffer_after,
                    'position': list(self.buffer_positions[buffer_after]),
                    'status': 'in_buffer',
                    'buffer_level': self.buffers[buffer_after].level
                })

        # 所有工位完成
        cycle_time = self.env.now - arrival_time
        self.stats['cycle_time'].append(cycle_time)
        self.stats['produced'] += 1
        self.stats['in_system'] -= 1

        if part_id in self._aborted_parts:
            self._aborted_parts.remove(part_id)

        self.log_event('part_finished', {
            'part_id': part_id,
            'position': [115, 20],  # 成品区（调整坐标）
            'status': 'finished',
            'cycle_time': cycle_time
        })

    def run(self, until: float = 100):
        """运行仿真"""
        self.stopped_early = False
        self.stop_event = self.env.event()

        if self._pre_run_stop_requested:
            self.stop_requested = True
            self.stop_event.succeed()
            self._pre_run_stop_requested = False
        else:
            self.stop_requested = False

        # 启动停止监视器
        self.env.process(self._stop_monitor())

        # 启动物料生成器
        self.env.process(self.part_generator())

        # 运行仿真
        try:
            self.env.run(until=until)
        except simpy.core.StopSimulation:
            pass
        finally:
            self.stop_event = None

        # 计算最终统计数据
        return self.get_statistics()

    def _stop_monitor(self):
        """监听停止事件并终止仿真"""
        yield self.stop_event
        self.stopped_early = True
        raise simpy.core.StopSimulation("Stop requested")

    def request_stop(self):
        """请求停止仿真"""
        self.stop_requested = True
        if self.stop_event is not None and not self.stop_event.triggered:
            self.stop_event.succeed()
        else:
            self._pre_run_stop_requested = True

    def _handle_part_abort(self, part_id: str):
        """标记物料在停止时被中断"""
        if part_id in self._aborted_parts:
            return

        self._aborted_parts.add(part_id)
        if self.stats['in_system'] > 0:
            self.stats['in_system'] -= 1

        self.log_event('part_aborted', {
            'part_id': part_id,
            'status': 'aborted'
        })

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

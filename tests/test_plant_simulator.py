import unittest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator

class TestPlantSimulator(unittest.TestCase):
    """PlantSimulator类的单元测试。"""

    def setUp(self):
        """为每个测试设置默认模拟器。"""
        self.initial_quality = WaterQuality(
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            ph=7.0,
            turbidity=10.0,
            dissolved_oxygen=5.0
        )
        self.simulator = PlantSimulator(self.initial_quality)

    def test_initialization(self):
        """测试模拟器以正确状态初始化。"""
        self.assertEqual(self.simulator.current_quality, self.initial_quality)

    def test_turbidity_reduction(self):
        """测试混凝剂剂量在延迟后降低浊度。"""
        initial_turbidity = self.simulator.current_quality.turbidity
        delay = self.simulator._delay_steps

        # 应用剂量，然后应用零值以冲洗管道
        self.simulator.step(coagulant_dose=1.0, aeration_rate=0)
        for _ in range(delay):
            self.simulator.step(coagulant_dose=0, aeration_rate=0)

        new_turbidity = self.simulator.current_quality.turbidity
        self.assertLess(new_turbidity, initial_turbidity)

    def test_do_increase_and_decrease(self):
        """测试曝气在延迟后增加DO，消耗在延迟后减少DO。"""
        delay = self.simulator._delay_steps

        # 情况1：仅曝气
        simulator = PlantSimulator(self.initial_quality)
        simulator._do_consumption_rate = 0 # 禁用此部分的消耗
        initial_do = simulator.current_quality.dissolved_oxygen

        simulator.step(coagulant_dose=0, aeration_rate=10)
        for _ in range(delay):
            simulator.step(coagulant_dose=0, aeration_rate=0)

        self.assertGreater(simulator.current_quality.dissolved_oxygen, initial_do)

        # 情况2：仅消耗（延迟不影响此）
        simulator = PlantSimulator(self.initial_quality)
        initial_do = simulator.current_quality.dissolved_oxygen
        simulator.step(coagulant_dose=0, aeration_rate=0)
        self.assertLess(simulator.current_quality.dissolved_oxygen, initial_do)

    def test_bounds(self):
        """测试水质参数保持在逻辑范围内。"""
        # 高剂量强制浊度为零
        self.simulator.step(coagulant_dose=1000, aeration_rate=0)
        self.assertGreaterEqual(self.simulator.current_quality.turbidity, 0)

        # 高曝气强制DO达到饱和
        self.simulator.step(coagulant_dose=0, aeration_rate=1000)
        # 一步后，它应该更接近饱和，但不超过
        self.assertLessEqual(self.simulator.current_quality.dissolved_oxygen, 9.0)

if __name__ == '__main__':
    unittest.main()

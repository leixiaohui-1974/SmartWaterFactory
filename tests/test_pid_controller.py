import unittest
import sys
import os

# 将项目根目录添加到Python路径，以允许从water_plant_controller导入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from water_plant_controller.control.pid_controller import PIDController

class TestPIDController(unittest.TestCase):
    """PIDController类的单元测试。"""

    def test_proportional_only(self):
        """测试比例项按预期工作。"""
        # Kp=0.5, Ki=0, Kd=0. 设定点=100.
        controller = PIDController(Kp=0.5, Ki=0, Kd=0, setpoint=100)
        controller.set_output_limits(-100, 100)  # 允许负输出用于测试
        # 当前值为50，误差为50。输出应为0.5 * 50 = 25。
        output = controller.calculate(current_value=50)
        self.assertAlmostEqual(output, 25.0)
        # 当前值为100，误差为0。输出应为0。
        output = controller.calculate(current_value=100)
        self.assertAlmostEqual(output, 0.0)
        # 当前值为120，误差为-20。输出应为0.5 * -20 = -10。
        output = controller.calculate(current_value=120)
        self.assertAlmostEqual(output, -10.0)

    def test_integral_action(self):
        """测试积分项随时间累积误差。"""
        # Kp=0, Ki=0.1, Kd=0. 设定点=100.
        controller = PIDController(Kp=0, Ki=0.1, Kd=0, setpoint=100)
        # 步骤1：当前值=90，误差=10。积分 = 0 + 0.1*10*1 = 1。输出 = 1。
        output = controller.calculate(current_value=90)
        self.assertAlmostEqual(output, 1.0)
        # 步骤2：当前值=90，误差=10。积分 = 1 + 0.1*10*1 = 2。输出 = 2。
        output = controller.calculate(current_value=90)
        self.assertAlmostEqual(output, 2.0)
        # 步骤3：当前值=110，误差=-10。积分 = 2 + 0.1*(-10)*1 = 1。输出 = 1。
        output = controller.calculate(current_value=110)
        self.assertAlmostEqual(output, 1.0)

    def test_derivative_action(self):
        """测试微分项对误差变化率的响应。"""
        # Kp=0, Ki=0, Kd=0.2. 设定点=100.
        controller = PIDController(Kp=0, Ki=0, Kd=0.2, setpoint=100)
        controller.set_output_limits(-100, 100)  # 允许负输出用于测试
        # 步骤1：当前值=90，误差=10。前一个误差=0。导数=(10-0)/1=10。输出=0.2*10=2
        output = controller.calculate(current_value=90)
        self.assertAlmostEqual(output, 2.0)
        # 步骤2：当前值=95，误差=5。前一个误差=10。导数=(5-10)/1=-5。输出=0.2*(-5)=-1
        output = controller.calculate(current_value=95)
        self.assertAlmostEqual(output, -1.0)

    def test_output_clamping(self):
        """测试输出在定义的限制范围内正确限制。"""
        controller = PIDController(Kp=10, Ki=0, Kd=0, setpoint=100)
        controller.set_output_limits(0, 50)
        # 误差为10，P项为100，但应限制为50。
        output = controller.calculate(current_value=90)
        self.assertAlmostEqual(output, 50.0)
        # 误差为-10，P项为-100，但应限制为-10。
        controller.set_output_limits(-10, 10)
        output = controller.calculate(current_value=110)
        self.assertAlmostEqual(output, -10.0)

    def test_reset(self):
        """测试reset方法清除控制器的状态。"""
        controller = PIDController(Kp=0.5, Ki=0.1, Kd=0.2, setpoint=100)
        controller.calculate(current_value=90) # 误差=10
        self.assertNotEqual(controller._integral, 0)
        self.assertNotEqual(controller._previous_error, 0)

        controller.reset()
        self.assertEqual(controller._integral, 0)
        self.assertEqual(controller._previous_error, 0)

    def test_reverse_acting(self):
        """测试reverse_acting标志正确反转误差。"""
        # 正作用（默认）
        controller_direct = PIDController(Kp=1, Ki=0, Kd=0, setpoint=100)
        controller_direct.set_output_limits(-100, 100)
        # 当前值=120，误差=-20，输出=-20
        output_direct = controller_direct.calculate(current_value=120)
        self.assertAlmostEqual(output_direct, -20.0)

        # 反作用
        controller_reverse = PIDController(Kp=1, Ki=0, Kd=0, setpoint=100, reverse_acting=True)
        controller_reverse.set_output_limits(-100, 100)
        # 当前值=120，误差=-20，反转误差=20，输出=20
        output_reverse = controller_reverse.calculate(current_value=120)
        self.assertAlmostEqual(output_reverse, 20.0)

if __name__ == '__main__':
    unittest.main()

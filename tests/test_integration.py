import unittest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.control.pid_controller import PIDController
from config.settings import PID_GAINS

class TestIntegration(unittest.TestCase):
    """
    集成测试，确保控制器和模拟器协同工作。
    """

    def test_closed_loop_control(self):
        """
        测试完整的闭环控制场景，其中PID控制器
        驱动工艺模拟器达到设定点。
        """
        # 1. 初始化
        initial_quality = WaterQuality(
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            ph=7.0,
            turbidity=25.0,  # 高初始浊度
            dissolved_oxygen=4.0  # 低初始DO
        )
        simulator = PlantSimulator(initial_quality)

        # 2. 控制器设置
        turbidity_setpoint = 5.0
        do_setpoint = 8.5

        dosing_gains = PID_GAINS["dosing_controller"]
        aeration_gains = PID_GAINS["aeration_controller"]

        dosing_controller = PIDController(
            Kp=dosing_gains["Kp"], Ki=dosing_gains["Ki"], Kd=dosing_gains["Kd"],
            setpoint=turbidity_setpoint, reverse_acting=True
        )
        dosing_controller.set_output_limits(0, 10)
        dosing_controller.set_integral_limits(-5, 5)

        aeration_controller = PIDController(
            Kp=aeration_gains["Kp"], Ki=aeration_gains["Ki"], Kd=aeration_gains["Kd"],
            setpoint=do_setpoint
        )
        aeration_controller.set_output_limits(0, 20)
        aeration_controller.set_integral_limits(-15, 15)

        # 3. 模拟循环
        simulation_steps = 300
        for _ in range(simulation_steps):
            current_quality = simulator.current_quality
            coagulant_dose = dosing_controller.calculate(current_quality.turbidity)
            aeration_rate = aeration_controller.calculate(current_quality.dissolved_oxygen)
            simulator.step(coagulant_dose=coagulant_dose, aeration_rate=aeration_rate)

        # 4. 断言
        final_quality = simulator.current_quality
        self.assertAlmostEqual(final_quality.turbidity, turbidity_setpoint, delta=1.0)
        self.assertAlmostEqual(final_quality.dissolved_oxygen, do_setpoint, delta=0.5)

    def test_pid_anti_windup(self):
        """
        测试当输出饱和时，积分项不会无限增长。
        """
        # 高比例增益强制饱和
        controller = PIDController(Kp=50, Ki=0.1, Kd=0, setpoint=100)
        controller.set_output_limits(0, 10) # 低输出限制
        controller.set_integral_limits(-5, 5) # 积分限制

        # 持续向控制器输入大误差
        for _ in range(100):
            output = controller.calculate(current_value=0)
            self.assertAlmostEqual(output, 10) # 应该在最大输出处饱和

        # 积分项应该限制在其最大限制，而不是无穷大
        self.assertAlmostEqual(controller._integral, 5)

if __name__ == '__main__':
    unittest.main()

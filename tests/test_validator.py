import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.validator import validate_config

class TestConfigValidator(unittest.TestCase):
    """配置验证器的单元测试。"""

    def setUp(self):
        """为每个测试设置默认有效配置。"""
        self.valid_sim_config = {
            "do_saturation": 9.0,
            "do_consumption_rate": 0.02,
            "turbidity_decay_factor": 0.05,
            "do_increase_rate": 0.05,
            "time_delay_steps": 5,
            "aeration_non_linearity": 1.5,
        }
        self.valid_pid_gains = {
            "dosing_controller": {"Kp": 0.1, "Ki": 0.01, "Kd": 0.1},
            "aeration_controller": {"Kp": 0.8, "Ki": 0.1, "Kd": 0.1},
        }

    def test_valid_config(self):
        """测试有效配置通过验证而不出错。"""
        try:
            validate_config(self.valid_sim_config, self.valid_pid_gains)
        except ValueError:
            self.fail("validate_config()意外地引发了ValueError！")

    def test_missing_sim_key(self):
        """测试缺少模拟键会引发ValueError。"""
        invalid_config = self.valid_sim_config.copy()
        del invalid_config["do_saturation"]
        with self.assertRaisesRegex(ValueError, "缺少必需的模拟参数"):
            validate_config(invalid_config, self.valid_pid_gains)

    def test_wrong_type_sim_key(self):
        """测试模拟键类型错误会引发ValueError。"""
        invalid_config = self.valid_sim_config.copy()
        invalid_config["time_delay_steps"] = "five" # 应该是int
        with self.assertRaisesRegex(ValueError, "必须是非负整数"):
            validate_config(invalid_config, self.valid_pid_gains)

    def test_missing_pid_controller(self):
        """测试PID增益中缺少控制器会引发ValueError。"""
        invalid_gains = self.valid_pid_gains.copy()
        del invalid_gains["dosing_controller"]
        with self.assertRaisesRegex(ValueError, "缺少必需的PID控制器：'dosing_controller'"):
            validate_config(self.valid_sim_config, invalid_gains)

    def test_negative_simulation_values(self):
        """测试负的模拟参数值"""
        invalid_sim_config = self.valid_sim_config.copy()
        invalid_sim_config["time_delay_steps"] = -1
        
        with self.assertRaisesRegex(ValueError, "'time_delay_steps' 必须是非负整数"):
            validate_config(invalid_sim_config, self.valid_pid_gains)

    def test_extreme_simulation_values(self):
        """测试极端模拟参数值"""
        invalid_sim_config = self.valid_sim_config.copy()
        invalid_sim_config["do_saturation"] = -5.0
        
        with self.assertRaisesRegex(ValueError, "'do_saturation' 必须是非负数"):
            validate_config(invalid_sim_config, self.valid_pid_gains)

    def test_zero_pid_gains(self):
        """测试所有PID增益为零"""
        zero_gains = {
            "dosing_controller": {"Kp": 0.0, "Ki": 0.0, "Kd": 0.0},
            "aeration_controller": {"Kp": 0.0, "Ki": 0.0, "Kd": 0.0}
        }
        
        with self.assertRaisesRegex(ValueError, "控制器 'dosing_controller' 的所有PID增益不能同时为零"):
            validate_config(self.valid_sim_config, zero_gains)

    def test_negative_pid_gains(self):
        """测试负PID增益"""
        negative_gains = {
            "dosing_controller": {"Kp": -1.0, "Ki": 0.1, "Kd": 0.05},
            "aeration_controller": {"Kp": 1.0, "Ki": 0.1, "Kd": 0.05}
        }
        
        with self.assertRaisesRegex(ValueError, "PID增益必须为非负值"):
            validate_config(self.valid_sim_config, negative_gains)

    def test_invalid_config_types(self):
        """测试无效配置类型"""
        with self.assertRaisesRegex(TypeError, "sim_config必须是字典类型"):
            validate_config("invalid", self.valid_pid_gains)
        
        with self.assertRaisesRegex(TypeError, "pid_gains必须是字典类型"):
            validate_config(self.valid_sim_config, "invalid")

    def test_boundary_simulation_values(self):
        """测试边界模拟参数值"""
        boundary_sim_config = self.valid_sim_config.copy()
        boundary_sim_config["time_delay_steps"] = 0  # 最小有效值
        boundary_sim_config["do_saturation"] = 0.1   # 接近零的正值
        
        # 应该不抛出异常
        try:
            validate_config(boundary_sim_config, self.valid_pid_gains)
        except ValueError:
            self.fail("validate_config()意外地引发了ValueError！")

    def test_large_time_delay(self):
        """测试大时间延迟值"""
        large_delay_config = self.valid_sim_config.copy()
        large_delay_config["time_delay_steps"] = 50  # 在合理范围内
        
        # 应该不抛出异常
        try:
            validate_config(large_delay_config, self.valid_pid_gains)
        except ValueError:
            self.fail("validate_config()意外地引发了ValueError！")

    def test_missing_pid_gain(self):
        """测试控制器缺少增益会引发ValueError。"""
        invalid_gains = self.valid_pid_gains.copy()
        del invalid_gains["aeration_controller"]["Kp"]
        with self.assertRaisesRegex(ValueError, "缺少必需的PID增益 'Kp'"):
            validate_config(self.valid_sim_config, invalid_gains)

    def test_wrong_type_pid_gain(self):
        """测试PID增益类型错误会引发ValueError。"""
        invalid_gains = self.valid_pid_gains.copy()
        invalid_gains["dosing_controller"]["Ki"] = "zero point one" # 应该是float
        with self.assertRaisesRegex(ValueError, "类型不正确"):
            validate_config(self.valid_sim_config, invalid_gains)

if __name__ == '__main__':
    unittest.main()

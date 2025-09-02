import pytest
import math
from datetime import datetime
from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.control.pid_controller import PIDController
from water_plant_controller.control.on_off_controller import OnOffController
from config.settings import SIMULATION_DEFAULTS


class TestErrorHandling:
    """测试错误处理和边界条件"""
    
    def setup_method(self):
        """设置测试环境"""
        self.initial_quality = WaterQuality(
            timestamp=datetime.now(),
            ph=7.0,
            turbidity=25.0,
            dissolved_oxygen=4.0
        )
        self.simulator = PlantSimulator(self.initial_quality, SIMULATION_DEFAULTS)
        self.pid_controller = PIDController(Kp=1.0, Ki=0.1, Kd=0.05, setpoint=10.0)
        self.onoff_controller = OnOffController(setpoint=10.0)
    
    # PlantSimulator错误处理测试
    def test_plant_simulator_negative_coagulant_dose(self):
        """测试负混凝剂剂量"""
        with pytest.raises(ValueError, match="coagulant_dose必须为非负值"):
            self.simulator.step(-1.0, 5.0)
    
    def test_plant_simulator_negative_aeration_rate(self):
        """测试负曝气速率"""
        with pytest.raises(ValueError, match="aeration_rate必须为非负值"):
            self.simulator.step(5.0, -1.0)
    
    def test_plant_simulator_invalid_coagulant_type(self):
        """测试无效混凝剂类型"""
        with pytest.raises(TypeError, match="coagulant_dose必须是数值类型"):
            self.simulator.step("invalid", 5.0)
    
    def test_plant_simulator_invalid_aeration_type(self):
        """测试无效曝气类型"""
        with pytest.raises(TypeError, match="aeration_rate必须是数值类型"):
            self.simulator.step(5.0, "invalid")
    
    def test_plant_simulator_extreme_coagulant_dose(self):
        """测试极端混凝剂剂量"""
        with pytest.raises(ValueError, match="coagulant_dose过大，可能导致不稳定"):
            self.simulator.step(1500.0, 5.0)
    
    def test_plant_simulator_extreme_aeration_rate(self):
        """测试极端曝气速率"""
        with pytest.raises(ValueError, match="aeration_rate过大，可能导致不稳定"):
            self.simulator.step(5.0, 1500.0)
    
    def test_plant_simulator_nan_coagulant_dose(self):
        """测试NaN混凝剂剂量"""
        with pytest.raises(ValueError, match="coagulant_dose包含无效数值"):
            self.simulator.step(float('nan'), 5.0)
    
    def test_plant_simulator_inf_aeration_rate(self):
        """测试植物模拟器无穷大曝气速率"""
        with pytest.raises(ValueError, match="aeration_rate过大，可能导致不稳定"):
            self.simulator.step(5.0, float('inf'))
    
    # PID控制器错误处理测试
    def test_pid_controller_invalid_current_value_type(self):
        """测试PID控制器无效当前值类型"""
        with pytest.raises(TypeError, match="current_value必须是数值类型"):
            self.pid_controller.calculate("invalid")
    
    def test_pid_controller_invalid_dt_type(self):
        """测试PID控制器无效时间步长类型"""
        with pytest.raises(TypeError, match="dt必须是数值类型"):
            self.pid_controller.calculate(10.0, "invalid")
    
    def test_pid_controller_negative_dt(self):
        """测试PID控制器负时间步长"""
        with pytest.raises(ValueError, match="时间步长dt必须为非负值"):
            self.pid_controller.calculate(10.0, -1.0)
    
    def test_pid_controller_nan_current_value(self):
        """测试PID控制器NaN当前值"""
        with pytest.raises(ValueError, match="current_value包含无效数值"):
            self.pid_controller.calculate(float('nan'))
    
    def test_pid_controller_inf_dt(self):
        """测试PID控制器无穷大时间步长"""
        with pytest.raises(ValueError, match="dt包含无效数值"):
            self.pid_controller.calculate(10.0, float('inf'))
    
    def test_pid_controller_negative_gains(self):
        """测试PID控制器负增益"""
        with pytest.raises(ValueError, match="PID增益必须为非负数"):
            PIDController(Kp=-1.0, Ki=0.1, Kd=0.05, setpoint=10.0)
    
    # OnOff控制器错误处理测试
    def test_onoff_controller_invalid_current_value_type(self):
        """测试OnOff控制器无效当前值类型"""
        with pytest.raises(TypeError, match="current_value必须是数值类型"):
            self.onoff_controller.calculate("invalid")
    
    def test_onoff_controller_nan_current_value(self):
        """测试OnOff控制器NaN当前值"""
        with pytest.raises(ValueError, match="current_value包含无效数值"):
            self.onoff_controller.calculate(float('nan'))
    
    def test_onoff_controller_inf_current_value(self):
        """测试OnOff控制器无穷大当前值"""
        with pytest.raises(ValueError, match="current_value包含无效数值"):
            self.onoff_controller.calculate(float('inf'))
    
    # 边界条件测试
    def test_plant_simulator_zero_inputs(self):
        """测试零输入值"""
        result = self.simulator.step(0.0, 0.0)
        assert isinstance(result, WaterQuality)
        assert result.turbidity >= 0
        assert result.dissolved_oxygen >= 0
    
    def test_plant_simulator_maximum_valid_inputs(self):
        """测试最大有效输入值"""
        result = self.simulator.step(999.0, 999.0)
        assert isinstance(result, WaterQuality)
        assert result.turbidity >= 0
        assert result.dissolved_oxygen >= 0
    
    def test_pid_controller_zero_dt(self):
        """测试PID控制器零时间步长"""
        result = self.pid_controller.calculate(10.0, 0.0)
        assert isinstance(result, (int, float))
        assert not math.isnan(result)
        assert not math.isinf(result)
    
    def test_pid_controller_very_large_error(self):
        """测试PID控制器非常大的误差"""
        result = self.pid_controller.calculate(1000000.0)
        assert isinstance(result, (int, float))
        assert not math.isnan(result)
        assert not math.isinf(result)
    
    def test_onoff_controller_boundary_values(self):
        """测试OnOff控制器边界值"""
        # 测试等于设定点的值
        result = self.onoff_controller.calculate(10.0)
        assert result == self.onoff_controller.output_min
        
        # 测试略小于设定点的值
        result = self.onoff_controller.calculate(9.999)
        assert result == self.onoff_controller.output_max
        
        # 测试略大于设定点的值
        result = self.onoff_controller.calculate(10.001)
        assert result == self.onoff_controller.output_min
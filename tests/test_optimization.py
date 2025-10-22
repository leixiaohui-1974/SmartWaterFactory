#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PID自动调优模块测试。"""

import unittest
import numpy as np
from datetime import datetime

from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.optimization import (
    PIDParameters,
    TuningConstraints,
    TuningObjective,
    GeneticAlgorithmTuner,
    GeneticAlgorithmConfig,
    ParticleSwarmTuner,
    ParticleSwarmConfig,
    ZieglerNicholsTuner,
    ZNMethod,
    AutoTuner,
    TuningMethod,
    tune_pid,
)


class TestPIDParameters(unittest.TestCase):
    """测试PID参数类。"""

    def test_to_array(self):
        """测试转换为数组。"""
        params = PIDParameters(Kp=1.0, Ki=0.5, Kd=0.2)
        arr = params.to_array()
        self.assertTrue(isinstance(arr, np.ndarray))
        self.assertEqual(len(arr), 3)
        self.assertEqual(arr[0], 1.0)
        self.assertEqual(arr[1], 0.5)
        self.assertEqual(arr[2], 0.2)

    def test_from_array(self):
        """测试从数组创建。"""
        arr = np.array([1.5, 0.3, 0.1])
        params = PIDParameters.from_array(arr)
        self.assertEqual(params.Kp, 1.5)
        self.assertEqual(params.Ki, 0.3)
        self.assertEqual(params.Kd, 0.1)


class TestTuningConstraints(unittest.TestCase):
    """测试调优约束类。"""

    def test_clip(self):
        """测试参数裁剪。"""
        constraints = TuningConstraints(
            kp_min=0.0, kp_max=5.0,
            ki_min=0.0, ki_max=1.0,
            kd_min=0.0, kd_max=2.0
        )

        # 测试超出上界
        params = PIDParameters(Kp=10.0, Ki=2.0, Kd=5.0)
        clipped = constraints.clip(params)
        self.assertEqual(clipped.Kp, 5.0)
        self.assertEqual(clipped.Ki, 1.0)
        self.assertEqual(clipped.Kd, 2.0)

        # 测试超出下界
        params = PIDParameters(Kp=-1.0, Ki=-0.5, Kd=-1.0)
        clipped = constraints.clip(params)
        self.assertEqual(clipped.Kp, 0.0)
        self.assertEqual(clipped.Ki, 0.0)
        self.assertEqual(clipped.Kd, 0.0)

    def test_get_bounds(self):
        """测试获取边界。"""
        constraints = TuningConstraints(
            kp_min=0.0, kp_max=5.0,
            ki_min=0.0, ki_max=1.0,
            kd_min=0.0, kd_max=2.0
        )
        bounds = constraints.get_bounds()
        self.assertEqual(len(bounds), 3)
        self.assertEqual(bounds[0], (0.0, 5.0))
        self.assertEqual(bounds[1], (0.0, 1.0))
        self.assertEqual(bounds[2], (0.0, 2.0))


class TestGeneticAlgorithmTuner(unittest.TestCase):
    """测试遗传算法调优器。"""

    def setUp(self):
        """设置测试环境。"""
        self.initial_quality = WaterQuality(
            timestamp=datetime.now(),
            ph=7.0,
            turbidity=15.0,
            dissolved_oxygen=6.0
        )
        self.setpoint = 5.0
        self.constraints = TuningConstraints(
            kp_min=0.0, kp_max=5.0,
            ki_min=0.0, ki_max=1.0,
            kd_min=0.0, kd_max=2.0
        )

    def test_initialization(self):
        """测试初始化。"""
        tuner = GeneticAlgorithmTuner(
            initial_quality=self.initial_quality,
            setpoint=self.setpoint,
            constraints=self.constraints
        )
        self.assertIsNotNone(tuner)
        self.assertEqual(tuner.setpoint, self.setpoint)

    def test_tune(self):
        """测试调优过程。"""
        ga_config = GeneticAlgorithmConfig(
            population_size=10,
            elite_size=2
        )

        tuner = GeneticAlgorithmTuner(
            initial_quality=self.initial_quality,
            setpoint=self.setpoint,
            constraints=self.constraints,
            simulation_steps=100,
            ga_config=ga_config
        )

        result = tuner.tune(max_iterations=5)

        # 检查结果
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.best_params)
        self.assertGreater(result.best_score, 0)
        self.assertLessEqual(result.iterations, 5)


class TestParticleSwarmTuner(unittest.TestCase):
    """测试粒子群优化调优器。"""

    def setUp(self):
        """设置测试环境。"""
        self.initial_quality = WaterQuality(
            timestamp=datetime.now(),
            ph=7.0,
            turbidity=15.0,
            dissolved_oxygen=6.0
        )
        self.setpoint = 5.0
        self.constraints = TuningConstraints(
            kp_min=0.0, kp_max=5.0,
            ki_min=0.0, ki_max=1.0,
            kd_min=0.0, kd_max=2.0
        )

    def test_initialization(self):
        """测试初始化。"""
        tuner = ParticleSwarmTuner(
            initial_quality=self.initial_quality,
            setpoint=self.setpoint,
            constraints=self.constraints
        )
        self.assertIsNotNone(tuner)

    def test_tune(self):
        """测试调优过程。"""
        pso_config = ParticleSwarmConfig(
            swarm_size=8
        )

        tuner = ParticleSwarmTuner(
            initial_quality=self.initial_quality,
            setpoint=self.setpoint,
            constraints=self.constraints,
            simulation_steps=100,
            pso_config=pso_config
        )

        result = tuner.tune(max_iterations=5)

        # 检查结果
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.best_params)
        self.assertGreater(result.best_score, 0)


class TestZieglerNicholsTuner(unittest.TestCase):
    """测试Ziegler-Nichols调优器。"""

    def setUp(self):
        """设置测试环境。"""
        self.initial_quality = WaterQuality(
            timestamp=datetime.now(),
            ph=7.0,
            turbidity=15.0,
            dissolved_oxygen=6.0
        )
        self.setpoint = 5.0

    def test_step_response_method(self):
        """测试阶跃响应法。"""
        tuner = ZieglerNicholsTuner(
            initial_quality=self.initial_quality,
            setpoint=self.setpoint,
            method=ZNMethod.STEP_RESPONSE,
            simulation_steps=100
        )

        result = tuner.tune()

        # 检查结果
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.best_params)
        self.assertGreater(result.best_score, 0)


class TestAutoTuner(unittest.TestCase):
    """测试自动调优器。"""

    def setUp(self):
        """设置测试环境。"""
        self.initial_quality = WaterQuality(
            timestamp=datetime.now(),
            ph=7.0,
            turbidity=15.0,
            dissolved_oxygen=6.0
        )
        self.setpoint = 5.0

    def test_auto_tuning(self):
        """测试自动调优。"""
        tuner = AutoTuner(
            initial_quality=self.initial_quality,
            setpoint=self.setpoint,
            simulation_steps=100
        )

        result = tuner.tune(
            method=TuningMethod.GENETIC_ALGORITHM,
            max_iterations=3
        )

        self.assertIsNotNone(result)
        self.assertIsNotNone(result.best_params)


class TestTunePIDFunction(unittest.TestCase):
    """测试便捷函数。"""

    def test_tune_pid_function(self):
        """测试tune_pid函数。"""
        initial_quality = WaterQuality(
            timestamp=datetime.now(),
            ph=7.0,
            turbidity=15.0,
            dissolved_oxygen=6.0
        )
        setpoint = 5.0

        result = tune_pid(
            initial_quality=initial_quality,
            setpoint=setpoint,
            method=TuningMethod.GENETIC_ALGORITHM,
            max_iterations=3,
            simulation_steps=100
        )

        self.assertIsNotNone(result)
        self.assertIsNotNone(result.best_params)
        self.assertGreater(result.best_score, 0)


if __name__ == '__main__':
    unittest.main()

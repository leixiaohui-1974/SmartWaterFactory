"""Wastewater treatment modules — A/A/O process simulation, precision aeration & dosing.

面向农村污水处理的集成测试装置模块：
- wastewater_quality: 污水水质数据模型 + GB18918 达标判定
- aao_simulator: A/A/O (厌氧-缺氧-好氧) 工艺仿真
- aeration_controller: 精准曝气控制 (DO 级联 + 节能优化)
- dosing_controller: 精准加药控制 (碳源 + 絮凝剂)
"""

from water_plant_controller.wastewater.wastewater_quality import (
    WastewaterQuality,
    GB18918_LIMITS,
)
from water_plant_controller.wastewater.aao_simulator import AAOSimulator
from water_plant_controller.wastewater.aeration_controller import AerationController
from water_plant_controller.wastewater.dosing_controller import DosingController

__all__ = [
    "WastewaterQuality",
    "GB18918_LIMITS",
    "AAOSimulator",
    "AerationController",
    "DosingController",
]

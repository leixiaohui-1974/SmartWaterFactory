"""污水处理装置设计验证模块

基于方案汇报0311.pptx提出的关键问题：
1. 招标参数尺寸不合理（好氧池偏小）
2. 水力停留时间(HRT)需满足进水浓度和流量处理达标要求

提供池体设计参数验证、HRT计算、达标可行性分析。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReactorDesign:
    """反应池设计参数"""

    # 池体尺寸 (m)
    length: float = 3.0
    width: float = 2.0
    depth: float = 3.5
    # 有效水深系数
    effective_depth_ratio: float = 0.85

    @property
    def volume_m3(self) -> float:
        """有效容积 (m³)"""
        return self.length * self.width * self.depth * self.effective_depth_ratio

    def hrt_hours(self, Q_m3_h: float) -> float:
        """水力停留时间 HRT (h)"""
        if Q_m3_h <= 0:
            return float("inf")
        return self.volume_m3 / Q_m3_h


@dataclass
class PlantDesign:
    """集成测试装置整体设计参数"""

    # 设计流量
    Q_design_m3_h: float = 1.0  # m³/h (小型农村污水站)

    # 各反应池
    anaerobic: ReactorDesign = field(default_factory=lambda: ReactorDesign(
        length=2.0, width=1.5, depth=3.0,
    ))
    anoxic: ReactorDesign = field(default_factory=lambda: ReactorDesign(
        length=2.5, width=1.5, depth=3.0,
    ))
    aerobic: ReactorDesign = field(default_factory=lambda: ReactorDesign(
        length=3.0, width=2.0, depth=3.5,
    ))
    settling: ReactorDesign = field(default_factory=lambda: ReactorDesign(
        length=2.0, width=2.0, depth=3.0,
    ))

    # 回流比
    sludge_return_ratio: float = 0.5
    internal_recycle_ratio: float = 2.0

    # MLSS
    MLSS_mg_L: float = 3000.0


# ---------------------------------------------------------------------------
# HRT 推荐范围（基于GB/T标准和工程经验）
# ---------------------------------------------------------------------------

HRT_RECOMMENDATIONS = {
    "anaerobic": {"min_h": 1.0, "recommended_h": 2.0, "max_h": 4.0, "purpose": "释磷/水解酸化"},
    "anoxic": {"min_h": 1.5, "recommended_h": 3.0, "max_h": 6.0, "purpose": "反硝化脱氮"},
    "aerobic": {"min_h": 4.0, "recommended_h": 6.0, "max_h": 12.0, "purpose": "硝化/好氧降解COD"},
    "settling": {"min_h": 1.5, "recommended_h": 2.5, "max_h": 4.0, "purpose": "泥水分离"},
}

# ---------------------------------------------------------------------------
# 进水浓度与所需最低HRT关系（经验公式）
# ---------------------------------------------------------------------------

# 好氧池最低HRT经验公式: HRT_min = COD_in / (k * MLSS * f_removal)
# k: 降解速率常数 (L/mg/h), 典型值 0.0001-0.0005
# f_removal: 目标去除率

DEFAULT_K_COD = 0.0003  # L/(mg·h) 好氧COD降解速率
DEFAULT_K_NH3 = 0.0001  # L/(mg·h) 硝化速率


def calc_min_aerobic_hrt(
    COD_in: float = 250.0,
    NH3_N_in: float = 30.0,
    COD_target: float = 50.0,
    NH3_N_target: float = 5.0,
    MLSS: float = 3000.0,
    k_cod: float = DEFAULT_K_COD,
    k_nh3: float = DEFAULT_K_NH3,
) -> dict[str, Any]:
    """计算满足出水达标所需的最低好氧HRT。

    基于简化一阶动力学: C_out = C_in * exp(-k * MLSS * HRT)
    => HRT_min = -ln(C_target/C_in) / (k * MLSS)

    Args:
        COD_in: 进水COD (mg/L)
        NH3_N_in: 进水氨氮 (mg/L)
        COD_target: 出水COD目标 (mg/L, 一级A=50)
        NH3_N_target: 出水氨氮目标 (mg/L, 一级A=5)
        MLSS: 混合液悬浮固体 (mg/L)
        k_cod: COD降解速率常数
        k_nh3: 硝化速率常数

    Returns:
        dict with min_hrt_cod, min_hrt_nh3, controlling_factor, min_hrt
    """
    import math

    hrt_cod = float("inf")
    hrt_nh3 = float("inf")

    if COD_in > COD_target and k_cod * MLSS > 0:
        hrt_cod = -math.log(COD_target / COD_in) / (k_cod * MLSS)

    if NH3_N_in > NH3_N_target and k_nh3 * MLSS > 0:
        hrt_nh3 = -math.log(NH3_N_target / NH3_N_in) / (k_nh3 * MLSS)

    controlling = "COD" if hrt_cod >= hrt_nh3 else "NH3_N"
    min_hrt = max(hrt_cod, hrt_nh3)

    return {
        "min_hrt_cod_h": round(hrt_cod, 2),
        "min_hrt_nh3_h": round(hrt_nh3, 2),
        "controlling_factor": controlling,
        "min_hrt_h": round(min_hrt, 2),
        "safety_factor_hrt_h": round(min_hrt * 1.3, 2),  # 1.3倍安全系数
    }


def validate_plant_design(
    design: PlantDesign,
    influent_COD: float = 250.0,
    influent_NH3_N: float = 30.0,
    standard: str = "一级A",
) -> dict[str, Any]:
    """验证整体设计参数的合理性。

    检查各反应池HRT是否满足推荐范围和达标要求。
    直接回应PPT中提出的"参数尺寸不合理"问题。

    Args:
        design: 装置设计参数
        influent_COD: 进水COD (mg/L)
        influent_NH3_N: 进水氨氮 (mg/L)
        standard: 排放标准 ("一级A" 或 "一级B")

    Returns:
        验证报告dict
    """
    from .wastewater_quality import GB18918_LIMITS

    Q = design.Q_design_m3_h
    limits = GB18918_LIMITS.get(standard, GB18918_LIMITS["一级A"])

    # 各池HRT
    zones = {
        "anaerobic": design.anaerobic,
        "anoxic": design.anoxic,
        "aerobic": design.aerobic,
        "settling": design.settling,
    }

    hrt_report = {}
    issues = []
    warnings = []

    for zone_name, reactor in zones.items():
        hrt = reactor.hrt_hours(Q)
        rec = HRT_RECOMMENDATIONS[zone_name]
        status = "ok"

        if hrt < rec["min_h"]:
            status = "critical"
            issues.append(
                f"{zone_name}池HRT={hrt:.1f}h < 最低要求{rec['min_h']}h，"
                f"建议≥{rec['recommended_h']}h（{rec['purpose']}）"
            )
        elif hrt < rec["recommended_h"]:
            status = "warning"
            warnings.append(
                f"{zone_name}池HRT={hrt:.1f}h < 推荐值{rec['recommended_h']}h"
            )

        hrt_report[zone_name] = {
            "volume_m3": round(reactor.volume_m3, 2),
            "hrt_h": round(hrt, 2),
            "min_h": rec["min_h"],
            "recommended_h": rec["recommended_h"],
            "status": status,
            "purpose": rec["purpose"],
        }

    # 好氧池达标验证
    min_hrt = calc_min_aerobic_hrt(
        COD_in=influent_COD,
        NH3_N_in=influent_NH3_N,
        COD_target=limits["COD"],
        NH3_N_target=limits["NH3_N"],
        MLSS=design.MLSS_mg_L,
    )

    aerobic_hrt = design.aerobic.hrt_hours(Q)
    if aerobic_hrt < min_hrt["min_hrt_h"]:
        issues.append(
            f"好氧池HRT={aerobic_hrt:.1f}h < 达标所需最低HRT={min_hrt['min_hrt_h']}h"
            f"（控制因子: {min_hrt['controlling_factor']}），出水可能不达标！"
        )

    # 总HRT
    total_hrt = sum(r.hrt_hours(Q) for r in zones.values())

    # 尺寸优化建议
    recommendations = []
    if issues:
        # 计算所需最小好氧池容积
        needed_volume = min_hrt["safety_factor_hrt_h"] * Q
        current_volume = design.aerobic.volume_m3
        if needed_volume > current_volume:
            recommendations.append(
                f"建议好氧池容积从{current_volume:.1f}m³增加到≥{needed_volume:.1f}m³"
            )
            # 具体尺寸建议（保持宽度和深度不变）
            needed_length = needed_volume / (
                design.aerobic.width * design.aerobic.depth * design.aerobic.effective_depth_ratio
            )
            recommendations.append(
                f"若保持宽={design.aerobic.width}m、深={design.aerobic.depth}m，"
                f"建议长度≥{needed_length:.1f}m"
            )

    return {
        "success": True,
        "design_flow_m3_h": Q,
        "standard": standard,
        "hrt_report": hrt_report,
        "total_hrt_h": round(total_hrt, 2),
        "aerobic_min_hrt": min_hrt,
        "issues": issues,
        "warnings": warnings,
        "recommendations": recommendations,
        "overall_status": "critical" if issues else ("warning" if warnings else "ok"),
    }


def suggest_optimal_design(
    Q_m3_h: float = 1.0,
    influent_COD: float = 250.0,
    influent_NH3_N: float = 30.0,
    influent_TN: float = 40.0,
    influent_TP: float = 4.0,
    standard: str = "一级A",
    MLSS: float = 3000.0,
    safety_factor: float = 1.3,
) -> dict[str, Any]:
    """根据进水水质和处理要求，推荐最优池体设计。

    回应PPT中的问题：在满足处理要求前提下给出合理的尺寸建议。

    Args:
        Q_m3_h: 设计流量 (m³/h)
        influent_COD/NH3_N/TN/TP: 进水水质
        standard: 排放标准
        MLSS: 设计MLSS浓度
        safety_factor: 安全系数

    Returns:
        推荐设计参数dict
    """
    from .wastewater_quality import GB18918_LIMITS

    limits = GB18918_LIMITS.get(standard, GB18918_LIMITS["一级A"])

    # 好氧HRT需求
    min_hrt = calc_min_aerobic_hrt(
        COD_in=influent_COD, NH3_N_in=influent_NH3_N,
        COD_target=limits["COD"], NH3_N_target=limits["NH3_N"],
        MLSS=MLSS,
    )

    # 各池推荐HRT（取推荐值和计算值的较大者）
    aerobic_hrt = max(
        HRT_RECOMMENDATIONS["aerobic"]["recommended_h"],
        min_hrt["safety_factor_hrt_h"],
    )
    anaerobic_hrt = HRT_RECOMMENDATIONS["anaerobic"]["recommended_h"]
    anoxic_hrt = HRT_RECOMMENDATIONS["anoxic"]["recommended_h"]
    settling_hrt = HRT_RECOMMENDATIONS["settling"]["recommended_h"]

    # 如果TN高，增加缺氧池HRT
    if influent_TN > 30:
        anoxic_hrt = max(anoxic_hrt, 4.0)

    # 计算所需容积
    def calc_dimensions(volume: float, width: float = 1.5, depth: float = 3.0) -> dict:
        eff_ratio = 0.85
        length = volume / (width * depth * eff_ratio)
        return {
            "volume_m3": round(volume, 2),
            "length_m": round(length, 2),
            "width_m": width,
            "depth_m": depth,
            "hrt_h": round(volume / Q_m3_h, 2),
        }

    design = {
        "anaerobic": calc_dimensions(anaerobic_hrt * Q_m3_h),
        "anoxic": calc_dimensions(anoxic_hrt * Q_m3_h),
        "aerobic": calc_dimensions(aerobic_hrt * Q_m3_h, width=2.0, depth=3.5),
        "settling": calc_dimensions(settling_hrt * Q_m3_h, width=2.0, depth=3.0),
    }

    total_volume = sum(d["volume_m3"] for d in design.values())
    total_hrt = sum(d["hrt_h"] for d in design.values())

    return {
        "success": True,
        "design_flow_m3_h": Q_m3_h,
        "standard": standard,
        "MLSS_mg_L": MLSS,
        "safety_factor": safety_factor,
        "influent": {
            "COD": influent_COD, "NH3_N": influent_NH3_N,
            "TN": influent_TN, "TP": influent_TP,
        },
        "recommended_design": design,
        "total_volume_m3": round(total_volume, 2),
        "total_hrt_h": round(total_hrt, 2),
        "sludge_return_ratio": 0.5,
        "internal_recycle_ratio": max(2.0, influent_TN / limits["TN"] - 1),
    }

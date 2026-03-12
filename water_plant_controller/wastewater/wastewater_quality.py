"""Wastewater quality data model with GB18918-2002 compliance check.

污水水质数据类 + 城镇污水处理厂污染物排放标准 (GB18918-2002) 达标判定。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any

# GB18918-2002 一级A标准限值 (mg/L except pH)
GB18918_LIMITS: Dict[str, Dict[str, float]] = {
    "一级A": {
        "COD": 50.0,
        "NH3_N": 5.0,
        "TN": 15.0,
        "TP": 0.5,
        "SS": 10.0,
        "pH_min": 6.0,
        "pH_max": 9.0,
    },
    "一级B": {
        "COD": 60.0,
        "NH3_N": 8.0,
        "TN": 20.0,
        "TP": 1.0,
        "SS": 20.0,
        "pH_min": 6.0,
        "pH_max": 9.0,
    },
}


@dataclass
class WastewaterQuality:
    """Single wastewater quality measurement.

    Attributes:
        COD: Chemical Oxygen Demand (mg/L)
        NH3_N: Ammonia Nitrogen (mg/L)
        TN: Total Nitrogen (mg/L)
        TP: Total Phosphorus (mg/L)
        SS: Suspended Solids (mg/L)
        DO: Dissolved Oxygen (mg/L)
        pH: pH value
    """

    COD: float = 250.0
    NH3_N: float = 30.0
    TN: float = 40.0
    TP: float = 4.0
    SS: float = 200.0
    DO: float = 0.5
    pH: float = 7.0

    def check_compliance(self, standard: str = "一级A") -> Dict[str, Any]:
        """Check compliance against GB18918-2002 standard.

        Returns dict with overall pass/fail and per-parameter results.
        """
        limits = GB18918_LIMITS.get(standard, GB18918_LIMITS["一级A"])
        results: Dict[str, Any] = {}
        all_pass = True

        for param in ("COD", "NH3_N", "TN", "TP", "SS"):
            value = getattr(self, param)
            limit = limits[param]
            passed = value <= limit
            if not passed:
                all_pass = False
            results[param] = {
                "value": value,
                "limit": limit,
                "pass": passed,
                "margin": limit - value,
            }

        ph_pass = limits["pH_min"] <= self.pH <= limits["pH_max"]
        if not ph_pass:
            all_pass = False
        results["pH"] = {
            "value": self.pH,
            "range": [limits["pH_min"], limits["pH_max"]],
            "pass": ph_pass,
        }

        return {
            "standard": standard,
            "overall_pass": all_pass,
            "parameters": results,
        }

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    def removal_rate(self, influent: "WastewaterQuality") -> Dict[str, float]:
        """Calculate removal rates compared to influent quality."""
        rates = {}
        for param in ("COD", "NH3_N", "TN", "TP", "SS"):
            inf_val = getattr(influent, param)
            eff_val = getattr(self, param)
            if inf_val > 0:
                rates[param] = (inf_val - eff_val) / inf_val * 100.0
            else:
                rates[param] = 0.0
        return rates

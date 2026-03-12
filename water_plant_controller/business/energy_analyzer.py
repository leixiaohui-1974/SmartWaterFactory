"""Energy consumption analysis and optimization for water treatment plants.

Provides:
1. EnergyAnalyzer — per-process energy accounting and benchmarking
2. EnergyOptimizer — peak-valley load shifting and scheduling optimization

Tracks energy across treatment processes:
- Aeration (typically 40-60% of total)
- Pumping (20-30%)
- Mixing/stirring (5-10%)
- UV/ozone disinfection (5-10%)
- Auxiliary (lighting, HVAC, etc.)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ProcessEnergy:
    """Energy breakdown for a single process unit."""

    process_name: str
    power_kw: float = 0.0
    duration_hours: float = 0.0

    @property
    def energy_kwh(self) -> float:
        return self.power_kw * self.duration_hours

    def to_dict(self) -> Dict[str, float]:
        return {
            "process": self.process_name,
            "power_kw": self.power_kw,
            "duration_hours": self.duration_hours,
            "energy_kwh": round(self.energy_kwh, 2),
        }


@dataclass
class EnergyProfile:
    """Complete energy profile for a time period."""

    period_hours: float
    processes: List[ProcessEnergy] = field(default_factory=list)

    @property
    def total_energy_kwh(self) -> float:
        return sum(p.energy_kwh for p in self.processes)

    @property
    def total_power_kw(self) -> float:
        return sum(p.power_kw for p in self.processes)

    def breakdown_percent(self) -> Dict[str, float]:
        total = self.total_energy_kwh
        if total <= 0:
            return {p.process_name: 0.0 for p in self.processes}
        return {p.process_name: round(p.energy_kwh / total * 100, 1) for p in self.processes}


@dataclass
class EnergyBenchmark:
    """Energy efficiency benchmark result."""

    metric: str
    value: float
    unit: str
    rating: str  # "excellent", "good", "average", "poor"
    industry_avg: float
    industry_best: float


class EnergyAnalyzer:
    """Analyze energy consumption patterns and efficiency.

    Parameters
    ----------
    water_volume_m3_per_day : float
        Daily water throughput (m³/d) for per-unit-volume calculations.
    """

    def __init__(self, water_volume_m3_per_day: float = 10000.0) -> None:
        self.water_volume = water_volume_m3_per_day
        self._hourly_history: List[Dict[str, float]] = []

    def record_hourly(
        self,
        hour: int,
        aeration_kw: float = 0.0,
        pumping_kw: float = 0.0,
        mixing_kw: float = 0.0,
        disinfection_kw: float = 0.0,
        auxiliary_kw: float = 0.0,
    ) -> None:
        """Record hourly power consumption by process."""
        self._hourly_history.append({
            "hour": hour,
            "aeration": aeration_kw,
            "pumping": pumping_kw,
            "mixing": mixing_kw,
            "disinfection": disinfection_kw,
            "auxiliary": auxiliary_kw,
            "total": aeration_kw + pumping_kw + mixing_kw + disinfection_kw + auxiliary_kw,
        })

    def get_daily_profile(self) -> EnergyProfile:
        """Compute daily energy profile from hourly records."""
        process_totals: Dict[str, float] = {}
        processes = ["aeration", "pumping", "mixing", "disinfection", "auxiliary"]

        for proc in processes:
            total_kwh = sum(h.get(proc, 0.0) for h in self._hourly_history)
            process_totals[proc] = total_kwh

        period = len(self._hourly_history)
        avg_power = {k: v / max(period, 1) for k, v in process_totals.items()}
        profile = EnergyProfile(
            period_hours=float(period),
            processes=[
                ProcessEnergy(name, avg_power[name], float(period))
                for name in process_totals
            ],
        )
        return profile

    def compute_kpis(self) -> Dict[str, float]:
        """Compute energy efficiency KPIs.

        Returns
        -------
        dict
            Energy KPIs including specific energy consumption (kWh/m³).
        """
        profile = self.get_daily_profile()
        total_kwh = profile.total_energy_kwh
        hours = max(profile.period_hours, 1.0)

        # Specific energy consumption (kWh/m³)
        daily_volume = self.water_volume * (hours / 24.0)
        sec = total_kwh / daily_volume if daily_volume > 0 else 0.0

        # Peak power
        peak_kw = max((h["total"] for h in self._hourly_history), default=0.0)
        avg_kw = total_kwh / hours if hours > 0 else 0.0
        load_factor = avg_kw / peak_kw if peak_kw > 0 else 0.0

        # Aeration fraction (key efficiency indicator)
        aeration_kwh = sum(h.get("aeration", 0.0) for h in self._hourly_history)
        aeration_pct = aeration_kwh / total_kwh * 100 if total_kwh > 0 else 0.0

        return {
            "total_energy_kwh": round(total_kwh, 1),
            "specific_energy_kwh_per_m3": round(sec, 4),
            "peak_power_kw": round(peak_kw, 1),
            "average_power_kw": round(avg_kw, 1),
            "load_factor": round(load_factor, 3),
            "aeration_fraction_pct": round(aeration_pct, 1),
            "period_hours": hours,
        }

    def benchmark(self) -> List[EnergyBenchmark]:
        """Benchmark energy efficiency against industry standards.

        Industry reference values (municipal wastewater):
        - Specific energy: 0.3-0.8 kWh/m³ (avg 0.5)
        - Aeration fraction: 40-60%
        - Load factor: 0.6-0.85
        """
        kpis = self.compute_kpis()
        benchmarks = []

        # Specific energy consumption
        sec = kpis["specific_energy_kwh_per_m3"]
        if sec <= 0.3:
            rating = "excellent"
        elif sec <= 0.5:
            rating = "good"
        elif sec <= 0.7:
            rating = "average"
        else:
            rating = "poor"
        benchmarks.append(EnergyBenchmark(
            metric="单位能耗", value=round(sec, 3), unit="kWh/m³",
            rating=rating, industry_avg=0.5, industry_best=0.25,
        ))

        # Load factor
        lf = kpis["load_factor"]
        if lf >= 0.85:
            rating = "excellent"
        elif lf >= 0.7:
            rating = "good"
        elif lf >= 0.55:
            rating = "average"
        else:
            rating = "poor"
        benchmarks.append(EnergyBenchmark(
            metric="负荷率", value=round(lf, 3), unit="",
            rating=rating, industry_avg=0.7, industry_best=0.9,
        ))

        # Aeration fraction
        af = kpis["aeration_fraction_pct"]
        if af <= 45:
            rating = "excellent"
        elif af <= 55:
            rating = "good"
        elif af <= 65:
            rating = "average"
        else:
            rating = "poor"
        benchmarks.append(EnergyBenchmark(
            metric="曝气占比", value=round(af, 1), unit="%",
            rating=rating, industry_avg=55.0, industry_best=40.0,
        ))

        return benchmarks

    def get_peak_valley_distribution(self) -> Dict[str, float]:
        """Compute energy distribution across peak/flat/valley periods.

        Peak: 08:00-12:00, 17:00-21:00
        Flat: 12:00-17:00, 21:00-23:00
        Valley: 23:00-08:00
        """
        peak_kwh = 0.0
        flat_kwh = 0.0
        valley_kwh = 0.0

        for h in self._hourly_history:
            hour = h["hour"] % 24
            total = h["total"]
            if (8 <= hour < 12) or (17 <= hour < 21):
                peak_kwh += total
            elif (23 <= hour or hour < 8):
                valley_kwh += total
            else:
                flat_kwh += total

        total = peak_kwh + flat_kwh + valley_kwh
        return {
            "peak_kwh": round(peak_kwh, 1),
            "flat_kwh": round(flat_kwh, 1),
            "valley_kwh": round(valley_kwh, 1),
            "peak_pct": round(peak_kwh / total * 100, 1) if total > 0 else 0.0,
            "flat_pct": round(flat_kwh / total * 100, 1) if total > 0 else 0.0,
            "valley_pct": round(valley_kwh / total * 100, 1) if total > 0 else 0.0,
        }


class EnergyOptimizer:
    """Optimize energy consumption via load shifting.

    Identifies opportunities to shift flexible loads (backwash, sludge
    processing, non-critical pumping) from peak to valley periods.

    Parameters
    ----------
    peak_rate : float
        Peak electricity rate (元/kWh).
    flat_rate : float
        Flat electricity rate.
    valley_rate : float
        Valley (off-peak) rate.
    """

    def __init__(
        self,
        peak_rate: float = 1.05,
        flat_rate: float = 0.68,
        valley_rate: float = 0.35,
    ) -> None:
        self.peak_rate = peak_rate
        self.flat_rate = flat_rate
        self.valley_rate = valley_rate

    def _get_rate(self, hour: int) -> float:
        h = hour % 24
        if (8 <= h < 12) or (17 <= h < 21):
            return self.peak_rate
        elif (23 <= h or h < 8):
            return self.valley_rate
        return self.flat_rate

    def analyze_savings(
        self,
        hourly_data: List[Dict[str, float]],
        shiftable_fraction: float = 0.15,
    ) -> Dict:
        """Analyze potential savings from load shifting.

        Parameters
        ----------
        hourly_data : list of dict
            Hourly records with 'hour' and 'total' keys.
        shiftable_fraction : float
            Fraction of load that can be shifted (default 15%).

        Returns
        -------
        dict
            Current cost, optimized cost, savings amount and percentage.
        """
        current_cost = 0.0
        total_shiftable_kwh = 0.0
        peak_shiftable_kwh = 0.0

        for h in hourly_data:
            hour = int(h["hour"])
            total = h["total"]
            rate = self._get_rate(hour)
            current_cost += total * rate

            shiftable = total * shiftable_fraction
            total_shiftable_kwh += shiftable
            if (8 <= hour % 24 < 12) or (17 <= hour % 24 < 21):
                peak_shiftable_kwh += shiftable

        # Optimized: shift peak shiftable load to valley
        optimized_cost = current_cost - peak_shiftable_kwh * (self.peak_rate - self.valley_rate)

        savings = current_cost - optimized_cost
        savings_pct = savings / current_cost * 100 if current_cost > 0 else 0.0

        return {
            "current_cost_yuan": round(current_cost, 2),
            "optimized_cost_yuan": round(optimized_cost, 2),
            "savings_yuan": round(savings, 2),
            "savings_percent": round(savings_pct, 1),
            "peak_shiftable_kwh": round(peak_shiftable_kwh, 1),
            "total_shiftable_kwh": round(total_shiftable_kwh, 1),
        }

    def recommend_schedule(
        self,
        flexible_loads: List[Dict[str, float]],
    ) -> List[Dict]:
        """Recommend optimal scheduling for flexible loads.

        Parameters
        ----------
        flexible_loads : list of dict
            Each with 'name', 'power_kw', 'duration_hours', 'current_hour'.

        Returns
        -------
        list of dict
            Recommended schedule with cost comparison.
        """
        recommendations = []

        # Valley hours (cheapest)
        valley_hours = list(range(23, 24)) + list(range(0, 8))

        for load in flexible_loads:
            name = load["name"]
            power = load["power_kw"]
            duration = load["duration_hours"]
            current_hour = int(load.get("current_hour", 10))

            current_rate = self._get_rate(current_hour)
            current_cost = power * duration * current_rate

            # Find cheapest start time
            best_cost = float("inf")
            best_hour = current_hour

            for start in range(24):
                cost = 0.0
                for offset in range(int(duration)):
                    h = (start + offset) % 24
                    cost += power * self._get_rate(h)
                if cost < best_cost:
                    best_cost = cost
                    best_hour = start

            savings = current_cost - best_cost

            recommendations.append({
                "load_name": name,
                "power_kw": power,
                "duration_hours": duration,
                "current_hour": current_hour,
                "recommended_hour": best_hour,
                "current_cost_yuan": round(current_cost, 2),
                "optimized_cost_yuan": round(best_cost, 2),
                "savings_yuan": round(savings, 2),
                "action": "移至谷电时段" if best_hour != current_hour else "无需调整",
            })

        recommendations.sort(key=lambda r: r["savings_yuan"], reverse=True)
        return recommendations

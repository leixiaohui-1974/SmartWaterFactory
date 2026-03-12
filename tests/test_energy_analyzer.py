"""Tests for energy analysis and optimization module."""

from __future__ import annotations

import pytest

from water_plant_controller.business.energy_analyzer import (
    EnergyAnalyzer,
    EnergyOptimizer,
    EnergyProfile,
    ProcessEnergy,
)


# ---------------------------------------------------------------------------
# ProcessEnergy / EnergyProfile
# ---------------------------------------------------------------------------


class TestProcessEnergy:
    def test_energy_calculation(self):
        p = ProcessEnergy("aeration", power_kw=50.0, duration_hours=24.0)
        assert p.energy_kwh == 1200.0

    def test_to_dict(self):
        p = ProcessEnergy("pumping", power_kw=20.0, duration_hours=10.0)
        d = p.to_dict()
        assert d["energy_kwh"] == 200.0
        assert d["process"] == "pumping"


class TestEnergyProfile:
    def test_total_energy(self):
        profile = EnergyProfile(
            period_hours=24.0,
            processes=[
                ProcessEnergy("aeration", 50.0, 24.0),
                ProcessEnergy("pumping", 20.0, 24.0),
            ],
        )
        assert profile.total_energy_kwh == 1680.0

    def test_breakdown_percent(self):
        profile = EnergyProfile(
            period_hours=24.0,
            processes=[
                ProcessEnergy("aeration", 60.0, 24.0),  # 1440 kWh
                ProcessEnergy("pumping", 40.0, 24.0),   # 960 kWh
            ],
        )
        breakdown = profile.breakdown_percent()
        assert breakdown["aeration"] == 60.0
        assert breakdown["pumping"] == 40.0


# ---------------------------------------------------------------------------
# EnergyAnalyzer
# ---------------------------------------------------------------------------


class TestEnergyAnalyzer:
    @staticmethod
    def _make_analyzer_with_data():
        analyzer = EnergyAnalyzer(water_volume_m3_per_day=10000)
        for hour in range(24):
            # Simulate varying load
            base_aeration = 80.0 if 6 <= hour <= 22 else 40.0
            analyzer.record_hourly(
                hour=hour,
                aeration_kw=base_aeration,
                pumping_kw=30.0,
                mixing_kw=10.0,
                disinfection_kw=8.0,
                auxiliary_kw=5.0,
            )
        return analyzer

    def test_daily_profile(self):
        analyzer = self._make_analyzer_with_data()
        profile = analyzer.get_daily_profile()
        assert profile.period_hours == 24.0
        assert profile.total_energy_kwh > 0
        assert len(profile.processes) == 5

    def test_kpis(self):
        analyzer = self._make_analyzer_with_data()
        kpis = analyzer.compute_kpis()

        assert kpis["total_energy_kwh"] > 0
        assert kpis["specific_energy_kwh_per_m3"] > 0
        assert 0 < kpis["load_factor"] <= 1.0
        assert 0 < kpis["aeration_fraction_pct"] < 100

    def test_specific_energy_reasonable(self):
        """Specific energy should be in realistic range for water treatment."""
        analyzer = self._make_analyzer_with_data()
        kpis = analyzer.compute_kpis()
        sec = kpis["specific_energy_kwh_per_m3"]
        # Typical range 0.1-2.0 kWh/m³
        assert 0.05 < sec < 5.0

    def test_benchmark(self):
        analyzer = self._make_analyzer_with_data()
        benchmarks = analyzer.benchmark()

        assert len(benchmarks) == 3
        for bm in benchmarks:
            assert bm.rating in ("excellent", "good", "average", "poor")
            assert bm.industry_avg > 0

    def test_peak_valley_distribution(self):
        analyzer = self._make_analyzer_with_data()
        dist = analyzer.get_peak_valley_distribution()

        assert dist["peak_kwh"] > 0
        assert dist["valley_kwh"] > 0
        total_pct = dist["peak_pct"] + dist["flat_pct"] + dist["valley_pct"]
        assert abs(total_pct - 100.0) < 0.5

    def test_empty_analyzer(self):
        analyzer = EnergyAnalyzer()
        kpis = analyzer.compute_kpis()
        assert kpis["total_energy_kwh"] == 0.0


# ---------------------------------------------------------------------------
# EnergyOptimizer
# ---------------------------------------------------------------------------


class TestEnergyOptimizer:
    @staticmethod
    def _make_hourly_data():
        data = []
        for hour in range(24):
            data.append({"hour": hour, "total": 100.0})
        return data

    def test_savings_positive(self):
        """Load shifting should produce non-negative savings."""
        opt = EnergyOptimizer()
        data = self._make_hourly_data()
        result = opt.analyze_savings(data, shiftable_fraction=0.2)

        assert result["savings_yuan"] >= 0
        assert result["savings_percent"] >= 0

    def test_higher_shift_more_savings(self):
        """More shiftable load should yield more savings."""
        opt = EnergyOptimizer()
        data = self._make_hourly_data()

        low = opt.analyze_savings(data, shiftable_fraction=0.05)
        high = opt.analyze_savings(data, shiftable_fraction=0.30)
        assert high["savings_yuan"] >= low["savings_yuan"]

    def test_peak_valley_rate_differential(self):
        """Larger rate differential should yield more savings."""
        opt_small = EnergyOptimizer(peak_rate=0.8, valley_rate=0.5)
        opt_large = EnergyOptimizer(peak_rate=1.5, valley_rate=0.2)
        data = self._make_hourly_data()

        r_small = opt_small.analyze_savings(data)
        r_large = opt_large.analyze_savings(data)
        assert r_large["savings_yuan"] > r_small["savings_yuan"]

    def test_recommend_schedule(self):
        opt = EnergyOptimizer()
        loads = [
            {"name": "反冲洗", "power_kw": 30, "duration_hours": 2, "current_hour": 10},
            {"name": "污泥脱水", "power_kw": 15, "duration_hours": 4, "current_hour": 14},
            {"name": "加药搅拌", "power_kw": 5, "duration_hours": 1, "current_hour": 9},
        ]
        recs = opt.recommend_schedule(loads)

        assert len(recs) == 3
        for rec in recs:
            assert rec["optimized_cost_yuan"] <= rec["current_cost_yuan"]
            assert 0 <= rec["recommended_hour"] < 24

    def test_recommend_shifts_to_valley(self):
        """Peak-hour loads should be recommended to shift to valley."""
        opt = EnergyOptimizer()
        loads = [
            {"name": "高峰负载", "power_kw": 50, "duration_hours": 1, "current_hour": 10},
        ]
        recs = opt.recommend_schedule(loads)
        # Should recommend a valley hour (23-07)
        rec_hour = recs[0]["recommended_hour"]
        assert (23 <= rec_hour or rec_hour < 8), f"Expected valley hour, got {rec_hour}"

    def test_already_optimal_no_change(self):
        """Load already in valley should not be moved."""
        opt = EnergyOptimizer()
        loads = [
            {"name": "谷电负载", "power_kw": 20, "duration_hours": 1, "current_hour": 3},
        ]
        recs = opt.recommend_schedule(loads)
        # Valley hour is already cheapest, recommended should also be valley
        assert recs[0]["recommended_hour"] in range(0, 8) or recs[0]["recommended_hour"] == 23

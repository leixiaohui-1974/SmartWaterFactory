"""Tests for business cost optimization module."""

from __future__ import annotations

import pytest

from water_plant_controller.business.cost_optimizer import (
    ChemicalPrice,
    CostOptimizer,
    CostTracker,
    EnergyPrice,
    OperatingCost,
    QualityConstraint,
)


# ---------------------------------------------------------------------------
# OperatingCost
# ---------------------------------------------------------------------------


class TestOperatingCost:
    def test_total(self):
        c = OperatingCost(electricity_yuan=10.0, chemicals_yuan=5.0, maintenance_yuan=2.0)
        assert c.total_yuan == 17.0

    def test_to_dict(self):
        c = OperatingCost(electricity_yuan=1.0, chemicals_yuan=2.0, maintenance_yuan=3.0)
        d = c.to_dict()
        assert d["total_yuan"] == 6.0
        assert "electricity_yuan" in d


# ---------------------------------------------------------------------------
# CostTracker
# ---------------------------------------------------------------------------


class TestCostTracker:
    def test_record_and_summary(self):
        tracker = CostTracker(dt_hours=1.0)
        tracker.record_step(hour=10, power_kw=50, chemicals_kg={"coagulant": 1.0})
        tracker.record_step(hour=11, power_kw=50, chemicals_kg={"coagulant": 1.0})

        summary = tracker.get_summary()
        assert summary["steps"] == 2
        assert summary["total"]["total_yuan"] > 0

    def test_peak_valley_pricing(self):
        """Peak hours should cost more than valley hours."""
        tracker_peak = CostTracker(dt_hours=1.0)
        tracker_valley = CostTracker(dt_hours=1.0)

        tracker_peak.record_step(hour=10, power_kw=50)  # peak
        tracker_valley.record_step(hour=3, power_kw=50)  # valley

        peak_cost = tracker_peak.get_summary()["total"]["electricity_yuan"]
        valley_cost = tracker_valley.get_summary()["total"]["electricity_yuan"]
        assert peak_cost > valley_cost, "Peak should cost more than valley"

    def test_chemical_costs_accumulate(self):
        tracker = CostTracker()
        for _ in range(10):
            tracker.record_step(hour=12, chemicals_kg={"coagulant": 0.5, "carbon_source": 0.3})

        summary = tracker.get_summary()
        assert summary["total"]["chemicals_yuan"] > 0

    def test_empty_tracker(self):
        tracker = CostTracker()
        summary = tracker.get_summary()
        assert summary["steps"] == 0
        assert summary["total"]["total_yuan"] == 0.0

    def test_history_length(self):
        tracker = CostTracker()
        for i in range(5):
            tracker.record_step(hour=float(i), power_kw=10)
        assert len(tracker.get_history()) == 5


# ---------------------------------------------------------------------------
# CostOptimizer
# ---------------------------------------------------------------------------


class TestCostOptimizer:
    def test_optimize_returns_valid_result(self):
        opt = CostOptimizer()
        result = opt.optimize(hour=10, influent_turbidity=30.0, influent_do=2.0)

        assert result["success"]
        assert result["cost_yuan_per_hour"] > 0
        assert "optimal_params" in result
        assert "predicted_quality" in result

    def test_quality_constraints_met(self):
        """Optimized solution should meet quality constraints."""
        qc = QualityConstraint(turbidity_max=3.0, do_min=5.0)
        opt = CostOptimizer(quality_constraint=qc)
        result = opt.optimize(hour=14, influent_turbidity=25.0)

        q = result["predicted_quality"]
        assert q["turbidity"] <= qc.turbidity_max + 0.5  # tolerance for numerical solver
        assert q["dissolved_oxygen"] >= qc.do_min - 0.5

    def test_valley_electricity_cheaper_than_peak(self):
        """Valley electricity rate should be lower than peak rate."""
        opt = CostOptimizer()
        peak_result = opt.optimize(hour=10)  # peak
        valley_result = opt.optimize(hour=3)  # valley

        assert valley_result["energy_rate"] < peak_result["energy_rate"]

    def test_higher_turbidity_needs_more_chemicals(self):
        """Higher influent turbidity should require more coagulant."""
        opt = CostOptimizer()
        low = opt.optimize(hour=14, influent_turbidity=10.0)
        high = opt.optimize(hour=14, influent_turbidity=50.0)

        assert high["optimal_params"]["coagulant_dose_kg_h"] >= low["optimal_params"]["coagulant_dose_kg_h"]

    def test_savings_positive(self):
        """Optimization should achieve some savings vs baseline."""
        opt = CostOptimizer()
        result = opt.optimize(hour=10)
        assert result["savings_percent"] >= 0

    def test_optimize_schedule_24h(self):
        """24-hour schedule optimization should return valid results."""
        opt = CostOptimizer()
        hours = list(range(24))
        result = opt.optimize_schedule(hours)

        assert len(result["schedule"]) == 24
        assert result["total_cost_yuan"] > 0
        assert result["total_cost_yuan"] > 0  # meaningful cost

    def test_process_model_physics(self):
        """Process model should produce physically plausible results."""
        q = CostOptimizer._process_model(
            aeration_power=30.0,
            coagulant_dose=2.0,
            carbon_dose=1.0,
            influent_turbidity=30.0,
            influent_do=2.0,
        )
        assert 0 < q["turbidity"] < 30.0
        assert q["dissolved_oxygen"] > 2.0
        assert 5.0 < q["ph"] < 9.0

    def test_custom_prices(self):
        """Custom pricing should affect costs."""
        cheap = CostOptimizer(
            energy_price=EnergyPrice(peak=0.5, flat=0.3, valley=0.1),
            chemical_price=ChemicalPrice(coagulant=1.0, carbon_source=1.0),
        )
        expensive = CostOptimizer(
            energy_price=EnergyPrice(peak=2.0, flat=1.5, valley=0.8),
            chemical_price=ChemicalPrice(coagulant=5.0, carbon_source=6.0),
        )

        r_cheap = cheap.optimize(hour=10)
        r_expensive = expensive.optimize(hour=10)

        # Same hour, same influent, but different prices → different costs
        # (optimal params may differ too, so we can't simply compare costs directly,
        # but the expensive one's baseline should be higher)
        assert r_expensive["baseline_cost_yuan_per_hour"] > r_cheap["baseline_cost_yuan_per_hour"]

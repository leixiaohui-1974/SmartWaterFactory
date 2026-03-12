"""Tests for predictive maintenance module."""

from __future__ import annotations

import numpy as np
import pytest

from water_plant_controller.maintenance.predictive_maintenance import (
    AnomalyDetector,
    EquipmentStatus,
    MaintenancePredictor,
    MaintenanceScheduler,
    RULPrediction,
)


# ---------------------------------------------------------------------------
# EquipmentStatus
# ---------------------------------------------------------------------------


class TestEquipmentStatus:
    def test_health_score_nominal(self):
        """New equipment at nominal should have high health score."""
        eq = EquipmentStatus(
            equipment_id="pump-01", name="进水泵 #1",
            operating_hours=100, rated_life_hours=20000,
            performance_index=1.0, vibration_level=0.5, temperature_delta=2.0,
        )
        assert eq.health_score() > 80

    def test_health_score_degraded(self):
        """Heavily used equipment should have lower health score."""
        eq = EquipmentStatus(
            equipment_id="pump-02", name="进水泵 #2",
            operating_hours=18000, rated_life_hours=20000,
            performance_index=0.6, vibration_level=6.0, temperature_delta=15.0,
        )
        assert eq.health_score() < 50

    def test_health_score_bounds(self):
        """Health score should be between 0 and 100."""
        for hours in [0, 10000, 25000]:
            for perf in [0.0, 0.5, 1.0]:
                eq = EquipmentStatus(
                    equipment_id="x", name="x",
                    operating_hours=hours, performance_index=perf,
                    vibration_level=np.random.uniform(0, 15),
                    temperature_delta=np.random.uniform(0, 40),
                )
                assert 0.0 <= eq.health_score() <= 100.0


# ---------------------------------------------------------------------------
# Anomaly Detection
# ---------------------------------------------------------------------------


class TestAnomalyDetector:
    @staticmethod
    def _make_normal_data(n=200):
        np.random.seed(42)
        return np.column_stack([
            np.random.normal(50, 2, n),   # vibration
            np.random.normal(25, 1, n),   # temperature
            np.random.normal(0.9, 0.05, n),  # power factor
        ])

    def test_zscore_normal_not_anomaly(self):
        data = self._make_normal_data()
        det = AnomalyDetector(method="zscore")
        det.fit(data)

        normal_reading = np.array([50, 25, 0.9])
        result = det.detect(normal_reading)
        assert not result.is_anomaly
        assert result.method == "zscore"

    def test_zscore_extreme_is_anomaly(self):
        data = self._make_normal_data()
        det = AnomalyDetector(method="zscore", z_threshold=3.0)
        det.fit(data)

        extreme_reading = np.array([70, 40, 0.3])
        result = det.detect(extreme_reading)
        assert result.is_anomaly
        assert result.score > 3.0

    def test_detect_batch(self):
        data = self._make_normal_data()
        det = AnomalyDetector(method="zscore")
        det.fit(data)

        batch = np.array([
            [50, 25, 0.9],   # normal
            [70, 40, 0.3],   # anomaly
            [51, 24, 0.88],  # normal
        ])
        results = det.detect_batch(batch)
        assert len(results) == 3
        assert not results[0].is_anomaly
        assert results[1].is_anomaly

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("sklearn"),
        reason="scikit-learn not installed",
    )
    def test_isolation_forest(self):
        data = self._make_normal_data(500)
        det = AnomalyDetector(method="isolation_forest")
        det.fit(data)

        normal = det.detect(np.array([50, 25, 0.9]))
        extreme = det.detect(np.array([80, 45, 0.2]))
        assert not normal.is_anomaly
        assert extreme.is_anomaly
        assert extreme.score > normal.score

    def test_detect_before_fit(self):
        det = AnomalyDetector()
        with pytest.raises(RuntimeError, match="fit"):
            det.detect(np.array([1, 2, 3]))


# ---------------------------------------------------------------------------
# RUL Prediction
# ---------------------------------------------------------------------------


class TestMaintenancePredictor:
    def test_new_equipment_high_rul(self):
        """New equipment should have high RUL."""
        predictor = MaintenancePredictor()
        eq = EquipmentStatus(
            equipment_id="blower-01", name="曝气风机 #1",
            operating_hours=500, performance_index=0.98,
        )
        rul = predictor.estimate_rul(eq)
        assert rul.rul_hours > 10000
        assert rul.rul_days > 400

    def test_worn_equipment_low_rul(self):
        """Heavily degraded equipment should have low RUL."""
        predictor = MaintenancePredictor()
        eq = EquipmentStatus(
            equipment_id="blower-02", name="曝气风机 #2",
            operating_hours=15000, performance_index=0.55,
            vibration_level=8.0, temperature_delta=20.0,
        )
        rul = predictor.estimate_rul(eq)
        assert rul.rul_hours < 2000

    def test_failed_equipment_zero_rul(self):
        """Equipment below failure threshold should have RUL=0."""
        predictor = MaintenancePredictor(failure_threshold=0.5)
        eq = EquipmentStatus(
            equipment_id="pump-03", name="回流泵 #3",
            operating_hours=20000, performance_index=0.4,
        )
        rul = predictor.estimate_rul(eq)
        assert rul.rul_hours == 0.0

    def test_vibration_reduces_rul(self):
        """High vibration should reduce RUL."""
        predictor = MaintenancePredictor()
        eq_low_vib = EquipmentStatus(
            equipment_id="a", name="a",
            operating_hours=5000, performance_index=0.9,
            vibration_level=1.0,
        )
        eq_high_vib = EquipmentStatus(
            equipment_id="b", name="b",
            operating_hours=5000, performance_index=0.9,
            vibration_level=10.0,
        )
        rul_low = predictor.estimate_rul(eq_low_vib)
        rul_high = predictor.estimate_rul(eq_high_vib)
        assert rul_low.rul_hours > rul_high.rul_hours

    def test_fleet_estimation(self):
        predictor = MaintenancePredictor()
        fleet = [
            EquipmentStatus("p1", "泵1", 1000, 20000, 0.95),
            EquipmentStatus("p2", "泵2", 10000, 20000, 0.7),
            EquipmentStatus("p3", "泵3", 18000, 20000, 0.55),
        ]
        results = predictor.estimate_fleet(fleet)
        assert len(results) == 3
        # RUL should decrease with degradation
        assert results[0].rul_hours > results[1].rul_hours > results[2].rul_hours


# ---------------------------------------------------------------------------
# Maintenance Scheduling
# ---------------------------------------------------------------------------


class TestMaintenanceScheduler:
    @staticmethod
    def _make_fleet():
        return [
            EquipmentStatus("pump-01", "进水泵 #1", 500, 20000, 0.98, 1.0, 2.0),
            EquipmentStatus("pump-02", "进水泵 #2", 12000, 20000, 0.65, 5.5, 12.0),
            EquipmentStatus("blower-01", "风机 #1", 18000, 20000, 0.52, 8.0, 18.0),
            EquipmentStatus("mixer-01", "搅拌器 #1", 8000, 15000, 0.8, 3.0, 5.0),
            EquipmentStatus("pump-03", "回流泵 #3", 19500, 20000, 0.45, 9.0, 22.0),
        ]

    def test_plan_generation(self):
        scheduler = MaintenanceScheduler()
        fleet = self._make_fleet()
        plans = scheduler.generate_plan(fleet)

        assert len(plans) == 5
        # First plan should be the most urgent
        assert plans[0].priority in ("urgent", "high")
        # All plans should have valid fields
        for plan in plans:
            assert plan.priority in ("urgent", "high", "medium", "low")
            assert plan.estimated_cost_yuan > 0
            assert plan.health_score >= 0

    def test_urgent_equipment_first(self):
        """Failed equipment should be scheduled first."""
        scheduler = MaintenanceScheduler()
        fleet = self._make_fleet()
        plans = scheduler.generate_plan(fleet)

        # pump-03 (perf=0.45) should be urgent and near the top
        urgent_ids = [p.equipment_id for p in plans if p.priority == "urgent"]
        assert "pump-03" in urgent_ids

    def test_fleet_summary(self):
        scheduler = MaintenanceScheduler()
        fleet = self._make_fleet()
        summary = scheduler.get_fleet_summary(fleet)

        assert summary["equipment_count"] == 5
        assert 0 < summary["average_health_score"] < 100
        assert summary["total_estimated_cost_yuan"] > 0
        assert len(summary["plans"]) == 5

        counts = summary["priority_counts"]
        assert counts["urgent"] + counts["high"] + counts["medium"] + counts["low"] == 5

    def test_all_healthy_fleet(self):
        """Fleet of healthy equipment should have low priority maintenance."""
        scheduler = MaintenanceScheduler()
        fleet = [
            EquipmentStatus(f"eq-{i}", f"设备{i}", 100, 20000, 0.99, 0.5, 1.0)
            for i in range(3)
        ]
        plans = scheduler.generate_plan(fleet)
        for plan in plans:
            assert plan.priority == "low"

    def test_priority_ordering(self):
        """Plans should be sorted by priority then by RUL."""
        scheduler = MaintenanceScheduler()
        fleet = self._make_fleet()
        plans = scheduler.generate_plan(fleet)

        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        for i in range(len(plans) - 1):
            p_curr = priority_order[plans[i].priority]
            p_next = priority_order[plans[i + 1].priority]
            assert p_curr <= p_next, f"Plans not sorted: {plans[i].priority} before {plans[i+1].priority}"

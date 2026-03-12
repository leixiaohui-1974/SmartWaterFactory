"""Analytics API blueprint — ML prediction, cost optimization, energy analysis, maintenance.

Adds REST endpoints for the new SmartWaterFactory Phase 2 modules.
Register with: ``app.register_blueprint(analytics_bp)``
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

try:
    from flask import Blueprint, jsonify, request
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    # Provide stubs so the module can be imported without Flask
    Blueprint = None  # type: ignore[assignment,misc]

import numpy as np

from water_plant_controller.ml.time_series_forecaster import (
    ARIMAForecaster,
    ExponentialSmoothingForecaster,
    EnsembleForecaster,
)
from water_plant_controller.ml.predictive_model import WaterQualityPredictor
from water_plant_controller.business.cost_optimizer import CostTracker, CostOptimizer
from water_plant_controller.business.energy_analyzer import EnergyAnalyzer, EnergyOptimizer
from water_plant_controller.maintenance.predictive_maintenance import (
    AnomalyDetector,
    EquipmentStatus,
    MaintenancePredictor,
    MaintenanceScheduler,
)

logger = logging.getLogger(__name__)

# Guard: only create blueprint when Flask is available
if FLASK_AVAILABLE:
    analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")
else:
    analytics_bp = None  # type: ignore[assignment]

# ---------- Input validation constants ----------

MAX_TIMESERIES_LENGTH = 10000
MAX_HORIZON = 100
MAX_EQUIPMENT_COUNT = 200
MAX_HISTORY_ROWS = 5000

# ---------- Shared state ----------

_energy_analyzer: EnergyAnalyzer | None = None
_cost_tracker: CostTracker | None = None


def _get_energy_analyzer() -> EnergyAnalyzer:
    global _energy_analyzer
    if _energy_analyzer is None:
        _energy_analyzer = EnergyAnalyzer(water_volume_m3_per_day=5000)
        # Populate with demo data
        for hour in range(24):
            base = 60.0 if 6 <= hour <= 22 else 30.0
            _energy_analyzer.record_hourly(
                hour=hour,
                aeration_kw=base,
                pumping_kw=25.0,
                mixing_kw=8.0,
                disinfection_kw=6.0,
                auxiliary_kw=4.0,
            )
    return _energy_analyzer


def _get_cost_tracker() -> CostTracker:
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
        # Seed with demo entries
        for hour in range(24):
            _cost_tracker.record_hourly(
                hour=hour,
                energy_kwh=80 + 30 * np.sin((hour - 8) * np.pi / 12),
                chemical_kg=2.5 + 0.5 * np.sin((hour - 6) * np.pi / 12),
                water_volume_m3=200 + 50 * np.sin((hour - 10) * np.pi / 12),
            )
    return _cost_tracker


# ---------- ML Prediction ----------


@analytics_bp.route("/predict/timeseries", methods=["POST"])
def predict_timeseries():
    """Run time series forecast.

    Request JSON: {data: number[], horizon: int, method: "arima"|"es"|"ensemble"}
    """
    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    raw_data = body.get("data", [])
    if not isinstance(raw_data, list) or len(raw_data) > MAX_TIMESERIES_LENGTH:
        return jsonify({"error": f"data must be a list with <= {MAX_TIMESERIES_LENGTH} items"}), 400

    try:
        data = np.array(raw_data, dtype=float)
        horizon = int(body.get("horizon", 6))
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid numeric input: {e}"}), 400

    if not 1 <= horizon <= MAX_HORIZON:
        return jsonify({"error": f"horizon must be between 1 and {MAX_HORIZON}"}), 400
    if len(data) < 5:
        return jsonify({"error": "Need at least 5 data points"}), 400

    method = body.get("method", "ensemble")
    if method not in ("arima", "es", "ensemble"):
        return jsonify({"error": "method must be 'arima', 'es', or 'ensemble'"}), 400

    try:
        t0 = time.time()
        if method == "arima":
            forecaster = ARIMAForecaster(p=2, d=1, q=0)
        elif method == "es":
            forecaster = ExponentialSmoothingForecaster(alpha=0.3, beta=0.1)
        else:
            forecaster = EnsembleForecaster()

        result = forecaster.fit_predict(data, horizon)
        elapsed = round((time.time() - t0) * 1000, 1)
    except Exception as e:
        logger.exception("Forecast computation failed")
        return jsonify({"error": f"Forecast failed: {e}"}), 500

    return jsonify({
        "method": result.method,
        "values": [round(v, 4) for v in result.values],
        "lower_bound": [round(v, 4) for v in result.lower_bound] if result.lower_bound is not None else None,
        "upper_bound": [round(v, 4) for v in result.upper_bound] if result.upper_bound is not None else None,
        "confidence": result.confidence,
        "metrics": result.metrics,
        "elapsed_ms": elapsed,
    })


@analytics_bp.route("/predict/water-quality", methods=["POST"])
def predict_water_quality():
    """Run water quality prediction.

    Request JSON: {history: [{turbidity, ph, do}, ...], horizon: int}
    """
    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    history = body.get("history", [])
    if not isinstance(history, list) or len(history) > MAX_HISTORY_ROWS:
        return jsonify({"error": f"history must be a list with <= {MAX_HISTORY_ROWS} items"}), 400

    try:
        horizon = int(body.get("horizon", 6))
    except (ValueError, TypeError):
        return jsonify({"error": "horizon must be an integer"}), 400

    if not 1 <= horizon <= MAX_HORIZON:
        return jsonify({"error": f"horizon must be between 1 and {MAX_HORIZON}"}), 400
    if len(history) < 10:
        return jsonify({"error": "Need at least 10 historical records"}), 400

    try:
        predictor = WaterQualityPredictor()
        turbidity = [float(h["turbidity"]) for h in history]
        ph = [float(h["ph"]) for h in history]
        do_vals = [float(h["do"]) for h in history]

        predictor.fit(turbidity, ph, do_vals)
        pred = predictor.predict(horizon)
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({"error": f"Invalid history data: {e}"}), 400
    except Exception as e:
        logger.exception("Water quality prediction failed")
        return jsonify({"error": f"Prediction failed: {e}"}), 500

    return jsonify({
        "predictions": pred,
        "horizon": horizon,
        "input_length": len(history),
    })


# ---------- Energy Analysis ----------


@analytics_bp.route("/energy/kpis", methods=["GET"])
def energy_kpis():
    """Get energy efficiency KPIs."""
    analyzer = _get_energy_analyzer()
    return jsonify(analyzer.compute_kpis())


@analytics_bp.route("/energy/benchmark", methods=["GET"])
def energy_benchmark():
    """Benchmark energy efficiency against industry standards."""
    analyzer = _get_energy_analyzer()
    benchmarks = analyzer.benchmark()
    return jsonify([{
        "metric": b.metric,
        "value": b.value,
        "unit": b.unit,
        "rating": b.rating,
        "industry_avg": b.industry_avg,
        "industry_best": b.industry_best,
    } for b in benchmarks])


@analytics_bp.route("/energy/peak-valley", methods=["GET"])
def energy_peak_valley():
    """Get peak/flat/valley energy distribution."""
    analyzer = _get_energy_analyzer()
    return jsonify(analyzer.get_peak_valley_distribution())


@analytics_bp.route("/energy/savings", methods=["POST"])
def energy_savings():
    """Analyze potential savings from load shifting.

    Request JSON: {shiftable_fraction: float}
    """
    body = request.get_json(force=True) if request.is_json else {}
    fraction = float(body.get("shiftable_fraction", 0.15))

    analyzer = _get_energy_analyzer()
    optimizer = EnergyOptimizer()
    result = optimizer.analyze_savings(analyzer._hourly_history, shiftable_fraction=fraction)
    return jsonify(result)


@analytics_bp.route("/energy/schedule", methods=["POST"])
def energy_schedule():
    """Recommend optimal schedule for flexible loads.

    Request JSON: {loads: [{name, power_kw, duration_hours, current_hour}, ...]}
    """
    body = request.get_json(force=True)
    loads = body.get("loads", [
        {"name": "反冲洗", "power_kw": 30, "duration_hours": 2, "current_hour": 10},
        {"name": "污泥脱水", "power_kw": 15, "duration_hours": 4, "current_hour": 14},
        {"name": "加药搅拌", "power_kw": 5, "duration_hours": 1, "current_hour": 9},
    ])

    optimizer = EnergyOptimizer()
    recs = optimizer.recommend_schedule(loads)
    return jsonify(recs)


# ---------- Cost Optimization ----------


@analytics_bp.route("/cost/summary", methods=["GET"])
def cost_summary():
    """Get cost tracking summary."""
    tracker = _get_cost_tracker()
    return jsonify(tracker.get_summary())


@analytics_bp.route("/cost/optimize", methods=["POST"])
def cost_optimize():
    """Run cost optimization.

    Request JSON: {water_volume_m3: float, turbidity_target: float}
    """
    body = request.get_json(force=True) if request.is_json else {}
    volume = float(body.get("water_volume_m3", 5000))

    optimizer = CostOptimizer(water_volume_m3=volume)
    result = optimizer.optimize()
    return jsonify(result)


# ---------- Predictive Maintenance ----------


@analytics_bp.route("/maintenance/fleet", methods=["POST"])
def maintenance_fleet():
    """Get fleet maintenance plan.

    Request JSON: {equipment: [{equipment_id, name, operating_hours, ...}, ...]}
    """
    body = request.get_json(force=True) if request.is_json else {}
    equipment_data = body.get("equipment", None)

    if equipment_data is None:
        # Demo fleet
        fleet = [
            EquipmentStatus("PMP-001", "曝气鼓风机A", operating_hours=15000, rated_life_hours=20000,
                            performance_index=0.72, vibration_level=4.5, temperature_delta=12, criticality_tier=1),
            EquipmentStatus("PMP-002", "曝气鼓风机B", operating_hours=8000, rated_life_hours=20000,
                            performance_index=0.92, vibration_level=1.2, temperature_delta=3, criticality_tier=1),
            EquipmentStatus("MIX-001", "搅拌器", operating_hours=12000, rated_life_hours=15000,
                            performance_index=0.85, vibration_level=2.8, temperature_delta=5, criticality_tier=2),
            EquipmentStatus("PMP-003", "回流泵", operating_hours=18000, rated_life_hours=25000,
                            performance_index=0.68, vibration_level=5.2, temperature_delta=18, criticality_tier=1),
            EquipmentStatus("UV-001", "紫外消毒", operating_hours=6000, rated_life_hours=12000,
                            performance_index=0.95, vibration_level=0.5, temperature_delta=2, criticality_tier=2),
            EquipmentStatus("VLV-001", "进水阀", operating_hours=20000, rated_life_hours=30000,
                            performance_index=0.88, vibration_level=1.0, temperature_delta=1, criticality_tier=3),
        ]
    else:
        if not isinstance(equipment_data, list) or len(equipment_data) > MAX_EQUIPMENT_COUNT:
            return jsonify({"error": f"equipment must be a list with <= {MAX_EQUIPMENT_COUNT} items"}), 400
        try:
            fleet = [EquipmentStatus(**eq) for eq in equipment_data]
        except (TypeError, KeyError) as e:
            return jsonify({"error": f"Invalid equipment data: {e}"}), 400

    try:
        scheduler = MaintenanceScheduler()
        summary = scheduler.get_fleet_summary(fleet)
    except Exception as e:
        logger.exception("Maintenance planning failed")
        return jsonify({"error": f"Maintenance planning failed: {e}"}), 500
    return jsonify(summary)


@analytics_bp.route("/maintenance/anomaly", methods=["POST"])
def maintenance_anomaly():
    """Detect anomaly in sensor readings.

    Request JSON: {history: [[v1,v2,...], ...], reading: [v1,v2,...]}
    """
    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    if "history" not in body or "reading" not in body:
        return jsonify({"error": "Both 'history' and 'reading' fields required"}), 400

    try:
        history = np.array(body["history"], dtype=float)
        reading = np.array(body["reading"], dtype=float)
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid numeric data: {e}"}), 400

    if history.size == 0 or history.ndim < 1:
        return jsonify({"error": "history must be a non-empty array"}), 400
    if len(history) > MAX_HISTORY_ROWS:
        return jsonify({"error": f"history must have <= {MAX_HISTORY_ROWS} rows"}), 400

    try:
        detector = AnomalyDetector(method="zscore")
        detector.fit(history)
        result = detector.detect(reading)
    except Exception as e:
        logger.exception("Anomaly detection failed")
        return jsonify({"error": f"Anomaly detection failed: {e}"}), 500

    return jsonify({
        "is_anomaly": result.is_anomaly,
        "score": round(result.score, 4),
        "method": result.method,
        "details": result.details,
    })


# ---------- Dashboard endpoint ----------


@analytics_bp.route("/dashboard", methods=["GET"])
def analytics_dashboard():
    """Get combined analytics dashboard data."""
    try:
        return _build_dashboard_response()
    except Exception as e:
        logger.exception("Dashboard data generation failed")
        return jsonify({"error": f"Dashboard failed: {e}"}), 500


def _build_dashboard_response():
    analyzer = _get_energy_analyzer()
    tracker = _get_cost_tracker()

    # Energy
    energy_kpis = analyzer.compute_kpis()
    benchmarks = analyzer.benchmark()
    peak_valley = analyzer.get_peak_valley_distribution()

    # Cost
    cost_summary = tracker.get_summary()

    # Maintenance (demo fleet)
    fleet = [
        EquipmentStatus("PMP-001", "曝气鼓风机A", operating_hours=15000, performance_index=0.72,
                        vibration_level=4.5, temperature_delta=12, criticality_tier=1),
        EquipmentStatus("PMP-002", "曝气鼓风机B", operating_hours=8000, performance_index=0.92,
                        vibration_level=1.2, temperature_delta=3, criticality_tier=1),
        EquipmentStatus("MIX-001", "搅拌器", operating_hours=12000, rated_life_hours=15000,
                        performance_index=0.85, vibration_level=2.8, temperature_delta=5, criticality_tier=2),
        EquipmentStatus("PMP-003", "回流泵", operating_hours=18000, rated_life_hours=25000,
                        performance_index=0.68, vibration_level=5.2, temperature_delta=18, criticality_tier=1),
    ]
    scheduler = MaintenanceScheduler()
    maint_summary = scheduler.get_fleet_summary(fleet)

    # Energy savings
    optimizer = EnergyOptimizer()
    savings = optimizer.analyze_savings(analyzer._hourly_history)

    return jsonify({
        "energy": {
            "kpis": energy_kpis,
            "benchmarks": [{
                "metric": b.metric, "value": b.value, "unit": b.unit,
                "rating": b.rating, "industry_avg": b.industry_avg,
            } for b in benchmarks],
            "peak_valley": peak_valley,
            "savings": savings,
        },
        "cost": cost_summary,
        "maintenance": maint_summary,
        "timestamp": time.time(),
    })

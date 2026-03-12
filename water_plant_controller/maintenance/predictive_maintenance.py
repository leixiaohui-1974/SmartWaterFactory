"""Predictive maintenance for water treatment plant equipment.

Provides three core capabilities:
1. AnomalyDetector — detect abnormal equipment behavior via statistical methods
2. MaintenancePredictor — estimate remaining useful life (RUL)
3. MaintenanceScheduler — generate optimal maintenance plans

Algorithms:
- Z-score anomaly detection (always available)
- Isolation Forest (optional, requires scikit-learn)
- Exponential degradation RUL model
- Priority-based scheduling with cost optimization
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

logger = logging.getLogger(__name__)

try:
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class EquipmentStatus:
    """Current status of a piece of equipment."""

    equipment_id: str
    name: str
    operating_hours: float = 0.0
    rated_life_hours: float = 20000.0
    performance_index: float = 1.0  # 1.0 = nominal, 0.0 = failed
    vibration_level: float = 0.0  # mm/s RMS
    temperature_delta: float = 0.0  # degrees above normal
    power_factor: float = 1.0  # current/rated power ratio
    criticality_tier: int = 2  # 1=critical, 2=important, 3=auxiliary

    def health_score(self) -> float:
        """Compute composite health score (0-100)."""
        age_factor = max(0.0, 1.0 - self.operating_hours / self.rated_life_hours)
        perf_factor = self.performance_index
        vib_penalty = min(self.vibration_level / 10.0, 1.0)
        temp_penalty = min(self.temperature_delta / 30.0, 1.0)
        score = (0.3 * age_factor + 0.3 * perf_factor + 0.2 * (1 - vib_penalty) + 0.2 * (1 - temp_penalty)) * 100
        return round(max(0.0, min(100.0, score)), 1)


@dataclass
class AnomalyResult:
    """Result of anomaly detection on a single reading."""

    is_anomaly: bool
    score: float  # anomaly score (higher = more anomalous)
    method: str
    details: Dict[str, float] = field(default_factory=dict)


@dataclass
class RULPrediction:
    """Remaining Useful Life prediction."""

    equipment_id: str
    rul_hours: float
    rul_days: float
    confidence: float
    degradation_rate: float  # performance loss per hour
    method: str


@dataclass
class MaintenancePlan:
    """Scheduled maintenance action."""

    equipment_id: str
    equipment_name: str
    priority: str  # "urgent", "high", "medium", "low"
    action: str
    estimated_cost_yuan: float
    recommended_date_hours: float  # hours from now
    health_score: float
    rul_hours: float


# ---------------------------------------------------------------------------
# Anomaly Detection
# ---------------------------------------------------------------------------


class AnomalyDetector:
    """Detect abnormal equipment behavior from sensor readings.

    Uses Z-score method by default; Isolation Forest if sklearn available.

    Parameters
    ----------
    method : str
        ``"auto"`` (prefer isolation_forest), ``"zscore"``, or ``"isolation_forest"``.
    z_threshold : float
        Z-score threshold for anomaly flagging (default 3.0).
    contamination : float
        Expected proportion of anomalies for Isolation Forest (default 0.05).
    """

    def __init__(
        self,
        method: str = "auto",
        z_threshold: float = 3.0,
        contamination: float = 0.05,
    ) -> None:
        if method == "auto":
            self._method = "isolation_forest" if SKLEARN_AVAILABLE else "zscore"
        elif method == "isolation_forest" and not SKLEARN_AVAILABLE:
            logger.warning("sklearn not available, falling back to zscore")
            self._method = "zscore"
        else:
            self._method = method

        self._z_threshold = z_threshold
        self._contamination = contamination
        self._model = None
        self._mean: Optional[np.ndarray] = None
        self._std: Optional[np.ndarray] = None
        self._fitted = False

    def fit(self, data: np.ndarray) -> None:
        """Fit detector on historical normal operating data.

        Parameters
        ----------
        data : ndarray of shape (n_samples, n_features)
            Feature matrix of normal operating readings.
        """
        if data.ndim == 1:
            data = data.reshape(-1, 1)

        self._mean = data.mean(axis=0)
        self._std = data.std(axis=0)
        self._std[self._std == 0] = 1.0

        if self._method == "isolation_forest":
            self._model = IsolationForest(
                contamination=self._contamination,
                random_state=42,
                n_estimators=100,
            )
            self._model.fit(data)

        self._fitted = True

    def detect(self, reading: np.ndarray) -> AnomalyResult:
        """Check if a single reading is anomalous.

        Parameters
        ----------
        reading : ndarray of shape (n_features,)
            Current sensor reading.

        Returns
        -------
        AnomalyResult
        """
        if not self._fitted:
            raise RuntimeError("Must call fit() before detect()")

        if reading.ndim == 1:
            reading = reading.reshape(1, -1)

        if self._method == "isolation_forest" and self._model is not None:
            pred = self._model.predict(reading)
            score_raw = self._model.decision_function(reading)
            is_anomaly = bool(pred[0] == -1)
            score = float(-score_raw[0])  # Higher = more anomalous
            return AnomalyResult(
                is_anomaly=is_anomaly,
                score=score,
                method="isolation_forest",
            )
        else:
            # Z-score method
            z_scores = np.abs((reading[0] - self._mean) / self._std)
            max_z = float(np.max(z_scores))
            is_anomaly = max_z > self._z_threshold
            details = {f"z_score_{i}": float(z) for i, z in enumerate(z_scores)}
            return AnomalyResult(
                is_anomaly=is_anomaly,
                score=max_z,
                method="zscore",
                details=details,
            )

    def detect_batch(self, data: np.ndarray) -> List[AnomalyResult]:
        """Detect anomalies in a batch of readings."""
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        return [self.detect(data[i]) for i in range(data.shape[0])]


# ---------------------------------------------------------------------------
# RUL Prediction
# ---------------------------------------------------------------------------


class MaintenancePredictor:
    """Predict remaining useful life (RUL) of equipment.

    Uses exponential degradation model:
        P(t) = P_0 * exp(-lambda * t)

    Where P is performance index, t is operating hours, lambda is
    the degradation rate estimated from historical data.

    Parameters
    ----------
    failure_threshold : float
        Performance index below which equipment is considered failed.
    """

    def __init__(self, failure_threshold: float = 0.5) -> None:
        self.failure_threshold = failure_threshold

    def estimate_rul(self, status: EquipmentStatus) -> RULPrediction:
        """Estimate RUL from current equipment status.

        Parameters
        ----------
        status : EquipmentStatus
            Current equipment condition.

        Returns
        -------
        RULPrediction
        """
        perf = max(status.performance_index, 0.01)
        hours = max(status.operating_hours, 1.0)

        # Estimate base degradation rate from performance history
        if perf < 1.0:
            # lambda_base = -ln(P/P0) / t
            base_rate = -math.log(perf) / hours
        else:
            # No degradation observed yet — use rated life estimate
            base_rate = -math.log(self.failure_threshold) / status.rated_life_hours

        # Covariates accelerate degradation (proportional hazard approach):
        #   lambda_eff = lambda_base * exp(beta_vib * V + beta_temp * T)
        # where V and T are normalized vibration and temperature exceedance
        beta_vib = 0.15   # vibration acceleration coefficient
        beta_temp = 0.10  # temperature acceleration coefficient
        vib_norm = status.vibration_level / 10.0   # normalize by typical alarm threshold
        temp_norm = status.temperature_delta / 20.0
        acceleration = math.exp(beta_vib * vib_norm + beta_temp * temp_norm)
        degradation_rate = base_rate * acceleration

        # RUL = time until performance hits failure threshold
        # P(t + RUL) = P(t) * exp(-lambda_eff * RUL) = threshold
        # RUL = -ln(threshold / P(t)) / lambda_eff
        if degradation_rate > 0 and perf > self.failure_threshold:
            rul_hours = -math.log(self.failure_threshold / perf) / degradation_rate
        elif perf <= self.failure_threshold:
            rul_hours = 0.0
        else:
            rul_hours = status.rated_life_hours - hours

        rul_hours = max(0.0, rul_hours)
        rul_days = rul_hours / 24.0

        # Confidence based on data quality
        confidence = 0.9 if perf < 0.95 else 0.7  # More data on degradation → higher confidence

        return RULPrediction(
            equipment_id=status.equipment_id,
            rul_hours=round(rul_hours, 1),
            rul_days=round(rul_days, 1),
            confidence=confidence,
            degradation_rate=round(degradation_rate, 8),
            method="exponential_degradation",
        )

    def estimate_fleet(self, fleet: List[EquipmentStatus]) -> List[RULPrediction]:
        """Estimate RUL for a fleet of equipment."""
        return [self.estimate_rul(eq) for eq in fleet]


# ---------------------------------------------------------------------------
# Maintenance Scheduling
# ---------------------------------------------------------------------------


class MaintenanceScheduler:
    """Generate maintenance plans based on equipment health and RUL.

    Parameters
    ----------
    urgent_threshold_hours : float
        RUL below this triggers urgent maintenance.
    high_threshold_hours : float
        RUL below this triggers high priority.
    medium_threshold_hours : float
        RUL below this triggers medium priority.
    """

    def __init__(
        self,
        urgent_threshold_hours: float = 168,    # 1 week
        high_threshold_hours: float = 720,      # 1 month
        medium_threshold_hours: float = 2160,   # 3 months
    ) -> None:
        self.urgent_threshold = urgent_threshold_hours
        self.high_threshold = high_threshold_hours
        self.medium_threshold = medium_threshold_hours
        self._predictor = MaintenancePredictor()

    def _classify_priority(self, rul_hours: float, health_score: float) -> str:
        """Classify maintenance priority."""
        if rul_hours <= 0 or health_score < 20:
            return "urgent"
        elif rul_hours < self.urgent_threshold or health_score < 40:
            return "urgent"
        elif rul_hours < self.high_threshold or health_score < 60:
            return "high"
        elif rul_hours < self.medium_threshold or health_score < 75:
            return "medium"
        return "low"

    def _recommend_action(self, priority: str, status: EquipmentStatus) -> str:
        """Generate maintenance action recommendation."""
        if priority == "urgent":
            if status.performance_index < 0.3:
                return "立即更换设备"
            return "停机检修，检查关键部件"
        elif priority == "high":
            if status.vibration_level > 5.0:
                return "检查轴承和对中，必要时更换"
            if status.temperature_delta > 15.0:
                return "检查冷却系统和润滑"
            return "安排计划性大修"
        elif priority == "medium":
            return "下次停机窗口进行预防性检查"
        return "纳入例行巡检计划"

    def _estimate_cost(self, priority: str, status: EquipmentStatus) -> float:
        """Estimate maintenance cost (元) based on priority and asset criticality."""
        base_costs = {"urgent": 15000, "high": 8000, "medium": 3000, "low": 500}
        base = base_costs.get(priority, 1000)
        # Scale by equipment criticality tier (1=critical 2x, 2=important 1x, 3=aux 0.5x)
        tier_multiplier = {1: 2.0, 2: 1.0, 3: 0.5}
        scale = tier_multiplier.get(status.criticality_tier, 1.0)
        return round(base * scale, 0)

    def generate_plan(self, fleet: List[EquipmentStatus]) -> List[MaintenancePlan]:
        """Generate maintenance plans for a fleet of equipment.

        Parameters
        ----------
        fleet : list of EquipmentStatus
            Current status of all equipment.

        Returns
        -------
        list of MaintenancePlan
            Maintenance plans sorted by priority (urgent first).
        """
        plans = []

        for eq in fleet:
            rul = self._predictor.estimate_rul(eq)
            health = eq.health_score()
            priority = self._classify_priority(rul.rul_hours, health)

            plan = MaintenancePlan(
                equipment_id=eq.equipment_id,
                equipment_name=eq.name,
                priority=priority,
                action=self._recommend_action(priority, eq),
                estimated_cost_yuan=self._estimate_cost(priority, eq),
                recommended_date_hours=max(0.0, rul.rul_hours * 0.8),  # 80% of RUL
                health_score=health,
                rul_hours=rul.rul_hours,
            )
            plans.append(plan)

        # Sort by priority
        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        plans.sort(key=lambda p: (priority_order.get(p.priority, 4), p.rul_hours))

        return plans

    def get_fleet_summary(self, fleet: List[EquipmentStatus]) -> Dict:
        """Generate fleet-level maintenance summary.

        Returns
        -------
        dict
            Fleet health summary with priority counts and total cost estimate.
        """
        plans = self.generate_plan(fleet)

        priority_counts = {"urgent": 0, "high": 0, "medium": 0, "low": 0}
        total_cost = 0.0
        health_scores = []

        for plan in plans:
            priority_counts[plan.priority] += 1
            total_cost += plan.estimated_cost_yuan
            health_scores.append(plan.health_score)

        avg_health = float(np.mean(health_scores)) if health_scores else 0.0

        return {
            "equipment_count": len(fleet),
            "average_health_score": round(avg_health, 1),
            "priority_counts": priority_counts,
            "total_estimated_cost_yuan": round(total_cost, 0),
            "plans": [
                {
                    "equipment_id": p.equipment_id,
                    "name": p.equipment_name,
                    "priority": p.priority,
                    "action": p.action,
                    "cost_yuan": p.estimated_cost_yuan,
                    "health_score": p.health_score,
                    "rul_hours": p.rul_hours,
                }
                for p in plans
            ],
        }

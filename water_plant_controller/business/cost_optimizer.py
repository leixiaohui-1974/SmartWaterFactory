"""Operating cost optimization for water treatment plants.

Tracks and optimizes costs across three categories:
- Electricity (pumping, aeration, mixing)
- Chemicals (coagulant, disinfectant, carbon source)
- Maintenance (equipment wear proportional to operating intensity)

Optimization uses scipy.optimize.minimize with quality constraints.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

logger = logging.getLogger(__name__)

# Try scipy for constrained optimization
try:
    from scipy.optimize import minimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


@dataclass
class EnergyPrice:
    """Time-of-use electricity pricing (元/kWh).

    Attributes
    ----------
    peak : float
        Peak hour rate (e.g., 08:00-12:00, 17:00-21:00).
    flat : float
        Flat rate (e.g., 12:00-17:00, 21:00-23:00).
    valley : float
        Valley (off-peak) rate (e.g., 23:00-08:00).
    """

    peak: float = 1.05
    flat: float = 0.68
    valley: float = 0.35


@dataclass
class ChemicalPrice:
    """Chemical unit prices (元/kg).

    Attributes
    ----------
    coagulant : float
        PAC/PFS coagulant price.
    disinfectant : float
        Chlorine/ClO2 disinfectant price.
    carbon_source : float
        External carbon source (methanol/acetate) price.
    pac : float
        Polyaluminium chloride price.
    """

    coagulant: float = 2.5
    disinfectant: float = 4.0
    carbon_source: float = 3.0
    pac: float = 8.0


@dataclass
class OperatingCost:
    """Snapshot of operating costs for a time period."""

    electricity_yuan: float = 0.0
    chemicals_yuan: float = 0.0
    maintenance_yuan: float = 0.0

    @property
    def total_yuan(self) -> float:
        return self.electricity_yuan + self.chemicals_yuan + self.maintenance_yuan

    def to_dict(self) -> Dict[str, float]:
        return {
            "electricity_yuan": self.electricity_yuan,
            "chemicals_yuan": self.chemicals_yuan,
            "maintenance_yuan": self.maintenance_yuan,
            "total_yuan": self.total_yuan,
        }


@dataclass
class QualityConstraint:
    """Effluent quality constraint.

    Attributes
    ----------
    turbidity_max : float
        Maximum allowable turbidity (NTU).
    do_min : float
        Minimum dissolved oxygen (mg/L).
    ph_min : float
        Minimum pH.
    ph_max : float
        Maximum pH.
    """

    turbidity_max: float = 3.0
    do_min: float = 5.0
    ph_min: float = 6.5
    ph_max: float = 8.5


class CostTracker:
    """Track real-time operating costs over simulation steps.

    Usage
    -----
    >>> tracker = CostTracker(energy_price=EnergyPrice())
    >>> tracker.record_step(hour=10, power_kw=50, chemicals_kg={"coagulant": 0.5})
    >>> tracker.get_summary()
    """

    def __init__(
        self,
        energy_price: Optional[EnergyPrice] = None,
        chemical_price: Optional[ChemicalPrice] = None,
        dt_hours: float = 1.0 / 60,  # default 1 minute steps
    ) -> None:
        self.energy_price = energy_price or EnergyPrice()
        self.chemical_price = chemical_price or ChemicalPrice()
        self.dt_hours = dt_hours
        self._history: List[OperatingCost] = []
        self._cumulative = OperatingCost()

    def _get_rate(self, hour: float) -> float:
        """Get electricity rate based on time-of-use."""
        h = hour % 24
        if (8 <= h < 12) or (17 <= h < 21):
            return self.energy_price.peak
        elif (23 <= h or h < 8):
            return self.energy_price.valley
        else:
            return self.energy_price.flat

    def record_step(
        self,
        hour: float,
        power_kw: float = 0.0,
        chemicals_kg: Optional[Dict[str, float]] = None,
        equipment_intensity: float = 1.0,
    ) -> OperatingCost:
        """Record costs for one simulation step.

        Parameters
        ----------
        hour : float
            Current hour of day (0-24).
        power_kw : float
            Total power consumption (kW).
        chemicals_kg : dict, optional
            Chemical consumption {name: kg_per_step}.
        equipment_intensity : float
            Operating intensity factor for maintenance cost (0-2).

        Returns
        -------
        OperatingCost
            Cost for this step.
        """
        # Electricity cost
        rate = self._get_rate(hour)
        elec_cost = power_kw * self.dt_hours * rate

        # Chemical cost
        chem_cost = 0.0
        if chemicals_kg:
            prices = {
                "coagulant": self.chemical_price.coagulant,
                "disinfectant": self.chemical_price.disinfectant,
                "carbon_source": self.chemical_price.carbon_source,
                "pac": self.chemical_price.pac,
            }
            for name, kg in chemicals_kg.items():
                unit_price = prices.get(name, 0.0)
                chem_cost += kg * unit_price

        # Maintenance cost (simplified: proportional to intensity × base rate)
        base_maintenance_rate = 0.01  # 元/step at intensity=1.0
        maint_cost = equipment_intensity * base_maintenance_rate

        step_cost = OperatingCost(
            electricity_yuan=elec_cost,
            chemicals_yuan=chem_cost,
            maintenance_yuan=maint_cost,
        )
        self._history.append(step_cost)
        self._cumulative.electricity_yuan += elec_cost
        self._cumulative.chemicals_yuan += chem_cost
        self._cumulative.maintenance_yuan += maint_cost

        return step_cost

    def get_summary(self) -> Dict:
        """Return cumulative cost summary."""
        return {
            "total": self._cumulative.to_dict(),
            "steps": len(self._history),
            "avg_per_step": OperatingCost(
                electricity_yuan=self._cumulative.electricity_yuan / max(len(self._history), 1),
                chemicals_yuan=self._cumulative.chemicals_yuan / max(len(self._history), 1),
                maintenance_yuan=self._cumulative.maintenance_yuan / max(len(self._history), 1),
            ).to_dict(),
        }

    def get_history(self) -> List[Dict[str, float]]:
        """Return per-step cost history."""
        return [c.to_dict() for c in self._history]


class CostOptimizer:
    """Multi-objective optimizer: minimize cost while meeting quality constraints.

    Uses scipy constrained optimization to find optimal operating parameters:
    - Aeration power (DO control)
    - Chemical dosing rates
    - Pump scheduling

    Parameters
    ----------
    quality_constraint : QualityConstraint
        Effluent quality requirements.
    energy_price : EnergyPrice
        Time-of-use pricing.
    chemical_price : ChemicalPrice
        Chemical unit prices.
    """

    def __init__(
        self,
        quality_constraint: Optional[QualityConstraint] = None,
        energy_price: Optional[EnergyPrice] = None,
        chemical_price: Optional[ChemicalPrice] = None,
    ) -> None:
        self.qc = quality_constraint or QualityConstraint()
        self.energy_price = energy_price or EnergyPrice()
        self.chemical_price = chemical_price or ChemicalPrice()

    @staticmethod
    def _process_model(
        aeration_power: float,
        coagulant_dose: float,
        carbon_dose: float,
        influent_turbidity: float = 30.0,
        influent_do: float = 2.0,
    ) -> Dict[str, float]:
        """Simplified process model: map inputs → effluent quality.

        This is a reduced-order model suitable for optimization.
        Real applications should use the full PlantSimulator.
        """
        # Turbidity removal: Michaelis-Menten-like (multi-stage)
        removal_eff = coagulant_dose / (coagulant_dose + 0.3)
        effluent_turbidity = influent_turbidity * (1 - removal_eff * 0.98)

        # DO: aeration power increases DO
        kla = 0.8 * (aeration_power / 10.0) ** 0.6  # Transfer coefficient
        do_saturation = 9.2  # mg/L at 20°C
        effluent_do = influent_do + kla * (do_saturation - influent_do)
        effluent_do = min(effluent_do, do_saturation)

        # pH affected slightly by chemicals
        effluent_ph = 7.0 + 0.1 * coagulant_dose - 0.05 * carbon_dose
        effluent_ph = max(5.0, min(9.0, effluent_ph))

        return {
            "turbidity": effluent_turbidity,
            "dissolved_oxygen": effluent_do,
            "ph": effluent_ph,
        }

    def optimize(
        self,
        hour: float,
        influent_turbidity: float = 30.0,
        influent_do: float = 2.0,
    ) -> Dict:
        """Find cost-optimal operating parameters.

        Parameters
        ----------
        hour : float
            Current hour of day (for energy pricing).
        influent_turbidity : float
            Incoming water turbidity (NTU).
        influent_do : float
            Incoming dissolved oxygen (mg/L).

        Returns
        -------
        dict
            Optimal parameters, predicted quality, and estimated cost.
        """
        # Decision variables: [aeration_power_kw, coagulant_kg, carbon_kg]
        # Bounds
        bounds = [
            (1.0, 50.0),   # aeration power kW
            (0.1, 5.0),    # coagulant dose kg/h
            (0.0, 3.0),    # carbon source dose kg/h
        ]

        # Energy rate for this hour
        h = hour % 24
        if (8 <= h < 12) or (17 <= h < 21):
            rate = self.energy_price.peak
        elif (23 <= h or h < 8):
            rate = self.energy_price.valley
        else:
            rate = self.energy_price.flat

        def cost_fn(x):
            aeration, coag, carbon = x
            elec = aeration * rate  # kWh * rate
            chem = coag * self.chemical_price.coagulant + carbon * self.chemical_price.carbon_source
            return elec + chem

        def turbidity_constraint(x):
            q = self._process_model(x[0], x[1], x[2], influent_turbidity, influent_do)
            return self.qc.turbidity_max - q["turbidity"]

        def do_constraint(x):
            q = self._process_model(x[0], x[1], x[2], influent_turbidity, influent_do)
            return q["dissolved_oxygen"] - self.qc.do_min

        def ph_lower_constraint(x):
            q = self._process_model(x[0], x[1], x[2], influent_turbidity, influent_do)
            return q["ph"] - self.qc.ph_min

        def ph_upper_constraint(x):
            q = self._process_model(x[0], x[1], x[2], influent_turbidity, influent_do)
            return self.qc.ph_max - q["ph"]

        constraints = [
            {"type": "ineq", "fun": turbidity_constraint},
            {"type": "ineq", "fun": do_constraint},
            {"type": "ineq", "fun": ph_lower_constraint},
            {"type": "ineq", "fun": ph_upper_constraint},
        ]

        x0 = [15.0, 1.5, 0.5]

        if SCIPY_AVAILABLE:
            result = minimize(
                cost_fn,
                x0,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"maxiter": 200, "ftol": 1e-8},
            )
            optimal = result.x
            success = result.success
            cost = float(result.fun)
        else:
            # Fallback: grid search
            best_cost = float("inf")
            optimal = x0
            success = True
            for aer in np.linspace(bounds[0][0], bounds[0][1], 10):
                for coag in np.linspace(bounds[1][0], bounds[1][1], 10):
                    for carb in np.linspace(bounds[2][0], bounds[2][1], 5):
                        x = [aer, coag, carb]
                        q = self._process_model(x[0], x[1], x[2], influent_turbidity, influent_do)
                        # Check constraints
                        if (
                            q["turbidity"] <= self.qc.turbidity_max
                            and q["dissolved_oxygen"] >= self.qc.do_min
                            and self.qc.ph_min <= q["ph"] <= self.qc.ph_max
                        ):
                            c = cost_fn(x)
                            if c < best_cost:
                                best_cost = c
                                optimal = x
            cost = cost_fn(optimal)

        quality = self._process_model(optimal[0], optimal[1], optimal[2], influent_turbidity, influent_do)

        # Also compute baseline cost (using initial guess)
        baseline_cost = cost_fn(x0)
        savings_pct = (1 - cost / baseline_cost) * 100 if baseline_cost > 0 else 0.0

        return {
            "success": success,
            "optimal_params": {
                "aeration_power_kw": round(float(optimal[0]), 2),
                "coagulant_dose_kg_h": round(float(optimal[1]), 3),
                "carbon_dose_kg_h": round(float(optimal[2]), 3),
            },
            "predicted_quality": {k: round(v, 3) for k, v in quality.items()},
            "cost_yuan_per_hour": round(cost, 2),
            "baseline_cost_yuan_per_hour": round(baseline_cost, 2),
            "savings_percent": round(savings_pct, 1),
            "energy_rate": round(rate, 2),
            "constraints_met": (
                quality["turbidity"] <= self.qc.turbidity_max
                and quality["dissolved_oxygen"] >= self.qc.do_min
                and self.qc.ph_min <= quality["ph"] <= self.qc.ph_max
            ),
        }

    def optimize_schedule(
        self,
        hours: Sequence[float],
        influent_turbidity: float = 30.0,
        influent_do: float = 2.0,
    ) -> Dict:
        """Optimize operating parameters across multiple hours.

        Returns per-hour optimal settings and aggregate cost savings.
        """
        schedule = []
        total_cost = 0.0
        total_baseline = 0.0

        for hour in hours:
            result = self.optimize(hour, influent_turbidity, influent_do)
            schedule.append({
                "hour": hour,
                **result["optimal_params"],
                "cost_yuan": result["cost_yuan_per_hour"],
                "quality": result["predicted_quality"],
            })
            total_cost += result["cost_yuan_per_hour"]
            total_baseline += result["baseline_cost_yuan_per_hour"]

        return {
            "schedule": schedule,
            "total_cost_yuan": round(total_cost, 2),
            "total_baseline_yuan": round(total_baseline, 2),
            "total_savings_percent": round(
                (1 - total_cost / total_baseline) * 100 if total_baseline > 0 else 0.0, 1
            ),
        }

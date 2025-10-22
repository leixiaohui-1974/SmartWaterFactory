from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class EnergyCoordinator:
    """
    Coordinates multiple actuators to respect a combined energy/cost budget.

    Actuators can be assigned weighting factors to prioritise one output over
    another when scaling is required.
    """

    budget_per_step: float
    weights: Dict[str, float]

    def coordinate(
        self,
        actuators: List[Tuple[str, object, float, dict]],
    ) -> Dict[str, float]:
        """
        Apply coordination and return a mapping of actuator name -> scaling factor.

        Args:
            actuators: List of (name, controller, output, diagnostics) tuples.
        """

        total_cost = sum(diag.get("instantaneous_cost", 0.0) for _, _, _, diag in actuators)
        if self.budget_per_step <= 0 or total_cost <= self.budget_per_step or total_cost == 0:
            return {name: 1.0 for name, _, _, _ in actuators}

        scaling: Dict[str, float] = {}
        for name, controller, output, diag in actuators:
            weight = self.weights.get(name, 1.0)
            factor = max(0.0, min(1.0, (self.budget_per_step / total_cost) ** weight))
            scaling[name] = factor
            if hasattr(controller, "apply_output_override"):
                controller.apply_output_override(output * factor)
            diag["energy_scaling_factor"] = factor
        return scaling

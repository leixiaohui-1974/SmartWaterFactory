"""A/A/O (Anaerobic-Anoxic-Aerobic) process simulator.

厌氧-缺氧-好氧工艺仿真器，基于 Monod 动力学简化模型。
支持：COD降解、硝化、反硝化、除磷过程。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Any, List

from water_plant_controller.wastewater.wastewater_quality import WastewaterQuality


@dataclass
class AAOParams:
    """A/A/O reactor parameters."""

    # Reactor volumes (m³)
    V_anaerobic: float = 50.0
    V_anoxic: float = 80.0
    V_aerobic: float = 120.0

    # Flow (m³/h)
    Q_in: float = 10.0

    # Monod kinetics — COD degradation
    mu_max_cod: float = 0.3       # max specific growth rate (1/h)
    K_cod: float = 20.0           # half-saturation COD (mg/L)
    Y_cod: float = 0.6            # yield coefficient

    # Nitrification (aerobic)
    mu_max_nit: float = 0.08      # max nitrification rate (1/h)
    K_nh3: float = 1.0            # half-saturation NH3-N (mg/L)
    K_do_nit: float = 0.5         # DO half-saturation for nitrification (mg/L)

    # Denitrification (anoxic)
    mu_max_denit: float = 0.12    # max denitrification rate (1/h)
    K_no3: float = 0.5            # half-saturation NO3 (mg/L)

    # Phosphorus
    P_release_rate: float = 0.02  # anaerobic P release (mg/L/h per mg MLSS)
    P_uptake_rate: float = 0.05   # aerobic P uptake (mg/L/h per mg MLSS)

    # Biomass
    MLSS: float = 3000.0          # Mixed Liquor Suspended Solids (mg/L)

    # Sludge return ratio
    R_sludge: float = 0.5
    # Internal recycle ratio
    R_internal: float = 2.0


class AAOSimulator:
    """Simplified A/A/O process simulator using Euler integration.

    Models the three-zone treatment process:
    1. Anaerobic zone: P release, fermentation
    2. Anoxic zone: Denitrification, COD removal
    3. Aerobic zone: Nitrification, COD oxidation, P uptake
    """

    def __init__(self, params: AAOParams | None = None):
        self.params = params or AAOParams()

    def simulate(
        self,
        influent: WastewaterQuality,
        DO_aerobic: float = 2.0,
        dt: float = 0.1,
        duration: float = 24.0,
    ) -> Dict[str, Any]:
        """Run A/A/O simulation.

        Args:
            influent: Inlet water quality.
            DO_aerobic: Dissolved oxygen setpoint in aerobic zone (mg/L).
            dt: Time step (hours).
            duration: Simulation duration (hours).

        Returns:
            Dict with effluent quality, time series, and removal rates.
        """
        p = self.params
        n_steps = int(duration / dt)
        Q = p.Q_in

        # State variables: COD, NH3-N, NO3-N, TP, DO per zone
        # Initialize with influent
        anaerobic = {
            "COD": influent.COD, "NH3_N": influent.NH3_N,
            "NO3_N": 0.0, "TP": influent.TP, "DO": 0.1,
        }
        anoxic = dict(anaerobic)
        aerobic = dict(anaerobic)
        aerobic["DO"] = DO_aerobic

        history: List[Dict[str, float]] = []

        for step in range(n_steps):
            t = step * dt

            # --- Anaerobic zone ---
            # COD fermentation (slow)
            r_cod_an = p.mu_max_cod * 0.3 * anaerobic["COD"] / (p.K_cod + anaerobic["COD"]) * p.MLSS / 1000
            # P release
            r_p_release = p.P_release_rate * p.MLSS / 1000

            anaerobic["COD"] += (-r_cod_an + Q / p.V_anaerobic * (influent.COD - anaerobic["COD"])) * dt
            anaerobic["TP"] += (r_p_release + Q / p.V_anaerobic * (influent.TP - anaerobic["TP"])) * dt
            anaerobic["NH3_N"] += Q / p.V_anaerobic * (influent.NH3_N - anaerobic["NH3_N"]) * dt
            anaerobic["COD"] = max(0.0, anaerobic["COD"])

            # --- Anoxic zone ---
            # Denitrification
            monod_no3 = anoxic["NO3_N"] / (p.K_no3 + anoxic["NO3_N"]) if anoxic["NO3_N"] > 0 else 0
            r_denit = p.mu_max_denit * monod_no3 * p.MLSS / 1000
            # COD consumption by denitrification
            r_cod_anox = p.mu_max_cod * 0.5 * anoxic["COD"] / (p.K_cod + anoxic["COD"]) * p.MLSS / 1000

            Q_anox_in = Q + Q * p.R_internal  # internal recycle from aerobic
            anoxic["COD"] += (-r_cod_anox + Q / p.V_anoxic * (anaerobic["COD"] - anoxic["COD"])) * dt
            anoxic["NO3_N"] += (-r_denit * 2.86 + Q * p.R_internal / p.V_anoxic * (aerobic.get("NO3_N", 0) - anoxic["NO3_N"])) * dt
            anoxic["NH3_N"] += Q / p.V_anoxic * (anaerobic["NH3_N"] - anoxic["NH3_N"]) * dt
            anoxic["TP"] += Q / p.V_anoxic * (anaerobic["TP"] - anoxic["TP"]) * dt
            anoxic["COD"] = max(0.0, anoxic["COD"])
            anoxic["NO3_N"] = max(0.0, anoxic["NO3_N"])

            # --- Aerobic zone ---
            aerobic["DO"] = DO_aerobic  # controlled by aeration
            monod_do = aerobic["DO"] / (p.K_do_nit + aerobic["DO"])

            # Nitrification: NH3-N → NO3-N
            monod_nh3 = aerobic["NH3_N"] / (p.K_nh3 + aerobic["NH3_N"]) if aerobic["NH3_N"] > 0 else 0
            r_nit = p.mu_max_nit * monod_nh3 * monod_do * p.MLSS / 1000

            # COD oxidation
            r_cod_aer = p.mu_max_cod * aerobic["COD"] / (p.K_cod + aerobic["COD"]) * monod_do * p.MLSS / 1000

            # P uptake
            r_p_uptake = p.P_uptake_rate * monod_do * p.MLSS / 1000

            aerobic["COD"] += (-r_cod_aer + Q / p.V_aerobic * (anoxic["COD"] - aerobic["COD"])) * dt
            aerobic["NH3_N"] += (-r_nit + Q / p.V_aerobic * (anoxic["NH3_N"] - aerobic["NH3_N"])) * dt
            aerobic["NO3_N"] += (r_nit * 0.8 + Q / p.V_aerobic * (anoxic["NO3_N"] - aerobic["NO3_N"])) * dt
            aerobic["TP"] += (-r_p_uptake + Q / p.V_aerobic * (anoxic["TP"] - aerobic["TP"])) * dt

            aerobic["COD"] = max(0.0, aerobic["COD"])
            aerobic["NH3_N"] = max(0.0, aerobic["NH3_N"])
            aerobic["NO3_N"] = max(0.0, aerobic["NO3_N"])
            aerobic["TP"] = max(0.0, aerobic["TP"])

            if step % max(1, n_steps // 100) == 0:
                history.append({"t": round(t, 2), **{f"eff_{k}": round(v, 3) for k, v in aerobic.items()}})

        # Build effluent
        effluent = WastewaterQuality(
            COD=max(0.0, aerobic["COD"]),
            NH3_N=max(0.0, aerobic["NH3_N"]),
            TN=max(0.0, aerobic["NH3_N"] + aerobic["NO3_N"]),
            TP=max(0.0, aerobic["TP"]),
            SS=max(0.0, influent.SS * 0.05),  # ~95% SS removal by settling
            DO=DO_aerobic,
            pH=influent.pH,
        )

        removal = effluent.removal_rate(influent)
        compliance = effluent.check_compliance()

        return {
            "success": True,
            "method": "AAO_Monod",
            "influent": influent.to_dict(),
            "effluent": effluent.to_dict(),
            "removal_rates": removal,
            "compliance": compliance,
            "duration_h": duration,
            "n_steps": n_steps,
            "history": history,
        }

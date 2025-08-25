from datetime import datetime, timedelta
from water_plant_controller.models.water_quality import WaterQuality
from config.settings import SIMULATION_DEFAULTS

class PlantSimulator:
    """
    Simulates the water treatment process in a simplified manner.
    """

    def __init__(self, initial_quality: WaterQuality, config: dict = None):
        """
        Initializes the simulator with a starting water quality.
        :param initial_quality: The initial WaterQuality state.
        :param config: A dictionary with simulation parameters to override defaults.
        """
        self.current_quality = initial_quality
        self.simulation_time = initial_quality.timestamp

        # Load default settings and override with any provided config
        self.config = SIMULATION_DEFAULTS.copy()
        if config:
            self.config.update(config)

        self._do_saturation = self.config["do_saturation"]
        self._do_consumption_rate = self.config["do_consumption_rate"]
        self._turbidity_decay_factor = self.config["turbidity_decay_factor"]
        self._do_increase_rate = self.config["do_increase_rate"]

    def step(self, coagulant_dose: float, aeration_rate: float) -> WaterQuality:
        """
        Advances the simulation by one time step (e.g., 1 minute).

        :param coagulant_dose: The amount of coagulant added (e.g., in mg/L).
        :param aeration_rate: The rate of aeration (e.g., in m^3/hr).
        :return: The new WaterQuality state after the step.
        """
        # --- Update simulation time ---
        self.simulation_time += timedelta(minutes=1)

        # --- Simulate Turbidity change ---
        # Model: Coagulant causes turbidity to decrease.
        turbidity_reduction = self._turbidity_decay_factor * coagulant_dose * self.current_quality.turbidity
        new_turbidity = self.current_quality.turbidity - turbidity_reduction

        # --- Simulate Dissolved Oxygen (DO) change ---
        # Model: Aeration increases DO towards saturation, while natural processes consume it.
        current_do = self.current_quality.dissolved_oxygen

        # Effect of aeration
        do_increase = self._do_increase_rate * aeration_rate * (self._do_saturation - current_do)

        # Effect of natural consumption
        do_decrease = self._do_consumption_rate * current_do

        new_do = current_do + do_increase - do_decrease

        # --- Update state ---
        # (pH and temperature are assumed constant for this simple model)
        self.current_quality = WaterQuality(
            timestamp=self.simulation_time,
            ph=self.current_quality.ph,
            turbidity=max(0, new_turbidity),  # Ensure turbidity is not negative
            dissolved_oxygen=max(0, min(self._do_saturation, new_do)) # Ensure DO is within bounds
        )

        return self.current_quality

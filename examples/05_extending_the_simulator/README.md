# Example 5: Extending the Simulator

This guide provides a step-by-step tutorial on how to extend the `PlantSimulator` with new physical parameters and behaviors. This is the most advanced example and is intended for users who want to customize the simulation for their own specific needs.

## The Goal

Our goal is to modify the simulator to include the effect of **water temperature**. We will make the "natural dissolved oxygen consumption" dependent on temperature, based on the idea that biological activity increases in warmer water.

We will walk through the four key files that need to be changed:
1.  `water_plant_controller/models/water_quality.py` (the data model)
2.  `config/settings.py` (the configuration)
3.  `config/validator.py` (the configuration validator)
4.  `water_plant_controller/simulation/plant_simulator.py` (the simulator itself)

---

## Step 1: Update the `WaterQuality` Model

First, we need to add `temperature` to our data model.

-   **File to edit**: `water_plant_controller/models/water_quality.py`

Add a new attribute `temperature` to the `WaterQuality` dataclass.

**Before:**
```python
@dataclass
class WaterQuality:
    timestamp: datetime
    ph: float
    turbidity: float
    dissolved_oxygen: float
```

**After:**
```python
@dataclass
class WaterQuality:
    timestamp: datetime
    ph: float
    turbidity: float
    dissolved_oxygen: float
    temperature: float = 15.0 # Default to 15°C
```
We give it a default value for convenience.

---

## Step 2: Update the Configuration

Next, we need a new parameter in our settings file to define the relationship between temperature and oxygen consumption. We'll add a `temp_factor` that determines how much the consumption rate changes for each degree above a base temperature.

-   **File to edit**: `config/settings.py`

Add a new key, `do_consumption_temp_factor`, to the `SIMULATION_DEFAULTS` dictionary.

```python
SIMULATION_DEFAULTS = {
    # ... existing parameters
    "aeration_non_linearity": 1.5,
    "base_temp_for_consumption": 15.0, # The temperature at which the base rate applies
    "do_consumption_temp_factor": 0.001, # How much consumption increases per degree
}
```

---

## Step 3: Update the Configuration Validator

Since we added new configuration parameters, we must update our validator to check for them. This ensures the simulation won't run with an incomplete configuration.

-   **File to edit**: `config/validator.py`

Add the new keys to the `required_sim_keys` dictionary.

```python
required_sim_keys = {
    # ... existing keys
    "aeration_non_linearity": (int, float),
    "base_temp_for_consumption": (int, float),
    "do_consumption_temp_factor": (int, float),
}
```

---

## Step 4: Update the `PlantSimulator`

This is the final and most important step, where we implement the new logic.

-   **File to edit**: `water_plant_controller/simulation/plant_simulator.py`

**4.1: Load the new parameters in `__init__`**
First, load the new configuration values in the `__init__` method.

```python
class PlantSimulator:
    def __init__(self, ...):
        # ... existing code
        self._aeration_non_linearity = self.config["aeration_non_linearity"]
        self._base_temp = self.config["base_temp_for_consumption"]
        self._temp_factor = self.config["do_consumption_temp_factor"]
        # ... existing code
```

**4.2: Update the simulation logic in `step`**
Now, modify the calculation for `do_decrease` in the `step` method to include the effect of temperature.

**Before:**
```python
# Effect of natural consumption
do_decrease = self._do_consumption_rate * current_do
```

**After:**
```python
# Effect of natural consumption (now temperature-dependent)
temp_difference = self.current_quality.temperature - self._base_temp
dynamic_consumption_rate = self._do_consumption_rate + (temp_difference * self._temp_factor)
do_decrease = dynamic_consumption_rate * current_do
```

**4.3: Update the `WaterQuality` object creation**
Finally, make sure to pass the new temperature through when creating the new `WaterQuality` state object at the end of the `step` method.

**Before:**
```python
self.current_quality = WaterQuality(
    timestamp=self.simulation_time,
    ph=self.current_quality.ph,
    # ...
)
```

**After:**
```python
self.current_quality = WaterQuality(
    timestamp=self.simulation_time,
    ph=self.current_quality.ph,
    temperature=self.current_quality.temperature, # Pass the temperature through
    # ...
)
```
*(For a more advanced simulation, you could also make the temperature change over time!)*

---

## Conclusion

That's it! By following these four steps, you have successfully extended the simulator with a new physical behavior. You would also need to update any tests that are affected by this change, but the core modification is complete. This structured approach—Model, Config, Validator, Simulator—makes the project easy and safe to extend.

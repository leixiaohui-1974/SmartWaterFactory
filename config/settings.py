# --- Simulation Parameters ---

# These parameters define the behavior of the water treatment plant simulator.
# They are intended to be constants but can be tuned for different scenarios.

SIMULATION_DEFAULTS = {
    "do_saturation": 9.0,           # Saturation concentration for dissolved oxygen (mg/L)
    "do_consumption_rate": 0.02,    # Natural rate of DO consumption by biomass
    "turbidity_decay_factor": 0.05, # How effectively coagulant reduces turbidity
    "do_increase_rate": 0.05,       # How effectively aeration increases DO
}


# --- PID Controller Gains ---

# These are the default tuning parameters (gains) for the PID controllers.
# They provide a stable starting point but may need to be adjusted for
# optimal performance depending on the operational conditions.

PID_GAINS = {
    "dosing_controller": {
        "Kp": 0.12,
        "Ki": 0.001,
        "Kd": 0.5,
    },
    "aeration_controller": {
        "Kp": 1.2,
        "Ki": 0.22,
        "Kd": 0.1,
    },
}

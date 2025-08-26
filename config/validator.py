def validate_config(sim_config: dict, pid_gains: dict):
    """
    Validates the simulation and PID gains configuration dictionaries.
    Raises ValueError if the configuration is invalid.

    :param sim_config: The simulation configuration dictionary.
    :param pid_gains: The PID gains configuration dictionary.
    """
    # --- Validate Simulation Config ---
    required_sim_keys = {
        "do_saturation": (int, float),
        "do_consumption_rate": (int, float),
        "turbidity_decay_factor": (int, float),
        "do_increase_rate": (int, float),
        "time_delay_steps": int,
        "aeration_non_linearity": (int, float),
    }

    for key, expected_type in required_sim_keys.items():
        if key not in sim_config:
            raise ValueError(f"Missing required simulation parameter in config: '{key}'")
        if not isinstance(sim_config[key], expected_type):
            raise ValueError(f"Simulation parameter '{key}' has incorrect type. "
                             f"Expected {expected_type}, got {type(sim_config[key])}.")

    # --- Validate PID Gains Config ---
    if "dosing_controller" not in pid_gains:
        raise ValueError("Missing 'dosing_controller' gains in PID_GAINS config.")
    if "aeration_controller" not in pid_gains:
        raise ValueError("Missing 'aeration_controller' gains in PID_GAINS config.")

    required_pid_keys = {
        "Kp": (int, float),
        "Ki": (int, float),
        "Kd": (int, float),
    }

    for controller_name, gains in pid_gains.items():
        for key, expected_type in required_pid_keys.items():
            if key not in gains:
                raise ValueError(f"Missing required PID gain '{key}' for '{controller_name}' in config.")
            if not isinstance(gains[key], expected_type):
                raise ValueError(f"PID gain '{key}' for '{controller_name}' has incorrect type. "
                                 f"Expected {expected_type}, got {type(gains[key])}.")

    print("Configuration validated successfully.")

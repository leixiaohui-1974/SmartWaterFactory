import csv
import os
import tempfile
import unittest

from run_simulation import run_and_log_simulation


class TestRunSimulationPrecisionPID(unittest.TestCase):
    def _run_and_validate(self, controller_type: str):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "precision_log.csv")

            success = run_and_log_simulation(
                steps=20,
                log_file=log_path,
                turbidity_setpoint=5.0,
                do_setpoint=8.5,
                controller_type=controller_type,
            )

            self.assertTrue(success)
            self.assertTrue(os.path.exists(log_path))

            with open(log_path, "r", encoding="utf-8", newline="") as csvfile:
                reader = csv.DictReader(csvfile)
                fieldnames = reader.fieldnames or []

                expected_columns = {
                    "coagulant_saturated",
                    "aeration_saturated",
                    "coagulant_cost",
                    "aeration_cost",
                    "turbidity_disturbance",
                    "filtered_turbidity",
                    "sensor_bias_estimate",
                    "sensor_bias_threshold",
                    "sensor_fault_likelihood",
                    "turbidity_reliability",
                    "turbidity_soft_measurement",
                    "turbidity_measurement_used",
                    "primary_sensor_fault",
                    "secondary_sensor_fault",
                    "redundant_sensor_active",
                    "energy_scaling_factor",
                    "energy_budget",
                    "coagulant_energy_scale",
                    "aeration_energy_scale",
                    "fault_fallback_active",
                }

                self.assertTrue(
                    expected_columns.issubset(set(fieldnames)),
                    "Precision controller diagnostics missing from CSV header",
                )

                row = next(reader, None)
                self.assertIsNotNone(row, "CSV log should contain at least one row")

                # Numeric conversion should not raise
                float(row["coagulant_cost"])
                float(row["aeration_cost"])
                int(row["coagulant_saturated"])
                int(row["aeration_saturated"])
                float(row["energy_scaling_factor"])
                float(row["energy_budget"])
                float(row["coagulant_energy_scale"])
                float(row["aeration_energy_scale"])
                float(row["filtered_turbidity"])
                float(row["sensor_bias_estimate"])
                float(row["sensor_bias_threshold"])
                float(row["sensor_fault_likelihood"])

    def test_precision_pid_generates_extended_columns(self):
        self._run_and_validate("precision-pid")

    def test_adaptive_pid_generates_extended_columns(self):
        self._run_and_validate("adaptive-pid")

    def test_mpc_generates_extended_columns(self):
        self._run_and_validate("mpc")

    def test_energy_coordination_scales_output_when_budget_low(self):
        from config.settings import ENERGY_COORDINATION

        original_enabled = ENERGY_COORDINATION.get("enabled", False)
        original_budget = ENERGY_COORDINATION.get("budget_per_step", 0.0)
        ENERGY_COORDINATION["enabled"] = True
        ENERGY_COORDINATION["budget_per_step"] = 0.01

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                log_path = os.path.join(tmpdir, "low_budget.csv")
                success = run_and_log_simulation(
                    steps=30,
                    log_file=log_path,
                    turbidity_setpoint=5.0,
                    do_setpoint=8.5,
                    controller_type="precision-pid",
                )
                self.assertTrue(success)

                with open(log_path, "r", encoding="utf-8", newline="") as csvfile:
                    reader = csv.DictReader(csvfile)
                    scales = [float(row["energy_scaling_factor"]) for row in reader]
                    self.assertTrue(any(scale < 0.99 for scale in scales))
        finally:
            ENERGY_COORDINATION["enabled"] = original_enabled
            ENERGY_COORDINATION["budget_per_step"] = original_budget

    def test_fault_fallback_engages_with_sensor_provider(self):
        from config.settings import FAULT_TOLERANCE

        original_enabled = FAULT_TOLERANCE.get("enabled", False)
        original_threshold = FAULT_TOLERANCE.get("consecutive_fault_threshold", 3)
        FAULT_TOLERANCE["enabled"] = True
        FAULT_TOLERANCE["consecutive_fault_threshold"] = 1

        def faulty_sensor(**kwargs):
            return {"turbidity": 10.0, "dissolved_oxygen": 0.0}

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                log_path = os.path.join(tmpdir, "fault_demo.csv")
                success = run_and_log_simulation(
                    steps=10,
                    log_file=log_path,
                    turbidity_setpoint=5.0,
                    do_setpoint=8.5,
                    controller_type="precision-pid",
                    sensor_provider=faulty_sensor,
                )
                self.assertTrue(success)

                with open(log_path, "r", encoding="utf-8", newline="") as csvfile:
                    reader = csv.DictReader(csvfile)
                    fallback_flags = [int(row["fault_fallback_active"]) for row in reader]
                    self.assertTrue(any(flag == 1 for flag in fallback_flags))
        finally:
            FAULT_TOLERANCE["enabled"] = original_enabled
            FAULT_TOLERANCE["consecutive_fault_threshold"] = original_threshold

    def test_redundant_sensor_prevents_fallback(self):
        from config.settings import FAULT_TOLERANCE

        original_enabled = FAULT_TOLERANCE.get("enabled", False)
        original_threshold = FAULT_TOLERANCE.get("consecutive_fault_threshold", 3)
        FAULT_TOLERANCE["enabled"] = True
        FAULT_TOLERANCE["consecutive_fault_threshold"] = 1

        def primary_sensor_fault(**kwargs):
            return {"turbidity": 6.0}

        def redundant_sensor(**kwargs):
            return {"turbidity": 0.0, "dissolved_oxygen": 0.0}

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                log_path = os.path.join(tmpdir, "redundancy_demo.csv")
                success = run_and_log_simulation(
                    steps=15,
                    log_file=log_path,
                    turbidity_setpoint=5.0,
                    do_setpoint=8.5,
                    controller_type="precision-pid",
                    sensor_provider=primary_sensor_fault,
                    redundant_sensor_provider=redundant_sensor,
                )
                self.assertTrue(success)

                with open(log_path, "r", encoding="utf-8", newline="") as csvfile:
                    reader = csv.DictReader(csvfile)
                    rows = list(reader)
                    redundant_flags = [float(row["redundant_sensor_active"]) for row in rows]
                    fallback_flags = [int(row["fault_fallback_active"]) for row in rows]
                    self.assertTrue(any(flag >= 0.5 for flag in redundant_flags))
                    self.assertTrue(all(flag == 0 for flag in fallback_flags))
        finally:
            FAULT_TOLERANCE["enabled"] = original_enabled
            FAULT_TOLERANCE["consecutive_fault_threshold"] = original_threshold


if __name__ == "__main__":
    unittest.main()

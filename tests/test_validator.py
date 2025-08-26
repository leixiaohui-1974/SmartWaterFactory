import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.validator import validate_config

class TestConfigValidator(unittest.TestCase):
    """Unit tests for the configuration validator."""

    def setUp(self):
        """Set up a default valid configuration for each test."""
        self.valid_sim_config = {
            "do_saturation": 9.0,
            "do_consumption_rate": 0.02,
            "turbidity_decay_factor": 0.05,
            "do_increase_rate": 0.05,
            "time_delay_steps": 5,
            "aeration_non_linearity": 1.5,
        }
        self.valid_pid_gains = {
            "dosing_controller": {"Kp": 0.1, "Ki": 0.01, "Kd": 0.1},
            "aeration_controller": {"Kp": 0.8, "Ki": 0.1, "Kd": 0.1},
        }

    def test_valid_config(self):
        """Test that a valid configuration passes without error."""
        try:
            validate_config(self.valid_sim_config, self.valid_pid_gains)
        except ValueError:
            self.fail("validate_config() raised ValueError unexpectedly!")

    def test_missing_sim_key(self):
        """Test that a missing simulation key raises a ValueError."""
        invalid_config = self.valid_sim_config.copy()
        del invalid_config["do_saturation"]
        with self.assertRaisesRegex(ValueError, "Missing required simulation parameter"):
            validate_config(invalid_config, self.valid_pid_gains)

    def test_wrong_type_sim_key(self):
        """Test that a simulation key with the wrong type raises a ValueError."""
        invalid_config = self.valid_sim_config.copy()
        invalid_config["time_delay_steps"] = "five" # Should be int
        with self.assertRaisesRegex(ValueError, "has incorrect type"):
            validate_config(invalid_config, self.valid_pid_gains)

    def test_missing_pid_controller(self):
        """Test that a missing controller in PID gains raises a ValueError."""
        invalid_gains = self.valid_pid_gains.copy()
        del invalid_gains["dosing_controller"]
        with self.assertRaisesRegex(ValueError, "Missing 'dosing_controller' gains"):
            validate_config(self.valid_sim_config, invalid_gains)

    def test_missing_pid_gain(self):
        """Test that a missing gain for a controller raises a ValueError."""
        invalid_gains = self.valid_pid_gains.copy()
        del invalid_gains["aeration_controller"]["Kp"]
        with self.assertRaisesRegex(ValueError, "Missing required PID gain 'Kp'"):
            validate_config(self.valid_sim_config, invalid_gains)

    def test_wrong_type_pid_gain(self):
        """Test that a PID gain with the wrong type raises a ValueError."""
        invalid_gains = self.valid_pid_gains.copy()
        invalid_gains["dosing_controller"]["Ki"] = "zero point one" # Should be float
        with self.assertRaisesRegex(ValueError, "has incorrect type"):
            validate_config(self.valid_sim_config, invalid_gains)

if __name__ == '__main__':
    unittest.main()

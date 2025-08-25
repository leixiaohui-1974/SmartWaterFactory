import unittest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from water_plant_controller.models.water_quality import WaterQuality

class TestWaterQuality(unittest.TestCase):
    """Unit tests for the WaterQuality data class."""

    def test_creation(self):
        """Test that a WaterQuality object can be created with correct attributes."""
        ts = datetime.now()
        wq = WaterQuality(
            timestamp=ts,
            ph=7.2,
            turbidity=3.4,
            dissolved_oxygen=8.1
        )
        self.assertEqual(wq.timestamp, ts)
        self.assertEqual(wq.ph, 7.2)
        self.assertEqual(wq.turbidity, 3.4)
        self.assertEqual(wq.dissolved_oxygen, 8.1)

if __name__ == '__main__':
    unittest.main()

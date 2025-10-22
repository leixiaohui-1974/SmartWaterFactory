import pytest
from datetime import datetime

from water_plant_controller.models.water_quality import WaterQuality


class TestWaterQuality:
    def test_creation(self):
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        quality = WaterQuality(
            timestamp=timestamp,
            ph=7.0,
            turbidity=5.0,
            dissolved_oxygen=8.0,
        )

        assert quality.timestamp == timestamp
        assert quality.ph == 7.0
        assert quality.turbidity == 5.0
        assert quality.dissolved_oxygen == 8.0

        str_repr = str(quality)
        assert "WaterQuality" in str_repr
        assert "7.0" in str_repr

    def test_post_init_validation(self):
        timestamp = datetime.now()

        with pytest.raises(ValueError, match="pH must fall between 0 and 14"):
            WaterQuality(timestamp=timestamp, ph=15.0, turbidity=1.0, dissolved_oxygen=8.0)

        with pytest.raises(ValueError, match="pH must fall between 0 and 14"):
            WaterQuality(timestamp=timestamp, ph=-1.0, turbidity=1.0, dissolved_oxygen=8.0)

        with pytest.raises(ValueError, match="Turbidity cannot be negative"):
            WaterQuality(timestamp=timestamp, ph=7.0, turbidity=-1.0, dissolved_oxygen=8.0)

        with pytest.raises(ValueError, match="Dissolved oxygen cannot be negative"):
            WaterQuality(timestamp=timestamp, ph=7.0, turbidity=1.0, dissolved_oxygen=-1.0)

    def test_is_within_normal_range(self):
        timestamp = datetime.now()

        normal_quality = WaterQuality(
            timestamp=timestamp, ph=7.0, turbidity=1.0, dissolved_oxygen=8.0
        )
        assert normal_quality.is_within_normal_range() is True

        low_ph_quality = WaterQuality(
            timestamp=timestamp, ph=5.0, turbidity=1.0, dissolved_oxygen=8.0
        )
        assert low_ph_quality.is_within_normal_range() is False

        high_ph_quality = WaterQuality(
            timestamp=timestamp, ph=9.5, turbidity=1.0, dissolved_oxygen=8.0
        )
        assert high_ph_quality.is_within_normal_range() is False

        high_turbidity_quality = WaterQuality(
            timestamp=timestamp, ph=7.0, turbidity=15.0, dissolved_oxygen=8.0
        )
        assert high_turbidity_quality.is_within_normal_range() is False

        low_do_quality = WaterQuality(
            timestamp=timestamp, ph=7.0, turbidity=1.0, dissolved_oxygen=3.0
        )
        assert low_do_quality.is_within_normal_range() is False

        high_do_quality = WaterQuality(
            timestamp=timestamp, ph=7.0, turbidity=1.0, dissolved_oxygen=15.0
        )
        assert high_do_quality.is_within_normal_range() is False

    def test_boundary_values(self):
        timestamp = datetime.now()

        min_ph_quality = WaterQuality(
            timestamp=timestamp, ph=0.0, turbidity=1.0, dissolved_oxygen=8.0
        )
        assert min_ph_quality.ph == 0.0

        max_ph_quality = WaterQuality(
            timestamp=timestamp, ph=14.0, turbidity=1.0, dissolved_oxygen=8.0
        )
        assert max_ph_quality.ph == 14.0

        zero_values_quality = WaterQuality(
            timestamp=timestamp, ph=7.0, turbidity=0.0, dissolved_oxygen=0.0
        )
        assert zero_values_quality.turbidity == 0.0
        assert zero_values_quality.dissolved_oxygen == 0.0

    def test_normal_range_boundaries(self):
        timestamp = datetime.now()

        lower_bound_quality = WaterQuality(
            timestamp=timestamp, ph=6.5, turbidity=0.0, dissolved_oxygen=5.0
        )
        assert lower_bound_quality.is_within_normal_range() is True

        upper_bound_quality = WaterQuality(
            timestamp=timestamp, ph=8.5, turbidity=4.0, dissolved_oxygen=12.0
        )
        assert upper_bound_quality.is_within_normal_range() is True

from dataclasses import dataclass
from datetime import datetime


@dataclass
class WaterQuality:
    """
    Represent a water-quality sample measured at a specific time.

    The dataclass stores the core measurements produced during the treatment
    process—timestamp, pH, turbidity, and dissolved oxygen concentration.
    Each value is expected to stay within realistic physical ranges.
    """

    timestamp: datetime
    ph: float
    turbidity: float
    dissolved_oxygen: float

    def __post_init__(self) -> None:
        """
        Validate that the supplied values remain inside their permissible ranges.

        Raises:
            ValueError: If a parameter falls outside its expected bounds.
        """

        if not (0.0 <= self.ph <= 14.0):
            raise ValueError(f"pH must fall between 0 and 14; received {self.ph}")
        if self.turbidity < 0.0:
            raise ValueError(f"Turbidity cannot be negative; received {self.turbidity}")
        if self.dissolved_oxygen < 0.0:
            raise ValueError(
                f"Dissolved oxygen cannot be negative; received {self.dissolved_oxygen}"
            )

    def is_within_normal_range(self) -> bool:
        """
        Return True if the measurements fall inside the nominal operating band.
        """

        return (
            6.5 <= self.ph <= 8.5
            and self.turbidity <= 10.0
            and 5.0 <= self.dissolved_oxygen <= 12.0
        )

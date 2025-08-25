from dataclasses import dataclass
from datetime import datetime

@dataclass
class WaterQuality:
    """
    Represents the water quality parameters at a specific point in time.
    """
    timestamp: datetime
    ph: float
    turbidity: float  # in NTU (Nephelometric Turbidity Units)
    dissolved_oxygen: float  # in mg/L

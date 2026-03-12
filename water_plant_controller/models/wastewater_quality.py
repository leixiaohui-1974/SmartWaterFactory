from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WastewaterQuality:
    """
    Composite wastewater-quality sample for rural domestic treatment scenarios.

    Concentration units are mg/L except `pH`, `temperature` (degC), and
    `flow_rate` (m3/d).
    """

    COD: float
    NH3_N: float
    TN: float
    TP: float
    SS: float
    DO: float
    pH: float
    temperature: float
    flow_rate: float

    def __post_init__(self) -> None:
        for field_name in ("COD", "NH3_N", "TN", "TP", "SS", "DO", "flow_rate"):
            value = getattr(self, field_name)
            if value < 0.0:
                raise ValueError(f"{field_name} cannot be negative; received {value}")

        if not (0.0 <= self.pH <= 14.0):
            raise ValueError(f"pH must fall between 0 and 14; received {self.pH}")

        if not (-5.0 <= self.temperature <= 60.0):
            raise ValueError(
                f"temperature must remain within a realistic operating range; received {self.temperature}"
            )

    def is_discharge_compliant(self) -> bool:
        """
        Check whether the sample meets GB18918-2002 Class 1A limits.

        The ammonia limit follows the standard's temperature-dependent notation:
        5 mg/L under typical conditions and 8 mg/L when water temperature is
        at or below 12 degC.
        """

        ammonia_limit = 8.0 if self.temperature <= 12.0 else 5.0

        return (
            self.COD <= 50.0
            and self.NH3_N <= ammonia_limit
            and self.TN <= 15.0
            and self.TP <= 0.5
            and self.SS <= 10.0
            and 6.0 <= self.pH <= 9.0
        )

    @classmethod
    def from_rural_typical(cls) -> "WastewaterQuality":
        """
        Return a representative rural domestic wastewater influent.
        """

        return cls(
            COD=280.0,
            NH3_N=28.0,
            TN=38.0,
            TP=4.5,
            SS=180.0,
            DO=0.6,
            pH=7.1,
            temperature=18.0,
            flow_rate=120.0,
        )

"""ML prediction module for water quality forecasting.

Provides time-series forecasting and predictive models for water treatment
process parameters (turbidity, DO, pH) with multiple algorithm backends.
"""

from water_plant_controller.ml.time_series_forecaster import (
    ARIMAForecaster,
    ExponentialSmoothingForecaster,
    TimeSeriesForecaster,
)
from water_plant_controller.ml.predictive_model import (
    PredictiveModel,
    WaterQualityPredictor,
)

__all__ = [
    "ARIMAForecaster",
    "ExponentialSmoothingForecaster",
    "TimeSeriesForecaster",
    "PredictiveModel",
    "WaterQualityPredictor",
]

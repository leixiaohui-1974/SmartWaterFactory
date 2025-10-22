from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional


@dataclass
class KalmanFilter1D:
    """
    Minimal 1-D Kalman filter for slowly varying signals.

    State model:
        x_k = x_(k-1) + w_k
        z_k = x_k + v_k
    """

    process_var: float
    measurement_var: float
    estimate: float = 0.0
    covariance: float = 1.0

    def update(self, measurement: float) -> tuple[float, float]:
        # Prediction step
        pred_covariance = self.covariance + self.process_var

        # Update step
        kalman_gain = pred_covariance / (pred_covariance + self.measurement_var)
        self.estimate = self.estimate + kalman_gain * (measurement - self.estimate)
        self.covariance = (1.0 - kalman_gain) * pred_covariance
        return self.estimate, self.covariance


class SensorMonitor:
    """
    Monitor that fuses measurements with a Kalman predictor and tracks sensor bias.

    The monitor maintains an exponential moving average (EMA) of the bias and its
    variance to derive an adaptive threshold.  The resulting likelihood score can
    be used to trigger alarms or weight redundant measurements.
    """

    def __init__(
        self,
        *,
        process_var: float = 0.08,
        measurement_var: float = 2.5,
        bias_forget: float = 0.98,
        min_threshold: float = 0.5,
        cross_tolerance: float = 1.5,
        fault_score_decay: float = 0.92,
        fault_score_threshold: float = 0.4,
    ) -> None:
        self.filter = KalmanFilter1D(
            process_var=process_var,
            measurement_var=measurement_var,
        )
        self.bias_mean = 0.0
        self.bias_var = 1.0
        self.forget = bias_forget
        self.min_threshold = min_threshold
        self.cross_tolerance = cross_tolerance
        self.fault_score_decay = fault_score_decay
        self.fault_score_threshold = fault_score_threshold
        self._fault_score = 0.0

    def update(
        self,
        measurement: float,
        *,
        redundant_measurement: Optional[float] = None,
    ) -> dict[str, float]:
        estimate, _ = self.filter.update(measurement)

        bias = measurement - estimate
        # Update bias statistics (EMA)
        self.bias_mean = self.forget * self.bias_mean + (1.0 - self.forget) * bias
        deviation = bias - self.bias_mean
        self.bias_var = self.forget * self.bias_var + (1.0 - self.forget) * (
            deviation * deviation
        )
        sigma = max(self.bias_var**0.5, 1e-6)
        adaptive_threshold = max(self.min_threshold, 3.0 * sigma)

        likelihood = min(1.0, abs(bias) / (adaptive_threshold + 1e-6))
        primary_reliability = max(0.0, min(1.0, 1.0 - likelihood))

        fused_measurement = measurement
        redundant_reliability: Optional[float] = None
        dual_sensor_delta = 0.0
        if redundant_measurement is not None and math.isfinite(redundant_measurement):
            dual_sensor_delta = measurement - redundant_measurement
            cross_likelihood = min(
                1.0, abs(dual_sensor_delta) / (self.cross_tolerance + 1e-6)
            )
            redundant_reliability = max(0.0, min(1.0, 1.0 - cross_likelihood))
            weight_sum = primary_reliability + redundant_reliability
            if weight_sum > 1e-6:
                fused_measurement = (
                    measurement * primary_reliability
                    + redundant_measurement * redundant_reliability
                ) / weight_sum

        combined_reliability = primary_reliability
        if redundant_reliability is not None:
            combined_reliability = max(primary_reliability, redundant_reliability)

        soft_measurement = (
            combined_reliability * fused_measurement
            + (1.0 - combined_reliability) * estimate
        )

        self._fault_score = (
            self.fault_score_decay * self._fault_score
            + (1.0 - self.fault_score_decay) * (1.0 - combined_reliability)
        )
        fault_trip = float(self._fault_score >= self.fault_score_threshold)

        return {
            "filtered_turbidity": estimate,
            "sensor_bias_estimate": bias,
            "sensor_bias_threshold": adaptive_threshold,
            "sensor_fault_likelihood": likelihood,
            "sensor_reliability": combined_reliability,
            "soft_measurement": soft_measurement,
            "fused_measurement": fused_measurement,
            "redundant_reliability": redundant_reliability or 0.0,
            "dual_sensor_delta": dual_sensor_delta,
            "fault_score": self._fault_score,
            "fault_trip": fault_trip,
        }

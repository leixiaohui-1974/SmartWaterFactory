"""Time-series forecasting for water quality parameters.

Implements multiple forecasting strategies:
- Exponential Smoothing (Holt-Winters, no external deps)
- ARIMA (numpy-based simplified implementation)
- Ensemble (weighted combination of multiple forecasters)

All forecasters share a common interface via ``TimeSeriesForecaster``.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np


@dataclass
class ForecastResult:
    """Container for forecast output."""

    values: List[float]
    lower_bound: List[float]
    upper_bound: List[float]
    confidence: float = 0.95
    method: str = "unknown"
    metrics: dict = field(default_factory=dict)


class TimeSeriesForecaster(ABC):
    """Abstract base for time-series forecasters."""

    @abstractmethod
    def fit(self, data: Sequence[float]) -> None:
        """Fit the forecaster on historical data."""

    @abstractmethod
    def predict(self, steps: int) -> ForecastResult:
        """Forecast ``steps`` time steps ahead."""

    def fit_predict(self, data: Sequence[float], steps: int) -> ForecastResult:
        """Convenience: fit then predict."""
        self.fit(data)
        return self.predict(steps)


class ExponentialSmoothingForecaster(TimeSeriesForecaster):
    """Holt double exponential smoothing (trend, no seasonality).

    Parameters
    ----------
    alpha : float
        Level smoothing factor (0 < alpha < 1).
    beta : float
        Trend smoothing factor (0 < beta < 1).
    """

    def __init__(self, alpha: float = 0.3, beta: float = 0.1) -> None:
        if not 0 < alpha < 1:
            raise ValueError(f"alpha must be in (0, 1), got {alpha}")
        if not 0 < beta < 1:
            raise ValueError(f"beta must be in (0, 1), got {beta}")
        self.alpha = alpha
        self.beta = beta
        self._level: float = 0.0
        self._trend: float = 0.0
        self._residuals: List[float] = []
        self._fitted = False

    def fit(self, data: Sequence[float]) -> None:
        arr = list(data)
        if len(arr) < 2:
            raise ValueError("Need at least 2 data points")

        # Initialize
        self._level = arr[0]
        self._trend = arr[1] - arr[0]
        self._residuals = []

        for i in range(1, len(arr)):
            prev_level = self._level
            self._level = self.alpha * arr[i] + (1 - self.alpha) * (prev_level + self._trend)
            self._trend = self.beta * (self._level - prev_level) + (1 - self.beta) * self._trend
            fitted_val = prev_level + self._trend
            self._residuals.append(arr[i] - fitted_val)

        self._fitted = True

    def predict(self, steps: int) -> ForecastResult:
        if not self._fitted:
            raise RuntimeError("Must call fit() before predict()")

        residual_std = float(np.std(self._residuals)) if self._residuals else 1.0
        values = []
        lower = []
        upper = []

        for h in range(1, steps + 1):
            forecast = self._level + h * self._trend
            # Prediction interval widens with horizon
            margin = 1.96 * residual_std * math.sqrt(h)
            values.append(forecast)
            lower.append(forecast - margin)
            upper.append(forecast + margin)

        return ForecastResult(
            values=values,
            lower_bound=lower,
            upper_bound=upper,
            method="holt_exponential_smoothing",
            metrics={"residual_std": residual_std},
        )


class ARIMAForecaster(TimeSeriesForecaster):
    """Simplified ARIMA(p, d, q) forecaster using numpy least-squares.

    This is a lightweight implementation suitable for short-term water
    quality forecasting without requiring statsmodels.

    Parameters
    ----------
    p : int
        Autoregressive order.
    d : int
        Differencing order (0 or 1).
    q : int
        Moving-average order.
    """

    def __init__(self, p: int = 3, d: int = 1, q: int = 1) -> None:
        self.p = p
        self.d = d
        self.q = q
        self._ar_coefs: Optional[np.ndarray] = None
        self._ma_coefs: Optional[np.ndarray] = None
        self._residuals: List[float] = []
        self._history: List[float] = []
        self._diff_history: List[float] = []
        self._fitted = False

    @staticmethod
    def _difference(data: List[float], order: int) -> List[float]:
        result = list(data)
        for _ in range(order):
            result = [result[i] - result[i - 1] for i in range(1, len(result))]
        return result

    def fit(self, data: Sequence[float]) -> None:
        arr = list(data)
        n = len(arr)
        if n < self.p + self.d + 2:
            raise ValueError(f"Need at least {self.p + self.d + 2} data points, got {n}")

        self._history = arr[:]

        # Difference
        diffed = self._difference(arr, self.d)
        self._diff_history = diffed

        # AR: fit y[t] = c + sum(phi_i * y[t-i]) via least squares
        if self.p > 0 and len(diffed) > self.p:
            X_rows = []
            y_vec = []
            for t in range(self.p, len(diffed)):
                row = [diffed[t - i - 1] for i in range(self.p)]
                row.append(1.0)  # intercept
                X_rows.append(row)
                y_vec.append(diffed[t])
            X = np.array(X_rows)
            y = np.array(y_vec)
            # Least squares: phi = (X'X)^{-1} X'y
            try:
                coefs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
                self._ar_coefs = coefs[:-1]
                self._intercept = coefs[-1]
            except np.linalg.LinAlgError:
                self._ar_coefs = np.zeros(self.p)
                self._intercept = 0.0
        else:
            self._ar_coefs = np.zeros(max(self.p, 1))
            self._intercept = float(np.mean(diffed)) if diffed else 0.0

        # Compute residuals for MA and prediction intervals
        self._residuals = []
        for t in range(self.p, len(diffed)):
            pred = self._intercept
            for i in range(self.p):
                pred += self._ar_coefs[i] * diffed[t - i - 1]
            self._residuals.append(diffed[t] - pred)

        # Simple MA coefficients (average recent residual influence)
        if self.q > 0 and len(self._residuals) > self.q:
            self._ma_coefs = np.zeros(self.q)
            # Approximate MA via correlation of residuals
            res_arr = np.array(self._residuals)
            for j in range(self.q):
                if len(res_arr) > j + 1:
                    lagged = res_arr[: -(j + 1)]
                    current = res_arr[j + 1 :]
                    min_len = min(len(lagged), len(current))
                    if min_len > 0:
                        corr = np.corrcoef(lagged[:min_len], current[:min_len])
                        self._ma_coefs[j] = corr[0, 1] if not np.isnan(corr[0, 1]) else 0.0
        else:
            self._ma_coefs = np.zeros(max(self.q, 1))

        self._fitted = True

    def predict(self, steps: int) -> ForecastResult:
        if not self._fitted:
            raise RuntimeError("Must call fit() before predict()")

        diff_ext = list(self._diff_history)
        res_ext = list(self._residuals)
        residual_std = float(np.std(self._residuals)) if self._residuals else 1.0

        for _ in range(steps):
            pred = self._intercept
            # AR component
            for i in range(self.p):
                idx = len(diff_ext) - i - 1
                if idx >= 0:
                    pred += self._ar_coefs[i] * diff_ext[idx]
            # MA component
            for j in range(self.q):
                idx = len(res_ext) - j - 1
                if idx >= 0:
                    pred += self._ma_coefs[j] * res_ext[idx]

            diff_ext.append(pred)
            res_ext.append(0.0)

        # Integrate back (support d >= 2)
        forecasts_diff = diff_ext[len(self._diff_history):]

        if self.d == 0:
            integrated = forecasts_diff
        else:
            # Multi-order integration: apply cumsum d times
            # Need the last value from each differencing level
            integrated = list(forecasts_diff)
            history_levels = [list(self._history)]
            for _ in range(self.d - 1):
                history_levels.append(self._difference(history_levels[-1], 1))

            for level in range(self.d):
                anchor = history_levels[self.d - 1 - level][-1]
                new_integrated = []
                cumsum = anchor
                for val in integrated:
                    cumsum += val
                    new_integrated.append(cumsum)
                integrated = new_integrated

        values = []
        lower = []
        upper = []
        for h, val in enumerate(integrated, 1):
            margin = 1.96 * residual_std * math.sqrt(h)
            values.append(val)
            lower.append(val - margin)
            upper.append(val + margin)

        return ForecastResult(
            values=values,
            lower_bound=lower,
            upper_bound=upper,
            method=f"arima({self.p},{self.d},{self.q})",
            metrics={
                "residual_std": residual_std,
                "ar_coefs": self._ar_coefs.tolist() if self._ar_coefs is not None else [],
            },
        )


class EnsembleForecaster(TimeSeriesForecaster):
    """Weighted ensemble of multiple forecasters.

    Parameters
    ----------
    forecasters : list of (weight, forecaster) tuples
    """

    def __init__(
        self,
        forecasters: Optional[List[tuple]] = None,
    ) -> None:
        if forecasters is None:
            forecasters = [
                (0.5, ARIMAForecaster(p=3, d=1, q=1)),
                (0.5, ExponentialSmoothingForecaster(alpha=0.3, beta=0.1)),
            ]
        self._forecasters = forecasters
        total_w = sum(w for w, _ in self._forecasters)
        self._weights = [w / total_w for w, _ in self._forecasters]

    def fit(self, data: Sequence[float]) -> None:
        for _, forecaster in self._forecasters:
            forecaster.fit(data)

    def predict(self, steps: int) -> ForecastResult:
        results = [f.predict(steps) for _, f in self._forecasters]

        values = [0.0] * steps
        lower = [0.0] * steps
        upper = [0.0] * steps

        for w, res in zip(self._weights, results):
            for i in range(steps):
                values[i] += w * res.values[i]
                lower[i] += w * res.lower_bound[i]
                upper[i] += w * res.upper_bound[i]

        return ForecastResult(
            values=values,
            lower_bound=lower,
            upper_bound=upper,
            method="ensemble",
            metrics={"sub_methods": [r.method for r in results]},
        )

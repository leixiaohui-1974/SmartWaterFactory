"""Tests for ML prediction module (time series + predictive models)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from water_plant_controller.ml.time_series_forecaster import (
    ARIMAForecaster,
    EnsembleForecaster,
    ExponentialSmoothingForecaster,
)
from water_plant_controller.ml.predictive_model import (
    PredictiveModel,
    WaterQualityPredictor,
)


# ---------------------------------------------------------------------------
# Exponential Smoothing
# ---------------------------------------------------------------------------


class TestExponentialSmoothing:
    """Test Holt exponential smoothing forecaster."""

    def test_basic_forecast(self):
        """Linear trend data should produce increasing forecasts."""
        data = [10.0 + 0.5 * i for i in range(30)]
        f = ExponentialSmoothingForecaster(alpha=0.3, beta=0.1)
        result = f.fit_predict(data, 5)

        assert len(result.values) == 5
        assert result.method == "holt_exponential_smoothing"
        # Forecasts should continue the upward trend
        assert result.values[-1] > result.values[0]

    def test_constant_series(self):
        """Constant series should forecast near-constant values."""
        data = [5.0] * 20
        f = ExponentialSmoothingForecaster()
        result = f.fit_predict(data, 3)

        for v in result.values:
            assert abs(v - 5.0) < 1.0

    def test_prediction_intervals_widen(self):
        """Prediction intervals should widen with horizon."""
        data = list(np.random.normal(10.0, 1.0, 50))
        f = ExponentialSmoothingForecaster()
        result = f.fit_predict(data, 10)

        widths = [u - l for u, l in zip(result.upper_bound, result.lower_bound)]
        assert widths[-1] > widths[0], "Intervals should widen over time"

    def test_invalid_alpha(self):
        with pytest.raises(ValueError, match="alpha"):
            ExponentialSmoothingForecaster(alpha=1.5)

    def test_too_few_points(self):
        f = ExponentialSmoothingForecaster()
        with pytest.raises(ValueError, match="at least 2"):
            f.fit([5.0])

    def test_predict_before_fit(self):
        f = ExponentialSmoothingForecaster()
        with pytest.raises(RuntimeError, match="fit"):
            f.predict(3)


# ---------------------------------------------------------------------------
# ARIMA
# ---------------------------------------------------------------------------


class TestARIMA:
    """Test simplified ARIMA forecaster."""

    def test_arima_linear_trend(self):
        """ARIMA(3,1,1) should handle linear trend data."""
        data = [10.0 + 0.3 * i + 0.1 * np.sin(i) for i in range(50)]
        f = ARIMAForecaster(p=3, d=1, q=1)
        result = f.fit_predict(data, 5)

        assert len(result.values) == 5
        assert "arima" in result.method

    def test_arima_stationary(self):
        """ARIMA(2,0,0) on stationary data should produce stable forecasts."""
        np.random.seed(42)
        data = list(np.random.normal(100.0, 2.0, 60))
        f = ARIMAForecaster(p=2, d=0, q=0)
        result = f.fit_predict(data, 5)

        for v in result.values:
            assert 80.0 < v < 120.0, f"Forecast {v} out of reasonable range"

    def test_arima_has_prediction_intervals(self):
        data = [float(i) for i in range(20)]
        f = ARIMAForecaster(p=2, d=1, q=0)
        result = f.fit_predict(data, 3)

        for v, l, u in zip(result.values, result.lower_bound, result.upper_bound):
            assert l <= v <= u

    def test_arima_too_few_points(self):
        f = ARIMAForecaster(p=3, d=1, q=1)
        with pytest.raises(ValueError, match="at least"):
            f.fit([1.0, 2.0])

    def test_arima_metrics(self):
        data = [10.0 + i * 0.5 for i in range(30)]
        f = ARIMAForecaster()
        result = f.fit_predict(data, 3)

        assert "residual_std" in result.metrics
        assert "ar_coefs" in result.metrics


# ---------------------------------------------------------------------------
# Ensemble
# ---------------------------------------------------------------------------


class TestEnsemble:
    """Test ensemble forecaster."""

    def test_ensemble_combines_methods(self):
        data = [10.0 + 0.2 * i for i in range(40)]
        f = EnsembleForecaster()
        result = f.fit_predict(data, 5)

        assert result.method == "ensemble"
        assert len(result.values) == 5
        assert "sub_methods" in result.metrics

    def test_ensemble_between_components(self):
        """Ensemble values should be between component forecasts."""
        data = [10.0 + 0.5 * i for i in range(40)]
        arima = ARIMAForecaster(p=2, d=1, q=0)
        es = ExponentialSmoothingForecaster()

        r_arima = arima.fit_predict(data, 3)
        r_es = es.fit_predict(data, 3)

        ensemble = EnsembleForecaster([(0.5, ARIMAForecaster(p=2, d=1, q=0)), (0.5, ExponentialSmoothingForecaster())])
        r_ens = ensemble.fit_predict(data, 3)

        for i in range(3):
            lo = min(r_arima.values[i], r_es.values[i])
            hi = max(r_arima.values[i], r_es.values[i])
            assert lo - 0.01 <= r_ens.values[i] <= hi + 0.01


# ---------------------------------------------------------------------------
# Predictive Model
# ---------------------------------------------------------------------------


class TestPredictiveModel:
    """Test multi-target predictive model."""

    def _make_training_data(self, n=100):
        np.random.seed(42)
        X = np.random.randn(n, 3)
        y = {
            "turbidity": 5.0 + 2.0 * X[:, 0] - 1.5 * X[:, 1] + np.random.randn(n) * 0.3,
            "dissolved_oxygen": 8.0 - 0.5 * X[:, 0] + 1.0 * X[:, 2] + np.random.randn(n) * 0.2,
            "ph": 7.0 + 0.3 * X[:, 1] + np.random.randn(n) * 0.1,
        }
        return X, y

    def test_numpy_backend_fit_predict(self):
        X, y = self._make_training_data()
        model = PredictiveModel(backend="numpy")
        scores = model.fit(X, y, feature_names=["temp", "flow", "pressure"])

        assert len(scores) == 3
        for target, r2 in scores.items():
            assert r2 > 0.5, f"{target} R² too low: {r2}"

        result = model.predict(np.array([0.5, -0.3, 1.0]))
        assert "turbidity" in result.values
        assert "dissolved_oxygen" in result.values
        assert "ph" in result.values
        assert result.method == "numpy"

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("sklearn"),
        reason="scikit-learn not installed",
    )
    def test_sklearn_backend_fit_predict(self):
        X, y = self._make_training_data()
        model = PredictiveModel(backend="sklearn")
        scores = model.fit(X, y)

        for target, r2 in scores.items():
            assert r2 > 0.7, f"{target} R² too low: {r2}"

        result = model.predict(np.array([0.5, -0.3, 1.0]))
        assert "turbidity" in result.values
        assert result.method == "sklearn"
        # Should have feature importance
        assert len(result.feature_importance) > 0

    def test_predict_before_fit(self):
        model = PredictiveModel(backend="numpy")
        with pytest.raises(RuntimeError, match="fit"):
            model.predict(np.array([1.0, 2.0, 3.0]))


# ---------------------------------------------------------------------------
# Water Quality Predictor (high-level)
# ---------------------------------------------------------------------------


class TestWaterQualityPredictor:
    """Test the high-level water quality predictor."""

    @staticmethod
    def _make_history(n=80):
        """Generate synthetic water quality history."""
        np.random.seed(123)
        history = []
        for i in range(n):
            t = i / n
            history.append({
                "turbidity": 5.0 + 3.0 * np.sin(2 * np.pi * t) + np.random.randn() * 0.3,
                "dissolved_oxygen": 7.5 - 1.0 * np.cos(2 * np.pi * t) + np.random.randn() * 0.2,
                "ph": 7.2 + 0.3 * np.sin(4 * np.pi * t) + np.random.randn() * 0.1,
            })
        return history

    def test_fit_and_predict(self):
        history = self._make_history(80)
        predictor = WaterQualityPredictor(
            horizon_minutes=5,
            lookback_steps=10,
            backend="numpy",
        )
        scores = predictor.fit(history)

        assert "turbidity" in scores
        assert "dissolved_oxygen" in scores

        # Predict from recent data
        result = predictor.predict(history[-15:])
        assert "turbidity" in result.values
        assert "ph" in result.values

    def test_too_few_readings(self):
        predictor = WaterQualityPredictor(lookback_steps=10, horizon_minutes=5)
        with pytest.raises(ValueError, match="at least"):
            predictor.fit([{"turbidity": 1.0, "dissolved_oxygen": 8.0, "ph": 7.0}] * 5)

    def test_feature_extraction(self):
        history = self._make_history(20)
        features, names = WaterQualityPredictor._extract_features(history, 10)

        # Should have features for 3 parameters × 7 features each = 21
        assert len(features) == 21
        assert len(names) == 21
        assert "turbidity_current" in names
        assert "dissolved_oxygen_trend" in names
        assert "ph_roc" in names

    def test_predict_values_reasonable(self):
        """Predicted values should be within physical bounds."""
        history = self._make_history(80)
        predictor = WaterQualityPredictor(
            horizon_minutes=5, lookback_steps=10, backend="numpy",
        )
        predictor.fit(history)
        result = predictor.predict(history[-15:])

        # Turbidity should be positive
        assert result.values["turbidity"] > 0
        # DO should be reasonable
        assert 0 < result.values["dissolved_oxygen"] < 20
        # pH should be in range
        assert 4 < result.values["ph"] < 10

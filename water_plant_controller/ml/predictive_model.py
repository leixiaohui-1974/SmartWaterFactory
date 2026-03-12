"""Predictive models for water treatment process parameters.

Provides multi-parameter water quality prediction using:
- Linear regression (numpy, always available)
- Gradient boosting (scikit-learn, optional)
- Feature engineering for water treatment domain

Key use cases:
- Predict effluent quality 15-30 minutes ahead
- Predict chemical dosing requirements
- Predict energy consumption patterns
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Check sklearn availability
try:
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


@dataclass
class PredictionResult:
    """Container for prediction output."""

    values: Dict[str, float]
    confidence: Dict[str, float]
    feature_importance: Dict[str, float] = field(default_factory=dict)
    method: str = "unknown"
    metrics: Dict[str, float] = field(default_factory=dict)


class PredictiveModel:
    """Multi-target regression model for water quality prediction.

    Supports two backends:
    - ``numpy``: Polynomial regression via least-squares (always available)
    - ``sklearn``: Gradient boosting regressor (if scikit-learn installed)

    Parameters
    ----------
    backend : str
        ``"auto"`` (prefer sklearn), ``"numpy"``, or ``"sklearn"``.
    degree : int
        Polynomial degree for numpy backend.
    targets : list of str
        Target variable names (default: turbidity, dissolved_oxygen, ph).
    """

    def __init__(
        self,
        backend: str = "auto",
        degree: int = 2,
        targets: Optional[List[str]] = None,
    ) -> None:
        if backend == "auto":
            self._backend = "sklearn" if SKLEARN_AVAILABLE else "numpy"
        elif backend == "sklearn" and not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for sklearn backend")
        else:
            self._backend = backend

        self._degree = degree
        self._targets = targets or ["turbidity", "dissolved_oxygen", "ph"]
        self._models: Dict[str, Any] = {}
        self._scalers: Dict[str, Any] = {}
        self._np_mean: Optional[np.ndarray] = None
        self._np_std: Optional[np.ndarray] = None
        self._feature_names: List[str] = []
        self._fitted = False

    def _build_features(self, X: np.ndarray) -> np.ndarray:
        """Build polynomial features from raw input."""
        if self._backend == "numpy" and self._degree > 1:
            features = [X]
            for d in range(2, self._degree + 1):
                features.append(X ** d)
            # Add interaction terms for pairs
            n_features = X.shape[1]
            if n_features >= 2:
                for i in range(min(n_features, 5)):
                    for j in range(i + 1, min(n_features, 5)):
                        features.append((X[:, i] * X[:, j]).reshape(-1, 1))
            return np.hstack(features)
        return X

    def fit(
        self,
        X: np.ndarray,
        y: Dict[str, np.ndarray],
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """Fit prediction models for each target.

        Parameters
        ----------
        X : ndarray of shape (n_samples, n_features)
            Input feature matrix.
        y : dict mapping target_name -> ndarray of shape (n_samples,)
            Target values for each variable.
        feature_names : list of str, optional
            Names for input features (for interpretability).

        Returns
        -------
        dict
            Training R² score for each target.
        """
        self._feature_names = feature_names or [f"x{i}" for i in range(X.shape[1])]
        scores = {}

        for target in self._targets:
            if target not in y:
                logger.warning("Target %s not in training data, skipping", target)
                continue

            y_target = np.array(y[target])

            if self._backend == "sklearn":
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                model = GradientBoostingRegressor(
                    n_estimators=100,
                    max_depth=4,
                    learning_rate=0.1,
                    random_state=42,
                )
                model.fit(X_scaled, y_target)
                # Store residual std for confidence estimation
                y_pred = model.predict(X_scaled)
                model._residual_std_ = float(np.std(y_target - y_pred))
                self._scalers[target] = scaler
                self._models[target] = model
                scores[target] = float(model.score(X_scaled, y_target))
            else:
                # Numpy: scale features before polynomial expansion
                if self._np_mean is None:
                    self._np_mean = X.mean(axis=0)
                    self._np_std = X.std(axis=0)
                    self._np_std[self._np_std == 0] = 1.0  # avoid div by zero
                X_scaled = (X - self._np_mean) / self._np_std
                X_poly = self._build_features(X_scaled)
                # Add intercept
                ones = np.ones((X_poly.shape[0], 1))
                X_aug = np.hstack([ones, X_poly])
                try:
                    coefs, residuals, _, _ = np.linalg.lstsq(X_aug, y_target, rcond=None)
                    self._models[target] = coefs
                except np.linalg.LinAlgError:
                    self._models[target] = np.zeros(X_aug.shape[1])

                # Compute R²
                y_pred = X_aug @ self._models[target]
                ss_res = np.sum((y_target - y_pred) ** 2)
                ss_tot = np.sum((y_target - np.mean(y_target)) ** 2)
                r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
                scores[target] = float(r2)

        self._fitted = True
        return scores

    def predict(self, X: np.ndarray) -> PredictionResult:
        """Predict target values for new input features.

        Parameters
        ----------
        X : ndarray of shape (1, n_features) or (n_features,)
            Single sample input features.

        Returns
        -------
        PredictionResult
        """
        if not self._fitted:
            raise RuntimeError("Must call fit() before predict()")

        if X.ndim == 1:
            X = X.reshape(1, -1)

        values = {}
        confidence = {}
        importance = {}

        for target, model in self._models.items():
            if self._backend == "sklearn":
                X_scaled = self._scalers[target].transform(X)
                pred = model.predict(X_scaled)
                values[target] = float(pred[0])
                # Feature importance from gradient boosting
                imp = dict(zip(self._feature_names, model.feature_importances_.tolist()))
                importance.update({f"{target}_{k}": v for k, v in imp.items()})
                # Confidence from training residual distribution (not tree std)
                train_residual_std = getattr(model, '_residual_std_', 1.0)
                confidence[target] = max(0.0, 1.0 - min(train_residual_std / (abs(float(pred[0])) + 1e-6), 1.0))
            else:
                X_scaled = (X - self._np_mean) / self._np_std if self._np_mean is not None else X
                X_poly = self._build_features(X_scaled)
                ones = np.ones((X_poly.shape[0], 1))
                X_aug = np.hstack([ones, X_poly])
                pred = X_aug @ model
                values[target] = float(pred[0])
                confidence[target] = 0.8  # Fixed confidence for linear model

        return PredictionResult(
            values=values,
            confidence=confidence,
            feature_importance=importance,
            method=self._backend,
        )


class WaterQualityPredictor:
    """High-level predictor for water treatment plant parameters.

    Combines feature engineering specific to water treatment with
    the generic PredictiveModel backend.

    Parameters
    ----------
    horizon_minutes : int
        Prediction horizon in minutes (default 15).
    lookback_steps : int
        Number of historical steps for feature construction.
    """

    def __init__(
        self,
        horizon_minutes: int = 15,
        lookback_steps: int = 10,
        backend: str = "auto",
    ) -> None:
        self.horizon_minutes = horizon_minutes
        self.lookback_steps = lookback_steps
        self._model = PredictiveModel(
            backend=backend,
            targets=["turbidity", "dissolved_oxygen", "ph"],
        )
        self._fitted = False

    @staticmethod
    def _extract_features(
        history: List[Dict[str, float]],
        lookback: int,
    ) -> Tuple[np.ndarray, List[str]]:
        """Extract domain features from a window of water quality readings.

        Features include:
        - Current values
        - Rolling mean and std
        - Trend (linear slope)
        - Rate of change
        """
        window = history[-lookback:] if len(history) >= lookback else history
        n = len(window)

        features = []
        names = []

        for param in ["turbidity", "dissolved_oxygen", "ph"]:
            vals = [w.get(param, 0.0) for w in window]
            arr = np.array(vals)

            # Current value
            features.append(arr[-1])
            names.append(f"{param}_current")

            # Rolling mean
            features.append(float(np.mean(arr)))
            names.append(f"{param}_mean")

            # Rolling std
            features.append(float(np.std(arr)))
            names.append(f"{param}_std")

            # Min and max
            features.append(float(np.min(arr)))
            names.append(f"{param}_min")
            features.append(float(np.max(arr)))
            names.append(f"{param}_max")

            # Linear trend (slope)
            if n >= 2:
                x = np.arange(n, dtype=float)
                slope = float(np.polyfit(x, arr, 1)[0])
            else:
                slope = 0.0
            features.append(slope)
            names.append(f"{param}_trend")

            # Rate of change (last step)
            if n >= 2:
                roc = arr[-1] - arr[-2]
            else:
                roc = 0.0
            features.append(float(roc))
            names.append(f"{param}_roc")

        return np.array(features), names

    def fit(self, history: List[Dict[str, float]]) -> Dict[str, float]:
        """Fit the predictor from a list of time-ordered quality readings.

        Each reading is a dict with keys: turbidity, dissolved_oxygen, ph.
        The ``horizon_minutes`` determines how many steps ahead we predict.

        Parameters
        ----------
        history : list of dict
            Time-ordered water quality readings.

        Returns
        -------
        dict
            Training R² for each target.
        """
        horizon = max(1, self.horizon_minutes)
        lookback = self.lookback_steps

        if len(history) < lookback + horizon + 1:
            raise ValueError(
                f"Need at least {lookback + horizon + 1} readings, "
                f"got {len(history)}"
            )

        X_list = []
        y_dict: Dict[str, List[float]] = {t: [] for t in ["turbidity", "dissolved_oxygen", "ph"]}
        feature_names = None

        for i in range(lookback, len(history) - horizon):
            window = history[i - lookback : i + 1]
            feats, names = self._extract_features(window, lookback)
            X_list.append(feats)
            if feature_names is None:
                feature_names = names

            future = history[i + horizon]
            for target in y_dict:
                y_dict[target].append(future.get(target, 0.0))

        if not X_list:
            raise ValueError("Not enough data to construct training samples after windowing")
        X = np.array(X_list)
        y_arrays = {k: np.array(v) for k, v in y_dict.items()}

        scores = self._model.fit(X, y_arrays, feature_names)
        self._fitted = True
        return scores

    def predict(self, recent_history: List[Dict[str, float]]) -> PredictionResult:
        """Predict water quality ``horizon_minutes`` ahead.

        Parameters
        ----------
        recent_history : list of dict
            Most recent readings (at least ``lookback_steps`` entries).

        Returns
        -------
        PredictionResult
        """
        if not self._fitted:
            raise RuntimeError("Must call fit() before predict()")

        feats, _ = self._extract_features(recent_history, self.lookback_steps)
        return self._model.predict(feats)

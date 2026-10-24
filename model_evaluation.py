"""Evaluate an existing compatibility model on an independently labelled holdout."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def evaluate_saved_model(model, features, targets):
    """Return the notebook's clipped regression metrics without fitting a model.

    ``features`` must contain the five app inputs and ``targets`` must be
    independently labelled 0–100 compatibility scores. The function never
    calls ``fit`` and does not modify the supplied model.
    """
    x = np.asarray(features, dtype=float)
    y = np.asarray(targets, dtype=float).reshape(-1)
    if x.ndim != 2 or x.shape[1] != 5:
        raise ValueError("Expected a 2D feature matrix with exactly 5 columns")
    if x.shape[0] < 2 or y.size != x.shape[0]:
        raise ValueError("At least two feature rows and one target per row are required")
    if np.unique(y).size < 2:
        raise ValueError("Targets must contain at least two distinct values for R²")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Features and targets must contain only finite numbers")
    if ((y < 0) | (y > 100)).any():
        raise ValueError("Targets must be compatibility scores in the 0–100 range")

    predictions = np.asarray(model.predict(x), dtype=float).reshape(-1)
    if predictions.size != y.size or not np.isfinite(predictions).all():
        raise ValueError("Model must return one finite prediction per feature row")
    predictions = np.clip(predictions, 0, 100)
    return {
        "mae": float(mean_absolute_error(y, predictions)),
        "rmse": float(np.sqrt(mean_squared_error(y, predictions))),
        "r2": float(r2_score(y, predictions)),
        "n": int(y.size),
    }

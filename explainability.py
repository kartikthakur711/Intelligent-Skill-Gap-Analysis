"""Model-agnostic exact Shapley explanations for the app's five numeric inputs.

Attributions use an all-zero reference input, so they explain the model's
prediction relative to that reference. They are not causal effects and are
calculated on the model's raw output before the app's 0–100 display clipping.
"""
from __future__ import annotations

from itertools import combinations
from math import factorial

import numpy as np

FEATURE_NAMES = (
    "resume_skill_count",
    "job_skill_count",
    "skill_overlap_ratio",
    "tfidf_similarity",
    "semantic_similarity",
)


def explain_prediction(model, features):
    """Return (raw prediction, five additive attributions).

    Enumerates every feature coalition (only 32 for this five-feature model),
    making the result deterministic and exactly additive to the raw model
    output relative to the zero reference. Missing/non-finite values fail
    clearly rather than silently changing the prediction.
    """
    values = np.asarray(features, dtype=float).reshape(-1)
    if values.size != len(FEATURE_NAMES):
        raise ValueError(f"Expected {len(FEATURE_NAMES)} features, got {values.size}")
    if not np.isfinite(values).all():
        raise ValueError("Prediction features must all be finite numbers")

    baseline = np.zeros_like(values)
    raw_prediction = float(np.asarray(model.predict(values.reshape(1, -1))).reshape(-1)[0])
    contributions = np.zeros(len(values), dtype=float)
    n_features = len(values)

    for feature_idx in range(n_features):
        others = [idx for idx in range(n_features) if idx != feature_idx]
        for coalition_size in range(n_features):
            weight = (
                factorial(coalition_size)
                * factorial(n_features - coalition_size - 1)
                / factorial(n_features)
            )
            for coalition in combinations(others, coalition_size):
                before = baseline.copy()
                if coalition:
                    before[list(coalition)] = values[list(coalition)]
                after = before.copy()
                after[feature_idx] = values[feature_idx]
                pred_before = float(model.predict(before.reshape(1, -1))[0])
                pred_after = float(model.predict(after.reshape(1, -1))[0])
                contributions[feature_idx] += weight * (pred_after - pred_before)

    return raw_prediction, contributions

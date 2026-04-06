from __future__ import annotations

import math


def fastshap_approximation(
    reference_means: dict[str, float],
    current_means: dict[str, float],
    model_weights: dict[str, float],
) -> dict[str, float]:
    """
    Lightweight streaming SHAP-like approximation.

    Attribution is estimated by weighted shift from baseline means,
    normalized with a smooth squashing transform for stability.
    """
    attributions: dict[str, float] = {}
    for feature, baseline in reference_means.items():
        current = current_means.get(feature, baseline)
        weight = model_weights.get(feature, 1.0)
        delta = (current - baseline) * weight
        attributions[feature] = math.tanh(delta)
    return attributions


def top_drift_feature(shap_scores: dict[str, float]) -> str | None:
    if not shap_scores:
        return None
    return max(shap_scores, key=lambda key: abs(shap_scores[key]))

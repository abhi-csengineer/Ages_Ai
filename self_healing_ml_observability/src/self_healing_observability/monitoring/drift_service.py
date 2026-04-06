from __future__ import annotations

from self_healing_observability.monitoring.drift import (
    gaussian_kernel_mmd,
    population_stability_index,
)
from self_healing_observability.monitoring.explainability import (
    fastshap_approximation,
    top_drift_feature,
)
from self_healing_observability.store.duckdb_store import DuckDBFeatureStore


class DriftService:
    def __init__(self, store: DuckDBFeatureStore, min_reference_rows: int = 100) -> None:
        self.store = store
        self.min_reference_rows = min_reference_rows

    def ensure_reference_window(self) -> None:
        if self.store.count_logs("reference") >= self.min_reference_rows:
            return
        if self.store.count_logs("detection") >= self.min_reference_rows:
            self.store.copy_detection_to_reference(max_rows=self.min_reference_rows)

    def drift_score_psi(self) -> float:
        self.ensure_reference_window()
        features = self.store.list_numeric_features("reference")
        if not features:
            return 0.0

        scores: list[float] = []
        for feature in features:
            ref = self.store.feature_distribution("reference", feature)
            cur = self.store.feature_distribution("current", feature)
            if not ref or not cur:
                continue
            scores.append(population_stability_index(ref, cur))

        if not scores:
            return 0.0
        return float(sum(scores) / len(scores))

    def per_feature_psi(self) -> dict[str, float]:
        self.ensure_reference_window()
        result: dict[str, float] = {}
        features = self.store.list_numeric_features("reference")
        for feature in features:
            ref = self.store.feature_distribution("reference", feature)
            cur = self.store.feature_distribution("detection", feature)
            if not ref or not cur:
                continue
            result[feature] = population_stability_index(ref, cur)
        return result

    def drift_score_mmd(self) -> float:
        self.ensure_reference_window()
        ref_embed = self.store.embeddings_matrix("reference")
        det_embed = self.store.embeddings_matrix("detection")
        return gaussian_kernel_mmd(ref_embed, det_embed, sigma=1.0)

    def streaming_shap_top_feature(self, model_weights: dict[str, float] | None = None) -> str | None:
        self.ensure_reference_window()
        reference_means = self.store.feature_mean_map("reference")
        detection_means = self.store.feature_mean_map("detection")
        weights = model_weights if model_weights is not None else {
            key: 1.0 for key in reference_means.keys()
        }
        shap_scores = fastshap_approximation(reference_means, detection_means, weights)
        return top_drift_feature(shap_scores)

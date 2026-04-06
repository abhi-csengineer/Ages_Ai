from __future__ import annotations

from self_healing_observability.monitoring.drift import (
    population_stability_index,
    StreamingApproximateMMD,
)
from self_healing_observability.monitoring.explainability import (
    fastshap_approximation,
    top_drift_feature,
)
from self_healing_observability.store.base import FeatureStore


class DriftService:
    def __init__(self, store: FeatureStore, min_reference_rows: int = 100) -> None:
        self.store = store
        self.min_reference_rows = min_reference_rows
        self._mmd_stream: StreamingApproximateMMD | None = None
        self._stream_ready = False
        self._last_reference_count = -1
        self._last_detection_request_id: str | None = None

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
            cur = self.store.feature_distribution("detection", feature)
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

        reference_count = self.store.count_logs("reference")
        if reference_count <= 0:
            return 0.0

        if (not self._stream_ready) or (reference_count != self._last_reference_count):
            self._bootstrap_streaming_mmd(reference_count)

        # Incremental update for the newest detection point only (O(1) memory growth).
        latest = self.store.detection_records(limit=1)
        if latest:
            request_id = str(latest[0].get("request_id", ""))
            embeddings = latest[0].get("embeddings", [])
            if request_id and request_id != self._last_detection_request_id and embeddings:
                if self._mmd_stream is not None:
                    self._mmd_stream.observe_detection(list(embeddings))
                self._last_detection_request_id = request_id

        if self._mmd_stream is None:
            return 0.0
        return self._mmd_stream.mmd2()

    def _bootstrap_streaming_mmd(self, reference_count: int) -> None:
        # Bounded bootstrap prevents unbounded memory use on long runtimes.
        reference_matrix = self.store.embeddings_matrix("reference", limit=2048)
        detection_matrix = self.store.embeddings_matrix("detection", limit=2048)

        sample = reference_matrix or detection_matrix
        if not sample:
            self._mmd_stream = None
            self._stream_ready = False
            self._last_reference_count = reference_count
            self._last_detection_request_id = None
            return

        input_dim = max(1, len(sample[0]))
        self._mmd_stream = StreamingApproximateMMD(
            input_dim=input_dim,
            pca_components=min(4, input_dim),
            n_rff=64,
            sigma=1.0,
        )

        for row in reference_matrix:
            if row:
                self._mmd_stream.observe_reference(row)
        for row in detection_matrix:
            if row:
                self._mmd_stream.observe_detection(row)

        latest = self.store.detection_records(limit=1)
        self._last_detection_request_id = str(latest[0].get("request_id", "")) if latest else None
        self._last_reference_count = reference_count
        self._stream_ready = True

    def streaming_shap_top_feature(self, model_weights: dict[str, float] | None = None) -> str | None:
        self.ensure_reference_window()
        reference_means = self.store.feature_mean_map("reference")
        detection_means = self.store.feature_mean_map("detection")
        weights = model_weights if model_weights is not None else {
            key: 1.0 for key in reference_means.keys()
        }
        shap_scores = fastshap_approximation(reference_means, detection_means, weights)
        return top_drift_feature(shap_scores)

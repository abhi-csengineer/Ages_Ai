from __future__ import annotations

from typing import Any, Protocol

from self_healing_observability.contracts.schemas import InferenceLog


class FeatureStore(Protocol):
    def insert_log(
        self,
        log: InferenceLog,
        window_type: str,
        confidence: float,
        uncertainty: float,
        latency_ms: float,
    ) -> None: ...

    def list_numeric_features(self, window_type: str) -> list[str]: ...

    def feature_distribution(self, window_type: str, feature_name: str) -> list[float]: ...

    def count_logs(self, window_type: str) -> int: ...

    def detection_records(self, limit: int = 5000) -> list[dict[str, Any]]: ...

    def promote_detection_ids_to_reference(self, request_ids: list[str]) -> int: ...

    def copy_detection_to_reference(self, max_rows: int = 1000) -> int: ...

    def embedding_points(self, window_type: str, limit: int = 250) -> list[dict[str, float | str]]: ...

    def embeddings_matrix(self, window_type: str, limit: int = 4000) -> list[list[float]]: ...

    def feature_mean_map(self, window_type: str) -> dict[str, float]: ...

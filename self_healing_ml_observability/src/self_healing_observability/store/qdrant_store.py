from __future__ import annotations

import uuid
from datetime import datetime, timezone
import importlib
from typing import Any

from self_healing_observability.contracts.schemas import InferenceLog


class QdrantFeatureStore:
    """Qdrant-backed feature store for distributed, multi-instance deployments."""

    def __init__(
        self,
        url: str,
        api_key: str | None = None,
        collection_name: str = "ml_inference_logs",
        vector_size: int = 24,
        detection_window_size: int = 2000,
    ) -> None:
        try:
            qdrant_mod = importlib.import_module("qdrant_client")
            models_mod = importlib.import_module("qdrant_client.http.models")
        except ImportError as exc:
            raise RuntimeError(
                "qdrant-client is required for QdrantFeatureStore. Install with `pip install -r requirements.txt`."
            ) from exc

        self._models = models_mod
        QdrantClient = getattr(qdrant_mod, "QdrantClient")
        self._client = QdrantClient(url=url, api_key=api_key)
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.detection_window_size = detection_window_size

        self._client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=self._models.VectorParams(size=vector_size, distance=self._models.Distance.COSINE),
        )

    @staticmethod
    def _canonical_window(window_type: str) -> str:
        if window_type == "current":
            return "detection"
        return window_type

    def _vectorize(self, embeddings: list[float]) -> list[float]:
        vec = [float(v) for v in embeddings[: self.vector_size]]
        if len(vec) < self.vector_size:
            vec.extend([0.0] * (self.vector_size - len(vec)))
        return vec

    def _window_filter(self, window_type: str):
        window = self._canonical_window(window_type)
        return self._models.Filter(
            must=[
                self._models.FieldCondition(
                    key="window_type",
                    match=self._models.MatchValue(value=window),
                )
            ]
        )

    def _iter_points(self, window_type: str, limit: int = 4000):
        filt = self._window_filter(window_type)
        points: list[Any] = []
        next_offset = None
        while len(points) < limit:
            page_size = min(256, limit - len(points))
            page, next_offset = self._client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filt,
                with_payload=True,
                with_vectors=True,
                limit=page_size,
                offset=next_offset,
            )
            if not page:
                break
            points.extend(page)
            if next_offset is None:
                break
        return points

    def insert_log(
        self,
        log: InferenceLog,
        window_type: str,
        confidence: float,
        uncertainty: float,
        latency_ms: float,
    ) -> None:
        event_ts = log.event_ts if log.event_ts else datetime.now(timezone.utc)
        vector = self._vectorize(log.embeddings)
        window = self._canonical_window(window_type)

        payload = {
            "request_id": log.request_id,
            "event_ts": event_ts.isoformat(),
            "window_type": window,
            "input_features": {k: float(v) for k, v in log.input_features.items() if isinstance(v, (int, float))},
            "softmax_probs": [float(v) for v in log.softmax_probs],
            "confidence": float(confidence),
            "uncertainty": float(uncertainty),
            "latency_ms": float(latency_ms),
            "demographic_group": log.demographic_group,
            "observed_label": int(log.observed_label) if log.observed_label is not None else None,
        }

        point = self._models.PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload)
        self._client.upsert(collection_name=self.collection_name, points=[point], wait=False)

        if window == "detection":
            self._enforce_detection_window_cap()

    def _enforce_detection_window_cap(self) -> None:
        points = self._iter_points("detection", limit=max(self.detection_window_size + 512, 4096))
        if len(points) <= self.detection_window_size:
            return

        def _ts(point: Any) -> str:
            payload = point.payload or {}
            return str(payload.get("event_ts", ""))

        points_sorted = sorted(points, key=_ts, reverse=True)
        stale = points_sorted[self.detection_window_size :]
        stale_ids = [p.id for p in stale]
        if stale_ids:
            self._client.delete(
                collection_name=self.collection_name,
                points_selector=self._models.PointIdsList(points=stale_ids),
                wait=False,
            )

    def list_numeric_features(self, window_type: str) -> list[str]:
        points = self._iter_points(window_type, limit=2000)
        keys: set[str] = set()
        for point in points:
            payload = point.payload or {}
            feats = payload.get("input_features", {})
            if isinstance(feats, dict):
                keys.update(str(k) for k, v in feats.items() if isinstance(v, (int, float)))
        return sorted(keys)

    def feature_distribution(self, window_type: str, feature_name: str) -> list[float]:
        points = self._iter_points(window_type, limit=5000)
        dist: list[float] = []
        for point in points:
            payload = point.payload or {}
            feats = payload.get("input_features", {})
            if isinstance(feats, dict) and feature_name in feats and isinstance(feats[feature_name], (int, float)):
                dist.append(float(feats[feature_name]))
        return dist

    def count_logs(self, window_type: str) -> int:
        result = self._client.count(
            collection_name=self.collection_name,
            count_filter=self._window_filter(window_type),
            exact=False,
        )
        return int(result.count)

    def detection_records(self, limit: int = 5000) -> list[dict[str, Any]]:
        points = self._iter_points("detection", limit=limit)
        records: list[dict[str, Any]] = []
        for point in points:
            payload = point.payload or {}
            records.append(
                {
                    "request_id": str(payload.get("request_id", point.id)),
                    "softmax_probs": list(payload.get("softmax_probs", [])),
                    "embeddings": list(point.vector or []),
                }
            )
        return records

    def _delete_window(self, window_type: str) -> None:
        self._client.delete(
            collection_name=self.collection_name,
            points_selector=self._models.FilterSelector(filter=self._window_filter(window_type)),
            wait=True,
        )

    def promote_detection_ids_to_reference(self, request_ids: list[str]) -> int:
        if not request_ids:
            return 0

        self._delete_window("reference")

        filt = self._models.Filter(
            must=[
                self._models.FieldCondition(
                    key="window_type",
                    match=self._models.MatchValue(value="detection"),
                ),
                self._models.FieldCondition(
                    key="request_id",
                    match=self._models.MatchAny(any=request_ids),
                ),
            ]
        )

        points, _ = self._client.scroll(
            collection_name=self.collection_name,
            scroll_filter=filt,
            with_payload=True,
            with_vectors=True,
            limit=max(len(request_ids), 1),
        )

        promoted: list[Any] = []
        for point in points:
            payload = dict(point.payload or {})
            payload["window_type"] = "reference"
            promoted.append(self._models.PointStruct(id=str(uuid.uuid4()), vector=point.vector, payload=payload))

        if promoted:
            self._client.upsert(collection_name=self.collection_name, points=promoted, wait=True)
        return len(promoted)

    def copy_detection_to_reference(self, max_rows: int = 1000) -> int:
        self._delete_window("reference")

        points = self._iter_points("detection", limit=max_rows)
        if not points:
            return 0

        clones: list[Any] = []
        for point in points:
            payload = dict(point.payload or {})
            payload["window_type"] = "reference"
            clones.append(self._models.PointStruct(id=str(uuid.uuid4()), vector=point.vector, payload=payload))

        self._client.upsert(collection_name=self.collection_name, points=clones, wait=True)
        return len(clones)

    def feature_mean_map(self, window_type: str) -> dict[str, float]:
        points = self._iter_points(window_type, limit=5000)
        sums: dict[str, float] = {}
        counts: dict[str, int] = {}
        for point in points:
            payload = point.payload or {}
            feats = payload.get("input_features", {})
            if not isinstance(feats, dict):
                continue
            for key, value in feats.items():
                if isinstance(value, (int, float)):
                    sums[str(key)] = sums.get(str(key), 0.0) + float(value)
                    counts[str(key)] = counts.get(str(key), 0) + 1

        means: dict[str, float] = {}
        for key, total in sums.items():
            cnt = counts.get(key, 0)
            if cnt > 0:
                means[key] = total / cnt
        return means

    def embeddings_matrix(self, window_type: str, limit: int = 1024) -> list[list[float]]:
        points = self._iter_points(window_type, limit=limit)
        matrix: list[list[float]] = []
        for point in points:
            vector = list(point.vector or [])
            if vector:
                matrix.append([float(v) for v in vector])
        return matrix

    def embedding_points(self, window_type: str, limit: int = 300) -> list[dict[str, float | str]]:
        points = self._iter_points(window_type, limit=limit)
        out: list[dict[str, float | str]] = []
        for point in points:
            vector = list(point.vector or [])
            payload = point.payload or {}
            if not vector:
                continue
            out.append(
                {
                    "request_id": str(payload.get("request_id", point.id)),
                    "x": float(vector[0]),
                    "y": float(vector[1]) if len(vector) > 1 else 0.0,
                }
            )
        return out

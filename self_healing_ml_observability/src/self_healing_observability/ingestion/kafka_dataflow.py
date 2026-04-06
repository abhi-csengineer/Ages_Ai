from __future__ import annotations

import os

from self_healing_observability.ingestion.bytewax_flow import build_kafka_dataflow
from self_healing_observability.monitoring.streaming_stats import StreamingStats
from self_healing_observability.store import DuckDBFeatureStore, FeatureStore, QdrantFeatureStore


def _build_store() -> FeatureStore:
    backend = os.getenv("AEGIS_FEATURE_STORE_BACKEND", "qdrant").strip().lower()
    if backend == "qdrant":
        return QdrantFeatureStore(
            url=os.getenv("AEGIS_QDRANT_URL", "http://localhost:6333"),
            api_key=os.getenv("AEGIS_QDRANT_API_KEY"),
            collection_name=os.getenv("AEGIS_QDRANT_COLLECTION", "ml_inference_logs"),
            vector_size=int(os.getenv("AEGIS_VECTOR_SIZE", "24")),
            detection_window_size=int(os.getenv("AEGIS_DETECTION_WINDOW_SIZE", "20000")),
        )
    return DuckDBFeatureStore(
        db_path=os.getenv("AEGIS_DUCKDB_PATH", ":memory:"),
        detection_window_size=int(os.getenv("AEGIS_DETECTION_WINDOW_SIZE", "20000")),
    )


def create_flow():
    brokers = [v.strip() for v in os.getenv("AEGIS_KAFKA_BROKERS", "localhost:9092").split(",") if v.strip()]
    topics = [v.strip() for v in os.getenv("AEGIS_KAFKA_TOPICS", "inference-logs").split(",") if v.strip()]
    consumer_group = os.getenv("AEGIS_KAFKA_CONSUMER_GROUP", "aegis-bytewax-workers")

    store = _build_store()
    latency_stats = StreamingStats()
    return build_kafka_dataflow(
        brokers=brokers,
        topics=topics,
        consumer_group=consumer_group,
        store=store,
        latency_stats=latency_stats,
    )


flow = create_flow()

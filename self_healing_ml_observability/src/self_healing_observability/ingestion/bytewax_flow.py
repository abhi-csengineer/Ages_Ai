from __future__ import annotations

import json
import importlib
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from self_healing_observability.contracts.schemas import InferenceLog
from self_healing_observability.monitoring.no_label import (
    normalized_confidence,
    normalized_uncertainty,
)
from self_healing_observability.monitoring.streaming_stats import StreamingStats
from self_healing_observability.store.duckdb_store import DuckDBFeatureStore


class JsonLogSource:
    """Simple in-memory record holder for constructing a Bytewax source."""

    def __init__(self, records: Iterable[str]) -> None:
        self.records = list(records)


def parse_inference_log(raw: str) -> InferenceLog:
    data = json.loads(raw)
    if "event_ts" not in data:
        data["event_ts"] = datetime.now(timezone.utc).isoformat()
    if "model_b_probs" not in data:
        data["model_b_probs"] = data.get("softmax_probs", [])
    return InferenceLog.model_validate(data)


def build_dataflow(
    source: JsonLogSource,
    store: DuckDBFeatureStore,
    latency_stats: StreamingStats,
) -> Any:
    """
    Build Bytewax flow for ingestion -> validation -> feature-store persistence.
    """
    try:
        dataflow_mod = importlib.import_module("bytewax.dataflow")
        inputs_mod = importlib.import_module("bytewax.inputs")
        operators_mod = importlib.import_module("bytewax.operators")
    except ImportError as exc:
        raise RuntimeError(
            "bytewax is required to build the ingestion dataflow. Install dependencies with `pip install -r requirements.txt`."
        ) from exc

    Dataflow = getattr(dataflow_mod, "Dataflow")
    TestingSource = getattr(inputs_mod, "TestingSource")
    op = operators_mod

    flow = Dataflow("inference_log_ingestion")

    stream = op.input("source", flow, TestingSource(source.records))
    parsed = op.map("parse-json", stream, parse_inference_log)

    def persist(log: InferenceLog) -> InferenceLog:
        confidence = normalized_confidence(log.softmax_probs)
        uncertainty = normalized_uncertainty(log.softmax_probs)

        # Update streaming latency estimate if present in input_features.
        latency_val = log.input_features.get("latency_ms", 0.0)
        latency = float(latency_val) if isinstance(latency_val, (int, float)) else 0.0
        latency_stats.update(latency)

        store.insert_log(
            log=log,
            window_type="detection",
            confidence=confidence,
            uncertainty=uncertainty,
            latency_ms=latency,
        )
        return log

    _persisted = op.map("persist-to-duckdb", parsed, persist)
    return flow

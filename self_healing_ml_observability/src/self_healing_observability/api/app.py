from __future__ import annotations

import asyncio
import importlib
import os
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from self_healing_observability.api.middleware import MLCircuitBreakerMiddleware
from self_healing_observability.api.security_middleware import SecuritySidecarMiddleware
from self_healing_observability.contracts.schemas import (
    ActiveLearningQueueItem,
    ActiveLearningQueueResponse,
    ActiveLearningCandidateItem,
    ActiveLearningCandidatesResponse,
    EmbeddingPoint,
    EmbeddingPointsResponse,
    EmbeddingSnapshotResponse,
    FaithfulnessRequest,
    FaithfulnessResponse,
    GeminiInferenceRequest,
    GeminiInferenceResponse,
    HealerCollectRequest,
    HealerCollectResponse,
    InferenceLog,
    InferenceRequest,
    InferenceResponse,
    LiveTelemetryPayload,
    RetrainWebhookRequest,
    RetrainWebhookResponse,
    TelemetrySnapshot,
)
from self_healing_observability.core.circuit_breaker import MLCircuitBreaker
from self_healing_observability.core.circuit_cache import (
    InMemoryCircuitStateCache,
    RedisCircuitStateCache,
)
from self_healing_observability.core.incident_notifier import IncidentContext, IncidentEvent, notify_incident
from self_healing_observability.core.metrics import (
    ACTIVE_LEARNING_CANDIDATE_GAUGE,
    ACTIVE_LEARNING_DATA_EFFICIENCY_GAUGE,
    ACTIVE_LEARNING_DIVERSITY_GAUGE,
    ACTIVE_LEARNING_SELECTED_GAUGE,
    CIRCUIT_CRITICAL_DRIFT_STREAK_GAUGE,
    CIRCUIT_STATE_GAUGE,
    CIRCUIT_STATUS_GAUGE,
    HUI_WALTER_ESTIMATED_ACCURACY_GAUGE,
    NORMALIZED_CONFIDENCE_GAUGE,
    NORMALIZED_UNCERTAINTY_GAUGE,
    TOP_DRIFT_FEATURE_GAUGE,
    metrics_content_type,
    metrics_payload,
    publish_embedding_projection,
)
from self_healing_observability.monitoring.bias import BiasMonitor
from self_healing_observability.monitoring.drift_service import DriftService
from self_healing_observability.monitoring.no_label import (
    HuiWalterTracker,
    normalized_confidence,
    normalized_uncertainty,
)
from self_healing_observability.monitoring.active_learning import (
    DetectionRecord,
    SampleSelector,
    combined_uncertainty_score,
)
from self_healing_observability.monitoring.faithfulness import FaithfulnessScorer
from self_healing_observability.monitoring.security import PromptInjectionDetector
from self_healing_observability.monitoring.streaming_stats import StreamingStats
from self_healing_observability.store.retraining_bucket import RetrainingBucketStore
from self_healing_observability.store import DuckDBFeatureStore, FeatureStore, QdrantFeatureStore

N_CLASSES = 3

app = FastAPI(title="Self-Healing ML Observability System", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_store() -> FeatureStore:
    backend = os.getenv("AEGIS_FEATURE_STORE_BACKEND", "duckdb").strip().lower()
    if backend == "qdrant":
        qdrant_url = os.getenv("AEGIS_QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = os.getenv("AEGIS_QDRANT_API_KEY")
        collection = os.getenv("AEGIS_QDRANT_COLLECTION", "ml_inference_logs")
        vector_size = int(os.getenv("AEGIS_VECTOR_SIZE", "24"))
        detection_window_size = int(os.getenv("AEGIS_DETECTION_WINDOW_SIZE", "2000"))
        return QdrantFeatureStore(
            url=qdrant_url,
            api_key=qdrant_api_key,
            collection_name=collection,
            vector_size=vector_size,
            detection_window_size=detection_window_size,
        )

    db_path = os.getenv("AEGIS_DUCKDB_PATH", ":memory:")
    detection_window_size = int(os.getenv("AEGIS_DETECTION_WINDOW_SIZE", "2000"))
    return DuckDBFeatureStore(db_path=db_path, detection_window_size=detection_window_size)


def _build_circuit_cache():
    redis_url = os.getenv("AEGIS_REDIS_URL", "").strip()
    if redis_url:
        return RedisCircuitStateCache(redis_url=redis_url, key=os.getenv("AEGIS_REDIS_CIRCUIT_KEY", "aegis:circuit:state"))
    return InMemoryCircuitStateCache()


store = _build_store()
drift_service = DriftService(store=store, min_reference_rows=25)
circuit_breaker = MLCircuitBreaker(drift_threshold=0.25, bias_threshold=0.35, cache=_build_circuit_cache())
hui_walter_tracker = HuiWalterTracker()
bias_monitor = BiasMonitor(disparate_impact_threshold=0.8, equalized_odds_threshold=0.25)
sample_selector = SampleSelector(entropy_weight=0.6)
security_detector = PromptInjectionDetector(semantic_threshold=0.75)
faithfulness_scorer = FaithfulnessScorer()

latency_stats = StreamingStats()
psi_stats = StreamingStats()
mmd_stats = StreamingStats()
bias_stats = StreamingStats()

_last_top_feature: str | None = None

HUI_WALTER_ESTIMATED_ACCURACY_GAUGE.set(1.0)


class TelemetryWebSocketManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self._connections.discard(ws)


telemetry_manager = TelemetryWebSocketManager()
_bytewax_sidecar_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=4096)
_proxy_interactions: dict[str, dict[str, Any]] = {}
_umap_bounds = {
    "min_x": float("inf"),
    "max_x": float("-inf"),
    "min_y": float("inf"),
    "max_y": float("-inf"),
}
_embedding_model: Any = None
_gemini_model: Any = None
_gemini_model_name: str | None = None
retraining_bucket = RetrainingBucketStore(db_path=os.getenv("AEGIS_HEALER_DB_PATH", "healer_retraining_bucket.duckdb"))


def _publish_embedding_metrics() -> None:
    reference_points = store.embedding_points("reference", limit=250)
    live_points = store.embedding_points("detection", limit=250)
    publish_embedding_projection(reference_points=reference_points, live_points=live_points)


def _build_telemetry_snapshot(*, batch_event: bool = False) -> TelemetrySnapshot:
    hui_snapshot = hui_walter_tracker.estimate_error_rates()
    hui_accuracy = float(
        hui_snapshot.get("bayesian", {})
        .get("estimated", {})
        .get("accuracy_model_a", hui_snapshot.get("estimated", {}).get("accuracy_model_a", 0.0))
    )
    status = circuit_breaker.status.value
    return TelemetrySnapshot(
        circuit_state=circuit_breaker.state.value,
        circuit_status=status,
        hui_walter_estimated_accuracy=hui_accuracy,
        psi_drift_score=float(circuit_breaker.last_psi_score),
        mmd_drift_score=float(circuit_breaker.last_mmd_score),
        bias_score=float(circuit_breaker.last_bias_score),
        reference_count=int(store.count_logs("reference")),
        detection_count=int(store.count_logs("detection")),
        batch_event=batch_event,
        chaos_active=status in {"DRIFT_BIAS", "FALLBACK_MODE"},
    )


def _status_flag(*, psi_score: float, mmd_score: float, circuit_status: str) -> str:
    if circuit_status == "SECURITY_ATTACK":
        return "ATTACK"
    if circuit_status in {"DRIFT_BIAS", "FALLBACK_MODE"} or psi_score > 0.25 or mmd_score > 0.25:
        return "DRIFT"
    return "OK"


def _normalize_umap(embedding: list[float]) -> tuple[float, float]:
    x_raw = float(embedding[0]) if len(embedding) > 0 else 0.0
    y_raw = float(embedding[1]) if len(embedding) > 1 else 0.0

    _umap_bounds["min_x"] = min(_umap_bounds["min_x"], x_raw)
    _umap_bounds["max_x"] = max(_umap_bounds["max_x"], x_raw)
    _umap_bounds["min_y"] = min(_umap_bounds["min_y"], y_raw)
    _umap_bounds["max_y"] = max(_umap_bounds["max_y"], y_raw)

    span_x = max(_umap_bounds["max_x"] - _umap_bounds["min_x"], 1e-9)
    span_y = max(_umap_bounds["max_y"] - _umap_bounds["min_y"], 1e-9)
    x = (x_raw - _umap_bounds["min_x"]) / span_x
    y = (y_raw - _umap_bounds["min_y"]) / span_y
    return max(0.0, min(1.0, x)), max(0.0, min(1.0, y))


def _embedding_softmax(embedding: list[float]) -> list[float]:
    if not embedding:
        return [0.34, 0.33, 0.33]
    vec = np.asarray(embedding[:3], dtype=float)
    if vec.shape[0] < 3:
        vec = np.pad(vec, (0, 3 - vec.shape[0]))
    vec = np.tanh(vec)
    ex = np.exp(vec - np.max(vec))
    probs = ex / np.sum(ex)
    return [float(v) for v in probs]


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        sentence_mod = importlib.import_module("sentence_transformers")
        SentenceTransformer = getattr(sentence_mod, "SentenceTransformer")
        _embedding_model = SentenceTransformer(os.getenv("AEGIS_SENTENCE_MODEL", "all-MiniLM-L6-v2"))
    return _embedding_model


def _embed_text(text: str) -> list[float]:
    model = _get_embedding_model()
    vector = model.encode(text, normalize_embeddings=True)
    return [float(v) for v in vector.tolist()]


def _get_gemini_model():
    global _gemini_model, _gemini_model_name
    if _gemini_model is None:
        genai = importlib.import_module("google.generativeai")

        api_key = os.getenv("GOOGLE_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is not configured.")
        genai.configure(api_key=api_key)
        _gemini_model_name = os.getenv("AEGIS_GEMINI_MODEL", "gemini-1.5-flash-latest")
        _gemini_model = genai.GenerativeModel(_gemini_model_name)
    return _gemini_model


def _gemini_generate(prompt: str) -> str:
    global _gemini_model, _gemini_model_name
    model = _get_gemini_model()
    try:
        response = model.generate_content(prompt)
    except Exception as exc:
        msg = str(exc)
        if "not found" in msg.lower() or "not supported" in msg.lower():
            genai = importlib.import_module("google.generativeai")
            fallback_names = []
            try:
                for m in genai.list_models():
                    methods = set(getattr(m, "supported_generation_methods", []) or [])
                    name = str(getattr(m, "name", ""))
                    if "generateContent" in methods and name:
                        normalized = name.replace("models/", "")
                        fallback_names.append(normalized)
            except Exception:
                # Keep static fallbacks if model listing is unavailable.
                pass

            if not fallback_names:
                fallback_names = [
                    "gemini-1.5-flash-latest",
                    "gemini-1.5-flash-001",
                    "gemini-2.0-flash",
                ]

            # Prefer flash-class models if available.
            fallback_names = sorted(
                set(fallback_names),
                key=lambda n: ("flash" not in n.lower(), n),
            )
            for candidate in fallback_names:
                try:
                    model = genai.GenerativeModel(candidate)
                    response = model.generate_content(prompt)
                    _gemini_model = model
                    _gemini_model_name = candidate
                    break
                except Exception:
                    continue
            else:
                raise
        else:
            raise
    text = getattr(response, "text", "") or ""
    return str(text).strip() or "No response generated."


async def _bytewax_sidecar_worker() -> None:
    # Proxy-sidecar bridge: captures Gemini interactions for Bytewax-compatible stream processing.
    while True:
        _ = await _bytewax_sidecar_queue.get()
        _bytewax_sidecar_queue.task_done()


@app.on_event("startup")
async def _startup_tasks() -> None:
    asyncio.create_task(_bytewax_sidecar_worker())


async def fallback_inference(payload: dict[str, Any]) -> dict[str, Any]:
    features = payload.get("input_features", {})
    score = float(features.get("risk_score", 0.0))
    pred = 1 if score >= 0.5 else 0
    probs = [0.8, 0.2, 0.0] if pred == 0 else [0.2, 0.8, 0.0]
    confidence = normalized_confidence(probs)
    uncertainty = normalized_uncertainty(probs)
    return {
        "request_id": payload.get("request_id", "unknown"),
        "source": "fallback",
        "predicted_class": pred,
        "softmax_probs": probs,
        "confidence": confidence,
        "uncertainty": uncertainty,
        "psi_drift_score": circuit_breaker.last_psi_score,
        "mmd_drift_score": circuit_breaker.last_mmd_score,
        "bias_score": circuit_breaker.last_bias_score,
        "top_drift_feature": None,
        "circuit_state": circuit_breaker.state.value,
        "circuit_status": circuit_breaker.status.value,
    }


def _combined_drift_scores() -> tuple[float, float]:
    psi = drift_service.drift_score_psi()
    mmd = drift_service.drift_score_mmd()
    psi_stats.update(psi)
    mmd_stats.update(mmd)
    return psi, mmd


def _bias_score() -> float:
    score = bias_monitor.bias_score()
    bias_stats.update(score)
    return score


def _apply_reference_refresh(action: str) -> RetrainWebhookResponse:
    candidate_rows = store.detection_records(limit=5000)
    candidates = [
        DetectionRecord(
            request_id=str(row["request_id"]),
            softmax_probs=row["softmax_probs"],
            embeddings=row["embeddings"],
        )
        for row in candidate_rows
    ]

    selected = sample_selector.select_retraining_batch(
        records=candidates,
        budget_ratio=0.1,
        prefilter_multiplier=5,
    )
    selected_ids = [record.request_id for record in selected]
    promoted = store.promote_detection_ids_to_reference(selected_ids)

    total_candidates = len(candidates)
    selected_count = len(selected)
    efficiency = (selected_count / total_candidates) if total_candidates > 0 else 0.0

    summary = sample_selector.last_curation_summary
    ACTIVE_LEARNING_CANDIDATE_GAUGE.set(float(summary.candidate_rows))
    ACTIVE_LEARNING_SELECTED_GAUGE.set(float(summary.selected_rows))
    ACTIVE_LEARNING_DATA_EFFICIENCY_GAUGE.set(summary.achieved_efficiency_ratio)
    ACTIVE_LEARNING_DIVERSITY_GAUGE.set(summary.diversity_score)

    psi_stats.reset()
    mmd_stats.reset()
    bias_stats.reset()
    security_detector.reset_counters()
    circuit_breaker.reset()
    CIRCUIT_STATE_GAUGE.set(0)
    CIRCUIT_CRITICAL_DRIFT_STREAK_GAUGE.set(0)
    for status_name in ("OK", "DRIFT_BIAS", "SECURITY_ATTACK", "FALLBACK_MODE"):
        CIRCUIT_STATUS_GAUGE.labels(status=status_name).set(1 if status_name == "OK" else 0)
    _publish_embedding_metrics()

    return RetrainWebhookResponse(
        accepted=True,
        action=action,
        promoted_rows=promoted,
        selected_rows=selected_count,
        candidate_rows=total_candidates,
        data_efficiency_ratio=efficiency,
    )


async def _auto_heal_handler() -> bool:
    result = _apply_reference_refresh(action="autonomous_drift_heal")
    return result.promoted_rows > 0


async def _latch_alert_handler() -> None:
    event = IncidentEvent(
        source="ml_circuit_breaker",
        severity="critical",
        title="Aegis latching fallback mode engaged",
        message="Critical drift exceeded threshold for three consecutive windows. System locked in FALLBACK_MODE.",
        context=IncidentContext(
            psi_score=circuit_breaker.last_psi_score,
            mmd_score=circuit_breaker.last_mmd_score,
            bias_score=circuit_breaker.last_bias_score,
            critical_streak=circuit_breaker.consecutive_critical_drift_windows,
            status=circuit_breaker.status.value,
        ),
    )
    await asyncio.to_thread(notify_incident, event)


app.add_middleware(
    MLCircuitBreakerMiddleware,
    circuit_breaker=circuit_breaker,
    drift_score_provider=_combined_drift_scores,
    bias_score_provider=_bias_score,
    fallback_handler=fallback_inference,
    auto_heal_handler=_auto_heal_handler,
    latch_alert_handler=_latch_alert_handler,
    auto_heal_cooldown_seconds=float(os.getenv("AEGIS_AUTO_HEAL_COOLDOWN_S", "30")),
)

app.add_middleware(
    SecuritySidecarMiddleware,
    circuit_breaker=circuit_breaker,
    detector=security_detector,
    fallback_handler=fallback_inference,
    grpc_target=os.getenv("AEGIS_SIDECAR_GRPC_TARGET", ""),
    sidecar_timeout_seconds=float(os.getenv("AEGIS_SIDECAR_TIMEOUT_S", "0.02")),
)


def _mock_model_predict(features: dict[str, float]) -> list[float]:
    # Deterministic toy model for framework demonstration.
    weighted_sum = sum(features.values())
    p1 = max(0.0, min(1.0, 1.0 / (1.0 + (2.71828 ** (-weighted_sum)))))
    p2 = max(0.0, min(1.0, 0.6 * (1.0 - p1)))
    p3 = max(0.0, 1.0 - (p1 + p2))
    probs = [p1, p2, p3]
    total = sum(probs)
    return [p / total for p in probs] if total > 0 else [1.0 / N_CLASSES] * N_CLASSES


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=metrics_payload(), media_type=metrics_content_type())


@app.websocket("/ws/telemetry")
async def telemetry_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    last_detection_count = -1
    try:
        while True:
            detection_count = int(store.count_logs("detection"))
            batch_event = detection_count > last_detection_count
            snapshot = _build_telemetry_snapshot(batch_event=batch_event)
            await websocket.send_json(snapshot.model_dump(mode="json"))
            last_detection_count = detection_count
            await asyncio.sleep(0.75)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/live-telemetry")
async def live_telemetry_socket(websocket: WebSocket) -> None:
    await telemetry_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        telemetry_manager.disconnect(websocket)
    except Exception:
        telemetry_manager.disconnect(websocket)


@app.post("/predict", response_model=InferenceResponse)
async def predict(request: InferenceRequest) -> InferenceResponse:
    probs = _mock_model_predict(request.input_features)
    model_b_probs = list(reversed(probs))
    confidence = normalized_confidence(probs)
    uncertainty = normalized_uncertainty(probs)

    NORMALIZED_CONFIDENCE_GAUGE.set(confidence)
    NORMALIZED_UNCERTAINTY_GAUGE.set(uncertainty)

    predicted_class = int(max(range(len(probs)), key=lambda i: probs[i]))

    log = InferenceLog(
        request_id=request.request_id,
        event_ts=datetime.now(timezone.utc),
        input_features=request.input_features,
        embeddings=request.embeddings,
        softmax_probs=probs,
        model_b_probs=model_b_probs,
        population_id=request.population_id,
        demographic_group=request.demographic_group,
        observed_label=request.observed_label,
    )
    latency_ms = float(request.input_features.get("latency_ms", 0.0))
    latency_stats.update(latency_ms)

    store.insert_log(
        log=log,
        window_type="detection",
        confidence=confidence,
        uncertainty=uncertainty,
        latency_ms=latency_ms,
    )
    _publish_embedding_metrics()

    model_b_positive = model_b_probs[1] >= 0.5 if len(model_b_probs) > 1 else False
    hui_walter_tracker.update(
        population=request.population_id,
        model_a_positive=(predicted_class == 1),
        model_b_positive=model_b_positive,
    )
    hui_snapshot = hui_walter_tracker.estimate_error_rates()
    hui_accuracy = float(
        hui_snapshot.get("bayesian", {})
        .get("estimated", {})
        .get("accuracy_model_a", hui_snapshot.get("estimated", {}).get("accuracy_model_a", 0.0))
    )
    HUI_WALTER_ESTIMATED_ACCURACY_GAUGE.set(hui_accuracy)

    bias_monitor.update(
        group=request.demographic_group,
        prediction_positive=(predicted_class == 1),
        observed_label=request.observed_label,
    )

    psi_score, mmd_score = _combined_drift_scores()
    current_bias_score = _bias_score()

    top_feature: str | None = None
    if psi_score > 0.25 or mmd_score > 0.25:
        top_feature = drift_service.streaming_shap_top_feature(model_weights=request.input_features)

    global _last_top_feature
    if _last_top_feature and _last_top_feature != top_feature:
        TOP_DRIFT_FEATURE_GAUGE.labels(feature=_last_top_feature).set(0.0)
    if top_feature:
        TOP_DRIFT_FEATURE_GAUGE.labels(feature=top_feature).set(1.0)
    _last_top_feature = top_feature

    return InferenceResponse(
        request_id=request.request_id,
        source="model",
        predicted_class=predicted_class,
        softmax_probs=probs,
        confidence=confidence,
        uncertainty=uncertainty,
        psi_drift_score=psi_score,
        mmd_drift_score=mmd_score,
        bias_score=current_bias_score,
        top_drift_feature=top_feature,
        circuit_state=circuit_breaker.state.value,
        circuit_status=circuit_breaker.status.value,
    )


@app.get("/hui-walter")
async def hui_walter_snapshot() -> dict[str, object]:
    return hui_walter_tracker.estimate_error_rates()


@app.post("/retrain", response_model=RetrainWebhookResponse)
async def retrain_webhook(payload: RetrainWebhookRequest) -> RetrainWebhookResponse:
    should_retrain = any(
        alert.status == "firing"
        and alert.labels.alertname.lower() in {"driftalert", "biasalert", "securityalert"}
        for alert in payload.alerts
    )
    if not should_retrain:
        return RetrainWebhookResponse(
            accepted=True,
            action="noop",
            promoted_rows=0,
            selected_rows=0,
            candidate_rows=0,
            data_efficiency_ratio=0.0,
        )
    return _apply_reference_refresh(action="active_learning_reference_refresh")


@app.get("/active-learning/queue", response_model=ActiveLearningQueueResponse)
async def active_learning_queue(top_k: int = 5, candidate_limit: int = 500) -> ActiveLearningQueueResponse:
    rows = store.detection_records(limit=max(top_k, candidate_limit))
    records = [
        DetectionRecord(
            request_id=str(row["request_id"]),
            softmax_probs=row["softmax_probs"],
            embeddings=row["embeddings"],
        )
        for row in rows
    ]
    ranked = sample_selector.rank_by_uncertainty(records)
    items = [
        ActiveLearningQueueItem(
            request_id=rec.request_id,
            uncertainty_score=combined_uncertainty_score(rec.softmax_probs, sample_selector.entropy_weight),
        )
        for rec in ranked[: max(1, top_k)]
    ]
    return ActiveLearningQueueResponse(items=items)


@app.get("/active-learning/candidates", response_model=ActiveLearningCandidatesResponse)
async def active_learning_candidates(limit: int = 50) -> ActiveLearningCandidatesResponse:
    rows = store.detection_records(limit=max(1, limit))
    items = [
        ActiveLearningCandidateItem(
            request_id=str(row["request_id"]),
            confidence=normalized_confidence(row["softmax_probs"]),
            uncertainty=normalized_uncertainty(row["softmax_probs"]),
        )
        for row in rows
    ]
    items.sort(key=lambda x: x.uncertainty, reverse=True)
    return ActiveLearningCandidatesResponse(items=items)


@app.get("/embedding-snapshot", response_model=EmbeddingSnapshotResponse)
async def embedding_snapshot(limit: int = 400) -> EmbeddingSnapshotResponse:
    return EmbeddingSnapshotResponse(
        reference=store.embeddings_matrix("reference", limit=limit),
        detection=store.embeddings_matrix("detection", limit=limit),
    )


@app.get("/embedding-points", response_model=EmbeddingPointsResponse)
async def embedding_points(limit: int = 400) -> EmbeddingPointsResponse:
    reference_points = store.embedding_points("reference", limit=limit)
    live_points = store.embedding_points("detection", limit=limit)

    detection_rows = store.detection_records(limit=limit * 2)
    uncertainty_by_request_id = {
        str(row["request_id"]): normalized_uncertainty(row.get("softmax_probs", []))
        for row in detection_rows
    }

    points: list[EmbeddingPoint] = []
    for p in reference_points:
        points.append(
            EmbeddingPoint(
                request_id=str(p["request_id"]),
                source="reference",
                x=float(p["x"]),
                y=float(p["y"]),
                uncertainty=0.0,
            )
        )
    for p in live_points:
        request_id = str(p["request_id"])
        points.append(
            EmbeddingPoint(
                request_id=request_id,
                source="live",
                x=float(p["x"]),
                y=float(p["y"]),
                uncertainty=float(uncertainty_by_request_id.get(request_id, 0.0)),
            )
        )

    return EmbeddingPointsResponse(points=points)


@app.post("/faithfulness/score", response_model=FaithfulnessResponse)
async def faithfulness_score(payload: FaithfulnessRequest) -> FaithfulnessResponse:
    score = faithfulness_scorer.score(context=payload.context, answer=payload.answer)
    return FaithfulnessResponse(score=score, model_name=faithfulness_scorer.model_name)


@app.post("/api/v1/inference/gemini", response_model=GeminiInferenceResponse)
async def gemini_inference(payload: GeminiInferenceRequest) -> GeminiInferenceResponse:
    request_id = payload.request_id or str(uuid.uuid4())
    try:
        response_text = await asyncio.to_thread(_gemini_generate, payload.prompt)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"gemini_proxy_unavailable:{exc}") from exc

    try:
        embedding = await asyncio.to_thread(_embed_text, f"{payload.prompt}\n{response_text}")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"embedding_sidecar_unavailable:{exc}") from exc

    softmax_probs = _embedding_softmax(embedding)
    model_b_probs = list(reversed(softmax_probs))
    confidence = normalized_confidence(softmax_probs)
    uncertainty = normalized_uncertainty(softmax_probs)

    log = InferenceLog(
        request_id=request_id,
        event_ts=datetime.now(timezone.utc),
        input_features={
            "prompt_char_len": float(len(payload.prompt)),
            "response_char_len": float(len(response_text)),
            "semantic_energy": float(np.linalg.norm(np.asarray(embedding[:8], dtype=float))),
        },
        embeddings=embedding,
        softmax_probs=softmax_probs,
        model_b_probs=model_b_probs,
        population_id=payload.population_id,
        demographic_group=payload.demographic_group,
        observed_label=None,
    )
    store.insert_log(
        log=log,
        window_type="detection",
        confidence=confidence,
        uncertainty=uncertainty,
        latency_ms=0.0,
    )
    _publish_embedding_metrics()

    hui_walter_tracker.update(
        population=payload.population_id,
        model_a_positive=(softmax_probs[1] >= 0.5),
        model_b_positive=(model_b_probs[1] >= 0.5),
    )
    hui_snapshot = hui_walter_tracker.estimate_error_rates()
    hui_accuracy = float(
        hui_snapshot.get("bayesian", {})
        .get("estimated", {})
        .get("accuracy_model_a", hui_snapshot.get("estimated", {}).get("accuracy_model_a", 0.0))
    )
    HUI_WALTER_ESTIMATED_ACCURACY_GAUGE.set(hui_accuracy)

    psi_score, mmd_score = _combined_drift_scores()
    status = _status_flag(psi_score=psi_score, mmd_score=mmd_score, circuit_status=circuit_breaker.status.value)
    umap_x, umap_y = _normalize_umap(embedding)

    live_payload = LiveTelemetryPayload(
        request_id=request_id,
        status=status,
        accuracy=hui_accuracy,
        drift_magnitude=mmd_score,
        umap_x=umap_x,
        umap_y=umap_y,
    )
    await telemetry_manager.broadcast(live_payload.model_dump(mode="json"))

    interaction = {
        "request_id": request_id,
        "prompt": payload.prompt,
        "response_text": response_text,
        "status": status,
        "mmd_drift_score": mmd_score,
        "accuracy": hui_accuracy,
        "embedding": embedding,
        "metadata": {
            "provider_model": os.getenv("AEGIS_GEMINI_MODEL", "gemini-1.5-flash"),
            "population_id": payload.population_id,
            "demographic_group": payload.demographic_group,
            "umap_x": umap_x,
            "umap_y": umap_y,
        },
    }
    _proxy_interactions[request_id] = interaction
    if _bytewax_sidecar_queue.qsize() < 4000:
        await _bytewax_sidecar_queue.put(interaction)

    return GeminiInferenceResponse(
        request_id=request_id,
        prompt=payload.prompt,
        response_text=response_text,
        provider_model=os.getenv("AEGIS_GEMINI_MODEL", "gemini-1.5-flash"),
        mmd_drift_score=mmd_score,
        hui_walter_estimated_accuracy=hui_accuracy,
        status=status,
        umap_x=umap_x,
        umap_y=umap_y,
    )


@app.post("/api/v1/healer/collect", response_model=HealerCollectResponse)
async def healer_collect(payload: HealerCollectRequest) -> HealerCollectResponse:
    if payload.request_ids:
        rows = [
            _proxy_interactions[rid]
            for rid in payload.request_ids
            if rid in _proxy_interactions and _proxy_interactions[rid].get("status") == "DRIFT"
        ]
    else:
        rows = [row for row in _proxy_interactions.values() if row.get("status") == "DRIFT"]

    stored_rows = await asyncio.to_thread(retraining_bucket.insert_rows, rows)
    return HealerCollectResponse(accepted=True, stored_rows=stored_rows)

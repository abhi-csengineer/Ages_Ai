from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from fastapi.responses import Response

from self_healing_observability.api.middleware import MLCircuitBreakerMiddleware
from self_healing_observability.api.security_middleware import SecuritySidecarMiddleware
from self_healing_observability.contracts.schemas import (
    ActiveLearningQueueItem,
    ActiveLearningQueueResponse,
    EmbeddingSnapshotResponse,
    FaithfulnessRequest,
    FaithfulnessResponse,
    InferenceLog,
    InferenceRequest,
    InferenceResponse,
    RetrainWebhookRequest,
    RetrainWebhookResponse,
)
from self_healing_observability.core.circuit_breaker import MLCircuitBreaker
from self_healing_observability.core.metrics import (
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
from self_healing_observability.store.duckdb_store import DuckDBFeatureStore

N_CLASSES = 3

app = FastAPI(title="Self-Healing ML Observability System", version="0.1.0")
store = DuckDBFeatureStore(db_path=":memory:")
drift_service = DriftService(store=store, min_reference_rows=25)
circuit_breaker = MLCircuitBreaker(drift_threshold=0.25, bias_threshold=0.35)
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


def _publish_embedding_metrics() -> None:
    reference_points = store.embedding_points("reference", limit=250)
    live_points = store.embedding_points("detection", limit=250)
    publish_embedding_projection(reference_points=reference_points, live_points=live_points)


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


app.add_middleware(
    MLCircuitBreakerMiddleware,
    circuit_breaker=circuit_breaker,
    drift_score_provider=_combined_drift_scores,
    bias_score_provider=_bias_score,
    fallback_handler=fallback_inference,
)

app.add_middleware(
    SecuritySidecarMiddleware,
    circuit_breaker=circuit_breaker,
    detector=security_detector,
    fallback_handler=fallback_inference,
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
    hui_accuracy = float(hui_snapshot.get("estimated", {}).get("accuracy_model_a", 0.0))
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

    psi_stats.reset()
    mmd_stats.reset()
    bias_stats.reset()
    security_detector.reset_counters()
    circuit_breaker.reset()
    CIRCUIT_STATE_GAUGE.set(0)
    for status_name in ("OK", "DRIFT_BIAS", "SECURITY_ATTACK"):
        CIRCUIT_STATUS_GAUGE.labels(status=status_name).set(1 if status_name == "OK" else 0)
    _publish_embedding_metrics()

    return RetrainWebhookResponse(
        accepted=True,
        action="active_learning_reference_refresh",
        promoted_rows=promoted,
        selected_rows=selected_count,
        candidate_rows=total_candidates,
        data_efficiency_ratio=efficiency,
    )


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


@app.get("/embedding-snapshot", response_model=EmbeddingSnapshotResponse)
async def embedding_snapshot(limit: int = 400) -> EmbeddingSnapshotResponse:
    return EmbeddingSnapshotResponse(
        reference=store.embeddings_matrix("reference", limit=limit),
        detection=store.embeddings_matrix("detection", limit=limit),
    )


@app.post("/faithfulness/score", response_model=FaithfulnessResponse)
async def faithfulness_score(payload: FaithfulnessRequest) -> FaithfulnessResponse:
    score = faithfulness_scorer.score(context=payload.context, answer=payload.answer)
    return FaithfulnessResponse(score=score, model_name=faithfulness_scorer.model_name)

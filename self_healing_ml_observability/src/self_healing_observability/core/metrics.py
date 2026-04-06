from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

_embedding_label_cache: set[tuple[str, str]] = set()

DRIFT_SCORE_GAUGE = Gauge(
    "ml_drift_score",
    "Current drift score for online model monitoring.",
    labelnames=("method",),
)

BIAS_SCORE_GAUGE = Gauge(
    "ml_bias_score",
    "Composite bias score from disparate impact and equalized odds.",
)

TOP_DRIFT_FEATURE_GAUGE = Gauge(
    "ml_top_drift_feature_score",
    "One-hot marker for top drift feature attribution.",
    labelnames=("feature",),
)

NORMALIZED_CONFIDENCE_GAUGE = Gauge(
    "ml_normalized_confidence",
    "Normalized confidence based on softmax maxima.",
)

NORMALIZED_UNCERTAINTY_GAUGE = Gauge(
    "ml_normalized_uncertainty",
    "Normalized uncertainty based on class-probability spread.",
)

CIRCUIT_STATE_GAUGE = Gauge(
    "ml_circuit_breaker_open",
    "Circuit breaker state: 1=open, 0=closed.",
)

CIRCUIT_STATUS_GAUGE = Gauge(
    "ml_circuit_status",
    "Circuit breaker status by reason category.",
    labelnames=("status",),
)

CIRCUIT_CRITICAL_DRIFT_STREAK_GAUGE = Gauge(
    "ml_circuit_critical_drift_streak",
    "Consecutive windows above critical drift threshold.",
)

CIRCUIT_LATCH_TRIGGER_COUNTER = Counter(
    "ml_circuit_latch_trigger_total",
    "Total number of times the breaker latched into fallback mode.",
)

AUTO_HEAL_TRIGGER_COUNTER = Counter(
    "ml_auto_heal_trigger_total",
    "Autonomous healing trigger events.",
    labelnames=("result",),
)

INCIDENT_ALERT_COUNTER = Counter(
    "ml_incident_alert_total",
    "Outgoing incident alert notifications.",
    labelnames=("channel", "result"),
)

INFERENCE_LATENCY_HISTOGRAM = Histogram(
    "ml_inference_latency_seconds",
    "End-to-end inference latency in seconds.",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

INFERENCE_REQUEST_COUNTER = Counter(
    "ml_inference_requests_total",
    "Total number of inference requests.",
    labelnames=("source",),
)

INFERENCE_ERROR_COUNTER = Counter(
    "ml_inference_errors_total",
    "Total inference processing errors.",
)

SECURITY_ATTACK_COUNTER = Counter(
    "ml_security_attacks_total",
    "Number of detected prompt-injection or jailbreak attempts.",
    labelnames=("reason",),
)

SECURITY_SEMANTIC_SIMILARITY_GAUGE = Gauge(
    "ml_security_semantic_similarity",
    "Max semantic similarity to adversarial template vectors.",
)

MODEL_FAITHFULNESS_SCORE_GAUGE = Gauge(
    "model_faithfulness_score",
    "RAG faithfulness score from HHEM-2.1-Open or fallback scorer.",
)

HUI_WALTER_ESTIMATED_ACCURACY_GAUGE = Gauge(
    "ml_hui_walter_estimated_accuracy",
    "Estimated model accuracy from Hui-Walter no-label inference.",
)

EMBEDDING_X_GAUGE = Gauge(
    "embedding_x",
    "2D embedding x-coordinate for observability scatter.",
    labelnames=("source", "request_id"),
)

EMBEDDING_Y_GAUGE = Gauge(
    "embedding_y",
    "2D embedding y-coordinate for observability scatter.",
    labelnames=("source", "request_id"),
)

SATURATION_GAUGE = Gauge(
    "ml_inference_saturation",
    "Approximate saturation ratio based on active requests and capacity.",
)

ACTIVE_LEARNING_CANDIDATE_GAUGE = Gauge(
    "ml_active_learning_candidate_rows",
    "Candidate rows considered for retraining curation.",
)

ACTIVE_LEARNING_SELECTED_GAUGE = Gauge(
    "ml_active_learning_selected_rows",
    "Rows selected by diversity-based curation for retraining.",
)

ACTIVE_LEARNING_DATA_EFFICIENCY_GAUGE = Gauge(
    "ml_active_learning_data_efficiency_ratio",
    "Selected/candidate ratio for retraining curation.",
)

ACTIVE_LEARNING_DIVERSITY_GAUGE = Gauge(
    "ml_active_learning_diversity_score",
    "Average minimum pairwise embedding distance inside curated retraining batch.",
)


def publish_embedding_projection(
    reference_points: list[dict[str, float | str]],
    live_points: list[dict[str, float | str]],
) -> None:
    global _embedding_label_cache

    active: set[tuple[str, str]] = set()

    for source, points in (("reference", reference_points), ("live", live_points)):
        for point in points:
            request_id = str(point.get("request_id", "unknown"))
            x = float(point.get("x", 0.0))
            y = float(point.get("y", 0.0))
            EMBEDDING_X_GAUGE.labels(source=source, request_id=request_id).set(x)
            EMBEDDING_Y_GAUGE.labels(source=source, request_id=request_id).set(y)
            active.add((source, request_id))

    stale = _embedding_label_cache - active
    for source, request_id in stale:
        try:
            EMBEDDING_X_GAUGE.remove(source, request_id)
        except KeyError:
            pass
        try:
            EMBEDDING_Y_GAUGE.remove(source, request_id)
        except KeyError:
            pass

    _embedding_label_cache = active


def metrics_payload() -> bytes:
    return generate_latest()


def metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class InferenceLog(BaseModel):
    request_id: str = Field(..., min_length=1)
    event_ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    input_features: dict[str, Any]
    embeddings: list[float] = Field(default_factory=list)
    softmax_probs: list[float] = Field(..., min_length=2)
    model_b_probs: list[float] = Field(default_factory=list)
    population_id: int = Field(0, ge=0, le=1)
    demographic_group: str = Field(default="unknown", min_length=1)
    observed_label: int | None = Field(default=None, ge=0)

    @field_validator("softmax_probs")
    @classmethod
    def validate_softmax_probs(cls, value: list[float]) -> list[float]:
        if any(p < 0.0 or p > 1.0 for p in value):
            raise ValueError("softmax_probs must be in [0, 1]")
        prob_sum = sum(value)
        if prob_sum <= 0.0:
            raise ValueError("softmax_probs sum must be > 0")
        # Normalize in case of minor floating-point error in upstream producer.
        return [p / prob_sum for p in value]


class InferenceRequest(BaseModel):
    request_id: str = Field(..., min_length=1)
    input_features: dict[str, float]
    embeddings: list[float] = Field(default_factory=list)
    demographic_group: str = Field(default="unknown", min_length=1)
    population_id: int = Field(0, ge=0, le=1)
    observed_label: int | None = Field(default=None, ge=0)
    prompt: str | None = None


class InferenceResponse(BaseModel):
    request_id: str
    source: str
    predicted_class: int
    softmax_probs: list[float]
    confidence: float
    uncertainty: float
    psi_drift_score: float
    mmd_drift_score: float
    bias_score: float
    top_drift_feature: str | None = None
    circuit_state: str
    circuit_status: str = "OK"


class AlertLabels(BaseModel):
    alertname: str = "unknown"
    severity: str = "warning"


class AlertEvent(BaseModel):
    status: Literal["firing", "resolved"] = "firing"
    labels: AlertLabels = Field(default_factory=AlertLabels)


class RetrainWebhookRequest(BaseModel):
    receiver: str | None = None
    status: str | None = None
    alerts: list[AlertEvent] = Field(default_factory=list)


class RetrainWebhookResponse(BaseModel):
    accepted: bool
    action: str
    promoted_rows: int
    selected_rows: int = 0
    candidate_rows: int = 0
    data_efficiency_ratio: float = 0.0


class ActiveLearningQueueItem(BaseModel):
    request_id: str
    uncertainty_score: float


class ActiveLearningQueueResponse(BaseModel):
    items: list[ActiveLearningQueueItem] = Field(default_factory=list)


class ActiveLearningCandidateItem(BaseModel):
    request_id: str
    confidence: float
    uncertainty: float


class ActiveLearningCandidatesResponse(BaseModel):
    items: list[ActiveLearningCandidateItem] = Field(default_factory=list)


class TelemetrySnapshot(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    circuit_state: str
    circuit_status: str
    hui_walter_estimated_accuracy: float
    psi_drift_score: float
    mmd_drift_score: float
    bias_score: float
    reference_count: int
    detection_count: int
    batch_event: bool = False
    chaos_active: bool = False


class EmbeddingSnapshotResponse(BaseModel):
    reference: list[list[float]] = Field(default_factory=list)
    detection: list[list[float]] = Field(default_factory=list)


class EmbeddingPoint(BaseModel):
    request_id: str
    source: Literal["reference", "live"]
    x: float
    y: float
    uncertainty: float = 0.0


class EmbeddingPointsResponse(BaseModel):
    points: list[EmbeddingPoint] = Field(default_factory=list)


class FaithfulnessRequest(BaseModel):
    context: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)


class FaithfulnessResponse(BaseModel):
    score: float
    model_name: str


class GeminiInferenceRequest(BaseModel):
    request_id: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    population_id: int = Field(0, ge=0, le=1)
    demographic_group: str = Field(default="unknown", min_length=1)


class GeminiInferenceResponse(BaseModel):
    request_id: str
    prompt: str
    response_text: str
    provider_model: str
    mmd_drift_score: float
    hui_walter_estimated_accuracy: float
    status: Literal["OK", "DRIFT", "ATTACK"]
    umap_x: float = Field(ge=0.0, le=1.0)
    umap_y: float = Field(ge=0.0, le=1.0)


class HealerCollectRequest(BaseModel):
    request_ids: list[str] = Field(default_factory=list)


class HealerCollectResponse(BaseModel):
    accepted: bool
    stored_rows: int


class LiveTelemetryPayload(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: str
    status: Literal["OK", "DRIFT", "ATTACK"]
    accuracy: float
    drift_magnitude: float
    umap_x: float = Field(ge=0.0, le=1.0)
    umap_y: float = Field(ge=0.0, le=1.0)


class SidecarInferenceRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(datetime.now(timezone.utc).timestamp()))
    prompt: str = Field(..., min_length=1)
    population_id: int = Field(0, ge=0, le=1)
    demographic_group: str = Field(default="unknown", min_length=1)


class SidecarInferenceResponse(BaseModel):
    request_id: str
    response_text: str
    vigor: float = Field(ge=0.0, le=1.0)
    drift: float = Field(ge=0.0, le=100.0)
    coords: list[float] = Field(default_factory=list, min_length=2, max_length=2)
    attribution: dict[str, int] = Field(default_factory=dict)
    log: str
    embedding_dim: int
    provider_model: str


class SidecarRetrainResponse(BaseModel):
    accepted: bool
    status: Literal["success"]
    duration_seconds: int
    log: str

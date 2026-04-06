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


class EmbeddingSnapshotResponse(BaseModel):
    reference: list[list[float]] = Field(default_factory=list)
    detection: list[list[float]] = Field(default_factory=list)


class FaithfulnessRequest(BaseModel):
    context: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)


class FaithfulnessResponse(BaseModel):
    score: float
    model_name: str

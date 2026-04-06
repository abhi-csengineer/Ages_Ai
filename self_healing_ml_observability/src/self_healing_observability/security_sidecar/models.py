from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SidecarInspectRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    request_id: str = Field(min_length=1)
    prompt: str = Field(default="")
    metadata: dict[str, Any] = Field(default_factory=dict)


class SidecarInspectResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    request_id: str = Field(min_length=1)
    detected: bool
    reason: str
    similarity: float = Field(ge=0.0, le=1.0)
    redacted_prompt: str
    redaction_count: int = Field(ge=0)

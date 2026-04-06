from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from self_healing_observability.monitoring.security import PromptInjectionDetector


@dataclass
class InspectionResult:
    detected: bool
    reason: str
    similarity: float
    redacted_prompt: str
    redaction_count: int


class SidecarPromptInspector:
    """Performs PII redaction and jailbreak detection before model inference."""

    def __init__(self, semantic_threshold: float = 0.75) -> None:
        self.detector = PromptInjectionDetector(semantic_threshold=semantic_threshold)
        self._pii_patterns = [
            (re.compile(r"\b[\w.%-]+@[\w.-]+\.[A-Za-z]{2,}\b", re.IGNORECASE), "[REDACTED_EMAIL]"),
            (re.compile(r"\b(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b"), "[REDACTED_PHONE]"),
            (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
            (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "[REDACTED_CARD]"),
            (re.compile(r"\b(?:sk|pk|api|token)[-_]?[A-Za-z0-9]{10,}\b", re.IGNORECASE), "[REDACTED_SECRET]"),
        ]

    def redact_pii(self, prompt: str) -> tuple[str, int]:
        redacted = prompt
        total = 0
        for pattern, replacement in self._pii_patterns:
            redacted, n = pattern.subn(replacement, redacted)
            total += n
        return redacted, total

    def inspect(self, request_id: str, prompt: str, metadata: dict[str, Any] | None = None) -> InspectionResult:
        redacted_prompt, redaction_count = self.redact_pii(prompt)

        payload = {
            "request_id": request_id,
            "prompt": redacted_prompt,
            "metadata": metadata or {},
        }
        detected, reason, similarity = self.detector.detect(payload)
        return InspectionResult(
            detected=detected,
            reason=reason,
            similarity=similarity,
            redacted_prompt=redacted_prompt,
            redaction_count=redaction_count,
        )

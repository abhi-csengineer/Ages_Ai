from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from self_healing_observability.core.circuit_breaker import MLCircuitBreaker
from self_healing_observability.core.metrics import (
    CIRCUIT_STATE_GAUGE,
    CIRCUIT_STATUS_GAUGE,
    INFERENCE_LATENCY_HISTOGRAM,
    INFERENCE_REQUEST_COUNTER,
    SECURITY_ATTACK_COUNTER,
    SECURITY_SEMANTIC_SIMILARITY_GAUGE,
)
from self_healing_observability.monitoring.security import PromptInjectionDetector
from self_healing_observability.security_sidecar.grpc_client import GrpcSecuritySidecarClient


class SecuritySidecarMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        circuit_breaker: MLCircuitBreaker,
        detector: PromptInjectionDetector,
        fallback_handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
        grpc_target: str | None = None,
        sidecar_timeout_seconds: float = 0.02,
    ) -> None:
        super().__init__(app)
        self.circuit_breaker = circuit_breaker
        self.detector = detector
        self.fallback_handler = fallback_handler
        self.grpc_target = (grpc_target or "").strip()
        self.sidecar_timeout_seconds = max(float(sidecar_timeout_seconds), 0.001)
        self.sidecar_client = GrpcSecuritySidecarClient(self.grpc_target) if self.grpc_target else None

    @staticmethod
    async def _override_request_body(request: Request, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive  # type: ignore[attr-defined]
        request._body = body  # type: ignore[attr-defined]

    async def dispatch(self, request: Request, call_next):
        if request.url.path != "/predict":
            return await call_next(request)

        start = time.perf_counter()
        body = await request.body()
        payload: dict[str, Any] = {}
        if body:
            try:
                payload = await request.json()
            except Exception:
                payload = {}

        detected, reason, similarity = self.detector.detect(payload)
        prompt = str(payload.get("prompt", ""))

        if self.sidecar_client is not None and prompt:
            try:
                sidecar_resp = await self.sidecar_client.inspect_prompt(
                    request_id=str(payload.get("request_id", "unknown")),
                    prompt=prompt,
                    metadata={"path": request.url.path},
                    timeout_s=self.sidecar_timeout_seconds,
                )
                redacted = str(sidecar_resp.get("redacted_prompt", prompt))
                if redacted != prompt:
                    payload["prompt"] = redacted
                    await self._override_request_body(request, payload)

                detected = bool(sidecar_resp.get("detected", False))
                reason = str(sidecar_resp.get("reason", reason))
                similarity = float(sidecar_resp.get("similarity", similarity))
            except Exception:
                # Fail-open to local detector to preserve availability.
                detected, reason, similarity = self.detector.detect(payload)

        SECURITY_SEMANTIC_SIMILARITY_GAUGE.set(similarity)

        if detected:
            self.circuit_breaker.trip_security(semantic_similarity=similarity)
            SECURITY_ATTACK_COUNTER.labels(reason=reason).inc()
            CIRCUIT_STATE_GAUGE.set(1)
            for status_name in ("OK", "DRIFT_BIAS", "SECURITY_ATTACK", "FALLBACK_MODE"):
                CIRCUIT_STATUS_GAUGE.labels(status=status_name).set(
                    1 if self.circuit_breaker.status.value == status_name else 0
                )

            fallback = await self.fallback_handler(payload)
            fallback["circuit_status"] = self.circuit_breaker.status.value
            INFERENCE_REQUEST_COUNTER.labels(source="fallback").inc()
            INFERENCE_LATENCY_HISTOGRAM.observe(time.perf_counter() - start)
            return JSONResponse(fallback, status_code=200)

        return await call_next(request)

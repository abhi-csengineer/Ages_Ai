from __future__ import annotations

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


class SecuritySidecarMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        circuit_breaker: MLCircuitBreaker,
        detector: PromptInjectionDetector,
        fallback_handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    ) -> None:
        super().__init__(app)
        self.circuit_breaker = circuit_breaker
        self.detector = detector
        self.fallback_handler = fallback_handler

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
        SECURITY_SEMANTIC_SIMILARITY_GAUGE.set(similarity)

        if detected:
            self.circuit_breaker.trip_security(semantic_similarity=similarity)
            SECURITY_ATTACK_COUNTER.labels(reason=reason).inc()
            CIRCUIT_STATE_GAUGE.set(1)
            for status_name in ("OK", "DRIFT_BIAS", "SECURITY_ATTACK"):
                CIRCUIT_STATUS_GAUGE.labels(status=status_name).set(
                    1 if self.circuit_breaker.status.value == status_name else 0
                )

            fallback = await self.fallback_handler(payload)
            fallback["circuit_status"] = self.circuit_breaker.status.value
            INFERENCE_REQUEST_COUNTER.labels(source="fallback").inc()
            INFERENCE_LATENCY_HISTOGRAM.observe(time.perf_counter() - start)
            return JSONResponse(fallback, status_code=200)

        return await call_next(request)

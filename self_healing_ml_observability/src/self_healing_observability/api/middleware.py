from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from self_healing_observability.core.circuit_breaker import MLCircuitBreaker
from self_healing_observability.core.metrics import (
    AUTO_HEAL_TRIGGER_COUNTER,
    BIAS_SCORE_GAUGE,
    CIRCUIT_CRITICAL_DRIFT_STREAK_GAUGE,
    CIRCUIT_LATCH_TRIGGER_COUNTER,
    CIRCUIT_STATE_GAUGE,
    CIRCUIT_STATUS_GAUGE,
    DRIFT_SCORE_GAUGE,
    INFERENCE_ERROR_COUNTER,
    INFERENCE_LATENCY_HISTOGRAM,
    INFERENCE_REQUEST_COUNTER,
    SATURATION_GAUGE,
)


class MLCircuitBreakerMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        circuit_breaker: MLCircuitBreaker,
        drift_score_provider: Callable[[], tuple[float, float]],
        bias_score_provider: Callable[[], float],
        fallback_handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
        auto_heal_handler: Callable[[], Awaitable[bool]] | None = None,
        latch_alert_handler: Callable[[], Awaitable[None]] | None = None,
        auto_heal_cooldown_seconds: float = 30.0,
    ) -> None:
        super().__init__(app)
        self.circuit_breaker = circuit_breaker
        self.drift_score_provider = drift_score_provider
        self.bias_score_provider = bias_score_provider
        self.fallback_handler = fallback_handler
        self.auto_heal_handler = auto_heal_handler
        self.latch_alert_handler = latch_alert_handler
        self.auto_heal_cooldown_seconds = max(float(auto_heal_cooldown_seconds), 1.0)
        self._last_auto_heal_at = 0.0
        self._auto_heal_in_flight = False

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()

        if request.url.path in {"/metrics", "/health"}:
            return await call_next(request)

        try:
            psi_score, mmd_score = self.drift_score_provider()
            bias_score = self.bias_score_provider()
        except Exception:
            INFERENCE_ERROR_COUNTER.inc()
            raise

        DRIFT_SCORE_GAUGE.labels(method="psi").set(psi_score)
        DRIFT_SCORE_GAUGE.labels(method="mmd").set(mmd_score)
        BIAS_SCORE_GAUGE.set(bias_score)

        state = self.circuit_breaker.update(psi_score=psi_score, mmd_score=mmd_score, bias_score=bias_score)
        CIRCUIT_CRITICAL_DRIFT_STREAK_GAUGE.set(self.circuit_breaker.consecutive_critical_drift_windows)
        if self.circuit_breaker.just_latched:
            CIRCUIT_LATCH_TRIGGER_COUNTER.inc()
            if self.latch_alert_handler is not None:
                asyncio.create_task(self.latch_alert_handler())

        CIRCUIT_STATE_GAUGE.set(1 if self.circuit_breaker.is_open else 0)
        for status_name in ("OK", "DRIFT_BIAS", "SECURITY_ATTACK", "FALLBACK_MODE"):
            CIRCUIT_STATUS_GAUGE.labels(status=status_name).set(
                1 if self.circuit_breaker.status.value == status_name else 0
            )
        SATURATION_GAUGE.set(min(1.0, (psi_score + mmd_score + bias_score) / 3.0))

        if (
            self.circuit_breaker.status.value == "DRIFT_BIAS"
            and self.auto_heal_handler is not None
            and not self._auto_heal_in_flight
        ):
            now = time.monotonic()
            if (now - self._last_auto_heal_at) >= self.auto_heal_cooldown_seconds:
                self._last_auto_heal_at = now
                self._auto_heal_in_flight = True

                async def _heal() -> None:
                    try:
                        success = await self.auto_heal_handler()
                        AUTO_HEAL_TRIGGER_COUNTER.labels(result="success" if success else "noop").inc()
                    except Exception:
                        AUTO_HEAL_TRIGGER_COUNTER.labels(result="failed").inc()
                    finally:
                        self._auto_heal_in_flight = False

                asyncio.create_task(_heal())

        if self.circuit_breaker.is_open and request.url.path == "/predict":
            payload = await request.json()
            fallback = await self.fallback_handler(payload)
            fallback["circuit_status"] = self.circuit_breaker.status.value
            INFERENCE_REQUEST_COUNTER.labels(source="fallback").inc()
            elapsed = time.perf_counter() - start
            INFERENCE_LATENCY_HISTOGRAM.observe(elapsed)
            return JSONResponse(fallback, status_code=200)

        response = await call_next(request)
        if request.url.path == "/predict":
            source = "model" if state.value == "closed" else "fallback"
            INFERENCE_REQUEST_COUNTER.labels(source=source).inc()
        elapsed = time.perf_counter() - start
        INFERENCE_LATENCY_HISTOGRAM.observe(elapsed)
        return response

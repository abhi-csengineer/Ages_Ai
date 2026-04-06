from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol


@dataclass
class CircuitSnapshot:
    state: str
    status: str
    last_psi_score: float
    last_mmd_score: float
    last_bias_score: float
    security_attack_count: int
    last_security_similarity: float
    consecutive_critical_drift_windows: int
    latch_trigger_count: int


class CircuitStateCache(Protocol):
    def load(self) -> CircuitSnapshot | None: ...

    def save(self, snapshot: CircuitSnapshot) -> None: ...


class InMemoryCircuitStateCache:
    def __init__(self) -> None:
        self._snapshot: CircuitSnapshot | None = None

    def load(self) -> CircuitSnapshot | None:
        return self._snapshot

    def save(self, snapshot: CircuitSnapshot) -> None:
        self._snapshot = snapshot


class RedisCircuitStateCache:
    def __init__(self, redis_url: str, key: str = "aegis:circuit:state") -> None:
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError("redis package is required. Install with `pip install -r requirements.txt`.") from exc

        self._key = key
        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)

    def load(self) -> CircuitSnapshot | None:
        raw = self._redis.get(self._key)
        if not raw:
            return None
        payload = json.loads(raw)
        return CircuitSnapshot(
            state=str(payload.get("state", "closed")),
            status=str(payload.get("status", "OK")),
            last_psi_score=float(payload.get("last_psi_score", 0.0)),
            last_mmd_score=float(payload.get("last_mmd_score", 0.0)),
            last_bias_score=float(payload.get("last_bias_score", 0.0)),
            security_attack_count=int(payload.get("security_attack_count", 0)),
            last_security_similarity=float(payload.get("last_security_similarity", 0.0)),
            consecutive_critical_drift_windows=int(payload.get("consecutive_critical_drift_windows", 0)),
            latch_trigger_count=int(payload.get("latch_trigger_count", 0)),
        )

    def save(self, snapshot: CircuitSnapshot) -> None:
        payload = {
            "state": snapshot.state,
            "status": snapshot.status,
            "last_psi_score": snapshot.last_psi_score,
            "last_mmd_score": snapshot.last_mmd_score,
            "last_bias_score": snapshot.last_bias_score,
            "security_attack_count": snapshot.security_attack_count,
            "last_security_similarity": snapshot.last_security_similarity,
            "consecutive_critical_drift_windows": snapshot.consecutive_critical_drift_windows,
            "latch_trigger_count": snapshot.latch_trigger_count,
        }
        self._redis.set(self._key, json.dumps(payload))

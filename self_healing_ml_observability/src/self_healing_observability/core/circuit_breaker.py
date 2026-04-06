from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from self_healing_observability.core.circuit_cache import CircuitSnapshot, CircuitStateCache


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"


class CircuitStatus(str, Enum):
    OK = "OK"
    DRIFT_BIAS = "DRIFT_BIAS"
    SECURITY_ATTACK = "SECURITY_ATTACK"
    FALLBACK_MODE = "FALLBACK_MODE"


@dataclass
class MLCircuitBreaker:
    drift_threshold: float = 0.25
    bias_threshold: float = 0.35
    critical_drift_threshold: float = 0.45
    critical_window_streak: int = 3
    state: CircuitState = CircuitState.CLOSED
    status: CircuitStatus = CircuitStatus.OK
    last_psi_score: float = 0.0
    last_mmd_score: float = 0.0
    last_bias_score: float = 0.0
    security_attack_count: int = 0
    last_security_similarity: float = 0.0
    consecutive_critical_drift_windows: int = 0
    latch_trigger_count: int = 0
    just_latched: bool = False
    cache: CircuitStateCache | None = None

    def __post_init__(self) -> None:
        if self.cache is None:
            return
        snapshot = self.cache.load()
        if snapshot is None:
            return
        self.state = CircuitState(snapshot.state)
        self.status = CircuitStatus(snapshot.status)
        self.last_psi_score = snapshot.last_psi_score
        self.last_mmd_score = snapshot.last_mmd_score
        self.last_bias_score = snapshot.last_bias_score
        self.security_attack_count = snapshot.security_attack_count
        self.last_security_similarity = snapshot.last_security_similarity
        self.consecutive_critical_drift_windows = snapshot.consecutive_critical_drift_windows
        self.latch_trigger_count = snapshot.latch_trigger_count

    def _persist(self) -> None:
        if self.cache is None:
            return
        self.cache.save(
            CircuitSnapshot(
                state=self.state.value,
                status=self.status.value,
                last_psi_score=self.last_psi_score,
                last_mmd_score=self.last_mmd_score,
                last_bias_score=self.last_bias_score,
                security_attack_count=self.security_attack_count,
                last_security_similarity=self.last_security_similarity,
                consecutive_critical_drift_windows=self.consecutive_critical_drift_windows,
                latch_trigger_count=self.latch_trigger_count,
            )
        )

    def update(self, psi_score: float, mmd_score: float, bias_score: float) -> CircuitState:
        self.just_latched = False

        if self.status == CircuitStatus.SECURITY_ATTACK:
            self.state = CircuitState.OPEN
            return self.state

        if self.status == CircuitStatus.FALLBACK_MODE:
            self.state = CircuitState.OPEN
            return self.state

        self.last_psi_score = psi_score
        self.last_mmd_score = mmd_score
        self.last_bias_score = bias_score

        critical_drift = psi_score > self.critical_drift_threshold or mmd_score > self.critical_drift_threshold
        if critical_drift:
            self.consecutive_critical_drift_windows += 1
        else:
            self.consecutive_critical_drift_windows = 0

        if self.consecutive_critical_drift_windows >= max(self.critical_window_streak, 1):
            self.state = CircuitState.OPEN
            self.status = CircuitStatus.FALLBACK_MODE
            self.latch_trigger_count += 1
            self.just_latched = True
            self._persist()
            return self.state

        if (
            psi_score > self.drift_threshold
            or mmd_score > self.drift_threshold
            or bias_score > self.bias_threshold
        ):
            self.state = CircuitState.OPEN
            self.status = CircuitStatus.DRIFT_BIAS
        else:
            self.state = CircuitState.CLOSED
            self.status = CircuitStatus.OK
        self._persist()
        return self.state

    def trip_security(self, semantic_similarity: float = 1.0) -> None:
        self.security_attack_count += 1
        self.last_security_similarity = semantic_similarity
        self.state = CircuitState.OPEN
        self.status = CircuitStatus.SECURITY_ATTACK
        self._persist()

    def reset(self) -> None:
        self.state = CircuitState.CLOSED
        self.status = CircuitStatus.OK
        self.last_psi_score = 0.0
        self.last_mmd_score = 0.0
        self.last_bias_score = 0.0
        self.last_security_similarity = 0.0
        self.consecutive_critical_drift_windows = 0
        self.just_latched = False
        self._persist()

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"


class CircuitStatus(str, Enum):
    OK = "OK"
    DRIFT_BIAS = "DRIFT_BIAS"
    SECURITY_ATTACK = "SECURITY_ATTACK"


@dataclass
class MLCircuitBreaker:
    drift_threshold: float = 0.25
    bias_threshold: float = 0.35
    state: CircuitState = CircuitState.CLOSED
    status: CircuitStatus = CircuitStatus.OK
    last_psi_score: float = 0.0
    last_mmd_score: float = 0.0
    last_bias_score: float = 0.0
    security_attack_count: int = 0
    last_security_similarity: float = 0.0

    def update(self, psi_score: float, mmd_score: float, bias_score: float) -> CircuitState:
        if self.status == CircuitStatus.SECURITY_ATTACK:
            self.state = CircuitState.OPEN
            return self.state

        self.last_psi_score = psi_score
        self.last_mmd_score = mmd_score
        self.last_bias_score = bias_score
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
        return self.state

    def trip_security(self, semantic_similarity: float = 1.0) -> None:
        self.security_attack_count += 1
        self.last_security_similarity = semantic_similarity
        self.state = CircuitState.OPEN
        self.status = CircuitStatus.SECURITY_ATTACK

    def reset(self) -> None:
        self.state = CircuitState.CLOSED
        self.status = CircuitStatus.OK
        self.last_psi_score = 0.0
        self.last_mmd_score = 0.0
        self.last_bias_score = 0.0
        self.last_security_similarity = 0.0

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

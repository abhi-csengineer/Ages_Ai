from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StreamingStats:
    """Numerically stable streaming mean/variance via Welford's algorithm."""

    n: int = 0
    mean: float = 0.0
    sum_squared_diff: float = 0.0

    def update(self, x: float) -> None:
        self.n += 1
        delta = x - self.mean
        self.mean = self.mean + (delta / self.n)
        delta2 = x - self.mean
        self.sum_squared_diff += delta * delta2

    @property
    def variance(self) -> float:
        if self.n < 2:
            return 0.0
        return self.sum_squared_diff / (self.n - 1)

    @property
    def std_dev(self) -> float:
        return self.variance ** 0.5

    def reset(self) -> None:
        self.n = 0
        self.mean = 0.0
        self.sum_squared_diff = 0.0

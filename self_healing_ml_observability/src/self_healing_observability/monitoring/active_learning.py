from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


def entropy_uncertainty(probs: list[float], epsilon: float = 1e-12) -> float:
    if not probs:
        return 0.0
    arr = np.asarray(probs, dtype=float)
    arr = np.clip(arr, epsilon, 1.0)
    arr = arr / arr.sum()
    entropy = -float(np.sum(arr * np.log(arr)))
    max_entropy = math.log(len(arr)) if len(arr) > 1 else 1.0
    if max_entropy <= 0.0:
        return 0.0
    return entropy / max_entropy


def margin_uncertainty(probs: list[float]) -> float:
    if len(probs) < 2:
        return 0.0
    sorted_probs = sorted(probs, reverse=True)
    margin = sorted_probs[0] - sorted_probs[1]
    return max(0.0, 1.0 - margin)


def combined_uncertainty_score(probs: list[float], entropy_weight: float = 0.5) -> float:
    entropy = entropy_uncertainty(probs)
    margin = margin_uncertainty(probs)
    w = max(0.0, min(1.0, entropy_weight))
    return (w * entropy) + ((1.0 - w) * margin)


@dataclass
class DetectionRecord:
    request_id: str
    softmax_probs: list[float]
    embeddings: list[float]


class SampleSelector:
    """Uncertainty-first active learning selector with diversity filtering."""

    def __init__(self, entropy_weight: float = 0.5) -> None:
        self.entropy_weight = entropy_weight

    def rank_by_uncertainty(self, records: list[DetectionRecord]) -> list[DetectionRecord]:
        ranked = sorted(
            records,
            key=lambda rec: combined_uncertainty_score(rec.softmax_probs, self.entropy_weight),
            reverse=True,
        )
        return ranked

    def diversity_filter_core_set(
        self,
        records: list[DetectionRecord],
        target_size: int,
    ) -> list[DetectionRecord]:
        if not records or target_size <= 0:
            return []
        if len(records) <= target_size:
            return records

        embeddings = np.asarray([r.embeddings for r in records], dtype=float)
        if embeddings.ndim != 2 or embeddings.shape[1] == 0:
            return records[:target_size]

        selected_idxs: list[int] = [0]
        min_dist = np.linalg.norm(embeddings - embeddings[0], axis=1)

        while len(selected_idxs) < target_size:
            next_idx = int(np.argmax(min_dist))
            if next_idx in selected_idxs:
                break
            selected_idxs.append(next_idx)
            dist_to_new = np.linalg.norm(embeddings - embeddings[next_idx], axis=1)
            min_dist = np.minimum(min_dist, dist_to_new)

        return [records[i] for i in selected_idxs]

    def select_retraining_batch(
        self,
        records: list[DetectionRecord],
        budget_ratio: float = 0.1,
        prefilter_multiplier: int = 5,
    ) -> list[DetectionRecord]:
        if not records:
            return []

        final_target = max(1, int(len(records) * budget_ratio))
        prefilter_target = min(len(records), max(final_target, final_target * prefilter_multiplier))

        ranked = self.rank_by_uncertainty(records)
        uncertain_pool = ranked[:prefilter_target]
        diverse = self.diversity_filter_core_set(uncertain_pool, target_size=final_target)
        return diverse

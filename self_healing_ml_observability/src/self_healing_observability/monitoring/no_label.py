from __future__ import annotations

from dataclasses import dataclass, field


def _safe_ratio(num: float, den: float) -> float:
    if den <= 0.0:
        return 0.0
    return num / den


def normalized_confidence(probs: list[float]) -> float:
    n_classes = len(probs)
    if n_classes <= 1:
        return 1.0

    p_max = max(probs)
    denom = n_classes - 1
    confidence = ((n_classes * p_max) - 1.0) / denom
    return max(0.0, min(1.0, confidence))


def normalized_uncertainty(probs: list[float]) -> float:
    n_classes = len(probs)
    if n_classes <= 1:
        return 0.0

    p_max = max(probs)
    p_min = min(probs)
    p_n = (1.0 - p_max) / (n_classes - 1)

    if p_n <= 0.0:
        return 0.0

    uncertainty = 1.0 - (p_min / p_n)
    return max(0.0, min(1.0, uncertainty))


@dataclass
class HuiWalterTracker:
    """Tracks a 2x2x2 contingency table for two models and two populations."""

    table: list[list[list[int]]] = field(
        default_factory=lambda: [[[0, 0], [0, 0]], [[0, 0], [0, 0]]]
    )

    def update(self, population: int, model_a_positive: bool, model_b_positive: bool) -> None:
        if population not in (0, 1):
            raise ValueError("population must be 0 or 1")
        a_idx = 1 if model_a_positive else 0
        b_idx = 1 if model_b_positive else 0
        self.table[population][a_idx][b_idx] += 1

    def estimate_error_rates(self) -> dict[str, object]:
        """
        Method-of-moments approximation for Hui-Walter style no-label monitoring.

        This implementation uses two populations with potentially different
        prevalences and two conditionally independent tests/models.
        """
        n_pop = [0, 0]
        a_pos = [0, 0]
        b_pos = [0, 0]
        both_pos = [0, 0]

        for pop in (0, 1):
            counts = self.table[pop]
            n = counts[0][0] + counts[0][1] + counts[1][0] + counts[1][1]
            n_pop[pop] = n
            a_pos[pop] = counts[1][0] + counts[1][1]
            b_pos[pop] = counts[0][1] + counts[1][1]
            both_pos[pop] = counts[1][1]

        p_a = [_safe_ratio(a_pos[i], n_pop[i]) for i in (0, 1)]
        p_b = [_safe_ratio(b_pos[i], n_pop[i]) for i in (0, 1)]
        p_ab = [_safe_ratio(both_pos[i], n_pop[i]) for i in (0, 1)]

        p_bar = max(0.5 * (p_a[0] + p_a[1]), 1e-6)
        q_bar = max(1.0 - p_bar, 1e-6)

        # Approximate conditional agreement terms under independence.
        se_a = max(min(_safe_ratio(p_ab[0], p_bar), 1.0), 0.0)
        se_b = max(min(_safe_ratio(p_ab[1], p_bar), 1.0), 0.0)

        # Approximate specificity from disagreement with positives.
        sp_a = max(min(1.0 - _safe_ratio(max(p_a[0] - p_ab[0], 0.0), q_bar), 1.0), 0.0)
        sp_b = max(min(1.0 - _safe_ratio(max(p_b[1] - p_ab[1], 0.0), q_bar), 1.0), 0.0)

        prevalence_pop0 = max(min(p_bar, 1.0), 0.0)
        prevalence_pop1 = max(min(0.5 * (p_b[0] + p_b[1]), 1.0), 0.0)

        accuracy_a = prevalence_pop0 * se_a + (1.0 - prevalence_pop0) * sp_a
        fpr_a = 1.0 - sp_a

        return {
            "status": "estimated",
            "contingency_table_2x2x2": self.table,
            "population_sizes": {"population_0": n_pop[0], "population_1": n_pop[1]},
            "estimated": {
                "sensitivity_model_a": se_a,
                "specificity_model_a": sp_a,
                "sensitivity_model_b": se_b,
                "specificity_model_b": sp_b,
                "prevalence_population_0": prevalence_pop0,
                "prevalence_population_1": prevalence_pop1,
                "accuracy_model_a": accuracy_a,
                "false_positive_rate_model_a": fpr_a,
            },
        }

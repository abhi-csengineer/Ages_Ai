from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GroupStats:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0

    @property
    def positive_rate(self) -> float:
        total = self.tp + self.fp + self.tn + self.fn
        if total == 0:
            return 0.0
        return (self.tp + self.fp) / total

    @property
    def true_positive_rate(self) -> float:
        den = self.tp + self.fn
        if den == 0:
            return 0.0
        return self.tp / den

    @property
    def false_positive_rate(self) -> float:
        den = self.fp + self.tn
        if den == 0:
            return 0.0
        return self.fp / den


@dataclass
class BiasMonitor:
    disparate_impact_threshold: float = 0.8
    equalized_odds_threshold: float = 0.2
    groups: dict[str, GroupStats] = field(default_factory=dict)

    def update(self, group: str, prediction_positive: bool, observed_label: int | None) -> None:
        if group not in self.groups:
            self.groups[group] = GroupStats()
        stats = self.groups[group]

        if observed_label is None:
            # Without labels, track only prediction propensity in DI.
            if prediction_positive:
                stats.fp += 1
            else:
                stats.tn += 1
            return

        if prediction_positive and observed_label == 1:
            stats.tp += 1
        elif prediction_positive and observed_label == 0:
            stats.fp += 1
        elif (not prediction_positive) and observed_label == 0:
            stats.tn += 1
        else:
            stats.fn += 1

    def disparate_impact(self) -> float:
        if len(self.groups) < 2:
            return 1.0
        rates = [max(g.positive_rate, 1e-8) for g in self.groups.values()]
        return min(rates) / max(rates)

    def equalized_odds_gap(self) -> float:
        if len(self.groups) < 2:
            return 0.0
        tprs = [g.true_positive_rate for g in self.groups.values()]
        fprs = [g.false_positive_rate for g in self.groups.values()]
        return max(tprs) - min(tprs) + max(fprs) - min(fprs)

    def bias_score(self) -> float:
        di = self.disparate_impact()
        eo = self.equalized_odds_gap()
        return max(0.0, (1.0 - di) + eo)

    def is_bias_alert(self) -> bool:
        return (
            self.disparate_impact() < self.disparate_impact_threshold
            or self.equalized_odds_gap() > self.equalized_odds_threshold
        )

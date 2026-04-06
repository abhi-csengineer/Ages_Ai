from __future__ import annotations

import math
from dataclasses import dataclass, field


def _safe_ratio(num: float, den: float) -> float:
    if den <= 0.0:
        return 0.0
    return num / den


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _beta_posterior(mean_proxy: float, n_eff: int, prior_a: float = 1.0, prior_b: float = 1.0) -> dict[str, float]:
    """
    Beta posterior summary with normal-approximation 95% credible interval.

    We use a proxy sample size because Hui-Walter is itself an estimator under
    latent labels; this keeps uncertainty reporting conservative and stable.
    """
    n = max(int(n_eff), 1)
    m = _clip01(mean_proxy)

    alpha = prior_a + (m * n)
    beta = prior_b + ((1.0 - m) * n)

    post_mean = alpha / max(alpha + beta, 1e-9)
    post_var = (alpha * beta) / max(((alpha + beta) ** 2) * (alpha + beta + 1.0), 1e-9)
    post_sd = math.sqrt(max(post_var, 0.0))

    z = 1.96
    lower = _clip01(post_mean - (z * post_sd))
    upper = _clip01(post_mean + (z * post_sd))
    return {
        "posterior_mean": post_mean,
        "lower_95": lower,
        "upper_95": upper,
        "posterior_alpha": alpha,
        "posterior_beta": beta,
    }


def _accuracy_posterior_summary(
    prevalence: dict[str, float],
    sensitivity: dict[str, float],
    specificity: dict[str, float],
) -> dict[str, float]:
    """Approximate posterior for accuracy via first-order uncertainty propagation."""
    p = prevalence["posterior_mean"]
    se = sensitivity["posterior_mean"]
    sp = specificity["posterior_mean"]

    mean = (p * se) + ((1.0 - p) * sp)

    var_p = ((prevalence["upper_95"] - prevalence["lower_95"]) / 3.92) ** 2
    var_se = ((sensitivity["upper_95"] - sensitivity["lower_95"]) / 3.92) ** 2
    var_sp = ((specificity["upper_95"] - specificity["lower_95"]) / 3.92) ** 2

    var = (p * p * var_se) + (((1.0 - p) ** 2) * var_sp) + (((se - sp) ** 2) * var_p)
    sd = math.sqrt(max(var, 0.0))

    lower = _clip01(mean - (1.96 * sd))
    upper = _clip01(mean + (1.96 * sd))
    return {
        "posterior_mean": _clip01(mean),
        "lower_95": lower,
        "upper_95": upper,
    }


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

        n_total = n_pop[0] + n_pop[1]
        n_pos_pop0 = max(int(round(p_bar * max(n_pop[0], 1))), 1)
        n_pos_pop1 = max(int(round(p_bar * max(n_pop[1], 1))), 1)
        n_neg_pop0 = max(int(round(q_bar * max(n_pop[0], 1))), 1)
        n_neg_pop1 = max(int(round(q_bar * max(n_pop[1], 1))), 1)

        se_a_bayes = _beta_posterior(se_a, n_pos_pop0)
        sp_a_bayes = _beta_posterior(sp_a, n_neg_pop0)
        se_b_bayes = _beta_posterior(se_b, n_pos_pop1)
        sp_b_bayes = _beta_posterior(sp_b, n_neg_pop1)

        prev0_bayes = _beta_posterior(prevalence_pop0, max(n_pop[0], 1))
        prev1_bayes = _beta_posterior(prevalence_pop1, max(n_pop[1], 1))

        acc_a_bayes = _accuracy_posterior_summary(prev0_bayes, se_a_bayes, sp_a_bayes)
        fpr_a_bayes = _beta_posterior(fpr_a, n_neg_pop0)

        ci = {
            "sensitivity_model_a": se_a_bayes,
            "specificity_model_a": sp_a_bayes,
            "sensitivity_model_b": se_b_bayes,
            "specificity_model_b": sp_b_bayes,
            "prevalence_population_0": prev0_bayes,
            "prevalence_population_1": prev1_bayes,
            "accuracy_model_a": acc_a_bayes,
            "false_positive_rate_model_a": fpr_a_bayes,
            "effective_sample_size": n_total,
        }

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
            "bayesian": {
                "estimated": {
                    "sensitivity_model_a": se_a_bayes["posterior_mean"],
                    "specificity_model_a": sp_a_bayes["posterior_mean"],
                    "sensitivity_model_b": se_b_bayes["posterior_mean"],
                    "specificity_model_b": sp_b_bayes["posterior_mean"],
                    "prevalence_population_0": prev0_bayes["posterior_mean"],
                    "prevalence_population_1": prev1_bayes["posterior_mean"],
                    "accuracy_model_a": acc_a_bayes["posterior_mean"],
                    "false_positive_rate_model_a": fpr_a_bayes["posterior_mean"],
                },
                "credible_interval_95": ci,
            },
        }

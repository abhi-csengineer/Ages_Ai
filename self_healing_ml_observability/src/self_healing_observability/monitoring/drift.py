from __future__ import annotations

import numpy as np


def population_stability_index(
    reference: list[float], current: list[float], bins: int = 10, epsilon: float = 1e-8
) -> float:
    if not reference or not current:
        return 0.0

    ref_arr = np.asarray(reference, dtype=float)
    cur_arr = np.asarray(current, dtype=float)

    min_edge = min(float(ref_arr.min()), float(cur_arr.min()))
    max_edge = max(float(ref_arr.max()), float(cur_arr.max()))

    if min_edge == max_edge:
        return 0.0

    edges = np.linspace(min_edge, max_edge, bins + 1)
    ref_hist, _ = np.histogram(ref_arr, bins=edges)
    cur_hist, _ = np.histogram(cur_arr, bins=edges)

    ref_ratio = ref_hist / max(ref_hist.sum(), 1)
    cur_ratio = cur_hist / max(cur_hist.sum(), 1)

    ref_ratio = np.clip(ref_ratio, epsilon, None)
    cur_ratio = np.clip(cur_ratio, epsilon, None)

    psi = np.sum((cur_ratio - ref_ratio) * np.log(cur_ratio / ref_ratio))
    return float(max(0.0, psi))


def gaussian_kernel_mmd(
    reference_embeddings: list[list[float]],
    detection_embeddings: list[list[float]],
    sigma: float = 1.0,
) -> float:
    """Compute unbiased MMD^2 estimate with RBF kernel."""
    if not reference_embeddings or not detection_embeddings:
        return 0.0

    x = np.asarray(reference_embeddings, dtype=float)
    y = np.asarray(detection_embeddings, dtype=float)

    if x.ndim != 2 or y.ndim != 2:
        return 0.0
    if x.shape[1] != y.shape[1]:
        return 0.0

    gamma = 1.0 / (2.0 * max(sigma, 1e-8) ** 2)

    def _rbf(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        sq = np.sum((a[:, None, :] - b[None, :, :]) ** 2, axis=2)
        return np.exp(-gamma * sq)

    k_xx = _rbf(x, x)
    k_yy = _rbf(y, y)
    k_xy = _rbf(x, y)

    nx = x.shape[0]
    ny = y.shape[0]
    if nx < 2 or ny < 2:
        return 0.0

    np.fill_diagonal(k_xx, 0.0)
    np.fill_diagonal(k_yy, 0.0)

    term_x = k_xx.sum() / (nx * (nx - 1))
    term_y = k_yy.sum() / (ny * (ny - 1))
    term_xy = 2.0 * k_xy.mean()
    return float(max(0.0, term_x + term_y - term_xy))

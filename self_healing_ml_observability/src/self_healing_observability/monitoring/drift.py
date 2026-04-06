from __future__ import annotations

import numpy as np


class RunningVectorWelford:
    """Numerically stable running mean for vectors using Welford updates."""

    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.n = 0
        self.mean = np.zeros(dim, dtype=float)

    def update(self, x: np.ndarray) -> None:
        if x.shape[0] != self.dim:
            return
        self.n += 1
        delta = x - self.mean
        self.mean = self.mean + (delta / self.n)

    def reset(self) -> None:
        self.n = 0
        self.mean = np.zeros(self.dim, dtype=float)


class StreamingIncrementalPCA:
    """
    Incremental PCA with constant-memory state.

    The covariance sketch is maintained via a vectorized Welford update,
    then principal components are recomputed periodically.
    """

    def __init__(self, input_dim: int, n_components: int = 4, update_interval: int = 32) -> None:
        self.input_dim = max(1, input_dim)
        self.n_components = max(1, min(n_components, self.input_dim))
        self.update_interval = max(1, update_interval)

        self.n = 0
        self.mean = np.zeros(self.input_dim, dtype=float)
        self.m2 = np.zeros((self.input_dim, self.input_dim), dtype=float)

        self.components = np.eye(self.input_dim, dtype=float)[: self.n_components]
        self._pending_updates = 0

    def _normalize(self, x: list[float] | np.ndarray) -> np.ndarray:
        vec = np.asarray(x, dtype=float).reshape(-1)
        if vec.shape[0] == self.input_dim:
            return vec
        out = np.zeros(self.input_dim, dtype=float)
        take = min(self.input_dim, vec.shape[0])
        if take > 0:
            out[:take] = vec[:take]
        return out

    def update(self, x: list[float] | np.ndarray) -> None:
        vec = self._normalize(x)

        self.n += 1
        delta = vec - self.mean
        self.mean = self.mean + (delta / self.n)
        delta2 = vec - self.mean
        self.m2 += np.outer(delta, delta2)

        self._pending_updates += 1
        if self.n >= 2 and self._pending_updates >= self.update_interval:
            self._recompute_components()
            self._pending_updates = 0

    def _recompute_components(self) -> None:
        cov = self.covariance()
        if cov is None:
            return
        eigvals, eigvecs = np.linalg.eigh(cov)
        order = np.argsort(eigvals)[::-1]
        eigvecs = eigvecs[:, order]
        self.components = eigvecs[:, : self.n_components].T

    def covariance(self) -> np.ndarray | None:
        if self.n < 2:
            return None
        return self.m2 / max(self.n - 1, 1)

    def transform(self, x: list[float] | np.ndarray) -> np.ndarray:
        vec = self._normalize(x)
        centered = vec - self.mean
        return self.components @ centered

    def reset(self) -> None:
        self.n = 0
        self.mean = np.zeros(self.input_dim, dtype=float)
        self.m2 = np.zeros((self.input_dim, self.input_dim), dtype=float)
        self.components = np.eye(self.input_dim, dtype=float)[: self.n_components]
        self._pending_updates = 0


class StreamingApproximateMMD:
    """
    Streaming MMD estimator with Random Fourier Features (RFF).

    Embeddings are projected through an Incremental PCA basis first, then
    transformed into an RFF space where MMD^2 is ||mu_ref - mu_det||^2.
    """

    def __init__(
        self,
        input_dim: int,
        pca_components: int = 4,
        n_rff: int = 64,
        sigma: float = 1.0,
        seed: int = 42,
    ) -> None:
        self.input_dim = max(1, input_dim)
        self.pca_components = max(1, min(pca_components, self.input_dim))
        self.n_rff = max(8, n_rff)
        self.sigma = max(float(sigma), 1e-6)

        self.pca = StreamingIncrementalPCA(input_dim=self.input_dim, n_components=self.pca_components)

        rng = np.random.default_rng(seed)
        self._w = rng.normal(
            loc=0.0,
            scale=1.0 / self.sigma,
            size=(self.n_rff, self.pca_components),
        )
        self._b = rng.uniform(0.0, 2.0 * np.pi, size=(self.n_rff,))
        self._scale = np.sqrt(2.0 / self.n_rff)

        self.reference_stats = RunningVectorWelford(self.n_rff)
        self.detection_stats = RunningVectorWelford(self.n_rff)

    def _phi(self, projected: np.ndarray) -> np.ndarray:
        return self._scale * np.cos((self._w @ projected) + self._b)

    def observe_reference(self, embedding: list[float]) -> None:
        self.pca.update(embedding)
        projected = self.pca.transform(embedding)
        self.reference_stats.update(self._phi(projected))

    def observe_detection(self, embedding: list[float]) -> None:
        projected = self.pca.transform(embedding)
        self.detection_stats.update(self._phi(projected))

    def mmd2(self) -> float:
        if self.reference_stats.n == 0 or self.detection_stats.n == 0:
            return 0.0
        diff = self.reference_stats.mean - self.detection_stats.mean
        return float(max(0.0, float(diff @ diff)))

    def reset(self) -> None:
        self.pca.reset()
        self.reference_stats.reset()
        self.detection_stats.reset()


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

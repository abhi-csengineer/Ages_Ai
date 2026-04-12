import { EmbeddingPoint } from "../types/contracts";

/**
 * Generate mock embedding points for UMAP visualisation when backend is offline.
 * Creates two distinct clusters (reference + live) with realistic spread.
 */
export function generateMockEmbeddingPoints(): EmbeddingPoint[] {
  const points: EmbeddingPoint[] = [];

  /* ── Reference cluster: centered around (0.35, 0.45) ── */
  for (let i = 0; i < 140; i++) {
    points.push({
      request_id: `ref-mock-${i}`,
      source: "reference",
      x: 0.35 + (Math.random() - 0.5) * 0.28,
      y: 0.45 + (Math.random() - 0.5) * 0.3,
      uncertainty: Math.random() * 0.2,
    });
  }

  /* ── Live cluster: shifted right + up, showing drift ── */
  for (let i = 0; i < 80; i++) {
    points.push({
      request_id: `live-mock-${i}`,
      source: "live",
      x: 0.58 + (Math.random() - 0.5) * 0.25,
      y: 0.55 + (Math.random() - 0.5) * 0.28,
      uncertainty: 0.2 + Math.random() * 0.5,
    });
  }

  /* ── Outlier attack points ── */
  for (let i = 0; i < 12; i++) {
    points.push({
      request_id: `attack-mock-${i}`,
      source: "live",
      x: 0.85 + (Math.random() - 0.5) * 0.15,
      y: 0.2 + (Math.random() - 0.5) * 0.2,
      uncertainty: 0.7 + Math.random() * 0.3,
    });
  }

  return points;
}

/**
 * Generate a realistic MMD drift series for the drift histogram and sparkline.
 */
export function generateMockMmdSeries(): number[] {
  const series: number[] = [];
  let value = 0.04;
  for (let i = 0; i < 40; i++) {
    value += (Math.random() - 0.45) * 0.015;
    value = Math.max(0.005, Math.min(0.35, value));
    /* simulate a drift event spike around index 25-32 */
    if (i >= 25 && i <= 32) {
      value += 0.02 + Math.random() * 0.03;
      value = Math.min(0.35, value);
    }
    series.push(value);
  }
  return series;
}

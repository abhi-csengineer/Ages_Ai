import { EmbeddingPoint, ModelComparisonRow, ParameterDrift } from "../types/contracts";

/* ── UMAP mock clusters ── */
export function generateMockEmbeddingPoints(): EmbeddingPoint[] {
  const points: EmbeddingPoint[] = [];

  /* Reference cluster */
  for (let i = 0; i < 140; i++) {
    points.push({
      request_id: `ref-${i}`,
      source: "reference",
      x: 0.35 + (Math.random() - 0.5) * 0.28,
      y: 0.45 + (Math.random() - 0.5) * 0.3,
      uncertainty: Math.random() * 0.2,
    });
  }

  /* Live cluster (shifted) */
  for (let i = 0; i < 80; i++) {
    points.push({
      request_id: `live-${i}`,
      source: "live",
      x: 0.58 + (Math.random() - 0.5) * 0.25,
      y: 0.55 + (Math.random() - 0.5) * 0.28,
      uncertainty: 0.2 + Math.random() * 0.5,
    });
  }

  /* Attack outliers */
  for (let i = 0; i < 12; i++) {
    points.push({
      request_id: `atk-${i}`,
      source: "live",
      x: 0.85 + (Math.random() - 0.5) * 0.15,
      y: 0.2 + (Math.random() - 0.5) * 0.2,
      uncertainty: 0.7 + Math.random() * 0.3,
    });
  }

  return points;
}

/* ── Mock MMD drift series ── */
export function generateMockMmdSeries(): number[] {
  const series: number[] = [];
  let value = 0.04;
  for (let i = 0; i < 40; i++) {
    value += (Math.random() - 0.45) * 0.015;
    value = Math.max(0.005, Math.min(0.35, value));
    if (i >= 25 && i <= 32) {
      value += 0.02 + Math.random() * 0.03;
      value = Math.min(0.35, value);
    }
    series.push(value);
  }
  return series;
}

/* ── Mock model comparison data ── */
export function generateMockModelComparison(realAccuracy: number, realDrift: number): ModelComparisonRow[] {
  return [
    {
      model: "Fresh_AI_Baseline",
      accuracy: 0.9812,
      driftPct: 1.2,
      vigor: 0.98,
      isShadow: true,
    },
    {
      model: "Production_Model",
      accuracy: realAccuracy,
      driftPct: realDrift * 100,
      vigor: realAccuracy,
      isShadow: false,
    },
    {
      model: "Gemini_Pro",
      accuracy: 0.9341 + (Math.random() - 0.5) * 0.02,
      driftPct: 4.2 + (Math.random() - 0.5) * 2,
      vigor: 0.9341 + (Math.random() - 0.5) * 0.02,
      isShadow: false,
    },
  ];
}

/* ── Mock parameter drift data ── */
export function generateMockParameterDrifts(topDriftMagnitude: number): ParameterDrift[] {
  const base = [
    { name: "sentiment", label: "Sentiment", drift: 0.12 + Math.random() * 0.08 },
    { name: "token_count", label: "Token_Count", drift: 0.08 + Math.random() * 0.06 },
    { name: "latency", label: "Latency", drift: 0.05 + Math.random() * 0.04 },
    { name: "embedding_energy", label: "Embedding_Energy", drift: 0.15 + Math.random() * 0.1 },
    { name: "response_length", label: "Response_Length", drift: 0.06 + Math.random() * 0.05 },
  ];

  /* Inject a "critical" parameter if drift is high */
  if (topDriftMagnitude > 0.15) {
    const critIdx = Math.floor(Math.random() * base.length);
    base[critIdx].drift = 0.7 + Math.random() * 0.25;
  }

  return base;
}

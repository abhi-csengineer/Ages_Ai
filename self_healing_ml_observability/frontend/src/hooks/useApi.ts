import {
  ActiveLearningCandidatesResponse,
  EmbeddingPointsResponse,
  RetrainWebhookResponse,
  SidecarInferenceRequest,
  SidecarInferenceResponse,
} from "../types/contracts";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function fetchActiveLearningCandidates(
  limit = 30,
): Promise<ActiveLearningCandidatesResponse> {
  const res = await fetch(
    `${API_BASE}/active-learning/candidates?limit=${limit}`,
  );
  if (!res.ok) {
    throw new Error(`active_learning_candidates_failed:${res.status}`);
  }
  return (await res.json()) as ActiveLearningCandidatesResponse;
}

export async function fetchEmbeddingPoints(
  limit = 300,
): Promise<EmbeddingPointsResponse> {
  const res = await fetch(`${API_BASE}/embedding-points?limit=${limit}`);
  if (!res.ok) {
    throw new Error(`embedding_points_failed:${res.status}`);
  }
  return (await res.json()) as EmbeddingPointsResponse;
}

export async function triggerRetrain(): Promise<RetrainWebhookResponse> {
  const payload = {
    receiver: "aegis-mission-control",
    status: "firing",
    alerts: [
      {
        status: "firing",
        labels: { alertname: "DriftAlert", severity: "critical" },
      },
    ],
  };
  const res = await fetch(`${API_BASE}/retrain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`retrain_failed:${res.status}`);
  }
  return (await res.json()) as RetrainWebhookResponse;
}

export async function inferSidecar(
  payload: SidecarInferenceRequest,
): Promise<SidecarInferenceResponse> {
  const res = await fetch(`${API_BASE}/api/v1/inference`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`sidecar_inference_failed:${res.status}`);
  }
  return (await res.json()) as SidecarInferenceResponse;
}

export const inferGemini = inferSidecar;

export async function collectHealerSamples(
  requestIds: string[],
): Promise<{ accepted: boolean; stored_rows: number }> {
  const res = await fetch(`${API_BASE}/api/v1/healer/collect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request_ids: requestIds }),
  });
  if (!res.ok) {
    throw new Error(`healer_collect_failed:${res.status}`);
  }
  return (await res.json()) as { accepted: boolean; stored_rows: number };
}

export function getTelemetryWsUrl(): string {
  const configured = import.meta.env.VITE_WS_URL as string | undefined;
  if (configured) {
    return configured;
  }
  const base = API_BASE.replace(/^http/, "ws");
  return `${base}/ws/telemetry`;
}

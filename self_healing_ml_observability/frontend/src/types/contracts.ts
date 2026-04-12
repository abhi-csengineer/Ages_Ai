export interface ActiveLearningCandidateItem {
  request_id: string;
  confidence: number;
  uncertainty: number;
}

export interface ActiveLearningCandidatesResponse {
  items: ActiveLearningCandidateItem[];
}

export interface EmbeddingPoint {
  request_id: string;
  source: "reference" | "live";
  x: number;
  y: number;
  uncertainty: number;
}

export interface EmbeddingPointsResponse {
  points: EmbeddingPoint[];
}

export interface RetrainWebhookResponse {
  accepted: boolean;
  action: string;
  promoted_rows: number;
  selected_rows: number;
  candidate_rows: number;
  data_efficiency_ratio: number;
}

export interface TelemetrySnapshot {
  timestamp: string;
  circuit_state: string;
  circuit_status: "OK" | "DRIFT_BIAS" | "SECURITY_ATTACK" | "FALLBACK_MODE";
  hui_walter_estimated_accuracy: number;
  psi_drift_score: number;
  mmd_drift_score: number;
  bias_score: number;
  reference_count: number;
  detection_count: number;
  batch_event: boolean;
  chaos_active: boolean;
}

export interface LiveTelemetryPayload {
  timestamp: string;
  request_id: string;
  status: "OK" | "DRIFT" | "ATTACK";
  accuracy: number;
  drift_magnitude: number;
  umap_x: number;
  umap_y: number;
}

export interface GeminiInferenceRequest {
  request_id: string;
  prompt: string;
  population_id?: number;
  demographic_group?: string;
}

export interface GeminiInferenceResponse {
  request_id: string;
  prompt: string;
  response_text: string;
  provider_model: string;
  mmd_drift_score: number;
  hui_walter_estimated_accuracy: number;
  status: "OK" | "DRIFT" | "ATTACK";
  umap_x: number;
  umap_y: number;
}

export interface SidecarInferenceRequest {
  request_id?: string;
  prompt: string;
  population_id?: number;
  demographic_group?: string;
}

export interface SidecarInferenceResponse {
  request_id: string;
  response_text: string;
  vigor: number;
  drift: number;
  coords: [number, number];
  attribution: Record<string, number>;
  log: string;
  embedding_dim: number;
  provider_model: string;
}

export interface SecurityLogEntry {
  timestamp: string;
  type: "BLOCKED" | "REDACTED" | "PASSED" | "ANOMALY";
  message: string;
  request_id?: string;
}

/* ── New types for Chakra dashboard ── */

export interface ModelComparisonRow {
  model: string;
  accuracy: number;
  driftPct: number;
  vigor: number;
  isShadow: boolean;
}

export interface ParameterDrift {
  name: string;
  drift: number;      /* 0-1 scale */
  label: string;      /* display name */
}

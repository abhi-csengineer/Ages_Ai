import { useCallback, useEffect, useRef, useState } from "react";
import {
  LiveTelemetryPayload,
  SecurityLogEntry,
  TelemetrySnapshot,
} from "../types/contracts";
import { getTelemetryWsUrl } from "./useApi";

/* ws/metrics is an alias — we connect to ws/telemetry which provides all needed data */

/* ── default state ── */
const EMPTY_TELEMETRY: TelemetrySnapshot = {
  timestamp: new Date().toISOString(),
  circuit_state: "closed",
  circuit_status: "OK",
  hui_walter_estimated_accuracy: 1,
  psi_drift_score: 0,
  mmd_drift_score: 0,
  bias_score: 0,
  reference_count: 0,
  detection_count: 0,
  batch_event: false,
  chaos_active: false,
};

export interface StreamOrb {
  id: string;
  x: number;
  y: number;
  status: "OK" | "DRIFT" | "ATTACK";
}

/* ── simulated security events for demo ── */
const SIMULATED_MESSAGES: Array<{ type: SecurityLogEntry["type"]; msg: string }> = [
  { type: "BLOCKED", msg: "Prompt injection detected: 'ignore previous instructions'" },
  { type: "REDACTED", msg: "PII redacted: email <REDACTED>@domain.com in response" },
  { type: "PASSED", msg: "Inference request validated — no anomalies" },
  { type: "ANOMALY", msg: "Embedding drift detected on feature vector #47" },
  { type: "BLOCKED", msg: "Jailbreak attempt: role swap payload intercepted" },
  { type: "REDACTED", msg: "PII redacted: SSN ***-**-**** in user prompt" },
  { type: "PASSED", msg: "Gemini proxy response latency: 142ms — nominal" },
  { type: "ANOMALY", msg: "Response divergence: cosine similarity 0.62 vs baseline 0.91" },
  { type: "BLOCKED", msg: "Adversarial suffix detected — request quarantined" },
  { type: "REDACTED", msg: "PII redacted: phone +1-***-***-**** in context" },
  { type: "PASSED", msg: "Batch inference complete — 48 requests processed" },
  { type: "ANOMALY", msg: "MMD score spike: 0.34 > threshold 0.20" },
  { type: "BLOCKED", msg: "DAN-mode prompt pattern matched — blocked" },
  { type: "PASSED", msg: "Model checkpoint v2.4.1 health verified" },
  { type: "REDACTED", msg: "PII redacted: credit card ****-****-****-**** in payload" },
];

const MAX_MMD_SERIES = 60;
const MAX_ORBS = 120;
const MAX_LOG_ENTRIES = 80;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

function toStatus(snapshot: TelemetrySnapshot): LiveTelemetryPayload["status"] {
  if (snapshot.circuit_status === "SECURITY_ATTACK") {
    return "ATTACK";
  }
  if (snapshot.circuit_status === "DRIFT_BIAS") {
    return "DRIFT";
  }
  return "OK";
}

function normalizeMessage(
  parsed: LiveTelemetryPayload | TelemetrySnapshot | Record<string, unknown>,
): LiveTelemetryPayload {
  const isObject = typeof parsed === "object" && parsed !== null;
  if (
    isObject &&
    "vigor" in parsed &&
    "drift" in parsed &&
    "coords" in parsed
  ) {
    const coords = Array.isArray(parsed.coords) ? parsed.coords : [0.5, 0.5];
    const drift = Number(parsed.drift ?? 0);
    const vigor = Number(parsed.vigor ?? 1);
    const status: LiveTelemetryPayload["status"] =
      drift > 35 ? "ATTACK" : drift > 20 ? "DRIFT" : "OK";
    return {
      timestamp:
        typeof parsed.timestamp === "string"
          ? parsed.timestamp
          : new Date().toISOString(),
      request_id:
        typeof parsed.request_id === "string"
          ? parsed.request_id
          : `sidecar-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      status,
      accuracy: Math.max(0, Math.min(1, vigor)),
      drift_magnitude: Math.max(0, Math.min(1, drift / 100)),
      umap_x: Math.max(0, Math.min(1, Number(coords[0] ?? 0.5))),
      umap_y: Math.max(0, Math.min(1, Number(coords[1] ?? 0.5))),
    };
  }

  if (
    isObject &&
    "request_id" in parsed &&
    "status" in parsed &&
    "accuracy" in parsed &&
    "drift_magnitude" in parsed
  ) {
    return {
      timestamp:
        typeof parsed.timestamp === "string"
          ? parsed.timestamp
          : new Date().toISOString(),
      request_id: String(parsed.request_id),
      status:
        parsed.status === "ATTACK" || parsed.status === "DRIFT" || parsed.status === "OK"
          ? parsed.status
          : "OK",
      accuracy: Number(parsed.accuracy ?? 0),
      drift_magnitude: Number(parsed.drift_magnitude ?? 0),
      umap_x: Math.max(0, Math.min(1, Number(parsed.umap_x ?? 0.5))),
      umap_y: Math.max(0, Math.min(1, Number(parsed.umap_y ?? 0.5))),
    };
  }

  const snapshot = parsed as TelemetrySnapshot;
  const requestId = `snapshot-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  return {
    timestamp:
      typeof snapshot.timestamp === "string"
        ? snapshot.timestamp
        : new Date().toISOString(),
    request_id: requestId,
    status: toStatus(snapshot),
    accuracy: Number(snapshot.hui_walter_estimated_accuracy ?? 1),
    drift_magnitude: Number(snapshot.mmd_drift_score ?? 0),
    // Snapshot stream does not include UMAP coordinates; keep in-bounds defaults.
    umap_x: 0.5,
    umap_y: 0.5,
  };
}

export function useAegisStream() {
  /* ── public state (React renders only on RAF flush) ── */
  const [telemetry, setTelemetry] = useState<TelemetrySnapshot>(EMPTY_TELEMETRY);
  const [mmdSeries, setMmdSeries] = useState<number[]>([]);
  const [streamOrbs, setStreamOrbs] = useState<StreamOrb[]>([]);
  const [securityLog, setSecurityLog] = useState<SecurityLogEntry[]>([]);
  const [connected, setConnected] = useState(false);

  /* ── internal buffers (mutated per-message, flushed per-frame) ── */
  const bufferRef = useRef<LiveTelemetryPayload[]>([]);
  const rafRef = useRef<number>(0);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const simIndexRef = useRef(0);
  const mountedRef = useRef(true);
  const [hasReceivedData, setHasReceivedData] = useState(false);

  /* ── RAF flush: batch-merge buffered messages into React state ── */
  const flushBuffer = useCallback(() => {
    const batch = bufferRef.current.splice(0);
    if (batch.length === 0) {
      rafRef.current = requestAnimationFrame(flushBuffer);
      return;
    }

    const latest = batch[batch.length - 1];
    setHasReceivedData(true);

    setTelemetry((prev) => ({
      ...prev,
      timestamp: latest.timestamp,
      circuit_status:
        latest.status === "ATTACK"
          ? "SECURITY_ATTACK"
          : latest.status === "DRIFT"
            ? "DRIFT_BIAS"
            : "OK",
      hui_walter_estimated_accuracy: latest.accuracy,
      mmd_drift_score: latest.drift_magnitude,
      batch_event: true,
      chaos_active: latest.status !== "OK",
    }));

    setMmdSeries((prev) => {
      const additions = batch.map((p) => p.drift_magnitude);
      return [...prev, ...additions].slice(-MAX_MMD_SERIES);
    });

    setStreamOrbs((prev) => {
      const newOrbs: StreamOrb[] = batch.map((p) => ({
        id: `${p.request_id}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        x: p.umap_x,
        y: p.umap_y,
        status: p.status,
      }));
      return [...prev, ...newOrbs].slice(-MAX_ORBS);
    });

    /* ── generate security log entries from real telemetry ── */
    const logEntries: SecurityLogEntry[] = batch.map((p) => {
      let type: SecurityLogEntry["type"] = "PASSED";
      let message = `Inference ${p.request_id.slice(0, 8)} — nominal`;
      if (p.status === "ATTACK") {
        type = "BLOCKED";
        message = `Adversarial payload intercepted on req ${p.request_id.slice(0, 8)}`;
      } else if (p.status === "DRIFT") {
        type = "ANOMALY";
        message = `Drift detected: MMD=${p.drift_magnitude.toFixed(4)} on req ${p.request_id.slice(0, 8)}`;
      }
      return {
        timestamp: p.timestamp,
        type,
        message,
        request_id: p.request_id,
      };
    });

    setSecurityLog((prev) => [...prev, ...logEntries].slice(-MAX_LOG_ENTRIES));

    rafRef.current = requestAnimationFrame(flushBuffer);
  }, []);

  /* ── connect WebSocket with exponential backoff ── */
  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    try {
      const ws = new WebSocket(getTelemetryWsUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        reconnectAttempts.current = 0;
        ws.send("subscribe");
      };

      ws.onmessage = (ev) => {
        try {
          const parsed = JSON.parse(ev.data) as
            | LiveTelemetryPayload
            | TelemetrySnapshot
            | Record<string, unknown>;
          bufferRef.current.push(normalizeMessage(parsed));
        } catch {
          /* ignore malformed messages */
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (!mountedRef.current) return;
        const delay = Math.min(
          RECONNECT_BASE_MS * Math.pow(2, reconnectAttempts.current) +
            Math.random() * 500,
          RECONNECT_MAX_MS,
        );
        reconnectAttempts.current++;
        reconnectTimer.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      /* WebSocket constructor can throw in some environments */
      setConnected(false);
    }
  }, []);

  /* ── simulated event generator for demo mode ── */
  useEffect(() => {
    const interval = setInterval(() => {
      if (!mountedRef.current) return;
      const sim = SIMULATED_MESSAGES[simIndexRef.current % SIMULATED_MESSAGES.length];
      simIndexRef.current++;
      const entry: SecurityLogEntry = {
        timestamp: new Date().toISOString(),
        type: sim.type,
        message: sim.msg,
      };
      setSecurityLog((prev) => [...prev, entry].slice(-MAX_LOG_ENTRIES));
    }, 2200);

    return () => clearInterval(interval);
  }, []);

  /* ── lifecycle ── */
  useEffect(() => {
    mountedRef.current = true;
    rafRef.current = requestAnimationFrame(flushBuffer);
    connect();

    return () => {
      mountedRef.current = false;
      cancelAnimationFrame(rafRef.current);
      wsRef.current?.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [connect, flushBuffer]);

  const tripped =
    telemetry.circuit_status === "DRIFT_BIAS" ||
    telemetry.circuit_status === "FALLBACK_MODE" ||
    telemetry.circuit_status === "SECURITY_ATTACK";

  return {
    telemetry,
    mmdSeries,
    streamOrbs,
    securityLog,
    connected,
    tripped,
    hasReceivedData,
  };
}

import { useEffect, useMemo, useState } from "react";
import { LiveTelemetryPayload, TelemetrySnapshot } from "../types/contracts";
import { getTelemetryWsUrl } from "./useApi";

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

export function useWebSocket() {
  const [telemetry, setTelemetry] = useState<TelemetrySnapshot>(EMPTY_TELEMETRY);
  const [connected, setConnected] = useState(false);
  const [mmdSeries, setMmdSeries] = useState<number[]>([]);
  const [streamOrbs, setStreamOrbs] = useState<StreamOrb[]>([]);

  useEffect(() => {
    const ws = new WebSocket(getTelemetryWsUrl());

    ws.onopen = () => {
      setConnected(true);
      ws.send("subscribe");
    };
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (ev) => {
      const parsed = JSON.parse(ev.data) as LiveTelemetryPayload;
      setTelemetry((prev) => ({
        ...prev,
        timestamp: parsed.timestamp,
        circuit_status: parsed.status === "ATTACK" ? "SECURITY_ATTACK" : parsed.status === "DRIFT" ? "DRIFT_BIAS" : "OK",
        hui_walter_estimated_accuracy: parsed.accuracy,
        mmd_drift_score: parsed.drift_magnitude,
        batch_event: true,
        chaos_active: parsed.status !== "OK",
      }));
      setMmdSeries((prev) => [...prev, parsed.drift_magnitude].slice(-60));
      setStreamOrbs((prev) => {
        const orb: StreamOrb = {
          id: `${parsed.request_id}-${Date.now()}`,
          x: parsed.umap_x,
          y: parsed.umap_y,
          status: parsed.status,
        };
        return [...prev, orb].slice(-120);
      });
    };

    return () => ws.close();
  }, []);

  const tripped = useMemo(
    () => telemetry.circuit_status === "DRIFT_BIAS" || telemetry.circuit_status === "FALLBACK_MODE",
    [telemetry.circuit_status]
  );

  return {
    telemetry,
    connected,
    mmdSeries,
    streamOrbs,
    tripped,
  };
}
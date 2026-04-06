import { useEffect, useMemo, useRef, useState } from "react";
import { TelemetrySnapshot } from "../types/contracts";
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

export function useTelemetrySocket() {
  const [telemetry, setTelemetry] = useState<TelemetrySnapshot>(EMPTY_TELEMETRY);
  const [connected, setConnected] = useState(false);
  const [mmdSeries, setMmdSeries] = useState<number[]>([]);
  const lastDetectionCount = useRef<number>(-1);

  useEffect(() => {
    const ws = new WebSocket(getTelemetryWsUrl());

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (ev) => {
      const parsed = JSON.parse(ev.data) as TelemetrySnapshot;
      setTelemetry(parsed);

      const batchTick = parsed.batch_event || parsed.detection_count !== lastDetectionCount.current;
      if (batchTick) {
        setMmdSeries((prev) => {
          const next = [...prev, parsed.mmd_drift_score];
          return next.slice(-40);
        });
      }
      lastDetectionCount.current = parsed.detection_count;
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
    tripped,
  };
}

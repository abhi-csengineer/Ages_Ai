import { motion } from "framer-motion";
import { Crosshair, TrendingDown, TrendingUp } from "lucide-react";

interface VigorMeterProps {
  accuracy: number;
  mmdDrift: number;
  biasScore: number;
  mmdSeries: number[];
}

const MotionLine = motion.line;

export function VigorMeter({ accuracy, mmdDrift, biasScore, mmdSeries }: VigorMeterProps) {
  const pct = Math.max(0, Math.min(100, accuracy * 100));
  const isCritical = accuracy < 0.90;
  const isDegraded = accuracy < 0.95 && accuracy >= 0.90;
  const needleDeg = -120 + (pct / 100) * 240;
  const arcOffset = 1 - pct / 100;

  const statusLabel = isCritical ? "CRITICAL" : isDegraded ? "DEGRADED" : "NOMINAL";
  const statusColor = isCritical
    ? "text-aegis-red"
    : isDegraded
      ? "text-aegis-orange"
      : "text-aegis-cyan";

  /* sparkline path from mmdSeries */
  const sparkData = mmdSeries.length > 0 ? mmdSeries.slice(-30) : [0];
  const sparkMax = Math.max(...sparkData, 0.01);
  const sparkW = 200;
  const sparkH = 28;
  const sparkPath = sparkData
    .map((v, i) => {
      const x = (i / Math.max(sparkData.length - 1, 1)) * sparkW;
      const y = sparkH - (v / sparkMax) * sparkH;
      return `${i === 0 ? "M" : "L"}${x},${y}`;
    })
    .join(" ");

  return (
    <div
      className={`tile h-full flex flex-col ${
        isCritical ? "crt-glitch scanline-overlay border-aegis-red border-glow-red" : ""
      }`}
    >
      <div className="tile-header flex items-center justify-between">
        <span>TILE-A // VIGOR METER</span>
        <Crosshair className="w-3 h-3 text-aegis-cyan/30" />
      </div>

      <div className="tile-body flex-1 flex flex-col items-center justify-center gap-3">
        {/* Status Badge */}
        <div className="flex items-center gap-2">
          <span
            className={`status-led ${
              isCritical ? "status-led--alert" : isDegraded ? "status-led--warn" : "status-led--ok"
            }`}
          />
          <span className={`text-[0.65rem] tracking-[0.15em] uppercase ${statusColor}`}>
            {statusLabel}
          </span>
        </div>

        {/* Giant Digital Readout */}
        <div className={`digital-readout text-5xl font-bold ${isCritical ? "crt-text-glitch" : ""} ${statusColor}`}>
          {accuracy.toFixed(4)}
        </div>
        <span className="text-[0.55rem] tracking-[0.2em] uppercase text-aegis-cyan/40">
          HUI-WALTER ESTIMATED ACCURACY
        </span>

        {/* SVG Gauge Arc */}
        <div className="relative w-[160px] h-[90px] mt-1">
          <svg viewBox="0 0 200 110" width="100%" height="100%">
            {/* Track */}
            <path
              d="M 24 100 A 76 76 0 0 1 176 100"
              fill="none"
              stroke="#2D3748"
              strokeWidth="6"
            />
            {/* Fill */}
            <path
              d="M 24 100 A 76 76 0 0 1 176 100"
              fill="none"
              stroke={isCritical ? "#FF0033" : isDegraded ? "#FF4500" : "#00FFFF"}
              strokeWidth="6"
              pathLength={1}
              strokeDasharray={1}
              strokeDashoffset={arcOffset}
            />
            {/* Needle */}
            <g transform="translate(100,100)">
              <MotionLine
                x1="0" y1="0" x2="0" y2="-58"
                stroke={isCritical ? "#FF0033" : "#00FFFF"}
                strokeWidth="2"
                animate={{ rotate: needleDeg }}
                transition={{ type: "spring", stiffness: 130, damping: 12, mass: 0.55 }}
                style={{ transformOrigin: "0px 0px" }}
              />
              <rect x="-3" y="-3" width="6" height="6" fill={isCritical ? "#FF0033" : "#00FFFF"} />
            </g>
          </svg>
        </div>

        {/* Secondary Stats Row */}
        <div className="grid grid-cols-3 gap-2 w-full mt-1">
          <div className="border border-aegis-border p-2 text-center">
            <div className="text-[0.5rem] text-aegis-cyan/40 tracking-wider uppercase">MMD DRIFT</div>
            <div className={`digital-readout text-sm ${mmdDrift > 0.2 ? "text-aegis-orange" : "text-aegis-cyan"}`}>
              {mmdDrift.toFixed(4)}
            </div>
          </div>
          <div className="border border-aegis-border p-2 text-center">
            <div className="text-[0.5rem] text-aegis-cyan/40 tracking-wider uppercase">BIAS</div>
            <div className="digital-readout text-sm text-aegis-cyan">
              {biasScore.toFixed(4)}
            </div>
          </div>
          <div className="border border-aegis-border p-2 text-center">
            <div className="text-[0.5rem] text-aegis-cyan/40 tracking-wider uppercase">TREND</div>
            <div className="flex items-center justify-center gap-1">
              {mmdDrift > 0.15 ? (
                <TrendingUp className="w-3.5 h-3.5 text-aegis-orange" />
              ) : (
                <TrendingDown className="w-3.5 h-3.5 text-aegis-green" />
              )}
            </div>
          </div>
        </div>

        {/* MMD Sparkline */}
        <div className="w-full border border-aegis-border p-2 mt-1">
          <div className="text-[0.5rem] text-aegis-cyan/40 tracking-wider uppercase mb-1">MMD MAGNITUDE</div>
          <svg viewBox={`0 0 ${sparkW} ${sparkH}`} width="100%" height="28" className="block">
            <path d={sparkPath} fill="none" stroke="#00FFFF" strokeWidth="1.5" opacity="0.7" />
          </svg>
        </div>
      </div>
    </div>
  );
}

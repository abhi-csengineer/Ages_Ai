import { motion } from "framer-motion";
import { useMemo } from "react";
import { Scan } from "lucide-react";
import { EmbeddingPoint } from "../types/contracts";
import { StreamOrb } from "../hooks/useAegisStream";

interface VoidUmapProps {
  points: EmbeddingPoint[];
  mmdDrift: number;
  streamOrbs: StreamOrb[];
  pulseTick: number;
}

const MotionCircle = motion.circle;

const W = 1000;
const H = 500;
const PAD = 16;

export function VoidUmap({ points, mmdDrift, streamOrbs, pulseTick }: VoidUmapProps) {
  const reference = useMemo(() => points.filter((p) => p.source === "reference"), [points]);
  const live = useMemo(() => points.filter((p) => p.source === "live"), [points]);

  const bounds = useMemo(() => {
    const all = points.length > 0 ? points : [{ x: 0, y: 0 }];
    const xs = all.map((p) => p.x);
    const ys = all.map((p) => p.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    return {
      minX, maxX, minY, maxY,
      spanX: Math.max(maxX - minX, 1e-6),
      spanY: Math.max(maxY - minY, 1e-6),
    };
  }, [points]);

  const project = (x: number, y: number) => ({
    x: PAD + ((x - bounds.minX) / bounds.spanX) * (W - PAD * 2),
    y: H - PAD - ((y - bounds.minY) / bounds.spanY) * (H - PAD * 2),
  });

  /* grid lines */
  const gridLines = useMemo(() => {
    const lines: JSX.Element[] = [];
    const cols = 20;
    const rows = 12;
    for (let i = 0; i <= cols; i++) {
      const x = PAD + (i / cols) * (W - PAD * 2);
      lines.push(
        <line key={`v${i}`} x1={x} y1={PAD} x2={x} y2={H - PAD}
          stroke="#00FFFF" strokeWidth="0.5" opacity="0.04" />
      );
    }
    for (let i = 0; i <= rows; i++) {
      const y = PAD + (i / rows) * (H - PAD * 2);
      lines.push(
        <line key={`h${i}`} x1={PAD} y1={y} x2={W - PAD} y2={y}
          stroke="#00FFFF" strokeWidth="0.5" opacity="0.04" />
      );
    }
    return lines;
  }, []);

  const orbColor = (status: string) =>
    status === "ATTACK" ? "#FF0033" : status === "DRIFT" ? "#FF4500" : "#00FFFF";

  return (
    <div className="tile h-full flex flex-col">
      <div className="tile-header flex items-center justify-between">
        <span>TILE-B // VOID UMAP 2D</span>
        <div className="flex items-center gap-2">
          <Scan className="w-3 h-3 text-aegis-cyan/30" />
          <span className={`text-[0.55rem] ${mmdDrift > 0.2 ? "text-aegis-orange" : "text-aegis-cyan/50"}`}>
            DRIFT: {mmdDrift.toFixed(4)}
          </span>
        </div>
      </div>

      <div className="flex-1 relative" style={{ cursor: "crosshair" }}>
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%"
          className="block absolute inset-0 w-full h-full"
          preserveAspectRatio="xMidYMid meet"
        >
          <rect width={W} height={H} fill="#050505" />

          {/* Grid */}
          {gridLines}

          {/* Glow filter */}
          <defs>
            <filter id="umap-glow" x="-80%" y="-80%" width="260%" height="260%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Shockwave ring on new data */}
          <motion.circle
            key={`shockwave-${pulseTick}`}
            cx={W / 2} cy={H / 2} r="20"
            fill="none" stroke="#00FFFF" strokeWidth="1"
            initial={{ opacity: 0.6, scale: 0.5 }}
            animate={{ opacity: 0, scale: 8 }}
            transition={{ duration: 1.2, ease: "easeOut" }}
          />

          {/* Reference Points - dim cyan */}
          {reference.map((p, idx) => {
            const pt = project(p.x, p.y);
            return (
              <MotionCircle
                key={`ref-${p.request_id}-${idx}`}
                cx={pt.x} cy={pt.y} r={3}
                fill="#00FFFF" opacity={0.25}
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 0.25, scale: 1 }}
                transition={{ duration: 0.3, delay: Math.min(idx * 0.002, 0.3) }}
              />
            );
          })}

          {/* Live Points - bright */}
          {live.map((p, idx) => {
            const pt = project(p.x, p.y);
            return (
              <MotionCircle
                key={`live-${p.request_id}-${idx}`}
                cx={pt.x} cy={pt.y} r={4.5}
                fill="#FF4500" filter="url(#umap-glow)"
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 0.85, scale: 1 }}
                transition={{ duration: 0.4, delay: Math.min(idx * 0.003, 0.4) }}
                style={{ mixBlendMode: "screen" }}
              />
            );
          })}

          {/* Stream Orbs - pulsing new arrivals */}
          {streamOrbs.map((orb) => {
            const pt = project(orb.x, orb.y);
            return (
              <MotionCircle
                key={orb.id}
                cx={pt.x} cy={pt.y} r={6}
                fill={orbColor(orb.status)}
                filter="url(#umap-glow)"
                initial={{ opacity: 0, scale: 0 }}
                animate={{
                  opacity: [1, 0.4],
                  scale: [1.4, 0.8],
                }}
                transition={{ duration: 1.2, ease: "easeOut" }}
                style={{ mixBlendMode: "screen" }}
              />
            );
          })}

          {/* Crosshair center indicator */}
          <line x1={W / 2 - 15} y1={H / 2} x2={W / 2 + 15} y2={H / 2}
            stroke="#00FFFF" strokeWidth="0.5" opacity="0.15" />
          <line x1={W / 2} y1={H / 2 - 15} x2={W / 2} y2={H / 2 + 15}
            stroke="#00FFFF" strokeWidth="0.5" opacity="0.15" />
        </svg>

        {/* Legend overlay */}
        <div className="absolute bottom-2 left-2 flex gap-3 z-10">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 bg-aegis-cyan/25 inline-block" />
            <span className="text-[0.5rem] text-aegis-cyan/40 uppercase tracking-wider">REF</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 bg-aegis-orange inline-block" />
            <span className="text-[0.5rem] text-aegis-cyan/40 uppercase tracking-wider">LIVE</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 bg-aegis-red inline-block" />
            <span className="text-[0.5rem] text-aegis-cyan/40 uppercase tracking-wider">ATTACK</span>
          </div>
        </div>
      </div>
    </div>
  );
}

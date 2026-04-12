import { Database, Cpu, Zap } from "lucide-react";

interface StatusBarProps {
  queueCount: number;
  retraining: boolean;
  progress: number;
  driftScore: number;
}

export function StatusBar({ queueCount, retraining, progress, driftScore }: StatusBarProps) {
  return (
    <footer className="border-t-2 border-aegis-border bg-aegis-black px-4 py-2 flex items-center justify-between text-[0.6rem] tracking-[0.1em] uppercase">
      {/* Left stats */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <Database className="w-3 h-3 text-aegis-cyan/40" />
          <span className="text-aegis-cyan/50">
            QUEUE: <span className="text-aegis-cyan">{queueCount}</span>
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <Zap className="w-3 h-3 text-aegis-cyan/40" />
          <span className="text-aegis-cyan/50">
            MMD: <span className={driftScore > 0.2 ? "text-aegis-orange" : "text-aegis-cyan"}>{driftScore.toFixed(4)}</span>
          </span>
        </div>
      </div>

      {/* Center: retrain progress */}
      {retraining && (
        <div className="flex items-center gap-2 flex-1 max-w-xs mx-4">
          <Cpu className="w-3 h-3 text-aegis-orange animate-pulse" />
          <div className="flex-1 h-1 bg-aegis-border">
            <div
              className="h-full bg-aegis-orange transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="text-aegis-orange">{progress}%</span>
        </div>
      )}

      {/* Right: System ID */}
      <div className="flex items-center gap-2">
        <span className="text-aegis-cyan/30">SYS ID: AEGIS-7A</span>
        <span className="text-aegis-cyan/20">|</span>
        <span className="text-aegis-cyan/30">v2.4.1</span>
      </div>
    </footer>
  );
}

import { useEffect, useState } from "react";
import { Activity, Radio, Wifi, WifiOff } from "lucide-react";

interface HeaderBarProps {
  connected: boolean;
  circuitStatus: string;
  tripped: boolean;
}

export function HeaderBar({ connected, circuitStatus, tripped }: HeaderBarProps) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const statusText = tripped
    ? circuitStatus === "SECURITY_ATTACK"
      ? "THREAT DETECTED"
      : "DRIFT ALERT"
    : "ALL SYSTEMS NOMINAL";

  return (
    <header className="border-b-2 border-aegis-border bg-aegis-black px-4 py-3 flex items-center justify-between">
      {/* Left: Logo & Title */}
      <div className="flex items-center gap-3">
        <Activity className="w-5 h-5 text-aegis-cyan" />
        <h1 className="font-display text-sm tracking-[0.25em] text-aegis-cyan uppercase">
          AEGIS-AI
        </h1>
        <span className="text-[0.6rem] tracking-[0.15em] text-aegis-cyan/30 uppercase hidden sm:inline">
          // TACTICAL COMMAND
        </span>
      </div>

      {/* Center: Status */}
      <div className="flex items-center gap-3">
        <span
          className={`status-led ${
            tripped ? "status-led--alert" : "status-led--ok"
          }`}
        />
        <span
          className={`text-[0.65rem] tracking-[0.12em] uppercase ${
            tripped ? "text-aegis-red" : "text-aegis-green"
          }`}
        >
          {statusText}
        </span>
      </div>

      {/* Right: Connection & Clock */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          {connected ? (
            <Wifi className="w-3.5 h-3.5 text-aegis-green" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-aegis-red" />
          )}
          <span className="text-[0.6rem] text-aegis-cyan/40 uppercase tracking-wider">
            {connected ? "LIVE" : "OFFLINE"}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <Radio className="w-3 h-3 text-aegis-cyan/30" />
          <time className="text-[0.65rem] text-aegis-cyan/50 font-mono tabular-nums">
            {time.toLocaleTimeString("en-US", { hour12: false })}
          </time>
        </div>
      </div>
    </header>
  );
}

import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { Terminal, Send } from "lucide-react";
import { SecurityLogEntry } from "../types/contracts";
import { inferGemini } from "../hooks/useApi";

interface InferenceSidecarProps {
  securityLog: SecurityLogEntry[];
}

const typeColors: Record<SecurityLogEntry["type"], string> = {
  BLOCKED: "text-aegis-red",
  REDACTED: "text-aegis-orange",
  PASSED: "text-aegis-cyan/60",
  ANOMALY: "text-aegis-yellow",
};

const typeBg: Record<SecurityLogEntry["type"], string> = {
  BLOCKED: "bg-aegis-red/10",
  REDACTED: "bg-aegis-orange/10",
  PASSED: "bg-transparent",
  ANOMALY: "bg-aegis-yellow/10",
};

const typeLabel: Record<SecurityLogEntry["type"], string> = {
  BLOCKED: "BLKD",
  REDACTED: "RDCT",
  PASSED: "PASS",
  ANOMALY: "ANOM",
};

export function InferenceSidecar({ securityLog }: InferenceSidecarProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [prompt, setPrompt] = useState("");
  const [inferLoading, setInferLoading] = useState(false);

  /* auto-scroll to bottom */
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [securityLog.length]);

  const handleInfer = async () => {
    if (!prompt.trim() || inferLoading) return;
    setInferLoading(true);
    try {
      await inferGemini({
        request_id: crypto.randomUUID(),
        prompt,
        population_id: 0,
        demographic_group: "general",
      });
      setPrompt("");
    } catch {
      /* handled gracefully */
    } finally {
      setInferLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleInfer();
    }
  };

  const formatTime = (ts: string) => {
    try {
      return new Date(ts).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return "--:--:--";
    }
  };

  return (
    <div className="tile h-full flex flex-col">
      <div className="tile-header flex items-center justify-between">
        <span>TILE-C // INFERENCE SIDECAR</span>
        <Terminal className="w-3 h-3 text-aegis-cyan/30" />
      </div>

      {/* Terminal Feed */}
      <div ref={scrollRef} className="flex-1 terminal-scroll p-2 font-mono text-[0.6rem] leading-relaxed space-y-0.5 min-h-0">
        {securityLog.map((entry, idx) => (
          <motion.div
            key={`${entry.timestamp}-${idx}`}
            className={`flex gap-2 px-1 py-0.5 ${typeBg[entry.type]}`}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2 }}
          >
            <span className="text-aegis-cyan/25 flex-shrink-0 w-[52px]">
              {formatTime(entry.timestamp)}
            </span>
            <span className={`flex-shrink-0 w-[32px] font-bold ${typeColors[entry.type]}`}>
              [{typeLabel[entry.type]}]
            </span>
            <span className={`${typeColors[entry.type]} flex-1`}>
              {entry.message}
            </span>
          </motion.div>
        ))}
        {securityLog.length === 0 && (
          <div className="text-aegis-cyan/20 text-center py-8">
            AWAITING TELEMETRY STREAM...
            <span className="animate-blink">_</span>
          </div>
        )}
      </div>

      {/* Prompt Input */}
      <div className="border-t border-aegis-border p-2 flex gap-2">
        <div className="flex items-center text-aegis-cyan/30 text-[0.6rem] flex-shrink-0">
          {">_"}
        </div>
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="gemini proxy inference..."
          className="flex-1 bg-transparent border-none outline-none text-aegis-cyan text-[0.65rem] font-mono placeholder:text-aegis-cyan/15"
        />
        <button
          onClick={handleInfer}
          disabled={inferLoading || !prompt.trim()}
          className="text-aegis-cyan/50 hover:text-aegis-cyan disabled:text-aegis-cyan/15 transition-colors"
        >
          <Send className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}

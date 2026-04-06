import { Box, Checkbox, HStack, Text, VStack } from "@chakra-ui/react";
import { motion } from "framer-motion";
import { useMemo, useState } from "react";
import { EmbeddingPoint } from "../types/contracts";
import { StreamOrb } from "../hooks/useWebSocket";

interface UmapProjectionPanelProps {
  points: EmbeddingPoint[];
  mmdDrift: number;
  pulseTick?: number;
  streamOrbs?: StreamOrb[];
  onLassoSelect?: (requestIds: string[]) => void;
}

function mean(xs: number[]): number {
  if (xs.length === 0) {
    return 0;
  }
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}

const MotionCircle = motion.circle;

export function UmapProjectionPanel({
  points,
  mmdDrift,
  pulseTick = 0,
  streamOrbs = [],
  onLassoSelect,
}: UmapProjectionPanelProps) {
  const [showReference, setShowReference] = useState(true);
  const [showLive, setShowLive] = useState(true);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const reference = useMemo(
    () => points.filter((p) => p.source === "reference"),
    [points],
  );
  const live = useMemo(
    () => points.filter((p) => p.source === "live"),
    [points],
  );

  const bounds = useMemo(() => {
    const all = points.length > 0 ? points : [{ x: 0, y: 0 }];
    const xs = all.map((p) => p.x);
    const ys = all.map((p) => p.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    return {
      minX,
      maxX,
      minY,
      maxY,
      spanX: Math.max(maxX - minX, 1e-6),
      spanY: Math.max(maxY - minY, 1e-6),
    };
  }, [points]);

  const axisShiftPct = useMemo(() => {
    const refMean = mean(reference.map((p) => p.x));
    const liveMean = mean(live.map((p) => p.x));
    const denom = Math.max(Math.abs(refMean), 1e-6);
    return Math.abs((liveMean - refMean) / denom) * 100;
  }, [reference, live]);

  const project = (p: EmbeddingPoint) => {
    const width = 1000;
    const height = 420;
    const pad = 24;
    const x = pad + ((p.x - bounds.minX) / bounds.spanX) * (width - pad * 2);
    const y =
      height - pad - ((p.y - bounds.minY) / bounds.spanY) * (height - pad * 2);
    return { x, y };
  };

  const projectOrb = (orb: StreamOrb) => {
    const width = 1000;
    const height = 420;
    const pad = 24;
    return {
      x: pad + orb.x * (width - pad * 2),
      y: height - pad - orb.y * (height - pad * 2),
    };
  };

  const toggleLiveSelection = (requestId: string) => {
    setSelectedIds((prev) => {
      const exists = prev.includes(requestId);
      const next = exists
        ? prev.filter((id) => id !== requestId)
        : [...prev, requestId];
      onLassoSelect?.(next);
      return next;
    });
  };

  return (
    <Box p={4} layerStyle="glassPanel">
      <HStack justify="space-between" align="start" mb={3}>
        <VStack align="start" spacing={0}>
          <Text fontSize="sm" color="whiteAlpha.900" fontWeight="bold">
            UMAP 2D Projection
          </Text>
          <Text fontSize="xs" color="whiteAlpha.700">
            Embedding Space Drift
          </Text>
        </VStack>
        <Text fontSize="xs" color="whiteAlpha.700">
          Click live points to stage samples for Healer
        </Text>
      </HStack>

      <HStack align="stretch" spacing={3}>
        <VStack
          minW="170px"
          align="stretch"
          spacing={3}
          p={3}
          borderRadius="md"
          border="1px solid"
          borderColor="whiteAlpha.200"
          bg="whiteAlpha.100"
        >
          <Text
            fontSize="xs"
            textTransform="uppercase"
            letterSpacing="0.08em"
            color="whiteAlpha.700"
          >
            Legend Filters
          </Text>
          <Checkbox
            isChecked={showReference}
            onChange={(e) => setShowReference(e.target.checked)}
            colorScheme="blue"
          >
            <Text fontSize="sm" color="whiteAlpha.900">
              Reference
            </Text>
          </Checkbox>
          <Checkbox
            isChecked={showLive}
            onChange={(e) => setShowLive(e.target.checked)}
            colorScheme="blue"
          >
            <Text fontSize="sm" color="whiteAlpha.900">
              Live
            </Text>
          </Checkbox>
          <Text fontSize="xs" color="whiteAlpha.600">
            Selected: {selectedIds.length}
          </Text>
        </VStack>

        <Box flex="1" bg="rgba(12, 16, 22, 0.55)" borderRadius="md" p={2}>
          <svg
            viewBox="0 0 1000 420"
            width="100%"
            height="360"
            style={{ display: "block" }}
          >
            <defs>
              <filter
                id="live-glow"
                x="-50%"
                y="-50%"
                width="200%"
                height="200%"
              >
                <feGaussianBlur stdDeviation="3.5" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            <motion.circle
              key={`pulse-${pulseTick}`}
              cx="500"
              cy="210"
              r="18"
              fill="none"
              stroke="rgba(34, 211, 238, 0.65)"
              strokeWidth="2"
              initial={{ opacity: 0.8, scale: 0.4 }}
              animate={{ opacity: 0, scale: 6 }}
              transition={{ duration: 1.15, ease: "easeOut" }}
            />

            {showReference &&
              reference.map((p, idx) => {
                const pt = project(p);
                return (
                  <MotionCircle
                    key={`ref-${p.request_id}-${idx}`}
                    cx={pt.x}
                    cy={pt.y}
                    r={3.5}
                    fill="rgba(97, 140, 186, 0.45)"
                    initial={{ opacity: 0, scale: 0.3 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true, amount: 0.3 }}
                    transition={{
                      duration: 0.35,
                      delay: Math.min(idx * 0.003, 0.35),
                    }}
                    style={{ mixBlendMode: "screen" }}
                  />
                );
              })}

            {showLive &&
              live.map((p, idx) => {
                const pt = project(p);
                const selected = selectedIds.includes(p.request_id);
                return (
                  <MotionCircle
                    key={`live-${p.request_id}-${idx}`}
                    cx={pt.x}
                    cy={pt.y}
                    r={selected ? 6 : 4.5}
                    fill={selected ? "#FB7185" : "#F97316"}
                    filter="url(#live-glow)"
                    initial={{ opacity: 0, scale: 0.2 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true, amount: 0.3 }}
                    transition={{
                      duration: 0.45,
                      delay: Math.min(idx * 0.004, 0.45),
                    }}
                    whileHover={{ scale: 1.25 }}
                    onClick={() => toggleLiveSelection(p.request_id)}
                    style={{ mixBlendMode: "screen", cursor: "pointer" }}
                  />
                );
              })}

            {showLive &&
              streamOrbs.map((orb) => {
                const pt = projectOrb(orb);
                const color =
                  orb.status === "ATTACK"
                    ? "#FB7185"
                    : orb.status === "DRIFT"
                      ? "#F97316"
                      : "#22D3EE";
                return (
                  <MotionCircle
                    key={orb.id}
                    cx={pt.x}
                    cy={pt.y}
                    r={5}
                    fill={color}
                    filter="url(#live-glow)"
                    initial={{ opacity: 0, scale: 0.1 }}
                    animate={{ opacity: [0.9, 0.5], scale: [1.2, 0.75] }}
                    transition={{ duration: 1.0, ease: "easeOut" }}
                    style={{ mixBlendMode: "screen" }}
                  />
                );
              })}
          </svg>
        </Box>
      </HStack>

      <Box
        mt={3}
        p={3}
        borderRadius="md"
        bg="whiteAlpha.100"
        border="1px solid"
        borderColor="whiteAlpha.200"
      >
        <Text fontSize="sm" color="whiteAlpha.900">
          Prescriptive Summary: The Live cluster has shifted{" "}
          {axisShiftPct.toFixed(0)}% along Axis-1. This matches the MMD Drift
          Magnitude of {mmdDrift.toFixed(4)}.
        </Text>
      </Box>
    </Box>
  );
}

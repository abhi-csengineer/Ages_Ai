import { useEffect, useMemo, useState } from "react";
import { Box, SimpleGrid } from "@chakra-ui/react";
import { motion } from "framer-motion";
import { HeaderBar } from "./components/HeaderBar";
import { StatusBar } from "./components/StatusBar";
import { VigorMeter } from "./components/VigorMeter";
import { VoidUmap } from "./components/VoidUmap";
import { InferenceSidecar } from "./components/InferenceSidecar";
import { ModelComparisonMatrix } from "./components/ModelComparisonMatrix";
import { ParameterRootCause } from "./components/ParameterRootCause";
import { useAegisStream, StreamOrb } from "./hooks/useAegisStream";
import {
  fetchActiveLearningCandidates,
  fetchEmbeddingPoints,
} from "./hooks/useApi";
import { EmbeddingPoint } from "./types/contracts";
import {
  generateMockEmbeddingPoints,
  generateMockMmdSeries,
  generateMockModelComparison,
  generateMockParameterDrifts,
} from "./hooks/mockData";

/* ── Stagger animation for bento tiles ── */
const tileVariants = {
  hidden: { opacity: 0, scale: 0.97 },
  visible: (i: number) => ({
    opacity: 1,
    scale: 1,
    transition: {
      delay: 0.08 + i * 0.07,
      duration: 0.35,
      ease: "easeOut",
    },
  }),
};

const MotionBox = motion(Box);

/* ── Pre-generate stable mock data outside component ── */
const MOCK_POINTS = generateMockEmbeddingPoints();
const MOCK_MMDS = generateMockMmdSeries();

export default function App() {
  /* 1. Custom hook */
  const { telemetry, mmdSeries, streamOrbs, securityLog, connected, tripped } =
    useAegisStream();

  /* 2. All useState in stable order */
  const [realPoints, setRealPoints] = useState<EmbeddingPoint[]>([]);
  const [queueCount, setQueueCount] = useState(14);
  const [pulseTick, setPulseTick] = useState(0);
  const [mockOrbs, setMockOrbs] = useState<StreamOrb[]>([]);


  /* 4. useEffect — fetch real embedding points */
  useEffect(() => {
    const tick = async () => {
      try {
        const [cands, embeds] = await Promise.all([
          fetchActiveLearningCandidates(25),
          fetchEmbeddingPoints(320),
        ]);
        setQueueCount(cands.items.length);
        setRealPoints(embeds.points);
      } catch { /* backend offline */ }
    };
    tick();
    const timer = setInterval(tick, 5000);
    return () => clearInterval(timer);
  }, []);

  /* 5. useEffect — spawn mock stream orbs (always) */
  useEffect(() => {
    const interval = setInterval(() => {
      setPulseTick((t) => t + 1);
      setMockOrbs((prev) => {
        const statuses: Array<"OK" | "DRIFT" | "ATTACK"> = [
          "OK", "OK", "OK", "DRIFT", "DRIFT", "ATTACK",
        ];
        const status = statuses[Math.floor(Math.random() * statuses.length)];
        const orb: StreamOrb = {
          id: `mo-${Date.now()}-${Math.random().toString(36).slice(2, 5)}`,
          x: status === "ATTACK" ? 0.82 + (Math.random() - 0.5) * 0.12
            : status === "DRIFT" ? 0.58 + (Math.random() - 0.5) * 0.2
            : 0.35 + (Math.random() - 0.5) * 0.25,
          y: status === "ATTACK" ? 0.2 + (Math.random() - 0.5) * 0.15
            : status === "DRIFT" ? 0.55 + (Math.random() - 0.5) * 0.25
            : 0.45 + (Math.random() - 0.5) * 0.25,
          status,
        };
        return [...prev, orb].slice(-60);
      });
    }, 800);
    return () => clearInterval(interval);
  }, []);

  /* 6. useEffect — pulse on real batch events */
  useEffect(() => {
    if (!telemetry.batch_event) return;
    setPulseTick((t) => t + 1);
    fetchEmbeddingPoints(320)
      .then((resp) => setRealPoints(resp.points))
      .catch(() => {});
  }, [telemetry.batch_event]);

  /* ── Derived data ── */
  const embeddingPoints = realPoints.length > 50 ? realPoints : [...MOCK_POINTS, ...realPoints];
  const accuracy = telemetry.hui_walter_estimated_accuracy;
  const drift = telemetry.mmd_drift_score;
  const bias = telemetry.bias_score;
  const mmds = mmdSeries.length > 3 ? mmdSeries : MOCK_MMDS;
  const orbs = [...streamOrbs, ...mockOrbs].slice(-80);
  const isCritical = accuracy < 0.9 || tripped;

  /* Model comparison — recalculate when accuracy/drift change */
  const modelComparison = useMemo(
    () => generateMockModelComparison(accuracy, drift),
    [accuracy, drift],
  );

  /* Parameter drift — recalculate when drift changes */
  const parameterDrifts = useMemo(
    () => generateMockParameterDrifts(drift),
    [drift],
  );

  return (
    <Box h="100vh" w="100vw" display="flex" flexDir="column" bg="aegis.black" overflow="hidden">
      <HeaderBar
        connected={connected}
        circuitStatus={telemetry.circuit_status}
        tripped={isCritical}
      />

      {/* Bento Grid: 12 columns, 2 rows */}
      <SimpleGrid
        columns={12}
        spacing={0}
        flex={1}
        minH={0}
        templateRows="1fr 1fr"
        bg="aegis.border"
        gap="1px"
        p="1px"
      >
        {/* Row 1: Vigor(4) | UMAP(5) | Terminal(3) */}
        <MotionBox
          gridColumn="span 4"
          gridRow="span 1"
          minH={0}
          custom={0} variants={tileVariants} initial="hidden" animate="visible"
        >
          <VigorMeter accuracy={accuracy} mmdDrift={drift} biasScore={bias} mmdSeries={mmds} />
        </MotionBox>

        <MotionBox
          gridColumn="span 5"
          gridRow="span 1"
          minH={0}
          custom={1} variants={tileVariants} initial="hidden" animate="visible"
        >
          <VoidUmap points={embeddingPoints} mmdDrift={drift} streamOrbs={orbs} pulseTick={pulseTick} />
        </MotionBox>

        <MotionBox
          gridColumn="span 3"
          gridRow="span 1"
          minH={0}
          custom={2} variants={tileVariants} initial="hidden" animate="visible"
        >
          <InferenceSidecar securityLog={securityLog} />
        </MotionBox>

        {/* Row 2: Model Matrix(6) | Parameter Hub(6) */}
        <MotionBox
          gridColumn="span 6"
          gridRow="span 1"
          minH={0}
          custom={3} variants={tileVariants} initial="hidden" animate="visible"
        >
          <ModelComparisonMatrix models={modelComparison} />
        </MotionBox>

        <MotionBox
          gridColumn="span 6"
          gridRow="span 1"
          minH={0}
          custom={4} variants={tileVariants} initial="hidden" animate="visible"
        >
          <ParameterRootCause parameters={parameterDrifts} />
        </MotionBox>
      </SimpleGrid>

      <StatusBar queueCount={queueCount} driftScore={drift} />
    </Box>
  );
}

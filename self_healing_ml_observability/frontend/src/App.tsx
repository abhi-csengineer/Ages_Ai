import { useEffect, useMemo, useState } from "react";
import { Badge, Box, Flex, SimpleGrid, Text } from "@chakra-ui/react";
import { motion } from "framer-motion";
import { HeaderBar } from "./components/HeaderBar";
import { StatusBar } from "./components/StatusBar";
import { VigorMeter } from "./components/VigorMeter";
import { VoidUmap } from "./components/VoidUmap";
import { InferenceSidecar } from "./components/InferenceSidecar";
import { ModelComparisonMatrix } from "./components/ModelComparisonMatrix";
import { ParameterRootCause } from "./components/ParameterRootCause";
import { useAegisStream, StreamOrb } from "./hooks/useAegisStream";
import { usePersistentColorMode } from "./hooks/usePersistentColorMode";
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

const tileVariants = {
  hidden: { opacity: 0, y: 18, scale: 0.98 },
  visible: (index: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      delay: 0.08 + index * 0.06,
      duration: 0.38,
      ease: "easeOut",
    },
  }),
};

const MotionBox = motion(Box);
const MOCK_POINTS = generateMockEmbeddingPoints();
const MOCK_MMDS = generateMockMmdSeries();

export default function App() {
  const { colorMode, isDarkMode, toggleColorMode } = usePersistentColorMode();
  const { telemetry, mmdSeries, streamOrbs, securityLog, connected, tripped } =
    useAegisStream();

  const [realPoints, setRealPoints] = useState<EmbeddingPoint[]>([]);
  const [queueCount, setQueueCount] = useState(14);
  const [pulseTick, setPulseTick] = useState(0);
  const [mockOrbs, setMockOrbs] = useState<StreamOrb[]>([]);

  useEffect(() => {
    const tick = async () => {
      try {
        const [candidates, embeddings] = await Promise.all([
          fetchActiveLearningCandidates(25),
          fetchEmbeddingPoints(320),
        ]);
        setQueueCount(candidates.items.length);
        setRealPoints(embeddings.points);
      } catch {
        // The dashboard keeps realistic mock data visible when the API is offline.
      }
    };

    tick();
    const timer = window.setInterval(tick, 5000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setPulseTick((currentTick) => currentTick + 1);
      setMockOrbs((previousOrbs) => {
        const statuses: Array<"OK" | "DRIFT" | "ATTACK"> = [
          "OK",
          "OK",
          "OK",
          "DRIFT",
          "DRIFT",
          "ATTACK",
        ];
        const status = statuses[Math.floor(Math.random() * statuses.length)];
        const orb: StreamOrb = {
          id: `mo-${Date.now()}-${Math.random().toString(36).slice(2, 5)}`,
          x:
            status === "ATTACK"
              ? 0.82 + (Math.random() - 0.5) * 0.12
              : status === "DRIFT"
                ? 0.58 + (Math.random() - 0.5) * 0.2
                : 0.35 + (Math.random() - 0.5) * 0.25,
          y:
            status === "ATTACK"
              ? 0.2 + (Math.random() - 0.5) * 0.15
              : status === "DRIFT"
                ? 0.55 + (Math.random() - 0.5) * 0.25
                : 0.45 + (Math.random() - 0.5) * 0.25,
          status,
        };
        return [...previousOrbs, orb].slice(-60);
      });
    }, 800);

    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!telemetry.batch_event) {
      return;
    }

    setPulseTick((currentTick) => currentTick + 1);
    fetchEmbeddingPoints(320)
      .then((response) => setRealPoints(response.points))
      .catch(() => {
        // Ignore transient refresh errors so the live dashboard never blanks out.
      });
  }, [telemetry.batch_event]);

  const embeddingPoints =
    realPoints.length > 50 ? realPoints : [...MOCK_POINTS, ...realPoints];
  const accuracy = telemetry.hui_walter_estimated_accuracy;
  const drift = telemetry.mmd_drift_score;
  const bias = telemetry.bias_score;
  const mmds = mmdSeries.length > 3 ? mmdSeries : MOCK_MMDS;
  const orbs = [...streamOrbs, ...mockOrbs].slice(-80);
  const isCritical = accuracy < 0.9 || tripped;

  const modelComparison = useMemo(
    () => generateMockModelComparison(accuracy, drift),
    [accuracy, drift],
  );

  const parameterDrifts = useMemo(
    () => generateMockParameterDrifts(drift),
    [drift],
  );

  return (
    <Box
      bg="aegis.page"
      color="aegis.text"
      minH="100vh"
      transition="background-color 220ms ease, color 220ms ease"
    >
      <a className="skip-link" href="#dashboard-content">
        Skip to dashboard
      </a>

      <HeaderBar
        connected={connected}
        circuitStatus={telemetry.circuit_status}
        tripped={isCritical}
        isDarkMode={isDarkMode}
        onToggleTheme={toggleColorMode}
      />

      <Box
        aria-hidden="true"
        bgGradient={
          isDarkMode
            ? "radial(circle at top left, rgba(157,255,58,0.14), transparent 34%), radial(circle at top right, rgba(56,189,248,0.10), transparent 30%)"
            : "radial(circle at top left, rgba(37,99,235,0.14), transparent 34%), radial(circle at top right, rgba(20,184,166,0.12), transparent 30%)"
        }
        h="360px"
        left={0}
        pointerEvents="none"
        position="fixed"
        top={0}
        w="100%"
        zIndex={0}
      />

      <Box
        as="main"
        id="dashboard-content"
        maxW="1440px"
        mx="auto"
        px={{ base: 4, md: 6, xl: 8 }}
        py={{ base: 6, md: 8 }}
        position="relative"
        zIndex={1}
      >
        <Flex
          align={{ base: "flex-start", lg: "flex-end" }}
          direction={{ base: "column", lg: "row" }}
          gap={4}
          justify="space-between"
          mb={{ base: 5, md: 7 }}
        >
          <Box maxW="760px">
            <Badge bg="aegis.accentSoft" color="aegis.accent" mb={3}>
              Production command center
            </Badge>
            <Text
              as="h2"
              color="aegis.text"
              fontSize={{ base: "2xl", md: "4xl" }}
              fontWeight={900}
              letterSpacing="-0.04em"
              lineHeight={1.05}
            >
              Monitor drift, security, and model health in one polished workspace.
            </Text>
            <Text color="aegis.textMuted" fontSize={{ base: "sm", md: "md" }} mt={3}>
              Theme preference is saved as <strong>{colorMode}</strong> mode, and the
              interface adapts smoothly from desktop walls to tablet and mobile reviews.
            </Text>
          </Box>
          <StatusBar queueCount={queueCount} driftScore={drift} />
        </Flex>

        <SimpleGrid columns={{ base: 1, lg: 12 }} gap={{ base: 4, md: 5 }}>
          <MotionBox
            gridColumn={{ base: "span 1", lg: "span 4" }}
            minH={{ base: "520px", lg: "680px" }}
            custom={0}
            variants={tileVariants}
            initial="hidden"
            animate="visible"
          >
            <VigorMeter
              accuracy={accuracy}
              mmdDrift={drift}
              biasScore={bias}
              mmdSeries={mmds}
            />
          </MotionBox>

          <MotionBox
            gridColumn={{ base: "span 1", lg: "span 5" }}
            minH={{ base: "420px", md: "540px", lg: "680px" }}
            custom={1}
            variants={tileVariants}
            initial="hidden"
            animate="visible"
          >
            <VoidUmap
              points={embeddingPoints}
              mmdDrift={drift}
              streamOrbs={orbs}
              pulseTick={pulseTick}
            />
          </MotionBox>

          <MotionBox
            gridColumn={{ base: "span 1", lg: "span 3" }}
            minH={{ base: "460px", lg: "680px" }}
            custom={2}
            variants={tileVariants}
            initial="hidden"
            animate="visible"
          >
            <InferenceSidecar securityLog={securityLog} />
          </MotionBox>

          <MotionBox
            gridColumn={{ base: "span 1", lg: "span 6" }}
            minH={{ base: "420px", lg: "500px" }}
            custom={3}
            variants={tileVariants}
            initial="hidden"
            animate="visible"
          >
            <ModelComparisonMatrix models={modelComparison} />
          </MotionBox>

          <MotionBox
            gridColumn={{ base: "span 1", lg: "span 6" }}
            minH={{ base: "420px", lg: "500px" }}
            custom={4}
            variants={tileVariants}
            initial="hidden"
            animate="visible"
          >
            <ParameterRootCause parameters={parameterDrifts} />
          </MotionBox>
        </SimpleGrid>
      </Box>
    </Box>
  );
}

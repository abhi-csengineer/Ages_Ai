import {
  Box,
  Button,
  FormControl,
  Grid,
  GridItem,
  Input,
  Stat,
  StatLabel,
  StatNumber,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useEffect, useMemo, useState } from "react";
import { ActiveLearningTable } from "./components/ActiveLearningTable";
import { CircuitBreakerPulse } from "./components/CircuitBreakerPulse";
import { CriticalInsights } from "./components/CriticalInsights";
import { EvidentlyDriftWidget } from "./components/EvidentlyDriftWidget";
import { HuiWalterGauge } from "./components/HuiWalterGauge";
import { MmdSparkline } from "./components/MmdSparkline";
import { UmapProjectionPanel } from "./components/UmapProjectionPanel";
import {
  collectHealerSamples,
  fetchActiveLearningCandidates,
  fetchEmbeddingPoints,
  inferGemini,
} from "./hooks/useApi";
import { useWebSocket } from "./hooks/useWebSocket";
import { ActiveLearningCandidateItem, EmbeddingPoint } from "./types/contracts";

function QuickStat({ label, value }: { label: string; value: string }) {
  return (
    <Stat p={4} layerStyle="glassPanel">
      <StatLabel
        color="whiteAlpha.700"
        fontSize="xs"
        textTransform="uppercase"
        letterSpacing="0.1em"
      >
        {label}
      </StatLabel>
      <StatNumber fontSize="2xl" color="whiteAlpha.900">
        {value}
      </StatNumber>
    </Stat>
  );
}

export default function App() {
  const { telemetry, mmdSeries, streamOrbs } = useWebSocket();

  const [candidates, setCandidates] = useState<ActiveLearningCandidateItem[]>(
    [],
  );
  const [embeddingPoints, setEmbeddingPoints] = useState<EmbeddingPoint[]>([]);
  const [selectedRequestIds, setSelectedRequestIds] = useState<string[]>([]);
  const [approveLoading, setApproveLoading] = useState(false);
  const [approveProgress, setApproveProgress] = useState(0);
  const [pulseTick, setPulseTick] = useState(0);
  const [prompt, setPrompt] = useState(
    "Summarize the top model monitoring risks from the latest drift event.",
  );
  const [latestGeminiResponse, setLatestGeminiResponse] = useState("");
  const [inferLoading, setInferLoading] = useState(false);

  useEffect(() => {
    const tick = async () => {
      try {
        const [candidateResp, embedResp] = await Promise.all([
          fetchActiveLearningCandidates(25),
          fetchEmbeddingPoints(320),
        ]);
        setCandidates(candidateResp.items);
        setEmbeddingPoints(embedResp.points);
      } catch {
        // Keep dashboard resilient during transient backend issues.
      }
    };

    tick();
    const timer = window.setInterval(tick, 2500);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!telemetry.batch_event) {
      return;
    }
    setPulseTick((t) => t + 1);
    fetchEmbeddingPoints(320)
      .then((resp) => setEmbeddingPoints(resp.points))
      .catch(() => {
        // Keep dashboard resilient during transient backend issues.
      });
  }, [telemetry.batch_event]);

  const retrainLoop = async () => {
    if (approveLoading) {
      return;
    }
    setApproveLoading(true);
    setApproveProgress(4);

    const progressTimer = window.setInterval(() => {
      setApproveProgress((p) => (p < 88 ? p + 6 : p));
    }, 220);

    try {
      await collectHealerSamples(selectedRequestIds);
      setApproveProgress(100);
      const refreshed = await fetchActiveLearningCandidates(50);
      setCandidates(refreshed.items);
      setSelectedRequestIds([]);
    } finally {
      window.clearInterval(progressTimer);
      window.setTimeout(() => {
        setApproveLoading(false);
        setApproveProgress(0);
      }, 800);
    }
  };

  const visibleCandidates = useMemo(() => {
    if (selectedRequestIds.length === 0) {
      return candidates;
    }
    const picked = new Set(selectedRequestIds);
    return candidates.filter((c) => picked.has(c.request_id));
  }, [candidates, selectedRequestIds]);

  const runGeminiInference = async () => {
    if (!prompt.trim() || inferLoading) {
      return;
    }
    setInferLoading(true);
    try {
      const response = await inferGemini({
        request_id: crypto.randomUUID(),
        prompt,
        population_id: 0,
        demographic_group: "general",
      });
      setLatestGeminiResponse(response.response_text);
      const [candidateResp, embedResp] = await Promise.all([
        fetchActiveLearningCandidates(25),
        fetchEmbeddingPoints(320),
      ]);
      setCandidates(candidateResp.items);
      setEmbeddingPoints(embedResp.points);
    } finally {
      setInferLoading(false);
    }
  };

  return (
    <Box
      maxW="1280px"
      mx="auto"
      px={{ base: 3, md: 6 }}
      py={{ base: 4, md: 8 }}
      pb={{ base: "260px", md: "290px" }}
    >
      <VStack align="stretch" spacing={4}>
        <Text
          fontSize={{ base: "2xl", md: "3xl" }}
          fontWeight="bold"
          color="whiteAlpha.900"
        >
          Aegis-AI Command Center
        </Text>

        <CircuitBreakerPulse status={telemetry.circuit_status} />

        <CriticalInsights
          accuracy={telemetry.hui_walter_estimated_accuracy}
          onEngageCircuit={retrainLoop}
          loading={approveLoading}
        />

        <Tabs variant="line" colorScheme="blue" isLazy>
          <TabList borderColor="whiteAlpha.300">
            <Tab
              color="whiteAlpha.800"
              _selected={{ color: "#63B3ED", borderColor: "#63B3ED" }}
            >
              Summary
            </Tab>
            <Tab
              color="whiteAlpha.800"
              _selected={{ color: "#63B3ED", borderColor: "#63B3ED" }}
            >
              Data Drift
            </Tab>
            <Tab
              color="whiteAlpha.800"
              _selected={{ color: "#63B3ED", borderColor: "#63B3ED" }}
            >
              Model Health
            </Tab>
          </TabList>

          <TabPanels>
            <TabPanel px={0} pt={4}>
              <VStack align="stretch" spacing={4}>
                <Box layerStyle="glassPanel" p={4}>
                  <VStack align="stretch" spacing={3}>
                    <FormControl>
                      <Input
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        placeholder="Type prompt for Gemini 1.5 Flash"
                        bg="whiteAlpha.100"
                        borderColor="whiteAlpha.300"
                        color="whiteAlpha.900"
                      />
                    </FormControl>
                    <Button
                      onClick={runGeminiInference}
                      isLoading={inferLoading}
                      loadingText="Invoking Gemini"
                      bgGradient="linear(to-r, #22D3EE, #8B5CF6)"
                      color="white"
                      _hover={{ opacity: 0.9 }}
                    >
                      Run Live Gemini Proxy Inference
                    </Button>
                    {latestGeminiResponse ? (
                      <Box
                        p={3}
                        borderRadius="md"
                        bg="whiteAlpha.100"
                        border="1px solid"
                        borderColor="whiteAlpha.200"
                      >
                        <Text
                          fontSize="sm"
                          color="whiteAlpha.900"
                          noOfLines={5}
                        >
                          {latestGeminiResponse}
                        </Text>
                      </Box>
                    ) : null}
                  </VStack>
                </Box>

                <Grid
                  templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }}
                  gap={4}
                >
                  <QuickStat
                    label="Hui-Walter Accuracy"
                    value={telemetry.hui_walter_estimated_accuracy.toFixed(4)}
                  />
                  <QuickStat
                    label="MMD Drift"
                    value={telemetry.mmd_drift_score.toFixed(4)}
                  />
                  <QuickStat
                    label="Bias Score"
                    value={telemetry.bias_score.toFixed(4)}
                  />
                </Grid>
                <MmdSparkline values={mmdSeries} />
              </VStack>
            </TabPanel>

            <TabPanel px={0} pt={4}>
              <VStack align="stretch" spacing={4}>
                <EvidentlyDriftWidget
                  currentSeries={mmdSeries}
                  driftScore={telemetry.mmd_drift_score}
                />
                <UmapProjectionPanel
                  points={embeddingPoints}
                  mmdDrift={telemetry.mmd_drift_score}
                  pulseTick={pulseTick}
                  streamOrbs={streamOrbs}
                  onLassoSelect={setSelectedRequestIds}
                />
              </VStack>
            </TabPanel>

            <TabPanel px={0} pt={4}>
              <VStack align="stretch" spacing={4}>
                <Grid
                  templateColumns={{ base: "1fr", xl: "300px 1fr" }}
                  gap={4}
                >
                  <GridItem>
                    <HuiWalterGauge
                      accuracy={telemetry.hui_walter_estimated_accuracy}
                    />
                  </GridItem>
                  <GridItem>
                    <QuickStat
                      label="Queued For Healer"
                      value={String(visibleCandidates.length)}
                    />
                  </GridItem>
                </Grid>
              </VStack>
            </TabPanel>
          </TabPanels>
        </Tabs>

        <ActiveLearningTable
          items={visibleCandidates}
          inFlight={approveLoading}
          progress={approveProgress}
          onApprove={retrainLoop}
        />
      </VStack>
    </Box>
  );
}

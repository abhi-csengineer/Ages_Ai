import { Badge, Box, HStack, Text, VStack } from "@chakra-ui/react";
import ReactECharts from "echarts-for-react";

interface EvidentlyDriftWidgetProps {
  currentSeries: number[];
  driftScore: number;
}

function driftStatus(score: number): { label: string; colorScheme: "green" | "yellow" | "red" } {
  if (score < 0.1) {
    return { label: "LOW", colorScheme: "green" };
  }
  if (score <= 0.2) {
    return { label: "MODERATE", colorScheme: "yellow" };
  }
  return { label: "HIGH", colorScheme: "red" };
}

export function EvidentlyDriftWidget({ currentSeries, driftScore }: EvidentlyDriftWidgetProps) {
  const curr = currentSeries.length > 3 ? currentSeries.slice(-36) : [0.02, 0.03, 0.025, 0.04, 0.038, 0.042];
  const baseline = curr.map((v, i) => Math.max(0, v * (0.7 + ((i % 4) * 0.05))));
  const status = driftStatus(driftScore);

  return (
    <Box layerStyle="glassPanel" p={4}>
      <VStack align="stretch" spacing={3}>
        <HStack justify="space-between">
          <Text fontSize="md" fontWeight="bold" color="whiteAlpha.900">
            Data Drift Distribution (MMD)
          </Text>
          <Badge colorScheme={status.colorScheme} px={3} py={1} borderRadius="full" fontSize="xs">
            Drift Score {driftScore.toFixed(4)} · {status.label}
          </Badge>
        </HStack>

        <ReactECharts
          style={{ height: 260 }}
          option={{
            animation: true,
            grid: { top: 24, left: 34, right: 20, bottom: 30 },
            xAxis: {
              type: "category",
              data: curr.map((_, i) => i + 1),
              axisLabel: { color: "#A8B3C5" },
            },
            yAxis: {
              type: "value",
              axisLabel: { color: "#A8B3C5" },
              splitLine: { lineStyle: { color: "rgba(255, 255, 255, 0.08)" } },
            },
            tooltip: { trigger: "axis" },
            legend: {
              top: 0,
              textStyle: { color: "#E6EDF3" },
              data: ["Reference", "Current"],
            },
            series: [
              {
                name: "Reference",
                type: "line",
                smooth: true,
                symbol: "none",
                data: baseline,
                lineStyle: { color: "#5B7DA4", width: 2 },
                areaStyle: { color: "rgba(91, 125, 164, 0.25)" },
              },
              {
                name: "Current",
                type: "line",
                smooth: true,
                symbol: "none",
                data: curr,
                lineStyle: { color: "#F97316", width: 2.2 },
                areaStyle: { color: "rgba(249, 115, 22, 0.20)" },
              },
            ],
          }}
        />
      </VStack>
    </Box>
  );
}

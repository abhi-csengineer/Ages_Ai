import { Box, Text } from "@chakra-ui/react";
import ReactECharts from "echarts-for-react";

interface EmbeddingSpacePanelProps {
  reference: number[][];
  detection: number[][];
  chaosActive: boolean;
  driftPhase: number;
}

function toPoints(vectors: number[][], jitter = 0): [number, number][] {
  return vectors
    .filter((v) => v.length >= 2)
    .map((v) => [v[0] + jitter, v[1] + jitter * 0.6]);
}

export function EmbeddingSpacePanel({ reference, detection, chaosActive, driftPhase }: EmbeddingSpacePanelProps) {
  const driftJitter = chaosActive ? driftPhase * 0.035 : 0;
  const refPoints = toPoints(reference.slice(0, 350));
  const livePoints = toPoints(detection.slice(0, 350), driftJitter);

  return (
    <Box p={4} borderRadius="xl" bg="rgba(12, 17, 30, 0.82)" border="1px solid" borderColor="whiteAlpha.200">
      <Text fontSize="xs" textTransform="uppercase" letterSpacing="0.12em" color="whiteAlpha.700" mb={2}>
        UMAP Embedding Space
      </Text>
      <ReactECharts
        style={{ height: 320 }}
        option={{
          animation: true,
          grid: { top: 10, left: 24, right: 14, bottom: 26 },
          xAxis: { type: "value", splitLine: { lineStyle: { color: "rgba(255,255,255,0.08)" } } },
          yAxis: { type: "value", splitLine: { lineStyle: { color: "rgba(255,255,255,0.08)" } } },
          legend: { textStyle: { color: "#dbe5f6" } },
          tooltip: { trigger: "item" },
          series: [
            {
              name: "Reference",
              type: "scatter",
              data: refPoints,
              symbolSize: 7,
              itemStyle: { color: "rgba(80, 173, 255, 0.68)" },
            },
            {
              name: chaosActive ? "Live (Drifting)" : "Live",
              type: "scatter",
              data: livePoints,
              symbolSize: 8,
              itemStyle: { color: chaosActive ? "rgba(255, 89, 89, 0.95)" : "rgba(2, 235, 156, 0.86)" },
              emphasis: { scale: true },
            },
          ],
        }}
      />
    </Box>
  );
}

import { Box, Text } from "@chakra-ui/react";
import ReactECharts from "echarts-for-react";

interface MmdSparklineProps {
  values: number[];
}

export function MmdSparkline({ values }: MmdSparklineProps) {
  const data = values.length > 0 ? values : [0];

  return (
    <Box p={4} layerStyle="glassPanel">
      <Text
        fontSize="xs"
        textTransform="uppercase"
        letterSpacing="0.12em"
        color="whiteAlpha.700"
        mb={2}
      >
        MMD Drift Magnitude
      </Text>
      <ReactECharts
        style={{ height: 120 }}
        option={{
          animation: true,
          backgroundColor: "transparent",
          grid: { top: 10, left: 10, right: 10, bottom: 14 },
          xAxis: { type: "category", show: false, data: data.map((_, i) => i) },
          yAxis: { type: "value", show: false, min: 0 },
          series: [
            {
              type: "line",
              data,
              smooth: true,
              symbol: "none",
              lineStyle: { width: 2.5, color: "#3182CE" },
              areaStyle: { color: "rgba(49, 130, 206, 0.18)" },
            },
          ],
          tooltip: { trigger: "axis" },
        }}
      />
    </Box>
  );
}

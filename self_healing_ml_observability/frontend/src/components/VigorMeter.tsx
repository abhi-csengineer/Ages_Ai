import { Box, Flex, HStack, Text, Stat, StatLabel, StatNumber } from "@chakra-ui/react";
import { motion } from "framer-motion";

interface VigorMeterProps {
  accuracy: number;
  mmdDrift: number;
  biasScore: number;
  mmdSeries: number[];
}

const MotionLine = motion.line;

export function VigorMeter({ accuracy, mmdDrift, biasScore, mmdSeries }: VigorMeterProps) {
  const pct = Math.max(0, Math.min(100, accuracy * 100));
  const isCritical = accuracy < 0.90;
  const isDegraded = accuracy < 0.95 && accuracy >= 0.90;
  const needleDeg = -120 + (pct / 100) * 240;
  const arcOffset = 1 - pct / 100;

  const statusLabel = isCritical ? "CRITICAL" : isDegraded ? "DEGRADED" : "NOMINAL";
  const statusColor = isCritical ? "aegis.red" : isDegraded ? "aegis.orange" : "aegis.lime";
  const arcColor = isCritical ? "#FF0033" : isDegraded ? "#FF4D00" : "#CCFF00";

  /* sparkline */
  const sparkData = mmdSeries.length > 0 ? mmdSeries.slice(-30) : [0];
  const sparkMax = Math.max(...sparkData, 0.01);
  const sparkW = 200;
  const sparkH = 28;
  const sparkPath = sparkData
    .map((v, i) => {
      const x = (i / Math.max(sparkData.length - 1, 1)) * sparkW;
      const y = sparkH - (v / sparkMax) * sparkH;
      return `${i === 0 ? "M" : "L"}${x},${y}`;
    })
    .join(" ");

  return (
    <Box
      h="100%"
      bg="aegis.black"
      border="1px solid"
      borderColor={isCritical ? "aegis.red" : "aegis.border"}
      p={0}
      display="flex"
      flexDir="column"
      overflow="hidden"
      position="relative"
      sx={isCritical ? { animation: "crtGlitch 0.15s infinite" } : {}}
    >
      {/* Tile header */}
      <Flex
        px={3}
        py={1.5}
        borderBottom="1px solid"
        borderColor="aegis.border"
        justify="space-between"
        align="center"
        flexShrink={0}
      >
        <Text fontSize="0.55rem" color="aegis.textDim" letterSpacing="0.15em">
          TILE-A // VIGOR METER
        </Text>
      </Flex>

      {/* Body */}
      <Flex flex={1} direction="column" align="center" justify="center" gap={2} p={3}>
        {/* Status badge */}
        <HStack spacing={2}>
          <Box w="6px" h="6px" bg={statusColor} boxShadow={`0 0 6px ${arcColor}`} />
          <Text fontSize="0.6rem" color={statusColor} letterSpacing="0.15em" fontWeight={700}>
            {statusLabel}
          </Text>
        </HStack>

        {/* Giant readout */}
        <Text
          fontSize="3.5rem"
          fontWeight={800}
          color={statusColor}
          lineHeight={1}
          letterSpacing="0.08em"
          sx={isCritical ? { textShadow: "0 0 20px rgba(255,0,51,0.6)" } : {}}
        >
          {accuracy.toFixed(4)}
        </Text>
        <Text fontSize="0.5rem" color="aegis.textDim" letterSpacing="0.2em">
          HUI-WALTER ESTIMATED ACCURACY
        </Text>

        {/* SVG gauge */}
        <Box w="160px" h="90px" mt={1}>
          <svg viewBox="0 0 200 110" width="100%" height="100%">
            <path d="M 24 100 A 76 76 0 0 1 176 100" fill="none" stroke="#2D3748" strokeWidth="6" />
            <path
              d="M 24 100 A 76 76 0 0 1 176 100"
              fill="none"
              stroke={arcColor}
              strokeWidth="6"
              pathLength={1}
              strokeDasharray={1}
              strokeDashoffset={arcOffset}
            />
            <g transform="translate(100,100)">
              <MotionLine
                x1="0" y1="0" x2="0" y2="-58"
                stroke={arcColor}
                strokeWidth="2"
                animate={{ rotate: needleDeg }}
                transition={{ type: "spring", stiffness: 130, damping: 12, mass: 0.55 }}
                style={{ transformOrigin: "0px 0px" }}
              />
              <rect x="-3" y="-3" width="6" height="6" fill={arcColor} />
            </g>
          </svg>
        </Box>

        {/* Secondary stats */}
        <HStack spacing={3} w="100%">
          <Stat size="xs" textAlign="center" p={2} border="1px solid" borderColor="aegis.border" flex={1}>
            <StatLabel>MMD DRIFT</StatLabel>
            <StatNumber fontSize="sm" color={mmdDrift > 0.2 ? "aegis.orange" : "aegis.lime"}>
              {mmdDrift.toFixed(4)}
            </StatNumber>
          </Stat>
          <Stat size="xs" textAlign="center" p={2} border="1px solid" borderColor="aegis.border" flex={1}>
            <StatLabel>BIAS</StatLabel>
            <StatNumber fontSize="sm" color="aegis.lime">
              {biasScore.toFixed(4)}
            </StatNumber>
          </Stat>
          <Box flex={1} p={2} border="1px solid" borderColor="aegis.border">
            <Text fontSize="0.5rem" color="aegis.textDim" letterSpacing="0.12em" mb={1}>
              TREND
            </Text>
            <svg viewBox={`0 0 ${sparkW} ${sparkH}`} width="100%" height="28">
              <path d={sparkPath} fill="none" stroke="#CCFF00" strokeWidth="1.5" opacity="0.7" />
            </svg>
          </Box>
        </HStack>
      </Flex>
    </Box>
  );
}

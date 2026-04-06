import { Box, Text, VStack } from "@chakra-ui/react";
import { motion } from "framer-motion";

interface HuiWalterGaugeProps {
  accuracy: number;
}

const MotionLine = motion.line;

export function HuiWalterGauge({ accuracy }: HuiWalterGaugeProps) {
  const pct = Math.max(0, Math.min(100, accuracy * 100));
  const needleDeg = -120 + (pct / 100) * 240;
  const arcOffset = 1 - pct / 100;

  return (
    <Box p={4} layerStyle="glassPanel">
      <VStack spacing={3} align="start">
        <Text
          fontSize="xs"
          textTransform="uppercase"
          letterSpacing="0.12em"
          color="whiteAlpha.700"
        >
          Vigor Gauge · Hui-Walter Accuracy
        </Text>
        <Box position="relative" w="190px" h="132px">
          <svg viewBox="0 0 200 140" width="100%" height="100%">
            <defs>
              <linearGradient
                id="vigor-gradient"
                x1="0%"
                y1="0%"
                x2="100%"
                y2="0%"
              >
                <stop offset="0%" stopColor="#22D3EE" />
                <stop offset="100%" stopColor="#8B5CF6" />
              </linearGradient>
            </defs>

            <path
              d="M 24 116 A 76 76 0 0 1 176 116"
              fill="none"
              stroke="rgba(255,255,255,0.16)"
              strokeWidth="12"
              strokeLinecap="round"
            />
            <path
              d="M 24 116 A 76 76 0 0 1 176 116"
              fill="none"
              stroke="url(#vigor-gradient)"
              strokeWidth="12"
              strokeLinecap="round"
              pathLength={1}
              strokeDasharray={1}
              strokeDashoffset={arcOffset}
            />

            <g transform="translate(100,116)">
              <MotionLine
                x1="0"
                y1="0"
                x2="0"
                y2="-62"
                stroke="#CFFAFE"
                strokeWidth="3"
                strokeLinecap="round"
                animate={{ rotate: needleDeg }}
                transition={{
                  type: "spring",
                  stiffness: 130,
                  damping: 12,
                  mass: 0.55,
                }}
                style={{ transformOrigin: "0px 0px" }}
              />
              <circle r="6" fill="#A5F3FC" />
            </g>
          </svg>
          <Box
            position="absolute"
            inset="0"
            display="grid"
            placeItems="end center"
            pb="6px"
          >
            <Text fontSize="2xl" fontWeight="semibold" color="#C4B5FD">
              {pct.toFixed(1)}%
            </Text>
          </Box>
        </Box>
      </VStack>
    </Box>
  );
}

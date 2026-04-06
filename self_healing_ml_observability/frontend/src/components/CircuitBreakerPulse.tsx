import { Box, HStack, Text } from "@chakra-ui/react";
import { keyframes } from "@emotion/react";

interface CircuitBreakerPulseProps {
  status: string;
}

const breath = keyframes`
  0% { transform: scale(1); opacity: 0.8; }
  50% { transform: scale(1.12); opacity: 1; }
  100% { transform: scale(1); opacity: 0.8; }
`;

export function CircuitBreakerPulse({ status }: CircuitBreakerPulseProps) {
  const tripped =
    status === "DRIFT_BIAS" ||
    status === "FALLBACK_MODE" ||
    status === "SECURITY_ATTACK";
  const color = tripped ? "#FF5D73" : "#22C55E";

  return (
    <Box layerStyle="glassPanel" p={4}>
      <HStack spacing={3}>
        <Box
          w="14px"
          h="14px"
          borderRadius="full"
          bg={color}
          boxShadow={
            tripped
              ? "0 0 20px rgba(255, 93, 115, 0.9)"
              : "0 0 20px rgba(34, 197, 94, 0.9)"
          }
          animation={`${breath} 1.4s ease-in-out infinite`}
        />
        <Text color="whiteAlpha.900" fontWeight="bold" letterSpacing="0.03em">
          Circuit Breaker · {tripped ? "TRIPPED" : "STABLE"}
        </Text>
      </HStack>
    </Box>
  );
}

import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Box,
  Button,
  HStack,
  Text,
  VStack,
} from "@chakra-ui/react";

interface CriticalInsightsProps {
  accuracy: number;
  onEngageCircuit: () => void;
  loading: boolean;
}

export function CriticalInsights({
  accuracy,
  onEngageCircuit,
  loading,
}: CriticalInsightsProps) {
  const isCritical = accuracy < 0.9;

  return (
    <Box layerStyle="glassPanel" p={4}>
      <VStack align="stretch" spacing={3}>
        <Text fontSize="lg" fontWeight="bold" color="whiteAlpha.900">
          Critical Insights
        </Text>

        {isCritical ? (
          <Alert
            status="error"
            variant="left-accent"
            borderRadius="md"
            alignItems="center"
          >
            <AlertIcon />
            <Box flex="1">
              <AlertTitle>
                CRITICAL DECAY DETECTED: Engage Circuit Breaker?
              </AlertTitle>
              <AlertDescription>
                Hui-Walter Estimated Accuracy is {accuracy.toFixed(4)}, below
                the safe threshold of 0.9000.
              </AlertDescription>
            </Box>
            <Button
              colorScheme="red"
              onClick={onEngageCircuit}
              isLoading={loading}
              loadingText="Engaging"
            >
              Engage
            </Button>
          </Alert>
        ) : (
          <HStack
            justify="space-between"
            p={3}
            borderRadius="md"
            bg="rgba(34,197,94,0.15)"
            border="1px solid rgba(134,239,172,0.35)"
          >
            <Text color="#86EFAC" fontWeight="semibold">
              Model operating within expected health envelope.
            </Text>
            <Text color="#86EFAC" fontFamily="mono">
              Accuracy {accuracy.toFixed(4)}
            </Text>
          </HStack>
        )}
      </VStack>
    </Box>
  );
}

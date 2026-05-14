import { Flex, HStack, Text, VStack } from "@chakra-ui/react";

interface StatusBarProps {
  queueCount: number;
  driftScore: number;
}

export function StatusBar({ queueCount, driftScore }: StatusBarProps) {
  return (
    <Flex
      aria-label="System summary"
      as="aside"
      bg="aegis.surface"
      border="1px solid"
      borderColor="aegis.border"
      borderRadius="2xl"
      boxShadow="aegis.card"
      gap={4}
      minW={{ base: "100%", lg: "390px" }}
      p={4}
      wrap="wrap"
    >
      <Metric label="Queue" value={queueCount.toString()} />
      <Metric label="MMD drift" value={driftScore.toFixed(4)} />
      <Metric label="System" value="AEGIS-7A" />
    </Flex>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <VStack align="flex-start" flex="1 1 90px" spacing={0}>
      <Text
        color="aegis.textFaint"
        fontSize="0.65rem"
        fontWeight={800}
        letterSpacing="0.12em"
        textTransform="uppercase"
      >
        {label}
      </Text>
      <HStack spacing={2}>
        <Text color="aegis.accent" fontFamily="mono" fontSize="md" fontWeight={900}>
          {value}
        </Text>
      </HStack>
    </VStack>
  );
}

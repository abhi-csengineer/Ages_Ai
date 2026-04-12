import { Flex, HStack, Text } from "@chakra-ui/react";

interface StatusBarProps {
  queueCount: number;
  driftScore: number;
}

export function StatusBar({ queueCount, driftScore }: StatusBarProps) {
  return (
    <Flex
      h="28px"
      bg="aegis.black"
      borderTop="1px solid"
      borderColor="aegis.border"
      align="center"
      px={4}
      justify="space-between"
      flexShrink={0}
    >
      <HStack spacing={4}>
        <Text fontSize="0.5rem" color="aegis.textDim" letterSpacing="0.12em">
          ▦ QUEUE: {queueCount}
        </Text>
        <Text fontSize="0.5rem" color="aegis.textDim" letterSpacing="0.12em">
          ◈ MMD: {driftScore.toFixed(4)}
        </Text>
      </HStack>
      <Text fontSize="0.5rem" color="aegis.textDim" letterSpacing="0.12em">
        SYS ID: AEGIS-7A &nbsp;|&nbsp; V2.4.1
      </Text>
    </Flex>
  );
}

import { Badge, Box, HStack, Text } from "@chakra-ui/react";
import { motion } from "framer-motion";

const MotionBox = motion(Box);

interface VitalSignsHeaderProps {
  tripped: boolean;
  connected: boolean;
  status: string;
}

export function VitalSignsHeader({ tripped, connected, status }: VitalSignsHeaderProps) {
  return (
    <Box
      p={4}
      borderRadius="xl"
      bg="rgba(10, 19, 34, 0.8)"
      border="1px solid"
      borderColor="whiteAlpha.200"
      backdropFilter="blur(8px)"
    >
      <HStack justify="space-between" align="center">
        <Box>
          <Text fontSize="xs" textTransform="uppercase" color="whiteAlpha.700" letterSpacing="0.12em">
            Vital Signs
          </Text>
          <Text fontSize={{ base: "xl", md: "2xl" }} fontWeight="bold">
            Circuit Breaker: {tripped ? "TRIPPED" : "OK"}
          </Text>
        </Box>

        <HStack spacing={3}>
          <MotionBox
            w="14px"
            h="14px"
            borderRadius="full"
            bg={tripped ? "red.400" : "green.400"}
            boxShadow={tripped ? "0 0 24px rgba(248, 113, 113, 0.95)" : "0 0 16px rgba(34, 197, 94, 0.9)"}
            animate={
              tripped
                ? { scale: [1, 1.25, 1], opacity: [1, 0.7, 1] }
                : { scale: [1, 1.05, 1], opacity: [1, 0.9, 1] }
            }
            transition={{ duration: tripped ? 0.9 : 2.0, repeat: Infinity }}
          />
          <Badge colorScheme={connected ? "green" : "orange"} px={2} py={1} borderRadius="md">
            {connected ? "LIVE" : "RECONNECTING"}
          </Badge>
          <Badge colorScheme={tripped ? "red" : "green"} px={2} py={1} borderRadius="md">
            {status}
          </Badge>
        </HStack>
      </HStack>
    </Box>
  );
}

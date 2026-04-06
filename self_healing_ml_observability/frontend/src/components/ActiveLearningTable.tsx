import {
  Box,
  Button,
  HStack,
  Progress,
  Text,
  VStack,
  Flex,
  SimpleGrid,
} from "@chakra-ui/react";
import { motion } from "framer-motion";
import { ActiveLearningCandidateItem } from "../types/contracts";

interface ActiveLearningTableProps {
  items: ActiveLearningCandidateItem[];
  inFlight: boolean;
  progress: number;
  onApprove: () => void;
}

export function ActiveLearningTable({
  items,
  inFlight,
  progress,
  onApprove,
}: ActiveLearningTableProps) {
  const MotionBox = motion(Box);

  return (
    <Box
      position="fixed"
      left="50%"
      bottom={{ base: "14px", md: "20px" }}
      transform="translateX(-50%)"
      w={{ base: "calc(100% - 20px)", md: "min(980px, calc(100% - 48px))" }}
      zIndex={30}
      p={4}
      layerStyle="glassPanel"
    >
      <HStack justify="space-between" mb={3}>
        <VStack align="start" spacing={0}>
          <Text
            fontSize="xs"
            textTransform="uppercase"
            letterSpacing="0.12em"
            color="whiteAlpha.700"
          >
            Active Learning Queue
          </Text>
          <Text fontSize="sm" color="whiteAlpha.800">
            Swipe cards to triage candidates
          </Text>
        </VStack>
        <Button
          bgGradient="linear(to-r, #F97316, #FB7185)"
          color="white"
          size="sm"
          onClick={onApprove}
          isLoading={inFlight}
          loadingText="Triggering retrain"
          _hover={{
            transform: "translateY(-1px)",
            boxShadow:
              "0 0 0 1px rgba(255,255,255,0.16), 0 8px 20px rgba(251, 113, 133, 0.18)",
          }}
        >
          Label & Approve
        </Button>
      </HStack>

      {inFlight && (
        <Progress
          mb={3}
          size="sm"
          hasStripe
          isAnimated
          value={progress}
          colorScheme="orange"
        />
      )}

      <Box
        overflowX="auto"
        css={{
          scrollSnapType: "x mandatory",
          WebkitOverflowScrolling: "touch",
        }}
      >
        <Flex gap={3} minW="max-content" pb={1}>
          {items.map((item, idx) => {
            const c = Math.max(0, Math.min(1, item.confidence));
            const u = Math.max(0, Math.min(1, item.uncertainty));
            return (
              <MotionBox
                key={item.request_id}
                minW={{ base: "250px", md: "280px" }}
                p={3}
                borderRadius="lg"
                bg="rgba(255,255,255,0.035)"
                border="1px solid"
                borderColor="rgba(255,255,255,0.1)"
                scrollSnapAlign="start"
                initial={{ opacity: 0, y: 14, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{
                  duration: 0.35,
                  delay: Math.min(idx * 0.06, 0.36),
                }}
              >
                <VStack align="stretch" spacing={2}>
                  <Text
                    fontFamily="mono"
                    fontSize="xs"
                    color="whiteAlpha.900"
                    noOfLines={1}
                  >
                    {item.request_id}
                  </Text>
                  <SimpleGrid columns={2} spacing={2}>
                    <Box p={2} borderRadius="md" bg="rgba(34,197,94,0.18)">
                      <Text fontSize="xs" color="whiteAlpha.700">
                        Confidence
                      </Text>
                      <Text fontWeight="bold" color="#86EFAC">
                        {(c * 100).toFixed(1)}%
                      </Text>
                    </Box>
                    <Box p={2} borderRadius="md" bg="rgba(248,113,113,0.18)">
                      <Text fontSize="xs" color="whiteAlpha.700">
                        Uncertainty
                      </Text>
                      <Text fontWeight="bold" color="#FDA4AF">
                        {(u * 100).toFixed(1)}%
                      </Text>
                    </Box>
                  </SimpleGrid>
                </VStack>
              </MotionBox>
            );
          })}
        </Flex>
      </Box>
    </Box>
  );
}
